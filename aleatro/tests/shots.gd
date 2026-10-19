extends Node
## Renders each screen to build/shots/*.png. Run with a display:
##   godot --path . res://tests/shots.tscn

var main: Control


func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await _shot("1_title")
	Run.new_run(42)
	Run.charms = [Charms.make("lucky_penny"), Charms.make("twin_flame"), Charms.make("loaded_die")]
	main.show_select()
	await _shot("2_select")
	Run.start_trial()
	Run.deck[0].enh = "bonus"
	main.show_round()
	for i in 3:
		main._on_card_tapped(main.hand_row.get_child(i))
	await _shot("3_round_selected")
	main._on_card_inspected(main.hand_row.get_child(0))
	await get_tree().create_timer(0.4).timeout
	await _shot("3b_card_tooltip")
	main._on_charm_tapped(main.charm_views[2])
	await get_tree().create_timer(0.4).timeout
	await _shot("3c_charm_tooltip")
	main._hide_tooltip()
	main._on_play()
	await get_tree().create_timer(1.2).timeout
	await _shot("4_scoring")
	await get_tree().create_timer(4.0).timeout
	await _shot("5_after_play")
	Run.coins = 23
	Run.open_shop()
	main.show_shop()
	await _shot("6_shop")
	Run.trial_idx = 2
	main.show_select()
	await _shot("7_warden_select")
	get_tree().quit()


func _shot(name: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("res://build/shots/%s.png" % name)
