class_name LetterKeyboard
extends VBoxContainer
## On-screen keyboard using the target language's layout plus its accented
## letters. Keys look like word-bank tiles: white, outlined, with a lip.

signal letter(c: String)
signal erase

func build(target: String, _accent: Color) -> void:
	for c in get_children():
		c.queue_free()
	add_theme_constant_override("separation", 10)
	var info: Array = Vocab.keyboard_rows(target)
	var rows: Array = info[0]
	var extras: Array = info[1]
	if not extras.is_empty():
		add_child(_row(extras, true, false))
	for i in rows.size():
		add_child(_row(Array(rows[i].split("")), false, i == rows.size() - 1))

func _row(chars: Array, accent_row: bool, with_erase: bool) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 8)
	for ch in chars:
		var b := _key(ch, accent_row)
		b.pressed.connect(func(): letter.emit(ch))
		h.add_child(b)
	if with_erase:
		var e := _key("⌫", false)
		e.custom_minimum_size.x = 100
		e.add_theme_color_override("font_color", UI.BERRY)
		e.add_theme_color_override("font_pressed_color", UI.BERRY)
		e.add_theme_color_override("font_hover_color", UI.BERRY)
		e.pressed.connect(func(): erase.emit())
		h.add_child(e)
	return h

func _key(ch: String, accent_row: bool) -> Button:
	var b := Button.new()
	b.text = ch
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(56, 88)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_font_override("font", UI.font(true))
	b.add_theme_font_size_override("font_size", 34)
	UI.style_button(b, "neutral", 18)
	for s in ["normal", "hover", "pressed"]:
		var st: StyleBoxFlat = b.get_theme_stylebox(s).duplicate()
		st.content_margin_left = 0
		st.content_margin_right = 0
		st.content_margin_top = 8
		st.content_margin_bottom = 8 + (0 if s == "pressed" else 0)
		if accent_row:
			st.bg_color = UI.SKY_PALE if s != "hover" else Color("cdeefe")
			st.border_color = Color("84d8ff")
		b.add_theme_stylebox_override(s, st)
	var ink := UI.SKY_LIP if accent_row else UI.INK
	for c in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(c, ink)
	b.button_down.connect(func(): Sfx.play("key", randf_range(0.95, 1.08)); Sfx.buzz(8))
	return b
