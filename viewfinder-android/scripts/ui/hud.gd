class_name Hud
extends Control
## Touch-first HUD drawn in `_draw` so multi-touch works (left thumb on the
## stick while the right thumb looks / presses buttons). Mouse clicks arrive
## as emulated touches, so it also works on desktop.

var game  # Game (untyped to avoid a cyclic class reference)

var stick_vec := Vector2.ZERO
var rewind_held := false
var flash := 0.0
var fade := 0.0

var _buttons: Dictionary = {}  # name -> {c: Vector2, r: float, label: String}
var _touches: Dictionary = {}  # index -> {kind, name, origin, pos}
var _look_accum := Vector2.ZERO
var _last_look := Vector2.ZERO
var _title := ""
var _hint := ""
var _title_time := 0.0
var _toast := ""
var _toast_time := 0.0
var _u := 1.0
var _font: Font
var _t := 0.0

# Dialogue (Miso).
var _say_name := ""
var _say_lines: Array = []
var _say_chars := 0.0
var _say_hold := 0.0

# Photo eject animation.
var _eject_slot := -1
var _eject_t := 1.0

var _pause_panel: Control
var _complete_panel: Control
var _complete_next: Button
var _keep_photo: TextureRect
var _keep_caption: Label
var _vignette: GradientTexture2D
var _note_panel: Control
var _note_title: Label
var _note_text: Label

const STICK_R := 85.0
const INK := Color(0.22, 0.19, 0.26)
const PAPER := Color(1, 0.98, 0.94)
const ACCENT := Color(1.0, 0.6, 0.5)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_font = ThemeDB.fallback_font
	_pause_panel = _make_panel("Paused", [["Resume", "resume"], ["Restart", "restart"], ["Back to the Station", "hub"], ["Main menu", "menu"]])
	_complete_panel = _make_panel("Memory restored", [["Continue", "next"], ["Replay", "restart"], ["Main menu", "menu"]])
	_complete_next = _complete_panel.find_child("Btn_next", true, false)
	_build_keepsake()
	var g := Gradient.new()
	g.set_color(0, Color(0.1, 0.06, 0.12, 0.0))
	g.add_point(0.6, Color(0.1, 0.06, 0.12, 0.0))
	g.set_color(g.get_point_count() - 1, Color(0.1, 0.06, 0.12, 0.38))
	_vignette = GradientTexture2D.new()
	_vignette.gradient = g
	_vignette.fill = GradientTexture2D.FILL_RADIAL
	_vignette.fill_from = Vector2(0.5, 0.5)
	_vignette.fill_to = Vector2(1.08, 0.5)
	_vignette.width = 128
	_vignette.height = 128
	_build_note_panel()
	resized.connect(_layout)
	_layout()


func set_title(title: String, hint: String) -> void:
	_title = title
	_hint = hint
	_title_time = 4.5


func toast(msg: String) -> void:
	_toast = msg
	_toast_time = 2.8


func say(who: String, lines: Array) -> void:
	_say_name = who
	_say_lines = lines.duplicate()
	_say_chars = 0.0
	_say_hold = 0.0


func eject(slot: int) -> void:
	_eject_slot = slot
	_eject_t = 0.0


func fade_out() -> void:
	create_tween().tween_property(self, "fade", 1.0, 0.5)


func show_note(title: String, text: String) -> void:
	_note_title.text = title
	_note_text.text = text
	_note_panel.visible = true
	_touches.clear()
	stick_vec = Vector2.ZERO


func consume_look() -> Vector2:
	var v := _look_accum
	_look_accum = Vector2.ZERO
	_last_look = v
	return v


func peek_look() -> Vector2:
	return _last_look


func toggle_pause() -> void:
	if _complete_panel.visible:
		return
	_pause_panel.visible = not _pause_panel.visible
	get_tree().paused = _pause_panel.visible


func show_complete(last: bool, keepsake: Texture2D = null, place_name: String = "") -> void:
	_keep_photo.texture = keepsake
	_keep_caption.text = place_name
	_keep_photo.get_parent().get_parent().visible = keepsake != null
	var card: Control = _keep_photo.get_parent().get_parent()
	card.pivot_offset = card.size * 0.5
	card.scale = Vector2(0.6, 0.6)
	card.modulate.a = 0.0
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(card, "scale", Vector2.ONE, 0.5)
	tw.tween_property(card, "modulate:a", 1.0, 0.3)
	_complete_next.text = "Back to the Station" if not last else "Back to the Station  ✦"
	_complete_panel.visible = true
	_touches.clear()
	stick_vec = Vector2.ZERO
	rewind_held = false
	_say_lines.clear()


## True while the REWIND button (or the R key) is held.
func wants_rewind() -> bool:
	return rewind_held or Input.is_physical_key_pressed(KEY_R)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

func _layout() -> void:
	var s := size
	_u = clampf(minf(s.x / 1280.0, s.y / 720.0), 0.5, 3.0)
	var u := _u
	_buttons = {
		"jump": {"c": Vector2(s.x - 115 * u, s.y - 115 * u), "r": 66 * u, "label": ""},
		"act": {"c": Vector2(s.x - 262 * u, s.y - 78 * u), "r": 50 * u, "label": ""},
		"cam": {"c": Vector2(s.x - 115 * u, s.y - 278 * u), "r": 52 * u, "label": ""},
		"shutter": {"c": Vector2(s.x - 290 * u, s.y - 250 * u), "r": 72 * u, "label": ""},
		"place": {"c": Vector2(s.x - 290 * u, s.y - 250 * u), "r": 72 * u, "label": "PLACE"},
		"rotl": {"c": Vector2(s.x - 345 * u, s.y - 385 * u), "r": 38 * u, "label": "⟲"},
		"rotr": {"c": Vector2(s.x - 235 * u, s.y - 385 * u), "r": 38 * u, "label": "⟳"},
		"rewind": {"c": Vector2(78 * u, s.y * 0.42), "r": 48 * u, "label": ""},
		"pause": {"c": Vector2(s.x - 48 * u, 48 * u), "r": 30 * u, "label": ""},
	}


func _thumb_rect(i: int) -> Rect2:
	var u := _u
	return Rect2(Vector2(20 * u + i * 90 * u, 18 * u), Vector2(76 * u, 92 * u))


func _dialog_rect() -> Rect2:
	var w := minf(size.x * 0.56, 720 * _u)
	return Rect2(Vector2((size.x - w) * 0.5, size.y - 150 * _u), Vector2(w, 118 * _u))


func _button_visible(name: String) -> bool:
	if game == null or not game.ready_to_play or game.completed:
		return name == "pause"
	match name:
		"cam": return game.has_camera
		"shutter": return game.camera_mode
		"place", "rotl", "rotr": return game.raised >= 0 and not game.camera_mode
		"act": return game.act_label() != ""
	return true


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if _pause_panel.visible or _complete_panel.visible or _note_panel.visible:
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			_on_press(event.index, event.position)
		else:
			_on_release(event.index)
	elif event is InputEventScreenDrag:
		var t: Dictionary = _touches.get(event.index, {})
		if t.is_empty():
			return
		t["pos"] = event.position
		if t["kind"] == "look":
			_look_accum += event.relative * 1.6 / _u
		elif t["kind"] == "stick":
			_update_stick(t)


func _on_press(index: int, pos: Vector2) -> void:
	for name in _buttons.keys():
		if not _button_visible(name):
			continue
		var b: Dictionary = _buttons[name]
		if pos.distance_to(b["c"]) <= b["r"] * 1.15:
			_touches[index] = {"kind": "button", "name": name, "origin": pos, "pos": pos}
			if name == "rewind":
				rewind_held = true
			elif name == "pause":
				toggle_pause()
			elif game:
				game.on_hud_action(name)
			return
	if not _say_lines.is_empty() and _dialog_rect().has_point(pos):
		_touches[index] = {"kind": "button", "name": "dialog", "origin": pos, "pos": pos}
		_advance_dialog()
		return
	if game:
		for i in game.photos.size():
			if _thumb_rect(i).grow(6 * _u).has_point(pos):
				_touches[index] = {"kind": "button", "name": "photo", "origin": pos, "pos": pos}
				game.on_hud_action("photo_%d" % i)
				return
	if pos.x < size.x * 0.4:
		var t := {"kind": "stick", "name": "", "origin": pos, "pos": pos}
		_touches[index] = t
		_update_stick(t)
	else:
		_touches[index] = {"kind": "look", "name": "", "origin": pos, "pos": pos}


func _on_release(index: int) -> void:
	var t: Dictionary = _touches.get(index, {})
	_touches.erase(index)
	if t.is_empty():
		return
	if t["kind"] == "stick":
		stick_vec = Vector2.ZERO
	elif t["name"] == "rewind":
		rewind_held = false


func _update_stick(t: Dictionary) -> void:
	var d: Vector2 = t["pos"] - t["origin"]
	var r := STICK_R * _u
	if d.length() > r:
		t["origin"] = t["pos"] - d.normalized() * r
		d = d.normalized() * r
	var v := d / r
	stick_vec = Vector2(v.x, -v.y)


func _advance_dialog() -> void:
	if _say_lines.is_empty():
		return
	var line: String = _say_lines[0]
	if _say_chars < line.length():
		_say_chars = line.length()
	else:
		_say_lines.pop_front()
		_say_chars = 0.0
		_say_hold = 0.0


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	_t += delta
	flash = maxf(0.0, flash - delta * 2.5)
	_title_time = maxf(0.0, _title_time - delta)
	_toast_time = maxf(0.0, _toast_time - delta)
	_eject_t = minf(_eject_t + delta / 1.3, 1.0)
	if game and game.ready_to_play and not game.completed:
		fade = maxf(0.0, fade - delta * 2.0)
	if not _say_lines.is_empty():
		var line: String = _say_lines[0]
		if _say_chars < line.length():
			_say_chars += delta * 45.0
		else:
			_say_hold += delta
			if _say_hold > 2.2 + line.length() * 0.03:
				_advance_dialog()
	queue_redraw()


func _text(pos: Vector2, txt: String, fsize: int, col: Color, align := HORIZONTAL_ALIGNMENT_CENTER, width := -1.0) -> void:
	var fs := int(fsize * _u)
	if align == HORIZONTAL_ALIGNMENT_CENTER and width < 0:
		var w := _font.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		pos.x -= w * 0.5
	draw_string(_font, pos, txt, align, width, fs, col)


func _rounded(r: Rect2, col: Color, radius: float, border := Color(0, 0, 0, 0), bw := 0.0) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = col
	sb.set_corner_radius_all(int(radius))
	if bw > 0.0:
		sb.border_color = border
		sb.set_border_width_all(int(bw))
	sb.anti_aliasing = true
	draw_style_box(sb, r)


func _draw() -> void:
	if game == null:
		return
	var s := size
	var u := _u

	draw_texture_rect(_vignette, Rect2(Vector2.ZERO, s), false)
	if game.camera_mode:
		_draw_viewfinder()

	var rewinding: bool = wants_rewind() or game._auto_rewind > 0
	if rewinding and game.ready_to_play:
		draw_rect(Rect2(Vector2.ZERO, s), Color(0.55, 0.42, 0.3, 0.25))
		for i in 6:  # VHS-ish scan bands
			var y := fmod(_t * 220.0 + i * s.y / 6.0, s.y)
			draw_rect(Rect2(0, y, s.x, 3 * u), Color(1, 1, 1, 0.08))
		var a := 0.6 + 0.4 * sin(_t * 8.0)
		_text(Vector2(s.x * 0.5, s.y * 0.2), "◀◀  REWIND", 40, Color(1, 0.95, 0.85, a))

	_draw_stick()
	_draw_buttons()
	_draw_tray()

	# Level title card.
	if _title_time > 0.0 and game.ready_to_play:
		var a := clampf(minf(_title_time, 4.5 - _title_time) * 2.0, 0.0, 1.0)
		_text(Vector2(s.x * 0.5, 74 * u), _title, 34, Color(1, 1, 1, a))
		draw_line(Vector2(s.x * 0.5 - 120 * u, 88 * u), Vector2(s.x * 0.5 + 120 * u, 88 * u), Color(1, 1, 1, a * 0.7), 2 * u)

	_draw_dialog()

	if _toast_time > 0.0:
		var a := clampf(_toast_time, 0.0, 1.0)
		var tw := _font.get_string_size(_toast, HORIZONTAL_ALIGNMENT_LEFT, -1, int(22 * u)).x
		var y := s.y * 0.66
		_rounded(Rect2(Vector2((s.x - tw) * 0.5 - 18 * u, y - 30 * u), Vector2(tw + 36 * u, 44 * u)), Color(0.15, 0.13, 0.18, 0.5 * a), 22 * u)
		_text(Vector2(s.x * 0.5, y), _toast, 22, Color(1, 1, 1, a))

	if not game.camera_mode and game.raised < 0:
		draw_circle(s * 0.5, 3 * u, Color(1, 1, 1, 0.75))

	_draw_eject()

	if flash > 0.0:
		draw_rect(Rect2(Vector2.ZERO, s), Color(1, 1, 1, flash * 0.8))
	if fade > 0.0:
		draw_rect(Rect2(Vector2.ZERO, s), Color(0.97, 0.94, 0.9, fade))
		if not game.ready_to_play:
			_text(s * 0.5, "developing…", 26, Color(0.45, 0.38, 0.45, fade))


func _draw_stick() -> void:
	var u := _u
	for t in _touches.values():
		if t["kind"] == "stick":
			draw_circle(t["origin"], STICK_R * u, Color(1, 1, 1, 0.12))
			draw_arc(t["origin"], STICK_R * u, 0, TAU, 48, Color(1, 1, 1, 0.5), 3 * u, true)
			var knob: Vector2 = t["origin"] + Vector2(stick_vec.x, -stick_vec.y) * STICK_R * u
			draw_circle(knob, 32 * u, Color(1, 1, 1, 0.6))
	if not _touches.values().any(func(t): return t["kind"] == "stick"):
		var c := Vector2(170 * u, size.y - 160 * u)
		draw_arc(c, STICK_R * u, 0, TAU, 48, Color(1, 1, 1, 0.22), 2 * u, true)
		draw_circle(c, 26 * u, Color(1, 1, 1, 0.14))


func _draw_buttons() -> void:
	var u := _u
	for name in _buttons.keys():
		if not _button_visible(name):
			continue
		var b: Dictionary = _buttons[name]
		var c: Vector2 = b["c"]
		var r: float = b["r"]
		var pressed := _touches.values().any(func(t): return t["name"] == name)
		var bg := Color(1, 1, 1, 0.42 if pressed else 0.22)
		if name == "place":
			bg = Color(ACCENT, 0.8 if pressed else 0.6)
		draw_circle(c, r, bg)
		draw_arc(c, r, 0, TAU, 48, Color(1, 1, 1, 0.85), 2.5 * u, true)
		var ic := Color(1, 1, 1, 0.95)
		match name:
			"jump":
				draw_polyline(PackedVector2Array([c + Vector2(-20, 8) * u, c + Vector2(0, -12) * u, c + Vector2(20, 8) * u]), ic, 6 * u, true)
			"cam":
				_rounded(Rect2(c + Vector2(-24, -15) * u, Vector2(48, 32) * u), Color(0, 0, 0, 0), 6 * u, ic, 4 * u)
				draw_arc(c + Vector2(0, 1) * u, 10 * u, 0, TAU, 24, ic, 4 * u, true)
				draw_rect(Rect2(c + Vector2(-10, -21) * u, Vector2(12, 6) * u), ic)
				if game.film >= 0:
					_text(c + Vector2(0, r + 24 * u), "%d left" % game.film, 17, Color(1, 1, 1, 0.95))
			"shutter":
				draw_arc(c, r * 0.72, 0, TAU, 48, ic, 6 * u, true)
				draw_circle(c, r * 0.55, Color(1, 1, 1, 0.9 if pressed else 0.75))
			"rewind":
				for k in 2:
					var o := c + Vector2(-2 + k * 16, 0) * u
					draw_colored_polygon(PackedVector2Array([o + Vector2(-14, 0) * u, o + Vector2(2, -12) * u, o + Vector2(2, 12) * u]), ic)
			"pause":
				draw_rect(Rect2(c + Vector2(-9, -11) * u, Vector2(6, 22) * u), ic)
				draw_rect(Rect2(c + Vector2(3, -11) * u, Vector2(6, 22) * u), ic)
			"act":
				_text(c + Vector2(0, 8 * u), game.act_label(), 22, INK)
			_:
				_text(c + Vector2(0, 9 * u), b["label"], 24 if r > 45 * u else 26, INK)


func _draw_tray() -> void:
	var u := _u
	for i in game.photos.size():
		if i == _eject_slot and _eject_t < 1.0:
			continue
		var r := _thumb_rect(i)
		var lifted: bool = game.raised == i
		if lifted:
			r.position.y += 10 * u
		var p: Photo = game.photos[i]
		_draw_card(r, p, 1.0)
		if lifted:
			_rounded(r.grow(3 * u), Color(0, 0, 0, 0), 6 * u, ACCENT, 4 * u)


## A tiny picture in its frame: polaroid, paper sketch or framed painting.
func _draw_card(r: Rect2, p: Photo, alpha: float) -> void:
	var u := _u
	var inner: Rect2
	match p.kind:
		"sketch":
			r = Rect2(r.position, Vector2(r.size.x, r.size.x))
			draw_rect(r, Color(0.95, 0.93, 0.87, alpha))
			inner = r.grow(-4 * u)
		"painting":
			r = Rect2(r.position, Vector2(r.size.x, r.size.x))
			draw_rect(r, Color(0.5, 0.34, 0.22, alpha))
			inner = r.grow(-7 * u)
		_:
			draw_rect(Rect2(r.position + Vector2(3, 4) * u, r.size), Color(0, 0, 0, 0.18 * alpha))
			draw_rect(r, Color(PAPER, alpha))
			inner = Rect2(r.position + Vector2(6, 6) * u, Vector2(r.size.x - 12 * u, r.size.x - 12 * u))
	if p.texture:
		draw_texture_rect(p.texture, inner, false, Color(1, 1, 1, alpha))
	var dev := p.developed()
	if dev < 1.0:
		draw_rect(inner, Color(0.97, 0.96, 0.93, (1.0 - dev) * alpha))


func _draw_eject() -> void:
	if _eject_t >= 1.0 or _eject_slot < 0 or _eject_slot >= game.photos.size():
		return
	var s := size
	var u := _u
	var p: Photo = game.photos[_eject_slot]
	var big := Vector2(170, 206) * u
	var center_low := Vector2(s.x * 0.5 - big.x * 0.5, s.y + 10 * u)
	var center_up := Vector2(s.x * 0.5 - big.x * 0.5, s.y * 0.5 - big.y * 0.4)
	var dst := _thumb_rect(_eject_slot)
	var r: Rect2
	if _eject_t < 0.45:
		var k := _eject_t / 0.45
		k = 1.0 - pow(1.0 - k, 3.0)
		r = Rect2(center_low.lerp(center_up, k), big)
	elif _eject_t < 0.7:
		r = Rect2(center_up, big)
	else:
		var k := (_eject_t - 0.7) / 0.3
		k = k * k * (3.0 - 2.0 * k)
		r = Rect2(center_up.lerp(dst.position, k), big.lerp(dst.size, k))
	_draw_card(r, p, 1.0)


func _draw_dialog() -> void:
	if _say_lines.is_empty():
		return
	var u := _u
	var r := _dialog_rect()
	_rounded(r, Color(0.16, 0.14, 0.2, 0.72), 18 * u)
	var tag := Rect2(r.position + Vector2(18, -18) * u, Vector2(96, 34) * u)
	_rounded(tag, ACCENT, 17 * u)
	_text(tag.get_center() + Vector2(0, 8 * u), _say_name, 20, Color.WHITE)
	var line: String = _say_lines[0]
	var shown := line.substr(0, int(_say_chars))
	draw_multiline_string(_font, r.position + Vector2(22, 46) * u, shown, HORIZONTAL_ALIGNMENT_LEFT,
		r.size.x - 44 * u, int(21 * u), 3, Color(1, 0.98, 0.95))
	if _say_chars >= line.length():
		var a := 0.5 + 0.5 * sin(_t * 5.0)
		draw_colored_polygon(PackedVector2Array([r.end - Vector2(30, 22) * u, r.end - Vector2(18, 22) * u, r.end - Vector2(24, 14) * u]), Color(1, 1, 1, a))


func _draw_viewfinder() -> void:
	var s := size
	var u := _u
	var half_h := s.y * 0.5 * Photo.T / tan(deg_to_rad(Player.FOV * 0.5))
	var c := s * 0.5
	var r := Rect2(c - Vector2(half_h, half_h), Vector2(half_h, half_h) * 2.0)
	var dim := Color(0.05, 0.04, 0.06, 0.45)
	draw_rect(Rect2(0, 0, s.x, r.position.y), dim)
	draw_rect(Rect2(0, r.end.y, s.x, s.y - r.end.y), dim)
	draw_rect(Rect2(0, r.position.y, r.position.x, r.size.y), dim)
	draw_rect(Rect2(r.end.x, r.position.y, s.x - r.end.x, r.size.y), dim)
	var l := 40 * u
	var w := 4 * u
	var col := Color(1, 1, 1, 0.95)
	for corner in [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]:
		var dx := l if corner.x == r.position.x else -l
		var dy := l if corner.y == r.position.y else -l
		draw_line(corner, corner + Vector2(dx, 0), col, w)
		draw_line(corner, corner + Vector2(0, dy), col, w)
	# Rule-of-thirds guides.
	for k in [1.0 / 3.0, 2.0 / 3.0]:
		draw_line(Vector2(r.position.x + r.size.x * k, r.position.y), Vector2(r.position.x + r.size.x * k, r.end.y), Color(1, 1, 1, 0.18), 1.5 * u)
		draw_line(Vector2(r.position.x, r.position.y + r.size.y * k), Vector2(r.end.x, r.position.y + r.size.y * k), Color(1, 1, 1, 0.18), 1.5 * u)
	draw_line(c - Vector2(14, 0) * u, c + Vector2(14, 0) * u, col, 2 * u)
	draw_line(c - Vector2(0, 14) * u, c + Vector2(0, 14) * u, col, 2 * u)
	draw_circle(Vector2(r.position.x + 24 * u, r.position.y + 24 * u), 7 * u, Color(1, 0.3, 0.3, 0.6 + 0.4 * sin(_t * 5.0)))
	var tag := ""
	if absf(game.player.pitch) < deg_to_rad(6.0):
		tag = "level"
	elif absf(game.player.pitch) > deg_to_rad(86.0):
		tag = "vertical"
	if tag != "":
		_text(Vector2(c.x, r.end.y + 34 * u), tag, 18, Color(0.75, 1, 0.85))


# ---------------------------------------------------------------------------
# Panels (regular Buttons: they only need single touch)
# ---------------------------------------------------------------------------

func _make_panel(title: String, entries: Array) -> Control:
	var root := ColorRect.new()
	root.color = Color(0.12, 0.1, 0.14, 0.6)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.process_mode = Node.PROCESS_MODE_ALWAYS
	root.visible = false
	add_child(root)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	center.add_child(box)
	var lbl := Label.new()
	lbl.text = title
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", 44)
	box.add_child(lbl)
	for e in entries:
		var b := MainMenu.styled_button(e[0], 28)
		b.name = "Btn_" + e[1]
		b.custom_minimum_size = Vector2(400, 76)
		var act: String = e[1]
		b.pressed.connect(func(): _on_panel(act))
		box.add_child(b)
	return root


## The polaroid keepsake shown when a memory is restored.
func _build_keepsake() -> void:
	var box: VBoxContainer = _complete_panel.get_child(0).get_child(0)
	var card := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1.0, 0.99, 0.96)
	sb.content_margin_left = 14
	sb.content_margin_right = 14
	sb.content_margin_top = 14
	sb.content_margin_bottom = 8
	sb.shadow_color = Color(0, 0, 0, 0.35)
	sb.shadow_size = 14
	sb.shadow_offset = Vector2(4, 6)
	card.add_theme_stylebox_override("panel", sb)
	card.rotation = 0.04
	card.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var v := VBoxContainer.new()
	card.add_child(v)
	_keep_photo = TextureRect.new()
	_keep_photo.custom_minimum_size = Vector2(250, 250)
	_keep_photo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_keep_photo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	v.add_child(_keep_photo)
	_keep_caption = Label.new()
	_keep_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_keep_caption.add_theme_font_size_override("font_size", 24)
	_keep_caption.add_theme_color_override("font_color", INK.lightened(0.2))
	v.add_child(_keep_caption)
	box.add_child(card)
	box.move_child(card, 1)


func _build_note_panel() -> void:
	_note_panel = ColorRect.new()
	(_note_panel as ColorRect).color = Color(0.12, 0.1, 0.14, 0.55)
	_note_panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_note_panel.visible = false
	add_child(_note_panel)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_note_panel.add_child(center)
	var paper := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1.0, 0.97, 0.89)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(36)
	sb.shadow_color = Color(0, 0, 0, 0.3)
	sb.shadow_size = 12
	paper.add_theme_stylebox_override("panel", sb)
	paper.custom_minimum_size = Vector2(620, 0)
	paper.rotation = -0.015
	center.add_child(paper)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 18)
	paper.add_child(v)
	_note_title = Label.new()
	_note_title.add_theme_font_size_override("font_size", 32)
	_note_title.add_theme_color_override("font_color", INK)
	v.add_child(_note_title)
	_note_text = Label.new()
	_note_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_note_text.custom_minimum_size = Vector2(560, 0)
	_note_text.add_theme_font_size_override("font_size", 23)
	_note_text.add_theme_color_override("font_color", INK.lightened(0.15))
	v.add_child(_note_text)
	var close := MainMenu.styled_button("Close", 24)
	close.custom_minimum_size = Vector2(200, 64)
	close.size_flags_horizontal = Control.SIZE_SHRINK_END
	close.pressed.connect(func():
		_note_panel.visible = false
		Sfx.play("paper", -8.0))
	v.add_child(close)


func _on_panel(act: String) -> void:
	get_tree().paused = false
	if act == "resume":
		_pause_panel.visible = false
		return
	if game:
		game.on_hud_action(act)
