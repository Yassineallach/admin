class_name Props
extends RefCounted
## Decorative and structural building blocks. Every prop is a list of convex
## Solids so photos can slice through trees, arches and stairs like anything
## else.

const TRUNK := Color(0.55, 0.40, 0.32)
const LEAF := Color(0.52, 0.72, 0.48)
const LEAF_PINK := Color(0.96, 0.70, 0.76)
const LEAF_GOLD := Color(0.98, 0.80, 0.45)
const STONE := Color(0.90, 0.86, 0.80)
const STONE_WARM := Color(0.93, 0.80, 0.70)
const ROCK := Color(0.62, 0.55, 0.58)
const GRASS := Color(0.62, 0.80, 0.50)
const WOOD := Color(0.78, 0.58, 0.42)
const PLASTER := Color(0.97, 0.93, 0.86)
const ROOF := Color(0.85, 0.47, 0.42)
const WATER := Color(0.48, 0.74, 0.86)
const METAL := Color(0.35, 0.36, 0.42)
const LAMP := Color(1.0, 0.86, 0.55)


static func tree(base: Vector3, height: float = 3.6, leaf: Color = LEAF, seed: int = 0) -> Array:
	var out: Array = []
	var trunk := Solid.loft(base, Solid.ngon(7, 0.16), 0.0, height * 0.7, 0.7, TRUNK, Mat.WOOD,
		Color(0, 0, 0, 0), -1, true)
	out.append(trunk)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(base) + seed
	var top := base + Vector3(0, height * 0.72, 0)
	var main_r := height * 0.32
	var crown := Solid.sphere(top, Vector3(main_r, main_r * 0.85, main_r), leaf, Mat.FOLIAGE)
	crown.collide = false
	out.append(crown)
	for i in 3:
		var a := rng.randf() * TAU
		var r := main_r * rng.randf_range(0.55, 0.75)
		var off := Vector3(cos(a), rng.randf_range(-0.3, 0.25), sin(a)) * main_r * 0.75
		var blob := Solid.sphere(top + off, Vector3(r, r * 0.85, r), leaf.lightened(rng.randf_range(-0.06, 0.08)), Mat.FOLIAGE)
		blob.collide = false
		out.append(blob)
	return out


static func bush(base: Vector3, r: float = 0.6, leaf: Color = LEAF) -> Array:
	var s := Solid.sphere(base + Vector3(0, r * 0.6, 0), Vector3(r, r * 0.75, r), leaf.darkened(0.05), Mat.FOLIAGE)
	s.collide = false
	return [s]


static func column(base: Vector3, h: float, r: float = 0.3, col: Color = STONE) -> Array:
	return [
		Solid.box(base + Vector3(0, 0.12, 0), Vector3(r * 2.6, 0.24, r * 2.6), col, Color(0, 0, 0, 0), Mat.TILE),
		Solid.loft(base, Solid.ngon(10, r), 0.24, h - 0.24, 0.92, col, Mat.PLASTER, Color(0, 0, 0, 0), -1, true),
		Solid.box(base + Vector3(0, h - 0.12, 0), Vector3(r * 2.6, 0.24, r * 2.6), col, Color(0, 0, 0, 0), Mat.TILE),
	]


## Round arch. `axis` is the direction you walk through it (X or Z).
static func arch(center: Vector3, axis: Vector3, width: float, height: float, depth: float = 0.8,
		col: Color = STONE_WARM, thick: float = 0.6) -> Array:
	var out: Array = []
	var side := Vector3.UP.cross(axis).normalized()
	var basis := Basis(side, Vector3.UP, axis.normalized())
	var r_in := width * 0.5
	var r_out := r_in + thick
	var spring := height - r_out
	# Piers.
	for sgn in [-1.0, 1.0]:
		var c: Vector3 = center + side * sgn * (r_in + thick * 0.5) + Vector3.UP * spring * 0.5
		out.append(Solid.obox(c, Vector3(thick, spring, depth), basis, col, Mat.BRICK))
	# Voussoirs: convex ring segments.
	var segs := 7
	for i in segs:
		var a0 := PI * i / segs
		var a1 := PI * (i + 1) / segs
		var poly := PackedVector2Array([
			Vector2(cos(a0), sin(a0)) * r_in, Vector2(cos(a1), sin(a1)) * r_in,
			Vector2(cos(a1), sin(a1)) * r_out, Vector2(cos(a0), sin(a0)) * r_out])
		out.append(Solid.extrude(poly, depth, Transform3D(basis, center + Vector3.UP * spring), col, Mat.BRICK))
	# Cap stone on top.
	out.append(Solid.obox(center + Vector3.UP * (height + 0.12), Vector3(r_out * 2 + 0.2, 0.24, depth + 0.1), basis, col.lightened(0.05), Mat.TILE))
	return out


## Stairs: visual steps (no collision) plus an invisible ramp to walk on.
static func stairs(start: Vector3, dir: Vector3, steps: int, width: float, rise: float = 0.25,
		run: float = 0.4, col: Color = STONE, side_col: Color = STONE_WARM) -> Array:
	var out: Array = []
	dir = Vector3(dir.x, 0, dir.z).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	var basis := Basis(side, Vector3.UP, -dir)
	for k in steps:
		var h := rise * (k + 1)
		var c := start + dir * (run * (k + 0.5)) + Vector3.UP * (h * 0.5)
		var st := Solid.obox(c, Vector3(width, h, run), basis, side_col, Mat.PLASTER, col, Mat.TILE)
		st.collide = false
		out.append(st)
	var ramp := Solid.ramp(start, dir, run * steps, width, rise * steps, col)
	ramp.visible = false
	out.append(ramp)
	return out


static func railing(a: Vector3, b: Vector3, h: float = 0.9, col: Color = WOOD) -> Array:
	var out: Array = []
	var d := b - a
	var len := d.length()
	var dir := d / len
	var basis := Basis(dir.cross(Vector3.UP).normalized(), Vector3.UP, -dir)
	var n := maxi(1, int(len / 1.2))
	for i in n + 1:
		var p := a + dir * (len * i / n)
		var post := Solid.loft(p, Solid.ngon(6, 0.05), 0.0, h, 1.0, col, Mat.WOOD, Color(0, 0, 0, 0), -1, true)
		post.collide = false
		out.append(post)
	var rail := Solid.obox(a + d * 0.5 + Vector3.UP * h, Vector3(0.09, 0.07, len), basis, col, Mat.WOOD)
	rail.collide = false
	out.append(rail)
	return out


static func lamp(base: Vector3, h: float = 2.6) -> Array:
	var pole := Solid.loft(base, Solid.ngon(6, 0.06), 0.0, h, 0.8, METAL, Mat.METAL, Color(0, 0, 0, 0), -1, true)
	pole.collide = false
	var bulb := Solid.sphere(base + Vector3(0, h + 0.15, 0), Vector3(0.2, 0.24, 0.2), LAMP, Mat.GLOW)
	bulb.collide = false
	var cap := Solid.loft(base + Vector3(0, h + 0.3, 0), Solid.ngon(6, 0.26), 0.0, 0.18, 0.15, METAL, Mat.METAL)
	cap.collide = false
	return [pole, bulb, cap]


static func bench(c: Vector3, along_x: bool = true) -> Array:
	var basis := Basis() if along_x else Basis(Vector3.UP, PI * 0.5)
	var out: Array = []
	out.append(Solid.obox(c + Vector3(0, 0.45, 0), Vector3(1.6, 0.08, 0.45), basis, WOOD, Mat.PLANKS))
	out.append(Solid.obox(c + basis * Vector3(0, 0.75, -0.2), Vector3(1.6, 0.4, 0.06), basis, WOOD, Mat.PLANKS))
	for sx in [-0.7, 0.7]:
		out.append(Solid.obox(c + basis * Vector3(sx, 0.22, 0), Vector3(0.08, 0.45, 0.4), basis, METAL, Mat.METAL))
	return out


static func planter(c: Vector3, flower: Color = LEAF_PINK) -> Array:
	var box := Solid.box(c + Vector3(0, 0.3, 0), Vector3(1.0, 0.6, 1.0), STONE_WARM, Color(0, 0, 0, 0), Mat.BRICK)
	var soil := Solid.box(c + Vector3(0, 0.62, 0), Vector3(0.84, 0.04, 0.84), Color(0.45, 0.35, 0.3), Color(0, 0, 0, 0), Mat.GRASS)
	var out: Array = [box, soil]
	out.append_array(bush(c + Vector3(0, 0.55, 0), 0.45, flower))
	return out


static func crate(c: Vector3, s: float = 0.8) -> Array:
	return [Solid.box(c + Vector3(0, s * 0.5, 0), Vector3(s, s, s), WOOD, Color(0, 0, 0, 0), Mat.WOOD)]


## A little house: plaster walls, pitched roof, door and windows.
## `front` is the direction the door faces (one of the 4 axes).
static func house(base: Vector3, size: Vector3, front: Vector3 = Vector3.BACK,
		wall: Color = PLASTER, roof: Color = ROOF) -> Array:
	var out: Array = []
	var basis := Basis.looking_at(-front, Vector3.UP)
	out.append(Solid.obox(base + Vector3(0, size.y * 0.5, 0), size, basis, wall, Mat.PLASTER))
	var hw := size.x * 0.5 + 0.25
	var rh := size.x * 0.4
	var tri := PackedVector2Array([Vector2(-hw, 0), Vector2(hw, 0), Vector2(0, rh)])
	out.append(Solid.extrude(tri, size.z + 0.4, Transform3D(basis, base + Vector3(0, size.y, 0)), roof, Mat.ROOF))
	var fz := size.z * 0.5 + 0.03
	var door := Solid.obox(base + basis * Vector3(0, 0.95, fz), Vector3(0.9, 1.9, 0.08), basis, WOOD.darkened(0.15), Mat.WOOD)
	door.collide = false
	out.append(door)
	for sx in [-size.x * 0.3, size.x * 0.3]:
		var win := Solid.obox(base + basis * Vector3(sx, size.y * 0.62, fz), Vector3(0.7, 0.7, 0.08), basis, Color(0.55, 0.72, 0.85), Mat.METAL)
		win.collide = false
		out.append(win)
	return out


## Floating island: walkable rect top (grass on rock) with a tapered rocky
## underside. `mn`/`mx` are the XZ corners of the top surface at height y.
static func island(mn: Vector2, mx: Vector2, y: float, top_mat: int = Mat.GRASS,
		top_col: Color = GRASS, depth: float = 6.0, rock: Color = ROCK) -> Array:
	var out: Array = []
	out.append(Solid.box_mm(Vector3(mn.x, y - 1.0, mn.y), Vector3(mx.x, y, mx.y), rock, top_col, Mat.ROCK, top_mat))
	var c := Vector3((mn.x + mx.x) * 0.5, y - 1.0, (mn.y + mx.y) * 0.5)
	var hx := (mx.x - mn.x) * 0.5
	var hz := (mx.y - mn.y) * 0.5
	var poly := PackedVector2Array([Vector2(-hx, -hz), Vector2(hx, -hz), Vector2(hx, hz), Vector2(-hx, hz)])
	out.append(_inverted_taper(c, poly, depth, rock))
	return out


static func _inverted_taper(c: Vector3, poly: PackedVector2Array, depth: float, rock: Color) -> Solid:
	# Rocky underside: full rect at c.y tapering to a quarter-size base far below.
	var small := PackedVector2Array()
	for p in poly:
		small.append(p * 0.25)
	var s := Solid.loft(c + Vector3(0, -depth, 0), small, 0.0, depth, 4.0, rock, Mat.ROCK)
	return s


static func water(mn: Vector2, mx: Vector2, y: float) -> Solid:
	var s := Solid.box_mm(Vector3(mn.x, y - 0.5, mn.y), Vector3(mx.x, y, mx.y), WATER, Color(0, 0, 0, 0), Mat.WATER)
	s.collide = false
	return s


## Distant scenery: a few floating islands with trees around the horizon.
static func _decor(list: Array) -> Array:
	for x in list:
		(x as Solid).collide = false
	return list


## A patch of little flowers on short leafy mounds.
static func flowers(center: Vector3, radius: float = 1.2, count: int = 9, seed: int = 0,
		palette: Array = [Color(1, 0.62, 0.72), Color(1, 0.98, 0.95), Color(1, 0.85, 0.35), Color(0.75, 0.68, 1.0)]) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(center) + seed
	for i in count:
		var a := rng.randf() * TAU
		var r := sqrt(rng.randf()) * radius
		var p := center + Vector3(cos(a) * r, 0, sin(a) * r)
		var h := rng.randf_range(0.18, 0.35)
		out.append(Solid.loft(p, Solid.ngon(5, 0.12, rng.randf() * TAU), 0.0, h * 0.6, 0.35, LEAF.darkened(0.12), Mat.FOLIAGE))
		var col: Color = palette[rng.randi() % palette.size()]
		var bloom := Solid.sphere(p + Vector3(0, h * 0.6 + 0.04, 0), Vector3(0.075, 0.05, 0.075), col, Mat.PLASTER, 0)
		bloom.faces = bloom.faces.map(func(f): f.erase("sc"); return f)
		out.append(bloom)
	return _decor(out)


## A cluster of low-poly boulders.
static func rocks(center: Vector3, count: int = 3, size: float = 0.6, seed: int = 0) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(center) + seed
	for i in count:
		var s := size * rng.randf_range(0.45, 1.0)
		var p := center + Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1)) * size
		out.append(Solid.loft(p, Solid.ngon(6, s, rng.randf() * TAU), -0.1, s * rng.randf_range(0.5, 0.9), 0.55,
			ROCK.lightened(rng.randf_range(0.0, 0.2)), Mat.ROCK))
	return _decor(out)


## White picket fence.
static func fence(a: Vector3, b: Vector3, col: Color = Color(0.97, 0.95, 0.9)) -> Array:
	var out: Array = []
	var d := b - a
	var len := d.length()
	var dir := d / len
	var basis := Basis(dir.cross(Vector3.UP).normalized(), Vector3.UP, -dir)
	var n := maxi(1, int(len / 0.35))
	for i in n + 1:
		var p := a + dir * (len * i / n)
		out.append(Solid.obox(p + Vector3(0, 0.4, 0), Vector3(0.08, 0.8, 0.04), basis, col, Mat.WOOD))
	for y in [0.25, 0.6]:
		out.append(Solid.obox(a + d * 0.5 + Vector3(0, y, 0.0), Vector3(0.04, 0.07, len), basis, col.darkened(0.05), Mat.WOOD))
	return _decor(out)


## A string of little triangle flags sagging between two points.
static func bunting(a: Vector3, b: Vector3, sag: float = 0.6, colors: Array = [Color(1, 0.6, 0.6), Color(1, 0.88, 0.5), Color(0.6, 0.8, 1.0), Color(0.7, 0.9, 0.7)]) -> Array:
	var out: Array = []
	var d := b - a
	var len := d.length()
	var dir := d / len
	var segs := maxi(4, int(len / 0.7))
	var prev := a
	for i in range(1, segs + 1):
		var t := float(i) / segs
		var p := a + d * t - Vector3.UP * sag * 4.0 * t * (1.0 - t)
		var mid := (prev + p) * 0.5
		var seg_len := prev.distance_to(p)
		var sb := Basis.looking_at(p - prev, Vector3.UP)
		out.append(Solid.obox(mid, Vector3(0.02, 0.02, seg_len), sb, Color(0.95, 0.93, 0.9), Mat.PLASTER))
		var tri := PackedVector2Array([Vector2(-0.14, 0), Vector2(0.14, 0), Vector2(0, -0.32)])
		var basis2 := Basis(dir, Vector3.UP, dir.cross(Vector3.UP).normalized())
		out.append(Solid.extrude(tri, 0.01, Transform3D(basis2, mid - Vector3.UP * 0.01), colors[i % colors.size()], Mat.PLASTER))
		prev = p
	return _decor(out)


static func stepping_stones(a: Vector3, b: Vector3, n: int = 5) -> Array:
	var out: Array = []
	for i in n:
		var p := a.lerp(b, (i + 0.5) / n) + Vector3(sin(i * 2.1) * 0.25, 0, cos(i * 1.7) * 0.15)
		out.append(Solid.loft(p, Solid.ngon(7, 0.38, i * 0.7), -0.05, 0.035, 0.95, STONE, Mat.TILE))
	return _decor(out)


## Stone coping along the top of a wall (mn/mx = the wall's box).
static func wall_trim(mn: Vector3, mx: Vector3, col: Color = STONE) -> Array:
	return _decor([Solid.box_mm(Vector3(mn.x - 0.06, mx.y, mn.z - 0.06), Vector3(mx.x + 0.06, mx.y + 0.14, mx.z + 0.06), col, Color(0, 0, 0, 0), Mat.TILE)])


## A window with frame, sill and shutters on a wall face. `out_dir` points
## away from the wall (into the street).
static func window(c: Vector3, out_dir: Vector3, w: float = 1.0, h: float = 1.3,
		shutter: Color = Color(0.55, 0.72, 0.68)) -> Array:
	var out: Array = []
	var basis := Basis.looking_at(-out_dir, Vector3.UP)
	var f := WOOD.lightened(0.35)
	out.append(Solid.obox(c, Vector3(w, h, 0.06), basis, Color(0.6, 0.76, 0.88), Mat.METAL))
	out.append(Solid.obox(c + basis * Vector3(0, h * 0.5 + 0.05, 0.04), Vector3(w + 0.2, 0.1, 0.1), basis, f, Mat.WOOD))
	out.append(Solid.obox(c + basis * Vector3(0, -h * 0.5 - 0.06, 0.08), Vector3(w + 0.3, 0.1, 0.2), basis, STONE, Mat.TILE))
	for sx in [-1.0, 1.0]:
		out.append(Solid.obox(c + basis * Vector3(sx * (w * 0.5 + 0.05), 0, 0.04), Vector3(0.1, h, 0.1), basis, f, Mat.WOOD))
		out.append(Solid.obox(c + basis * Vector3(sx * (w * 0.75 + 0.12), 0, 0.06), Vector3(w * 0.5, h, 0.05), basis, shutter, Mat.PLANKS))
	out.append(Solid.obox(c, Vector3(0.05, h, 0.08), basis, f, Mat.WOOD))
	return _decor(out)


static func potted_plant(base: Vector3, leaf: Color = LEAF) -> Array:
	var out: Array = []
	out.append(Solid.loft(base, Solid.ngon(8, 0.22), 0.0, 0.4, 1.25, Color(0.86, 0.52, 0.4), Mat.PLASTER))
	var b := Solid.sphere(base + Vector3(0, 0.62, 0), Vector3(0.32, 0.3, 0.32), leaf, Mat.FOLIAGE, 0)
	out.append(b)
	return _decor(out)


## A washing line of photos drying in the darkroom.
static func photo_line(a: Vector3, b: Vector3, sag: float = 0.3) -> Array:
	var out: Array = []
	var d := b - a
	var len := d.length()
	var dir := d / len
	var segs := maxi(3, int(len / 0.9))
	var prev := a
	var tints := [Color(0.7, 0.85, 0.95), Color(0.98, 0.8, 0.75), Color(0.8, 0.9, 0.75), Color(0.95, 0.88, 0.7)]
	var basis2 := Basis(dir, Vector3.UP, dir.cross(Vector3.UP).normalized())
	for i in range(1, segs + 1):
		var t := float(i) / segs
		var p := a + d * t - Vector3.UP * sag * 4.0 * t * (1.0 - t)
		out.append(Solid.obox((prev + p) * 0.5, Vector3(0.015, 0.015, prev.distance_to(p)), Basis.looking_at(p - prev, Vector3.UP), Color(0.9, 0.88, 0.85), Mat.PLASTER))
		var c := (prev + p) * 0.5 - Vector3.UP * 0.2
		out.append(Solid.obox(c, Vector3(0.3, 0.36, 0.01), basis2, Color(0.99, 0.98, 0.95), Mat.PLASTER))
		out.append(Solid.obox(c + Vector3.UP * 0.03 + basis2.z * 0.008, Vector3(0.25, 0.25, 0.005), basis2, tints[i % tints.size()], Mat.PLASTER))
		out.append(Solid.obox(c + Vector3.UP * 0.19, Vector3(0.04, 0.06, 0.03), basis2, WOOD, Mat.WOOD))
		prev = p
	return _decor(out)


static func horizon(center: Vector3, radius: float = 140.0, count: int = 6, seed: int = 1, scale: float = 1.0) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	for i in count:
		var a := TAU * i / count + rng.randf_range(-0.3, 0.3)
		var r := radius * rng.randf_range(0.8, 1.2)
		var p := center + Vector3(cos(a) * r, rng.randf_range(-12, 18), sin(a) * r)
		var w := rng.randf_range(10, 22) * scale
		out.append_array(island(Vector2(p.x - w, p.z - w * 0.7), Vector2(p.x + w, p.z + w * 0.7), p.y, Mat.GRASS, GRASS, w * 0.9))
		for k in rng.randi_range(1, 3):
			var tp := p + Vector3(rng.randf_range(-w * 0.6, w * 0.6), 0, rng.randf_range(-w * 0.4, w * 0.4))
			var leaf: Color = [LEAF, LEAF_PINK, LEAF_GOLD][rng.randi() % 3]
			out.append_array(tree(tp, rng.randf_range(5, 9) * maxf(scale, 0.6), leaf, k))
	for s in out:
		(s as Solid).collide = false
	return out


static func sea(center: Vector3, y: float = -40.0, size: float = 900.0) -> Solid:
	var s := water(Vector2(center.x - size, center.z - size), Vector2(center.x + size, center.z + size), y)
	return s
