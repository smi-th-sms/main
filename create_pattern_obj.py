import bpy
import os

IMAGE_W = 2048.0
IMAGE_H = 1093.0
SOURCE_W = 2816.0
SOURCE_H = 1536.0
SX = SOURCE_W / IMAGE_W
SY = SOURCE_H / IMAGE_H
MM_PER_PIXEL = 0.1
UPSCALE_FACTOR = 100.0
MM_PER_UPSCALED_PIXEL = MM_PER_PIXEL / UPSCALE_FACTOR

OUT_DIR = r"E:\script\pythonWorkSpace\pattern_output"
os.makedirs(OUT_DIR, exist_ok=True)
OBJ_PATH = os.path.join(OUT_DIR, "garment_pattern_2d_color_100x_0.1mm_per_pixel.obj")
BLEND_PATH = os.path.join(OUT_DIR, "garment_pattern_2d_color_100x_0.1mm_per_pixel.blend")

# Coordinates are traced from the supplied pattern sheet preview (2048x1093),
# then converted to the original 2816x1536 image coordinate system.
P = {
    "front_torso": [(42,320),(74,302),(62,225),(88,171),(150,148),(205,139),(245,145),(257,181),(284,214),(306,229),(309,365),(294,487),(69,487),(56,424)],
    "back_torso": [(792,146),(900,108),(1015,145),(1105,172),(1086,248),(1074,366),(1055,497),(820,497),(802,391),(785,290)],
    "sleeve_left": [(51,684),(78,664),(111,580),(151,557),(185,568),(218,604),(250,668),(230,693),(211,767),(190,850),(139,861),(111,752),(82,694)],
    "sleeve_right": [(747,684),(775,657),(810,562),(850,555),(887,579),(920,629),(933,683),(910,703),(894,785),(875,860),(817,853),(795,775),(773,707)],
    "pants_front": [(1420,249),(1510,260),(1554,274),(1550,368),(1533,470),(1500,520),(1460,504),(1420,480),(1400,384)],
    "pants_back": [(1737,246),(1850,248),(1940,260),(1950,383),(1928,481),(1880,519),(1833,498),(1795,457),(1772,380)],
    "collar": [(1350,42),(1390,25),(1558,25),(1600,48),(1588,87),(1510,111),(1430,101),(1365,80)],
    "waist_tab_left": [(1372,151),(1490,151),(1490,181),(1375,181)],
    "waist_tab_right": [(1728,151),(1860,151),(1862,181),(1728,181)],
    "pocket_left": [(1378,562),(1470,561),(1468,692),(1384,697)],
    "pocket_right": [(1850,560),(1938,560),(1940,698),(1852,692)],
    "calf_pocket_left": [(1385,811),(1485,811),(1477,995),(1390,997)],
    "calf_pocket_right": [(1850,811),(1940,811),(1941,997),(1858,994)],
    "small_sleeve_panel": [(356,565),(397,570),(394,764),(371,764)],
    "small_zip_panel": [(430,602),(510,602),(552,681),(518,703),(430,667)],
    "diamond_piece": [(596,130),(659,70),(719,130),(658,191)],
    "long_narrow_panel": [(650,277),(675,264),(738,377),(711,394)],
    "long_narrow_panel_2": [(1110,593),(1135,600),(1119,830),(1094,826)],
}

COLOR_GROUPS = {
    "blue": {"names": ["front_torso", "diamond_piece", "small_sleeve_panel", "small_zip_panel"], "color": (0.42, 0.75, 0.86, 1.0)},
    "green": {"names": ["back_torso", "long_narrow_panel_2"], "color": (0.55, 0.78, 0.66, 1.0)},
    "purple": {"names": ["sleeve_left", "sleeve_right"], "color": (0.67, 0.58, 0.82, 1.0)},
    "orange": {"names": ["pants_front", "pocket_left", "calf_pocket_left"], "color": (0.95, 0.62, 0.38, 1.0)},
    "yellow": {"names": ["pants_back", "pocket_right", "calf_pocket_right"], "color": (0.98, 0.86, 0.36, 1.0)},
    "cream": {"names": ["collar", "waist_tab_left", "waist_tab_right", "long_narrow_panel", "small_sleeve_panel"], "color": (0.86, 0.78, 0.63, 1.0)},
}

def group_for(name):
    for group, info in COLOR_GROUPS.items():
        if name in info["names"]:
            return group
    return "neutral"

def make_material(name, rgba):
    mat = bpy.data.materials.new(name + "_Pattern_Material")
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.8
    return mat

def make_poly(name, pts):
    # Add intermediate vertices along every traced edge. This increases OBJ
    # sampling density while preserving the traced silhouette.
    dense = []
    max_segment_px = 0.25
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        steps = max(1, int(((dx * dx + dy * dy) ** 0.5) / max_segment_px))
        for j in range(steps):
            t = j / steps
            dense.append((a[0] + dx * t, a[1] + dy * t))
    pts = dense
    verts = []
    for x, y in pts:
        # center the sheet around origin; image y axis is inverted for Blender XY
        # Trace in a 100x upscaled coordinate space, while preserving the
        # requested physical scale in the final OBJ.
        px = (x * UPSCALE_FACTOR) * SX * MM_PER_UPSCALED_PIXEL / 1000.0
        py = ((IMAGE_H - y) * UPSCALE_FACTOR) * SY * MM_PER_UPSCALED_PIXEL / 1000.0
        verts.append((px, py, 0.0))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    group = group_for(name)
    collection = bpy.data.collections.get("PATTERN_" + group.upper())
    if collection is None:
        collection = bpy.data.collections.new("PATTERN_" + group.upper())
        bpy.context.scene.collection.children.link(collection)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for name, pts in P.items():
    obj = make_poly(name, pts)
    group = group_for(name)
    rgba = next((v["color"] for k, v in COLOR_GROUPS.items() if k == group), (0.7, 0.7, 0.7, 1.0))
    obj.data.materials.append(make_material(group, rgba))

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'CENTIMETERS'
scene['source_image'] = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_fb6j1tfb6j1tfb6j.jfif"
scene['scale_note'] = '100x internal coordinate upscaling with dense sampling; final physical scale is approximately 0.1 mm per source image pixel.'

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.wm.obj_export(filepath=OBJ_PATH, export_materials=True, export_uv=True, export_normals=False)
print('PATTERN_EXPORT', OBJ_PATH)
print('PATTERN_BLEND', BLEND_PATH)
