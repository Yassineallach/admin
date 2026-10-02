class_name ModelLib
extends RefCounted
## Loads imported CC0 models (Quaternius kits under res://assets/) once and
## turns them into sliceable triangle-soup Solids.

static var _cache: Dictionary = {}  # path -> { chunks: Array, aabb: AABB }

const NATURE := "res://assets/nature/"
const VILLAGE := "res://assets/village/"


## Local-space triangle chunks of a model (one per material).
static func data(path: String) -> Dictionary:
	if _cache.has(path):
		return _cache[path]
	var out := {"chunks": [], "aabb": AABB()}
	var scene: PackedScene = load(path)
	if scene == null:
		push_error("ModelLib: can't load " + path)
		_cache[path] = out
		return out
	var root := scene.instantiate()
	var first := true
	for mi in _mesh_instances(root):
		var xf := _local_xf(mi, root)
		var mesh: Mesh = mi.mesh
		for si in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(si)
			var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var norms: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV] if arrays[Mesh.ARRAY_TEX_UV] != null else PackedVector2Array()
			var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			var v := PackedVector3Array()
			var n := PackedVector3Array()
			var uv := PackedVector2Array()
			var count := idx.size() if not idx.is_empty() else verts.size()
			v.resize(count)
			n.resize(count)
			uv.resize(count)
			for k in count:
				var i := idx[k] if not idx.is_empty() else k
				v[k] = verts[i]
				n[k] = norms[i] if i < norms.size() else Vector3.UP
				uv[k] = uvs[i] if i < uvs.size() else Vector2.ZERO
			# Godot meshes are clockwise; keep that winding for the soup.
			v = xf * v
			n = Transform3D(xf.basis, Vector3.ZERO) * n
			var mat: Material = mi.get_surface_override_material(si)
			if mat == null:
				mat = mesh.surface_get_material(si)
			out["chunks"].append({"mat": mat, "v": v, "n": n, "uv": uv})
			for p in v:
				if first:
					out["aabb"] = AABB(p, Vector3.ZERO)
					first = false
				else:
					out["aabb"] = (out["aabb"] as AABB).expand(p)
	root.free()
	_cache[path] = out
	return out


static func _mesh_instances(n: Node) -> Array:
	var out: Array = []
	if n is MeshInstance3D and (n as MeshInstance3D).mesh != null:
		out.append(n)
	for c in n.get_children():
		out.append_array(_mesh_instances(c))
	return out


static func _local_xf(n: Node, root: Node) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var cur := n
	while cur != null and cur != root:
		if cur is Node3D:
			xf = (cur as Node3D).transform * xf
		cur = cur.get_parent()
	return xf


## A placed copy of a model as a soup Solid.
static func instance(path: String, pos: Vector3, yaw_deg: float = 0.0, scale: float = 1.0) -> Solid:
	var d := data(path)
	var s := Solid.new()
	s.collide = false
	s.material = Mat.PLASTER
	var xf := Transform3D(Basis(Vector3.UP, deg_to_rad(yaw_deg)).scaled(Vector3.ONE * scale), pos)
	var rot := Transform3D(Basis(Vector3.UP, deg_to_rad(yaw_deg)), Vector3.ZERO)
	for c in d["chunks"]:
		s.soup.append({"mat": c["mat"], "v": xf * (c["v"] as PackedVector3Array),
			"n": rot * (c["n"] as PackedVector3Array), "uv": c["uv"]})
	s._bounds = xf * (d["aabb"] as AABB)
	s._bounds_cached = true
	return s


static func aabb(path: String) -> AABB:
	return data(path)["aabb"]
