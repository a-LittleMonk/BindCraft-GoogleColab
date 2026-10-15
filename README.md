# BindCraft on Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/a-LittleMonk/BindCraft-GoogleColab/blob/main/BindCraft_colab.ipynb)

A patched copy of the BindCraft Colab notebook that actually runs on current
Colab (Python 3.13, recent JAX). Works against any target; it ships configured
for TGF-β1 as a worked example.

Built on [BindCraft](https://github.com/martinpacesa/BindCraft) by Martin
Pacesa — this repo is a personal wrapper around that work, not a replacement
for it. See [Credit](#credit).

**This repo is the only current version.** Check
[the releases page](https://github.com/a-LittleMonk/BindCraft-GoogleColab/releases)
for the newest number; the notebook prints its own version in the first cell, so
any copy can be checked against that page at a glance.

Colab opens a GitHub notebook **read-only**. Use *File > Save a copy in Drive*
to get a runnable one. That copy is a snapshot — it keeps the form values you
type into it, and it never picks up later fixes. Come back here for those.

## How to use it

1. Put your target PDB on Google Drive.
2. Open the notebook from the badge above, then *File > Save a copy in Drive*.
3. Set the Colab runtime to a GPU.
4. In cell 3, point the settings at your target:
   - `starting_pdb` — the path on Drive, e.g. `/content/drive/MyDrive/mytarget.pdb`
   - `chains` — which chain(s) to design against
   - `target_hotspot_residues` — the interface residues to aim at, e.g. `A31,A34`,
     or leave blank to let BindCraft choose
   - `binder_name` and `design_path` — the name and output folder for this campaign
5. Run cells **1 through 14 in order**. Cells 8 and 9 must come after cell 6;
   they raise an error telling you so if they don't.

The target must be a clean PDB: no waters, no ligands, no alternate
conformations. `examples/tgfb1.pdb` shows the expected shape.

Give each campaign its own `design_path`, and clear the folder before starting
fresh. BindCraft resumes from whatever CSV files it finds there, so leftover
designs from an earlier run get ranked alongside new ones.

**Close the Colab tab before editing the notebook from anywhere else.** An open
tab writes its stale in-memory copy back to Drive, which makes Drive fork the
file into `... (1).ipynb`. That wasted a fair amount of time once already.

### Check these two settings before a real run

The notebook ships with the values from a debugging session:

- cell 3: `lengths = "25,30"` → widen to something like `"25,40"`
- cell 5: `filter_option = "None"` → set to `"Peptide"`

`lengths` matters more than it looks. Binders shorter than roughly 20 residues
cannot fold into anything confident enough to pass the trajectory quality gate —
11- and 12-residue attempts scored 0.34–0.44 where the gate is 0.70, while 28–29
residues scored 0.74–0.76. Set the range too low and BindCraft rejects
everything and loops without ever accepting a design.

### The worked example

To reproduce the TGF-β1 run, upload `examples/tgfb1.pdb` to the root of your
Drive. Cell 3 already points at `/content/drive/MyDrive/tgfb1.pdb` with chain A
and hotspots `A31,A34,A91,A94`.

## Designing peptide binders

Per the [upstream wiki](https://github.com/martinpacesa/BindCraft/wiki/De-novo-binder-design-with-BindCraft),
BindCraft supports peptides of **8-25 residues**. It will run down to 4, but
peptides that short "almost never" pass the filters. Two things follow:

- **Expect roughly 5-10x lower in-silico success** than normal binder design.
  That is the single biggest practical constraint: at ~13 min a trajectory on a
  T4, a realistic peptide campaign is tens of hours, not one session. Zero
  accepted designs after a handful of trajectories is the expected outcome, not
  evidence of a broken setup.
- **Use the peptide settings on both sides**: `design_protocol = "Peptide"` in
  cell 4 *and* `filter_option = "Peptide"` in cell 5. `None` disables filtering
  entirely, which is for benchmarking — it does not make designs easier to get,
  since the trajectory gates in cell 10 run before any filter.

The wiki suggests sampling a **wide length range first**, then narrowing once you
see what works for the target, rather than committing to one narrow band.

On hotspots, it advises a radial patch of surface residues and notes that good
patches contain an aromatic (F/Y/W) along with I/L/M. A patch made only of
charged and polar residues gives a short peptide very little to grip.

Below about 8 residues BindCraft also omits cysteine (`omit_AAs: "C"`), so
disulfide-stapled macrocycles are out of scope here — RFpeptides is the tool for
those.

## Troubleshooting

### "Target number N of designs reached!" and it exits instantly

Not a failure. Before sampling anything, the design loop counts the `.pdb` files
in `Accepted/`; once that count has reached `number_of_final_designs` it reranks
and stops. The number in the message is **the count it found, not your target**,
which is what makes it read as if the target had been that number all along.

One trajectory can produce more than one accepted design — `max_mpnn_sequences`
is 2 — so a target of 1 is typically overshot to 2 on the first success.

To design more, raise `number_of_final_designs` in cell 3, then re-run **in this
order**:

| | |
|---|---|
| cell 3 | writes the settings JSON |
| cell 6 | reloads it — the run loop reads `target_settings` from memory, so this is what actually applies the new number |
| cells 8, 9 | cell 6 re-imports the broken `clear_mem`, so the shims must go back on |
| cell 10 | run |

**Re-running cell 10 on its own keeps the old target and exits again.** Cell 15
reports the count, the target, and whether the next run will do any work.

### Every trajectory is rejected

`Severe clashes detected, skipping analysis and MPNN optimisation` comes from
upstream's gate: it counts any two CA atoms closer than 2.5 Å in the predicted
complex, excluding same-residue and directly sequential pairs. Because it looks
at CA only, it does **not** skip same-chain pairs — a binder whose own backbone
has collapsed trips it exactly like a binder driven into the target.

That gate, and the `pLDDT < 0.7` one after it, are hardcoded in
`functions/colabdesign_utils.py` and run **before** your Filters setting, so
`filter_option = "None"` does not let these trajectories through.

**Cell 15** tells you which of the three it is — clashes inside the target (no
binder can ever pass; clean the PDB), inside the binder (usually too short), or
between binder and target (usually the hotspots) — and reports the mean binder
pLDDT against that 0.7 gate.

### The same sequences come back every run

That means no new design work happened. There is no global seed anywhere — each
trajectory draws its own `seed` and samples its own length — so genuinely new
trajectories cannot repeat. Cell 12 reads the cumulative
`final_design_stats.csv`, so it happily reprints old results. Check the
`_s<number>` in the design names and the "Sampled Trajectories" counter.

### A bad path costs 30 minutes

BindCraft re-reads `starting_pdb` at the *end* of each trajectory to compute the
target RMSD. A wrong path therefore raises nothing until the full trajectory has
run. If a long run dies with `Cannot open file`, check `starting_pdb` first —
Colab wipes `/content` on every restart, so anything not on Drive disappears.

### Timings

A full debug run (fast-debug preset, one accepted design) finished in about
6m40s on a T4. A real campaign takes hours and Colab will disconnect partway.
`design_path` points at Drive and BindCraft resumes from the CSVs it finds, so
re-running the run cell continues rather than starting over.

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
| — | 8 | **added** — JAX / Python 3.13 shims |
| — | 9 | **added** — tuning controls and presets |
| Run BindCraft! | 10 | byte-identical (27 KB, the whole design loop) |
| Consolidate & Rank | 11 | bug fix, post-processing only |
| Top 20 Designs | 12 | byte-identical |
| Top Design Display | 13 | guards an empty folder |
| Display animation | 14 | bug fix, display only |
| — | 15 | **added** — diagnostics, read-only |

Cell 1 clones upstream BindCraft and ColabDesign straight from their own
repositories and pulls the official AlphaFold2 2022-12-06 parameters, so the
algorithm code is upstream's at install time — nothing is vendored or forked
here.

### Cell 8 — compatibility patches (required)

Two of the APIs ColabDesign calls were removed from JAX, and without these shims
the pipeline cannot run at all. Neither changes a number in the design maths.

- `jnp.clip` was called with argument names that no longer exist. The shim
  forwards to JAX's own clip and self-tests both calling styles. It is written
  to be safe to run twice; a naive version patches itself on the second run and
  blows the recursion limit.
- `clear_mem` reaches for a module that was deleted; the shim frees memory via
  `jax.clear_caches()` instead. It replaces the name both inside the BindCraft
  package and at notebook scope, because cell 6's wildcard import makes a second
  copy of it that is easy to miss.

### Cell 9 — tuning controls

A `preset` dropdown plus 14 fields for values upstream hardcodes in
`functions/colabdesign_utils.py`, including the trajectory pLDDT gate and the
CA-clash limit. It edits that file from a pristine backup each time, so repeated
runs never compound.

- *Production defaults* — the reset. Restores **this protocol's own**
  `settings_advanced/*.json` values, snapshotted as they were loaded in cell 4,
  and rewrites the two gates back to upstream's `final_plddt < 0.7` and
  `ca_clashes > 0` — verified to reproduce upstream's `colabdesign_utils.py`
  byte for byte.
- *Fast debug* — cuts iterations roughly tenfold and drops the quality gate to
  0.1 so every trajectory reaches the downstream code. Checks the pipeline end
  to end in a few minutes. **Designs from this mode are meaningless**, and it
  says so loudly.
- *Custom* — uses whatever the fields below are set to.

### Cell 11 — consolidate and rank

Upstream assigned each filename stem to `target_settings["binder_name"]`, the
very key the loop then compares against. That silently breaks every rank past
the first, and raises `ValueError` on any filename without `_model` in it.

### Cells 13 and 14 — display

Both crashed when nothing had been ranked yet. Cell 14 also handed a file path
to `HTML()` instead of the file's contents, so the animation never rendered.

### Cell 15 — diagnostics

Added here; nothing upstream to compare against. Reads the failure CSV and
reports why trajectories were rejected, classifies any clashes as
target-target / binder-binder / binder-target with residue names, gives the mean
binder pLDDT against the 0.7 gate, and says whether the next run will do any
work. It only reads files.

## Files

| File | What it is |
|---|---|
| `BindCraft_colab.ipynb` | The notebook. 15 numbered cells; 1–14 run in order, 15 is a diagnostic. |
| `examples/tgfb1.pdb` | **Example target only, not part of the setup.** Chains A and B of 3KFD, 112 residues each, no waters or ligands. The notebook is set to use chain A. |

## Credit

**The science here is not mine.** BindCraft is Martin Pacesa's
([martinpacesa/BindCraft](https://github.com/martinpacesa/BindCraft)), built on
ColabDesign, AlphaFold2 and PyRosetta. The design loop in cell 10 is byte-for-byte
upstream's, and the table above shows exactly how little else differs.

This repo is a personal wrapper. I made it to get BindCraft running on current
Colab after the JAX changes broke it, and added the tuning cell and the
diagnostics cell while debugging my own runs. Nothing is copied or forked here —
BindCraft, ColabDesign and the AlphaFold2 parameters are downloaded from their
original sources when you run cell 1, and stay under their own terms.

Two practical notes: PyRosetta is free for academic use only, so check its terms
before any commercial work. And if you publish anything from this, cite the
BindCraft authors, not this repo.
