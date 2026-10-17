extends SceneTree
## Renders store / launcher PNGs from the SVG art with Godot's SVG renderer.
##   godot --headless --path . -s res://tools/art/export_png.gd

const JOBS := [
	["app_icon.svg", "store/icon_512.png", 512],
	["app_icon.svg", "store/icon_192.png", 192],
	["adaptive_foreground.svg", "store/adaptive_foreground_432.png", 432],
	["adaptive_background.svg", "store/adaptive_background_432.png", 432],
	["feature_graphic.svg", "store/feature_graphic_1024x500.png", 1024],
]

func _init() -> void:
	DirAccess.make_dir_recursive_absolute("res://assets/store")
	for j in JOBS:
		var text := FileAccess.get_file_as_string("res://assets/art/" + j[0])
		var probe := Image.new()
		probe.load_svg_from_string(text, 1.0)
		var img := Image.new()
		img.load_svg_from_string(text, float(j[2]) / probe.get_width())
		img.save_png("res://assets/" + j[1])
		print(j[1], " ", img.get_size())
	quit()
