extends Screen
## Personal word collection with memory strength per word.

func _ready() -> void:
	var root := make_root(24, 16)
	root.add_child(Widgets.top_bar(main, go_back, "📚 " + Loc.t("lexicon")))

	var stats := HBoxContainer.new()
	stats.add_theme_constant_override("separation", 14)
	stats.add_child(_stat("%d" % Game.known_count(), Loc.t("learning"), UI.ACCENT))
	stats.add_child(_stat("%d" % Game.mastered_count(), Loc.t("mastered"), UI.GREEN))
	stats.add_child(_stat("%d" % Game.due_words().size(), Loc.t("review"), UI.ACCENT_2))
	root.add_child(stats)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 10)
	scroll.add_child(list)
	root.add_child(scroll)

	var any := false
	for wi in Vocab.worlds.size():
		var words: Array = Vocab.worlds[wi]["words"].filter(func(w): return not Game.memory(w["id"]).is_empty())
		if words.is_empty():
			continue
		any = true
		var color: Color = Vocab.worlds[wi]["color"]
		list.add_child(UI.label("%s  %s" % [Vocab.worlds[wi]["emoji"], Vocab.world_name(wi, Game.native())], 28, color.lightened(0.35), true))
		for w in words:
			list.add_child(_row(w, color))
	if not any:
		var empty := UI.label("🔤\n" + Loc.t("empty_lexicon"), 30, UI.MUTED, false, HORIZONTAL_ALIGNMENT_CENTER)
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty.custom_minimum_size.y = 400
		list.add_child(empty)

func _stat(value: String, caption: String, color: Color) -> PanelContainer:
	var p := UI.panel(Color(color, 0.22), 24)
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.add_child(UI.label(value, 40, Color.WHITE, true, HORIZONTAL_ALIGNMENT_CENTER))
	v.add_child(UI.label(caption, 20, Color(1, 1, 1, 0.7), false, HORIZONTAL_ALIGNMENT_CENTER))
	p.add_child(v)
	return p

func _row(w: Dictionary, color: Color) -> PanelContainer:
	var p := UI.panel(Color(1, 1, 1, 0.07), 22)
	var h := HBoxContainer.new()
	p.add_child(h)
	h.add_child(UI.label(w["emoji"], 40))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var names := HBoxContainer.new()
	names.add_child(UI.label(Vocab.display(w, Game.target()), 28, Color.WHITE, true))
	names.add_child(UI.label("· " + Vocab.display(w, Game.native()), 22, UI.MUTED))
	v.add_child(names)
	var m: Dictionary = Game.memory(w["id"])
	var strength := float(m.get("box", 0)) / float(Game.SRS_INTERVALS.size() - 1)
	v.add_child(UI.progress_bar(strength, UI.GREEN if int(m.get("box", 0)) >= Game.MASTERED_BOX else color, 10))
	h.add_child(v)
	var speak := UI.button("🔊", Color("2ec4b6"), 24, 60)
	speak.custom_minimum_size.x = 68
	speak.pressed.connect(main.pronounce.bind(w))
	h.add_child(speak)
	return p
