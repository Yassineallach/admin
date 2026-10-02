class_name Teleporter
extends Node3D
## Level exit. Needs `needs` batteries plugged into its sockets before the pad
## activates. Its own small pad collider keeps it usable even if the floor
## under it gets carved away by a photo.

signal entered

var needs: int = 1
var powered: bool = false
var locked: bool = false
var sockets: Array[Vector3] = []  # local positions

var _ring_mat: StandardMaterial3D
var _beam: MeshInstance3D
var _socket_mats: Array[StandardMaterial3D] = []
var _t := 0.0


func setup(need_count: int, label: String = "", is_locked: bool = false, done: bool = false) -> void:
	needs = need_count
	locked = is_locked
	if label != "":
		var l := Label3D.new()
		var parts := label.split(" · ")
		l.text = (parts[0] + ("  ✓" if done else "")) + ("\n" + parts[1] if parts.size() > 1 else "")
		l.font_size = 64
		l.pixel_size = 0.0055
		l.line_spacing = -8
		l.outline_size = 12
		l.outline_modulate = Color(0.25, 0.2, 0.3, 0.8)
		l.modulate = Color(0.6, 0.58, 0.62) if is_locked else Color(1, 0.97, 0.9)
		l.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
		l.position = Vector3(0, 3.0, 0)
		add_child(l)
	var body := StaticBody3D.new()
	body.collision_layer = 1
	var cs := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 1.1
	cyl.height = 0.2
	cs.shape = cyl
	cs.position = Vector3(0, 0.1, 0)
	body.add_child(cs)
	add_child(body)

	var base := MeshInstance3D.new()
	var bm := CylinderMesh.new()
	bm.top_radius = 1.1
	bm.bottom_radius = 1.2
	bm.height = 0.2
	base.mesh = bm
	base.position = Vector3(0, 0.1, 0)
	var base_mat := StandardMaterial3D.new()
	base_mat.albedo_color = Color(0.93, 0.92, 0.95)
	base.material_override = base_mat
	add_child(base)

	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.85
	tm.outer_radius = 1.0
	ring.mesh = tm
	ring.position = Vector3(0, 0.22, 0)
	_ring_mat = StandardMaterial3D.new()
	_ring_mat.albedo_color = Color(0.5, 0.5, 0.55)
	_ring_mat.emission_enabled = true
	_ring_mat.emission = Color(0.4, 0.9, 1.0)
	_ring_mat.emission_energy_multiplier = 0.0
	ring.material_override = _ring_mat
	add_child(ring)

	_beam = MeshInstance3D.new()
	var beam_mesh := CylinderMesh.new()
	beam_mesh.top_radius = 0.75
	beam_mesh.bottom_radius = 0.9
	beam_mesh.height = 3.0
	beam_mesh.cap_top = false
	beam_mesh.cap_bottom = false
	_beam.mesh = beam_mesh
	_beam.position = Vector3(0, 1.7, 0)
	var beam_mat := StandardMaterial3D.new()
	beam_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	beam_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	beam_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	beam_mat.albedo_color = Color(0.55, 0.95, 1.0, 0.18)
	_beam.material_override = beam_mat
	_beam.visible = false
	add_child(_beam)

	for i in needs:
		var ang := PI * 0.5 + (i - (needs - 1) * 0.5) * 0.9
		var p := Vector3(cos(ang) * 1.55, 0.0, sin(ang) * 1.55)
		sockets.append(p + Vector3(0, 0.55, 0))
		var post := MeshInstance3D.new()
		var pm := CylinderMesh.new()
		pm.top_radius = 0.2
		pm.bottom_radius = 0.25
		pm.height = 0.3
		post.mesh = pm
		post.position = p + Vector3(0, 0.15, 0)
		var sm := StandardMaterial3D.new()
		sm.albedo_color = Color(0.35, 0.36, 0.42)
		sm.emission_enabled = true
		sm.emission = Color(1.0, 0.6, 0.3)
		sm.emission_energy_multiplier = 0.0
		post.material_override = sm
		_socket_mats.append(sm)
		add_child(post)
		var pbody := StaticBody3D.new()
		var pcs := CollisionShape3D.new()
		var pcyl := CylinderShape3D.new()
		pcyl.radius = 0.25
		pcyl.height = 0.3
		pcs.shape = pcyl
		pcs.position = post.position
		pbody.add_child(pcs)
		add_child(pbody)
	_update_power([])


func socket_world(i: int) -> Vector3:
	return global_transform * sockets[i]


## Called every physics frame by the game with all batteries.
func update_sockets(batteries: Array, player_pos: Vector3) -> void:
	var filled: Array = []
	filled.resize(needs)
	filled.fill(false)
	for b in batteries:
		var bat: Battery = b
		if bat.socket >= 0 and bat.socket < needs:
			filled[bat.socket] = true
	for b in batteries:
		var bat: Battery = b
		if bat.held or bat.socket >= 0:
			continue
		for i in needs:
			if filled[i]:
				continue
			if bat.global_position.distance_to(socket_world(i)) < 0.9:
				Sfx.play("click")
				bat.set_socket(i)
				bat.global_transform = Transform3D(Basis(), socket_world(i))
				filled[i] = true
				break
	_update_power(filled)
	if powered:
		var local := global_transform.affine_inverse() * player_pos
		if Vector2(local.x, local.z).length() < 0.9 and local.y > -0.5 and local.y < 2.0:
			entered.emit()


func _update_power(filled: Array) -> void:
	var count := 0
	for i in filled.size():
		if filled[i]:
			count += 1
		_socket_mats[i].emission_energy_multiplier = 2.0 if filled[i] else 0.0
	powered = count >= needs and not locked
	_ring_mat.emission_energy_multiplier = 2.5 if powered else 0.0
	_beam.visible = powered


func _process(delta: float) -> void:
	_t += delta
	if _beam.visible:
		_beam.rotation.y = _t * 0.8
		(_beam.material_override as StandardMaterial3D).albedo_color.a = 0.14 + 0.06 * sin(_t * 3.0)
