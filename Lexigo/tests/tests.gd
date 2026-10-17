extends Node
## Headless test suite. Run:
##   godot --headless --path . res://tests/tests.tscn
## Exits with code 0 when every check passes.

var _fails := 0
var _checks := 0

func _ready() -> void:
	_test_scripts_compile()
	_test_vocabulary()
	_test_levels_generate()
	_test_puzzle_flow()
	_test_srs()
	print("\n%d checks, %d failures" % [_checks, _fails])
	get_tree().quit(1 if _fails else 0)

func check(cond: bool, msg: String) -> void:
	_checks += 1
	if not cond:
		_fails += 1
		print("FAIL: ", msg)

func _scripts(dir: String) -> Array:
	var out := []
	for f in DirAccess.get_files_at(dir):
		if f.ends_with(".gd"):
			out.append(dir.path_join(f))
	for d in DirAccess.get_directories_at(dir):
		out.append_array(_scripts(dir.path_join(d)))
	return out

func _test_scripts_compile() -> void:
	for path in _scripts("res://scripts"):
		var s: Script = load(path)
		check(s != null and s.can_instantiate(), "compiles: " + path)

func _test_vocabulary() -> void:
	check(Vocab.worlds.size() == 8, "8 worlds")
	for t in Vocab.LANG_NAMES.keys():
		for w in Vocab.worlds.size():
			var n := Vocab.playable_words(w, t).size()
			check(n >= 17, "world %d has enough playable words in %s (%d)" % [w, t, n])
		var rows: Array = Vocab.keyboard_rows(t)
		var keys := "".join(rows[0]) + "".join(rows[1])
		for word in Vocab.all_words():
			for c in Vocab.answer(word, t):
				check(keys.contains(c), "keyboard %s can type %s in %s" % [t, c, Vocab.answer(word, t)])

func _test_levels_generate() -> void:
	for t in Vocab.LANG_NAMES.keys():
		for w in Vocab.worlds.size():
			for l in Vocab.LEVELS_PER_WORLD:
				var built := Vocab.crossword_entries(Vocab.level_words(w, l, t), t)
				var entries: Array = built[0]
				var layout := CrosswordGenerator.generate(entries, hash("%d%d%s" % [w, l, t]), built[1])
				var placed: int = layout["placements"].size()
				check(placed >= entries.size(), "%s w%d l%d placed %d/%d" % [t, w, l, placed, entries.size()])
				check(layout["width"] <= 13 and layout["height"] <= 13, "%s w%d l%d fits 13x13" % [t, w, l])
				check(_layout_valid(layout), "%s w%d l%d layout is consistent" % [t, w, l])

## Every pair of horizontally/vertically adjacent letters must belong to one placed word.
func _layout_valid(layout: Dictionary) -> bool:
	var grid := {}
	var owner := {}
	for p in layout["placements"]:
		var step: Vector2i = Vector2i(1, 0) if p["dir"] == 0 else Vector2i(0, 1)
		for k in p["answer"].length():
			var pos: Vector2i = Vector2i(p["col"], p["row"]) + step * k
			if grid.has(pos) and grid[pos] != p["answer"][k]:
				return false
			grid[pos] = p["answer"][k]
			if k > 0:
				owner[[pos - step, pos]] = true
	for pos in grid.keys():
		for step in [Vector2i(1, 0), Vector2i(0, 1)]:
			if grid.has(pos + step) and not owner.has([pos, pos + step]):
				return false
	return true

func _test_puzzle_flow() -> void:
	var t := "fr"
	var entries := []
	for word in Vocab.level_words(1, 0, t):
		entries.append({"answer": Vocab.answer(word, t), "word": word})
	var s := PuzzleState.new()
	s.setup(CrosswordGenerator.generate(entries, 7))
	var done := [false]
	s.completed.connect(func(): done[0] = true)
	# Type every answer through the public API, the way the keyboard does.
	for i in s.placements.size():
		if s.solved.has(i):
			continue
		s.select_word(i)
		for c in s.word_cells(i):
			s.cursor = c
			s.dir = s.placements[i]["dir"]
			s.type_letter(Vocab.base_letter(s.cells[c]["sol"]))
	check(done[0] and s.is_complete(), "typing all answers (accents relaxed) completes the puzzle")
	check(s.stars() == 3, "clean solve gives 3 stars")

	var s2 := PuzzleState.new()
	s2.setup(CrosswordGenerator.generate(entries, 7))
	s2.select_word(0)
	var wrong := 0
	s2.word_wrong.connect(func(_i): wrong += 1)
	for c in s2.word_cells(0):
		s2.cursor = c
		s2.dir = s2.placements[0]["dir"]
		s2.type_letter("Q" if s2.cells[c]["sol"] != "Q" else "Z")
	check(s2.mistakes >= 1, "a fully wrong word counts as a mistake")
	s2.select_word(0)
	s2.reveal_word()
	check(s2.solved.has(0) and s2.word_help[0] == 2, "reveal word solves it and marks it revealed")

func _test_srs() -> void:
	var id: String = Vocab.worlds[0]["words"][0]["id"]
	Game.data["srs"] = {}
	Game.record_word(id, 0)
	check(int(Game.memory(id)["box"]) == 1, "clean solve promotes to box 1")
	Game.record_word(id, 0)
	Game.record_word(id, 0)
	check(int(Game.memory(id)["box"]) == 3, "three clean solves reach box 3")
	Game.record_word(id, 2)
	check(int(Game.memory(id)["box"]) == 1, "revealed word drops back to box 1")
	check(Game.due_words().is_empty(), "nothing is due right after practice")
	Game.load_game()
