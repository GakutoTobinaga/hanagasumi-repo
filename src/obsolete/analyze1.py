import numpy as np, scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

d=np.load("/tmp/meshy/petal.npz"); V0=d["V"]; N0=d["N"]; T0=d["T"]
# UV継ぎ目で分割された頂点を、位置が同じものどうし統合する
q=np.round(V0/1e-5).astype(np.int64)
_,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
V=V0[first]; N=np.zeros_like(V); np.add.at(N,inv,N0); N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
T=inv[T0]; keep=(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0]); T=T[keep]; nV=len(V)
print("welded: verts %d -> %d, tris %d -> %d"%(len(V0),nV,len(T0),len(T)))
# ---- edges
E=np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]); E.sort(axis=1)
key=E[:,0].astype(np.int64)*nV+E[:,1]
uk,cnt=np.unique(key,return_counts=True)
Eu=np.stack([uk//nV,uk%nV],1)
L=np.linalg.norm(V[Eu[:,0]]-V[Eu[:,1]],axis=1)
bmask=cnt==1
bverts=np.unique(Eu[bmask].ravel())
tri_area=0.5*np.linalg.norm(np.cross(V[T[:,1]]-V[T[:,0]],V[T[:,2]]-V[T[:,0]]),axis=1)
print("area %.3f  boundary verts %d  boundary length %.2f"%(tri_area.sum(),len(bverts),L[bmask].sum()))
print("edge len percentiles (5,25,50,75,95,99):",np.percentile(L,[5,25,50,75,95,99]).round(5))

# ---- PCA frame
C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); order=np.argsort(w)[::-1]; vec=vec[:,order]
a,l,n=vec[:,0],vec[:,1],vec[:,2]
proj=C@a
bins=np.linspace(proj.min(),proj.max(),21); widths=[]
for i in range(20):
    m=(proj>=bins[i])&(proj<bins[i+1])
    widths.append(np.ptp(C[m]@l) if m.sum()>10 else 0)
print("width along e1 bins:",np.round(widths,2))
if np.mean(widths[:4])>np.mean(widths[-4:]): a=-a; proj=-proj   # a: base -> tip (narrow end = base)
base_pts=np.argsort(proj)[:200]; base=base_pts[np.argmin(np.linalg.norm(V[base_pts]-V[base_pts].mean(0),axis=1))]
print("extents e1,e2,e3: %.2f %.2f %.2f"%(np.ptp(proj),np.ptp(C@l),np.ptp(C@n)),"base vertex",base,V[base].round(3))

# ---- geodesic distances
G=sp.coo_matrix((np.concatenate([L,L]),(np.concatenate([Eu[:,0],Eu[:,1]]),np.concatenate([Eu[:,1],Eu[:,0]]))),shape=(nV,nV)).tocsr()
dg=dijkstra(G,indices=base)                     # from base
db=dijkstra(G,indices=bverts,min_only=True)     # from boundary
print("finite geodesic frac %.3f  max geodesic from base %.2f"%(np.isfinite(dg).mean(),np.nanmax(dg[np.isfinite(dg)])))
R=dg/np.nanmax(dg[np.isfinite(dg)])

# ---- curvature proxy (normal change per length)
Ni,Nj=N[Eu[:,0]],N[Eu[:,1]]
ang=np.arccos(np.clip((Ni*Nj).sum(1),-1,1)); ke=ang/np.maximum(L,1e-9)
kv=np.zeros(nV); cv=np.zeros(nV)
np.add.at(kv,Eu[:,0],ke); np.add.at(kv,Eu[:,1],ke); np.add.at(cv,Eu[:,0],1); np.add.at(cv,Eu[:,1],1); kv/=np.maximum(cv,1)
Lv=np.zeros(nV); np.add.at(Lv,Eu[:,0],L); np.add.at(Lv,Eu[:,1],L); Lv/=np.maximum(cv,1)
print("curvature proxy percentiles (50,90,99):",np.percentile(kv,[50,90,99]).round(2),"  excess kurtosis of per-edge k: %.1f"%stats.kurtosis(ke))
idx=np.random.default_rng(0).choice(nV,60000,replace=False)
rho=stats.spearmanr(np.log(kv[idx]+1e-6),np.log(Lv[idx]))[0]
print("Spearman(log curvature, log local edge length) = %.2f  (negative = fine mesh where curved)"%rho)

# ---- curvature / edge length vs distance to boundary
bd=db/np.nanmax(db[np.isfinite(db)])
edges_b=np.linspace(0,1,11); rows=[]
for i in range(10):
    m=(bd>=edges_b[i])&(bd<edges_b[i+1])&np.isfinite(bd)
    if m.sum()>50: rows.append((edges_b[i],kv[m].mean(),Lv[m].mean(),m.sum()))
print("dist_to_boundary(norm) | mean curvature | mean edge len | n")
for r in rows: print("  %.1f  %.2f  %.5f  %d"%r)

# ---- ridge count vs geodesic radius from base
pa=(V-V[base])@a; pl=(V-V[base])@l; pn=(V-V[base])@n
phi=np.arctan2(pl,pa)
res=[]
for r0 in np.arange(0.15,0.96,0.1):
    m=(np.abs(R-r0)<0.02)&np.isfinite(R)
    if m.sum()<500: continue
    lo,hi=np.percentile(phi[m],[1,99]); nb=400
    bi=np.clip(((phi[m]-lo)/(hi-lo)*nb).astype(int),0,nb-1)
    s=np.bincount(bi,weights=pn[m],minlength=nb); c=np.bincount(bi,minlength=nb)
    h=np.where(c>0,s/np.maximum(c,1),np.nan); ok=~np.isnan(h)
    if ok.sum()<50: continue
    h=np.interp(np.arange(nb),np.where(ok)[0],h[ok])
    hp=uniform_filter1d(h,3)-uniform_filter1d(h,41)
    out=[]
    for pr in (0.003,0.008):
        pk,_=find_peaks(hp,prominence=pr); out.append(len(pk))
    res.append((r0,np.degrees(hi-lo),out[0],out[1]))
print("R | fan span(deg) | ridges(prom>0.003) | ridges(prom>0.008)")
for r in res: print("  %.2f  %.0f  %d  %d"%r)

# ---- figure
fig,ax=plt.subplots(2,2,figsize=(13,10))
ax[0,0].hist(np.log10(L),bins=80); ax[0,0].set_title("edge length (log10)"); 
ax[0,1].plot([r[0]+0.05 for r in rows],[r[1] for r in rows],"o-",label="mean curvature proxy"); ax[0,1].set_xlabel("normalized distance to boundary"); ax2=ax[0,1].twinx(); ax2.plot([r[0]+0.05 for r in rows],[r[2] for r in rows],"s--",c="C1",label="mean edge length"); ax[0,1].set_title("curvature & mesh density vs distance to edge")
ax[1,0].plot([r[0] for r in res],[r[2] for r in res],"o-",label="prom>0.003"); ax[1,0].plot([r[0] for r in res],[r[3] for r in res],"s-",label="prom>0.008"); ax[1,0].legend(); ax[1,0].set_xlabel("normalized geodesic radius from base"); ax[1,0].set_title("ridge count along arc vs radius")
sub=idx[np.isfinite(R[idx])]
sc=ax[1,1].scatter(pl[sub],pa[sub],c=np.log10(kv[sub]+1e-3),s=1,cmap="magma"); ax[1,1].set_aspect("equal"); ax[1,1].set_title("curvature proxy map (projection on mean plane)"); plt.colorbar(sc,ax=ax[1,1])
plt.tight_layout(); plt.savefig("/tmp/meshy/analysis1.png",dpi=110)
np.savez("/tmp/meshy/derived.npz",R=R,bd=bd,kv=kv,Lv=Lv,pa=pa,pl=pl,pn=pn,phi=phi,base=base)
