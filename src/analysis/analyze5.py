import sys, numpy as np, scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d, binary_closing, binary_fill_holes, distance_transform_edt
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

d=np.load(sys.argv[1]); V0=d["V"]; N0=d["N"]; T0=d["T"]
q=np.round(V0/1e-5).astype(np.int64)
_,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
V=V0[first]; N=np.zeros_like(V); np.add.at(N,inv,N0); N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
T=inv[T0]; T=T[(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0])]; nV=len(V)
E=np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]); E.sort(axis=1)
key=E[:,0].astype(np.int64)*nV+E[:,1]; uk=np.unique(key); Eu=np.stack([uk//nV,uk%nV],1)
L=np.linalg.norm(V[Eu[:,0]]-V[Eu[:,1]],axis=1)
tri_a=0.5*np.linalg.norm(np.cross(V[T[:,1]]-V[T[:,0]],V[T[:,2]]-V[T[:,0]]),axis=1)
va=np.zeros(nV); 
for k in range(3): np.add.at(va,T[:,k],tri_a/3)
Lv=np.zeros(nV); cv=np.zeros(nV)
np.add.at(Lv,Eu[:,0],L); np.add.at(Lv,Eu[:,1],L); np.add.at(cv,Eu[:,0],1); np.add.at(cv,Eu[:,1],1); Lv/=np.maximum(cv,1)

# PCA frame
C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]
# 付け根を目視で指定: render_axes.py と同じ座標（x=横, y=法線, z=軸）で「xが最大の端」
P3=C@vec; best=None
for ax in (0,1):
    other=1-ax; lo_,hi_=P3[:,ax].min(),P3[:,ax].max(); t_=0.05*(hi_-lo_)
    for sign,mask in ((+1,P3[:,ax]<lo_+t_),(-1,P3[:,ax]>hi_-t_)):
        sec=np.ptp(P3[mask,other])*np.ptp(P3[mask,2])
        if best is None or sec<best[0]: best=(sec,ax,sign)
_,ax_,sign_=best
a0=sign_*vec[:,ax_]; l0=vec[:,1-ax_]; n0=vec[:,2]
xcoord=C@l0
cap=np.argsort(-xcoord)[:200]; base=cap[np.argmin(np.linalg.norm(V[cap]-V[cap].mean(0),axis=1))]
# 長さの軸: 付け根から、最も遠い5%の頂点の重心へ向かう向き。法線はそれに直交させる
dist_=np.linalg.norm(V-V[base],axis=1); far_=np.argsort(-dist_)[:int(0.05*len(V))]
a=V[far_].mean(0)-V[base]; a/=np.linalg.norm(a)
n=vec[:,2]-np.dot(vec[:,2],a)*a; n/=np.linalg.norm(n)
l=np.cross(n,a); proj=C@a
print("manual base vertex",base,V[base].round(3),"| length axis from base to far-centroid")
pa=(V-V[base])@a; pl=(V-V[base])@l; pn=(V-V[base])@n; phi=np.arctan2(pl,pa)
G=sp.coo_matrix((np.r_[L,L],(np.r_[Eu[:,0],Eu[:,1]],np.r_[Eu[:,1],Eu[:,0]])),shape=(nV,nV)).tocsr()
from scipy.sparse.csgraph import connected_components
ncomp,lab=connected_components(G,directed=False); print("connected components:",ncomp,"sizes(top3):",np.sort(np.bincount(lab))[::-1][:3])
dg=dijkstra(G,indices=base); fin=np.isfinite(dg); R=np.where(fin,dg/dg[fin].max(),np.nan)
wp=[np.ptp((V-V[base])[(proj-proj.min()>=k*np.ptp(proj)/10)&(proj-proj.min()<(k+1)*np.ptp(proj)/10)]@l) for k in range(10)]
print("extents e1,e2,e3: %.2f %.2f %.2f ; width/length %.2f ; width profile base->tip (10 bins):"%(np.ptp(proj),np.ptp(C@l),np.ptp(C@n),np.max(wp)/np.ptp(proj)),np.round(wp,2),"; widest at bin",int(np.argmax(wp))+1,"/10")

side=(N@n)>0   # 表/裏（PCAの最小軸に対する法線の向き）
print("side areas front %.2f back %.2f  total %.2f"%(va[side].sum(),va[~side].sum(),va.sum()))
res={}
# --- 厚み: 表の頂点から最近い裏の頂点までの距離
tb=cKDTree(V[~side]); rng=np.random.default_rng(0)
ii=rng.choice(np.where(side)[0],20000,replace=False); th=tb.query(V[ii])[0]
print("shell thickness proxy (nearest opposite-side vertex) pct 5,50,95: ",np.percentile(th,[5,50,95]).round(4))

# --- 輪郭からの距離（投影面のラスター距離変換）
g=1000; x0,x1=pl.min(),pl.max(); y0,y1=pa.min(),pa.max(); cs=max(x1-x0,y1-y0)/g
def bdist(mask):
    gi=np.clip(((pl[mask]-x0)/cs).astype(int),0,g-1); gj=np.clip(((pa[mask]-y0)/cs).astype(int),0,g-1)
    occ=np.zeros((g,g),bool); occ[gj,gi]=True
    occ=binary_fill_holes(binary_closing(occ,iterations=12)); e=distance_transform_edt(occ)*cs
    out=np.full(nV,np.nan); out[mask]=e[gj,gi]; return out
# --- スケール固定の粗さ D_sigma = 1-|面積加重平均法線|
def dispersion(mask,sig,ncent=40000):
    ids=np.where(mask)[0]; tr=cKDTree(V[ids]); cent=rng.choice(ids,min(ncent,len(ids)),replace=False)
    nb=tr.query_ball_point(V[cent],sig); D=np.empty(len(cent))
    for t,lst in enumerate(nb):
        j=ids[lst]; v=(va[j,None]*N[j]).sum(0)/va[j].sum(); D[t]=1-np.linalg.norm(v)
    return cent,D
out={}
for name,mask in (("front",side),("back",~side)):
    bd=bdist(mask); bdn=bd/np.nanmax(bd)
    out[name]={"bd":bdn,"bdmax":np.nanmax(bd)}
    for sig in (0.02,0.05):
        cent,D=dispersion(mask,sig); out[name][sig]=(cent,D)
    print(name,"max inward dist from outline (world units): %.3f"%np.nanmax(bd))
    cent,D=out[name][0.02]
    print("  Spearman(D_0.02, local edge length) = %.2f   (scale-fixed; ~0 means density does not follow roughness)"%stats.spearmanr(D,Lv[cent])[0])
    print("  roughness D@0.02 / D@0.05 vs normalized distance to outline:")
    for sig in (0.02,0.05):
        cent,D=out[name][sig]; b=bdn[cent]; row=[]
        for lo in np.arange(0,1,0.2):
            m=(b>=lo)&(b<lo+0.2); row.append("%.4f"%D[m].mean() if m.sum()>30 else "  -  ")
        print("   sigma",sig,":"," ".join(row),"   (bins 0-0.2 ... 0.8-1.0)")
    # D vs geodesic radius
    cent,D=out[name][0.02]; print("   D@0.02 vs R (0-0.2,...,0.8-1):"," ".join("%.4f"%D[(R[cent]>=lo)&(R[cent]<lo+0.2)].mean() if ((R[cent]>=lo)&(R[cent]<lo+0.2)).sum()>30 else "-" for lo in np.arange(0,1,0.2)))

# --- 折れ目（尾根）の本数 vs 半径、表裏それぞれ
def ridges(mask):
    r=[]
    for r0 in np.arange(0.15,0.96,0.1):
        m=mask&(np.abs(R-r0)<0.02)
        if m.sum()<300: continue
        lo,hi=np.percentile(phi[m],[1,99]); nb=400; bi=np.clip(((phi[m]-lo)/(hi-lo)*nb).astype(int),0,nb-1)
        s=np.bincount(bi,weights=pn[m],minlength=nb); c=np.bincount(bi,minlength=nb); h=np.where(c>0,s/np.maximum(c,1),np.nan); ok=~np.isnan(h)
        if ok.sum()<50: continue
        h=np.interp(np.arange(nb),np.where(ok)[0],h[ok]); hp=uniform_filter1d(h,3)-uniform_filter1d(h,41)
        r.append((r0,np.degrees(hi-lo),*[len(find_peaks(hp,prominence=p)[0]) for p in (0.003,0.008)]))
    return r
rr={}
for name,mask in (("front",side),("back",~side)):
    rr[name]=ridges(mask); print(name,"ridges: R | span(deg) | prom>0.003 | prom>0.008")
    for t in rr[name]: print("   %.2f %4.0f %3d %3d"%t)

fig,ax=plt.subplots(2,2,figsize=(13,10))
for name,c in (("front","C0"),("back","C1")):
    ax[0,0].plot([t[0] for t in rr[name]],[t[2] for t in rr[name]],"o-",c=c,label=name+" prom>0.003")
    ax[0,0].plot([t[0] for t in rr[name]],[t[3] for t in rr[name]],"s--",c=c,label=name+" prom>0.008")
    for sig,ls in ((0.02,"-"),(0.05,"--")):
        cent,D=out[name][sig]; b=out[name]["bd"][cent]; xs=np.arange(0,1,0.1)
        ax[0,1].plot(xs+0.05,[D[(b>=x)&(b<x+0.1)].mean() if ((b>=x)&(b<x+0.1)).sum()>30 else np.nan for x in xs],ls,c=c,label="%s sigma=%.2f"%(name,sig))
ax[0,0].legend(); ax[0,0].set_title("ridge count along arc vs normalized geodesic radius"); ax[0,1].legend(); ax[0,1].set_title("roughness vs normalized distance to outline")
cent,D=out["front"][0.02]; sc=ax[1,0].scatter(pl[cent],pa[cent],c=D,s=2,cmap="magma",vmax=np.percentile(D,98)); ax[1,0].set_aspect("equal"); ax[1,0].set_title("front: roughness D@0.02 (projected)"); plt.colorbar(sc,ax=ax[1,0])
cent,D=out["back"][0.02]; sc=ax[1,1].scatter(pl[cent],pa[cent],c=D,s=2,cmap="magma",vmax=np.percentile(D,98)); ax[1,1].set_aspect("equal"); ax[1,1].set_title("back: roughness D@0.02 (projected)"); plt.colorbar(sc,ax=ax[1,1])
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=100)
