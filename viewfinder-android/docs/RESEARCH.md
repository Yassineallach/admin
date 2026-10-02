# Viewfinder: research notes

These notes cover what *Viewfinder* is, how its central mechanic works, and how this
project rebuilds that mechanic for Android in Godot 4.7.

## 1. The game

| | |
|---|---|
| Developer | Sad Owl Studios (UK), directed by **Matt Stark** |
| Publisher | Thunderful |
| Engine | Unity |
| Release | PS5 + Windows, 18 July 2023 · PS4, Dec 2023 · Xbox Series X/S, 12 Aug 2025 · Nintendo Switch, 3 Dec 2025 |
| Mobile | **No official Android or iOS version.** This project fills that gap as a fan-made homage. |
| Awards | BAFTA Games Awards 2024: *New Intellectual Property* and *British Game*. Nominated at The Game Awards 2023 (Best Debut Indie, Best Independent Game) and the Golden Joystick Awards 2023 |

**Origin.** In late 2019 Matt Stark posted a short clip of a Unity prototype in
which a polaroid photo overwrote the game world. The clip went viral. He left
university to build it into a full game, and the project was shown at GDC's
Experimental Gameplay Workshop. His early tweets track the progress: the "polaroid
game", then *"the effect can now handle collisions and multiple photos"*, then the
working title *Viewfinder* (Feb 2020).

**Premise.** You explore a pastel, dream-like simulation built by a team of
researchers. You meet **Cait**, a virtual cat (you can pet her), who guides you
through the story. The world is split into **five hubs**, one for each former
researcher and styled after their interests. Most puzzles end at a **teleporter**
that has to be powered, usually by carrying **batteries** to it.

## 2. Core mechanics

1. **Photos become places.** You hold up a 2D photograph and line it up with the
   world. When you place it, its contents turn into real 3D geometry, seen from
   the angle you are looking from. Everything the photo's frame covers, *all the
   way to the horizon*, is replaced. That includes deleting what was there.
2. **The instant camera.** In later chapters you can take your own photos, so you
   can copy part of the world and paste it somewhere else. Some levels limit how
   much film you have.
3. **Found images.** Photos, postcards, paintings and drawings lying around the
   world work the same way. A drawing turns into a 3D place in its own art style.
4. **Copying objects.** Anything inside a photo is duplicated when you place it,
   including batteries. This is the standard way to get a second battery.
5. **Rotating photos.** You can roll the photo before placing it, so walls can
   become floors.
6. **Rewind.** Because a bad placement can soft-lock you, the game lets you rewind
   time freely. Later puzzles assume you will use it.
7. **Later puzzle elements.** Filters, photocopiers, fixed cameras, and timed or
   limited-shot rooms are added on top of the basics.

## 3. How the effect works technically

Stark's own description of the prototype (via 80.lv and interviews):

> When the player takes a photo, the system **duplicates the environment, makes it
> greyscale and slices the meshes** to remove anything outside the photo. When they
> place it into the world, it **slices the environment's meshes to make a hole** for
> the photo. The hard part was cutting meshes with thousands of triangles in a
> fraction of a second.

Put another way, a photo is the **infinite square pyramid (frustum)** that starts
at the camera:

* **Capture:** `photo = world ∩ frustum(camera)`, stored relative to the camera.
* **Place:** `world = (world − frustum(view)) ∪ transform(photo, view)`.

Since the photo is stored relative to the camera, placing it from a different pose
moves its contents rigidly. That is why lining up the polaroid with the world
lines up the geometry. Community Unreal recreations work the same way: a frustum
test, a runtime copy of actors, and mesh cutting with Geometry Script.

## 4. How this project implements it (Godot 4.7)

| Viewfinder idea | Implementation here |
|---|---|
| Mesh slicing | Every level surface is a **convex polyhedron** (`Solid`). Clipping a convex solid with a plane (Sutherland–Hodgman per face, plus a cap polygon) always gives another convex solid, so the slicer is exact and fast. It has no CSG edge cases. |
| Capture | `Slicer.capture` clips each solid against the 4 inward planes of the frustum and stores the pieces in camera space. |
| Place / carve | `Slicer.carve` splits each straddling solid into the convex parts that stick out of each frustum side, then drops the part inside. `Slicer.place` then pastes the photo's solids using the new camera transform. |
| Collision | Each solid becomes a `ConvexPolygonShape3D`. The whole level is **one batched mesh with one material**, so it costs one draw call on mobile GPUs. |
| Photo image | A `SubViewport` camera with the photo's exact FOV renders a 512² texture, which is shown on the polaroid. |
| Lining up | The held polaroid is a quad sized to cover exactly the photo frustum (`2·d·tan`), so what you see is what you place. Pitch and yaw snap to the capture angle or to level and 90° when you are within a few degrees, which helps a lot with touch controls. |
| Object copies | Batteries inside the frustum are recorded in camera space and spawned again on placement. Batteries inside the placement frustum are deleted. |
| Rewind | Every physics tick records the player and battery states. Each world-changing event (capture, place, pickup) pushes an immutable snapshot. Solids are never mutated, so a snapshot is only an array of references. Holding REWIND plays the timeline backwards at 2× speed. Falling off the world rewinds automatically. |
| Teleporter | Has battery sockets and its own pad collider, so it still works if a photo carves away the floor under it. |

Performance with GDScript on desktop is about 0.5–1 ms per capture or placement,
plus 0.3 ms to rebuild the mesh (see `tests/`). That leaves plenty of headroom on
phones.

## 5. Level design (6 original puzzles)

Each level teaches one Viewfinder idea:

1. **Found Photograph:** pick up a photo of a bridge and place it over a gap.
2. **Point and Shoot:** photograph a ramp behind you and paste it against a sheer cliff.
3. **Through the Window:** photograph a battery inside a sealed room to get a copy.
4. **Breakthrough:** a photo of empty space cuts a hole through a wall.
5. **Look Up:** a tower photographed from inside, looking straight up, becomes a
   horizontal tunnel across a chasm. The tower's half-width equals eye height, so
   the tunnel floor lines up with the ground exactly.
6. **Darkroom:** limited film, two batteries, and a postcard showing a ramp. It
   teaches you to aim *down* when copying objects, because a photo takes
   everything behind the object too.

## Sources

* Wikipedia – [Viewfinder (video game)](https://en.wikipedia.org/wiki/Viewfinder_(video_game))
* 80.lv – [Tutorial: Viewfinder's Reality-Bending Mechanic in Unity](https://80.lv/articles/tutorial-viewfinder-s-reality-bending-mechanic-in-unity)
* 80.lv – [A Mind-Bending Game Lets You Transform Environments](https://80.lv/articles/a-mind-bending-game-lets-you-transform-environments)
* Matt Stark on X – [working title](https://x.com/mattstark256/status/1224742431381512192), [collisions & multiple photos](https://x.com/mattstark256/status/1213156890475212800)
* Reviews – [PC Gamer](https://pcgamer.com/viewfinder-review), [GamesRadar](https://gamesradar.com/viewfinder-review), [Shacknews](https://shacknews.com/article/136279/viewfinder-review-score), [Checkpoint Gaming](https://checkpointgaming.net/reviews/2023/07/viewfinder-review-a-world-worth-capturing/), [Film Stories preview](https://filmstories.co.uk/features/viewfinder-preview-this-should-be-impossible/)
* Ports – [Nintendo Life (Switch)](https://www.nintendolife.com/news/2025/07/acclaimed-puzzler-viewfinder-bends-reality-on-switch-this-winter), [Digitally Downloaded (Xbox/Switch)](https://www.digitallydownloaded.net/2025/07/viewfinder-xbox-nintend-switch-announcement.html)
* BAFTA – [Creative Bloq interview](https://creativebloq.com/3d/video-game-design/viewfinders-sophie-knowles-reflects-on-her-bafta-breakthrough-joking-how-its-weird-to-be-associated-with-tom-holland-and-florence-pugh)
* Unreal recreation – [Fab listing](https://www.fab.com/listings/4073449a-9a03-4581-9ac4-3a8159e03860)
* Godot – [4.7.2 release](https://godotengine.org/download/archive/4.7.2-stable/), [Exporting for Android (4.7)](https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_android.html)
