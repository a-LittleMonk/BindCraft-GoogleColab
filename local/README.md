# Running BindCraft locally (or on a rented GPU)

The notebook in the repo root is for Colab. This folder runs the same pipeline
over SSH on any Linux box with an NVIDIA GPU — your own machine or a rented one.
It drives upstream BindCraft's command line directly, so none of the Colab
compatibility shims are needed: the installer pins Python 3.10 and the JAX
version upstream actually wants.

| File | What it does |
|---|---|
| `install.sh` | Installs conda, upstream BindCraft, its env, and the AF2 weights. Idempotent. |
| `run.sh` | Launches a campaign in `tmux` so it survives your SSH session dropping. |
| `fetch_results.sh` | Run on **your** machine to rsync results back down. |
| `BindCraft_local.ipynb` | Optional form-field notebook, mirroring the Colab cells. |
| `panel.py` | The code behind those forms, so the cells stay two lines. |
| `settings/tgfb1.json` | Target settings for the TGF-β1 example. Copy it for a new target. |

## Quick start

```bash
# on the GPU box
git clone https://github.com/a-LittleMonk/BindCraft-GoogleColab
cd BindCraft-GoogleColab/local
bash install.sh            # 15-40 min, mostly the 5 GB of AF2 weights
bash run.sh --smoke        # ~10 min, proves the pipeline works end to end
bash run.sh                # the real campaign
```

```bash
# later, from your own machine
bash fetch_results.sh root@ssh5.vast.ai:12345 ./results
```

`--smoke` cuts the iteration counts, drops the trajectory quality gate to 0.1
and turns the filters off, so one design gets through fast. **Designs from a
smoke run are meaningless** — it only tells you the install is good. `run.sh`
restores the stock gate from a pristine backup on every launch, so the patch
never compounds.

## The notebook

`BindCraft_local.ipynb` mirrors the Colab notebook's cells, with the same form
fields, the same dropdown wording and the same numbering, for the instance's
Jupyter. Open it and **set the kernel to "Python (BindCraft)"** — Jupyter on
these images runs in its own Python, which has no pandas and no BindCraft.
`install.sh` registers that kernel; cell 1 tells you if you're in the wrong one.

| Colab | Here |
|---|---|
| 1 Installation, 2 Mount Drive | `install.sh`, once. Cell 1 only verifies. |
| 3 Binder design settings | 2, same fields |
| 4 Advanced settings | 3, same four protocol dropdowns |
| 5 Filters | 4, same five options |
| 6 Import, 7 PyRosetta, 8 Compat patches | gone — nothing to shim locally |
| 9 Tuning controls | 5, same fields including both gates |
| 10 Run BindCraft | 6, but launches `tmux` instead of running in-kernel |
| 11 Consolidate & rank | done by `bindcraft.py` itself |
| 12 Top 20, 13 Top design, 14 Animation | 8, 9, 10 |
| 15 Diagnose rejected trajectories | 11 |

The run goes to `run.sh`, so **closing the browser does not stop it** — the one
thing the Colab notebook cannot do. Cell 6 also has a Stop button. The notebook
and `run.sh` read and write the same files in `settings/`, so there is one source
of truth either way.

Each cell is two lines, because the code lives in `panel.py`. Colab keeps a
form's values in the cell source; here they live in `panel.py`'s widget cache,
which means **re-running a cell keeps what you typed** instead of reloading it
from disk. Values reach disk when you press Save settings, or when cell 6 saves
them for you before launching.

A `git pull` on the box will complain that the notebook has local changes —
Jupyter rewrites it with execution counts the moment you open it. Discard that
copy with `git checkout -- local/BindCraft_local.ipynb` and pull again.

## Your own target

Copy `settings/tgfb1.json` and edit it:

- `starting_pdb` — path to the target. Must be clean: no waters, no ligands, no
  alternate conformations. `{{REPO}}` and `{{BC_ROOT}}` are substituted at launch.
- `chains` — which chain(s) to design against.
- `target_hotspot_residues` — interface residues, e.g. `A31,A34`. Blank lets
  BindCraft choose.
- `lengths` — **don't set this below ~20.** Shorter binders can't fold into
  anything that passes the quality gate, so BindCraft rejects everything and
  loops forever. 25–40 is a sensible peptide range.
- `design_path` — give every campaign its own folder. BindCraft resumes from the
  CSVs it finds there, so leftovers from an old run get ranked alongside new ones.

Then `bash run.sh -s settings/yourtarget.json`.

## When everything is rejected

Upstream hardcodes three gates that a trajectory has to clear, and the log tells
you which one stopped it:

| Log line | Gate | Flag |
|---|---|---|
| `Trajectory starting confidence low` | final pLDDT below 0.70 | `--plddt 0.5` |
| `Severe clashes detected` | any CA clash at all | `--clashes 10` |
| `... pLDDT too low to continue` | per-stage check, 0.65 | `--plddt 0.5` |

`--plddt` moves the first and third together, since they measure the same thing.
`run.sh` restores the stock values from a pristine backup on every launch, so the
patches never compound.

Loosening a gate does not make a design good — it just lets a doomed trajectory
spend time in MPNN optimisation. Use these to prove the pipeline works, or when
a target genuinely cannot reach 0.70, not to rescue a campaign.

Defaults are the peptide presets (`peptide_filters.json`,
`peptide_3stage_multimer_mpnn.json`). Override with `-f` and `-a` for other
binder types; upstream ships a set in `settings_filters/` and
`settings_advanced/`.

## Hardware

16 GB of VRAM is enough. Ampere or Ada works out of the box — 3090, 4090, A5000,
L40S, A100. Avoid the newest Blackwell cards, which may not have wheels for the
JAX version this pins. Budget 60 GB of disk.

## Notes for vast.ai

Every instance gives you both SSH and Jupyter. Use SSH for runs, Jupyter only to
look at results.

When picking an offer: CUDA ≥ 12.4, 60 GB disk, high download speed (you pull
5 GB of weights on every fresh rental), reliability above 99%, and at least one
direct port so `rsync` isn't stuck on the slow SSH proxy. Start on-demand rather
than interruptible.

**Destroying an instance deletes everything on it, and stopping one does not
stop the storage charge.** Volumes survive destruction but are pinned to a
single physical machine, so they only help if you re-rent that same host. The
reliable pattern is the one here: treat the box as disposable, rebuild it with
`install.sh`, and always `fetch_results.sh` before destroying.

You can paste this as the instance's on-start script to have it self-install:

```bash
cd /workspace && git clone https://github.com/a-LittleMonk/BindCraft-GoogleColab \
  && bash BindCraft-GoogleColab/local/install.sh
```
