class_name SolidWorld
extends Node3D
## Owns the list of Solids that make up the level and turns it into a single
## batched mesh + one static body (cheap on mobile GPUs: one draw call).

signal rebuilt

var solids: Array = []
var material: Material

var _mesh_instance: MeshInstance3D
var _anchored_mesh: MeshInstance3D
var _body: StaticBody3D


func _ready() -> void:
	_mesh_instance = MeshInstance3D.new()
	_mesh_instance.name = "Mesh"
	add_child(_mesh_instance)
	# Archive stone lives on its own mesh on a layer the photo camera can't see.
	_anchored_mesh = MeshInstance3D.new()
	_anchored_mesh.name = "Anchored"
	_anchored_mesh.layers = 4
	add_child(_anchored_mesh)
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
	var normal: Array = []
	var anchored: Array = []
	for s in solids:
		if (s as Solid).anchored:
			anchored.append(s)
		else:
			normal.append(s)
	_mesh_instance.mesh = build_mesh(normal, material)
	_anchored_mesh.mesh = build_mesh(anchored, material)
	for c in _body.get_children():
		_body.remove_child(c)
		c.queue_free()
	for s in solids:
		var sol: Solid = s
		if not sol.collide:
			continue
		if sol.shape_cache == null:
			var pts := sol.points()
			if pts.size() < 4:
				continue
			sol.shape_cache = ConvexPolygonShape3D.new()
			sol.shape_cache.points = pts
		var cs := CollisionShape3D.new()
		cs.shape = sol.shape_cache
		_body.add_child(cs)
	rebuilt.emit()


static func build_mesh(list: Array, mat: Material) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var custom := PackedFloat32Array()
	for s in list:
		var sol: Solid = s
		if not sol.visible:
			continue
		if sol.mesh_cache.is_empty():
			sol.mesh_cache = _solid_arrays(sol)
		var c: Array = sol.mesh_cache
		verts.append_array(c[0])
		normals.append_array(c[1])
		colors.append_array(c[2])
		uvs.append_array(c[3])
		uv2s.append_array(c[4])
		custom.append_array(c[5])
	var mesh := ArrayMesh.new()
	if verts.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_TEX_UV2] = uv2s
	arrays[Mesh.ARRAY_CUSTOM0] = custom
	var fmt := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, fmt)
	if mat:
		mesh.surface_set_material(0, mat)
	return mesh


## Triangulated vertex data for one solid:
## [verts, normals, colors, uv (metres), uv2 (material, style), custom0].
## CUSTOM0 = (barycentric xyz, bitmask of triangle edges that are real polygon
## edges) so the shader can draw outlines for the sketch / painting styles.
static func _solid_arrays(sol: Solid) -> Array:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var custom := PackedFloat32Array()
	const BARY := [Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, 1)]
	var style := float(sol.style)
	for f in sol.faces:
		var v: PackedVector3Array = f["v"]
		var n: Vector3 = f["n"]
		var col: Color = f["c"]
		var o: Vector3 = f["o"]
		var U: Vector3 = f["U"]
		var V: Vector3 = f["V"]
		var mid := Vector2(float(f["m"]), style)
		var sc: Variant = f.get("sc")
		var ax: Variant = f.get("ax")
		var nv := v.size()
		for i in range(1, nv - 1):
			var idx := [0, i, i + 1]
			# Godot treats clockwise triangles as front faces.
			if (v[i] - v[0]).cross(v[i + 1] - v[0]).dot(n) > 0.0:
				idx = [0, i + 1, i]
			# Edge opposite corner k joins the other two corners; it is a real
			# polygon edge when those are neighbours on the polygon.
			var mask := 0
			for k in 3:
				var a: int = idx[(k + 1) % 3]
				var b: int = idx[(k + 2) % 3]
				var dd: int = absi(a - b)
				if dd == 1 or dd == nv - 1:
					mask |= 1 << k
			for k in 3:
				var pv: Vector3 = v[idx[k]]
				var bc: Vector3 = BARY[k]
				custom.append(bc.x); custom.append(bc.y); custom.append(bc.z); custom.append(float(mask))
				verts.append(pv)
				var nn := n
				if sc != null:
					nn = (pv - (sc as Vector3)).normalized()
				elif ax != null:
					var ap: Vector3 = ax[0]
					var ad: Vector3 = ax[1]
					var r := pv - ap
					r -= ad * r.dot(ad)
					if r.length_squared() > 1e-8:
						nn = r.normalized()
				normals.append(nn)
				colors.append(col)
				var d := pv - o
				uvs.append(Vector2(d.dot(U), d.dot(V)))
				uv2s.append(mid)
	return [verts, normals, colors, uvs, uv2s, custom]
