#!/bin/bash
# Copy new hunt hits into the repo (dedupe by grid+shading) and commit.
Z=/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/scratch-zombo
R=/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang
cd $R || exit 1
Z=$Z R=$R python3 - <<'PY'
import json, glob, os, subprocess
Z=os.environ["Z"]; R=os.environ["R"]; F=R+"/docs/research/zombo-brainanas/found"
def sig(f):
    d=json.load(open(f)); return json.dumps([d["grid"], d["infected"]])
have={sig(f) for f in glob.glob(F+"/*.json")}
new=0
for f in sorted(glob.glob(Z+"/hunt/*/full_*.json")):
    if sig(f) in have: continue
    arm=f.split("/")[-2]; seed=f.split("full_")[1][:-5]; dst=f"{F}/{arm}_{seed}.json"
    os.system(f"cp {f} {dst}"); subprocess.run(["uv","run","--with","pillow","python",R+"/docs/research/zombo_brainanas_render.py",dst,dst[:-5]+".png"],check=False)
    have.add(sig(f)); new+=1
for p in glob.glob(Z+"/hunt/*/PROGRESS.md"):
    os.system(f"cp {p} {F}/PROGRESS_{p.split('/')[-2]}.md")
print(new,"new")
PY
git add docs/research/zombo-brainanas/found
git diff --cached --quiet && exit 0
git commit -qm "zombo-brainanas: sync found grids $(date +%H:%M)" && echo committed
git push -q origin HEAD 2>/dev/null && echo pushed || echo "push failed (kept local commit)"
