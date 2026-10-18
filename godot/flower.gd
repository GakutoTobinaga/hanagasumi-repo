extends SceneTree
# 実行: bash scripts/godot_render.sh（F3.glb を書き出してから、Xvfb＋ソフトウェアVulkan で描画する）
# 花の glb を読み込み、マテリアル・光・視点の案を切り替えて描画する。座標は glTF（Y上）。Blender の (x,y,z) → (x,z,-y)
# mat: std=標準マテリアル（不透明）、std_bl=標準マテリアルの Back Lighting、petal=petal.gdshader
# view: front=斜め上から、low=低い位置から（奥の花びらが逆光になる）
var variants := [
	{"tag": "A_std_front", "mat": "std", "back": false, "key_shadow": true, "view": "front"},
	{"tag": "B_std_backlight", "mat": "std_bl", "back": true, "key_shadow": true, "view": "front"},
	{"tag": "C_petal_front", "mat": "petal", "back": false, "key_shadow": true, "view": "front"},
	{"tag": "D_petal_backlit", "mat": "petal", "back": true, "key_shadow": true, "view": "front"},
	{"tag": "E_petal_backlit_nokeyshadow", "mat": "petal", "back": true, "key_shadow": false, "view": "front"},
	{"tag": "F_petal_backlit_low", "mat": "petal", "back": true, "key_shadow": true, "view": "low"},
	{"tag": "G_std_backlight_low", "mat": "std_bl", "back": true, "key_shadow": true, "view": "low"},
]
const CENTER := Vector3(0, 0.45, 0)
const VIEWS := {"front": Vector3(0, 4.5, 6), "low": Vector3(0, 1.2, 7.5)}
var vi := -1
var flower: Node3D
var key: DirectionalLight3D
var back: DirectionalLight3D
var cam: Camera3D
var frame := 0
func dir_light(from: Vector3, energy: float) -> DirectionalLight3D:
	var l := DirectionalLight3D.new(); l.light_energy = energy; l.shadow_enabled = true; l.shadow_bias = 0.03; l.shadow_normal_bias = 1.5
	l.directional_shadow_max_distance = 8.0
	root.add_child(l); l.look_at_from_position(from, Vector3(0, 0.4, 0)); return l
func _initialize():
	var doc := GLTFDocument.new(); var st := GLTFState.new()
	var err := doc.append_from_file("res://F3.glb", st); print("gltf load: ", err)
	flower = doc.generate_scene(st); root.add_child(flower)
	var env := WorldEnvironment.new(); var e := Environment.new(); e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.5, 0.5, 0.5); e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color = Color(0.82, 0.82, 0.86); e.ambient_light_energy = 0.25
	e.tonemap_mode = Environment.TONE_MAPPER_LINEAR; env.environment = e; root.add_child(env)
	key = dir_light(Vector3(2.5, 4.0, 3.5), 0.9)
	back = dir_light(Vector3(0.3, 1.0, -3.5), 0.9)   # 花の後ろ、やや上
	back.shadow_enabled = false                       # 透けを自分の裏面で遮らない（petal.gdshader の注を参照）
	cam = Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL; cam.size = 2.6; root.add_child(cam)
	root.size = Vector2i(900, 900)
	RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_HARD)   # 既定のソフトシャドウでは、花びらに細かい点の模様が出た（フィルタのパターン。ソフトウェア描画で目立つ可能性）
	next_variant()
func meshes(n: Node, out: Array) -> Array:
	if n is MeshInstance3D: out.append(n)
	for c in n.get_children(): meshes(c, out)
	return out
func make_material(kind: String) -> Material:
	if kind == "petal":
		var s := ShaderMaterial.new(); s.shader = load("res://petal.gdshader"); s.set_shader_parameter("translucency", 0.6); return s
	var m := StandardMaterial3D.new(); m.vertex_color_use_as_albedo = true; m.roughness = 0.8
	if kind == "std_bl": m.backlight_enabled = true; m.backlight = Color(0.4, 0.4, 0.4)
	return m
func next_variant():
	vi += 1
	if vi >= variants.size(): quit(); return
	var v: Dictionary = variants[vi]; var mat := make_material(v["mat"])
	for mi in meshes(flower, []): mi.material_override = mat
	back.visible = v["back"]; key.light_energy = 0.6 if v["back"] else 0.9; key.shadow_enabled = v["key_shadow"]
	cam.look_at_from_position(CENTER + VIEWS[v["view"]], CENTER)
	frame = 0
func _process(_d):
	frame += 1
	if frame == 8:
		var img := root.get_texture().get_image(); var p := "%s/godot_F3_%s.png" % [OS.get_environment("OUT_DIR") if OS.has_environment("OUT_DIR") else "/tmp/godot", variants[vi]["tag"]]; img.save_png(p); print("saved ", p)
		next_variant()
	return false
