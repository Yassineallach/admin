class_name CrosswordBoard
extends Control
## Draws a PuzzleState and turns taps into cell selections.

signal cell_tapped(pos: Vector2i)

var state: PuzzleState
var accent := UI.SKY
var _pop := {}       # Vector2i -> remaining seconds of a bounce
var _flash := {}     # Vector2i -> remaining seconds of a red flash
var _glow := {}      # Vector2i -> remaining seconds of the "solved" shimmer
var _cell := 40.0
var _origin := Vector2.ZERO
var _intro := 0.0

const POP_TIME := 0.32
const FLASH_TIME := 0.6
const GLOW_TIME := 0.9

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	resized.connect(queue_redraw)

func bind(s: PuzzleState, color: Color) -> void:
	state = s
	accent = color
	_intro = 1.0
	queue_redraw()

func pop_cell(p: Vector2i) -> void:
	_pop[p] = POP_TIME

func flash_word(i: int) -> void:
	for c in state.word_cells(i):
		_flash[c] = FLASH_TIME

func celebrate_word(i: int) -> void:
	var cs := state.word_cells(i)
	for k in cs.size():
		_glow[cs[k]] = GLOW_TIME + k * 0.06
		_pop[cs[k]] = POP_TIME + k * 0.06

func celebrate_all() -> void:
	for p in state.cells.keys():
		var d: float = (p.x + p.y) * 0.05
		_glow[p] = GLOW_TIME + d
		_pop[p] = POP_TIME + d

func _process(delta: float) -> void:
	var dirty := _intro > 0.0
	_intro = maxf(0.0, _intro - delta * 0.9)
	for dict: Dictionary in [_pop, _flash, _glow]:
		for k in dict.keys():
			dict[k] -= delta
			if dict[k] <= 0.0:
				dict.erase(k)
			dirty = true
	if dirty:
		queue_redraw()

func _layout() -> void:
	var gap := 8.0
	_cell = minf((size.x - gap) / state.width, (size.y - gap) / state.height)
	_cell = minf(_cell, 92.0)
	var board := Vector2(state.width, state.height) * _cell
	_origin = (size - board) * 0.5

func _gui_input(event: InputEvent) -> void:
	if state == null:
		return
	var pressed: bool = (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT) \
		or (event is InputEventScreenTouch and event.pressed)
	if not pressed:
		return
	var local: Vector2 = event.position
	var p := Vector2i(floori((local.x - _origin.x) / _cell), floori((local.y - _origin.y) / _cell))
	if state.cells.has(p):
		cell_tapped.emit(p)
		accept_event()

func _draw() -> void:
	if state == null or state.width == 0:
		return
	_layout()
	var active := state.current_word()
	var active_cells := state.word_cells(active) if active >= 0 else []
	var f := UI.font(true)
	var fr := UI.font(false)
	var radius := int(_cell * 0.2)
	var border := maxf(2.0, _cell * 0.045)
	var lip := maxf(3.0, _cell * 0.07)
	var numbers := {}
	for p in state.placements:
		numbers[Vector2i(p["col"], p["row"])] = p["number"]

	for pos in state.cells.keys():
		var cell: Dictionary = state.cells[pos]
		var appear := clampf((1.0 - _intro) * 2.2 - (pos.x + pos.y) * 0.05, 0.0, 1.0)
		var bounce := 1.0
		if _pop.has(pos):
			var k: float = clampf(_pop[pos] / POP_TIME, 0.0, 1.0)
			bounce = 1.0 + sin(k * PI) * 0.14
		var r := _cell_rect(pos, bounce * lerpf(0.6, 1.0, ease(appear, 0.4)))
		# Tile colours: face / outline / letter.
		var face := UI.WHITE
		var edge := UI.CLOUD
		var ink := UI.INK
		if cell["locked"]:
			face = UI.LEAF_PALE
			edge = Color("a5ed6e")
			ink = UI.LEAF_LIP
		if pos in active_cells and not cell["locked"]:
			face = Color("f1faff")
			edge = Color("84d8ff")
			ink = UI.SKY_LIP
		if pos == state.cursor and not state.is_complete():
			face = UI.SKY_PALE
			edge = UI.SKY
			ink = UI.SKY_LIP
		if _flash.has(pos):
			var t: float = clampf(_flash[pos] / FLASH_TIME, 0.0, 1.0)
			face = face.lerp(UI.BERRY_PALE, t)
			edge = edge.lerp(UI.BERRY, t)
			ink = ink.lerp(UI.BERRY, t)
		if _glow.has(pos):
			var g: float = sin(clampf(_glow[pos] / GLOW_TIME, 0.0, 1.0) * PI)
			face = face.lerp(Color("fff5c2"), g * 0.9)
			edge = edge.lerp(UI.SUN, g)
		var sb := StyleBoxFlat.new()
		sb.bg_color = face
		sb.set_corner_radius_all(radius)
		sb.set_border_width_all(int(border))
		sb.border_width_bottom = int(border + lip)
		sb.border_color = edge
		sb.anti_aliasing = true
		draw_style_box(sb, r)

		if numbers.has(pos):
			var ns := int(_cell * 0.22)
			draw_string(fr, r.position + Vector2(_cell * 0.11, ns + _cell * 0.07), str(numbers[pos]), HORIZONTAL_ALIGNMENT_LEFT, -1, ns, Color(UI.STONE, 0.9))

		if cell["val"] != "":
			var fs := int(_cell * 0.54)
			var baseline := r.position.y + (r.size.y - lip) * 0.5 + fs * 0.36
			draw_string(f, Vector2(r.position.x, baseline), cell["val"], HORIZONTAL_ALIGNMENT_CENTER, r.size.x, fs, ink)

	# Blinking caret on the cursor tile.
	if state.cells.has(state.cursor) and not state.is_complete() and state.cells[state.cursor]["val"] == "":
		var r := _cell_rect(state.cursor, 1.0)
		var blink := 0.35 + 0.65 * absf(sin(Time.get_ticks_msec() * 0.004))
		var bar := Rect2(r.get_center().x - _cell * 0.04, r.position.y + _cell * 0.22, maxf(3.0, _cell * 0.07), _cell * 0.44)
		draw_rect(bar, Color(UI.SKY, blink))
		queue_redraw()

func _cell_rect(pos: Vector2i, scale_f: float) -> Rect2:
	var pad := _cell * 0.05
	var full := Rect2(_origin + Vector2(pos) * _cell, Vector2.ONE * _cell).grow(-pad)
	var c := full.get_center()
	var s := full.size * scale_f
	return Rect2(c - s * 0.5, s)
