extends Node
## Player profile, progression, economy and spaced-repetition memory.
## Persisted as JSON in user://.

signal coins_changed(value: int)
signal profile_changed

const SAVE_PATH := "user://lexigo_save.json"
const SAVE_VERSION := 1

## Leitner boxes: review interval in days for each box.
const SRS_INTERVALS := [0.0, 0.5, 1.0, 3.0, 7.0, 16.0, 35.0]
const MASTERED_BOX := 4

const HINT_COST := {"letter": 10, "trim": 15, "word": 30, "listen": 0, "example": 0}
const START_COINS := 150

var data := {}

func _ready() -> void:
	load_game()

func default_data() -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"onboarded": false,
		"native": _guess_native(),
		"target": "fr",
		"coins": START_COINS,
		"xp": 0,
		"streak": 0,
		"best_streak": 0,
		"last_day": "",
		"daily_done": "",
		"progress": {},   # target -> {"w:l": stars}
		"srs": {},        # target -> {word_id: {box, due, seen, ok}}
		"settings": {"sfx": true, "voice": true, "haptics": true, "strict": false, "online": true},
	}

func _guess_native() -> String:
	var l := OS.get_locale_language()
	return l if l in Loc.LANGS else "en"

func load_game() -> void:
	data = default_data()
	if FileAccess.file_exists(SAVE_PATH):
		var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
		var parsed = JSON.parse_string(f.get_as_text())
		if parsed is Dictionary:
			for k in parsed.keys():
				data[k] = parsed[k]
			var defaults: Dictionary = default_data()["settings"]
			for k in defaults.keys():
				if not data["settings"].has(k):
					data["settings"][k] = defaults[k]
	Loc.lang = data["native"]

func save_game() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(data))

func reset() -> void:
	var keep_native: String = data["native"]
	data = default_data()
	data["native"] = keep_native
	save_game()
	profile_changed.emit()

# ---------- languages & settings ----------

func native() -> String:
	return data["native"]

func target() -> String:
	return data["target"]

func set_languages(n: String, t: String) -> void:
	data["native"] = n
	data["target"] = t
	Loc.lang = n
	save_game()
	profile_changed.emit()

func setting(key: String) -> bool:
	return data["settings"].get(key, false)

func set_setting(key: String, value: bool) -> void:
	data["settings"][key] = value
	save_game()

# ---------- economy ----------

func coins() -> int:
	return int(data["coins"])

func add_coins(n: int) -> void:
	data["coins"] = coins() + n
	coins_changed.emit(coins())
	save_game()

func spend(n: int) -> bool:
	if coins() < n:
		return false
	data["coins"] = coins() - n
	coins_changed.emit(coins())
	save_game()
	return true

func xp() -> int:
	return int(data["xp"])

func add_xp(n: int) -> void:
	data["xp"] = xp() + n

## Level curve: each level needs 100 more XP than the last.
func player_level() -> int:
	var lvl := 1
	var need := 100
	var left := xp()
	while left >= need:
		left -= need
		lvl += 1
		need += 100
	return lvl

func level_progress() -> float:
	var need := 100
	var left := xp()
	while left >= need:
		left -= need
		need += 100
	return float(left) / float(need)

# ---------- progression ----------

func _progress() -> Dictionary:
	if not data["progress"].has(target()):
		data["progress"][target()] = {}
	return data["progress"][target()]

func stars(world: int, level: int) -> int:
	return int(_progress().get("%d:%d" % [world, level], 0))

func world_stars(world: int) -> int:
	var s := 0
	for l in Vocab.LEVELS_PER_WORLD:
		s += stars(world, l)
	return s

func total_stars() -> int:
	var s := 0
	for w in Vocab.worlds.size():
		s += world_stars(w)
	return s

func world_unlocked(world: int) -> bool:
	return world == 0 or stars(world - 1, Vocab.LEVELS_PER_WORLD - 1) > 0

func level_unlocked(world: int, level: int) -> bool:
	if not world_unlocked(world):
		return false
	return level == 0 or stars(world, level - 1) > 0

func unlocked_worlds() -> int:
	var n := 0
	for w in Vocab.worlds.size():
		if world_unlocked(w):
			n = w + 1
	return n

func record_level(world: int, level: int, s: int) -> void:
	var key := "%d:%d" % [world, level]
	_progress()[key] = maxi(stars(world, level), s)

# ---------- streak & daily ----------

func today() -> String:
	return Time.get_date_string_from_system()

func touch_streak() -> void:
	var t := today()
	if data["last_day"] == t:
		return
	var yesterday := Time.get_date_string_from_unix_time(int(Time.get_unix_time_from_system()) - 86400)
	data["streak"] = int(data["streak"]) + 1 if data["last_day"] == yesterday else 1
	data["best_streak"] = maxi(int(data["best_streak"]), int(data["streak"]))
	data["last_day"] = t

func current_streak() -> int:
	var yesterday := Time.get_date_string_from_unix_time(int(Time.get_unix_time_from_system()) - 86400)
	if data["last_day"] == today() or data["last_day"] == yesterday:
		return int(data["streak"])
	return 0

func daily_done() -> bool:
	return data["daily_done"] == "%s|%s" % [today(), target()]

func mark_daily_done() -> void:
	data["daily_done"] = "%s|%s" % [today(), target()]

# ---------- spaced repetition ----------

func _srs() -> Dictionary:
	if not data["srs"].has(target()):
		data["srs"][target()] = {}
	return data["srs"][target()]

func memory(word_id: String) -> Dictionary:
	return _srs().get(word_id, {})

## quality: 0 = solved cleanly, 1 = solved with help/mistakes, 2 = revealed.
func record_word(word_id: String, quality: int) -> void:
	var m: Dictionary = _srs().get(word_id, {"box": 0, "due": 0.0, "seen": 0, "ok": 0})
	var box := int(m["box"])
	match quality:
		0:
			box = mini(box + 1, SRS_INTERVALS.size() - 1)
			m["ok"] = int(m["ok"]) + 1
		1:
			box = maxi(1, box - 1) if box > 1 else 1
		_:
			box = 1
	m["box"] = box
	m["seen"] = int(m["seen"]) + 1
	m["due"] = Time.get_unix_time_from_system() + SRS_INTERVALS[box] * 86400.0
	_srs()[word_id] = m

func due_words() -> Array:
	var now := Time.get_unix_time_from_system()
	var out := []
	var srs := _srs()
	for id in srs.keys():
		if float(srs[id]["due"]) <= now and not Vocab.get_word(id).is_empty():
			out.append(id)
	out.sort_custom(func(a, b): return float(srs[a]["due"]) < float(srs[b]["due"]))
	return out

## Due words first, topped up with the weakest known words.
func review_words(limit := 9) -> Array:
	var ids := due_words()
	if ids.size() < limit:
		var srs := _srs()
		var rest := srs.keys().filter(func(id): return not ids.has(id) and not Vocab.get_word(id).is_empty())
		rest.sort_custom(func(a, b): return int(srs[a]["box"]) < int(srs[b]["box"]))
		ids.append_array(rest)
	var out := []
	for id in ids.slice(0, limit):
		out.append(Vocab.get_word(id))
	return out

func known_count() -> int:
	return _srs().size()

func mastered_count() -> int:
	var n := 0
	for m in _srs().values():
		if int(m["box"]) >= MASTERED_BOX:
			n += 1
	return n
