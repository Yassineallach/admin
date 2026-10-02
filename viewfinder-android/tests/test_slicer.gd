extends SceneTree
## Headless unit tests for the slicing core.
## Run: godot --headless --path . --script res://tests/test_slicer.gd

var failures := 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("  ok   ", msg)
	else:
		failures += 1
		printerr("  FAIL ", msg)


func total_volume(list: Array) -> float:
	var v := 0.0
	for s in list:
		v += (s as Solid).volume()
	return v


func _init() -> void:
	print("Slicer tests")
	var cube := Solid.box(Vector3.ZERO, Vector3(2, 2, 2), Color.WHITE)
	check(absf(cube.volume() - 8.0) < 1e-4, "box volume = 8")

	var halves := Slicer.split(cube, Plane(Vector3.UP, 0.0))
	check(halves[0] != null and halves[1] != null, "split produces two halves")
	check(absf(halves[0].volume() - 4.0) < 1e-3, "upper half volume = 4")
	check(absf(halves[1].volume() - 4.0) < 1e-3, "lower half volume = 4")
	check(halves[0].faces.size() == 6, "half is a closed box (6 faces)")

	var diag := Slicer.split(cube, Plane(Vector3(1, 1, 1).normalized(), 0.0))
	check(absf(diag[0].volume() + diag[1].volume() - 8.0) < 1e-3, "diagonal split conserves volume")
	check(diag[0].faces.size() == 7, "diagonal half has hexagonal cap (7 faces)")

	check(Slicer.clip(cube, Plane(Vector3.UP, 5.0)) == null, "clip fully outside returns null")
	check(Slicer.clip(cube, Plane(Vector3.UP, -5.0)) == cube, "clip fully inside returns same solid")

	var ramp := Solid.ramp(Vector3(0, 0, 0), Vector3.FORWARD, 4.0, 2.0, 2.0, Color.RED)
	check(absf(ramp.volume() - 8.0) < 1e-3, "ramp volume = L*W*H/2")

	# Carving with a camera looking down -Z from z=+5 must remove the frustum
	# region and keep the rest; carve + capture must partition the volume.
	var cam := Transform3D(Basis(), Vector3(0, 0, 5))
	var t := 0.45
	var world := [Solid.box(Vector3(0, 0, 0), Vector3(10, 2, 2), Color.WHITE)]
	var kept := Slicer.carve(world, cam, t)
	var taken := Slicer.capture(world, cam, t)
	check(kept.size() >= 2, "carve splits straddling solid into pieces (%d)" % kept.size())
	check(absf(total_volume(kept) + total_volume(taken) - 40.0) < 0.01,
		"carve + capture partition the volume (%.3f + %.3f)" % [total_volume(kept), total_volume(taken)])

	# Placing a captured photo back from the same camera reconstructs the volume.
	var placed := Slicer.place(world, taken, cam, t)
	check(absf(total_volume(placed) - 40.0) < 0.01, "place from same viewpoint is identity on volume")

	# Captured pieces are camera-local: they must lie in front of the camera.
	var ok_local := true
	for s in taken:
		for p in (s as Solid).points():
			if p.z > 1e-3:
				ok_local = false
	check(ok_local, "captured solids are in camera space (z <= 0)")

	check(Slicer.point_in_frustum(cam, t, Vector3(0, 0, 0)), "origin is inside frustum")
	check(not Slicer.point_in_frustum(cam, t, Vector3(5, 0, 0)), "far side point is outside frustum")

	var mesh := SolidWorld.build_mesh(placed, null)
	check(mesh.get_surface_count() == 1, "batched mesh has one surface")

	print("done, failures: ", failures)
	quit(1 if failures > 0 else 0)
