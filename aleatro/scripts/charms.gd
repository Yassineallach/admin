class_name Charms
extends RefCounted
## Charm definitions and the hooks the scoring pipeline calls.
## A charm instance is {"id": String, "acc": int}; acc holds scaling state.

const RARITY_NAMES := ["Common", "Uncommon", "Rare"]
const RARITY_WEIGHTS := [70, 25, 8]
const PAIR_HANDS := ["pair", "two_pair", "three", "full_house", "four", "five"]

const DEFS := {
	"lucky_penny": {"name": "Lucky Penny", "desc": "+4 Mult", "rarity": 0, "price": 4},
	"twin_flame": {"name": "Twin Flame", "desc": "+8 Mult if the hand contains a pair", "rarity": 0, "price": 5},
	"ladder": {"name": "Ladder", "desc": "+90 Points if the hand is a Straight", "rarity": 0, "price": 5},
	"ink_blot": {"name": "Ink Blot", "desc": "+10 Mult if the hand is a Flush", "rarity": 0, "price": 5},
	"crimson_thread": {"name": "Crimson Thread", "desc": "Scored Hearts and Diamonds give +2 Mult", "rarity": 0, "price": 5},
	"night_thread": {"name": "Night Thread", "desc": "Scored Clubs and Spades give +20 Points", "rarity": 0, "price": 5},
	"odd_one": {"name": "Odd One", "desc": "Scored A, 3, 5, 7 and 9 give +3 Mult", "rarity": 0, "price": 5},
	"even_keel": {"name": "Even Keel", "desc": "Scored 2, 4, 6, 8 and 10 give +25 Points", "rarity": 0, "price": 5},
	"royal_court": {"name": "Royal Court", "desc": "Scored J, Q and K give +30 Points", "rarity": 0, "price": 5},
	"underdog": {"name": "Underdog", "desc": "+15 Mult if the hand is a High Card", "rarity": 0, "price": 4},
	"hoarder": {"name": "Hoarder", "desc": "+3 Points per card left in the draw pile", "rarity": 0, "price": 5},
	"tax_return": {"name": "Tax Return", "desc": "Earn 3 coins after each trial", "rarity": 0, "price": 5},
	"hourglass": {"name": "Hourglass", "desc": "+5 Mult per discard remaining", "rarity": 1, "price": 6},
	"piggy_bank": {"name": "Piggy Bank", "desc": "+1 Mult per 3 coins you hold", "rarity": 1, "price": 6},
	"high_roller": {"name": "High Roller", "desc": "Adds 3x the Points of the highest scored card", "rarity": 1, "price": 6},
	"snowball": {"name": "Snowball", "desc": "Gains +2 Mult every hand played", "rarity": 1, "price": 7},
	"echo": {"name": "Echo", "desc": "The first scored card scores twice", "rarity": 1, "price": 7},
	"minimalist": {"name": "Minimalist", "desc": "x2 Mult if you play 3 or fewer cards", "rarity": 1, "price": 7},
	"gambler": {"name": "Gambler", "desc": "1 in 3 chance of x4 Mult", "rarity": 2, "price": 8},
	"last_stand": {"name": "Last Stand", "desc": "x3 Mult on the final hand of a trial", "rarity": 2, "price": 8},
	"loaded_die": {"name": "Loaded Die", "desc": "x1.5 Mult", "rarity": 2, "price": 8},
	"prism": {"name": "Prism", "desc": "x3 Mult if scored cards include all 4 suits", "rarity": 2, "price": 9},
}


static func make(id: String) -> Dictionary:
	return {"id": id, "acc": 0}


static func name_of(ch: Dictionary) -> String:
	return DEFS[ch.id].name


static func describe(ch: Dictionary) -> String:
	var d: String = DEFS[ch.id].desc
	if ch.id == "snowball":
		d += " (now +%d)" % ch.acc
	return d


static func rarity_of(ch: Dictionary) -> int:
	return DEFS[ch.id].rarity


static func sell_value(ch: Dictionary) -> int:
	return maxi(1, int(DEFS[ch.id].price) / 2)


static func random_id(rng: RandomNumberGenerator, exclude: Array) -> String:
	var total := 0
	for w in RARITY_WEIGHTS:
		total += w
	var roll := rng.randi_range(1, total)
	var rarity := 0
	while roll > RARITY_WEIGHTS[rarity]:
		roll -= RARITY_WEIGHTS[rarity]
		rarity += 1
	var pool := []
	for id in DEFS:
		if DEFS[id].rarity == rarity and not exclude.has(id):
			pool.append(id)
	if pool.is_empty():
		for id in DEFS:
			if not exclude.has(id):
				pool.append(id)
	if pool.is_empty():
		return ""
	return pool[rng.randi_range(0, pool.size() - 1)]


## Effect of a charm when a single card scores. Returns {} or {"points"|"mult"|"xmult": n}.
static func on_card(ch: Dictionary, card: Dictionary, _ctx: Dictionary) -> Dictionary:
	var r: int = card.rank
	var s: int = card.suit
	match ch.id:
		"crimson_thread":
			if s <= 1:
				return {"mult": 2}
		"night_thread":
			if s >= 2:
				return {"points": 20}
		"odd_one":
			if r == 14 or (r <= 9 and r % 2 == 1):
				return {"mult": 3}
		"even_keel":
			if r <= 10 and r % 2 == 0:
				return {"points": 25}
		"royal_court":
			if r >= 11 and r <= 13:
				return {"points": 30}
	return {}


## Effect of a charm after all cards have scored.
static func on_hand(ch: Dictionary, ctx: Dictionary) -> Dictionary:
	var run = ctx.run
	var hand: String = ctx.hand
	match ch.id:
		"lucky_penny":
			return {"mult": 4}
		"twin_flame":
			if PAIR_HANDS.has(hand):
				return {"mult": 8}
		"ladder":
			if hand == "straight" or hand == "straight_flush":
				return {"points": 90}
		"ink_blot":
			if hand == "flush" or hand == "straight_flush":
				return {"mult": 10}
		"underdog":
			if hand == "high":
				return {"mult": 15}
		"hoarder":
			var n: int = run.draw_pile.size()
			if n > 0:
				return {"points": 3 * n}
		"hourglass":
			var d: int = run.discards_left
			if d > 0:
				return {"mult": 5 * d}
		"piggy_bank":
			var m: int = run.coins / 3
			if m > 0:
				return {"mult": m}
		"high_roller":
			var best := 0
			for c in ctx.scoring:
				best = maxi(best, HandEval.card_points(c))
			if best > 0:
				return {"points": 3 * best}
		"snowball":
			if ch.acc > 0:
				return {"mult": ch.acc}
		"minimalist":
			if ctx.played.size() <= 3:
				return {"xmult": 2.0}
		"gambler":
			if run.rng.randi_range(1, 3) == 1:
				return {"xmult": 4.0}
		"last_stand":
			if run.hands_left == 1:
				return {"xmult": 3.0}
		"loaded_die":
			return {"xmult": 1.5}
		"prism":
			var suits := {}
			for c in ctx.scoring:
				suits[c.suit] = true
			if suits.size() == 4:
				return {"xmult": 3.0}
	return {}


## How many extra times the card at this scoring position triggers.
static func retriggers(charms: Array, index: int) -> int:
	if index != 0:
		return 0
	var n := 0
	for ch in charms:
		if ch.id == "echo":
			n += 1
	return n


static func after_play(ch: Dictionary) -> void:
	if ch.id == "snowball":
		ch.acc += 2


static func end_trial_coins(ch: Dictionary) -> int:
	if ch.id == "tax_return":
		return 3
	return 0
