class_name CharmView
extends PanelContainer
## A charm slot. Shows an empty slot when `charm` is empty. Emits `tapped` when touched.

signal tapped(view: CharmView)

const SIZE := Vector2(124, 84)
const RARITY_COLORS := [Color("#7fb8ff"), Color("#7be0a1"), Color("#f2b544")]

var charm: Dictionary = {}
var index := -1


func setup(ch: Dictionary, idx: int) -> CharmView:
	charm = ch
	index = idx
	custom_minimum_size = SIZE
	var sb := StyleBoxFlat.new()
	sb.set_corner_radius_all(10)
	sb.set_content_margin_all(6)
	if ch.is_empty():
		sb.bg_color = Color(1, 1, 1, 0.04)
		sb.set_border_width_all(2)
		sb.border_color = Color(1, 1, 1, 0.12)
	else:
		sb.bg_color = Color("#3b2a78")
		sb.set_border_width_all(3)
		sb.border_color = RARITY_COLORS[Charms.rarity_of(ch)]
		var l := Label.new()
		l.text = Charms.name_of(ch)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.add_theme_font_size_override("font_size", 17)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(l)
	add_theme_stylebox_override("panel", sb)
	mouse_filter = Control.MOUSE_FILTER_STOP
	return self


func _gui_input(event: InputEvent) -> void:
	if charm.is_empty():
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		tapped.emit(self)
		accept_event()


func pulse() -> void:
	pivot_offset = size / 2.0
	var tw := create_tween()
	tw.tween_property(self, "scale", Vector2(1.15, 1.15), 0.07)
	tw.tween_property(self, "scale", Vector2.ONE, 0.12)
