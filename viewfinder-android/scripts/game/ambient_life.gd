class_name AmbientLife
extends Node3D
## Small touches that make the world feel alive: drifting pollen around the
## player, a flock of birds circling overhead and butterflies near the start.
## None of it is sliceable and none of it shows up in photographs.

const LAYER_NO_PHOTO := 4

var follow: Node3D
var _birds: Array = []
var _flies: Array = []
var _t := 0.0
var _pollen: CPUParticles3D


func setup(target: Node3D, center: Vector3, butterfly_at: Vector3) -> void:
	follow = target
	_pollen = CPUParticles3D.new()
	_pollen.amount = 70
	_pollen.lifetime = 9.0
	_pollen.preprocess = 9.0
	_pollen.local_coords = false
	_pollen.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_pollen.emission_box_extents = Vector3(9, 3, 9)
	_pollen.direction = Vector3(0.3, 0.2, 0.1)
	_pollen.spread = 180.0
	_pollen.gravity = Vector3(0, 0.02, 0)
	_pollen.initial_velocity_min = 0.05
	_pollen.initial_velocity_max = 0.25
	_pollen.scale_amount_min = 0.5
	_pollen.scale_amount_max = 1.2
	var q := QuadMesh.new()
	q.size = Vector2(0.05, 0.05)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.albedo_texture = _soft_dot()
	m.albedo_color = Color(1.0, 0.97, 0.85, 0.75)
	q.material = m
	_pollen.mesh = q
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 0))
	fade.add_point(0.2, Color(1, 1, 1, 1))
	fade.add_point(0.8, Color(1, 1, 1, 1))
	fade.set_color(fade.get_point_count() - 1, Color(1, 1, 1, 0))
	_pollen.color_ramp = fade
	_pollen.layers = LAYER_NO_PHOTO
	add_child(_pollen)

	var rng := RandomNumberGenerator.new()
	rng.seed = int(center.x * 13.0 + center.z * 7.0) + 5
	for i in 6:
		var b := _make_bird()
		add_child(b)
		_birds.append({"node": b, "r": rng.randf_range(16, 30), "h": rng.randf_range(16, 26) + center.y,
			"speed": rng.randf_range(0.18, 0.28), "phase": rng.randf() * TAU, "c": center,
			"flap": rng.randf_range(7.0, 9.0)})
	var cols := [Color(1.0, 0.75, 0.85), Color(1.0, 0.9, 0.5), Color(0.7, 0.85, 1.0), Color(1, 1, 1)]
	for i in 4:
		var f := _make_butterfly(cols[i % cols.size()])
		add_child(f)
		_flies.append({"node": f, "home": butterfly_at + Vector3(rng.randf_range(-4, 4), 0, rng.randf_range(-4, 4)),
			"phase": rng.randf() * 10.0})


func _soft_dot() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = 32
	t.height = 32
	return t


func _flat_mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.roughness = 1.0
	return m


func _make_bird() -> Node3D:
	var root := Node3D.new()
	var mat := _flat_mat(Color(0.32, 0.3, 0.38))
	var body := MeshInstance3D.new()
	var bm := CapsuleMesh.new()
	bm.radius = 0.09
	bm.height = 0.5
	body.mesh = bm
	body.rotation.x = PI * 0.5
	body.material_override = mat
	root.add_child(body)
	for sx in [-1.0, 1.0]:
		var pivot := Node3D.new()
		pivot.name = "L" if sx < 0 else "R"
		root.add_child(pivot)
		var wing := MeshInstance3D.new()
		var wm := PrismMesh.new()
		wm.size = Vector3(0.55, 0.02, 0.3)
		wing.mesh = wm
		wing.position = Vector3(0.3 * sx, 0, 0.02)
		wing.material_override = mat
		pivot.add_child(wing)
	_set_layers(root)
	return root


func _make_butterfly(c: Color) -> Node3D:
	var root := Node3D.new()
	var mat := _flat_mat(c)
	for sx in [-1.0, 1.0]:
		var pivot := Node3D.new()
		pivot.name = "L" if sx < 0 else "R"
		root.add_child(pivot)
		var wing := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(0.09, 0.12)
		wing.mesh = q
		wing.rotation.x = -PI * 0.5
		wing.position = Vector3(0.05 * sx, 0, 0)
		wing.material_override = mat
		pivot.add_child(wing)
	_set_layers(root)
	return root


func _set_layers(n: Node) -> void:
	if n is VisualInstance3D:
		(n as VisualInstance3D).layers = LAYER_NO_PHOTO
		if n is GeometryInstance3D:
			(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for c in n.get_children():
		_set_layers(c)


func _process(delta: float) -> void:
	_t += delta
	if follow and _pollen:
		_pollen.global_position = follow.global_position + Vector3(0, 1.5, 0)
	for b in _birds:
		var n: Node3D = b["node"]
		var a: float = b["phase"] + _t * float(b["speed"])
		var c: Vector3 = b["c"]
		var r: float = b["r"]
		var pos := c + Vector3(cos(a) * r, float(b["h"]) + sin(_t * 0.7 + a) * 1.5, sin(a) * r)
		var ahead := c + Vector3(cos(a + 0.05) * r, float(b["h"]), sin(a + 0.05) * r)
		n.global_position = pos
		n.look_at(ahead, Vector3.UP)
		var flap := sin(_t * float(b["flap"]) + float(b["phase"])) * 0.7
		(n.get_node("L") as Node3D).rotation.z = flap
		(n.get_node("R") as Node3D).rotation.z = -flap
	for f in _flies:
		var n: Node3D = f["node"]
		var ph: float = f["phase"] + _t
		var home: Vector3 = f["home"]
		n.global_position = home + Vector3(sin(ph * 0.7) * 1.6, 0.8 + sin(ph * 1.9) * 0.35 + sin(ph * 0.5) * 0.3, cos(ph * 0.53) * 1.6)
		n.rotation.y = ph * 0.7 + PI * 0.5
		var flap := sin(_t * 22.0 + float(f["phase"])) * 1.1
		(n.get_node("L") as Node3D).rotation.z = flap
		(n.get_node("R") as Node3D).rotation.z = -flap
