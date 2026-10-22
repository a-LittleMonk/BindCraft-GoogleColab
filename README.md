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

**Not using Colab?** [`local/`](local/README.md) runs the same pipeline over SSH
on any Linux box with an NVIDIA GPU — your own machine or a rented one.

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
   they raise an error telling you so if they don't. Cell 9 is a panel of
   settings; running it applies what it shows, so leaving it alone is fine.
   If you change something in it afterwards, press **Apply** — the run cell
   stops with `UNAPPLIED` rather than running the previous values.

The target must be a clean PDB: no waters, no ligands, no alternate
conformations. `examples/tgfb1.pdb` shows the expected shape.

Give each campaign its own `design_path`, and clear the folder before starting
fresh. BindCraft resumes from whatever CSV files it finds there, so leftover
designs from an earlier run get ranked alongside new ones.

**Close the Colab tab before editing the notebook from anywhere else.** An open
tab writes its stale in-memory copy back to Drive, which makes Drive fork the
file into `... (1).ipynb`. That wasted a fair amount of time once already.

### What it ships with

Upstream ships its fields filled in with a working PDL1 example. This notebook
ships the two paths as **placeholders you must replace**, and the rest tuned for
peptide design:

| Field | Value | |
|---|---|---|
| `design_path` | `/content/drive/MyDrive/BindCraft/your_folder_Name/` | **replace** |
| `starting_pdb` | `/content/drive/MyDrive/pdb_file_name.pdb` | **replace** |
| `binder_name` | `TGFb1` | name this campaign |
| `chains` | `A` | |
| `target_hotspot_residues` | *(blank — BindCraft picks the site)* | |
| `design_protocol` | `Peptide` | |
| `filter_option` | `Peptide` | |
| `lengths` | `25,40` | |
| `number_of_final_designs` | `10` | |

**The notebook will not run until you replace those two paths.** They are
deliberately not real: a path that silently works for someone else's Drive is
worse than one that is obviously a placeholder.

Cell 3 stops you immediately if you forget. That matters because upstream does
not: BindCraft only opens `starting_pdb` at the *end* of each trajectory, to
measure the design against the target, so a wrong path raises nothing for about
half an hour and then kills the run with `Cannot open file`. The check turns
that into an error you get in a second. It covers:

- either path left as the placeholder
- Drive not mounted yet (it points you back to cell 2)
- `starting_pdb` not existing
- the file having no `ATOM` records at all
- `chains` naming a chain the file does not contain — it lists the ones it does

It then prints a **target check** — what BindCraft is actually going to see,
so you can confirm it before committing GPU hours:

```
====================================================================
TARGET CHECK  -  tgfb1.pdb
====================================================================
chains in file:    A, B
designing against: A
ignored:           B

chain A:  112 residues, numbered 1-112
       1  ALDTNYCFSS TEKNCCVRQL YIDFRKDLGW KWIHEPKGYH ANFCLGPCPY
      51  IWSLDTQYSK VLALYNQHNP GASAAPCCVP QALEPLPIVY YVGRKPKVEQ
     101  LSNMIVRSCK CS

chain B:  112 residues, numbered 1-112   (not selected)

hotspots: A31,A34,A91,A94
   A31     LYS  K
   A34     HIS  H
   A91     TYR  Y
   A94     ARG  R
   4 residues, 1 aromatic (F/Y/W), 0 hydrophobic (I/L/M/V)

binder length:  25,40 residues, sampled per trajectory
designs wanted: 10
====================================================================
```

Each sequence line is labelled with the **real residue number** of its first
residue, not a running count, so it stays honest about structures that do not
start at 1 or that have holes in them. Gaps in the numbering are reported
explicitly, because hotspots are given in PDB numbering and a structure that
starts at residue 30 is a classic way to aim at the wrong site.

Hotspots are resolved against the structure and named, in all the formats
upstream accepts (`A31`, `A31-34`, `31`, or a bare `A` for the whole chain). A
residue that does not exist, or one on a chain you did not select, is an error
rather than something silently dropped during the run. The aromatic count is
there because the upstream wiki advises patches containing F/Y/W alongside
I/L/M — a patch with none gets a note saying so.

Below the report it also warns about leftover waters or ligands, and says how
many accepted designs are already sitting in `design_path` and whether the next
run will therefore do any work.

Three of these are worth understanding rather than just accepting.

**The hotspot field ships blank on purpose.** Left empty, BindCraft picks the
interface itself rather than being aimed at one. Naming residues constrains it
to a patch you have chosen, which is worth doing once you know the site is
druggable — but a patch that is mostly charged and polar gives a short peptide
very little to grip, and an unhelpful patch is worse than none. Starting blank
lets the run tell you where it wants to bind.

**`lengths` matters more than it looks.** Binders shorter than roughly 20
residues cannot fold into anything confident enough to pass the trajectory
quality gate — 11- and 12-residue attempts scored 0.34–0.44 where the gate is
0.70, while 28–29 residues scored 0.74–0.76. Set the range too low and
BindCraft rejects everything and loops without ever accepting a design.

**`number_of_final_designs` is a stopping condition, not a request.** The run
loop counts the designs already in `design_path` before it starts and exits
immediately if that count has been reached. It used to ship as `1`, which meant
any folder with a previous result in it made a fresh run exit in zero seconds.
At `10` there is room to work, but the same thing happens once you reach 10 —
raise it, or point `design_path` somewhere new.

### The worked example

To run the TGF-β1 example, upload `examples/tgfb1.pdb` to the root of your
Drive and set cell 3 to:

```
design_path  = /content/drive/MyDrive/BindCraft/TGFb1/
starting_pdb = /content/drive/MyDrive/tgfb1.pdb
binder_name  = TGFb1
chains       = A
```

Leave the hotspot field blank and let BindCraft choose the site.

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
  cell 4 *and* `filter_option = "Peptide"` in cell 5 — both are preset here, but
  it is easy to change one and forget the other. `None` disables filtering
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

## Reproducing a run

`fixed_seed` in cell 9 is 0 by default, which is upstream's behaviour: each
trajectory draws its own random seed, its own binder length and its own
helicity value. Set it to any other number and the run cell seeds numpy and
`random` once before the loop, so that whole sequence repeats — trajectory 1
gets the same seed and length it got last time, trajectory 2 the same, and so
on. The seed used is in every design name as `_s<number>`, and in
`trajectory_stats.csv`.

**It needs `preset` on `Custom`**, which means the other fields are used as
typed too. Switching from `Production defaults` straight to `Custom` carries
this protocol's own values across, so in practice only the seed has to be typed
— and the cell prints every value that differs from the protocol's own
`settings_advanced/*.json`, so anything else that moved shows up in that list.

What it does **not** promise is identical metrics. GPU floating-point
reductions are not deterministic between runs, and MPNN's own sampling is not
seeded here, so scores can move in the last decimal place. Treat it as "the
same designs", not "the same numbers to the bit".

Use it to re-examine one trajectory, or to compare two settings on the same
starting points. Do not use it for a production campaign: a fixed seed draws
the same binder lengths every time, so the search stops exploring.

Each run is also recorded in `<binder_name>_run_settings.json`, which appends
one entry per start of the run cell with the seed, the preset, the full
`advanced_settings` and the filters — enough to tell which settings produced
which rows after the fact.

## Comparing settings: a fixed number of trajectories each

`trajectories_this_run` in cell 9 stops the run cell once that many
trajectories have been attempted in this execution of it. Set it to 50, run,
change one setting, run again, and each configuration has had the same 50
attempts. Like `fixed_seed` it needs `preset` on `Custom` — which is no
hardship here, since comparing settings means typing settings anyway.

Two things make it different from upstream's `max_trajectories`, which is also
in cell 9 and still works as it always did:

| | `trajectories_this_run` | `max_trajectories` |
|---|---|---|
| counts | every attempt | only trajectories that passed the pLDDT and clash gates and wrote a row to `trajectory_stats.csv` |
| counts from | zero, each time the run cell is started | the beginning of the campaign, across sessions |

So `max_trajectories` is no safeguard against a run that rejects everything —
rejected trajectories never write a row, so the count never moves — and it
cannot express "50 more from here" once a campaign is underway.
`trajectories_this_run` does both.

Two caveats for comparisons. The other stopping conditions still apply, so a
run can end before the budget if `number_of_final_designs` is reached (raise it,
or use a fresh `design_path` per configuration) or if the rejection-rate monitor
trips. And the designs of one configuration are not the designs of another
unless `fixed_seed` is set as well — without it each run samples different
lengths and seeds, so a 50-vs-50 comparison is comparing distributions, not
pairs.

One configuration cannot be `Production defaults` itself, since the budget is
ignored there. To benchmark against stock, switch that preset to `Custom` —
which carries the protocol's own values across unchanged — and set only the
budget. The cell reporting "All values are at this protocol's stock settings" is
the confirmation that nothing else moved.

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

### `Cannot open file ...` when a trajectory finally succeeds

A space in `design_path`, `binder_name` or `starting_pdb`. PyRosetta reads
those paths through Rosetta's own C++ file layer, which cannot open a path
containing a space.

It is a nasty one because it stays hidden. Every Python reader in the pipeline
handles the path fine — the clash check and the contact count both read the
same file seconds earlier — so trajectories run normally and get rejected
normally. The error appears only when a trajectory *succeeds* and relaxing
starts, which can be half an hour of GPU time in. And the message names the
file, not the reason, so it reads like the file is missing.

Cell 3 now refuses to start if any of those three contains a space, and prints
the same name with underscores.

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

### Cell 1 ends with `No matching distribution found for pyrosetta`

A server outage, not your setup. See *Cell 1 — PyRosetta mirror fallback*
below: from v1.9.0 the cell falls back to the Johns Hopkins mirror and stops
on a genuine failure instead of reporting success.

On an older copy, the install is skipped on re-run because the params marker
already exists. Install PyRosetta by hand in a new cell:

```python
!pip install -q pyrosetta-installer
!python -c "import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(mirror=1, serialization=True)"
```

then carry on from cell 2 — the clone, ColabDesign and the AlphaFold params
will already be in place.

### The same sequences come back every run

That means no new design work happened. Unless `fixed_seed` is set, every
trajectory draws its own `seed` and samples its own length, so genuinely new
trajectories cannot repeat. Cell 12 reads the cumulative
`final_design_stats.csv`, so it happily reprints old results. Check the
`_s<number>` in the design names and the "Sampled Trajectories" counter.

If `fixed_seed` *is* set, repeating is the point — and re-running it into the
same `design_path` produces no work at all, since every design name is already
on disk. The run cell says so and stops after 20 skips.

### `UNAPPLIED: cell 9 shows values that have not been applied.`

The run cell will not start on values the panel is only displaying. Press
**Apply** in cell 9, or re-run the cell, which applies what it shows. The
message lists every value that differs from what was last applied, so it is also
the quickest way to see what you changed.

### Cell 9 shows nothing, or an empty rectangle

Cell 9 is an ipywidgets panel, and widgets need their JavaScript loaded, which
is cell 1's `from ipywidgets import HTML, VBox`. If cell 1 has not run in this
runtime, or the browser blocked it, the panel does not render. Re-run cell 1,
then cell 9. The settings are still applied either way — the cell applies them
as it runs, before anything is displayed — so a run started from an invisible
panel uses this protocol's stock values, not nothing.

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
| Installation | 1 | PyRosetta mirror fallback — see below |
| Mount Drive | 2 | byte-identical |
| Binder design settings | 3 | form values, plus a settings check — see below |
| Advanced settings | 4 | form values only (protocol choice) |
| Filters | 5 | form value only |
| Import functions | 6 | byte-identical |
| Initialise PyRosetta | 7 | byte-identical |
| — | 8 | **added** — JAX / Python 3.13 shims |
| — | 9 | **added** — tuning panel and presets |
| Run BindCraft! | 10 | design loop unchanged; two run controls wrapped around it — see below |
| Consolidate & Rank | 11 | bug fix, post-processing only |
| Top 20 Designs | 12 | byte-identical |
| Top Design Display | 13 | guards an empty folder |
| Display animation | 14 | bug fix, display only |
| — | 15 | **added** — diagnostics, read-only |

Cell 1 clones upstream BindCraft and ColabDesign straight from their own
repositories and pulls the official AlphaFold2 2022-12-06 parameters, so the
algorithm code is upstream's at install time — nothing is vendored or forked
here. The only edit is to how PyRosetta is fetched.

### Cell 1 — PyRosetta mirror fallback

Upstream installs PyRosetta from `west.rosettacommons.org` and nowhere else.
That host is the Institute for Protein Design's file server at UW, and it does
go down. When it does, three things compound:

1. PyRosetta is not on PyPI, so pip has no fallback. It retries five times and
   gives up.
2. The cell printed `BindCraft installation is finished, ready to run!` anyway,
   because nothing checked whether pip had succeeded. The failure only
   surfaced four cells later, at *Initialise PyRosetta*.
3. By then the AlphaFold params marker file existed, so re-running cell 1
   skipped the entire install block and never retried — which made a passing
   outage look permanent.

PyRosetta is now installed outside that block, and **upstream's own source is
still what is read first**: the `quarterly` channel on
`west.rosettacommons.org`, exactly as upstream's command names it.

```
pip install -q pyrosetta --find-links
  https://west.rosettacommons.org/pyrosetta/quarterly/release.cxx11thread.serialization
```

That matters more than it looks. The obvious fix is to hand the whole job to
[`pyrosetta-installer`](https://pypi.org/project/pyrosetta-installer/),
RosettaCommons' own tool, which knows both official mirrors — but it reads the
server's `release` directory while upstream pins the `quarterly` one. Using it
unconditionally would quietly change which PyRosetta build you get on a
perfectly normal day. So it is only reached when the official source cannot
deliver, and then it is pointed at `graylab.jhu.edu` (Johns Hopkins).

The wheel is picked off upstream's own page rather than left to pip, purely so
there is a progress bar. Choosing it correctly needs care: the versions there
look like `2026.29` and `2026.3`, and sorted as text the older one wins, so
they are compared as numbers. If anything about that goes wrong — the page
changes shape, no wheel matches this Python — **upstream's own pip command runs
instead**, exactly as before, just without the bar.

A short TCP probe runs first, because when the UW host is unreachable pip
spends about four minutes retrying before giving up. If it does not answer, the
cell says so and goes straight to the fallback.

The fallback also has to repair that mirror's TLS on the way past.
`graylab.jhu.edu` serves an incomplete certificate chain — its leaf certificate
is issued by *InCommon RSA OV SSL CA 3*, but the server still sends an older
intermediate, so nothing can build a path to the root and Python stops with
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. Browsers
and curl paper over this by fetching the missing certificate themselves; urllib
and pip do not, which is why that host tests healthy from a shell and fails
from inside the notebook. The cell fetches it from the address the leaf names
and adds it to a copy of the normal trust store. **Verification is not
disabled** — the root it chains to is already trusted, and every certificate is
still checked.

### Cell 1 — progress on the long downloads

Cell 1 pulls down about 7 GB in total and upstream reports none of it. Both
large downloads now share one progress line:

| What | Size | Upstream showed |
|---|---|---|
| AlphaFold2 parameters | 5.2 GB | one line, then silence |
| PyRosetta wheel | 1.7 GB | nothing at all |
| BindCraft clone | 6 MB | git's own progress |
| ColabDesign | small | nothing, but it takes seconds |

The AlphaFold download runs in the background while ColabDesign installs, and
upstream simply waited for a marker file in a sleep loop. That wait is now
where progress is reported, measured from the growing tar. aria2c is told
`--file-allocation=none` for this to work at all: it preallocates by default,
which makes the file jump to full size immediately and leaves nothing to
measure.

ColabDesign is installed in the background too, which is what makes the bar
useful. Upstream installed it in the foreground, so it blocked for several
minutes with nothing on screen and the bar then appeared at 98% — the download
had been running the whole time, invisibly. Both now run together and one loop
waits for the pair, marking the line `(+ ColabDesign)` while that is still
going.

Progress is measured from the **blocks allocated on disk**, not the file's
apparent size. aria2c fetches with 16 connections and no preallocation, so its
output file is sparse: the connection handling the last chunk writes near the
end within seconds, and the apparent size jumps to nearly the full length while
almost nothing has arrived. A single byte written at the 70% offset reports 70%.
Allocated blocks track what is actually there. Completion is taken from
aria2c's own `.aria2` control file, which it deletes when the transfer is done
— a far better signal than comparing sizes.

The extraction is watched as well, by the params folder filling up. It takes
several minutes and upstream reported none of it. Once the params are ready but
ColabDesign is still building, the line says so plainly rather than showing a
finished bar with a rate decaying towards zero.

For PyRosetta, **the wheel is downloaded by the cell rather than by pip** —
on both routes, the official server and the fallback — with the same bar:

```
  [===================                     ]  48.3%    807/1594 MB   1.3 MB/s  ETA 10.1 min
```

That is not cosmetic. The Johns Hopkins mirror serves at roughly 1-2 MB/s, so
the 1.67 GB wheel takes 20-30 minutes — and pip prints *nothing* for the whole
of it, because it only draws a progress bar when writing to a terminal, which
it is not inside a notebook. The cell therefore sat completely silent for half
an hour and looked hung while working perfectly. Now you can see it moving,
and pip is handed a local file it installs in seconds.

Finally, the cell **verifies PyRosetta is importable before claiming success**,
and raises otherwise. Re-running it retries, so an outage no longer means
resetting the runtime.

So on a normal day this behaves exactly as upstream does, and the additions
only run on the path where upstream would have failed silently.

### Cell 3 — settings check

Upstream's cell 3 writes the settings JSON and nothing else, so every mistake
in it surfaces much later: a wrong `starting_pdb` half an hour into the first
trajectory, a wrong chain id deeper still. The form fields are unchanged, but a
check now runs before the JSON is written and before any folder is created —
placeholders, Drive not mounted, missing file, a file with no `ATOM` records,
a chain that is not present, a hotspot that does not resolve. It raises on all
of those, then prints a target check: chains found, which are being designed
against, the one-letter sequence of each selected chain labelled by real
residue number, numbering gaps, every hotspot named, the binder length range
and the design count. Leftover waters and ligands get a warning, and it says
how many accepted designs `design_path` already holds.

It only reads; nothing about the design maths changes.

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

A `preset` dropdown plus 16 fields: the values upstream keeps in
`settings_advanced/*.json`, the two it hardcodes in
`functions/colabdesign_utils.py` (the trajectory pLDDT gate and the CA-clash
limit), and two run controls of this notebook's own. It edits that source file
from a pristine backup each time, so repeated runs never compound.

It is an **ipywidgets panel**, not a Colab `@param` form. Under either preset
every field is greyed out and shows that preset's own value — for `Production
defaults`, the value from the protocol JSON cell 6 loaded — and switching back
from `Custom` resets them all, so the defaults on show are always the ones a run
would use. A Colab form cannot do that: the code that reads an `@param` field
can neither disable it nor write a value back into it.

- *Production defaults* — the reset. Restores **this protocol's own**
  `settings_advanced/*.json` values, snapshotted as they were loaded in cell 4,
  and rewrites the two gates back to upstream's `final_plddt < 0.7` and
  `ca_clashes > 0` — verified to reproduce upstream's `colabdesign_utils.py`
  byte for byte, with both run controls back at 0.
- *Fast debug* — cuts iterations roughly tenfold and drops the quality gate to
  0.1 so every trajectory reaches the downstream code. Checks the pipeline end
  to end in a few minutes. **Designs from this mode are meaningless**, and it
  says so loudly.
- *Custom* — makes the fields editable, starting from the values on show.
  Switching straight from `Production defaults` therefore starts from this
  protocol's own values, with nothing to retype.

Two things follow from being widgets rather than a form. Values live in the
kernel, not in the notebook file, so a fresh runtime opens at the protocol's
stock values instead of at whatever was typed last session; the panel is cached,
so re-running the cell re-displays it with your values still in it, and only a
runtime restart clears them. And a widget changes nothing by being changed, so
the panel has an **Apply** button. Running the cell also applies what it shows,
which is why a straight run of cells 1–14 needs no clicking; the button is for
changing something afterwards without re-running the cell. The panel says
whether what it shows has been applied, and the run cell refuses to start on
values that have not been.

The last two sit under **Run controls**. Upstream has no equivalent of either:

- `fixed_seed` — see [Reproducing a run](#reproducing-a-run).
- `trajectories_this_run` — see
  [Comparing settings](#comparing-settings-a-fixed-number-of-trajectories-each).

Both are 0 under either preset, and `Custom` is the only way to set them. That
is deliberate: a seeded run or a capped run is not an upstream run, so letting
either be set under `Production defaults` would make that label untrue. When
they are in force they appear in the drift report with everything else that
differs from stock, so a seeded run cannot be mistaken for a stock one.

### Cell 10 — the run loop

The design loop itself is upstream's, untouched. What is added sits around it:

- The two cell 9 run controls above, read with `globals().get(...)` so a copy of
  the notebook whose cell 9 predates them still runs exactly as upstream did.
- A branch on the duplicate-name check. Upstream has none: it builds
  `design_name` from the length and the seed, skips the trajectory if that file
  already exists, and otherwise falls through to the top of `while True:`
  without advancing any counter. With a fresh random seed per trajectory a
  repeat is vanishingly rare, so this never mattered. A fixed seed makes it
  certain — re-run into the same `design_path` and every name it generates is
  already on disk — and the loop would spin forever printing nothing. It now
  counts the skips and stops after 20 in a row with a message saying why.
- The settings record written at the start of the cell logs both controls.

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
