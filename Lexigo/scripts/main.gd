extends Control
## Root of the app: animated background, screen navigation, toasts and
## shared helpers such as pronunciation.

const Background := preload("res://scripts/ui/background.gd")

var background: Control
var holder: Control
var overlay: Control
var current: Screen
var _toast: PanelContainer

func _ready() -> void:
	theme = UI.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background = Background.new()
	add_child(background)
	holder = Control.new()
	holder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(holder)
	overlay = Control.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(overlay)
	get_tree().auto_accept_quit = false
	if Game.data["onboarded"]:
		goto_home()
	else:
		goto_onboarding()

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST or what == NOTIFICATION_WM_CLOSE_REQUEST:
		if what == NOTIFICATION_WM_GO_BACK_REQUEST and current and current.go_back():
			return
		Game.save_game()
		get_tree().quit()
	elif what == NOTIFICATION_APPLICATION_PAUSED:
		Game.save_game()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and current:
		current.go_back()
		get_viewport().set_input_as_handled()

# ---------- safe area ----------

func _screen_to_view() -> float:
	var screen := DisplayServer.screen_get_size()
	return get_viewport_rect().size.y / maxf(1.0, float(screen.y)) if OS.has_feature("mobile") else 0.0

func safe_top() -> float:
	var safe := DisplayServer.get_display_safe_area()
	return safe.position.y * _screen_to_view()

func safe_bottom() -> float:
	var safe := DisplayServer.get_display_safe_area()
	var screen := DisplayServer.screen_get_size()
	return maxf(0.0, screen.y - safe.end.y) * _screen_to_view()

# ---------- navigation ----------

func show_screen(s: Screen) -> void:
	s.main = self
	var old := current
	current = s
	holder.add_child(s)
	background.set_palette(s.accent())
	s.modulate.a = 0.0
	s.position.x = 60
	var tw := s.create_tween().set_parallel()
	tw.tween_property(s, "modulate:a", 1.0, 0.28)
	tw.tween_property(s, "position:x", 0.0, 0.38).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	if old:
		old.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var t2 := old.create_tween().set_parallel()
		t2.tween_property(old, "modulate:a", 0.0, 0.2)
		t2.tween_property(old, "position:x", -60.0, 0.25)
		t2.chain().tween_callback(old.queue_free)
	Sfx.play("whoosh")

func goto_onboarding() -> void:
	show_screen(preload("res://scripts/screens/onboarding_screen.gd").new())

func goto_home() -> void:
	show_screen(preload("res://scripts/screens/home_screen.gd").new())

func open_lexicon() -> void:
	show_screen(preload("res://scripts/screens/lexicon_screen.gd").new())

func open_settings() -> void:
	show_screen(preload("res://scripts/screens/settings_screen.gd").new())

func play_level(world: int, level: int) -> void:
	var t := Game.target()
	var boss := level == Vocab.LEVELS_PER_WORLD - 1
	var title := "%s %s · %s" % [Vocab.worlds[world]["emoji"], Vocab.world_name(world, Game.native()),
		Loc.t("boss") if boss else "%s %d" % [Loc.t("level"), level + 1]]
	_start_puzzle({
		"mode": "level", "world": world, "level": level, "title": title,
		"color": Vocab.worlds[world]["color"],
		"words": Vocab.level_words(world, level, t),
		"seed": hash("lvl|%d|%d|%s" % [world, level, t]),
	})

func play_daily() -> void:
	if Game.daily_done():
		toast(Loc.t("daily_done"))
		return
	_start_puzzle({
		"mode": "daily", "title": "📅 " + Loc.t("daily_title"), "color": UI.GOLD.darkened(0.15),
		"words": Vocab.daily_words(Game.target(), Game.unlocked_worlds(), Game.today()),
		"seed": hash("daily|%s|%s" % [Game.today(), Game.target()]),
	})

func play_review() -> void:
	var words := Game.review_words()
	if words.size() < 3:
		toast(Loc.t("no_review"))
		return
	_start_puzzle({
		"mode": "review", "title": "🧠 " + Loc.t("review_title"), "color": UI.ACCENT_2,
		"words": words, "seed": int(Time.get_unix_time_from_system()),
	})

func _start_puzzle(cfg: Dictionary) -> void:
	var s: Screen = preload("res://scripts/screens/puzzle_screen.gd").new()
	s.config = cfg
	show_screen(s)

# ---------- feedback ----------

func toast(text: String) -> void:
	if _toast:
		_toast.queue_free()
	_toast = UI.pill(text, Color(0.08, 0.05, 0.2, 0.92))
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay.add_child(_toast)
	_toast.get_node("Label").autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_toast.custom_minimum_size.x = minf(640.0, size.x - 48.0)
	_toast.reset_size()
	_toast.position = Vector2((size.x - _toast.size.x) * 0.5, size.y * 0.16)
	_toast.modulate.a = 0.0
	var t := _toast
	var tw := t.create_tween()
	tw.tween_property(t, "modulate:a", 1.0, 0.2)
	tw.tween_interval(1.8)
	tw.tween_property(t, "modulate:a", 0.0, 0.3)
	tw.tween_callback(t.queue_free)

## Native-speaker recording when available online, device TTS otherwise.
func pronounce(word: Dictionary, explicit := true) -> void:
	var text := Vocab.display(word, Game.target())
	if Online.enabled():
		var stream: AudioStream = await Online.native_audio(text, Game.target())
		if stream:
			Sfx.play_stream(stream)
			return
	if not Sfx.speak(text, Game.target()) and explicit:
		toast("🔇 " + text)

## Burst of confetti at a point in global coordinates.
func confetti(at: Vector2, amount := 90) -> void:
	var p := CPUParticles2D.new()
	p.position = at
	p.amount = amount
	p.one_shot = true
	p.explosiveness = 0.95
	p.lifetime = 1.8
	p.direction = Vector2(0, -1)
	p.spread = 70.0
	p.initial_velocity_min = 500.0
	p.initial_velocity_max = 950.0
	p.gravity = Vector2(0, 1300)
	p.angular_velocity_min = -360.0
	p.angular_velocity_max = 360.0
	p.scale_amount_min = 7.0
	p.scale_amount_max = 14.0
	p.damping_min = 40.0
	p.damping_max = 90.0
	var g := Gradient.new()
	g.colors = PackedColorArray([UI.GOLD, UI.ACCENT_2, UI.GREEN, Color("4cc9f0"), UI.ACCENT])
	g.offsets = PackedFloat32Array([0.0, 0.25, 0.5, 0.75, 1.0])
	p.color_initial_ramp = g
	overlay.add_child(p)
	p.emitting = true
	get_tree().create_timer(2.5).timeout.connect(p.queue_free)
