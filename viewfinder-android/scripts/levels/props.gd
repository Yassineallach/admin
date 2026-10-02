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
## Viewfinder-ish palette: whitewash, pale concrete, glass and pastel accents.
const WHITE := Color(0.97, 0.96, 0.93)
const CONCRETE := Color(0.86, 0.84, 0.82)
const GLASS := Color(0.50, 0.70, 0.78)
const CORAL := Color(0.97, 0.66, 0.58)
const TEAL := Color(0.42, 0.74, 0.74)
const BUTTER := Color(0.98, 0.84, 0.50)
const LILAC := Color(0.74, 0.66, 0.92)
const ACCENTS := [CORAL, TEAL, BUTTER, LILAC]
const BLOSSOM := Color(1.0, 0.64, 0.80)
const BLOSSOM_LILAC := Color(0.80, 0.66, 1.0)
const AUTUMN := Color(1.0, 0.74, 0.40)


static func tree(base: Vector3, height: float = 3.6, leaf: Color = LEAF, seed: int = 0) -> Array:
	# Quaternius stylized trees. Pink and gold "leaf" colours become blossom /
	# autumn canopies (the same models with repainted leaves); green groves mix
	# in the odd pine.
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(base) + seed
	var name := "CommonTree_%d" % (1 + rng.randi() % 5)
	var tint := Color(0, 0, 0, 0)
	if leaf == LEAF_PINK:
		tint = BLOSSOM if rng.randf() < 0.7 else BLOSSOM_LILAC
	elif leaf == LEAF_GOLD:
		tint = AUTUMN
	elif rng.randf() < 0.25:
		name = "Pine_%d" % (1 + rng.randi() % 3)
	var path := ModelLib.NATURE + name + ".gltf"
	var model_h := ModelLib.aabb(path).size.y
	var sc := height / maxf(model_h, 0.1) * 1.25
	var out: Array = [ModelLib.instance(path, base, rng.randf() * 360.0, sc, tint)]
	var trunk := Solid.loft(base, Solid.ngon(7, 0.22 * sc * 1.6), 0.0, 2.2, 0.8, TRUNK, Mat.WOOD)
	trunk.visible = false
	out.append(trunk)
	return out

static func bush(base: Vector3, r: float = 0.6, leaf: Color = LEAF) -> Array:
	var name := "Bush_Common_Flowers" if leaf != LEAF else "Bush_Common"
	return [ModelLib.instance(ModelLib.NATURE + name + ".gltf", base, fposmod(base.x * 37.0 + base.z * 11.0, 360.0), r / 0.95)]

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
		out.append(Solid.obox(c, Vector3(thick, spring, depth), basis, col, Mat.PLASTER))
	# Voussoirs: convex ring segments.
	var segs := 7
	for i in segs:
		var a0 := PI * i / segs
		var a1 := PI * (i + 1) / segs
		var poly := PackedVector2Array([
			Vector2(cos(a0), sin(a0)) * r_in, Vector2(cos(a1), sin(a1)) * r_in,
			Vector2(cos(a1), sin(a1)) * r_out, Vector2(cos(a0), sin(a0)) * r_out])
		out.append(Solid.extrude(poly, depth, Transform3D(basis, center + Vector3.UP * spring), col, Mat.PLASTER))
	# Cap stone on top.
	out.append(Solid.obox(center + Vector3.UP * (height + 0.12), Vector3(r_out * 2 + 0.2, 0.24, depth + 0.1), basis, CONCRETE, Mat.CONCRETE))
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
	# Slim white pole with a ring collar and a glowing globe.
	var pole := Solid.loft(base, Solid.ngon(8, 0.07), 0.0, h, 0.7, WHITE, Mat.PLASTER, Color(0, 0, 0, 0), -1, true)
	pole.collide = false
	var foot := Solid.loft(base, Solid.ngon(8, 0.2), 0.0, 0.25, 0.6, CONCRETE, Mat.CONCRETE)
	foot.collide = false
	var collar := Solid.loft(base + Vector3(0, h - 0.05, 0), Solid.ngon(10, 0.2), 0.0, 0.08, 1.0, TEAL, Mat.PLASTER)
	collar.collide = false
	var bulb := Solid.sphere(base + Vector3(0, h + 0.2, 0), Vector3(0.22, 0.22, 0.22), LAMP, Mat.GLOW)
	bulb.collide = false
	return [pole, foot, collar, bulb]


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
	soil.collide = false
	var name := "Flower_3_Group" if flower == LEAF_PINK else "Flower_4_Group"
	return [box, soil, ModelLib.instance(ModelLib.NATURE + name + ".gltf", c + Vector3(0, 0.62, 0), c.x * 40.0, 0.38)]

static func crate(c: Vector3, s: float = 0.8) -> Array:
	var col := Solid.box(c + Vector3(0, s * 0.5, 0), Vector3(s, s, s), WOOD, Color(0, 0, 0, 0), Mat.WOOD)
	col.visible = false
	return [col, ModelLib.instance(ModelLib.VILLAGE + "Prop_Crate.gltf", c, c.x * 30.0, s / 1.06)]

## A whitewashed brutalist / solarpunk building: plinth, white block, thick
## concrete roof slab with a garden and solar panels, a pastel door under a
## canopy, a round window, glass slot windows and hanging vines.
## `front` is the direction the door faces (one of the 4 axes). With `tall`
## a cantilevered glass-fronted upper storey sits on top.
static func house(base: Vector3, size: Vector3, front: Vector3 = Vector3.BACK,
		wall: Color = WHITE, accent: Color = Color(0, 0, 0, 0), tall: bool = false) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(base)
	if accent.a == 0.0:
		accent = ACCENTS[rng.randi() % ACCENTS.size()]
	if wall.r < 0.95:
		wall = wall.lerp(WHITE, 0.6)  # pastel-tinted whitewash
	var yaw := atan2(front.x, front.z)
	var basis := Basis(Vector3.UP, yaw)
	var w := size.x
	var d := size.z
	var h := size.y
	var at := func(local: Vector3) -> Vector3: return base + basis * local
	out.append(Solid.obox(at.call(Vector3(0, 0.15, 0)), Vector3(w + 0.3, 0.3, d + 0.3), basis, CONCRETE, Mat.CONCRETE))
	out.append(Solid.obox(at.call(Vector3(0, h * 0.5, 0)), Vector3(w, h, d), basis, wall, Mat.PLASTER))
	out.append(Solid.obox(at.call(Vector3(0, h + 0.15, 0)), Vector3(w + 0.6, 0.3, d + 0.6), basis, CONCRETE, Mat.CONCRETE))
	var band := Solid.obox(at.call(Vector3(0, h - 0.18, 0)), Vector3(w + 0.04, 0.22, d + 0.04), basis, accent, Mat.PLASTER)
	band.collide = false
	out.append(band)
	var fz := d * 0.5
	# Door + canopy, off-centre so the round window fits beside it.
	var door_x := -w * 0.22
	out.append_array(_decor([
		Solid.obox(at.call(Vector3(door_x, 1.05, fz + 0.03)), Vector3(1.0, 2.1, 0.08), basis, accent, Mat.PLASTER),
		Solid.obox(at.call(Vector3(door_x, 1.05, fz + 0.02)), Vector3(1.2, 2.25, 0.05), basis, CONCRETE, Mat.CONCRETE),
		Solid.obox(at.call(Vector3(door_x + 0.3, 1.0, fz + 0.09)), Vector3(0.06, 0.25, 0.06), basis, METAL, Mat.METAL),
		Solid.obox(at.call(Vector3(door_x, 2.4, fz + 0.45)), Vector3(1.8, 0.12, 0.9), basis, CONCRETE, Mat.CONCRETE),
	]))
	# Round window.
	var r := minf(0.65, h * 0.2)
	var win_c := Vector3(w * 0.22, h * 0.55, fz)
	var xf := Transform3D(basis, at.call(win_c + Vector3(0, 0, 0.04)))
	out.append_array(_decor([
		Solid.extrude(Solid.ngon(16, r + 0.14), 0.08, xf, CONCRETE, Mat.CONCRETE),
		Solid.extrude(Solid.ngon(16, r), 0.1, Transform3D(basis, at.call(win_c + Vector3(0, 0, 0.06))), GLASS, Mat.GLASS),
	]))
	# Glass slot windows with white fins on the sides and back.
	for side in [[Vector3(w * 0.5, 0, 0), PI * 0.5, d], [Vector3(-w * 0.5, 0, 0), -PI * 0.5, d], [Vector3(0, 0, -fz), PI, w]]:
		var sb := basis * Basis(Vector3.UP, side[1])
		var span: float = side[2]
		var n := maxi(1, int(span / 1.6))
		for k in n:
			var along := (k - (n - 1) * 0.5) * 1.6
			var c: Vector3 = base + basis * (side[0] as Vector3) + sb * Vector3(along, h * 0.52, 0.04)
			out.append_array(_decor([
				Solid.obox(c, Vector3(0.55, h * 0.5, 0.06), sb, GLASS, Mat.GLASS),
				Solid.obox(c + sb * Vector3(0.38, 0, 0.06), Vector3(0.1, h * 0.62, 0.16), sb, wall, Mat.PLASTER),
				Solid.obox(c + sb * Vector3(-0.38, 0, 0.06), Vector3(0.1, h * 0.62, 0.16), sb, wall, Mat.PLASTER),
			]))
	var roof_y := h + 0.3
	if tall and w >= 4.0:
		# Cantilevered upper storey: hangs off one side, glass across the front.
		var uw := w * 0.6
		var ud := d * 0.75
		var ux := w * 0.3
		out.append(Solid.obox(at.call(Vector3(ux, roof_y + 1.1, 0)), Vector3(uw, 2.2, ud), basis, wall, Mat.PLASTER))
		out.append(Solid.obox(at.call(Vector3(ux, roof_y + 2.35, 0)), Vector3(uw + 0.5, 0.3, ud + 0.5), basis, CONCRETE, Mat.CONCRETE))
		out.append_array(_decor([
			Solid.obox(at.call(Vector3(ux, roof_y + 1.15, ud * 0.5 + 0.03)), Vector3(uw - 0.5, 1.1, 0.06), basis, GLASS, Mat.GLASS),
			Solid.obox(at.call(Vector3(ux, roof_y + 2.12, ud * 0.5 + 0.02)), Vector3(uw + 0.02, 0.18, 0.06), basis, accent, Mat.PLASTER),
		]))
		# Solar panels on the very top.
		for k in 2:
			out.append_array(_solar(at.call(Vector3(ux + (k - 0.5) * uw * 0.45, roof_y + 2.5, 0)), basis))
		# Garden on the remaining roof.
		out.append_array(_roof_garden(at.call(Vector3(-w * 0.3, roof_y, 0)), basis, w * 0.38, d * 0.8))
	else:
		out.append_array(_solar(at.call(Vector3(w * 0.22, roof_y, -d * 0.1)), basis))
		out.append_array(_roof_garden(at.call(Vector3(-w * 0.22, roof_y, 0)), basis, w * 0.4, d * 0.8))
	# Vines spill over the front edge; potted plants flank the door.
	for vx in [-w * 0.42, w * 0.38]:
		out.append(ModelLib.instance(ModelLib.VILLAGE + "Prop_Vine%d.gltf" % [1, 5, 6][rng.randi() % 3],
			at.call(Vector3(vx, h + 0.1, fz + 0.32)), rad_to_deg(yaw), 0.9))
	out.append_array(potted_plant(at.call(Vector3(door_x - 0.95, 0.3, fz + 0.45)), LEAF))
	return out


## A tilted solar panel on two little legs.
static func _solar(c: Vector3, basis: Basis) -> Array:
	var tilt := basis * Basis(Vector3.RIGHT, deg_to_rad(-25))
	return _decor([
		Solid.obox(c + Vector3(0, 0.45, 0), Vector3(1.3, 0.05, 0.9), tilt, METAL, Mat.SOLAR, Color(0, 0, 0, 0), Mat.SOLAR),
		Solid.obox(c + basis * Vector3(0, 0.2, 0.25), Vector3(0.08, 0.4, 0.08), basis, METAL, Mat.METAL),
		Solid.obox(c + basis * Vector3(0, 0.35, -0.25), Vector3(0.08, 0.7, 0.08), basis, METAL, Mat.METAL),
	])


## Grass bed with bushes and flowers on a flat roof.
static func _roof_garden(c: Vector3, basis: Basis, w: float, d: float) -> Array:
	var out: Array = []
	out.append(Solid.obox(c + Vector3(0, 0.15, 0), Vector3(w, 0.3, d), basis, CONCRETE, Mat.CONCRETE, GRASS, Mat.GRASS))
	out.append_array(bush(c + Vector3(0, 0.3, 0) + basis * Vector3(-w * 0.2, 0, d * 0.15), 0.55, LEAF))
	out.append_array(bush(c + Vector3(0, 0.3, 0) + basis * Vector3(w * 0.25, 0, -d * 0.2), 0.45, LEAF_PINK))
	out.append(ModelLib.instance(ModelLib.NATURE + "Grass_Common_Tall.gltf", c + Vector3(0, 0.3, 0) + basis * Vector3(w * 0.2, 0, d * 0.25), c.x * 17.0, 0.5))
	return _decor(out)


## Floating island: walkable rect top (grass on rock) with a tapered rocky
## underside. `mn`/`mx` are the XZ corners of the top surface at height y.
static func island(mn: Vector2, mx: Vector2, y: float, top_mat: int = Mat.GRASS,
		top_col: Color = GRASS, depth: float = 6.0, rock: Color = ROCK, scatter: bool = true) -> Array:
	var out: Array = []
	out.append(Solid.box_mm(Vector3(mn.x, y - 1.0, mn.y), Vector3(mx.x, y, mx.y), rock, top_col, Mat.ROCK, top_mat))
	var c := Vector3((mn.x + mx.x) * 0.5, y - 1.0, (mn.y + mx.y) * 0.5)
	var hx := (mx.x - mn.x) * 0.5
	var hz := (mx.y - mn.y) * 0.5
	var poly := PackedVector2Array([Vector2(-hx, -hz), Vector2(hx, -hz), Vector2(hx, hz), Vector2(-hx, hz)])
	out.append(_inverted_taper(c, poly, depth, rock))
	if top_mat == Mat.GRASS and scatter:
		out.append_array(grass_tufts(mn, mx, y))
	return out


## Scattered grass tufts and the odd fern / mushroom on a grassy top.
static func grass_tufts(mn: Vector2, mx: Vector2, y: float, density: float = 0.12) -> Array:
	var out: Array = []
	var q: int = Progress.quality() if Engine.get_main_loop() != null else 2
	var area := (mx.x - mn.x) * (mx.y - mn.y)
	var n := mini(int(area * density * [0.0, 0.5, 1.0][q]), 90)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(mn) + hash(mx)
	var names := ["Grass_Common_Short", "Grass_Common_Short", "Grass_Wispy_Short", "Grass_Common_Tall", "Clover_1", "Fern_1", "Mushroom_Common"]
	for i in n:
		var p := Vector3(rng.randf_range(mn.x + 0.4, mx.x - 0.4), y - 0.02, rng.randf_range(mn.y + 0.4, mx.y - 0.4))
		var name: String = names[rng.randi() % names.size()]
		var sc := 0.45
		if name == "Fern_1":
			sc = 0.12
		elif name == "Mushroom_Common":
			sc = 0.5
		out.append(ModelLib.instance(ModelLib.NATURE + name + ".gltf", p, rng.randf() * 360.0, sc * rng.randf_range(0.8, 1.25)))
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
		palette: Array = []) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(center) + seed
	var names := ["Flower_3_Group", "Flower_4_Group", "Flower_3_Single", "Clover_1", "Grass_Common_Short", "Plant_7"]
	var n := maxi(2, count / 2)
	for i in n:
		var a := rng.randf() * TAU
		var r := sqrt(rng.randf()) * radius
		var p := center + Vector3(cos(a) * r, 0, sin(a) * r)
		var name: String = names[rng.randi() % names.size()]
		var sc := 0.36 if name.begins_with("Flower") else 0.5
		out.append(ModelLib.instance(ModelLib.NATURE + name + ".gltf", p, rng.randf() * 360.0, sc * rng.randf_range(0.8, 1.2)))
	return out

## A cluster of low-poly boulders.
static func rocks(center: Vector3, count: int = 3, size: float = 0.6, seed: int = 0) -> Array:
	var out: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(center) + seed
	for i in count:
		var p := center + Vector3(rng.randf_range(-1, 1), -0.05, rng.randf_range(-1, 1)) * Vector3(size, 1, size)
		var name := "Rock_Medium_%d" % (1 + rng.randi() % 3)
		out.append(ModelLib.instance(ModelLib.NATURE + name + ".gltf", p, rng.randf() * 360.0, size / 3.0 * rng.randf_range(0.6, 1.1)))
	return out

## White picket fence.
static func fence(a: Vector3, b: Vector3, col: Color = Color(0.97, 0.95, 0.9)) -> Array:
	var out: Array = []
	var dvec := b - a
	var len := dvec.length()
	var dir := dvec / len
	var yaw := rad_to_deg(atan2(-dir.z, dir.x))
	var n := maxi(1, int(round(len / 2.05)))
	for i in n:
		var p := a + dir * (len * (i + 0.5) / n)
		out.append(ModelLib.instance(ModelLib.VILLAGE + "Prop_WoodenFence_Single.gltf", p, yaw, len / n / 2.06))
	return out

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
		var p := a.lerp(b, (i + 0.5) / n) + Vector3(sin(i * 2.1) * 0.25, 0.01, cos(i * 1.7) * 0.15)
		out.append(ModelLib.instance(ModelLib.NATURE + "RockPath_Round_Small_%d.gltf" % [1, 1, 1][i % 3], p, i * 50.0, 0.7))
	return out

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
	(out[0] as Solid).collide = false
	var name := "Plant_1" if leaf == LEAF else "Flower_3_Single"
	out.append(ModelLib.instance(ModelLib.NATURE + name + ".gltf", base + Vector3(0, 0.38, 0), base.x * 23.0, 0.45 if name == "Plant_1" else 0.3))
	return out

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
		out.append_array(island(Vector2(p.x - w, p.z - w * 0.7), Vector2(p.x + w, p.z + w * 0.7), p.y, Mat.GRASS, GRASS, w * 0.9, ROCK, false))
		# Whitewashed buildings and slender towers on the far islands.
		if rng.randf() < 0.75:
			var bp := p + Vector3(rng.randf_range(-w * 0.4, w * 0.1), 0, rng.randf_range(-w * 0.3, w * 0.2))
			var face: Vector3 = (center - bp) * Vector3(1, 0, 1)
			face = Vector3(signf(face.x), 0, 0) if absf(face.x) > absf(face.z) else Vector3(0, 0, signf(face.z))
			out.append_array(house(bp, Vector3(w * 0.5, w * 0.35, w * 0.35), face, WHITE, ACCENTS[rng.randi() % 4], true))
		if rng.randf() < 0.5:
			out.append_array(tower(p + Vector3(w * 0.6, 0, -w * 0.3), rng.randf_range(12, 24) * scale, ACCENTS[rng.randi() % 4]))
		for k in rng.randi_range(1, 3):
			var tp := p + Vector3(rng.randf_range(-w * 0.6, w * 0.6), 0, rng.randf_range(-w * 0.4, w * 0.4))
			var leaf: Color = [LEAF, LEAF_PINK, LEAF_GOLD][rng.randi() % 3]
			out.append_array(tree(tp, rng.randf_range(5, 9) * maxf(scale, 0.6), leaf, k))
	for s in out:
		(s as Solid).collide = false
	return out


## Slender retro-futurist tower: white shaft, pastel rings, glass crown.
static func tower(base: Vector3, h: float, accent: Color = TEAL) -> Array:
	var r := maxf(0.8, h * 0.06)
	var out: Array = []
	out.append(Solid.loft(base, Solid.ngon(12, r), 0.0, h, 0.75, WHITE, Mat.PLASTER, Color(0, 0, 0, 0), -1, true))
	for k in 3:
		var y := h * (0.35 + 0.2 * k)
		var rr := r * (1.0 - 0.25 * (y / h)) + 0.35
		out.append(Solid.loft(base + Vector3(0, y, 0), Solid.ngon(12, rr), 0.0, 0.35, 1.0, accent if k != 1 else WHITE, Mat.PLASTER))
	out.append(Solid.loft(base + Vector3(0, h, 0), Solid.ngon(12, r * 1.5), 0.0, r * 1.2, 0.6, GLASS, Mat.GLASS))
	out.append(Solid.loft(base + Vector3(0, h + r * 1.2, 0), Solid.ngon(12, r * 0.95), 0.0, 0.3, 0.2, WHITE, Mat.PLASTER))
	return _decor(out)


static func sea(center: Vector3, y: float = -40.0, size: float = 900.0) -> Solid:
	var s := water(Vector2(center.x - size, center.z - size), Vector2(center.x + size, center.z + size), y)
	return s
