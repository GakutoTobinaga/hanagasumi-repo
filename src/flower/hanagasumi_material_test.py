"""
hanagasumi_material_test.py -- 花全体の質感（薄い半透明）の描画試験。Cycles（CPU）。
花の組み立ては hanagasumi_flower_proto.py と同じ（FLOWERS の1つを選ぶ）。色は頂点カラー "Col"（OKLCH から計算済み）。
マテリアルの案を並べて描く:
  A 不透明: Diffuse のみ（Workbench に近い基準）
  B 半透明: Diffuse と Translucent を半々（前から照らす）
  C 半透明・逆光: B と同じマテリアルで、花の後ろ上から強い光
  D 半透明を強く: Translucent 0.8。逆光
  E 縁ほど薄い: Translucent の割合を、付け根0.5→縁0.9（r で代用。厚みマップはまだない）＋弱い光沢。逆光
メッシュは厚みのある閉じた殻なので、光は表と裏の2面を通る（薄板1枚とは見え方が違う可能性）。
実行: python hanagasumi_material_test.py -- <出力プレフィックス> [花の名前 F1〜F6] [サンプル数]
"""
import os, sys, math, time, numpy as np, bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "hanagasumi_flower_proto.py"), encoding="utf-8").read().split("bpy.ops.wm.read_factory_settings")[0])  # TYPES, FLOWERS, make_flower, place, petal_colors, OUT
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = args[1] if len(args) > 1 else "F5"; SAMPLES = int(args[2]) if len(args) > 2 else 64
g = next(f for f in FLOWERS if f["name"] == NAME)

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
obs = []
for pi, p in enumerate(make_flower(g, np.random.default_rng(g["seed"]))):
    d = TYPES[p["type"]]; Vw = place(d["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04); T = d["T"]; nv, m = len(Vw), len(T)
    me = bpy.data.meshes.new(f"p{pi}")
    me.vertices.add(nv); me.vertices.foreach_set("co", Vw.astype(np.float32).ravel())
    me.loops.add(3 * m); me.loops.foreach_set("vertex_index", T.astype(np.int32).ravel())
    me.polygons.add(m); me.polygons.foreach_set("loop_start", np.arange(0, 3 * m, 3, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(m, 3, dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(m, dtype=bool)); me.update(calc_edges=True)
    rgb = petal_colors(d["r"], g["col"], g["grad"])
    ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT'); ca.data.foreach_set("color", np.concatenate([rgb, np.ones((nv, 1))], 1).astype(np.float32).ravel())
    rr = me.attributes.new(name="r", type='FLOAT', domain='POINT'); rr.data.foreach_set("value", np.clip(d["r"], 0, 1).astype(np.float32))   # 付け根0→先端1
    ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob); obs.append(ob)

def material(name, trans, gloss=0.0, trans_by_r=False):
    mt = bpy.data.materials.new(name); mt.use_nodes = True; nt = mt.node_tree; N = nt.nodes; Lk = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); col = N.new("ShaderNodeAttribute"); col.attribute_name = "Col"
    dif = N.new("ShaderNodeBsdfDiffuse"); tr = N.new("ShaderNodeBsdfTranslucent"); mix = N.new("ShaderNodeMixShader")
    Lk.new(col.outputs["Color"], dif.inputs["Color"]); Lk.new(col.outputs["Color"], tr.inputs["Color"])
    if trans_by_r:   # 付け根 trans[0] → 縁 trans[1]
        ra = N.new("ShaderNodeAttribute"); ra.attribute_name = "r"; mp = N.new("ShaderNodeMapRange")
        mp.inputs["To Min"].default_value, mp.inputs["To Max"].default_value = trans; Lk.new(ra.outputs["Fac"], mp.inputs["Value"]); Lk.new(mp.outputs["Result"], mix.inputs["Fac"])
    else: mix.inputs["Fac"].default_value = trans
    Lk.new(dif.outputs[0], mix.inputs[1]); Lk.new(tr.outputs[0], mix.inputs[2]); sh = mix
    if gloss > 0:
        gl = N.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.35; m2 = N.new("ShaderNodeMixShader"); m2.inputs["Fac"].default_value = gloss
        Lk.new(mix.outputs[0], m2.inputs[1]); Lk.new(gl.outputs[0], m2.inputs[2]); sh = m2
    Lk.new(sh.outputs[0], out.inputs["Surface"]); return mt

def light(name, kind, loc, energy, size):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy
    if kind == "AREA": ld.size = size
    lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo); lo.location = loc
    lo.rotation_euler = (Vector((0, 0, 0.4)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return lo
key = light("key", "AREA", (2.5, -3.5, 4.0), 250, 3.0)      # 前・右上
back = light("back", "AREA", (0.3, 3.5, 0.6), 600, 2.0)    # カメラの反対側、低い位置（奥の花びらを透かす逆光）
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.82, 0.82, 0.86, 1); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25; sc.world = w
cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 2.6
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); center = Vector((0, 0, 0.45)); cam.location = center + Vector((0, -6, 4.5))
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 12; sc.cycles.diffuse_bounces = 6; sc.cycles.transmission_bounces = 12   # Translucent は diffuse の跳ね返りとして数えられる
sc.render.resolution_x = sc.render.resolution_y = 900; sc.view_settings.view_transform = 'Standard'   # 色は OKLCH で指定しているので、Workbench と同じく変換しない（AgX は彩度が落ちた）
VARIANTS = [("A_opaque", material("A", 0.0), False), ("B_translucent", material("B", 0.5), False),
            ("C_translucent_backlit", material("C", 0.5), True), ("D_strong_backlit", material("D", 0.8), True),
            ("E_edge_thin_backlit", material("E", (0.5, 0.9), gloss=0.06, trans_by_r=True), True)]
for tag, mt, backlit in VARIANTS:
    for ob in obs: ob.data.materials.clear(); ob.data.materials.append(mt)
    back.hide_render = not backlit; key.data.energy = 150 if backlit else 250
    sc.render.filepath = f"{OUT}_{NAME}_{tag}.png"; t = time.time(); bpy.ops.render.render(write_still=True); print(f"[{tag}] {time.time() - t:.0f}s"); sys.stdout.flush()
print("[done material]")
