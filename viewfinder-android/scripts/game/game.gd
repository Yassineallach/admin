class_name Game
extends Node3D
## Runs one level: builds the world, owns the photo inventory, performs
## capture / placement, and records everything for the rewind system.

signal exit_requested(next_level: int)

const PHOTO_PX := 512
const HOLD_DIST := 0.3
const MAX_FRAMES := 60 * 120  # two minutes of rewind
const REWIND_SPEED := 2
const SNAP_PITCH := deg_to_rad(8.0)
const SNAP_LEVEL := deg_to_rad(6.0)
const SNAP_YAW := deg_to_rad(5.0)
const SNAP_VERTICAL := deg_to_rad(86.0)

var level_index: int = 0
var level: Dictionary

var solid_world: SolidWorld
var entities: Node3D
var player: Player
var teleporter: Teleporter
var hud: Hud

var photos: Array = []
var film: int = 0
var has_camera: bool = false
var camera_mode: bool = false
var raised: int = -1
var roll: float = 0.0
var held: Battery = null
var batteries: Array = []
var pickups: Dictionary = {}  # key -> PhotoPickup
var collected: Dictionary = {}

var _photo_vp: SubViewport
var _photo_cam: Camera3D
var _held_root: Node3D
var _held_photo: MeshInstance3D
var _next_item_id := 1
var _photo_counter := 0

# Rewind
var _snapshots: Array = []
var _frames: Array = []
var _auto_rewind := 0
var _was_rewinding := false

var ready_to_play := false
var completed := false
var _pending_unstick := 0


func _ready() -> void:
	level = Levels.get_level(level_index)
	_build_environment()

	solid_world = SolidWorld.new()
	solid_world.name = "SolidWorld"
	add_child(solid_world)
	solid_world.set_solids(level["solids"].duplicate())

	entities = Node3D.new()
	entities.name = "Entities"
	add_child(entities)

	player = Player.new()
	player.name = "Player"
	add_child(player)
	player.global_position = level["spawn"]
	player.set_look(deg_to_rad(level["yaw"]), 0.0)
	player.frozen = true
	_build_held_photo()

	_photo_vp = SubViewport.new()
	_photo_vp.size = Vector2i(PHOTO_PX, PHOTO_PX)
	_photo_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	_photo_vp.msaa_3d = Viewport.MSAA_2X
	add_child(_photo_vp)
	_photo_cam = Camera3D.new()
	_photo_cam.fov = rad_to_deg(2.0 * atan(Photo.T))
	_photo_cam.keep_aspect = Camera3D.KEEP_HEIGHT
	_photo_cam.near = 0.05
	_photo_cam.far = 400.0
	_photo_cam.cull_mask = 1  # world only: no held photo / UI layer
	_photo_vp.add_child(_photo_cam)

	var tp: Dictionary = level["teleporter"]
	teleporter = Teleporter.new()
	entities.add_child(teleporter)
	teleporter.position = tp["pos"]
	teleporter.setup(int(tp["needs"]))
	teleporter.entered.connect(_on_teleporter_entered)

	for pos in level["batteries"]:
		_spawn_battery(Transform3D(Basis(), pos))

	has_camera = level["camera"]
	film = int(level["film"])

	hud = Hud.new()
	hud.game = self
	var layer := CanvasLayer.new()
	layer.name = "HudLayer"
	add_child(layer)
	layer.add_child(hud)
	hud.set_title(level["name"], level["hint"])
	hud.fade = 1.0

	await _prepare_found_photos()
	_snapshots.append(_make_snapshot())
	ready_to_play = true
	player.frozen = false


func _build_environment() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(0.52, 0.72, 0.9)
	sm.sky_horizon_color = Color(0.97, 0.88, 0.82)
	sm.ground_bottom_color = Color(0.78, 0.66, 0.72)
	sm.ground_horizon_color = Color(0.97, 0.88, 0.82)
	sm.sun_angle_max = 20.0
	sky.sky_material = sm
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.45
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.1
	env.fog_enabled = true
	env.fog_light_color = Color(0.95, 0.87, 0.85)
	env.fog_density = 0.0025
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(deg_to_rad(-55), deg_to_rad(35), 0)
	sun.light_energy = 0.75
	sun.shadow_bias = 0.06
	sun.shadow_normal_bias = 1.5
	sun.shadow_blur = 1.5
	sun.light_color = Color(1.0, 0.96, 0.9)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 70.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun)


func _build_held_photo() -> void:
	_held_root = Node3D.new()
	_held_root.position = Vector3(0, 0, -HOLD_DIST)
	player.camera.add_child(_held_root)
	var side := 2.0 * HOLD_DIST * Photo.T

	var frame := MeshInstance3D.new()
	var fq := QuadMesh.new()
	fq.size = Vector2(side * 1.12, side * 1.28)
	frame.mesh = fq
	frame.position = Vector3(0, -side * 0.08, -0.001)
	var fmat := StandardMaterial3D.new()
	fmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fmat.albedo_color = Color(0.99, 0.98, 0.95, 0.9)
	fmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fmat.no_depth_test = true
	fmat.render_priority = 10
	frame.material_override = fmat
	frame.layers = 2
	frame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_held_root.add_child(frame)

	_held_photo = MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(side, side)
	_held_photo.mesh = q
	_held_photo.layers = 2
	_held_photo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_held_root.add_child(_held_photo)
	_held_root.visible = false


# ---------------------------------------------------------------------------
# Found photos
# ---------------------------------------------------------------------------

func _prepare_found_photos() -> void:
	# Let the world render once so shadows/sky are ready for the snapshots.
	await get_tree().process_frame
	var source: Array = []
	for s in solid_world.solids:
		if (s as Solid).tag == "source":
			source.append(s)
	var idx := 0
	for fp in level["found"]:
		var xf: Transform3D = fp["from"]
		var p := Photo.new()
		p.title = fp.get("title", "Photo")
		p.solids = Slicer.capture(source, xf, Photo.T)
		p.pitch = xf.basis.get_euler().x
		p.texture = await _render_photo(xf)
		var pick := PhotoPickup.new()
		pick.key = "found_%d" % idx
		entities.add_child(pick)
		pick.position = fp["at"]
		pick.setup(p)
		pickups[pick.key] = pick
		idx += 1
	if not source.is_empty():
		var rest: Array = []
		for s in solid_world.solids:
			if (s as Solid).tag != "source":
				rest.append(s)
		solid_world.set_solids(rest)


func _render_photo(xf: Transform3D) -> Texture2D:
	_photo_cam.global_transform = xf
	if DisplayServer.get_name() == "headless":
		# No renderer (CI / tests): frame_post_draw never fires.
		await get_tree().process_frame
		return _placeholder_texture()
	var hide_held := held != null
	if hide_held:
		held.visible = false
	_photo_vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	if hide_held and is_instance_valid(held):
		held.visible = true
	var img := _photo_vp.get_texture().get_image()
	if img == null or img.is_empty():
		return _placeholder_texture()
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _placeholder_texture() -> Texture2D:
	var img := Image.create(8, 8, false, Image.FORMAT_RGB8)
	img.fill(Color(0.6, 0.75, 0.82))
	return ImageTexture.create_from_image(img)


# ---------------------------------------------------------------------------
# Camera / photos
# ---------------------------------------------------------------------------

func _snap_angle(a: float, step: float, tol: float) -> float:
	var k := roundf(a / step) * step
	return k if absf(a - k) < tol else a


func _capture_transform() -> Transform3D:
	var pitch := player.pitch
	if absf(pitch) > SNAP_VERTICAL:
		pitch = signf(pitch) * PI * 0.5
	elif absf(pitch) < SNAP_LEVEL:
		pitch = 0.0
	var yaw := _snap_angle(player.yaw, PI * 0.5, SNAP_YAW)
	return Transform3D(Basis.from_euler(Vector3(pitch, yaw, 0)), player.camera.global_position)


func _placement_transform(p: Photo) -> Transform3D:
	var pitch := player.pitch
	if absf(pitch - p.pitch) < SNAP_PITCH:
		pitch = p.pitch
	elif absf(pitch) < SNAP_LEVEL:
		pitch = 0.0
	var yaw := _snap_angle(player.yaw, PI * 0.5, SNAP_YAW)
	var b := Basis.from_euler(Vector3(pitch, yaw, 0)) * Basis(Vector3(0, 0, 1), roll)
	return Transform3D(b, player.camera.global_position)


func toggle_camera_mode() -> void:
	if not has_camera or not ready_to_play:
		return
	camera_mode = not camera_mode
	if camera_mode:
		lower_photo()


func take_photo() -> void:
	if not has_camera or not ready_to_play or completed:
		return
	if film == 0:
		hud.toast("Out of film — hold REWIND to get it back")
		return
	var xf := _capture_transform()
	var p := Photo.new()
	_photo_counter += 1
	p.title = "Photo %d" % _photo_counter
	p.pitch = xf.basis.get_euler().x
	p.solids = Slicer.capture(solid_world.solids, xf, Photo.T)
	var inv := xf.affine_inverse()
	for b in batteries:
		var bat: Battery = b
		if bat == held:
			continue
		if Slicer.point_in_frustum(xf, Photo.T, bat.global_position):
			p.items.append({"type": "battery", "xf": inv * bat.global_transform})
	photos.append(p)
	if film > 0:
		film -= 1
	_commit()
	hud.flash = 1.0
	camera_mode = false
	p.texture = await _render_photo(xf)
	hud.toast("Captured! Tap the photo to hold it up.")


func raise_photo(i: int) -> void:
	if i < 0 or i >= photos.size() or not ready_to_play:
		return
	if raised == i:
		lower_photo()
		return
	raised = i
	roll = 0.0
	camera_mode = false
	_update_held_photo()


func lower_photo() -> void:
	raised = -1
	_update_held_photo()


func rotate_photo(dir: int) -> void:
	if raised < 0:
		return
	roll = wrapf(roll + dir * PI * 0.5, -PI, PI)
	_update_held_photo()


func _update_held_photo() -> void:
	if raised < 0 or raised >= photos.size():
		raised = -1
		_held_root.visible = false
		return
	var p: Photo = photos[raised]
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_texture = p.texture
	mat.albedo_color = Color(1, 1, 1, 0.85)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.no_depth_test = true
	mat.render_priority = 11
	_held_photo.material_override = mat
	_held_root.rotation = Vector3(0, 0, roll)
	_held_root.visible = true


func place_photo() -> void:
	if raised < 0 or not ready_to_play or completed:
		return
	var p: Photo = photos[raised]
	var xf := _placement_transform(p)
	var new_solids := Slicer.place(solid_world.solids, p.solids, xf, Photo.T)
	for b in batteries.duplicate():
		var bat: Battery = b
		if bat == held:
			continue
		if Slicer.point_in_frustum(xf, Photo.T, bat.global_position):
			_remove_battery(bat)
	for it in p.items:
		_spawn_battery(xf * (it["xf"] as Transform3D))
	solid_world.set_solids(new_solids)
	photos.remove_at(raised)
	lower_photo()
	_commit()
	for b in batteries:
		(b as Battery).sleeping = false
	_pending_unstick = 2
	hud.flash = 0.6


# ---------------------------------------------------------------------------
# Batteries
# ---------------------------------------------------------------------------

func _spawn_battery(xf: Transform3D, id: int = -1) -> Battery:
	var b := Battery.new()
	b.id = id if id >= 0 else _next_item_id
	_next_item_id = maxi(_next_item_id, b.id + 1)
	entities.add_child(b)
	b.global_transform = xf
	batteries.append(b)
	return b


func _remove_battery(b: Battery) -> void:
	batteries.erase(b)
	if held == b:
		held = null
	b.queue_free()


func interact() -> void:
	if not ready_to_play or completed:
		return
	if held:
		var drop := player.camera.global_transform * Vector3(0, -0.2, -0.9)
		held.global_transform = Transform3D(Basis(), drop)
		held.set_held(false)
		held.linear_velocity = player.velocity
		held = null
		return
	var eye := player.camera.global_position
	var fwd := -player.camera.global_transform.basis.z
	var best: Battery = null
	var best_score := -INF
	for b in batteries:
		var bat: Battery = b
		var to := bat.global_position - eye
		var dist := to.length()
		if dist > 2.6:
			continue
		var facing := fwd.dot(to / maxf(dist, 0.001))
		if facing < 0.35:
			continue
		var score := facing - dist * 0.2
		if score > best_score:
			best_score = score
			best = bat
	if best:
		best.set_socket(-1)
		best.set_held(true)
		held = best
	else:
		hud.toast("Nothing to grab")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

func _physics_process(_delta: float) -> void:
	if not ready_to_play:
		return
	var rewinding := (hud.wants_rewind() or _auto_rewind > 0) and not completed
	if rewinding:
		_step_rewind()
		_was_rewinding = true
		return
	if _was_rewinding:
		_end_rewind()

	_read_controls()

	if held:
		held.global_transform = player.hold_point.global_transform
	if _pending_unstick > 0:
		_pending_unstick -= 1
		if _pending_unstick == 0:
			player.unstick()

	for key in pickups.keys():
		var pick: PhotoPickup = pickups[key]
		if collected.has(key):
			continue
		if pick.global_position.distance_to(player.global_position + Vector3(0, 0.9, 0)) < 1.4:
			collected[key] = true
			pick.visible = false
			photos.append(pick.photo)
			_commit()
			hud.toast("Found a photograph: " + pick.photo.title)

	teleporter.update_sockets(batteries, player.global_position)

	if player.global_position.y < float(level["kill_y"]):
		_auto_rewind = 150
		hud.toast("Whoops. Rewinding…")

	_record_frame()


func _read_controls() -> void:
	var mv := hud.stick_vec
	var kb := Vector2(
		float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A)),
		float(Input.is_physical_key_pressed(KEY_W)) - float(Input.is_physical_key_pressed(KEY_S)))
	if kb != Vector2.ZERO:
		mv = kb.normalized()
	player.move_input = mv
	var look := hud.consume_look()
	if look != Vector2.ZERO:
		player.look(look)


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	match event.physical_keycode:
		KEY_SPACE: player.jump_requested = true
		KEY_E: interact()
		KEY_C: toggle_camera_mode()
		KEY_F:
			if camera_mode:
				take_photo()
			elif raised >= 0:
				place_photo()
		KEY_Z: rotate_photo(-1)
		KEY_X: rotate_photo(1)
		KEY_ESCAPE: hud.toggle_pause()
		_:
			var n: int = event.physical_keycode - KEY_1
			if n >= 0 and n < 9:
				raise_photo(n)


func on_hud_action(name: String) -> void:
	match name:
		"jump": player.jump_requested = true
		"act": interact()
		"cam": toggle_camera_mode()
		"shutter": take_photo()
		"place": place_photo()
		"rotl": rotate_photo(-1)
		"rotr": rotate_photo(1)
		"restart": exit_requested.emit(level_index)
		"menu": exit_requested.emit(-1)
		"next": exit_requested.emit(level_index + 1 if level_index + 1 < Levels.count() else -1)
		_:
			if name.begins_with("photo_"):
				raise_photo(int(name.substr(6)))


func _on_teleporter_entered() -> void:
	if completed:
		return
	completed = true
	player.frozen = true
	Progress.mark_completed(level_index)
	hud.show_complete(level_index + 1 >= Levels.count())


# ---------------------------------------------------------------------------
# Rewind
# ---------------------------------------------------------------------------

func _make_snapshot() -> Dictionary:
	return {
		"solids": solid_world.solids,
		"photos": photos.duplicate(),
		"film": film,
		"collected": collected.duplicate(),
	}


func _commit() -> void:
	_snapshots.append(_make_snapshot())


func _apply_snapshot(s: Dictionary) -> void:
	if solid_world.solids != s["solids"]:
		solid_world.set_solids(s["solids"])
	photos = (s["photos"] as Array).duplicate()
	film = s["film"]
	collected = (s["collected"] as Dictionary).duplicate()
	for key in pickups.keys():
		(pickups[key] as PhotoPickup).visible = not collected.has(key)
	if raised >= photos.size():
		lower_photo()


func _record_frame() -> void:
	var items: Array = []
	for b in batteries:
		items.append((b as Battery).to_state())
	_frames.append({
		"pos": player.global_position,
		"vel": player.velocity,
		"yaw": player.yaw,
		"pitch": player.pitch,
		"snap": _snapshots.size() - 1,
		"items": items,
	})
	if _frames.size() > MAX_FRAMES:
		_frames.pop_front()


func _step_rewind() -> void:
	camera_mode = false
	for b in batteries:
		(b as Battery).freeze = true
	var frame: Dictionary = {}
	for i in REWIND_SPEED:
		if _frames.size() <= 1:
			break
		frame = _frames.pop_back()
		if _auto_rewind > 0:
			_auto_rewind -= 1
	if frame.is_empty():
		if not _frames.is_empty():
			frame = _frames[0]
		_auto_rewind = 0
	if frame.is_empty():
		return
	var si: int = frame["snap"]
	if si < _snapshots.size() - 1:
		_snapshots.resize(si + 1)
		_apply_snapshot(_snapshots[si])
	player.global_position = frame["pos"]
	player.velocity = frame["vel"]
	player.set_look(frame["yaw"], frame["pitch"])
	_sync_items(frame["items"])


func _end_rewind() -> void:
	_was_rewinding = false
	_auto_rewind = 0
	for b in batteries:
		var bat: Battery = b
		bat.set_held(bat.held)
		bat.set_socket(bat.socket)
	_pending_unstick = 1


func _sync_items(states: Array) -> void:
	var by_id: Dictionary = {}
	for b in batteries:
		by_id[(b as Battery).id] = b
	var seen: Dictionary = {}
	held = null
	for st in states:
		var id: int = st["id"]
		var bat: Battery = by_id.get(id)
		if bat == null:
			bat = _spawn_battery(st["xf"], id)
		seen[id] = true
		bat.global_transform = st["xf"]
		bat.linear_velocity = Vector3.ZERO
		bat.angular_velocity = Vector3.ZERO
		bat.held = st["held"]
		bat.socket = st["socket"]
		bat.freeze = true
		if bat.held:
			held = bat
	for id in by_id.keys():
		if not seen.has(id):
			_remove_battery(by_id[id])
