class_name Note
extends Node3D
## A floating archivist's note. Walk up and press READ.

var title := ""
var text := ""
var _t := 0.0
var _paper: MeshInstance3D
var _base_y := 0.0


func setup(t: String, body: String) -> void:
	title = t
	text = body
	_paper = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.32, 0.42, 0.01)
	_paper.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(1.0, 0.97, 0.88)
	m.emission_enabled = true
	m.emission = Color(1.0, 0.9, 0.7)
	m.emission_energy_multiplier = 0.25
	_paper.material_override = m
	add_child(_paper)
	for i in 4:
		var line := MeshInstance3D.new()
		var lm := BoxMesh.new()
		lm.size = Vector3(0.22 - (0.06 if i == 3 else 0.0), 0.015, 0.012)
		line.mesh = lm
		var lmat := StandardMaterial3D.new()
		lmat.albedo_color = Color(0.45, 0.42, 0.5)
		line.material_override = lmat
		line.position = Vector3(-0.03 if i == 3 else 0.0, 0.11 - i * 0.06, 0.0)
		_paper.add_child(line)
	_base_y = position.y


func _process(delta: float) -> void:
	_t += delta
	position.y = _base_y + sin(_t * 1.8) * 0.06
	_paper.rotation = Vector3(sin(_t * 1.1) * 0.15, _t * 0.6, sin(_t * 0.8) * 0.1)
