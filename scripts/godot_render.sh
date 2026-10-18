#!/bin/bash
# Godot（4.4.1、Forward+）で花を描画する試験。GPUなしの環境では、Xvfb と lavapipe（ソフトウェアVulkan）で動く。
# 前提: setup_env.sh と load_all_glb.sh を実行済み（/tmp/meshy/dec_t*.npz）。出力: $OUT_DIR/godot_F3_*.png（既定 /tmp/godot）
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"; GD=/tmp/godot/Godot_v4.4.1-stable_linux.x86_64; export OUT_DIR="${OUT_DIR:-/tmp/godot}"
mkdir -p /tmp/godot "$OUT_DIR"
if [ ! -x "$GD" ]; then
  curl -sSL -o /tmp/godot/g.zip https://github.com/godotengine/godot/releases/download/4.4.1-stable/Godot_v4.4.1-stable_linux.x86_64.zip
  /tmp/bpyenv/bin/python -c "import zipfile; zipfile.ZipFile('/tmp/godot/g.zip').extractall('/tmp/godot')"; chmod +x "$GD"
fi
if ! ls /usr/share/vulkan/icd.d/lvp_icd* >/dev/null 2>&1; then (apt-get install -y mesa-vulkan-drivers xvfb || (apt-get update && apt-get install -y mesa-vulkan-drivers xvfb)) >/dev/null; fi
/tmp/bpyenv/bin/python "$SRC/src/flower/export_flower_gltf.py" -- "$SRC/godot/F3.glb" F3
xvfb-run -a -s "-screen 0 1280x1024x24" "$GD" --path "$SRC/godot" --rendering-driver vulkan --script flower.gd
