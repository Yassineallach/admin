class_name MainMenu
extends Control
## Title screen + level select.

signal level_chosen(index: int)

const BG := Color(0.96, 0.93, 0.88)
const INK := Color(0.25, 0.2, 0.28)
const ACCENT := Color(0.94, 0.62, 0.52)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 48)
	add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 48)
	margin.add_child(row)

	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.alignment = BoxContainer.ALIGNMENT_CENTER
	left.add_theme_constant_override("separation", 14)
	row.add_child(left)

	var title := Label.new()
	title.text = "LENSFOLD"
	title.add_theme_font_size_override("font_size", 92)
	title.add_theme_color_override("font_color", INK)
	left.add_child(title)
	var sub := Label.new()
	sub.text = "Every photo is a place.\nA perspective puzzle inspired by Viewfinder."
	sub.add_theme_font_size_override("font_size", 26)
	sub.add_theme_color_override("font_color", INK.lightened(0.25))
	left.add_child(sub)

	var play := _button("Continue" if Progress.unlocked > 1 else "Play", 34)
	play.pressed.connect(func(): level_chosen.emit(mini(Progress.unlocked, Levels.count()) - 1))
	left.add_child(play)

	var sens_row := HBoxContainer.new()
	var sl := Label.new()
	sl.text = "Look speed"
	sl.add_theme_font_size_override("font_size", 22)
	sl.add_theme_color_override("font_color", INK)
	sens_row.add_child(sl)
	var slider := HSlider.new()
	slider.min_value = 0.3
	slider.max_value = 2.5
	slider.step = 0.05
	slider.value = float(Progress.settings["look_sensitivity"])
	slider.custom_minimum_size = Vector2(260, 40)
	slider.value_changed.connect(func(v):
		Progress.settings["look_sensitivity"] = v
		Progress.save_progress())
	sens_row.add_child(slider)
	left.add_child(sens_row)

	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 16)
	var right := CenterContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_child(grid)
	row.add_child(right)
	for i in Levels.count():
		var lv := Levels.get_level(i)
		var locked := i + 1 > Progress.unlocked
		var label: String = lv["name"]
		if Progress.completed.has(i):
			label += "  ✓"
		var b := _button(label, 24)
		b.custom_minimum_size = Vector2(300, 78)
		b.disabled = locked
		if locked:
			b.text = "🔒 " + label
		var idx := i
		b.pressed.connect(func(): level_chosen.emit(idx))
		grid.add_child(b)


func _button(text: String, fsize: int) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(320, 80)
	b.add_theme_font_size_override("font_size", fsize)
	var sb := StyleBoxFlat.new()
	sb.bg_color = ACCENT
	sb.set_corner_radius_all(14)
	b.add_theme_stylebox_override("normal", sb)
	var sbh := sb.duplicate()
	sbh.bg_color = ACCENT.lightened(0.15)
	b.add_theme_stylebox_override("hover", sbh)
	b.add_theme_stylebox_override("focus", sbh)
	var sbp := sb.duplicate()
	sbp.bg_color = ACCENT.darkened(0.15)
	b.add_theme_stylebox_override("pressed", sbp)
	var sbd := sb.duplicate()
	sbd.bg_color = Color(0.82, 0.8, 0.8)
	b.add_theme_stylebox_override("disabled", sbd)
	b.add_theme_color_override("font_color", Color.WHITE)
	b.add_theme_color_override("font_disabled_color", Color(0.55, 0.52, 0.55))
	return b
