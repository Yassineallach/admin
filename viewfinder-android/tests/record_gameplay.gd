extends Node
## Scripted gameplay run for recording trailers/GIFs with Godot's Movie Maker:
##   godot --path . --write-movie out/frame.png --fixed-fps 30 res://tests/record_gameplay.tscn
## Everything goes through the real game (physics, slicer, HUD); only the
## "player's thumbs" are scripted.

var game: Game


func _ready() -> void:
	Progress.unlocked = 9
	Progress.settings["hub_intro_seen"] = true
	await _scene_found_photograph()
	await _scene_look_up()
	await _scene_sketchbook()
	get_tree().quit()


# --- helpers ---------------------------------------------------------------

func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func secs(t: float) -> void:
	await frames(int(t * 30.0))


func load_level(i: int) -> void:
	if game:
		await fade(1.0, 0.4)
		game.queue_free()
		await get_tree().process_frame
	game = Game.new()
	game.level_index = i
	add_child(game)
	while not game.ready_to_play:
		await get_tree().process_frame
	game.hud._say_lines.clear()


func fade(to: float, t: float) -> void:
	var from: float = game.hud.fade
	var n := int(t * 30.0)
	for k in n:
		game.hud.fade = lerpf(from, to, float(k + 1) / n)
		await get_tree().physics_frame


## Smoothly turn the view to (yaw, pitch) in degrees.
func look(yaw_deg: float, pitch_deg: float, t: float) -> void:
	var y0 := game.player.yaw
	var p0 := game.player.pitch
	var y1 := y0 + wrapf(deg_to_rad(yaw_deg) - y0, -PI, PI)
	var p1 := deg_to_rad(pitch_deg)
	var n := maxi(1, int(t * 30.0))
	for k in n:
		var e := smoothstep(0.0, 1.0, float(k + 1) / n)
		game.player.set_look(lerpf(y0, y1, e), lerpf(p0, p1, e))
		await get_tree().physics_frame


## Walk (with the virtual stick) towards a point, steering the view.
func walk_to(target: Vector3, pitch_deg: float = 0.0, max_t: float = 8.0, hop := false) -> void:
	var n := int(max_t * 30.0)
	for k in n:
		var p := game.player.global_position
		var d := Vector3(target.x - p.x, 0, target.z - p.z)
		if d.length() < 0.25:
			break
		var want := atan2(-d.x, -d.z)
		var yaw := game.player.yaw + wrapf(want - game.player.yaw, -PI, PI) * 0.15
		var pitch := lerpf(game.player.pitch, deg_to_rad(pitch_deg), 0.1)
		game.player.set_look(yaw, pitch)
		game.hud.stick_vec = Vector2(0, clampf(d.length() / 1.2, 0.35, 1.0))
		if hop and game.player.is_on_floor() and k % 25 == 0:
			game.player.jump_requested = true
		await get_tree().physics_frame
	game.hud.stick_vec = Vector2.ZERO
	await frames(4)


# --- scenes ----------------------------------------------------------------

func _scene_found_photograph() -> void:
	await load_level(0)
	game.player.set_look(0.0, deg_to_rad(-6))
	await fade(0.0, 0.6)
	await secs(0.6)
	await walk_to(Vector3(0, 0, 1.4), -10)      # walk into the polaroid on the table
	await secs(0.8)
	await look(0, -18, 0.8)
	await walk_to(Vector3(0, 0, -3.6), -18)     # to the edge of the gap
	await look(0, -20, 0.4)
	game.raise_photo(0)                         # hold it up
	await secs(1.6)
	game.place_photo()                          # the photo becomes the world
	await secs(1.4)
	await walk_to(Vector3(0, 0, -19), -6, 7.0, true)  # cross the bridge to the teleporter
	await secs(1.8)


func _scene_look_up() -> void:
	await load_level(4)
	game.player.global_position = Vector3(-1.5, 0, 3.5)
	game.player.set_look(deg_to_rad(-90), 0.0)
	await fade(0.0, 0.5)
	await walk_to(Vector3(3.5, 0, 3.5), 0)      # into the tower
	await look(-90, 89, 1.2)                    # look straight up
	game.toggle_camera_mode()
	await secs(0.9)
	await game.take_photo()
	await secs(1.6)
	await look(90, 0, 0.8)
	await walk_to(Vector3(-0.3, 0, 3.5), 0)     # back out of the door
	await walk_to(Vector3(0, 0, -2), 0)
	await look(0, 0, 0.6)
	game.raise_photo(0)
	await secs(1.2)
	game.place_photo()                          # the tower lies down as a tunnel
	await secs(1.0)
	await walk_to(Vector3(0, 0, -24), 0, 5.0)
	await secs(0.5)


func _scene_sketchbook() -> void:
	await load_level(5)
	game.player.set_look(PI, 0.0)
	await fade(0.0, 0.5)
	await walk_to(Vector3(0, 0, 4.6), -8)       # pick up the pencil sketch
	await secs(0.5)
	await look(0, 0, 1.0)
	await walk_to(Vector3(0, 0, -9), 0, 6.0)
	game.raise_photo(0)
	await secs(1.4)
	game.place_photo()
	await secs(0.8)
	await walk_to(Vector3(0, 7, -27), 14, 6.0)  # climb the pencil stairs
	await secs(1.0)
	await fade(1.0, 0.6)
