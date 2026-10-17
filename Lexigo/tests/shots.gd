extends Node
## Captures screenshots of each screen. Needs a display (e.g. xvfb-run):
##   godot --path . --resolution 720x1280 res://tests/shots.tscn -- <out_dir>

var out := "user://shots"

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if not args.is_empty():
		out = args[0]
	DirAccess.make_dir_recursive_absolute(out)
	Game.reset()
	Game.data["onboarded"] = false
	var main: Control = load("res://scripts/main.gd").new()
	add_child(main)
	await _wait(1.2)
	await _shot("1_onboarding")
	Game.set_languages("en", "fr")
	Game.data["onboarded"] = true
	# Pretend some progress so the map looks lived-in.
	for l in 6:
		Game.record_level(0, l, 3 - (l % 2))
	Game.record_level(1, 0, 2)
	Game.record_level(1, 1, 3)
	for w in Vocab.worlds[0]["words"]:
		Game.record_word(w["id"], 0)
	Game.add_xp(240)
	Game.touch_streak()
	main.goto_home()
	await _wait(1.6)
	await _shot("2_home")
	main.current._scroll.scroll_vertical = 0
	await _wait(0.5)
	await _shot("2b_home_top")
	main.play_level(1, 2)
	await _wait(1.6)
	var screen = main.current
	var st: PuzzleState = screen.state
	# Solve the first two words, leave a partial third.
	for i in 2:
		st.select_word(i)
		for c in st.word_cells(i):
			if not st.cells[c]["locked"]:
				st.cursor = c
				st.dir = st.placements[i]["dir"]
				screen._type(st.cells[c]["sol"])
	var w := 2
	while st.solved.has(w):
		w += 1
	st.select_word(w)
	screen._type(st.cells[st.cursor]["sol"])
	screen._shuffled[w] = "  ".join(Array(st.placements[w]["answer"].split("")).map(func(x): return x))
	screen._refresh()
	await _wait(1.2)
	await _shot("3_puzzle")
	for i in st.placements.size():
		if not st.solved.has(i):
			st.select_word(i)
			st.reveal_word()
	await _wait(4.5)
	await _shot("4_results")
	main.open_lexicon()
	await _wait(1.4)
	await _shot("5_words")
	main.open_settings()
	await _wait(1.4)
	await _shot("6_settings")
	Game.reset()
	get_tree().quit()

func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out.path_join(name + ".png"))
	print("shot ", name)
