class_name Levels
extends RefCounted
## Level data. Each level is built procedurally from convex Solids so that the
## photo slicer can cut every surface.
##
## Dictionary keys:
##   name, hint            : strings shown in the HUD
##   spawn, yaw            : player start (yaw in degrees, 0 = facing -Z)
##   solids                : Array[Solid] (tag "source" = only exists to be photographed)
##   batteries             : Array[Vector3]
##   teleporter            : { pos: Vector3, needs: int }
##   camera, film          : whether the player owns a camera, film count (-1 = infinite)
##   found                 : [{ at: Vector3, from: Transform3D, title: String }]
##   kill_y                : falling below this triggers an automatic rewind

const CREAM := Color(0.86, 0.80, 0.73)
const SAND := Color(0.90, 0.85, 0.77)
const PEACH := Color(0.94, 0.69, 0.60)
const ROSE := Color(0.84, 0.55, 0.60)
const TEAL := Color(0.40, 0.66, 0.68)
const MINT := Color(0.58, 0.78, 0.68)
const LAV := Color(0.73, 0.69, 0.88)
const BUTTER := Color(0.98, 0.86, 0.55)
const STONE := Color(0.80, 0.79, 0.80)
const SKYBLUE := Color(0.62, 0.80, 0.93)

## Far-away origin for scenery that only exists inside found photographs.
const SRC := Vector3(1000, 0, 0)


static func count() -> int:
	return 6


static func get_level(i: int) -> Dictionary:
	match i:
		0: return _found_photograph()
		1: return _point_and_shoot()
		2: return _through_the_window()
		3: return _breakthrough()
		4: return _look_up()
		5: return _darkroom()
	return _found_photograph()


static func _eye(pos: Vector3, yaw_deg: float, pitch_deg: float) -> Transform3D:
	var b := Basis.from_euler(Vector3(deg_to_rad(pitch_deg), deg_to_rad(yaw_deg), 0))
	return Transform3D(b, pos)


static func _tag(list: Array, tag: String) -> Array:
	for s in list:
		(s as Solid).tag = tag
	return list


static func _pillar(x: float, z: float, h: float, col: Color) -> Solid:
	return Solid.box_mm(Vector3(x - 0.3, 0, z - 0.3), Vector3(x + 0.3, h, z + 0.3), col)


# ---------------------------------------------------------------------------
# 1. A photo you find becomes a place you can walk on.
# ---------------------------------------------------------------------------
static func _found_photograph() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-4, -1, -4), Vector3(4, 0, 4.5), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-4, 0, 4), Vector3(4, 3.5, 4.5), PEACH))
	s.append(Solid.box_mm(Vector3(-4.4, 0, -4), Vector3(-4, 1.0, 4.5), PEACH))
	s.append(Solid.box_mm(Vector3(4, 0, -4), Vector3(4.4, 1.0, 4.5), PEACH))
	s.append(Solid.box_mm(Vector3(-0.7, 0, 0.0), Vector3(0.7, 0.8, 1.0), LAV))  # pedestal
	# Far platform.
	s.append(Solid.box_mm(Vector3(-4, -1, -24), Vector3(4, 0, -13), CREAM, SAND))
	s.append(_pillar(-3.4, -14, 3, ROSE))
	s.append(_pillar(3.4, -14, 3, ROSE))
	s.append(Solid.box_mm(Vector3(-3.7, 3, -14.3), Vector3(3.7, 3.5, -13.7), ROSE))
	s.append(Solid.box_mm(Vector3(-4, 0, -24.5), Vector3(4, 4, -24), PEACH))

	# The photograph's scenery: a railed bridge.
	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-1.5, -1, -26), SRC + Vector3(1.5, 0, 2), TEAL, MINT))
	src.append(Solid.box_mm(SRC + Vector3(-1.7, 0, -26), SRC + Vector3(-1.5, 0.9, 2), BUTTER))
	src.append(Solid.box_mm(SRC + Vector3(1.5, 0, -26), SRC + Vector3(1.7, 0.9, 2), BUTTER))
	for z in [-6.0, -12.0, -18.0]:
		src.append(Solid.box_mm(SRC + Vector3(-1.8, -3, z - 0.3), SRC + Vector3(-1.5, 0, z + 0.3), BUTTER))
		src.append(Solid.box_mm(SRC + Vector3(1.5, -3, z - 0.3), SRC + Vector3(1.8, 0, z + 0.3), BUTTER))
	s.append_array(_tag(src, "source"))

	return {
		"name": "1 · Found Photograph",
		"hint": "Walk into the polaroid to pick it up. Tap it (top-left) to hold it up, aim at the gap, then PLACE.",
		"spawn": Vector3(0, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -19), "needs": 0},
		"camera": false, "film": 0,
		"found": [{"at": Vector3(0, 1.4, 0.5), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, -20), "title": "Bridge"}],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 2. Take your own photo of a ramp, turn around, paste it against a cliff.
# ---------------------------------------------------------------------------
static func _point_and_shoot() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-6, -1, -40), Vector3(6, 0, 30), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-6.5, 0, -40), Vector3(-6, 7, 30), LAV))
	s.append(Solid.box_mm(Vector3(6, 0, -40), Vector3(6.5, 7, 30), LAV))
	# Teleporter cliff (no way up).
	s.append(Solid.box_mm(Vector3(-6, 0, -40), Vector3(6, 4, -14), PEACH, SAND))
	# Look-alike cliff behind the start, with a ramp. Dead end.
	s.append(Solid.ramp(Vector3(0, 0, 14), Vector3.BACK, 6, 3, 4, TEAL, MINT))
	s.append(Solid.box_mm(Vector3(-6, 0, 20), Vector3(6, 4, 30), PEACH, SAND))
	s.append(Solid.box_mm(Vector3(-6, 4, 29.5), Vector3(6, 7, 30), ROSE))
	return {
		"name": "2 · Point and Shoot",
		"hint": "You have a camera. Tap CAM, frame the ramp behind you, press SNAP. Then face the cliff and PLACE it.",
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
	s.append(Solid.box_mm(Vector3(-14, -1, -14), Vector3(14, 0, 14), CREAM, SAND))
	# Sealed room: x [-3, 3], z [-12.4, -6]
	var wall := ROSE
	s.append(Solid.box_mm(Vector3(-3.4, 0, -6.4), Vector3(-0.8, 3.6, -6.0), wall))
	s.append(Solid.box_mm(Vector3(0.8, 0, -6.4), Vector3(3.4, 3.6, -6.0), wall))
	s.append(Solid.box_mm(Vector3(-0.8, 0, -6.4), Vector3(0.8, 1.0, -6.0), wall))
	s.append(Solid.box_mm(Vector3(-0.8, 2.2, -6.4), Vector3(0.8, 3.6, -6.0), wall))
	s.append(Solid.box_mm(Vector3(-3.4, 0, -12.8), Vector3(3.4, 3.6, -12.4), PEACH))
	s.append(Solid.box_mm(Vector3(-3.4, 0, -12.4), Vector3(-3.0, 3.6, -6.4), PEACH))
	s.append(Solid.box_mm(Vector3(3.0, 0, -12.4), Vector3(3.4, 3.6, -6.4), PEACH))
	s.append(Solid.box_mm(Vector3(-3.4, 3.6, -12.8), Vector3(3.4, 4.0, -6.0), LAV))
	s.append(Solid.box_mm(Vector3(-0.6, 0, -10.6), Vector3(0.6, 0.5, -9.4), BUTTER))
	# Some open-space decoration.
	s.append(_pillar(8, 8, 2.5, TEAL))
	s.append(_pillar(-8, 8, 2.5, TEAL))
	s.append(Solid.box_mm(Vector3(-14, 0, 13.6), Vector3(14, 2, 14), LAV))
	return {
		"name": "3 · Through the Window",
		"hint": "The teleporter needs a battery. Press against the window and photograph the one inside. Then PLACE the photo in open space.",
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
	s.append(Solid.box_mm(Vector3(-2, -1, -26), Vector3(2, 0, 10), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-2.4, -1, -26), Vector3(-2, 4, 10), w))
	s.append(Solid.box_mm(Vector3(2, -1, -26), Vector3(2.4, 4, 10), w))
	s.append(Solid.box_mm(Vector3(-2.4, 4, -26), Vector3(2.4, 4.4, 10), PEACH))
	s.append(Solid.box_mm(Vector3(-2.4, -1, -26.4), Vector3(2.4, 4.4, -26), PEACH))
	# The blocking wall.
	s.append(Solid.box_mm(Vector3(-2, 0, -8), Vector3(2, 4, -6), ROSE))
	# Open terrace behind the start.
	s.append(Solid.box_mm(Vector3(-2, -1, 10), Vector3(2, 0, 34), TEAL, MINT))
	for z in [14.0, 20.0, 26.0, 32.0]:
		s.append(_pillar(-1.7, z, 1.2, BUTTER))
		s.append(_pillar(1.7, z, 1.2, BUTTER))
	return {
		"name": "4 · Breakthrough",
		"hint": "A photo replaces everything inside its frame. Photograph the open terrace, stand well back from the wall, and PLACE.",
		"spawn": Vector3(0, 0, -1), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -19), "needs": 0},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 5. A vertical shaft photographed from below becomes a horizontal tunnel.
# ---------------------------------------------------------------------------
static func _look_up() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-7, -1, -6), Vector3(7, 0, 8), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-5, -1, -34), Vector3(5, 0, -18), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-5, 0, -34.4), Vector3(5, 4, -34), PEACH))
	# Shaft centred on (3.5, 3.5), interior half-width 1.5 (= eye height).
	var cx := 3.5
	var cz := 3.5
	var h := 40.0
	var t := 0.3
	s.append(Solid.box_mm(Vector3(cx - 1.5 - t, 0, cz - 1.5 - t), Vector3(cx + 1.5 + t, h, cz - 1.5), TEAL))
	s.append(Solid.box_mm(Vector3(cx - 1.5 - t, 0, cz + 1.5), Vector3(cx + 1.5 + t, h, cz + 1.5 + t), MINT))
	s.append(Solid.box_mm(Vector3(cx + 1.5, 0, cz - 1.5), Vector3(cx + 1.5 + t, h, cz + 1.5), BUTTER))
	# West wall has a doorway at the bottom.
	s.append(Solid.box_mm(Vector3(cx - 1.5 - t, 2.4, cz - 1.5), Vector3(cx - 1.5, h, cz + 1.5), LAV))
	s.append(Solid.box_mm(Vector3(cx - 1.5 - t, 0, cz - 1.5), Vector3(cx - 1.5, 2.4, cz - 0.6), LAV))
	s.append(Solid.box_mm(Vector3(cx - 1.5 - t, 0, cz + 0.6), Vector3(cx - 1.5, 2.4, cz + 1.5), LAV))
	s.append(Solid.box_mm(Vector3(-7, 0, 7.6), Vector3(7, 2.5, 8), ROSE))
	return {
		"name": "5 · Look Up",
		"hint": "Stand in the middle of the tower and look straight up. A tunnel is a tower lying down. Stand back from the edge to PLACE.",
		"spawn": Vector3(-2, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [],
		"teleporter": {"pos": Vector3(0, 0, -28), "needs": 0},
		"camera": true, "film": -1,
		"found": [],
		"kill_y": -15.0,
	}


# ---------------------------------------------------------------------------
# 6. Everything together, with limited film.
# ---------------------------------------------------------------------------
static func _darkroom() -> Dictionary:
	var s: Array = []
	s.append(Solid.box_mm(Vector3(-10, -1, -40), Vector3(10, 0, 10), CREAM, SAND))
	s.append(Solid.box_mm(Vector3(-10, 0, -40), Vector3(10, 6, -12), PEACH, SAND))
	s.append(Solid.box_mm(Vector3(-10.4, 0, -40), Vector3(-10, 8, 10), LAV))
	s.append(Solid.box_mm(Vector3(10, 0, -40), Vector3(10.4, 8, 10), LAV))
	s.append(Solid.box_mm(Vector3(-10, 0, 9.6), Vector3(10, 8, 10), LAV))
	# Rug + plinth for the battery.
	s.append(Solid.box_mm(Vector3(4.5, 0, 0.5), Vector3(7.5, 0.05, 3.5), ROSE))
	s.append(Solid.box_mm(Vector3(5.6, 0, 1.6), Vector3(6.4, 0.4, 2.4), BUTTER))
	s.append(Solid.box_mm(Vector3(-2, 0, 5), Vector3(2, 0.8, 6), STONE))  # postcard stand

	var src: Array = []
	src.append(Solid.box_mm(SRC + Vector3(-10, -1, -40), SRC + Vector3(10, 0, 4), CREAM, SAND))
	src.append(Solid.ramp(SRC + Vector3(0, 0, -5), Vector3.FORWARD, 9, 4, 6, TEAL, MINT))
	src.append(Solid.box_mm(SRC + Vector3(-10, 0, -40), SRC + Vector3(10, 6, -14), PEACH, SAND))
	src.append(Solid.box_mm(SRC + Vector3(-10.4, 0, -40), SRC + Vector3(-10, 8, 4), LAV))
	src.append(Solid.box_mm(SRC + Vector3(10, 0, -40), SRC + Vector3(10.4, 8, 4), LAV))
	s.append_array(_tag(src, "source"))
	return {
		"name": "6 · Darkroom",
		"hint": "Two batteries, three shots. Copy one by aiming DOWN at it — a photo replaces everything in its frame, all the way to the horizon. Hold REWIND to undo.",
		"spawn": Vector3(0, 0, 3), "yaw": 0.0,
		"solids": s,
		"batteries": [Vector3(6, 0.75, 2)],
		"teleporter": {"pos": Vector3(0, 6, -30), "needs": 2},
		"camera": true, "film": 3,
		"found": [{"at": Vector3(0, 1.5, 5.5), "from": _eye(SRC + Vector3(0, 1.5, 0), 0, 0), "title": "Postcard"}],
		"kill_y": -15.0,
	}
