class_name Hud
extends Control
## Touch-first HUD drawn entirely in `_draw` so that multi-touch works
## (left thumb on the stick while the right thumb looks / presses buttons).
## Mouse clicks arrive as emulated touches, so it also works on desktop.

var game  # Game (untyped to avoid a cyclic class reference)

var stick_vec := Vector2.ZERO
var rewind_held := false
var flash := 0.0
var fade := 0.0

var _buttons: Dictionary = {}  # name -> {c: Vector2, r: float, label: String}
var _touches: Dictionary = {}  # index -> {kind, name, origin, pos}
var _look_accum := Vector2.ZERO
var _title := ""
var _hint := ""
var _hint_time := 0.0
var _toast := ""
var _toast_time := 0.0
var _u := 1.0
var _font: Font
var _t := 0.0

var _pause_panel: Control
var _complete_panel: Control
var _complete_next: Button

const STICK_R := 85.0
const INK := Color(0.2, 0.18, 0.24)
const PAPER := Color(1, 0.98, 0.94)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_font = ThemeDB.fallback_font
	_pause_panel = _make_panel("Paused", [["Resume", "resume"], ["Restart level", "restart"], ["Main menu", "menu"]])
	_complete_panel = _make_panel("Teleporter reached!", [["Next level", "next"], ["Replay", "restart"], ["Main menu", "menu"]])
	_complete_next = _complete_panel.find_child("Btn_next", true, false)
	resized.connect(_layout)
	_layout()


func set_title(title: String, hint: String) -> void:
	_title = title
	_hint = hint
	_hint_time = 14.0


func toast(msg: String) -> void:
	_toast = msg
	_toast_time = 2.8


func consume_look() -> Vector2:
	var v := _look_accum
	_look_accum = Vector2.ZERO
	return v


func toggle_pause() -> void:
	if _complete_panel.visible:
		return
	_pause_panel.visible = not _pause_panel.visible
	get_tree().paused = _pause_panel.visible


func show_complete(last: bool) -> void:
	_complete_next.text = "Finish" if last else "Next level"
	_complete_panel.visible = true
	_touches.clear()
	stick_vec = Vector2.ZERO
	rewind_held = false


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

func _layout() -> void:
	var s := size
	_u = clampf(minf(s.x / 1280.0, s.y / 720.0), 0.5, 3.0)
	var u := _u
	_buttons = {
		"jump": {"c": Vector2(s.x - 115 * u, s.y - 115 * u), "r": 68 * u, "label": "JUMP"},
		"act": {"c": Vector2(s.x - 265 * u, s.y - 80 * u), "r": 52 * u, "label": "GRAB"},
		"cam": {"c": Vector2(s.x - 115 * u, s.y - 280 * u), "r": 52 * u, "label": "CAM"},
		"shutter": {"c": Vector2(s.x - 290 * u, s.y - 250 * u), "r": 72 * u, "label": "SNAP"},
		"place": {"c": Vector2(s.x - 290 * u, s.y - 250 * u), "r": 72 * u, "label": "PLACE"},
		"rotl": {"c": Vector2(s.x - 345 * u, s.y - 385 * u), "r": 40 * u, "label": "⟲"},
		"rotr": {"c": Vector2(s.x - 235 * u, s.y - 385 * u), "r": 40 * u, "label": "⟳"},
		"rewind": {"c": Vector2(80 * u, s.y * 0.42), "r": 50 * u, "label": "REW"},
		"pause": {"c": Vector2(s.x - 48 * u, 48 * u), "r": 32 * u, "label": "II"},
	}


func _thumb_rect(i: int) -> Rect2:
	var u := _u
	return Rect2(Vector2(20 * u + i * 92 * u, 20 * u), Vector2(80 * u, 96 * u))


func _button_visible(name: String) -> bool:
	if game == null or not game.ready_to_play or game.completed:
		return name == "pause"
	match name:
		"cam": return game.has_camera
		"shutter": return game.camera_mode
		"place", "rotl", "rotr": return game.raised >= 0 and not game.camera_mode
	return true


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if _pause_panel.visible or _complete_panel.visible:
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
		# Drag the origin along so the stick never feels "stuck".
		t["origin"] = t["pos"] - d.normalized() * r
		d = d.normalized() * r
	var v := d / r
	stick_vec = Vector2(v.x, -v.y)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	_t += delta
	flash = maxf(0.0, flash - delta * 2.5)
	_hint_time = maxf(0.0, _hint_time - delta)
	_toast_time = maxf(0.0, _toast_time - delta)
	if game and game.ready_to_play:
		fade = maxf(0.0, fade - delta * 2.0)
	queue_redraw()


## True while the REWIND button (or the R key) is held.
func wants_rewind() -> bool:
	return rewind_held or Input.is_physical_key_pressed(KEY_R)


func _text(pos: Vector2, txt: String, fsize: int, col: Color, align := HORIZONTAL_ALIGNMENT_CENTER, width := -1.0) -> void:
	var fs := int(fsize * _u)
	if align == HORIZONTAL_ALIGNMENT_CENTER and width < 0:
		var w := _font.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		pos.x -= w * 0.5
	draw_string(_font, pos, txt, align, width, fs, col)


func _draw() -> void:
	if game == null:
		return
	var s := size
	var u := _u

	if game.camera_mode:
		_draw_viewfinder()

	# Rewind tint.
	var rewinding: bool = wants_rewind() or game._auto_rewind > 0
	if rewinding and game.ready_to_play:
		draw_rect(Rect2(Vector2.ZERO, s), Color(0.55, 0.42, 0.3, 0.28))
		var a := 0.6 + 0.4 * sin(_t * 8.0)
		_text(Vector2(s.x * 0.5, s.y * 0.2), "◀◀  REWIND", 40, Color(1, 0.95, 0.85, a))

	# Stick.
	for t in _touches.values():
		if t["kind"] == "stick":
			draw_circle(t["origin"], STICK_R * u, Color(1, 1, 1, 0.12))
			draw_arc(t["origin"], STICK_R * u, 0, TAU, 48, Color(1, 1, 1, 0.5), 3 * u, true)
			var knob: Vector2 = t["origin"] + Vector2(stick_vec.x, -stick_vec.y) * STICK_R * u
			draw_circle(knob, 34 * u, Color(1, 1, 1, 0.55))
	if not _touches.values().any(func(t): return t["kind"] == "stick"):
		var c := Vector2(170 * u, s.y - 160 * u)
		draw_arc(c, STICK_R * u, 0, TAU, 48, Color(1, 1, 1, 0.22), 2 * u, true)
		_text(c + Vector2(0, 8 * u), "MOVE", 18, Color(1, 1, 1, 0.35))

	# Buttons.
	for name in _buttons.keys():
		if not _button_visible(name):
			continue
		var b: Dictionary = _buttons[name]
		var pressed := _touches.values().any(func(t): return t["name"] == name)
		var col := Color(1, 1, 1, 0.5 if pressed else 0.28)
		if name == "shutter" or name == "place":
			col = Color(1, 0.55, 0.45, 0.75 if pressed else 0.55)
		draw_circle(b["c"], b["r"], col)
		draw_arc(b["c"], b["r"], 0, TAU, 48, Color(1, 1, 1, 0.8), 2.5 * u, true)
		var label: String = b["label"]
		if name == "act" and game.held != null:
			label = "DROP"
		_text(b["c"] + Vector2(0, 9 * u), label, 24 if b["r"] > 45 * u else 20, INK)
	if game.has_camera and game.film >= 0:
		var cb: Dictionary = _buttons["cam"]
		_text(cb["c"] + Vector2(0, cb["r"] + 26 * u), "film %d" % game.film, 18, Color(1, 1, 1, 0.9))

	# Photo tray.
	for i in game.photos.size():
		var r := _thumb_rect(i)
		var lifted: bool = game.raised == i
		if lifted:
			r.position.y += 10 * u
		draw_rect(r, PAPER)
		var inner := Rect2(r.position + Vector2(6, 6) * u, Vector2(r.size.x - 12 * u, r.size.x - 12 * u))
		var p: Photo = game.photos[i]
		if p.texture:
			draw_texture_rect(p.texture, inner, false)
		else:
			draw_rect(inner, Color(0.7, 0.8, 0.85))
		if lifted:
			draw_rect(r, Color(1, 0.55, 0.45), false, 4 * u)
		_text(Vector2(r.get_center().x, r.end.y - 4 * u), str(i + 1), 14, INK)

	# Title + hint.
	if _hint_time > 0.0 and game.ready_to_play:
		var a := clampf(_hint_time, 0.0, 1.0)
		var w := minf(s.x * 0.5, 660 * u)
		var box := Rect2(Vector2((s.x - w) * 0.5, 14 * u), Vector2(w, 112 * u))
		draw_rect(box, Color(0.15, 0.13, 0.18, 0.55 * a))
		_text(box.position + Vector2(w * 0.5, 30 * u), _title, 22, Color(1, 0.9, 0.75, a))
		draw_multiline_string(_font, box.position + Vector2(16 * u, 56 * u), _hint,
			HORIZONTAL_ALIGNMENT_CENTER, w - 32 * u, int(17 * u), 4, Color(1, 1, 1, a))

	if _toast_time > 0.0:
		var a := clampf(_toast_time, 0.0, 1.0)
		var tw := _font.get_string_size(_toast, HORIZONTAL_ALIGNMENT_LEFT, -1, int(24 * u)).x
		draw_rect(Rect2(Vector2((s.x - tw) * 0.5 - 16 * u, s.y * 0.68 - 32 * u), Vector2(tw + 32 * u, 46 * u)), Color(0.15, 0.13, 0.18, 0.5 * a))
		_text(Vector2(s.x * 0.5, s.y * 0.68), _toast, 24, Color(1, 1, 1, a))

	# Crosshair dot.
	if not game.camera_mode:
		draw_circle(s * 0.5, 3 * u, Color(1, 1, 1, 0.7))

	if flash > 0.0:
		draw_rect(Rect2(Vector2.ZERO, s), Color(1, 1, 1, flash * 0.8))
	if fade > 0.0:
		draw_rect(Rect2(Vector2.ZERO, s), Color(0.96, 0.93, 0.88, fade))
		_text(s * 0.5, "developing…", 26, Color(0.4, 0.35, 0.4, fade))


func _draw_viewfinder() -> void:
	var s := size
	var u := _u
	# Square frame matching the photo frustum exactly.
	var half_h := s.y * 0.5 * Photo.T / tan(deg_to_rad(Player.FOV * 0.5))
	var c := s * 0.5
	var r := Rect2(c - Vector2(half_h, half_h), Vector2(half_h, half_h) * 2.0)
	var dim := Color(0, 0, 0, 0.35)
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
	draw_line(c - Vector2(14, 0) * u, c + Vector2(14, 0) * u, col, 2 * u)
	draw_line(c - Vector2(0, 14) * u, c + Vector2(0, 14) * u, col, 2 * u)
	if absf(game.player.pitch) < deg_to_rad(6.0):
		_text(Vector2(c.x, r.end.y + 34 * u), "level", 18, Color(0.7, 1, 0.8))
	elif absf(game.player.pitch) > deg_to_rad(86.0):
		_text(Vector2(c.x, r.end.y + 34 * u), "vertical", 18, Color(0.7, 1, 0.8))


# ---------------------------------------------------------------------------
# Menus (regular Buttons: they only need single touch)
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
	box.add_theme_constant_override("separation", 18)
	center.add_child(box)
	var lbl := Label.new()
	lbl.text = title
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", 44)
	box.add_child(lbl)
	for e in entries:
		var b := Button.new()
		b.name = "Btn_" + e[1]
		b.text = e[0]
		b.custom_minimum_size = Vector2(380, 84)
		b.add_theme_font_size_override("font_size", 30)
		var act: String = e[1]
		b.pressed.connect(func(): _on_panel(act))
		box.add_child(b)
	return root


func _on_panel(act: String) -> void:
	get_tree().paused = false
	if act == "resume":
		_pause_panel.visible = false
		return
	if game:
		game.on_hud_action(act)
