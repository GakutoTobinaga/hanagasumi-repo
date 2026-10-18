import bpy, numpy as np
SPEC={"t1":"slab","t2":"slab","t3":"slab","t4":"xmax","t5":"slab","t6":"xmax"}   # 付け根: slab=端の断面が最小 / xmax=目視で確認した位置
TARGET=50000
def load(tag):
    d=np.load(f"/tmp/meshy/{tag}.npz"); V0=d["V"]; T0=d["T"]
    q=np.round(V0/1e-5).astype(np.int64); _,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
    V=V0[first]; T=inv[T0]; T=T[(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0])]; return V,T
def petal_frame(V,mode):
    C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]; P3=C@vec; best=None
    for ax in (0,1):
        other=1-ax; lo,hi=P3[:,ax].min(),P3[:,ax].max(); t=0.05*(hi-lo)
        for sign,mask in ((+1,P3[:,ax]<lo+t),(-1,P3[:,ax]>hi-t)):
            sec=np.ptp(P3[mask,other])*np.ptp(P3[mask,2])
            if best is None or sec<best[0]: best=(sec,ax,sign)
    _,ax,sign=best; a0=sign*vec[:,ax]; l0=vec[:,1-ax]
    if mode=="slab": cap=np.argsort(C@a0)[:200]
    else: cap=np.argsort(-(C@l0))[:200]
    base=cap[np.argmin(np.linalg.norm(V[cap]-V[cap].mean(0),axis=1))]
    dist=np.linalg.norm(V-V[base],axis=1); far=np.argsort(-dist)[:int(0.05*len(V))]
    a=V[far].mean(0)-V[base]; a/=np.linalg.norm(a)
    n=vec[:,2]-np.dot(vec[:,2],a)*a; n/=np.linalg.norm(n); l=np.cross(n,a)
    P=np.stack([(V-V[base])@l,(V-V[base])@n,(V-V[base])@a],1)
    Lm=P[:,2].max(); tip=P[:,2]>0.85*Lm
    if P[tip,1].mean()<0:   # 先端が+n側に反るように（花の内側に向かって曲がる）
        n=-n; l=np.cross(n,a); P=np.stack([(V-V[base])@l,(V-V[base])@n,(V-V[base])@a],1)
    return P
for tag,mode in SPEC.items():
    V,T=load(tag); P=petal_frame(V,mode); Lm=P[:,2].max(); P=P/Lm
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me=bpy.data.meshes.new("p"); nv=len(P); m=len(T)
    me.vertices.add(nv); me.vertices.foreach_set("co",P.astype(np.float32).ravel())
    me.loops.add(3*m); me.loops.foreach_set("vertex_index",T.astype(np.int32).ravel())
    me.polygons.add(m); me.polygons.foreach_set("loop_start",np.arange(0,3*m,3,dtype=np.int32)); me.polygons.foreach_set("loop_total",np.full(m,3,dtype=np.int32)); me.update(calc_edges=True)
    ob=bpy.data.objects.new("p",me); bpy.context.scene.collection.objects.link(ob)
    md=ob.modifiers.new("d","DECIMATE"); md.decimate_type='COLLAPSE'; md.ratio=min(1.0,TARGET/m); md.use_collapse_triangulate=True
    dg=bpy.context.evaluated_depsgraph_get(); ev=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg); ev.calc_loop_triangles()
    Vd=np.empty(len(ev.vertices)*3); ev.vertices.foreach_get("co",Vd); Vd=Vd.reshape(-1,3)
    Td=np.empty(len(ev.loop_triangles)*3,dtype=np.int64); ev.loop_triangles.foreach_get("vertices",Td); Td=Td.reshape(-1,3)
    r=np.linalg.norm(Vd,axis=1); r/=r.max()
    np.savez(f"/tmp/meshy/dec_{tag}.npz",V=Vd,T=Td,r=r,Lm=Lm)
    print(tag,"tris %d -> %d | width %.2f depth %.2f (length=1.00) | original length %.2f"%(m,len(Td),np.ptp(Vd[:,0]),np.ptp(Vd[:,1]),Lm))
