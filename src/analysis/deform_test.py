import sys, json, numpy as np
def load(path):
    d=np.load(path); V0=d["V"]; T0=d["T"]
    q=np.round(V0/1e-5).astype(np.int64)
    _,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
    V=V0[first]; T=inv[T0]; T=T[(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0])]
    return V,T
def frame(V,T):
    nV=len(V); ta=0.5*np.linalg.norm(np.cross(V[T[:,1]]-V[T[:,0]],V[T[:,2]]-V[T[:,0]]),axis=1)
    va=np.zeros(nV)
    for k in range(3): np.add.at(va,T[:,k],ta/3)
    C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]
    a,l,n=vec[:,0],vec[:,1],vec[:,2]; proj=C@a
    bins=np.linspace(proj.min(),proj.max(),21); wd=[np.ptp(C[(proj>=bins[i])&(proj<bins[i+1])]@l) for i in range(20)]
    if np.mean(wd[:4])>np.mean(wd[-4:]): a=-a
    # 右手系にそろえる（反転を避ける）
    if np.dot(np.cross(l,n),a)<0: n=-n
    pa=(V-V.mean(0))@a; pa-=pa.min()
    pl=(V-V.mean(0))@l; pl-=(va*pl).sum()/va.sum()
    pn=(V-V.mean(0))@n
    return np.stack([pl,pn,pa],1)       # x=横, y=法線, z=付け根→先端
def vnormals(P,T):
    fn=np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]]); N=np.zeros_like(P)
    for k in range(3): np.add.at(N,T[:,k],fn)
    return N/np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
def edges(T,nV):
    E=np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]); E.sort(axis=1)
    uk=np.unique(E[:,0].astype(np.int64)*nV+E[:,1]); return np.stack([uk//nV,uk%nV],1)
def deform(P,sw,sl,bend,trough):
    Lm=np.ptp(P[:,2]); Wm=np.ptp(P[:,0]); Q=P.copy()
    Q[:,0]=P[:,0]*sw; Q[:,2]=P[:,2]*sl
    Q[:,1]=P[:,1]+bend*Lm*(P[:,2]/Lm)**2+trough*(Wm/2)*(P[:,0]/(Wm/2))**2
    return Q
def overlap(P,cs=0.004):
    gi=((P[:,0]-P[:,0].min())/cs).astype(int); gj=((P[:,2]-P[:,2].min())/cs).astype(int); key=gi.astype(np.int64)*100000+gj
    o=np.argsort(key); ks=key[o]; y=P[o,1]; uk,st=np.unique(ks,return_index=True); en=np.r_[st[1:],len(ks)]
    return float(np.mean([y[s:e].max()-y[s:e].min()>0.08 for s,e in zip(st,en)]))
def area(P,T): return float(0.5*np.linalg.norm(np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]]),axis=1).sum())
conds=[("identity",1,1,0,0),("width0.8",0.8,1,0,0),("width1.2",1.2,1,0,0),("length0.8",1,0.8,0,0),("length1.2",1,1.2,0,0),
       ("bend+0.3",1,1,0.3,0),("bend-0.3",1,1,-0.3,0),("trough0.3",1,1,0,0.3),("combo",0.9,1.1,0.2,0.2)]
res={}
for tag in sys.argv[1:]:
    V,T=load(f"/tmp/meshy/{tag}.npz"); P=frame(V,T); E=edges(T,len(P)); N0=vnormals(P,T)
    L0=np.linalg.norm(P[E[:,0]]-P[E[:,1]],axis=1); a0=area(P,T); o0=overlap(P)
    ang0=np.arccos(np.clip((N0[E[:,0]]*N0[E[:,1]]).sum(1),-1,1))
    print("== %s  verts %d  length %.2f width %.2f depth %.2f  overlap %.3f"%(tag,len(P),np.ptp(P[:,2]),np.ptp(P[:,0]),np.ptp(P[:,1]),o0))
    print("%-10s | edge stretch p5/p50/p95 | normal change deg p50/p95 | crease p95 ratio | overlap | area ratio"%"condition")
    for name,sw,sl,b,t in conds:
        Q=deform(P,sw,sl,b,t); N1=vnormals(Q,T)
        L1=np.linalg.norm(Q[E[:,0]]-Q[E[:,1]],axis=1); st=np.percentile(L1/np.maximum(L0,1e-9),[5,50,95])
        dn=np.degrees(np.arccos(np.clip((N0*N1).sum(1),-1,1)))
        ang1=np.arccos(np.clip((N1[E[:,0]]*N1[E[:,1]]).sum(1),-1,1))
        cr=np.percentile(ang1,95)/max(np.percentile(ang0,95),1e-9)
        print("%-10s |  %.2f / %.2f / %.2f      |  %5.1f / %5.1f          |  %.2f             | %.3f   | %.2f"%(name,*st,np.percentile(dn,50),np.percentile(dn,95),cr,overlap(Q),area(Q,T)/a0))
