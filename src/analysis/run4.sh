#!/bin/bash
cd /tmp/meshy; : > progress4.log
for k in t5 t4 t6 t1; do
  echo "[start $k] $(date +%T)" >> progress4.log
  timeout 1200 /tmp/bpyenv/bin/python analyze4.py /tmp/meshy/$k.npz /tmp/meshy/analysis4_$k.png > a4_$k.log 2>&1
  echo "[done $k] $(date +%T)" >> progress4.log
done
echo "[ALL DONE]" >> progress4.log
