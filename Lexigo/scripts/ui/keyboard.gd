class_name LetterKeyboard
extends VBoxContainer
## Letter bank: only the tiles the current word needs, shuffled, plus a few
## decoys. Used tiles grey out and come back when a letter is erased.

signal letter(c: String)
signal erase

var _flow: HFlowContainer
var _tiles: Array = []
var _buttons: Array[Button] = []
var _back: Button
var _word := -2
var _signature := ""

func build(_target: String, _accent: Color) -> void:
	add_theme_constant_override("separation", 12)
	custom_minimum_size.y = 2 * 100 + 12
	_flow = HFlowContainer.new()
	_flow.alignment = FlowContainer.ALIGNMENT_CENTER
	_flow.add_theme_constant_override("h_separation", 10)
	_flow.add_theme_constant_override("v_separation", 12)
	_flow.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(_flow)
	_back = _tile("⌫")
	_back.custom_minimum_size.x = 120
	for c in ["font_color", "font_hover_color", "font_pressed_color"]:
		_back.add_theme_color_override(c, UI.BERRY)
	_back.pressed.connect(func(): erase.emit())
	_flow.add_child(_back)

## Rebuilds the tiles when the word (or its tile set) changes, otherwise
## just refreshes which tiles are used.
func show_word(state: PuzzleState, w: int) -> void:
	var tiles: Array = [] if w < 0 or state.solved.has(w) else state.bank_tiles(w)
	var sig := "%d|%s" % [w, "".join(tiles)]
	if sig != _signature:
		_signature = sig
		_rebuild(tiles, w != _word)
		_word = w
	_back.visible = not tiles.is_empty()
	if tiles.is_empty():
		return
	var used := state.bank_used(w, tiles)
	for k in _buttons.size():
		_buttons[k].disabled = used[k]

func _rebuild(tiles: Array, animate: bool) -> void:
	for b in _buttons:
		b.queue_free()
	_buttons.clear()
	_tiles = tiles
	for k in tiles.size():
		var b := _tile(tiles[k])
		var ch: String = tiles[k]
		b.pressed.connect(func(): letter.emit(ch))
		_flow.add_child(b)
		_buttons.append(b)
		_flow.move_child(_back, -1)
		if animate:
			b.modulate.a = 0.0
			b.scale = Vector2.ONE * 0.6
			var tw := b.create_tween().set_parallel()
			tw.tween_interval(k * 0.035)
			tw.chain().tween_property(b, "modulate:a", 1.0, 0.15)
			tw.tween_property(b, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			b.resized.connect(func(): b.pivot_offset = b.size * 0.5, CONNECT_ONE_SHOT)

func _tile(ch: String) -> Button:
	var b := Button.new()
	b.text = ch
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(88, 100)
	b.add_theme_font_override("font", UI.font(true))
	b.add_theme_font_size_override("font_size", 44)
	UI.style_button(b, "neutral", 20)
	for s in ["normal", "hover", "pressed", "disabled"]:
		var st: StyleBoxFlat = b.get_theme_stylebox(s).duplicate()
		st.content_margin_left = 0
		st.content_margin_right = 0
		if s == "disabled":
			# An empty slot where the tile was.
			st.bg_color = UI.CLOUD
			st.border_color = UI.CLOUD
			st.border_width_bottom = UI.BORDER
		b.add_theme_stylebox_override(s, st)
	for c in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(c, UI.INK)
	b.add_theme_color_override("font_disabled_color", Color(0, 0, 0, 0))
	b.button_down.connect(func(): Sfx.play("key", randf_range(0.95, 1.08)); Sfx.buzz(8))
	return b
