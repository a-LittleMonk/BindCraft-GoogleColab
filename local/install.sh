#!/usr/bin/env bash
# Install BindCraft on a fresh Linux GPU box (tested target: vast.ai).
# Idempotent: re-running after a completed install does nothing.
#
#   bash install.sh              # auto-detect CUDA from nvidia-smi
#   BC_CUDA=12.4 bash install.sh # force a CUDA version
#   BC_ROOT=/data bash install.sh
set -euo pipefail

BC_ROOT="${BC_ROOT:-/workspace}"
BC_DIR="$BC_ROOT/bindcraft"
MARKER="$BC_DIR/.install_complete"

if [ -f "$MARKER" ]; then
  echo "BindCraft already installed at $BC_DIR (remove $MARKER to force)."
  exit 0
fi

echo "=== 0/5 system packages ==="
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git wget curl tmux rsync bzip2 ca-certificates
fi

echo "=== 1/5 conda ==="
if ! command -v conda >/dev/null 2>&1; then
  for c in /opt/conda /opt/miniforge3 "$HOME/miniforge3" "$HOME/miniconda3"; do
    [ -f "$c/etc/profile.d/conda.sh" ] && . "$c/etc/profile.d/conda.sh" && break
  done
fi
if ! command -v conda >/dev/null 2>&1; then
  echo "Installing Miniforge to $HOME/miniforge3"
  wget -q -O /tmp/miniforge.sh \
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
  bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"
  rm -f /tmp/miniforge.sh
  . "$HOME/miniforge3/etc/profile.d/conda.sh"
  "$HOME/miniforge3/bin/conda" init bash >/dev/null
fi
CONDA_BASE="$(conda info --base)"
. "$CONDA_BASE/etc/profile.d/conda.sh"
echo "conda at $CONDA_BASE"

# Upstream's installer creates the env with --name but then activates the
# hardcoded path $CONDA_BASE/envs/BindCraft. Some images (vast.ai's, for one)
# point envs_dirs somewhere else entirely, so the env lands outside that path
# and the activation fails. Force envs_dirs back for the duration of the install.
ENV_PREFIX="$CONDA_BASE/envs/BindCraft"
# Only CONDA_ENVS_DIRS: mamba aborts if the legacy CONDA_ENVS_PATH is set too.
export CONDA_ENVS_DIRS="$CONDA_BASE/envs"
unset CONDA_ENVS_PATH
mkdir -p "$CONDA_BASE/envs"

# Drop any half-built BindCraft env from an earlier attempt, wherever it landed.
while read -r stale; do
  [ -n "$stale" ] && [ "$stale" != "$ENV_PREFIX" ] && [ -d "$stale" ] && {
    echo "Removing stale env at $stale"; rm -rf "$stale"; }
done < <(conda env list 2>/dev/null | awk '{print $NF}' | grep -E '/BindCraft$' || true)

# Upstream's installer wants mamba or conda; mamba is much faster when present.
PKG_MANAGER=conda
command -v mamba >/dev/null 2>&1 && PKG_MANAGER=mamba

echo "=== 2/5 CUDA detection ==="
CUDA="${BC_CUDA:-}"
if [ -z "$CUDA" ] && command -v nvidia-smi >/dev/null 2>&1; then
  # nvidia-smi's header reports the driver's maximum supported CUDA, e.g. "12.4"
  CUDA="$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: *\([0-9.]*\).*/\1/p' | head -1)"
fi
if [ -z "$CUDA" ]; then
  echo "WARNING: no GPU / CUDA detected. Installing CPU build - fine for a dry run, useless for real designs."
else
  echo "CUDA $CUDA"
fi

echo "=== 3/5 upstream BindCraft ==="
mkdir -p "$BC_ROOT"
if [ -d "$BC_DIR/.git" ]; then
  git -C "$BC_DIR" pull --ff-only
else
  git clone https://github.com/martinpacesa/BindCraft "$BC_DIR"
fi

echo "=== 4/5 environment + AF2 weights (slow: 15-40 min) ==="
cd "$BC_DIR"
chmod +x install_bindcraft.sh
if [ -n "$CUDA" ]; then
  ./install_bindcraft.sh --pkg_manager "$PKG_MANAGER" --cuda "$CUDA"
else
  ./install_bindcraft.sh --pkg_manager "$PKG_MANAGER"
fi

echo "=== 5/5 verifying ==="
conda activate "$ENV_PREFIX"
# Record the prefix so run.sh activates by path and never depends on envs_dirs.
echo "$ENV_PREFIX" > "$BC_DIR/.env_prefix"
python - <<'PY'
import jax
print("jax", jax.__version__, "devices:", jax.devices())
import colabdesign, pyrosetta  # noqa: F401
print("colabdesign + pyrosetta import OK")
PY
[ -f "$BC_DIR/params/params_model_5_ptm.npz" ] || { echo "Error: AF2 weights missing"; exit 1; }

# Keep a pristine copy so the smoke-test patch in run.sh never compounds.
cp -n "$BC_DIR/functions/colabdesign_utils.py" "$BC_DIR/functions/colabdesign_utils.py.orig"

touch "$MARKER"
echo
echo "Done. BindCraft is at $BC_DIR, env at $ENV_PREFIX"
echo "Next:  bash run.sh --smoke"
