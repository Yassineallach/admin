class_name Scoring
extends RefCounted
## Turns a played hand into an ordered list of scoring steps.
## Order: hand base -> each scored card, left to right -> cards held in hand -> charms, left to right.
## Score = Points x Mult.

const ENHANCEMENTS := {
	"bonus": {"name": "Bonus", "desc": "+25 Points when scored", "effect": {"points": 25}},
	"spark": {"name": "Spark", "desc": "+3 Mult when scored", "effect": {"mult": 3}},
	"glass": {"name": "Glass", "desc": "x2 Mult when scored, 1 in 4 chance to shatter", "effect": {"xmult": 2.0}},
	"iron": {"name": "Iron", "desc": "x1.5 Mult while held in hand", "effect": {}},
}


## Returns [points, mult] for a hand type at its current level.
static func base_for(run, hand_id: String) -> Array:
	var info: Dictionary = HandEval.INFO[hand_id]
	var lvl: int = run.hand_levels.get(hand_id, 1)
	var p := float(info.points + info.lp * (lvl - 1))
	var m := float(info.mult + info.lm * (lvl - 1))
	if run.current_warden() == "halver":
		p = ceilf(p / 2.0)
		m = maxf(1.0, ceilf(m / 2.0))
	return [p, m]


static func score_play(run, played: Array, held: Array) -> Dictionary:
	var ev := HandEval.evaluate(played)
	var hand_id: String = ev.hand
	var scoring: Array = ev.scoring
	var base := base_for(run, hand_id)
	var acc := {"points": base[0], "mult": base[1]}
	var steps: Array = [_step("base", null, "", acc)]
	var ctx := {"run": run, "played": played, "held": held, "hand": hand_id, "scoring": scoring}

	for i in scoring.size():
		var card: Dictionary = scoring[i]
		if run.is_muted(card):
			steps.append(_step("card", card, "Muted", acc))
			continue
		for t in 1 + Charms.retriggers(run.charms, i):
			var pts := HandEval.card_points(card)
			acc.points += pts
			steps.append(_step("card", card, "+%d" % pts, acc))
			if ENHANCEMENTS.has(card.enh) and not ENHANCEMENTS[card.enh].effect.is_empty():
				steps.append(_step("card", card, _apply(ENHANCEMENTS[card.enh].effect, acc), acc))
			for ci in run.charms.size():
				var eff := Charms.on_card(run.charms[ci], card, ctx)
				if not eff.is_empty():
					steps.append(_step("charm", ci, _apply(eff, acc), acc))

	for card in held:
		if card.enh == "iron" and not run.is_muted(card):
			steps.append(_step("held", card, _apply({"xmult": 1.5}, acc), acc))

	for ci in run.charms.size():
		var eff := Charms.on_hand(run.charms[ci], ctx)
		if not eff.is_empty():
			steps.append(_step("charm", ci, _apply(eff, acc), acc))

	return {
		"hand": hand_id,
		"scoring": scoring,
		"steps": steps,
		"points": acc.points,
		"mult": acc.mult,
		"total": acc.points * acc.mult,
	}


static func _step(kind: String, ref, text: String, acc: Dictionary) -> Dictionary:
	return {"kind": kind, "ref": ref, "text": text, "points": acc.points, "mult": acc.mult}


static func _apply(eff: Dictionary, acc: Dictionary) -> String:
	var parts := PackedStringArray()
	if eff.has("points"):
		acc.points += eff.points
		parts.append("+%d" % int(eff.points))
	if eff.has("mult"):
		acc.mult += eff.mult
		parts.append("+%s Mult" % fmt_num(eff.mult))
	if eff.has("xmult"):
		acc.mult *= eff.xmult
		parts.append("x%s Mult" % fmt_num(eff.xmult))
	return " ".join(parts)


static func fmt_num(x: float) -> String:
	if is_equal_approx(x, roundf(x)):
		return str(int(roundf(x)))
	return "%.1f" % x
