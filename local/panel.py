"""Form fields for the local BindCraft runner.

The notebook cells are two lines each; everything they do is here. Widgets are
built once and cached in _W, so re-running a cell re-displays the same widgets
with whatever you typed into them still there.

Nothing in here runs a campaign. run() hands that to run.sh, which starts it in
a tmux session owned by the machine rather than by the notebook.
"""

import json
import os
import pathlib
import subprocess
import sys
from itertools import combinations

import ipywidgets as W
from IPython.display import HTML, clear_output, display

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
BC_ROOT = pathlib.Path(os.environ.get("BC_ROOT", "/workspace"))
BC_DIR = BC_ROOT / "bindcraft"
SETTINGS_DIR = HERE / "settings"

STATE = {"settings": None, "design_path": str(BC_ROOT / "designs"),
         "advanced": None, "filters": None}

_W = {}

_ROW = dict(style={"description_width": "190px"}, layout=W.Layout(width="700px"))


def _md(text):
    return W.HTML(f"<div style='max-width:760px;margin:2px 0 6px'>{text}</div>")


def _expand(v):
    return str(v).replace("{{REPO}}", str(REPO)).replace("{{BC_ROOT}}", str(BC_ROOT))


def _running():
    return subprocess.run(["tmux", "has-session", "-t", "bindcraft"],
                          capture_output=True).returncode == 0


def _design_path():
    return pathlib.Path(STATE["design_path"])


# ---------------------------------------------------------------- 1. install

def check_install():
    print("kernel :", sys.executable)
    ok = True
    for label, p in (("run.sh", HERE / "run.sh"),
                     ("bindcraft", BC_DIR / "bindcraft.py"),
                     ("AF2 weights", BC_DIR / "params" / "params_model_5_ptm.npz")):
        hit = p.exists()
        ok &= hit
        print(f"{label:12s}: {'OK     ' if hit else 'MISSING'} {p}")

    try:
        import pandas  # noqa: F401
        print("packages    : OK")
    except ModuleNotFoundError as e:
        ok = False
        print(f"packages    : MISSING ({e.name})")
        print("\n>>> This notebook is running in the wrong Python.")
        print(">>> Kernel > Change kernel > 'Python (BindCraft)'.")
        print(">>> If that kernel is not listed, run: bash local/install.sh")

    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                          "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    print("GPU         :", gpu or "none detected - designs would be useless")
    if not ok:
        print("\nFix the above before running the cells below.")


# --------------------------------------------------------------- 2. settings

def _build_settings():
    files = sorted(p.name for p in SETTINGS_DIR.glob("*.json"))
    w = {}
    w["file"] = W.Dropdown(options=files + ["<new campaign>"],
                           value=files[0] if files else "<new campaign>",
                           description="Settings file", **_ROW)
    w["path"] = W.Text(description="design_path", **_ROW)
    w["name"] = W.Text(description="binder_name", **_ROW)
    w["pdb"] = W.Text(description="starting_pdb", **_ROW)
    w["chains"] = W.Text(description="chains", placeholder="A,C", **_ROW)
    w["hotspots"] = W.Text(description="target_hotspot_residues",
                           placeholder="A31,A34 or blank", **_ROW)
    w["lengths"] = W.IntRangeSlider(min=15, max=150, step=1, description="lengths",
                                    continuous_update=False, **_ROW)
    w["designs"] = W.IntText(description="number_of_final_designs", **_ROW)
    w["warn"] = W.HTML()
    w["out"] = W.Output()

    def check(*_):
        lo, _hi = w["lengths"].value
        w["warn"].value = (
            "<b style='color:#c0392b'>Under ~20 residues a binder cannot fold into "
            "anything that passes the quality gate - BindCraft will reject every "
            "trajectory and loop without accepting a design.</b>" if lo < 20 else "")

    def load(*_):
        name = w["file"].value
        if name == "<new campaign>":
            s = {"design_path": f"{BC_ROOT}/designs/mytarget/",
                 "binder_name": "mytarget", "starting_pdb": "", "chains": "A",
                 "target_hotspot_residues": "", "lengths": [25, 40],
                 "number_of_final_designs": 10}
        else:
            s = json.load(open(SETTINGS_DIR / name))
        w["path"].value = _expand(s.get("design_path", ""))
        w["name"].value = s.get("binder_name", "")
        w["pdb"].value = _expand(s.get("starting_pdb", ""))
        w["chains"].value = s.get("chains", "A")
        w["hotspots"].value = s.get("target_hotspot_residues") or ""
        lo, hi = s.get("lengths", [25, 40])
        w["lengths"].value = (int(lo), int(hi))
        w["designs"].value = int(s.get("number_of_final_designs", 10))
        STATE["design_path"] = w["path"].value
        check()

    def on_save(_=None):
        with w["out"]:
            clear_output()
            print(save_settings())

    w["save"] = W.Button(description="Save settings", icon="save",
                         button_style="primary")
    w["save"].on_click(on_save)
    w["file"].observe(load, names="value")
    w["lengths"].observe(check, names="value")
    load()

    w["box"] = W.VBox([
        _md("Pick an existing campaign to resume it, or <code>&lt;new campaign&gt;</code> "
            "to start one. These are the files in <code>local/settings/</code> - the "
            "same ones <code>run.sh</code> reads, so the notebook and the command "
            "line never disagree."),
        w["file"],
        _md("Where designs are written. Give every campaign its own folder: "
            "BindCraft resumes from the CSVs it finds there, so leftovers from an "
            "old run get ranked alongside the new ones."),
        w["path"], w["name"],
        _md("The target <code>.pdb</code>, experimental or AlphaFold2. Trim it to as "
            "small as you need - the whole selected chain is backpropagated through "
            "the network and a big one costs real time. No waters, no ligands, no "
            "alternate conformations."),
        w["pdb"],
        _md("Which chains to target, comma-separated. Other chains are ignored."),
        w["chains"],
        _md("Which positions to aim at: <code>1,2-10</code>, chain-specific "
            "<code>A1-10,B1-20</code>, or whole chains <code>A</code>. Blank lets "
            "the pipeline pick a site."),
        w["hotspots"],
        _md("Minimum and maximum binder size; sizes are sampled between them."),
        w["lengths"],
        _md("How many designs passing the filters you want."),
        w["designs"],
        w["warn"], w["save"], w["out"],
    ])
    return w


def settings():
    if "settings" not in _W:
        _W["settings"] = _build_settings()
    display(_W["settings"]["box"])


def _collect():
    w = _W["settings"]
    lo, hi = w["lengths"].value
    return {"design_path": w["path"].value.strip().rstrip("/") + "/",
            "binder_name": w["name"].value.strip(),
            "starting_pdb": w["pdb"].value.strip(),
            "chains": w["chains"].value.strip(),
            "target_hotspot_residues": w["hotspots"].value.strip(),
            "lengths": [int(lo), int(hi)],
            "number_of_final_designs": int(w["designs"].value)}


def save_settings():
    """Write the form to its JSON file and return a short report."""
    w = _W["settings"]
    s = _collect()
    name = w["file"].value
    if name == "<new campaign>":
        name = (s["binder_name"] or "mytarget") + ".json"
    path = SETTINGS_DIR / name
    path.write_text(json.dumps(s, indent=4) + "\n")
    if name not in w["file"].options:
        w["file"].options = (sorted(p.name for p in SETTINGS_DIR.glob("*.json"))
                             + ["<new campaign>"])
    w["file"].value = name
    STATE["settings"], STATE["design_path"] = str(path), s["design_path"]

    msg = [f"Saved {path}"]
    if not os.path.isfile(s["starting_pdb"]):
        msg += ["", f"WARNING: starting_pdb does not exist: {s['starting_pdb']}",
                "BindCraft re-reads it only at the END of a trajectory, so a wrong",
                "path costs a full trajectory before it errors."]
    if " " in s["starting_pdb"] or " " in s["design_path"]:
        msg += ["", "WARNING: a path contains a space. PyRosetta cannot open those."]
    return "\n".join(msg)


# --------------------------------------------------------------- 3. advanced

_BASE = {"Default": "default_4stage_multimer",
         "Beta-sheet": "betasheet_4stage_multimer",
         "Peptide": "peptide_3stage_multimer"}


def _build_advanced():
    w = {}
    w["design"] = W.Dropdown(options=list(_BASE), value="Peptide",
                             description="design_protocol", **_ROW)
    w["pred"] = W.Dropdown(options=["Default", "HardTarget"],
                           description="prediction_protocol", **_ROW)
    w["iface"] = W.Dropdown(options=["AlphaFold2", "MPNN"],
                            description="interface_protocol", **_ROW)
    w["tmpl"] = W.Dropdown(options=["Default", "Masked"],
                           description="template_protocol", **_ROW)
    w["out"] = W.Output()

    def path():
        tag = _BASE[w["design"].value]
        if w["iface"].value == "MPNN":
            tag += "_mpnn"
        if w["tmpl"].value == "Masked":
            tag += "_flexible"
        if w["pred"].value == "HardTarget":
            tag += "_hardtarget"
        return BC_DIR / "settings_advanced" / f"{tag}.json"

    def show(*_):
        with w["out"]:
            clear_output()
            p = path()
            if p.exists():
                STATE["advanced"] = str(p)
                print("advanced settings:", p.name)
            else:
                STATE["advanced"] = None
                print("No preset for that combination:", p.name)
                print("\nUpstream does not ship every combination. Available here:")
                for q in sorted((BC_DIR / "settings_advanced")
                                .glob(f"{_BASE[w['design'].value]}*.json")):
                    print("  ", q.name)

    for key in ("design", "pred", "iface", "tmpl"):
        w[key].observe(show, names="value")
    show()

    w["box"] = W.VBox([
        _md("Which design protocol. <b>Default</b> is recommended. <b>Beta-sheet</b> "
            "promotes beta-sheeted binders but needs more sampling. <b>Peptide</b> "
            "is optimised for helical peptide binders."),
        w["design"],
        _md("Prediction protocol. <b>Default</b> predicts the binder from single "
            "sequence. <b>HardTarget</b> uses an initial guess to improve complex "
            "prediction on difficult targets, at the cost of some bias."),
        w["pred"],
        _md("Interface design. <b>AlphaFold2</b> generates the interface; "
            "<b>MPNN</b> optimises it with soluble MPNN."),
        w["iface"],
        _md("Target template. <b>Default</b> allows limited flexibility, "
            "<b>Masked</b> allows more on both sidechain and backbone."),
        w["tmpl"], w["out"],
    ])
    return w


def advanced():
    if "advanced" not in _W:
        _W["advanced"] = _build_advanced()
    display(_W["advanced"]["box"])


# ---------------------------------------------------------------- 4. filters

_FILTERS = {"Default": "default_filters.json",
            "Peptide": "peptide_filters.json",
            "Relaxed": "relaxed_filters.json",
            "Peptide_Relaxed": "peptide_relaxed_filters.json",
            "None": "no_filters.json"}


def _build_filters():
    w = {"choice": W.Dropdown(options=list(_FILTERS), value="Peptide",
                              description="filter_option", **_ROW),
         "out": W.Output()}

    def show(*_):
        with w["out"]:
            clear_output()
            p = BC_DIR / "settings_filters" / _FILTERS[w["choice"].value]
            STATE["filters"] = str(p)
            print("filters:", p.name, "" if p.exists() else "  (MISSING)")

    w["choice"].observe(show, names="value")
    show()
    w["box"] = W.VBox([
        _md("<b>Default</b> is recommended. <b>Peptide</b> is for peptide binders. "
            "<b>Relaxed</b> is more permissive but may give fewer experimental "
            "successes. <b>Peptide_Relaxed</b> is for non-helical peptides. "
            "<b>None</b> is for benchmarking."),
        w["choice"], w["out"],
    ])
    return w


def filters():
    if "filters" not in _W:
        _W["filters"] = _build_filters()
    display(_W["filters"]["box"])


# ----------------------------------------------------------------- 5. tuning

_FAST = dict(soft_iterations=8, temporary_iterations=5, hard_iterations=2,
             greedy_iterations=2, num_seqs=4, max_mpnn_sequences=1,
             save_design_animations=False, save_design_trajectory_plots=False)

_FIELDS = [
    ("soft", "soft_iterations", 75), ("temp", "temporary_iterations", 45),
    ("hard", "hard_iterations", 5), ("greedy", "greedy_iterations", 15),
    ("numseq", "num_seqs", 10), ("maxmpnn", "max_mpnn_sequences", 2),
    ("recdes", "num_recycles_design", 1), ("recval", "num_recycles_validation", 3),
    ("maxtraj", "max_trajectories", 0),
]


def _build_tuning():
    w = {"preset": W.Dropdown(options=["Production defaults", "Fast debug",
                                       "Custom - use fields below"],
                              description="preset", **_ROW),
         "out": W.Output()}
    for key, desc, val in _FIELDS:
        w[key] = W.IntText(value=val, description=desc, **_ROW)
    w["sample"] = W.Checkbox(value=True, description="sample_models",
                             indent=True, **_ROW)
    w["anim"] = W.Checkbox(value=True, description="save_design_animations",
                           indent=True, **_ROW)
    w["plots"] = W.Checkbox(value=True, description="save_design_trajectory_plots",
                            indent=True, **_ROW)
    w["gate"] = W.FloatText(value=0.70, step=0.05,
                            description="trajectory_plddt_threshold", **_ROW)
    w["clash"] = W.IntText(value=0, description="max_ca_clashes", **_ROW)

    custom_keys = [k for k, _, _ in _FIELDS] + ["sample", "anim", "plots",
                                                "gate", "clash"]

    def sync(*_):
        custom = w["preset"].value.startswith("Custom")
        for k in custom_keys:
            w[k].disabled = not custom
        with w["out"]:
            clear_output()
            if w["preset"].value == "Production defaults":
                print("Using this protocol's own settings_advanced JSON unchanged,")
                print("with the stock gates (0.70 final pLDDT, 0 CA clashes).")
            elif w["preset"].value == "Fast debug":
                print("Iterations cut ~10x, gates dropped to 0.10 pLDDT / 100")
                print("clashes, filters off, one design, animations and plots off.")
                print("DESIGNS FROM THIS MODE ARE STRUCTURALLY MEANINGLESS.")
            else:
                print("Using the fields above. They start at the Peptide protocol's")
                print("values; Default and Beta-sheet use num_seqs 20, so prefer")
                print("'Production defaults' over retyping a whole protocol.")

    w["preset"].observe(sync, names="value")
    sync()

    w["box"] = W.VBox([
        _md("<b>Preset.</b> <code>Production defaults</code> is the reset - this "
            "protocol's own values, gates untouched. <code>Fast debug</code> "
            "exercises the pipeline in minutes and produces meaningless designs. "
            "<code>Custom</code> uses the fields below."),
        w["preset"], w["out"],
        _md("<b>Trajectory optimisation</b> - the biggest lever on runtime."),
        w["soft"], w["temp"], w["hard"], w["greedy"],
        _md("<b>MPNN sequence design</b>"), w["numseq"], w["maxmpnn"],
        _md("<b>AlphaFold2</b>"), w["recdes"], w["recval"], w["sample"],
        _md("<b>Limits and output.</b> <code>max_trajectories</code> 0 means "
            "unlimited. It counts rows in <code>trajectory_stats.csv</code>, and "
            "rejected trajectories never write one, so it is no safeguard against "
            "a run that rejects everything."),
        w["maxtraj"], w["anim"], w["plots"],
        _md("<b>Acceptance gates</b>, which upstream hardcodes in "
            "<code>colabdesign_utils.py</code> rather than exposing in the JSON. A "
            "trajectory is rejected below the pLDDT threshold or above the CA-clash "
            "count. Lowering either lets unfolded junk reach MPNN - use it to "
            "exercise the pipeline, never for real designs."),
        w["gate"], w["clash"],
    ])
    return w


def tuning():
    if "tuning" not in _W:
        _W["tuning"] = _build_tuning()
    display(_W["tuning"]["box"])


# --------------------------------------------------------------------- 6. run

def _advanced_json():
    """Return (advanced_path, plddt_override, clash_override)."""
    t = _W["tuning"]
    base = pathlib.Path(STATE["advanced"])
    if t["preset"].value == "Production defaults":
        return base, None, None

    if t["preset"].value == "Fast debug":
        # run.sh --smoke builds its own advanced file and sets both gates, so
        # passing anything here would only be overridden.
        return None, None, None

    a = json.load(open(base))
    a.update({desc: int(t[key].value) for key, desc, _ in _FIELDS
              if desc != "max_trajectories"})
    a["max_trajectories"] = int(t["maxtraj"].value) or False
    a["sample_models"] = bool(t["sample"].value)
    a["save_design_animations"] = bool(t["anim"].value)
    a["save_design_trajectory_plots"] = bool(t["plots"].value)
    out = BC_ROOT / "advanced_notebook.json"
    out.write_text(json.dumps(a, indent=4) + "\n")
    gate = float(t["gate"].value)
    return out, (gate if abs(gate - 0.70) > 1e-9 else None), (int(t["clash"].value) or None)


def _build_run():
    w = {"out": W.Output(),
         "go": W.Button(description="Run BindCraft", button_style="success",
                        icon="play"),
         "stop": W.Button(description="Stop run", button_style="danger",
                          icon="stop")}

    def go(_):
        with w["out"]:
            clear_output()
            missing = [n for n in ("settings", "advanced", "tuning", "filters")
                       if n not in _W]
            if missing:
                print("Run the cells above first; not yet run:", ", ".join(missing))
                return
            if _running():
                print("A run is already going in tmux session 'bindcraft'.")
                print("Stop it first, or you will lose it.")
                return
            if not STATE["advanced"]:
                print("Cell 3 has no valid protocol preset selected.")
                return
            print(save_settings(), "\n")
            adv, gate, clash = _advanced_json()
            cmd = ["bash", str(HERE / "run.sh"), "-s", STATE["settings"]]
            if _W["tuning"]["preset"].value == "Fast debug":
                cmd.append("--smoke")
            else:
                cmd += ["-f", STATE["filters"], "-a", str(adv)]
                if gate is not None:
                    cmd += ["--plddt", f"{gate:.2f}"]
                if clash is not None:
                    cmd += ["--clashes", str(clash)]
            print(" ".join(cmd), "\n")
            r = subprocess.run(cmd, capture_output=True, text=True)
            print(r.stdout, r.stderr, sep="")
            if r.returncode:
                print(f"\nrun.sh exited {r.returncode} - nothing was launched.")
            else:
                print("\nRunning in tmux. Closing this tab will not stop it.")

    def stop(_):
        with w["out"]:
            clear_output()
            if not _running():
                print("No run in progress.")
                return
            subprocess.run(["tmux", "kill-session", "-t", "bindcraft"])
            print("Stopped. Whatever was already written to the design folder is")
            print("kept, and running again resumes from it.")

    w["go"].on_click(go)
    w["stop"].on_click(stop)
    w["box"] = W.VBox([
        _md("This writes the settings from the cells above and hands the campaign "
            "to <code>run.sh</code>, which starts it in a <code>tmux</code> "
            "session. The run belongs to the machine, not to this notebook - the "
            "browser can go away. A real campaign takes hours."),
        W.HBox([w["go"], w["stop"]]), w["out"],
    ])
    return w


def run():
    if "run" not in _W:
        _W["run"] = _build_run()
    display(_W["run"]["box"])


# ---------------------------------------------------------------- 7. progress

def _build_progress():
    import pandas as pd

    w = {"out": W.Output(), "ref": W.Button(description="Refresh", icon="refresh")}

    def refresh(_=None):
        with w["out"]:
            clear_output()
            dp = _design_path()
            print("tmux session 'bindcraft':", "running" if _running() else "not running")
            print("design folder           :", dp)
            if not dp.is_dir():
                print("\nNothing written yet.")
                return
            for label, fn in (("Sampled trajectories", "trajectory_stats.csv"),
                              ("MPNN designs", "mpnn_design_stats.csv"),
                              ("Accepted designs", "final_design_stats.csv")):
                f = dp / fn
                n = len(pd.read_csv(f)) if f.exists() else 0
                print(f"{label:22s} {n}")
            logs = sorted(dp.glob("run_*.log"))
            if logs:
                print(f"\n--- last 30 lines of {logs[-1].name} ---")
                print(subprocess.run(["tail", "-n", "30", str(logs[-1])],
                                     capture_output=True, text=True).stdout)

    w["ref"].on_click(refresh)
    w["refresh"] = refresh
    w["box"] = W.VBox([_md("Press Refresh. Nothing polls on its own, so this never "
                           "holds the kernel."), w["ref"], w["out"]])
    return w


def progress():
    if "progress" not in _W:
        _W["progress"] = _build_progress()
    display(_W["progress"]["box"])
    _W["progress"]["refresh"]()


# -------------------------------------------------------------- 8-10. results

def top_designs(n=20):
    import pandas as pd

    final = _design_path() / "final_design_stats.csv"
    if not final.exists():
        print("No final_design_stats.csv yet - nothing has been ranked.")
        return
    df = pd.read_csv(final)
    if df.empty:
        print("No designs accepted yet. The diagnose cell says why.")
        return
    cols = [c for c in ["Rank", "Design", "Sequence", "Length", "pLDDT", "i_pTM",
                        "pAE", "i_pAE", "Binder_Energy_Score",
                        "ShapeComplementarity", "Interface_Hydrophobicity",
                        "n_InterfaceResidues", "Hotspot_RMSD"] if c in df.columns]
    out = df[cols] if cols else df
    if "Rank" in out.columns:
        out = out.sort_values("Rank")
    pd.set_option("display.max_colwidth", 60)
    display(out.head(n))
    print(f"\n{len(df)} accepted design(s) total.")


def top_design_structure():
    ranked = sorted((_design_path() / "Accepted" / "Ranked").glob("*.pdb"))
    if not ranked:
        print("Nothing in Accepted/Ranked yet.")
        return
    pdb = ranked[0]
    print(f"{len(ranked)} ranked design(s). Showing {pdb.name}")
    try:
        import py3Dmol
        v = py3Dmol.view(width=780, height=520)
        v.addModel(pdb.read_text(), "pdb")
        v.setStyle({"cartoon": {"color": "lightgrey"}})
        v.setStyle({"chain": "B"}, {"cartoon": {"color": "orange"}})
        v.zoomTo()
        v.show()
        print("Target grey, binder orange.")
    except Exception as e:
        print("Could not render:", e)


def animation():
    anims = sorted((_design_path() / "Accepted" / "Animation").glob("*.html"))
    if not anims:
        print("No animations. They are off in Fast debug and in any run with")
        print("save_design_animations unchecked.")
        return
    print(f"{len(anims)} animation(s). Showing {anims[0].name}")
    # Pass the file's CONTENTS: HTML(path) renders the path as text.
    display(HTML(anims[0].read_text()))


# ------------------------------------------------------------- 11. diagnostics

def _ca_atoms(path):
    out = []
    for line in open(path):
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            out.append((line[21], int(line[22:26]),
                        (float(line[30:38]), float(line[38:46]), float(line[46:54]))))
    return out


def diagnose(max_pdbs=6):
    import pandas as pd

    dp = _design_path()

    # Will the next run do anything at all? The loop counts .pdb files in
    # Accepted/ before sampling and breaks once that count reaches
    # number_of_final_designs, printing the count it found rather than your target.
    acc = dp / "Accepted"
    have = len([f for f in acc.glob("*.pdb")
                if not f.name.startswith(".")]) if acc.is_dir() else 0
    want = None
    if STATE["settings"] and os.path.isfile(STATE["settings"]):
        want = int(json.load(open(STATE["settings"]))["number_of_final_designs"])
    print(f"Accepted designs on disk: {have}" + (f"   target: {want}" if want else ""))
    if want and have >= want:
        print("   -> the next run reranks and exits in seconds without designing")
        print(f"      anything. Raise number_of_final_designs above {have}, save,")
        print("      then run again.")
    elif want:
        print(f"   -> {want - have} more to find")
    print()

    # The tally BindCraft already keeps.
    cand = sorted(dp.glob("*failure*.csv"))
    if cand:
        f = pd.read_csv(cand[0])
        tally = {c: int(f[c].sum()) for c in f.columns if f[c].dtype != object}
        tally = {k: v for k, v in sorted(tally.items(), key=lambda kv: -kv[1]) if v}
        if tally:
            print("Why designs were rejected:")
            for k, v in tally.items():
                print(f"  {v:6d}  {k}")
        else:
            print("Failure tally is empty.")
    else:
        print("No failure CSV found in", dp)
    print()

    # Where the clashes are. The gate counts any two CA atoms closer than 2.5 A
    # (same residue and directly sequential pairs excluded). Because it looks at
    # CA only it does not skip same-chain pairs, so a collapsed binder trips it
    # just as readily as a binder driven into the target. This says which.
    pdbs = sorted((dp / "Trajectory").glob("*.pdb"))[:max_pdbs]
    if not pdbs:
        print("No trajectory PDBs in", dp / "Trajectory")
        return
    for p in pdbs:
        atoms = _ca_atoms(p)
        same = cross = 0
        for (c1, r1, x1), (c2, r2, x2) in combinations(atoms, 2):
            if c1 == c2 and abs(r1 - r2) <= 1:
                continue
            if sum((a - b) ** 2 for a, b in zip(x1, x2)) < 2.5 ** 2:
                if c1 == c2:
                    same += 1
                else:
                    cross += 1
        verdict = ("clean" if same + cross == 0 else
                   "binder collapsed on itself" if cross == 0 else
                   "binder into target" if same == 0 else "both")
        print(f"{p.name:46s} same-chain {same:4d}  cross-chain {cross:4d}   {verdict}")
    print("\nSame-chain clashes mean the binder folded into itself: a length or")
    print("protocol problem. Cross-chain means it was driven into the target,")
    print("usually the hotspots.")
