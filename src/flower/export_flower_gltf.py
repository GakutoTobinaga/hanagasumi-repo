"""
export_flower_gltf.py -- 花を1つ組み立てて、glTF（.glb）で書き出す（Godot に渡す用）。
組み立ては hanagasumi_flower_proto.py と同じ（FLOWERS の1つ）。色は頂点カラー COLOR_0（リニアRGB、OKLCH から計算済み）。
花びらは1枚ずつ別のメッシュ（ノード名 p0, p1, ...）。マテリアルは付けない（Godot 側で付ける）。
実行: python export_flower_gltf.py -- <出力.glb> [花の名前 F1〜F6]
"""
import os, sys, numpy as np, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "hanagasumi_flower_proto.py"), encoding="utf-8").read().split("bpy.ops.wm.read_factory_settings")[0])  # TYPES, FLOWERS, make_flower, place, petal_colors, OUT
NAME = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else "F3"
g = next(f for f in FLOWERS if f["name"] == NAME)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
for pi, p in enumerate(make_flower(g, np.random.default_rng(g["seed"]))):
    d = TYPES[p["type"]]; Vw = place(d["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04); T = d["T"]; nv, m = len(Vw), len(T)
    me = bpy.data.meshes.new(f"p{pi}")
    me.vertices.add(nv); me.vertices.foreach_set("co", Vw.astype(np.float32).ravel())
    me.loops.add(3 * m); me.loops.foreach_set("vertex_index", T.astype(np.int32).ravel())
    me.polygons.add(m); me.polygons.foreach_set("loop_start", np.arange(0, 3 * m, 3, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(m, 3, dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(m, dtype=bool)); me.update(calc_edges=True)
    rgb = petal_colors(d["r"], g["col"], g["grad"])
    ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT'); ca.data.foreach_set("color", np.concatenate([rgb, np.ones((nv, 1))], 1).astype(np.float32).ravel())
    me.color_attributes.active_color = ca; me.color_attributes.render_color_index = 0
    ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob)
kw = dict(filepath=OUT, export_format='GLB', export_apply=False, export_materials='NONE')
try: bpy.ops.export_scene.gltf(**kw, export_vertex_color='ACTIVE')     # Blender 4.2以降。マテリアルなしでも頂点カラーを書き出す
except TypeError: bpy.ops.export_scene.gltf(**kw, export_colors=True)
print("[exported]", OUT, os.path.getsize(OUT) // 1024, "KB")
