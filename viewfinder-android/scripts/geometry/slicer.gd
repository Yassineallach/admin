class_name Slicer
extends RefCounted
## Plane clipping of convex solids, and the photo frustum operations that drive
## the whole game:
##
##  * capture: keep only the parts of the world inside the photo frustum
##  * place:   delete everything inside the frustum, then paste the photo in
##
## The frustum is the infinite square pyramid that starts at the camera and
## opens along -Z, with half-angle tangent `t` on both axes.

const EPS := 0.0005
const MERGE_EPS := 0.0005
## Pieces thinner than this along the cutting plane normal are discarded.
const MIN_THICKNESS := 0.004


## Clip `s` keeping the half-space where plane.distance_to(p) >= 0.
## Returns `s` itself when untouched, null when nothing is left.
static func clip(s: Solid, plane: Plane, cap_color: Variant = null) -> Solid:
	var any_out := false
	var max_d := -INF
	for f in s.faces:
		for p in (f["v"] as PackedVector3Array):
			var d := plane.distance_to(p)
			max_d = maxf(max_d, d)
			if d < -EPS:
				any_out = true
	if not any_out:
		return s
	if max_d < MIN_THICKNESS:
		return null

	var out := Solid.new()
	out.copy_meta_from(s)
	var cap_pts := PackedVector3Array()
	for f in s.faces:
		var poly: PackedVector3Array = f["v"]
		var res := PackedVector3Array()
		var n := poly.size()
		for i in n:
			var a: Vector3 = poly[i]
			var b: Vector3 = poly[(i + 1) % n]
			var da := plane.distance_to(a)
			var db := plane.distance_to(b)
			if da >= -EPS:
				res.append(a)
				if da <= EPS:
					cap_pts.append(a)
			if (da > EPS and db < -EPS) or (da < -EPS and db > EPS):
				var p := a.lerp(b, da / (da - db))
				res.append(p)
				cap_pts.append(p)
		res = _clean_polygon(res)
		if res.size() >= 3:
			var g: Dictionary = f.duplicate()
			g["v"] = res
			out.faces.append(g)

	var cap := _build_cap(cap_pts, -plane.normal)
	if cap.size() >= 3:
		var cc: Color = cap_color if cap_color != null else s.color
		out.add_face(cap, -plane.normal, cc)
	if out.faces.size() < 4:
		return null
	return out


## Splits `s` into (inside, outside) where inside = plane side >= 0.
static func split(s: Solid, plane: Plane) -> Array:
	var flipped := Plane(-plane.normal, -plane.d)
	return [clip(s, plane), clip(s, flipped)]


static func _clean_polygon(poly: PackedVector3Array) -> PackedVector3Array:
	var res := PackedVector3Array()
	for p in poly:
		if res.is_empty() or res[res.size() - 1].distance_squared_to(p) > MERGE_EPS * MERGE_EPS:
			res.append(p)
	while res.size() > 1 and res[0].distance_squared_to(res[res.size() - 1]) <= MERGE_EPS * MERGE_EPS:
		res.remove_at(res.size() - 1)
	return res


## Orders the coplanar intersection points into a convex polygon.
static func _build_cap(pts: PackedVector3Array, normal: Vector3) -> PackedVector3Array:
	var uniq := PackedVector3Array()
	for p in pts:
		var dup := false
		for q in uniq:
			if p.distance_squared_to(q) <= MERGE_EPS * MERGE_EPS * 4.0:
				dup = true
				break
		if not dup:
			uniq.append(p)
	if uniq.size() < 3:
		return PackedVector3Array()
	var c := Vector3.ZERO
	for p in uniq:
		c += p
	c /= uniq.size()
	var u := normal.cross(Vector3.UP if absf(normal.y) < 0.9 else Vector3.RIGHT).normalized()
	var v := normal.cross(u)
	var keyed: Array = []
	for p in uniq:
		var r := p - c
		keyed.append([atan2(r.dot(v), r.dot(u)), p])
	keyed.sort_custom(func(a, b): return a[0] < b[0])
	var res := PackedVector3Array()
	for k in keyed:
		res.append(k[1])
	return res


# ---------------------------------------------------------------------------
# Photo frustum
# ---------------------------------------------------------------------------

## The 4 inward-facing side planes of the photo frustum in camera-local space.
static func local_frustum(t: float) -> Array:
	return [
		Plane(Vector3(-1, 0, -t).normalized(), 0.0),  # right
		Plane(Vector3(1, 0, -t).normalized(), 0.0),   # left
		Plane(Vector3(0, -1, -t).normalized(), 0.0),  # top
		Plane(Vector3(0, 1, -t).normalized(), 0.0),   # bottom
	]


static func world_frustum(cam: Transform3D, t: float) -> Array:
	var out: Array = []
	for pl in local_frustum(t):
		out.append(cam * (pl as Plane))
	return out


static func point_in_frustum(cam: Transform3D, t: float, p: Vector3) -> bool:
	var l := cam.affine_inverse() * p
	var depth := -l.z
	return depth > 0.05 and absf(l.x) <= t * depth and absf(l.y) <= t * depth


## 0 = fully outside some plane, 1 = fully inside all planes, 2 = straddles.
static func _classify(s: Solid, planes: Array) -> int:
	# Fast path on the cached bounding box.
	var b := s.bounds()
	var box_inside_all := true
	for pl in planes:
		var plane: Plane = pl
		var mx := -INF
		var mn := INF
		for i in 8:
			var d := plane.distance_to(b.get_endpoint(i))
			mx = maxf(mx, d)
			mn = minf(mn, d)
		if mx < -EPS:
			return 0
		if mn < -EPS:
			box_inside_all = false
	if box_inside_all:
		return 1
	if s.is_soup():
		return 2  # decided triangle by triangle
	var inside_all := true
	for pl in planes:
		var all_out := true
		var all_in := true
		for f in s.faces:
			for p in (f["v"] as PackedVector3Array):
				var d := (pl as Plane).distance_to(p)
				if d > EPS:
					all_out = false
				if d < -EPS:
					all_in = false
		if all_out:
			return 0
		if not all_in:
			inside_all = false
	return 1 if inside_all else 2


## Returns the pieces of `solids` that lie inside the frustum, expressed in
## camera-local coordinates.
static func capture(solids: Array, cam: Transform3D, t: float) -> Array:
	var planes := world_frustum(cam, t)
	var inv := cam.affine_inverse()
	var out: Array = []
	for s in solids:
		if (s as Solid).anchored:
			continue
		var cls := _classify(s, planes)
		if cls == 0:
			continue
		var piece: Solid = s
		if cls == 2:
			if s.is_soup():
				piece = _cut_soup(s, planes, true)
			else:
				for pl in planes:
					piece = clip(piece, pl)
					if piece == null:
						break
		if piece != null:
			out.append(piece.transformed(inv))
	return out


## Removes everything inside the frustum from `solids` and returns the
## remaining pieces (as a new array). Pieces outside are split into convex
## parts, one per frustum side they stick out of.
static func carve(solids: Array, cam: Transform3D, t: float) -> Array:
	var planes := world_frustum(cam, t)
	var out: Array = []
	for s in solids:
		if (s as Solid).anchored:
			out.append(s)
			continue
		var cls := _classify(s, planes)
		if cls == 0:
			out.append(s)
			continue
		if cls == 1:
			continue
		if s.is_soup():
			var kept := _cut_soup(s, planes, false)
			if kept != null:
				out.append(kept)
			continue
		var rest: Solid = s
		for pl in planes:
			var parts := split(rest, pl)
			if parts[1] != null:
				out.append(parts[1])
			rest = parts[0]
			if rest == null:
				break
		# Whatever is left in `rest` is inside the frustum and gets deleted.
	return out


## Full photo placement: carve the world, then paste the photo's solids.
static func place(world: Array, photo_solids: Array, cam: Transform3D, t: float) -> Array:
	var out := carve(world, cam, t)
	for s in photo_solids:
		out.append((s as Solid).transformed(cam))
	return out


# ---------------------------------------------------------------------------
# Triangle soups (imported art)
# ---------------------------------------------------------------------------

## Triangles with an edge longer than this are clipped exactly; smaller ones
## are kept or dropped whole by their centroid (fast, and invisible on dense
## foliage and props).
const BIG_TRI_SQ := 0.45 * 0.45


## Keeps the part of a soup inside all `planes` (keep_inside) or outside the
## region they bound (not keep_inside). Returns null when nothing is left.
static func _cut_soup(s: Solid, planes: Array, keep_inside: bool) -> Solid:
	var out := Solid.new()
	out.copy_meta_from(s)
	var pn: Array = []
	var pd: Array = []
	for pl in planes:
		pn.append((pl as Plane).normal)
		pd.append((pl as Plane).d)
	var np := planes.size()
	for c in s.soup:
		var v: PackedVector3Array = c["v"]
		var n: PackedVector3Array = c["n"]
		var uv: PackedVector2Array = c["uv"]
		var ov := PackedVector3Array()
		var on := PackedVector3Array()
		var ouv := PackedVector2Array()
		var i := 0
		var count := v.size()
		while i < count:
			var a := v[i]
			var b := v[i + 1]
			var d := v[i + 2]
			var all_in := true
			var outside := false
			for k in np:
				var nn: Vector3 = pn[k]
				var dd: float = pd[k]
				var da := nn.dot(a) - dd
				var db := nn.dot(b) - dd
				var dc := nn.dot(d) - dd
				if da < 0.0 and db < 0.0 and dc < 0.0:
					outside = true
					break
				if da < 0.0 or db < 0.0 or dc < 0.0:
					all_in = false
			var inside: bool
			if outside:
				inside = false
			elif all_in:
				inside = true
			elif maxf(a.distance_squared_to(b), maxf(b.distance_squared_to(d), d.distance_squared_to(a))) > BIG_TRI_SQ:
				_clip_tri(planes, keep_inside, [[a, n[i], uv[i]], [b, n[i + 1], uv[i + 1]], [d, n[i + 2], uv[i + 2]]], ov, on, ouv)
				i += 3
				continue
			else:
				var cen := (a + b + d) / 3.0
				inside = true
				for k in np:
					if (pn[k] as Vector3).dot(cen) - float(pd[k]) < 0.0:
						inside = false
						break
			if inside == keep_inside:
				ov.append(a); ov.append(b); ov.append(d)
				on.append(n[i]); on.append(n[i + 1]); on.append(n[i + 2])
				ouv.append(uv[i]); ouv.append(uv[i + 1]); ouv.append(uv[i + 2])
			i += 3
		if not ov.is_empty():
			out.soup.append({"mat": c["mat"], "v": ov, "n": on, "uv": ouv})
	return out if out.is_soup() else null


## Exact clip of one textured triangle, appending the kept fan triangles.
static func _clip_tri(planes: Array, keep_inside: bool, poly: Array,
		ov: PackedVector3Array, on: PackedVector3Array, ouv: PackedVector2Array) -> void:
	var rest := poly
	for pl in planes:
		var plane: Plane = pl
		if not keep_inside:
			var outside := _clip_poly(rest, Plane(-plane.normal, -plane.d))
			_emit_fan(outside, ov, on, ouv)
		rest = _clip_poly(rest, plane)
		if rest.size() < 3:
			return
	if keep_inside:
		_emit_fan(rest, ov, on, ouv)


static func _clip_poly(poly: Array, pl: Plane) -> Array:
	var out: Array = []
	var m := poly.size()
	for i in m:
		var A: Array = poly[i]
		var B: Array = poly[(i + 1) % m]
		var da := pl.distance_to(A[0])
		var db := pl.distance_to(B[0])
		if da >= 0.0:
			out.append(A)
		if (da >= 0.0) != (db >= 0.0):
			var t := da / (da - db)
			out.append([(A[0] as Vector3).lerp(B[0], t), (A[1] as Vector3).lerp(B[1], t).normalized(),
				(A[2] as Vector2).lerp(B[2], t)])
	return out


static func _emit_fan(poly: Array, ov: PackedVector3Array, on: PackedVector3Array, ouv: PackedVector2Array) -> void:
	for i in range(1, poly.size() - 1):
		for p in [poly[0], poly[i], poly[i + 1]]:
			ov.append(p[0])
			on.append(p[1])
			ouv.append(p[2])
