class_name Player
extends CharacterBody3D
## First-person controller driven by the touch HUD (or keyboard on desktop).

const SPEED := 4.5
const ACCEL := 30.0
const JUMP_VELOCITY := 5.2
const GRAVITY := 14.0
const EYE_HEIGHT := 1.5
const FOV := 70.0

var yaw: float = 0.0
var pitch: float = 0.0
var move_input := Vector2.ZERO  # x = strafe, y = forward
var jump_requested := false
var frozen := false

signal footstep
signal landed(strength: float)

var _bob_t := 0.0
var _bob_amt := 0.0
var _land_dip := 0.0
var _was_on_floor := true
var _fall_speed := 0.0

var head: Node3D
var camera: Camera3D
var hold_point: Node3D


func _init() -> void:
	collision_layer = 4
	collision_mask = 1 | 2
	floor_snap_length = 0.3
	floor_max_angle = deg_to_rad(50.0)
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.75
	cs.shape = cap
	cs.position = Vector3(0, 0.875, 0)
	add_child(cs)
	head = Node3D.new()
	head.position = Vector3(0, EYE_HEIGHT, 0)
	add_child(head)
	camera = Camera3D.new()
	camera.fov = FOV
	camera.near = 0.05
	camera.far = 400.0
	camera.cull_mask = 0xFFFFF  # sees layer 2 (held photo) too
	head.add_child(camera)
	hold_point = Node3D.new()
	hold_point.position = Vector3(0.35, -0.35, -0.75)
	camera.add_child(hold_point)


func look(delta_px: Vector2) -> void:
	var sens: float = 0.0045 * float(Progress.settings.get("look_sensitivity", 1.0))
	var inv := -1.0 if Progress.settings.get("invert_y", false) else 1.0
	yaw -= delta_px.x * sens
	pitch = clampf(pitch - delta_px.y * sens * inv, deg_to_rad(-89.0), deg_to_rad(89.0))
	_apply_look()


func set_look(y: float, p: float) -> void:
	yaw = y
	pitch = p
	_apply_look()


func _apply_look() -> void:
	rotation = Vector3(0, yaw, 0)
	head.rotation = Vector3(pitch, 0, 0)


func eye_transform() -> Transform3D:
	return camera.global_transform


## Steady eye position (without head-bob): photos are taken / placed from here
## so that bobbing never changes where a picture lands.
func eye_origin() -> Vector3:
	return head.global_position


func _physics_process(delta: float) -> void:
	if frozen:
		return
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif jump_requested:
		velocity.y = JUMP_VELOCITY
	jump_requested = false
	var dir := (transform.basis * Vector3(move_input.x, 0, -move_input.y))
	dir.y = 0
	if dir.length() > 1.0:
		dir = dir.normalized()
	var target := dir * SPEED
	var horiz := Vector3(velocity.x, 0, velocity.z).move_toward(target, ACCEL * delta)
	velocity.x = horiz.x
	velocity.z = horiz.z
	if not is_on_floor():
		_fall_speed = maxf(_fall_speed, -velocity.y)
	move_and_slide()
	_update_bob(delta)


func _update_bob(delta: float) -> void:
	var on_floor := is_on_floor()
	if on_floor and not _was_on_floor and _fall_speed > 2.5:
		var k := clampf((_fall_speed - 2.5) / 8.0, 0.0, 1.0)
		_land_dip = 0.05 + 0.1 * k
		landed.emit(k)
	if on_floor:
		_fall_speed = 0.0
	_was_on_floor = on_floor
	var speed := Vector2(velocity.x, velocity.z).length()
	var target_amt := clampf(speed / SPEED, 0.0, 1.0) if on_floor else 0.0
	_bob_amt = lerpf(_bob_amt, target_amt, clampf(delta * 8.0, 0.0, 1.0))
	if _bob_amt > 0.05:
		var prev := _bob_t
		_bob_t += delta * (6.0 + speed * 0.9)
		# One step per half bob cycle.
		if floor(prev / PI) != floor(_bob_t / PI):
			footstep.emit()
	_land_dip = move_toward(_land_dip, 0.0, delta * 0.6)
	camera.position = Vector3(cos(_bob_t) * 0.018 * _bob_amt,
		absf(sin(_bob_t)) * 0.035 * _bob_amt - _land_dip, 0.0)
	camera.rotation.z = cos(_bob_t) * 0.006 * _bob_amt


## Push the player upward until the capsule no longer overlaps level geometry.
## Used after a photo is placed on top of where the player is standing.
func unstick() -> void:
	var space := get_world_3d().direct_space_state
	var q := PhysicsShapeQueryParameters3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	q.shape = cap
	q.collision_mask = 1
	for i in 60:
		q.transform = Transform3D(Basis(), global_position + Vector3(0, 0.875 + i * 0.25, 0))
		if space.intersect_shape(q, 1).is_empty():
			if i > 0:
				global_position += Vector3(0, i * 0.25, 0)
				velocity = Vector3.ZERO
			return
