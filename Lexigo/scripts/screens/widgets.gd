class_name Widgets
extends RefCounted
## Composite widgets shared by several screens.

## Crossword-tile logo: each letter on its own bouncing tile.
static func logo(tile := 86) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 8)
	var colors := [Color("7c5cff"), Color("ff5ca8"), Color("ffc93c"), Color("2ec4b6"), Color("3a86ff"), Color("ff6b6b")]
	var word := "LEXIGO"
	for i in word.length():
		var p := PanelContainer.new()
		var s := UI.box(Color.WHITE, int(tile * 0.22))
		s.border_width_bottom = int(tile * 0.1)
		s.border_color = colors[i].darkened(0.1)
		s.content_margin_left = 0
		s.content_margin_right = 0
		s.content_margin_top = 0
		s.content_margin_bottom = 0
		p.add_theme_stylebox_override("panel", s)
		p.custom_minimum_size = Vector2(tile, tile)
		var l := UI.label(word[i], int(tile * 0.62), colors[i], true, HORIZONTAL_ALIGNMENT_CENTER)
		p.add_child(l)
		h.add_child(p)
		var tw := p.create_tween().set_loops()
		tw.tween_interval(i * 0.12)
		tw.tween_property(p, "position:y", -10.0, 0.35).as_relative().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		tw.tween_property(p, "position:y", 10.0, 0.35).as_relative().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
		tw.tween_interval(2.6 - i * 0.12)
	return h

## Selectable language chips. on_pick(code) is called when one is chosen.
static func language_chips(codes: Array, selected: String, on_pick: Callable, columns := 3) -> GridContainer:
	var g := GridContainer.new()
	g.columns = columns
	g.add_theme_constant_override("h_separation", 12)
	g.add_theme_constant_override("v_separation", 12)
	for code in codes:
		var on: bool = code == selected
		var b := UI.button("%s  %s" % [Vocab.LANG_FLAGS[code], Vocab.LANG_NAMES[code]], UI.ACCENT if on else Color("2c2360"), 24, 76)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if on:
			var st: StyleBoxFlat = b.get_theme_stylebox("normal").duplicate()
			st.set_border_width_all(4)
			st.border_width_bottom = 8
			st.border_color = UI.GOLD
			b.add_theme_stylebox_override("normal", st)
			b.add_theme_stylebox_override("hover", st)
		b.pressed.connect(on_pick.bind(code))
		g.add_child(b)
	return g

static func top_bar(main: Node, back: Callable, title := "") -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 12)
	var b := UI.button("‹", Color("2c2360"), 40, 72)
	b.custom_minimum_size.x = 72
	b.pressed.connect(back)
	h.add_child(b)
	var t := UI.label(title, 30, Color.WHITE, true)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	h.add_child(t)
	h.add_child(coin_pill())
	return h

static func coin_pill() -> PanelContainer:
	var p := UI.pill("🪙 %d" % Game.coins())
	var l: Label = p.get_node("Label")
	var update := func(v: int):
		l.text = "🪙 %d" % v
		UI.pop(p, 1.2)
	Game.coins_changed.connect(update)
	p.tree_exiting.connect(func(): Game.coins_changed.disconnect(update))
	return p
