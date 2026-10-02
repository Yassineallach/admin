class_name PhotoPickup
extends Node3D
## A picture lying around the level: a polaroid, a pencil sketch or a framed
## painting. Walking into it adds it to the player's collection.

var photo: Photo
var key: String = ""
var _t := 0.0
var _front: MeshInstance3D
var _base_y := 0.0
var _spin := true


func setup(p: Photo) -> void:
	photo = p
	_base_y = position.y
	var frame := MeshInstance3D.new()
	var fm := BoxMesh.new()
	var img_size := 0.42
	var img_off := Vector3(0, 0.05, 0.011)
	var frame_col := Color(0.98, 0.97, 0.94)
	match p.kind:
		"sketch":
			fm.size = Vector3(0.5, 0.5, 0.01)
			img_size = 0.46
			img_off = Vector3(0, 0, 0.006)
			frame_col = Color(0.96, 0.94, 0.88)
			_spin = false
		"painting":
			fm.size = Vector3(0.62, 0.62, 0.05)
			img_size = 0.5
			img_off = Vector3(0, 0, 0.026)
			frame_col = Color(0.55, 0.38, 0.26)
			_spin = false
		_:
			fm.size = Vector3(0.5, 0.6, 0.02)
	frame.mesh = fm
	var fmat := StandardMaterial3D.new()
	fmat.albedo_color = frame_col
	frame.material_override = fmat
	add_child(frame)
	_front = MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(img_size, img_size)
	_front.mesh = qm
	_front.position = img_off
	add_child(_front)
	if _spin:
		var back := _front.duplicate()
		back.rotation.y = PI
		back.position.z = -img_off.z
		add_child(back)
	else:
		# Leaning back on an easel, facing -Z (towards the player's start).
		rotation = Vector3(-0.22, PI, 0)
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
	if _spin:
		rotation.y = _t * 1.2
		position.y = _base_y + sin(_t * 2.0) * 0.05
