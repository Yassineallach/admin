class_name CardView
extends Control
## A playing card drawn entirely in code. Emits `tapped` when touched.

signal tapped(view: CardView)
## Emitted when the card is held down instead of tapped.
signal inspected(view: CardView)

const CARD_SIZE := Vector2(80, 116)
const FACE := Color("#f6f1e7")
const SUIT_COLORS := [Color("#d93a55"), Color("#e8841c"), Color("#16927f"), Color("#2b3a67")]
const ENH_COLORS := {
	"bonus": Color("#3fa7f5"),
	"spark": Color("#f2545b"),
	"glass": Color("#9fe3f0"),
	"iron": Color("#8a8f9c"),
}
const SELECTED_BORDER := Color("#f2b544")
const RAISE := 24.0
const HOLD_TIME := 0.4

var card: Dictionary = {}
var interactive := true
var selected := false:
	set(v):
		selected = v
		queue_redraw()
var dimmed := false:
	set(v):
		dimmed = v
		queue_redraw()
var _press_time := -1.0
var _hold_fired := false
var _glow_t := 0.0
var lift := 0.0:
	set(v):
		lift = v
		queue_redraw()


func setup(c: Dictionary, can_tap := true) -> CardView:
	card = c
	interactive = can_tap
	custom_minimum_size = CARD_SIZE
	size_flags_vertical = Control.SIZE_SHRINK_END
	mouse_filter = Control.MOUSE_FILTER_STOP if can_tap else Control.MOUSE_FILTER_IGNORE
	return self


func _gui_input(event: InputEvent) -> void:
	if not interactive:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_press_time = Time.get_ticks_msec() / 1000.0
			_hold_fired = false
		elif _press_time >= 0.0:
			_press_time = -1.0
			if not _hold_fired:
				tapped.emit(self)
		accept_event()


func _process(delta: float) -> void:
	if _press_time >= 0.0 and not _hold_fired and Time.get_ticks_msec() / 1000.0 - _press_time >= HOLD_TIME:
		_hold_fired = true
		inspected.emit(self)
		bump()
	if selected:
		_glow_t += delta
		queue_redraw()


func bump() -> void:
	var tw := create_tween()
	tw.tween_property(self, "lift", -18.0, 0.07)
	tw.tween_property(self, "lift", 0.0, 0.12)


func _draw() -> void:
	if card.is_empty():
		return
	var r := Rect2(Vector2(0, lift - (RAISE if selected else 0.0)), size)
	var shadow := StyleBoxFlat.new()
	shadow.bg_color = Color(0, 0, 0, 0.35)
	shadow.set_corner_radius_all(10)
	draw_style_box(shadow, Rect2(r.position + Vector2(3, 5), r.size))
	if selected:
		var glow := StyleBoxFlat.new()
		glow.bg_color = Color(0, 0, 0, 0)
		glow.set_corner_radius_all(12)
		glow.shadow_color = Color(SELECTED_BORDER, 0.35 + 0.25 * sin(_glow_t * 5.0))
		glow.shadow_size = 12
		draw_style_box(glow, r)

	var enh: String = card.enh
	var sb := StyleBoxFlat.new()
	sb.bg_color = FACE
	if enh == "glass":
		sb.bg_color = Color("#e3f7fb")
	elif enh == "iron":
		sb.bg_color = Color("#d5d8de")
	sb.set_corner_radius_all(10)
	sb.set_border_width_all(4 if selected or enh != "" else 2)
	sb.border_color = SELECTED_BORDER if selected else ENH_COLORS.get(enh, Color("#c9bfae"))
	draw_style_box(sb, r)

	var col: Color = SUIT_COLORS[card.suit]
	var font := ThemeDB.fallback_font
	draw_string(font, r.position + Vector2(8, 30), HandEval.rank_text(card.rank), HORIZONTAL_ALIGNMENT_LEFT, -1, 26, col)
	draw_suit(self, card.suit, r.position + Vector2(18, 46), 8.0, col)
	draw_suit(self, card.suit, r.position + Vector2(r.size.x * 0.58, r.size.y * 0.62), 20.0, col)
	if enh != "":
		var label: String = Scoring.ENHANCEMENTS[enh].name.to_upper()
		draw_string(font, r.position + Vector2(0, r.size.y - 8), label, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 13, ENH_COLORS[enh].darkened(0.25))
	if dimmed:
		var dim := StyleBoxFlat.new()
		dim.bg_color = Color(0.05, 0.03, 0.12, 0.55)
		dim.set_corner_radius_all(10)
		draw_style_box(dim, r)


## Draws a suit symbol from basic shapes so no special font glyphs are needed.
static func draw_suit(ci: CanvasItem, suit: int, c: Vector2, s: float, col: Color) -> void:
	match suit:
		0: # heart
			ci.draw_circle(c + Vector2(-0.5 * s, -0.25 * s), 0.52 * s, col)
			ci.draw_circle(c + Vector2(0.5 * s, -0.25 * s), 0.52 * s, col)
			ci.draw_colored_polygon(PackedVector2Array([c + Vector2(-1.0 * s, -0.05 * s), c + Vector2(1.0 * s, -0.05 * s), c + Vector2(0, 1.0 * s)]), col)
		1: # diamond
			ci.draw_colored_polygon(PackedVector2Array([c + Vector2(0, -1.0 * s), c + Vector2(0.72 * s, 0), c + Vector2(0, 1.0 * s), c + Vector2(-0.72 * s, 0)]), col)
		2: # club
			ci.draw_circle(c + Vector2(0, -0.5 * s), 0.42 * s, col)
			ci.draw_circle(c + Vector2(-0.48 * s, 0.1 * s), 0.42 * s, col)
			ci.draw_circle(c + Vector2(0.48 * s, 0.1 * s), 0.42 * s, col)
			ci.draw_circle(c + Vector2(0, -0.05 * s), 0.3 * s, col)
			ci.draw_colored_polygon(PackedVector2Array([c + Vector2(0, -0.1 * s), c + Vector2(-0.32 * s, 1.0 * s), c + Vector2(0.32 * s, 1.0 * s)]), col)
		3: # spade
			ci.draw_circle(c + Vector2(-0.5 * s, 0.2 * s), 0.5 * s, col)
			ci.draw_circle(c + Vector2(0.5 * s, 0.2 * s), 0.5 * s, col)
			ci.draw_colored_polygon(PackedVector2Array([c + Vector2(0, -1.0 * s), c + Vector2(-0.98 * s, 0.1 * s), c + Vector2(0.98 * s, 0.1 * s)]), col)
			ci.draw_colored_polygon(PackedVector2Array([c + Vector2(0, 0.2 * s), c + Vector2(-0.32 * s, 1.0 * s), c + Vector2(0.32 * s, 1.0 * s)]), col)
