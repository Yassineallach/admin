class_name CrosswordGenerator
extends RefCounted
## Builds a compact, fully-interlocked crossword layout from a list of answers.
## Runs several seeded greedy attempts and keeps the best-scoring grid.

const ACROSS := 0
const DOWN := 1

## entries: Array of {"answer": String, ...}. Extra keys are carried through.
## Returns {"width", "height", "placements": [{answer, row, col, dir, number, ...}]}.
## spares: optional substitutes used when some entries cannot be interlocked.
static func generate(entries: Array, seed_value: int, spares: Array = [], max_size := 13, attempts := 80) -> Dictionary:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var best := {}
	var best_score := -INF
	for a in attempts:
		# Longest first gives the skeleton, but jitter keeps attempts different.
		var keyed := []
		for e in entries:
			keyed.append([e["answer"].length() + rng.randf() * 3.0, e])
		keyed.sort_custom(func(x, y): return x[0] > y[0])
		var order := keyed.map(func(k): return k[1])
		var result := _attempt(order, spares, entries.size(), rng, max_size)
		var score := _score(result)
		if score > best_score:
			best_score = score
			best = result
		if result["placements"].size() == entries.size() and a > 20:
			break
	return _finalize(best)

static func _attempt(order: Array, spares: Array, want: int, rng: RandomNumberGenerator, max_size: int) -> Dictionary:
	var grid := {}      # Vector2i -> letter
	var used := {}      # Vector2i -> bitmask of directions using the cell
	var placements := []
	var pending := order.duplicate()
	var first: Dictionary = pending.pop_front()
	var dir0 := ACROSS if rng.randf() < 0.7 else DOWN
	_place(grid, used, placements, first, 0, 0, dir0)
	var progress := true
	while progress and not pending.is_empty():
		progress = false
		for e in pending.duplicate():
			var options := _candidates(grid, used, e["answer"], max_size)
			if options.is_empty():
				continue
			options.sort_custom(func(x, y): return x[3] > y[3])
			var top := mini(3, options.size())
			var pick: Array = options[rng.randi_range(0, top - 1)] if rng.randf() < 0.35 else options[0]
			_place(grid, used, placements, e, pick[0], pick[1], pick[2])
			pending.erase(e)
			progress = true
	for e in spares:
		if placements.size() >= want:
			break
		var options := _candidates(grid, used, e["answer"], max_size)
		if not options.is_empty():
			options.sort_custom(func(x, y): return x[3] > y[3])
			_place(grid, used, placements, e, options[0][0], options[0][1], options[0][2])
	return {"grid": grid, "placements": placements}

static func _place(grid: Dictionary, used: Dictionary, placements: Array, e: Dictionary, r: int, c: int, d: int) -> void:
	var w: String = e["answer"]
	var step := Vector2i(1, 0) if d == ACROSS else Vector2i(0, 1)
	for i in w.length():
		var p := Vector2i(c, r) + step * i
		grid[p] = w[i]
		used[p] = used.get(p, 0) | (1 << d)
	var p2 := e.duplicate()
	p2["row"] = r
	p2["col"] = c
	p2["dir"] = d
	placements.append(p2)

## Returns [row, col, dir, score] for every legal crossing placement.
static func _candidates(grid: Dictionary, used: Dictionary, w: String, max_size: int) -> Array:
	var out := []
	var bounds := _bounds(grid)
	var b0: Vector2i = bounds[0]
	var b1: Vector2i = bounds[1]
	var area := (b1.x - b0.x + 1) * (b1.y - b0.y + 1)
	for cell in grid.keys():
		var letter: String = grid[cell]
		for i in w.length():
			if w[i] != letter:
				continue
			for d in [ACROSS, DOWN]:
				if used[cell] & (1 << d):
					continue
				var step := Vector2i(1, 0) if d == ACROSS else Vector2i(0, 1)
				var start: Vector2i = cell - step * i
				var res := _check(grid, used, w, start, d)
				if res < 0:
					continue
				var end := start + step * (w.length() - 1)
				var mn := Vector2i(mini(b0.x, start.x), mini(b0.y, start.y))
				var mx := Vector2i(maxi(b1.x, end.x), maxi(b1.y, end.y))
				var wdt := mx.x - mn.x + 1
				var hgt := mx.y - mn.y + 1
				if wdt > max_size or hgt > max_size:
					continue
				var growth := wdt * hgt - area
				var squareness := absi(wdt - hgt)
				out.append([start.y, start.x, d, res * 12.0 - growth * 0.35 - squareness * 0.8])
	return out

## Number of crossings if legal, -1 otherwise.
static func _check(grid: Dictionary, used: Dictionary, w: String, start: Vector2i, d: int) -> int:
	var step := Vector2i(1, 0) if d == ACROSS else Vector2i(0, 1)
	var perp := Vector2i(0, 1) if d == ACROSS else Vector2i(1, 0)
	if grid.has(start - step) or grid.has(start + step * w.length()):
		return -1
	var crossings := 0
	for i in w.length():
		var p := start + step * i
		if grid.has(p):
			if grid[p] != w[i] or (used[p] & (1 << d)):
				return -1
			crossings += 1
		else:
			if grid.has(p + perp) or grid.has(p - perp):
				return -1
	return crossings if crossings > 0 else -1

static func _bounds(grid: Dictionary) -> Array:
	var mn := Vector2i(1 << 20, 1 << 20)
	var mx := Vector2i(-(1 << 20), -(1 << 20))
	for p in grid.keys():
		mn = Vector2i(mini(mn.x, p.x), mini(mn.y, p.y))
		mx = Vector2i(maxi(mx.x, p.x), maxi(mx.y, p.y))
	return [mn, mx]

static func _score(result: Dictionary) -> float:
	var b := _bounds(result["grid"])
	var w: int = b[1].x - b[0].x + 1
	var h: int = b[1].y - b[0].y + 1
	var density := float(result["grid"].size()) / float(w * h)
	return result["placements"].size() * 100.0 + density * 40.0 - absi(w - h) * 2.0 - maxi(w, h) * 1.5

## Normalises coordinates to start at 0,0 and assigns clue numbers.
static func _finalize(result: Dictionary) -> Dictionary:
	if result.is_empty():
		return {"width": 0, "height": 0, "placements": []}
	var b := _bounds(result["grid"])
	var mn: Vector2i = b[0]
	var placements: Array = result["placements"]
	for p in placements:
		p["row"] -= mn.y
		p["col"] -= mn.x
	placements.sort_custom(func(x, y): return x["row"] < y["row"] or (x["row"] == y["row"] and (x["col"] < y["col"] or (x["col"] == y["col"] and x["dir"] < y["dir"]))))
	var numbers := {}
	var next := 1
	for p in placements:
		var key := Vector2i(p["col"], p["row"])
		if not numbers.has(key):
			numbers[key] = next
			next += 1
		p["number"] = numbers[key]
	return {
		"width": b[1].x - mn.x + 1,
		"height": b[1].y - mn.y + 1,
		"placements": placements,
	}
