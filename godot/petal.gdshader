// 花びらのシェーダー（試作）。薄い半透明の膜を、リアルタイム向けの近似で描く。
// 色は頂点カラー（OKLCH から計算済みのリニアRGB）。UV.x = 付け根からの距離 r（0→先端1）。
// 透け = translucency × 薄さ × (向きによらない透け + 光源が花びらの真後ろにあるほど強い透け)
// 透けには影を掛けない（花びらのメッシュは厚みのある閉じた殻なので、影を掛けると、自分の裏面で遮られて透けが消える）。
shader_type spatial;
render_mode cull_back;

uniform float translucency : hint_range(0.0, 3.0) = 1.0;
uniform float view_power : hint_range(1.0, 16.0) = 3.0;     // 大きいほど、光源と視線がそろったときだけ光る
uniform float edge_thin : hint_range(0.0, 1.0) = 0.6;       // 付け根の透けやすさ = 1 - edge_thin、縁 = 1
uniform float base_backlight : hint_range(0.0, 1.0) = 0.2;  // 向きによらない透け（裏から光が当たっている面）
uniform float wrap : hint_range(0.0, 1.0) = 0.25;           // 拡散光の回り込み（薄い膜は、光の境目がやわらかい）

varying float thin;

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.75;
	thin = mix(1.0 - edge_thin, 1.0, clamp(UV.x, 0.0, 1.0));
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float diff = clamp((ndl + wrap) / (1.0 + wrap), 0.0, 1.0);
	DIFFUSE_LIGHT += diff * ATTENUATION * LIGHT_COLOR / PI;
	float back = clamp(-ndl, 0.0, 1.0);
	float aligned = pow(clamp(dot(VIEW, -LIGHT), 0.0, 1.0), view_power);
	DIFFUSE_LIGHT += translucency * thin * (base_backlight * back + aligned * (0.5 + 0.5 * back)) * LIGHT_COLOR / PI;
}
