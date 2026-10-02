# Kakuro trailer

`kakuro_trailer.mp4`: a 32 s promo, 1920x1080, 60 fps, H.264 High + AAC stereo, faststart, about -14 LUFS.

This is a frame-by-frame recreation of the game, not captured gameplay. Godot 4.7 could not be installed in
the build environment. Each frame is drawn with skia-python using the Godot project's own constants
(palette.gd LIGHT theme, board_view.gd, combo_panel.gd, number_pad.gd, icon_button.gd, icons.gd,
title_logo.gd, mascot.gd + kaku_shape.gd, win_stars.gd, game_screen.gd layout), its Nunito fonts, Kaku's art
layers, the app icon, the real puzzle bank (Easy/Medium/Hard/Expert level 1, Easy level 6), and its own music
(`menu_loop.ogg`, 110 bpm) and SFX. Hint text follows `core/logic.gd` `explain()`.

Re-render: `./build.sh` (python3 + skia-python, numpy, soundfile; ffmpeg).

| Time | Shot | Camera | Text | Sound |
|---|---|---|---|---|
| 0.00-4.36 | Hook: close-up, five digits complete three runs (green sweeps) | slow pull-out 1.95x to 1.72x | none | marimba notes only (digits are notes), run sparkle |
| 4.36-8.73 | Title screen: KAKURO tiles drop, Kaku hops, PLAY pops and is pressed | push-in 1.0x to 1.08x | Cross sums. Pure logic. | music in on the cut; tile notes 3-1-4-9-7-2 |
| 8.73-13.09 | Level 1: board intro, combo helper (16 in 2 / 17 in 2, unique), 9 then 7 | push to the helper and board | Every clue is a sum / No digit repeats in a run | taps, notes |
| 13.09-17.45 | Solving on the beat, sums sweep, Kaku hops, progress fills | slow push | Every digit plays a note | a note per digit, run sparkles |
| 17.45-19.64 | Medium 8x8: explained hint card, revealed digit | hold on the top half | Hints that explain why | hint twinkle, note |
| 19.64-21.82 | Cuts on each beat: Easy 6x6, Medium 8x8, Hard 10x10, Expert 12x12 | cut per beat | Easy to Expert + grid size | one note per cut |
| 21.82-26.18 | Beat of silence, last digit, win wave, Solved! card with 3 stars | pull back to the card | One solution. No guessing. | silence, note, win jingle, star dings, music back |
| 26.18-32.29 | End card: icon, KAKURO tiles, tagline, modes, store badge placeholder | static | CROSS SUMS · PURE LOGIC | tile notes, final ding, music stops |

Placeholder: the "STORE BADGE" outline in `trailer.py` (`end_card`) must be replaced with the official Google Play badge.
