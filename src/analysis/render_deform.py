import sys, math, numpy as np, bpy
from mathutils import Vector
src=open("/tmp/meshy/deform_test.py").read().split("conds=")[0]
exec(src.replace("import sys, json, numpy as np",""))
tag=sys.argv[sys.argv.index("--")+1]; out=sys.argv[sys.argv.index("--")+2]
V,T=load(f"/tmp/meshy/{tag}.npz"); P=frame(V,T)
conds=[("original",1,1,0,0),("width0.8",0.8,1,0,0),("width1.2",1.2,1,0,0),("bend+0.3",1,1,0.3,0),("trough0.3",1,1,0,0.3),("combo",0.9,1.1,0.2,0.2)]
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
spacing=2.0
for i,(name,sw,sl,b,t) in enumerate(conds):
    Q=deform(P,sw,sl,b,t); Q[:,0]+=(i-(len(conds)-1)/2)*spacing
    me=bpy.data.meshes.new(name); n=len(Q); m=len(T)
    me.vertices.add(n); me.vertices.foreach_set("co",Q.astype(np.float32).ravel())
    me.loops.add(3*m); me.loops.foreach_set("vertex_index",T.astype(np.int32).ravel())
    me.polygons.add(m); me.polygons.foreach_set("loop_start",np.arange(0,3*m,3,dtype=np.int32)); me.polygons.foreach_set("loop_total",np.full(m,3,dtype=np.int32))
    me.polygons.foreach_set("use_smooth",np.ones(m,dtype=bool)); me.update(calc_edges=True)
    ob=bpy.data.objects.new(name,me); sc.collection.objects.link(ob)
    cu=bpy.data.curves.new("l","FONT"); cu.body=name; cu.size=0.14; cu.align_x='CENTER'
    lb=bpy.data.objects.new("l",cu); lb.location=((i-(len(conds)-1)/2)*spacing,0,-0.15); lb.rotation_euler=(math.pi/2,0,0); sc.collection.objects.link(lb)
sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=2400; sc.render.resolution_y=1000
sc.view_settings.view_transform='Standard'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='SINGLE'; sh.single_color=(0.78,0.74,0.90); sh.show_cavity=True
w=bpy.data.worlds.new("w"); w.color=(1,1,1); sc.world=w
Lm=float(np.ptp(P[:,2])); center=Vector((0,0,Lm*0.5))
def shot(off,path,scale):
    cd=bpy.data.cameras.new("c"); cd.type='ORTHO'; cd.ortho_scale=scale
    cam=bpy.data.objects.new("c",cd); sc.collection.objects.link(cam); cam.location=center+Vector(off)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler(); sc.camera=cam; sc.render.filepath=path
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam,do_unlink=True)
shot((0,-12,0),out+"_front.png",13.0)
shot((-5,-10,5),out+"_3q.png",13.0)
print("[done render]",tag)
