# g039 (Ghast) sprite pipeline for Blender 5.2 -- run inside Blender: exec(open(PATH).read())
# Builds scene 'g039_sprites' (ortho camera rig, lights, blade glow, shadow catcher), the actions
# g039_st / g039_mo / g039_at / g039_da on SmartRigArmature, and renders frames to render/frames/<act>/<pass>/dD_fF.png
import bpy, math, os, mathutils
from mathutils import Vector, Matrix, Quaternion
ROOT = r"C:\Users\Ivan Chan\Documents\GitHub\SGgalaxy\art3d\units\g039\render"
SCN = 'g039_sprites'; ARM = 'SmartRigArmature'; MESH = 'geometry_0'
PIVOT = Vector((0.2, -0.05, 0.0))
ELEV = 55.0
FRAMES = {'st': 12, 'mo': 12, 'at': 14, 'da': 1}
CANVAS = {'st': (179, 179), 'mo': (179, 179), 'at': (177, 178), 'da': (179, 179)}
PIV = (89, 109)
SS = 4          # supersampling: render at SS x canvas, pack_g039.py downsamples + sharpens
SCALE = 1.0     # character size vs the original sprite
OUTDIR = 'frames'
ARM_A = ['Bone_022', 'Bone_027']          # both shoulder chains (two-handed grip)
LEG_A = 'Bone_009'; LEG_B = 'Bone_014'; SHIN_A = 'Bone_008'; SHIN_B = 'Bone_013'
SPINE = 'Bone_004'; CHEST = 'Bone_002'; ROOTB = 'Bone_000'; HEAD = 'Bone_017'

def sc(): return bpy.data.scenes[SCN]
def arm(): return bpy.data.objects[ARM]

def with_scene(fn):
    def w(*a, **k):
        win = bpy.context.window_manager.windows[0]; old = win.scene
        win.scene = sc()
        try: return fn(*a, **k)
        finally: win.scene = old
    return w

# ---------------------------------------------------------------- setup
def setup():
    s = sc(); a = arm()
    # blade glow capsule along the sword bones (hand -> tip)
    g = bpy.data.objects.get('BladeGlow')
    if not g:
        import bmesh
        me = bpy.data.meshes.new('BladeGlow'); bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
        bm.to_mesh(me); bm.free()
        g = bpy.data.objects.new('BladeGlow', me); s.collection.objects.link(g)
    hand = Vector((-0.11, -0.01, 0.93)); tip = Vector((-0.68, 0.30, 1.84))
    d = (tip - hand); L = d.length; u = d.normalized()
    start = hand + u * 0.22; mid = (start + tip) / 2; half = (tip - start).length / 2
    g.parent = None
    q = Vector((0, 0, 1)).rotation_difference(u)
    g.matrix_world = Matrix.Translation(mid) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((0.15, 0.15, half + 0.10, 1))
    # parent to the sword bone keeping transform
    mw = g.matrix_world.copy(); g.parent = a; g.parent_type = 'BONE'; g.parent_bone = 'Bone_044'; g.matrix_world = mw
    m = bpy.data.materials.get('BladeGlowMat') or bpy.data.materials.new('BladeGlowMat'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.2
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1]); nt.links.new(inv.outputs[0], pw.inputs[0]); nt.links.new(pw.outputs[0], mul.inputs[0])
    em.inputs['Color'].default_value = (0.38, 0.30, 1.0, 1)
    nt.links.new(mul.outputs[0], em.inputs['Strength']); nt.links.new(em.outputs[0], o.inputs['Surface'])
    g.data.materials.clear(); g.data.materials.append(m)
    # shadow catcher plane
    p = bpy.data.objects.get('ShadowCatcher')
    if not p:
        me = bpy.data.meshes.new('ShadowCatcher')
        me.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)], [], [(0, 1, 2, 3)])
        p = bpy.data.objects.new('ShadowCatcher', me); s.collection.objects.link(p)
    p.is_shadow_catcher = True
    # shadow sun: shadow falls screen-right and away (measured on the original sts frames)
    rig = bpy.data.objects['SpriteRig']
    ld = bpy.data.lights.get('ShadowSun') or bpy.data.lights.new('ShadowSun', 'SUN'); ld.energy = 3.0; ld.angle = math.radians(2)
    sun = bpy.data.objects.get('ShadowSun') or bpy.data.objects.new('ShadowSun', ld)
    if sun.name not in s.collection.objects: s.collection.objects.link(sun)
    sun.parent = rig
    travel = Vector((0.25, 0.195, -0.8)).normalized()
    sun.rotation_euler = (-travel).to_track_quat('Z', 'Y').to_euler()
    # key light along the same direction so shading matches the shadow
    key = bpy.data.objects['SpriteKey']; key.rotation_euler = sun.rotation_euler.copy(); key.data.energy = 8.0
    bpy.data.objects['SpriteFill'].data.energy = 2.0; bpy.data.objects['SpriteRim'].data.energy = 3.0
    if bpy.data.objects.get('PivotMarker'): bpy.data.objects['PivotMarker'].hide_render = True
    for pb in a.pose.bones: pb.rotation_mode = 'QUATERNION'
    setup_shadow_proj()
    return 'ok'

SHADOW_TRAVEL = Vector((0.25, 0.195, -0.8)).normalized()     # in rig space (screen-fixed)
def setup_shadow_proj():
    """EEVEE shadow: the deformed character flattened onto z=0 along the light direction, drawn black"""
    s = sc()
    o = bpy.data.objects.get('ShadowProj')
    if not o:
        me = bpy.data.meshes.new('ShadowProj'); o = bpy.data.objects.new('ShadowProj', me); s.collection.objects.link(o)
    ng = bpy.data.node_groups.get('ShadowProjGN')
    if ng: bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new('ShadowProjGN', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; Lk = ng.links
    gi = N.new('FunctionNodeInputVector'); gi.name = 'DirVec'; go = N.new('NodeGroupOutput')
    oi = N.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value = bpy.data.objects[MESH]; oi.transform_space = 'RELATIVE'
    pos = N.new('GeometryNodeInputPosition'); sep = N.new('ShaderNodeSeparateXYZ'); sepd = N.new('ShaderNodeSeparateXYZ')
    div = N.new('ShaderNodeMath'); div.operation = 'DIVIDE'
    sc_ = N.new('ShaderNodeVectorMath'); sc_.operation = 'SCALE'
    sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'
    sp = N.new('GeometryNodeSetPosition')
    Lk.new(pos.outputs[0], sep.inputs[0]); Lk.new(gi.outputs[0], sepd.inputs[0])
    Lk.new(sep.outputs['Z'], div.inputs[0]); Lk.new(sepd.outputs['Z'], div.inputs[1])
    Lk.new(gi.outputs[0], sc_.inputs[0]); Lk.new(div.outputs[0], sc_.inputs['Scale'])
    Lk.new(pos.outputs[0], sub.inputs[0]); Lk.new(sc_.outputs[0], sub.inputs[1])
    Lk.new(oi.outputs['Geometry'], sp.inputs['Geometry']); Lk.new(sub.outputs[0], sp.inputs['Position'])
    Lk.new(sp.outputs['Geometry'], go.inputs[0])
    md = o.modifiers.get('ShadowProj') or o.modifiers.new('ShadowProj', 'NODES'); md.node_group = ng
    m = bpy.data.materials.get('ShadowProjMat') or bpy.data.materials.new('ShadowProjMat'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0, 0, 0, 1); nt.links.new(em.outputs[0], out.inputs['Surface'])
    me = o.data; me.materials.clear(); me.materials.append(m)
    # Set Position output keeps the source materials; override with a Set Material node
    sm = N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = m
    Lk.new(sp.outputs['Geometry'], sm.inputs['Geometry']); Lk.new(sm.outputs['Geometry'], go.inputs[0])
    o.hide_render = True
    return o

def set_shadow_dir():
    rig = bpy.data.objects['SpriteRig']; o = bpy.data.objects['ShadowProj']
    d = rig.matrix_world.to_3x3() @ SHADOW_TRAVEL
    bpy.data.node_groups['ShadowProjGN'].nodes['DirVec'].vector = d
    o.update_tag()

# ---------------------------------------------------------------- posing helpers (armature space)
def reset():
    for pb in arm().pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def rot(name, axis, deg, pivot=None):
    """rotate bone `name` (and so its children) about an armature-space axis through pivot (default: bone head)"""
    pb = arm().pose.bones[name]
    if pivot is None: pivot = pb.head.copy()
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized())
    pb.matrix = Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot)) @ pb.matrix
    bpy.context.view_layer.update()

def move(name, vec):
    pb = arm().pose.bones[name]
    pb.matrix = Matrix.Translation(Vector(vec)) @ pb.matrix
    bpy.context.view_layer.update()

def key_all(frame):
    for pb in arm().pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame); pb.keyframe_insert('location', frame=frame)

SHOULDER_PIVOT = Vector((0.2, -0.0, 1.27))
def arms(axis, deg, pivot=None):
    piv = pivot or SHOULDER_PIVOT
    for b in ARM_A: rot(b, axis, deg, piv)

def sword_vec():
    pbs = arm().pose.bones
    return (pbs['Bone_043'].tail - pbs['Bone_044'].head).normalized()

def arms_dir(target, amount=1.0):
    """rotate both arm chains about the shoulders so the sword points along `target` (armature space)"""
    v = sword_vec(); t = Vector(target).normalized()
    q = v.rotation_difference(t)
    ax, ang = q.to_axis_angle()
    if ang > 1e-4: arms(ax, math.degrees(ang) * amount)

def slerp_dirs(keys, t):
    """keys: [(t, vec), ...] sorted, piecewise slerp with smoothstep"""
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0; k = k * k * (3 - 2 * k)
            qa = Vector((0, 0, 1)).rotation_difference(Vector(a).normalized())
            qb = Vector((0, 0, 1)).rotation_difference(Vector(b).normalized())
            return (qa.slerp(qb, k) @ Vector((0, 0, 1)))
    return Vector(keys[-1][1])

S_REST = (-0.53, 0.29, 0.85)
S_RUN = (-0.55, 0.50, -0.50)
S_WIND = (-0.30, 0.70, 0.65)
S_HIGH = (-0.05, -0.75, 0.65)
S_END = (0.60, -0.55, -0.45)

# ---------------------------------------------------------------- actions
def new_action(name):
    a = arm()
    if a.animation_data is None: a.animation_data_create()
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    a.animation_data.action = act
    return act

S_FWD = (-0.15, -0.95, 0.20)
def pose_st(t):
    # hold (f0-3), sword flourish forward (f4-8, like the original), settle (f9-11)
    w = 2 * math.pi * t
    rot(SPINE, (1, 0, 0), 2.5 * math.sin(w))
    rot(SPINE, (0, 0, 1), -10 * math.sin(math.pi * min(1, max(0, (t - 0.3) / 0.45))))
    rot(HEAD, (0, 0, 1), 6.0 * math.sin(w + 2.0))
    move(ROOTB, (0, 0, -0.012 * (1 - math.cos(w)) / 2))
    target = slerp_dirs([(0, S_REST), (0.30, S_REST), (0.42, S_FWD), (0.66, S_FWD), (0.80, S_REST), (1.0, S_REST)], t)
    arms_dir(target)
    arms((0, 0, 1), 4.0 * math.sin(w))

def neutral_legs():
    # rest pose is a wide lunge: bring both legs under the hips before cycling
    rot(LEG_A, (0, 1, 0), -16); rot(LEG_B, (0, 1, 0), 15); rot(LEG_B, (1, 0, 0), 20)

def pose_mo(t):
    w = 2 * math.pi * t
    move(ROOTB, (0, 0, 0.035 * abs(math.sin(w)) - 0.03))
    neutral_legs()
    A = 38
    rot(LEG_A, (1, 0, 0), -A * math.sin(w)); rot(LEG_B, (1, 0, 0), A * math.sin(w))
    rot(SHIN_A, (1, 0, 0), 15 + 45 * max(0.0, math.sin(w + math.pi / 2)))
    rot(SHIN_B, (1, 0, 0), 15 + 45 * max(0.0, math.sin(w - math.pi / 2)))
    rot(SPINE, (1, 0, 0), 14)                          # lean into the run
    rot(SPINE, (0, 0, 1), 6 * math.sin(w))
    arms_dir(S_RUN)                                     # sword held low, trailing behind
    arms((1, 0, 0), 5 * math.sin(w))

def _slash_axis():
    s = Vector((-0.53, 0.29, 0.85)).normalized(); e = Vector((0.45, -0.65, -0.35)).normalized()
    return s.cross(e).normalized()

def pose_at(t):
    # t in [0,1): 0-0.28 wind-up, 0.28-0.6 slash, 0.6-1 recover
    ax = _slash_axis()
    if t < 0.28: k = t / 0.28; tw = 18 * k; lunge = 0
    elif t < 0.6: k = (t - 0.28) / 0.32; e = k * k * (3 - 2 * k); tw = 18 - 48 * e; lunge = 0.14 * e
    else: k = (t - 0.6) / 0.4; e = k * k * (3 - 2 * k); tw = -30 * (1 - e); lunge = 0.14 * (1 - e)
    move(ROOTB, (0, -lunge, -0.05 * min(1, lunge / 0.14)))
    rot(SPINE, (0, 0, 1), tw); rot(SPINE, (1, 0, 0), 12 * lunge / 0.14)
    if lunge > 0: rot(LEG_B, (1, 0, 0), -15 * lunge / 0.14)
    target = slerp_dirs([(0, S_REST), (0.28, S_WIND), (0.40, S_HIGH), (0.6, S_END), (0.75, S_END), (1.0, S_REST)], t)
    arms_dir(target)

def pose_da(t):
    rot(ROOTB, (1, 0, 0), -82, pivot=Vector((0.2, 0.0, 0.0)))
    move(ROOTB, (0, 0, 0.12))
    arms((0, 1, 0), 40); rot(HEAD, (1, 0, 0), -20)
    rot(LEG_B, (1, 0, 0), 25)

POSERS = {'st': pose_st, 'mo': pose_mo, 'at': pose_at, 'da': pose_da}

@with_scene
def build_actions():
    out = {}
    for act, n in FRAMES.items():
        new_action('g039_' + act)
        for f in range(n):
            reset(); POSERS[act](f / n); key_all(f + 1)
        out[act] = n
    arm().animation_data.action = None; reset()
    return out

# ---------------------------------------------------------------- rendering
def dir_rot(d, D=8): return math.radians(90 - d * 360 / D)

def _vis(mode):
    a = arm(); mesh = bpy.data.objects[MESH]; g = bpy.data.objects['BladeGlow']; p = bpy.data.objects['ShadowCatcher']
    s = sc()
    if mode == 'body':
        s.render.engine = 'BLENDER_EEVEE'; mesh.hide_render = False; mesh.visible_camera = True
        g.hide_render = True; p.hide_render = True; s.render.film_transparent = True
    elif mode == 'glow':
        s.render.engine = 'BLENDER_EEVEE'; mesh.hide_render = True; g.hide_render = False; p.hide_render = True
        s.render.film_transparent = True
    elif mode == 'shadow':
        s.render.engine = 'BLENDER_EEVEE'; mesh.hide_render = True; g.hide_render = True; p.hide_render = True
        s.render.film_transparent = True
    bpy.data.objects['ShadowProj'].hide_render = (mode != 'shadow')
    bpy.data.objects['ShadowSun'].hide_render = True

@with_scene
def render(act, passes=('body', 'glow', 'shadow'), dirs=None, frames=None):
    s = sc(); a = arm(); rig = bpy.data.objects['SpriteRig']; cam = bpy.data.objects['SpriteCam']
    W, H = CANVAS[act]; s.render.resolution_x = W; s.render.resolution_y = H
    s.render.resolution_percentage = int(100 * SS); s.render.filter_size = 1.2
    # keep the pivot at pixel PIV for this canvas (ortho scale is per larger side)
    cam.data.sensor_fit = 'AUTO'
    big = max(W, H); cam.data.ortho_scale = 4.4 * big / 179 / SCALE
    cam.data.shift_x = ((W / 2) - (PIV[0] + 0.5)) / big * -1
    cam.data.shift_y = ((PIV[1] + 0.5) - (H / 2)) / big
    a.animation_data.action = bpy.data.actions['g039_' + act]
    s.frame_start = 1; s.frame_end = FRAMES[act]
    D = 1 if act == 'da' else 8
    dirs = range(D) if dirs is None else dirs
    frames = range(FRAMES[act]) if frames is None else frames
    n = 0
    for ps in passes:
        _vis(ps)
        os.makedirs(os.path.join(ROOT, OUTDIR, act, ps), exist_ok=True)
        for d in dirs:
            rig.rotation_euler = (0, 0, -dir_rot(1 if act == 'da' else d, 8))
            bpy.context.view_layer.update(); set_shadow_dir()
            for f in frames:
                s.frame_set(f + 1)
                s.render.filepath = os.path.join(ROOT, OUTDIR, act, ps, 'd%d_f%02d.png' % (d, f))
                bpy.ops.render.render(write_still=True, scene=s.name); n += 1
    _vis('body'); rig.rotation_euler = (0, 0, 0); a.animation_data.action = None; reset()
    return n
