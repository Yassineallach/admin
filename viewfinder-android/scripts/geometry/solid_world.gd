class_name SolidWorld
extends Node3D
## Owns the list of Solids that make up the level and turns it into a single
## batched mesh + one static body (cheap on mobile GPUs: one draw call).

signal rebuilt

var solids: Array = []
var material: Material

var _mesh_instance: MeshInstance3D
var _anchored_mesh: MeshInstance3D
var _props_mesh: MeshInstance3D
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
	_props_mesh = MeshInstance3D.new()
	_props_mesh.name = "Props"
	add_child(_props_mesh)
	_body = StaticBody3D.new()
	_body.name = "Body"
	_body.collision_layer = 1
	_body.collision_mask = 0
	add_child(_body)
	if material == null:
		var sm := ShaderMaterial.new()
		sm.shader = load("res://shaders/world.gdshader")
		for pair in [["tex_grass", "grass.jpg"], ["tex_cobble", "cobble.png"], ["tex_brick", "stone_brick.png"],
				["tex_plaster", "plaster.png"], ["tex_wood", "wood.png"], ["tex_roof", "roof_tiles.png"], ["tex_rock", "cliff.jpg"]]:
			sm.set_shader_parameter(pair[0], load("res://assets/textures/" + pair[1]))
		material = sm


func set_solids(list: Array) -> void:
	solids = list
	rebuild()


func rebuild() -> void:
	var normal: Array = []
	var anchored: Array = []
	var props: Array = []
	for s in solids:
		if (s as Solid).is_soup():
			props.append(s)
		elif (s as Solid).anchored:
			anchored.append(s)
		else:
			normal.append(s)
	_mesh_instance.mesh = build_mesh(normal, material)
	_anchored_mesh.mesh = build_mesh(anchored, material)
	_props_mesh.mesh = build_props(props)
	for c in _body.get_children():
		_body.remove_child(c)
		c.queue_free()
	for s in solids:
		var sol: Solid = s
		if not sol.collide:
			continue
		if sol.shape_cache == null:
			# Paper-thin pieces (rugs, slivers left over from photo cuts) get no
			# collision: degenerate convex hulls upset the physics engine.
			var bb := sol.bounds().size
			if minf(bb.x, minf(bb.y, bb.z)) < 0.03:
				continue
			var pts := sol.points()
			if pts.size() < 4:
				continue
			sol.shape_cache = ConvexPolygonShape3D.new()
			sol.shape_cache.points = pts
		var cs := CollisionShape3D.new()
		cs.shape = sol.shape_cache
		_body.add_child(cs)
	rebuilt.emit()


static var _prop_mats: Dictionary = {}
const WIND_WORDS := ["Leaves", "Leaf", "Grass", "Flower", "Vine", "Fern", "Plant", "Clover"]


## Shader material for an imported surface material in a given art style.
static func prop_material(src: Material, style: int) -> Material:
	var key := "%d:%d" % [src.get_instance_id() if src else 0, style]
	if _prop_mats.has(key):
		return _prop_mats[key]
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/prop.gdshader")
	m.set_shader_parameter("style", float(style))
	if src is BaseMaterial3D:
		var b: BaseMaterial3D = src
		if b.albedo_texture:
			m.set_shader_parameter("albedo_tex", b.albedo_texture)
		else:
			m.set_shader_parameter("use_tex", 0.0)
		m.set_shader_parameter("albedo_color", b.albedo_color)
		if b.has_meta("recolor"):
			m.set_shader_parameter("recolor", 1.0)
		if b.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
			m.set_shader_parameter("alpha_cut", 0.5)
		var name := b.resource_name
		for w in WIND_WORDS:
			if name.contains(w):
				m.set_shader_parameter("wind", 1.0)
				break
	else:
		m.set_shader_parameter("use_tex", 0.0)
	_prop_mats[key] = m
	return m


## All soup solids batched into one mesh with a surface per material/style.
static func build_props(list: Array) -> ArrayMesh:
	var groups: Dictionary = {}  # key -> [mat, style, chunks]
	for s in list:
		var sol: Solid = s
		if not sol.visible:
			continue
		for c in sol.soup:
			var mat: Material = c["mat"]
			var key := "%d:%d" % [mat.get_instance_id() if mat else 0, sol.style]
			if not groups.has(key):
				groups[key] = [mat, sol.style, []]
			(groups[key][2] as Array).append(c)
	var mesh := ArrayMesh.new()
	for key in groups.keys():
		var g: Array = groups[key]
		# Packed arrays are values: build locals, then hand them over.
		var v := PackedVector3Array()
		var n := PackedVector3Array()
		var uv := PackedVector2Array()
		for c in g[2]:
			v.append_array(c["v"])
			n.append_array(c["n"])
			uv.append_array(c["uv"])
		if v.is_empty():
			continue
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = v
		arrays[Mesh.ARRAY_NORMAL] = n
		arrays[Mesh.ARRAY_TEX_UV] = uv
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		mesh.surface_set_material(mesh.get_surface_count() - 1, prop_material(g[0], g[1]))
	return mesh


static func build_mesh(list: Array, mat: Material) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var custom := PackedFloat32Array()
	for s in list:
		var sol: Solid = s
		if not sol.visible or sol.is_soup():
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
