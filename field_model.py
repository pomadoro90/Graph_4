"""
Комплексная упрощённая 3D-модель нефтяного месторождения для Blender.

Состав сцены:
- добывающая скважина с насосной арматурой / станком-качалкой;
- нагнетательная скважина;
- ДНС, УПСВ, УПН, БКНС, КНС;
- система трубопроводов: нефтегазожидкостные, водоводы, товарная нефть;
- резервуары, сепараторы, насосные блоки, эстакады, стрелки потоков и подписи.

Запуск:
    blender --background --python field_model.py
или внутри Blender: Scripting -> Open -> Run Script.

Результат сохраняется рядом со скриптом:
    field_development_complex.blend
"""

from __future__ import annotations

import math
import os
from typing import Iterable, Tuple

import bpy
from mathutils import Vector

Vec3 = Tuple[float, float, float]

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT_BLEND = os.path.join(HERE, "field_development_complex.blend")

# ---------------------------------------------------------------------------
# Сцена, материалы, базовые примитивы
# ---------------------------------------------------------------------------


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.curves,
        bpy.data.fonts,
    ):
        for item in list(block):
            if getattr(item, "users", 0) == 0:
                block.remove(item)


def mat(name: str, rgba: Tuple[float, float, float, float], metallic=0.0, roughness=0.55, alpha=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    if alpha is not None or rgba[3] < 1.0:
        m.blend_method = "BLEND"
        m.show_transparent_back = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha if alpha is not None else rgba[3]
    return m


MATS = {}


def make_materials():
    MATS.update(
        ground=mat("Ground / tundra", (0.18, 0.27, 0.16, 1), roughness=0.9),
        gravel=mat("Gravel pads", (0.33, 0.32, 0.29, 1), roughness=0.85),
        road=mat("Service roads", (0.10, 0.10, 0.10, 1), roughness=0.8),
        steel=mat("Dark steel", (0.08, 0.09, 0.11, 1), metallic=0.8, roughness=0.35),
        orange=mat("Safety orange", (0.95, 0.43, 0.08, 1), metallic=0.25, roughness=0.55),
        blue=mat("Water blue", (0.05, 0.34, 0.86, 1), metallic=0.1, roughness=0.3),
        pipe_oil=mat("Oil / emulsion pipeline", (0.13, 0.13, 0.14, 1), metallic=0.7, roughness=0.33),
        pipe_water=mat("Injection water pipeline", (0.02, 0.28, 0.85, 1), metallic=0.45, roughness=0.38),
        pipe_product=mat("Sales oil pipeline", (0.95, 0.74, 0.12, 1), metallic=0.55, roughness=0.35),
        pipe_gas=mat("Gas line", (0.50, 0.76, 0.95, 0.42), metallic=0.15, roughness=0.12, alpha=0.42),
        building=mat("White process modules", (0.82, 0.84, 0.80, 1), metallic=0.15, roughness=0.5),
        tank=mat("Storage tank metal", (0.68, 0.70, 0.66, 1), metallic=0.55, roughness=0.28),
        red=mat("Valve red", (0.8, 0.05, 0.04, 1), metallic=0.25, roughness=0.5),
        green=mat("Equipment green", (0.12, 0.42, 0.18, 1), metallic=0.2, roughness=0.6),
        text=mat("Black label text", (0.02, 0.02, 0.02, 1), roughness=0.5),
        glass=mat("Transparent vessels", (0.55, 0.82, 1.0, 0.32), metallic=0.1, roughness=0.06, alpha=0.32),
    )


def assign(obj, material):
    obj.data.materials.append(material)
    return obj


def add_box(name: str, loc: Vec3, scale: Vec3, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    return obj


def add_cylinder(name: str, loc: Vec3, radius: float, depth: float, material, vertices=32, axis="Z", rot=(0, 0, 0)):
    rotation = rot
    if axis == "X":
        rotation = (0, math.radians(90), 0)
    elif axis == "Y":
        rotation = (math.radians(90), 0, 0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    assign(obj, material)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def add_cone(name: str, loc: Vec3, r1: float, r2: float, depth: float, material, vertices=32):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    assign(obj, material)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def new_mesh_obj(name: str, verts, faces, material):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign(obj, material)
    try:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth()
        obj.select_set(False)
    except Exception:
        pass
    return obj


def add_annular_sector(name: str, loc: Vec3, outer_r: float, inner_r: float,
                       thickness: float, start_deg: float, end_deg: float,
                       material, segments=18):
    """Экструдированный сектор кольца в плоскости YZ, толщина вдоль X.

    Используется для реалистичных сегментных противовесов станка-качалки:
    это не случайные висящие диски, а толстые болтовые грузы на кривошипах.
    """
    x, y, z = loc
    a0 = math.radians(start_deg)
    a1 = math.radians(end_deg)
    if a1 < a0:
        a0, a1 = a1, a0
    pts_outer = []
    pts_inner = []
    for i in range(segments + 1):
        a = a0 + (a1 - a0) * i / segments
        pts_outer.append((outer_r * math.cos(a), outer_r * math.sin(a)))
        pts_inner.append((inner_r * math.cos(a), inner_r * math.sin(a)))
    loop = pts_outer + list(reversed(pts_inner))
    verts = [(x - thickness / 2, y + yy, z + zz) for yy, zz in loop] + [(x + thickness / 2, y + yy, z + zz) for yy, zz in loop]
    n = len(loop)
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        faces.append((i, (i + 1) % n, (i + 1) % n + n, i + n))
    return new_mesh_obj(name, verts, faces, material)


def _unit(v: Vector) -> Vector:
    if v.length <= 1e-8:
        return Vector((0, 0, 0))
    return v.normalized()


def add_quarter_torus_elbow(name: str, corner: Vec3, prev_pt: Vec3, next_pt: Vec3,
                            pipe_radius: float, material, bend_radius=None, seg=16, ring=12):
    """90° трубный отвод как четверть тора, без шаровых муфт.

    prev_pt -> corner -> next_pt должны образовывать примерно прямой угол.
    Отвод касается прямых труб в точках на расстоянии bend_radius от угла.
    """
    c = Vector(corner)
    u = _unit(Vector(prev_pt) - c)   # от угла назад к входящей трубе
    v = _unit(Vector(next_pt) - c)   # от угла по выходящей трубе
    if u.length == 0 or v.length == 0 or abs(u.dot(v)) > 0.12:
        return None
    bend_radius = bend_radius or pipe_radius * 3.8
    plane_n = u.cross(v)
    if plane_n.length <= 1e-8:
        return None
    plane_n.normalize()
    center = c + u * bend_radius + v * bend_radius
    verts = []
    faces = []
    for i in range(seg + 1):
        t = (math.pi / 2) * i / seg
        # starts at corner+u*R and ends at corner+v*R
        arc = center - v * (bend_radius * math.cos(t)) - u * (bend_radius * math.sin(t))
        tangent = _unit(v * math.sin(t) - u * math.cos(t))
        binormal = _unit(tangent.cross(plane_n))
        for j in range(ring):
            a = 2 * math.pi * j / ring
            pos = arc + plane_n * (pipe_radius * math.cos(a)) + binormal * (pipe_radius * math.sin(a))
            verts.append(tuple(pos))
    for i in range(seg):
        for j in range(ring):
            a = i * ring + j
            b = i * ring + (j + 1) % ring
            c2 = (i + 1) * ring + (j + 1) % ring
            d = (i + 1) * ring + j
            faces.append((a, b, c2, d))
    return new_mesh_obj(name, verts, faces, material)


def add_flange(name: str, loc: Vec3, direction: Vec3, radius: float, material):
    d = _unit(Vector(direction))
    if d.length == 0:
        return None
    # Плоская фланцевая шайба, а не шар/капсула: малая толщина вдоль трубы.
    return cylinder_between(name, tuple(Vector(loc) - d * radius * 0.16), tuple(Vector(loc) + d * radius * 0.16), radius * 1.38, material, vertices=32)


def add_pipe_support_at(name: str, p: Vec3, radius: float):
    x, y, z = p
    if z <= 0.42:
        return
    add_h_support(name, x, y, max(0.20, z - radius - 0.05))
    add_box(name + "_clamp", (x, y, z - radius * 0.15), (radius * 2.8, radius * 1.1, radius * 0.35), MATS["orange"])


def cylinder_between(name: str, p1: Vec3, p2: Vec3, radius: float, material, vertices=24):
    v1, v2 = Vector(p1), Vector(p2)
    mid = (v1 + v2) / 2
    direction = v2 - v1
    length = direction.length
    if length <= 1e-6:
        return None
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    obj = bpy.context.active_object
    obj.name = name
    quat = direction.to_track_quat("Z", "Y")
    obj.rotation_euler = quat.to_euler()
    assign(obj, material)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def pipe_path(name: str, points: Iterable[Vec3], radius: float, material, elevated=True):
    """Связная трасса трубы.

    Прямые участки подрезаются у 90° углов, а сами углы строятся как
    четверть тора. Сферических "шариков" на поворотах нет: концы получают
    фланцы/заглушки, промежуточные прямые стыки — короткие муфты.
    """
    pts = [Vector(p) for p in points]
    if len(pts) < 2:
        return
    bend_radius = radius * 4.0

    def is_elbow(i: int) -> bool:
        if i <= 0 or i >= len(pts) - 1:
            return False
        a = _unit(pts[i - 1] - pts[i])
        b = _unit(pts[i + 1] - pts[i])
        return a.length > 0 and b.length > 0 and abs(a.dot(b)) < 0.12

    # Прямые участки: у углов оставляем место под радиусный отвод.
    for i in range(len(pts) - 1):
        start = Vector(pts[i])
        end = Vector(pts[i + 1])
        direction = _unit(end - start)
        if direction.length == 0:
            continue
        if is_elbow(i):
            start = pts[i] + direction * bend_radius
        if is_elbow(i + 1):
            end = pts[i + 1] - direction * bend_radius
        if (end - start).length > radius * 2.0:
            cylinder_between(f"{name}_straight_{i+1:02d}", tuple(start), tuple(end), radius, material, vertices=28)
            if elevated:
                span = end - start
                steps = max(1, int(span.length // 3.8))
                for k in range(1, steps + 1):
                    p = start + span * (k / (steps + 1))
                    add_pipe_support_at(f"{name}_support_{i+1:02d}_{k:02d}", tuple(p), radius)

    # Фитинги: 90° = четверть тора, прямые промежуточные точки = фланцевая муфта.
    for i in range(1, len(pts) - 1):
        if is_elbow(i):
            add_quarter_torus_elbow(f"{name}_elbow_{i:02d}", tuple(pts[i]), tuple(pts[i - 1]), tuple(pts[i + 1]), radius, material, bend_radius=bend_radius)
        else:
            d = _unit(pts[i + 1] - pts[i - 1])
            add_flange(f"{name}_coupling_{i:02d}", tuple(pts[i]), tuple(d), radius, material)

    # Видимые фланцы на начальном и конечном подключении к оборудованию.
    add_flange(f"{name}_start_flange", tuple(pts[0]), tuple(pts[1] - pts[0]), radius, material)
    add_flange(f"{name}_end_flange", tuple(pts[-1]), tuple(pts[-1] - pts[-2]), radius, material)


# ---------------------------------------------------------------------------
# Подписи, дороги, площадки
# ---------------------------------------------------------------------------


def add_label(text: str, loc: Vec3, size=0.42, rot_z=0.0):
    # Подписи сделаны крупнее, чем физический масштаб объектов: это учебная
    # обзорная схема, где важнее читаемость технологических узлов.
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(70), 0, rot_z))
    obj = bpy.context.active_object
    obj.name = "Label_" + text
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size * 1.45
    obj.data.extrude = 0.012
    assign(obj, MATS["text"])
    return obj


def add_pad(name: str, loc: Vec3, sx: float, sy: float):
    add_box(name, (loc[0], loc[1], 0.025), (sx, sy, 0.05), MATS["gravel"])


def add_road(name: str, p1: Vec3, p2: Vec3, width=1.0):
    x1, y1, _ = p1
    x2, y2, _ = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    add_box(name, ((x1 + x2) / 2, (y1 + y2) / 2, 0.035), (length, width, 0.035), MATS["road"], rot=(0, 0, angle))


# ---------------------------------------------------------------------------
# Нефтепромысловые элементы
# ---------------------------------------------------------------------------


def add_h_support(name: str, x: float, y: float, top_z: float):
    post_h = max(0.45, top_z)
    for off in (-0.42, 0.42):
        add_box(name + f"_post_{off}", (x, y + off, post_h / 2), (0.08, 0.08, post_h), MATS["steel"])
    add_box(name + "_beam", (x, y, post_h), (0.10, 1.05, 0.08), MATS["steel"])


def add_valve_tree(name: str, loc: Vec3, scale=1.0, injection=False):
    x, y, z = loc
    material = MATS["blue"] if injection else MATS["steel"]
    add_cylinder(name + "_casing", (x, y, z + 0.45 * scale), 0.14 * scale, 0.9 * scale, material, vertices=24)
    add_cylinder(name + "_flange", (x, y, z + 0.95 * scale), 0.25 * scale, 0.12 * scale, MATS["orange"], vertices=24)
    add_cylinder(name + "_cross", (x, y, z + 1.16 * scale), 0.07 * scale, 0.9 * scale, material, axis="X", vertices=16)
    add_cylinder(name + "_top", (x, y, z + 1.42 * scale), 0.07 * scale, 0.45 * scale, material, vertices=16)
    for sx in (-1, 1):
        add_cylinder(name + f"_handwheel_{sx}", (x + sx * 0.52 * scale, y, z + 1.16 * scale), 0.16 * scale, 0.04 * scale, MATS["red"], axis="X", vertices=24)


def add_pumpjack(name: str, loc: Vec3, scale=0.8):
    """Станок-качалка, приближенный к референсу pump_script.py.

    Вместо условного конуса используется А-рама, H-балансир, настоящая
    профильная "лошадиная голова" с дугой, кривошипы, сегментные
    противовесы, шатуны и шток к устью скважины.
    """
    x, y, z = loc
    s = scale
    add_box(name + "_pad", (x, y, z + 0.06 * s), (5.0 * s, 8.5 * s, 0.12 * s), MATS["gravel"])
    add_box(name + "_skid", (x, y - 0.25 * s, z + 0.34 * s), (3.6 * s, 7.4 * s, 0.42 * s), MATS["steel"])

    # A-frame / samson post: четыре наклонные стойки + крестовые связи.
    leg_top = Vector((x, y, z + 5.8 * s))
    leg_bot_z = z + 0.72 * s
    base_half_x = 1.55 * s
    base_half_y = 1.30 * s
    for bx, by, suffix in [(-base_half_x, -base_half_y, "FL"), (base_half_x, -base_half_y, "FR"),
                           (-base_half_x, base_half_y, "RL"), (base_half_x, base_half_y, "RR")]:
        cylinder_between(name + "_A_frame_" + suffix, (x + bx, y + by, leg_bot_z), tuple(leg_top), 0.075 * s, MATS["steel"], vertices=12)
    for yy, label in [(-0.75 * s, "front"), (0.75 * s, "rear")]:
        cylinder_between(name + "_cross_" + label, (x - 0.85 * s, y + yy, z + 2.65 * s), (x + 0.85 * s, y + yy, z + 2.65 * s), 0.055 * s, MATS["steel"], vertices=10)
    for xx, label in [(-0.85 * s, "L"), (0.85 * s, "R")]:
        cylinder_between(name + "_cross_side_" + label, (x + xx, y - 0.75 * s, z + 2.65 * s), (x + xx, y + 0.75 * s, z + 2.65 * s), 0.055 * s, MATS["steel"], vertices=10)

    add_box(name + "_saddle", (x, y, z + 5.82 * s), (1.25 * s, 1.35 * s, 0.42 * s), MATS["steel"])
    add_cylinder(name + "_pivot", (x, y, z + 5.98 * s), 0.13 * s, 1.65 * s, MATS["steel"], axis="X", vertices=20)

    # H-profile walking beam: top/bottom flanges + web.
    beam_len = 9.5 * s
    beam_y0 = y - 1.4 * s
    beam_z = z + 6.3 * s
    add_box(name + "_beam_top_flange", (x, beam_y0, beam_z + 0.29 * s), (0.70 * s, beam_len, 0.12 * s), MATS["steel"])
    add_box(name + "_beam_bottom_flange", (x, beam_y0, beam_z - 0.29 * s), (0.70 * s, beam_len, 0.12 * s), MATS["steel"])
    add_box(name + "_beam_web", (x, beam_y0, beam_z), (0.14 * s, beam_len, 0.46 * s), MATS["steel"])

    # Голова балансира: экструдированная YZ-силуэтная деталь с дугой.
    head_y_beam = beam_y0 - beam_len / 2
    head_y_chord = head_y_beam - 0.75 * s
    head_top = beam_z + 0.80 * s
    head_chord_bot = beam_z - 1.20 * s
    chord_half = (head_top - head_chord_bot) / 2
    chord_mid = (head_top + head_chord_bot) / 2
    sagitta = 0.75 * s
    uc = (sagitta * sagitta - chord_half * chord_half) / (2 * sagitta)
    r_seg = sagitta - uc
    theta_bot = math.atan2(-chord_half, -uc)
    theta_top = -theta_bot
    arc = []
    for k in range(14):
        t = theta_bot + (theta_top - theta_bot) * k / 13
        u = uc + r_seg * math.cos(t)
        v = r_seg * math.sin(t)
        arc.append((head_y_chord - u, chord_mid + v))
    sil = [(head_y_beam, head_top), (head_y_beam, beam_z - 0.35 * s)] + arc
    verts = [(-0.14 * s, yy, zz) for yy, zz in sil] + [(0.14 * s, yy, zz) for yy, zz in sil]
    verts = [(vx + x, vy, vz) for vx, vy, vz in verts]
    n = len(sil)
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        faces.append((i, (i + 1) % n, (i + 1) % n + n, i + n))
    new_mesh_obj(name + "_horse_head_curved", verts, faces, MATS["steel"])

    # Кривошипно-шатунный механизм и противовесы-сегменты.
    crank_y = y + 4.0 * s
    crank_z = z + 2.0 * s
    pin_y = crank_y - 0.45 * s
    pin_z = crank_z + 0.32 * s
    add_box(name + "_gearbox", (x, crank_y, z + 1.05 * s), (1.35 * s, 1.05 * s, 1.0 * s), MATS["steel"])
    add_box(name + "_motor", (x + 1.35 * s, crank_y + 1.15 * s, z + 0.78 * s), (0.9 * s, 1.2 * s, 0.72 * s), MATS["green"])
    add_cylinder(name + "_crankshaft", (x, crank_y, crank_z), 0.11 * s, 2.3 * s, MATS["steel"], axis="X", vertices=20)
    for side, sx in [("L", -0.95 * s), ("R", 0.95 * s)]:
        cylinder_between(name + "_crank_arm_" + side, (x + sx, crank_y, crank_z), (x + sx, pin_y, pin_z), 0.06 * s, MATS["orange"], vertices=10)
        add_cylinder(name + "_crank_pin_hub_" + side, (x + sx, pin_y, pin_z), 0.13 * s, 0.24 * s, MATS["steel"], axis="X", vertices=18)
        add_annular_sector(name + "_counterweight_segment_" + side, (x + sx, crank_y, crank_z), 0.78 * s, 0.42 * s, 0.22 * s, 205, 318, MATS["orange"], segments=20)
        for bolt_i, ang_deg in enumerate((222, 260, 300), start=1):
            a = math.radians(ang_deg)
            add_cylinder(
                f"{name}_counterweight_bolt_{side}_{bolt_i}",
                (x + sx, crank_y + 0.59 * s * math.cos(a), crank_z + 0.59 * s * math.sin(a)),
                0.045 * s,
                0.27 * s,
                MATS["steel"],
                axis="X",
                vertices=12,
            )
        cylinder_between(name + "_pitman_" + side, (x + sx, pin_y, pin_z), (x + sx * 0.45, beam_y0 + beam_len / 2 - 0.3 * s, beam_z - 0.35 * s), 0.045 * s, MATS["steel"], vertices=10)

    # Подвеска, полированный шток и устье строго под головой.
    cable_y = head_y_chord
    cable_top_z = head_chord_bot
    cable_bot_z = z + 0.9 * s
    cylinder_between(name + "_bridle_cable", (x, cable_y, cable_bot_z), (x, cable_y, cable_top_z), 0.035 * s, MATS["steel"], vertices=10)
    add_box(name + "_carrier_bar", (x, cable_y, cable_bot_z), (0.8 * s, 0.10 * s, 0.08 * s), MATS["steel"])
    add_valve_tree(name + "_wellhead", (x, cable_y, z), scale=0.72 * s)



def add_injection_well(name: str, loc: Vec3):
    x, y, z = loc
    add_pad(name + "_pad", loc, 4.0, 4.0)
    add_valve_tree(name + "_tree", (x, y, z), scale=1.05, injection=True)
    add_cylinder(name + "_filter_skid", (x + 1.15, y + 0.75, z + 0.45), 0.26, 1.4, MATS["blue"], axis="X", vertices=24)
    add_box(name + "_control_box", (x - 1.1, y + 0.6, z + 0.65), (0.8, 0.55, 1.0), MATS["building"])
    add_label("Нагнетательная\nскважина", (x, y - 2.8, z + 0.08), size=0.34)


def add_horizontal_vessel(name: str, loc: Vec3, length: float, radius: float, material):
    """Горизонтальный аппарат на седловых опорах от земли до нижней образующей."""
    x, y, z = loc
    # страховка: центр не ниже радиуса + небольшой зазор под седла
    z = max(z, radius + 0.35)
    add_cylinder(name + "_body", (x, y, z), radius, length, material, axis="X", vertices=40)
    add_cylinder(name + "_left_head", (x - length / 2, y, z), radius, 0.08, material, axis="X", vertices=40)
    add_cylinder(name + "_right_head", (x + length / 2, y, z), radius, 0.08, material, axis="X", vertices=40)
    saddle_h = max(0.12, z - radius)
    for sx in (-0.34, 0.34):
        sx_abs = x + sx * length
        add_box(name + f"_saddle_{sx}", (sx_abs, y, saddle_h / 2), (0.36, radius * 1.75, saddle_h), MATS["steel"])
        add_box(name + f"_saddle_cap_{sx}", (sx_abs, y, z - radius + 0.035), (0.52, radius * 1.95, 0.07), MATS["orange"])
    # патрубки аппарата: вход/выход + верхний газоотвод, чтобы трубы имели куда подключаться
    add_flange(name + "_left_nozzle", (x - length / 2 - 0.08, y, z), (-1, 0, 0), 0.13, MATS["steel"])
    add_flange(name + "_right_nozzle", (x + length / 2 + 0.08, y, z), (1, 0, 0), 0.13, MATS["steel"])
    add_cylinder(name + "_gas_nozzle", (x, y, z + radius + 0.18), 0.08, 0.36, MATS["steel"], vertices=16)


def add_tank(name: str, loc: Vec3, radius=1.0, height=2.0, label=""):
    x, y, z = loc
    base_z = 0.0 if z < 0.02 else z
    # фундаментное кольцо и юбка: резервуар не висит и не стоит "в воздухе".
    add_cylinder(name + "_foundation", (x, y, base_z + 0.08), radius + 0.42, 0.16, MATS["gravel"], vertices=56)
    add_cylinder(name + "_skirt", (x, y, base_z + 0.22), radius * 1.02, 0.28, MATS["steel"], vertices=56)
    add_cylinder(name + "_wall", (x, y, base_z + 0.28 + height / 2), radius, height, MATS["tank"], vertices=56)
    add_cylinder(name + "_roof", (x, y, base_z + 0.28 + height + 0.08), radius * 0.98, 0.16, MATS["tank"], vertices=56)
    add_cylinder(name + "_roof_center_cap", (x, y, base_z + 0.28 + height + 0.22), radius * 0.18, 0.12, MATS["steel"], vertices=24)
    # боковые патрубки/фланцы для видимой технологической связности
    nozzle_z = base_z + 0.28 + min(1.0, height * 0.45)
    add_flange(name + "_inlet_nozzle", (x - radius - 0.08, y, nozzle_z), (-1, 0, 0), 0.14, MATS["steel"])
    add_flange(name + "_outlet_nozzle", (x + radius + 0.08, y, nozzle_z), (1, 0, 0), 0.14, MATS["steel"])
    add_cylinder(name + "_top_vent", (x, y, base_z + 0.28 + height + 0.62), 0.07, 0.36, MATS["steel"], vertices=16)
    if label:
        add_label(label, (x, y - radius - 0.7, base_z + 0.08), size=0.32)



def add_pump_block(name: str, loc: Vec3, count=3, water=False):
    """Насосный блок на общей раме с входным/напорным коллекторами."""
    x, y, z = loc
    material = MATS["blue"] if water else MATS["orange"]
    span = max(1.0, (count - 1) * 0.9 + 0.9)
    add_box(name + "_common_skid", (x, y, z + 0.12), (2.4, span + 0.45, 0.18), MATS["steel"])
    suction_x = x - 1.28
    discharge_x = x + 1.12
    add_cylinder(name + "_suction_header", (suction_x, y, z + 0.55), 0.09, span + 0.55, MATS["steel"], axis="Y", vertices=18)
    add_cylinder(name + "_discharge_header", (discharge_x, y, z + 0.62), 0.09, span + 0.55, material, axis="Y", vertices=18)
    for i in range(count):
        yy = y + (i - (count - 1) / 2) * 0.9
        add_box(f"{name}_pump_base_{i+1}", (x, yy, z + 0.24), (1.55, 0.48, 0.14), MATS["steel"])
        add_box(f"{name}_pump_{i+1}", (x, yy, z + 0.50), (1.25, 0.36, 0.38), material)
        add_cylinder(f"{name}_motor_{i+1}", (x - 0.78, yy, z + 0.51), 0.20, 0.55, MATS["green"], axis="X", vertices=20)
        cylinder_between(f"{name}_suction_spool_{i+1}", (suction_x, yy, z + 0.55), (x - 0.62, yy, z + 0.55), 0.055, MATS["steel"], vertices=14)
        cylinder_between(f"{name}_discharge_spool_{i+1}", (x + 0.62, yy, z + 0.62), (discharge_x, yy, z + 0.62), 0.055, material, vertices=14)
        add_flange(f"{name}_pump_suction_flange_{i+1}", (x - 0.62, yy, z + 0.55), (1, 0, 0), 0.06, MATS["steel"])
        add_flange(f"{name}_pump_discharge_flange_{i+1}", (x + 0.62, yy, z + 0.62), (1, 0, 0), 0.06, material)



def add_facility_dns(loc: Vec3):
    x, y, z = loc
    add_pad("DNS_pad", loc, 8.5, 6.5)
    add_box("DNS_control_module", (x - 2.6, y + 1.6, z + 0.55), (2.1, 1.5, 1.1), MATS["building"])
    add_horizontal_vessel("DNS_group_meter", (x - 0.3, y - 0.9, z + 1.05), 3.0, 0.48, MATS["glass"])
    add_pump_block("DNS_booster", (x + 2.35, y - 0.4, z), count=3)
    add_cylinder("DNS_flare_stack", (x + 3.6, y + 2.0, z + 2.0), 0.08, 4.0, MATS["steel"], vertices=12)
    add_cylinder("DNS_flare_burner_tip", (x + 3.6, y + 2.0, z + 4.17), 0.13, 0.26, MATS["orange"], vertices=16)
    add_cylinder("DNS_flare_cap", (x + 3.6, y + 2.0, z + 4.34), 0.16, 0.05, MATS["steel"], vertices=16)
    add_label("ДНС\nдожимная насосная", (x, y - 3.8, z + 0.08), size=0.34)


def add_facility_upsv(loc: Vec3):
    x, y, z = loc
    add_pad("UPSV_pad", loc, 9.0, 7.0)
    add_horizontal_vessel("UPSV_separator_1", (x - 1.7, y + 1.1, z + 1.1), 3.2, 0.55, MATS["glass"])
    add_horizontal_vessel("UPSV_separator_2", (x - 1.7, y - 0.7, z + 1.1), 3.2, 0.55, MATS["glass"])
    add_tank("UPSV_water_tank", (x + 2.2, y + 0.9, z), radius=0.9, height=1.8, label="вода")
    add_box("UPSV_reagent_block", (x + 2.1, y - 1.55, z + 0.55), (2.0, 1.0, 1.1), MATS["building"])
    add_label("УПСВ\nпредварительный\nсброс воды", (x, y - 4.0, z + 0.08), size=0.32)


def add_facility_upn(loc: Vec3):
    x, y, z = loc
    add_pad("UPN_pad", loc, 11.0, 8.0)
    add_horizontal_vessel("UPN_treater", (x - 2.5, y + 1.0, z + 1.2), 3.7, 0.62, MATS["glass"])
    add_box("UPN_heater", (x - 2.5, y - 1.4, z + 0.75), (2.7, 1.15, 1.5), MATS["orange"])
    add_tank("UPN_sales_tank_A", (x + 1.2, y + 1.2, z), radius=0.95, height=2.1, label="товарная\nнефть")
    add_tank("UPN_sales_tank_B", (x + 3.4, y + 1.2, z), radius=0.95, height=2.1)
    add_pump_block("UPN_export_pumps", (x + 2.3, y - 1.85, z), count=2)
    add_label("УПН\nподготовка нефти", (x, y - 4.5, z + 0.08), size=0.34)


def add_facility_bkns(loc: Vec3):
    x, y, z = loc
    add_pad("BKNS_pad", loc, 7.5, 5.0)
    add_box("BKNS_module", (x - 1.9, y, z + 0.65), (2.3, 1.6, 1.3), MATS["building"])
    add_pump_block("BKNS_high_pressure", (x + 1.1, y, z), count=4, water=True)
    add_cylinder("BKNS_blue_header", (x + 2.9, y, z + 0.65), 0.11, 3.6, MATS["blue"], axis="Y", vertices=16)
    add_label("БКНС\nблочная кустовая\nнасосная", (x, y - 3.0, z + 0.08), size=0.31)


def add_facility_kns(loc: Vec3):
    x, y, z = loc
    add_pad("KNS_pad", loc, 6.5, 4.5)
    add_tank("KNS_intake_tank", (x - 1.7, y + 0.4, z), radius=0.7, height=1.45, label="стоки")
    add_pump_block("KNS_transfer", (x + 1.2, y - 0.15, z), count=2, water=True)
    # Внутренняя обвязка КНС: бак -> всасывающий коллектор -> напорный коллектор.
    # Низкие участки идут на отметках насосных коллекторов, чтобы не висеть в воздухе.
    pipe_path(
        "KNS_intake_tank_to_suction_header",
        [(x - 0.92, y + 0.4, z + 0.93), (x - 0.08, y + 0.4, z + 0.72), (x - 0.08, y - 0.15, z + 0.55)],
        0.075,
        MATS["pipe_water"],
        elevated=True,
    )
    pipe_path(
        "KNS_discharge_header_to_station_tie_in",
        [(x + 2.32, y - 0.15, z + 0.62), (x + 2.32, y + 0.95, z + 0.82), (x + 2.32, y + 1.85, z + 0.82)],
        0.08,
        MATS["pipe_water"],
        elevated=True,
    )
    add_box("KNS_operator_box", (x + 1.2, y + 1.45, z + 0.45), (1.4, 0.8, 0.9), MATS["building"])
    add_label("КНС\nкустовая насосная", (x, y - 2.7, z + 0.08), size=0.31)


def add_arrow(name: str, loc: Vec3, direction="X", material=None):
    """Плоская стрелка направления потока вместо торчащего конуса.

    Предыдущие 3D-конусы воспринимались как случайные цветные капли/маркеры.
    Здесь стрелка лежит тонкой табличкой над трубой и не маскируется под фитинг.
    """
    material = material or MATS["orange"]
    x, y, z = loc
    length = 0.86
    width = 0.36
    tail = 0.46
    thick = 0.028
    local = [
        (-length / 2, -width * 0.30, 0),
        (-length / 2 + tail, -width * 0.30, 0),
        (-length / 2 + tail, -width / 2, 0),
        (length / 2, 0, 0),
        (-length / 2 + tail, width / 2, 0),
        (-length / 2 + tail, width * 0.30, 0),
        (-length / 2, width * 0.30, 0),
    ]
    yaw = {"X": 0.0, "-X": math.pi, "Y": math.pi / 2, "-Y": -math.pi / 2}.get(direction, 0.0)
    verts_top = []
    verts_bot = []
    for lx, ly, _ in local:
        rx = lx * math.cos(yaw) - ly * math.sin(yaw)
        ry = lx * math.sin(yaw) + ly * math.cos(yaw)
        verts_top.append((x + rx, y + ry, z + thick / 2))
        verts_bot.append((x + rx, y + ry, z - thick / 2))
    n = len(local)
    verts = verts_top + verts_bot
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        faces.append((i, (i + 1) % n, (i + 1) % n + n, i + n))
    obj = new_mesh_obj(name, verts, faces, material)
    add_box(name + "_stand", (x, y, z - 0.11), (0.08, 0.08, 0.22), MATS["steel"])
    return obj


# ---------------------------------------------------------------------------
# Компоновка месторождения
# ---------------------------------------------------------------------------


def build_field():
    clear_scene()
    make_materials()

    # Земля и дороги
    add_box("Field_ground", (0, 0, -0.03), (62, 42, 0.04), MATS["ground"])
    add_road("Road_main_wellpad_to_dns", (-20, -8, 0), (-5, -1, 0), 0.75)
    add_road("Road_dns_upsv", (-5, -1, 0), (5, 0, 0), 0.85)
    add_road("Road_upsv_upn", (5, 0, 0), (16, 0, 0), 0.85)
    add_road("Road_water_stations", (5, 0, 0), (4, 12, 0), 0.75)

    # Куст добывающих скважин
    producing = [(-22, -9, 0), (-17, -11, 0), (-20, -4, 0)]
    for i, p in enumerate(producing, start=1):
        add_pumpjack(f"Producing_well_{i}", p, scale=0.72)
        add_label(f"Добывающая\nскважина {i}\nс насосной\nарматурой", (p[0], p[1] - 5.0, 0.08), size=0.28)

    # Нагнетательный куст и насосные станции воды
    inj = (0, 15, 0)
    add_injection_well("Injection_well", inj)
    add_facility_kns((8, 12, 0))
    add_facility_bkns((-5, 12, 0))

    # Технологическая цепочка подготовки нефти
    add_facility_dns((-6, -1, 0))
    add_facility_upsv((5, 0, 0))
    add_facility_upn((17, 0, 0))

    # Трубопроводы добычи: куст -> ДНС
    manifold = (-13, -6, 0.72)
    add_cylinder("Wellpad_manifold", manifold, 0.18, 3.5, MATS["pipe_oil"], axis="Y", vertices=24)
    for i, p in enumerate(producing, start=1):
        pipe_path(
            f"Flowline_well_{i}_to_manifold",
            [(p[0], p[1] - 3.65 * 0.72, 0.65), (p[0], manifold[1], 0.75), manifold],
            0.07,
            MATS["pipe_oil"],
            elevated=True,
        )
    pipe_path(
        "Gathering_pipeline_manifold_to_DNS",
        [manifold, (-10.5, -6, 0.9), (-10.5, -1.9, 1.05), (-7.88, -1.9, 1.05)],
        0.13,
        MATS["pipe_oil"],
        elevated=True,
    )

    # Нефтяная технологическая линия: ДНС -> УПСВ -> УПН -> экспорт
    pipe_path("DNS_to_UPSV_emulsion", [(-4.70, -1.9, 1.05), (-1.0, -1.9, 1.10), (-1.0, 1.1, 1.10), (1.62, 1.1, 1.10)], 0.15, MATS["pipe_oil"])
    # Явная короткая обвязка проблемного узла у УПСВ: патрубок, фланец, колено и вход в аппарат.
    pipe_path("UPSV_separator_nozzle_spool", [(1.70, 1.1, 1.10), (1.55, 1.1, 1.10), (1.55, 1.1, 1.35), (2.05, 1.1, 1.35)], 0.095, MATS["pipe_oil"])
    add_flange("UPSV_separator_inlet_extra_flange", (1.68, 1.1, 1.10), (-1, 0, 0), 0.12, MATS["steel"])
    pipe_path("UPSV_to_UPN_oil", [(4.98, 1.1, 1.10), (8.8, 1.1, 1.15), (8.8, 1.0, 1.15), (12.57, 1.0, 1.20)], 0.15, MATS["pipe_oil"])
    pipe_path("UPN_tank_to_export_pumps", [(18.25, 1.2, 1.23), (18.25, -1.85, 1.05), (18.9, -1.85, 1.05)], 0.13, MATS["pipe_product"])
    pipe_path("UPN_sales_oil_export", [(19.9, -1.85, 1.0), (24.0, -1.85, 1.0), (24.0, -4.0, 1.0), (29, -4, 1.0)], 0.16, MATS["pipe_product"])
    add_label("товарная нефть\nна внешний\nнефтепровод", (28, -6.2, 0.08), size=0.32)

    # Вода: УПСВ/КНС -> БКНС -> нагнетательная скважина
    pipe_path("Produced_water_UPSV_to_KNS", [(8.18, 0.9, 1.08), (8.18, 6.5, 0.95), (5.52, 12.4, 0.95)], 0.11, MATS["pipe_water"])
    pipe_path("KNS_to_BKNS_water", [(10.32, 13.85, 0.82), (10.32, 14.0, 0.95), (-5.18, 14.0, 0.95), (-5.18, 12.0, 0.95)], 0.12, MATS["pipe_water"])
    pipe_path("BKNS_to_injection_well", [(-2.78, 12.0, 1.05), (-2.78, 15.0, 1.05), (-0.20, 15.0, 1.05)], 0.13, MATS["pipe_water"])

    # Газовая линия и факел
    # ДНС теперь явно связана с верхней газовой трубой через патрубок/короткий штуцер.
    pipe_path("DNS_group_meter_top_nozzle_to_gas_header", [(-6.3, -1.9, 1.72), (-6.3, -0.9, 1.72)], 0.07, MATS["pipe_gas"])
    pipe_path("Gas_line_DNS_UPSV", [(-6.3, -0.9, 1.72), (-6.3, 2.4, 1.9), (3.3, 2.4, 1.9), (3.3, 1.1, 1.75)], 0.07, MATS["pipe_gas"])
    pipe_path("Gas_line_UPSV_UPN", [(3.3, 1.1, 1.75), (3.3, 2.8, 1.9), (14.5, 2.8, 1.9), (14.5, 1.0, 1.9)], 0.07, MATS["pipe_gas"])

    # Стрелки потоков
    add_arrow("Arrow_gathering", (-9.0, -3.8, 1.15), direction="Y", material=MATS["orange"])
    add_arrow("Arrow_dns_upsv", (0.5, -1.0, 1.35), direction="X", material=MATS["orange"])
    add_arrow("Arrow_upsv_upn", (11.0, 0.2, 1.4), direction="X", material=MATS["orange"])
    add_arrow("Arrow_export", (25.5, -2.2, 1.2), direction="X", material=MATS["pipe_product"])
    add_arrow("Arrow_water_to_bkns", (2.0, 12.0, 1.15), direction="-X", material=MATS["blue"])
    add_arrow("Arrow_water_to_inj", (-4.0, 15.0, 1.25), direction="X", material=MATS["blue"])

    # Легенда
    add_box("Legend_panel", (-25, 13, 0.75), (7.0, 0.12, 1.5), MATS["building"])
    add_label("Схема месторождения:\nчёрный — нефть/эмульсия\nсиний — вода на закачку\nжёлтый — товарная нефть\nголубой прозрачный — газ", (-25, 12.7, 1.05), size=0.28)

    # Камера и свет
    bpy.ops.object.light_add(type="SUN", location=(0, -8, 20), rotation=(math.radians(45), 0, math.radians(25)))
    bpy.context.active_object.name = "Sun_main"
    bpy.context.active_object.data.energy = 3.0
    bpy.ops.object.light_add(type="AREA", location=(0, -12, 10))
    bpy.context.active_object.name = "Area_fill"
    bpy.context.active_object.data.energy = 450
    bpy.context.active_object.data.size = 8

    # Ортографическая камера: вся схема помещается в кадр без перспективного
    # обрезания левого куста добывающих скважин.
    bpy.ops.object.camera_add(location=(1, -38, 26), rotation=(math.radians(58), 0, math.radians(4)))
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    cam.name = "Camera_overview"
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 60

    # Рендер-настройки
    scene = bpy.context.scene
    engine_items = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engine_items else "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"

    # Организация: origin/cursor
    bpy.context.scene.cursor.location = (0, 0, 0)


def main():
    build_field()
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("Saved:", OUT_BLEND)
    print("Objects:", len(bpy.data.objects))


if __name__ == "__main__":
    main()
