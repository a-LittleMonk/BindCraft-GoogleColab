# BindCraft on Colab — TGF-β1 peptide binders

A patched copy of the BindCraft Colab notebook that actually runs on current
Colab (Python 3.13, recent JAX), set up to design peptide binders against
TGF-β1 (PDB 3KFD).

## Files

| File | What it is |
|---|---|
| `BindCraft_final.ipynb` | The notebook. 14 numbered cells, run in order. |
| `tgfb1.pdb` | The target. Chains A and B of 3KFD, 112 residues each, no waters or ligands. The notebook uses chain A only. |

## How to use it

1. Upload both files to Google Drive. The notebook expects the target at
   `/content/drive/MyDrive/tgfb1.pdb` — if you put it elsewhere, change
   `starting_pdb` in cell 3.
2. Open `BindCraft_final.ipynb` in Colab and set the runtime to a GPU.
3. Run cells **1 through 14 in order**. Cells 8 and 9 must come after cell 6;
   they raise an error telling you so if they don't.

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

Also clear out `/content/drive/MyDrive/BindCraft/TGFb1/` before starting fresh.
BindCraft resumes from whatever CSV files it finds there, so leftover designs
from an earlier run get ranked alongside new ones.

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
