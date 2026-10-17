extends Screen
## Personal word collection with memory strength per word.

func _ready() -> void:
	var root := make_root(24, 16)
	root.add_child(Widgets.top_bar(main, go_back, Loc.t("lexicon")))

	var stats := HBoxContainer.new()
	stats.add_theme_constant_override("separation", 14)
	stats.add_child(_stat("%d" % Game.known_count(), Loc.t("learning"), UI.SKY, UI.SKY_LIP, "book"))
	stats.add_child(_stat("%d" % Game.mastered_count(), Loc.t("mastered"), UI.LEAF, UI.LEAF_LIP, "crown"))
	stats.add_child(_stat("%d" % Game.due_words().size(), Loc.t("review"), UI.GRAPE, UI.GRAPE_LIP, "review"))
	root.add_child(stats)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 12)
	scroll.add_child(list)
	root.add_child(scroll)

	var any := false
	for wi in Vocab.worlds.size():
		var words: Array = Vocab.worlds[wi]["words"].filter(func(w): return not Game.memory(w["id"]).is_empty())
		if words.is_empty():
			continue
		any = true
		var color: Color = Vocab.worlds[wi]["color"]
		var head := HBoxContainer.new()
		head.add_child(UI.art("worlds/%s.svg" % Vocab.worlds[wi]["id"], 56))
		head.add_child(UI.label(Vocab.world_name(wi, Game.native()), 32, color.darkened(0.2), true))
		list.add_child(head)
		for w in words:
			list.add_child(_row(w, color))
	if not any:
		list.add_child(Widgets.mascot_says("think", Loc.t("empty_lexicon")))

func _stat(value: String, caption: String, color: Color, lip: Color, icon_name: String) -> PanelContainer:
	var p := UI.panel(UI.box(UI.WHITE, UI.R_CARD, UI.BORDER, UI.CLOUD, 2))
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_child(UI.icon(icon_name, 40))
	h.add_child(UI.label(value, 40, lip, true))
	v.add_child(h)
	var c := UI.caps(caption, 18, UI.STONE)
	c.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(c)
	p.add_child(v)
	return p

func _row(w: Dictionary, color: Color) -> PanelContainer:
	var p := UI.panel(UI.card_box(false, 24))
	var h := HBoxContainer.new()
	p.add_child(h)
	h.add_child(UI.label(w["emoji"], 42))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var names := HBoxContainer.new()
	names.add_child(UI.label(Vocab.display(w, Game.target()), 30, UI.INK, true))
	names.add_child(UI.label(Vocab.display(w, Game.native()), 24, UI.STONE))
	v.add_child(names)
	var m: Dictionary = Game.memory(w["id"])
	var box := int(m.get("box", 0))
	var strength := float(box) / float(Game.SRS_INTERVALS.size() - 1)
	v.add_child(UI.progress_bar(strength, UI.LEAF if box >= Game.MASTERED_BOX else color, 18))
	h.add_child(v)
	var speak := UI.icon_button("speaker", 48)
	speak.pressed.connect(main.pronounce.bind(w))
	h.add_child(speak)
	return p
