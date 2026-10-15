# BindCraft on Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/a-LittleMonk/BindCraft-GoogleColab/blob/main/BindCraft_final.ipynb)

One click, no sign-in: the repo is public, so Colab can read it anonymously.

Colab opens a GitHub notebook **read-only**. Use *File > Save a copy in Drive* to
get a runnable copy — and note that the form values you then enter (target,
contigs, hotspots) are saved in that copy, not here, so the repo stays a clean
template.

A patched copy of the BindCraft Colab notebook that actually runs on current
Colab (Python 3.13, recent JAX). Works against any target; it currently ships
configured for TGF-β1 as a worked example.

## How it differs from upstream BindCraft

Checked cell by cell against
[martinpacesa/BindCraft](https://github.com/martinpacesa/BindCraft)
(`notebooks/BindCraft.ipynb`). **The design logic is upstream's, unmodified.**

| Upstream cell | Here | |
|---|---|---|
| Installation | 1 | byte-identical |
| Mount Drive | 2 | byte-identical |
| Binder design settings | 3 | form values only (target, lengths, hotspots) |
| Advanced settings | 4 | form values only (protocol choice) |
| Filters | 5 | form value only |
| Import functions | 6 | byte-identical |
| Initialise PyRosetta | 7 | byte-identical |
| — | 8 | **added** — JAX/Python 3.13 shims |
| — | 9 | **added** — tuning controls and presets |
| Run BindCraft! | 10 | byte-identical (27 KB, the whole design loop) |
| Consolidate & Rank | 11 | bug fix, post-processing only |
| Top 20 Designs | 12 | byte-identical |
| Top Design Display | 13 | guards an empty folder |
| Display animation | 14 | bug fix, display only |

Cell 1 clones upstream BindCraft and ColabDesign straight from their own
repositories and pulls the official AlphaFold2 2022-12-06 parameters, so the
algorithm code is upstream's at install time — nothing is vendored or forked
here.

The two added cells are the only ones that touch behaviour:

- **Cell 8** shims `jnp.clip` (argument renaming only — it forwards to JAX's own
  clip and self-tests both calling styles) and `clear_mem` (frees memory via
  `jax.clear_caches()`, since the old `jax.lib.xla_bridge` path was removed).
  Neither changes a number in the design maths.
- **Cell 9** on `Production defaults` restores this protocol's own
  `settings_advanced/*.json` values and rewrites the two hardcoded gates back to
  upstream's `final_plddt < 0.7` and `ca_clashes > 0` — verified to reproduce
  upstream's `colabdesign_utils.py` byte for byte. On `Fast debug` it relaxes
  them deliberately, and says so loudly; designs from that preset are not valid.

## Files

| File | What it is |
|---|---|
| `BindCraft_final.ipynb` | The notebook. 14 numbered cells, run in order. |
| `examples/tgfb1.pdb` | **Example target only, not part of the setup.** Chains A and B of 3KFD, 112 residues each, no waters or ligands. The notebook is set to use chain A. |

## How to use it

1. Put your target PDB on Google Drive and upload the notebook to Colab.
2. In cell 3, point the settings at your target:
   - `starting_pdb` — the path on Drive, e.g. `/content/drive/MyDrive/mytarget.pdb`
   - `chains` — which chain(s) to design against
   - `target_hotspot_residues` — the interface residues to aim at, e.g. `A31,A34`,
     or leave blank to let BindCraft choose
   - `binder_name` and `design_path` — the name and output folder for this campaign
3. Set the Colab runtime to a GPU.
4. Run cells **1 through 14 in order**. Cells 8 and 9 must come after cell 6;
   they raise an error telling you so if they don't.

The target must be a clean PDB: no waters, no ligands, no alternate
conformations. The example file shows the expected shape.

### The example

To reproduce the TGF-β1 run instead, upload `examples/tgfb1.pdb` to the root of
your Drive. Cell 3 already points at `/content/drive/MyDrive/tgfb1.pdb` with
chain A and hotspots `A31,A34,A91,A94`.

**Close the Colab tab before editing the notebook from anywhere else.** An open
tab writes its stale in-memory copy back to Drive, which makes Drive fork the
file into `... (1).ipynb`. That wasted a fair amount of time once already.

## Check these two settings before a real run

The notebook ships with the values from a debugging session:

- cell 3: `lengths = "25,30"` → widen to something like `"25,40"`
- cell 5: `filter_option = "None"` → set to `"Peptide"`

`lengths` matters more than it looks. Binders shorter than roughly 20 residues
cannot fold into anything confident enough to pass the trajectory quality gate —
11- and 12-residue attempts scored 0.34–0.44 where the gate is 0.70, while 28–29
residues scored 0.74–0.76. Set the range too low and BindCraft rejects
everything and loops without ever accepting a design.

Also give each campaign its own `design_path`, and clear the folder before
starting fresh. BindCraft resumes from whatever CSV files it finds there, so
leftover designs from an earlier run get ranked alongside new ones.

## What was changed from upstream

**Cell 8 — Compatibility patches (required).** Two of the APIs ColabDesign calls
were removed from JAX, and without these shims the pipeline cannot run at all:

- `jnp.clip` was called with argument names that no longer exist. The shim is
  written to be safe to run twice; a naive version patches itself on the second
  run and blows the recursion limit.
- `clear_mem` reaches for a module that was deleted. The shim replaces it both
  inside the BindCraft package and at notebook scope, because cell 6's wildcard
  import makes a second copy of the name that is easy to miss.

**Cell 9 — Tuning controls.** A `preset` dropdown with three choices:

- *Production defaults* — stock BindCraft values. This is the reset.
- *Fast debug* — cuts iterations roughly tenfold and drops the quality gate to
  0.1 so every trajectory reaches the downstream code. Useful for checking the
  pipeline end to end in a few minutes. **Designs from this mode are
  meaningless.**
- *Custom* — uses whatever the fields below are set to.

The cell also exposes the trajectory pLDDT threshold and the CA-clash limit,
which upstream hardcodes in `functions/colabdesign_utils.py`. It edits that file
from a pristine backup each time, so repeated runs never compound.

**Cell 11 — Consolidate & Rank.** Upstream assigned each filename stem to
`target_settings["binder_name"]`, the very key the loop then compares against.
That silently breaks every rank past the first, and raises `ValueError` on any
filename without `_model` in it.

**Cells 13 and 14 — display.** Both crashed when nothing had been ranked yet.
Cell 14 also handed a file path to `HTML()` instead of the file's contents, so
the animation never rendered.

## Why a bad path used to cost 30 minutes

BindCraft re-reads `starting_pdb` at the *end* of each trajectory to compute the
target RMSD. A wrong path therefore raises nothing until the full trajectory has
run. If a long run dies with `Cannot open file`, check `starting_pdb` first —
Colab wipes `/content` on every restart, so anything not on Drive disappears.

## Timings

A full debug run (fast-debug preset, one accepted design) finished in about
6m40s on a T4. A real campaign takes hours and Colab will disconnect partway.
`design_path` points at Drive and BindCraft resumes from the CSVs it finds, so
re-running the run cell continues rather than starting over.
