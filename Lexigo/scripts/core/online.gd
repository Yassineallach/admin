extends Node
## Optional online extras. Everything here degrades gracefully: if the
## network or the service is unavailable the game keeps working offline.
##  - Example sentences: Tatoeba (CC BY 2.0 FR)
##  - Native-speaker recordings: Wiktionary / Wikimedia Commons / Lingua Libre (CC BY-SA)

const USER_AGENT := "Lexigo/1.0 (com.mardev.Lexigo; language-learning game)"
const TIMEOUT := 8.0

## Lingua Libre file names embed the Wikidata id of the language.
const LINGUA_LIBRE := {"en": "Q1860", "fr": "Q150", "es": "Q1321", "de": "Q188", "it": "Q652", "pt": "Q5146"}

var _sentence_cache := {}
var _audio_cache := {}

func enabled() -> bool:
	return Game.setting("online")

## Returns {"text": String, "translation": String} or {} when nothing is found.
func example_sentence(word: String, target: String, native: String) -> Dictionary:
	var key := "%s|%s|%s" % [word, target, native]
	if _sentence_cache.has(key):
		return _sentence_cache[key]
	var result := {}
	if enabled():
		var url := "https://tatoeba.org/eng/api_v0/search?from=%s&to=%s&query=%s&orphans=no&unapproved=no&sort=words" % [
			Vocab.ISO3[target], Vocab.ISO3[native], ("=" + word).uri_encode()]
		var json = await _get_json(url)
		if json is Dictionary and json.get("results") is Array:
			for r in json["results"]:
				var text: String = r.get("text", "")
				if text == "" or text.length() > 90:
					continue
				var tr := _first_translation(r, Vocab.ISO3[native])
				result = {"text": text, "translation": tr}
				break
	_sentence_cache[key] = result
	return result

func _first_translation(r: Dictionary, lang3: String) -> String:
	var groups = r.get("translations", [])
	if groups is Array:
		for g in groups:
			if g is Array:
				for t in g:
					if t is Dictionary and t.get("lang", "") == lang3:
						return t.get("text", "")
	return ""

## Returns an AudioStream recorded by a native speaker, or null.
func native_audio(word: String, target: String) -> AudioStream:
	var key := "%s|%s" % [word, target]
	if _audio_cache.has(key):
		return _audio_cache[key]
	var stream: AudioStream = null
	if enabled():
		var file := await _find_audio_file(word, target)
		if file != "":
			stream = await _download_audio(file)
	_audio_cache[key] = stream
	return stream

func _find_audio_file(word: String, target: String) -> String:
	var url := "https://en.wiktionary.org/w/api.php?action=query&format=json&prop=images&imlimit=100&titles=%s" % word.uri_encode()
	var json = await _get_json(url)
	if not (json is Dictionary):
		return ""
	var pages = json.get("query", {}).get("pages", {})
	var ll := "(%s)" % Vocab.ISO3[target]
	var prefix := "file:%s-" % target
	for page in pages.values():
		for img in page.get("images", []):
			var title: String = img.get("title", "")
			var low := title.to_lower()
			if not (low.ends_with(".ogg") or low.ends_with(".wav") or low.ends_with(".mp3")):
				continue
			if low.contains(ll.to_lower()) or low.contains(LINGUA_LIBRE[target].to_lower()) or low.begins_with(prefix):
				return title
	return ""

func _download_audio(file_title: String) -> AudioStream:
	var url := "https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url&titles=%s" % file_title.uri_encode()
	var json = await _get_json(url)
	if not (json is Dictionary):
		return null
	var src := ""
	for page in json.get("query", {}).get("pages", {}).values():
		var info = page.get("imageinfo", [])
		if info is Array and not info.is_empty():
			src = info[0].get("url", "")
	if src == "":
		return null
	var bytes: PackedByteArray = await _get_bytes(src)
	if bytes.is_empty():
		return null
	var low := src.to_lower()
	if low.ends_with(".mp3"):
		var mp3 := AudioStreamMP3.new()
		mp3.data = bytes
		return mp3
	if low.ends_with(".ogg"):
		return AudioStreamOggVorbis.load_from_buffer(bytes)
	if low.ends_with(".wav"):
		return AudioStreamWAV.load_from_buffer(bytes)
	return null

# ---------- http helpers ----------

func _get_json(url: String) -> Variant:
	var bytes: PackedByteArray = await _get_bytes(url)
	if bytes.is_empty():
		return null
	return JSON.parse_string(bytes.get_string_from_utf8())

func _get_bytes(url: String) -> PackedByteArray:
	var req := HTTPRequest.new()
	req.timeout = TIMEOUT
	add_child(req)
	var err := req.request(url, ["User-Agent: " + USER_AGENT, "Api-User-Agent: " + USER_AGENT])
	if err != OK:
		req.queue_free()
		return PackedByteArray()
	var res: Array = await req.request_completed
	req.queue_free()
	if res[0] != HTTPRequest.RESULT_SUCCESS or res[1] != 200:
		return PackedByteArray()
	return res[3]
