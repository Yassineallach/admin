extends Node
## Renders a set of gameplay screenshots (needs a real display / Xvfb).
## Run: godot --path . --rendering-driver opengl3 res://tests/screenshots.tscn -- <out_dir>

var out_dir := "user://shots"
var game: Game


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0]
	DirAccess.make_dir_recursive_absolute(out_dir)

	var menu := MainMenu.new()
	var layer := CanvasLayer.new()
	layer.add_child(menu)
	add_child(layer)
	await settle(10)
	await shot("00_menu")
	layer.queue_free()

	await load_level(0)
	await pose(Vector3(0, 0, 3), 0, -8)
	await shot("01_found_photograph_start")
	await pose(Vector3(0, 0, 1.6), 0, 0)
	await settle(4)
	await pose(Vector3(0, 0, -3.6), 0, -20)
	game.raise_photo(0)
	await shot("02_holding_photo")
	game.place_photo()
	await settle(8)
	await pose(Vector3(0, 0, -3.6), 0, -12)
	await shot("03_bridge_placed")

	await load_level(1)
	await pose(Vector3(0, 0, 4), 180, 0)
	game.camera_mode = true
	await shot("04_viewfinder")
	await game.take_photo()
	await pose(Vector3(0, 0, -4), 0, 0)
	await shot("05_cliff_before")
	game.raise_photo(0)
	game.place_photo()
	await settle(8)
	await pose(Vector3(1.5, 0, -6), 15, 5)
	await shot("06_cliff_after")

	await load_level(4)
	await pose(Vector3(3.5, 0, 3.5), 0, 89)
	await shot("07_shaft_up")
	await game.take_photo()
	await pose(Vector3(0, 0, -2), 0, 0)
	game.raise_photo(0)
	game.place_photo()
	await settle(8)
	await pose(Vector3(0, 0, -3), 0, 0)
	await shot("08_tunnel")

	await load_level(2)
	await pose(Vector3(0, 0, -5.6), 0, 0)
	await shot("09_window")
	get_tree().quit()


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
