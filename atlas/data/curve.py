import math
# Rodvold 1988 prior, 70 kg adult, CrCl 100 mL/min, adjusted = dosing weight = 70 kg (sample patient)
W=70.0; crcl=100.0
CL=0.0474*crcl+0.003*W          # L/h
Vdb=0.7*W                       # L
Vc=0.17*W                       # L
k21=0.46
beta=CL/Vdb; k10=CL/Vc; alpha=k10*k21/beta; k12=alpha+beta-k21-k10
dose=1000.0; tau=12.0; tinf=1.0; R=dose/tinf
# two-compartment infusion, superposition of doses (closed form)
def c_single(t):
    # concentration from one infusion started at t=0
    A=(alpha-k21)/(Vc*alpha*(alpha-beta)); B=(k21-beta)/(Vc*beta*(alpha-beta))
    if t<=0: return 0.0
    if t<=tinf:
        return R*(A*(1-math.exp(-alpha*t))+B*(1-math.exp(-beta*t)))
    return R*(A*(1-math.exp(-alpha*tinf))*math.exp(-alpha*(t-tinf))+B*(1-math.exp(-beta*tinf))*math.exp(-beta*(t-tinf)))
T=72.0; n=int(T/tau)
pts=[]
step=0.1
t=0.0
while t<=T+1e-9:
    c=sum(c_single(t-i*tau) for i in range(n))
    pts.append((t,c)); t+=step
cmax=max(c for _,c in pts)
print(f"CL={CL:.2f} Vdb={Vdb:.1f} Vc={Vc:.1f} beta={beta:.4f} k10={k10:.3f} alpha={alpha:.3f} k12={k12:.3f} cmax={cmax:.1f}")
# troughs
for i in range(1,n+1):
    tt=i*tau
    c=sum(c_single(tt-j*tau) for j in range(n))
    print(f"trough before dose {i+1} at {tt:.0f} h: {c:.1f}")
# auc24 at steady-ish (48-72)
auc=sum(((pts[k][1]+pts[k+1][1])/2)*step for k in range(len(pts)-1) if 48<=pts[k][0]<72)
print(f"AUC 48-72h: {auc:.0f} mg*h/L ; analytic ss AUC24 = {2*dose/CL:.0f}")
# svg polyline: plot area x 40..600 (0..72h), y 12..132 (ymax 40 mg/L)
X0,X1,Y0,Y1=44,604,14,134; YMAX=60.0
def sx(t): return X0+(X1-X0)*t/T
def sy(c): return Y1-(Y1-Y0)*min(c,YMAX)/YMAX
poly=" ".join(f"{sx(t):.1f},{sy(c):.1f}" for t,c in pts[::3])
open("poly.txt","w").write(poly)
print("band y for 15-20:",sy(20),sy(15))
area=[f"{sx(48):.1f},{sy(0):.1f}"]+[f"{sx(t):.1f},{sy(c):.1f}" for t,c in pts if 48-1e-9<=t<=72+1e-9][::2]+[f"{sx(72):.1f},{sy(0):.1f}"]
open("area.txt","w").write(" ".join(area))
print("ticks y:", {v:round(sy(v),1) for v in (0,20,40,60)})
print("ticks x:", {h:round(sx(h),1) for h in (0,12,24,36,48,60,72)})
print("trough y 7.5:", round(sy(7.5),1))
