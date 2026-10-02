class_name Battery
extends RigidBody3D
## Carryable power cell. Can be duplicated by photographing it.

var id: int = 0
var held: bool = false
## Index of the teleporter socket it is plugged into, -1 when loose.
var socket: int = -1

var _glow: StandardMaterial3D


func _init() -> void:
	mass = 2.0
	collision_layer = 2
	collision_mask = 1 | 2
	continuous_cd = true
	can_sleep = true
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.16
	cyl.height = 0.5
	shape.shape = cyl
	add_child(shape)

	var body := MeshInstance3D.new()
	var bm := CylinderMesh.new()
	bm.top_radius = 0.16
	bm.bottom_radius = 0.16
	bm.height = 0.42
	body.mesh = bm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.22, 0.24, 0.3)
	mat.roughness = 0.5
	body.material_override = mat
	add_child(body)

	var band := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.165
	cm.bottom_radius = 0.165
	cm.height = 0.16
	band.mesh = cm
	_glow = StandardMaterial3D.new()
	_glow.albedo_color = Color(1.0, 0.75, 0.3)
	_glow.emission_enabled = true
	_glow.emission = Color(1.0, 0.7, 0.25)
	_glow.emission_energy_multiplier = 1.6
	band.material_override = _glow
	add_child(band)

	var cap := MeshInstance3D.new()
	var capm := CylinderMesh.new()
	capm.top_radius = 0.06
	capm.bottom_radius = 0.06
	capm.height = 0.08
	cap.mesh = capm
	cap.position = Vector3(0, 0.25, 0)
	cap.material_override = mat
	add_child(cap)


func set_held(v: bool) -> void:
	held = v
	freeze = v or socket >= 0
	collision_layer = 0 if v else 2
	collision_mask = 0 if v else (1 | 2)
	if not v:
		sleeping = false


func set_socket(i: int) -> void:
	socket = i
	freeze = held or i >= 0
	_glow.emission_energy_multiplier = 3.0 if i >= 0 else 1.6


func to_state() -> Dictionary:
	return {"id": id, "xf": global_transform, "held": held, "socket": socket}
