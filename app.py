# Pump Line Calculator – SI
# NPSH_available, Δp pe aspirație (S) și refulare (D), p1/p2 la duzele pompei.
# Selectezi fittingurile dintr-o bibliotecă simplă (K sau Δp fix [bar]).

import math
import pandas as pd
import streamlit as st

# ---- stil "wide" fără set_page_config (evită StreamlitAPIException) ----
st.markdown("""
<style>
.block-container {max-width: 1200px; padding-top: 1rem; padding-bottom: 2rem;}
</style>
""", unsafe_allow_html=True)

g = 9.80665  # m/s²

# ---------- Bibliotecă fittinguri (editabilă) ----------
# col: grup, denumire, tip("K" sau "dp"), valoare, notă
LIB = pd.DataFrame([
    ["Elbow",   "Elbow 90° (LR)",   "K", 0.30, "0.2–0.4"],
    ["Elbow",   "Elbow 45°",        "K", 0.20, "0.15–0.3"],
    ["Tee",     "Tee – run",        "K", 0.60, ""],
    ["Tee",     "Tee – branch",     "K", 1.80, ""],
    ["Valve",   "Ball (full bore)", "K", 0.05, ""],
    ["Valve",   "Gate (open)",      "K", 0.15, ""],
    ["Valve",   "Globe (open)",     "K", 10.0, ""],
    ["Valve",   "Butterfly (open)", "K", 0.70, ""],
    ["Check",   "Check (swing)",    "K", 2.00, ""],
    ["Meter",   "Mag meter",        "K", 0.30, "vendor>lib"],
    ["Strainer","Y-strainer clean", "dp", 0.05, "bar/buc"],
    ["Strainer","Basket clean",     "dp", 0.10, "bar/buc"],
    ["Filter",  "Cartridge clean",  "dp", 0.20, "bar/buc"],
    ["Reducer", "Reducer gradual",  "K", 0.30, "0.2–0.5"],
    ["Instr.",  "Probe (LSL/FSL)",  "K", 0.05, ""],
], columns=["grp","item","tip","val","note"])

# ---------- Helpers ----------
def Re(rho, v, D, mu): 
    return rho * v * D / mu

def f_swamee_jain(Rey, eps, D):
    if Rey <= 0: 
        return 0.0
    return 0.25 / (math.log10(eps/(3.7*D) + 5.74/(Rey**0.9))**2)

def h_major(f, L, D, v): 
    return f * (L/D) * (v*v) / (2*g)

def h_minor(Ksum, v):     
    return Ksum * (v*v) / (2*g)

def dp_pa(rho, h):        # transformă head [m] în presiune [Pa]
    return rho * g * h

def pa_to_bar(pa):        # Pa -> bar
    return pa / 1e5

def bar_to_pa(bar):       # bar -> Pa
    return bar * 1e5

def ui_line(title, Dmm_def, L_def, epsmm_def, multiselect_key):
    """UI pentru o linie (S sau D). Returnează D[m], L[m], eps[m], Ksum[-], dpsum_bar[bar], df_items."""
    st.subheader(title)
    c1,c2,c3 = st.columns(3)
    with c1:
        D_mm = st.number_input("D [mm]", 5.0, 2000.0, Dmm_def, 1.0, key=title+"D")
        D = D_mm / 1000.0
    with c2:
        L = st.number_input("L [m]", 0.0, 20000.0, L_def, 0.5, key=title+"L")
    with c3:
        eps = st.number_input("ε [mm]", 0.0, 2.0, epsmm_def, 0.005, key=title+"eps") / 1000.0

    st.caption("Alege fittingurile și cantitățile. La elementele **dp**, Δp este în **bar/buc**.")
    items = st.multiselect("Fittings", LIB["item"].tolist(), default=[], key=multiselect_key)

    rows = []
    for it in items:
        r = LIB[LIB.item == it].iloc[0]
        q = st.number_input(f"{it} – Qty", 0, 200, 1, key=title+it)
        if q > 0:
            rows.append({"item": it, "tip": r["tip"], "val": r["val"], "qty": q})
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["item","tip","val","qty"])

    # ΣK și ΣΔp(bar)
    Ksum = float((df.query("tip=='K'")["val"] * df.query("tip=='K'")["qty"]).sum()) if not df.empty else 0.0
    dpsum_bar = float((df.query("tip=='dp'")["val"] * df.query("tip=='dp'")["qty"]).sum()) if not df.empty else 0.0

    # extra K manual (opțional)
    Ksum = st.number_input("K (extra) [-]", 0.0, 500.0, Ksum, 0.1, key=title+"Kextra")
    return D, L, eps, Ksum, dpsum_bar, df

# ---------- Inputuri generale ----------
st.title("Pump Line Calculator – SI (simplu)")

s1,s2,s3,s4 = st.columns(4)
with s1: rho = st.number_input("ρ [kg/m³]", 100.0, 3000.0, 1000.0, 1.0)
with s2: mu  = st.number_input("μ [mPa·s]", 0.1, 5000.0, 1.0, 0.1) / 1000.0  # Pa·s
with s3: Q   = st.number_input("Q [m³/h]", 0.01, 200000.0, 50.0, 0.1) / 3600.0  # m³/s
with s4: Pv  = bar_to_pa(st.number_input("P_vap [bar(abs)]", 0.0, 15.0, 0.023, 0.001))

b1,b2,b3,b4 = st.columns(4)
with b1: Ps = bar_to_pa(st.number_input("P_s (rezervor) [bar(abs)]", 0.0, 50.0, 1.013, 0.01))
with b2: Pd = bar_to_pa(st.number_input("P_d (destinație) [bar(abs)]", 0.0, 100.0, 1.013, 0.01))
with b3: Dz_S = st.number_input("Δz_S [m]", -100.0, 200.0, 2.0, 0.1, help="(+): suprafața peste pompă")
with b4: Dz_D = st.number_input("Δz_D [m]", -200.0, 500.0, 10.0, 0.1, help="(+): destinația peste pompă")

# ---------- Linii S și D ----------
D_S, L_S, eps_S, K_S, dpsumS_bar, dfS = ui_line("S (Suction)", 100.0, 20.0, 0.045, "selS")
D_D, L_D, eps_D, K_D, dpsumD_bar, dfD = ui_line("D (Discharge)", 80.0, 80.0, 0.045, "selD")

# ---------- Calcule ----------
# viteze
A_S = math.pi * D_S**2 / 4.0
A_D = math.pi * D_D**2 / 4.0
v_S = Q / A_S
v_D = Q / A_D

# Reynolds + factor frecare
Re_S = Re(rho, v_S, D_S, mu)
Re_D = Re(rho, v_D, D_D, mu)
f_S  = f_swamee_jain(Re_S, eps_S, D_S)
f_D  = f_swamee_jain(Re_D, eps_D, D_D)

# head pierderi (m): majore + minore + echivalent Δp fix
h_S = h_major(f_S, L_S, D_S, v_S) + h_minor(K_S, v_S) + bar_to_pa(dpsumS_bar) / (rho * g)
h_D = h_major(f_D, L_D, D_D, v_D) + h_minor(K_D, v_D) + bar_to_pa(dpsumD_bar) / (rho * g)

# presiuni absolute în duze
p1 = Ps + dp_pa(rho, Dz_S - h_S)      # aspirație (la pompă)
p2 = Pd + dp_pa(rho, Dz_D + h_D)      # refulare (la pompă)

# NPSH_available (cap total la secțiunea S minus Pvap)
NPSH_a = p1 / (rho * g) + v_S**2 / (2 * g) - Pv / (rho * g)

# ---------- Rezultate ----------
st.markdown("---")
c1,c2,c3 = st.columns(3)
with c1:
    st.metric("v_S [m/s]", f"{v_S:.3f}")
    st.metric("Re_S [-]", f"{Re_S:,.0f}")
    st.metric("f_S [-]", f"{f_S:.4f}")
    st.metric("h_S [m]", f"{h_S:.3f}")
with c2:
    st.metric("v_D [m/s]", f"{v_D:.3f}")
    st.metric("Re_D [-]", f"{Re_D:,.0f}")
    st.metric("f_D [-]", f"{f_D:.4f}")
    st.metric("h_D [m]", f"{h_D:.3f}")
with c3:
    st.metric("p₁ (S nozzle) [bar(abs)]", f"{pa_to_bar(p1):.3f}")
    st.metric("p₂ (D nozzle) [bar(abs)]", f"{pa_to_bar(p2):.3f}")
    st.metric("NPSH_a [m]", f"{NPSH_a:.3f}")

# tabel sumar
tbl = pd.DataFrame({
    "Mărime": ["ρ","μ","Q","D_S","L_S","ε_S","K_S","Δp_S[bar]","D_D","L_D","ε_D","K_D","Δp_D[bar]","p₁","p₂","NPSH_a"],
    "Valoare":[rho, mu*1000, Q*3600, D_S*1000, L_S, eps_S*1000, K_S, dpsumS_bar,
               D_D*1000, L_D, eps_D*1000, K_D, dpsumD_bar, pa_to_bar(p1), pa_to_bar(p2), NPSH_a],
    "Unități":["kg/m³","mPa·s","m³/h","mm","m","mm","-","bar","mm","m","mm","-","bar","bar(abs)","bar(abs)","m"]
})
st.dataframe(tbl, use_container_width=True)

# tips rapide
tips = []
if v_S > 1.5: tips.append("v_S > 1.5 m/s – reduce viteza pe aspirație.")
if K_S > 5:   tips.append("K_S mare – folosește coturi LR / armături cu K mic.")
if NPSH_a < 2: tips.append("NPSH_a < 2 m – risc de cavitație.")
if tips:
    st.subheader("Tips")
    for t in tips:
        st.write("• " + t)
