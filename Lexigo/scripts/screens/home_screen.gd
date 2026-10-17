extends Screen
## Learning path: stats bar, world banners with a winding trail of level
## nodes, the mascot cheering beside your current level, and a tab bar.

const NODE := 116.0
const STEP := 226.0
const ZIGZAG := [0.0, 72.0, 112.0, 72.0, 0.0, -72.0]

var _scroll: ScrollContainer
var _current_node: Control

func go_back() -> bool:
	return false

func _ready() -> void:
	var root := make_root(0, 0)
	root.add_child(UI.margin(_stats_bar(), 28, 8, 28, 8))
	root.add_child(Widgets.divider())

	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 18)
	var lm := UI.margin(list, 24, 24, 24, 40)
	lm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(lm)
	root.add_child(_scroll)
	for w in Vocab.worlds.size():
		list.add_child(_banner(w))
		if Game.world_unlocked(w):
			list.add_child(_path(w))
	root.add_child(Widgets.divider())
	root.add_child(UI.margin(_tab_bar(), 20, 8, 20, 8))

	await get_tree().process_frame
	await get_tree().process_frame
	if is_instance_valid(_current_node) and is_instance_valid(_scroll):
		var y := _current_node.get_global_rect().position.y - _scroll.get_global_rect().position.y - 260.0
		if y > 0:
			create_tween().tween_property(_scroll, "scroll_vertical", int(y), 0.7).set_trans(Tween.TRANS_CUBIC)

func _stats_bar() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 22)
	var lang := UI.button(Vocab.LANG_NAMES[Game.target()], "outline", 22, 72)
	lang.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	lang.pressed.connect(main.open_settings)
	h.add_child(lang)
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(sp)
	var streak := Game.current_streak()
	h.add_child(UI.stat(Loc.t("streak_short"), str(streak), UI.FLAME if streak > 0 else UI.MIST))
	h.add_child(UI.stat(Loc.t("stars"), str(Game.total_stars()), UI.SUN_LIP))
	h.add_child(Widgets.coin_stat())
	h.add_child(UI.stat(Loc.t("level"), "%d" % Game.player_level(), UI.SKY))
	return h

func _banner(w: int) -> PanelContainer:
	var world: Dictionary = Vocab.worlds[w]
	var unlocked := Game.world_unlocked(w)
	var color: Color = world["color"] if unlocked else UI.MIST
	var p := UI.panel(UI.box(color, UI.R_CARD, 0, UI.CLOUD, UI.LIP, color.darkened(0.2)))
	var h := HBoxContainer.new()
	p.add_child(h)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(UI.caps("%s %d · %d/%d %s" % [Loc.t("world"), w + 1, Game.world_stars(w), Vocab.LEVELS_PER_WORLD * 3, Loc.t("stars")], 22, Color(1, 1, 1, 0.8)))
	var name := UI.label(Vocab.world_name(w, Game.native()), 36, UI.WHITE, true)
	name.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(name)
	if not unlocked:
		var hint := UI.label(Loc.t("locked"), 22, Color(1, 1, 1, 0.9))
		hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		v.add_child(hint)
	h.add_child(v)
	var badge := UI.art("worlds/%s.svg" % world["id"], 112)
	if not unlocked:
		badge.modulate = Color(1, 1, 1, 0.45)
	h.add_child(badge)
	return p

func _path(w: int) -> Control:
	var area := Control.new()
	area.custom_minimum_size.y = Vocab.LEVELS_PER_WORLD * STEP + 40
	area.mouse_filter = Control.MOUSE_FILTER_PASS
	var color: Color = Vocab.worlds[w]["color"]
	var current := -1
	for l in Vocab.LEVELS_PER_WORLD:
		if Game.level_unlocked(w, l) and Game.stars(w, l) == 0 and current < 0:
			current = l
	for l in Vocab.LEVELS_PER_WORLD:
		var node := _node(w, l, color, l == current)
		var x: float = ZIGZAG[l % ZIGZAG.size()]
		node.anchor_left = 0.5
		node.anchor_right = 0.5
		node.offset_left = x - NODE * 0.5
		node.offset_right = x + NODE * 0.5
		node.offset_top = 70 + l * STEP
		node.offset_bottom = node.offset_top + NODE + 40
		area.add_child(node)
		if l == current:
			_current_node = node
	# The mascot keeps you company beside the current stretch of trail.
	if current >= 0 or w == Game.unlocked_worlds() - 1:
		var spot := clampi(current if current >= 0 else 2, 0, Vocab.LEVELS_PER_WORLD - 1)
		var side := -1.0 if ZIGZAG[spot % ZIGZAG.size()] >= 0 else 1.0
		var m := UI.mascot("happy" if current >= 0 else "cheer", 170)
		m.anchor_left = 0.5
		m.anchor_right = 0.5
		m.offset_left = side * 190 - 85
		m.offset_right = m.offset_left + 170
		m.offset_top = 60 + spot * STEP
		m.offset_bottom = m.offset_top + 170
		if side > 0:
			m.flip_h = true
		area.add_child(m)
		UI.bob(m, 6.0, 2.2)
	return area

func _node(w: int, l: int, color: Color, is_current: bool) -> Control:
	var holder := Control.new()
	holder.mouse_filter = Control.MOUSE_FILTER_PASS
	var unlocked := Game.level_unlocked(w, l)
	var s := Game.stars(w, l)
	var boss := l == Vocab.LEVELS_PER_WORLD - 1
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(NODE, NODE - 8)
	b.size = b.custom_minimum_size
	b.position = Vector2(0, 0)
	var face := color if unlocked else UI.CLOUD
	var lip := color.darkened(0.25) if unlocked else Color("cecece")
	var normal := UI.box(face, int(NODE * 0.5), 0, UI.CLOUD, 12, lip)
	var pressed := normal.duplicate()
	pressed.border_width_bottom = 0
	pressed.expand_margin_top = -12
	b.add_theme_stylebox_override("normal", normal)
	b.add_theme_stylebox_override("hover", normal)
	b.add_theme_stylebox_override("pressed", pressed)
	b.add_theme_stylebox_override("disabled", normal)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.text = Loc.t("boss_short").to_upper() if boss else str(l + 1)
	b.add_theme_font_override("font", UI.font(true, boss))
	b.add_theme_font_size_override("font_size", 26 if boss else 46)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_disabled_color"]:
		b.add_theme_color_override(c, UI.WHITE if unlocked else UI.MIST)
	b.disabled = not unlocked
	b.pressed.connect(func():
		Sfx.play("select")
		main.play_level(w, l))
	holder.add_child(b)

	if unlocked and s > 0:
		var stars := UI.caps("%d/3 %s" % [s, Loc.t("stars")], 18, UI.SUN_LIP)
		stars.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		stars.position = Vector2(NODE * 0.5 - 80, NODE + 2)
		stars.custom_minimum_size.x = 160
		holder.add_child(stars)

	if is_current:
		# Pulsing ring + "START" bubble above the node.
		var ring := Panel.new()
		ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var rs := StyleBoxFlat.new()
		rs.draw_center = false
		rs.set_border_width_all(8)
		rs.border_color = Color(color, 0.35)
		rs.set_corner_radius_all(int(NODE * 0.5 + 14))
		rs.anti_aliasing = true
		ring.add_theme_stylebox_override("panel", rs)
		ring.position = Vector2(-14, -14)
		ring.size = Vector2(NODE + 28, NODE + 20)
		holder.add_child(ring)
		holder.move_child(ring, 0)
		var start := UI.panel(UI.box(UI.WHITE, 22, UI.BORDER, UI.CLOUD, 2))
		var sl := UI.caps(Loc.t("start_node"), 24, color.darkened(0.1))
		sl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		start.add_child(sl)
		start.mouse_filter = Control.MOUSE_FILTER_IGNORE
		holder.add_child(start)
		start.position = Vector2(NODE * 0.5 - 80, -74)
		start.custom_minimum_size = Vector2(160, 0)
		UI.bob(start, 6.0, 1.4)
	return holder

func _tab_bar() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	var tabs := [
		["home", Callable(), true],
		["daily", main.play_daily, false],
		["review", main.play_review, false],
		["lexicon", main.open_lexicon, false],
		["settings", main.open_settings, false],
	]
	for t in tabs:
		var b := Button.new()
		b.text = Loc.t(t[0]).to_upper()
		b.add_theme_font_override("font", UI.font(true, true))
		b.add_theme_font_size_override("font_size", 17)
		b.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		b.clip_text = true
		for c in ["font_color", "font_hover_color", "font_pressed_color"]:
			b.add_theme_color_override(c, UI.SKY_LIP if t[2] else UI.STONE)
		b.focus_mode = Control.FOCUS_NONE
		b.custom_minimum_size = Vector2(0, 92)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var st: StyleBox = UI.box(UI.SKY_PALE, 22, UI.BORDER, Color("84d8ff")) if t[2] else StyleBoxEmpty.new()
		for s in ["normal", "hover", "pressed", "focus"]:
			b.add_theme_stylebox_override(s, st)
		if t[1].is_valid():
			b.pressed.connect(t[1])
		b.pressed.connect(func(): Sfx.play("tap"))
		h.add_child(b)
		if t[0] == "review":
			var due := Game.due_words().size()
			if due > 0:
				var badge := UI.panel(UI.box(UI.BERRY, 20))
				var bl := UI.label(str(due), 20, UI.WHITE, true, HORIZONTAL_ALIGNMENT_CENTER)
				badge.add_child(bl)
				badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
				var sb: StyleBoxFlat = badge.get_theme_stylebox("panel")
				sb.content_margin_left = 10
				sb.content_margin_right = 10
				sb.content_margin_top = 0
				sb.content_margin_bottom = 0
				b.add_child(badge)
				badge.position = Vector2(70, 2)
		if t[0] == "daily" and not Game.daily_done():
			var dot := Panel.new()
			dot.add_theme_stylebox_override("panel", UI.box(UI.FLAME, 11))
			dot.size = Vector2(22, 22)
			dot.mouse_filter = Control.MOUSE_FILTER_IGNORE
			b.add_child(dot)
			dot.position = Vector2(80, 8)
	return h
