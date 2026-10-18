import sys, json, numpy as np
from scipy.spatial import cKDTree
d=np.load(sys.argv[1]); label=sys.argv[2]
V0=d["V"]; N0=d["N"]; T0=d["T"]
q=np.round(V0/1e-5).astype(np.int64)
_,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
V=V0[first]; N=np.zeros_like(V); np.add.at(N,inv,N0); N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
T=inv[T0]; T=T[(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0])]; nV=len(V)
tri_a=0.5*np.linalg.norm(np.cross(V[T[:,1]]-V[T[:,0]],V[T[:,2]]-V[T[:,0]]),axis=1)
va=np.zeros(nV)
for k in range(3): np.add.at(va,T[:,k],tri_a/3)
# フレーム（base→tip, 横, 法線）
C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]
a,l,n=vec[:,0],vec[:,1],vec[:,2]; proj=C@a
bins=np.linspace(proj.min(),proj.max(),21); wd=[np.ptp(C[(proj>=bins[i])&(proj<bins[i+1])]@l) for i in range(20)]
if np.mean(wd[:4])>np.mean(wd[-4:]): a=-a; proj=-proj
pl=C@l; pn=C@n; pa=proj
cen=(va*pl).sum()/va.sum()          # 面積加重の中心線
x=pl-cen; half=max(abs(x.min()),abs(x.max()))
left=x<0; right=~left
rng=np.random.default_rng(0)
# 1) 粗さ D@0.02（表裏を別々に、左右で平均）
side=(N@n)>0
def disp(mask,sig=0.02,ncent=20000):
    ids=np.where(mask)[0]; tr=cKDTree(V[ids]); cent=rng.choice(ids,min(ncent,len(ids)),replace=False)
    nb=tr.query_ball_point(V[cent],sig); D=np.empty(len(cent))
    for t,lst in enumerate(nb):
        j=ids[lst]; v=(va[j,None]*N[j]).sum(0)/va[j].sum(); D[t]=1-np.linalg.norm(v)
    return cent,D
Dl=[];Dr=[]
for m in (side,~side):
    c,D=disp(m); Dl+=list(D[left[c]]); Dr+=list(D[right[c]])
DL,DR=float(np.mean(Dl)),float(np.mean(Dr))
# 2) 重なり: 投影面の同じセルに、法線方向に離れた層が複数あるか
cs=0.004; gi=((x-x.min())/cs).astype(int); gj=((pa-pa.min())/cs).astype(int); key=gi.astype(np.int64)*100000+gj
order=np.argsort(key); ks=key[order]; pn_s=pn[order]; x_s=x[order]
uk,start=np.unique(ks,return_index=True); end=np.r_[start[1:],len(ks)]
spread=np.array([pn_s[s:e].max()-pn_s[s:e].min() for s,e in zip(start,end)]); xc=np.array([x_s[s:e].mean() for s,e in zip(start,end)])
ov=spread>0.08
oL=float(ov[xc<0].mean()) if (xc<0).any() else 0.0; oR=float(ov[xc>=0].mean()) if (xc>=0).any() else 0.0
# 3) 縁の傾き: 横方向の外側15%で、法線が平均面の法線からどれだけ傾くか（1=平ら、小さいほど巻いている）
rimL=np.abs(N[(x<-0.85*half)]@n); rimR=np.abs(N[(x>0.85*half)]@n)
rL=float(rimL.mean()) if len(rimL) else np.nan; rR=float(rimR.mean()) if len(rimR) else np.nan
def asym(p,q): return abs(p-q)/(p+q) if (p+q)>0 else 0.0
out=dict(sample=label,verts=nV,D_left=DL,D_right=DR,asym_D=asym(DL,DR),overlap_left=oL,overlap_right=oR,overlap_total=float(ov.mean()),asym_overlap=asym(oL,oR),rim_flat_left=rL,rim_flat_right=rR,asym_rim=abs(rL-rR))
print(json.dumps(out))
