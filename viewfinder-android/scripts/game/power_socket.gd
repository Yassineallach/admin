class_name PowerSocket
extends Node3D
## A pedestal that takes one battery. Powered sockets open linked gates.

const BASE := 100  ## battery.socket values 100+id belong to power sockets

var id: int = 0
var powered := false
var _lamp: StandardMaterial3D
var _cable: StandardMaterial3D


func setup(socket_id: int, cable_to: Vector3 = Vector3.INF) -> void:
	id = socket_id
	var stone := StandardMaterial3D.new()
	stone.albedo_color = Color(0.3, 0.31, 0.4)
	var base := MeshInstance3D.new()
	var bm := CylinderMesh.new()
	bm.top_radius = 0.26
	bm.bottom_radius = 0.34
	bm.height = 0.5
	base.mesh = bm
	base.position.y = 0.25
	base.material_override = stone
	add_child(base)
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.3
	cyl.height = 0.5
	cs.shape = cyl
	cs.position.y = 0.25
	body.add_child(cs)
	add_child(body)
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.17
	tm.outer_radius = 0.24
	ring.mesh = tm
	ring.position.y = 0.5
	_lamp = StandardMaterial3D.new()
	_lamp.albedo_color = Color(0.4, 0.42, 0.5)
	_lamp.emission_enabled = true
	_lamp.emission = Color(1.0, 0.7, 0.3)
	_lamp.emission_energy_multiplier = 0.0
	ring.material_override = _lamp
	add_child(ring)
	if cable_to != Vector3.INF:
		# A cable on the ground showing which gate this socket feeds.
		var a := Vector3(0, 0.03, 0)
		var b := cable_to - position
		b.y = 0.03
		var cable := MeshInstance3D.new()
		var cm := BoxMesh.new()
		cm.size = Vector3(0.06, 0.04, a.distance_to(b))
		cable.mesh = cm
		cable.position = (a + b) * 0.5
		cable.basis = Basis.looking_at(b - a, Vector3.UP)
		_cable = StandardMaterial3D.new()
		_cable.albedo_color = Color(0.25, 0.25, 0.3)
		_cable.emission_enabled = true
		_cable.emission = Color(1.0, 0.7, 0.3)
		_cable.emission_energy_multiplier = 0.0
		cable.material_override = _cable
		add_child(cable)


func slot() -> Vector3:
	return global_position + Vector3(0, 0.78, 0)


func update(batteries: Array) -> void:
	var has := false
	for b in batteries:
		if (b as Battery).socket == BASE + id:
			has = true
	if not has:
		for b in batteries:
			var bat: Battery = b
			if bat.held or bat.socket >= 0:
				continue
			if bat.global_position.distance_to(slot()) < 0.8:
				Sfx.play("click")
				bat.set_socket(BASE + id)
				bat.global_transform = Transform3D(Basis(), slot())
				has = true
				break
	powered = has
	_lamp.emission_energy_multiplier = 2.5 if has else 0.0
	if _cable:
		_cable.emission_energy_multiplier = 1.5 if has else 0.0
