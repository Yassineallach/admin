extends Screen
## Playing a crossword: board, clue card, hints and the letter bank.

const ResultPanel := preload("res://scripts/screens/result_panel.gd")

var config: Dictionary
var state := PuzzleState.new()
var board: CrosswordBoard
var keyboard: LetterKeyboard
var _clue_card: Control
var _clue_meta: Label
var _clue_pic: TextureRect
var _clue_text: Label
var _clue_extra: Label
var _mascot: TextureRect
var _progress: Control
var _timer_label: Label
var _banner: PanelContainer
var _elapsed := 0.0
var _done := false
var _examples := {}    # placement index -> example dict
var _hint_buttons := {}

func accent() -> Color:
	return config.get("color", UI.SKY)

func go_back() -> bool:
	Game.save_game()
	main.goto_home()
	return true

func _ready() -> void:
	var built := Vocab.crossword_entries(config["words"], Game.target())
	var layout := CrosswordGenerator.generate(built[0], config.get("seed", 1), built[1])
	state.strict_accents = Game.setting("strict")
	state.setup(layout)
	state.word_solved.connect(_on_word_solved)
	state.word_wrong.connect(_on_word_wrong)
	state.completed.connect(_on_completed)
	_build()
	_refresh()

func _build() -> void:
	var root := make_root(20, 12)
	# Header: close, progress through the grid, timer.
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 16)
	var close := Widgets.back_button()
	close.pressed.connect(go_back)
	top.add_child(close)
	_progress = UI.progress_bar(0.0, UI.LEAF, 30)
	_progress.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_progress.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	top.add_child(_progress)
	_timer_label = UI.label("0:00", 26, UI.STONE, true)
	top.add_child(_timer_label)
	top.add_child(Widgets.coin_stat())
	root.add_child(top)
	var title := UI.caps(config.get("title", ""), 22, accent().darkened(0.15))
	title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	root.add_child(title)

	root.add_child(_build_clue_card())

	board = CrosswordBoard.new()
	board.size_flags_vertical = Control.SIZE_EXPAND_FILL
	board.custom_minimum_size.y = 320
	board.bind(state, accent())
	board.cell_tapped.connect(func(p):
		state.tap(p)
		Sfx.play("select")
		_refresh())
	root.add_child(board)

	root.add_child(_build_hints())

	keyboard = LetterKeyboard.new()
	keyboard.build(Game.target(), accent())
	keyboard.letter.connect(_type)
	keyboard.erase.connect(func():
		state.backspace()
		_refresh())
	root.add_child(keyboard)

## Lexi "asks" for the current word from a speech bubble.
func _build_clue_card() -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 4)
	_mascot = UI.mascot("think", 132)
	h.add_child(_mascot)
	var bubble := UI.panel(UI.box(UI.WHITE, UI.R_CARD, UI.BORDER, UI.CLOUD))
	bubble.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	bubble.add_child(row)
	# Tapping the bubble moves on to the next word.
	bubble.gui_input.connect(func(e: InputEvent):
		if (e is InputEventMouseButton and e.pressed) or (e is InputEventScreenTouch and e.pressed):
			state.next_word(1)
			_refresh(true))
	_clue_pic = UI.art("words/basics/hello.svg", 112)
	row.add_child(_clue_pic)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_clue_meta = UI.caps("", 20, UI.STONE)
	_clue_text = UI.label("", 36, UI.INK, true)
	_clue_text.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	_clue_extra = UI.label("", 24, UI.STONE)
	_clue_extra.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_clue_meta)
	v.add_child(_clue_text)
	v.add_child(_clue_extra)
	row.add_child(v)
	h.add_child(bubble)
	_clue_card = h
	return h

func _build_hints() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 10)
	var defs := [["letter", "hint_letter"], ["trim", "hint_trim_short"], ["listen", "hint_listen"], ["example", "hint_example"], ["word", "hint_word"]]
	for d in defs:
		var cost: int = Game.HINT_COST[d[0]]
		var price := "%d %s" % [cost, Loc.t("coins")] if cost > 0 else Loc.t("free")
		var b := UI.button("%s\n%s" % [Loc.t(d[1]), price], "neutral", 20, 92)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_constant_override("line_spacing", -4)
		b.tooltip_text = Loc.t("hint_" + d[0])
		b.pressed.connect(_use_hint.bind(d[0]))
		h.add_child(b)
		_hint_buttons[d[0]] = b
	return h

## Slides a feedback strip in over the keyboard, then away again.
func _feedback(good: bool, title: String, detail := "") -> void:
	if is_instance_valid(_banner):
		_banner.queue_free()
	var color := UI.LEAF_LIP if good else UI.BERRY_LIP
	_banner = UI.panel(UI.box(UI.LEAF_PALE if good else UI.BERRY_PALE, UI.R_CARD))
	_banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	h.add_child(UI.mascot("cheer" if good else "oops", 88))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.add_child(UI.label(title, 36, color, true))
	if detail != "":
		v.add_child(UI.label(detail, 26, color))
	h.add_child(v)
	_banner.add_child(h)
	add_child(_banner)
	var w := size.x - 40.0
	_banner.custom_minimum_size.x = w
	_banner.reset_size()
	var y := keyboard.get_global_rect().position.y - get_global_rect().position.y
	_banner.position = Vector2(20, size.y)
	var tw := _banner.create_tween()
	tw.tween_property(_banner, "position:y", y - 12, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_interval(1.1)
	tw.tween_property(_banner, "position:y", size.y, 0.25).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	tw.tween_callback(_banner.queue_free)

func _set_mascot(pose: String, back_after := 1.4) -> void:
	_mascot.texture = UI.art_texture("mascot/lexi_%s.svg" % pose, 132)
	UI.pop(_mascot, 1.12)
	if back_after > 0:
		get_tree().create_timer(back_after).timeout.connect(func():
			if is_instance_valid(_mascot) and not _done:
				_mascot.texture = UI.art_texture("mascot/lexi_think.svg", 132))

func _process(delta: float) -> void:
	if not _done:
		_elapsed += delta
		_timer_label.text = UI.format_time(_elapsed)

func _unhandled_key_input(event: InputEvent) -> void:
	if _done or not (event is InputEventKey) or not event.pressed:
		return
	match event.keycode:
		KEY_BACKSPACE, KEY_DELETE:
			state.backspace()
			_refresh()
		KEY_TAB, KEY_ENTER, KEY_DOWN:
			state.next_word(-1 if event.shift_pressed else 1)
			_refresh(true)
		KEY_UP:
			state.next_word(-1)
			_refresh(true)
		KEY_SPACE:
			state.tap(state.cursor)
			_refresh()
		_:
			if event.unicode > 0:
				var c := String.chr(event.unicode).to_upper()
				if c.length() == 1 and c.to_lower() != c:
					_type(c)
				else:
					return
			else:
				return
	get_viewport().set_input_as_handled()

func _type(c: String) -> void:
	if _done:
		return
	var at := state.cursor
	state.type_letter(c)
	board.pop_cell(at)
	_refresh()

# ---------- feedback ----------

func _on_word_solved(i: int) -> void:
	board.celebrate_word(i)
	UI.set_progress(_progress, float(state.solved.size()) / maxf(1.0, state.placements.size()))
	var w: Dictionary = state.placements[i]["word"]
	if not state.is_complete():
		_feedback(true, Loc.t("praise%d" % (1 + state.solved.size() % 3)), "%s = %s" % [Vocab.display(w, Game.target()), Vocab.display(w, Game.native())])
	_set_mascot("cheer")
	Sfx.play("correct", randf_range(0.97, 1.05))
	Sfx.buzz(30)
	UI.pop(_clue_card, 1.04)
	if Game.setting("voice"):
		main.pronounce(state.placements[i]["word"], false)

func _on_word_wrong(i: int) -> void:
	board.flash_word(i)
	_feedback(false, Loc.t("not_quite"))
	_set_mascot("oops")
	Sfx.play("wrong")
	Sfx.buzz(60)
	UI.shake(_clue_card)
	get_tree().create_timer(0.45).timeout.connect(func():
		if is_instance_valid(self):
			state.clear_wrong(i)
			_refresh())

func _refresh(sound := false) -> void:
	if sound:
		Sfx.play("select")
	board.queue_redraw()
	var w := state.current_word()
	if w < 0:
		return
	var p: Dictionary = state.placements[w]
	var word: Dictionary = p["word"]
	var dir_name := Loc.t("across") if p["dir"] == CrosswordGenerator.ACROSS else Loc.t("down")
	_clue_meta.text = ("%d %s · %d · " % [p["number"], dir_name, p["answer"].length()]) + Loc.t("write_in") % Vocab.LANG_NAMES[Game.target()]
	_clue_pic.texture = UI.word_texture(word, 112)
	_clue_text.text = Vocab.display(word, Game.native())
	var extra := ""
	if _examples.has(w):
		var ex: Dictionary = _examples[w]
		if ex.is_empty():
			extra += ("\n" if extra != "" else "") + Loc.t("no_example")
		else:
			var masked: String = _mask(ex["text"], Vocab.display(word, Game.target())) if not state.solved.has(w) else ex["text"]
			extra += ("\n" if extra != "" else "") + "“%s”" % masked
			if ex.get("translation", "") != "":
				extra += "\n" + ex["translation"]
	_clue_extra.text = extra
	_clue_extra.visible = extra != ""
	for k in _hint_buttons.keys():
		_hint_buttons[k].disabled = _done or state.solved.has(w)
	_hint_buttons["trim"].disabled = _hint_buttons["trim"].disabled or state.trimmed.has(w)
	keyboard.show_word(state, w)

func _mask(sentence: String, word: String) -> String:
	var low := sentence.to_lower()
	var i := low.find(word.to_lower())
	if i < 0:
		return sentence
	return sentence.substr(0, i) + "＿".repeat(maxi(3, word.length() / 2)) + sentence.substr(i + word.length())

# ---------- hints ----------

func _use_hint(kind: String) -> void:
	var w := state.current_word()
	if w < 0 or state.solved.has(w):
		return
	var cost: int = Game.HINT_COST[kind]
	if kind == "trim" and state.trimmed.has(w):
		return
	if cost > 0 and not Game.spend(cost):
		main.toast(Loc.t("no_coins"))
		Sfx.play("wrong")
		return
	match kind:
		"letter":
			var cell := state.reveal_letter()
			if cell.x >= 0:
				board.pop_cell(cell)
			Sfx.play("hint")
		"word":
			state.reveal_word()
			Sfx.play("hint")
		"trim":
			state.trimmed[w] = true
			state.word_help[w] = maxi(state.word_help[w], 1)
			state.hints_used += 1
			Sfx.play("hint")
		"listen":
			main.pronounce(state.placements[w]["word"])
		"example":
			var word: Dictionary = state.placements[w]["word"]
			_clue_extra.text = Loc.t("loading")
			_clue_extra.visible = true
			var ex: Dictionary = await Online.example_sentence(Vocab.display(word, Game.target()), Game.target(), Game.native())
			if not is_instance_valid(self):
				return
			_examples[w] = ex
	_refresh()

# ---------- completion ----------

func _on_completed() -> void:
	_done = true
	_refresh()
	var stars := state.stars()
	var mode: String = config["mode"]
	var unlocked_before := Game.unlocked_worlds()
	for i in state.placements.size():
		Game.record_word(state.placements[i]["word"]["id"], state.word_help[i])
	var coins := 15 + stars * 10
	var xp := state.placements.size() * 10 + stars * 15
	match mode:
		"level":
			Game.record_level(config["world"], config["level"], stars)
		"daily":
			Game.mark_daily_done()
			coins += 40
			xp += 30
		"review":
			coins += state.placements.size() * 2
	Game.touch_streak()
	Game.add_xp(xp)
	Game.add_coins(coins)
	Game.save_game()
	var new_world := Game.unlocked_worlds() > unlocked_before

	await get_tree().create_timer(0.35).timeout
	board.celebrate_all()
	_set_mascot("cheer", 0)
	Sfx.play("win")
	main.confetti(board.global_position + Vector2(board.size.x * 0.5, board.size.y * 0.7))
	await get_tree().create_timer(1.1).timeout
	if not is_instance_valid(self):
		return
	var panel := ResultPanel.new()
	panel.setup(self, {
		"stars": stars, "coins": coins, "xp": xp, "time": _elapsed,
		"mistakes": state.mistakes, "hints": state.hints_used, "new_world": new_world,
		"words": state.placements.map(func(p): return p["word"]),
		"clean": state.word_help.values().count(0),
	})
	add_child(panel)

func next_action() -> void:
	if config["mode"] != "level":
		main.goto_home()
		return
	var w: int = config["world"]
	var l: int = config["level"] + 1
	if l >= Vocab.LEVELS_PER_WORLD:
		w += 1
		l = 0
	if w < Vocab.worlds.size() and Game.level_unlocked(w, l):
		main.play_level(w, l)
	else:
		main.goto_home()

func replay() -> void:
	match config["mode"]:
		"level":
			main.play_level(config["world"], config["level"])
		"review":
			main.play_review()
		_:
			main.goto_home()
