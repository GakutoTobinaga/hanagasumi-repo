import sys, numpy as np
sys.argv=["x","--","/tmp/meshy/mutcheck"]
src=open("/mnt/user-data/outputs/hanagasumi_breeding_test.py",encoding="utf-8").read().split("PA = dict(")[0]
for a,b in (("rng.normal(0, 5)","rng.normal(0, 5*MUT)"),("rng.normal(0, 0.03)","rng.normal(0, 0.03*MUT)"),("rng.normal(0, 0.05)","rng.normal(0, 0.05*MUT)"),("rng.normal(0, 8)","rng.normal(0, 8*MUT)"),("if rng.random() < 0.15:","if rng.random() < 0.15*MUT:")):
    assert a in src,a; src=src.replace(a,b)
MUT=1.0
exec(src)
PA=dict(name="F2", N=8,layers=1,theta=55,az_jit=0.10,types=["t1","t2"],order="alternate",col=(0.72,0.35,300),grad=(0,0,0,0),seed=2)
PB=dict(name="F3", N=10,layers=2,theta=45,az_jit=0.15,types=["t3","t4","t6"],order="spiral",col=(0.80,0.45,350),grad=(1,0.6,0.5,0.3),seed=3)
for P_ in (PA,PB): P_["petals"]=make_flower2(P_,np.random.default_rng(P_["seed"]))
def pheno(g,seed):
    pet=g["petals"] if "petals" in g else make_flower2(g,np.random.default_rng(seed)); allv=[]
    for p in pet:
        d=TYPES[p["type"]]; allv.append(place(d["V"],p["theta"],p["phi"],p["roll"],p["scale"],0.04))
    A=np.concatenate(allv); return float(np.hypot(A[:,0],A[:,1]).max()), float(A[:,2].max())
rA,hA=pheno(PA,0); rB,hB=pheno(PB,0); print("親 F2 半径%.2f 高さ%.2f | 親 F3 半径%.2f 高さ%.2f"%(rA,hA,rB,hB))
lo_r,hi_r=min(rA,rB),max(rA,rB); lo_h,hi_h=min(hA,hB),max(hA,hB)
res={}
for label,mut in (("突然変異あり",1.0),("突然変異なし",0.0)):
    MUT=mut; rng=np.random.default_rng(7); R=[];H=[];TH=[];LY=[];GR=[]
    for i in range(240):
        c=breed(PA,PB,rng,"c"); r,h=pheno(c,100+i); R.append(r);H.append(h);TH.append(c["theta"]);LY.append(c["layers"]);GR.append(c["grad"][0])
    R=np.array(R);H=np.array(H);TH=np.array(TH);LY=np.array(LY)
    out_r=np.mean((R>hi_r+0.02)|(R<lo_r-0.02)); out_h=np.mean((H>hi_h+0.02)|(H<lo_h-0.02)); above=np.mean(R>hi_r+0.02)
    print("%s: 半径 範囲[%.2f,%.2f] 平均%.2f | 親の範囲外(±0.02) 半径%.0f%% (うち大きい側%.0f%%) 高さ%.0f%% | 層2の割合%.0f%% | グラデあり%.0f%%"%(label,R.min(),R.max(),R.mean(),out_r*100,above*100,out_h*100,np.mean(LY==2)*100,np.mean(GR)*100))
    res[label]=(R,H,TH,LY)
# 層と開き角の組み合わせで、半径がどう変わるか（突然変異なし）
R,H,TH,LY=res["突然変異なし"]
print("--- 突然変異なし: 層と開き角ごとの半径の平均")
for ly in (1,2):
    for lo,hi in ((44,48),(48,52),(52,56)):
        m=(LY==ly)&(TH>=lo)&(TH<hi)
        if m.sum()>3: print("  層%d 開き角%d-%d度: 半径平均%.2f (n=%d)"%(ly,lo,hi,R[m].mean(),m.sum()))
