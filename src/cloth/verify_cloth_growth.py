"""
verify_cloth_growth.py  --  「縁だけ成長させるCloth」で縮れが出るかの切り分け用

目的:
  無地の花びら1枚で、成長差(縁ほど辺が長くなる)+Clothだけで
  縮れ/座屈が出るかを確認する。色・筋・自己衝突・厚みは入れない。

実行:
  blender -b -P verify_cloth_growth.py -- --out /tmp/cloth_test
  blender -b -P verify_cloth_growth.py -- --growth 0.1 0.2 --bending 0.1 1.0 --frames 100

出力:
  <out>.blend            ... 各パターンの最終形状（静的スナップショット）
  <out>_oblique.png      ... 斜め上からの比較画像
  <out>_low.png          ... 低い角度（凹凸が見えやすい）
  <out>_metrics.json     ... パラメータと数値指標

並び: 列=成長量(growth)、行=曲げ剛性(bending)。先頭列は成長ゼロ(baseline)で、
座屈判定は同じ曲げ剛性のbaselineとの比で行う。
Blender 4.5 想定。
注意: Blender 4.5 では shrink_max < shrink_min が補正される（エラーなし）。
      そのため頂点グループの重みを反転し、shrink_min(負)を動かす方式にしている。
"""
import bpy
import sys
import os
import math
import json
import argparse
import numpy as np
from mathutils import Vector, noise

# ---------------------------------------------------------------- 引数
def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--h", type=float, default=0.014, help="目標エッジ長(L=1基準)。0.014で約3000頂点")
    p.add_argument("--frames", type=int, default=120)
    p.add_argument("--ramp", type=int, default=80, help="成長が最大になるフレーム")
    p.add_argument("--growth", type=float, nargs="+", default=[0.12, 0.25, 0.40],
                   help="縁での辺の伸び率(0.25=25%%)。列方向")
    p.add_argument("--bending", type=float, nargs="+", default=[0.05, 0.5, 5.0],
                   help="曲げ剛性。行方向")
    p.add_argument("--r0", type=float, default=0.35, help="成長が始まる相対半径")
    p.add_argument("--power", type=float, default=2.0, help="縁への集中度")
    p.add_argument("--aniso", type=float, default=0.35, help="成長の角度ムラ")
    p.add_argument("--mode", choices=["outline", "radial", "both"], default="outline",
                   help="成長場: outline=輪郭からの距離(側面の縁も成長) / radial=付け根からの距離 / both")
    p.add_argument("--edge-width", dest="edge_width", type=float, default=0.18,
                   help="outlineモードで成長が効く輪郭からの幅(L=1基準)")
    p.add_argument("--cup", type=float, default=0.0,
                   help="初期形状の中央カップ量。z += cup * r^2 （正で上向きに凹む）")
    p.add_argument("--curl", type=float, default=0.0,
                   help="初期形状の縁の反り返り量。z -= curl * w（縁側だけ背面方向へ）。座屈の向きを偏らせる")
    p.add_argument("--pleat-freq", dest="pleat_freq", type=float, default=0.0,
                   help="付け根から放射状に走るひだの本数（扇全体での周期数）。0でOFF")
    p.add_argument("--pleat-amp", dest="pleat_amp", type=float, default=0.6,
                   help="ひだの成長量（縁の成長を1としたときの比）")
    p.add_argument("--asym", type=float, default=0.0,
                   help="左右非対称。-1..1。正で+x側の成長が強く、負で-x側が強い")
    p.add_argument("--bend-long", dest="bend_long", type=float, default=0.0,
                   help="初期形状: 長さ方向の反り。z += bend_long*(y/L)^2")
    p.add_argument("--trough", type=float, default=0.0,
                   help="初期形状: 断面の樋状の丸まり。z += trough*(x/0.5)^2")
    p.add_argument("--pleat-init-amp", dest="pleat_init_amp", type=float, default=0.0,
                   help="初期形状に入れる放射状ひだの高さ(L=1基準)。解析式 z += amp*A(r)*cos(pi*freq*u+位相ノイズ)")
    p.add_argument("--pleat-init-freq", dest="pleat_init_freq", type=float, default=15.0,
                   help="初期形状のひだの本数（扇全体での周期数）。見本の測定では約12〜18")
    p.add_argument("--pleat-warp", dest="pleat_warp", type=float, default=0.0,
                   help="初期ひだの位置を不規則にずらす量(角度座標u基準)。半径方向にも変化するのでひだが曲がる")
    p.add_argument("--pleat-var", dest="pleat_var", type=float, default=0.0,
                   help="ひだごとの振幅のムラ（0..1）")
    p.add_argument("--pleat-branch", dest="pleat_branch", type=float, default=0.0,
                   help="縁側で周波数2倍の二次ひだを足す量（主ひだに対する比）。枝分かれの近似")
    p.add_argument("--pleat-init-r0", dest="pleat_init_r0", type=float, default=0.15,
                   help="ひだが立ち上がり始める相対半径（付け根は平らに保つ）")
    p.add_argument("--rest-mode", dest="rest_mode", choices=["none", "circ"], default="none",
                   help="none=従来(辺を等方的にShrink) / circ=Rest Shape Keyで円周方向だけ自然長を伸ばす"
                        "(growth値=円周方向の伸び率。半径が大きいほど効く)")
    p.add_argument("--rest-dynamic", dest="rest_dynamic", type=int, default=1, help="circモードで Dynamic Mesh をONにするか(1/0)")
    p.add_argument("--rest-r0", dest="rest_r0", type=float, default=0.15, help="circモードで効き始める相対半径")
    p.add_argument("--curl-asym", dest="curl_asym", type=float, default=0.0,
                   help="縁の反り返りの左右の偏り。-1..1。curl*(1+asym*u)。1なら片側がほぼ0で反対側が2倍")
    p.add_argument("--curl-noise", dest="curl_noise", type=float, default=0.0,
                   help="縁の反り返りの、輪郭に沿ったムラ（0..1）。一様なcurlが皿のように垂れる問題への対策")
    p.add_argument("--selfdist", type=float, default=0.004, help="自己衝突の最小距離")
    p.add_argument("--outline", choices=["fan", "shield"], default="fan", help="輪郭の形")
    p.add_argument("--tip-curl", dest="tip_curl", type=float, default=0.3,
                   help="先端(y/L>0.8)でのcurlの倍率 0..1。小さいほど先端の折れ返りが弱まる")
    p.add_argument("--quality", type=int, default=8, help="Cloth Quality Steps")
    p.add_argument("--selfcol", action="store_true", help="自己衝突ON（最初はOFF推奨）")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", default="/tmp/cloth_test")
    return p.parse_args(argv)


# ---------------------------------------------------------------- 形状
L = 1.0   # 花びらの長さ（相対値）
W = 0.55  # shield輪郭の最大半幅の目安
W_FAN = 0.82  # fan輪郭: 最大半幅がおよそ 0.5 になる係数（幅≒長さ）


def halfwidth(t, outline="fan"):
    """t=y/L における半幅。
    shield: 付け根は細く、先端は平ら寄り（従来）
    fan   : 付け根が細く、最大幅は t≈0.7 付近、外縁は丸い扇形"""
    if outline == "shield":
        return W * (0.12 + 0.88 * t ** 0.8) * math.sqrt(max(0.0, 1.0 - t ** 6))
    return W_FAN * (0.10 + 0.90 * t ** 0.9) * math.sqrt(max(0.0, 1.0 - t ** 3))


def build_mesh(h, seed, outline="fan"):
    """三角格子（ほぼ正三角形）で輪郭内を埋める。依存はNumPyのみ。
    格子の方向性が座屈に出ないよう、頂点に微小ジッタを入れる。"""
    rng = np.random.default_rng(seed)
    dy = h * math.sqrt(3) / 2
    ny = int(L / dy) + 1
    nx = int(max(W, W_FAN) / h) + 2

    index, pts = {}, []
    for j in range(ny):
        y = j * dy
        t = y / L
        if t > 1.0:
            continue
        hw = halfwidth(t, outline)
        for i in range(-nx, nx + 1):
            x = (i + 0.5 * (j & 1)) * h
            if abs(x) <= hw:
                index[(i, j)] = len(pts)
                pts.append((x, y))

    raw_tris = []
    for j in range(ny - 1):
        for i in range(-nx - 1, nx + 2):
            if j % 2 == 0:
                cands = [((i, j), (i + 1, j), (i, j + 1)),
                         ((i, j), (i, j + 1), (i - 1, j + 1))]
            else:
                cands = [((i, j), (i + 1, j), (i + 1, j + 1)),
                         ((i, j), (i + 1, j + 1), (i, j + 1))]
            for c in cands:
                if all(k in index for k in c):
                    raw_tris.append(tuple(index[k] for k in c))

    # 未使用頂点を除去して振り直し
    used = sorted({v for t in raw_tris for v in t})
    remap = {old: new for new, old in enumerate(used)}
    pts = np.array([pts[v] for v in used], dtype=np.float64)
    tris = [tuple(remap[v] for v in t) for t in raw_tris]

    pts += rng.uniform(-0.12 * h, 0.12 * h, size=pts.shape)          # xyジッタ
    z = rng.uniform(-0.05 * h, 0.05 * h, size=(len(pts), 1))          # 対称性を崩す微小z
    verts = np.hstack([pts, z])
    return verts, tris


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def boundary_vertices(tris):
    """輪郭頂点（1枚の三角形にしか属さない辺の頂点）のインデックス"""
    cnt = {}
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            cnt[k] = cnt.get(k, 0) + 1
    return sorted({v for k, n in cnt.items() if n == 1 for v in k})


def boundary_distance(verts, tris):
    """各頂点から輪郭までの最短距離。
    輪郭頂点への離散距離なので、誤差は最大でも辺長h程度。"""
    bidx = boundary_vertices(tris)
    bp = verts[bidx, :2]
    diff = verts[:, None, :2] - bp[None, :, :]
    return np.sqrt((diff ** 2).sum(-1)).min(axis=1)


def pleat_init(verts, r_rel, args):
    """初期形状の放射状ひだ（解析式）。Clothは初期形状を曲げの自然状態として使うので、
    ここで入れたひだは保たれ、縁の縮れ(成長)がその上に重なる。
      主ひだ : cos(pi*f*u' + 位相)        u' = u + warp*noise(u, r)  … 位置のムラ・ひだの曲がり
      二次ひだ: cos(2*pi*f*u' + 位相2)    縁側(r>0.45)で立ち上がる   … 枝分かれの近似
      振幅ムラ: 1 + var*noise(u*f/2)                                  … ひだごとの高さの違い"""
    if args.pleat_init_amp == 0.0:
        return 0.0
    f = args.pleat_init_freq
    th = np.arctan2(verts[:, 0], verts[:, 1])
    u = th / max(float(np.abs(th).max()), 1e-6)
    sd = args.seed
    nz = lambda a, b, c: np.array([noise.noise(Vector((x, y, c))) for x, y in zip(a, b)])
    u2 = u + args.pleat_warp * nz(u * 2.0, r_rel * 1.5, sd * 5.1)
    ph1 = 0.6 * nz(r_rel * 1.5, np.full_like(r_rel, sd * 5.1), 2.0)
    amp_mod = 1.0 + args.pleat_var * nz(u * f * 0.5, np.full_like(u, sd * 2.7), 3.0)
    A1 = smoothstep(args.pleat_init_r0, 0.8, r_rel)
    A2 = smoothstep(0.45, 0.9, r_rel)
    primary = np.cos(math.pi * f * u2 + ph1)
    secondary = np.cos(2.0 * math.pi * f * u2 + 1.7 * ph1 + 1.3)
    return args.pleat_init_amp * A1 * amp_mod * (primary + args.pleat_branch * A2 * secondary)


def growth_weights(verts, tris, args):
    """頂点ごとの成長場 w (0..1)。辺の自然長は 1 + growth*w 倍になる（頂点側）。
      outline: (1 - d/edge_width)^p  … d=輪郭からの距離。側面・先端の縁すべてが成長
               ただし付け根(ピン留め側)は root_fade で成長ゼロに落とす
      radial : smoothstep(r0,1,r)^p  … 付け根からの距離。主に先端側
    ここに角度ムラ (1 + aniso*noise(θ)) を掛ける。"""
    x, y = verts[:, 0], verts[:, 1]
    r = np.hypot(x, y)
    r = r / r.max()
    theta = np.arctan2(x, y)
    nz = np.array([noise.noise(Vector((th * 2.0, args.seed * 7.1, 0.0))) for th in theta])

    radial = smoothstep(args.r0, 1.0, r) ** args.power
    d = boundary_distance(verts, tris)
    outline = (1.0 - np.clip(d / args.edge_width, 0.0, 1.0)) ** args.power
    root_fade = smoothstep(0.05 * L, 0.30 * L, y)
    outline = outline * root_fade

    if args.mode == "radial":
        base = radial
    elif args.mode == "outline":
        base = outline
    else:
        base = np.maximum(radial, outline)
    w = base * (1.0 + args.aniso * nz)

    # 角度方向の座標 u (-1..1)。ひだ・非対称はこの u で決める
    u = theta / max(float(np.abs(theta).max()), 1e-6)
    if args.pleat_freq > 0.0:
        # 付け根から放射状に走るひだ: 角度方向に周期的に成長量を変える。
        # 位相を半径方向にゆっくり揺らして、完全に直線的なひだになるのを避ける
        ph = 0.6 * np.array([noise.noise(Vector((rr * 1.5, args.seed * 3.3, 1.0))) for rr in r])
        pleat = 0.5 * (1.0 + np.cos(math.pi * args.pleat_freq * u + ph))
        interior = smoothstep(0.2, 0.9, r) * root_fade
        w = w + args.pleat_amp * interior * pleat
    if args.asym != 0.0:
        w = w * (1.0 + args.asym * u)
    w = np.clip(w, 0.0, 1.0)
    return w, r


# ---------------------------------------------------------------- Cloth
def make_cloth_petal(name, loc, verts, tris, w, r_rel, growth, bending, args):
    scene = bpy.context.scene
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], tris)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    scene.collection.objects.link(obj)

    # 頂点グループ: 成長場 / 付け根ピン
    vg_g = obj.vertex_groups.new(name="growth")
    vg_p = obj.vertex_groups.new(name="pin")
    for i in range(len(verts)):
        # Blender 4.5 では shrink_max < shrink_min が補正されるため、
        # 重みを反転し shrink_min（負）側を動かす。成長させたい場所ほど重みを小さくする
        vg_g.add([i], float(1.0 - w[i]), 'REPLACE')
        if verts[i, 1] < 0.08 * L:
            vg_p.add([i], 1.0, 'REPLACE')

    mod = obj.modifiers.new("Cloth", 'CLOTH')
    s = mod.settings
    s.quality = args.quality
    s.mass = 0.3
    s.air_damping = 1.0
    s.tension_stiffness = 15.0
    s.compression_stiffness = 15.0   # 低くすると座屈しやすいがヨレやすい。比較対象の候補
    s.shear_stiffness = 5.0
    s.bending_model = 'ANGULAR'
    s.bending_stiffness = bending
    s.bending_damping = 0.5
    s.effector_weights.gravity = 0.0  # 重力OFF
    s.vertex_group_mass = "pin"
    s.pin_stiffness = 1.0
    s.vertex_group_shrink = "growth"

    # 辺の自然長倍率は両端頂点の重みから決まる。重みを反転してあるので、
    # 元の成長場 w に対して頂点側の倍率が 1 + growth*w になる（4.5で実測確認済みの方式）。
    # shrink_max は shrink_min 未満だと補正されるので 0 のまま固定し、shrink_min だけ動かす。
    s.shrink_max = 0.0
    s.shrink_min = 0.0
    if args.rest_mode == "none":
        s.keyframe_insert(data_path="shrink_min", frame=1)
        s.shrink_min = -growth
        assert abs(s.shrink_min + growth) < 1e-6, "shrink_min が代入値と一致しない（クランプされた可能性）"
        s.keyframe_insert(data_path="shrink_min", frame=args.ramp)
    else:
        # 円周方向だけ自然長を伸ばした「Rest」形状キーを作り、そこから辺の自然長を取る。
        # 実際の初期形状(Basis)はそのままなので、円周方向に圧縮された状態から始まり、
        # 余った円周長が座屈して放射状のひだになる、という仮説の検証。
        xy = np.array([(v.co.x, v.co.y, v.co.z) for v in me.vertices])
        rr = np.hypot(xy[:, 0], xy[:, 1])
        rr_rel = rr / rr.max()
        th = np.arctan2(xy[:, 0], xy[:, 1])
        gc = growth * smoothstep(args.rest_r0, 0.9, rr_rel)
        th2 = th * (1.0 + gc)
        rest = np.stack([rr * np.sin(th2), rr * np.cos(th2), xy[:, 2]], axis=1)
        obj.shape_key_add(name="Basis", from_mix=False)
        rk = obj.shape_key_add(name="Rest", from_mix=False)
        rk.data.foreach_set("co", rest.ravel())
        rk.value = 0.0
        s.use_dynamic_mesh = bool(args.rest_dynamic)
        s.rest_shape_key = rk

    cs = mod.collision_settings
    cs.use_collision = False
    cs.use_self_collision = bool(args.selfcol)
    if args.selfcol:
        cs.self_distance_min = args.selfdist

    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = args.frames
    return obj


def snapshot(obj, growth, bending):
    """シム結果を静的メッシュとして固定し、元のClothオブジェクトを消す"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)
    snap = bpy.data.objects.new(obj.name + "_final", me)
    snap.matrix_world = obj.matrix_world.copy()
    snap["growth"] = growth
    snap["bending"] = bending
    bpy.context.scene.collection.objects.link(snap)
    old_me = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(old_me)
    return snap


def total_area(me):
    return float(sum(p.area for p in me.polygons))


# ---------------------------------------------------------------- 描画
def add_label(text, loc, size=0.09):
    cu = bpy.data.curves.new("lbl", 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new("lbl", cu)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)


def setup_render(scene):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1400
    scene.view_settings.view_transform = 'Standard'
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'SINGLE'
    sh.single_color = (0.78, 0.74, 0.90)
    sh.show_cavity = True
    world = bpy.data.worlds.new("w")
    world.color = (1.0, 1.0, 1.0)
    scene.world = world


def render_view(scene, center, offset, scale, path):
    cd = bpy.data.cameras.new("cam")
    cd.type = 'ORTHO'
    cd.ortho_scale = scale
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = center + Vector(offset)
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


# ---------------------------------------------------------------- main
def fit_residual(co, order):
    """xy に対する z の最小二乗フィット残差。
    order=1: 平面（傾きを除く） / order=2: 2次曲面（全体のカップ・樋・反りを除く）"""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if order == 1:
        A = np.stack([x, y, np.ones_like(x)], axis=1)
    else:
        A = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], axis=1)
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    return z - A @ coef


def fit_residual_rms(co, order):
    res = fit_residual(co, order)
    return float(np.sqrt((res ** 2).mean())), float(np.abs(res).max())


def edge_metrics(co, xy0, bidx, n=1024):
    """輪郭に沿ったzのしわ(2次曲面除去後)を弧長で等間隔にリサンプルしてFFTする。
    edge_rms : 縁の凹凸の大きさ
    edge_kpk : 支配的な周期数（輪郭1周あたり）
    edge_hf  : k>=16 のパワー比。細かい縮れ（第2世代以降）がどれだけあるかの目安"""
    res = fit_residual(co, 2)
    b = np.array(bidx)
    c = xy0[b].mean(axis=0)
    ang = np.arctan2(xy0[b, 0] - c[0], xy0[b, 1] - c[1])
    order = b[np.argsort(ang)]
    pts = xy0[order]
    seg = np.hypot(*(np.roll(pts, -1, axis=0) - pts).T)
    total = float(seg.sum())
    sarc = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
    su = np.linspace(0.0, total, n, endpoint=False)
    z = np.interp(su, sarc, res[order], period=total)
    z = z - z.mean()
    pw = np.abs(np.fft.rfft(z)) ** 2
    p1 = pw[1:]
    hf = float(p1[15:].sum() / max(p1.sum(), 1e-12))
    return float(np.sqrt((z ** 2).mean())), int(np.argmax(p1)) + 1, hf


def ring_spectrum(co, nbins=96, kmax=30):
    """半径 0.5〜0.85 の帯について、角度方向のしわ(2次曲面除去後のz)をFFTし、
    支配的な周期数kとそのシェアを返す。放射状のひだが出ていれば、
    ひだの本数付近にピークが立つはず。"""
    res = fit_residual(co, 2)
    r = np.hypot(co[:, 0], co[:, 1])
    r = r / r.max()
    th = np.arctan2(co[:, 0], co[:, 1])
    m = (r > 0.5) & (r < 0.85)
    if m.sum() < nbins:
        return 0, 0.0
    edges = np.linspace(th.min(), th.max(), nbins + 1)
    idx = np.clip(np.digitize(th[m], edges) - 1, 0, nbins - 1)
    prof = np.zeros(nbins)
    cnt = np.zeros(nbins)
    np.add.at(prof, idx, res[m])
    np.add.at(cnt, idx, 1.0)
    prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)
    mag = np.abs(np.fft.rfft(prof - prof.mean()))[1:kmax + 1]
    if mag.sum() <= 0:
        return 0, 0.0
    k = int(np.argmax(mag)) + 1
    return k, float(mag[k - 1] ** 2 / (mag ** 2).sum())


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = args.frames

    verts, tris = build_mesh(args.h, args.seed, args.outline)
    w, r_rel = growth_weights(verts, tris, args)
    # 座屈の向きを偏らせる初期反り（Clothは初期形状を曲げの自然状態として使う）
    verts = verts.copy()
    tip = smoothstep(0.80 * L, 0.98 * L, verts[:, 1])
    curl_scale = 1.0 - (1.0 - args.tip_curl) * tip
    th0 = np.arctan2(verts[:, 0], verts[:, 1])
    u0 = th0 / max(float(np.abs(th0).max()), 1e-6)
    nzc = np.array([noise.noise(Vector((t * 3.0, args.seed * 9.1, 4.0))) for t in th0])
    curl_mod = np.clip(1.0 + args.curl_asym * u0 + args.curl_noise * nzc, 0.0, 2.5)
    verts[:, 2] += (args.cup * r_rel ** 2 - args.curl * w * curl_scale * curl_mod
                    + args.bend_long * (verts[:, 1] / L) ** 2
                    + args.trough * (verts[:, 0] / 0.5) ** 2
                    + pleat_init(verts, r_rel, args))
    print(f"[info] verts={len(verts)} tris={len(tris)} mode={args.mode} outline={args.outline} cup={args.cup} curl={args.curl} tip_curl={args.tip_curl} curl_asym={args.curl_asym} curl_noise={args.curl_noise} pleat_init={args.pleat_init_amp}x{args.pleat_init_freq}(warp{args.pleat_warp},var{args.pleat_var},br{args.pleat_branch}) pleat={args.pleat_freq}x{args.pleat_amp} asym={args.asym} bend_long={args.bend_long} trough={args.trough}")

    # 比較用に、成長ゼロの列(baseline)を必ず先頭に入れる
    growths = [0.0] + [g for g in args.growth if g != 0.0]

    sx, sy = 1.7, 1.7
    nc, nr = len(growths), len(args.bending)
    objs = []
    for ri, b in enumerate(args.bending):
        for ci, g in enumerate(growths):
            x = (ci - (nc - 1) / 2) * sx
            y = (ri - (nr - 1) / 2) * sy
            o = make_cloth_petal(f"petal_g{g}_b{b}", (x, y, 0.0), verts, tris, w, r_rel, g, b, args)
            objs.append((o, g, b, x, y))

    # 初期面積（成長前）
    area0 = total_area(objs[0][0].data)

    # シミュレーションを順番に進める（飛ばさず1フレームずつ）
    scene.frame_set(1)
    for f in range(1, args.frames + 1):
        scene.frame_set(f)
        if f % 20 == 0:
            print(f"[sim] frame {f}/{args.frames}")

    # 最終フレームでアニメ値が入力どおりか確認（クランプ/キー未登録バグの検知）
    for o, g, b, x, y in objs:
        got = o.modifiers["Cloth"].settings.shrink_min
        if args.rest_mode == "none" and abs(got + g) > 1e-6:
            raise RuntimeError(f"shrink_min mismatch: expected {-g}, got {got} ({o.name})")

    # スナップショット化して指標を計算
    bidx_edge = boundary_vertices(tris)
    raw = []
    for o, g, b, x, y in objs:
        snap = snapshot(o, g, b)
        co = np.empty(len(snap.data.vertices) * 3)
        snap.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        nrm = np.empty(len(snap.data.polygons) * 3)
        snap.data.polygons.foreach_get("normal", nrm)
        flipped = float((nrm.reshape(-1, 3)[:, 2] < 0.0).mean())  # 法線が下向きの面の割合（巻き込みの目安）
        plane_rms, plane_max = fit_residual_rms(co, 1)
        wrinkle_rms, wrinkle_max = fit_residual_rms(co, 2)
        ring_k, ring_share = ring_spectrum(co)
        edge_rms, edge_kpk, edge_hf = edge_metrics(co, verts[:, :2], bidx_edge)
        raw.append({
            "growth": g, "bending": b, "pos": (x, y),
            "area_ratio": total_area(snap.data) / area0,
            "flipped_frac": flipped,
            "plane_rms": plane_rms, "plane_max": plane_max,
            "wrinkle_rms": wrinkle_rms, "wrinkle_max": wrinkle_max,
            "ring_k": ring_k, "ring_share": ring_share,
            "edge_rms": edge_rms, "edge_kpk": edge_kpk, "edge_hf": edge_hf,
        })

    # 同じ曲げ剛性・成長ゼロとの比較で「座屈したか」を判定する
    base = {m["bending"]: m for m in raw if m["growth"] == 0.0}
    metrics = []
    for m in raw:
        b0 = base[m["bending"]]
        m["plane_rms_vs_base"] = m["plane_rms"] / max(b0["plane_rms"], 1e-6)
        m["wrinkle_rms_vs_base"] = m["wrinkle_rms"] / max(b0["wrinkle_rms"], 1e-6)
        # 判定: 成長ゼロ(同じ曲げ剛性)の3倍超。絶対値の下限は置かない
        # （細かい縮れは振幅が小さく、絶対値閾値だと見逃すため）
        m["buckled"] = bool(m["growth"] > 0.0 and m["plane_rms_vs_base"] > 3.0)
        out = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "pos"}
        metrics.append(out)
        print("[result]", out)
        if m["growth"] > 0.0 and not m["buckled"]:
            print("   -> 座屈判定NG: 成長量・compression_stiffness・ramp・quality を確認")
        add_label(f"g={m['growth']}  bend={m['bending']}", (m["pos"][0], m["pos"][1] - 0.12, 0.0))

    # 診断メモ:
    #  area_ratio       … 増えただけでは座屈の証拠にならない（平面のまま広がっても増える）
    #  plane_rms        … 平面フィットからのずれ（傾きは除去済み）。成長ゼロとの比(_vs_base)で見る
    #  wrinkle_rms      … 2次曲面（全体のカップ形状）まで除いたずれ。縮れ/しわの量に近い
    with open(args.out + "_metrics.json", "w") as fp:
        json.dump({"args": vars(args), "initial_area": area0, "results": metrics}, fp, indent=2)

    setup_render(scene)
    center = Vector((0.0, 0.5, 0.0))
    span = max(nc * sx, nr * sy) * 1.15
    render_view(scene, center, (0.0, -6.0, 6.0), span * 1.05, args.out + "_oblique.png")
    render_view(scene, center, (0.0, -9.0, 2.2), span * 1.05, args.out + "_low.png")

    bpy.ops.wm.save_as_mainfile(filepath=args.out + ".blend")
    print("[done]", args.out)


if __name__ == "__main__":
    main()
