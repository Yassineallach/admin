extends Node
## Persists which levels are unlocked / completed.

const PATH := "user://progress.cfg"

var unlocked: int = 1
var completed: Dictionary = {}
var settings := {"look_sensitivity": 1.0, "invert_y": false}


func _ready() -> void:
	load_progress()


func load_progress() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	unlocked = int(cfg.get_value("progress", "unlocked", 1))
	completed = cfg.get_value("progress", "completed", {})
	for k in settings.keys():
		settings[k] = cfg.get_value("settings", k, settings[k])


func save_progress() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("progress", "unlocked", unlocked)
	cfg.set_value("progress", "completed", completed)
	for k in settings.keys():
		cfg.set_value("settings", k, settings[k])
	cfg.save(PATH)


func mark_completed(index: int) -> void:
	completed[index] = true
	unlocked = maxi(unlocked, index + 2)
	save_progress()
