import sys, math, numpy as np, bpy
from mathutils import Vector
tag=sys.argv[sys.argv.index("--")+1]; out=sys.argv[sys.argv.index("--")+2]
d=np.load(f"/tmp/meshy/{tag}.npz"); V0=d["V"]; T0=d["T"]
q=np.round(V0/1e-5).astype(np.int64); _,first,inv=np.unique(q,axis=0,return_index=True,return_inverse=True); inv=inv.ravel()
V=V0[first]; T=inv[T0]; T=T[(T[:,0]!=T[:,1])&(T[:,1]!=T[:,2])&(T[:,2]!=T[:,0])]
C=V-V.mean(0); w,vec=np.linalg.eigh(np.cov(C.T)); vec=vec[:,np.argsort(w)[::-1]]; P3=C@vec; best=None
for ax in (0,1):
    other=1-ax; lo,hi=P3[:,ax].min(),P3[:,ax].max(); t=0.05*(hi-lo)
    for sign,mask in ((+1,P3[:,ax]<lo+t),(-1,P3[:,ax]>hi-t)):
        sec=np.ptp(P3[mask,other])*np.ptp(P3[mask,2])
        if best is None or sec<best[0]: best=(sec,ax,sign)
_,ax,sign=best
a=sign*vec[:,ax]; l=vec[:,1-ax]; n=vec[:,2]
if np.dot(np.cross(l,n),a)<0: n=-n
pa=C@a; pa-=pa.min(); P=np.stack([C@l,C@n,pa],1); P[:,0]-=P[:,0].mean()
Lm=P[:,2].max(); base_pt=P[P[:,2]<0.03*Lm].mean(0); far_pt=P[P[:,2]>0.97*Lm].mean(0)
print(tag,"detected base (red) at",base_pt.round(2),"opposite end (blue) at",far_pt.round(2),"length %.2f width %.2f"%(Lm,np.ptp(P[:,0])))
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
me=bpy.data.meshes.new("p"); nv=len(P); m=len(T)
me.vertices.add(nv); me.vertices.foreach_set("co",P.astype(np.float32).ravel())
me.loops.add(3*m); me.loops.foreach_set("vertex_index",T.astype(np.int32).ravel())
me.polygons.add(m); me.polygons.foreach_set("loop_start",np.arange(0,3*m,3,dtype=np.int32)); me.polygons.foreach_set("loop_total",np.full(m,3,dtype=np.int32))
me.polygons.foreach_set("use_smooth",np.ones(m,dtype=bool)); me.update(calc_edges=True)
ob=bpy.data.objects.new("p",me); ob.color=(0.80,0.78,0.90,1); sc.collection.objects.link(ob)
for pt,col in ((base_pt,(1,0.05,0.05,1)),(far_pt,(0.1,0.3,1,1))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07,location=tuple(pt)); s=bpy.context.active_object; s.color=col
sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=800; sc.render.resolution_y=900
sc.view_settings.view_transform='Standard'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
wd=bpy.data.worlds.new("w"); wd.color=(1,1,1); sc.world=wd
center=Vector((0,0,Lm*0.5))
def shot(off,path):
    cd=bpy.data.cameras.new("c"); cd.type='ORTHO'; cd.ortho_scale=max(Lm,np.ptp(P[:,0]))*1.25
    cam=bpy.data.objects.new("c",cd); sc.collection.objects.link(cam); cam.location=center+Vector(off)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler(); sc.camera=cam; sc.render.filepath=path
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam,do_unlink=True)
shot((0,-8,0),out+"_a.png"); shot((0,8,0),out+"_b.png"); shot((-4,-6,3),out+"_c.png")
