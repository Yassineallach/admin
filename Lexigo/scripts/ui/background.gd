extends ColorRect
## Flat white canvas. The design language relies on colour blocks and
## characters for depth, not gradients, so the backdrop stays quiet.

func _ready() -> void:
	color = UI.WHITE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func set_palette(_accent: Color) -> void:
	pass
