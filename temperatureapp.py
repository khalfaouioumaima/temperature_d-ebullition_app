import base64
import hmac
import os
import unicodedata
import urllib.request
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from thermo import Chemical

try:
    from thermo.group_contribution.joback import Joback
except Exception:
    Joback = None

TROUTON = 88.0
P_ATM = 101325.0

# ---------------------- Background: pink science doodles ----------------------
SVG_LABO = """<svg xmlns="http://www.w3.org/2000/svg" width="700" height="600" viewBox="0 0 700 600">
<defs>
<g id="atom" fill="none" stroke="#f08cae" stroke-width="2.5">
<ellipse rx="34" ry="12"/><ellipse rx="34" ry="12" transform="rotate(60)"/><ellipse rx="34" ry="12" transform="rotate(120)"/>
<circle r="5" fill="#f08cae"/>
</g>
<g id="erl" stroke="#f08cae" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">
<path d="M-27 20 L27 20 L38 38 Q42 48 32 48 L-32 48 Q-42 48 -38 38Z" fill="#f8b4cb"/>
<path d="M-10 -45 L-10 -10 L-38 38 Q-42 48 -32 48 L32 48 Q42 48 38 38 L10 -10 L10 -45 M-15 -45 L15 -45" fill="none"/>
</g>
<g id="rond" stroke="#f08cae" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">
<path d="M-31 8 A32 32 0 1 0 31 8Z" fill="#f8b4cb"/>
<path d="M-9 -50 L-9 -18 A32 32 0 1 0 9 -18 L9 -50 M-14 -50 L14 -50" fill="none"/>
</g>
<g id="bec" stroke="#f08cae" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">
<path d="M-24 0 L24 0 L24 30 Q24 38 16 38 L-16 38 Q-24 38 -24 30Z" fill="#f8b4cb"/>
<path d="M-25 -30 L-25 30 Q-25 38 -17 38 L17 38 Q25 38 25 30 L25 -30" fill="none"/>
<path d="M-25 -14 L-14 -14 M-25 -2 L-17 -2" fill="none" stroke-width="2"/>
</g>
<g id="bulb" fill="none" stroke="#f08cae" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">
<path d="M-12 14 Q-30 -5 -20 -22 Q0 -42 20 -22 Q30 -5 12 14Z"/>
<path d="M-10 22 L10 22 M-8 30 L8 30 M-5 36 L5 36"/>
<path d="M0 -52 L0 -46 M-30 -40 L-26 -36 M30 -40 L26 -36 M-38 -12 L-32 -12 M38 -12 L32 -12"/>
</g>
<g id="mag" fill="none" stroke="#f08cae" stroke-width="2.5" stroke-linejoin="round">
<path d="M-25 30 L-25 -5 A25 25 0 0 1 25 -5 L25 30 L13 30 L13 -5 A13 13 0 0 0 -13 -5 L-13 30Z" fill="#f8b4cb"/>
</g>
<path id="star" d="M0 -7 L2 -2 L7 0 L2 2 L0 7 L-2 2 L-7 0 L-2 -2Z" fill="#f08cae"/>
</defs>

<g font-family="Comic Sans MS, Segoe Print, cursive, sans-serif" font-size="26" fill="#f08cae">
<text x="150" y="70">E=mc²</text>
<text x="430" y="62">V=IR</text>
<text x="30" y="235">PV=nRT</text>
<text x="400" y="245">E=ma</text>
<text x="150" y="425">E=hf</text>
<text x="335" y="425">H₂O</text>
<text x="565" y="405">F=ma</text>
<text x="160" y="565">pH</text>
<text x="455" y="565">NaCl</text>
</g>

<use href="#atom" x="80" y="70"/>
<use href="#erl" x="330" y="90"/>
<use href="#bulb" x="570" y="85"/>
<use href="#rond" x="190" y="265"/>
<use href="#atom" x="330" y="255"/>
<use href="#mag" x="540" y="250"/>
<use href="#bec" x="640" y="240"/>
<use href="#atom" x="90" y="405"/>
<use href="#bulb" x="275" y="405"/>
<use href="#erl" x="500" y="415"/>
<use href="#rond" x="80" y="545"/>
<use href="#mag" x="265" y="545"/>
<use href="#atom" x="375" y="540"/>
<use href="#bec" x="610" y="540"/>

<use href="#star" x="30" y="140"/><use href="#star" x="130" y="165"/>
<use href="#star" x="250" y="170"/><use href="#star" x="420" y="150"/>
<use href="#star" x="500" y="175"/><use href="#star" x="480" y="320"/>
<use href="#star" x="20" y="330"/><use href="#star" x="235" y="350"/>
<use href="#star" x="430" y="350"/><use href="#star" x="665" y="340"/>
<use href="#star" x="30" y="485"/><use href="#star" x="205" y="485"/>
<use href="#star" x="330" y="485"/><use href="#star" x="450" y="505"/>
<use href="#star" x="665" y="470"/><use href="#star" x="545" y="590"/>
<g fill="#f8b4cb">
<circle cx="190" cy="130" r="3"/><circle cx="60" cy="200" r="3"/><circle cx="270" cy="215" r="3"/>
<circle cx="460" cy="95" r="3"/><circle cx="650" cy="170" r="3"/><circle cx="600" cy="320" r="3"/>
<circle cx="150" cy="350" r="3"/><circle cx="385" cy="330" r="3"/><circle cx="660" cy="410" r="3"/>
<circle cx="40" cy="600" r="3"/><circle cx="230" cy="590" r="3"/><circle cx="530" cy="510" r="3"/>
</g>
</svg>"""


@st.cache_data(show_spinner=False)
def charger_fond():
    # Si un fichier "fond.png" est à côté de app.py, il est utilisé comme fond
    if os.path.exists("fond.png"):
        with open("fond.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return "data:image/png;base64," + data, "cover"
    return "data:image/svg+xml," + urllib.parse.quote(SVG_LABO), "700px 600px"


def construire_css():
    fond, taille = charger_fond()
    css = """
<style>
.stApp {
    background-color: #fde8ef;
    background-image: url("__FOND__");
    background-size: __TAILLE__;
    background-attachment: fixed;
}
header[data-testid="stHeader"] { background: transparent; }
h1 { color: #b83266; font-size: 2.4rem !important; }
h2, h3 { color: #b83266; }
.bandeau {
    height: 8px;
    border-radius: 8px;
    margin: 4px 0 20px 0;
    background: linear-gradient(90deg, #f8b4cb, #f08cae, #fbc9da, #f6a5c0, #fde0ea);
}
.stTextInput input {
    border: 2px solid #f6c1d4;
    border-radius: 12px;
    padding: 12px 16px;
    background: white;
}
.stTextInput input:focus { border-color: #e0679a; }
[data-testid="stForm"],
[data-testid="stColumn"],
[data-testid="column"] {
    background: rgba(255, 255, 255, 0.9);
    border: 2px solid #f6c1d4;
    border-radius: 16px;
    padding: 14px 18px;
}
.stButton button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 10px;
    border: 2px solid #f08cae;
    background: #fff0f5;
    color: #b83266;
}
[data-testid="stMetricValue"] { color: #d6336c; font-weight: 600; }
</style>
"""
    return css.replace("__FOND__", fond).replace("__TAILLE__", taille)


def enlever_accents(texte):
    texte = texte.strip().replace("œ", "oe").replace("’", "'")
    texte = unicodedata.normalize("NFD", texte)
    return "".join(ch for ch in texte if unicodedata.category(ch) != "Mn")


def temperature_ebullition(nom):
    res = {"erreur": None, "T_K": None, "methode": None, "fiabilite": None}
    try:
        c = Chemical(enlever_accents(nom), P=P_ATM)
    except Exception:
        res["erreur"] = "Molecule not found. Try the English name, the formula or the SMILES."
        return res

    res["nom_officiel"] = c.name
    res["formule"] = c.formula
    res["smiles"] = c.smiles

    if c.Tb:
        res.update(T_K=c.Tb, methode="Tabulated value", fiabilite="very good")
        return res
    try:
        T = c.VaporPressure.solve_prop(P_ATM)
        if T:
            res.update(T_K=T, methode="Vapor pressure: Psat(T) = 1 atm",
                       fiabilite="very good")
            return res
    except Exception:
        pass
    if Joback and c.smiles:
        try:
            T = Joback(c.smiles).estimate()["Tb"]
            if T:
                res.update(T_K=T, methode="Joback estimation",
                           fiabilite="medium (± 10 to 30 K)")
                return res
        except Exception:
            pass
    if c.Hvap_Tbm:
        res.update(T_K=c.Hvap_Tbm / TROUTON, methode="Trouton's rule",
                   fiabilite="low (inaccurate for associated liquids)")
        return res

    res["erreur"] = "No method could compute the boiling point for this molecule."
    return res


@st.cache_data(show_spinner=False)
def telecharger_sdf(smiles, nom):
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
    for type_, valeur in (("smiles", smiles), ("name", nom)):
        if not valeur:
            continue
        url = base + type_ + "/" + urllib.parse.quote(valeur, safe="") + "/SDF?record_type=3d"
        try:
            with urllib.request.urlopen(url, timeout=10) as rep:
                return rep.read().decode("utf-8")
        except Exception:
            continue
    return None


def afficher_3d(sdf):
    sdf_js = sdf.replace("\\", "\\\\").replace("`", "\\`")
    components.html(f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="mol" style="width:100%;height:380px;position:relative;"></div>
    <script>
      const v = $3Dmol.createViewer("mol", {{backgroundColor: "white"}});
      v.addModel(`{sdf_js}`, "sdf");
      v.setStyle({{}}, {{stick: {{}}, sphere: {{scale: 0.25}}}});
      v.zoomTo();
      v.render();
    </script>
    """, height=400)


def verifier_connexion():
    if st.session_state.get("auth"):
        return True
    st.title("🧪 Hi chemist")
    st.markdown('<div class="bandeau"></div>', unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Log in")
    if ok:
        try:
            users = st.secrets["users"]
        except Exception:
            st.error("No account configured (missing [users] section in Secrets).")
            return False
        if u in users and hmac.compare_digest(p, str(users[u])):
            st.session_state["auth"] = True
            st.session_state["user"] = u
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    return False


# ---------------------- Config (must be the first Streamlit command) ----------------------
st.set_page_config(page_title="Boiling point", page_icon="🧪", layout="wide")
st.markdown(construire_css(), unsafe_allow_html=True)

# ---------------------- Login ----------------------
if not verifier_connexion():
    st.stop()

with st.sidebar:
    st.write(f"Logged in as: {st.session_state['user']}")
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

# ---------------------- Home ----------------------
st.title("🧪 Boiling point + 3D structure")
st.markdown('<div class="bandeau"></div>', unsafe_allow_html=True)
st.caption("Enter a molecule: get its boiling point and 3D structure.")

nom = st.text_input("Molecule (English name, formula or SMILES):", placeholder="ethanol")

if nom.strip():
    r = temperature_ebullition(nom)
    if r["erreur"]:
        st.error(r["erreur"])
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"{r['nom_officiel']} ({r['formule']})")
            st.metric("Boiling point", f"{r['T_K']:.1f} K")
            st.write(f"**{r['T_K'] - 273.15:.1f} °C**")
            st.write("**Method:**", r["methode"])
            st.write("**Reliability:**", r["fiabilite"])
        with col2:
            sdf = telecharger_sdf(r["smiles"], r["nom_officiel"])
            if sdf:
                afficher_3d(sdf)
            else:
                st.info("3D structure unavailable (no internet or molecule not found).")
