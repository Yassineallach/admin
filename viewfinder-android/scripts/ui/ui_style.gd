class_name UiStyle
extends RefCounted
## Shared look for menus and HUD: chunky slanted bold type, deep-blue panels
## and bright yellow buttons with a drop shadow (an original cartoon
## battle-royale-style theme; no third-party fonts or art).

const NAVY := Color(0.07, 0.13, 0.38)
const BLUE := Color(0.12, 0.42, 0.95)
const YELLOW := Color(1.0, 0.84, 0.16)
const INK := Color(0.08, 0.10, 0.25)

static var _display: FontVariation


## Engine font made heavy and slanted for titles and buttons.
static func display_font() -> Font:
	if _display == null:
		_display = FontVariation.new()
		_display.base_font = ThemeDB.fallback_font
		_display.variation_embolden = 1.1
		_display.variation_transform = Transform2D(Vector2(1.0, 0.0), Vector2(-0.2, 1.0), Vector2.ZERO)
		_display.spacing_glyph = 1
	return _display


static func button(text: String, fsize: int) -> Button:
	var b := Button.new()
	b.text = text.to_upper()
	b.custom_minimum_size = Vector2(320, 80)
	b.add_theme_font_override("font", display_font())
	b.add_theme_font_size_override("font_size", fsize)
	var sb := StyleBoxFlat.new()
	sb.bg_color = YELLOW
	sb.set_corner_radius_all(6)
	sb.border_width_bottom = 5
	sb.border_color = YELLOW.darkened(0.3)
	sb.shadow_color = Color(0, 0, 0, 0.3)
	sb.shadow_size = 4
	sb.shadow_offset = Vector2(0, 3)
	sb.skew = Vector2(0.12, 0)
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	b.add_theme_stylebox_override("normal", sb)
	var sbh: StyleBoxFlat = sb.duplicate()
	sbh.bg_color = YELLOW.lightened(0.25)
	b.add_theme_stylebox_override("hover", sbh)
	b.add_theme_stylebox_override("focus", sbh)
	var sbp: StyleBoxFlat = sb.duplicate()
	sbp.bg_color = YELLOW.darkened(0.12)
	sbp.border_width_bottom = 2
	b.add_theme_stylebox_override("pressed", sbp)
	var sbd: StyleBoxFlat = sb.duplicate()
	sbd.bg_color = Color(0.32, 0.38, 0.6, 0.85)
	sbd.border_color = Color(0.2, 0.24, 0.42)
	b.add_theme_stylebox_override("disabled", sbd)
	b.add_theme_color_override("font_color", INK)
	b.add_theme_color_override("font_hover_color", INK)
	b.add_theme_color_override("font_pressed_color", INK)
	b.add_theme_color_override("font_focus_color", INK)
	b.add_theme_color_override("font_disabled_color", Color(0.75, 0.8, 0.95))
	return b
