#!/bin/bash
cd /tmp/meshy; U=${GLB_DIR:-assets}; : > lr.jsonl
python_=/tmp/bpyenv/bin/python
for spec in "1_image-to-3d|/tmp/meshy/petal.npz|" "2_wavy|/tmp/meshy/petal2.npz|" \
  "3_bottom_left||$U/Meshy_AI_hanagasumi_bottom_lef_1018013946_generate.glb" \
  "4_bottom_right||$U/Meshy_AI_hanagasumi_bottom_rig_1018013941_generate.glb" \
  "5_fan||$U/Meshy_AI_hanagasumi_fan_petal__1018013937_generate.glb" \
  "6_top_right||$U/Meshy_AI_top_right_petal_model_10180123453.glb"; do
  IFS='|' read -r label npz glb <<< "$spec"
  if [ -z "$npz" ]; then npz=/tmp/meshy/lr_tmp.npz; $python_ load_arg.py -- "$glb" $npz > /dev/null 2>&1; fi
  $python_ analyze_lr.py $npz "$label" >> lr.jsonl 2>> lr.err
  [ "$npz" = "/tmp/meshy/lr_tmp.npz" ] && rm -f $npz
  echo "[done $label] $(date +%T)" >> lr.progress
done
echo "[ALL DONE]" >> lr.progress
