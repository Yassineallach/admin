class_name HandEval
extends RefCounted
## Poker hand detection and the base values of each hand type.

const ORDER := ["high", "pair", "two_pair", "three", "straight", "flush", "full_house", "four", "straight_flush", "five"]

# Points and Mult at level 1; lp/lm are what each extra level adds.
const INFO := {
	"high": {"name": "High Card", "points": 5, "mult": 1, "lp": 10, "lm": 1},
	"pair": {"name": "Pair", "points": 12, "mult": 2, "lp": 15, "lm": 1},
	"two_pair": {"name": "Two Pair", "points": 22, "mult": 2, "lp": 20, "lm": 1},
	"three": {"name": "Three of a Kind", "points": 32, "mult": 3, "lp": 20, "lm": 2},
	"straight": {"name": "Straight", "points": 35, "mult": 4, "lp": 30, "lm": 2},
	"flush": {"name": "Flush", "points": 38, "mult": 4, "lp": 15, "lm": 2},
	"full_house": {"name": "Full House", "points": 45, "mult": 4, "lp": 25, "lm": 2},
	"four": {"name": "Four of a Kind", "points": 65, "mult": 6, "lp": 30, "lm": 3},
	"straight_flush": {"name": "Straight Flush", "points": 110, "mult": 8, "lp": 40, "lm": 4},
	"five": {"name": "Five of a Kind", "points": 130, "mult": 11, "lp": 35, "lm": 3},
}

const RANK_TEXT := {11: "J", 12: "Q", 13: "K", 14: "A"}
const SUIT_NAMES := ["Hearts", "Diamonds", "Clubs", "Spades"]


static func rank_text(rank: int) -> String:
	return RANK_TEXT.get(rank, str(rank))


static func card_name(card: Dictionary) -> String:
	return "%s of %s" % [rank_text(card.rank), SUIT_NAMES[card.suit]]


static func card_points(card: Dictionary) -> int:
	var r: int = card.rank
	if r == 14:
		return 11
	return mini(r, 10)


## Returns {"hand": hand id, "scoring": the cards that score, in played order}.
static func evaluate(cards: Array) -> Dictionary:
	if cards.is_empty():
		return {"hand": "high", "scoring": []}
	var by_rank := {}
	for c in cards:
		if not by_rank.has(c.rank):
			by_rank[c.rank] = []
		by_rank[c.rank].append(c)
	var groups: Array = by_rank.values()
	groups.sort_custom(func(a: Array, b: Array) -> bool:
		if a.size() != b.size():
			return a.size() > b.size()
		return a[0].rank > b[0].rank
	)
	var flush := cards.size() == 5
	for c in cards:
		if c.suit != cards[0].suit:
			flush = false
	var straight := cards.size() == 5 and by_rank.size() == 5 and _is_run(by_rank.keys())
	var top: Array = groups[0]
	var second: Array = groups[1] if groups.size() > 1 else []

	var hand := "high"
	var scoring: Array = [top[0]]
	if straight and flush:
		hand = "straight_flush"
		scoring = cards
	elif top.size() == 5:
		hand = "five"
		scoring = top
	elif top.size() == 4:
		hand = "four"
		scoring = top
	elif top.size() == 3 and second.size() >= 2:
		hand = "full_house"
		scoring = cards
	elif flush:
		hand = "flush"
		scoring = cards
	elif straight:
		hand = "straight"
		scoring = cards
	elif top.size() == 3:
		hand = "three"
		scoring = top
	elif top.size() == 2 and second.size() == 2:
		hand = "two_pair"
		scoring = top + second
	elif top.size() == 2:
		hand = "pair"
		scoring = top

	var ids := {}
	for c in scoring:
		ids[c.id] = true
	var ordered := cards.filter(func(c): return ids.has(c.id))
	return {"hand": hand, "scoring": ordered}


static func _is_run(ranks: Array) -> bool:
	var r := ranks.duplicate()
	r.sort()
	if r == [2, 3, 4, 5, 14]:
		return true
	for i in range(1, r.size()):
		if r[i] != r[0] + i:
			return false
	return true
