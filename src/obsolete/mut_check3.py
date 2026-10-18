import sys, numpy as np
sys.argv=["x","--","/tmp/meshy/mutcheck"]
src=open("/mnt/user-data/outputs/hanagasumi_breeding_test.py",encoding="utf-8").read().split("PA = dict(")[0]
for a,b in (("rng.normal(0, 5)","rng.normal(0, 5*MUT)"),("rng.normal(0, 0.03)","rng.normal(0, 0.03*MUT)"),("rng.normal(0, 0.05)","rng.normal(0, 0.05*MUT)"),("rng.normal(0, 8)","rng.normal(0, 8*MUT)"),("rng.normal(0, 0.04)","rng.normal(0, 0.04*MUT)"),("if rng.random() < 0.15:","if rng.random() < 0.15*MUT:")):
    src=src.replace(a,b)
MUT=1.0; exec(src)
PA=dict(name="F2",N=8,layers=1,theta=55,az_jit=0.10,types=["t1","t2"],order="alternate",col=(0.72,0.35,300),grad=(0,0,0,0),radius=0.93,seed=2)
PB=dict(name="F3",N=10,layers=2,theta=45,az_jit=0.15,types=["t3","t4","t6"],order="spiral",col=(0.80,0.45,350),grad=(1,0.6,0.5,0.3),radius=1.00,seed=3)
for P_ in (PA,PB): P_["petals"]=make_flower2(P_,np.random.default_rng(P_["seed"]))
def natural(g,seed):
    pet=g["petals"] if "petals" in g else make_flower2(g,np.random.default_rng(seed))
    A=np.concatenate([place(TYPES[p["type"]]["V"],p["theta"],p["phi"],p["roll"],p["scale"],0.04) for p in pet])
    return float(np.hypot(A[:,0],A[:,1]).max()), float(A[:,2].max())
_,hA=natural(PA,0); _,hB=natural(PB,0); PA["height"]=hA; PB["height"]=hB
print("親の高さ(自然): F2 %.2f / F3 %.2f"%(hA,hB))
for label,mut in (("突然変異なし",0.0),("突然変異あり",1.0)):
    MUT=mut; rng=np.random.default_rng(7); FXY=[];FZ=[];Rr=[];Hh=[]
    for i in range(240):
        c=breed(PA,PB,rng,"c"); a=c["alpha"]
        c["height"]=float(np.clip(a*hA+(1-a)*hB+rng.normal(0,0.04*MUT),0.4,1.2))
        r0,h0=natural(c,100+i); FXY.append(c["radius"]/r0); FZ.append(c["height"]/h0); Rr.append(c["radius"]); Hh.append(c["height"])
    FXY=np.array(FXY);FZ=np.array(FZ);Rr=np.array(Rr);Hh=np.array(Hh)
    lo_r,hi_r=0.93,1.00; lo_h,hi_h=min(hA,hB),max(hA,hB)
    print("%s: 半径の範囲外%.0f%% 高さの範囲外%.0f%% | 横方向の拡縮 5/50/95%%点 %.2f/%.2f/%.2f | 縦方向の拡縮 %.2f/%.2f/%.2f | 縦/横の比 5/95%%点 %.2f/%.2f"%(label,np.mean((Rr>hi_r+0.02)|(Rr<lo_r-0.02))*100,np.mean((Hh>hi_h+0.02)|(Hh<lo_h-0.02))*100,*np.percentile(FXY,[5,50,95]),*np.percentile(FZ,[5,50,95]),*np.percentile(FZ/FXY,[5,95])))
