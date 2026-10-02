class_name Mat
extends RefCounted
## Material and art-style ids shared by Solid, the mesh builder and the world
## shader (scripts/../shaders/world.gdshader). Keep the numbers in sync.

const PLASTER := 0
const GRASS := 1
const TILE := 2
const BRICK := 3
const WOOD := 4
const WATER := 5
const ROOF := 6
const METAL := 7
const FOLIAGE := 8
const ROCK := 9
const PLANKS := 10
const GLOW := 11
## Archive stone (anchored solids): dark slate with glowing rune lines.
const ARCHIVE := 12
## Window glass: deep teal with a sky reflection and highlight streaks.
const GLASS := 13
## Board-formed concrete (brutalist blocks): pale, with plank imprints.
const CONCRETE := 14
## Solar panel cells.
const SOLAR := 15

const STYLE_NORMAL := 0
## Pencil on paper: what you get from a found sketch.
const STYLE_SKETCH := 1
## Soft watercolour: what you get from a found painting.
const STYLE_PAINT := 2
## Faded sepia: old photographs.
const STYLE_SEPIA := 3
