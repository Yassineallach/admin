"""Writes notebooks/<Site>_<Model>.ipynb: copies of the two server notebooks with MODEL preset,
so the app can open one with a single tap. Run after changing either notebook:

    python make_notebooks.py
"""

import json
import os
import re

MODELS = ["VoxCPM2", "IndexTTS-2.5", "OmniVoice", "Chatterbox", "Chatterbox-Turbo"]
SITES = {"Colab": "VoxCPM_Server_Colab.ipynb", "Kaggle": "VoxCPM_Server_Kaggle.ipynb"}

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, "notebooks")
os.makedirs(out_dir, exist_ok=True)

for site, source in SITES.items():
    with open(os.path.join(here, source)) as f:
        base = json.load(f)
    for model in MODELS:
        nb = json.loads(json.dumps(base))
        cell = "".join(nb["cells"][1]["source"])
        cell, n = re.subn(r'^MODEL = "[^"]*"', f'MODEL = "{model}"', cell, count=1, flags=re.M)
        assert n == 1, "MODEL line not found in " + source
        nb["cells"][1]["source"] = cell
        intro = "".join(nb["cells"][0]["source"]).split("\n", 1)[1].lstrip("\n")
        # The model is already chosen in these copies.
        intro = re.sub(r"Pick the \*\*MODEL\*\* in the first cell(?: \([^)]*\))?, then ", "Then ", intro)
        nb["cells"][0]["source"] = (
            f"# {model} server for the VoxCPM Studio app\n\n"
            f"This copy already has **MODEL = {model}** set in the first cell.\n\n" + intro
        )
        with open(os.path.join(out_dir, f"{site}_{model}.ipynb"), "w") as f:
            json.dump(nb, f, indent=1)
print("wrote", len(SITES) * len(MODELS), "notebooks to", out_dir)
