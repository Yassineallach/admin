extends Screen
## Playing a crossword: board, clue card, hints and keyboard.

const ResultPanel := preload("res://scripts/screens/result_panel.gd")

var config: Dictionary
var state := PuzzleState.new()
var board: CrosswordBoard
var keyboard: LetterKeyboard
var _clue_card: PanelContainer
var _clue_meta: Label
var _clue_emoji: Label
var _clue_text: Label
var _clue_extra: Label
var _timer_label: PanelContainer
var _elapsed := 0.0
var _done := false
var _shuffled := {}    # placement index -> scrambled letters string
var _examples := {}    # placement index -> example dict
var _hint_buttons := {}

func accent() -> Color:
	return config.get("color", UI.ACCENT)

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
	var root := make_root(18, 12)
	var bar := Widgets.top_bar(main, go_back, config.get("title", ""))
	_timer_label = UI.pill("⏱ 0:00")
	bar.add_child(_timer_label)
	bar.move_child(_timer_label, 2)
	root.add_child(bar)

	board = CrosswordBoard.new()
	board.size_flags_vertical = Control.SIZE_EXPAND_FILL
	board.custom_minimum_size.y = 360
	board.bind(state, accent())
	board.cell_tapped.connect(func(p):
		state.tap(p)
		Sfx.play("select")
		_refresh())
	root.add_child(board)

	root.add_child(_build_clue_card())
	root.add_child(_build_hints())

	keyboard = LetterKeyboard.new()
	keyboard.build(Game.target(), accent())
	keyboard.letter.connect(_type)
	keyboard.erase.connect(func():
		state.backspace()
		_refresh())
	root.add_child(keyboard)

func _build_clue_card() -> PanelContainer:
	_clue_card = PanelContainer.new()
	var st := UI.box(Color.WHITE, 26, 8)
	st.content_margin_left = 8
	st.content_margin_right = 8
	_clue_card.add_theme_stylebox_override("panel", st)
	var h := HBoxContainer.new()
	_clue_card.add_child(h)
	var prev := UI.flat_button("‹", 52, UI.INK)
	prev.pressed.connect(func(): state.next_word(-1); _refresh(true))
	h.add_child(prev)
	_clue_emoji = UI.label("", 60, UI.INK, false, HORIZONTAL_ALIGNMENT_CENTER)
	_clue_emoji.custom_minimum_size.x = 84
	h.add_child(_clue_emoji)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_clue_meta = UI.label("", 20, accent().darkened(0.2), true)
	_clue_text = UI.label("", 34, UI.INK, true)
	_clue_text.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	_clue_extra = UI.label("", 22, Color(UI.INK, 0.7))
	_clue_extra.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_clue_meta)
	v.add_child(_clue_text)
	v.add_child(_clue_extra)
	h.add_child(v)
	var nxt := UI.flat_button("›", 52, UI.INK)
	nxt.pressed.connect(func(): state.next_word(1); _refresh(true))
	h.add_child(nxt)
	return _clue_card

func _build_hints() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	var defs := [
		["letter", "💡", Loc.t("hint_letter"), Color("ffb703")],
		["shuffle", "🔀", Loc.t("hint_shuffle"), Color("3a86ff")],
		["listen", "🔊", Loc.t("hint_listen"), Color("2ec4b6")],
		["example", "📝", Loc.t("hint_example"), Color("9d4edd")],
		["word", "✨", Loc.t("hint_word"), Color("ff5ca8")],
	]
	for d in defs:
		var cost: int = Game.HINT_COST[d[0]]
		var label := "%s %s" % [d[1], ("%d" % cost) if cost > 0 else d[2]]
		var b := UI.button(label, d[3], 22, 64)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.tooltip_text = d[2]
		b.pressed.connect(_use_hint.bind(d[0]))
		h.add_child(b)
		_hint_buttons[d[0]] = b
	return h

func _process(delta: float) -> void:
	if not _done:
		_elapsed += delta
		_timer_label.get_node("Label").text = "⏱ " + UI.format_time(_elapsed)

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
	Sfx.play("correct", randf_range(0.97, 1.05))
	Sfx.buzz(30)
	UI.pop(_clue_card, 1.04)
	if Game.setting("voice"):
		main.pronounce(state.placements[i]["word"], false)

func _on_word_wrong(i: int) -> void:
	board.flash_word(i)
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
	_clue_meta.text = "%d %s · %d" % [p["number"], dir_name, p["answer"].length()] + (" ✓" if state.solved.has(w) else "")
	_clue_emoji.text = word["emoji"]
	_clue_text.text = Vocab.display(word, Game.native())
	var extra := ""
	if _shuffled.has(w):
		extra = "🔀 " + _shuffled[w]
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
	if kind == "shuffle" and _shuffled.has(w):
		return
	if cost > 0 and not Game.spend(cost):
		main.toast("🪙 " + Loc.t("no_coins"))
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
		"shuffle":
			var letters: Array = Array(state.placements[w]["answer"].split(""))
			letters.shuffle()
			_shuffled[w] = " ".join(letters)
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
