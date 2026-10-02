class_name SolidWorld
extends Node3D
## Owns the list of Solids that make up the level and turns it into a single
## batched mesh + one static body (cheap on mobile GPUs: one draw call).

signal rebuilt

var solids: Array = []
var material: Material

var _mesh_instance: MeshInstance3D
var _body: StaticBody3D


func _ready() -> void:
	_mesh_instance = MeshInstance3D.new()
	_mesh_instance.name = "Mesh"
	add_child(_mesh_instance)
	_body = StaticBody3D.new()
	_body.name = "Body"
	_body.collision_layer = 1
	_body.collision_mask = 0
	add_child(_body)
	if material == null:
		var sm := ShaderMaterial.new()
		sm.shader = load("res://shaders/world.gdshader")
		material = sm


func set_solids(list: Array) -> void:
	solids = list
	rebuild()


func rebuild() -> void:
	_mesh_instance.mesh = build_mesh(solids, material)
	for c in _body.get_children():
		_body.remove_child(c)
		c.queue_free()
	for s in solids:
		var sol: Solid = s
		if not sol.collide:
			continue
		var pts := sol.points()
		if pts.size() < 4:
			continue
		var shape := ConvexPolygonShape3D.new()
		shape.points = pts
		var cs := CollisionShape3D.new()
		cs.shape = shape
		_body.add_child(cs)
	rebuilt.emit()


static func build_mesh(list: Array, mat: Material) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	for s in list:
		for f in (s as Solid).faces:
			var v: PackedVector3Array = f["v"]
			var n: Vector3 = f["n"]
			var c: Color = f["c"]
			for i in range(1, v.size() - 1):
				var a := v[0]
				var b := v[i]
				var d := v[i + 1]
				# Godot treats clockwise triangles as front faces.
				if (b - a).cross(d - a).dot(n) > 0.0:
					var tmp := b
					b = d
					d = tmp
				verts.append(a); verts.append(b); verts.append(d)
				normals.append(n); normals.append(n); normals.append(n)
				colors.append(c); colors.append(c); colors.append(c)
	var mesh := ArrayMesh.new()
	if verts.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	if mat:
		mesh.surface_set_material(0, mat)
	return mesh
