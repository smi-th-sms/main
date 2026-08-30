import bpy
import json
import os

ROOT = r"E:\script\pythonWorkSpace\pattern_output\c130_components"
DATA = os.path.join(ROOT, "c130_pattern_components.json")
OBJ = os.path.join(ROOT, "c130_pattern_components.obj")
BLEND = os.path.join(ROOT, "c130_pattern_components.blend")

with open(DATA, "r", encoding="utf-8") as f:
    data = json.load(f)
w, h = data["width"], data["height"]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
img = bpy.data.images.load(data["texture"], check_existing=False)
mat = bpy.data.materials.new("C130_Pattern_Alpha_Texture")
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
tex = nodes.new("ShaderNodeTexImage")
tex.image = img
tex.interpolation = "Linear"
links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
bsdf.inputs["Roughness"].default_value = 0.8
try: mat.surface_render_method = "DITHERED"
except Exception: pass

scale = 0.001
for c in data["components"]:
    poly = c["polygon"]
    verts = []
    for x, y in poly:
        verts.append(((x - w/2) * scale, (h/2 - y) * scale, 0.0))
    mesh = bpy.data.meshes.new(f"Pattern_{c['index']:03d}_Mesh")
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.uv_layers.new(name="UVMap")
    for loop, (x, y) in zip(mesh.uv_layers[0].data, poly):
        loop.uv = (x / w, 1.0 - y / h)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(f"Pattern_{c['index']:03d}", mesh)
    bpy.context.collection.objects.link(obj)
    obj["source_bbox_pixels"] = c["bbox"]
    obj["source_pixel_area"] = c["pixels"]

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene["source_image"] = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_m7oljqm7oljqm7ol.jfif"
scene["workflow"] = "Alpha connected-component cutout meshes with full-image UV projection"
scene["component_count"] = len(data["components"])
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.wm.obj_export(filepath=OBJ, export_materials=True, export_uv=True, export_normals=False)
print("component_count", len(data["components"]))
print("OBJ", OBJ)
print("BLEND", BLEND)
