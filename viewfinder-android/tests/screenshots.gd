extends Node
## Renders a set of gameplay screenshots (needs a real display / Xvfb).
## Run: godot --path . --rendering-driver opengl3 res://tests/screenshots.tscn -- <out_dir> [only]

var out_dir := "user://shots"
var only := ""
var game: Game


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0]
	if args.size() > 1:
		only = args[1]
	DirAccess.make_dir_recursive_absolute(out_dir)
	Progress.unlocked = 9

	if want("menu"):
		var root := Node.new()
		root.add_child(MenuBackdrop.new())
		var menu := MainMenu.new()
		var layer := CanvasLayer.new()
		layer.add_child(menu)
		root.add_child(layer)
		add_child(root)
		await settle(40)
		await shot("00_menu")
		root.queue_free()
		await settle(2)

	if want("hub"):
		await load_level(-1)
		await pose(Vector3(0, 0, 6.5), 0, -4)
		await shot("01_hub")
		await pose(Vector3(1.9, 0, 2.5), 0, -32)
		game.cat.watch(game.player.camera.global_position)
		await settle(30)
		await shot("02_miso")

	if want("l1"):
		await load_level(0)
		await pose(Vector3(0, 0, 3), 0, -8)
		await shot("03_found_photograph")
		await pose(Vector3(0, 0, 1.6), 0, 0)
		await settle(4)
		await pose(Vector3(0, 0, -3.6), 0, -20)
		game.raise_photo(0)
		await settle(20)
		await shot("04_holding_photo")
		game.place_photo()
		await settle(40)
		await pose(Vector3(0, 0, -3.0), 0, -10)
		await shot("05_bridge_placed")
		await pose(Vector3(5.5, 0.5, -6), 60, -8)
		game.player.frozen = true
		await shot("06_bridge_side")

	if want("l2"):
		await load_level(1)
		await pose(Vector3(0, 0, 4), 180, 0)
		game.camera_mode = true
		await shot("07_viewfinder")
		game.take_photo()
		await settle(28)
		await shot("08_eject")
		await settle(90)
		await pose(Vector3(0, 0, -4), 0, 0)
		game.raise_photo(0)
		game.place_photo()
		await settle(40)
		await pose(Vector3(2, 0, -6), 15, 8)
		await shot("09_stairs_pasted")

	if want("l5"):
		await load_level(4)
		await pose(Vector3(3.5, 0, 3.5), 0, 89)
		await shot("10_tower_up")
		await game.take_photo()
		await settle(90)
		await pose(Vector3(0, 0, -2), 0, 0)
		game.raise_photo(0)
		game.place_photo()
		await settle(40)
		await pose(Vector3(0, 0, -3), 0, 0)
		await shot("11_tunnel")

	if want("l6"):
		await load_level(5)
		await pose(Vector3(0, 0, 3.3), 180, -10)
		await shot("12_sketch_easel")
		await pose(Vector3(0, 0, 4.6), 180, 0)
		await settle(4)
		await pose(Vector3(0, 0, -9), 0, 0)
		game.raise_photo(0)
		await settle(20)
		await shot("13_holding_sketch")
		game.place_photo()
		await settle(40)
		await pose(Vector3(0, 0, -10.5), 0, 12)
		await shot("14_pencil_stairs")

	if want("l7"):
		await load_level(6)
		await pose(Vector3(-3, 0, 3.9), 0, 0)
		await settle(4)
		await pose(Vector3(0, 0, -2), 0, 0)
		game.raise_photo(0)
		await settle(20)
		await shot("15_holding_painting")
		game.place_photo()
		await settle(40)
		await pose(Vector3(0, 0, -3), 0, -6)
		await shot("16_painted_bridge")

	if want("done"):
		await load_level(0)
		game.player.global_position = Vector3(0, 0.3, -19)
		await settle(90)
		await shot("18_memory_restored")

	if want("ch2"):
		await load_level(8)
		await pose(Vector3(-1.5, 0, 4.5), 8, -6)
		await shot("20_power_cut")
		await pose(Vector3(0.5, 0, -6.4), 0, -5)
		await shot("20b_gate")
		await load_level(9)
		await pose(Vector3(1.5, 0, 6.8), 15, -8)
		await shot("21_two_keys")
		await load_level(10)
		await pose(Vector3(6, 0, 9), -55, 14)
		await shot("22_watchtower")
		await load_level(11)
		await pose(Vector3(0, 0, 7), 0, -2)
		await shot("23_plan_ahead")

	if want("l8"):
		await load_level(7)
		await pose(Vector3(0, 0, 8), 0, -6)
		await shot("17_darkroom")
	get_tree().quit()


func want(tag: String) -> bool:
	return only == "" or only.split(",").has(tag)


func settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func load_level(i: int) -> void:
	if game:
		game.queue_free()
		await settle(2)
	game = Game.new()
	game.level_index = i
	add_child(game)
	while not game.ready_to_play:
		await get_tree().process_frame
	game.hud.fade = 0.0
	game.hud._title_time = 0.0


func pose(pos: Vector3, yaw_deg: float, pitch_deg: float) -> void:
	game.player.global_position = pos
	game.player.velocity = Vector3.ZERO
	game.player.set_look(deg_to_rad(yaw_deg), deg_to_rad(pitch_deg))
	await settle(3)
	game.player.global_position = pos


func shot(name: String) -> void:
	await settle(6)
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join(name + ".png"))
	print("saved ", name)
