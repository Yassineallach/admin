extends Control
## Renders every card in the game to build/shots/card_sheet.png. Run with a display:
##   godot --path . --resolution 1340x1500 res://tests/card_sheet.tscn

const GOLD := Color("#f2b544")
const TEXT := Color("#f3ecff")
const SOFT := Color("#b5a8d6")


func _ready() -> void:
	get_tree().root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	var bg := ColorRect.new()
	bg.color = Color("#170f38")
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 14)
	margin.add_child(root)

	root.add_child(_label("Aleatro: every card", 34, GOLD))
	for suit in 4:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		var name_l := _label(HandEval.SUIT_NAMES[suit], 20, SOFT)
		name_l.custom_minimum_size = Vector2(100, 0)
		row.add_child(name_l)
		for r in range(2, 15):
			row.add_child(CardView.new().setup({"id": 0, "rank": r, "suit": suit, "enh": ""}, false))
		root.add_child(row)

	root.add_child(_label("Enhancements (applied by sigils)", 24, GOLD))
	var enh_row := HBoxContainer.new()
	enh_row.add_theme_constant_override("separation", 12)
	for enh in Scoring.ENHANCEMENTS:
		enh_row.add_child(CardView.new().setup({"id": 0, "rank": 13, "suit": 0, "enh": enh}, false))
		enh_row.add_child(_wrapped("%s\n%s" % [Scoring.ENHANCEMENTS[enh].name, Scoring.ENHANCEMENTS[enh].desc], 17, 190))
	root.add_child(enh_row)

	root.add_child(_label("Charms  (blue = common, green = uncommon, gold = rare)", 24, GOLD))
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 10)
	var i := 0
	for id in Charms.DEFS:
		var cell := HBoxContainer.new()
		cell.add_theme_constant_override("separation", 8)
		cell.add_child(CharmView.new().setup(Charms.make(id), i))
		cell.add_child(_wrapped("%s\n%d coins" % [Charms.DEFS[id].desc, Charms.DEFS[id].price], 16, 160))
		grid.add_child(cell)
		i += 1
	root.add_child(grid)

	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("res://build/shots/card_sheet.png")
	get_tree().quit()


func _label(t: String, font_size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = t
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	return l


func _wrapped(t: String, font_size: int, width: int) -> Label:
	var l := _label(t, font_size, TEXT)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(width, 0)
	return l
