extends Control
## Builds every screen in code and drives the scoring animations.

const BG_TOP := Color("#2a1866")
const BG_BOTTOM := Color("#0b0a1f")
const GOLD := Color("#f2b544")
const POINTS_COLOR := Color("#3fa7f5")
const MULT_COLOR := Color("#f2545b")
const TEXT := Color("#f3ecff")
const SOFT_TEXT := Color("#b5a8d6")
const PANEL := Color("#24184d")
const PANEL_DIM := Color("#171033")

const HELP_TEXT := """Each floor has three trials: a Minor Trial, a Major Trial and a Warden. Reach the target score to clear a trial. Clear all 8 floors to win.

Tap up to 5 cards, then Play to score them as a poker hand. You have a few hands and discards per trial.

Score = Points x Mult. The hand type gives base Points and Mult. Each scored card adds its Points (A = 11, faces = 10). Then charms apply, left to right, so their order matters.

Earn coins by clearing trials. You also earn 1 coin per unused hand, and 1 coin of interest for every 5 you hold (up to 5).

Spend coins in the shop:
- Charms: up to 5, with permanent effects.
- Runes: level up a hand type.
- Sigils: enhance or reshape your deck.

Wardens bend one rule, so read them before you play. You can skip Minor and Major trials for a small bonus, but you miss that shop."""

var screen: VBoxContainer
var info_label: Label
var busy := false
var selected: Array = []
var card_views := {}
var charm_views: Array = []
var lbl := {}
var hand_row: HBoxContainer
var played_row: HBoxContainer
var play_btn: Button
var discard_btn: Button
var sort_by_suit := false
var blip: AudioStreamPlayer
var step_count := 0
var pending_rewards: Array = []


func _ready() -> void:
	theme = _make_theme()
	var bg := TextureRect.new()
	var grad := Gradient.new()
	grad.set_color(0, BG_TOP)
	grad.set_color(1, BG_BOTTOM)
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill_from = Vector2(0.5, 0)
	tex.fill_to = Vector2(0.5, 1)
	tex.width = 8
	tex.height = 256
	bg.texture = tex
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var safe := _safe_margins()
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", safe.x)
	margin.add_theme_constant_override("margin_bottom", safe.y)
	add_child(margin)
	screen = VBoxContainer.new()
	screen.add_theme_constant_override("separation", 12)
	margin.add_child(screen)

	blip = AudioStreamPlayer.new()
	blip.stream = _make_blip()
	blip.max_polyphony = 4
	blip.volume_db = -8.0
	add_child(blip)

	show_title()


func _safe_margins() -> Vector2i:
	var top := 24
	var bottom := 20
	if OS.has_feature("mobile"):
		var safe := DisplayServer.get_display_safe_area()
		var screen_size := DisplayServer.screen_get_size()
		if screen_size.y > 0:
			var k := get_viewport_rect().size.y / float(screen_size.y)
			top = maxi(top, int(safe.position.y * k) + 8)
			bottom = maxi(bottom, int((screen_size.y - safe.end.y) * k) + 8)
	return Vector2i(top, bottom)


# --- Building blocks ----------------------------------------------------------

func _make_theme() -> Theme:
	var t := Theme.new()
	t.default_font_size = 22
	t.set_color("font_color", "Label", TEXT)

	var normal := StyleBoxFlat.new()
	normal.bg_color = GOLD
	normal.set_corner_radius_all(12)
	normal.content_margin_left = 18
	normal.content_margin_right = 18
	normal.content_margin_top = 12
	normal.content_margin_bottom = 12
	var hover := normal.duplicate()
	hover.bg_color = GOLD.lightened(0.12)
	var pressed := normal.duplicate()
	pressed.bg_color = GOLD.darkened(0.2)
	var disabled := normal.duplicate()
	disabled.bg_color = Color("#4a4163")
	t.set_stylebox("normal", "Button", normal)
	t.set_stylebox("hover", "Button", hover)
	t.set_stylebox("pressed", "Button", pressed)
	t.set_stylebox("disabled", "Button", disabled)
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		t.set_color(c, "Button", Color("#1b1030"))
	t.set_color("font_disabled_color", "Button", Color("#8d84a6"))
	t.set_font_size("font_size", "Button", 24)

	var panel := StyleBoxFlat.new()
	panel.bg_color = PANEL
	panel.set_corner_radius_all(14)
	panel.set_content_margin_all(14)
	t.set_stylebox("panel", "PanelContainer", panel)
	return t


func _label(text: String, font_size := 22, color := TEXT, align := HORIZONTAL_ALIGNMENT_CENTER) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	return l


## Same as _label, but wraps long text to the available width.
func _wrapped(text: String, font_size := 22, color := TEXT, align := HORIZONTAL_ALIGNMENT_CENTER) -> Label:
	var l := _label(text, font_size, color, align)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return l


func _button(text: String, cb: Callable, min_width := 0) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(min_width, 64)
	b.pressed.connect(cb)
	return b


func _panel(color := PANEL, border := Color(0, 0, 0, 0)) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(14)
	sb.set_content_margin_all(14)
	if border.a > 0:
		sb.set_border_width_all(3)
		sb.border_color = border
	p.add_theme_stylebox_override("panel", sb)
	return p


func _spacer() -> Control:
	var c := Control.new()
	c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return c


func _hbox(sep := 12, align := BoxContainer.ALIGNMENT_CENTER) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	h.alignment = align
	return h


func _clear() -> void:
	for c in screen.get_children():
		screen.remove_child(c)
		c.queue_free()
	lbl.clear()
	card_views.clear()
	charm_views.clear()
	info_label = null


func _info_bar() -> void:
	info_label = _wrapped("", 20, SOFT_TEXT)
	info_label.custom_minimum_size = Vector2(0, 56)
	screen.add_child(info_label)


func _toast(text: String) -> void:
	if info_label == null:
		return
	info_label.text = text
	info_label.modulate = Color(1, 1, 1, 0.3)
	create_tween().tween_property(info_label, "modulate", Color.WHITE, 0.2)


func _header() -> void:
	var h := _hbox(12, BoxContainer.ALIGNMENT_BEGIN)
	var left := _label("Floor %d / %d" % [Run.floor_num, Run.FLOORS], 24, TEXT, HORIZONTAL_ALIGNMENT_LEFT)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(left)
	lbl.coins = _label("%d coins" % Run.coins, 26, GOLD, HORIZONTAL_ALIGNMENT_RIGHT)
	h.add_child(lbl.coins)
	screen.add_child(h)


func _refresh_coins() -> void:
	if lbl.has("coins"):
		lbl.coins.text = "%d coins" % Run.coins


func _charms_row() -> void:
	var h := _hbox(8)
	for i in Run.MAX_CHARMS:
		var ch: Dictionary = Run.charms[i] if i < Run.charms.size() else {}
		var v := CharmView.new().setup(ch, i)
		v.tapped.connect(_on_charm_tapped)
		h.add_child(v)
		if not ch.is_empty():
			charm_views.append(v)
	screen.add_child(h)


func _on_charm_tapped(v: CharmView) -> void:
	_toast("%s: %s" % [Charms.name_of(v.charm), Charms.describe(v.charm)])


static func fmt(x: float) -> String:
	if x >= 1e12:
		var e := int(floor(log(x) / log(10.0)))
		return "%.2fe%d" % [x / pow(10.0, e), e]
	var s := str(int(roundf(x)))
	var out := ""
	var n := 0
	for i in range(s.length() - 1, -1, -1):
		out = s[i] + out
		n += 1
		if n % 3 == 0 and i > 0:
			out = "," + out
	return out


static func fmt_mult(x: float) -> String:
	if x < 1e12 and not is_equal_approx(x, roundf(x)):
		return "%.1f" % x
	return fmt(x)


# --- Title & help --------------------------------------------------------------

func show_title() -> void:
	_clear()
	screen.add_child(_spacer())
	var title := _label("ALEATRO", 104, GOLD)
	title.add_theme_constant_override("outline_size", 12)
	title.add_theme_color_override("font_outline_color", Color("#1b1030"))
	screen.add_child(title)
	screen.add_child(_wrapped("a roguelike of chance and combinations", 24, SOFT_TEXT))
	var fan := _hbox(-18)
	fan.custom_minimum_size = Vector2(0, 170)
	var sample := [[14, 0], [13, 3], [12, 1], [11, 2], [10, 0]]
	for i in sample.size():
		var cv := CardView.new().setup({"id": -1 - i, "rank": sample[i][0], "suit": sample[i][1], "enh": ""}, false)
		cv.rotation = deg_to_rad(-12 + i * 6)
		fan.add_child(cv)
	screen.add_child(fan)
	screen.add_child(_spacer())
	for b in [_button("New Run", _start_run, 380), _button("How to Play", show_help, 380)]:
		b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		screen.add_child(b)
	if Run.best_floor > 0:
		screen.add_child(_wrapped("Best: cleared a trial on floor %d" % Run.best_floor, 20, SOFT_TEXT))
	screen.add_child(_spacer())


func show_help() -> void:
	_clear()
	screen.add_child(_label("How to Play", 40, GOLD))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var text := _wrapped(HELP_TEXT, 22, TEXT, HORIZONTAL_ALIGNMENT_LEFT)
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(text)
	screen.add_child(scroll)
	var b := _button("Back", show_title, 380)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	screen.add_child(b)


func _start_run() -> void:
	Run.new_run()
	show_select()


# --- Trial selection -------------------------------------------------------------

func show_select() -> void:
	_clear()
	_header()
	_charms_row()
	screen.add_child(_label("Choose your next trial", 28))
	for t in 3:
		var current := t == Run.trial_idx
		var p := _panel(PANEL if current else PANEL_DIM, GOLD if current else Color(0, 0, 0, 0))
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 6)
		var title: String = Run.TRIAL_NAMES[t]
		if t == 2:
			title += ": " + Run.warden_name()
		v.add_child(_label(title, 28, GOLD if current else SOFT_TEXT))
		if t == 2:
			v.add_child(_wrapped(Run.warden_desc(), 22, MULT_COLOR))
		v.add_child(_label("Target %s  ·  Reward %d coins" % [fmt(Run.target(t)), Run.TRIAL_REWARD[t]], 22))
		if t < Run.trial_idx:
			v.add_child(_label("Done", 20, SOFT_TEXT))
		elif current:
			var row := _hbox()
			row.add_child(_button("Play", _on_play_trial, 200))
			if t < 2:
				row.add_child(_button("Skip", _on_skip_trial, 200))
			v.add_child(row)
			if t < 2:
				v.add_child(_wrapped("Skipping gives +5 coins or a free hand level, but you miss the shop.", 18, SOFT_TEXT))
		p.add_child(v)
		screen.add_child(p)
	screen.add_child(_spacer())
	_info_bar()


func _on_play_trial() -> void:
	Run.start_trial()
	selected.clear()
	show_round()


func _on_skip_trial() -> void:
	var msg := Run.skip_trial()
	show_select()
	_toast(msg)


# --- Round ------------------------------------------------------------------------

func show_round() -> void:
	_clear()
	_header()

	var top := _panel()
	var th := _hbox(12, BoxContainer.ALIGNMENT_BEGIN)
	var tl := VBoxContainer.new()
	tl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var tname: String = Run.TRIAL_NAMES[Run.trial_idx]
	if Run.trial_idx == 2:
		tname = Run.warden_name()
	tl.add_child(_label(tname, 26, GOLD, HORIZONTAL_ALIGNMENT_LEFT))
	tl.add_child(_label("Target  " + fmt(Run.target()), 22, TEXT, HORIZONTAL_ALIGNMENT_LEFT))
	th.add_child(tl)
	var tr := VBoxContainer.new()
	tr.add_child(_label("Score", 18, SOFT_TEXT, HORIZONTAL_ALIGNMENT_RIGHT))
	lbl.score = _label(fmt(Run.score), 40, TEXT, HORIZONTAL_ALIGNMENT_RIGHT)
	tr.add_child(lbl.score)
	th.add_child(tr)
	top.add_child(th)
	screen.add_child(top)
	if Run.trial_idx == 2:
		screen.add_child(_wrapped(Run.warden_desc(), 20, MULT_COLOR))

	var stats := _hbox(40)
	lbl.hands = _label("", 24, POINTS_COLOR)
	lbl.discards = _label("", 24, MULT_COLOR)
	stats.add_child(lbl.hands)
	stats.add_child(lbl.discards)
	screen.add_child(stats)

	_charms_row()

	var hp := _panel(PANEL_DIM)
	var hv := VBoxContainer.new()
	lbl.hand_name = _label("", 26, TEXT)
	hv.add_child(lbl.hand_name)
	var pm := _hbox(14)
	pm.add_child(_score_box("points", POINTS_COLOR))
	pm.add_child(_label("x", 34, TEXT))
	pm.add_child(_score_box("mult", MULT_COLOR))
	hv.add_child(pm)
	hp.add_child(hv)
	screen.add_child(hp)

	played_row = _hbox(6)
	played_row.custom_minimum_size = Vector2(0, 140)
	screen.add_child(played_row)
	screen.add_child(_spacer())

	hand_row = _hbox(4)
	hand_row.custom_minimum_size = Vector2(0, CardView.CARD_SIZE.y + CardView.RAISE + 6)
	screen.add_child(hand_row)

	var buttons := _hbox(10)
	buttons.add_child(_button("Sort", _on_sort, 120))
	discard_btn = _button("Discard", _on_discard, 190)
	play_btn = _button("Play Hand", _on_play, 230)
	buttons.add_child(discard_btn)
	buttons.add_child(play_btn)
	screen.add_child(buttons)
	_info_bar()

	_refresh_hand()
	_refresh_stats()
	_update_preview()


func _score_box(key: String, color: Color) -> PanelContainer:
	var p := _panel(color.darkened(0.55), color)
	p.custom_minimum_size = Vector2(200, 0)
	lbl[key] = _label("0", 38, TEXT)
	p.add_child(lbl[key])
	lbl[key + "_box"] = p
	return p


func _refresh_stats() -> void:
	lbl.hands.text = "Hands %d" % Run.hands_left
	lbl.discards.text = "Discards %d" % Run.discards_left
	_refresh_coins()


func _sort_hand() -> void:
	if sort_by_suit:
		Run.hand.sort_custom(func(a, b): return a.suit < b.suit or (a.suit == b.suit and a.rank > b.rank))
	else:
		Run.hand.sort_custom(func(a, b): return a.rank > b.rank or (a.rank == b.rank and a.suit < b.suit))


func _refresh_hand() -> void:
	_sort_hand()
	for c in hand_row.get_children():
		hand_row.remove_child(c)
		c.queue_free()
	card_views.clear()
	for card in Run.hand:
		var v := CardView.new().setup(card)
		v.selected = selected.has(card)
		v.tapped.connect(_on_card_tapped)
		hand_row.add_child(v)
		card_views[card.id] = v


func _on_card_tapped(v: CardView) -> void:
	if busy:
		return
	if selected.has(v.card):
		selected.erase(v.card)
		v.selected = false
	elif selected.size() < Run.MAX_SELECT:
		selected.append(v.card)
		v.selected = true
	else:
		_toast("You can select up to %d cards" % Run.MAX_SELECT)
		return
	if v.card.enh != "":
		_toast("%s: %s" % [Scoring.ENHANCEMENTS[v.card.enh].name, Scoring.ENHANCEMENTS[v.card.enh].desc])
	_update_preview()


func _update_preview() -> void:
	if selected.is_empty():
		lbl.hand_name.text = "Select up to 5 cards"
		lbl.points.text = "0"
		lbl.mult.text = "0"
	else:
		var hand_id: String = HandEval.evaluate(selected).hand
		var base := Scoring.base_for(Run, hand_id)
		lbl.hand_name.text = "%s  ·  Lv.%d" % [HandEval.INFO[hand_id].name, Run.hand_levels[hand_id]]
		lbl.points.text = fmt(base[0])
		lbl.mult.text = fmt_mult(base[1])
	play_btn.disabled = busy or selected.is_empty()
	discard_btn.disabled = busy or selected.is_empty() or Run.discards_left <= 0


func _on_sort() -> void:
	if busy:
		return
	sort_by_suit = not sort_by_suit
	_refresh_hand()
	_toast("Sorted by " + ("suit" if sort_by_suit else "rank"))


func _on_discard() -> void:
	if busy or not Run.discard(selected.duplicate()):
		return
	selected.clear()
	_refresh_hand()
	_refresh_stats()
	_update_preview()


func _on_play() -> void:
	if busy:
		return
	var err := Run.can_play(selected)
	if err != "":
		_toast(err)
		return
	busy = true
	var played := selected.duplicate()
	played.sort_custom(func(a, b): return Run.hand.find(a) < Run.hand.find(b))
	selected.clear()
	_update_preview()

	var before := Run.score
	var result := Run.play(played)
	for c in played:
		var v: CardView = card_views[c.id]
		v.selected = false
		v.dimmed = not result.scoring.has(c)
		v.interactive = false
		hand_row.remove_child(v)
		played_row.add_child(v)
	lbl.hand_name.text = HandEval.INFO[result.hand].name
	_refresh_stats()
	await get_tree().create_timer(0.35).timeout

	var steps: Array = result.steps
	var delay := clampf(2.6 / float(steps.size()), 0.12, 0.34)
	step_count = 0
	for st in steps:
		_show_step(st)
		await get_tree().create_timer(delay).timeout

	lbl.hand_name.text = "%s  =  %s" % [HandEval.INFO[result.hand].name, fmt(result.total)]
	var tw := create_tween()
	tw.tween_method(func(x: float): lbl.score.text = fmt(x), before, Run.score, 0.6)
	await tw.finished
	if not result.broken.is_empty():
		var names := PackedStringArray()
		for c in result.broken:
			names.append(HandEval.card_name(c))
		_toast("Shattered: " + ", ".join(names))
	await get_tree().create_timer(0.6).timeout

	for c in played_row.get_children():
		played_row.remove_child(c)
		c.queue_free()
	busy = false
	if Run.trial_won:
		show_trial_cleared()
	elif Run.is_lost():
		show_game_over()
	else:
		_refresh_hand()
		_refresh_stats()
		_update_preview()


func _show_step(st: Dictionary) -> void:
	lbl.points.text = fmt(st.points)
	lbl.mult.text = fmt_mult(st.mult)
	var text: String = st.text
	var color := MULT_COLOR if text.contains("Mult") else POINTS_COLOR
	match st.kind:
		"base":
			_pulse(lbl.points_box)
			_pulse(lbl.mult_box)
			return
		"card", "held":
			var v: CardView = card_views.get(st.ref.id)
			if v:
				v.bump()
				_float_text(v, text, Color("#9a93ad") if text == "Muted" else color)
		"charm":
			if st.ref < charm_views.size():
				var cv: CharmView = charm_views[st.ref]
				cv.pulse()
				_float_text(cv, text, color)
	step_count += 1
	blip.pitch_scale = minf(1.0 + step_count * 0.05, 2.2)
	blip.play()


func _pulse(c: Control) -> void:
	c.pivot_offset = c.size / 2.0
	var tw := create_tween()
	tw.tween_property(c, "scale", Vector2(1.08, 1.08), 0.08)
	tw.tween_property(c, "scale", Vector2.ONE, 0.12)


func _float_text(target: Control, text: String, color: Color) -> void:
	var l := _label(text, 26, color)
	l.add_theme_constant_override("outline_size", 8)
	l.add_theme_color_override("font_outline_color", Color("#120b2a"))
	l.z_index = 20
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	l.reset_size()
	l.global_position = target.global_position + Vector2(target.size.x / 2.0 - l.size.x / 2.0, -30)
	var tw := create_tween().set_parallel()
	tw.tween_property(l, "position:y", l.position.y - 44, 0.6)
	tw.tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.25)
	tw.chain().tween_callback(l.queue_free)


# --- Rewards, shop, end screens -------------------------------------------------------

func show_trial_cleared() -> void:
	_clear()
	_header()
	screen.add_child(_spacer())
	screen.add_child(_label("Trial Cleared!", 52, GOLD))
	screen.add_child(_label("Score %s  /  Target %s" % [fmt(Run.score), fmt(Run.target())], 24, SOFT_TEXT))
	var rows := Run.trial_rewards()
	var p := _panel()
	var v := VBoxContainer.new()
	var total := 0
	for row in rows:
		var h := _hbox(12, BoxContainer.ALIGNMENT_BEGIN)
		var name_l := _label(row[0], 24, TEXT, HORIZONTAL_ALIGNMENT_LEFT)
		name_l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(name_l)
		h.add_child(_label("+%d" % row[1], 24, GOLD, HORIZONTAL_ALIGNMENT_RIGHT))
		v.add_child(h)
		total += row[1]
	v.add_child(_label("Total  +%d coins" % total, 28, GOLD, HORIZONTAL_ALIGNMENT_RIGHT))
	p.add_child(v)
	screen.add_child(p)
	screen.add_child(_spacer())
	pending_rewards = rows
	var b := _button("Continue to Shop", _on_continue_to_shop, 420)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	screen.add_child(b)
	screen.add_child(_spacer())


func _on_continue_to_shop() -> void:
	Run.collect(pending_rewards)
	pending_rewards = []
	Run.open_shop()
	show_shop()


func show_shop() -> void:
	_clear()
	_header()
	screen.add_child(_label("Shop", 40, GOLD))
	for i in Run.shop_offers.size():
		var o: Dictionary = Run.shop_offers[i]
		var p := _panel(PANEL if o.type != "sold" else PANEL_DIM)
		var h := _hbox(12, BoxContainer.ALIGNMENT_BEGIN)
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if o.type == "sold":
			v.add_child(_label("Sold", 22, SOFT_TEXT, HORIZONTAL_ALIGNMENT_LEFT))
		else:
			v.add_child(_label(Run.offer_title(o), 24, GOLD, HORIZONTAL_ALIGNMENT_LEFT))
			v.add_child(_wrapped(Run.offer_desc(o), 19, TEXT, HORIZONTAL_ALIGNMENT_LEFT))
		h.add_child(v)
		if o.type != "sold":
			var b := _button("%d" % o.price, _on_buy.bind(i), 96)
			b.disabled = Run.coins < o.price
			h.add_child(b)
		p.add_child(h)
		screen.add_child(p)
	var rr := _button("Reroll  (%d)" % Run.reroll_cost, _on_reroll, 260)
	rr.disabled = Run.coins < Run.reroll_cost
	rr.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	screen.add_child(rr)

	screen.add_child(_wrapped("Your charms (%d/%d). They score left to right." % [Run.charms.size(), Run.MAX_CHARMS], 20, SOFT_TEXT))
	for i in Run.charms.size():
		var ch: Dictionary = Run.charms[i]
		var h := _hbox(8, BoxContainer.ALIGNMENT_BEGIN)
		var l := _wrapped("%s: %s" % [Charms.name_of(ch), Charms.describe(ch)], 18, TEXT, HORIZONTAL_ALIGNMENT_LEFT)
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(l)
		if i > 0:
			h.add_child(_button("<", _on_move_charm.bind(i, -1), 56))
		h.add_child(_button("Sell %d" % Charms.sell_value(ch), _on_sell.bind(i), 110))
		screen.add_child(h)

	var levels := GridContainer.new()
	levels.columns = 2
	levels.add_theme_constant_override("h_separation", 24)
	for h_id in HandEval.ORDER:
		if Run.hand_levels[h_id] > 1:
			levels.add_child(_label("%s Lv.%d" % [HandEval.INFO[h_id].name, Run.hand_levels[h_id]], 18, SOFT_TEXT, HORIZONTAL_ALIGNMENT_LEFT))
	if levels.get_child_count() > 0:
		screen.add_child(levels)
	else:
		levels.free()

	screen.add_child(_spacer())
	var next := _button("Next Trial", _on_leave_shop, 380)
	next.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	screen.add_child(next)
	_info_bar()


func _on_buy(i: int) -> void:
	var r := Run.buy(i)
	show_shop()
	_toast(r.msg)


func _on_reroll() -> void:
	if Run.reroll():
		show_shop()


func _on_sell(i: int) -> void:
	var msg := Run.sell_charm(i)
	show_shop()
	_toast(msg)


func _on_move_charm(i: int, delta: int) -> void:
	Run.move_charm(i, delta)
	show_shop()


func _on_leave_shop() -> void:
	if Run.advance() == "victory":
		show_victory()
	else:
		show_select()


func show_game_over() -> void:
	_clear()
	screen.add_child(_spacer())
	screen.add_child(_label("Run Over", 64, MULT_COLOR))
	screen.add_child(_label("Floor %d · %s" % [Run.floor_num, Run.TRIAL_NAMES[Run.trial_idx]], 28))
	screen.add_child(_label("Scored %s of %s" % [fmt(Run.score), fmt(Run.target())], 24, SOFT_TEXT))
	screen.add_child(_spacer())
	_end_buttons()


func show_victory() -> void:
	_clear()
	screen.add_child(_spacer())
	screen.add_child(_label("Victory!", 72, GOLD))
	screen.add_child(_label("You cleared all %d floors." % Run.FLOORS, 28))
	screen.add_child(_spacer())
	_end_buttons()


func _end_buttons() -> void:
	for b in [_button("New Run", _start_run, 380), _button("Title", show_title, 380)]:
		b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		screen.add_child(b)
	screen.add_child(_spacer())


# --- Sound ---------------------------------------------------------------------

func _make_blip() -> AudioStreamWAV:
	var rate := 22050
	var n := int(rate * 0.08)
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var t := float(i) / rate
		var env := exp(-t * 45.0)
		var s := (sin(TAU * 660.0 * t) + 0.3 * sin(TAU * 1320.0 * t)) * env * 0.45
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = rate
	w.stereo = false
	w.data = data
	return w
