#!/usr/bin/env bash
# Re-renders kakuro_trailer.mp4 (1920x1080, 60 fps, H.264 High + AAC stereo, faststart).
# Needs: python3 with skia-python, numpy, soundfile; ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build

python3 trailer.py events > build/sfx.json
python3 mix.py build/sfx.json build/mix.wav
# Normalize to about -14 LUFS integrated; a limiter keeps true peak under -1 dBFS.
ffmpeg -hide_banner -loglevel error -y -i build/mix.wav \
  -af "volume=2.1dB,alimiter=limit=0.79:attack=2:release=60:level=disabled" \
  -ar 48000 -c:a pcm_f32le build/mix_norm.wav

python3 trailer.py frames | ffmpeg -hide_banner -loglevel error -y \
  -f rawvideo -pix_fmt rgba -s 1920x1080 -r 60 -i - \
  -i build/mix_norm.wav \
  -map 0:v -map 1:a \
  -c:v libx264 -profile:v high -preset slow -crf 16 -pix_fmt yuv420p -r 60 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 256k -ac 2 -ar 48000 \
  -movflags +faststart -shortest \
  kakuro_trailer.mp4

python3 loudness_report.py kakuro_trailer.mp4
