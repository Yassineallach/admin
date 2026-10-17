extends Node
## Bundled vocabulary: themed worlds, each word translated into every
## supported language. Words are addressed by "<world>:<english>" ids.

const LANG_NAMES := {
	"en": "English", "fr": "Français", "es": "Español",
	"de": "Deutsch", "it": "Italiano", "pt": "Português",
}
## Tatoeba / Wiktionary use ISO 639-3 codes.
const ISO3 := {"en": "eng", "fr": "fra", "es": "spa", "de": "deu", "it": "ita", "pt": "por"}

const LEVELS_PER_WORLD := 6
const MIN_LEN := 3

const KEYBOARDS := {
	"qwerty": ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"],
	"azerty": ["AZERTYUIOP", "QSDFGHJKLM", "WXCVBN"],
	"qwertz": ["QWERTZUIOP", "ASDFGHJKL", "YXCVBNM"],
}
const LAYOUT := {"en": "qwerty", "fr": "azerty", "es": "qwerty", "de": "qwertz", "it": "qwerty", "pt": "qwerty"}

const BASE_LETTERS := {
	"À": "A", "Á": "A", "Â": "A", "Ã": "A", "Ä": "A",
	"Ç": "C", "È": "E", "É": "E", "Ê": "E", "Ë": "E",
	"Ì": "I", "Í": "I", "Î": "I", "Ï": "I", "Ñ": "N",
	"Ò": "O", "Ó": "O", "Ô": "O", "Õ": "O", "Ö": "O",
	"Ù": "U", "Ú": "U", "Û": "U", "Ü": "U", "Œ": "Œ",
}

var langs: Array = []
var worlds: Array = []
var _words := {}

func _ready() -> void:
	_load("res://data/vocab.json")

func _load(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Lexigo: missing vocabulary file %s" % path)
		return
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	langs = data["langs"]
	for w in data["worlds"]:
		var world := {
			"id": w["id"],
			"emoji": w["emoji"],
			"color": Color(w["color"]),
			"name": w["name"],
			"words": [],
		}
		for row in w["words"]:
			var word := {"id": "%s:%s" % [w["id"], row[1]], "emoji": row[0], "world": w["id"], "t": {}}
			for i in langs.size():
				word["t"][langs[i]] = row[i + 1]
			world["words"].append(word)
			_words[word["id"]] = word
		worlds.append(world)

func world_name(idx: int, lang: String) -> String:
	var names: Dictionary = worlds[idx]["name"]
	return names.get(lang, names["en"])

func get_word(id: String) -> Dictionary:
	return _words.get(id, {})

func all_words() -> Array:
	return _words.values()

## Uppercased crossword answer, or "" when the translation cannot be a grid entry.
func answer(word: Dictionary, target: String) -> String:
	var raw: String = word["t"].get(target, "")
	var up := raw.to_upper()
	if up.length() != raw.length() or up.length() < MIN_LEN:
		return ""
	for c in up:
		if c.to_lower() == c:
			return ""
	return up

func display(word: Dictionary, lang: String) -> String:
	return word["t"].get(lang, "")

func playable_words(world_idx: int, target: String) -> Array:
	var out := []
	for w in worlds[world_idx]["words"]:
		if answer(w, target) != "":
			out.append(w)
	return out

## Each world introduces its words over five levels (4 new + 2 recap each)
## and finishes with a larger boss grid mixing the whole world.
func level_words(world_idx: int, level_idx: int, target: String) -> Array:
	var pool := playable_words(world_idx, target)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("%s|%s" % [worlds[world_idx]["id"], target])
	_shuffle(pool, rng)
	var n := pool.size()
	var out := []
	if level_idx >= LEVELS_PER_WORLD - 1:
		rng.seed = hash("boss|%s|%s" % [worlds[world_idx]["id"], target])
		var copy := pool.duplicate()
		_shuffle(copy, rng)
		return copy.slice(0, mini(9, n))
	var per_new := ceili(float(n) / (LEVELS_PER_WORLD - 1))
	var start := level_idx * per_new
	for i in range(start, mini(start + per_new, n)):
		out.append(pool[i])
	var recap := 0
	var j := start - 1
	while recap < 2 and j >= 0:
		out.append(pool[j])
		recap += 1
		j -= 2
	var k := start + per_new
	while out.size() < 6 and k < n:
		out.append(pool[k])
		k += 1
	return out

func daily_words(target: String, unlocked_worlds: int, date_key: String) -> Array:
	var pool := []
	for i in maxi(1, unlocked_worlds):
		pool.append_array(playable_words(i, target))
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("daily|%s|%s" % [date_key, target])
	_shuffle(pool, rng)
	return pool.slice(0, mini(10, pool.size()))

## Builds generator entries for a word list, with same-world substitutes.
func crossword_entries(words: Array, target: String) -> Array:
	var entries := []
	var ids := {}
	var worlds_seen := {}
	for w in words:
		var ans := answer(w, target)
		if ans != "" and not ids.has(w["id"]):
			entries.append({"answer": ans, "word": w})
			ids[w["id"]] = true
			worlds_seen[w["world"]] = true
	var spares := []
	for i in worlds.size():
		if worlds_seen.has(worlds[i]["id"]):
			for w in playable_words(i, target):
				if not ids.has(w["id"]):
					spares.append({"answer": answer(w, target), "word": w})
	return [entries, spares]

func keyboard_rows(target: String) -> Array:
	var rows: Array = KEYBOARDS[LAYOUT.get(target, "qwerty")].duplicate()
	var extras := {}
	for w in _words.values():
		for c in answer(w, target):
			if c < "A" or c > "Z":
				extras[c] = true
	var accent: Array = extras.keys()
	accent.sort()
	return [rows, accent]

static func base_letter(c: String) -> String:
	return BASE_LETTERS.get(c, c)

func _shuffle(arr: Array, rng: RandomNumberGenerator) -> void:
	for i in range(arr.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp
