class_name Game
extends Node3D
## Runs one level (or the hub): builds the world, owns the photo inventory,
## performs capture / placement, and records everything for rewind.

## next >= 0: load that level · HUB: go to the hub · MENU: main menu.
signal exit_requested(next_level: int)

const HUB := -2
const MENU := -1

const PHOTO_PX := 512
const HOLD_DIST := 0.3
const MAX_FRAMES := 60 * 120  # two minutes of rewind
const REWIND_SPEED := 2
const SNAP_PITCH := deg_to_rad(8.0)
const SNAP_LEVEL := deg_to_rad(6.0)
const SNAP_YAW := deg_to_rad(5.0)
const SNAP_VERTICAL := deg_to_rad(86.0)
## Visual layer for things that should not appear in photographs.
const LAYER_NO_PHOTO := 4

## Level to play; -1 = hub.
var level_index: int = 0
var level: Dictionary
var is_hub := false

var solid_world: SolidWorld
var entities: Node3D
var player: Player
var teleporter: Teleporter
var hub_pads: Array = []
var cat: Cat
var notes: Array = []
var sockets: Dictionary = {}  # id -> PowerSocket
var gates: Array = []
var fixed_cams: Array = []
var copiers: Array = []
var hint_index := 0
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
var _held_frame: MeshInstance3D
var _held_photo: MeshInstance3D
var _held_dev: MeshInstance3D
var _held_dev_mat: StandardMaterial3D
var _raise_t := 1.0
var _sway := Vector2.ZERO
var _next_item_id := 1
var _photo_counter := 0
var _cat_line := 0

# Rewind
var _snapshots: Array = []
var _frames: Array = []
var _auto_rewind := 0
var _was_rewinding := false

var ready_to_play := false
var completed := false
var _pending_unstick := 0


func _ready() -> void:
	is_hub = level_index < 0
	level = Levels.hub() if is_hub else Levels.get_level(level_index)
	_build_environment()

	solid_world = SolidWorld.new()
	solid_world.name = "SolidWorld"
	add_child(solid_world)
	solid_world.set_solids(level["solids"].duplicate())
	# Distant islands + sea: a backdrop that photos never cut (like a skybox).
	var backdrop := MeshInstance3D.new()
	backdrop.name = "Backdrop"
	backdrop.mesh = SolidWorld.build_mesh(level.get("backdrop", []), solid_world.material)
	backdrop.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(backdrop)

	entities = Node3D.new()
	entities.name = "Entities"
	add_child(entities)

	player = Player.new()
	player.name = "Player"
	add_child(player)
	player.global_position = level["spawn"]
	player.set_look(deg_to_rad(level["yaw"]), 0.0)
	player.frozen = true
	var life := AmbientLife.new()
	add_child(life)
	life.setup(player, Vector3(level["spawn"]) * Vector3(1, 0, 1) + Vector3(0, level["spawn"].y, 0), level["spawn"])
	player.footstep.connect(func(): Sfx.play("step", -14.0, randf_range(0.85, 1.15)))
	player.landed.connect(func(k: float): Sfx.play("land", lerpf(-12.0, -4.0, k)))
	_build_held_photo()

	_photo_vp = SubViewport.new()
	_photo_vp.size = Vector2i(PHOTO_PX, PHOTO_PX)
	_photo_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	_photo_vp.msaa_3d = Viewport.MSAA_2X if Progress.quality() >= 2 else Viewport.MSAA_DISABLED
	add_child(_photo_vp)
	_photo_cam = Camera3D.new()
	_photo_cam.fov = rad_to_deg(2.0 * atan(Photo.T))
	_photo_cam.keep_aspect = Camera3D.KEEP_HEIGHT
	_photo_cam.near = 0.05
	_photo_cam.far = 600.0
	_photo_cam.cull_mask = 1  # world + batteries only
	_photo_vp.add_child(_photo_cam)

	if is_hub:
		for i in Levels.count():
			var pad := Teleporter.new()
			entities.add_child(pad)
			pad.position = Levels.hub_pad(i)
			pad.rotation.y = atan2(-pad.position.x, -pad.position.z)
			var locked := i + 1 > Progress.unlocked
			pad.setup(0, Levels.get_level_name(i), locked, Progress.completed.has(i))
			pad.entered.connect(_on_hub_pad.bind(i))
			hub_pads.append(pad)
			_no_photo(pad)
	elif level.get("teleporter") != null:
		var tp: Dictionary = level["teleporter"]
		teleporter = Teleporter.new()
		entities.add_child(teleporter)
		teleporter.position = tp["pos"]
		teleporter.setup(int(tp["needs"]))
		teleporter.entered.connect(_on_teleporter_entered)
		_no_photo(teleporter)

	for pos in level["batteries"]:
		_spawn_battery(Transform3D(Basis(), pos))
	for sd in level.get("sockets", []):
		var ps := PowerSocket.new()
		entities.add_child(ps)
		ps.position = sd["pos"]
		ps.setup(int(sd["id"]), sd.get("cable_to", Vector3.INF))
		sockets[int(sd["id"])] = ps
		_no_photo(ps)
	for gd in level.get("gates", []):
		var g := Gate.new()
		entities.add_child(g)
		g.position = gd["pos"]
		g.rotation.y = deg_to_rad(gd.get("yaw", 0.0))
		g.setup(gd["size"], gd["needs"])
		gates.append(g)
		_no_photo(g)
	for fc in level.get("fixed_cameras", []):
		var cam_node := FixedCamera.new()
		entities.add_child(cam_node)
		cam_node.position = fc["base"]
		cam_node.setup(fc["eye"])
		fixed_cams.append(cam_node)
		_no_photo(cam_node)
	for cp in level.get("copiers", []):
		var copier := Photocopier.new()
		entities.add_child(copier)
		copier.position = cp["pos"]
		copier.rotation.y = deg_to_rad(cp.get("yaw", 0.0))
		copier.setup()
		copiers.append(copier)
		_no_photo(copier)

	if level.has("cat"):
		cat = Cat.new()
		entities.add_child(cat)
		cat.position = level["cat"]["pos"]
		cat.rotation.y = deg_to_rad(level["cat"]["yaw"])
		_no_photo(cat)
	for n in level.get("notes", []):
		var note := Note.new()
		entities.add_child(note)
		note.position = n["at"]
		note.setup(n["title"], n["text"])
		notes.append(note)
		_no_photo(note)

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
	if cat:
		var lines: Array = level["cat"]["lines"]
		if is_hub and Progress.settings.get("hub_intro_seen", false):
			lines = ["Welcome back. Pick a pad, any pad."]
		hud.say("Miso", lines)
		if is_hub:
			Progress.settings["hub_intro_seen"] = true
			Progress.save_progress()


func _no_photo(n: Node) -> void:
	if n is VisualInstance3D:
		(n as VisualInstance3D).layers = LAYER_NO_PHOTO
	for c in n.get_children():
		_no_photo(c)


func _build_environment() -> void:
	Game.make_environment(self)


## Resolution / anti-aliasing per quality level (cheaper on phones).
static func apply_quality(vp: Viewport, q: int) -> void:
	if vp == null:
		return
	vp.msaa_3d = Viewport.MSAA_2X if q >= 2 else Viewport.MSAA_DISABLED
	vp.scaling_3d_scale = [0.7, 0.85, 1.0][clampi(q, 0, 2)]
	RenderingServer.directional_shadow_atlas_set_size(2048 if q >= 2 else 1024, true)


## Sky, ambient light, fog, glow and the sun. Shared with the menu backdrop.
static func make_environment(parent: Node) -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/sky.gdshader")
	sky.sky_material = sm
	var q := Progress.quality()
	# The ambient-light cubemap is rendered once, not every frame: re-rendering
	# the animated sky into it each frame is far too heavy for phone GPUs.
	sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL if q >= 2 else Sky.PROCESS_MODE_AUTOMATIC
	sky.radiance_size = Sky.RADIANCE_SIZE_64 if q >= 2 else Sky.RADIANCE_SIZE_32
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.55
	env.ambient_light_sky_contribution = 0.8
	env.ambient_light_color = Color(1.0, 0.92, 0.9)
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	env.glow_enabled = q >= 1
	env.glow_intensity = 0.55
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 0.9
	env.fog_enabled = true
	env.fog_light_color = Color(0.98, 0.88, 0.86)
	env.fog_density = 0.0016
	env.fog_sky_affect = 0.0
	env.fog_aerial_perspective = 0.4
	var we := WorldEnvironment.new()
	we.environment = env
	parent.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(deg_to_rad(-48), deg_to_rad(28), 0)
	sun.light_energy = 1.25
	sun.light_color = Color(1.0, 0.95, 0.88)
	sun.shadow_enabled = q >= 1
	sun.shadow_bias = 0.06
	sun.shadow_normal_bias = 1.5
	sun.shadow_blur = 1.5
	sun.directional_shadow_max_distance = 70.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS if q >= 2 else DirectionalLight3D.SHADOW_ORTHOGONAL
	if q < 2:
		sun.directional_shadow_max_distance = 40.0
	Game.apply_quality(parent.get_viewport(), q)
	parent.add_child(sun)


func _build_held_photo() -> void:
	_held_root = Node3D.new()
	_held_root.position = Vector3(0, 0, -HOLD_DIST)
	player.camera.add_child(_held_root)
	var side := 2.0 * HOLD_DIST * Photo.T

	_held_frame = _overlay_quad(Vector2(side * 1.12, side * 1.28), Color(0.99, 0.98, 0.95), 9)
	_held_frame.position = Vector3(0, -side * 0.08, -0.001)
	_held_root.add_child(_held_frame)

	_held_photo = _overlay_quad(Vector2(side, side), Color.WHITE, 10)
	_held_root.add_child(_held_photo)

	_held_dev = _overlay_quad(Vector2(side, side), Color(0.97, 0.96, 0.93, 0.0), 11)
	_held_dev_mat = _held_dev.material_override
	_held_dev.position.z = 0.0005
	_held_root.add_child(_held_dev)
	_build_hands(side)
	_held_root.visible = false


## Two stylised hands pinching the bottom corners of the held picture.
func _build_hands(side: float) -> void:
	var skin := StandardMaterial3D.new()
	skin.albedo_color = Color(0.86, 0.62, 0.5)
	skin.roughness = 1.0
	skin.no_depth_test = true
	skin.render_priority = 14
	var sleeve := StandardMaterial3D.new()
	sleeve.albedo_color = Color(0.42, 0.5, 0.72)
	sleeve.roughness = 1.0
	sleeve.no_depth_test = true
	sleeve.render_priority = 13
	for sx in [-1.0, 1.0]:
		# Hands hold the sides of the picture: the palm tucks behind the frame,
		# the thumb rests on the front, the sleeve runs off the bottom of the screen.
		var hand := Node3D.new()
		hand.position = Vector3(side * 0.56 * sx, -side * 0.3, 0.0)
		_held_root.add_child(hand)
		var palm := MeshInstance3D.new()
		var pm := SphereMesh.new()
		pm.radius = 0.024
		pm.height = 0.048
		palm.mesh = pm
		palm.scale = Vector3(0.8, 1.35, 0.5)
		palm.position = Vector3(0.006 * sx, -0.004, -0.006)
		var palm_mat: StandardMaterial3D = skin.duplicate()
		palm_mat.render_priority = 8
		palm.material_override = palm_mat
		hand.add_child(palm)
		var thumb := MeshInstance3D.new()
		var tm := CapsuleMesh.new()
		tm.radius = 0.008
		tm.height = 0.038
		thumb.mesh = tm
		thumb.position = Vector3(-0.011 * sx, 0.006, 0.004)
		thumb.rotation.z = 0.9 * sx
		thumb.material_override = skin
		hand.add_child(thumb)
		var cuff := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.022
		cm.bottom_radius = 0.028
		cm.height = 0.16
		cuff.mesh = cm
		cuff.position = Vector3(0.03 * sx, -0.09, -0.02)
		cuff.rotation = Vector3(-0.3, 0, 0.35 * sx)
		var cuff_mat: StandardMaterial3D = sleeve.duplicate()
		cuff_mat.render_priority = 7
		cuff.material_override = cuff_mat
		hand.add_child(cuff)
		for c in hand.get_children():
			(c as MeshInstance3D).layers = 2
			(c as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _overlay_quad(size: Vector2, col: Color, priority: int) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = size
	mi.mesh = q
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = col
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.no_depth_test = true
	m.render_priority = priority
	mi.material_override = m
	mi.layers = 2
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


# ---------------------------------------------------------------------------
# Found pictures
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
		p.kind = fp.get("kind", "photo")
		p.solids = Slicer.capture(source, xf, Photo.T)
		p.pitch = xf.basis.get_euler().x
		p.texture = await _render_photo(xf)
		var pick := PhotoPickup.new()
		pick.key = "found_%d" % idx
		entities.add_child(pick)
		pick.position = fp["at"]
		pick.setup(p)
		_no_photo(pick)
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
	return Transform3D(Basis.from_euler(Vector3(pitch, yaw, 0)), player.eye_origin())


func _placement_transform(p: Photo) -> Transform3D:
	var pitch := player.pitch
	if absf(pitch - p.pitch) < SNAP_PITCH:
		pitch = p.pitch
	elif absf(pitch) < SNAP_LEVEL:
		pitch = 0.0
	var yaw := _snap_angle(player.yaw, PI * 0.5, SNAP_YAW)
	var b := Basis.from_euler(Vector3(pitch, yaw, 0)) * Basis(Vector3(0, 0, 1), roll)
	return Transform3D(b, player.eye_origin())


func toggle_camera_mode() -> void:
	if not has_camera or not ready_to_play:
		return
	camera_mode = not camera_mode
	Sfx.play("click", -8.0, 1.4 if camera_mode else 1.1)
	if camera_mode:
		lower_photo()


func take_photo() -> void:
	if not has_camera or not ready_to_play or completed:
		return
	if film == 0:
		Sfx.play("denied")
		hud.toast("Out of film — hold REWIND to get it back")
		return
	if film > 0:
		film -= 1
	camera_mode = false
	await _capture(_capture_transform())


## Take a photo from `xf` (the player's camera or a fixed camera).
func _capture(xf: Transform3D) -> void:
	var p := Photo.new()
	_photo_counter += 1
	p.title = "Photo %d" % _photo_counter
	p.kind = "photo"
	p.taken_ms = Time.get_ticks_msec()
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
	_commit()
	Sfx.play("shutter")
	hud.flash = 1.0
	p.texture = await _render_photo(xf)
	p.taken_ms = Time.get_ticks_msec()
	Sfx.play("eject", -4.0)
	hud.eject(photos.find(p))


func copy_photo() -> void:
	if raised < 0:
		hud.toast("Hold up the picture you want to copy")
		return
	var src: Photo = photos[raised]
	var p := Photo.new()
	p.solids = src.solids
	p.items = src.items
	p.texture = src.texture
	p.title = src.title + " (copy)"
	p.kind = src.kind
	p.pitch = src.pitch
	p.taken_ms = Time.get_ticks_msec()
	photos.append(p)
	_commit()
	for c in copiers:
		(c as Photocopier).scan()
	Sfx.play("eject", -4.0, 1.2)
	hud.eject(photos.size() - 1)


func raise_photo(i: int) -> void:
	if i < 0 or i >= photos.size() or not ready_to_play:
		return
	if raised == i:
		lower_photo()
		return
	raised = i
	roll = 0.0
	camera_mode = false
	_raise_t = 0.0
	Sfx.play("paper", -6.0)
	_update_held_photo()


func lower_photo() -> void:
	raised = -1
	_update_held_photo()


func rotate_photo(dir: int) -> void:
	if raised < 0:
		return
	roll = wrapf(roll + dir * PI * 0.5, -PI, PI)
	Sfx.play("paper", -10.0, 1.3)
	_update_held_photo()


func _update_held_photo() -> void:
	if raised < 0 or raised >= photos.size():
		raised = -1
		_held_root.visible = false
		return
	var p: Photo = photos[raised]
	var side := 2.0 * HOLD_DIST * Photo.T
	var fm: StandardMaterial3D = _held_frame.material_override
	var fq: QuadMesh = _held_frame.mesh
	match p.kind:
		"sketch":
			fq.size = Vector2(side * 1.06, side * 1.06)
			_held_frame.position = Vector3(0, 0, -0.001)
			fm.albedo_color = Color(0.95, 0.93, 0.87, 0.95)
		"painting":
			fq.size = Vector2(side * 1.16, side * 1.16)
			_held_frame.position = Vector3(0, 0, -0.001)
			fm.albedo_color = Color(0.5, 0.34, 0.22, 0.97)
		_:
			fq.size = Vector2(side * 1.12, side * 1.28)
			_held_frame.position = Vector3(0, -side * 0.08, -0.001)
			fm.albedo_color = Color(0.99, 0.98, 0.95, 0.92)
	var mat: StandardMaterial3D = _held_photo.material_override
	mat.albedo_texture = p.texture
	mat.albedo_color = Color(1, 1, 1, 0.86)
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
	_play_place_effect(p)
	lower_photo()
	_commit()
	for b in batteries:
		(b as Battery).sleeping = false
	_pending_unstick = 2
	Sfx.play("place")
	hud.flash = 0.45


## The held picture swells past the screen edges as it becomes the world.
func _play_place_effect(p: Photo) -> void:
	var fx := _overlay_quad((_held_photo.mesh as QuadMesh).size, Color(1, 1, 1, 0.85), 12)
	(fx.material_override as StandardMaterial3D).albedo_texture = p.texture
	fx.position = _held_root.position
	fx.rotation = _held_root.rotation
	player.camera.add_child(fx)
	var tw := create_tween().set_parallel().set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw.tween_property(fx, "scale", Vector3(3.2, 3.2, 1), 0.35)
	tw.tween_property(fx.material_override, "albedo_color:a", 0.0, 0.35)
	tw.chain().tween_callback(fx.queue_free)


func _process(delta: float) -> void:
	if not ready_to_play or _held_root == null:
		return
	# Held picture: slide up when raised, sway gently with the view, develop.
	if _held_root.visible:
		_raise_t = minf(_raise_t + delta * 4.0, 1.0)
		var e := 1.0 - pow(1.0 - _raise_t, 3.0)
		var look := hud.peek_look()
		_sway = _sway.lerp(Vector2(clampf(-look.x * 0.00012, -0.01, 0.01), clampf(look.y * 0.00012, -0.01, 0.01)), delta * 8.0)
		_held_root.position = Vector3(0.12 * (1.0 - e) + _sway.x, -0.25 * (1.0 - e) + _sway.y, -HOLD_DIST)
		_held_root.rotation = Vector3(0, 0, roll + _sway.x * 2.0 + 0.2 * (1.0 - e))
		var p: Photo = photos[raised] if raised >= 0 and raised < photos.size() else null
		_held_dev_mat.albedo_color.a = 1.0 - (p.developed() if p else 1.0)
	if cat:
		cat.watch(player.camera.global_position)


# ---------------------------------------------------------------------------
# Batteries, notes, cat
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


func _battery_in_reach() -> Battery:
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
	return best


func _note_in_reach() -> Note:
	for n in notes:
		if (n as Note).global_position.distance_to(player.camera.global_position) < 2.0:
			return n
	return null


func _cat_in_reach() -> bool:
	return cat != null and cat.global_position.distance_to(player.global_position) < 2.0


func _fixed_cam_in_reach() -> FixedCamera:
	for c in fixed_cams:
		if (c as FixedCamera).button_pos().distance_to(player.global_position + Vector3(0, 0.9, 0)) < 1.7:
			return c
	return null


func _copier_in_reach() -> bool:
	for c in copiers:
		if (c as Node3D).global_position.distance_to(player.global_position) < 2.2:
			return true
	return false


## What the context button would do right now (shown as its label).
func act_label() -> String:
	if held:
		return "DROP"
	if _battery_in_reach():
		return "GRAB"
	if _fixed_cam_in_reach():
		return "SNAP"
	if _copier_in_reach():
		return "COPY"
	if _note_in_reach():
		return "READ"
	if _cat_in_reach():
		return "PET"
	return ""


func interact() -> void:
	if not ready_to_play or completed:
		return
	if held:
		var drop := player.camera.global_transform * Vector3(0, -0.2, -0.9)
		held.global_transform = Transform3D(Basis(), drop)
		held.set_held(false)
		held.linear_velocity = player.velocity
		held = null
		Sfx.play("click", -6.0, 0.8)
		return
	var best := _battery_in_reach()
	if best:
		best.set_socket(-1)
		best.set_held(true)
		held = best
		Sfx.play("click", -4.0, 1.2)
		return
	var fc := _fixed_cam_in_reach()
	if fc:
		fc.fire()
		Sfx.play("click", -4.0)
		await _capture(fc.eye)
		return
	if _copier_in_reach():
		copy_photo()
		return
	var note := _note_in_reach()
	if note:
		Sfx.play("paper")
		hud.show_note(note.title, note.text)
		return
	if _cat_in_reach():
		cat.pet()
		var extra := ["Mrrrp.", "Purrrr…", "You're doing great. Probably."]
		hud.say("Miso", [extra[_cat_line % extra.size()]])
		_cat_line += 1
		return
	hud.toast("Nothing to grab")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

func _physics_process(_delta: float) -> void:
	if not ready_to_play:
		return
	var rewinding := (hud.wants_rewind() or _auto_rewind > 0) and not completed
	Sfx.loop("rewind", rewinding, -10.0)
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
			Sfx.play("pickup")
			hud.toast("Found: " + pick.photo.title + " — tap it to hold it up")

	for id in sockets.keys():
		(sockets[id] as PowerSocket).update(batteries)
	for g in gates:
		(g as Gate).update(sockets)
	if teleporter:
		teleporter.update_sockets(batteries, player.global_position)
	for pad in hub_pads:
		(pad as Teleporter).update_sockets([], player.global_position)

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
		KEY_H: next_hint()
		_:
			var n: int = event.physical_keycode - KEY_1
			if n >= 0 and n < 9:
				raise_photo(n)


## Hints come one at a time, from a gentle nudge to the full answer.
func next_hint() -> void:
	var hints: Array = level.get("hints", [level["hint"]])
	if hints.is_empty():
		return
	var i := mini(hint_index, hints.size() - 1)
	hint_index += 1
	if cat:
		cat.pet()
	hud.say("Miso", ["Hint %d/%d — %s" % [i + 1, hints.size(), hints[i]]])


func on_hud_action(name: String) -> void:
	match name:
		"hint": next_hint()
		"jump": player.jump_requested = true
		"act": interact()
		"cam": toggle_camera_mode()
		"shutter": take_photo()
		"place": place_photo()
		"rotl": rotate_photo(-1)
		"rotr": rotate_photo(1)
		"restart": exit_requested.emit(HUB if is_hub else level_index)
		"menu": exit_requested.emit(MENU)
		"hub", "next": exit_requested.emit(HUB)
		_:
			if name.begins_with("photo_"):
				raise_photo(int(name.substr(6)))


func _on_teleporter_entered() -> void:
	if completed:
		return
	completed = true
	player.frozen = true
	Sfx.play("teleport")
	Progress.mark_completed(level_index)
	hud.flash = 1.0
	# A keepsake: the game snaps one last photo of the restored memory.
	var keep := await _render_photo(Transform3D(Basis.from_euler(Vector3(deg_to_rad(-8), player.yaw + PI, 0)),
		player.eye_origin() + Vector3(0, 1.2, 0)))
	hud.show_complete(level_index + 1 >= Levels.count(), keep, Levels.NAMES[level_index])


func _on_hub_pad(i: int) -> void:
	if completed:
		return
	completed = true
	player.frozen = true
	Sfx.play("teleport")
	hud.fade_out()
	await get_tree().create_timer(0.6).timeout
	exit_requested.emit(i)


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
