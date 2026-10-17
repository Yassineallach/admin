class_name UI
extends RefCounted
## Lexigo design system: colour tokens, type scale, chunky "3D" buttons,
## illustration loading and motion helpers. The interface uses words, not
## icons or emoji; the only pictures are Lexi and the world illustrations. See docs/DESIGN.md.

# ---------- colour tokens ----------
const WHITE := Color("ffffff")
const SNOW := Color("f7f7f7")       # surfaces
const CLOUD := Color("e5e5e5")      # borders, lips of white elements
const MIST := Color("afafaf")       # disabled, placeholders
const STONE := Color("777777")      # secondary text
const INK := Color("4b4b4b")        # primary text

const LEAF := Color("58cc02")       # primary action, success
const LEAF_LIP := Color("58a700")
const LEAF_PALE := Color("d7ffb8")
const SKY := Color("1cb0f6")        # selection, info, links
const SKY_LIP := Color("1899d6")
const SKY_PALE := Color("ddf4ff")
const BERRY := Color("ff4b4b")      # errors
const BERRY_LIP := Color("ea2b2b")
const BERRY_PALE := Color("ffdfe0")
const SUN := Color("ffc800")        # rewards, stars, coins
const SUN_LIP := Color("e5a500")
const FLAME := Color("ff9600")      # streak
const GRAPE := Color("ce82ff")      # special, examples
const GRAPE_LIP := Color("a560e8")

# Kept for older call sites: map to the new tokens.
const ACCENT := SKY
const ACCENT_2 := GRAPE
const GOLD := SUN
const GREEN := LEAF
const RED := BERRY
const MUTED := STONE
const PAPER := WHITE

# ---------- metrics (720-wide design viewport ≈ 2× dp) ----------
const LIP := 8              # bottom depth of pressable elements
const BORDER := 4           # outline width of white elements
const R_BUTTON := 26
const R_CARD := 32
const R_TILE := 20

const ART := "res://assets/art/"

static var _fonts := {}
static var _theme: Theme
static var _tex_cache := {}

## weight: 500 regular … 800 extra bold. caps=true adds tracking for uppercase labels.
static func font(bold := true, caps := false) -> Font:
	var key := "%s%s" % [bold, caps]
	if _fonts.has(key):
		return _fonts[key]
	var base: FontFile = load("res://assets/fonts/Nunito.ttf")
	var f := FontVariation.new()
	f.base_font = base
	f.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 800 if bold else 650}
	if caps:
		f.spacing_glyph = 1
	_fonts[key] = f
	return f

static func theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = font(false)
	t.default_font_size = 30
	t.set_color("font_color", "Label", INK)
	t.set_font("font", "Button", font(true, true))
	t.set_font_size("font_size", "Button", 28)
	var grabber := box(CLOUD, 6)
	t.set_stylebox("grabber", "VScrollBar", grabber)
	t.set_stylebox("grabber_highlight", "VScrollBar", grabber)
	t.set_stylebox("grabber_pressed", "VScrollBar", grabber)
	t.set_stylebox("scroll", "VScrollBar", StyleBoxEmpty.new())
	t.set_constant("separation", "VBoxContainer", 16)
	t.set_constant("separation", "HBoxContainer", 12)
	_theme = t
	return t

# ---------- style boxes ----------

static func box(color: Color, radius := R_CARD, border := 0, border_color := CLOUD, lip := 0, lip_color := CLOUD) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = color
	s.set_corner_radius_all(radius)
	s.anti_aliasing = true
	s.content_margin_left = 24
	s.content_margin_right = 24
	s.content_margin_top = 16
	s.content_margin_bottom = 16
	if border > 0:
		s.set_border_width_all(border)
		s.border_color = border_color
	if lip > 0:
		s.border_width_bottom = border + lip
		s.border_color = border_color if border > 0 else lip_color
	return s

## An outlined white card with a lip, the default container.
static func card_box(selected := false, radius := R_CARD) -> StyleBoxFlat:
	if selected:
		return box(SKY_PALE, radius, BORDER, Color("84d8ff"), 2)
	return box(WHITE, radius, BORDER, CLOUD, 2)

# ---------- text ----------

static func label(text: String, size := 30, color := INK, bold := false, align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", font(bold))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

static func caps(text: String, size := 24, color := STONE) -> Label:
	var l := label(text.to_upper(), size, color, true)
	l.add_theme_font_override("font", font(true, true))
	return l

# ---------- buttons ----------

const KINDS := {
	"primary": [LEAF, LEAF_LIP, WHITE],
	"secondary": [SKY, SKY_LIP, WHITE],
	"danger": [BERRY, BERRY_LIP, WHITE],
	"reward": [SUN, SUN_LIP, WHITE],
	"special": [GRAPE, GRAPE_LIP, WHITE],
	"outline": [WHITE, CLOUD, SKY],
	"neutral": [WHITE, CLOUD, INK],
	"ghost": [Color(0, 0, 0, 0), Color(0, 0, 0, 0), SKY],
}

## Chunky button: the lip collapses and the face drops when pressed.
static func button(text: String, kind := "primary", size := 28, min_h := 96) -> Button:
	var b := Button.new()
	b.text = text.to_upper() if kind != "neutral" else text
	b.custom_minimum_size = Vector2(0, min_h)
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", font(true, kind != "neutral"))
	b.add_theme_font_size_override("font_size", size)
	style_button(b, kind)
	b.pressed.connect(func(): Sfx.play("tap"); Sfx.buzz(12))
	return b

static func style_button(b: Button, kind: String, radius := R_BUTTON) -> void:
	var k: Array = KINDS[kind]
	var face: Color = k[0]
	var lip: Color = k[1]
	var text: Color = k[2]
	var outlined := face == WHITE
	var normal := box(face, radius, BORDER if outlined else 0, CLOUD, LIP, lip)
	if kind == "ghost":
		normal = box(face, radius)
	var hover := normal.duplicate()
	hover.bg_color = face.lightened(0.06) if not outlined else SNOW
	var pressed := normal.duplicate()
	pressed.border_width_bottom = BORDER if outlined else 0
	pressed.content_margin_top += LIP
	pressed.expand_margin_top = -LIP
	pressed.content_margin_bottom -= 0
	var disabled := box(CLOUD, radius, 0, CLOUD, LIP, Color("d0d0d0"))
	b.add_theme_stylebox_override("normal", normal)
	b.add_theme_stylebox_override("hover", hover)
	b.add_theme_stylebox_override("pressed", pressed)
	b.add_theme_stylebox_override("disabled", disabled)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "font_hover_pressed_color"]:
		b.add_theme_color_override(c, text)
	b.add_theme_color_override("font_disabled_color", MIST)

static func flat_button(text: String, size := 30, color := SKY) -> Button:
	var b := Button.new()
	b.text = text
	b.flat = true
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", font(true))
	b.add_theme_font_size_override("font_size", size)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(c, color)
	var empty := StyleBoxEmpty.new()
	for s in ["normal", "hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(s, empty)
	b.pressed.connect(func(): Sfx.play("tap"))
	return b

# ---------- art ----------

## Rasterises an SVG from assets/art at the requested pixel size (cached).
static func art_texture(rel_path: String, px: float) -> Texture2D:
	var key := "%s@%d" % [rel_path, int(px)]
	if _tex_cache.has(key):
		return _tex_cache[key]
	var text := FileAccess.get_file_as_string(ART + rel_path)
	if text == "":
		return null
	var probe := Image.new()
	probe.load_svg_from_string(text, 1.0)
	var scale := px / maxf(1.0, maxf(probe.get_width(), probe.get_height()))
	var img := Image.new()
	img.load_svg_from_string(text, scale)
	var tex := ImageTexture.create_from_image(img)
	_tex_cache[key] = tex
	return tex

static func art(rel_path: String, px: float) -> TextureRect:
	var r := TextureRect.new()
	r.texture = art_texture(rel_path, px)
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.custom_minimum_size = Vector2(px, px)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r

## Illustration for a vocabulary word: assets/art/words/<world>/<english>.svg
static func word_texture(word: Dictionary, px := 112.0) -> Texture2D:
	return art_texture("words/%s/%s.svg" % [word["world"], word["t"]["en"]], px)

static func word_art(word: Dictionary, px := 112.0) -> TextureRect:
	var r := art("words/%s/%s.svg" % [word["world"], word["t"]["en"]], px)
	return r

static func mascot(pose: String, px := 200.0) -> TextureRect:
	return art("mascot/lexi_%s.svg" % pose, px)

# ---------- composites ----------

static func panel(style: StyleBox) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", style)
	return p

## Number over a small caps caption, as used in the stats bar.
static func stat(caption: String, value: String, color: Color) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", -6)
	var l := label(value, 32, color, true, HORIZONTAL_ALIGNMENT_CENTER)
	l.name = "Value"
	v.add_child(l)
	var c := caps(caption, 16, STONE)
	c.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(c)
	return v

static func margin(child: Control, left := 24, top := 24, right := 24, bottom := 24) -> MarginContainer:
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_left", left)
	m.add_theme_constant_override("margin_top", top)
	m.add_theme_constant_override("margin_right", right)
	m.add_theme_constant_override("margin_bottom", bottom)
	m.add_child(child)
	return m

## Rounded progress bar with the glossy highlight stripe.
static func progress_bar(value: float, color := LEAF, height := 32) -> Control:
	var bg := Panel.new()
	bg.custom_minimum_size = Vector2(0, height)
	bg.add_theme_stylebox_override("panel", box(CLOUD, height))
	var fill := Panel.new()
	fill.name = "Fill"
	fill.add_theme_stylebox_override("panel", box(color, height))
	fill.anchor_bottom = 1.0
	fill.anchor_right = clampf(value, 0.0, 1.0)
	fill.visible = value > 0.001
	bg.add_child(fill)
	var shine := Panel.new()
	shine.add_theme_stylebox_override("panel", box(Color(1, 1, 1, 0.3), height))
	shine.anchor_left = 0.0
	shine.anchor_right = 1.0
	shine.offset_left = height * 0.5
	shine.offset_right = -height * 0.5
	shine.offset_top = height * 0.22
	shine.offset_bottom = height * 0.42
	shine.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fill.add_child(shine)
	return bg

static func set_progress(bar: Control, value: float, animate := true) -> void:
	var fill: Panel = bar.get_node("Fill")
	fill.visible = value > 0.001
	if animate:
		bar.create_tween().tween_property(fill, "anchor_right", clampf(value, 0.0, 1.0), 0.4).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	else:
		fill.anchor_right = clampf(value, 0.0, 1.0)

## Speech bubble with a small tail on the left, for the mascot.
static func bubble(content: Control) -> PanelContainer:
	var p := panel(box(WHITE, R_CARD, BORDER, CLOUD))
	p.add_child(content)
	return p

static func spacer(h := 16, expand := false) -> Control:
	var c := Control.new()
	c.custom_minimum_size.y = h
	if expand:
		c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return c

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

static func appear(c: Control, delay := 0.0) -> void:
	c.modulate.a = 0.0
	var tw := c.create_tween()
	tw.tween_interval(delay)
	tw.tween_property(c, "modulate:a", 1.0, 0.3)

## Gentle idle bob, used on the mascot.
static func bob(c: Control, amount := 8.0, period := 1.6) -> void:
	var tw := c.create_tween().set_loops()
	tw.tween_property(c, "position:y", -amount, period * 0.5).as_relative().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(c, "position:y", amount, period * 0.5).as_relative().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

static func format_time(seconds: float) -> String:
	var s := int(seconds)
	return "%d:%02d" % [s / 60, s % 60]
