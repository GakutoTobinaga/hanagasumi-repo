"""
measure_reference_photo.py -- 最初の見本写真（花びら6枚＋雄しべ・雌しべの分解写真）の測定。
  1) 花びら6枚の輪郭（短軸/長軸、solidity、輪郭長/凸包周長）
  2) 色（OKLCH）: 花びらを輪郭からの距離で中心/中間/縁に分けた値、紫の核、雄しべ・雌しべ側のクラスタ
使い方: python measure_reference_photo.py <見本写真.png>
注意: 2値化のしきい値225は、この写真に合わせたもの。短軸/長軸は、付け根の向きに依存しない（常に1以下）。
"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull
path = sys.argv[1]
rgb = np.array(Image.open(path).convert("RGB")).astype(float) / 255; gray = rgb.mean(2) * 255
gray_L = np.array(Image.open(path).convert("L")).astype(float)     # 輪郭の測定は、PILの輝度変換(L)で行う（会話中の報告値と一致させるため）
mask = ndi.binary_opening(gray_L < 225, iterations=2); mask = ndi.binary_fill_holes(mask)
mask_rgbmean = ndi.binary_fill_holes(ndi.binary_opening(gray < 225, iterations=2))       # 色の測定は、RGB平均のグレーで作った領域を使う（同上）
lab, n = ndi.label(mask); areas = ndi.sum(mask, lab, range(1, n + 1)); cm = ndi.center_of_mass(mask, lab, range(1, n + 1))
ids = [i + 1 for i in range(n) if areas[i] > 12000 and cm[i][1] < 1000]      # 左側にある花びら6枚（右側は雄しべ・雌しべ）
print("花びらの数:", len(ids))
rows = []
for i in ids:
    ys, xs = np.where(lab == i); P = np.stack([xs, ys], 1).astype(float); C = P - P.mean(0)
    w, v = np.linalg.eigh(np.cov(C.T)); v = v[:, np.argsort(w)[::-1]]; pr = [np.ptp(C @ v[:, k]) for k in (0, 1)]
    hull = ConvexHull(P); edge = (lab == i) & ~ndi.binary_erosion(lab == i)
    rows.append((ndi.center_of_mass(mask, lab, i), areas[i - 1], pr[0], pr[1], pr[1] / pr[0], areas[i - 1] / hull.volume, edge.sum() / hull.area))
rows.sort(key=lambda r: (0 if r[0][0] < 470 else 1, r[0][1]))
names = ["top-left", "top-mid", "top-right", "bottom-left", "bottom-mid", "bottom-right"]
print("%-13s %6s %5s %5s  短軸/長軸 solidity 輪郭/凸包" % ("位置", "面積", "長軸", "短軸"))
for nm, r in zip(names, rows): print("%-13s %6d %5.0f %5.0f   %.2f      %.2f     %.2f" % (nm, r[1], r[2], r[3], r[4], r[5], r[6]))
def to_oklch(rgb):
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4); r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b); m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b); s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s; a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s; bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, np.hypot(a, bb), np.degrees(np.arctan2(bb, a)) % 360
lab_c, n_c = ndi.label(mask_rgbmean); areas_c = ndi.sum(mask_rgbmean, lab_c, range(1, n_c + 1)); cm_c = ndi.center_of_mass(mask_rgbmean, lab_c, range(1, n_c + 1))
ids_c = [i + 1 for i in range(n_c) if areas_c[i] > 12000 and cm_c[i][1] < 1000]
L, C, H = to_oklch(rgb)
chm = lambda h: np.degrees(np.arctan2(np.sin(np.radians(h)).mean(), np.cos(np.radians(h)).mean())) % 360
allp = np.isin(lab_c, ids_c); dist = np.zeros(lab_c.shape)
for i in ids_c:
    m = lab_c == i; d = ndi.distance_transform_edt(m); dist[m] = d[m] / d[m].max()
print("--- 花びらの色（OKLCH）: 輪郭からの距離で分けた中央値と10-90%点")
for nm, m in (("core", allp & (dist > 0.5)), ("mid", allp & (dist >= 0.15) & (dist <= 0.5)), ("rim", allp & (dist < 0.15))):
    print("%-5s L %.2f [%.2f-%.2f]  C %.3f [%.3f-%.3f]  H %4.0f度" % (nm, np.median(L[m]), *np.percentile(L[m], [10, 90]), np.median(C[m]), *np.percentile(C[m], [10, 90]), chm(H[m])))
print("--- 各花びらの紫の核（C上位10%）")
for k, i in enumerate(ids_c):
    m = lab_c == i; mm = m & (C >= np.percentile(C[m], 90)); print("  petal%d L %.2f C %.3f H %3.0f" % (k, np.median(L[mm]), np.median(C[mm]), chm(H[mm])))
reg = (gray < 235) & (np.arange(rgb.shape[1])[None, :] > 950)
X = np.stack([L[reg], (C * np.cos(np.radians(H)))[reg], (C * np.sin(np.radians(H)))[reg]], 1); rng = np.random.default_rng(0); cen = X[rng.choice(len(X), 4, replace=False)]
for _ in range(25):
    lbl = np.argmin(((X[:, None] - cen[None]) ** 2).sum(2), 1); cen = np.array([X[lbl == k].mean(0) if (lbl == k).any() else cen[k] for k in range(4)])
print("--- 雄しべ・雌しべ側（x>950）4クラスタ（画素数, L, C, H）")
for k in np.argsort(-np.bincount(lbl, minlength=4)): c = cen[k]; print("  n=%6d L %.2f C %.3f H %3.0f" % ((lbl == k).sum(), c[0], np.hypot(c[1], c[2]), np.degrees(np.arctan2(c[2], c[1])) % 360))
