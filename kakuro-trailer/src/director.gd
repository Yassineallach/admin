extends Node
## Trailer capture director (capture copy only, not part of the game).
## Runs the real game and performs each trailer moment with real touch input,
## printing "MARK t name" and "TAP t x y kind" lines (window pixels) for the edit.

var main: Main
var t := 0.0
var scale_px := 1.0


func _process(delta: float) -> void:
	t += delta


func mark(name: String) -> void:
	print("MARK %.4f %s" % [t, name])


func wait(sec: float) -> void:
	await get_tree().create_timer(sec).timeout


func win_pos(p: Vector2) -> Vector2:
	return p * scale_px


func _mouse(p: Vector2, pressed: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = MOUSE_BUTTON_LEFT
	ev.pressed = pressed
	ev.position = win_pos(p)
	ev.global_position = ev.position
	Input.parse_input_event(ev)


func _motion(p: Vector2) -> void:
	var ev := InputEventMouseMotion.new()
	ev.position = win_pos(p)
	ev.global_position = ev.position
	ev.button_mask = MOUSE_BUTTON_MASK_LEFT
	Input.parse_input_event(ev)


func tap(p: Vector2, kind: String = "tap", hold: float = 0.09) -> void:
	var w := win_pos(p)
	print("TAP %.4f %.1f %.1f %s" % [t, w.x, w.y, kind])
	_mouse(p, true)
	await wait(hold)
	_mouse(p, false)


func cell_pos(g, i: int) -> Vector2:
	return g.board.cell_center_global(i)


func key_pos(g, d: int) -> Vector2:
	var r: Rect2 = g.pad._key_rect(d - 1)
	return g.pad.get_global_transform() * r.get_center()


func put(g, i: int, d: int, gap: float = 0.22) -> void:
	await tap(cell_pos(g, i))
	await wait(gap)
	await tap(key_pos(g, d), "key")


func ring_put(g, i: int, d: int) -> void:
	var c := cell_pos(g, i)
	var w := win_pos(c)
	print("TAP %.4f %.1f %.1f ringstart" % [t, w.x, w.y])
	await tap(c)           # select
	await wait(0.25)
	_mouse(c, true)
	await wait(0.42)       # hold: the ring fans out
	var maxd: int = g.state.puzzle.max_digit
	var ang := -PI / 2 + (d - 1) * TAU / maxd
	var cpx: float = g.board.cell_px()
	var target: Vector2 = c + Vector2(cos(ang), sin(ang)) * cpx * 1.55
	for k in 10:
		var p := c.lerp(target, (k + 1) / 10.0)
		_motion(p)
		var wp := win_pos(p)
		print("DRAG %.4f %.1f %.1f" % [t, wp.x, wp.y])
		await wait(0.035)
	await wait(0.25)
	_mouse(target, false)
	var wt := win_pos(target)
	print("TAP %.4f %.1f %.1f ringend" % [t, wt.x, wt.y])


func run_order(p) -> Array:
	## Cells in solving order: runs one by one, across first, top to bottom.
	var order: Array = []
	var seen := {}
	var runs: Array = p.runs.duplicate()
	runs.sort_custom(func(a, b): return (a["cells"][0] as int) < (b["cells"][0] as int))
	for r in runs:
		for c in r["cells"]:
			if not seen.has(c):
				seen[c] = true
				order.append(c)
	return order


func _ready() -> void:
	Motion.auto_detect = false
	GameData.set_setting("language", "en")
	GameData.set_setting("dark", false)
	GameData.set_setting("music", false)     # music is laid in the edit; sfx are recorded
	GameData.set_setting("haptics", false)
	GameData.set_flag("onboarded", true)
	GameData.set_flag("ring_tip", true)
	GameData.hint_balance = 30
	GameData.levels_done["0"] = range(0, 12)
	for i in 12:
		GameData.level_stars["0:%d" % i] = 3 if i % 4 != 2 else 2
		GameData.level_times["0:%d" % i] = 60 + i * 7
	GameData.play_diff = 0
	GameData.daily["streak"] = 6
	GameData.daily["best_streak"] = 9
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	scale_px = float(get_window().size.x) / get_viewport().get_visible_rect().size.x
	print("SCALE ", scale_px, " WIN ", get_window().size, " VIS ", get_viewport().get_visible_rect().size)

	# ---- 1. Launch splash over the title screen
	mark("splash")
	var sp := SplashOverlay.new()
	main.add_child(sp)
	await wait(3.9)

	# ---- 2. Title screen: fresh entrance, poke Kaku
	main.go("menu", {}, false)
	mark("menu")
	await wait(1.6)
	var m = main.current
	await tap(m.mascot.get_global_rect().get_center(), "tap")
	mark("kaku_poke")
	await wait(1.6)
	await tap(m.play.get_global_rect().get_center(), "tap")
	mark("play_tap")
	await wait(0.2)

	# ---- 3. Level map
	main.go("levels", {"diff": 0})
	mark("levels")
	await wait(1.8)
	var maps := main.current.find_children("*", "LevelMap", true, false)
	if maps.size() > 0:
		var lm = maps[0]
		await tap(lm.get_global_transform() * lm.node_center(12), "tap")
	mark("level_tap")
	await wait(0.3)
	if main.route != "game":
		main.go("game", {"mode": "level", "diff": 0, "index": 12})

	# ---- 4. Gameplay: an Easy level, played for real
	await wait(1.2)
	mark("game1")
	var g = main.current
	var s = g.state
	var order := run_order(s.puzzle)
	var sol = s.puzzle.solution
	# first two runs at a steady pace
	var n_first := 0
	for i in order.slice(0, 5):
		await put(g, i, sol[i])
		await wait(0.30)
		n_first += 1
	mark("ring")
	await ring_put(g, order[5], sol[order[5]])
	await wait(0.6)
	# a mistake: auto check on, a wrong digit, Kaku says oops
	GameData.set_setting("auto_check", true)
	var wi: int = order[6]
	var wrong := (int(sol[wi]) % 9) + 1
	mark("mistake")
	await put(g, wi, wrong)
	await wait(1.1)
	await tap(key_pos(g, sol[wi]), "key")
	GameData.set_setting("auto_check", false)
	await wait(0.6)
	# a hint: Lumo explains the logic
	mark("hint")
	await tap(g.tool_hint.get_global_rect().get_center(), "tap")
	await wait(3.6)
	# finish: quick, rhythmic fill
	mark("finish")
	for i in order:
		if s.values[i] == 0:
			await put(g, i, sol[i], 0.12)
			await wait(0.12)
	mark("win")
	await wait(5.5)

	# ---- 5. Bigger grids: Medium, Hard, Expert (fast fills)
	for spec in [[1, 7, "medium"], [2, 4, "hard"], [3, 2, "expert"]]:
		main.go("game", {"mode": "level", "diff": spec[0], "index": spec[1]}, false)
		await wait(0.9)
		mark(spec[2])
		var gg = main.current
		var ss = gg.state
		var ord := run_order(ss.puzzle)
		for k in mini(ord.size(), 26):
			var ci: int = ord[k]
			gg._select(ci, false)
			gg._digit(ss.puzzle.solution[ci])
			await wait(0.09)
		await wait(0.8)

	# ---- 6. Daily Challenge with Blaze, Quick Play with Zip
	main.go("game", {"mode": "daily", "diff": 1, "date_key": GameData.today_key()}, false)
	var tw := 0.0
	while main.current.state == null and tw < 30.0:
		await wait(0.2); tw += 0.2
	mark("daily")
	await wait(2.6)
	main.go("game", {"mode": "quick", "diff": 0}, false)
	tw = 0.0
	while main.current.state == null and tw < 30.0:
		await wait(0.2); tw += 0.2
	mark("quick")
	await wait(2.6)

	# ---- 7. Chapter unlocked: Kaku's celebration
	main.go("levels", {"diff": 0}, false)
	await wait(0.3)
	mark("unlock")
	main.show_chapter_unlock(0, 1)
	await wait(6.5)

	# ---- 8. End card stage: logo + Kaku on the title stage
	main.clear_overlays()
	var card := Control.new()
	card.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	main.add_child(card)
	var bd := TitleBackdrop.new()
	bd.size = get_viewport().get_visible_rect().size
	card.add_child(bd)
	var box := UI.vbox(0)
	box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	card.add_child(box)
	var top := UI.spacer(8, true)
	box.add_child(top)
	var kaku := Mascot.new()
	kaku.custom_minimum_size = Vector2(300, 320)
	kaku.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	kaku.mood = "happy"
	box.add_child(kaku)
	var logo := TitleLogo.new()
	box.add_child(logo)
	var bottom := UI.spacer(8, true)
	bottom.size_flags_stretch_ratio = 1.6
	box.add_child(bottom)
	mark("endcard")
	await wait(0.9)
	kaku.hop(1.0)
	await wait(1.6)
	kaku.react("yay", 2.0)
	kaku.hop(1.2)
	await wait(3.0)
	var r := logo.get_global_rect()
	print("LOGO %.1f %.1f %.1f %.1f" % [r.position.x * scale_px, r.position.y * scale_px, r.size.x * scale_px, r.size.y * scale_px])
	mark("done")
	get_tree().quit()
