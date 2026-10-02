class_name Levels
extends RefCounted
## Level data. Every surface is a convex Solid (see Props) so that the photo
## slicer can cut through everything, scenery included.
##
## Dictionary keys:
##   name, hint            : strings (the hint is also Miso's last line)
##   cat                   : { pos, yaw, lines: [String] } companion placement + dialogue
##   notes                 : [{ at, title, text }] archivist notes to read
##   spawn, yaw            : player start (yaw in degrees, 0 = facing -Z)
##   solids                : Array[Solid] (tag "source" = only exists to be photographed)
##   batteries             : Array[Vector3]
##   teleporter            : { pos: Vector3, needs: int }
##   camera, film          : whether the player owns a camera, film count (-1 = infinite)
##   found                 : [{ at, from: Transform3D, title, kind: "photo"|"sketch"|"painting" }]
##   kill_y                : falling below this triggers an automatic rewind

const P := preload("res://scripts/levels/props.gd")

const CREAM := Color(0.92, 0.88, 0.80)
const TILE_C := Color(0.90, 0.85, 0.78)
const PEACH := Color(0.94, 0.72, 0.62)
const ROSE := Color(0.90, 0.62, 0.62)
const TEAL := Color(0.52, 0.74, 0.76)
const MINT := Color(0.62, 0.80, 0.70)
const LAV := Color(0.76, 0.72, 0.90)
const BUTTER := Color(0.98, 0.86, 0.58)
const BRICK := Color(0.88, 0.62, 0.52)
const BRICK_PALE := Color(0.93, 0.80, 0.70)

## Far-away origins for scenery that only exists inside found pictures.
const SRC := Vector3(1000, 0, 0)
const SRC2 := Vector3(2000, 0, 0)

const LEVEL_COUNT := 12


const NAMES := ["Found Photograph", "Point and Shoot", "Through the Window", "Breakthrough",
	"Look Up", "Sketchbook", "Watercolour", "Darkroom",
	"Power Cut", "Two Keys", "Watchtower", "Plan Ahead"]


static func count() -> int:
	return LEVEL_COUNT


static func get_level_name(i: int) -> String:
	return "%d · %s" % [i + 1, NAMES[i]]


static func get_level(i: int) -> Dictionary:
	var lv: Dictionary
	match i:
		0: lv = _found_photograph()
		1: lv = _point_and_shoot()
		2: lv = _through_the_window()
		3: lv = _breakthrough()
		4: lv = _look_up()
		5: lv = _sketchbook()
		6: lv = _watercolour()
		7: lv = _darkroom()
		8: lv = _power_cut()
		9: lv = _two_keys()
		10: lv = _watchtower()
		11: lv = _plan_ahead()
		_: lv = _found_photograph()
	lv["backdrop"] = backdrop(lv.get("backdrop_seed", i + 3), play_bounds(lv))
	if CH1_TEXT.has(i):
		# Miso sets the scene; the solution only comes as hints you ask for.
		lv["cat"]["lines"] = CH1_TEXT[i][0]
		lv["hints"] = CH1_TEXT[i][1]
	return lv


const CH1_TEXT := {
	0: [["The bridge in this memory is gone. Someone left a photo of it on the table.", "I'd help, but I'm a cat."],
		["Walk into the photo on the table to pick it up.",
		"Tap the photo in the top-left to hold it up. It's a window into another place.",
		"Stand at the edge, look down at the gap at the same angle as the photo, and PLACE it."]],
	1: [["Ooh, a camera. The archivists' favourite toy.", "That terrace has no way up. Annoying, isn't it?"],
		["Look around. Is there anything in this courtyard that goes up?",
		"A photo of some stairs is as good as the stairs.",
		"Photograph the stairs behind you from the middle of the courtyard, turn round and place the photo against the cliff from a similar distance."]],
	2: [["The teleporter needs a battery. There's one in that cottage… which has no door. Classic Tomas."],
		["You can't get in. But your camera can look in.",
		"Anything inside a photo gets copied. Batteries too.",
		"Press right up against the window and photograph the battery, then place the photo out in the open garden."]],
	3: [["A wall. Rude."],
		["A photo doesn't only add things. It replaces everything inside its frame.",
		"What would a picture of an empty corridor do to a wall?",
		"Photograph the open terrace behind you, stand well back from the wall so the frame covers it from floor to ceiling, and place."]],
	4: [["That island is much too far to jump. Even for me."],
		["Have you been inside the tower?",
		"From the inside, looking straight up, the tower is a long tube.",
		"Stand in the middle of the tower and photograph straight up. Then stand back from the edge, look straight ahead and place it: a tunnel."]],
	5: [["Ines used to sketch here. She drew stairs everywhere."],
		["Drawings work just like photos.",
		"The sketch was drawn standing on the ground, a few steps from a cliff like this one.",
		"Pick up the sketch, stand about 5 m from the cliff, look straight ahead and place it."]],
	6: [["Tomas painted this view before the bridge washed away. Or before he forgot to build it."],
		["Paintings work like photos too.",
		"Where you stand matters: too close to the edge and the bridge starts out over thin air.",
		"Take the painting, stand a few steps back from the edge facing the far island, and place it."]],
	7: [["This was the darkroom. Every memory was developed here."],
		["Two batteries, and a high ledge. The postcard might help with one of those.",
		"Copying a battery copies everything else in the frame too. Aim down so you only take a bit of floor.",
		"Copy the battery aiming down, place the postcard about 5 m from the ledge looking straight ahead, then carry both batteries up."]],
}


## XZ rectangle covering everything you can walk on or photograph in a level
## (picture-only scenery far away at SRC is ignored).
static func play_bounds(lv: Dictionary) -> Rect2:
	var r := Rect2()
	var first := true
	for s in lv.get("solids", []):
		var b: AABB = (s as Solid).get_aabb()
		if absf(b.get_center().x) > 400.0 or b.size.x > 200.0:
			continue
		var rr := Rect2(b.position.x, b.position.z, b.size.x, b.size.z)
		r = rr if first else r.merge(rr)
		first = false
	for key in ["spawn"]:
		if lv.has(key):
			var p: Vector3 = lv[key]
			r = r.expand(Vector2(p.x, p.z))
	if lv.has("teleporter"):
		var tp: Vector3 = lv["teleporter"]["pos"]
		r = r.expand(Vector2(tp.x, tp.z))
	return r


## Scenery that is rendered but never sliced: a ring of floating city blocks
## around the play area, then islands with towers on the horizon. Nothing in
## the ring can block a view inside the play area, since it stays outside
## the (convex) play rectangle.
static func backdrop(seed: int, play: Rect2 = Rect2(-20, -20, 40, 40)) -> Array:
	var q: int = Progress.quality() if Engine.get_main_loop() != null else 2
	var s: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = seed * 7919
	var margin := 7.0
	var ctr := Vector3(play.get_center().x, 0, play.get_center().y)
	var heights := [-7.0, -4.0, -2.0, 0.0, 2.5, 5.0]
	var k := 0
	for side in 4:
		var horiz := side < 2  # districts along the -Z / +Z sides run along X
		var length := (play.size.x if horiz else play.size.y) + margin * 2.0 + 16.0
		var count := maxi(1, roundi(length / 24.0))
		if q == 0:
			count = maxi(1, count / 2)
		for i in count:
			var seg := length / count
			var ah := seg * 0.5 - rng.randf_range(1.5, 4.0)
			var dh := rng.randf_range(5.5, 8.5)
			var off := rng.randf_range(0.0, 7.0)
			var y: float = heights[rng.randi() % heights.size()]
			var t := -length * 0.5 + seg * (i + 0.5)
			var c: Vector3
			var half: Vector2
			match side:
				0: c = Vector3(ctr.x + t, y, play.position.y - margin - dh - off); half = Vector2(ah, dh)
				1: c = Vector3(ctr.x + t, y, play.end.y + margin + dh + off); half = Vector2(ah, dh)
				2: c = Vector3(play.position.x - margin - dh - off, y, ctr.z + t); half = Vector2(dh, ah)
				_: c = Vector3(play.end.x + margin + dh + off, y, ctr.z + t); half = Vector2(dh, ah)
			s.append_array(P.district(c, half, ctr, seed * 31 + k, q))
			k += 1
	var radius := maxf(play.size.x, play.size.y) * 0.5
	s.append_array(P.horizon(ctr, radius + 110.0, 7, seed))
	s.append_array(P.horizon(ctr + Vector3(0, -6, 0), radius + 55.0, 7, seed + 101, 0.5))
	return s


static func _eye(pos: Vector3, yaw_deg: float, pitch_deg: float) -> Transform3D:
	var b := Basis.from_euler(Vector3(deg_to_rad(pitch_deg), deg_to_rad(yaw_deg), 0))
	return Transform3D(b, pos)


static func _tag(list: Array, tag: String, style: int = Mat.STYLE_NORMAL) -> Array:
	for s in list:
		(s as Solid).tag = tag
		(s as Solid).style = style
	return list


static func _wall(mn: Vector3, mx: Vector3, col: Color = P.WHITE, mat: int = Mat.PLASTER) -> Solid:
	# Whitewashed walls with a pale concrete coping on top.
	return Solid.box_mm(mn, mx, col, P.CONCRETE, mat, Mat.CONCRETE)


static func _table(c: Vector3) -> Array:
	var out: Array = [Solid.box(c + Vector3(0, 0.8, 0), Vector3(1.4, 0.1, 1.0), P.WOOD, Color(0, 0, 0, 0), Mat.PLANKS)]
	for sx in [-0.6, 0.6]:
		for sz in [-0.4, 0.4]:
			out.append(Solid.box(c + Vector3(sx, 0.375, sz), Vector3(0.1, 0.75, 0.1), P.WOOD.darkened(0.1), Color(0, 0, 0, 0), Mat.WOOD))
	return out


# ---------------------------------------------------------------------------
# Hub: the Station, with a portal for each level.
# ---------------------------------------------------------------------------
static func hub() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-16, -16), Vector2(16, 16), 0.0, Mat.GRASS, P.GRASS, 10.0))
	# Central tiled plaza + fountain.
	s.append(Solid.loft(Vector3.ZERO, Solid.ngon(12, 7.0), -0.2, 0.02, 1.0, TILE_C, Mat.TILE))
	s.append(Solid.loft(Vector3.ZERO, Solid.ngon(16, 2.2), 0.0, 0.55, 1.0, P.WHITE, Mat.PLASTER, P.CONCRETE, Mat.CONCRETE))
	var basin := Solid.loft(Vector3.ZERO, Solid.ngon(12, 1.9), 0.55, 0.5, 1.0, P.WATER, Mat.WATER)
	basin.collide = false
	s.append(basin)
	# Sculpture: a white plinth holding a glowing orb inside a pastel ring.
	s.append(Solid.loft(Vector3(0, 0.55, 0), Solid.ngon(10, 0.32), 0.0, 1.5, 0.7, P.WHITE, Mat.PLASTER, Color(0, 0, 0, 0), -1, true))
	var orb := Solid.sphere(Vector3(0, 2.45, 0), Vector3(0.4, 0.4, 0.4), P.LAMP, Mat.GLOW, 2)
	orb.collide = false
	s.append(orb)
	for k in 12:
		var a0 := TAU * k / 12.0
		var seg := Solid.obox(Vector3(0, 2.45, 0) + Vector3(cos(a0), sin(a0), 0) * 0.75, Vector3(0.12, 0.42, 0.12),
			Basis(Vector3.BACK, a0), P.TEAL, Mat.PLASTER)
		seg.collide = false
		s.append(seg)
	# Ring of trees, lamps and benches.
	for i in 8:
		var a := TAU * (i + 0.5) / 8.0
		var p := Vector3(cos(a), 0, sin(a))
		s.append_array(P.tree(p * 14.6, 4.2, [P.LEAF, P.LEAF_PINK, P.LEAF_GOLD][i % 3], i))
		s.append_array(P.lamp(p * 7.6))
	s.append_array(P.house(Vector3(0, 0, 13), Vector3(6, 3.4, 3.2), Vector3.FORWARD, P.WHITE, P.CORAL, true))
	s.append_array(P.arch(Vector3(0, 0, -15), Vector3.FORWARD, 3.0, 4.2, 0.8, P.WHITE))
	s.append_array(P.house(Vector3(-12.6, 0, -12.6), Vector3(4.2, 3.2, 3.2), Vector3.RIGHT, P.WHITE, P.TEAL))
	s.append_array(P.house(Vector3(12.6, 0, -12.6), Vector3(4.2, 3.2, 3.2), Vector3.LEFT, P.WHITE, P.BUTTER))
	# Dressing.
	for i in 8:
		var a := TAU * (i + 0.5) / 8.0
		var d := Vector3(cos(a), 0, sin(a))
		s.append_array(P.flowers(d * 9.3, 1.1, 8, i))
	for i in 4:
		var a0 := TAU * (i * 2 + 0.5) / 8.0
		var a1 := TAU * (i * 2 + 1.5) / 8.0
		s.append_array(P.bunting(Vector3(cos(a0), 0, sin(a0)) * 7.6 + Vector3(0, 2.7, 0), Vector3(cos(a1), 0, sin(a1)) * 7.6 + Vector3(0, 2.7, 0), 0.5))
	s.append_array(P.stepping_stones(Vector3(0, 0, 7.2), Vector3(0, 0, 11.2), 4))
	s.append_array(P.potted_plant(Vector3(-2.4, 0, 11.1)))
	s.append_array(P.potted_plant(Vector3(2.4, 0, 11.1), P.LEAF_PINK))
	for c in [Vector3(-14.5, 0, 6), Vector3(14, 0, -3), Vector3(-13, 0, -9), Vector3(10, 0, 13.5)]:
		s.append_array(P.rocks(c, 3, 0.7))
	s.append_array(P.fence(Vector3(-15.5, 0, 9), Vector3(-15.5, 0, 15.5)))
	s.append_array(P.fence(Vector3(15.5, 0, 9), Vector3(15.5, 0, 15.5)))
	return {
		"name": "The Station",
		"hint": "Step onto a glowing pad to enter a memory.",
		"cat": {"pos": Vector3(1.9, 0.55, 0.8), "yaw": -40.0, "lines": [
			"Oh! A visitor. Welcome to the Station.",
			"The archivists kept their favourite places here… as photographs.",
			"Each pad leads into one of their memories. Bring the teleporters back to life and the Archive wakes up.",
			"I'm Miso. Pet me any time. It helps. Mostly me.",
		]},
		"notes": [{"at": Vector3(-2.6, 1.0, 2.0), "title": "Welcome note",
			"text": "To whoever finds the Station running again:\n\nWe built the Archive so places could outlive us. A photograph here is not a picture of a place — it IS the place. Hold one up, and the world will make room for it.\n\n— Ines, head archivist"}],
		"spawn": Vector3(0, 0, 4.5), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -40), "needs": 99},
		"camera": false, "film": 0,
		"found": [],
		"kill_y": -15.0,
		"is_hub": true,
		"backdrop": backdrop(42, Rect2(-16, -16, 32, 32)),
	}


## Portal pad positions in the hub (one per level). Chapter 1 fills the far
## (-Z) semicircle, chapter 2 sits on the near side either side of the house.
static func hub_pad(i: int) -> Vector3:
	var a: float
	if i < 8:
		a = PI + PI * (i + 0.5) / 8.0
	else:
		a = [0.08, 0.27, 0.73, 0.92][i - 8] * PI
	return Vector3(cos(a) * 11.5, 0.0, sin(a) * 11.5)


static func _archive(mn: Vector3, mx: Vector3) -> Solid:
	var s := Solid.box_mm(mn, mx, Color(0.32, 0.33, 0.42), Color(0, 0, 0, 0), Mat.ARCHIVE)
	s.anchored = true
	return s


## Archive-stone enclosure with an optional doorway in the north wall.
static func _archive_room(mn: Vector2, mx: Vector2, h: float, door_z: float = INF, door_w: float = 2.4, door_h: float = 3.2) -> Array:
	var s: Array = []
	var t := 0.4
	s.append(_archive(Vector3(mn.x - t, 0, mn.y - t), Vector3(mn.x, h, mx.y + t)))
	s.append(_archive(Vector3(mx.x, 0, mn.y - t), Vector3(mx.x + t, h, mx.y + t)))
	s.append(_archive(Vector3(mn.x, 0, mx.y), Vector3(mx.x, h, mx.y + t)))
	s.append(_archive(Vector3(mn.x, 0, mn.y - t), Vector3(mx.x, h, mn.y)))
	if door_z != INF:
		var hw := door_w * 0.5
		s.append(_archive(Vector3(mn.x, 0, door_z - t), Vector3(-hw, h, door_z)))
		s.append(_archive(Vector3(hw, 0, door_z - t), Vector3(mx.x, h, door_z)))
		s.append(_archive(Vector3(-hw, door_h, door_z - t), Vector3(hw, h, door_z)))
	# Someone still waters the Archive: potted plants and ferns in the corners.
	var i := 0
	for c in [Vector2(mn.x + 0.6, mn.y + 0.6), Vector2(mx.x - 0.6, mn.y + 0.6),
			Vector2(mn.x + 0.6, mx.y - 0.6), Vector2(mx.x - 0.6, mx.y - 0.6)]:
		s.append_array(P.potted_plant(Vector3(c.x, 0, c.y), P.LEAF if i % 2 == 0 else P.LEAF_PINK))
		var off := Vector3(signf(-c.x) * 0.7, 0, 0)
		s.append(ModelLib.instance(ModelLib.NATURE + "Fern_1.gltf", Vector3(c.x, 0, c.y) + off, c.x * 40.0 + c.y * 7.0, 0.7))
		i += 1
	return s


# ---------------------------------------------------------------------------
# 1. A photo you find becomes a place you can walk on.
# ---------------------------------------------------------------------------
static func _found_photograph() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-4, -4), Vector2(4, 4.5), 0.0, Mat.TILE, TILE_C, 7.0))
	s.append_array(P.arch(Vector3(0, 0, 4.25), Vector3.BACK, 2.4, 3.6, 0.5, P.STONE_WARM, 0.5))
	s.append(_wall(Vector3(-4, 0, 4.0), Vector3(-1.75, 1.3, 4.5)))
	s.append(_wall(Vector3(1.75, 0, 4.0), Vector3(4, 1.3, 4.5)))
	s.append(_wall(Vector3(-4.4, 0, -4), Vector3(-4, 1.0, 4.5)))
	s.append(_wall(Vector3(4, 0, -4), Vector3(4.4, 1.0, 4.5)))
	s.append_array(_table(Vector3(0, 0, 0.5)))
	s.append_array(P.tree(Vector3(-2.9, 0, 2.6), 3.4, P.LEAF_PINK))
	s.append_array(P.planter(Vector3(3.0, 0, 3.0), P.LEAF_GOLD))
	s.append_array(P.lamp(Vector3(-3.5, 0, -3.5)))
	s.append_array(P.lamp(Vector3(3.5, 0, -3.5)))
	# Far platform.
	s.append_array(P.island(Vector2(-4, -24), Vector2(4, -13), 0.0, Mat.TILE, TILE_C, 8.0))
	s.append_array(P.arch(Vector3(0, 0, -14), Vector3.FORWARD, 5.4, 4.6, 0.7, ROSE.lightened(0.15)))
	s.append_array(P.tree(Vector3(-3, 0, -22), 3.8, P.LEAF))
	s.append_array(P.tree(Vector3(3, 0, -22), 3.2, P.LEAF_GOLD))
	s.append(_wall(Vector3(-4, 0, -24.4), Vector3(4, 1.2, -24)))

	# The photograph's scenery: a wooden footbridge on stone piers.
	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-1.5, -0.4, -26), SRC + Vector3(1.5, 0, 2), P.WOOD, Color(0, 0, 0, 0), Mat.PLANKS))
	src.append_array(P.railing(SRC + Vector3(-1.45, 0, 2), SRC + Vector3(-1.45, 0, -26), 0.95))
	src.append_array(P.railing(SRC + Vector3(1.45, 0, 2), SRC + Vector3(1.45, 0, -26), 0.95))
	for z in [-6.0, -14.0, -22.0]:
		src.append(Solid.loft(SRC + Vector3(0, 0, z), Solid.ngon(8, 1.0), -12.0, -0.4, 0.8, P.STONE, Mat.BRICK))
	s.append_array(_tag(src, "source"))

	# Dressing.
	s.append_array(P.flowers(Vector3(-2.9, 0, 2.6), 0.9, 7))
	s.append_array(P.flowers(Vector3(-3.0, 0, -21.5), 0.8, 6))
	s.append_array(P.flowers(Vector3(3.0, 0, -21.5), 0.8, 6, 3))
	s.append_array(P.potted_plant(Vector3(3.3, 0, -14.8), P.LEAF_PINK))
	s.append_array(P.potted_plant(Vector3(-3.3, 0, -14.8)))
	s.append_array(P.bunting(Vector3(-3.5, 2.55, -3.5), Vector3(3.5, 2.55, -3.5), 0.5))
	s.append_array(P.wall_trim(Vector3(-4.4, 0, -4), Vector3(-4, 1.0, 4.5)))
	s.append_array(P.wall_trim(Vector3(4, 0, -4), Vector3(4.4, 1.0, 4.5)))
	s.append_array(P.potted_plant(Vector3(-3.4, 1.14, 0.5), P.LEAF_GOLD))
	return {
		"name": "1 · Found Photograph",
		"hint": "Walk into the polaroid, tap it (top-left) to hold it up, line it up with the gap, then PLACE.",
		"cat": {"pos": Vector3(1.6, 0, 2.2), "yaw": -150.0, "lines": [
			"The bridge in this memory is gone. But someone left a photo of it on the table.",
			"Pick it up, hold it up and line it up with the gap. Then place it.",
			"Whatever is in a photo becomes real. Don't overthink it. I never do.",
		]},
		"notes": [],
		"spawn": Vector3(0, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -19), "needs": 0},
		"camera": false, "film": 0,
		"found": [{"at": Vector3(0, 1.25, 0.5), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, -20), "title": "Old footbridge", "kind": "photo"}],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 2. Take your own photo of some stairs, turn around, paste it on a cliff.
# ---------------------------------------------------------------------------
static func _point_and_shoot() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-6, -1, -40), Vector3(6, 0, 30), CREAM, TILE_C, Mat.ROCK, Mat.TILE))
	# Town walls on both sides with windows and a cornice.
	for sx in [-1.0, 1.0]:
		var x0: float = 6.0 * sx
		s.append(_wall(Vector3(minf(x0, x0 + 0.5 * sx), 0, -40), Vector3(maxf(x0, x0 + 0.5 * sx), 7, 30), BRICK_PALE))
		s.append(Solid.box_mm(Vector3(minf(x0 - 0.15 * sx, x0 + 0.6 * sx), 6.6, -40), Vector3(maxf(x0 - 0.15 * sx, x0 + 0.6 * sx), 7.0, 30), P.STONE, Color(0, 0, 0, 0), Mat.TILE))
		for z in [-8.0, -2.0, 4.0, 10.0]:
			var w := Solid.box(Vector3(x0 - 0.04 * sx, 3.4, z), Vector3(0.08, 1.4, 1.0), Color(0.56, 0.72, 0.86), Color(0, 0, 0, 0), Mat.METAL)
			w.collide = false
			s.append(w)
	# Teleporter cliff (no way up) — a raised garden terrace.
	s.append(Solid.box_mm(Vector3(-6, 0, -40), Vector3(6, 4, -14), P.STONE_WARM, P.GRASS, Mat.BRICK, Mat.GRASS))
	s.append_array(P.tree(Vector3(-4, 4, -36), 3.5, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(4, 4, -36), 3.0, P.LEAF))
	# Look-alike terrace behind the start, with stairs. Dead end.
	s.append_array(P.stairs(Vector3(0, 0, 14), Vector3.BACK, 16, 3.0, 0.25, 0.375))
	s.append(Solid.box_mm(Vector3(-6, 0, 20), Vector3(6, 4, 30), P.STONE_WARM, P.GRASS, Mat.BRICK, Mat.GRASS))
	s.append_array(P.tree(Vector3(-4, 4, 26), 3.5, P.LEAF_GOLD))
	s.append_array(P.tree(Vector3(4, 4, 26), 3.0, P.LEAF))
	s.append_array(P.planter(Vector3(-4.5, 0, 8)))
	s.append_array(P.planter(Vector3(4.5, 0, -6)))
	s.append_array(P.bench(Vector3(-4.6, 0, 1), false))
	# Dressing: shuttered windows, strings of flags across the street, plants.
	for z in [-8.0, -2.0, 4.0, 10.0]:
		s.append_array(P.window(Vector3(-5.92, 3.4, z), Vector3.RIGHT, 1.0, 1.3, Color(0.55, 0.72, 0.68)))
		s.append_array(P.window(Vector3(5.92, 3.4, z), Vector3.LEFT, 1.0, 1.3, Color(0.9, 0.62, 0.6)))
	for z in [-10.0, -4.0, 2.0, 8.0]:
		s.append_array(P.bunting(Vector3(-5.9, 5.9, z), Vector3(5.9, 5.9, z + 1.5), 0.8))
	s.append_array(P.potted_plant(Vector3(-5.3, 0, -12.5)))
	s.append_array(P.potted_plant(Vector3(5.3, 0, 12.5), P.LEAF_PINK))
	s.append_array(P.facade(-6.0, 1.0, -13.0, 13.0, 6.6, [-8.0, -2.0, 4.0, 10.0], 21))
	s.append_array(P.facade(6.0, -1.0, -13.0, 13.0, 6.6, [-8.0, -2.0, 4.0, 10.0], 22))
	s.append_array(P.flowers(Vector3(0, 4, -32), 3.0, 14))
	s.append_array(P.flowers(Vector3(0, 4, 24), 3.0, 14, 5))
	return {
		"name": "2 · Point and Shoot",
		"hint": "Tap CAM, frame the stairs behind you, press SNAP. Then face the cliff and PLACE it.",
		"cat": {"pos": Vector3(2.2, 0, 0.5), "yaw": 160.0, "lines": [
			"Ooh, you found a camera! The archivists' favourite toy.",
			"Those stairs behind us lead nowhere. But the terrace ahead has no stairs at all…",
			"Take a picture of the stairs, then hold it up against the cliff.",
		]},
		"notes": [{"at": Vector3(-4.6, 0.6, 1.6), "title": "Field log #2",
			"text": "Tested the instant camera in the courtyard today. Took a picture of the east steps and put them on the west wall. The building did not mind.\n\nNote for Ines: please stop putting stairs on my ceiling.\n— Tomas"}],
		"spawn": Vector3(0, 0, 2), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 4, -27), "needs": 0},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 3. Photograph a battery through a window to make your own copy.
# ---------------------------------------------------------------------------
static func _through_the_window() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-14, -14), Vector2(14, 14), 0.0, Mat.GRASS, P.GRASS, 9.0))
	# Sealed cottage: x [-3.4, 3.4], z [-12.8, -6]
	var wall := BRICK
	s.append(_wall(Vector3(-3.4, 0, -6.4), Vector3(-0.8, 3.6, -6.0), wall))
	s.append(_wall(Vector3(0.8, 0, -6.4), Vector3(3.4, 3.6, -6.0), wall))
	s.append(_wall(Vector3(-0.8, 0, -6.4), Vector3(0.8, 1.0, -6.0), wall))
	s.append(_wall(Vector3(-0.8, 2.2, -6.4), Vector3(0.8, 3.6, -6.0), wall))
	s.append(_wall(Vector3(-3.4, 0, -12.8), Vector3(3.4, 3.6, -12.4), PEACH, Mat.PLASTER))
	s.append(_wall(Vector3(-3.4, 0, -12.4), Vector3(-3.0, 3.6, -6.4), PEACH, Mat.PLASTER))
	s.append(_wall(Vector3(3.0, 0, -12.4), Vector3(3.4, 3.6, -6.4), PEACH, Mat.PLASTER))
	s.append(Solid.box_mm(Vector3(-3.0, 0.0, -12.4), Vector3(3.0, 0.02, -6.4), P.WOOD, Color(0, 0, 0, 0), Mat.PLANKS))
	var tri := PackedVector2Array([Vector2(-3.9, 0), Vector2(3.9, 0), Vector2(0, 2.4)])
	s.append(Solid.extrude(tri, 7.4, Transform3D(Basis(), Vector3(0, 3.6, -9.4)), P.ROOF, Mat.ROOF))
	# Window sill + frame details (outside, below the opening).
	s.append(Solid.box_mm(Vector3(-1.0, 0.92, -6.0), Vector3(1.0, 1.0, -5.8), P.STONE, Color(0, 0, 0, 0), Mat.TILE))
	s.append(Solid.box_mm(Vector3(-0.6, 0, -10.6), Vector3(0.6, 0.5, -9.4), BUTTER, Color(0, 0, 0, 0), Mat.WOOD))
	# Garden.
	s.append_array(P.tree(Vector3(-8, 0, 8), 4.0, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(-10, 0, -4), 3.6, P.LEAF))
	s.append_array(P.tree(Vector3(10, 0, 10), 4.4, P.LEAF_GOLD))
	s.append_array(P.tree(Vector3(-9, 0, -11), 3.2, P.LEAF))
	s.append_array(P.bush(Vector3(-4.5, 0, -6.5)))
	s.append_array(P.bush(Vector3(4.5, 0, -6.5)))
	s.append_array(P.lamp(Vector3(-6, 0, 3)))
	s.append_array(P.bench(Vector3(-6, 0, 6)))
	for x in range(-12, 13, 3):
		s.append_array(P.bush(Vector3(x, 0, 13), 0.7, P.LEAF.darkened(0.05)))
	# Dressing.
	for sx in [-1.0, 1.0]:
		var sh := Solid.box(Vector3(sx * 1.15, 1.6, -5.97), Vector3(0.6, 1.3, 0.05), Color(0.55, 0.72, 0.68), Color(0, 0, 0, 0), Mat.PLANKS)
		sh.collide = false
		s.append(sh)
	s.append_array(P.flowers(Vector3(-2.2, 0, -5.4), 0.6, 6))
	s.append_array(P.flowers(Vector3(2.2, 0, -5.4), 0.6, 6, 2))
	s.append_array(P.flowers(Vector3(-8, 0, 8), 1.5, 10))
	s.append_array(P.flowers(Vector3(10, 0, 10), 1.5, 10, 4))
	s.append_array(P.flowers(Vector3(-10, 0, -4), 1.2, 8, 6))
	s.append_array(P.stepping_stones(Vector3(0, 0, -1.2), Vector3(0, 0, -5.2), 4))
	s.append_array(P.fence(Vector3(-13.5, 0, 12.2), Vector3(-4, 0, 12.2)))
	s.append_array(P.fence(Vector3(4, 0, 12.2), Vector3(13.5, 0, 12.2)))
	for c in [Vector3(-13, 0, -13), Vector3(13, 0, -12), Vector3(12.5, 0, 4)]:
		s.append_array(P.rocks(c, 3, 0.7))
	s.append_array(P.potted_plant(Vector3(-6.9, 0, 6.7), P.LEAF_PINK))
	return {
		"name": "3 · Through the Window",
		"hint": "Press right up against the window and photograph the battery inside. Then PLACE the photo in open space.",
		"cat": {"pos": Vector3(-1.5, 0, -3.5), "yaw": 30.0, "lines": [
			"The teleporter needs a battery. There's one in the cottage… which has no door. Classic Tomas.",
			"Here's a secret: anything inside a photo gets copied. Batteries too.",
			"Squish your face against the window and take a picture.",
		]},
		"notes": [],
		"spawn": Vector3(0, 0, 0), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(0, 0.8, -10)],
		"teleporter": {"pos": Vector3(8, 0, 1), "needs": 1},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 4. Placing a photo of nothing cuts a hole.
# ---------------------------------------------------------------------------
static func _breakthrough() -> Dictionary:
	var s: Array = []
	var w := LAV
	s.append(Solid.box_mm(Vector3(-2, -1, -26), Vector3(2, 0, 10), CREAM, TILE_C, Mat.ROCK, Mat.TILE))
	s.append(_wall(Vector3(-2.4, -1, -26), Vector3(-2, 4, 10), w, Mat.PLASTER))
	s.append(_wall(Vector3(2, -1, -26), Vector3(2.4, 4, 10), w, Mat.PLASTER))
	s.append(_wall(Vector3(-2.4, 4, -26), Vector3(2.4, 4.4, 10), P.WOOD, Mat.PLANKS))
	s.append(_wall(Vector3(-2.4, -1, -26.4), Vector3(2.4, 4.4, -26), PEACH, Mat.PLASTER))
	# Ceiling beams and wall lamps.
	for z in range(-24, 10, 4):
		var beam := Solid.box(Vector3(0, 3.9, z), Vector3(4.0, 0.2, 0.25), P.WOOD.darkened(0.15), Color(0, 0, 0, 0), Mat.WOOD)
		beam.collide = false
		s.append(beam)
		var lampl := Solid.sphere(Vector3(-1.9, 2.8, z + 2), Vector3(0.14, 0.18, 0.14), P.LAMP, Mat.GLOW)
		lampl.collide = false
		s.append(lampl)
	# The blocking wall.
	s.append(_wall(Vector3(-2, 0, -8), Vector3(2, 4, -6), BRICK))
	# Open terrace behind the start.
	s.append(Solid.box_mm(Vector3(-2, -1, 10), Vector3(2, 0, 34), P.ROCK, P.GRASS, Mat.ROCK, Mat.GRASS))
	for z in [14.0, 20.0, 26.0, 32.0]:
		s.append_array(P.column(Vector3(-1.7, 0, z), 1.6, 0.25, BUTTER))
		s.append_array(P.column(Vector3(1.7, 0, z), 1.6, 0.25, BUTTER))
	# Dressing: framed pictures and plants along the hall, flowers on the terrace.
	for z in [-22.0, -16.0, -12.0, 2.0, 6.0]:
		for sx in [-1.0, 1.0]:
			var fr := Solid.box(Vector3(1.97 * sx, 2.3, z), Vector3(0.04, 0.9, 1.2), P.WOOD.darkened(0.2), Color(0, 0, 0, 0), Mat.WOOD)
			fr.collide = false
			s.append(fr)
			var pic := Solid.box(Vector3(1.95 * sx, 2.3, z), Vector3(0.03, 0.7, 1.0), [ROSE, TEAL, BUTTER, MINT][(int(z) + 30) % 4], Color(0, 0, 0, 0), Mat.PLASTER)
			pic.collide = false
			s.append(pic)
	s.append_array(P.potted_plant(Vector3(-1.6, 0, 8.6)))
	s.append_array(P.potted_plant(Vector3(1.6, 0, -24.6), P.LEAF_PINK))
	s.append_array(P.flowers(Vector3(-1.2, 0, 22), 0.6, 6))
	s.append_array(P.flowers(Vector3(1.2, 0, 29), 0.6, 6, 1))
	return {
		"name": "4 · Breakthrough",
		"hint": "Photograph the open terrace, stand well back from the wall, and PLACE. A photo replaces everything in its frame.",
		"cat": {"pos": Vector3(1.3, 0, -3.5), "yaw": 140.0, "lines": [
			"A wall. Rude.",
			"A photo doesn't just add things. It replaces everything inside its frame.",
			"So… what if you took a picture of nothing in particular?",
		]},
		"notes": [],
		"spawn": Vector3(0, 0, -1), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -19), "needs": 0},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 5. A vertical tower photographed from below becomes a horizontal tunnel.
# ---------------------------------------------------------------------------
static func _look_up() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-7, -6), Vector2(7, 8), 0.0, Mat.GRASS, P.GRASS, 8.0))
	s.append_array(P.island(Vector2(-5, -34), Vector2(5, -18), 0.0, Mat.TILE, TILE_C, 8.0))
	s.append(_wall(Vector3(-5, 0, -34.4), Vector3(5, 3, -34), PEACH, Mat.PLASTER))
	s.append_array(P.arch(Vector3(0, 0, -33.6), Vector3.FORWARD, 2.6, 3.8, 0.6))
	# Tower centred on (3.5, 3.5), interior half-width 1.5 (= eye height).
	var cx := 3.5
	var cz := 3.5
	var h := 40.0
	var t := 0.3
	s.append(_wall(Vector3(cx - 1.5 - t, 0, cz - 1.5 - t), Vector3(cx + 1.5 + t, h, cz - 1.5), Color(0.66, 0.80, 0.84)))
	s.append(_wall(Vector3(cx - 1.5 - t, 0, cz + 1.5), Vector3(cx + 1.5 + t, h, cz + 1.5 + t), Color(0.72, 0.86, 0.72)))
	s.append(_wall(Vector3(cx + 1.5, 0, cz - 1.5), Vector3(cx + 1.5 + t, h, cz + 1.5), Color(0.98, 0.86, 0.62)))
	# West wall has a doorway at the bottom.
	s.append(_wall(Vector3(cx - 1.5 - t, 2.4, cz - 1.5), Vector3(cx - 1.5, h, cz + 1.5), LAV))
	s.append(_wall(Vector3(cx - 1.5 - t, 0, cz - 1.5), Vector3(cx - 1.5, 2.4, cz - 0.6), LAV))
	s.append(_wall(Vector3(cx - 1.5 - t, 0, cz + 0.6), Vector3(cx - 1.5, 2.4, cz + 1.5), LAV))
	# Crenellations on top.
	for i in 4:
		var a := Vector3([-1.2, 1.2, -1.2, 1.2][i], 0, [-1.2, -1.2, 1.2, 1.2][i])
		s.append(Solid.box(Vector3(cx, h + 0.4, cz) + a, Vector3(0.8, 0.8, 0.8), P.STONE, Color(0, 0, 0, 0), Mat.BRICK))
	s.append_array(P.tree(Vector3(-4.5, 0, 5), 3.6, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(-5.5, 0, -3.5), 3.0, P.LEAF))
	s.append_array(P.lamp(Vector3(-3, 0, -5.2)))
	s.append_array(P.tree(Vector3(-3.5, 0, -30), 3.4, P.LEAF_GOLD))
	s.append_array(P.tree(Vector3(3.5, 0, -30), 3.4, P.LEAF))
	# Dressing.
	s.append_array(P.flowers(Vector3(-4.5, 0, 5), 1.1, 8))
	s.append_array(P.flowers(Vector3(-5.5, 0, -3.5), 1.0, 7, 2))
	s.append_array(P.rocks(Vector3(6, 0, 7), 3, 0.6))
	s.append_array(P.rocks(Vector3(-6.3, 0, 7), 2, 0.5))
	s.append_array(P.flowers(Vector3(-3.5, 0, -30), 1.0, 7, 3))
	s.append_array(P.flowers(Vector3(3.5, 0, -30), 1.0, 7, 4))
	s.append_array(P.bunting(Vector3(-3, 2.5, -5.2), Vector3(1.7, 6.0, 1.7), 0.6))
	return {
		"name": "5 · Look Up",
		"hint": "Stand in the middle of the tower and look straight up. A tunnel is just a tower lying down. Stand back from the edge to PLACE.",
		"cat": {"pos": Vector3(-1.5, 0, 1.5), "yaw": -60.0, "lines": [
			"That island is much too far to jump. Even for me.",
			"Have you looked up inside the tower? It's a long, long tube.",
			"I wonder what a tube looks like… lying down.",
		]},
		"notes": [],
		"spawn": Vector3(-2, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -28), "needs": 0},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 6. A pencil sketch: the stairs it shows become real — still in pencil.
# ---------------------------------------------------------------------------
static func _sketchbook() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-8, -14), Vector2(8, 8), 0.0, Mat.GRASS, P.GRASS, 8.0))
	s.append(Solid.box_mm(Vector3(-8, 0, -40), Vector3(8, 7, -14), P.STONE_WARM, P.GRASS, Mat.BRICK, Mat.GRASS))
	s.append_array(P.island(Vector2(-8, -40), Vector2(8, -14), 0.0, Mat.ROCK, P.ROCK, 9.0))
	s.append_array(P.tree(Vector3(-5, 7, -36), 3.4, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(5, 7, -37), 3.0, P.LEAF))
	s.append_array(P.house(Vector3(-5, 0, 3), Vector3(4, 3, 3), Vector3.RIGHT, PEACH.lightened(0.2)))
	s.append_array(P.tree(Vector3(5.5, 0, 4.5), 3.5, P.LEAF_GOLD))
	s.append_array(P.bush(Vector3(5, 0, -10)))
	# Easel with the sketch.
	s.append(Solid.box(Vector3(0, 0.6, 5.2), Vector3(0.1, 1.2, 0.1), P.WOOD, Color(0, 0, 0, 0), Mat.WOOD))
	s.append(Solid.box(Vector3(0, 1.0, 5.1), Vector3(1.0, 0.08, 0.2), P.WOOD, Color(0, 0, 0, 0), Mat.WOOD))

	# The drawing: a stone staircase climbing the cliff (in pencil).
	var src: Array = []
	src.append(Solid.box_mm(SRC2 + Vector3(-8, -1, -40), SRC2 + Vector3(8, 0, 4), CREAM, Color(0, 0, 0, 0), Mat.TILE))
	src.append_array(P.stairs(SRC2 + Vector3(0, 0, -5), Vector3.FORWARD, 28, 3.0, 0.25, 0.45))
	src.append(Solid.box_mm(SRC2 + Vector3(-8, 0, -40), SRC2 + Vector3(8, 7, -17.6), CREAM, Color(0, 0, 0, 0), Mat.BRICK))
	src.append_array(P.railing(SRC2 + Vector3(-1.5, 0, -5), SRC2 + Vector3(-1.5, 7, -17.6), 0.9))
	src.append_array(P.railing(SRC2 + Vector3(1.5, 0, -5), SRC2 + Vector3(1.5, 7, -17.6), 0.9))
	src.append_array(P.column(SRC2 + Vector3(-2.2, 7, -19), 2.4, 0.3))
	src.append_array(P.column(SRC2 + Vector3(2.2, 7, -19), 2.4, 0.3))
	s.append_array(_tag(src, "source", Mat.STYLE_SKETCH))
	# Dressing.
	s.append_array(P.flowers(Vector3(5.5, 0, 4.5), 1.2, 9))
	s.append_array(P.flowers(Vector3(-5, 7, -36), 1.0, 8, 2))
	s.append_array(P.fence(Vector3(-7.6, 0, 7.6), Vector3(7.6, 0, 7.6)))
	s.append_array(P.rocks(Vector3(6.5, 0, -12), 3, 0.7))
	s.append_array(P.rocks(Vector3(-6.5, 0, -2), 2, 0.6))
	s.append_array(P.potted_plant(Vector3(-2.8, 0, 2.0), P.LEAF_GOLD))
	return {
		"name": "6 · Sketchbook",
		"hint": "Pick up the sketch from the easel. Stand about 5 m from the cliff, look straight ahead and PLACE it.",
		"cat": {"pos": Vector3(1.5, 0, 3.0), "yaw": -120.0, "lines": [
			"Ines used to sketch here. She drew stairs everywhere. Even on the cliff that never had any.",
			"A drawing works just like a photo. It stays a drawing, though. Very stylish.",
		]},
		"notes": [{"at": Vector3(-2.6, 0.9, 5.2), "title": "Sketchbook margin",
			"text": "If the Archive can hold photographs, why not drawings? A drawing is a place someone hoped for.\n\nTried it this morning. The stairs are still made of pencil. I climbed them anyway.\n— Ines"}],
		"spawn": Vector3(0, 0, 3), "yaw": 180.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 7, -32), "needs": 0},
		"camera": false, "film": 0,
		"found": [{"at": Vector3(0, 1.45, 5.15), "from": _eye(SRC2 + Vector3(0, 1.5, 0), 0, 0), "title": "Pencil sketch", "kind": "sketch"}],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 7. A watercolour painting of a bridge across a river gorge.
# ---------------------------------------------------------------------------
static func _watercolour() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-7, -6), Vector2(7, 8), 0.0, Mat.GRASS, P.GRASS, 14.0))
	s.append_array(P.island(Vector2(-7, -32), Vector2(7, -18), 0.0, Mat.GRASS, P.GRASS, 14.0))
	s.append(P.water(Vector2(-30, -20), Vector2(30, -4), -10.0))
	s.append_array(P.tree(Vector3(-5, 0, 5), 3.8, P.LEAF))
	s.append_array(P.tree(Vector3(5.5, 0, 6), 3.4, P.LEAF_PINK))
	s.append_array(P.house(Vector3(4.5, 0, 0), Vector3(3.4, 3, 3), Vector3.LEFT))
	s.append_array(P.tree(Vector3(-5, 0, -28), 4.0, P.LEAF_GOLD))
	s.append_array(P.tree(Vector3(5, 0, -27), 3.6, P.LEAF))
	s.append_array(P.lamp(Vector3(-2.2, 0, -19)))
	s.append_array(P.lamp(Vector3(2.2, 0, -19)))
	s.append(Solid.box(Vector3(-3, 0.6, 5.0), Vector3(0.1, 1.2, 0.1), P.WOOD, Color(0, 0, 0, 0), Mat.WOOD))
	s.append(Solid.box(Vector3(-3, 1.0, 4.9), Vector3(1.0, 0.08, 0.2), P.WOOD, Color(0, 0, 0, 0), Mat.WOOD))

	# The painting: a stone arch bridge over a river, in watercolour.
	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-7, -1, -3.5), SRC + Vector3(7, 0, 4), P.GRASS, Color(0, 0, 0, 0), Mat.GRASS))
	src.append(Solid.box_mm(SRC + Vector3(-2, -0.6, -40), SRC + Vector3(2, 0, -3.5), P.STONE_WARM, TILE_C, Mat.BRICK, Mat.TILE))
	src.append_array(P.railing(SRC + Vector3(-1.9, 0, -3.5), SRC + Vector3(-1.9, 0, -40), 0.8, P.STONE))
	src.append_array(P.railing(SRC + Vector3(1.9, 0, -3.5), SRC + Vector3(1.9, 0, -40), 0.8, P.STONE))
	for z in [-9.0, -17.0, -25.0, -33.0]:
		src.append(Solid.loft(SRC + Vector3(0, 0, z), Solid.ngon(8, 1.4), -14.0, -0.6, 0.85, P.STONE_WARM, Mat.BRICK))
	src.append(P.water(Vector2(SRC.x - 30, -40), Vector2(SRC.x + 30, -4), -10.0))
	src.append_array(P.tree(SRC + Vector3(-5, 0, 2), 3.5, P.LEAF_PINK))
	s.append_array(_tag(src, "source", Mat.STYLE_PAINT))
	# Dressing.
	s.append_array(P.flowers(Vector3(-5, 0, 5), 1.2, 9))
	s.append_array(P.flowers(Vector3(5.5, 0, 6), 1.0, 8, 2))
	s.append_array(P.flowers(Vector3(-5, 0, -28), 1.2, 9, 3))
	s.append_array(P.rocks(Vector3(-6.4, 0, -5.4), 3, 0.6))
	s.append_array(P.rocks(Vector3(6.4, 0, -18.6), 3, 0.6))
	s.append_array(P.fence(Vector3(-6.8, 0, 7.6), Vector3(6.8, 0, 7.6)))
	s.append_array(P.bunting(Vector3(-2.2, 2.6, -19), Vector3(2.2, 2.6, -19), 0.4))
	return {
		"name": "7 · Watercolour",
		"hint": "Take the painting from the easel. Stand a few steps back from the edge, face the far island and PLACE it.",
		"cat": {"pos": Vector3(1.2, 0, 3.6), "yaw": -160.0, "lines": [
			"Tomas painted this view before the bridge washed away. Or before he forgot to build it. Hard to say.",
			"Paintings stay paintings. I think it's prettier that way.",
		]},
		"notes": [],
		"spawn": Vector3(0, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -25), "needs": 0},
		"camera": false, "film": 0,
		"found": [{"at": Vector3(-3, 1.45, 4.85), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, 0), "title": "River painting", "kind": "painting"}],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 8. Everything together, with limited film.
# ---------------------------------------------------------------------------
static func _darkroom() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-10, -1, -40), Vector3(10, 0, 10), P.WOOD, P.WOOD, Mat.ROCK, Mat.PLANKS))
	s.append(Solid.box_mm(Vector3(-10, 0, -40), Vector3(10, 6, -12), BRICK_PALE, TILE_C, Mat.BRICK, Mat.TILE))
	s.append(_wall(Vector3(-10.4, 0, -40), Vector3(-10, 8, 10), LAV, Mat.PLASTER))
	s.append(_wall(Vector3(10, 0, -40), Vector3(10.4, 8, 10), LAV, Mat.PLASTER))
	s.append(_wall(Vector3(-10, 0, 9.6), Vector3(10, 8, 10), LAV, Mat.PLASTER))
	# Framed pictures on the walls.
	for z in [-6.0, 0.0, 6.0]:
		for sx in [-1.0, 1.0]:
			var fr := Solid.box(Vector3(9.95 * sx, 3.2, z), Vector3(0.06, 1.6, 2.2), P.WOOD.darkened(0.2), Color(0, 0, 0, 0), Mat.WOOD)
			fr.collide = false
			s.append(fr)
			var pic := Solid.box(Vector3(9.9 * sx, 3.2, z), Vector3(0.06, 1.3, 1.9), [ROSE, TEAL, BUTTER][(int(z) + 6) / 6 % 3], Color(0, 0, 0, 0), Mat.PLASTER)
			pic.collide = false
			s.append(pic)
	# Rug + plinth for the battery.
	s.append(Solid.box_mm(Vector3(4.5, 0, 0.5), Vector3(7.5, 0.05, 3.5), ROSE, Color(0, 0, 0, 0), Mat.PLASTER))
	s.append(Solid.box_mm(Vector3(5.6, 0, 1.6), Vector3(6.4, 0.4, 2.4), BUTTER, Color(0, 0, 0, 0), Mat.WOOD))
	s.append(Solid.box_mm(Vector3(-2, 0, 5), Vector3(2, 0.8, 6), P.STONE, Color(0, 0, 0, 0), Mat.TILE))
	s.append_array(P.planter(Vector3(-8.5, 0, 8.3)))
	s.append_array(P.planter(Vector3(8.5, 0, 8.3), P.LEAF_GOLD))

	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-10, -1, -40), SRC + Vector3(10, 0, 4), P.WOOD, Color(0, 0, 0, 0), Mat.PLANKS))
	src.append_array(P.stairs(SRC + Vector3(0, 0, -5), Vector3.FORWARD, 24, 4.0, 0.25, 0.375))
	src.append(Solid.box_mm(SRC + Vector3(-10, 0, -40), SRC + Vector3(10, 6, -14), BRICK_PALE, TILE_C, Mat.BRICK, Mat.TILE))
	src.append(_wall(SRC + Vector3(-10.4, 0, -40), SRC + Vector3(-10, 8, 4), LAV, Mat.PLASTER))
	src.append(_wall(SRC + Vector3(10, 0, -40), SRC + Vector3(10.4, 8, 4), LAV, Mat.PLASTER))
	s.append_array(_tag(src, "source", Mat.STYLE_SEPIA))
	# Dressing: photos drying on lines, plants, a desk.
	s.append_array(P.photo_line(Vector3(-9.8, 5.2, 7.0), Vector3(9.8, 5.2, 7.0), 0.4))
	s.append_array(P.photo_line(Vector3(-9.8, 5.0, -4.0), Vector3(9.8, 5.0, -2.0), 0.4))
	s.append_array(P.potted_plant(Vector3(-9.3, 0, -10.8)))
	s.append_array(P.potted_plant(Vector3(9.3, 0, -10.8), P.LEAF_PINK))
	var desk: Array = _table(Vector3(-7, 0, 2))
	for d in desk:
		(d as Solid).collide = false
	s.append_array(desk)
	for k in 3:
		var paper := Solid.obox(Vector3(-7.3 + k * 0.3, 0.86, 2.0 + k * 0.1), Vector3(0.3, 0.01, 0.38), Basis(Vector3.UP, k * 0.3), Color(0.99, 0.98, 0.95), Mat.PLASTER)
		paper.collide = false
		s.append(paper)
	return {
		"name": "8 · Darkroom",
		"hint": "Two batteries, three shots. Copy one by aiming DOWN at it — a photo replaces everything in its frame, all the way to the horizon. Hold REWIND to undo.",
		"cat": {"pos": Vector3(-1.5, 0, 2.0), "yaw": 30.0, "lines": [
			"This was the darkroom. The archivists developed every memory here.",
			"Two batteries this time, and only three shots of film. Aim down when you copy something, or you'll copy the whole room.",
			"And if it all goes wrong, hold REWIND. I won't tell anyone.",
		]},
		"notes": [{"at": Vector3(2.6, 1.0, 5.5), "title": "Darkroom rules",
			"text": "1. Film is precious. Think before you shoot.\n2. A photo takes EVERYTHING in its frame, all the way to the horizon. Aim carefully.\n3. Do not photograph the cat. She multiplies.\n— management"}],
		"spawn": Vector3(0, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(6, 0.75, 2)],
		"teleporter": {"pos": Vector3(0, 6, -30), "needs": 2},
		"camera": true, "film": 2,
		"found": [{"at": Vector3(0, 1.5, 5.5), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, 0), "title": "Old postcard", "kind": "photo"}],
		"kill_y": -15.0,
		"backdrop_seed": 0,
	}


# ===========================================================================
# Chapter 2 — the Archive's deeper rooms. Archive stone can't be photographed,
# so these puzzles can't be bypassed by cutting through walls.
# ===========================================================================

# ---------------------------------------------------------------------------
# 9. The only battery is behind a gate that needs a battery.
# ---------------------------------------------------------------------------
static func _power_cut() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-8, -1, -22.4), Vector3(8, 0, 8.4), CREAM, TILE_C, Mat.ROCK, Mat.TILE))
	s.append_array(P.island(Vector2(-8.4, -22.8), Vector2(8.4, 8.8), -1.0, Mat.ROCK, P.ROCK, 9.0))
	s.append_array(_archive_room(Vector2(-8, -22), Vector2(8, 8), 5.0, -8.0))
	s.append(Solid.box_mm(Vector3(-0.5, 0, -11.5), Vector3(0.5, 0.5, -10.5), BUTTER, Color(0, 0, 0, 0), Mat.WOOD))
	s.append_array(P.planter(Vector3(-6.8, 0, 6.8)))
	s.append_array(P.planter(Vector3(6.8, 0, 6.8), P.LEAF_GOLD))
	s.append_array(P.lamp(Vector3(-6.8, 0, -6.6)))
	s.append_array(P.potted_plant(Vector3(6.8, 0, -20.8), P.LEAF_PINK))
	s.append_array(P.potted_plant(Vector3(-6.8, 0, -20.8)))
	s.append_array(P.flowers(Vector3(-5, 0, 1), 1.2, 8))
	return {
		"name": "9 · Power Cut",
		"hint": "",
		"cat": {"pos": Vector3(-1.6, 0, 4.0), "yaw": 20.0, "lines": [
			"The deep Archive. See the dark stone? Photos can't touch it. Can't even see it.",
			"The gate needs power. The teleporter needs power. And there's one battery… on the wrong side.",
		]},
		"hints": [
			"The gate is just light. Your camera can see straight through it.",
			"A photo of the battery gives you a battery. But careful where you place it: a photo deletes everything inside its frame, including the original.",
			"Photograph the battery through the gate, place the photo facing sideways (not towards the gate), plug the copy into the socket, then copy the original once more inside.",
		],
		"notes": [{"at": Vector3(5.5, 1.1, 6.0), "title": "Maintenance memo",
			"text": "Reminder: the vault gate draws from the socket by the door. If you take the battery out, the gate shuts. If you are inside when it shuts, that is your problem.\n— Facilities"}],
		"spawn": Vector3(0, 0, 5), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(0, 0.8, -11)],
		"sockets": [{"id": 0, "pos": Vector3(4, 0, -6.5), "cable_to": Vector3(1.3, 0, -8)}],
		"gates": [{"pos": Vector3(0, 0, -8.2), "size": Vector3(2.4, 3.2, 0.4), "needs": [0]}],
		"teleporter": {"pos": Vector3(0, 0, -17), "needs": 2},
		"camera": true, "film": 2,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 10. Three batteries needed, one battery, one shot of film — and a copier.
# ---------------------------------------------------------------------------
static func _two_keys() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-9, -1, -26.4), Vector3(9, 0, 9.4), CREAM, TILE_C, Mat.ROCK, Mat.TILE))
	s.append_array(P.island(Vector2(-9.4, -26.8), Vector2(9.4, 9.8), -1.0, Mat.ROCK, P.ROCK, 9.0))
	s.append_array(_archive_room(Vector2(-9, -26), Vector2(9, 9), 5.0, -10.0))
	s.append(Solid.box_mm(Vector3(-5.5, 0, 3.5), Vector3(-4.5, 0.5, 4.5), BUTTER, Color(0, 0, 0, 0), Mat.WOOD))
	s.append(Solid.box_mm(Vector3(-7, 0, 1), Vector3(-3, 0.04, 7), ROSE, Color(0, 0, 0, 0), Mat.PLASTER))
	s.append_array(P.potted_plant(Vector3(-8, 0, 8)))
	s.append_array(P.potted_plant(Vector3(8, 0, 8), P.LEAF_GOLD))
	s.append_array(P.lamp(Vector3(-8, 0, -8.6)))
	s.append_array(P.lamp(Vector3(8, 0, -8.6)))
	s.append_array(P.flowers(Vector3(0, 0, -22), 1.5, 10))
	return {
		"name": "10 · Two Keys",
		"hint": "",
		"cat": {"pos": Vector3(1.5, 0, 6.0), "yaw": -30.0, "lines": [
			"Two sockets on the gate, one on the teleporter. That's three batteries.",
			"We have one battery, one shot of film… and a photocopier. Tomas loved that thing.",
		]},
		"hints": [
			"Count it out: one photo of one battery only gets you to two.",
			"A photocopier copies a photo — and everything that's in it.",
			"Photograph the battery (aim down), hold the photo up at the copier and COPY it, then place both photos. Three batteries.",
		],
		"notes": [],
		"spawn": Vector3(0, 0, 6.5), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(-5, 0.8, 4)],
		"sockets": [
			{"id": 0, "pos": Vector3(-4, 0, -8.5), "cable_to": Vector3(-1.3, 0, -10)},
			{"id": 1, "pos": Vector3(4, 0, -8.5), "cable_to": Vector3(1.3, 0, -10)},
		],
		"gates": [{"pos": Vector3(0, 0, -10.2), "size": Vector3(2.4, 3.2, 0.4), "needs": [0, 1]}],
		"copiers": [{"pos": Vector3(5, 0, 4), "yaw": 0.0}],
		"teleporter": {"pos": Vector3(0, 0, -18), "needs": 1},
		"camera": true, "film": 1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 11. The right photo has to be taken from the right height.
# ---------------------------------------------------------------------------
static func _watchtower() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-10, -10), Vector2(26, 10), 0.0, Mat.GRASS, P.GRASS, 9.0))
	# Archive cliff with the teleporter on top.
	s.append(_archive(Vector3(-10, 0, -30), Vector3(10, 6, -10)))
	s.append_array(P.island(Vector2(-10, -30), Vector2(10, -10), 0.0, Mat.ROCK, P.ROCK, 9.0))
	# The overlook: a floating terrace you can see but not reach.
	s.append(Solid.box_mm(Vector3(16, 5, -14), Vector3(28, 6, 2), P.STONE_WARM, TILE_C, Mat.BRICK, Mat.TILE))
	s.append(Solid.loft(Vector3(22, 5, -6), PackedVector2Array([Vector2(-6, -8), Vector2(6, -8), Vector2(6, 8), Vector2(-6, 8)]), -4.0, 0.0, 1.0, P.ROCK, Mat.ROCK))
	s.append_array(P.stairs(Vector3(22, 6, 0), Vector3.FORWARD, 24, 3.0, 0.25, 0.375))
	s.append(Solid.box_mm(Vector3(19, 11, -14), Vector3(25, 12, -9), P.STONE_WARM, TILE_C, Mat.BRICK, Mat.TILE))
	s.append_array(P.column(Vector3(22, 6, -11.5), 5.0, 0.6))
	s.append_array(P.tree(Vector3(17.5, 6, -12), 3.0, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(26.5, 6, -3), 2.8, P.LEAF))
	s.append_array(P.flowers(Vector3(-6, 0, 6), 1.4, 10))
	s.append_array(P.rocks(Vector3(8, 0, 8), 3, 0.6))
	return {
		"name": "11 · Watchtower",
		"hint": "",
		"cat": {"pos": Vector3(2, 0, 7), "yaw": 160.0, "lines": [
			"The archivists left two cameras out here. One on the grass, one up on that tall mast.",
			"You can't take your own photos in this memory. Choose wisely… or rewind. I won't judge.",
		]},
		"hints": [
			"A photo remembers where the camera was. Placed from your eyes, things in it keep the same height relative to you.",
			"The stairs on the overlook start 1.5 m below the tall mast's camera. That's exactly how far your eyes are from the ground.",
			"Press the button at the foot of the tall mast. Stand about 5 m from the cliff, face it, look straight ahead and PLACE. Bring the battery up with you.",
		],
		"notes": [],
		"spawn": Vector3(0, 0, 7), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(23.8, 6.3, 1)],
		"fixed_cameras": [
			{"base": Vector3(22, 0, 6), "eye": _eye(Vector3(22, 7.5, 6), 0, 0)},
			{"base": Vector3(9, 0, -4), "eye": _eye(Vector3(9, 1.5, -4), -75, 12)},
		],
		"teleporter": {"pos": Vector3(0, 6, -20), "needs": 1},
		"camera": false, "film": 0,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 12. One bridge, two gaps and a cliff 2.6 m higher than you.
# ---------------------------------------------------------------------------
static func _plan_ahead() -> Dictionary:
	var s: Array = []
	s.append_array(P.island(Vector2(-6, -4), Vector2(6, 8), 0.0, Mat.GRASS, P.GRASS, 8.0))
	s.append_array(P.island(Vector2(-6, -24), Vector2(6, -12), 0.0, Mat.GRASS, P.GRASS, 8.0))
	s.append(_archive(Vector3(-7, -6, -48), Vector3(7, 2.6, -35)))
	s.append(Solid.box_mm(Vector3(-7, 2.6, -48), Vector3(7, 2.62, -35), P.GRASS, Color(0, 0, 0, 0), Mat.GRASS))
	s.append_array(_table(Vector3(-3, 0, 4)))
	s.append_array(P.tree(Vector3(-4.5, 0, 6.5), 3.4, P.LEAF_PINK))
	s.append_array(P.tree(Vector3(4.5, 0, -22), 3.2, P.LEAF))
	s.append_array(P.tree(Vector3(-5, 2.6, -46), 3.6, P.LEAF_GOLD))
	s.append_array(P.flowers(Vector3(-4, 0, -14), 1.2, 8))
	s.append_array(P.flowers(Vector3(3, 2.6, -44), 1.5, 9))
	s.append_array(P.lamp(Vector3(3.5, 0, -3)))

	# The photo: a plain stone causeway (no railings — you'll want to step off it).
	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-1.5, -0.4, -32), SRC + Vector3(1.5, 0, 2), P.STONE_WARM, TILE_C, Mat.BRICK, Mat.TILE))
	for x in [-1.45, 1.45]:
		var curb := Solid.box_mm(SRC + Vector3(x - 0.05, 0, -32), SRC + Vector3(x + 0.05, 0.15, 2), P.STONE, Color(0, 0, 0, 0), Mat.TILE)
		curb.collide = false
		src.append(curb)
	s.append_array(_tag(src, "source"))
	return {
		"name": "12 · Plan Ahead",
		"hint": "",
		"cat": {"pos": Vector3(1.5, 0, 5.5), "yaw": -150.0, "lines": [
			"Two gaps, one photograph. And that last cliff is taller than you.",
			"Photos get used up when you place them. Just saying.",
		]},
		"hints": [
			"Before you place anything: is there a way to have more than one of that photo?",
			"Holding a photo tilted up makes whatever's in it tilt up too. A bridge can become a ramp.",
			"COPY the photo first. Place one level across the first gap, then on the middle island tilt your view about 10° up and place the second as a ramp to the cliff top.",
		],
		"notes": [],
		"spawn": Vector3(0, 0, 6), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"copiers": [{"pos": Vector3(3.5, 0, 4.5), "yaw": -90.0}],
		"teleporter": {"pos": Vector3(4, 2.62, -41), "needs": 0},
		"camera": false, "film": 0,
		"found": [{"at": Vector3(-3, 1.25, 4), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, 0), "title": "Causeway", "kind": "photo"}],
		"kill_y": -15.0,
	}
