extends SceneTree
## Rasterises every SVG in assets/art with Godot's own SVG renderer (ThorVG)
## into one PNG, to review the art exactly as the game will draw it.
##   godot --headless --path . -s res://tools/art/contact_sheet.gd -- out.png

func _init() -> void:
	var out: String = OS.get_cmdline_user_args()[0] if not OS.get_cmdline_user_args().is_empty() else "user://art.png"
	var files := []
	for sub in ["mascot", "worlds", "icons", ""]:
		var dir := "res://assets/art".path_join(sub)
		for f in DirAccess.get_files_at(dir):
			if f.ends_with(".svg"):
				files.append(dir.path_join(f))
	var cell := 200
	var cols := 6
	var rows := ceili(files.size() / float(cols))
	var sheet := Image.create(cols * cell, rows * cell, false, Image.FORMAT_RGBA8)
	sheet.fill(Color.WHITE)
	for i in files.size():
		var text := FileAccess.get_file_as_string(files[i])
		var img := Image.new()
		img.load_svg_from_string(text, 1.0)
		var s := float(cell - 16) / maxf(img.get_width(), img.get_height())
		img.resize(int(img.get_width() * s), int(img.get_height() * s), Image.INTERPOLATE_LANCZOS)
		img.convert(Image.FORMAT_RGBA8)
		var x := (i % cols) * cell + (cell - img.get_width()) / 2
		var y := (i / cols) * cell + (cell - img.get_height()) / 2
		sheet.blend_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), Vector2i(x, y))
	sheet.save_png(out)
	print("sheet: ", files.size(), " images")
	quit()
