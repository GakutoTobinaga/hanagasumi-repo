import bpy, numpy as np, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="/mnt/user-data/uploads/Meshy_AI_flower_petal_model_1018011222_image-to-3d-texture.glb")
objs=[o for o in bpy.data.objects if o.type=='MESH']
print("mesh objects:", [(o.name, len(o.data.vertices), len(o.data.polygons)) for o in objs])
o=objs[0]
dg=bpy.context.evaluated_depsgraph_get()
me=o.evaluated_get(dg).to_mesh()
me.calc_loop_triangles()
M=np.array(o.matrix_world)
V=np.empty(len(me.vertices)*3); me.vertices.foreach_get("co",V); V=V.reshape(-1,3)
V=(M[:3,:3]@V.T).T+M[:3,3]
N=np.empty(len(me.vertices)*3); me.vertices.foreach_get("normal",N); N=N.reshape(-1,3)
T=np.empty(len(me.loop_triangles)*3,dtype=np.int64); me.loop_triangles.foreach_get("vertices",T); T=T.reshape(-1,3)
print("verts",len(V),"tris",len(T))
print("bbox min",V.min(0).round(3),"max",V.max(0).round(3))
print("images:",[(i.name,tuple(i.size)) for i in bpy.data.images])
print("materials:",[m.name for m in bpy.data.materials])
np.savez("/tmp/meshy/petal.npz",V=V,N=N,T=T)
