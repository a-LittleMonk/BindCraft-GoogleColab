#!/usr/bin/env bash
# Launch a BindCraft campaign on a local/rented GPU box.
#
#   bash run.sh --smoke                     # ~10 min pipeline check, designs are meaningless
#   bash run.sh                             # real campaign, detached in tmux
#   bash run.sh -s settings/mytarget.json
#   bash run.sh --plddt 0.5                 # loosen the trajectory quality gate
#   bash run.sh --fg                        # run in the foreground instead of tmux
#
# Detached runs: reattach with `tmux attach -t bindcraft`, detach with ctrl-b d.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BC_ROOT="${BC_ROOT:-/workspace}"
BC_DIR="$BC_ROOT/bindcraft"

SETTINGS="$REPO/local/settings/tgfb1.json"
FILTERS="$BC_DIR/settings_filters/peptide_filters.json"
ADVANCED="$BC_DIR/settings_advanced/peptide_3stage_multimer_mpnn.json"
SMOKE=0
FOREGROUND=0
PLDDT=""

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--settings) SETTINGS="$2"; shift 2 ;;
    -f|--filters)  FILTERS="$2";  shift 2 ;;
    -a|--advanced) ADVANCED="$2"; shift 2 ;;
    --plddt)       PLDDT="$2"; shift 2 ;;
    --smoke)       SMOKE=1; shift ;;
    --fg)          FOREGROUND=1; shift ;;
    -h|--help)     sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

[ -f "$BC_DIR/bindcraft.py" ] || { echo "BindCraft not installed. Run: bash $REPO/local/install.sh"; exit 1; }
[ -f "$SETTINGS" ] || { echo "No such settings file: $SETTINGS"; exit 1; }

# Render {{REPO}} / {{BC_ROOT}} placeholders into a real settings file.
RENDERED="$BC_ROOT/run_settings.json"
sed -e "s|{{REPO}}|$REPO|g" -e "s|{{BC_ROOT}}|$BC_ROOT|g" "$SETTINGS" > "$RENDERED"

STARTING_PDB=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['starting_pdb'])" "$RENDERED")
DESIGN_PATH=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['design_path'])" "$RENDERED")
# BindCraft only re-reads starting_pdb at the END of a trajectory, so a bad path
# costs a full trajectory before it errors. Check it up front instead.
[ -f "$STARTING_PDB" ] || { echo "starting_pdb does not exist: $STARTING_PDB"; exit 1; }
# PyRosetta cannot open a path containing a space, and fails deep into the run.
for p in "$STARTING_PDB" "$DESIGN_PATH" "$BC_DIR"; do
  case "$p" in *" "*) echo "Path contains a space, which PyRosetta cannot open: $p"; exit 1 ;; esac
done
mkdir -p "$DESIGN_PATH"

# Restore the pristine quality gate, then lower it only for smoke runs.
GATE_FILE="$BC_DIR/functions/colabdesign_utils.py"
[ -f "$GATE_FILE.orig" ] && cp -f "$GATE_FILE.orig" "$GATE_FILE"

if [ "$SMOKE" = 1 ]; then
  echo ">>> SMOKE MODE: iterations cut, quality gate dropped to 0.1, filters off."
  echo ">>> Designs from this run are meaningless. It only proves the pipeline runs."
  FILTERS="$BC_DIR/settings_filters/no_filters.json"
  ADVANCED="$BC_ROOT/advanced_smoke.json"
  python3 - "$BC_DIR/settings_advanced/peptide_3stage_multimer_mpnn.json" "$ADVANCED" <<'PY'
import json, sys
a = json.load(open(sys.argv[1]))
a.update(soft_iterations=8, temporary_iterations=5, hard_iterations=2,
         greedy_iterations=2, num_seqs=4, max_mpnn_sequences=1,
         save_design_animations=False, save_design_trajectory_plots=False)
json.dump(a, open(sys.argv[2], "w"), indent=4)
PY
  PLDDT="${PLDDT:-0.1}"
  python3 - "$RENDERED" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
s["number_of_final_designs"] = 1
json.dump(s, open(sys.argv[1], "w"), indent=4)
PY
fi

# The trajectory pLDDT gate is hardcoded in upstream, not exposed in the JSON,
# so it is patched in rather than passed. The restore above is what keeps this
# from compounding across runs.
if [ -n "$PLDDT" ]; then
  echo ">>> Trajectory pLDDT gate set to $PLDDT (stock is 0.65)."
  sed -i "s/plddt > 0\.65/plddt > $PLDDT/g" "$GATE_FILE"
fi

LOG="$DESIGN_PATH/run_$(date +%Y%m%d_%H%M%S).log"
CMD="cd '$BC_DIR' && python -u bindcraft.py -s '$RENDERED' -f '$FILTERS' -a '$ADVANCED' 2>&1 | tee '$LOG'"

echo "settings : $RENDERED"
echo "filters  : $FILTERS"
echo "advanced : $ADVANCED"
echo "target   : $STARTING_PDB"
echo "output   : $DESIGN_PATH"
echo "log      : $LOG"
echo

CONDA_BASE="$(conda info --base)"
# Activate by prefix, not by name: some images point envs_dirs away from
# $CONDA_BASE/envs, so a name lookup finds nothing. install.sh records the path.
ENV_PREFIX="$(cat "$BC_DIR/.env_prefix" 2>/dev/null || true)"
[ -n "$ENV_PREFIX" ] || ENV_PREFIX="$CONDA_BASE/envs/BindCraft"
[ -d "$ENV_PREFIX" ] || { echo "No BindCraft env at $ENV_PREFIX. Re-run install.sh"; exit 1; }
ACTIVATE=". '$CONDA_BASE/etc/profile.d/conda.sh' && conda activate '$ENV_PREFIX'"

if [ "$FOREGROUND" = 1 ]; then
  bash -lc "$ACTIVATE && $CMD"
else
  tmux kill-session -t bindcraft 2>/dev/null || true
  tmux new-session -d -s bindcraft "bash -lc \"$ACTIVATE && $CMD; echo; echo '[run finished - press a key]'; read\""
  echo "Started in tmux session 'bindcraft'."
  echo "  watch:    tmux attach -t bindcraft     (detach: ctrl-b then d)"
  echo "  tail log: tail -f '$LOG'"
fi
