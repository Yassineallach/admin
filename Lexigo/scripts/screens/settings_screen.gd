extends Screen
## Settings: languages, audio, accessibility and credits.

var _reset_armed := false

func _ready() -> void:
	_build()

func _build() -> void:
	for c in get_children():
		c.queue_free()
	var root := make_root(24, 16)
	root.add_child(Widgets.top_bar(main, go_back, Loc.t("settings")))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 14)
	scroll.add_child(v)
	root.add_child(scroll)

	v.add_child(UI.caps(Loc.t("i_speak"), 24))
	v.add_child(Widgets.language_list(Loc.LANGS, Game.native(), func(c):
		var t := Game.target()
		if t == c:
			t = "en" if c != "en" else "fr"
		Game.set_languages(c, t)
		_build()))
	v.add_child(UI.caps(Loc.t("i_learn"), 24))
	var targets := Vocab.LANG_NAMES.keys().filter(func(c): return c != Game.native())
	v.add_child(Widgets.language_list(targets, Game.target(), func(c):
		Game.set_languages(Game.native(), c)
		_build()))

	v.add_child(UI.spacer(6))
	var group := VBoxContainer.new()
	group.add_theme_constant_override("separation", 0)
	var card := UI.panel(UI.box(UI.WHITE, UI.R_CARD, UI.BORDER, UI.CLOUD))
	card.add_child(group)
	for row in [["speaker", "sound", "sfx"], ["speaker", "voice", "voice"], ["flame", "haptics", "haptics"],
			["note", "strict", "strict"], ["gem", "online", "online"]]:
		if group.get_child_count() > 0:
			group.add_child(Widgets.divider())
		group.add_child(_toggle(row[0], Loc.t(row[1]), row[2]))
	v.add_child(card)

	var reset := UI.button(Loc.t("reset_confirm") if _reset_armed else Loc.t("reset"), "danger" if _reset_armed else "neutral", 26, 88)
	if not _reset_armed:
		reset.add_theme_color_override("font_color", UI.BERRY)
	reset.pressed.connect(func():
		if _reset_armed:
			Game.reset()
			main.goto_onboarding()
		else:
			_reset_armed = true
			_build())
	v.add_child(reset)

	v.add_child(UI.caps(Loc.t("credits"), 24))
	var credits := UI.label(
		"Lexigo 1.1 · com.mardev.Lexigo · Made with Godot Engine\n" +
		"Font: Nunito (SIL Open Font License)\n" +
		"Example sentences: Tatoeba.org (CC BY 2.0 FR)\n" +
		"Native pronunciations: Wiktionary, Wikimedia Commons & Lingua Libre contributors (CC BY-SA)", 22, UI.STONE)
	credits.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(credits)

func _toggle(icon_name: String, text: String, key: String) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	h.custom_minimum_size.y = 92
	h.add_child(UI.icon(icon_name, 44))
	var l := UI.label(text, 28, UI.INK, true)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	h.add_child(l)
	h.add_child(_switch(Game.setting(key), func():
		Game.set_setting(key, not Game.setting(key))
		_build()))
	return h

## Pill switch: knob slides right and the track fills blue when on.
func _switch(on: bool, toggle: Callable) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(104, 60)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var track := UI.box(UI.SKY if on else UI.CLOUD, 30)
	for s in ["normal", "hover", "pressed", "focus"]:
		b.add_theme_stylebox_override(s, track)
	var knob := Panel.new()
	knob.add_theme_stylebox_override("panel", UI.box(UI.WHITE, 24, 0, UI.CLOUD, 4, UI.SKY_LIP if on else Color("cecece")))
	knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	knob.size = Vector2(48, 48)
	knob.position = Vector2(50 if on else 6, 4)
	b.add_child(knob)
	b.pressed.connect(func(): Sfx.play("select"); toggle.call())
	return b
