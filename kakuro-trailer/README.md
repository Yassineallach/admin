# Kakuro — promotional trailer

`kakuro_trailer.mp4`: 37 s, 1080×1920 (9:16), 30 fps, H.264 + AAC stereo.

Real gameplay, recorded from the game itself in Godot 4.7.2 (Movie Maker mode),
cut to the game's own menu music ("Sunny Grid", 110 BPM, 16 bars) with the
game's recorded sound effects (marimba digits, Kaku's voice, win jingle).
Added in the edit: four short captions, touch markers where the scripted
touches landed, and the end-card tagline and store badge.

## Re-recording

1. Copy the game project, add `src/director.gd` and `src/director.tscn` to its
   root, set `kakuro/online/required=false` and the window override to
   1080×1920 in the copy's `project.godot` (the director never ships).
2. Record:

       xvfb-run -a -s "-screen 0 1200x2000x24" godot --path <copy> \
         --rendering-driver opengl3 --fixed-fps 30 \
         --write-movie /abs/path/cap/take1/f.png res://director.tscn > cap/take1.log

3. Edit (Python 3 + skia-python, numpy, imageio-ffmpeg; paths at the top of
   `edit.py`):

       python3 edit.py audio trailer_audio.wav
       python3 edit.py video kakuro_trailer.mp4 trailer_audio.wav

The Google Play badge on the end card is a placeholder: replace it with the
official badge from Google's badge generator once the listing is live.
