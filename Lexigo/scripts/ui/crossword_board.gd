class_name CrosswordBoard
extends Control
## Draws a PuzzleState and turns taps into cell selections.

signal cell_tapped(pos: Vector2i)

var state: PuzzleState
var accent := UI.ACCENT
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
	var radius := int(_cell * 0.18)
	var numbers := {}
	for p in state.placements:
		numbers[Vector2i(p["col"], p["row"])] = p["number"]

	# Soft shadow plate under every cell for depth.
	for pos in state.cells.keys():
		var r := _cell_rect(pos, 1.0)
		var sh := UI.box(Color(0, 0, 0, 0.28), radius)
		draw_style_box(sh, Rect2(r.position + Vector2(0, _cell * 0.07), r.size))

	for pos in state.cells.keys():
		var cell: Dictionary = state.cells[pos]
		var appear := clampf((1.0 - _intro) * 2.2 - (pos.x + pos.y) * 0.05, 0.0, 1.0)
		var bounce := 1.0
		if _pop.has(pos):
			var k: float = clampf(_pop[pos] / POP_TIME, 0.0, 1.0)
			bounce = 1.0 + sin(k * PI) * 0.16
		var r := _cell_rect(pos, bounce * lerpf(0.6, 1.0, ease(appear, 0.4)))
		var bg := UI.PAPER
		if cell["locked"]:
			bg = UI.GREEN.lerp(Color.WHITE, 0.72)
		if pos in active_cells:
			bg = accent.lerp(Color.WHITE, 0.62)
		if pos == state.cursor:
			bg = accent.lerp(Color.WHITE, 0.15)
		if _flash.has(pos):
			bg = bg.lerp(UI.RED, clampf(_flash[pos] / FLASH_TIME, 0.0, 1.0))
		if _glow.has(pos):
			var g: float = clampf(_glow[pos] / GLOW_TIME, 0.0, 1.0)
			bg = bg.lerp(UI.GOLD, sin(g * PI) * 0.8)
		var face := UI.box(bg, radius)
		face.border_width_bottom = int(maxf(2.0, _cell * 0.06))
		face.border_color = bg.darkened(0.18)
		draw_style_box(face, r)

		if numbers.has(pos):
			var ns := int(_cell * 0.22)
			draw_string(fr, r.position + Vector2(_cell * 0.09, ns + _cell * 0.05), str(numbers[pos]), HORIZONTAL_ALIGNMENT_LEFT, -1, ns, Color(UI.INK, 0.55))

		if cell["val"] != "":
			var fs := int(_cell * 0.56)
			var col := UI.INK
			if cell["locked"]:
				col = Color("13804a")
			elif pos == state.cursor:
				col = Color.WHITE
			var baseline := r.position.y + r.size.y * 0.5 + fs * 0.36
			draw_string(f, Vector2(r.position.x, baseline), cell["val"], HORIZONTAL_ALIGNMENT_CENTER, r.size.x, fs, col)

	# Caret under the cursor cell.
	if state.cells.has(state.cursor) and not state.is_complete():
		var r := _cell_rect(state.cursor, 1.0)
		var blink := 0.55 + 0.45 * sin(Time.get_ticks_msec() * 0.008)
		var bar := Rect2(r.position.x + r.size.x * 0.25, r.end.y - _cell * 0.16, r.size.x * 0.5, maxf(3.0, _cell * 0.05))
		draw_rect(bar, Color(1, 1, 1, blink))
		queue_redraw()

func _cell_rect(pos: Vector2i, scale_f: float) -> Rect2:
	var pad := _cell * 0.05
	var full := Rect2(_origin + Vector2(pos) * _cell, Vector2.ONE * _cell).grow(-pad)
	var c := full.get_center()
	var s := full.size * scale_f
	return Rect2(c - s * 0.5, s)
