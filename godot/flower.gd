extends SceneTree
# 実行: bash scripts/godot_render.sh（F3.glb を書き出してから、Xvfb＋ソフトウェアVulkan で描画する）
# 花の glb を読み込み、マテリアル案を切り替えて描画する。座標は glTF（Y上）。Blender の (x,y,z) → (x,z,-y)
var variants := ["A_opaque", "B_std_backlight", "C_shader_backlight", "D_shader_backlight_noshadow", "E_std_transmittance"]
var vi := -1
var flower: Node3D
var key: DirectionalLight3D
var back: DirectionalLight3D
var frame := 0
func dir_light(from: Vector3, energy: float) -> DirectionalLight3D:
	var l := DirectionalLight3D.new(); l.light_energy = energy; l.shadow_enabled = true; l.shadow_bias = 0.03; l.shadow_normal_bias = 1.5
	root.add_child(l); l.look_at_from_position(from, Vector3(0, 0.4, 0)); return l
func _initialize():
	var doc := GLTFDocument.new(); var st := GLTFState.new()
	var err := doc.append_from_file("res://F3.glb", st); print("gltf load: ", err)
	flower = doc.generate_scene(st); root.add_child(flower)
	var env := WorldEnvironment.new(); var e := Environment.new(); e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.5, 0.5, 0.5); e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color = Color(0.82, 0.82, 0.86); e.ambient_light_energy = 0.25
	e.tonemap_mode = Environment.TONE_MAPPER_LINEAR; env.environment = e; root.add_child(env)
	key = dir_light(Vector3(2.5, 4.0, 3.5), 0.9)
	back = dir_light(Vector3(0.3, 0.6, -3.5), 0.9)
	var cam := Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL; cam.size = 2.6; root.add_child(cam)
	cam.look_at_from_position(Vector3(0, 0.45, 0) + Vector3(0, 4.5, 6), Vector3(0, 0.45, 0))
	root.size = Vector2i(900, 900)
	next_variant()
func meshes(n: Node, out: Array) -> Array:
	if n is MeshInstance3D: out.append(n)
	for c in n.get_children(): meshes(c, out)
	return out
func make_material(tag: String) -> Material:
	if tag.begins_with("A") or tag.begins_with("B") or tag.begins_with("E"):
		var m := StandardMaterial3D.new(); m.vertex_color_use_as_albedo = true; m.roughness = 0.8
		if tag.begins_with("B"): m.backlight_enabled = true; m.backlight = Color(0.4, 0.4, 0.4)
		if tag.begins_with("E"): m.subsurf_scatter_transmittance_enabled = true; m.subsurf_scatter_transmittance_color = Color(1, 1, 1); m.subsurf_scatter_transmittance_depth = 0.1
		return m
	var s := ShaderMaterial.new(); var sh := Shader.new()
	sh.code = "shader_type spatial;\nvoid fragment(){ ALBEDO = COLOR.rgb; ROUGHNESS = 0.8; BACKLIGHT = COLOR.rgb * 0.5; }\n"   # 逆光の透けを、花びらの色で
	s.shader = sh; return s
func next_variant():
	vi += 1
	if vi >= variants.size(): quit(); return
	var tag: String = variants[vi]; var mat := make_material(tag)
	for mi in meshes(flower, []): mi.material_override = mat
	var backlit := not tag.begins_with("A")
	back.visible = backlit; key.light_energy = 0.6 if backlit else 0.9
	back.shadow_enabled = not tag.contains("noshadow")
	frame = 0
func _process(_d):
	frame += 1
	if frame == 8:
		var img := root.get_texture().get_image(); var p := "%s/godot_F3_%s.png" % [OS.get_environment("OUT_DIR") if OS.has_environment("OUT_DIR") else "/tmp/godot", variants[vi]]; img.save_png(p); print("saved ", p)
		next_variant()
	return false
