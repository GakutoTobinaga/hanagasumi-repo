#!/bin/bash
cd /tmp/meshy
U=${GLB_DIR:-assets}
declare -A F=( [p3_bottom_left]="$U/Meshy_AI_hanagasumi_bottom_lef_1018013946_generate.glb" \
               [p4_bottom_right]="$U/Meshy_AI_hanagasumi_bottom_rig_1018013941_generate.glb" \
               [p5_fan]="$U/Meshy_AI_hanagasumi_fan_petal__1018013937_generate.glb" \
               [p6_top_right]="$U/Meshy_AI_top_right_petal_model_10180123453.glb" )
for k in p4_bottom_right p5_fan p6_top_right; do
  echo "[start $k] $(date +%T)" >> progress.log
  /tmp/bpyenv/bin/python load_arg.py -- "${F[$k]}" /tmp/meshy/$k.npz > $k.load.log 2>&1
  timeout 1200 /tmp/bpyenv/bin/python analyze3.py /tmp/meshy/$k.npz /tmp/meshy/analysis_$k.png > $k.log 2>&1
  rm -f /tmp/meshy/$k.npz
  echo "[done $k] $(date +%T)" >> progress.log
done
echo "[ALL DONE]" >> progress.log
