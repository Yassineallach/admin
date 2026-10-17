extends Screen
## World map: profile header, daily/review shortcuts and the world journey.

var _scroll: ScrollContainer

func go_back() -> bool:
	return false

func _ready() -> void:
	var root := make_root(24, 18)
	root.add_child(_header())
	var logo := Widgets.logo(64)
	root.add_child(logo)
	var learning := UI.flat_button("%s  %s  ›" % [Vocab.LANG_FLAGS[Game.target()], Vocab.LANG_NAMES[Game.target()]], 26, UI.MUTED)
	learning.pressed.connect(main.open_settings)
	root.add_child(learning)
	root.add_child(_shortcuts())

	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 20)
	_scroll.add_child(list)
	root.add_child(_scroll)
	var focus_world := 0
	for w in Vocab.worlds.size():
		var card := _world_card(w)
		list.add_child(card)
		UI.appear(card, 0.08 + w * 0.05)
		if Game.world_unlocked(w):
			focus_world = w
	var pad := Control.new()
	pad.custom_minimum_size.y = 24
	list.add_child(pad)
	root.add_child(_nav())
	# Scroll so the newest unlocked world is in view.
	await get_tree().process_frame
	await get_tree().process_frame
	if is_instance_valid(_scroll) and focus_world > 0:
		var target: Control = list.get_child(focus_world)
		create_tween().tween_property(_scroll, "scroll_vertical", int(target.position.y), 0.6).set_trans(Tween.TRANS_CUBIC)

func _header() -> HBoxContainer:
	var h := HBoxContainer.new()
	var lvl := UI.panel(Color(0, 0, 0, 0.25), 36)
	var lv := VBoxContainer.new()
	lv.add_theme_constant_override("separation", 6)
	lv.custom_minimum_size.x = 190
	lv.add_child(UI.label("⭐ %s %d" % [Loc.t("level"), Game.player_level()], 24, Color.WHITE, true))
	lv.add_child(UI.progress_bar(Game.level_progress(), UI.GOLD, 10))
	lvl.add_child(lv)
	h.add_child(lvl)
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(sp)
	h.add_child(UI.pill("🔥 %d" % Game.current_streak()))
	h.add_child(UI.pill("⭐ %d" % Game.total_stars()))
	h.add_child(Widgets.coin_pill())
	return h

func _shortcuts() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	var done := Game.daily_done()
	var daily := UI.button("📅 %s%s" % [Loc.t("daily"), "  ✓" if done else ""], Color("e0a100") if not done else Color("6c6496"), 28, 96)
	daily.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	daily.pressed.connect(main.play_daily)
	h.add_child(daily)
	var due := Game.due_words().size()
	var review := UI.button("🧠 %s" % Loc.t("review"), UI.ACCENT_2, 28, 96)
	review.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	review.pressed.connect(main.play_review)
	if due > 0:
		var badge := UI.pill(str(due), UI.RED)
		badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
		badge.set_anchors_preset(Control.PRESET_TOP_RIGHT)
		badge.position = Vector2(-50, -14)
		review.add_child(badge)
		var tw := badge.create_tween().set_loops()
		tw.tween_property(badge, "scale", Vector2.ONE * 1.12, 0.5).set_trans(Tween.TRANS_SINE)
		tw.tween_property(badge, "scale", Vector2.ONE, 0.5).set_trans(Tween.TRANS_SINE)
	h.add_child(review)
	if not done:
		var tw2 := daily.create_tween().set_loops()
		tw2.tween_interval(2.0)
		tw2.tween_callback(func(): UI.pop(daily, 1.05, 0.4))
	return h

func _world_card(w: int) -> PanelContainer:
	var world: Dictionary = Vocab.worlds[w]
	var color: Color = world["color"]
	var unlocked := Game.world_unlocked(w)
	var card := PanelContainer.new()
	var st := UI.box(color.darkened(0.45) if unlocked else Color(0.2, 0.18, 0.32, 0.8), 32, 10)
	st.border_width_top = 6
	st.border_color = color if unlocked else Color(1, 1, 1, 0.08)
	st.content_margin_left = 22
	st.content_margin_right = 22
	st.content_margin_top = 18
	st.content_margin_bottom = 22
	card.add_theme_stylebox_override("panel", st)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	card.add_child(v)

	var head := HBoxContainer.new()
	head.add_child(UI.label(world["emoji"] if unlocked else "🔒", 52))
	var titles := VBoxContainer.new()
	titles.add_theme_constant_override("separation", 0)
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sub := "%s %d" % [Loc.t("world"), w + 1]
	titles.add_child(UI.label(sub.to_upper(), 18, color.lightened(0.4) if unlocked else UI.MUTED, true))
	titles.add_child(UI.label(Vocab.world_name(w, Game.native()), 32, Color.WHITE if unlocked else UI.MUTED, true))
	head.add_child(titles)
	var max_stars := Vocab.LEVELS_PER_WORLD * 3
	head.add_child(UI.pill("★ %d/%d" % [Game.world_stars(w), max_stars], Color(0, 0, 0, 0.3)))
	v.add_child(head)

	if not unlocked:
		var hint := UI.label(Loc.t("locked"), 22, UI.MUTED)
		hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		v.add_child(hint)
		return card

	# Preview of the words waiting in this world, in the target language.
	var preview := ""
	var ws := Vocab.playable_words(w, Game.target())
	for i in mini(5, ws.size()):
		preview += ws[i]["emoji"] + " "
	v.add_child(UI.label(preview + "…", 26, Color(1, 1, 1, 0.75)))

	var path := HBoxContainer.new()
	path.alignment = BoxContainer.ALIGNMENT_CENTER
	path.add_theme_constant_override("separation", 10)
	for l in Vocab.LEVELS_PER_WORLD:
		path.add_child(_level_node(w, l, color))
	v.add_child(path)
	return card

func _level_node(w: int, l: int, color: Color) -> VBoxContainer:
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 4)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var unlocked := Game.level_unlocked(w, l)
	var s := Game.stars(w, l)
	var boss := l == Vocab.LEVELS_PER_WORLD - 1
	var is_next := unlocked and s == 0
	var face := color if unlocked else Color(1, 1, 1, 0.12)
	if s > 0:
		face = color.lightened(0.15)
	var text := "👑" if boss else str(l + 1)
	if not unlocked:
		text = "🔒"
	var b := UI.button(text, face, 30, 84)
	var round_st: StyleBoxFlat = b.get_theme_stylebox("normal").duplicate()
	round_st.set_corner_radius_all(42)
	if is_next:
		round_st.set_border_width_all(4)
		round_st.border_width_bottom = 8
		round_st.border_color = Color.WHITE
	b.add_theme_stylebox_override("normal", round_st)
	b.add_theme_stylebox_override("hover", round_st)
	var pressed_st: StyleBoxFlat = b.get_theme_stylebox("pressed").duplicate()
	pressed_st.set_corner_radius_all(42)
	b.add_theme_stylebox_override("pressed", pressed_st)
	b.disabled = not unlocked
	b.custom_minimum_size = Vector2(84, 84)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.pressed.connect(main.play_level.bind(w, l))
	col.add_child(b)
	var st := UI.label(UI.stars_text(s) if unlocked else " ", 18, UI.GOLD, true, HORIZONTAL_ALIGNMENT_CENTER)
	col.add_child(st)
	if is_next:
		var tw := b.create_tween().set_loops()
		tw.tween_callback(func(): UI.pop(b, 1.1, 0.5))
		tw.tween_interval(1.4)
	return col

func _nav() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	var words := UI.button("📚 " + Loc.t("lexicon"), Color("2c2360"), 26, 80)
	words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	words.pressed.connect(main.open_lexicon)
	h.add_child(words)
	var settings := UI.button("⚙️ " + Loc.t("settings"), Color("2c2360"), 26, 80)
	settings.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	settings.pressed.connect(main.open_settings)
	h.add_child(settings)
	return h
