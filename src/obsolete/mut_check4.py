import sys, numpy as np
sys.argv=["x","--","/tmp/meshy/mutcheck"]
src=open("/mnt/user-data/outputs/hanagasumi_breeding_test.py",encoding="utf-8").read().split("PA = dict(")[0]
for a,b in (("rng.normal(0, 5)","rng.normal(0, 5*MUT)"),("rng.normal(0, 0.03)","rng.normal(0, 0.03*MUT)"),("rng.normal(0, 0.05)","rng.normal(0, 0.05*MUT)"),("rng.normal(0, 8)","rng.normal(0, 8*MUT)"),("rng.normal(0, 0.04)","rng.normal(0, 0.04*MUT)"),("if rng.random() < 0.15:","if rng.random() < 0.15*MUT:")):
    src=src.replace(a,b)
MUT=1.0; exec(src)
def natural_size(petals):
    A=np.concatenate([place(TYPES[p["type"]]["V"],p["theta"],p["phi"],p["roll"],p["scale"],0.04) for p in petals]); return float(np.hypot(A[:,0],A[:,1]).max()), float(A[:,2].max())
PA=dict(name="F2",N=8,layers=1,theta=55,az_jit=0.10,types=["t1","t2"],order="alternate",col=(0.72,0.35,300),grad=(0,0,0,0),seed=2)
PB=dict(name="F3",N=10,layers=2,theta=45,az_jit=0.15,types=["t3","t4","t6"],order="spiral",col=(0.80,0.45,350),grad=(1,0.6,0.5,0.3),seed=3)
for P_ in (PA,PB): P_["petals"]=make_flower2(P_,np.random.default_rng(P_["seed"])); P_["radius"],P_["height"]=natural_size(P_["petals"])
print("親 F2 半径%.2f 高さ%.2f | 親 F3 半径%.2f 高さ%.2f"%(PA["radius"],PA["height"],PB["radius"],PB["height"]))
lo_r,hi_r=min(PA["radius"],PB["radius"]),max(PA["radius"],PB["radius"]); lo_h,hi_h=min(PA["height"],PB["height"]),max(PA["height"],PB["height"])
for label,mut in (("突然変異なし",0.0),("突然変異あり",1.0)):
    MUT=mut; rng=np.random.default_rng(7); FXY=[];FZ=[];R=[];H=[];ST=[];TH=[]
    for i in range(240):
        c=breed(PA,PB,rng,"c"); pet=make_flower2(c,np.random.default_rng(100+i)); r0,h0=natural_size(pet)
        FXY.append(c["radius"]/r0); FZ.append(c["height"]/h0); R.append(c["radius"]); H.append(c["height"]); ST.append(c["grad"][1] if c["grad"][0] else 0.0); TH.append(c["theta"])
    FXY,FZ,R,H,ST,TH=map(np.array,(FXY,FZ,R,H,ST,TH))
    print("%s: 半径の範囲外%.0f%% 高さの範囲外%.0f%% | 横の拡縮5/50/95%% %.2f/%.2f/%.2f 縦 %.2f/%.2f/%.2f 縦横比5/95%% %.2f/%.2f | グラデ強さ 平均%.2f [%.2f,%.2f] あり%.0f%% | 開き角[%.0f,%.0f]"%(label,np.mean((R>hi_r+0.02)|(R<lo_r-0.02))*100,np.mean((H>hi_h+0.02)|(H<lo_h-0.02))*100,*np.percentile(FXY,[5,50,95]),*np.percentile(FZ,[5,50,95]),*np.percentile(FZ/FXY,[5,95]),ST.mean(),ST.min(),ST.max(),np.mean(ST>0)*100,TH.min(),TH.max()))
