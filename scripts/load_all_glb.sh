#!/bin/bash
# assets/ のGLB6枚を読み込み、/tmp/meshy/t1..t6.npz を作り、型の下処理（付け根を原点、長さ1、約5万面）を行う。
# GLB_DIR で、GLBのあるフォルダを指定できる（既定: assets）。
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"; GLB_DIR="${GLB_DIR:-$SRC/assets}"; PY=/tmp/bpyenv/bin/python
mkdir -p /tmp/meshy
declare -A F=(
 [t1]="Meshy_AI_flower_petal_model_1018011222_image-to-3d-texture.glb"
 [t2]="Meshy_AI_wavy_petal_model_1018011754_generate.glb"
 [t3]="Meshy_AI_hanagasumi_bottom_lef_1018013946_generate.glb"
 [t4]="Meshy_AI_hanagasumi_bottom_rig_1018013941_generate.glb"
 [t5]="Meshy_AI_hanagasumi_fan_petal__1018013937_generate.glb"
 [t6]="Meshy_AI_top_right_petal_model_10180123453.glb" )
for t in t1 t2 t3 t4 t5 t6; do
  echo "loading $t: ${F[$t]}"; $PY "$SRC/src/analysis/load_arg.py" -- "$GLB_DIR/${F[$t]}" /tmp/meshy/$t.npz > /dev/null 2>&1
done
$PY "$SRC/src/flower/prep_types.py"
