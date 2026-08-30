import bpy
import os

SRC = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_m7oljqm7oljqm7ol.jfif"
OUT_DIR = r"E:\script\pythonWorkSpace\pattern_output"
os.makedirs(OUT_DIR, exist_ok=True)
PNG = os.path.join(OUT_DIR, "c130_flight_suit_pattern_transparent.png")
OBJ = os.path.join(OUT_DIR, "c130_flight_suit_pattern_uv.obj")
MTL = os.path.join(OUT_DIR, "c130_flight_suit_pattern_uv.mtl")
BLEND = os.path.join(OUT_DIR, "c130_flight_suit_pattern_uv.blend")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
w, h = 2816, 1536
aspect = w / h
height = 1.0
width = aspect * height
verts = [(-width/2, -height/2, 0), (width/2, -height/2, 0),
         (width/2, height/2, 0), (-width/2, height/2, 0)]
mesh = bpy.data.meshes.new("C130PatternUV_Mesh")
mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
mesh.uv_layers.new(name="UVMap")
for loop, uv in zip(mesh.uv_layers[0].data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
    loop.uv = uv
obj = bpy.data.objects.new("C130_Flight_Suit_Pattern_UV", mesh)
bpy.context.collection.objects.link(obj)

img = bpy.data.images.load(PNG, check_existing=False)
mat = bpy.data.materials.new("C130_Pattern_Transparent_Material")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
tex = nodes.new("ShaderNodeTexImage")
tex.image = img
links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
bsdf.inputs["Roughness"].default_value = 0.8
try:
    mat.surface_render_method = 'DITHERED'
except Exception:
    pass
obj.data.materials.append(mat)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene['source_image'] = SRC
scene['workflow'] = 'Full-resolution image projected to a UV plane; checkerboard background removed by alpha.'
scene['note'] = 'The OBJ mesh is one rectangular UV plane. The visible pattern is preserved by the PNG texture.'
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.wm.obj_export(filepath=OBJ, export_materials=True, export_uv=True, export_normals=False)
print('PNG', PNG)
print('OBJ', OBJ)
print('MTL', MTL)
print('BLEND', BLEND)
