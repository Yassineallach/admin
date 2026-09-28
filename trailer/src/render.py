import sys
import subprocess
import skia
import imageio_ffmpeg
from prim import *
import scenes as A
import scenes2 as B

END = bar(17)          # 41.74 s of picture
TAIL = 1.3             # held end card while the last chime rings out
DURATION = END + TAIL


def draw(c, t, state):
    if t < bar(4):
        A.london_intro(c, t)
    elif t < bar(5):
        A.shot04(c, t)
    elif t < bar(6):
        A.shot05(c, t)
    elif t < bar(7):
        A.shot06(c, t)
    elif t < bar(8):
        A.shot07(c, t)
    elif t < bar(9):
        A.shot08(c, t)
    elif t < bar(10):
        A.shot09(c, t)
    elif t < bar(11):
        A.shot10(c, t)
    elif t < bar(12):
        A.shot11(c, t)
    elif t < bar(13):
        B.shot12(c, t)
    elif t < bar(14):
        B.shot13(c, t)
    elif t < bar(15):
        B.shot14(c, t)
    else:
        B.shot15_16(c, min(t, END), state.get('last14'))


def make_surface():
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def still(t, path):
    surf = make_surface()
    draw(surf.getCanvas(), t, {})
    surf.makeImageSnapshot().save(path)


def render(out_path, fps=30, audio=None):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (W, H),
           '-r', str(fps), '-i', '-']
    if audio:
        cmd += ['-i', audio, '-c:a', 'aac', '-b:a', '256k', '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
            '-profile:v', 'high', '-movflags', '+faststart', out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = make_surface()
    state = {}
    n = int(round(DURATION * fps))
    t15 = bar(15)
    for i in range(n):
        t = i / fps
        c = surf.getCanvas()
        c.clear(skia.ColorWHITE)
        draw(c, t, state)
        img = surf.makeImageSnapshot()
        if t < t15 <= t + 1.0 / fps:
            state['last14'] = img
        proc.stdin.write(img.tobytes())
        if i % 60 == 0:
            print('frame %d/%d' % (i, n), flush=True)
    proc.stdin.close()
    proc.wait()


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for a in sys.argv[3:]:
            t = float(a)
            still(t, '%s/f_%05.2f.png' % (sys.argv[2], t))
    else:
        render(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30, sys.argv[4] if len(sys.argv) > 4 else None)
