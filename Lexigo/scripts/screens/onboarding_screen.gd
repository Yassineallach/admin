extends Screen
## First launch, in two steps: the language you speak, then the one to learn.

var _native := "en"
var _target := "fr"
var _step := 0

func _ready() -> void:
	_native = Game.native()
	_target = Game.target() if Game.target() != _native else ("fr" if _native != "fr" else "en")
	_build()

func go_back() -> bool:
	if _step == 1:
		_step = 0
		_build()
		return true
	return false

func _build() -> void:
	for c in get_children():
		c.queue_free()
	Loc.lang = _native
	var root := make_root(32, 24)
	var top := HBoxContainer.new()
	var back := Widgets.back_button()
	back.visible = _step == 1
	back.pressed.connect(go_back)
	top.add_child(back)
	var bar := UI.progress_bar(0.5 if _step == 0 else 1.0, UI.LEAF, 28)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	top.add_child(bar)
	root.add_child(top)
	if _step == 0:
		root.add_child(Widgets.logo(84))
		var says := Widgets.mascot_says("wave", "%s\n%s" % [Loc.t("hello_lexi"), Loc.t("ask_native")])
		root.add_child(says)
		root.add_child(Widgets.language_list(Loc.LANGS, _native, func(c):
			_native = c
			if _target == c:
				_target = "en" if c != "en" else "fr"
			_build()))
	else:
		root.add_child(UI.spacer(20))
		root.add_child(Widgets.mascot_says("happy", Loc.t("ask_target")))
		var targets := Vocab.LANG_NAMES.keys().filter(func(c): return c != _native)
		root.add_child(Widgets.language_list(targets, _target, func(c):
			_target = c
			_build()))
	root.add_child(UI.spacer(10, true))
	root.add_child(Widgets.divider())
	var go := UI.button(Loc.t("continue"), "primary", 30, 104)
	go.pressed.connect(_next)
	root.add_child(go)
	var says_node: Control = root.get_child(2 if _step == 0 else 2)
	UI.appear(says_node)

func _next() -> void:
	if _step == 0:
		_step = 1
		Sfx.play("whoosh")
		_build()
		return
	Game.set_languages(_native, _target)
	Game.data["onboarded"] = true
	Game.save_game()
	main.goto_home()
