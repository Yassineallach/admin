extends Node
## Procedurally synthesised sound effects + ambient music (no audio assets).
## Autoloaded as `Sfx`. Call Sfx.play("shutter").

const RATE := 22050
const MUSIC_RATE := 11025

var _streams: Dictionary = {}
var _players: Array[AudioStreamPlayer] = []
var _music: AudioStreamPlayer
var _ambience: AudioStreamPlayer
var _loops: Dictionary = {}  # name -> AudioStreamPlayer
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rng.seed = 7
	_streams["shutter"] = _shutter()
	_streams["eject"] = _eject()
	_streams["place"] = _place()
	_streams["chime"] = _chime([880.0, 1318.5], 0.5)
	_streams["pickup"] = _chime([659.3, 987.8, 1318.5], 0.6)
	_streams["click"] = _click()
	_streams["teleport"] = _chime([523.3, 659.3, 784.0, 1046.5, 1318.5], 1.4)
	_streams["denied"] = _tone(180.0, 0.18, 0.35)
	_streams["purr"] = _purr()
	_streams["rewind"] = _rewind()
	_streams["paper"] = _paper()
	_streams["meow"] = _meow()
	_streams["step"] = _step()
	_streams["land"] = _land()
	_streams["hum"] = _hum()
	for i in 8:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_players.append(p)
	_music = AudioStreamPlayer.new()
	_music.volume_db = -9.0
	add_child(_music)
	_ambience = AudioStreamPlayer.new()
	_ambience.volume_db = -12.0
	add_child(_ambience)
	# Music takes a moment to synthesise: do it after the first frame.
	_build_music.call_deferred()


func play(name: String, volume_db: float = 0.0, pitch: float = 1.0) -> void:
	var s: AudioStream = _streams.get(name)
	if s == null:
		return
	for p in _players:
		if not p.playing:
			p.stream = s
			p.volume_db = volume_db
			p.pitch_scale = pitch
			p.play()
			return


func get_stream(name: String) -> AudioStream:
	return _streams.get(name)


func loop(name: String, on: bool, volume_db: float = -4.0) -> void:
	var p: AudioStreamPlayer = _loops.get(name)
	if on:
		if p == null:
			p = AudioStreamPlayer.new()
			p.stream = _streams[name]
			add_child(p)
			_loops[name] = p
		p.volume_db = volume_db
		if not p.playing:
			p.play()
	elif p and p.playing:
		p.stop()


## Music and ambience are synthesised on the main thread a slice at a time
## (a few thousand samples per frame) so nothing runs on a background thread
## and the game never hitches.
func _build_music() -> void:
	var w: AudioStreamWAV = await _music_loop()
	var amb: AudioStreamWAV = await _ambience_loop()
	if is_inside_tree():
		_start_music(w, amb)


const SAMPLES_PER_FRAME := 2500


func _yield_now(i: int) -> bool:
	return i % SAMPLES_PER_FRAME == SAMPLES_PER_FRAME - 1 and is_inside_tree()


func _start_music(w: AudioStreamWAV, amb: AudioStreamWAV) -> void:
	_music.stream = w
	_music.play()
	_ambience.stream = amb
	_ambience.play()


func set_music(on: bool) -> void:
	_music.stream_paused = not on


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------

## Safety margin after every buffer. The mixer reads a few samples ahead
## while resampling (pitch_scale != 1, 11 kHz music at 44/48 kHz output). A
## buffer that ends exactly on its last sample let it read past the end of the
## allocation, which crashed the audio thread on some Android phones
## (SIGSEGV in AudioTrack).
const PAD := 512


func _wav(samples: PackedFloat32Array, rate: int = RATE, looped: bool = false) -> AudioStreamWAV:
	var n := samples.size()
	var data := PackedByteArray()
	data.resize((n + PAD) * 2)
	data.fill(0)
	for i in n:
		data.encode_s16(i * 2, int(clampf(samples[i], -1.0, 1.0) * 32000.0))
	if looped and n > 0:
		# Continue the waveform past the loop point so any read-ahead stays
		# both in bounds and seamless.
		for i in PAD:
			data.encode_s16((n + i) * 2, int(clampf(samples[i % n], -1.0, 1.0) * 32000.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = rate
	w.stereo = false
	w.data = data
	if looped:
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_begin = 0
		w.loop_end = n  # loop well inside the padded buffer
	return w


func _buf(seconds: float, rate: int = RATE) -> PackedFloat32Array:
	var b := PackedFloat32Array()
	b.resize(int(seconds * rate))
	return b


func _shutter() -> AudioStreamWAV:
	var b := _buf(0.22)
	for i in b.size():
		var t := float(i) / RATE
		var n := _rng.randf_range(-1, 1)
		var click1 := n * exp(-t * 300.0)
		var t2 := t - 0.07
		var click2 := 0.0
		if t2 > 0:
			click2 = _rng.randf_range(-1, 1) * exp(-t2 * 220.0) * 0.8 + sin(TAU * 1800.0 * t2) * exp(-t2 * 120.0) * 0.3
		b[i] = (click1 + click2) * 0.7
	return _wav(b)


func _eject() -> AudioStreamWAV:
	var b := _buf(0.9)
	var phase := 0.0
	for i in b.size():
		var t := float(i) / RATE
		var f := 140.0 + 40.0 * sin(t * 30.0)
		phase += TAU * f / RATE
		var env := minf(t * 20.0, 1.0) * clampf((0.9 - t) * 6.0, 0.0, 1.0)
		var buzz := (fmod(phase, TAU) / TAU - 0.5) * 0.5 + _rng.randf_range(-0.15, 0.15)
		b[i] = buzz * env * 0.45
	return _wav(b)


func _place() -> AudioStreamWAV:
	var b := _buf(0.8)
	var lp := 0.0
	for i in b.size():
		var t := float(i) / RATE
		var cutoff := lerpf(0.02, 0.35, clampf(t / 0.25, 0.0, 1.0)) * clampf((0.8 - t) / 0.5, 0.0, 1.0)
		lp += (_rng.randf_range(-1, 1) - lp) * cutoff
		var whoosh := lp * 1.6 * minf(t * 8.0, 1.0)
		var thump := sin(TAU * 70.0 * t) * exp(-maxf(t - 0.22, 0.0) * 18.0) * (1.0 if t > 0.22 else 0.0)
		b[i] = whoosh * 0.6 + thump * 0.55
	return _wav(b)


func _chime(freqs: Array, dur: float) -> AudioStreamWAV:
	var b := _buf(dur + 0.6)
	var step := 0.08
	for k in freqs.size():
		var f: float = freqs[k]
		var start := int(k * step * RATE)
		for i in range(start, b.size()):
			var t := float(i - start) / RATE
			var env := exp(-t * 4.0) * minf(t * 200.0, 1.0)
			b[i] += (sin(TAU * f * t) + 0.3 * sin(TAU * f * 2.0 * t)) * env * 0.22
	return _wav(b)


func _tone(f: float, dur: float, vol: float) -> AudioStreamWAV:
	var b := _buf(dur)
	for i in b.size():
		var t := float(i) / RATE
		b[i] = sin(TAU * f * t) * vol * minf(t * 100.0, 1.0) * clampf((dur - t) * 30.0, 0.0, 1.0)
	return _wav(b)


func _click() -> AudioStreamWAV:
	var b := _buf(0.12)
	for i in b.size():
		var t := float(i) / RATE
		b[i] = (sin(TAU * 2400.0 * t) * 0.4 + _rng.randf_range(-1, 1) * 0.5) * exp(-t * 90.0)
	return _wav(b)


func _paper() -> AudioStreamWAV:
	var b := _buf(0.35)
	var lp := 0.0
	for i in b.size():
		var t := float(i) / RATE
		lp += (_rng.randf_range(-1, 1) - lp) * 0.5
		var crackle := 1.0 if _rng.randf() < 0.02 else 0.3
		b[i] = lp * crackle * sin(PI * t / 0.35) * 0.5
	return _wav(b)


func _purr() -> AudioStreamWAV:
	var dur := 2.0
	var b := _buf(dur)
	var lp := 0.0
	for i in b.size():
		var t := float(i) / RATE
		lp += (_rng.randf_range(-1, 1) - lp) * 0.08
		var am := 0.5 + 0.5 * sin(TAU * 24.0 * t)
		var breath := 0.6 + 0.4 * sin(TAU * t / dur)
		b[i] = lp * am * breath * 2.2
	return _wav(b, RATE, true)


func _meow() -> AudioStreamWAV:
	var b := _buf(0.6)
	var phase := 0.0
	for i in b.size():
		var t := float(i) / RATE
		var f := 520.0 + 260.0 * sin(PI * clampf(t / 0.5, 0.0, 1.0)) - 120.0 * t
		phase += TAU * f / RATE
		var env := minf(t * 25.0, 1.0) * clampf((0.6 - t) * 5.0, 0.0, 1.0)
		var v := sin(phase) + 0.45 * sin(phase * 2.0) + 0.2 * sin(phase * 3.0)
		b[i] = v * env * 0.22
	return _wav(b)


func _rewind() -> AudioStreamWAV:
	var dur := 1.0
	var b := _buf(dur)
	var phase := 0.0
	for i in b.size():
		var t := float(i) / RATE
		var f := 300.0 + 220.0 * (1.0 - fmod(t * 4.0, 1.0))
		phase += TAU * f / RATE
		b[i] = (sin(phase) * 0.18 + _rng.randf_range(-0.05, 0.05)) * (0.7 + 0.3 * sin(TAU * 8.0 * t))
	return _wav(b, RATE, true)


## A gentle 16-second ambient loop: warm pad chords plus a sparse music-box
## arpeggio. Built so the end flows seamlessly into the start.
func _step() -> AudioStreamWAV:
	var b := _buf(0.14)
	var lp := 0.0
	for i in b.size():
		var t := float(i) / RATE
		lp += (_rng.randf_range(-1, 1) - lp) * 0.18
		b[i] = (lp * 1.4 + sin(TAU * 90.0 * t) * 0.4) * exp(-t * 38.0) * minf(t * 400.0, 1.0)
	return _wav(b)


func _land() -> AudioStreamWAV:
	var b := _buf(0.3)
	var lp := 0.0
	for i in b.size():
		var t := float(i) / RATE
		lp += (_rng.randf_range(-1, 1) - lp) * 0.1
		b[i] = (lp * 1.6 + sin(TAU * 60.0 * t) * 0.7) * exp(-t * 16.0) * minf(t * 300.0, 1.0)
	return _wav(b)


func _hum() -> AudioStreamWAV:
	var dur := 2.0
	var b := _buf(dur)
	for i in b.size():
		var t := float(i) / RATE
		var wob := 1.0 + 0.25 * sin(TAU * 0.5 * t)
		b[i] = (sin(TAU * 110.0 * t) * 0.18 + sin(TAU * 220.0 * t) * 0.08 * wob + sin(TAU * 330.5 * t) * 0.04) * 0.8
	return _wav(b, RATE, true)


## Gentle wind with the occasional bird call (12 s, loops).
func _ambience_loop() -> AudioStreamWAV:
	var rng := RandomNumberGenerator.new()
	rng.seed = 99
	var length := 12.0
	var n := int(length * MUSIC_RATE)
	var b := PackedFloat32Array()
	b.resize(n)
	var lp := 0.0
	var lp2 := 0.0
	for i in n:
		var t := float(i) / MUSIC_RATE
		lp += (rng.randf_range(-1, 1) - lp) * 0.02
		lp2 += (lp - lp2) * 0.3
		var gust := 0.55 + 0.45 * sin(TAU * t / length) * sin(TAU * t * 2.0 / length + 1.0)
		b[i] = lp2 * 2.2 * gust
		if _yield_now(i):
			await get_tree().process_frame
	# Bird chirps: short frequency sweeps.
	var calls := [[1.3, 2600.0], [1.45, 3000.0], [4.8, 2200.0], [5.0, 2500.0], [5.15, 2800.0], [8.6, 3200.0], [8.75, 2700.0]]
	for cl in calls:
		var start := int(float(cl[0]) * MUSIC_RATE)
		var f0: float = cl[1]
		var dur := 0.09
		var phase := 0.0
		for k in int(dur * MUSIC_RATE):
			var t := float(k) / MUSIC_RATE
			var f := f0 * (1.0 + 0.6 * sin(PI * t / dur))
			phase += TAU * minf(f, MUSIC_RATE * 0.45) / MUSIC_RATE
			if start + k < n:
				b[start + k] += sin(phase) * sin(PI * t / dur) * 0.08
	return _wav(b, MUSIC_RATE, true)


func _music_loop() -> AudioStreamWAV:
	var length := 16.0
	var n := int(length * MUSIC_RATE)
	var b := PackedFloat32Array()
	b.resize(n)
	# Cmaj7 - Am9 - Fmaj7 - G6 (root frequencies in Hz)
	var chords := [
		[130.81, 196.0, 246.94, 329.63],
		[110.0, 164.81, 246.94, 261.63],
		[87.31, 174.61, 220.0, 329.63],
		[98.0, 196.0, 246.94, 329.63],
	]
	var arp := [523.25, 659.25, 783.99, 987.77, 880.0, 659.25, 587.33, 783.99,
		523.25, 659.25, 698.46, 880.0, 783.99, 659.25, 587.33, 493.88]
	var chord_len := length / chords.size()
	for i in n:
		var t := float(i) / MUSIC_RATE
		var v := 0.0
		for c in chords.size():
			# Distance in time from this chord's window (wrapping for seamless loop).
			var start := c * chord_len
			var dt := fposmod(t - start, length)
			if dt > chord_len + 2.0:
				continue
			var env := minf(dt / 1.5, 1.0) * clampf((chord_len + 2.0 - dt) / 2.0, 0.0, 1.0)
			for f in chords[c]:
				var ff: float = f
				v += (sin(TAU * ff * t) + 0.25 * sin(TAU * ff * 2.0 * t + 0.5)) * env * 0.05
		var step := length / arp.size()
		var k := int(t / step)
		var at := t - k * step
		var note: float = arp[k % arp.size()]
		v += sin(TAU * note * at) * exp(-at * 3.2) * 0.07 * minf(at * 300.0, 1.0)
		# Tail of the previous note across the loop boundary.
		var prev: float = arp[(k - 1 + arp.size()) % arp.size()]
		var pt := at + step
		v += sin(TAU * prev * pt) * exp(-pt * 3.2) * 0.07
		b[i] = v
		if _yield_now(i):
			await get_tree().process_frame
	return _wav(b, MUSIC_RATE, true)
