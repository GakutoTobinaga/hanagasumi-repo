"""
hanagasumi_layer_mut_test.py -- 層・並べ方の突然変異の率を比べる試験。
hanagasumi_selection_test.py の4つの狙いで、20世代選別したあと、選別をやめて20世代進める。
選別中に層・並べ方が片方に固定されるか、選別をやめたあとに戻るか、選別の効きが落ちないかを見る。
実行: python hanagasumi_layer_mut_test.py -- <出力プレフィックス> <率>   （率は LAYER_MUT と ORDER_MUT の両方に使う）
"""
import os, sys, json, numpy as np
sel = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hanagasumi_selection_test.py"), encoding="utf-8").read()
exec(sel.split("GENS = 20;")[0])                     # breed、FOUNDERS、TARGETS、select などを読み込む
RATE = float(sys.argv[-1]); LAYER_MUT = ORDER_MUT = RATE
SEL_GENS = 20; FREE_GENS = 20; REPS = 5; SHOW = (0, 5, 20, 25, 30, 40); KS = (12, 2)
def layer_order(pop):
    return float(np.mean([x["layers"] == 2 for x in pop])), float(np.mean([x["order"] == "spiral" for x in pop]))
runs = [("選別なし", None, None, 60)] + [(label, score, metric, k) for label, score, metric, _ in TARGETS for k in KS]
summary = {}
print("率 %.2f: 層2の割合 / らせんの割合（5回平均）。選別は%d世代目まで、その後は選別なし。 [固定]=5回中、その世代で0か1の回数" % (RATE, SEL_GENS))
for label, score, metric, k in runs:
    rows = {g: [] for g in SHOW}; tg = []
    for rep in range(REPS):
        rng = np.random.default_rng(3000 + rep); pop = [dict(f) for f in FOUNDERS for _ in range(10)]
        for gen in range(SEL_GENS + FREE_GENS + 1):
            if gen in rows: rows[gen].append(layer_order(pop))
            if gen == SEL_GENS and metric: tg.append(metric(pop))
            if gen < SEL_GENS + FREE_GENS:
                pop = next_gen(select(pop, score, k, rng) if (score and gen < SEL_GENS) else pop, rng, gen + 1)
    key = "%s k=%d" % (label, k); summary[key] = {"target_at_%d" % SEL_GENS: float(np.mean(tg)) if tg else None}
    line = "%-26s" % key + ("狙い%6.2f |" % np.mean(tg) if tg else "%11s|" % "")
    for g in SHOW:
        L = np.array([r[0] for r in rows[g]]); O = np.array([r[1] for r in rows[g]])
        fixL = int(np.sum((L == 0) | (L == 1))); fixO = int(np.sum((O == 0) | (O == 1)))
        summary[key][str(g)] = dict(layers2=float(L.mean()), spiral=float(O.mean()), fixed_layers=fixL, fixed_order=fixO)
        line += " g%-2d %.2f/%.2f[%d/%d]" % (g, L.mean(), O.mean(), fixL, fixO)
    print(line); sys.stdout.flush()
json.dump(summary, open(OUT + "_layermut_%s.json" % ("%.2f" % RATE).replace(".", ""), "w"), ensure_ascii=False, indent=1)
