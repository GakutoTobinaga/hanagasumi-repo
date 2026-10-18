import sys, numpy as np
for tag in ["t1","t2","t3","t4","t5","t6"]:
    d=np.load(f"/tmp/meshy/{tag}.npz"); V0=d["V"]
    q=np.round(V0/1e-5).astype(np.int64); _,first=np.unique(q,axis=0,return_index=True); V=V0[first]
    C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]
    P=C@vec  # 列: e1,e2,e3
    ext=[np.ptp(P[:,k]) for k in range(3)]
    # 旧ロジック: e1上で、20分割した幅(e2方向の広がり)の先頭4と末尾4を比較
    bins=np.linspace(P[:,0].min(),P[:,0].max(),21); wd=[np.ptp(P[(P[:,0]>=bins[i])&(P[:,0]<bins[i+1]),1]) for i in range(20)]
    old_end="e1-low" if np.mean(wd[:4])<np.mean(wd[-4:]) else "e1-high"
    # 新ロジック: e1,e2それぞれの両端のスラブ(両端5%)の、断面の大きさ（もう一方の面内軸の広がり×法線方向の広がり）
    cands=[]
    for ax,other in ((0,1),(1,0)):
        lo,hi=P[:,ax].min(),P[:,ax].max(); t=0.05*(hi-lo)
        for name,m in ((f"e{ax+1}-low",P[:,ax]<lo+t),(f"e{ax+1}-high",P[:,ax]>hi-t)):
            cands.append((np.ptp(P[m,other])*np.ptp(P[m,2]),name,np.ptp(P[m,other])))
    cands.sort()
    print("%s: extents e1 %.2f e2 %.2f e3 %.2f | 旧ロジックの付け根=%s | スラブ断面が最小の端=%s (幅%.2f)、次点=%s (幅%.2f)"%(tag,*ext,old_end,cands[0][1],cands[0][2],cands[1][1],cands[1][2]))
