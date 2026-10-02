class_name Gate
extends Node3D
## A shimmering energy barrier. Opens while all of its sockets are powered.
## Gates are part of the Archive: photos can't remove them.

var needs: Array = []  # socket ids
var open := false
var _body: StaticBody3D
var _mat: ShaderMaterial
var _field: MeshInstance3D
var _t := 0.0


func setup(size: Vector3, socket_ids: Array) -> void:
	needs = socket_ids
	_body = StaticBody3D.new()
	_body.collision_layer = 1
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	cs.position.y = size.y * 0.5
	_body.add_child(cs)
	add_child(_body)
	_field = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(size.x, size.y, 0.05)
	_field.mesh = bm
	_field.position.y = size.y * 0.5
	_mat = ShaderMaterial.new()
	_mat.shader = load("res://shaders/gate.gdshader")
	_field.material_override = _mat
	_field.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_field)


func update(sockets: Dictionary) -> void:
	var all := true
	for id in needs:
		var s: PowerSocket = sockets.get(id)
		if s == null or not s.powered:
			all = false
	if all != open:
		open = all
		_body.collision_layer = 0 if open else 1
		Sfx.play("chime" if open else "denied", -6.0)


func _process(delta: float) -> void:
	_t += delta
	var target := 0.0 if open else 1.0
	var a := move_toward(_field.scale.y, target, delta * 3.0)
	_field.scale = Vector3(1, maxf(a, 0.001), 1)
	_field.visible = a > 0.01
	_mat.set_shader_parameter("strength", 0.85 + 0.15 * sin(_t * 4.0))
