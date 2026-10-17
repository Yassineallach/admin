class_name LetterKeyboard
extends VBoxContainer
## On-screen keyboard using the target language's layout plus its accented letters.

signal letter(c: String)
signal erase

var _keys := {}

func build(target: String, accent: Color) -> void:
	for c in get_children():
		c.queue_free()
	_keys.clear()
	add_theme_constant_override("separation", 10)
	var info: Array = Vocab.keyboard_rows(target)
	var rows: Array = info[0]
	var extras: Array = info[1]
	if not extras.is_empty():
		add_child(_row(extras, Color("4b3d8f"), false))
	for i in rows.size():
		add_child(_row(Array(rows[i].split("")), Color("2c2360"), i == rows.size() - 1))

func _row(chars: Array, color: Color, with_erase: bool) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 8)
	for ch in chars:
		var b := _key(ch, color)
		b.pressed.connect(func(): letter.emit(ch))
		h.add_child(b)
		_keys[ch] = b
	if with_erase:
		var e := _key("⌫", Color("ff5c7a"))
		e.custom_minimum_size.x = 96
		e.pressed.connect(func(): erase.emit())
		h.add_child(e)
	return h

func _key(ch: String, color: Color) -> Button:
	var b := Button.new()
	b.text = ch
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(56, 84)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_font_override("font", UI.font(true))
	b.add_theme_font_size_override("font_size", 32)
	var n := UI.box(color, 14)
	n.content_margin_left = 0
	n.content_margin_right = 0
	n.border_width_bottom = 6
	n.border_color = color.darkened(0.45)
	var p := UI.box(color.lightened(0.25), 14)
	p.content_margin_left = 0
	p.content_margin_right = 0
	p.border_width_top = 4
	p.border_color = Color(0, 0, 0, 0)
	b.add_theme_stylebox_override("normal", n)
	b.add_theme_stylebox_override("hover", n)
	b.add_theme_stylebox_override("pressed", p)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.button_down.connect(func(): Sfx.play("key", randf_range(0.95, 1.08)); Sfx.buzz(8))
	return b
