extends Node
## Soak test: runs the real Main scene flow (menu -> hub -> levels) for a while,
## exercising photos, rewind and level switches. Watch the log for errors.
## Run: godot --path . res://tests/soak.tscn  (with a display or Xvfb)

var main: Node


func _ready() -> void:
	Progress.unlocked = 13
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await secs(4.0)
	print("SOAK menu ok")
	for lv in [-2, 0, 1, 4, 8, 10, 11, -2]:
		main.start_level(Game.HUB if lv == -2 else lv)
		var g: Game = await wait_game()
		print("SOAK level ", lv, " loaded")
		await secs(3.0)
		if not g.is_hub:
			g.hud.stick_vec = Vector2(0.3, 1)
			await secs(1.5)
			g.hud.stick_vec = Vector2.ZERO
			if g.has_camera:
				g.camera_mode = true
				await g.take_photo()
				await secs(1.0)
			if not g.photos.is_empty():
				g.raise_photo(0)
				await secs(0.6)
				g.place_photo()
				await secs(1.0)
			g.hud.rewind_held = true
			await secs(1.5)
			g.hud.rewind_held = false
		await secs(2.0)
	print("SOAK DONE frames=", Engine.get_frames_drawn())
	get_tree().quit()


func secs(t: float) -> void:
	await get_tree().create_timer(t).timeout


func wait_game() -> Game:
	while true:
		await get_tree().process_frame
		for c in main.get_children():
			if c is Game and not c.is_queued_for_deletion() and (c as Game).ready_to_play:
				return c
	return null
