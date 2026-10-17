extends Control
## End-of-grid celebration: Lexi cheers, stars land, stat cards count up,
## and the words just practised can be heard again.

var _screen: Node
var _info: Dictionary

func setup(screen: Node, info: Dictionary) -> void:
	_screen = screen
	_info = info

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var bg := ColorRect.new()
	bg.color = UI.WHITE
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var main: Node = _screen.main

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	var m := UI.margin(v, 32, int(main.safe_top()) + 24, 32, int(main.safe_bottom()) + 24)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(m)

	var lexi := UI.mascot("cheer", 170)
	lexi.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(lexi)
	var stars: int = _info["stars"]
	v.add_child(UI.label(Loc.t("grid_complete"), 46, UI.SUN_LIP, true, HORIZONTAL_ALIGNMENT_CENTER))
	var sub := Loc.t("perfect") if stars == 3 else (Loc.t("great") if stars == 2 else Loc.t("good"))
	if _info.get("new_world", false):
		sub += "  " + Loc.t("new_world")
	var sub_l := UI.label(sub, 28, UI.STONE, true, HORIZONTAL_ALIGNMENT_CENTER)
	sub_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(sub_l)

	var star_row := HBoxContainer.new()
	star_row.alignment = BoxContainer.ALIGNMENT_CENTER
	star_row.add_theme_constant_override("separation", 10)
	var star_nodes := []
	for i in 3:
		var s := UI.icon("star_empty", 80 if i == 1 else 64)
		star_row.add_child(s)
		star_nodes.append(s)
	v.add_child(star_row)

	var words: Array = _info["words"]
	var accuracy := 100
	if not words.is_empty():
		accuracy = int(round(100.0 * float(_info.get("clean", words.size())) / words.size()))
	var cards := HBoxContainer.new()
	cards.add_theme_constant_override("separation", 14)
	var xp_card := _stat_card(Loc.t("total_xp"), "star", "0", UI.SUN, UI.SUN_LIP)
	cards.add_child(xp_card)
	cards.add_child(_stat_card(Loc.t("time"), "calendar", UI.format_time(_info["time"]), UI.SKY, UI.SKY_LIP))
	cards.add_child(_stat_card(Loc.t("accuracy"), "check", "%d%%" % accuracy, UI.LEAF, UI.LEAF_LIP))
	v.add_child(cards)
	var coins := UI.stat("coin", "+0", UI.SUN_LIP)
	coins.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(coins)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 10)
	scroll.add_child(list)
	v.add_child(UI.caps(Loc.t("words_learned"), 22))
	v.add_child(scroll)
	for w in words:
		list.add_child(_word_row(w, main))

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	var map := UI.button(Loc.t("home"), "neutral", 26, 84, "map")
	map.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map.pressed.connect(main.goto_home)
	row.add_child(map)
	if _screen.config["mode"] != "daily":
		var again := UI.button(Loc.t("retry"), "neutral", 26, 84, "review")
		again.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		again.pressed.connect(_screen.replay)
		row.add_child(again)
	v.add_child(row)
	var nxt := UI.button(Loc.t("continue"), "primary", 30, 104)
	nxt.pressed.connect(_screen.next_action)
	v.add_child(nxt)

	# Entrance: slide up, then stars, then counters.
	m.modulate.a = 0.0
	m.position.y = 80
	var tw := m.create_tween().set_parallel()
	tw.tween_property(m, "modulate:a", 1.0, 0.25)
	tw.tween_property(m, "position:y", 0.0, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await tw.finished
	UI.bob(lexi, 6.0, 1.8)
	for i in stars:
		await get_tree().create_timer(0.22).timeout
		if not is_instance_valid(self):
			return
		var s: TextureRect = star_nodes[i]
		s.texture = UI.icon_texture("star", 80 if i == 1 else 64)
		UI.pop(s, 1.45, 0.4)
		Sfx.play("star", 1.0 + i * 0.12)
		Sfx.buzz(20)
	_count_up(xp_card.get_meta("value"), "%d", _info["xp"])
	_count_up(coins.get_node("Value"), "+%d", _info["coins"])
	Sfx.play("coin")

func _stat_card(title: String, icon_name: String, value: String, color: Color, lip: Color) -> PanelContainer:
	var card := UI.panel(UI.box(color, 26, UI.BORDER, color))
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sb: StyleBoxFlat = card.get_theme_stylebox("panel")
	sb.content_margin_left = 0
	sb.content_margin_right = 0
	sb.content_margin_top = 6
	sb.content_margin_bottom = 0
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	var t := UI.caps(title, 18, UI.WHITE)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var inner := UI.panel(UI.box(UI.WHITE, 22))
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_child(UI.icon(icon_name, 36))
	var val := UI.label(value, 32, lip, true)
	h.add_child(val)
	inner.add_child(h)
	v.add_child(inner)
	card.add_child(v)
	card.set_meta("value", val)
	return card

func _count_up(l: Label, fmt: String, to: int) -> void:
	create_tween().tween_method(func(v: float): l.text = fmt % int(v), 0.0, float(to), 0.8).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)

func _word_row(w: Dictionary, main: Node) -> PanelContainer:
	var p := UI.panel(UI.card_box(false, 24))
	var h := HBoxContainer.new()
	p.add_child(h)
	h.add_child(UI.label(w["emoji"], 40))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UI.label(Vocab.display(w, Game.target()), 30, UI.INK, true))
	v.add_child(UI.label(Vocab.display(w, Game.native()), 24, UI.STONE))
	h.add_child(v)
	var speak := UI.icon_button("speaker", 48)
	speak.pressed.connect(main.pronounce.bind(w))
	h.add_child(speak)
	return p
