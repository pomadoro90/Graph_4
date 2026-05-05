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
    pts = list(points)
    for i in range(len(pts) - 1):
        cylinder_between(f"{name}_{i+1:02d}", pts[i], pts[i + 1], radius, material, vertices=24)
    # маленькие сферические муфты на узлах — визуально заменяют колена
    for i, p in enumerate(pts):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius * 1.18, location=p)
        s = bpy.context.active_object
        s.name = f"{name}_joint_{i+1:02d}"
        assign(s, material)
    if elevated:
        for i, p in enumerate(pts[1:-1], start=1):
            if p[2] > 0.7:
                add_h_support(f"{name}_support_{i:02d}", p[0], p[1], p[2] - radius - 0.08)


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
    """Упрощённая станция-качалка в стиле pump_script.py."""
    x, y, z = loc
    s = scale
    add_box(name + "_pad", (x, y, z + 0.05 * s), (4.2 * s, 6.2 * s, 0.10 * s), MATS["gravel"])
    add_box(name + "_skid", (x, y, z + 0.28 * s), (3.3 * s, 5.2 * s, 0.28 * s), MATS["steel"])
    # A-frame legs
    top = (x, y, z + 3.9 * s)
    for bx, by in [(-1.1, -0.9), (1.1, -0.9), (-1.1, 0.9), (1.1, 0.9)]:
        cylinder_between(name + "_leg", (x + bx * s, y + by * s, z + 0.45 * s), top, 0.055 * s, MATS["steel"], vertices=12)
    add_cylinder(name + "_pivot", (x, y, z + 4.0 * s), 0.11 * s, 1.25 * s, MATS["steel"], axis="X", vertices=18)
    # walking beam and horse head
    add_box(name + "_beam", (x, y - 0.45 * s, z + 4.18 * s), (0.38 * s, 5.9 * s, 0.28 * s), MATS["steel"])
    add_cone(name + "_horse_head", (x, y - 3.65 * s, z + 3.95 * s), 0.48 * s, 0.25 * s, 0.95 * s, MATS["orange"], vertices=4)
    # crank, gearbox, counterweight, motor
    add_box(name + "_gearbox", (x, y + 2.15 * s, z + 0.85 * s), (1.25 * s, 0.95 * s, 0.9 * s), MATS["steel"])
    add_cylinder(name + "_crankshaft", (x, y + 2.12 * s, z + 1.55 * s), 0.10 * s, 1.65 * s, MATS["steel"], axis="X", vertices=18)
    add_cylinder(name + "_counterweight_L", (x - 0.9 * s, y + 2.0 * s, z + 1.15 * s), 0.46 * s, 0.14 * s, MATS["orange"], axis="X", vertices=28)
    add_cylinder(name + "_counterweight_R", (x + 0.9 * s, y + 2.0 * s, z + 1.15 * s), 0.46 * s, 0.14 * s, MATS["orange"], axis="X", vertices=28)
    add_box(name + "_motor", (x + 1.25 * s, y + 3.25 * s, z + 0.75 * s), (0.85 * s, 1.15 * s, 0.72 * s), MATS["green"])
    # bridle to wellhead
    add_cylinder(name + "_bridle", (x, y - 3.65 * s, z + 2.15 * s), 0.035 * s, 3.1 * s, MATS["steel"], vertices=12)
    add_valve_tree(name + "_wellhead", (x, y - 3.65 * s, z), scale=0.7 * s)


def add_injection_well(name: str, loc: Vec3):
    x, y, z = loc
    add_pad(name + "_pad", loc, 4.0, 4.0)
    add_valve_tree(name + "_tree", (x, y, z), scale=1.05, injection=True)
    add_cylinder(name + "_filter_skid", (x + 1.15, y + 0.75, z + 0.45), 0.26, 1.4, MATS["blue"], axis="X", vertices=24)
    add_box(name + "_control_box", (x - 1.1, y + 0.6, z + 0.65), (0.8, 0.55, 1.0), MATS["building"])
    add_label("Нагнетательная\nскважина", (x, y - 2.8, z + 0.08), size=0.34)


def add_horizontal_vessel(name: str, loc: Vec3, length: float, radius: float, material):
    add_cylinder(name + "_body", loc, radius, length, material, axis="X", vertices=32)
    x, y, z = loc
    add_cylinder(name + "_left_head", (x - length / 2, y, z), radius, 0.08, material, axis="X", vertices=32)
    add_cylinder(name + "_right_head", (x + length / 2, y, z), radius, 0.08, material, axis="X", vertices=32)
    for sx in (-0.35, 0.35):
        add_box(name + f"_saddle_{sx}", (x + sx * length, y, z - radius - 0.12), (0.22, radius * 1.8, 0.22), MATS["steel"])


def add_tank(name: str, loc: Vec3, radius=1.0, height=2.0, label=""):
    x, y, z = loc
    add_cylinder(name + "_wall", (x, y, z + height / 2), radius, height, MATS["tank"], vertices=48)
    add_cone(name + "_roof", (x, y, z + height + 0.22), radius, 0.12, 0.45, MATS["tank"], vertices=48)
    add_cylinder(name + "_bund", (x, y, z + 0.04), radius + 0.35, 0.08, MATS["gravel"], vertices=48)
    if label:
        add_label(label, (x, y - radius - 0.7, z + 0.08), size=0.32)


def add_pump_block(name: str, loc: Vec3, count=3, water=False):
    x, y, z = loc
    material = MATS["blue"] if water else MATS["orange"]
    for i in range(count):
        yy = y + (i - (count - 1) / 2) * 0.9
        add_box(f"{name}_pump_{i+1}", (x, yy, z + 0.38), (1.25, 0.36, 0.42), material)
        add_cylinder(f"{name}_motor_{i+1}", (x - 0.78, yy, z + 0.38), 0.20, 0.55, MATS["green"], axis="X", vertices=20)
        add_cylinder(f"{name}_manifold_{i+1}", (x + 0.82, yy, z + 0.45), 0.08, 0.75, MATS["steel"], axis="Y", vertices=16)


def add_facility_dns(loc: Vec3):
    x, y, z = loc
    add_pad("DNS_pad", loc, 8.5, 6.5)
    add_box("DNS_control_module", (x - 2.6, y + 1.6, z + 0.55), (2.1, 1.5, 1.1), MATS["building"])
    add_horizontal_vessel("DNS_group_meter", (x - 0.3, y - 0.9, z + 1.05), 3.0, 0.48, MATS["glass"])
    add_pump_block("DNS_booster", (x + 2.35, y - 0.4, z), count=3)
    add_cylinder("DNS_flare_stack", (x + 3.6, y + 2.0, z + 2.0), 0.08, 4.0, MATS["steel"], vertices=12)
    add_cone("DNS_flare_tip", (x + 3.6, y + 2.0, z + 4.15), 0.18, 0.04, 0.3, MATS["orange"], vertices=16)
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
    add_box("KNS_operator_box", (x + 1.2, y + 1.45, z + 0.45), (1.4, 0.8, 0.9), MATS["building"])
    add_label("КНС\nкустовая насосная", (x, y - 2.7, z + 0.08), size=0.31)


def add_arrow(name: str, loc: Vec3, direction="X", material=None):
    material = material or MATS["orange"]
    x, y, z = loc
    if direction == "X":
        add_cone(name, (x, y, z), 0.22, 0.0, 0.55, material, vertices=24).rotation_euler[1] = math.radians(90)
    elif direction == "-X":
        add_cone(name, (x, y, z), 0.22, 0.0, 0.55, material, vertices=24).rotation_euler[1] = math.radians(-90)
    elif direction == "Y":
        add_cone(name, (x, y, z), 0.22, 0.0, 0.55, material, vertices=24).rotation_euler[0] = math.radians(-90)
    else:
        add_cone(name, (x, y, z), 0.22, 0.0, 0.55, material, vertices=24).rotation_euler[0] = math.radians(90)


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
        [manifold, (-10, -6, 0.9), (-9.2, -1, 1.05), (-6.8, -1, 1.05)],
        0.13,
        MATS["pipe_oil"],
        elevated=True,
    )

    # Нефтяная технологическая линия: ДНС -> УПСВ -> УПН -> экспорт
    pipe_path("DNS_to_UPSV_emulsion", [(-2.0, -1, 1.05), (1.5, -1, 1.15), (2.5, 0, 1.15)], 0.15, MATS["pipe_oil"])
    pipe_path("UPSV_to_UPN_oil", [(8.5, 0.2, 1.2), (12, 0.2, 1.2), (13.0, 0, 1.2)], 0.15, MATS["pipe_oil"])
    pipe_path("UPN_sales_oil_export", [(21.8, -1.9, 1.0), (25, -1.9, 1.0), (29, -4, 1.0)], 0.16, MATS["pipe_product"])
    add_label("товарная нефть\nна внешний\nнефтепровод", (28, -6.2, 0.08), size=0.32)

    # Вода: УПСВ/КНС -> БКНС -> нагнетательная скважина
    pipe_path("Produced_water_UPSV_to_KNS", [(7.3, 1.0, 0.85), (8, 5.5, 0.85), (8, 9.5, 0.85)], 0.11, MATS["pipe_water"])
    pipe_path("KNS_to_BKNS_water", [(5.0, 12, 0.95), (0, 12, 0.95), (-1.3, 12, 0.95)], 0.12, MATS["pipe_water"])
    pipe_path("BKNS_to_injection_well", [(-7.5, 12, 1.05), (-7.5, 15, 1.05), (-0.9, 15, 1.05)], 0.13, MATS["pipe_water"])

    # Газовая линия и факел
    pipe_path("Gas_line_DNS_UPSV", [(-3.0, 1.8, 1.9), (2.0, 2.6, 1.9), (4.5, 2.4, 1.9)], 0.07, MATS["pipe_gas"])
    pipe_path("Gas_line_UPSV_UPN", [(6.8, 2.4, 1.9), (11.5, 2.8, 1.9), (15.0, 2.0, 1.9)], 0.07, MATS["pipe_gas"])

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
