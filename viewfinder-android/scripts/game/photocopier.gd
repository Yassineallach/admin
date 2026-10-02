class_name Photocopier
extends Node3D
## Hold a picture up near it and press COPY to get a duplicate.

var _light: StandardMaterial3D
var _t := 0.0
var _scan := 0.0


func setup() -> void:
	var shell := StandardMaterial3D.new()
	shell.albedo_color = Color(0.9, 0.88, 0.84)
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.32, 0.33, 0.4)
	_add_box(Vector3(1.2, 0.9, 0.8), Vector3(0, 0.45, 0), shell)
	_add_box(Vector3(1.1, 0.08, 0.7), Vector3(0, 0.94, 0), dark)
	_add_box(Vector3(1.24, 0.1, 0.84), Vector3(0, 1.03, 0.0), shell)
	_add_box(Vector3(0.5, 0.06, 0.4), Vector3(0.2, 0.55, 0.42), dark)  # output tray
	var glass := MeshInstance3D.new()
	var gm := BoxMesh.new()
	gm.size = Vector3(1.0, 0.02, 0.6)
	glass.mesh = gm
	glass.position.y = 0.985
	_light = StandardMaterial3D.new()
	_light.albedo_color = Color(0.5, 0.9, 0.7)
	_light.emission_enabled = true
	_light.emission = Color(0.5, 1.0, 0.7)
	_light.emission_energy_multiplier = 0.3
	glass.material_override = _light
	add_child(glass)
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(1.2, 1.1, 0.8)
	cs.shape = bs
	cs.position.y = 0.55
	body.add_child(cs)
	add_child(body)
	var label := Label3D.new()
	label.text = "COPY"
	label.font_size = 48
	label.pixel_size = 0.004
	label.position = Vector3(0, 0.6, 0.41)
	label.modulate = Color(0.32, 0.33, 0.4)
	add_child(label)


func _add_box(size: Vector3, pos: Vector3, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.position = pos
	mi.material_override = mat
	add_child(mi)


func scan() -> void:
	_scan = 1.0


func _process(delta: float) -> void:
	_t += delta
	_scan = maxf(0.0, _scan - delta * 1.2)
	_light.emission_energy_multiplier = 0.3 + 0.15 * sin(_t * 2.0) + _scan * 4.0
