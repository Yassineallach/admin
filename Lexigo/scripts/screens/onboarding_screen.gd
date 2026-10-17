extends Screen
## First launch: pick the language you speak and the one you want to learn.

var _native := "en"
var _target := "fr"
var _animated := false

func _ready() -> void:
	_native = Game.native()
	_target = Game.target() if Game.target() != _native else ("fr" if _native != "fr" else "en")
	_build()

func go_back() -> bool:
	return false

func _build() -> void:
	for c in get_children():
		c.queue_free()
	Loc.lang = _native
	var root := make_root(32, 22)
	root.alignment = BoxContainer.ALIGNMENT_CENTER
	root.add_child(Widgets.logo(92))
	var tag := UI.label(Loc.t("tagline"), 28, UI.MUTED, false, HORIZONTAL_ALIGNMENT_CENTER)
	tag.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(tag)
	root.add_child(_spacer(20))
	root.add_child(UI.label(Loc.t("i_speak"), 30, Color.WHITE, true))
	root.add_child(Widgets.language_chips(Loc.LANGS, _native, func(c):
		_native = c
		if _target == c:
			_target = "en" if c != "en" else "fr"
		_build()))
	root.add_child(_spacer(10))
	root.add_child(UI.label(Loc.t("i_learn"), 30, Color.WHITE, true))
	var targets := Vocab.LANG_NAMES.keys().filter(func(c): return c != _native)
	root.add_child(Widgets.language_chips(targets, _target, func(c):
		_target = c
		_build()))
	root.add_child(_spacer(30))
	var go := UI.button(Loc.t("start"), UI.GREEN, 36, 104)
	go.pressed.connect(_finish)
	root.add_child(go)
	if not _animated:
		_animated = true
		for i in root.get_child_count():
			UI.appear(root.get_child(i), i * 0.05)

func _spacer(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size.y = h
	return c

func _finish() -> void:
	Game.set_languages(_native, _target)
	Game.data["onboarded"] = true
	Game.save_game()
	main.goto_home()
