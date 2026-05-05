"""Простая 3D-модель участка нефтепровода для Blender.

Труба идёт по земле слева, поднимается двумя ступенями на эстакаду,
проходит по верхнему ярусу и одним спуском возвращается к земле справа.
Каждый 90°-поворот — настоящая четверть тора (построена через bmesh).
Опоры Н-образные: две стойки + перекладина + верхняя балка.
Все трубы прозрачные.

Запуск:
    blender --python oil_pipeline.py
или внутри Blender: Scripting -> Open -> oil_pipeline.py -> Run Script.
"""

import math
from typing import Tuple

import bmesh
import bpy


# ---------------------------------------------------------------------------
# Параметры
# ---------------------------------------------------------------------------

PIPE_RADIUS = 0.3
BEND_RADIUS = 0.6          # радиус колена (major radius четверти тора)
WALL_THICKNESS = 0.05      # толщина стенки (внутренний радиус = PIPE_RADIUS - это)

Z_LOW = 0.35               # нижний уровень (почти по земле)
Z_MID = 1.8                # промежуточная ступень
Z_HIGH = 3.8               # верхний ярус эстакады

X_START = 0.0
X_STEP1 = 5.0              # первый подъём (низ -> середина)
X_STEP2 = 8.0              # второй подъём (середина -> верх)
X_DROP = 20.0              # спуск (верх -> низ)
X_END = 24.0

PIPE_Y_OFFSETS = (-1.0, 0.0, 1.0)

# Позиции опор и уровни, до которых они должны дотягиваться
SUPPORT_POSITIONS_MID = (6.5,)
SUPPORT_POSITIONS_HIGH = (10.5, 13.5, 16.5, 19.2)

SUPPORT_HALF_Y = 1.7       # расстояние от оси до стойки H-опоры


# ---------------------------------------------------------------------------
# Утилиты сцены и материалов
# ---------------------------------------------------------------------------

def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                  bpy.data.cameras, bpy.data.curves):
        for item in list(block):
            block.remove(item)


def make_transparent_pipe_material() -> bpy.types.Material:
    mat = bpy.data.materials.new(name="PipeTransparent")
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    # Показываем внутреннюю стенку трубы сквозь прозрачную внешнюю
    mat.show_transparent_back = True
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (300, 0)
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = (0.55, 0.8, 1.0, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.2
    bsdf.inputs["Roughness"].default_value = 0.1
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.22
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 1.0
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = 1.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.45

    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def make_steel_material() -> bpy.types.Material:
    mat = bpy.data.materials.new(name="SupportSteel")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.22, 0.22, 0.25, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.8
        bsdf.inputs["Roughness"].default_value = 0.5
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def apply_pipe_wall(obj: bpy.types.Object) -> None:
    """Превращает поверхностную оболочку в полую стенку заданной толщины.

    Исходный меш — внешняя поверхность трубы. Solidify продавливает её
    внутрь на WALL_THICKNESS (offset=-1) и замыкает открытые торцы
    кольцевыми крышками (use_rim=True).
    """
    mod = obj.modifiers.new(name="PipeWall", type="SOLIDIFY")
    mod.thickness = WALL_THICKNESS
    mod.offset = -1.0          # стенка уходит внутрь от внешней поверхности
    mod.use_rim = True         # кольцевые торцы
    mod.use_rim_only = False

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


# ---------------------------------------------------------------------------
# Примитивы трубы
# ---------------------------------------------------------------------------

def add_straight_pipe(p1: Tuple[float, float, float],
                      p2: Tuple[float, float, float],
                      material: bpy.types.Material) -> None:
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 1e-6:
        return
    center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0, (z1 + z2) / 2.0)

    if abs(dx) > max(abs(dy), abs(dz)):
        rotation = (0.0, math.radians(90.0), 0.0)
    elif abs(dy) > abs(dz):
        rotation = (math.radians(90.0), 0.0, 0.0)
    else:
        rotation = (0.0, 0.0, 0.0)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_RADIUS,
        depth=length,
        location=center,
        rotation=rotation,
        vertices=32,
        end_fill_type="NOTHING",   # открытые торцы — Solidify сам сделает кольцо
    )
    obj = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    apply_pipe_wall(obj)
    assign_material(obj, material)


def add_quarter_bend(center: Tuple[float, float, float],
                     start_deg: float, end_deg: float,
                     material: bpy.types.Material) -> None:
    """Четверть тора в плоскости XZ — реальный кусок 1/4 бублика.

    Строится через bmesh: ось дуги — окружность major_radius вокруг `center`,
    вокруг каждого осевого узла строится колечко minor_radius.
    Углы задаются в плоскости XZ (0° = +X, 90° = +Z).
    """
    # Всегда обходим дугу в одном направлении — тогда нормали получаемых
    # квадов смотрят наружу, и Solidify корректно делает стенку внутрь.
    if start_deg > end_deg:
        start_deg, end_deg = end_deg, start_deg

    major_segments = 16
    minor_segments = 24
    R = BEND_RADIUS
    r = PIPE_RADIUS

    a0 = math.radians(start_deg)
    a1 = math.radians(end_deg)

    mesh = bpy.data.meshes.new("BendMesh")
    bm = bmesh.new()

    rings = []
    for i in range(major_segments + 1):
        t = i / major_segments
        theta = a0 + t * (a1 - a0)
        axis_pt = (
            center[0] + R * math.cos(theta),
            center[1],
            center[2] + R * math.sin(theta),
        )
        u = (math.cos(theta), 0.0, math.sin(theta))  # радиальная ось сечения
        v = (0.0, 1.0, 0.0)                           # вторая ось сечения

        ring = []
        for j in range(minor_segments):
            phi = 2.0 * math.pi * j / minor_segments
            cp, sp = math.cos(phi), math.sin(phi)
            ring.append(bm.verts.new((
                axis_pt[0] + r * (cp * u[0] + sp * v[0]),
                axis_pt[1] + r * (cp * u[1] + sp * v[1]),
                axis_pt[2] + r * (cp * u[2] + sp * v[2]),
            )))
        rings.append(ring)

    for i in range(major_segments):
        for j in range(minor_segments):
            jn = (j + 1) % minor_segments
            face = bm.faces.new([rings[i][j], rings[i][jn],
                                 rings[i + 1][jn], rings[i + 1][j]])
            face.smooth = True

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Bend", mesh)
    bpy.context.collection.objects.link(obj)
    apply_pipe_wall(obj)
    assign_material(obj, material)


# ---------------------------------------------------------------------------
# Ступенчатый профиль трубы
# ---------------------------------------------------------------------------

def build_stepped_pipe(y: float, material: bpy.types.Material) -> None:
    r = BEND_RADIUS

    # Центры дуг и их угловые диапазоны (0° = +X, 90° = +Z):
    bends = [
        ((X_STEP1 - r, y, Z_LOW + r), 270.0, 360.0),   # c1: низ -> вверх
        ((X_STEP1 + r, y, Z_MID - r), 180.0,  90.0),   # c2: вверх -> вправо
        ((X_STEP2 - r, y, Z_MID + r), 270.0, 360.0),   # c3: середина -> вверх
        ((X_STEP2 + r, y, Z_HIGH - r), 180.0,  90.0),  # c4: вверх -> вправо
        ((X_DROP - r, y, Z_HIGH - r),   90.0,   0.0),  # c5: вправо -> вниз
        ((X_DROP + r, y, Z_LOW + r),   180.0, 270.0),  # c6: вниз -> вправо
    ]
    for center, a0, a1 in bends:
        add_quarter_bend(center, a0, a1, material)

    # Горизонтали (укорочены на r возле углов)
    add_straight_pipe((X_START, y, Z_LOW),
                      (X_STEP1 - r, y, Z_LOW), material)
    add_straight_pipe((X_STEP1 + r, y, Z_MID),
                      (X_STEP2 - r, y, Z_MID), material)
    add_straight_pipe((X_STEP2 + r, y, Z_HIGH),
                      (X_DROP - r, y, Z_HIGH), material)
    add_straight_pipe((X_DROP + r, y, Z_LOW),
                      (X_END, y, Z_LOW), material)

    # Вертикальные перемычки между коленами
    add_straight_pipe((X_STEP1, y, Z_LOW + r),
                      (X_STEP1, y, Z_MID - r), material)
    add_straight_pipe((X_STEP2, y, Z_MID + r),
                      (X_STEP2, y, Z_HIGH - r), material)
    add_straight_pipe((X_DROP, y, Z_HIGH - r),
                      (X_DROP, y, Z_LOW + r), material)


# ---------------------------------------------------------------------------
# Н-образные опоры (две стойки + поперечина + верхняя балка)
# ---------------------------------------------------------------------------

def add_h_support(x: float, top_z: float,
                  material: bpy.types.Material) -> None:
    post_section = 0.14
    beam_thickness = 0.12
    half_y = SUPPORT_HALF_Y

    # Верх стойки — чтобы над ним поместилась горизонтальная балка, на которой
    # лежат трубы (труба касается балки).
    post_top = top_z - PIPE_RADIUS - beam_thickness
    if post_top <= 0.3:
        post_top = top_z - PIPE_RADIUS  # на всякий случай

    # Две вертикальные стойки (ноги буквы Н)
    for sign in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(x, sign * half_y, post_top / 2.0),
        )
        post = bpy.context.active_object
        post.scale = (post_section, post_section, post_top)
        assign_material(post, material)

    # Средняя перекладина — собственно «палочка» буквы Н
    mid_z = post_top * 0.55
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0.0, mid_z))
    crossbar = bpy.context.active_object
    crossbar.scale = (post_section * 0.8,
                      2.0 * half_y,
                      post_section * 0.7)
    assign_material(crossbar, material)

    # Верхняя балка, на которой лежат трубы
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(x, 0.0, post_top + beam_thickness / 2.0),
    )
    top_beam = bpy.context.active_object
    top_beam.scale = (post_section * 1.4,
                      2.0 * half_y + post_section,
                      beam_thickness)
    assign_material(top_beam, material)


def add_supports(material: bpy.types.Material) -> None:
    for x in SUPPORT_POSITIONS_MID:
        add_h_support(x, Z_MID, material)
    for x in SUPPORT_POSITIONS_HIGH:
        add_h_support(x, Z_HIGH, material)


# ---------------------------------------------------------------------------
# Окружение
# ---------------------------------------------------------------------------

def add_ground() -> None:
    bpy.ops.mesh.primitive_plane_add(
        size=60.0,
        location=((X_START + X_END) / 2.0, 0.0, 0.0),
    )
    ground = bpy.context.active_object
    ground.name = "Ground"
    mat = bpy.data.materials.new(name="Ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.18, 0.28, 0.14, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.95
    assign_material(ground, mat)


def add_camera_and_light() -> None:
    bpy.ops.object.camera_add(
        location=((X_START + X_END) / 2.0, -14.0, 5.5),
        rotation=(math.radians(80.0), 0.0, 0.0),
    )
    bpy.context.scene.camera = bpy.context.active_object

    bpy.ops.object.light_add(
        type="SUN",
        location=(4.0, -6.0, 12.0),
        rotation=(math.radians(50.0), 0.0, math.radians(30.0)),
    )
    bpy.context.active_object.data.energy = 3.5


# ---------------------------------------------------------------------------
# Главная сборка
# ---------------------------------------------------------------------------

def build_pipeline() -> None:
    clear_scene()

    pipe_mat = make_transparent_pipe_material()
    support_mat = make_steel_material()

    for y in PIPE_Y_OFFSETS:
        build_stepped_pipe(y, pipe_mat)

    add_supports(support_mat)
    add_ground()
    add_camera_and_light()

    scene = bpy.context.scene
    engine_items = {e.identifier for e in
                    bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    scene.render.engine = ("BLENDER_EEVEE_NEXT"
                           if "BLENDER_EEVEE_NEXT" in engine_items
                           else "BLENDER_EEVEE")


if __name__ == "__main__":
    build_pipeline()
    print("Нефтепровод с Н-опорами и четверть-торовыми коленами готов.")