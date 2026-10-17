extends Control
## End-of-puzzle overlay: stars, rewards and the words just practised.

var _screen: Node
var _info: Dictionary

func setup(screen: Node, info: Dictionary) -> void:
	_screen = screen
	_info = info

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.color = Color(0.03, 0.02, 0.1, 0.0)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	create_tween().tween_property(dim, "color:a", 0.72, 0.3)

	var main: Node = _screen.main
	var card := PanelContainer.new()
	var st := UI.box(Color("251a55"), 40, 24)
	st.border_width_top = 8
	st.border_color = _screen.accent()
	st.content_margin_left = 30
	st.content_margin_right = 30
	st.content_margin_top = 26
	st.content_margin_bottom = 30
	card.add_theme_stylebox_override("panel", st)
	var m := UI.margin(card, 28, int(main.safe_top()) + 60, 28, int(main.safe_bottom()) + 40)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(m)

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 16)
	card.add_child(v)

	var stars: int = _info["stars"]
	var title := Loc.t("perfect") if stars == 3 else (Loc.t("great") if stars == 2 else Loc.t("good"))
	v.add_child(UI.label(title, 52, Color.WHITE, true, HORIZONTAL_ALIGNMENT_CENTER))

	var star_row := HBoxContainer.new()
	star_row.alignment = BoxContainer.ALIGNMENT_CENTER
	star_row.add_theme_constant_override("separation", 18)
	var star_labels := []
	for i in 3:
		var s := UI.label("★", 96 if i == 1 else 80, Color(1, 1, 1, 0.15), true, HORIZONTAL_ALIGNMENT_CENTER)
		s.custom_minimum_size = Vector2(100, 110)
		star_row.add_child(s)
		star_labels.append(s)
	v.add_child(star_row)

	var stats := HBoxContainer.new()
	stats.alignment = BoxContainer.ALIGNMENT_CENTER
	stats.add_theme_constant_override("separation", 14)
	stats.add_child(UI.pill("⏱ " + UI.format_time(_info["time"])))
	stats.add_child(UI.pill("❌ %d" % _info["mistakes"]))
	stats.add_child(UI.pill("💡 %d" % _info["hints"]))
	v.add_child(stats)

	var rewards := HBoxContainer.new()
	rewards.alignment = BoxContainer.ALIGNMENT_CENTER
	rewards.add_theme_constant_override("separation", 14)
	var coin_l := UI.pill("🪙 +0", Color(UI.GOLD, 0.25))
	var xp_l := UI.pill("⭐ +0 XP", Color(UI.ACCENT, 0.35))
	rewards.add_child(coin_l)
	rewards.add_child(xp_l)
	v.add_child(rewards)

	if _info.get("new_world", false):
		var nw := UI.label("🎉 " + Loc.t("new_world"), 30, UI.GOLD, true, HORIZONTAL_ALIGNMENT_CENTER)
		v.add_child(nw)

	v.add_child(UI.label(Loc.t("words_learned"), 24, UI.MUTED, true))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 8)
	scroll.add_child(list)
	v.add_child(scroll)
	for w in _info["words"]:
		list.add_child(_word_row(w, main))

	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 14)
	var home := UI.button("🌍 " + Loc.t("home"), Color("3d3275"), 26, 88)
	home.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	home.pressed.connect(main.goto_home)
	buttons.add_child(home)
	if _screen.config["mode"] != "daily":
		var again := UI.button("↻", Color("3d3275"), 30, 88)
		again.custom_minimum_size.x = 96
		again.pressed.connect(_screen.replay)
		buttons.add_child(again)
	var nxt := UI.button(Loc.t("next") + " ›", UI.GREEN, 30, 88)
	nxt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nxt.pressed.connect(_screen.next_action)
	buttons.add_child(nxt)
	v.add_child(buttons)

	card.modulate.a = 0.0
	card.scale = Vector2.ONE * 0.85
	await get_tree().process_frame
	UI.center_pivot(card)
	var tw := card.create_tween().set_parallel()
	tw.tween_property(card, "modulate:a", 1.0, 0.25)
	tw.tween_property(card, "scale", Vector2.ONE, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await tw.finished
	for i in stars:
		await get_tree().create_timer(0.22).timeout
		if not is_instance_valid(self):
			return
		var s: Label = star_labels[i]
		s.add_theme_color_override("font_color", UI.GOLD)
		UI.pop(s, 1.5, 0.4)
		Sfx.play("star", 1.0 + i * 0.12)
		Sfx.buzz(20)
	_count_up(coin_l.get_node("Label"), "🪙 +%d", _info["coins"])
	_count_up(xp_l.get_node("Label"), "⭐ +%d XP", _info["xp"])
	Sfx.play("coin")

func _count_up(l: Label, fmt: String, to: int) -> void:
	create_tween().tween_method(func(v: float): l.text = fmt % int(v), 0.0, float(to), 0.8).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)

func _word_row(w: Dictionary, main: Node) -> PanelContainer:
	var p := UI.panel(Color(1, 1, 1, 0.07), 20)
	var h := HBoxContainer.new()
	p.add_child(h)
	h.add_child(UI.label(w["emoji"], 40))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UI.label(Vocab.display(w, Game.target()), 30, Color.WHITE, true))
	v.add_child(UI.label(Vocab.display(w, Game.native()), 22, UI.MUTED))
	h.add_child(v)
	var m: Dictionary = Game.memory(w["id"])
	h.add_child(UI.label("🧠 %d/%d" % [int(m.get("box", 0)), Game.SRS_INTERVALS.size() - 1], 20, UI.MUTED))
	var speak := UI.button("🔊", Color("2ec4b6"), 26, 64)
	speak.custom_minimum_size.x = 72
	speak.pressed.connect(main.pronounce.bind(w))
	h.add_child(speak)
	return p
