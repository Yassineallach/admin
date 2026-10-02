class_name MenuBackdrop
extends Node3D
## Live 3D scene behind the main menu: the Station island seen from a slowly
## orbiting camera, with Miso, birds and drifting pollen.

var _cam: Camera3D
var _t := 0.0
var _focus := Vector3(0, 1.5, 0)


func _ready() -> void:
	Game.make_environment(self)
	var lv := Levels.hub()
	var world := SolidWorld.new()
	add_child(world)
	world.set_solids(lv["solids"])
	var back := MeshInstance3D.new()
	back.mesh = SolidWorld.build_mesh(lv["backdrop"], world.material)
	back.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(back)
	for i in Levels.count():
		var pad := Teleporter.new()
		add_child(pad)
		pad.position = Levels.hub_pad(i)
		pad.setup(0, "", i + 1 > Progress.unlocked)
	var cat := Cat.new()
	add_child(cat)
	cat.position = lv["cat"]["pos"]
	cat.rotation.y = deg_to_rad(lv["cat"]["yaw"])
	_cam = Camera3D.new()
	_cam.fov = 60.0
	_cam.far = 600.0
	add_child(_cam)
	cat.watch(Vector3(0, 6, 22))
	var life := AmbientLife.new()
	add_child(life)
	life.setup(_cam, Vector3.ZERO, Vector3(0, 0, 4))
	_update_cam()


func _process(delta: float) -> void:
	_t += delta
	_update_cam()


func _update_cam() -> void:
	var a := 0.6 + _t * 0.04
	var pos := Vector3(sin(a) * 26.0, 9.0 + sin(_t * 0.1) * 1.5, cos(a) * 26.0)
	_cam.global_position = pos
	# Offset the look target so the island sits on the right of the screen,
	# leaving the left side for the title and buttons.
	var right := Vector3(cos(a), 0, -sin(a))
	_cam.look_at(_focus - right * 7.0, Vector3.UP)
