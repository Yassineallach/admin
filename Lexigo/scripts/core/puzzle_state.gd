class_name PuzzleState
extends RefCounted
## Runtime state of one crossword: cells, cursor, solved words and scoring.

signal word_solved(index: int)
signal word_wrong(index: int)
signal completed

var width := 0
var height := 0
var placements: Array = []        # from CrosswordGenerator
var cells := {}                   # Vector2i -> {sol, val, locked, words:[across_idx, down_idx]}
var solved := {}                  # placement index -> true
var cursor := Vector2i.ZERO
var dir := CrosswordGenerator.ACROSS
var strict_accents := false
var mistakes := 0
var hints_used := 0
var word_help := {}               # placement index -> 0 clean, 1 helped, 2 revealed

func setup(layout: Dictionary) -> void:
	width = layout["width"]
	height = layout["height"]
	placements = layout["placements"]
	cells.clear()
	for i in placements.size():
		var p: Dictionary = placements[i]
		var step := _step(p["dir"])
		var ans: String = p["answer"]
		for k in ans.length():
			var pos := Vector2i(p["col"], p["row"]) + step * k
			if not cells.has(pos):
				cells[pos] = {"sol": ans[k], "val": "", "locked": false, "words": [-1, -1]}
			cells[pos]["words"][p["dir"]] = i
		word_help[i] = 0
	if not placements.is_empty():
		select_word(0)

func _step(d: int) -> Vector2i:
	return Vector2i(1, 0) if d == CrosswordGenerator.ACROSS else Vector2i(0, 1)

func word_cells(i: int) -> Array:
	var p: Dictionary = placements[i]
	var out := []
	for k in p["answer"].length():
		out.append(Vector2i(p["col"], p["row"]) + _step(p["dir"]) * k)
	return out

func current_word() -> int:
	if not cells.has(cursor):
		return -1
	var w: int = cells[cursor]["words"][dir]
	if w < 0:
		w = cells[cursor]["words"][1 - dir]
	return w

func select_word(i: int) -> void:
	dir = placements[i]["dir"]
	var cs := word_cells(i)
	cursor = cs[0]
	for c in cs:
		if cells[c]["val"] == "":
			cursor = c
			break

func tap(pos: Vector2i) -> void:
	if not cells.has(pos):
		return
	if pos == cursor:
		var other: int = cells[pos]["words"][1 - dir]
		if other >= 0:
			dir = 1 - dir
	else:
		cursor = pos
		if cells[pos]["words"][dir] < 0:
			dir = 1 - dir

func letters_match(typed: String, sol: String) -> bool:
	if typed == sol:
		return true
	return not strict_accents and Vocab.base_letter(typed) == Vocab.base_letter(sol)

func type_letter(letter: String) -> void:
	if not cells.has(cursor):
		return
	var cell: Dictionary = cells[cursor]
	if not cell["locked"]:
		cell["val"] = letter
	var w := current_word()
	_check_words_at(cursor)
	_advance(w)

func _advance(w: int) -> void:
	if w < 0:
		return
	if solved.has(w):
		next_word(1)
		return
	var cs := word_cells(w)
	var idx := cs.find(cursor)
	for k in range(idx + 1, cs.size()):
		if not cells[cs[k]]["locked"]:
			cursor = cs[k]
			return
	for k in range(0, idx):
		if cells[cs[k]]["val"] == "":
			cursor = cs[k]
			return

func backspace() -> void:
	if not cells.has(cursor):
		return
	var cell: Dictionary = cells[cursor]
	if cell["val"] != "" and not cell["locked"]:
		cell["val"] = ""
		return
	var w := current_word()
	if w < 0:
		return
	var cs := word_cells(w)
	var idx := cs.find(cursor)
	for k in range(idx - 1, -1, -1):
		if not cells[cs[k]]["locked"]:
			cursor = cs[k]
			cells[cursor]["val"] = ""
			return

func next_word(delta: int) -> void:
	var n := placements.size()
	var w := maxi(current_word(), 0)
	for step in range(1, n + 1):
		var cand := posmod(w + step * delta, n)
		if not solved.has(cand):
			select_word(cand)
			return

func _check_words_at(pos: Vector2i) -> void:
	for w in cells[pos]["words"]:
		if w < 0 or solved.has(w):
			continue
		var cs := word_cells(w)
		var full := true
		var ok := true
		for c in cs:
			var cell: Dictionary = cells[c]
			if cell["val"] == "":
				full = false
				break
			if not letters_match(cell["val"], cell["sol"]):
				ok = false
		if not full:
			continue
		if ok:
			_solve(w)
		else:
			mistakes += 1
			word_help[w] = maxi(word_help[w], 1)
			word_wrong.emit(w)

func _solve(w: int) -> void:
	solved[w] = true
	for c in word_cells(w):
		cells[c]["val"] = cells[c]["sol"]
		cells[c]["locked"] = true
	word_solved.emit(w)
	# A locked letter may complete a crossing word as well.
	for c in word_cells(w):
		for other in cells[c]["words"]:
			if other >= 0 and other != w and not solved.has(other):
				var all_ok := true
				for oc in word_cells(other):
					if cells[oc]["val"] == "" or not letters_match(cells[oc]["val"], cells[oc]["sol"]):
						all_ok = false
						break
				if all_ok:
					_solve(other)
	if is_complete():
		completed.emit()

func is_complete() -> bool:
	return solved.size() == placements.size()

func clear_wrong(w: int) -> void:
	for c in word_cells(w):
		var cell: Dictionary = cells[c]
		if not cell["locked"] and not letters_match(cell["val"], cell["sol"]):
			cell["val"] = ""

## Reveals the cursor cell (or the first open cell of the word). Returns it.
func reveal_letter() -> Vector2i:
	var w := current_word()
	if w < 0 or solved.has(w):
		return Vector2i(-1, -1)
	var target := cursor
	if cells[target]["locked"] or letters_match(cells[target]["val"], cells[target]["sol"]):
		for c in word_cells(w):
			if not cells[c]["locked"] and not letters_match(cells[c]["val"], cells[c]["sol"]):
				target = c
				break
	cells[target]["val"] = cells[target]["sol"]
	cells[target]["locked"] = true
	hints_used += 1
	for i in cells[target]["words"]:
		if i >= 0:
			word_help[i] = maxi(word_help[i], 1)
	cursor = target
	_check_words_at(target)
	_advance(w)
	return target

func reveal_word() -> int:
	var w := current_word()
	if w < 0 or solved.has(w):
		return -1
	hints_used += 2
	word_help[w] = 2
	_solve(w)
	if not is_complete():
		next_word(1)
	return w

func stars() -> int:
	if mistakes <= 1 and hints_used == 0:
		return 3
	if mistakes <= 3 and hints_used <= 2:
		return 2
	return 1
