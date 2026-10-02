class_name Photo
extends RefCounted
## A photograph: the slice of the world that was inside the camera frustum,
## stored in camera-local space, plus copies of any items it caught.

## Half-angle tangent of the (square) photo frustum. Shared by every photo so
## the on-screen viewfinder frame and the held polaroid line up exactly.
const T := 0.45

var solids: Array = []
## [{ "type": "battery", "xf": Transform3D (camera-local) }]
var items: Array = []
var texture: Texture2D
var title: String = "Photo"
## Camera pitch (radians) the photo was taken at; placement snaps to it.
var pitch: float = 0.0
## "photo" (polaroid), "sketch" (pencil drawing) or "painting" (framed canvas).
var kind: String = "photo"
## When the picture was taken (msec): used for the developing animation.
var taken_ms: int = -100000


## 0 = still white, 1 = fully developed.
func developed() -> float:
	return clampf((Time.get_ticks_msec() - taken_ms) / 1800.0, 0.0, 1.0)
