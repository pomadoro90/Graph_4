"""
Build a simplified pumpjack (oil rig) model from primitives.
Replaces the single high-poly mesh in demo.blend with a clean, low-poly
construction kit of boxes, cylinders and a few triangular prisms,
keeping the original RootNode/Camera/Light.
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

# Resolve demo.blend relative to this script, so the build works on any OS
# (Windows/macOS/Linux) regardless of Blender's current working directory.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # When run via Blender's Text editor, __file__ is not defined; fall back
    # to the directory of the currently-open .blend, then to the cwd.
    _HERE = (os.path.dirname(bpy.data.filepath) if bpy.data.filepath
             else os.getcwd())

SRC = os.path.join(_HERE)
DST = os.path.join(_HERE)

# ---------- load file, keep RootNode/Camera/Light ----------
bpy.ops.wm.open_mainfile(filepath=SRC)

# delete the old high-poly mesh
for name in list(bpy.data.objects.keys()):
    obj = bpy.data.objects[name]
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# also purge orphan meshes
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

root = bpy.data.objects.get("RootNode")
if root is None:
    root = bpy.data.objects.new("RootNode", None)
    bpy.context.collection.objects.link(root)

# ---------- materials ----------
def make_mat(name, rgba, metallic=0.6, roughness=0.45):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
    return m

MAT_BODY   = make_mat("Body",   (0.12, 0.14, 0.18, 1.0), 0.8, 0.35)  # dark blue-gray
MAT_ACCENT = make_mat("Accent", (0.95, 0.42, 0.08, 1.0), 0.3, 0.55)  # orange
MAT_DARK   = make_mat("Dark",   (0.04, 0.04, 0.05, 1.0), 0.9, 0.3)   # near-black

# ---------- helpers ----------
def new_mesh_obj(name, verts, faces, material=None, parent=None,
                 location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    if material is not None:
        me.materials.append(material)
    if parent is not None:
        obj.parent = parent
    return obj

def box_verts(sx, sy, sz):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
         (-hx, -hy,  hz), (hx, -hy,  hz), (hx, hy,  hz), (-hx, hy,  hz)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f

def add_box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, parent=None):
    v, f = box_verts(*size)
    return new_mesh_obj(name, v, f, material=mat, parent=parent,
                        location=loc, rotation=rot)

def cyl_verts(radius, depth, segments=24, axis='Z'):
    hz = depth / 2
    verts = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        x, y = radius * math.cos(a), radius * math.sin(a)
        if axis == 'Z':
            verts.append((x, y, -hz))
        elif axis == 'Y':
            verts.append((x, -hz, y))
        else:  # X
            verts.append((-hz, x, y))
    for i in range(segments):
        a = 2 * math.pi * i / segments
        x, y = radius * math.cos(a), radius * math.sin(a)
        if axis == 'Z':
            verts.append((x, y, hz))
        elif axis == 'Y':
            verts.append((x, hz, y))
        else:
            verts.append((hz, x, y))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, j + segments, i + segments))
    faces.append(tuple(range(segments)))
    faces.append(tuple(range(2 * segments - 1, segments - 1, -1)))
    return verts, faces

def add_cylinder(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0),
                 segments=20, axis='Z', mat=None, parent=None):
    v, f = cyl_verts(radius, depth, segments=segments, axis=axis)
    return new_mesh_obj(name, v, f, material=mat, parent=parent,
                        location=loc, rotation=rot)

def add_tri_prism(name, width, depth, height, loc=(0, 0, 0), rot=(0, 0, 0),
                  mat=None, parent=None):
    # triangular prism, apex on +Z, base on -Z, extruded along Y
    hw, hd, hh = width / 2, depth / 2, height / 2
    verts = [(-hw, -hd, -hh), (hw, -hd, -hh), (0, -hd, hh),
             (-hw,  hd, -hh), (hw,  hd, -hh), (0,  hd, hh)]
    faces = [(0, 1, 2), (5, 4, 3),
             (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    return new_mesh_obj(name, verts, faces, material=mat, parent=parent,
                        location=loc, rotation=rot)


# ===================================================================
#  Pumpjack layout
#  Axes:  +Z up,  +Y = rear (crank/motor),  -Y = front (horse head)
#  All numbers are pre-scale; RootNode still carries scale=100 if set.
# ===================================================================

# concrete pad / skid
add_box("Pad",  (5.0, 8.5, 0.30), loc=(0, 0, 0.15), mat=MAT_DARK, parent=root)
add_box("Skid", (3.6, 7.6, 0.45), loc=(0, -0.3, 0.52), mat=MAT_BODY, parent=root)

# ---------- Samson post (A-frame) : four angled legs forming pyramid ----------
LEG_BASE_HALF_X = 1.55   # half-width at the bottom
LEG_BASE_HALF_Y = 1.3    # half-depth at the bottom
LEG_TOP_Z       = 5.8    # pivot height
LEG_BOT_Z       = 0.75
LEG_THK         = 0.18

def slanted_leg(name, x0, y0, x1, y1, thickness=LEG_THK, mat=MAT_BODY):
    dx, dy, dz = x1 - x0, y1 - y0, LEG_TOP_Z - LEG_BOT_Z
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    mx, my, mz = (x0 + x1) / 2, (y0 + y1) / 2, (LEG_BOT_Z + LEG_TOP_Z) / 2
    # rotate a box of size (thk, thk, length) to align +Z with leg direction
    # compute Euler: first rotate around X so +Z points to projected direction
    ang_y = math.atan2(dx, dz)       # rotation around Y tilts X/Z
    proj_xz = math.sqrt(dx * dx + dz * dz)
    ang_x = -math.atan2(dy, proj_xz) # rotation around X tilts into Y
    obj = add_box(name, (thickness, thickness, length),
                  loc=(mx, my, mz), rot=(ang_x, ang_y, 0), mat=mat, parent=root)
    return obj

def leg_xy_at_z(z):
    """Centre-line X/Y half-extents of a leg at height z (interpolated between
    the base (half_x, half_y) and the apex (0,0) at LEG_TOP_Z)."""
    t = (z - LEG_BOT_Z) / (LEG_TOP_Z - LEG_BOT_Z)
    t = max(0.0, min(1.0, t))
    return LEG_BASE_HALF_X * (1 - t), LEG_BASE_HALF_Y * (1 - t)

# front pair and rear pair of the A-frame
slanted_leg("A_frame_FL", -LEG_BASE_HALF_X, -LEG_BASE_HALF_Y, 0.0, 0.0)
slanted_leg("A_frame_FR",  LEG_BASE_HALF_X, -LEG_BASE_HALF_Y, 0.0, 0.0)
slanted_leg("A_frame_RL", -LEG_BASE_HALF_X,  LEG_BASE_HALF_Y, 0.0, 0.0)
slanted_leg("A_frame_RR",  LEG_BASE_HALF_X,  LEG_BASE_HALF_Y, 0.0, 0.0)

# Cross-braces at mid-height — length equals the centre-to-centre distance
# between legs at that Z, so the braces sit flush between the legs and do
# not poke outside the A-frame footprint.
CROSS_Z = 2.6
_cx, _cy = leg_xy_at_z(CROSS_Z)
add_box("A_cross_front",  (2 * _cx, 0.12, 0.12),
        loc=(0, -_cy, CROSS_Z), mat=MAT_BODY, parent=root)
add_box("A_cross_rear",   (2 * _cx, 0.12, 0.12),
        loc=(0,  _cy, CROSS_Z), mat=MAT_BODY, parent=root)
add_box("A_cross_side_L", (0.12, 2 * _cy, 0.12),
        loc=(-_cx, 0, CROSS_Z), mat=MAT_BODY, parent=root)
add_box("A_cross_side_R", (0.12, 2 * _cy, 0.12),
        loc=( _cx, 0, CROSS_Z), mat=MAT_BODY, parent=root)

# pivot/saddle bearing block on top of A-frame
add_box("Saddle", (1.2, 1.4, 0.45), loc=(0, 0, LEG_TOP_Z + 0.0), mat=MAT_BODY, parent=root)
add_cylinder("Pivot", radius=0.18, depth=1.6,
             loc=(0, 0, LEG_TOP_Z + 0.15), rot=(math.pi / 2, 0, 0),
             axis='Z', mat=MAT_DARK, parent=root)

# ---------- Walking beam (balancer) ----------
# The beam is a straight structural H-profile in cross-section: a wide top
# flange, a wide bottom flange, and a thin vertical web connecting them
# (the letter "H" when viewed along the beam axis from the end).
BEAM_LEN      = 9.5
BEAM_Z        = LEG_TOP_Z + 0.50
BEAM_Y0       = -1.4          # shift forward so the head overhangs wellhead
BEAM_WIDTH    = 0.70          # flange width along X (the H's horizontal bars)
BEAM_HEIGHT   = 0.70          # overall beam height along Z
FLANGE_THK    = 0.12          # flange thickness along Z
WEB_THK       = 0.14          # web thickness along X (the H's vertical bar)

# Top flange (wide horizontal slab)
add_box("Beam_TopFlange", (BEAM_WIDTH, BEAM_LEN, FLANGE_THK),
        loc=(0, BEAM_Y0, BEAM_Z + (BEAM_HEIGHT - FLANGE_THK) / 2),
        mat=MAT_BODY, parent=root)
# Bottom flange (wide horizontal slab)
add_box("Beam_BotFlange", (BEAM_WIDTH, BEAM_LEN, FLANGE_THK),
        loc=(0, BEAM_Y0, BEAM_Z - (BEAM_HEIGHT - FLANGE_THK) / 2),
        mat=MAT_BODY, parent=root)
# Web (thin vertical plate connecting the two flanges)
add_box("Beam_Web", (WEB_THK, BEAM_LEN, BEAM_HEIGHT - 2 * FLANGE_THK),
        loc=(0, BEAM_Y0, BEAM_Z),
        mat=MAT_BODY, parent=root)

# ---------- Horse head (головка балансира, item #3 on the drawing) ----------
# Composite silhouette: a trapezoid bolted to the front end of the beam,
# plus a circular segment (arc pulled by a chord) that forms the curved
# front profile. Exactly the shape described on the engineering drawing
# ("одна сторона — дуга, стянутая хордой + трапеция").
HEAD_Y_BEAM      = BEAM_Y0 - BEAM_LEN / 2      # back of head = front of beam
HEAD_TRAP_LEN    = 0.75                        # trapezoid length along -Y
HEAD_Y_CHORD     = HEAD_Y_BEAM - HEAD_TRAP_LEN # chord position (front of trap)
HEAD_Z_TOP       = BEAM_Z + 0.80               # flat top of the head
HEAD_Z_BOT_BACK  = BEAM_Z - 0.35               # bottom-back (at beam's bottom flange)
HEAD_Z_CHORD_BOT = BEAM_Z - 1.20               # chord-bottom (cable attaches here)
HEAD_SAGITTA     = 0.75                        # arc depth forward of chord
HEAD_THICKNESS   = 0.22                        # head thickness along X

def _extrude_silhouette(name, sil_loop, thickness, material):
    """Extrude a closed 2D loop of (Y,Z) points along X into a prism."""
    n = len(sil_loop)
    verts = [(-thickness / 2, y, z) for (y, z) in sil_loop] + \
            [( thickness / 2, y, z) for (y, z) in sil_loop]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    new_mesh_obj(name, verts, faces, material=material, parent=root)

def _arc_samples(chord_half_v, sagitta, n_arc):
    """Sample a true circular arc passing through (0, ±chord_half_v) in a
    local (u, v) frame and bulging to (+sagitta, 0). Returns a list of
    (u, v) going from the v=-chord_half_v endpoint, through the +u peak,
    to the v=+chord_half_v endpoint."""
    uc = (sagitta ** 2 - chord_half_v ** 2) / (2 * sagitta)
    r_seg = sagitta - uc
    # Angle at the lower endpoint: vector from (uc,0) to (0,-chord_half_v)
    # is (-uc, -chord_half_v).
    theta_bot = math.atan2(-chord_half_v, -uc)
    theta_top = -theta_bot   # symmetric around the +u axis (θ=0)
    out = []
    for k in range(n_arc + 1):
        theta = theta_bot + (theta_top - theta_bot) * k / n_arc
        u = uc + r_seg * math.cos(theta)
        v = 0 + r_seg * math.sin(theta)
        out.append((u, v))
    return out, r_seg, uc

def horse_head():
    chord_half_v = (HEAD_Z_TOP - HEAD_Z_CHORD_BOT) / 2
    chord_mid_z  = (HEAD_Z_TOP + HEAD_Z_CHORD_BOT) / 2
    n_arc = 16

    # Arc samples in local (u,v) where +u points in -Y direction (forward)
    # and +v points in +Z direction (up). Arc goes from chord-bot to chord-top.
    arc_uv, r_seg, uc = _arc_samples(chord_half_v, HEAD_SAGITTA, n_arc)

    def _uv_to_yz(u, v):
        return (HEAD_Y_CHORD - u, chord_mid_z + v)

    arc_yz = [_uv_to_yz(u, v) for (u, v) in arc_uv]

    # Silhouette loop, clockwise in (Y,Z):
    #   back-top → back-bot → slanted bottom → chord-bot → arc → chord-top → top edge → back-top
    sil = [
        (HEAD_Y_BEAM,  HEAD_Z_TOP),       # back-top (at beam)
        (HEAD_Y_BEAM,  HEAD_Z_BOT_BACK),  # back-bot
        arc_yz[0],                        # chord-bot (start of arc)
    ]
    sil.extend(arc_yz[1:-1])              # arc interior points
    sil.append(arc_yz[-1])                # chord-top (end of arc)
    # top edge closes implicitly back to the first vertex

    _extrude_silhouette("HorseHead", sil, HEAD_THICKNESS, MAT_BODY)

    # Orange rim: thin ribbon along the arc only (the curved front edge).
    rim_offset = 0.15
    rim_inner = arc_yz
    rim_outer = []
    # Same arc but with an outward-offset radius.
    for k in range(n_arc + 1):
        theta_bot = math.atan2(-chord_half_v, -uc)
        theta_top = -theta_bot
        theta = theta_bot + (theta_top - theta_bot) * k / n_arc
        u = uc + (r_seg + rim_offset) * math.cos(theta)
        v = 0 + (r_seg + rim_offset) * math.sin(theta)
        rim_outer.append(_uv_to_yz(u, v))
    rim_loop = rim_inner + list(reversed(rim_outer))
    _extrude_silhouette("HorseHead_Rim", rim_loop,
                        HEAD_THICKNESS + 0.04, MAT_ACCENT)

horse_head()

# ---------- Bridle cable + polished rod + wellhead (cylinders) ----------
# Single central cable ("подвеска сальникового штока", item #12 on the
# reference drawing) hanging from the head's chin (= chord-bottom of the
# horse head's circular segment) straight down to the carrier bar.
CABLE_TOP_Z = HEAD_Z_CHORD_BOT
CABLE_BOT_Z = 0.90
CABLE_Y     = HEAD_Y_CHORD
cable_len   = CABLE_TOP_Z - CABLE_BOT_Z
add_cylinder("Bridle", 0.05, cable_len,
             loc=(0.0, CABLE_Y, (CABLE_TOP_Z + CABLE_BOT_Z) / 2),
             mat=MAT_DARK, parent=root)
# carrier bar
add_box("CarrierBar", (0.9, 0.12, 0.10), loc=(0, CABLE_Y, CABLE_BOT_Z),
        mat=MAT_DARK, parent=root)
# polished rod (cylinder) going down into the wellhead
add_cylinder("PolishedRod", 0.06, CABLE_BOT_Z - 0.05,
             loc=(0, CABLE_Y, CABLE_BOT_Z / 2),
             mat=MAT_DARK, parent=root)
# wellhead / stuffing box (cylinder) — "связь со скважиной"
add_cylinder("Wellhead_Body", 0.28, 0.90,
             loc=(0, CABLE_Y, 0.45), mat=MAT_BODY, parent=root)
add_cylinder("Wellhead_Flange", 0.36, 0.12,
             loc=(0, CABLE_Y, 0.90), mat=MAT_ACCENT, parent=root)
add_cylinder("Wellhead_Casing", 0.22, 0.40,
             loc=(0, CABLE_Y, 0.15), mat=MAT_DARK, parent=root)

# ---------- Crank shaft, crank arms, counterweights, pitman ----------
# The crankshaft runs horizontally across the machine (along X), behind the
# A-frame.  Two crank arms (rotating slabs) hang off each end of the shaft;
# a big orange counterweight disc is bolted to each arm, and the pitman
# arms connect the rear of the walking beam down to the "crank pin" — the
# pivot at the far end of the crank arm.
BEAM_REAR_Y   = BEAM_Y0 + BEAM_LEN / 2 - 0.3
CRANK_Y       = BEAM_REAR_Y + 1.1
CRANK_Z       = 2.0
# Crank arm length picked so the four-bar linkage
# (crank – pitman – rocker – ground) satisfies the Grashof condition
# s + l < p + q with the crank being the shortest link.  That is the
# *only* proportion that lets the crank rotate continuously (full 360°)
# while the walking beam rocks as a bounded swing — which is exactly
# the real-world pumpjack kinematics the user asked for.  Values in the
# original demo gave s+l = 7.58 > p+q = 5.82, i.e. a non-Grashof
# linkage that CANNOT close for all crank angles, so any attempt to
# drive it by a full-revolution crank was bound to freeze or pop.
CRANK_ARM_LEN = 0.55
CRANK_ANG     = math.radians(35)       # crank angle (mid-stroke pose)
CRANK_HALF_X  = 0.95                   # x-offset of each crank arm from centre
CW_THK        = 0.22                   # counterweight thickness (along X)
# The counterweight is a single circular segment — the geometrical
# figure bounded by a straight chord and a circular arc (item #10 on
# the drawing, interpreted as a "дуга окружности, стянутая хордой").
# The chord sits at the crank pin (the outer end of the arm),
# perpendicular to the arm's radial direction; the arc bulges CW_SAGITTA
# further radially outward.  No disc, no hub — just one clean segment.
CW_CHORD_HALF = 0.60                   # chord half-length (along tangent)
CW_SAGITTA    = 0.70                   # arc bulge past chord (along radial)

# Crank pin position (end of the crank arm that drives the pitman).
# In the machine's YZ side view, the pin sits at distance CRANK_ARM_LEN
# from the shaft, at angle CRANK_ANG above the +Y direction (tilted toward
# the beam), so the pitman lands cleanly behind the beam.
pin_dy =  math.cos(CRANK_ANG) * CRANK_ARM_LEN
pin_dz =  math.sin(CRANK_ANG) * CRANK_ARM_LEN
PIN_Y  = CRANK_Y - pin_dy              # pin is on the beam-side of the shaft
PIN_Z  = CRANK_Z + pin_dz

# Crank shaft (long cylinder across X)
add_cylinder("CrankShaft", 0.12, 2.3,
             loc=(0, CRANK_Y, CRANK_Z), rot=(0, math.pi / 2, 0),
             axis='Z', mat=MAT_DARK, parent=root)

def _segment_silhouette_uv(chord_half, sagitta, n_arc=24):
    """Closed (u, v) outline of a circular segment — the figure bounded
    by the chord between (0, -chord_half) and (0, +chord_half) and the
    circular arc through (sagitta, 0).  Points are returned in
    clockwise order: upper chord endpoint → arc (through the peak) →
    lower chord endpoint.  The chord itself closes the polygon back to
    the first point implicitly."""
    # Arc's parent circle passes through (0, ±chord_half) and (sagitta, 0).
    c      = (sagitta * sagitta - chord_half * chord_half) / (2 * sagitta)
    r_arc  = sagitta - c
    arc_cu = c                                  # arc centre along u
    theta_p1 = math.atan2( chord_half, -c)      # upper chord endpoint
    theta_p2 = -theta_p1                        # lower chord endpoint

    out = []
    for k in range(n_arc + 1):
        t = k / n_arc
        theta = theta_p1 + (theta_p2 - theta_p1) * t
        u = arc_cu + r_arc * math.cos(theta)
        v = r_arc * math.sin(theta)
        out.append((u, v))
    return out


def _crank_assembly(side, x_off):
    # Crank arm: an orange slab from the shaft out to the crank pin.
    arm_mid = (x_off,
               (CRANK_Y + PIN_Y) / 2,
               (CRANK_Z + PIN_Z) / 2)
    ang_x = math.atan2(pin_dy, pin_dz)
    add_box(f"CrankArm_{side}", (0.20, 0.45, CRANK_ARM_LEN + 0.25),
            loc=arm_mid, rot=(ang_x, 0, 0),
            mat=MAT_ACCENT, parent=root)

    # ------------------------------------------------------------------
    # Counterweight (item #10 on the drawing) — one circular segment
    # bolted to the outer end of the crank arm.  The chord sits at the
    # pin, perpendicular to the arm; the arc bulges past the pin along
    # the arm's radial direction.  Single extruded prism, so there are
    # no coplanar / tangent faces to cause Z-fighting with the disc
    # (there is no disc anymore).
    # ------------------------------------------------------------------
    # Counterweight sits outboard of the crank arm so the meshes do not
    # intersect (arm half-thickness + segment half-thickness + clearance).
    cw_off = 0.10 + CW_THK / 2 + 0.05
    cw_x   = x_off + (cw_off if x_off > 0 else -cw_off)

    # Local radial (from crank shaft toward the pin) and its 90° tangent.
    radial_y = -pin_dy / CRANK_ARM_LEN
    radial_z =  pin_dz / CRANK_ARM_LEN
    tang_y   = -radial_z
    tang_z   =  radial_y

    # Chord midpoint = the crank pin.  Arc bulges past the pin.
    cw_y = PIN_Y
    cw_z = PIN_Z

    sil_uv = _segment_silhouette_uv(CW_CHORD_HALF, CW_SAGITTA)
    sil_yz = [
        (cw_y + u * radial_y + v * tang_y,
         cw_z + u * radial_z + v * tang_z)
        for (u, v) in sil_uv
    ]
    n = len(sil_yz)
    verts = [(cw_x - CW_THK / 2, y, z) for (y, z) in sil_yz] + \
            [(cw_x + CW_THK / 2, y, z) for (y, z) in sil_yz]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    new_mesh_obj(f"Counterweight_{side}", verts, faces,
                 material=MAT_ACCENT, parent=root)

    # small crank pin stub sticking outboard of the arm end
    add_cylinder(f"CrankPin_{side}", 0.09, 0.35,
                 loc=(cw_x, PIN_Y, PIN_Z),
                 rot=(0, math.pi / 2, 0), axis='Z',
                 mat=MAT_DARK, parent=root)

_crank_assembly("L", -CRANK_HALF_X)
_crank_assembly("R",  CRANK_HALF_X)

# Pitman arms — connect the rear of the walking beam down to the crank pin.
# Pitman tops sit just below the beam's bottom flange (Z = 5.95) so a
# transverse wrist pin connecting both pitmans can live clear of the beam.
PIT_TOP_Z       = BEAM_Z - BEAM_HEIGHT / 2 - 0.15   # 5.80
PIT_X_HALF      = CRANK_HALF_X + 0.18 + 0.05        # ±1.18 (unchanged)
WRIST_PIN_R     = 0.08
def pitman(name, x_off):
    top = (x_off, BEAM_REAR_Y, PIT_TOP_Z)
    bot = (x_off, PIN_Y,       PIN_Z)
    mx  = (top[0] + bot[0]) / 2
    my  = (top[1] + bot[1]) / 2
    mz  = (top[2] + bot[2]) / 2
    dy  = bot[1] - top[1]
    dz  = bot[2] - top[2]
    length = math.sqrt(dy * dy + dz * dz)
    # A box of size (..., ..., length) along +Z — rotation around X that maps
    # (0,0,+1) → (0, dy, dz)/length has sin(a) = -dy/length.
    ang_x = math.atan2(-dy, dz)
    add_box(name, (0.10, 0.12, length + 0.2),
            loc=(mx, my, mz), rot=(ang_x, 0, 0),
            mat=MAT_BODY, parent=root)

pitman("Pitman_L", -PIT_X_HALF)
pitman("Pitman_R",  PIT_X_HALF)

# Transverse wrist pin connecting both pitman tops to the walking beam.
# Single cylinder along X at the pitman-top height, spanning the full
# width between pitmans (plus 0.15 overhang on each side).  The pin
# hangs just below the beam's bottom flange (0.07 clearance) so it does
# not pierce the beam.  A small dark hanger plate ties it up to the
# flange so the pin visibly anchors to the beam instead of floating.
_pin_len = 2.0 * PIT_X_HALF + 0.30
add_cylinder("WristPin", WRIST_PIN_R, _pin_len,
             loc=(0, BEAM_REAR_Y, PIT_TOP_Z),
             rot=(0, math.pi / 2, 0), axis='Z',
             mat=MAT_DARK, parent=root)
# Hanger bracket: short vertical box from just above the pin's top rim
# up into the bottom flange of the beam (a tiny overlap with the flange
# so no two faces are coplanar — no Z-fighting at the joint).
_hanger_bot_z = PIT_TOP_Z + WRIST_PIN_R                 # 5.88
_hanger_top_z = BEAM_Z - BEAM_HEIGHT / 2 + 0.04         # 5.99, 0.04 inside flange
add_box("WristPin_Hanger",
        (0.18, 0.22, _hanger_top_z - _hanger_bot_z),
        loc=(0, BEAM_REAR_Y, (_hanger_top_z + _hanger_bot_z) / 2),
        mat=MAT_DARK, parent=root)

# ---------- Gearbox + prime mover + belt guard at the back ----------
# Gearbox sits directly under the crankshaft; its input sheave is on the
# side of the gearbox, driven by V-belts coming up from the motor pulley.
GEARBOX_Y = CRANK_Y + 0.15
add_box("Gearbox", (1.7, 1.3, 1.35),
        loc=(0, GEARBOX_Y, 1.10), mat=MAT_BODY, parent=root)
# Gearbox_Top sits on top of the gearbox.  Centre it so its bottom
# face is a little INSIDE the gearbox volume (Z = 1.81 → bottom 1.75,
# gearbox top 1.775): embedding it avoids the coplanar-face Z-fighting
# that a flush-stacked cap produces.  The top face of Gearbox_Top at
# Z = 1.87 and the walls of the gearbox at Z ≤ 1.775 never share a
# plane, so the render is clean.
add_box("Gearbox_Top", (1.8, 1.4, 0.12),
        loc=(0, GEARBOX_Y, 1.81), mat=MAT_ACCENT, parent=root)

# Large input sheave (flywheel-style pulley) on the side of the gearbox.
# It's a big orange disc with a dark hub and four visible spokes.
SHEAVE_X      = 0.95                 # outboard side of the gearbox
SHEAVE_Y      = GEARBOX_Y
SHEAVE_Z      = 1.10
SHEAVE_RADIUS = 0.70
SHEAVE_THK    = 0.14

add_cylinder("Sheave_Rim", SHEAVE_RADIUS, SHEAVE_THK,
             loc=(SHEAVE_X, SHEAVE_Y, SHEAVE_Z),
             rot=(0, math.pi / 2, 0), axis='Z',
             mat=MAT_ACCENT, parent=root)
add_cylinder("Sheave_Hub", 0.16, SHEAVE_THK + 0.08,
             loc=(SHEAVE_X, SHEAVE_Y, SHEAVE_Z),
             rot=(0, math.pi / 2, 0), axis='Z',
             mat=MAT_DARK, parent=root)
# four spokes (thin slabs running through the hub in the YZ plane)
for k in range(4):
    ang = k * math.pi / 4
    add_box(f"Sheave_Spoke_{k}",
            (SHEAVE_THK * 0.6, 2 * SHEAVE_RADIUS * 0.92, 0.09),
            loc=(SHEAVE_X, SHEAVE_Y, SHEAVE_Z),
            rot=(ang, 0, 0), mat=MAT_ACCENT, parent=root)

# Motor block (prime mover) on its own skid, offset outboard from the sheave.
MOTOR_X        = SHEAVE_X + 0.15
MOTOR_Y        = GEARBOX_Y + 2.0
MOTOR_Z        = 0.85
MOTOR_THK_Y    = 1.6                                # motor depth along Y
PULLEY_RADIUS  = 0.28
# Pulley sits on the motor shaft, in front of the motor.  The offset
# has to clear both the pulley rim AND the belt guard's outer arc
# from the motor body.  Guard radius at the pulley is 0.36, motor
# half-thickness is 0.80, plus a small margin → offset ≈ 1.25.  The
# belt guard uses the same constant so both meshes agree on where
# the pulley centre is.
PULLEY_Y_OFF   = 1.25
PULLEY_Y       = MOTOR_Y - PULLEY_Y_OFF
PULLEY_Z       = SHEAVE_Z - 0.25

add_box("MotorSkid", (1.4, 1.9, 0.18),
        loc=(MOTOR_X, MOTOR_Y, 0.30), mat=MAT_DARK, parent=root)
add_box("Motor", (1.1, MOTOR_THK_Y, 1.0),
        loc=(MOTOR_X, MOTOR_Y, MOTOR_Z + 0.10),
        mat=MAT_BODY, parent=root)
# motor pulley (small dark cylinder on the motor shaft, aligned with sheave)
add_cylinder("MotorPulley", PULLEY_RADIUS, 0.20,
             loc=(SHEAVE_X, PULLEY_Y, PULLEY_Z),
             rot=(0, math.pi / 2, 0), axis='Z',
             mat=MAT_DARK, parent=root)
# Visible motor shaft between the motor's inboard face and the pulley
# (previously the pulley was flush against the motor, which caused the
# pulley rim to embed inside the motor body).
_motor_inner_y = MOTOR_Y - MOTOR_THK_Y / 2
_shaft_len     = _motor_inner_y - PULLEY_Y
add_cylinder("MotorShaft", 0.045, _shaft_len,
             loc=(SHEAVE_X, (PULLEY_Y + _motor_inner_y) / 2, PULLEY_Z),
             axis='Y', mat=MAT_DARK, parent=root)

# Belt guard — the curved orange "fin" cover that shrouds the V-belts
# between the motor pulley and the gearbox sheave.  Built as the convex
# hull of the two (inflated) pulley circles, extruded thin along X.
def _belt_guard():
    p1_y, p1_z = SHEAVE_Y, SHEAVE_Z                                  # sheave centre
    p2_y, p2_z = PULLEY_Y, PULLEY_Z                                  # motor pulley centre
    r1 = SHEAVE_RADIUS + 0.12
    r2 = 0.36

    # Centre-line and external-tangent geometry.  The convex hull of
    # two circles is bounded by each circle's FAR arc (away from the
    # other circle) plus the two common external tangent lines.
    # Tangent-point normals make angle β with the centre-line where
    # cos(β) = (r1 − r2) / L.
    dy, dz    = p2_y - p1_y, p2_z - p1_z
    L_centres = math.hypot(dy, dz)
    base_ang  = math.atan2(dz, dy)
    cos_b     = (r1 - r2) / L_centres
    sin_b     = math.sqrt(max(0.0, 1.0 - cos_b * cos_b))
    beta      = math.atan2(sin_b, cos_b)

    loop = []
    # Sheave arc: from upper tangent point (angle base_ang + β) CCW
    # through the far side (angle base_ang + π) to the lower tangent
    # point (angle base_ang − β, reached by sweeping 2π − 2β).
    n1 = 24
    sweep1 = 2.0 * math.pi - 2.0 * beta
    for k in range(n1 + 1):
        t = k / n1
        a = (base_ang + beta) + t * sweep1
        loop.append((p1_y + r1 * math.cos(a), p1_z + r1 * math.sin(a)))
    # Motor-pulley arc: from lower tangent point (angle base_ang − β)
    # CCW through its far side (angle base_ang, which points AWAY from
    # the sheave from the pulley's local frame) to the upper tangent
    # point (angle base_ang + β), sweeping only 2β.
    n2 = 12
    sweep2 = 2.0 * beta
    for k in range(n2 + 1):
        t = k / n2
        a = (base_ang - beta) + t * sweep2
        loop.append((p2_y + r2 * math.cos(a), p2_z + r2 * math.sin(a)))
    # The two straight external-tangent edges close the loop implicitly
    # (last sheave point → first pulley point, last pulley point → first
    # sheave point).

    # Extrude along X, sitting just outboard of the sheave so the guard
    # covers the belts from view.
    thk = 0.08
    offset_x = SHEAVE_X + SHEAVE_THK / 2 + thk / 2 + 0.02
    n = len(loop)
    verts = [(offset_x - thk / 2, y, z) for (y, z) in loop] + \
            [(offset_x + thk / 2, y, z) for (y, z) in loop]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    new_mesh_obj("BeltGuard", verts, faces, material=MAT_ACCENT, parent=root)

_belt_guard()

# ---------- Ladder on the rear of the A-frame ----------
# The ladder leans against the rear face of the Samson post.  Stringers and
# rungs share the same path: both run from (LAD_BOT_Y, LAD_BOT_Z) up to
# (LAD_TOP_Y, LAD_TOP_Z) along the same line in the Y-Z plane, so rungs sit
# between the two stringers at every height.
LAD_HALF_W = 0.42            # half-distance between the two stringers (X)
LAD_BOT_Y  = 1.55            # ladder foot, behind the machine
LAD_BOT_Z  = 0.55
LAD_TOP_Y  = 0.55            # ladder top, next to the safety platform
LAD_TOP_Z  = LEG_TOP_Z - 0.35

_ldy      = LAD_TOP_Y - LAD_BOT_Y
_ldz      = LAD_TOP_Z - LAD_BOT_Z
lad_len   = math.sqrt(_ldy * _ldy + _ldz * _ldz)
# Rotation around X so a box authored along local +Z aligns with the ladder:
# a point (0,0,+L/2) maps to (0, -sin(a), cos(a)) * L/2, and we want that to
# equal (0, _ldy, _ldz) / lad_len * L/2  →  sin(a) = -_ldy / lad_len.
lad_ang   = math.atan2(-_ldy, _ldz)
lad_mid_y = (LAD_BOT_Y + LAD_TOP_Y) / 2
lad_mid_z = (LAD_BOT_Z + LAD_TOP_Z) / 2

# Two parallel stringers
for sign, name in ((-1, "Stringer_L"), (1, "Stringer_R")):
    add_box(name, (0.06, 0.06, lad_len),
            loc=(sign * LAD_HALF_W, lad_mid_y, lad_mid_z),
            rot=(lad_ang, 0, 0), mat=MAT_DARK, parent=root)

# Rungs — horizontal cross-bars spanning both stringers, positioned along
# the same tilted line the stringers follow.
n_rungs = 10
for i in range(n_rungs):
    t  = (i + 0.5) / n_rungs
    ry = LAD_BOT_Y + t * _ldy
    rz = LAD_BOT_Z + t * _ldz
    add_box(f"Rung_{i}", (2 * LAD_HALF_W + 0.04, 0.04, 0.04),
            loc=(0.0, ry, rz), mat=MAT_DARK, parent=root)

# ---------- safety platform at the pivot ----------
add_box("Platform", (1.6, 0.6, 0.05),
        loc=(0, 0.65, LEG_TOP_Z - 0.25), mat=MAT_DARK, parent=root)
add_box("Rail_Back", (1.6, 0.04, 0.6),
        loc=(0, 0.93, LEG_TOP_Z + 0.05), mat=MAT_DARK, parent=root)

# ---------- save ----------
# Make sure RootNode keeps scale=100 so the scene framing matches the old file
root.location = (0, 0, 0)
root.rotation_euler = (0, 0, 0)
root.scale = (1.0, 1.0, 1.0)   # model is authored in ~real-world meters now


# ============================================================
#  Animation rig — armature + keyframed four-bar-linkage motion
# ============================================================
#
#   crank-shaft ←—— r1 ——→ beam-saddle       (ground link, fixed)
#        |                         \
#        r2 = crank arm             r4 = rocker (rear half of walking beam)
#        |                           \
#        pin ←—— r3 = pitman ——→ wrist-pin  (on the rear of the beam)
#
# Every joint lies in one YZ plane (the rig is mirror-symmetric in X),
# and every joint is a pure rotation about world-X.
#
# Fixed pivots of the real machine:
#   * crankshaft axis at (0, CRANK_Y, CRANK_Z)   — counterweights orbit
#   * beam saddle      at (0, 0, LEG_TOP_Z+0.15) — balancer pivots (качели)
#   * wellhead         at (0, CABLE_Y, 0.45)     — cable enters the ground
#
# All rotating / swinging parts are rigid: crank arms, counterweights,
# walking beam (incl. horse head), pitman arms and wrist pin keep their
# authored shape and size.  The counterweights sweep a full revolution
# around the crank-shaft axis.  The walking beam rocks as a swing around
# the saddle (classic "качели" motion).  The only part that changes
# length is the bridle cable ("подвеска сальникового штока") — it
# stretches between the moving horse-head chin and the fixed wellhead,
# exactly reproducing the real-world polished-rod stroke going down into
# the ground and back up.
#
# Rather than fight Blender's IK solver with a 4-bar linkage (IK with
# head_tail=1 across a central target bone and off-axis pitmans is
# ambiguous and flips "assembly modes"), we SOLVE the kinematics in
# closed form below and bake every bone's rotation directly into
# keyframes.  The result is a perfectly synchronised, deterministic
# loop — identical geometry every cycle, no solver drift.

BEAM_PIVOT_Z = LEG_TOP_Z + 0.15
WELLHEAD_Z   = 0.45

# ---------- four-bar linkage parameters (YZ plane) ----------
_SHAFT_Y,  _SHAFT_Z  = CRANK_Y, CRANK_Z
_SADDLE_Y, _SADDLE_Z = 0.0,     BEAM_PIVOT_Z

_DY_PIN0 = PIN_Y       - _SHAFT_Y        # rest crank-pin offset (Y)
_DZ_PIN0 = PIN_Z       - _SHAFT_Z        # rest crank-pin offset (Z)
_DY_WR0  = BEAM_REAR_Y - _SADDLE_Y       # rest wrist-pin offset (Y)
_DZ_WR0  = PIT_TOP_Z   - _SADDLE_Z       # rest wrist-pin offset (Z)

_R_CRANK  = math.hypot(_DY_PIN0, _DZ_PIN0)      # r2
_R_ROCKER = math.hypot(_DY_WR0,  _DZ_WR0)       # r4
_R_PITMAN = math.hypot(PIN_Y - BEAM_REAR_Y,     # r3 (constant link length)
                       PIN_Z - PIT_TOP_Z)

# Base angles at rest (measured in the saddle- / wrist-pin frames of the
# YZ plane, same sign convention as Blender's rotation_euler.x around a
# roll=0 bone lying in that plane).
_REST_WRIST  = math.atan2(_DZ_WR0,  _DY_WR0)            # saddle  → wrist-pin
_REST_PITMAN = math.atan2(PIN_Z - PIT_TOP_Z,            # wrist   → crank-pin
                          PIN_Y - BEAM_REAR_Y)

def _wrap(a):
    """Canonical angle in (−π, π]."""
    return ((a + math.pi) % (2.0 * math.pi)) - math.pi

def _solve_4bar(crank_angle):
    """Return (beam_delta, pitman_delta), both in radians relative to
    rest, that the walking beam and a pitman bone (child of the beam)
    must take so the linkage closes for the given crank rotation."""
    c, s  = math.cos(crank_angle), math.sin(crank_angle)
    # Crank pin after rotating its rest offset around world-X.
    pin_y = _SHAFT_Y + c * _DY_PIN0 - s * _DZ_PIN0
    pin_z = _SHAFT_Z + s * _DY_PIN0 + c * _DZ_PIN0

    # Distance from saddle to the (now-moved) crank pin.
    dpy = pin_y - _SADDLE_Y
    dpz = pin_z - _SADDLE_Z
    d   = math.hypot(dpy, dpz)

    # Law-of-cosines angle at the saddle between (saddle→pin) and
    # (saddle→wrist-pin).  Clamped to guard against sub-ULP overshoot
    # when the linkage passes through its extreme positions.
    cos_g = (_R_ROCKER * _R_ROCKER + d * d - _R_PITMAN * _R_PITMAN) \
            / (2.0 * _R_ROCKER * d)
    cos_g = max(-1.0, min(1.0, cos_g))
    g     = math.acos(cos_g)
    base  = math.atan2(dpz, dpy)

    # Two candidate wrist-pin angles (±g from the saddle→pin direction);
    # a real pumpjack is a Grashof four-bar, so the correct branch is
    # always whichever stays closest to the rest configuration.
    wrist_ang = min((base + g, base - g),
                    key=lambda a: abs(_wrap(a - _REST_WRIST)))
    beam_delta = _wrap(wrist_ang - _REST_WRIST)

    # Pitman direction in world YZ, then subtract the beam's rotation so
    # the pitman bone (parented to Beam) carries only the residual.
    wrist_y  = _SADDLE_Y + _R_ROCKER * math.cos(wrist_ang)
    wrist_z  = _SADDLE_Z + _R_ROCKER * math.sin(wrist_ang)
    pit_ang  = math.atan2(pin_z - wrist_z, pin_y - wrist_y)
    pit_delta = _wrap(pit_ang - _REST_PITMAN - beam_delta)
    return beam_delta, pit_delta


# ---------- empty that pins the bridle's bottom end to the ground ----------
wellhead_target = bpy.data.objects.new("WellheadTarget", None)
wellhead_target.location = (0.0, CABLE_Y, WELLHEAD_Z)
bpy.context.collection.objects.link(wellhead_target)

# ---------- armature & bones ----------
arm_data = bpy.data.armatures.new("PumpjackRig")
arm_obj  = bpy.data.objects.new("PumpjackRig", arm_data)
bpy.context.collection.objects.link(arm_obj)
for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.context.view_layer.objects.active = arm_obj
arm_obj.select_set(True)

bpy.ops.object.mode_set(mode='EDIT')
ebones = arm_data.edit_bones

# Crank — pivots around the crank-shaft axis; head at the shaft, tail at
# the crank pin.  roll=0 keeps local-X aligned with world-X, so
# rotation_euler.x spins the arms in the YZ plane.
b_crank = ebones.new("Crank")
b_crank.head = (0.0, CRANK_Y, CRANK_Z)
b_crank.tail = (0.0, PIN_Y,   PIN_Z)
b_crank.roll = 0.0

# Walking beam (балансир) — head at the saddle, tail at the rear wrist
# pin.  Rocks around its head (the saddle) like a seesaw.
b_beam = ebones.new("Beam")
b_beam.head = (0.0, 0.0,         BEAM_PIVOT_Z)
b_beam.tail = (0.0, BEAM_REAR_Y, PIT_TOP_Z)
b_beam.roll = 0.0

# Two pitman arms — parented to Beam (their heads move with the wrist
# pin as the beam swings), each tracking the crank pin on its own side.
for _side, _sign in (("L", -1), ("R", +1)):
    pb = ebones.new(f"Pitman_{_side}")
    pb.head        = (_sign * PIT_X_HALF, BEAM_REAR_Y, PIT_TOP_Z)
    pb.tail        = (_sign * PIT_X_HALF, PIN_Y,       PIN_Z)
    pb.parent      = b_beam
    pb.use_connect = False
    pb.roll        = 0.0

# Bridle cable — head on the horse-head chin (rides the beam), tail
# straight below at the wellhead.  The Stretch-To constraint wired up
# below makes it elongate / shrink as the chin moves.
b_bridle = ebones.new("Bridle")
b_bridle.head        = (0.0, CABLE_Y, CABLE_TOP_Z)
b_bridle.tail        = (0.0, CABLE_Y, CABLE_BOT_Z)
b_bridle.parent      = b_beam
b_bridle.use_connect = False
b_bridle.roll        = 0.0

bpy.ops.object.mode_set(mode='OBJECT')


# ---------- pose-mode constraints ----------
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')

# Bridle stretches between the horse-head's chin (bone head, which rides
# the walking beam) and the fixed wellhead target.  Stretch-To both aims
# the bone's Y axis at the target AND scales the bone so head-to-tail
# distance tracks the target distance exactly — the bridle mesh, bound
# to this bone via an Armature modifier, elongates on the up-stroke and
# shortens on the down-stroke.  'NO_VOLUME' prevents the radial bulging
# that Stretch-To applies by default (a real cable doesn't get thinner
# when pulled taut in this simplified model).
pb_bridle = arm_obj.pose.bones["Bridle"]
st = pb_bridle.constraints.new(type='STRETCH_TO')
st.target      = wellhead_target
st.rest_length = CABLE_TOP_Z - CABLE_BOT_Z         # == bridle mesh length
st.volume      = 'NO_VOLUME'

bpy.ops.object.mode_set(mode='OBJECT')


# ---------- parent rigid meshes to bones ----------
# Bone-parenting anchors a child at the bone's TAIL in the bone's own
# frame.  To preserve world position at rest we set
#     matrix_parent_inverse = (arm_world @ bone_rest @ T(0, L, 0))^-1
# With that inverse in place, pose rotations of the bone rotate the
# child rigidly around the bone's HEAD — i.e. the saddle for the beam,
# the crank-shaft for the crank arms, the wrist pin for the pitmans.
MESH_TO_BONE = {
    # crank-side rotating parts (orbit around the crank-shaft axis)
    "CrankArm_L":      "Crank",
    "CrankArm_R":      "Crank",
    "Counterweight_L": "Crank",
    "Counterweight_R": "Crank",
    "CrankPin_L":      "Crank",
    "CrankPin_R":      "Crank",
    # walking-beam rigid cluster (swings around the saddle pivot)
    "Beam_TopFlange":  "Beam",
    "Beam_BotFlange":  "Beam",
    "Beam_Web":        "Beam",
    "HorseHead":       "Beam",
    "HorseHead_Rim":   "Beam",
    "WristPin":        "Beam",
    "WristPin_Hanger": "Beam",
    # pitmans track their respective bones
    "Pitman_L":        "Pitman_L",
    "Pitman_R":        "Pitman_R",
}

_arm_mat = arm_obj.matrix_world.copy()
for _mesh_name, _bone_name in MESH_TO_BONE.items():
    _obj = bpy.data.objects.get(_mesh_name)
    if _obj is None:
        continue
    _bone = arm_obj.data.bones[_bone_name]
    _effective_parent = (_arm_mat
                         @ _bone.matrix_local
                         @ Matrix.Translation((0.0, _bone.length, 0.0)))
    _obj.parent                = arm_obj
    _obj.parent_type           = 'BONE'
    _obj.parent_bone           = _bone_name
    _obj.matrix_parent_inverse = _effective_parent.inverted()


# ---------- rig the Bridle mesh so it deforms with its bone ----------
# Armature modifier + a vertex group weighted 1.0 to the "Bridle" bone
# makes every vertex of the bridle cylinder follow the pose of that bone
# (including the Stretch-To scale along local Y).  The mesh is parented
# to the armature object (not to the bone) so the Armature modifier is
# the only deformer — bone-parenting on top would freeze the mesh at
# the rest tail and suppress the stretch.
_bridle = bpy.data.objects.get("Bridle")
if _bridle is not None:
    _vg = _bridle.vertex_groups.new(name="Bridle")
    _vg.add(list(range(len(_bridle.data.vertices))), 1.0, 'REPLACE')
    _mod = _bridle.modifiers.new(name="Armature", type='ARMATURE')
    _mod.object            = arm_obj
    _mod.use_vertex_groups = True
    _mw = _bridle.matrix_world.copy()
    _bridle.parent       = arm_obj
    _bridle.parent_type  = 'OBJECT'
    _bridle.matrix_world = _mw


# ---------- bake one revolution of kinematics into keyframes ----------
# Build the action and its F-curves explicitly rather than going through
# bpy.ops + keyframe_insert, which silently fails in script contexts
# where the operator poll rejects the calling context.  This approach
# is also faster and guarantees a working animation regardless of the
# editor state at run time.
FRAMES_PER_REV = 120

for _bn in ("Crank", "Beam", "Pitman_L", "Pitman_R"):
    arm_obj.pose.bones[_bn].rotation_mode = 'XYZ'

if arm_obj.animation_data is None:
    arm_obj.animation_data_create()
_action = bpy.data.actions.new("PumpjackAction")
arm_obj.animation_data.action = _action


def _add_rot_x_fcurve(bone, group):
    # Blender 4.4+ uses the "layered Action" model: F-curves live inside
    # a channelbag attached to a strip on a layer for a given slot, not
    # directly on the Action.  fcurve_ensure_for_datablock() creates all
    # of that plumbing (layer + keyframe strip + slot, bound to arm_obj)
    # the first time it is called, and returns a plain F-curve we can
    # keyframe into the usual way.  Works on both the legacy and the
    # new API without a version-gate.
    if hasattr(_action, "fcurve_ensure_for_datablock"):
        fc = _action.fcurve_ensure_for_datablock(
            datablock=arm_obj,
            data_path=f'pose.bones["{bone}"].rotation_euler',
            index=0,
            group_name=group,
        )
    else:
        fc = _action.fcurves.new(
            data_path=f'pose.bones["{bone}"].rotation_euler',
            index=0,
            action_group=group,
        )
    fc.keyframe_points.add(count=FRAMES_PER_REV + 1)
    return fc


_fc_crank = _add_rot_x_fcurve("Crank",    "Crank")
_fc_beam  = _add_rot_x_fcurve("Beam",     "Beam")
_fc_pit_l = _add_rot_x_fcurve("Pitman_L", "Pitman")
_fc_pit_r = _add_rot_x_fcurve("Pitman_R", "Pitman")

for _i in range(FRAMES_PER_REV + 1):
    _theta       = (_i / FRAMES_PER_REV) * 2.0 * math.pi
    _beam, _pit  = _solve_4bar(_theta)
    _frame       = float(_i + 1)
    for _fc, _val in ((_fc_crank, _theta),
                      (_fc_beam,  _beam),
                      (_fc_pit_l, _pit),
                      (_fc_pit_r, _pit)):      # left == right by symmetry
        _kp = _fc.keyframe_points[_i]
        _kp.co            = (_frame, _val)
        _kp.interpolation = 'LINEAR'

# Cycles modifiers so the rig keeps animating past the keyed range.
#   • Crank: REPEAT_OFFSET — angle must keep growing monotonically so
#     the counterweights continue spinning instead of snapping back.
#   • Beam / Pitman: REPEAT — they already return to their starting
#     angle after one crank revolution, so plain repetition is seamless.
for _fc in (_fc_crank, _fc_beam, _fc_pit_l, _fc_pit_r):
    _cm = _fc.modifiers.new(type='CYCLES')
    if _fc is _fc_crank:
        _cm.mode_before = 'REPEAT_OFFSET'
        _cm.mode_after  = 'REPEAT_OFFSET'
    else:
        _cm.mode_before = 'REPEAT'
        _cm.mode_after  = 'REPEAT'

bpy.context.scene.frame_start   = 1
bpy.context.scene.frame_end     = FRAMES_PER_REV
bpy.context.scene.frame_current = 1

# Poke the depsgraph so all constraints / modifiers / bone bindings are
# evaluated before the file is saved.
bpy.context.view_layer.update()

# Diagnostic so the user can confirm from the build log that the
# animation data actually made it into the scene.  Walks both the
# legacy fcurves list and the new layered-action channelbag.
def _iter_all_fcurves(action):
    if hasattr(action, "fcurves") and action.fcurves:
        yield from action.fcurves
        return
    for _lyr in action.layers:
        for _strip in _lyr.strips:
            for _cb in getattr(_strip, "channelbags", []):
                yield from _cb.fcurves

_all_fcurves = list(_iter_all_fcurves(_action))
print("Animation F-curves:", len(_all_fcurves))
for _fc_dbg in _all_fcurves:
    print(f"  {_fc_dbg.data_path}[{_fc_dbg.array_index}]: "
          f"{len(_fc_dbg.keyframe_points)} keyframes, "
          f"{len(_fc_dbg.modifiers)} modifiers")


bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
print("Saved:", DST)
print("Objects:", len(bpy.data.objects))