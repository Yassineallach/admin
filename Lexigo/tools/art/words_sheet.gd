extends SceneTree
## Contact sheet of every word illustration, one world per row.
##   godot --headless --path . -s res://tools/art/words_sheet.gd -- out.png

func _init() -> void:
	var out: String = OS.get_cmdline_user_args()[0] if not OS.get_cmdline_user_args().is_empty() else "user://words.png"
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/vocab.json"))
	var cell := 110
	var worlds: Array = data["worlds"]
	var sheet := Image.create(20 * cell, worlds.size() * cell, false, Image.FORMAT_RGBA8)
	sheet.fill(Color.WHITE)
	for r in worlds.size():
		var words: Array = worlds[r]["words"]
		for c in words.size():
			var text := FileAccess.get_file_as_string("res://assets/art/words/%s/%s.svg" % [worlds[r]["id"], words[c][1]])
			var img := Image.new()
			img.load_svg_from_string(text, 100.0 / 160.0)
			img.convert(Image.FORMAT_RGBA8)
			sheet.blend_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), Vector2i(c * cell + 5, r * cell + 5))
	sheet.save_png(out)
	quit()
