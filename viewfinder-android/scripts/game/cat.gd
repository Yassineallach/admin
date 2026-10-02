class_name Cat
extends Node3D
## Miso, the Archive's resident cat: lies in a loaf, follows you with her eyes,
## swishes her tail, and purrs (with hearts) when petted.

signal petted

var _head: Node3D
var _tail: Node3D
var _eyes: Array[MeshInstance3D] = []
var _body: MeshInstance3D
var _t := 0.0
var _blink := 2.0
var _pet_time := 0.0
var _look_target := Vector3.ZERO
var _has_target := false

const FUR := Color(0.97, 0.70, 0.45)
const CREAM := Color(1.0, 0.94, 0.85)
const DARK := Color(0.18, 0.15, 0.17)
const PINK := Color(0.98, 0.62, 0.66)


func _ready() -> void:
	var fur := _mat(FUR)
	var cream := _mat(CREAM)
	var dark := _mat(DARK)
	var pink := _mat(PINK)

	_body = _mesh(_capsule(0.17, 0.62), fur, Vector3(0, 0.17, 0.02), Vector3(PI * 0.5, 0, 0))
	_body.scale = Vector3(1.0, 1.0, 0.85)
	_mesh(_sphere(0.15), cream, Vector3(0, 0.15, -0.18)).scale = Vector3(0.9, 0.85, 0.7)
	for sx in [-0.1, 0.1]:
		_mesh(_sphere(0.07), cream, Vector3(sx, 0.05, -0.27)).scale = Vector3(1, 0.6, 1.4)  # paws
	# Ginger saddle patch on the back.
	_mesh(_sphere(0.15), _mat(FUR.darkened(0.12)), Vector3(0, 0.25, 0.1)).scale = Vector3(1.05, 0.55, 1.5)

	_head = Node3D.new()
	_head.position = Vector3(0, 0.36, -0.24)
	add_child(_head)
	_mesh(_sphere(0.16), fur, Vector3.ZERO, Vector3.ZERO, _head).scale = Vector3(1.08, 0.94, 0.98)
	_mesh(_sphere(0.08), cream, Vector3(0, -0.05, -0.11), Vector3.ZERO, _head).scale = Vector3(1.2, 0.8, 0.8)
	_mesh(_sphere(0.022), pink, Vector3(0, -0.02, -0.165), Vector3.ZERO, _head)
	for sx in [-1.0, 1.0]:
		var ear := _mesh(_cone(0.07, 0.13), fur, Vector3(0.085 * sx, 0.13, 0.0), Vector3(0, 0, -0.35 * sx), _head)
		_mesh(_cone(0.04, 0.08), pink, Vector3(0, -0.01, -0.025), Vector3.ZERO, ear)
		var eye := _mesh(_sphere(0.028), dark, Vector3(0.062 * sx, 0.025, -0.135), Vector3.ZERO, _head)
		eye.scale = Vector3(1, 1.25, 0.6)
		_eyes.append(eye)

	_tail = Node3D.new()
	_tail.position = Vector3(0, 0.14, 0.32)
	add_child(_tail)
	var seg_parent: Node3D = _tail
	for i in 4:
		var seg := Node3D.new()
		seg.position = Vector3(0, 0.0, 0.0) if i == 0 else Vector3(0, 0, 0.12)
		seg.rotation.x = -0.35
		seg_parent.add_child(seg)
		_mesh(_capsule(0.04, 0.16), _mat(FUR if i < 3 else FUR.darkened(0.2)), Vector3(0, 0, 0.06), Vector3(PI * 0.5, 0, 0), seg)
		seg_parent = seg


func _mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 1.0
	m.rim_enabled = true
	m.rim = 0.3
	return m


func _mesh(mesh: Mesh, mat: Material, pos: Vector3, rot: Vector3 = Vector3.ZERO, parent: Node3D = null) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	(parent if parent else self).add_child(mi)
	return mi


func _sphere(r: float) -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = r
	m.height = r * 2.0
	m.radial_segments = 16
	m.rings = 8
	return m


func _capsule(r: float, h: float) -> CapsuleMesh:
	var m := CapsuleMesh.new()
	m.radius = r
	m.height = h
	m.radial_segments = 12
	m.rings = 4
	return m


func _cone(r: float, h: float) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = 0.0
	m.bottom_radius = r
	m.height = h
	m.radial_segments = 8
	return m


func watch(target: Vector3) -> void:
	_look_target = target
	_has_target = true


func pet() -> void:
	_pet_time = 2.5
	petted.emit()
	Sfx.loop("purr", true, -6.0)
	Sfx.play("meow", -6.0, randf_range(0.95, 1.1))
	for i in 3:
		var h := Label3D.new()
		h.text = "♥"
		h.font_size = 96
		h.pixel_size = 0.003
		h.modulate = Color(1.0, 0.45, 0.55)
		h.outline_size = 0
		h.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		h.no_depth_test = true
		h.position = Vector3(randf_range(-0.15, 0.15), 0.55, -0.1)
		add_child(h)
		var tw := create_tween().set_parallel()
		tw.tween_property(h, "position", h.position + Vector3(randf_range(-0.2, 0.2), 0.5, 0), 1.3).set_delay(i * 0.25)
		tw.tween_property(h, "modulate:a", 0.0, 1.3).set_delay(i * 0.25)
		tw.chain().tween_callback(h.queue_free)


func _process(delta: float) -> void:
	_t += delta
	_body.scale.y = 1.0 + sin(_t * 2.2) * 0.025
	# Tail swish (faster and happier while being petted).
	var happy := _pet_time > 0.0
	_tail.rotation.y = sin(_t * (3.2 if happy else 1.3)) * (0.6 if happy else 0.35)
	_tail.rotation.x = -0.2 + sin(_t * 0.7) * 0.1
	# Head follows the player.
	if _has_target:
		var local := to_local(_look_target)
		var yaw := clampf(atan2(-local.x, -local.z), -1.0, 1.0)
		var pitch := clampf(atan2(local.y - 0.36, Vector2(local.x, local.z).length()) * 0.5, -0.3, 0.4)
		_head.rotation.y = lerpf(_head.rotation.y, yaw, delta * 3.0)
		_head.rotation.x = lerpf(_head.rotation.x, pitch, delta * 3.0)
	_head.rotation.z = sin(_t * 0.9) * 0.06 + (sin(_t * 6.0) * 0.08 if happy else 0.0)
	# Blink, or keep eyes shut while purring.
	_blink -= delta
	var shut := happy or _blink < 0.12
	if _blink < 0.0:
		_blink = randf_range(2.0, 5.0)
	for e in _eyes:
		e.scale.y = 0.15 if shut else 1.25
	if _pet_time > 0.0:
		_pet_time -= delta
		if _pet_time <= 0.0:
			Sfx.loop("purr", false)
