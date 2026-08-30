import bpy
import os

SRC = r"C:\Users\smi_th\Downloads\Gemini_Generated_Image_fb6j1tfb6j1tfb6j.jfif"
OUT_DIR = r"E:\script\pythonWorkSpace\pattern_output"
os.makedirs(OUT_DIR, exist_ok=True)
PNG = os.path.join(OUT_DIR, "pattern_white_background_removed.png")
BLEND = os.path.join(OUT_DIR, "pattern_uv_transparent.blend")
OBJ = os.path.join(OUT_DIR, "pattern_uv_transparent.obj")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

w, h = 2816, 1536
aspect = w / h
height_m = 1.0
width_m = height_m * aspect
verts = [(-width_m/2, -height_m/2, 0), (width_m/2, -height_m/2, 0),
         (width_m/2, height_m/2, 0), (-width_m/2, height_m/2, 0)]
mesh = bpy.data.meshes.new("PatternUVPlane_Mesh")
mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
mesh.uv_layers.new(name="UVMap")
uv = mesh.uv_layers[0].data
for loop, co in zip(uv, [(0,0), (1,0), (1,1), (0,1)]):
    loop.uv = co
obj = bpy.data.objects.new("Pattern_UV_Transparent", mesh)
bpy.context.collection.objects.link(obj)

img = bpy.data.images.load(PNG, check_existing=False)
img.name = "Pattern_White_Background_Removed"
mat = bpy.data.materials.new("Pattern_UV_Alpha_Material")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
tex = nodes.new("ShaderNodeTexImage")
tex.image = img
tex.interpolation = 'Linear'
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
scene.unit_settings.length_unit = 'METERS'
scene['source_image'] = SRC
scene['workflow'] = 'UV-projected image plane with near-white background removed by alpha'
scene['note'] = 'The visible pattern is exact to the source image; the underlying mesh is a single rectangular UV plane.'

bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.wm.obj_export(filepath=OBJ, export_materials=True, export_uv=True, export_normals=False)
print('UV_PNG', PNG)
print('UV_BLEND', BLEND)
print('UV_OBJ', OBJ)
