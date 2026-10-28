"""Deploy the VoxCPM2 server on Modal (https://modal.com): a permanent URL, GPU billed per second
only while generating, scales to zero when idle. Modal's free plan includes monthly credits.

    pip install modal
    modal setup                      # log in once
    modal deploy modal_app.py        # prints https://<you>--voxcpm-server-serve.modal.run

Put that URL in the app's Settings. Optional API key:
    modal secret create voxcpm-key VOXCPM_API_KEY=<your-key>
and uncomment the `secrets=` line below.
"""

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("voxcpm", "fastapi", "python-multipart", "soundfile", "librosa")
    .env({"HF_HOME": "/cache/huggingface"})
    .add_local_file("server.py", "/root/server.py")
)

# Keeps the downloaded model between cold starts so it isn't fetched every time.
cache = modal.Volume.from_name("voxcpm-cache", create_if_missing=True)

app = modal.App("voxcpm-server")


@app.function(
    image=image,
    gpu="T4",
    volumes={"/cache": cache},
    scaledown_window=300,  # stay warm 5 minutes after the last request
    timeout=1800,
    # secrets=[modal.Secret.from_name("voxcpm-key")],
)
@modal.asgi_app()
def serve():
    import sys

    sys.path.insert(0, "/root")
    import server

    server.get_model()  # load during cold start, before the first request is handled
    cache.commit()
    return server.app
