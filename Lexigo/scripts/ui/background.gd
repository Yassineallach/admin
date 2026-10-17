extends Control
## Animated backdrop: drifting colour blobs (shader) plus floating letters.

const SHADER := """
shader_type canvas_item;
uniform vec4 top_color : source_color;
uniform vec4 bottom_color : source_color;
uniform vec4 accent : source_color;
uniform vec4 accent2 : source_color;
uniform float aspect = 0.56;
void fragment() {
	vec2 uv = UV;
	vec3 c = mix(top_color.rgb, bottom_color.rgb, smoothstep(0.0, 1.0, uv.y));
	float t = TIME * 0.07;
	for (int i = 0; i < 5; i++) {
		float fi = float(i);
		vec2 p = vec2(0.5 + 0.48 * sin(t * (1.0 + fi * 0.21) + fi * 1.7),
					  0.5 + 0.48 * cos(t * (0.8 + fi * 0.17) + fi * 2.3));
		vec2 d = (uv - p) * vec2(1.0, 1.0 / aspect);
		float glow = exp(-dot(d, d) * 5.5);
		c += mix(accent.rgb, accent2.rgb, mod(fi, 2.0)) * glow * 0.16;
	}
	float vignette = smoothstep(1.25, 0.35, length((uv - 0.5) * vec2(1.0, 1.0 / aspect) * 0.9));
	COLOR = vec4(c * mix(0.7, 1.0, vignette), 1.0);
}
"""

const GLYPHS := "ABCDEFGHIJKLMNOPQRSTUVWXYZÉÑÜÇÀÖ"

var _rect: ColorRect
var _mat: ShaderMaterial
var _letters := []
var _layer: Control
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_rect = ColorRect.new()
	_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sh := Shader.new()
	sh.code = SHADER
	_mat = ShaderMaterial.new()
	_mat.shader = sh
	_rect.material = _mat
	add_child(_rect)
	move_child(_rect, 0)
	_layer = Control.new()
	_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.draw.connect(_draw_letters)
	add_child(_layer)
	set_palette(UI.ACCENT)
	_rng.seed = 42
	for i in 22:
		_letters.append(_new_letter(true))

func set_palette(accent: Color) -> void:
	_mat.set_shader_parameter("top_color", UI.BG_TOP)
	_mat.set_shader_parameter("bottom_color", UI.BG_BOTTOM)
	var current = _mat.get_shader_parameter("accent")
	var from: Color = current if current is Color else accent
	create_tween().tween_method(func(c: Color): _mat.set_shader_parameter("accent", c), from, accent, 0.6)
	_mat.set_shader_parameter("accent2", UI.ACCENT_2)

func _new_letter(anywhere: bool) -> Dictionary:
	var s := size if size.x > 0 else Vector2(720, 1280)
	return {
		"pos": Vector2(_rng.randf() * s.x, _rng.randf() * s.y if anywhere else s.y + 60),
		"speed": _rng.randf_range(14, 42),
		"size": _rng.randi_range(28, 84),
		"rot": _rng.randf_range(-0.4, 0.4),
		"spin": _rng.randf_range(-0.15, 0.15),
		"alpha": _rng.randf_range(0.04, 0.11),
		"glyph": GLYPHS[_rng.randi_range(0, GLYPHS.length() - 1)],
	}

func _process(delta: float) -> void:
	_mat.set_shader_parameter("aspect", size.x / maxf(size.y, 1.0))
	for i in _letters.size():
		var l: Dictionary = _letters[i]
		l["pos"].y -= l["speed"] * delta
		l["rot"] += l["spin"] * delta
		if l["pos"].y < -100:
			_letters[i] = _new_letter(false)
	_layer.queue_redraw()

func _draw_letters() -> void:
	var f := UI.font(true)
	for l in _letters:
		_layer.draw_set_transform(l["pos"], l["rot"], Vector2.ONE)
		_layer.draw_string(f, Vector2.ZERO, l["glyph"], HORIZONTAL_ALIGNMENT_CENTER, -1, l["size"], Color(1, 1, 1, l["alpha"]))
	_layer.draw_set_transform(Vector2.ZERO, 0, Vector2.ONE)
