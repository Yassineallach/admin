class_name FixedCamera
extends Node3D
## A camera bolted to the top of a tall mast. Press the button at its foot
## and it takes a photo from up there — from a height you can't reach.

var eye: Transform3D
var _button_mat: StandardMaterial3D
var _t := 0.0
var _flash: OmniLight3D


func setup(eye_xf: Transform3D) -> void:
	eye = eye_xf
	var metal := StandardMaterial3D.new()
	metal.albedo_color = Color(0.36, 0.37, 0.45)
	var h := eye.origin.y - global_position.y
	var mast := MeshInstance3D.new()
	var mm := CylinderMesh.new()
	mm.top_radius = 0.08
	mm.bottom_radius = 0.12
	mm.height = h - 0.2
	mast.mesh = mm
	mast.position.y = (h - 0.2) * 0.5
	mast.material_override = metal
	add_child(mast)
	# Camera body + lens, aimed like the photo it takes.
	var head := Node3D.new()
	add_child(head)
	head.global_transform = eye
	var body := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.5, 0.36, 0.34)
	body.mesh = bm
	var cmat := StandardMaterial3D.new()
	cmat.albedo_color = Color(0.95, 0.9, 0.82)
	body.material_override = cmat
	head.add_child(body)
	var lens := MeshInstance3D.new()
	var lm := CylinderMesh.new()
	lm.top_radius = 0.11
	lm.bottom_radius = 0.13
	lm.height = 0.16
	lens.mesh = lm
	lens.rotation.x = PI * 0.5
	lens.position.z = -0.24
	lens.material_override = metal
	head.add_child(lens)
	var stripe := MeshInstance3D.new()
	var sm := BoxMesh.new()
	sm.size = Vector3(0.52, 0.06, 0.36)
	stripe.mesh = sm
	var smat := StandardMaterial3D.new()
	smat.albedo_color = Color(0.95, 0.55, 0.45)
	stripe.material_override = smat
	head.add_child(stripe)
	_flash = OmniLight3D.new()
	_flash.light_energy = 0.0
	_flash.omni_range = 6.0
	_flash.position.z = -0.4
	head.add_child(_flash)
	# The button at the bottom.
	var post := MeshInstance3D.new()
	var pm := BoxMesh.new()
	pm.size = Vector3(0.4, 0.9, 0.4)
	post.mesh = pm
	post.position = Vector3(0.6, 0.45, 0)
	post.material_override = metal
	add_child(post)
	var btn := MeshInstance3D.new()
	var bt := CylinderMesh.new()
	bt.top_radius = 0.12
	bt.bottom_radius = 0.12
	bt.height = 0.08
	btn.mesh = bt
	btn.position = Vector3(0.6, 0.94, 0)
	_button_mat = StandardMaterial3D.new()
	_button_mat.albedo_color = Color(1.0, 0.4, 0.35)
	_button_mat.emission_enabled = true
	_button_mat.emission = Color(1.0, 0.35, 0.3)
	btn.material_override = _button_mat
	add_child(btn)
	var body2 := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(0.4, 0.9, 0.4)
	cs.shape = bs
	cs.position = Vector3(0.6, 0.45, 0)
	body2.add_child(cs)
	add_child(body2)


func button_pos() -> Vector3:
	return global_position + Vector3(0.6, 0.95, 0)


func fire() -> void:
	_flash.light_energy = 6.0
	create_tween().tween_property(_flash, "light_energy", 0.0, 0.4)


func _process(delta: float) -> void:
	_t += delta
	_button_mat.emission_energy_multiplier = 0.8 + 0.6 * sin(_t * 4.0)
