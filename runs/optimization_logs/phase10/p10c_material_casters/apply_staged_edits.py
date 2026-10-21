"""Copy target files into runs/optimization_logs/phase10/p10c_material_casters/staged/
and apply P10-C edits while preserving exact CRLF/LF line endings of each original file."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STAGED = Path(__file__).resolve().parent / "staged"

FILES = [
    "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json",
    "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json",
    "mod/beamng_earth/lua/ge/extensions/beamngEarth/satmat.lua",
    "mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua",
    "server/buildings.py",
    "server/tests/test_buildings.py",
]

for rel in FILES:
    dst = STAGED / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, dst)


def edit_preserving_newlines(rel_path: str, replacements: list[tuple[str, str]]) -> None:
    p = STAGED / rel_path
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    for old, new in replacements:
        old_lf = old.replace("\r\n", "\n")
        new_lf = new.replace("\r\n", "\n")
        assert old_lf in text, f"Target not found in {rel_path}:\n{old_lf!r}"
        assert text.count(old_lf) == 1, f"Target matched multiple times in {rel_path}"
        text = text.replace(old_lf, new_lf, 1)
    out = text.replace("\n", "\r\n") if crlf else text
    p.write_bytes(out.encode("utf-8"))
    print(f"Updated staged/{rel_path} (crlf={crlf})")


# 1. buildings.materials.json: castShadows=false on bne_bld_marble + add bne_bld_far (castShadows=false, vertColor=true)
edit_preserving_newlines(
    "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json",
    [
        (
            '        "vertColor": true\n      },\n      {},\n      {},\n      {}\n    ],\n    "translucent": false\n  },\n  "bne_bld_brick": {',
            '        "vertColor": true\n      },\n      {},\n      {},\n      {}\n    ],\n    "translucent": false,\n    "castShadows": false\n  },\n  "bne_bld_brick": {',
        ),
        (
            '        "emissiveMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_e.color.png",\n        "vertColor": true\n      },\n      {},\n      {},\n      {}\n    ],\n    "translucent": false,\n    "castShadows": false\n  }\n}',
            '        "emissiveMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_e.color.png",\n        "vertColor": true\n      },\n      {},\n      {},\n      {}\n    ],\n    "translucent": false,\n    "castShadows": false\n  },\n  "bne_bld_far": {\n    "name": "bne_bld_far",\n    "mapTo": "bne_bld_far",\n    "class": "Material",\n    "version": 1.5,\n    "persistentId": "7a91c3e4-5b12-4d89-9a01-3c4d5e6f7a8b",\n    "Stages": [\n      {\n        "baseColorMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_b.color.png",\n        "normalMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_nm.normal.png",\n        "roughnessMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_r.data.png",\n        "ambientOcclusionMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_ao.data.png",\n        "metallicMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_m.data.png",\n        "baseColorFactor": [\n          1,\n          1,\n          1,\n          1\n        ],\n        "emissiveMap": "/assets/materials/trim/plaster/t_highrise_plaster/t_highrise_plaster_e.color.png",\n        "vertColor": true\n      },\n      {},\n      {},\n      {}\n    ],\n    "translucent": false,\n    "castShadows": false\n  }\n}',
        ),
    ],
)

# 2. tunnel.materials.json: castShadows=false on bne_tunnel_light and bne_tunnel_soil
edit_preserving_newlines(
    "mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json",
    [
        (
            '        "roughnessFactor": 0.4\n      },\n      {},\n      {},\n      {}\n    ],\n    "groundType": "METAL",\n    "translucent": false\n  },\n  "bne_tunnel_stone": {',
            '        "roughnessFactor": 0.4\n      },\n      {},\n      {},\n      {}\n    ],\n    "groundType": "METAL",\n    "translucent": false,\n    "castShadows": false\n  },\n  "bne_tunnel_stone": {',
        ),
        (
            '    "groundType": "GRASS",\n    "translucent": false\n  },\n  "bne_bridge_concrete": {',
            '    "groundType": "GRASS",\n    "translucent": false,\n    "castShadows": false\n  },\n  "bne_bridge_concrete": {',
        ),
    ],
)

# 3. satmat.lua: enforce castShadows='0' when adopting an existing material
edit_preserving_newlines(
    "mod/beamng_earth/lua/ge/extensions/beamngEarth/satmat.lua",
    [
        (
            "  if m then\n    if texture then m:setField('colorMap', 0, texture) end\n  else",
            "  if m then\n    if texture then m:setField('colorMap', 0, texture) end\n    m:setField('castShadows', 0, '0')\n  else",
        ),
    ],
)

# 4. roads.lua: disable castShadows on all stock road, marking, drain, and sidewalk/curb materials in loadMaterials()
edit_preserving_newlines(
    "mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua",
    [
        (
            "M.OPAQUE = { 'road_asphalt_2lane', 'italy_cobblestone' }\n\nlocal function loadMaterials()\n  if loadedMaterials then return end\n  for _, f in ipairs(M.MATERIAL_FILES) do loadJsonMaterialsFile(f) end\n  for _, name in ipairs(M.OPAQUE) do\n    local m = scenetree.findObject(name)\n    if m then\n      pcall(function() m:setField('translucent', 0, '0'); m:flush(); m:reload() end)\n    end\n  end\n  local pad = scenetree.findObject('tactile_indicator')    -- curb ramp pads: US truncated domes are yellow\n  if pad then pcall(function() pad:setField('baseColorFactor', 0, '0.95 0.78 0.18 1'); pad:flush(); pad:reload() end) end\n  loadedMaterials = true\nend",
            "M.OPAQUE = { 'road_asphalt_2lane', 'italy_cobblestone' }\n-- Ground-hugging road ribbons, markings, drains, and raised sidewalks/curbs should never cast shadows\n-- into PSSM cascades (per-object shadow flags on TSStatic are no-ops in BeamNG 0.40; Material.castShadows is real).\nM.NO_SHADOW = {\n  'road_asphalt_2lane', 'italy_cobblestone', 'm_dirt_road', 'sidewalk_concrete',\n  'm_metal_grid_drain', 'gutter1', 'line_white', 'line_yellow', 'line_dashed_long', 'crossing_white',\n  'curbs', 'sidewalk1', 'tactile_indicator',\n}\n\nlocal function loadMaterials()\n  if loadedMaterials then return end\n  for _, f in ipairs(M.MATERIAL_FILES) do loadJsonMaterialsFile(f) end\n  for _, name in ipairs(M.OPAQUE) do\n    local m = scenetree.findObject(name)\n    if m then\n      pcall(function() m:setField('translucent', 0, '0'); m:flush(); m:reload() end)\n    end\n  end\n  local pad = scenetree.findObject('tactile_indicator')    -- curb ramp pads: US truncated domes are yellow\n  if pad then pcall(function() pad:setField('baseColorFactor', 0, '0.95 0.78 0.18 1'); pad:flush(); pad:reload() end) end\n  for _, name in ipairs(M.NO_SHADOW) do\n    local m = scenetree.findObject(name)\n    if m then\n      pcall(function() m:setField('castShadows', 0, '0'); m:flush(); m:reload() end)\n    end\n  end\n  loadedMaterials = true\nend",
        ),
    ],
)

# 5. server/buildings.py: FAR_MAT, LITE_ALBEDO vertex-colour baking + UV clamping for lite=True, BLD_LOD_PX=3600.0
edit_preserving_newlines(
    "server/buildings.py",
    [
        (
            'GLASS = "bne_bld_glass"     # sash windows laid over plain walls (no shadow casting to avoid shadow acne)\nMATERIALS = (FACADE, SHOP, OFFICE, ROOF_FLAT, ROOF_SLATE, ROOF_SHINGLE, SIDING, STUCCO, ROOF_METAL, PANEL, METALWALL,\n             STONE, MARBLE, BRICK_WALL, CONCRETE, GLASS)',
            'GLASS = "bne_bld_glass"     # sash windows laid over plain walls (no shadow casting to avoid shadow acne)\nFAR_MAT = "bne_bld_far"     # distant horizon buildings (bldfar, 640-1600 m): single-primitive, castShadows=false\nMATERIALS = (FACADE, SHOP, OFFICE, ROOF_FLAT, ROOF_SLATE, ROOF_SHINGLE, SIDING, STUCCO, ROOF_METAL, PANEL, METALWALL,\n             STONE, MARBLE, BRICK_WALL, CONCRETE, GLASS)\n# Base-texture RGB albedos relative to bne_bld_facade\'s plain plaster strip, baked into vertex colours when\n# lite=True collapses all materials into a single primitive so roofs, brick, stone and glass keep their look.\nLITE_ALBEDO = {\n    SHOP: (0.72, 0.72, 0.74),\n    OFFICE: (0.68, 0.76, 0.84),\n    ROOF_FLAT: (0.55, 0.55, 0.56),\n    ROOF_SLATE: (0.48, 0.50, 0.54),\n    ROOF_SHINGLE: (0.62, 0.56, 0.52),\n    SIDING: (0.94, 0.93, 0.90),\n    STUCCO: (0.95, 0.94, 0.92),\n    ROOF_METAL: (0.72, 0.74, 0.76),\n    PANEL: (0.88, 0.87, 0.85),\n    METALWALL: (0.78, 0.80, 0.82),\n    STONE: (0.82, 0.78, 0.72),\n    MARBLE: (0.95, 0.94, 0.92),\n    BRICK_WALL: (0.68, 0.38, 0.32),\n    CONCRETE: (0.74, 0.74, 0.72),\n}',
        ),
        (
            "        if spec.plain:\n            u1 = L / SIDING_UV_M\n            m.quad((ax, ay, z0), (bx, by, z0), (bx, by, z_eave), (ax, ay, z_eave),\n                   (0, z0 / SIDING_UV_M), (u1, z0 / SIDING_UV_M), (u1, z_eave / SIDING_UV_M), (0, z_eave / SIDING_UV_M),\n                   fac)\n            continue",
            "        if spec.plain:\n            if lite:\n                m.quad((ax, ay, z0), (bx, by, z0), (bx, by, z_eave), (ax, ay, z_eave),\n                       (0.002, 0.995), (0.012, 0.995), (0.012, 0.999), (0.002, 0.999), fac)\n                continue\n            u1 = L / SIDING_UV_M\n            m.quad((ax, ay, z0), (bx, by, z0), (bx, by, z_eave), (ax, ay, z_eave),\n                   (0, z0 / SIDING_UV_M), (u1, z0 / SIDING_UV_M), (u1, z_eave / SIDING_UV_M), (0, z_eave / SIDING_UV_M),\n                   fac)\n            continue",
        ),
        (
            'def build(specs_and_ground, lite=False):\n    """The tile\'s mesh from [(Spec, ground z min, ground z max)] with rings in the tile\'s local frame:\n    (positions, uvs, tris, tri material indices, MATERIALS) or None if empty. lite (far tiles): no\n    cornices, whole walls instead of one quad per bay."""\n    m = Mesh()\n    for spec, gmin, gmax in specs_and_ground:\n        _build_one(m, spec, gmin, gmax, lite)\n    if m.n == 0:\n        return None\n    P, UV, T, M, C = m.arrays()\n    if lite:\n        # Collapse all coarse distant geometry into a single material primitive (`bne_bld_facade`)\n        # so the engine submits 1 drawcall per tile for detail50 / bldfar instead of up to 16.\n        M = np.zeros(len(T), dtype=np.int32)\n    return P, UV, T, M, (MATERIALS[:1] if lite else MATERIALS), C',
            'def build(specs_and_ground, lite=False, far=False):\n    """The tile\'s mesh from [(Spec, ground z min, ground z max)] with rings in the tile\'s local frame:\n    (positions, uvs, tris, tri material indices, MATERIALS) or None if empty. lite (far tiles / coarse LOD): no\n    cornices, whole walls instead of one quad per bay, merged into 1 primitive with baked vertex colours.\n    far=True uses FAR_MAT (`bne_bld_far`, castShadows=false) so horizon building tiles never cast shadows."""\n    m = Mesh()\n    for spec, gmin, gmax in specs_and_ground:\n        _build_one(m, spec, gmin, gmax, lite)\n    if m.n == 0:\n        return None\n    P, UV, T, M, C = m.arrays()\n    if lite:\n        # Remap non-windowed triangles (roofs, plain walls, brick, stone) to the solid plaster UV patch\n        # (0.006, 0.997) so window sheets / night emissives never bleed onto roofs, and bake each material\'s\n        # base texture albedo into vertex colours C before collapsing to 1 draw primitive.\n        non_win = ~np.isin(M, (0, 1, 2))\n        if non_win.any():\n            v_idx = np.unique(T[non_win])\n            UV[v_idx, 0] = 0.006\n            UV[v_idx, 1] = 0.997\n        for mat_name, rgb in LITE_ALBEDO.items():\n            mi = MATERIALS.index(mat_name)\n            mask = M == mi\n            if mask.any():\n                vi = np.unique(T[mask])\n                C[vi, :3] = np.clip(np.round(C[vi, :3].astype(np.float64) * rgb), 0, 255).astype(np.uint8)\n        M = np.zeros(len(T), dtype=np.int32)\n    mats = (FAR_MAT,) if (lite and far) else (MATERIALS[:1] if lite else MATERIALS)\n    return P, UV, T, M, mats, C',
        ),
        (
            "BLD_LOD_PX = 2700.0",
            "BLD_LOD_PX = 3600.0",
        ),
        (
            "    mesh = build(items, lite=True)\n    data = {\"v\": 1}",
            "    mesh = build(items, lite=True, far=True)\n    data = {\"v\": 1}",
        ),
    ],
)

# 6. server/tests/test_buildings.py: expand test_shadow_materials_and_lite_window_omission
edit_preserving_newlines(
    "server/tests/test_buildings.py",
    [
        (
            '        for non_shadow in ("bne_bld_glass", "bne_wire", "bne_sidewalk_brick"):\n            self.assertIn(non_shadow, mats)\n            self.assertIs(mats[non_shadow].get("castShadows"), False, non_shadow)\n        # A house with plain walls uses bne_bld_glass for laid-over windows in the full mesh and omits them in lite\n        spec = next(bld.plan(rect(k * 40, 20, 12, 9), {"class": "house"}, 0, 39.2, -76.9)\n                    for k in range(40) if bld.plan(rect(k * 40, 20, 12, 9), {"class": "house"}, 0, 39.2, -76.9).wall)\n        _, _, T_full, M_full, mats_full, _ = bld.build([(spec, 0.0, 0.0)], lite=False)\n        _, _, T_lite, M_lite, mats_lite, _ = bld.build([(spec, 0.0, 0.0)], lite=True)\n        self.assertIn(mats_full.index(bld.GLASS), set(M_full.tolist()))\n        self.assertLess(len(T_lite), len(T_full), "lite mesh omits laid-over glass window quads")\n        self.assertEqual(len(mats_lite), 1, "lite mesh merges materials into a single primitive")\n        self.assertTrue((M_lite == 0).all())',
            '        for non_shadow in ("bne_bld_glass", "bne_bld_marble", "bne_bld_far", "bne_wire", "bne_sidewalk_brick"):\n            self.assertIn(non_shadow, mats)\n            self.assertIs(mats[non_shadow].get("castShadows"), False, non_shadow)\n        tun_path = mats_path.parent / "tunnel.materials.json"\n        tun_mats = json.loads(tun_path.read_text(encoding="utf-8"))\n        for non_shadow in ("bne_tunnel_light", "bne_tunnel_soil"):\n            self.assertIn(non_shadow, tun_mats)\n            self.assertIs(tun_mats[non_shadow].get("castShadows"), False, non_shadow)\n        # A house with plain walls uses bne_bld_glass for laid-over windows in the full mesh and omits them in lite\n        spec = next(bld.plan(rect(k * 40, 20, 12, 9), {"class": "house"}, 0, 39.2, -76.9)\n                    for k in range(40) if bld.plan(rect(k * 40, 20, 12, 9), {"class": "house"}, 0, 39.2, -76.9).wall)\n        _, _, T_full, M_full, mats_full, C_full = bld.build([(spec, 0.0, 0.0)], lite=False)\n        _, UV_lite, T_lite, M_lite, mats_lite, C_lite = bld.build([(spec, 0.0, 0.0)], lite=True)\n        _, _, _, _, mats_far, _ = bld.build([(spec, 0.0, 0.0)], lite=True, far=True)\n        self.assertIn(mats_full.index(bld.GLASS), set(M_full.tolist()))\n        self.assertLess(len(T_lite), len(T_full), "lite mesh omits laid-over glass window quads")\n        self.assertEqual(mats_lite, (bld.FACADE,), "near lite LOD uses bne_bld_facade")\n        self.assertEqual(mats_far, (bld.FAR_MAT,), "far horizon tiles use bne_bld_far (castShadows=false)")\n        self.assertTrue((M_lite == 0).all())\n        # Plain walls and roof triangles in lite mode are remapped to the solid plaster patch (v >= 0.99)\n        self.assertTrue((UV_lite[:, 1] >= 0.99).all(), "plain walls and roof avoid window-sheet bands in lite mode")',
        ),
    ],
)


# 7. Generate clean git apply-ready .diff files and verify each with `git apply --check`
import subprocess

DIFF_TARGETS = [
    ("mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json", "buildings.materials.json.diff"),
    ("mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json", "tunnel.materials.json.diff"),
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/satmat.lua", "satmat.lua.diff"),
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua", "roads.lua.diff"),
    ("server/buildings.py", "buildings.py.diff"),
    ("server/tests/test_buildings.py", "test_buildings.py.diff"),
]

out_dir = Path(__file__).resolve().parent
for rel, diff_name in DIFF_TARGETS:
    staged_rel = f"runs/optimization_logs/phase10/p10c_material_casters/staged/{rel}"
    res = subprocess.run(
        ["git", "diff", "--no-index", "--no-color", "--", rel, staged_rel],
        cwd=ROOT,
        capture_output=True,
    )
    raw = res.stdout.decode("utf-8")
    lines = raw.splitlines(keepends=True)
    fixed = []
    for ln in lines:
        if ln.startswith("diff --git "):
            fixed.append(f"diff --git a/{rel} b/{rel}\n")
        elif ln.startswith("--- "):
            fixed.append(f"--- a/{rel}\n")
        elif ln.startswith("+++ "):
            fixed.append(f"+++ b/{rel}\n")
        else:
            fixed.append(ln)
    diff_path = out_dir / diff_name
    diff_path.write_bytes("".join(fixed).encode("utf-8"))
    chk = subprocess.run(["git", "apply", "--check", str(diff_path)], cwd=ROOT, capture_output=True, text=True)
    assert chk.returncode == 0, f"git apply --check failed for {diff_name}: {chk.stderr}"
    print(f"[OK] Generated and verified {diff_name} with git apply --check")
