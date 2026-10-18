"""
hanagasumi_flower_proto.py  --  花霞の花全体の試作（雄しべ・雌しべなし）
遺伝子（枚数・層・開き角・方位角ムラ・型の割り当て・色・グラデーション）から花を組み立て、
Workbench（頂点カラー）で描画する。型は /tmp/meshy/dec_t1..t6.npz（付け根を原点、長さ1、約5万面）。
実行: python hanagasumi_flower_proto.py -- <出力プレフィックス>
"""
import sys, math, json, numpy as np, bpy
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/meshy/flower"
TYPES = {k: np.load(f"/tmp/meshy/dec_{k}.npz") for k in ("t1", "t2", "t3", "t4", "t5", "t6")}

# ---------------- OKLCH ----------------
def oklch_to_lin(L, C, H):
    h = np.radians(H); a = C * np.cos(h); b = C * np.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b; m_ = L - 0.1055613458 * a - 0.0638541728 * b; s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return np.stack([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                     -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                     -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s], -1)
def max_chroma(L, H):
    lo, hi = 0.0, 0.5
    for _ in range(30):
        mid = (lo + hi) / 2; rgb = oklch_to_lin(L, mid, H)
        if np.all(rgb >= -1e-4) and np.all(rgb <= 1 + 1e-4): lo = mid
        else: hi = mid
    return lo
def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def petal_colors(r, col, grad):
    L, Crel, H = col; C = Crel * max_chroma(L, H)
    present, strength, mid, soft = grad
    t = smoothstep(mid - soft, mid + soft, r) * strength if present else np.zeros_like(r)   # 付け根→縁
    Lv = np.minimum(L + 0.17 * t, 0.97); Cv = C * (1 - t * (1 - 0.3))
    return np.clip(oklch_to_lin(Lv, Cv, H), 0, 1)

# ---------------- 配置 ----------------
def place(P, theta, phi, roll, scale, r0):
    rh = np.array([math.cos(phi), math.sin(phi), 0.0])
    a = math.sin(theta) * rh + math.cos(theta) * np.array([0, 0, 1.0])        # 花びらの長さ方向
    n = -math.cos(theta) * rh + math.sin(theta) * np.array([0, 0, 1.0])       # 内側（上向き）の法線
    l = np.cross(n, a); c, s = math.cos(roll), math.sin(roll)
    l2 = c * l + s * n; n2 = -s * l + c * n; R = np.stack([l2, n2, a], 1)
    return (P * scale) @ R.T + r0 * rh
def make_flower(g, rng):
    N, layers = g["N"], g["layers"]; th0 = math.radians(g["theta"]); petals = []
    n_out = N // 2 if layers == 2 else 0; groups = [(N - n_out, th0, 0.0)] + ([(n_out, th0 + math.radians(15), 0.5)] if n_out else [])
    k = 0
    for cnt, th, off in groups:
        step = 2 * math.pi / cnt
        for i in range(cnt):
            phi = (i + off) * step + g["az_jit"] * step * rng.uniform(-1, 1)
            theta = th + math.radians(rng.uniform(-10, 10))
            roll0 = math.radians(8)
            roll = roll0 * (k / max(N - 1, 1)) * 2 if g["order"] == "spiral" else roll0 * (1 if k % 2 == 0 else -1)
            roll += math.radians(rng.uniform(-5, 5)); scale = 1 + rng.uniform(-0.10, 0.10)
            tname = g["types"][rng.integers(len(g["types"]))]; k += 1
            petals.append(dict(type=tname, phi=phi, theta=theta, roll=roll, scale=scale))
    return petals

FLOWERS = [
 dict(name="F1", N=6,  layers=1, theta=30, az_jit=0.05, types=["t5"],                          order="alternate", col=(0.72,0.35,300), grad=(1,0.8,0.5,0.35), seed=1),
 dict(name="F2", N=8,  layers=1, theta=55, az_jit=0.10, types=["t1","t2"],                     order="alternate", col=(0.72,0.35,300), grad=(0,0,0,0),         seed=2),
 dict(name="F3", N=10, layers=2, theta=45, az_jit=0.15, types=["t3","t4","t6"],                order="spiral",    col=(0.80,0.45,350), grad=(1,0.6,0.5,0.3),   seed=3),
 dict(name="F4", N=7,  layers=1, theta=75, az_jit=0.10, types=["t1","t5","t6"],                order="alternate", col=(0.78,0.55,40),  grad=(1,0.7,0.5,0.3),   seed=4),
 dict(name="F5", N=9,  layers=2, theta=60, az_jit=0.10, types=["t1","t2","t3","t4","t5","t6"], order="spiral",    col=(0.70,0.40,255), grad=(1,0.9,0.45,0.3),  seed=5),
 dict(name="F6", N=6,  layers=1, theta=20, az_jit=0.05, types=["t2","t3"],                     order="spiral",    col=(0.88,0.45,95),  grad=(1,0.5,0.5,0.3),   seed=6),
]
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; record = []
for fi, g in enumerate(FLOWERS):
    rng = np.random.default_rng(g["seed"]); petals = make_flower(g, rng)
    cx, cy = (fi % 3 - 1) * 3.0, (0.5 - fi // 3) * 3.0
    for pi, p in enumerate(petals):
        d = TYPES[p["type"]]; Vw = place(d["V"], p["theta"], p["phi"], p["roll"], p["scale"], 0.04); Vw[:, 0] += cx; Vw[:, 1] += cy
        T = d["T"]; nv, m = len(Vw), len(T)
        me = bpy.data.meshes.new(f"{g['name']}_p{pi}")
        me.vertices.add(nv); me.vertices.foreach_set("co", Vw.astype(np.float32).ravel())
        me.loops.add(3 * m); me.loops.foreach_set("vertex_index", T.astype(np.int32).ravel())
        me.polygons.add(m); me.polygons.foreach_set("loop_start", np.arange(0, 3 * m, 3, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(m, 3, dtype=np.int32))
        me.polygons.foreach_set("use_smooth", np.ones(m, dtype=bool)); me.update(calc_edges=True)
        rgb = petal_colors(d["r"], g["col"], g["grad"]); ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set("color", np.concatenate([rgb, np.ones((nv, 1))], 1).astype(np.float32).ravel())
        me.color_attributes.active_color = ca
        ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob)
        p["theta_deg"] = round(math.degrees(p.pop("theta")), 1); p["phi_deg"] = round(math.degrees(p.pop("phi")), 1); p["roll_deg"] = round(math.degrees(p.pop("roll")), 1); p["scale"] = round(p["scale"], 3)
    record.append(dict(g, petals=petals))
json.dump(record, open(OUT + "_genes.json", "w"), ensure_ascii=False, indent=1)

sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 2400; sc.render.resolution_y = 1700
sc.view_settings.view_transform = 'Standard'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_cavity = True
try: sh.show_shadows = True; sh.shadow_intensity = 0.35
except Exception: pass
if "--flat" in sys.argv:   # 色の確認用: 陰影なし（形は分かりにくいが、設定した色とグラデーションがそのまま見える）
    sh.light = 'FLAT'; sh.show_cavity = False
    try: sh.show_shadows = False
    except Exception: pass
w = bpy.data.worlds.new("w"); w.color = (0.93, 0.93, 0.95); sc.world = w
center = Vector((0, 0, 0.5))
def shot(off, path, scale):
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = scale
    cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); cam.location = center + Vector(off)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam; sc.render.filepath = path
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam, do_unlink=True)
shot((0, 0, 12), OUT + "_top.png", 9.2)
if "--flat" not in sys.argv:
    shot((0, -9, 7), OUT + "_34.png", 9.6)
print("[done flowers]")
