"""Tests for scoped hot-reload (`world_reload`: `native/earthfast/src/reload.rs`, `server/earthd.py`,
`server/blockworker.py`, `server/grading.py`).

Verifies:
  - Rust `reload` kernel scope validation, bitmasks, and `PLAN_NEUTRAL` config digest invariance;
  - `world_reload` capability key (`restart.key`) and connection-lease enforcement;
  - non-plan reloads (`roads`, `veg`, `surface`, `signs`, `nav`) reset only the targeted trackers and leave
    `PlanStore` road plans and `Grader._mapped` untouched;
  - `"plans"` reloads trigger `PlanStore.late_reset` / `_State.late_reset` ONLY on targeted cells while keeping
    other cells intact.
"""
import os
import sys
import threading
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
ROOT = SERVER.parent
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import blockworker  # noqa: E402
import earthd  # noqa: E402
import fast  # noqa: E402
import geodesy  # noqa: E402
import grading  # noqa: E402
import mapcells  # noqa: E402
import revisit  # noqa: E402
import srvrestart  # noqa: E402


class RustReloadKernelTest(unittest.TestCase):
    def test_scope_validation_and_mask(self):
        self.assertEqual(fast.reload_scope_mask(["roads", "veg", "roads"]), (1 << 1) | (1 << 2))
        self.assertEqual(
            fast.reload_scope_mask(["nav", "signs", "surface", "veg", "roads", "plans"]),
            0x3F,
        )
        with self.assertRaises(ValueError):
            fast.reload_scope_mask([])
        with self.assertRaises(ValueError):
            fast.reload_scope_mask(["roads", "unknown_scope"])

    def test_plan_neutral_config_digests(self):
        f0, p0 = fast.reload_config_digests(None)
        f1, p1 = fast.reload_config_digests('{"BNE_ROADSIGNS": true, "BNE_CATENARY": "1", "BNE_WEAR_STRIPS": true}')
        self.assertNotEqual(f0, f1)
        self.assertEqual(p0, p1, "PLAN_NEUTRAL switches must never alter the road-plans digest")
        for k in revisit.PLAN_NEUTRAL:
            _, pk = fast.reload_config_digests(f'{{"{k}": "on"}}')
            self.assertEqual(pk, p0, k)
        f2, p2 = fast.reload_config_digests('{"BNE_GRADE_GUARD": "on"}')
        self.assertNotEqual(p0, p2, "non-neutral switches alter the road-plans digest")

    def test_reload_plan_non_plan_vs_plans(self):
        p_non = fast.reload_plan(
            ["veg", "roads", "signs"],
            clear_cells=[(14, 8400, 5900)],
            active_cells=[(14, 8400, 5900), (14, 8401, 5900)],
            config_json='{"BNE_ROADSIGNS": true}',
            serial=1,
        )
        self.assertEqual(p_non["scopes"], ["roads", "veg", "signs"])
        self.assertFalse(p_non["invalidates_plans"])
        self.assertIsNone(p_non["plans_epoch"])
        self.assertEqual(p_non["evict_cells"], [])

        p_plans = fast.reload_plan(
            ["plans", "roads"],
            clear_cells=[(14, 8405, 5902), (14, 8402, 5901), (14, 8405, 5902)],
            active_cells=[(14, 8400, 5900)],
            config_json='{"BNE_GRADE_GUARD": "on"}',
            serial=2,
        )
        self.assertTrue(p_plans["invalidates_plans"])
        self.assertIsNotNone(p_plans["plans_epoch"])
        self.assertEqual(p_plans["evict_cells"], [(14, 8402, 5901), (14, 8405, 5902)])


class SelectiveLateResetTest(unittest.TestCase):
    def test_planstore_and_blockworker_selective_late_reset(self):
        store = grading.PlanStore(mapdata=None, elev=lambda la, lo: 0.0)
        c1 = mapcells.CellKey(14, 8400, 5900)
        c2 = mapcells.CellKey(14, 8401, 5900)
        pl1 = store.planner_of_cell(c1)
        pl2 = store.planner_of_cell(c2)
        pl1.cells[c1] = [("r1", "plan1")]
        pl1.keeps[c1] = [("k1", 4.0)]
        pl1.__dict__.setdefault("_road_stages", {})[c1] = "stage1"
        pl2.cells[c2] = [("r2", "plan2")]
        pl2.keeps[c2] = [("k2", 4.0)]
        pl2.__dict__.setdefault("_road_stages", {})[c2] = "stage2"

        gr = grading.Grader(geodesy.EnuFrame(44.0, 4.7), None, lambda la, lo: 0.0, store=store)
        gr._mapped[c1] = [("r1", "mapped1")]
        gr._mapped[c2] = [("r2", "mapped2")]

        st = blockworker._State.__new__(blockworker._State)
        st.lock = threading.Lock()
        st.plan_store = store
        st.graders = {1: gr}
        st.chunks = {}
        st.late_resets = 0

        st.late_reset([c1])
        self.assertEqual(st.late_resets, 1)
        self.assertNotIn(c1, pl1.cells)
        self.assertNotIn(c1, pl1.keeps)
        self.assertNotIn(c1, pl1.__dict__.get("_road_stages", {}))
        self.assertNotIn(c1, gr._mapped)
        # Untargeted cell c2 remains intact in both PlanStore and Grader._mapped
        self.assertEqual(pl2.cells.get(c2), [("r2", "plan2")])
        self.assertEqual(pl2.keeps.get(c2), [("k2", 4.0)])
        self.assertEqual(pl2.__dict__.get("_road_stages", {}).get(c2), "stage2")
        self.assertEqual(gr._mapped.get(c2), [("r2", "mapped2")])


class WorldReloadDispatchTest(unittest.TestCase):
    def make_fixture(self):
        s = earthd.Server.__new__(earthd.Server)
        s.restart_key = "ab" * 16
        s.reload_serial = 0
        s.reload_epoch = None
        s.plans_reload_epoch = None
        s.plan_store = grading.PlanStore(mapdata=None, elev=lambda la, lo: 0.0)
        c1 = mapcells.CellKey(14, 8400, 5900)
        c2 = mapcells.CellKey(14, 8401, 5900)
        s.plan_store.planner_of_cell(c1).cells[c1] = [("r1", "plan1")]
        s.plan_store.planner_of_cell(c2).cells[c2] = [("r2", "plan2")]
        gr = grading.Grader(geodesy.EnuFrame(44.0, 4.7), None, lambda la, lo: 0.0, store=s.plan_store)
        gr._mapped[c1] = [("r1", "mapped1")]
        gr._mapped[c2] = [("r2", "mapped2")]
        s.anchors = {1: types.SimpleNamespace(id=1, grader=gr, stale=())}
        s.hm = {(1, 0, 0): {"ter": "t.ter"}}
        s.base_stale = set()
        s.roads = False

        sent = []
        signs_refreshed = []
        veg_forgotten = []
        nav_refreshed = []
        roads_closed = []

        conn = earthd.Connection.__new__(earthd.Connection)
        conn.s = s
        conn.closing = False
        conn.active = 1
        conn.road_geo = False
        conn.swap_gen = False
        conn.lease = types.SimpleNamespace(connection=conn)
        conn.send = lambda m: sent.append(m)
        conn.roads = types.SimpleNamespace(close=lambda: roads_closed.append(1))
        conn.signs = types.SimpleNamespace(refresh=lambda: signs_refreshed.append(1))
        conn.veg = types.SimpleNamespace(forget=lambda: veg_forgotten.append(1))
        conn.nav = types.SimpleNamespace(refresh=lambda: nav_refreshed.append(1))
        return s, conn, gr, (c1, c2), sent, roads_closed, signs_refreshed, veg_forgotten, nav_refreshed

    def test_bad_key_and_unauthenticated_connection_rejected(self):
        s, conn, gr, (c1, c2), sent, roads_closed, *_ = self.make_fixture()
        for bad_msg in (
            {"type": "world_reload", "key": "00" * 16, "scopes": ["roads"]},
            {"type": "world_reload", "key": "", "scopes": ["plans"]},
            {"type": "world_reload", "scopes": ["roads"]},
        ):
            conn.dispatch(bad_msg)
            self.assertFalse(sent[-1]["ok"])
            self.assertIn("restart key", sent[-1]["error"])
        # Stray connection without hello lease
        conn_no_lease = earthd.Connection.__new__(earthd.Connection)
        conn_no_lease.s = s
        conn_no_lease.closing = False
        conn_no_lease.lease = None
        conn_no_lease.send = lambda m: sent.append(m)
        conn_no_lease.dispatch({"type": "world_reload", "key": s.restart_key, "scopes": ["roads"]})
        self.assertFalse(sent[-1]["ok"])
        self.assertIn("no hello", sent[-1]["error"])
        # Nothing evicted or reset
        self.assertEqual(roads_closed, [])
        self.assertIn(c1, s.plan_store.planner_of_cell(c1).cells)
        self.assertIn(c2, s.plan_store.planner_of_cell(c2).cells)

    def test_scoped_non_plan_reload_leaves_plans_untouched(self):
        s, conn, gr, (c1, c2), sent, roads_closed, signs_refreshed, veg_forgotten, nav_refreshed = self.make_fixture()
        conn.dispatch({
            "type": "world_reload",
            "key": s.restart_key,
            "scopes": ["roads", "veg", "signs"],
            "clear_cells": [[14, 8400, 5900]],
            "config": {"BNE_WEAR_STRIPS": True, "BNE_ROADSIGNS": True},
        })
        ans = sent[-1]
        self.assertTrue(ans["ok"], ans)
        self.assertEqual(ans["scopes"], ["roads", "veg", "signs"])
        self.assertIsNone(ans["plansEpoch"])
        self.assertEqual(ans["evicted"], [])
        self.assertIsNone(s.plans_reload_epoch)
        self.assertEqual(len(roads_closed), 1)
        self.assertEqual(len(signs_refreshed), 1)
        self.assertEqual(len(veg_forgotten), 1)
        self.assertEqual(len(nav_refreshed), 0)
        # Road plans in PlanStore and Grader._mapped remain untouched!
        self.assertIn(c1, s.plan_store.planner_of_cell(c1).cells)
        self.assertIn(c2, s.plan_store.planner_of_cell(c2).cells)
        self.assertIn(c1, gr._mapped)
        self.assertIn(c2, gr._mapped)

    def test_scoped_plans_reload_evicts_only_targeted_cells(self):
        s, conn, gr, (c1, c2), sent, roads_closed, *_ = self.make_fixture()
        conn.dispatch({
            "type": "world_reload",
            "key": s.restart_key,
            "scopes": ["plans", "roads"],
            "clear_cells": [[c1.z, c1.x, c1.y]],
            "config": {"BNE_GRADE_GUARD": "on"},
        })
        ans = sent[-1]
        self.assertTrue(ans["ok"], ans)
        self.assertEqual(ans["scopes"], ["plans", "roads"])
        self.assertIsNotNone(ans["plansEpoch"])
        self.assertEqual(ans["evicted"], [[c1.z, c1.x, c1.y]])
        self.assertEqual(len(roads_closed), 1)
        # Targeted cell c1 evicted from both PlanStore and Grader._mapped
        self.assertNotIn(c1, s.plan_store.planner_of_cell(c1).cells)
        self.assertNotIn(c1, gr._mapped)
        # Untargeted cell c2 stays cached in memory
        self.assertIn(c2, s.plan_store.planner_of_cell(c2).cells)
        self.assertIn(c2, gr._mapped)


if __name__ == "__main__":
    unittest.main()
