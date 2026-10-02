class_name Solid
extends RefCounted
## A convex polyhedron made of planar polygon faces.
##
## Solids are treated as immutable: every slicing / transform operation returns
## a new Solid. That lets the rewind system keep cheap references to old world
## states without deep copies.

## Each face: { "v": PackedVector3Array (convex polygon), "n": Vector3 (outward), "c": Color }
var faces: Array = []
## Colour used for new cap faces produced when this solid is cut.
var color: Color = Color.WHITE
## Whether the solid gets a collision shape.
var collide: bool = true
## Free-form tag ("source" marks scenery that only exists to be photographed).
var tag: String = ""


func add_face(verts: PackedVector3Array, normal: Vector3, col: Color) -> void:
	faces.append({"v": verts, "n": normal.normalized(), "c": col})


func copy_meta_from(other: Solid) -> void:
	color = other.color
	collide = other.collide
	tag = other.tag


## Returns a copy of this solid with all vertices transformed by `xf`.
## Only rigid transforms (rotation + translation) are expected.
func transformed(xf: Transform3D) -> Solid:
	var s := Solid.new()
	s.copy_meta_from(self)
	for f in faces:
		var src: PackedVector3Array = f["v"]
		var dst := PackedVector3Array()
		dst.resize(src.size())
		for i in src.size():
			dst[i] = xf * src[i]
		s.faces.append({"v": dst, "n": (xf.basis * (f["n"] as Vector3)).normalized(), "c": f["c"]})
	return s


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


func get_aabb() -> AABB:
	var first := true
	var box := AABB()
	for f in faces:
		for p in (f["v"] as PackedVector3Array):
			if first:
				box = AABB(p, Vector3.ZERO)
				first = false
			else:
				box = box.expand(p)
	return box


func center() -> Vector3:
	var pts := points()
	var c := Vector3.ZERO
	for p in pts:
		c += p
	return c / maxf(1.0, pts.size())


## Volume via the divergence theorem (used by tests and to drop slivers).
## Uses each face's stored outward normal, so vertex winding does not matter.
func volume() -> float:
	var vol := 0.0
	for f in faces:
		var v: PackedVector3Array = f["v"]
		var area := Vector3.ZERO
		for i in range(1, v.size() - 1):
			area += (v[i] - v[0]).cross(v[i + 1] - v[0])
		vol += area.length() * 0.5 * (f["n"] as Vector3).dot(v[0]) / 3.0
	return absf(vol)


# ---------------------------------------------------------------------------
# Primitive builders
# ---------------------------------------------------------------------------

## Axis-aligned box. `top` overrides the colour of the upward face.
static func box(c: Vector3, size: Vector3, col: Color, top: Color = Color(0, 0, 0, 0)) -> Solid:
	var s := Solid.new()
	s.color = col
	var h := size * 0.5
	var top_col := top if top.a > 0.0 else col
	var side_dark := col.darkened(0.06)
	var p := [
		c + Vector3(-h.x, -h.y, -h.z), c + Vector3(h.x, -h.y, -h.z),
		c + Vector3(h.x, h.y, -h.z), c + Vector3(-h.x, h.y, -h.z),
		c + Vector3(-h.x, -h.y, h.z), c + Vector3(h.x, -h.y, h.z),
		c + Vector3(h.x, h.y, h.z), c + Vector3(-h.x, h.y, h.z),
	]
	s.add_face(PackedVector3Array([p[3], p[2], p[6], p[7]]), Vector3.UP, top_col)
	s.add_face(PackedVector3Array([p[0], p[4], p[5], p[1]]), Vector3.DOWN, col.darkened(0.25))
	s.add_face(PackedVector3Array([p[4], p[7], p[6], p[5]]), Vector3.BACK, col)
	s.add_face(PackedVector3Array([p[0], p[1], p[2], p[3]]), Vector3.FORWARD, side_dark)
	s.add_face(PackedVector3Array([p[1], p[5], p[6], p[2]]), Vector3.RIGHT, col.darkened(0.03))
	s.add_face(PackedVector3Array([p[0], p[3], p[7], p[4]]), Vector3.LEFT, side_dark)
	return s


## Box from min/max corners.
static func box_mm(mn: Vector3, mx: Vector3, col: Color, top: Color = Color(0, 0, 0, 0)) -> Solid:
	return box((mn + mx) * 0.5, mx - mn, col, top)


## A ramp whose low edge is centred at `start` (on the ground at start.y) and
## rises by `height` over `length` metres along the horizontal unit vector `dir`.
static func ramp(start: Vector3, dir: Vector3, length: float, width: float, height: float,
		col: Color, top: Color = Color(0, 0, 0, 0)) -> Solid:
	dir = Vector3(dir.x, 0, dir.z).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	var mid := start + dir * length * 0.5 + Vector3.UP * height * 0.5
	# Build an oriented box by building it axis-aligned then rotating.
	var basis := Basis(side, Vector3.UP, -dir)
	var b := box(Vector3.ZERO, Vector3(width, height, length), col, top)
	var s := b.transformed(Transform3D(basis, mid))
	# Cut along the slope: keep H*(s) - L*(y - y0) >= 0 where s = (p - start).dir
	var n := dir * height - Vector3.UP * length
	var d := height * start.dot(dir) - length * start.y
	var inv := 1.0 / n.length()
	var cap := top if top.a > 0.0 else col
	var cut := Slicer.clip(s, Plane(n * inv, d * inv), cap)
	if cut == null:
		return s
	cut.color = col
	return cut
