extends Node
## Headless integration test: solves every level with scripted inputs, using
## the real physics, slicer, rewind and teleporter logic.
## Run: godot --headless --fixed-fps 60 --path . res://tests/level_playthrough.tscn

var failures := 0
var game: Game


func _ready() -> void:
	for i in Levels.count():
		await _run_level(i)
	await _test_rewind()
	await _test_hub()
	await _test_wrong_moves()
	print("PLAYTHROUGH DONE, failures: ", failures)
	get_tree().quit(1 if failures > 0 else 0)


func check(cond: bool, msg: String) -> void:
	if cond:
		print("  ok   ", msg)
	else:
		failures += 1
		printerr("  FAIL ", msg)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func load_level(i: int) -> void:
	if game:
		game.queue_free()
		await get_tree().process_frame
	game = Game.new()
	game.level_index = i
	add_child(game)
	while not game.ready_to_play:
		await get_tree().process_frame
	await frames(5)


func pose(pos: Vector3, yaw_deg: float, pitch_deg: float) -> void:
	game.player.global_position = pos
	game.player.velocity = Vector3.ZERO
	game.player.set_look(deg_to_rad(yaw_deg), deg_to_rad(pitch_deg))
	await frames(2)
	game.player.global_position = pos
	game.player.set_look(deg_to_rad(yaw_deg), deg_to_rad(pitch_deg))


func snap() -> void:
	game.camera_mode = true
	await game.take_photo()


func place(idx: int) -> void:
	if game.raised != idx:
		game.raise_photo(idx)
	game.place_photo()
	await frames(4)


## Walk forward (hopping over small seams) until the level completes.
func walk_to_finish(seconds: float) -> bool:
	var t := 0
	while t < int(seconds * 60) and not game.completed:
		if t % 60 == 0 and OS.has_environment("DEBUG_WALK"):
			print("    t=", t, " pos=", game.player.global_position, " auto=", game._auto_rewind)
		game.player.move_input = Vector2(0, 1)
		game.hud.stick_vec = Vector2(0, 1)
		if game.player.is_on_floor() and t % 20 == 0:
			game.player.jump_requested = true
		await get_tree().physics_frame
		t += 1
	game.hud.stick_vec = Vector2.ZERO
	return game.completed


func ground_at(x: float, z: float, from_y := 20.0) -> float:
	var space := game.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(Vector3(x, from_y, z), Vector3(x, -20, z), 1)
	var hit := space.intersect_ray(q)
	return hit["position"].y if hit else -INF


func grab_nearest_battery(exclude_socketed := true) -> Battery:
	var best: Battery = null
	for b in game.batteries:
		if exclude_socketed and (b as Battery).socket >= 0:
			continue
		best = b
	if best == null:
		return null
	var bp := best.global_position
	var stand := bp + Vector3(0, 0, 1.4)
	stand.y = maxf(ground_at(stand.x, stand.z), 0.0)
	await pose(stand, 0, 0)
	var d := bp - game.player.camera.global_position
	var yaw := atan2(-d.x, -d.z)
	var pitch := atan2(d.y, Vector2(d.x, d.z).length())
	game.player.set_look(yaw, pitch)
	game.interact()
	await frames(2)
	return game.held


func deliver(b: Battery, socket_i: int) -> void:
	b.global_transform = Transform3D(Basis(), game.teleporter.socket_world(socket_i) + Vector3(0, 0.2, 0))
	b.set_held(false)
	game.held = null
	await frames(30)


func deliver_to(b: Battery, pos: Vector3) -> void:
	b.global_transform = Transform3D(Basis(), pos + Vector3(0, 0.2, 0))
	b.set_held(false)
	if game.held == b:
		game.held = null
	await frames(30)


func loose_batteries() -> Array:
	return game.batteries.filter(func(b): return (b as Battery).socket < 0)


func _run_level(i: int) -> void:
	print("Level ", i + 1, ": ", Levels.get_level(i)["name"])
	await load_level(i)
	match i:
		0:
			check(game.photos.is_empty(), "no photos at start")
			await pose(Vector3(0, 0, 1.6), 0, 0)
			await frames(3)
			check(game.photos.size() == 1, "found photo picked up")
			await pose(Vector3(0, 0, -3.6), 0, -18)
			await place(0)
			check(ground_at(0, -10) > -0.2 and ground_at(0, -10) < 0.2, "bridge spans the gap (y=%.2f)" % ground_at(0, -10))
		1:
			await pose(Vector3(0, 0, 4), 180, 1)
			await snap()
			check(game.photos.size() == 1, "photo taken")
			await pose(Vector3(0, 0, -4), 0, 0)
			await place(0)
			check(ground_at(0, -17) > 1.0, "ramp now leads up the cliff (y=%.2f)" % ground_at(0, -17))
		2:
			await pose(Vector3(0, 0, -5.6), 0, 0)
			await snap()
			check(game.photos.size() == 1 and game.photos[0].items.size() == 1, "photo copied the battery")
			await pose(Vector3(0, 0, 0), -90, 0)
			await place(0)
			await frames(40)
			check(game.batteries.size() == 2, "battery duplicated (%d)" % game.batteries.size())
			var b := game.batteries[1] as Battery
			check(b.global_position.x > 2.0 and b.global_position.y > 0.0, "copy is reachable at %s" % b.global_position)
			await pose(b.global_position + Vector3(-1.2, -b.global_position.y, 0), -90, -30)
			game.interact()
			check(game.held == b, "picked up the copy")
			await pose(Vector3(8, 0, 3.6), 0, -45)
			game.interact()
			await frames(60)
			check(b.socket == 0, "battery plugged into teleporter")
			check(game.teleporter.powered, "teleporter powered")
			await pose(Vector3(8, 0.3, 1.2), 0, 0)
			await frames(5)
		3:
			await pose(Vector3(0, 0, -1), 180, 0)
			await snap()
			await pose(Vector3(0, 0, -2.5), 0, 0)
			await place(0)
			check(ground_at(0, -7) > -0.2, "floor through the hole")
		4:
			await pose(Vector3(3.5, 0, 3.5), 0, 89)
			await snap()
			check(game.photos[0].solids.size() >= 3, "shaft walls captured (%d)" % game.photos[0].solids.size())
			await pose(Vector3(0, 0, -2), 0, 0)
			await place(0)
			var g := ground_at(0, -12, 2.5)
			check(absf(g) < 0.1, "tunnel floor is level with the ground (y=%.3f)" % g)
		5:
			await pose(Vector3(0, 0, 4.6), 180, 0)
			await frames(3)
			check(game.photos.size() == 1 and game.photos[0].kind == "sketch", "sketch picked up")
			var sketch_style := true
			for so in game.photos[0].solids:
				sketch_style = sketch_style and (so as Solid).style == Mat.STYLE_SKETCH
			check(sketch_style, "sketch geometry keeps the pencil style")
			await pose(Vector3(0, 0, -9), 0, 0)
			await place(0)
			check(ground_at(0, -20, 8.0) > 2.0, "pencil stairs climb the cliff (y=%.2f)" % ground_at(0, -20, 8.0))
		6:
			await pose(Vector3(-3, 0, 3.9), 0, 0)
			await frames(3)
			check(game.photos.size() == 1 and game.photos[0].kind == "painting", "painting picked up")
			await pose(Vector3(0, 0, -2), 0, 0)
			await place(0)
			var gy := ground_at(0, -12, 3.0)
			check(absf(gy) < 0.05, "painted bridge spans the gorge (y=%.2f)" % gy)
		7:
			# Aim down so the photo only grabs a patch of floor + the battery.
			await pose(Vector3(6, 0, 3.6), 0, -50)
			await snap()
			check(game.photos[0].items.size() == 1, "battery in photo")
			check(game.film == 1, "film decreased")
			await pose(Vector3(-5, 0, 3.6), 0, -47)
			await place(0)
			await frames(40)
			check(game.batteries.size() == 2, "second battery created")
			await pose(Vector3(0, 0, 4.4), 0, 0)
			await frames(3)
			check(game.photos.size() == 1, "postcard collected")
			await pose(Vector3(0, 0, -7), 0, 0)
			if OS.has_environment("DEBUG_WALK"):
				for z in range(-6, -24, -1):
					print("    pre z=", z, " g=", ground_at(0, z, 3.0))
			await place(0)
			if OS.has_environment("DEBUG_WALK"):
				for z in range(-6, -24, -1):
					print("    post z=", z, " g=", ground_at(0, z, 8.0))
			check(ground_at(0, -16) > 1.5, "ramp up to the ledge (y=%.2f)" % ground_at(0, -16))
			var b1 := await grab_nearest_battery()
			check(b1 != null, "grabbed battery 1")
			if b1:
				await deliver(b1, 0)
			var b2 := await grab_nearest_battery()
			check(b2 != null, "grabbed battery 2")
			if b2:
				await deliver(b2, 1)
			check(game.teleporter.powered, "teleporter powered by two batteries")
			await pose(Vector3(0, 0, -7), 0, 0)
		8:
			# Power Cut: copy through the gate, sideways, power the gate, copy again.
			await pose(Vector3(0, 0, -7.5), 0, -13)
			await snap()
			check(game.photos.size() == 1 and game.photos[0].items.size() == 1, "battery photographed through the gate")
			await pose(Vector3(0, 0, 0), 90, -13)
			await place(0)
			await frames(40)
			check(game.batteries.size() == 2, "copy made and original kept (%d)" % game.batteries.size())
			var copy: Battery = null
			for b in game.batteries:
				if (b as Battery).global_position.x < -1.0:
					copy = b
			check(copy != null, "copy landed beside the player")
			if copy:
				await deliver_to(copy, game.sockets[0].slot())
			check((game.gates[0] as Gate).open, "gate opened by the copy")
			await pose(Vector3(0, 0, -9.7), 0, -50)
			await snap()
			check(game.film == 0, "both shots used")
			await pose(Vector3(3, 0, -12), 0, -47)
			await place(0)
			await frames(40)
			var loose := loose_batteries()
			check(loose.size() == 2, "two batteries for the teleporter (%d)" % loose.size())
			for k in mini(loose.size(), 2):
				await deliver(loose[k], k)
			check(game.teleporter.powered, "teleporter powered")
			await pose(Vector3(0, 0, -12.5), 0, 0)
		9:
			# Two Keys: one photo, photocopied, gives three batteries.
			await pose(Vector3(-5, 0, 5.3), 0, -50)
			await snap()
			check(game.photos.size() == 1 and game.photos[0].items.size() == 1 and game.film == 0, "battery photographed with the only film")
			game.raise_photo(0)
			await pose(Vector3(5, 0, 5.6), 0, 0)
			check(game.act_label() == "COPY", "copier in reach")
			game.interact()
			await frames(4)
			check(game.photos.size() == 2 and game.photos[1].items.size() == 1, "photocopy carries the battery")
			await pose(Vector3(0, 0, 3.3), 0, -47)
			await place(0)
			await pose(Vector3(2.5, 0, 3.3), 0, -47)
			await place(0)
			await frames(40)
			check(game.batteries.size() == 3, "three batteries (%d)" % game.batteries.size())
			var loose := loose_batteries()
			if loose.size() >= 3:
				await deliver_to(loose[0], game.sockets[0].slot())
				await deliver_to(loose[1], game.sockets[1].slot())
				check((game.gates[0] as Gate).open, "both keys open the gate")
				await deliver(loose[2], 0)
			check(game.teleporter.powered, "teleporter powered")
			await pose(Vector3(0, 0, -12), 0, 0)
		10:
			# Watchtower: only the tall mast's photo lines up with the ground.
			await pose(Vector3(22.6, 0, 7.4), 180, 0)
			check(game.act_label() == "SNAP", "fixed camera button in reach")
			game.interact()
			await frames(10)
			check(game.photos.size() == 1 and game.photos[0].items.size() == 1, "mast camera photographed stairs + battery")
			await pose(Vector3(0, 0, 5), 0, 0)
			await place(0)
			await frames(40)
			var g := ground_at(0, -5.5, 9.0)
			check(g > 2.5 and g < 3.6, "stairs rise from the ground up the cliff (y=%.2f)" % g)
			var low: Array = game.batteries.filter(func(b): return (b as Battery).global_position.y < 1.5)
			check(low.size() == 1, "a copy of the battery came down to the ground")
			if low.size() == 1:
				await deliver(low[0], 0)
			await pose(Vector3(0, 0, 3), 0, 0)
		11:
			# Plan Ahead: copy first, then a level bridge and a tilted ramp.
			await pose(Vector3(-3, 0, 5.3), 0, 0)
			await frames(3)
			check(game.photos.size() == 1, "found the causeway photo")
			game.raise_photo(0)
			await pose(Vector3(3.5, 0, 6.3), 0, 0)
			game.interact()
			await frames(4)
			check(game.photos.size() == 2, "photo copied")
			await pose(Vector3(0, 0, 0), 0, 0)
			await place(0)
			check(absf(ground_at(0, -8, 3.0)) < 0.1, "causeway spans the first gap")
			await pose(Vector3(0, 0, -21), 0, 10.5)
			await place(0)
			var top := ground_at(0, -34.6, 12.0)
			check(top > 2.2 and top < 3.2, "tilted causeway ramps up to the cliff (y=%.2f)" % top)
			var t := 0
			game.player.set_look(0, 0)
			while t < 300 and game.player.global_position.z > -35.6:
				game.hud.stick_vec = Vector2(0, 1)
				if game.player.is_on_floor() and t % 20 == 0:
					game.player.jump_requested = true  # hop up onto the ramp's lip
				await get_tree().physics_frame
				t += 1
			game.hud.stick_vec = Vector2(1, 0)
			await frames(70)
			game.hud.stick_vec = Vector2.ZERO
			await frames(10)
			check(game.player.global_position.y > 2.4, "walked up the ramp onto the cliff (y=%.2f)" % game.player.global_position.y)
			await pose(Vector3(4, 2.7, -40.4), 0, 0)
			await frames(10)
	if not game.completed:
		await walk_to_finish(14.0)
	if not game.completed:
		print("    player ended at ", game.player.global_position)
	check(game.completed, "level %d completed" % (i + 1))


## The obvious-but-wrong moves must fail, otherwise the puzzles are trivial.
func _test_wrong_moves() -> void:
	print("Wrong moves")
	await load_level(8)  # Power Cut: placing the copy towards the gate deletes the original
	await pose(Vector3(0, 0, -7.5), 0, -13)
	await snap()
	await pose(Vector3(0, 0, 0), 0, -13)
	await place(0)
	await frames(30)
	check(game.batteries.size() == 1, "Power Cut: placing towards the vault erases the original battery")
	await load_level(9)  # Two Keys: without the copier there are only two batteries
	await pose(Vector3(-5, 0, 5.3), 0, -50)
	await snap()
	await pose(Vector3(0, 0, 3.3), 0, -47)
	await place(0)
	await frames(30)
	check(game.batteries.size() == 2 and game.film == 0, "Two Keys: one photo alone isn't enough")
	await load_level(10)  # Watchtower: the low camera's stairs float in the air
	await pose(Vector3(9.6, 0, -2.6), 180, 0)
	game.interact()
	await frames(10)
	await pose(Vector3(0, 0, 5), 0, 0)
	await place(0)
	await frames(10)
	var g := ground_at(0, -5.5, 9.0)
	check(not (g > 2.5 and g < 3.6), "Watchtower: the ground camera's photo doesn't give usable stairs")
	await load_level(11)  # Plan Ahead: a level causeway hits the cliff face
	await pose(Vector3(-3, 0, 5.3), 0, 0)
	await frames(3)
	await pose(Vector3(0, 0, 0), 0, 0)
	await place(0)
	check(game.photos.is_empty(), "Plan Ahead: the only photo is used up")
	check(ground_at(0, -34.6, 2.0) < 0.5, "Plan Ahead: a level causeway can't reach the cliff top")


func _test_hub() -> void:
	print("Hub")
	if game:
		game.queue_free()
		await get_tree().process_frame
	Progress.unlocked = 1
	game = Game.new()
	game.level_index = -1
	add_child(game)
	while not game.ready_to_play:
		await get_tree().process_frame
	await frames(5)
	check(game.hub_pads.size() == Levels.count(), "hub has a pad per level")
	check(not (game.hub_pads[1] as Teleporter).powered, "locked pads are off")
	var chosen := [-99]
	game.exit_requested.connect(func(n): chosen[0] = n)
	await pose(Levels.hub_pad(1), 0, 0)
	await frames(10)
	check(chosen[0] == -99, "locked pad does nothing")
	await pose(Levels.hub_pad(0), 0, 0)
	await frames(60)
	check(chosen[0] == 0, "first pad opens level 1")


func _test_rewind() -> void:
	print("Rewind")
	await load_level(1)
	var before := game.solid_world.solids
	await pose(Vector3(0, 0, 4), 180, 0)
	await snap()
	await pose(Vector3(0, 0, -4), 0, 0)
	await place(0)
	check(game.solid_world.solids != before, "world changed after placement")
	await frames(10)
	game.hud.rewind_held = true
	await frames(400)
	game.hud.rewind_held = false
	await frames(2)
	check(game.solid_world.solids == before, "rewind restored original world")
	check(game.photos.is_empty(), "rewind removed the photo")
	# Falling off the world triggers an automatic rewind.
	await pose(Vector3(0, 0, 2), 0, 0)
	await frames(30)
	game.player.global_position = Vector3(0, -20, 0)
	await frames(200)
	check(game.player.global_position.y > -1.0, "auto-rewind after falling (y=%.2f)" % game.player.global_position.y)
