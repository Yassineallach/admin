class_name Challenges
extends RefCounted
## Preset runs with changed rules. Each entry's `rules` are read by Run.rule().
##
## Supported rules:
##   deck_enh: String       every starting card gets this enhancement
##   ranks_min: int         the starting deck only has ranks from this up to Ace
##   glass_odds: int        Glass shatters 1 in N times (default 4)
##   hands, discards: int   per trial, before warden effects
##   no_interest, no_hand_money: bool
##   price_mult: float      multiplies shop prices and the reroll cost
##   no_shop_charms: bool   the shop never offers charms
##   start_charms: Array    charms you start with
##   locked_charms: Array   charms you start with that cannot be sold
##   floor_mute: bool       each floor mutes one suit, in order Hearts, Diamonds, Clubs, Spades

const LIST := [
	{
		"id": "glass_cannon",
		"name": "Glass Cannon",
		"desc": "Every card starts as Glass, and Glass shatters 1 in 2 times. Win before your deck runs out.",
		"rules": {"deck_enh": "glass", "glass_odds": 2},
	},
	{
		"id": "pauper",
		"name": "Pauper",
		"desc": "No interest and no coins for unused hands, but every shop price is halved.",
		"rules": {"no_interest": true, "no_hand_money": true, "price_mult": 0.5},
	},
	{
		"id": "one_shot",
		"name": "One Shot",
		"desc": "One hand per trial, plus 6 discards to find it.",
		"rules": {"hands": 1, "discards": 6},
	},
	{
		"id": "royal_blood",
		"name": "Royal Blood",
		"desc": "Your deck has only 10s through Aces. Royal Court is fixed in your first slot.",
		"rules": {"ranks_min": 10, "locked_charms": ["royal_court"]},
	},
	{
		"id": "silent_suits",
		"name": "Silent Suits",
		"desc": "Each floor mutes a suit for every trial on it: Hearts, then Diamonds, Clubs and Spades.",
		"rules": {"floor_mute": true},
	},
	{
		"id": "snowblind",
		"name": "Snowblind",
		"desc": "Start with Snowball. The shop never sells charms.",
		"rules": {"start_charms": ["snowball"], "no_shop_charms": true},
	},
]


static func find(id: String) -> Dictionary:
	for c in LIST:
		if c.id == id:
			return c
	return {}
