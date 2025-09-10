# Pump Line Calculator – SI (refined UI)
# Rezultate mari: NPSH(A), p_refulare (p2), p_aspiratie (p1)
# Fittings selectabile; pres. rezervor atmosferica/custom; pompa sub/deasupra nivelului.

import math
import pandas as pd
import streamlit as st

# ---- stil "wide" fără set_page_config ----
st.markdown("""
<style>
h1, h2, h3, h4, h5, h6 {text-decoration: none;}
.css-15eqn8j a {display: none;}  /* ascunde link-urile de ancoră */
</style>
""", unsafe_allow_html=True)

g = 9.80665  # m/s²

# ---------- Bibliotecă fittinguri ----------
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

def dp_pa(rho, h):        # head [m] -> Pa
    return rho * g * h

def pa_to_bar(pa):        # Pa -> bar
    return pa / 1e5

def bar_to_pa(bar):       # bar -> Pa
    return bar * 1e5

def p_atm_from_alt_bar(h_m: float) -> float:
    """Presiune atmosferică standard în bar(abs) la altitudine h [m]. ISA simplificată."""
    pa = 101325.0 * (1.0 - 2.25577e-5 * h_m) ** 5.25588
    return pa / 1e5

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

# ============================================================
#                   UI: Panou stânga (intrări)
# ============================================================
st.sidebar.title("Inputs")

# Fluide
rho = st.sidebar.number_input("ρ [kg/m³]", 100.0, 3000.0, 1000.0, 1.0)
mu  = st.sidebar.number_input("μ [mPa·s]", 0.1, 5000.0, 1.0, 0.1) / 1000.0  # Pa·s
Q   = st.sidebar.number_input("Q [m³/h]", 0.01, 200000.0, 50.0, 0.1) / 3600.0  # m³/s
Pv  = bar_to_pa(st.sidebar.number_input("P_vap [bar(abs)]", 0.0, 15.0, 0.023, 0.001))

# Pompa sub/deasupra suprafeței
pos_choice = st.sidebar.radio("Poziția pompei vs. suprafața de aspirație",
                              ["Sub nivel (inundată)", "Deasupra nivelului"],
                              index=0)
dz_mag = st.sidebar.number_input("Distanța verticală |Δz| [m]",
                                 0.0, 200.0, 2.0, 0.1,
                                 help="Distanța pe verticală între suprafața lichid și axa pompei.")
Dz_S = dz_mag if pos_choice == "Sub nivel (inundată)" else -dz_mag

# Presiunea în rezervorul de aspirație
p_res_choice = st.sidebar.radio("Presiunea în rezervorul de aspirație",
                                ["Atmosferică", "Custom"],
                                index=0)
if p_res_choice == "Atmosferică":
    alt = st.sidebar.number_input("Altitudine amplasament [m]", -400.0, 4000.0, 0.0, 10.0)
    Ps_bar = p_atm_from_alt_bar(alt)
    st.sidebar.write(f"**P_atm ≈ {Ps_bar:.3f} bar(abs)**")
else:
    Ps_bar = st.sidebar.number_input("P_s [bar(abs)]", 0.0, 50.0, 1.013, 0.01)

Ps = bar_to_pa(Ps_bar)

# Presiunea la destinație (refulare)
Pd_bar = st.sidebar.number_input("P_d (destinație) [bar(abs)]", 0.0, 100.0, 1.013, 0.01)
Pd = bar_to_pa(Pd_bar)

# Cota destinației
Dz_D = st.sidebar.number_input("Δz_D [m]", -200.0, 500.0, 10.0, 0.1,
                               help="(+): destinația mai sus decât pompa.")

st.title("Pump Line Calculator")

# ============================================================
#               Linii S și D (conductă + fittinguri)
# ============================================================
D_S, L_S, eps_S, K_S, dpsumS_bar, dfS = ui_line("S (Suction)", 100.0, 20.0, 0.045, "selS")
D_D, L_D, eps_D, K_D, dpsumD_bar, dfD = ui_line("D (Discharge)", 80.0, 80.0, 0.045, "selD")

# ============================================================
#                       Calcule
# ============================================================
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

# Recomandări Q_min / Q_max în funcție de v pe aspirație
v_min_S = 0.5   # m/s
v_max_S = 1.5   # m/s
Qmin = v_min_S * A_S * 3600.0  # m³/h
Qmax = v_max_S * A_S * 3600.0  # m³/h

# ============================================================
#                       Rezultate mari
# ============================================================
st.markdown("---")
st.markdown("<div class='big'>Rezultate</div>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
with r1:
    st.metric("NPSH (A) [m]", f"{NPSH_a:.3f}")
with r2:
    st.metric("Presiune refulare p₂ [bar(abs)]", f"{pa_to_bar(p2):.3f}")
with r3:
    st.metric("Presiune stut aspirație p₁ [bar(abs)]", f"{pa_to_bar(p1):.3f}")

st.markdown("---")
st.write(f"**Sugestie debit** (pe baza D_S={D_S*1000:.0f} mm și v_S recomandat {v_min_S}…{v_max_S} m/s): "
         f"Q_min ≈ **{Qmin:.1f} m³/h**, Q_max ≈ **{Qmax:.1f} m³/h**.")

# opțional: info utile
with st.expander("Detalii tehnice (opțional)"):
    st.write(pd.DataFrame({
        "Mărime":["v_S","Re_S","f_S","h_S","v_D","Re_D","f_D","h_D"],
        "Valoare":[v_S, Re_S, f_S, h_S, v_D, Re_D, f_D, h_D],
        "Unități":["m/s","-","-","m","m/s","-","-","m"]
    }))
    st.caption("Formule: Darcy–Weisbach; f = Swamee–Jain; ΣK pentru pierderi locale. "
               "NPSH(A) = p₁/(ρg) + v₁²/(2g) − Pvap/(ρg).")


