extends Screen
## Settings: languages, audio, accessibility and credits.

var _reset_armed := false

func _ready() -> void:
	_build()

func _build() -> void:
	for c in get_children():
		c.queue_free()
	var root := make_root(24, 16)
	root.add_child(Widgets.top_bar(main, go_back, "⚙️ " + Loc.t("settings")))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 14)
	scroll.add_child(v)
	root.add_child(scroll)

	v.add_child(UI.label(Loc.t("i_speak"), 26, UI.MUTED, true))
	v.add_child(Widgets.language_chips(Loc.LANGS, Game.native(), func(c):
		var t := Game.target()
		if t == c:
			t = "en" if c != "en" else "fr"
		Game.set_languages(c, t)
		_build()))
	v.add_child(UI.label(Loc.t("i_learn"), 26, UI.MUTED, true))
	var targets := Vocab.LANG_NAMES.keys().filter(func(c): return c != Game.native())
	v.add_child(Widgets.language_chips(targets, Game.target(), func(c):
		Game.set_languages(Game.native(), c)
		_build()))

	v.add_child(_toggle("🔈 " + Loc.t("sound"), "sfx"))
	v.add_child(_toggle("🔊 " + Loc.t("voice"), "voice"))
	v.add_child(_toggle("📳 " + Loc.t("haptics"), "haptics"))
	v.add_child(_toggle("✍️ " + Loc.t("strict"), "strict"))
	v.add_child(_toggle("🌐 " + Loc.t("online"), "online"))

	var reset := UI.button(Loc.t("reset_confirm") if _reset_armed else "🔄 " + Loc.t("reset"), UI.RED if _reset_armed else Color("3d3275"), 24, 76)
	reset.pressed.connect(func():
		if _reset_armed:
			Game.reset()
			main.goto_onboarding()
		else:
			_reset_armed = true
			_build())
	v.add_child(reset)

	v.add_child(UI.label(Loc.t("credits"), 26, UI.MUTED, true))
	var credits := UI.label(
		"Lexigo 1.0 · com.mardev.Lexigo · Made with Godot Engine\n" +
		"Example sentences: Tatoeba.org (CC BY 2.0 FR)\n" +
		"Native pronunciations: Wiktionary, Wikimedia Commons & Lingua Libre contributors (CC BY-SA)\n" +
		"Emoji rendered with your device's system font.", 20, Color(1, 1, 1, 0.6))
	credits.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(credits)

func _toggle(text: String, key: String) -> PanelContainer:
	var p := UI.panel(Color(1, 1, 1, 0.07), 22)
	var h := HBoxContainer.new()
	p.add_child(h)
	var l := UI.label(text, 26, Color.WHITE, true)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	h.add_child(l)
	var on := Game.setting(key)
	var b := UI.button("ON" if on else "OFF", UI.GREEN if on else Color("5a5180"), 22, 60)
	b.custom_minimum_size.x = 110
	b.pressed.connect(func():
		Game.set_setting(key, not Game.setting(key))
		_build())
	h.add_child(b)
	return p
