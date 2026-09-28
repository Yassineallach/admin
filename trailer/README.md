# Transit — promotional trailer

`transit_trailer.mp4`: 43 s, 1920×1080, 60 fps, H.264 + AAC stereo.

A motion-graphics trailer drawn in code in the game's own visual language
(palette, station shapes, line widths, trains, dock, clock and logo taken from
`scripts/config.gd`, `shapes.gd`, `cities.gd`, `main.gd` and `icon.svg`, set in
Jost). It follows the 16-shot storyboard, cut on a 92 BPM grid. The score is
synthesised in the manner of `scripts/audio.gd`: every sound is an on-screen
event in A minor pentatonic over a soft pad.

It is a recreation, not footage captured from the Godot build.

## Re-rendering

Needs Python 3 with `skia-python`, `numpy`, `imageio-ffmpeg`, and the game
project unzipped at `../game` next to `src/` (for `fonts/Jost.ttf`).

    cd src
    python3 audio.py score.wav
    python3 render.py video ../transit_trailer.mp4 60 score.wav
    python3 render.py still <dir> 1.0 12.5 30.0   # check individual frames
