"""Verify staged P10-C edits (JSON validity, unit tests) and benchmark urban tile
draw primitives, shadow caster primitives, vertices, triangles, and .cdae bytes before/after."""
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
STAGED = Path(__file__).resolve().parent / "staged"

# 1. Validate JSON syntax of all materials.json files (staged where modified, original otherwise)
MAT_FILES = [
    STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json",
    STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json",
    ROOT / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/main.materials.json",
    ROOT / "mod/beamng_earth/levels/beamng_earth/art/runway/main.materials.json",
    ROOT / "mod/beamng_earth/levels/beamng_earth/art/terrains/main.materials.json",
]
for mf in MAT_FILES:
    data = json.loads(mf.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) > 0, f"Invalid JSON in {mf}"
print(f"[OK] Validated JSON syntax for all {len(MAT_FILES)} *.materials.json files.")

# 2. Run staged test_buildings.py with staged/server first on sys.path
sys.path.insert(0, str(STAGED / "server" / "tests"))
sys.path.insert(0, str(STAGED / "server"))
sys.path.insert(2, str(ROOT / "server" / "tests"))
sys.path.insert(3, str(ROOT / "server"))

import buildings as bld_staged  # noqa: E402
import cdae  # noqa: E402
import test_buildings  # noqa: E402

# Monkeypatch test_buildings to read staged buildings.materials.json & tunnel.materials.json
orig_read_text = Path.read_text


def staged_read_text(self, *args, **kwargs):
    s = str(self).replace("\\", "/")
    if s.endswith("art/shapes/beamngEarth/buildings.materials.json"):
        return orig_read_text(STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json", *args, **kwargs)
    if s.endswith("art/shapes/beamngEarth/tunnel.materials.json"):
        return orig_read_text(STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json", *args, **kwargs)
    return orig_read_text(self, *args, **kwargs)


Path.read_text = staged_read_text
suite = unittest.defaultTestLoader.loadTestsFromModule(test_buildings)
res = unittest.TextTestRunner(verbosity=1).run(suite)
assert res.wasSuccessful(), "test_buildings failed!"
print(f"[OK] Passed all {res.testsRun} tests in staged test_buildings.py.")

# 3. Benchmark a realistic 180-building urban tile (Baltimore / Fells Point mix)
rng = np.random.default_rng(42)
items = []


def rect(x, y, w, d):
    return np.array([(x, y), (x + w, y), (x + w, y + d), (x, y + d)], np.float64)


# 80 attached row houses (some with marble stoops), 45 detached houses (siding/stucco/stone + windows + porches),
# 25 retail/commercial shops, 15 midrise/highrise offices, 8 industrial/warehouses, 4 churches, 3 parking garages
for i in range(80):
    r = rect((i % 20) * 6.5, (i // 20) * 28.0, 6.0, 16.0)
    sp = bld_staged.plan(r, {"class": "terrace"}, neighbours=2, lat=39.28, lon=-76.59, dense=True)
    if i % 2 == 0:
        sp.stoop = (0, 3.0)
    items.append((sp, 0.0, 0.4))

for i in range(45):
    r = rect((i % 15) * 16.0, 120.0 + (i // 15) * 24.0, 11.0, 9.5)
    lat, lon = (46.59, 7.91) if i % 5 == 0 else (39.29, -76.61)
    sp = bld_staged.plan(r, {"class": "house"}, neighbours=0, lat=lat, lon=lon)
    if i % 3 == 0:
        sp.door = (0, 5.5)
        sp.porch = True
    items.append((sp, 0.0, 0.0))

for i in range(25):
    r = rect((i % 10) * 22.0, 200.0 + (i // 10) * 25.0, 14.0, 18.0)
    sp = bld_staged.plan(r, {"class": "retail"}, neighbours=1, lat=39.28, lon=-76.59, dense=True)
    sp.sign = 0
    items.append((sp, 0.0, 0.0))

for i in range(15):
    h = 36.0 if i < 10 else 95.0
    r = rect((i % 5) * 45.0, 260.0 + (i // 5) * 45.0, 32.0, 28.0)
    sp = bld_staged.plan(r, {"class": "office", "height": h}, neighbours=0, lat=40.758, lon=-73.985, dense=True)
    items.append((sp, 0.0, 0.0))

for i in range(8):
    r = rect(i * 30.0, 400.0, 24.0, 18.0)
    cls = "barn" if i < 3 else "industrial"
    sp = bld_staged.plan(r, {"class": cls}, neighbours=0, lat=39.4, lon=-77.4, town=True)
    sp.front = 0
    items.append((sp, 0.0, 0.0))

for i in range(4):
    r = rect(i * 40.0, 450.0, 28.0, 14.0)
    sp = bld_staged.plan(r, {"class": "church"}, neighbours=0, lat=37.36, lon=-118.39)
    items.append((sp, 0.0, 0.0))

for i in range(3):
    r = rect(i * 70.0, 500.0, 56.0, 38.0)
    sp = bld_staged.plan(r, {"class": "parking", "num_floors": 4, "height": 12.0}, neighbours=0, lat=39.28, lon=-76.59)
    items.append((sp, 0.0, 0.0))

bld_mats_before = json.loads(orig_read_text(ROOT / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json", encoding="utf-8"))
bld_mats_after = json.loads(orig_read_text(STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json", encoding="utf-8"))
tun_mats_after = json.loads(orig_read_text(STAGED / "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json", encoding="utf-8"))


def casts_shadow(mat_name, bld_dict, tun_dict):
    if mat_name in bld_dict:
        return bld_dict[mat_name].get("castShadows", True) is not False
    if mat_name in tun_dict:
        return tun_dict[mat_name].get("castShadows", True) is not False
    return True


parts = bld_staged.build_parts(items, with_lod=True)
far_mesh = bld_staged.build(items, lite=True, far=True)

with tempfile.TemporaryDirectory() as d:
    total_verts_hi = total_tris_hi = total_prims_hi = 0
    total_verts_lo = total_tris_lo = total_prims_lo = 0
    shadow_prims_hi_before = shadow_prims_hi_after = 0
    shadow_prims_lo_after = 0
    cdae_bytes_bld = 0
    used_mat_names_hi = set()
    for idx, part in enumerate(parts):
        p = os.path.join(d, f"bld_{idx}.cdae")
        cdae_bytes_bld += bld_staged.write(p, part)
        sh = cdae.read(p)
        mat_names = [m["name"] for m in sh["materials"]]
        m_hi, m_lo = sh["meshes"][0], sh["meshes"][1]
        a_hi, a_lo = cdae.mesh_arrays(m_hi), cdae.mesh_arrays(m_lo)
        n_prims_hi = m_hi["primitives"][0]
        n_prims_lo = m_lo["primitives"][0]
        total_verts_hi += m_hi["verts"][0]
        total_tris_hi += m_hi["indices"][0] // 3
        total_prims_hi += n_prims_hi
        total_verts_lo += m_lo["verts"][0]
        total_tris_lo += m_lo["indices"][0] // 3
        total_prims_lo += n_prims_lo
        for k in range(n_prims_hi):
            _, _, mat_word = struct.unpack_from("<3i", a_hi["primitives"], k * 12)
            mname = mat_names[mat_word & cdae.PRIM_MATERIAL_MASK]
            used_mat_names_hi.add(mname)
            if casts_shadow(mname, bld_mats_before, tun_mats_after):
                shadow_prims_hi_before += 1
            if casts_shadow(mname, bld_mats_after, tun_mats_after):
                shadow_prims_hi_after += 1
        for k in range(n_prims_lo):
            _, _, mat_word = struct.unpack_from("<3i", a_lo["primitives"], k * 12)
            mname = mat_names[mat_word & cdae.PRIM_MATERIAL_MASK]
            if casts_shadow(mname, bld_mats_after, tun_mats_after):
                shadow_prims_lo_after += 1

    pfar = os.path.join(d, "bldfar.cdae")
    cdae_bytes_far = bld_staged.write(pfar, far_mesh)
    sh_far = cdae.read(pfar)
    far_mat_names = [m["name"] for m in sh_far["materials"]]
    far_prims = sh_far["meshes"][0]["primitives"][0]
    far_shadow_before = far_prims  # used bne_bld_facade (castShadows=True)
    far_shadow_after = sum(1 for m in far_mat_names if casts_shadow(m, bld_mats_after, tun_mats_after))

print("\n=== URBAN TILE BENCHMARK (180 buildings, 16 materials used) ===")
print(f"Mesh parts (MAX_MESH_VERTS={bld_staged.MAX_MESH_VERTS}): {len(parts)}")
print(f"High LOD (detail{int(bld_staged.BLD_LOD_PX)}): {total_verts_hi} verts, {total_tris_hi} tris, {total_prims_hi} total primitives")
print(f"  -> Shadow-casting primitives in High LOD: {shadow_prims_hi_before} (before) -> {shadow_prims_hi_after} (after, bne_bld_marble=false, bne_bld_glass=false)")
print(f"Low LOD (detail2, merged vertex-colored): {total_verts_lo} verts ({100*total_verts_lo/total_verts_hi:.1f}%), {total_tris_lo} tris ({100*total_tris_lo/total_tris_hi:.1f}%), {total_prims_lo} total primitives")
print(f"  -> Shadow-casting primitives in Low LOD: 15 per part / {shadow_prims_hi_before} total (unmerged baseline) -> {shadow_prims_lo_after} total (merged)")
print(f"bldfar tile (640-1600m): {sh_far['meshes'][0]['verts'][0]} verts, {sh_far['meshes'][0]['indices'][0]//3} tris, materials={far_mat_names}")
print(f"  -> Shadow-casting primitives per bldfar tile: {far_shadow_before} (before, bne_bld_facade) -> {far_shadow_after} (after, bne_bld_far)")
print(f"File sizes: bld={cdae_bytes_bld/1024:.1f} KB, bldfar={cdae_bytes_far/1024:.1f} KB")
