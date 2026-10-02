class_name PhotoPickup
extends Node3D
## A polaroid lying around the level. Walking into it adds its photo to the
## player's collection.

var photo: Photo
var key: String = ""
var _t := 0.0
var _front: MeshInstance3D


func setup(p: Photo) -> void:
	photo = p
	var frame := MeshInstance3D.new()
	var fm := BoxMesh.new()
	fm.size = Vector3(0.5, 0.6, 0.02)
	frame.mesh = fm
	var white := StandardMaterial3D.new()
	white.albedo_color = Color(0.98, 0.97, 0.94)
	frame.material_override = white
	add_child(frame)
	_front = MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(0.42, 0.42)
	_front.mesh = qm
	_front.position = Vector3(0, 0.05, 0.011)
	add_child(_front)
	var back := _front.duplicate()
	back.rotation.y = PI
	back.position.z = -0.011
	add_child(back)
	refresh_texture()


func refresh_texture() -> void:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	if photo and photo.texture:
		mat.albedo_texture = photo.texture
	else:
		mat.albedo_color = Color(0.6, 0.75, 0.8)
	for c in get_children():
		if c is MeshInstance3D and c.mesh is QuadMesh:
			c.material_override = mat


func _process(delta: float) -> void:
	_t += delta
	rotation.y = _t * 1.2
	position.y += sin(_t * 2.0) * 0.002
