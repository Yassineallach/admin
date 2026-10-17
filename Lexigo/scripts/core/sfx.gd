extends Node
## Procedurally synthesised sound effects, text-to-speech and haptics.
## No audio assets are shipped: every effect is generated at startup.

const RATE := 22050

var _streams := {}
var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _voice_cache := {}

func _ready() -> void:
	for i in 8:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_players.append(p)
	_streams["tap"] = _tone([[880.0, 0.035]], 0.25, "sine")
	_streams["key"] = _tone([[620.0, 0.03]], 0.18, "triangle")
	_streams["select"] = _tone([[520.0, 0.04], [780.0, 0.05]], 0.2, "sine")
	_streams["correct"] = _tone([[660.0, 0.07], [880.0, 0.07], [1320.0, 0.16]], 0.3, "triangle")
	_streams["wrong"] = _tone([[220.0, 0.09], [165.0, 0.16]], 0.3, "square")
	_streams["coin"] = _tone([[1320.0, 0.05], [1760.0, 0.12]], 0.22, "square")
	_streams["hint"] = _tone([[700.0, 0.05], [1050.0, 0.05], [1400.0, 0.08]], 0.22, "sine")
	_streams["win"] = _tone([[523.0, 0.11], [659.0, 0.11], [784.0, 0.11], [1047.0, 0.32]], 0.32, "triangle")
	_streams["star"] = _tone([[1047.0, 0.06], [1568.0, 0.14]], 0.26, "sine")
	_streams["whoosh"] = _noise(0.22, 0.12)

func play(name: String, pitch := 1.0) -> void:
	if not Game.setting("sfx") or not _streams.has(name):
		return
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = _streams[name]
	p.pitch_scale = pitch
	p.play()

func play_stream(stream: AudioStream) -> void:
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = stream
	p.pitch_scale = 1.0
	p.play()

func buzz(ms := 25) -> void:
	if Game.setting("haptics") and OS.has_feature("mobile"):
		Input.vibrate_handheld(ms)

# ---------- text to speech ----------

func can_speak(lang: String) -> bool:
	return _voice_for(lang) != ""

func speak(text: String, lang: String) -> bool:
	if not Game.setting("voice"):
		return false
	var v := _voice_for(lang)
	if v == "":
		return false
	DisplayServer.tts_stop()
	DisplayServer.tts_speak(text, v, 80, 1.0, 0.9)
	return true

func _voice_for(lang: String) -> String:
	if _voice_cache.has(lang):
		return _voice_cache[lang]
	var v := ""
	if DisplayServer.has_feature(DisplayServer.FEATURE_TEXT_TO_SPEECH):
		var voices := DisplayServer.tts_get_voices_for_language(lang)
		if not voices.is_empty():
			v = voices[0]
	_voice_cache[lang] = v
	return v

# ---------- synthesis ----------

func _tone(notes: Array, volume: float, wave: String) -> AudioStreamWAV:
	var data := PackedByteArray()
	for n in notes:
		var freq: float = n[0]
		var dur: float = n[1]
		var count := int(dur * RATE)
		for i in count:
			var t := float(i) / RATE
			var phase := fmod(t * freq, 1.0)
			var s := 0.0
			match wave:
				"square":
					s = 1.0 if phase < 0.5 else -1.0
					s *= 0.5
				"triangle":
					s = 4.0 * absf(phase - 0.5) - 1.0
				_:
					s = sin(TAU * phase)
			var attack := minf(1.0, i / (RATE * 0.004))
			var release := pow(1.0 - float(i) / count, 2.0)
			_push(data, s * volume * attack * release)
	return _wav(data)

func _noise(dur: float, volume: float) -> AudioStreamWAV:
	var data := PackedByteArray()
	var count := int(dur * RATE)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var lp := 0.0
	for i in count:
		var k := float(i) / count
		lp = lerpf(lp, rng.randf_range(-1.0, 1.0), 0.08 + k * 0.4)
		_push(data, lp * volume * sin(PI * k))
	return _wav(data)

func _push(data: PackedByteArray, s: float) -> void:
	var v := int(clampf(s, -1.0, 1.0) * 32767.0)
	data.append(v & 0xFF)
	data.append((v >> 8) & 0xFF)

func _wav(data: PackedByteArray) -> AudioStreamWAV:
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.stereo = false
	w.data = data
	return w
