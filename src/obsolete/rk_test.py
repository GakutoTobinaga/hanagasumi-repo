import bpy, numpy as np, sys, itertools
def run(dynamic, keys_first, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=40
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=40,y_subdivisions=40,size=1.0)
    o=bpy.context.active_object
    me=o.data
    co=np.empty(len(me.vertices)*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
    co[:,2]+=np.random.default_rng(0).uniform(-1e-4,1e-4,len(co)); me.vertices.foreach_set("co",co.ravel())
    vg=o.vertex_groups.new(name="pin"); vg.add([i for i,v in enumerate(co) if v[1]<-0.49],1.0,'REPLACE')
    def mk_keys():
        o.shape_key_add(name="Basis",from_mix=False)
        rk=o.shape_key_add(name="Rest",from_mix=False)
        r=co.copy(); r[:,0]*=scale; r[:,1]*=scale   # 等方に拡大した自然長
        rk.data.foreach_set("co",r.ravel()); return rk
    if keys_first: rk=mk_keys()
    m=o.modifiers.new("Cloth","CLOTH"); s=m.settings
    s.effector_weights.gravity=0.0; s.vertex_group_mass="pin"; s.quality=5
    if not keys_first: rk=mk_keys()
    s.use_dynamic_mesh=dynamic; s.rest_shape_key=rk
    m.collision_settings.use_collision=False
    for f in range(1,41): sc.frame_set(f)
    dg=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(dg).to_mesh()
    z=np.empty(len(ev.vertices)*3); ev.vertices.foreach_get("co",z); z=z.reshape(-1,3)
    return z[:,2].std(), np.ptp(z[:,0]), np.ptp(z[:,1])
for dyn,kf in itertools.product([False,True],[False,True]):
    for scale in (1.0,1.5):
        zs,px,py=run(dyn,kf,scale)
        print("dynamic=%d keys_first=%d rest_scale=%.1f -> z_std %.5f  x-extent %.3f y-extent %.3f"%(dyn,kf,scale,zs,px,py))
