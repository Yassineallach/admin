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
