import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pump Sizing", layout="wide")

g = 9.80665  # m/s²

# ---------- Helpers ----------
def reynolds(rho, v, D, mu):
    return rho * v * D / mu

def f_swamee_jain(Re, eps, D):
    # eps, D in m
    if Re <= 0: 
        return 0.0
    return 0.25 / (math.log10(eps / (3.7 * D) + 5.74 / (Re ** 0.9))) ** 2

def head_loss_major(f, L, D, v):
    return f * (L / D) * (v ** 2) / (2 * g)

def head_loss_minor(Ksum, v):
    return Ksum * (v ** 2) / (2 * g)

def dp_from_head(rho, head):  # Pa
    return rho * g * head

def pa_from_bar(bar):
    return bar * 1e5

def bar_from_pa(pa):
    return pa / 1e5

# ---------- Sidebar Inputs ----------
st.sidebar.title("Setări generale (SI)")
rho = st.sidebar.number_input("Densitate ρ [kg/m³]", 100.0, 3000.0, 1000.0, step=1.0)
mu_mPas = st.sidebar.number_input("Vâscozitate dinamică μ [mPa·s] (1 mPa·s = 1 cP)", 0.1, 5000.0, 1.0, step=0.1)
mu = mu_mPas / 1000.0  # Pa·s
Q_m3h = st.sidebar.number_input("Debit Q [m³/h]", 0.1, 100000.0, 50.0, step=0.1)
Q = Q_m3h / 3600.0  # m³/s
Pvap_bar = st.sidebar.number_input("Presiune de vapori a lichidului Pvap [bar(abs)]", 0.0, 10.0, 0.023, step=0.001)
Pvap = pa_from_bar(Pvap_bar)

st.title("Template calcul pompă centrifugă – SI")

# ---------- Suction block ----------
st.header("1) Linia de **aspirație**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    D_s_mm = st.number_input("Diametru interior D_s [mm]", 5.0, 2000.0, 100.0, step=1.0)
    D_s = D_s_mm / 1000.0
with col2:
    L_s = st.number_input("Lungime dreaptă L_s [m]", 0.0, 10000.0, 20.0, step=0.5)
with col3:
    eps_s_mm = st.number_input("Rugozitate ε_s [mm]", 0.0, 2.0, 0.045, step=0.005)
    eps_s = eps_s_mm / 1000.0
with col4:
    K_s = st.number_input("ΣK fitinguri aspirație [-]", 0.0, 200.0, 2.0, step=0.1)

col5, col6, col7 = st.columns(3)
with col5:
    Ps_bar = st.number_input("Presiune la suprafața rezervorului de aspirație Ps [bar(abs)]", 0.0, 50.0, 1.01325, step=0.01)
    Ps = pa_from_bar(Ps_bar)
with col6:
    dz_s = st.number_input("Δz_s = z_suprafață - z_pompă [m]", -100.0, 200.0, 2.0, step=0.1,
                           help="Pozitiv dacă suprafața lichidului este deasupra pompei (aspirație inundată).")
with col7:
    note_s = st.text_input("Notă aspirație (opțional)", "")

# ---------- Discharge block ----------
st.header("2) Linia de **refulare**")
col1d, col2d, col3d, col4d = st.columns(4)
with col1d:
    D_d_mm = st.number_input("Diametru interior D_d [mm]", 5.0, 2000.0, 80.0, step=1.0)
    D_d = D_d_mm / 1000.0
with col2d:
    L_d = st.number_input("Lungime dreaptă L_d [m]", 0.0, 20000.0, 80.0, step=0.5)
with col3d:
    eps_d_mm = st.number_input("Rugozitate ε_d [mm]", 0.0, 2.0, 0.045, step=0.005)
    eps_d = eps_d_mm / 1000.0
with col4d:
    K_d = st.number_input("ΣK fitinguri refulare [-]", 0.0, 500.0, 10.0, step=0.5)

col5d, col6d, col7d = st.columns(3)
with col5d:
    Pd_bar = st.number_input("Presiune la destinație (vas/linie) Pd [bar(abs)]", 0.0, 100.0, 1.01325, step=0.01)
    Pd = pa_from_bar(Pd_bar)
with col6d:
    dz_d = st.number_input("Δz_d = z_destinație - z_pompă [m]", -200.0, 500.0, 10.0, step=0.1,
                           help="Pozitiv dacă destinația este mai sus decât pompa.")
with col7d:
    note_d = st.text_input("Notă refulare (opțional)", "")

# ---------- Core calculations ----------
# Velocities
As = math.pi * D_s**2 / 4.0
Ad = math.pi * D_d**2 / 4.0
vs = Q / As
vd = Q / Ad

# Reynolds
Re_s = reynolds(rho, vs, D_s, mu)
Re_d = reynolds(rho, vd, D_d, mu)

# Friction factors
f_s = f_swamee_jain(Re_s, eps_s, D_s)
f_d = f_swamee_jain(Re_d, eps_d, D_d)

# Head losses
hf_s_major = head_loss_major(f_s, L_s, D_s, vs)
hf_s_minor = head_loss_minor(K_s, vs)
hf_s = hf_s_major + hf_s_minor

hf_d_major = head_loss_major(f_d, L_d, D_d, vd)
hf_d_minor = head_loss_minor(K_d, vd)
hf_d = hf_d_major + hf_d_minor

# Suction nozzle absolute pressure (static)
# Bernoulli între suprafață (v~0) și duza de aspirație (punct 1)
# p1_abs/ρg + v1^2/2g + z1 = Ps/ρg + 0 + z_s - (hf_s)
# => p1_abs = ρg [ Ps/(ρg) + z_s - z1 - hf_s ]  (notăm z1 = z_pumpă => Δz_s definit)
p1_abs = Ps + dp_from_head(rho, dz_s - hf_s)  # Pa
p1_bar = bar_from_pa(p1_abs)

# Discharge nozzle absolute pressure (static)
# De la destinație (punct 2d, v≈0) la duza de refulare (punct 2 la pompă), invers direcției de curgere:
# p2_abs/ρg = Pd/ρg + (z_d - z_pompa) + hf_d
p2_abs = Pd + dp_from_head(rho, dz_d + hf_d)  # Pa
p2_bar = bar_from_pa(p2_abs)

# NPSH available conform definiției pe **cap total la aspirație**:
# NPSHa = (p1_total_abs/ρg) - (Pvap/ρg)
# p1_total_abs/ρg = p1_abs/(ρg) + v1^2/(2g)  (include capul de viteză la secțiunea duzei)
NPSHa = p1_abs / (rho * g) + (vs**2) / (2 * g) - Pvap / (rho * g)  # [m]

# ---------- Results ----------
st.header("3) Rezultate")
rcols = st.columns(3)
with rcols[0]:
    st.metric("v_s (aspirație) [m/s]", f"{vs:.3f}")
    st.metric("Re_s [-]", f"{Re_s:,.0f}")
    st.metric("f_s (-)", f"{f_s:.4f}")
    st.metric("h_f,s (total) [m]", f"{hf_s:.3f}")
with rcols[1]:
    st.metric("v_d (refulare) [m/s]", f"{vd:.3f}")
    st.metric("Re_d [-]", f"{Re_d:,.0f}")
    st.metric("f_d (-)", f"{f_d:.4f}")
    st.metric("h_f,d (total) [m]", f"{hf_d:.3f}")
with rcols[2]:
    st.metric("Presiune duză aspirație p₁ [bar(abs)]", f"{p1_bar:.3f}")
    st.metric("Presiune duză refulare p₂ [bar(abs)]", f"{p2_bar:.3f}")
    st.metric("NPSH_available [m]", f"{NPSHa:.3f}")

# Summary table
df = pd.DataFrame({
    "Mărime": [
        "ρ [kg/m³]", "μ [mPa·s]", "Q [m³/h]",
        "D_s [mm]", "L_s [m]", "ε_s [mm]", "ΣK_s [-]",
        "D_d [mm]", "L_d [m]", "ε_d [mm]", "ΣK_d [-]",
        "Ps [bar(abs)]", "Pd [bar(abs)]", "Δz_s [m]", "Δz_d [m]",
        "v_s [m/s]", "v_d [m/s]", "Re_s [-]", "Re_d [-]",
        "f_s [-]", "f_d [-]",
        "h_f,s [m]", "h_f,d [m]",
        "p₁ [bar(abs)]", "p₂ [bar(abs)]",
        "NPSH_available [m]"
    ],
    "Valoare": [
        rho, mu_mPas, Q_m3h,
        D_s_mm, L_s, eps_s_mm, K_s,
        D_d_mm, L_d, eps_d_mm, K_d,
        Ps_bar, Pd_bar, dz_s, dz_d,
        vs, vd, Re_s, Re_d,
        f_s, f_d,
        hf_s, hf_d,
        p1_bar, p2_bar,
        NPSHa
    ]
})
st.dataframe(df, use_container_width=True)

st.caption(
    "Formule: Darcy–Weisbach, f (Swamee–Jain), ΣK pentru pierderi locale. "
    "NPSH_available = p₁_total_abs/(ρg) − Pvap/(ρg) = p₁/(ρg) + v₁²/(2g) − Pvap/(ρg). "
    "Toate mărimile în unități SI."
)

# ---------- Nice-to-have: sanity tips ----------
tips = []
if vs > 2.0:
    tips.append("Viteza pe aspirație > 2 m/s – recomandat să fie 0.5…1.5 m/s pentru NPSH bun.")
if K_s > 5:
    tips.append("ΣK mare pe aspirație – încearcă coturi LR, vane cu K mic, fitinguri mai puține.")
if NPSHa < 2:
    tips.append("NPSH_available mic (<2 m) – risc de cavitație. Crește diametrul pe aspirație sau scade pierderile.")
if tips:
    st.subheader("Sugestii rapide")
    for t in tips:
        st.write("• " + t)


