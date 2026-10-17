class_name Widgets
extends RefCounted
## Composite widgets shared by several screens.

## Lower-case rounded wordmark.
static func logo(size := 72) -> Label:
	var l := UI.label("lexigo", size, UI.LEAF, true, HORIZONTAL_ALIGNMENT_CENTER)
	var f := FontVariation.new()
	f.base_font = load("res://assets/fonts/Nunito.ttf")
	f.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 1000}
	f.spacing_glyph = -2
	l.add_theme_font_override("font", f)
	return l

## Mascot with a speech bubble beside it.
static func mascot_says(pose: String, text: String, mascot_px := 170) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	var m := UI.mascot(pose, mascot_px)
	h.add_child(m)
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var l := UI.label(text, 32, UI.INK, true)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.name = "Text"
	var b := UI.bubble(l)
	v.add_child(b)
	h.add_child(v)
	return h

## Selectable list of languages as outlined cards with flags.
static func language_list(codes: Array, selected: String, on_pick: Callable, columns := 2) -> GridContainer:
	var g := GridContainer.new()
	g.columns = columns
	g.add_theme_constant_override("h_separation", 14)
	g.add_theme_constant_override("v_separation", 14)
	for code in codes:
		var on: bool = code == selected
		var b := Button.new()
		b.text = Vocab.LANG_NAMES[code]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(0, 96)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_override("font", UI.font(true))
		b.add_theme_font_size_override("font_size", 30)
		var st := UI.card_box(on, UI.R_BUTTON)
		var pressed := st.duplicate()
		pressed.border_width_bottom = UI.BORDER
		pressed.expand_margin_top = -2
		b.add_theme_stylebox_override("normal", st)
		b.add_theme_stylebox_override("hover", st)
		b.add_theme_stylebox_override("pressed", pressed)
		b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		var ink := UI.SKY_LIP if on else UI.INK
		for c in ["font_color", "font_hover_color", "font_pressed_color"]:
			b.add_theme_color_override(c, ink)
		b.pressed.connect(func(): Sfx.play("select"); on_pick.call(code))
		g.add_child(b)
	return g

## Header with a back button, a title and the coin count.
static func top_bar(_main: Node, back: Callable, title := "") -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	var b := back_button()
	b.pressed.connect(back)
	h.add_child(b)
	var t := UI.label(title, 34, UI.INK, true)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	t.name = "Title"
	h.add_child(t)
	h.add_child(coin_stat())
	return h

static func coin_stat() -> VBoxContainer:
	var s := UI.stat(Loc.t("coins"), str(Game.coins()), UI.SUN_LIP)
	var l: Label = s.get_node("Value")
	var update := func(v: int):
		l.text = str(v)
		UI.pop(s, 1.2)
	Game.coins_changed.connect(update)
	s.tree_exiting.connect(func(): Game.coins_changed.disconnect(update))
	return s

static func back_button() -> Button:
	var b := UI.flat_button(Loc.t("back").to_upper(), 24, UI.STONE)
	b.add_theme_font_override("font", UI.font(true, true))
	return b

## Thin grey divider that spans the width.
static func divider() -> ColorRect:
	var c := ColorRect.new()
	c.color = UI.CLOUD
	c.custom_minimum_size.y = 4
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c
