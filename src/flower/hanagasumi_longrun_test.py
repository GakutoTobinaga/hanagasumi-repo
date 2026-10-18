"""
hanagasumi_longrun_test.py -- 世代試験の延長（50世代）。設定E1（層の分離・開き角は自動決定・遺伝子ごとのK/突然変異）。
開き角は遺伝子の動きに影響しないので、探索を省略（derive_thetaを固定値に差し替え）して高速化。
12世代目の値が、前回のE1と一致するかも確認する（再現性の確認）。
実行: python hanagasumi_longrun_test.py -- <出力プレフィックス>
"""
import os, sys, json, math, numpy as np
full = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hanagasumi_breeding_test.py"), encoding="utf-8").read()
head = full.split("PA = dict(")[0]
for a, b in (("rng.normal(0, 0.03)", "rng.normal(0, 0.03*MUT)"), ("rng.normal(0, 0.015)", "rng.normal(0, 0.015*MUT)"), ("rng.normal(0, 0.05)", "rng.normal(0, 0.05*MUT)"),
             ("rng.normal(0, HUE_MUT)", "rng.normal(0, HUE_MUT*MUT)"), ("rng.normal(0, 0.04)", "rng.normal(0, 0.04*MUT)"), ("if rng.random() < 0.15:", "if rng.random() < 0.15*MUT:")):
    assert a in head, a; head = head.replace(a, b)
MUT = 1.0; exec(head)
derive_theta = lambda g: 50.0                       # 遺伝子の動きに影響しないので、探索を省略
src2 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hanagasumi_generations_test.py"), encoding="utf-8").read()
ns = src2.split("FOUNDERS = [")[1].split("]\nfor f in FOUNDERS")[0]
FOUNDERS = eval("[" + ns + "]")
def natural_size(petals):
    A = np.concatenate([place(TYPES[p["type"]]["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04) for p in petals])
    return float(np.hypot(A[:, 0], A[:, 1]).max()), float(A[:, 2].max())
for f in FOUNDERS:
    f["petals"] = make_flower2(f, np.random.default_rng(f["seed"])); f["radius"], f["height"] = natural_size(f["petals"])
TNAMES = ["t1", "t2", "t3", "t4", "t5", "t6"]
def circ(h):
    r = np.radians(h); C, S = np.cos(r).mean(), np.sin(r).mean(); R = math.hypot(C, S)
    return (math.degrees(math.atan2(S, C)) % 360), math.degrees(math.sqrt(max(-2 * math.log(max(R, 1e-9)), 0)))
def stats(pop):
    g = lambda f: np.array([f(x) for x in pop], float); hm, hs = circ(g(lambda x: x["col"][2])); tc = np.zeros(6)
    for x in pop:
        for t in (x["type_seq"] if "type_seq" in x else [p["type"] for p in x["petals"]]): tc[TNAMES.index(t)] += 1
    pr = tc / tc.sum(); eff = math.exp(-(pr[pr > 0] * np.log(pr[pr > 0])).sum())
    return {"az_jit": g(lambda x: x["az_jit"]).std(), "L": g(lambda x: x["col"][0]).std(), "C_rel": g(lambda x: x["col"][1]).std(), "hue(deg)": hs,
            "grad強さ": g(lambda x: x["grad"][1] if x["grad"][0] else 0).std(), "radius": g(lambda x: x["radius"]).std(), "height": g(lambda x: x["height"]).std(), "N": g(lambda x: x["N"]).std(),
            "_layers2": float(np.mean(g(lambda x: x["layers"]) == 2)), "_eff_types": eff, "_radius_mean": g(lambda x: x["radius"]).mean(), "_height_mean": g(lambda x: x["height"]).mean(), "_strength_mean": g(lambda x: x["grad"][1] if x["grad"][0] else 0).mean()}
def next_gen(pop, rng, gen, n=60):
    out = []
    for i in range(n):
        a, b = rng.choice(len(pop), 2, replace=False); c = breed(pop[a], pop[b], rng, f"g{gen}_{i}"); c["petals"] = [{"type": t} for t in c["type_seq"]]; out.append(c)
    return out
GENS = 50; REPS = 5; SHOW = (0, 12, 30, 50); LAYER_FIX = True; SPREAD_K = 0.45; DERIVE_THETA = True
CONFIGS = [("基準(型変異0%, 色相σ8度)", dict(TYPE_MUT=0.0, HUE_MUT=8)), ("F1 型変異4%, 色相σ12度", dict(TYPE_MUT=0.04, HUE_MUT=12)), ("F2 型変異6%, 色相σ16度", dict(TYPE_MUT=0.06, HUE_MUT=16))]
keys = ["az_jit", "L", "C_rel", "hue(deg)", "grad強さ", "radius", "height", "N"]; summary = {}
for label, prm in CONFIGS:
    TYPE_MUT = prm["TYPE_MUT"]; HUE_MUT = prm["HUE_MUT"]; allr = {gk: [] for gk in range(GENS + 1)}
    for rep in range(REPS):
        rng = np.random.default_rng(1000 + rep); pop = [dict(f) for f in FOUNDERS for _ in range(10)]
        for gen in range(GENS + 1):
            allr[gen].append(stats(pop))
            if gen < GENS: pop = next_gen(pop, rng, gen + 1)
    mean = {gk: {k: float(np.mean([r[k] for r in v])) for k in v[0]} for gk, v in allr.items()}; summary[label] = {str(g): mean[g] for g in SHOW}
    print("=== %s" % label); print("%-5s" % "世代" + " ".join("%9s" % k for k in keys) + " | 層2割合 型有効数")
    for gk in SHOW: print("%-5d" % gk + " ".join("%9.2f" % (mean[gk][k] / mean[0][k]) for k in keys) + " |  %.2f   %.1f" % (mean[gk]["_layers2"], mean[gk]["_eff_types"]))
    r50 = [r["hue(deg)"] / mean[0]["hue(deg)"] for r in allr[50]]; print("  色相SD比の50世代目: 平均%.2f 最小%.2f 最大%.2f | 色相SD(度) 0→50世代: %.0f→%.0f" % (np.mean(r50), min(r50), max(r50), mean[0]["hue(deg)"], mean[50]["hue(deg)"]))
    sys.stdout.flush()
json.dump(summary, open(OUT + "_longrun2.json", "w"), ensure_ascii=False, indent=1)
