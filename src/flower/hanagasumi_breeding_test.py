"""
hanagasumi_breeding_test.py -- 交配の試験。親2つ(F2, F3)から、仕様書(v0.1.x)の交配ルールで子を作り、描画する。
hanagasumi_flower_proto.py の関数部（OKLCH・配置・色）を再利用する。
実行: python hanagasumi_breeding_test.py -- <出力プレフィックス>
"""
import sys, math, json, numpy as np, bpy
from mathutils import Vector
import os
HERE = os.path.dirname(os.path.abspath(__file__))     # 同じフォルダのスクリプトを参照する
PROTO = os.path.join(HERE, "hanagasumi_flower_proto.py")
SPREAD_K = 0.45     # 子のばらつき: 親どうしの差に比例したノイズの係数（平均で混ぜると世代ごとにばらつきが減るのを防ぐ）
LAYER_FIX = True    # True: 層の遺伝子を枚数から切り離す（見た目だけ、枚数8未満なら1層）
DERIVE_THETA = True # True: 開き角は遺伝子にせず、半径と高さの比に合うように自動で決める（花全体の歪みを避ける）
KSCALE = dict(az=0.45, C=0.45, L=0.7, hue=1.0)
HUE_MUT = 16       # 色相の突然変異の大きさ（度）。8度だと、50世代で色相のSDが0.34倍に減った
TYPE_MUT = 0.06    # 花びら1枚ごとに、別の型に置き換える確率（0だと、50世代で型の有効数が5.7から3.3に減った）
LAYER_MUT = 0.03   # 層（1⇔2）を反転する確率。0だと、選別の巻き添えで片方に固定されて戻らなかった（選別ありの8条件中7条件）
ORDER_MUT = 0.03   # 並べ方（らせん⇔交互）を反転する確率。層と同じ理由
ALL_TYPES = ["t1", "t2", "t3", "t4", "t5", "t6"]   # 遺伝子ごとのKの倍率（SPREAD_Kにかける）。突然変異が相対的に大きい遺伝子は、Kを小さくする
exec(open(PROTO, encoding="utf-8").read().split("FLOWERS = [")[0])      # TYPES, oklch, petal_colors, place, make_flower, OUT

def make_flower2(g, rng):
    """make_flower と同じだが、型の並び(type_seq)を指定できる"""
    N = g["N"]; layers = g["layers"] if N >= 8 else 1; th0 = math.radians(g["theta"]); petals = []
    n_out = N // 2 if layers == 2 else 0; groups = [(N - n_out, th0, 0.0)] + ([(n_out, th0 + math.radians(15), 0.5)] if n_out else [])
    k = 0
    for cnt, th, off in groups:
        step = 2 * math.pi / cnt
        for i in range(cnt):
            phi = (i + off) * step + g["az_jit"] * step * rng.uniform(-1, 1)
            theta = th + math.radians(rng.uniform(-10, 10)); roll0 = math.radians(8)
            roll = roll0 * (k / max(N - 1, 1)) * 2 if g["order"] == "spiral" else roll0 * (1 if k % 2 == 0 else -1)
            roll += math.radians(rng.uniform(-5, 5)); scale = 1 + rng.uniform(-0.10, 0.10)
            tname = g["type_seq"][k] if "type_seq" in g else g["types"][rng.integers(len(g["types"]))]; k += 1
            petals.append(dict(type=tname, phi=phi, theta=theta, roll=roll, scale=scale))
    return petals

def hue_mix(H1, H2, alpha):               # alpha = 親1の重み。色相環の短い弧に沿って補間
    d = ((H2 - H1 + 180) % 360) - 180; return (H1 + (1 - alpha) * d) % 360
def derive_theta(g):
    """高さ/半径の比に、花の自然な縦横比が合う開き角を探す。合えば、半径・高さに合わせる拡縮が等方的になり、歪まない。"""
    target = g["height"] / g["radius"]
    def asp(th):
        gg = dict(g); gg["theta"] = th
        A = np.concatenate([place(TYPES[p["type"]]["V"][::8], p["theta"], p["phi"], p["roll"], p["scale"], 0.04) for p in make_flower2(gg, np.random.default_rng(g["seed"]))])
        return A[:, 2].max() / np.hypot(A[:, 0], A[:, 1]).max()
    grid = np.linspace(15, 85, 8); vals = np.array([asp(t) for t in grid]); o = np.argsort(vals)
    return float(np.interp(target, vals[o], grid[o]))

def breed(A, B, rng, name):
    alpha = rng.uniform(0.2, 0.8); mix = lambda a, b, k=None: alpha * a + (1 - alpha) * b + rng.normal(0, 1) * (SPREAD_K if k is None else k) * abs(a - b)
    N = int(rng.choice([A["N"], B["N"], round((A["N"] + B["N"]) / 2)]))
    if rng.random() < 0.15: N += int(rng.choice([-1, 1]))
    N = int(np.clip(N, 6, 10)); layers = int(rng.choice([A["layers"], B["layers"]]))
    if LAYER_MUT > 0 and rng.random() < LAYER_MUT: layers = 3 - layers                                    # 層の突然変異
    if not LAYER_FIX and N < 8: layers = 1
    theta = None if DERIVE_THETA else float(np.clip(mix(A["theta"], B["theta"]) + rng.normal(0, 5), 20, 80))
    az = float(np.clip(mix(A["az_jit"], B["az_jit"], SPREAD_K * KSCALE["az"]) + rng.normal(0, 0.015), 0, 0.25))
    order = str(rng.choice([A["order"], B["order"]]))
    if ORDER_MUT > 0 and rng.random() < ORDER_MUT: order = "alternate" if order == "spiral" else "spiral"    # 並べ方の突然変異
    LA, CA, HA = A["col"]; LB, CB, HB = B["col"]
    if CA < 0.05: H = HB
    elif CB < 0.05: H = HA
    else: H = (hue_mix(HA, HB, alpha) + rng.normal(0, 1) * SPREAD_K * KSCALE["hue"] * abs(((HB - HA + 180) % 360) - 180)) % 360
    col = (float(np.clip(mix(LA, LB, SPREAD_K * KSCALE["L"]) + rng.normal(0, 0.03), 0.5, 0.95)), float(np.clip(mix(CA, CB, SPREAD_K * KSCALE["C"]) + rng.normal(0, 0.03), 0.1, 0.9)), float((H + rng.normal(0, HUE_MUT)) % 360))
    gA, gB = A["grad"], B["grad"]
    sA = gA[1] if gA[0] else 0.0; sB = gB[1] if gB[0] else 0.0                    # グラデのない親は強さ0として扱う
    st = float(np.clip(mix(sA, sB) + rng.normal(0, 0.05), 0, 0.9))
    if st >= 0.1:
        src = [g_ for g_ in (gA, gB) if g_[0]]; grad = (1, st, float(np.mean([g_[2] for g_ in src])), float(np.mean([g_[3] for g_ in src])))
    else: grad = (0, 0, 0, 0)
    radius = float(np.clip(mix(A["radius"], B["radius"]) + rng.normal(0, 0.04), 0.7, 1.3))   # 花の半径（独立した遺伝子）
    height = float(np.clip(mix(A["height"], B["height"]) + rng.normal(0, 0.04), 0.4, 1.2))   # 花の高さ（独立した遺伝子）
    poolA = [p["type"] for p in A["petals"]]; poolB = [p["type"] for p in B["petals"]]; pa = rng.uniform(0.3, 0.7)
    type_seq = [(str(rng.choice(poolA)) if rng.random() < pa else str(rng.choice(poolB))) for _ in range(N)]
    type_seq = [str(rng.choice(ALL_TYPES)) if (TYPE_MUT > 0 and rng.random() < TYPE_MUT) else t for t in type_seq]            # 型の突然変異
    child = dict(name=name, N=N, layers=layers, theta=theta, az_jit=az, order=order, col=col, grad=grad, radius=radius, height=height, type_seq=type_seq,
                 parents=(A["name"], B["name"]), alpha=round(alpha, 2), p_from_A=round(pa, 2), seed=int(rng.integers(1, 10**9)))
    if DERIVE_THETA: child["theta"] = derive_theta(child)
    return child

PA = dict(name="F2(親A)", N=8,  layers=1, theta=55, az_jit=0.10, types=["t1","t2"],          order="alternate", col=(0.72,0.35,300), grad=(0,0,0,0), seed=2)
PB = dict(name="F3(親B)", N=10, layers=2, theta=45, az_jit=0.15, types=["t3","t4","t6"],     order="spiral",    col=(0.80,0.45,350), grad=(1,0.6,0.5,0.3), seed=3)
def natural_size(petals):
    A = np.concatenate([place(TYPES[p["type"]]["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04) for p in petals])
    return float(np.hypot(A[:, 0], A[:, 1]).max()), float(A[:, 2].max())
for P_ in (PA, PB):
    P_["petals"] = make_flower2(P_, np.random.default_rng(P_["seed"])); P_["radius"], P_["height"] = natural_size(P_["petals"])
rngc = np.random.default_rng(2026)
children = [breed(PA, PB, rngc, f"C{i+1}") for i in range(6)]
# 配置: 左の列に親(上=A,下=B)、右の3列×2行に子
cells = [(PA, 0, 0), (PB, 0, 1)] + [(c, 1 + i % 3, i // 3) for i, c in enumerate(children)]
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; rec = []
for g, col_i, row_i in cells:
    cx, cy = (col_i - 1.5) * 3.0, (0.5 - row_i) * 3.0
    rng = np.random.default_rng(g.get("seed", 100 + hash(g["name"]) % 1000))
    petals = g["petals"] if "petals" in g else make_flower2(g, rng)
    raw = [place(TYPES[p["type"]]["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04) for p in petals]
    cat = np.concatenate(raw); r_nat = float(np.hypot(cat[:, 0], cat[:, 1]).max()); h_nat = float(cat[:, 2].max())
    fxy, fz = g["radius"] / r_nat, g["height"] / h_nat                                            # 半径・高さを遺伝子の値に合わせる
    allv = []
    for pi, p in enumerate(petals):
        d = TYPES[p["type"]]; Vw = raw[pi] * np.array([fxy, fxy, fz]); Vw[:, 0] += cx; Vw[:, 1] += cy; allv.append(Vw)
        T = d["T"]; nv, m = len(Vw), len(T); me = bpy.data.meshes.new(f"{g['name']}_p{pi}")
        me.vertices.add(nv); me.vertices.foreach_set("co", Vw.astype(np.float32).ravel())
        me.loops.add(3 * m); me.loops.foreach_set("vertex_index", T.astype(np.int32).ravel())
        me.polygons.add(m); me.polygons.foreach_set("loop_start", np.arange(0, 3 * m, 3, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(m, 3, dtype=np.int32))
        me.polygons.foreach_set("use_smooth", np.ones(m, dtype=bool)); me.update(calc_edges=True)
        rgb = petal_colors(d["r"], g["col"], g["grad"]); ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set("color", np.concatenate([rgb, np.ones((nv, 1))], 1).astype(np.float32).ravel()); me.color_attributes.active_color = ca
        sc.collection.objects.link(bpy.data.objects.new(me.name, me))
    A_ = np.concatenate(allv); rad = float(np.hypot(A_[:, 0] - cx, A_[:, 1] - cy).max()); hgt = float(A_[:, 2].max())
    comp = {t: sum(1 for p in petals if p["type"] == t) for t in sorted({p["type"] for p in petals})}
    L_, C_, H_ = g["col"]
    print("%-9s N=%2d 層%d 開き角%5.1f 型%s 色(L%.2f,C%.2f,H%3.0f) グラデ強さ%.2f  半径%.2f(遺伝子%.2f) 高さ%.2f(遺伝子%.2f) 拡縮 横%.2f 縦%.2f" % (g["name"], g["N"], g["layers"], g["theta"], comp, L_, C_, H_, g["grad"][1], rad, g["radius"], hgt, g["height"], fxy, fz))
    rec.append(dict(name=g["name"], N=g["N"], layers=g["layers"], theta=round(g["theta"], 1), col=[round(x, 3) for x in g["col"]], grad=list(g["grad"]), types=comp, radius=round(rad, 3), height=round(hgt, 3), scale_xy=round(fxy, 3), scale_z=round(fz, 3), parents=g.get("parents"), alpha=g.get("alpha")))
json.dump(rec, open(OUT + "_breeding.json", "w"), ensure_ascii=False, indent=1)
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 2400; sc.render.resolution_y = 1300
sc.view_settings.view_transform = 'Standard'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_cavity = True
w = bpy.data.worlds.new("w"); w.color = (0.93, 0.93, 0.95); sc.world = w
center = Vector((0, 0, 0.5))
def shot(off, path, scale):
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = scale
    cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); cam.location = center + Vector(off)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam; sc.render.filepath = path
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam, do_unlink=True)
sh.light = 'FLAT'; sh.show_cavity = False; shot((0, 0, 12), OUT + "_colors_top.png", 13.0)          # 色（陰影なし）
sh.light = 'STUDIO'; sh.show_cavity = True; shot((0, -10, 8), OUT + "_34.png", 13.5)               # 形（斜め上）
print("[done breeding]")
