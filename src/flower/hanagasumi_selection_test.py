"""
hanagasumi_selection_test.py -- 選別ありの世代試験（プレイヤーが親を選ぶ想定）。
交配ルール・始祖・統計は hanagasumi_longrun_test.py と同じ（設定F2: 型変異6%、色相σ16度）。
各世代60個体のうち、狙いに近い上位k個体だけを親にして、ランダムなペアから次の60個体を作る。
k=12（上位20%、ゆるい選別）と k=2（毎世代1組、強い選別）を比べる。
見るもの: 狙った形質が寄るか（速さ・到達点）、他の遺伝子のばらつき・型の多様性・層が崩れないか。
実行: python hanagasumi_selection_test.py -- <出力プレフィックス>
"""
import os, sys, json, math, numpy as np
lr = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hanagasumi_longrun_test.py"), encoding="utf-8").read()
exec(lr.split("GENS = 50;")[0])                      # breed、FOUNDERS、stats などを読み込む（試験の本体は実行しない）
LAYER_FIX = True; SPREAD_K = 0.45; DERIVE_THETA = True; TYPE_MUT = 0.06; HUE_MUT = 16
hue_dist = lambda h, t: abs(((h - t + 180) % 360) - 180)
TARGETS = [  # (ラベル, スコア関数: 大きいほど狙いに近い, 狙いの指標)
    ("色相300度(範囲内)", lambda x: -hue_dist(x["col"][2], 300), lambda pop: float(np.mean([hue_dist(x["col"][2], 300) for x in pop])), "300度からの距離(度)"),
    ("色相180度(始祖にない)", lambda x: -hue_dist(x["col"][2], 180), lambda pop: float(np.mean([hue_dist(x["col"][2], 180) for x in pop])), "180度からの距離(度)"),
    ("半径が大きい", lambda x: x["radius"], lambda pop: float(np.mean([x["radius"] for x in pop])), "半径の平均"),
    ("枚数10", lambda x: x["N"], lambda pop: float(np.mean([x["N"] for x in pop])), "枚数の平均")]
def select(pop, score, k, rng):
    s = np.array([score(x) for x in pop]) + rng.normal(0, 1e-9, len(pop))      # 同点はランダムに
    return [pop[i] for i in np.argsort(-s)[:k]]
GENS = 20; REPS = 5; SHOW = (0, 1, 3, 5, 10, 20); KS = (60, 12, 2)            # k=60 は選別なし（対照）
keys = ["az_jit", "L", "C_rel", "hue(deg)", "grad強さ", "radius", "height", "N"]; summary = {}
for label, score, metric, mname in TARGETS:
    summary[label] = {}
    for k in KS:
        allr = {g: [] for g in range(GENS + 1)}; met = {g: [] for g in range(GENS + 1)}
        for rep in range(REPS):
            rng = np.random.default_rng(2000 + rep); pop = [dict(f) for f in FOUNDERS for _ in range(10)]
            for gen in range(GENS + 1):
                allr[gen].append(stats(pop)); met[gen].append(metric(pop))
                if gen < GENS: pop = next_gen(select(pop, score, k, rng) if k < len(pop) else pop, rng, gen + 1)
        mean = {g: {kk: float(np.mean([r[kk] for r in v])) for kk in v[0]} for g, v in allr.items()}
        summary[label]["k=%d" % k] = {str(g): dict(mean[g], target=float(np.mean(met[g])), target_min=float(np.min(met[g])), target_max=float(np.max(met[g]))) for g in SHOW}
        print("=== %s  k=%d%s  狙いの指標: %s" % (label, k, "(選別なし)" if k == 60 else "", mname))
        print("%-4s %8s |" % ("世代", "狙い") + " ".join("%8s" % kk for kk in keys) + " | 層2割合 型有効数 半径平均 高さ平均")
        for g in SHOW:
            print("%-4d %8.2f |" % (g, np.mean(met[g])) + " ".join("%8.2f" % (mean[g][kk] / mean[0][kk]) for kk in keys)
                  + " |  %.2f    %.1f    %.2f    %.2f" % (mean[g]["_layers2"], mean[g]["_eff_types"], mean[g]["_radius_mean"], mean[g]["_height_mean"]))
        sys.stdout.flush()
json.dump(summary, open(OUT + "_selection.json", "w"), ensure_ascii=False, indent=1)
