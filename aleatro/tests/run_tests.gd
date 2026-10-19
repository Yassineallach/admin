extends SceneTree
## Headless checks. Run with:
##   godot --headless --path . --import
##   godot --headless --path . -s res://tests/run_tests.gd

var failures := 0
var RunState: GDScript = load("res://scripts/run_state.gd")


func _init() -> void:
	_test_hands()
	_test_scoring()
	_test_simulated_runs()
	print("Tests finished: %d failure(s)" % failures)
	quit(1 if failures > 0 else 0)


func check(cond: bool, what: String) -> void:
	if not cond:
		failures += 1
		printerr("FAIL: " + what)


func cards(spec: Array) -> Array:
	var out := []
	for i in spec.size():
		out.append({"id": i, "rank": spec[i][0], "suit": spec[i][1], "enh": spec[i][2] if spec[i].size() > 2 else ""})
	return out


func _test_hands() -> void:
	var cases := [
		[[[14, 0]], "high", 1],
		[[[5, 0], [5, 1], [9, 2]], "pair", 2],
		[[[5, 0], [5, 1], [9, 2], [9, 3], [2, 0]], "two_pair", 4],
		[[[7, 0], [7, 1], [7, 2], [3, 3]], "three", 3],
		[[[14, 0], [2, 1], [3, 2], [4, 3], [5, 0]], "straight", 5],
		[[[10, 0], [11, 1], [12, 2], [13, 3], [14, 0]], "straight", 5],
		[[[2, 1], [6, 1], [9, 1], [11, 1], [13, 1]], "flush", 5],
		[[[4, 0], [4, 1], [4, 2], [8, 3], [8, 0]], "full_house", 5],
		[[[9, 0], [9, 1], [9, 2], [9, 3], [2, 0]], "four", 4],
		[[[5, 3], [6, 3], [7, 3], [8, 3], [9, 3]], "straight_flush", 5],
		[[[6, 0], [6, 1], [6, 2], [6, 3], [6, 0]], "five", 5],
		[[[11, 0], [12, 1], [13, 2], [14, 3], [2, 0]], "high", 1],
	]
	for c in cases:
		var ev := HandEval.evaluate(cards(c[0]))
		check(ev.hand == c[1], "hand %s expected %s got %s" % [str(c[0]), c[1], ev.hand])
		check(ev.scoring.size() == c[2], "scoring count for %s expected %d got %d" % [c[1], c[2], ev.scoring.size()])


func _test_scoring() -> void:
	var run = RunState.new()
	run.new_run(1234)
	# Pair of kings: (12 + 10 + 10) x 2 = 64
	var played := cards([[13, 0], [13, 1], [4, 2]])
	var r := Scoring.score_play(run, played, [])
	check(r.total == 64.0, "pair of kings expected 64 got %s" % r.total)
	# Lucky Penny (+4 Mult) and Loaded Die (x1.5), in that order: 32 x (2 + 4) x 1.5 = 288
	run.charms = [Charms.make("lucky_penny"), Charms.make("loaded_die")]
	r = Scoring.score_play(run, played, [])
	check(r.total == 288.0, "charm order expected 288 got %s" % r.total)
	# Reversed order: 32 x (2 x 1.5 + 4) = 224
	run.charms.reverse()
	r = Scoring.score_play(run, played, [])
	check(r.total == 224.0, "reversed charm order expected 224 got %s" % r.total)
	# Bonus card and held Iron card: (12 + 10 + 25 + 10) x 2 x 1.5 = 171
	run.charms = []
	var enh := cards([[13, 0, "bonus"], [13, 1], [2, 2, "iron"]])
	r = Scoring.score_play(run, [enh[0], enh[1]], [enh[2]])
	check(r.total == 171.0, "enhancements expected 171 got %s" % r.total)
	# Hand levels: Pair Lv.2 = 27 points, 3 mult
	run.hand_levels["pair"] = 2
	r = Scoring.score_play(run, played, [])
	check(r.total == (27.0 + 20.0) * 3.0, "pair level 2 expected 141 got %s" % r.total)
	run.free()


## Plays whole runs with a greedy bot to catch runtime errors and gauge difficulty.
func _test_simulated_runs() -> void:
	var floors := []
	for s in 40:
		var run = RunState.new()
		run.new_run(1000 + s)
		var guard := 0
		var done := false
		while not done and guard < 200:
			guard += 1
			run.start_trial()
			while not run.trial_won and not run.is_lost():
				var best := _best_play(run)
				if run.discards_left > 0 and best.total < (run.target() - run.score) / maxf(1.0, run.hands_left) * 0.5:
					var low: Array = run.hand.duplicate()
					low.sort_custom(func(a, b): return a.rank < b.rank)
					run.discard(low.slice(0, 3))
					continue
				run.play(best.cards)
			if run.is_lost():
				done = true
				break
			run.collect(run.trial_rewards())
			run.open_shop()
			for i in run.shop_offers.size():
				if run.shop_offers[i].type != "sold" and run.coins - run.shop_offers[i].price >= 2:
					run.buy(i)
			if run.advance() == "victory":
				done = true
				floors.append(99)
		if floors.size() <= s:
			floors.append(run.floor_num)
		check(run.deck.size() > 0, "deck never empties")
		run.free()
	floors.sort()
	var wins := floors.count(99)
	print("Simulated 40 bot runs. Floors reached: %s  (wins: %d)" % [str(floors), wins])


func _best_play(run) -> Dictionary:
	var hand: Array = run.hand
	var best := {"total": -1.0, "cards": []}
	var need := 5 if run.current_warden() == "glutton" else 0
	var n := hand.size()
	for mask in range(1, 1 << n):
		var pick := []
		for i in n:
			if mask & (1 << i):
				pick.append(hand[i])
		if pick.size() > 5 or (need > 0 and pick.size() != need):
			continue
		var held := hand.filter(func(c): return not pick.has(c))
		var r := Scoring.score_play(run, pick, held)
		if r.total > best.total:
			best = {"total": r.total, "cards": pick}
	return best
