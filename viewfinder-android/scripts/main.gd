extends Node
## Scene flow: menu <-> level.

var _current: Node


func _ready() -> void:
	show_menu()


func _clear() -> void:
	get_tree().paused = false
	if _current:
		_current.queue_free()
		_current = null


func show_menu() -> void:
	_clear()
	var layer := CanvasLayer.new()
	var menu := MainMenu.new()
	menu.level_chosen.connect(start_level)
	layer.add_child(menu)
	add_child(layer)
	_current = layer


## index >= 0: a level, Game.HUB: the Station hub.
func start_level(index: int) -> void:
	_clear()
	var g := Game.new()
	g.level_index = -1 if index == Game.HUB else clampi(index, 0, Levels.count() - 1)
	g.exit_requested.connect(func(next: int):
		if next == Game.MENU:
			show_menu.call_deferred()
		else:
			start_level.call_deferred(next))
	add_child(g)
	_current = g
