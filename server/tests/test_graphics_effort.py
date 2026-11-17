"""Tests for deterministic graphics effort/density scaling (`poc/graphics-effort`:
`native/earthfast/src/geotiles.rs`, `server/earthd.py` `Connection.set_graphics`, `mod/.../settings.lua`).

Verifies:
  - Rust `fast.scale_graphics_effort` deterministic `dm::Dm` scaling, `[0.5, 3.0]` clamping, and `photoPx` tier stepping;
  - `Connection.set_graphics` applies `effortScale` across terrain LOD (`lod_scale`), vegetation reach (`veg.send_m`),
    and building/skyline/bridge reach (`bldfar`, `bldsky`, `brfar`) and restores base scales when `effortScale = 1.0`;
  - zero `revisit` cache or `plans_switches_key` pollution when changing `effortScale`.
"""
import os
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
ROOT = SERVER.parent
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import buildings  # noqa: E402
import earthd  # noqa: E402
import fast  # noqa: E402
import revisit  # noqa: E402
import vegetation  # noqa: E402


class RustGraphicsEffortTest(unittest.TestCase):
    def test_identity_and_clamping(self):
        self.assertEqual(fast.scale_graphics_effort(1.0, 1.0, 1.0, 2048, 1.0), (1.0, 1.0, 1.0, 2048))
        self.assertEqual(fast.scale_graphics_effort(1.3, 1.5, 1.5, 4096, float("nan")), (1.3, 1.5, 1.5, 4096))
        self.assertEqual(fast.scale_graphics_effort(2.8, 2.8, 2.8, 4096, 2.0), (3.0, 3.0, 3.0, 4096))
        self.assertEqual(fast.scale_graphics_effort(0.5, 0.5, 0.5, 1024, 0.5), (0.5, 0.5, 0.5, 1024))

    def test_sublinear_dm_scaling_and_photo_tiers(self):
        l_low, t_low, b_low, px_low = fast.scale_graphics_effort(1.0, 1.0, 1.0, 2048, 0.5)
        self.assertAlmostEqual(l_low, round(0.5 ** 0.5, 6), places=6)
        self.assertAlmostEqual(t_low, round(0.5 ** 0.75, 6), places=6)
        self.assertEqual(t_low, b_low)
        self.assertEqual(px_low, 1024)

        l_hi, t_hi, b_hi, px_hi = fast.scale_graphics_effort(1.0, 1.0, 1.0, 2048, 2.0)
        self.assertAlmostEqual(l_hi, round(2.0 ** 0.5, 6), places=6)
        self.assertAlmostEqual(t_hi, round(2.0 ** 0.75, 6), places=6)
        self.assertEqual(t_hi, b_hi)
        self.assertEqual(px_hi, 4096)


class SetGraphicsEffortTest(unittest.TestCase):
    def make_conn(self):
        s = earthd.Server.__new__(earthd.Server)
        s.base_px = 2048
        s.near_visual = "detail"
        s.hm = {}
        s.anchors = {}
        s.base_stale = set()
        s.lod_px = 0.0
        s.kfun = lambda lvl: 4.0

        conn = earthd.Connection.__new__(earthd.Connection)
        conn.s = s
        conn.closing = False
        conn.active = None
        conn.lod_scale = 1.0
        conn.tree_scale = 1.0
        conn.building_scale = 1.0
        conn.effort_scale = 1.0
        conn.lod_px = None
        conn.view_cap = None
        conn.far_geo = False
        conn.far_pack = False
        conn.far_hz = False
        conn.bldpack = None
        conn.bldhz = None
        conn.veg = vegetation.Tracker(vegetation.SEND_M, vegetation.DROP_M, 1, "veg")
        conn.bldfar = vegetation.Tracker(buildings.FAR_SEND_M, buildings.FAR_DROP_M, 1, "bldfar",
                                         group=buildings.SKY_UNIT)
        conn.bldsky = vegetation.Tracker(buildings.SKY_SEND_M, buildings.SKY_DROP_M, 1, "bldsky",
                                         unit=buildings.SKY_UNIT, inner=(buildings.FAR_SEND_M, buildings.SKY_UNIT))
        conn.brfar = vegetation.Tracker(buildings.BRIDGE_FAR_SEND_M, buildings.BRIDGE_FAR_DROP_M, 1, "brfar")
        return s, conn

    def test_set_graphics_effort_scales_and_restores_without_revisit_pollution(self):
        s, conn = self.make_conn()
        code0 = revisit.code_key()
        sw0 = revisit.switches_key()
        psw0 = revisit.plans_switches_key()

        conn.dispatch({
            "type": "graphics",
            "lodScale": 1.0,
            "treeScale": 1.0,
            "buildingScale": 1.0,
            "photoPx": 2048,
            "effortScale": 0.5,
        })
        l_exp, t_exp, b_exp, px_exp = fast.scale_graphics_effort(1.0, 1.0, 1.0, 2048, 0.5)
        self.assertEqual((conn.lod_scale, conn.tree_scale, conn.building_scale), (l_exp, t_exp, b_exp))
        self.assertAlmostEqual(conn.veg.send_m, vegetation.SEND_M * t_exp)
        self.assertAlmostEqual(conn.bldfar.send_m, buildings.FAR_SEND_M * b_exp)
        self.assertAlmostEqual(conn.bldsky.send_m, buildings.SKY_SEND_M * b_exp)
        self.assertAlmostEqual(conn.brfar.send_m, buildings.BRIDGE_FAR_SEND_M * b_exp)
        self.assertEqual(s.base_px, px_exp)

        # Restoring effortScale to 1.0 restores the base preset scales
        conn.dispatch({"type": "graphics", "photoPx": 2048, "effortScale": 1.0})
        self.assertEqual((conn.lod_scale, conn.tree_scale, conn.building_scale), (1.0, 1.0, 1.0))
        self.assertEqual(s.base_px, 2048)

        # Zero revisit cache key or plans_switches_key pollution
        self.assertEqual(revisit.code_key(), code0)
        self.assertEqual(revisit.switches_key(), sw0)
        self.assertEqual(revisit.plans_switches_key(), psw0)


if __name__ == "__main__":
    unittest.main()
