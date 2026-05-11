"""
QA рендеры: 8 ракурсов для аудита oilfield-сцены.
Запуск: blender --background field_development_complex.blend --python qa_render.py
"""
import os, bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "qa_renders")
os.makedirs(OUT_DIR, exist_ok=True)

bpy.context.scene.render.engine = "BLENDER_EEVEE"
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.image_settings.file_format = "PNG"

def render_cam(name, loc, rot, ortho=False, ortho_scale=50):
    cam = bpy.data.cameras.new(name)
    cam_ob = bpy.data.objects.new(name, cam)
    bpy.context.collection.objects.link(cam_ob)
    cam_ob.location = loc
    cam_ob.rotation_euler = rot
    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    bpy.context.scene.camera = cam_ob
    bpy.context.scene.render.filepath = os.path.join(OUT_DIR, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {name}.png")
    bpy.data.objects.remove(cam_ob, do_unlink=True)
    bpy.data.cameras.remove(cam, do_unlink=True)

# Основные ракурсы
render_cam("01_overview_iso", (80, -80, 60), (1.1, 0, 0.785), ortho=False)
render_cam("02_top_plan", (0, 0, 120), (0, 0, 0), ortho=True, ortho_scale=100)
render_cam("03_side_east", (120, 0, 25), (1.57, 0, 1.57), ortho=True, ortho_scale=80)
render_cam("04_side_north", (0, -120, 25), (1.57, 0, 0), ortho=True, ortho_scale=80)
render_cam("05_pumpjack_closeup", (15, -15, 12), (1.2, 0, 0.785), ortho=False)
render_cam("06_UPN_pipes", (-25, -15, 20), (1.0, 0, -0.3), ortho=False)
render_cam("07_wellhead_nodes", (25, 10, 8), (1.0, 0, 2.2), ortho=False)
render_cam("08_KNS_BKNS_zone", (-50, 20, 25), (1.1, 0, -0.5), ortho=False)

print(f"Done. Renders saved to: {OUT_DIR}")
