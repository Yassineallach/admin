class_name Solid
extends RefCounted
## A convex polyhedron made of planar polygon faces.
##
## Solids are treated as immutable: every slicing / transform operation returns
## a new Solid. That lets the rewind system keep cheap references to old world
## states without deep copies.
##
## Each face is a Dictionary:
##   v  : PackedVector3Array   convex polygon
##   n  : Vector3              outward normal
##   c  : Color                tint
##   m  : int                  material id (see Mat)
##   o, U, V : Vector3         texture frame: uv = ((p-o).U, (p-o).V) in metres.
##                             The frame moves with the face, so textures stay
##                             glued to geometry that a photo relocates.
##   sc : Vector3 (optional)   sphere centre -> smooth spherical normals
##   ax : Array  (optional)    [point, dir] cylinder axis -> smooth radial normals

## Tint / material used for cap faces created when this solid is cut.
var color: Color = Color.WHITE
var material: int = Mat.PLASTER
## Art style the solid is rendered with (Mat.STYLE_*). Kept through photos.
var style: int = Mat.STYLE_NORMAL
var collide: bool = true
var visible: bool = true
## Archive stone: photos can't cut it, copy it, or even see it.
var anchored: bool = false
## Free-form tag ("source" marks scenery that only exists to be photographed).
var tag: String = ""

var faces: Array = []
var _bounds_cached := false
var _bounds := AABB()
## Detailed art (imported models) is stored as a triangle "soup" instead of
## convex faces: Array of chunks { mat: Material, v, n: PackedVector3Array
## (triangle list), uv: PackedVector2Array }. Soups are cut triangle by
## triangle, never capped, and never collide (props get invisible convex
## colliders instead).
var soup: Array = []
## Caches filled lazily by SolidWorld (valid forever: solids never change).
var mesh_cache: Array = []
var shape_cache: ConvexPolygonShape3D


static func frame_for(n: Vector3) -> Array:
	var an := n.abs()
	if an.y >= an.x and an.y >= an.z:
		return [Vector3.RIGHT, Vector3.BACK]
	if an.x >= an.z:
		return [Vector3.BACK, Vector3.UP]
	return [Vector3.RIGHT, Vector3.UP]


func add_face(verts: PackedVector3Array, normal: Vector3, col: Color, mat: int = -1) -> Dictionary:
	var n := normal.normalized()
	var fr := frame_for(n)
	var f := {"v": verts, "n": n, "c": col, "m": material if mat < 0 else mat,
		"o": Vector3.ZERO, "U": fr[0], "V": fr[1]}
	faces.append(f)
	return f


func copy_meta_from(other: Solid) -> void:
	color = other.color
	material = other.material
	style = other.style
	collide = other.collide
	visible = other.visible
	anchored = other.anchored
	tag = other.tag


func is_soup() -> bool:
	return not soup.is_empty()


## Returns a copy of this solid transformed by the rigid transform `xf`.
func transformed(xf: Transform3D) -> Solid:
	var s := Solid.new()
	s.copy_meta_from(self)
	if is_soup():
		var rot := Transform3D(xf.basis, Vector3.ZERO)
		for c in soup:
			s.soup.append({"mat": c["mat"], "v": xf * (c["v"] as PackedVector3Array),
				"n": rot * (c["n"] as PackedVector3Array), "uv": c["uv"]})
		s._bounds = xf * bounds()
		s._bounds_cached = true
		return s
	var b := xf.basis
	for f in faces:
		var src: PackedVector3Array = f["v"]
		var dst := PackedVector3Array()
		dst.resize(src.size())
		for i in src.size():
			dst[i] = xf * src[i]
		var g: Dictionary = f.duplicate()
		g["v"] = dst
		g["n"] = (b * (f["n"] as Vector3)).normalized()
		g["o"] = xf * (f["o"] as Vector3)
		g["U"] = b * (f["U"] as Vector3)
		g["V"] = b * (f["V"] as Vector3)
		if f.has("sc"):
			g["sc"] = xf * (f["sc"] as Vector3)
		if f.has("ax"):
			g["ax"] = [xf * (f["ax"][0] as Vector3), (b * (f["ax"][1] as Vector3)).normalized()]
		s.faces.append(g)
	return s


func with(props: Dictionary) -> Solid:
	for k in props.keys():
		set(k, props[k])
	return self


## Unique vertex positions (used for convex collision shapes).
func points() -> PackedVector3Array:
	var out := PackedVector3Array()
	for f in faces:
		for p in (f["v"] as PackedVector3Array):
			var dup := false
			for q in out:
				if p.distance_squared_to(q) < 1e-8:
					dup = true
					break
			if not dup:
				out.append(p)
	return out


## Cached AABB (solids are immutable once built, so this never goes stale).
func bounds() -> AABB:
	if not _bounds_cached:
		_bounds = get_aabb()
		_bounds_cached = true
	return _bounds


func get_aabb() -> AABB:
	var first := true
	var box := AABB()
	for c in soup:
		for p in (c["v"] as PackedVector3Array):
			if first:
				box = AABB(p, Vector3.ZERO)
				first = false
			else:
				box = box.expand(p)
	for f in faces:
		for p in (f["v"] as PackedVector3Array):
			if first:
				box = AABB(p, Vector3.ZERO)
				first = false
			else:
				box = box.expand(p)
	return box


## Volume via the divergence theorem, using stored outward normals.
func volume() -> float:
	if is_soup():
		return 0.0
	var vol := 0.0
	for f in faces:
		var v: PackedVector3Array = f["v"]
		var area := Vector3.ZERO
		for i in range(1, v.size() - 1):
			area += (v[i] - v[0]).cross(v[i + 1] - v[0])
		vol += area.length() * 0.5 * (f["n"] as Vector3).dot(v[0]) / 3.0
	return absf(vol)


# ---------------------------------------------------------------------------
# Primitive builders (all convex)
# ---------------------------------------------------------------------------

## Axis-aligned box. `top` overrides the colour of the upward face and
## `top_mat` its material (e.g. grass on top of rock).
static func box(c: Vector3, size: Vector3, col: Color, top: Color = Color(0, 0, 0, 0),
		mat: int = Mat.PLASTER, top_mat: int = -1) -> Solid:
	var s := Solid.new()
	s.color = col
	s.material = mat
	var h := size * 0.5
	var top_col := top if top.a > 0.0 else col
	var p := [
		c + Vector3(-h.x, -h.y, -h.z), c + Vector3(h.x, -h.y, -h.z),
		c + Vector3(h.x, h.y, -h.z), c + Vector3(-h.x, h.y, -h.z),
		c + Vector3(-h.x, -h.y, h.z), c + Vector3(h.x, -h.y, h.z),
		c + Vector3(h.x, h.y, h.z), c + Vector3(-h.x, h.y, h.z),
	]
	s.add_face(PackedVector3Array([p[3], p[2], p[6], p[7]]), Vector3.UP, top_col, top_mat)
	s.add_face(PackedVector3Array([p[0], p[4], p[5], p[1]]), Vector3.DOWN, col.darkened(0.2))
	s.add_face(PackedVector3Array([p[4], p[7], p[6], p[5]]), Vector3.BACK, col)
	s.add_face(PackedVector3Array([p[0], p[1], p[2], p[3]]), Vector3.FORWARD, col)
	s.add_face(PackedVector3Array([p[1], p[5], p[6], p[2]]), Vector3.RIGHT, col)
	s.add_face(PackedVector3Array([p[0], p[3], p[7], p[4]]), Vector3.LEFT, col)
	return s


## Box from min/max corners.
static func box_mm(mn: Vector3, mx: Vector3, col: Color, top: Color = Color(0, 0, 0, 0),
		mat: int = Mat.PLASTER, top_mat: int = -1) -> Solid:
	return box((mn + mx) * 0.5, mx - mn, col, top, mat, top_mat)


## A ramp whose low edge is centred at `start` and rises by `height` over
## `length` metres along the horizontal unit vector `dir`.
static func ramp(start: Vector3, dir: Vector3, length: float, width: float, height: float,
		col: Color, top: Color = Color(0, 0, 0, 0), mat: int = Mat.PLASTER, top_mat: int = -1) -> Solid:
	dir = Vector3(dir.x, 0, dir.z).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	var mid := start + dir * length * 0.5 + Vector3.UP * height * 0.5
	var basis := Basis(side, Vector3.UP, -dir)
	var b := box(Vector3.ZERO, Vector3(width, height, length), col, Color(0, 0, 0, 0), mat)
	var s := b.transformed(Transform3D(basis, mid))
	var n := dir * height - Vector3.UP * length
	var d := height * start.dot(dir) - length * start.y
	var inv := 1.0 / n.length()
	var cut := Slicer.clip(s, Plane(n * inv, d * inv), top if top.a > 0.0 else col)
	if cut == null:
		return s
	if top_mat >= 0:
		cut.faces[cut.faces.size() - 1]["m"] = top_mat
	cut.color = col
	cut.material = mat
	return cut


## Regular N-gon in the XZ plane (counter-clockwise seen from above).
static func ngon(n: int, r: float, phase: float = 0.0) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in n:
		var a := phase + TAU * i / n
		out.append(Vector2(cos(a), -sin(a)) * r)
	return out


## Loft between two similar convex polygons (top = bottom scaled), placed at
## heights y0 / y1 around `c`. Covers prisms, cylinders, cones, island bottoms.
static func loft(c: Vector3, poly: PackedVector2Array, y0: float, y1: float, top_scale: float,
		col: Color, mat: int = Mat.PLASTER, top: Color = Color(0, 0, 0, 0), top_mat: int = -1,
		smooth: bool = false) -> Solid:
	var s := Solid.new()
	s.color = col
	s.material = mat
	var n := poly.size()
	var bot := PackedVector3Array()
	var tp := PackedVector3Array()
	for p in poly:
		bot.append(c + Vector3(p.x, y0, p.y))
		tp.append(c + Vector3(p.x * top_scale, y1, p.y * top_scale))
	var top_poly := PackedVector3Array()
	var bot_poly := PackedVector3Array()
	for i in n:
		top_poly.append(tp[i])
		bot_poly.append(bot[n - 1 - i])
	if top_scale > 0.001:
		s.add_face(top_poly, Vector3.UP, top if top.a > 0.0 else col, top_mat)
	s.add_face(bot_poly, Vector3.DOWN, col.darkened(0.15))
	var axis_dir := Vector3.UP
	for i in n:
		var j := (i + 1) % n
		var quad := PackedVector3Array([bot[i], bot[j]])
		if top_scale > 0.001:
			quad.append(tp[j])
			quad.append(tp[i])
		else:
			quad.append(tp[i])
		var nn := (bot[j] - bot[i]).cross(tp[i] - bot[i]).normalized()
		if nn.dot((bot[i] + bot[j]) * 0.5 - (c + Vector3(0, y0, 0))) < 0:
			nn = -nn
		var f := s.add_face(quad, nn, col)
		if smooth:
			f["ax"] = [c + Vector3(0, y0, 0), axis_dir]
	return s


## Geodesic sphere (icosahedron subdivided once: 80 faces). Smooth-shaded.
static func sphere(c: Vector3, r: Vector3, col: Color, mat: int = Mat.FOLIAGE, subdiv: int = 1) -> Solid:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var verts := [
		Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0),
		Vector3(0, -1, t), Vector3(0, 1, t), Vector3(0, -1, -t), Vector3(0, 1, -t),
		Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	for i in verts.size():
		verts[i] = (verts[i] as Vector3).normalized()
	var tris := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4],
		[11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
		[4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
	var sub: Array = []
	if subdiv <= 0:
		for tri in tris:
			sub.append([verts[tri[0]], verts[tri[1]], verts[tri[2]]])
		tris = []
	for tri in tris:
		var a: Vector3 = verts[tri[0]]
		var b: Vector3 = verts[tri[1]]
		var d: Vector3 = verts[tri[2]]
		var ab := ((a + b) * 0.5).normalized()
		var bd := ((b + d) * 0.5).normalized()
		var da := ((d + a) * 0.5).normalized()
		sub.append([a, ab, da]); sub.append([ab, b, bd]); sub.append([da, bd, d]); sub.append([ab, bd, da])
	var s := Solid.new()
	s.color = col
	s.material = mat
	for tri in sub:
		var pts := PackedVector3Array()
		for v in tri:
			pts.append(c + (v as Vector3) * r)
		var nn := (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
		if nn.dot(pts[0] - c) < 0:
			nn = -nn
		var f := s.add_face(pts, nn, col)
		f["sc"] = c
	return s


## Convex polygon (local XY, any winding) extruded `depth` along local -Z…+Z,
## then placed with `xf`. Used for arch segments, roofs, wedges.
static func extrude(poly: PackedVector2Array, depth: float, xf: Transform3D, col: Color,
		mat: int = Mat.PLASTER) -> Solid:
	var s := Solid.new()
	s.color = col
	s.material = mat
	var n := poly.size()
	var c2 := Vector2.ZERO
	for p in poly:
		c2 += p
	c2 /= n
	var front := PackedVector3Array()
	var back := PackedVector3Array()
	for p in poly:
		front.append(Vector3(p.x, p.y, depth * 0.5))
		back.append(Vector3(p.x, p.y, -depth * 0.5))
	s.add_face(front, Vector3.BACK, col)
	s.add_face(back, Vector3.FORWARD, col)
	for i in n:
		var j := (i + 1) % n
		var e := poly[j] - poly[i]
		var nn := Vector3(e.y, -e.x, 0).normalized()
		var mid := (poly[i] + poly[j]) * 0.5 - c2
		if nn.dot(Vector3(mid.x, mid.y, 0)) < 0:
			nn = -nn
		s.add_face(PackedVector3Array([front[i], front[j], back[j], back[i]]), nn, col)
	return s.transformed(xf)


## Oriented box.
static func obox(center: Vector3, size: Vector3, basis: Basis, col: Color, mat: int = Mat.PLASTER,
		top: Color = Color(0, 0, 0, 0), top_mat: int = -1) -> Solid:
	return box(Vector3.ZERO, size, col, top, mat, top_mat).transformed(Transform3D(basis, center))
