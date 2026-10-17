class_name UI
extends RefCounted
## Shared look & feel: palette, fonts, styled widgets and juicy animations.

const BG_TOP := Color("1a1140")
const BG_BOTTOM := Color("3a1f6e")
const ACCENT := Color("7c5cff")
const ACCENT_2 := Color("ff5ca8")
const GOLD := Color("ffc93c")
const GREEN := Color("2ed47a")
const RED := Color("ff4d6d")
const INK := Color("1d1838")
const PAPER := Color("fbf9ff")
const MUTED := Color("9b93c9")
const CARD := Color(1, 1, 1, 0.08)

static var _font: Font
static var _font_bold: Font
static var _theme: Theme

static func font(bold := true) -> Font:
	if _font == null:
		var names := PackedStringArray(["Nunito", "Poppins", "Montserrat", "Roboto", "Noto Sans", "Segoe UI", "Helvetica", "sans-serif"])
		var f := SystemFont.new()
		f.font_names = names
		f.font_weight = 500
		f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
		_font = f
		var b := SystemFont.new()
		b.font_names = names
		b.font_weight = 800
		_font_bold = b
	return _font_bold if bold else _font

static func theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = font(false)
	t.default_font_size = 26
	t.set_color("font_color", "Label", Color.WHITE)
	for state in ["normal", "hover", "pressed", "disabled", "focus"]:
		t.set_stylebox(state, "Button", box(ACCENT, 26))
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	t.set_font("font", "Button", font(true))
	t.set_font_size("font_size", "Button", 28)
	t.set_color("font_color", "Button", Color.WHITE)
	t.set_color("font_hover_color", "Button", Color.WHITE)
	t.set_color("font_pressed_color", "Button", Color.WHITE)
	t.set_color("font_focus_color", "Button", Color.WHITE)
	t.set_color("font_disabled_color", "Button", Color(1, 1, 1, 0.45))
	t.set_stylebox("panel", "PanelContainer", box(CARD, 28))
	var grabber := box(Color(1, 1, 1, 0.25), 6)
	t.set_stylebox("grabber", "VScrollBar", grabber)
	t.set_stylebox("grabber_highlight", "VScrollBar", grabber)
	t.set_stylebox("grabber_pressed", "VScrollBar", grabber)
	t.set_stylebox("scroll", "VScrollBar", StyleBoxEmpty.new())
	t.set_constant("separation", "VBoxContainer", 16)
	t.set_constant("separation", "HBoxContainer", 12)
	_theme = t
	return t

static func box(color: Color, radius := 24, shadow := 0, border := 0, border_color := Color.TRANSPARENT) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = color
	s.set_corner_radius_all(radius)
	s.anti_aliasing = true
	s.content_margin_left = 22
	s.content_margin_right = 22
	s.content_margin_top = 14
	s.content_margin_bottom = 14
	if shadow > 0:
		s.shadow_color = Color(0, 0, 0, 0.35)
		s.shadow_size = shadow
		s.shadow_offset = Vector2(0, shadow * 0.5)
	if border > 0:
		s.set_border_width_all(border)
		s.border_color = border_color
	return s

static func label(text: String, size := 26, color := Color.WHITE, bold := false, align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", font(bold))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

## Chunky 3D-looking button: a darker "lip" under the face that collapses when pressed.
static func button(text: String, color := ACCENT, size := 28, min_h := 84) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, min_h)
	b.add_theme_font_size_override("font_size", size)
	var normal := box(color, 26)
	normal.border_width_bottom = 8
	normal.border_color = color.darkened(0.35)
	var hover := normal.duplicate()
	hover.bg_color = color.lightened(0.08)
	var pressed := box(color.darkened(0.08), 26)
	pressed.border_width_top = 6
	pressed.border_color = Color(0, 0, 0, 0)
	pressed.content_margin_top = 18
	var disabled := box(Color(0.5, 0.5, 0.6, 0.35), 26)
	b.add_theme_stylebox_override("normal", normal)
	b.add_theme_stylebox_override("hover", hover)
	b.add_theme_stylebox_override("pressed", pressed)
	b.add_theme_stylebox_override("disabled", disabled)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.pressed.connect(func(): Sfx.play("tap"); Sfx.buzz(12))
	return b

static func flat_button(text: String, size := 28, color := Color.WHITE) -> Button:
	var b := Button.new()
	b.text = text
	b.flat = true
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", color)
	b.add_theme_color_override("font_hover_color", color.lightened(0.2))
	b.add_theme_color_override("font_pressed_color", color.darkened(0.2))
	var empty := StyleBoxEmpty.new()
	for s in ["normal", "hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(s, empty)
	b.pressed.connect(func(): Sfx.play("tap"))
	return b

static func panel(color := CARD, radius := 28, shadow := 0) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(color, radius, shadow))
	return p

static func pill(text: String, color := Color(0, 0, 0, 0.28)) -> PanelContainer:
	var p := PanelContainer.new()
	var s := box(color, 40)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 6
	s.content_margin_bottom = 6
	p.add_theme_stylebox_override("panel", s)
	var l := label(text, 26, Color.WHITE, true, HORIZONTAL_ALIGNMENT_CENTER)
	l.name = "Label"
	p.add_child(l)
	return p

static func margin(child: Control, left := 24, top := 24, right := 24, bottom := 24) -> MarginContainer:
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_left", left)
	m.add_theme_constant_override("margin_top", top)
	m.add_theme_constant_override("margin_right", right)
	m.add_theme_constant_override("margin_bottom", bottom)
	m.add_child(child)
	return m

static func progress_bar(value: float, color := GOLD, height := 14) -> Control:
	var bg := Panel.new()
	bg.custom_minimum_size = Vector2(0, height)
	bg.add_theme_stylebox_override("panel", box(Color(0, 0, 0, 0.3), height))
	var fill := Panel.new()
	fill.add_theme_stylebox_override("panel", box(color, height))
	fill.anchor_bottom = 1.0
	fill.anchor_right = clampf(value, 0.0, 1.0)
	fill.visible = value > 0.001
	bg.add_child(fill)
	return bg

static func stars_text(n: int, total := 3) -> String:
	return "★".repeat(n) + "☆".repeat(total - n)

# ---------- motion ----------

static func center_pivot(c: Control) -> void:
	c.pivot_offset = c.size * 0.5

static func pop(c: Control, strength := 1.15, time := 0.28) -> void:
	center_pivot(c)
	var tw := c.create_tween()
	tw.tween_property(c, "scale", Vector2.ONE * strength, time * 0.4).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(c, "scale", Vector2.ONE, time * 0.6).set_trans(Tween.TRANS_SINE)

static func shake(c: Control, amount := 14.0) -> void:
	var x := c.position.x
	var tw := c.create_tween()
	for i in 5:
		tw.tween_property(c, "position:x", x + (amount if i % 2 == 0 else -amount) * (1.0 - i * 0.18), 0.04)
	tw.tween_property(c, "position:x", x, 0.04)

static func appear(c: Control, delay := 0.0, from := Vector2(0, 40)) -> void:
	c.modulate.a = 0.0
	var tw := c.create_tween()
	tw.tween_interval(delay)
	tw.tween_callback(func():
		c.position += from
		var t2 := c.create_tween().set_parallel()
		t2.tween_property(c, "modulate:a", 1.0, 0.3)
		t2.tween_property(c, "position", c.position - from, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT))

static func format_time(seconds: float) -> String:
	var s := int(seconds)
	return "%d:%02d" % [s / 60, s % 60]
