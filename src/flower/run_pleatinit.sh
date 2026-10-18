#!/bin/bash
mkdir -p /tmp/run13; cd /tmp/run13
for amp in 0 0.03 0.06; do
  echo "[start amp=$amp] $(date +%T)" >> prog.log
  timeout 1500 /tmp/bpyenv/bin/python $(dirname "$0")/../cloth/verify_cloth_growth.py -- --selfcol --outline fan --h 0.014 --frames 120 --ramp 80 --growth 0.4 --bending 0.05 0.5 --curl 0.1 --tip-curl 0.3 --pleat-init-amp $amp --pleat-init-freq 15 --out /tmp/run13/amp$amp > amp$amp.log 2>&1
  echo "[done amp=$amp] $(date +%T)" >> prog.log
done
echo "[ALL DONE]" >> prog.log
