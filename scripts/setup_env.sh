#!/bin/bash
# Python 3.11 + bpy 4.5.0（PyPIのモジュール版Blender）を、/tmp/bpyenv に作る。
# 動作確認した環境: Ubuntu 24（標準Pythonは3.12で、bpy 4.5.0のホイールがないため、uvで3.11を用意する）
set -e
cd "$(dirname "$0")/.."
pip install --user uv >/dev/null 2>&1 || pip install uv
export PATH="$PATH:$HOME/.local/bin"
uv python install 3.11
uv venv --python 3.11 /tmp/bpyenv
uv pip install --python /tmp/bpyenv/bin/python -r requirements.txt
mkdir -p /tmp/meshy
/tmp/bpyenv/bin/python -c "import bpy; print('bpy', bpy.app.version_string)"
