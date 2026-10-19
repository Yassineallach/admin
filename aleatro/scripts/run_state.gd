extends Node
## State of the current run and the rules that move it forward. Autoloaded as `Run`.
## Cards are {"id", "rank" (2-14), "suit" (0-3), "enh"}.

const HAND_SIZE := 8
const HANDS_PER_TRIAL := 4
const DISCARDS_PER_TRIAL := 3
const MAX_SELECT := 5
const MAX_CHARMS := 5
const FLOORS := 8
const START_COINS := 4
const SHOP_SLOTS := 3
const BASE_REROLL := 5
const FLOOR_TARGETS := [200, 560, 1500, 3800, 8600, 16500, 28000, 44000]
const TRIAL_NAMES := ["Minor Trial", "Major Trial", "Warden"]
const TRIAL_SCALE := [1.0, 1.5, 2.0]
const TRIAL_REWARD := [3, 4, 5]
const SAVE_PATH := "user://aleatro.cfg"

const WARDENS := {
	"miser": {"name": "The Miser", "desc": "No discards this trial"},
	"blight": {"name": "The Blight", "desc": "%s are muted and do not score"},
	"vise": {"name": "The Vise", "desc": "Hand size is 2 smaller"},
	"glutton": {"name": "The Glutton", "desc": "You must play exactly 5 cards"},
	"bastion": {"name": "The Bastion", "desc": "The target is 50% higher"},
	"halver": {"name": "The Halver", "desc": "Base Points and Mult are halved"},
	"tithe": {"name": "The Tithe", "desc": "Lose 1 coin for every card played"},
	"sentinel": {"name": "The Sentinel", "desc": "Only 2 hands this trial"},
}

const SIGILS := {
	"bonus": {"name": "Sigil of Weight", "desc": "3 random cards become Bonus (+25 Points)", "price": 3},
	"spark": {"name": "Sigil of Spark", "desc": "3 random cards become Spark (+3 Mult)", "price": 3},
	"glass": {"name": "Sigil of Glass", "desc": "2 random cards become Glass (x2 Mult, may shatter)", "price": 4},
	"iron": {"name": "Sigil of Iron", "desc": "2 random cards become Iron (x1.5 Mult while held)", "price": 4},
	"cull": {"name": "Sigil of Culling", "desc": "Destroy the 3 lowest cards in your deck", "price": 3},
	"mirror": {"name": "Sigil of Echoes", "desc": "Copy 2 random cards in your deck", "price": 4},
}
const RUNE_PRICE := 3

var rng := RandomNumberGenerator.new()
var seed_value := 0
var next_uid := 0
var deck: Array = []
var draw_pile: Array = []
var hand: Array = []
var charms: Array = []
var coins := START_COINS
var floor_num := 1
var trial_idx := 0
var hand_levels := {}
var hands_left := 0
var discards_left := 0
var score := 0.0
var trial_won := false
var warden_key := ""
var muted_suit := 0
var reroll_cost := BASE_REROLL
var shop_offers: Array = []
var best_floor := 0


func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		best_floor = cfg.get_value("stats", "best_floor", 0)


func new_run(seed_in := 0) -> void:
	seed_value = seed_in if seed_in != 0 else randi()
	rng.seed = seed_value
	next_uid = 0
	deck.clear()
	for s in 4:
		for r in range(2, 15):
			deck.append(make_card(r, s))
	charms.clear()
	hand.clear()
	draw_pile.clear()
	coins = START_COINS
	floor_num = 1
	trial_idx = 0
	hand_levels.clear()
	for h in HandEval.ORDER:
		hand_levels[h] = 1
	_pick_warden()


func make_card(rank: int, suit: int, enh := "") -> Dictionary:
	var c := {"id": next_uid, "rank": rank, "suit": suit, "enh": enh}
	next_uid += 1
	return c


# --- Trials -----------------------------------------------------------------

func _pick_warden() -> void:
	var keys := WARDENS.keys()
	warden_key = keys[rng.randi_range(0, keys.size() - 1)]
	muted_suit = rng.randi_range(0, 3)


## Warden id while the warden trial is being played, else "".
func current_warden() -> String:
	return warden_key if trial_idx == 2 else ""


func warden_name() -> String:
	return WARDENS[warden_key].name


func warden_desc() -> String:
	var d: String = WARDENS[warden_key].desc
	if warden_key == "blight":
		d = d % HandEval.SUIT_NAMES[muted_suit]
	return d


func is_muted(card: Dictionary) -> bool:
	return current_warden() == "blight" and card.suit == muted_suit


func target(trial := -1) -> float:
	var t := trial if trial >= 0 else trial_idx
	var base: float = FLOOR_TARGETS[floor_num - 1] * TRIAL_SCALE[t]
	if t == 2 and warden_key == "bastion":
		base *= 1.5
	return base


func hand_size() -> int:
	return HAND_SIZE - (2 if current_warden() == "vise" else 0)


func start_trial() -> void:
	score = 0.0
	trial_won = false
	hands_left = HANDS_PER_TRIAL
	discards_left = DISCARDS_PER_TRIAL
	match current_warden():
		"miser":
			discards_left = 0
		"sentinel":
			hands_left = 2
	draw_pile = deck.duplicate()
	shuffle(draw_pile)
	hand.clear()
	draw_to_full()


func shuffle(a: Array) -> void:
	for i in range(a.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = a[i]
		a[i] = a[j]
		a[j] = tmp


func draw_to_full() -> void:
	while hand.size() < hand_size() and not draw_pile.is_empty():
		hand.append(draw_pile.pop_back())


## Empty string when the selection can be played, otherwise the reason it cannot.
func can_play(selected: Array) -> String:
	if selected.is_empty():
		return "Select at least one card"
	if selected.size() > MAX_SELECT:
		return "Play at most %d cards" % MAX_SELECT
	if current_warden() == "glutton" and selected.size() != 5:
		return "The Glutton demands exactly 5 cards"
	return ""


func play(selected: Array) -> Dictionary:
	var held := hand.filter(func(c): return not selected.has(c))
	var result := Scoring.score_play(self, selected, held)
	score += result.total
	hands_left -= 1
	for c in selected:
		hand.erase(c)
	if current_warden() == "tithe":
		coins = maxi(0, coins - selected.size())
	var broken := []
	for c in result.scoring:
		if c.enh == "glass" and rng.randi_range(1, 4) == 1:
			broken.append(c)
			deck.erase(c)
	result["broken"] = broken
	for ch in charms:
		Charms.after_play(ch)
	if score >= target():
		trial_won = true
		best_floor = maxi(best_floor, floor_num)
		save_stats()
	else:
		draw_to_full()
	return result


func discard(selected: Array) -> bool:
	if discards_left <= 0 or selected.is_empty():
		return false
	for c in selected:
		hand.erase(c)
	discards_left -= 1
	draw_to_full()
	return true


func is_lost() -> bool:
	return not trial_won and hands_left <= 0


## Rows of [label, coins] earned for clearing the current trial.
func trial_rewards() -> Array:
	var rows := [[TRIAL_NAMES[trial_idx] + " cleared", TRIAL_REWARD[trial_idx]]]
	if hands_left > 0:
		rows.append(["Unused hands (%d)" % hands_left, hands_left])
	var interest := mini(coins / 5, 5)
	if interest > 0:
		rows.append(["Interest (1 per 5 held)", interest])
	for ch in charms:
		var c := Charms.end_trial_coins(ch)
		if c > 0:
			rows.append([Charms.name_of(ch), c])
	return rows


func collect(rows: Array) -> void:
	for row in rows:
		coins += row[1]


## Moves to the next trial. Returns "victory" after the last floor, otherwise "select".
func advance() -> String:
	trial_idx += 1
	if trial_idx > 2:
		trial_idx = 0
		floor_num += 1
		if floor_num > FLOORS:
			floor_num = FLOORS
			return "victory"
		_pick_warden()
	return "select"


## Skips a minor or major trial for a small reward. Returns a description of the reward.
func skip_trial() -> String:
	var msg := ""
	if rng.randf() < 0.5:
		coins += 5
		msg = "Skipped: +5 coins"
	else:
		var h: String = HandEval.ORDER[rng.randi_range(0, HandEval.ORDER.size() - 1)]
		hand_levels[h] += 1
		msg = "Skipped: %s leveled up to %d" % [HandEval.INFO[h].name, hand_levels[h]]
	advance()
	return msg


func save_stats() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("stats", "best_floor", best_floor)
	cfg.save(SAVE_PATH)


# --- Shop -------------------------------------------------------------------

func open_shop() -> void:
	reroll_cost = BASE_REROLL
	roll_shop()


func roll_shop() -> void:
	shop_offers.clear()
	for i in SHOP_SLOTS:
		shop_offers.append(_random_offer())


func _owned_ids() -> Array:
	var ids := []
	for ch in charms:
		ids.append(ch.id)
	for o in shop_offers:
		if o.type == "charm":
			ids.append(o.id)
	return ids


func _random_offer() -> Dictionary:
	var roll := rng.randf()
	if roll < 0.6:
		var id := Charms.random_id(rng, _owned_ids())
		if id != "":
			return {"type": "charm", "id": id, "price": Charms.DEFS[id].price}
	if roll < 0.85:
		var h: String = HandEval.ORDER[rng.randi_range(0, HandEval.ORDER.size() - 1)]
		return {"type": "rune", "hand": h, "price": RUNE_PRICE}
	var keys := SIGILS.keys()
	var s: String = keys[rng.randi_range(0, keys.size() - 1)]
	return {"type": "sigil", "id": s, "price": SIGILS[s].price}


func offer_title(o: Dictionary) -> String:
	match o.type:
		"charm":
			return Charms.DEFS[o.id].name
		"rune":
			return "Rune: " + HandEval.INFO[o.hand].name
		"sigil":
			return SIGILS[o.id].name
	return ""


func offer_desc(o: Dictionary) -> String:
	match o.type:
		"charm":
			return "%s charm. %s" % [Charms.RARITY_NAMES[Charms.DEFS[o.id].rarity], Charms.DEFS[o.id].desc]
		"rune":
			var info: Dictionary = HandEval.INFO[o.hand]
			return "Level up %s (Lv.%d): +%d Points, +%d Mult" % [info.name, hand_levels[o.hand], info.lp, info.lm]
		"sigil":
			return SIGILS[o.id].desc
	return ""


func reroll() -> bool:
	if coins < reroll_cost:
		return false
	coins -= reroll_cost
	reroll_cost += 1
	roll_shop()
	return true


## Buys an offer. Returns {"ok": bool, "msg": String}.
func buy(i: int) -> Dictionary:
	var o: Dictionary = shop_offers[i]
	if o.type == "sold":
		return {"ok": false, "msg": "Already sold"}
	if coins < o.price:
		return {"ok": false, "msg": "Not enough coins"}
	if o.type == "charm" and charms.size() >= MAX_CHARMS:
		return {"ok": false, "msg": "Charm slots are full. Sell one first."}
	coins -= o.price
	var msg := ""
	match o.type:
		"charm":
			charms.append(Charms.make(o.id))
			msg = "Bought %s" % Charms.DEFS[o.id].name
		"rune":
			hand_levels[o.hand] += 1
			msg = "%s is now level %d" % [HandEval.INFO[o.hand].name, hand_levels[o.hand]]
		"sigil":
			msg = apply_sigil(o.id)
	shop_offers[i] = {"type": "sold", "price": 0}
	return {"ok": true, "msg": msg}


func sell_charm(i: int) -> String:
	var ch: Dictionary = charms[i]
	var value := Charms.sell_value(ch)
	coins += value
	charms.remove_at(i)
	return "Sold %s for %d coins" % [Charms.name_of(ch), value]


func move_charm(i: int, delta: int) -> void:
	var j := i + delta
	if j < 0 or j >= charms.size():
		return
	var tmp = charms[i]
	charms[i] = charms[j]
	charms[j] = tmp


func apply_sigil(id: String) -> String:
	match id:
		"bonus", "spark":
			return _enhance(3, id)
		"glass", "iron":
			return _enhance(2, id)
		"cull":
			if deck.size() <= 20:
				return "Your deck is too small to cull"
			var sorted := deck.duplicate()
			sorted.sort_custom(func(a, b): return a.rank < b.rank)
			var names := PackedStringArray()
			for c in sorted.slice(0, 3):
				deck.erase(c)
				names.append(HandEval.card_name(c))
			return "Destroyed " + ", ".join(names)
		"mirror":
			var names := PackedStringArray()
			for n in 2:
				var src: Dictionary = deck[rng.randi_range(0, deck.size() - 1)]
				deck.append(make_card(src.rank, src.suit, src.enh))
				names.append(HandEval.card_name(src))
			return "Copied " + ", ".join(names)
	return ""


func _enhance(n: int, enh: String) -> String:
	var pool := deck.filter(func(c): return c.enh == "")
	if pool.is_empty():
		pool = deck.duplicate()
	shuffle(pool)
	var names := PackedStringArray()
	for c in pool.slice(0, n):
		c.enh = enh
		names.append(HandEval.card_name(c))
	return "%s: %s" % [Scoring.ENHANCEMENTS[enh].name, ", ".join(names)]
