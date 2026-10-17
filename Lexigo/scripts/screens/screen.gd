class_name Screen
extends Control
## Base for full-page screens managed by Main.

var main: Node

func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

## Android back button / Escape. Return true when handled.
func go_back() -> bool:
	main.goto_home()
	return true

func accent() -> Color:
	return UI.ACCENT

## Root column respecting the device safe area (notches, rounded corners).
func make_root(side := 24, gap := 16) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", gap)
	var m := UI.margin(v, side, int(main.safe_top()) + 16, side, int(main.safe_bottom()) + 16)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(m)
	return v
