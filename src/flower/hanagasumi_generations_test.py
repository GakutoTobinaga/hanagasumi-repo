"""
hanagasumi_generations_test.py -- 世代を重ねた交配の試験（選別なしのランダム交配）。
始祖6個体（F1〜F6）を10個体ずつ→60個体。毎世代、ランダムに2親を選んで60個体を作る。12世代、5回繰り返し。
突然変異の大きさ(MUT=0,1,2倍)を変えて、各遺伝子のばらつき（SD）が、どう変わるかを測る。
最後に、MUT=1・1回目の12世代目から8個体を描画する。
実行: python hanagasumi_generations_test.py -- <出力プレフィックス>
"""
import os, sys, json, math, numpy as np
BREED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hanagasumi_breeding_test.py")
full = open(BREED, encoding="utf-8").read()
head = full.split("PA = dict(")[0]
for a, b in (("rng.normal(0, 0.03)", "rng.normal(0, 0.03*MUT)"), ("rng.normal(0, 0.015)", "rng.normal(0, 0.015*MUT)"), ("rng.normal(0, 0.05)", "rng.normal(0, 0.05*MUT)"),
             ("rng.normal(0, 8)", "rng.normal(0, 8*MUT)"), ("rng.normal(0, 0.04)", "rng.normal(0, 0.04*MUT)"), ("if rng.random() < 0.15:", "if rng.random() < 0.15*MUT:")):
    assert a in head, a; head = head.replace(a, b)
MUT = 1.0
exec(head)                                                  # breed, make_flower2, place, TYPES, OUT ...
def natural_size(petals):
    A = np.concatenate([place(TYPES[p["type"]]["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04) for p in petals])
    return float(np.hypot(A[:, 0], A[:, 1]).max()), float(A[:, 2].max())
FOUNDERS = [
 dict(name="F1", N=6,  layers=1, theta=30, az_jit=0.05, types=["t5"],                          order="alternate", col=(0.72,0.35,300), grad=(1,0.8,0.5,0.35), seed=1),
 dict(name="F2", N=8,  layers=1, theta=55, az_jit=0.10, types=["t1","t2"],                     order="alternate", col=(0.72,0.35,300), grad=(0,0,0,0),         seed=2),
 dict(name="F3", N=10, layers=2, theta=45, az_jit=0.15, types=["t3","t4","t6"],                order="spiral",    col=(0.80,0.45,350), grad=(1,0.6,0.5,0.3),   seed=3),
 dict(name="F4", N=7,  layers=1, theta=75, az_jit=0.10, types=["t1","t5","t6"],                order="alternate", col=(0.78,0.55,40),  grad=(1,0.7,0.5,0.3),   seed=4),
 dict(name="F5", N=9,  layers=2, theta=60, az_jit=0.10, types=["t1","t2","t3","t4","t5","t6"], order="spiral",    col=(0.70,0.40,255), grad=(1,0.9,0.45,0.3),  seed=5),
 dict(name="F6", N=6,  layers=1, theta=20, az_jit=0.05, types=["t2","t3"],                     order="spiral",    col=(0.88,0.45,95),  grad=(1,0.5,0.5,0.3),   seed=6)]
for f in FOUNDERS:
    f["petals"] = make_flower2(f, np.random.default_rng(f["seed"])); f["radius"], f["height"] = natural_size(f["petals"])
TNAMES = ["t1", "t2", "t3", "t4", "t5", "t6"]
def circ(h):                                                # 色相の円周平均とSD（度）
    r = np.radians(h); C, S = np.cos(r).mean(), np.sin(r).mean(); R = math.hypot(C, S)
    return (math.degrees(math.atan2(S, C)) % 360), math.degrees(math.sqrt(max(-2 * math.log(max(R, 1e-9)), 0)))
def stats(pop):
    g = lambda f: np.array([f(x) for x in pop], float)
    hm, hs = circ(g(lambda x: x["col"][2]))
    tc = np.zeros(6)
    for x in pop:
        for t in (x["type_seq"] if "type_seq" in x else [p["type"] for p in x["petals"]]): tc[TNAMES.index(t)] += 1
    pr = tc / tc.sum(); eff = math.exp(-(pr[pr > 0] * np.log(pr[pr > 0])).sum())
    return {"theta": g(lambda x: x["theta"]).std(), "az_jit": g(lambda x: x["az_jit"]).std(), "L": g(lambda x: x["col"][0]).std(), "C_rel": g(lambda x: x["col"][1]).std(),
            "hue(deg)": hs, "grad強さ": g(lambda x: x["grad"][1] if x["grad"][0] else 0).std(), "radius": g(lambda x: x["radius"]).std(), "height": g(lambda x: x["height"]).std(),
            "N": g(lambda x: x["N"]).std(), "_layers2": float(np.mean(g(lambda x: x["layers"]) == 2)), "_spiral": float(np.mean([x["order"] == "spiral" for x in pop])), "_eff_types": eff,
            "_hue_mean": hm, "_N_mean": g(lambda x: x["N"]).mean()}
def next_gen(pop, rng, gen, n=60):
    out = []
    for i in range(n):
        a, b = rng.choice(len(pop), 2, replace=False); c = breed(pop[a], pop[b], rng, f"g{gen}_{i}")
        c["petals"] = [{"type": t} for t in c["type_seq"]]; out.append(c)
    return out
GENS = 12; REPS = 5; SHOW = (0, 1, 2, 4, 8, 12); results = {}; dist_res = {}; keep = None
CONFIGS = [("E0 開き角=遺伝子のまま", False), ("E1 開き角=自動決定", True)]
CHOSEN = "E1 開き角=自動決定"; MUT = 1.0; LAYER_FIX = True; SPREAD_K = 0.45
def distortions(pop):                       # 花全体の縦横の拡縮比（1に近いほど歪みがない）
    out = []
    for c in pop:
        if "seed" not in c: continue
        r0, h0 = natural_size(make_flower2(c, np.random.default_rng(c["seed"]))); out.append((c["height"] / h0) / (c["radius"] / r0))
    return out
for label, derive in CONFIGS:
    DERIVE_THETA = derive; acc = {gk: [] for gk in SHOW}; dl = []; sat = []
    for rep in range(REPS):
        rng = np.random.default_rng(1000 + rep); pop = [dict(f) for f in FOUNDERS for _ in range(10)]
        for gen in range(GENS + 1):
            if gen in acc: acc[gen].append(stats(pop))
            if gen == GENS: dl += distortions(pop); sat += [c["theta"] <= 16 or c["theta"] >= 84 for c in pop]
            if gen < GENS: pop = next_gen(pop, rng, gen + 1)
        if label == CHOSEN and rep == 0: keep = pop
    results[label] = {gk: {k: float(np.mean([r[k] for r in v])) for k in v[0]} for gk, v in acc.items()}
    dl = np.array(dl); dist_res[label] = dict(p5=float(np.percentile(dl, 5)), p50=float(np.percentile(dl, 50)), p95=float(np.percentile(dl, 95)), outside=float(np.mean((dl < 0.85) | (dl > 1.20))), theta_saturated=float(np.mean(sat)))
keys = ["theta", "az_jit", "L", "C_rel", "hue(deg)", "grad強さ", "radius", "height", "N"]
print("=== 12世代目/0世代目のSD比（5回の平均）。参考: 前回の設定D(開き角=遺伝子, 全遺伝子K=0.45): theta .61 az 1.95 L 1.09 C_rel 1.92 hue .63 grad .62 radius .57 height .68 N .56")
print("%-22s" % "設定" + " ".join("%8s" % k for k in keys) + " | 層2割合 型有効数")
for label in results:
    r0, r12 = results[label][0], results[label][12]
    print("%-22s" % label + " ".join("%8.2f" % (r12[k] / r0[k]) for k in keys) + " |  %.2f→%.2f  %.1f→%.1f" % (r0["_layers2"], r12["_layers2"], r0["_eff_types"], r12["_eff_types"]))
print("=== 12世代目の花の歪み（縦拡縮/横拡縮、1=歪みなし。検証済みの範囲は0.85〜1.20）")
for label, d in dist_res.items(): print("%-22s 5/50/95%%点 %.2f/%.2f/%.2f | 範囲外 %.0f%% | 開き角が下限/上限(15,85度付近)に張り付いた割合 %.0f%%" % (label, d["p5"], d["p50"], d["p95"], d["outside"] * 100, d["theta_saturated"] * 100))
json.dump(dict(sd=results, distortion=dist_res), open(OUT + "_generations3.json", "w"), ensure_ascii=False, indent=1)
sys.stdout.flush()
# ---- 12世代目（MUT=1, 1回目）から8個体を描画
rng = np.random.default_rng(5); idx = rng.choice(len(keep), 8, replace=False)
cells = []
for k, i in enumerate(idx):
    g = {kk: v for kk, v in keep[i].items() if kk != "petals"}; g["name"] = f"G12-{k+1}"; cells.append((g, k % 4, k // 4))
tail = "bpy.ops.wm.read_factory_settings" + full.split("bpy.ops.wm.read_factory_settings", 1)[1]
exec(tail)
