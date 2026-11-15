import hmac
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

# ---------------------- Fond : dessins de labo en couleurs claires ----------------------
SVG_LABO = """<svg xmlns="http://www.w3.org/2000/svg" width="700" height="600" viewBox="0 0 700 600">
<g stroke-linecap="round" stroke-linejoin="round" stroke-width="3">

<!-- Becher -->
<path d="M63 88 L137 88 L137 132 Q137 145 124 145 L76 145 Q63 145 63 132Z" fill="#bcdcf7"/>
<path d="M56 40 L62 40 L62 132 Q62 146 76 146 L124 146 Q138 146 138 132 L138 40 L144 40" fill="none" stroke="#aab4bf"/>
<path d="M62 62 L78 62 M62 80 L72 80 M62 98 L78 98 M62 116 L72 116" fill="none" stroke="#c4ccd4" stroke-width="2"/>

<!-- Erlenmeyer -->
<path d="M297 125 L363 125 L380 150 Q386 162 372 162 L288 162 Q274 162 280 150Z" fill="#bfe8c3"/>
<path d="M318 40 L318 90 L280 150 Q274 162 288 162 L372 162 Q386 162 380 150 L342 90 L342 40" fill="none" stroke="#aab4bf"/>
<path d="M312 40 L348 40" fill="none" stroke="#aab4bf"/>

<!-- Burette sur support -->
<rect x="541" y="70" width="18" height="156" fill="#fbe9a0"/>
<path d="M540 30 L540 226 M560 30 L560 226 M536 30 L564 30" fill="none" stroke="#aab4bf"/>
<path d="M540 60 L530 60 M540 90 L534 90 M540 120 L530 120 M540 150 L534 150 M540 180 L530 180" fill="none" stroke="#c4ccd4" stroke-width="2"/>
<path d="M534 238 L566 238 M550 226 L550 262" fill="none" stroke="#aab4bf"/>
<circle cx="550" cy="280" r="5" fill="#f6b3c6"/>
<path d="M610 20 L610 348 M570 348 L650 348 M610 110 L560 110 M610 190 L560 190" fill="none" stroke="#c4ccd4"/>
<path d="M522 304 L524 336 Q524 342 530 342 L570 342 Q576 342 576 336 L578 304" fill="#f6c3d2" stroke="#aab4bf"/>

<!-- Tubes a essai -->
<path d="M73 300 L95 300 L95 350 Q95 365 84 365 Q73 365 73 350Z" fill="#f4a9a9"/>
<path d="M107 285 L129 285 L129 350 Q129 365 118 365 Q107 365 107 350Z" fill="#bfe8c3"/>
<path d="M141 320 L163 320 L163 350 Q163 365 152 365 Q141 365 141 350Z" fill="#fbe9a0"/>
<path d="M72 250 L72 350 Q72 366 84 366 Q96 366 96 350 L96 250 M106 250 L106 350 Q106 366 118 366 Q130 366 130 350 L130 250 M140 250 L140 350 Q140 366 152 366 Q164 366 164 350 L164 250" fill="none" stroke="#aab4bf"/>

<!-- Ballon a fond rond -->
<path d="M209 470 A41 41 0 1 0 291 470Z" fill="#fbe9a0"/>
<path d="M240 392 L240 436 A41 41 0 1 0 260 436 L260 392 M234 392 L266 392" fill="none" stroke="#aab4bf"/>

<!-- Molecule d'eau -->
<path d="M400 330 L368 362 M400 330 L432 362" fill="none" stroke="#c4ccd4"/>
<circle cx="400" cy="330" r="17" fill="#f4a0a0"/>
<circle cx="368" cy="362" r="10" fill="#dfe3e8"/>
<circle cx="432" cy="362" r="10" fill="#dfe3e8"/>

<!-- Benzene -->
<path d="M512 480 L491 516 L449 516 L428 480 L449 444 L491 444Z" fill="none" stroke="#c4ccd4"/>
<circle cx="470" cy="480" r="22" fill="none" stroke="#dfe3e8" stroke-width="2"/>
<circle cx="512" cy="480" r="9" fill="#f6b3c6"/>
<circle cx="491" cy="516" r="9" fill="#a8d0f0"/>
<circle cx="449" cy="516" r="9" fill="#bfe8c3"/>
<circle cx="428" cy="480" r="9" fill="#fbe9a0"/>
<circle cx="449" cy="444" r="9" fill="#f4a0a0"/>
<circle cx="491" cy="444" r="9" fill="#cfd4da"/>

<!-- Methane -->
<path d="M345 545 L315 520 M345 545 L375 520 M345 545 L315 570 M345 545 L375 570" fill="none" stroke="#c4ccd4"/>
<circle cx="345" cy="545" r="14" fill="#cfd4da"/>
<circle cx="315" cy="520" r="9" fill="#a8d0f0"/>
<circle cx="375" cy="520" r="9" fill="#f6b3c6"/>
<circle cx="315" cy="570" r="9" fill="#bfe8c3"/>
<circle cx="375" cy="570" r="9" fill="#fbe9a0"/>

<!-- Thermometre -->
<rect x="630" y="415" width="4" height="70" fill="#f4a0a0" stroke="none"/>
<circle cx="632" cy="486" r="9" fill="#f4a0a0" stroke="none"/>
<path d="M624 390 L624 472 A12 12 0 1 0 640 472 L640 390 Q632 380 624 390" fill="none" stroke="#aab4bf"/>
<path d="M642 405 L650 405 M642 425 L648 425 M642 445 L650 445" fill="none" stroke="#c4ccd4" stroke-width="2"/>

<!-- Bulles -->
<circle cx="200" cy="215" r="6" fill="none" stroke="#a8d0f0"/>
<circle cx="225" cy="245" r="4" fill="#bfe8c3" stroke="none"/>
<circle cx="450" cy="120" r="7" fill="none" stroke="#f6b3c6"/>
<circle cx="480" cy="215" r="4" fill="#fbe9a0" stroke="none"/>
<circle cx="440" cy="260" r="6" fill="none" stroke="#bfe8c3"/>
<circle cx="40" cy="450" r="6" fill="none" stroke="#fbe9a0"/>
<circle cx="110" cy="520" r="5" fill="#a8d0f0" stroke="none"/>
<circle cx="180" cy="580" r="4" fill="#f6b3c6" stroke="none"/>
<circle cx="660" cy="560" r="6" fill="none" stroke="#a8d0f0"/>
<circle cx="250" cy="330" r="4" fill="#f4a0a0" stroke="none"/>
</g>
</svg>"""

FOND = "data:image/svg+xml," + urllib.parse.quote(SVG_LABO)

CSS = """
<style>
.stApp {
    background-color: #ffffff;
    background-image: url("__FOND__");
    background-size: 700px 600px;
    background-attachment: fixed;
}
header[data-testid="stHeader"] { background: transparent; }
h1 { color: #12355b; font-size: 2.4rem !important; }
h2, h3 { color: #12355b; }
.bandeau {
    height: 8px;
    border-radius: 8px;
    margin: 4px 0 20px 0;
    background: linear-gradient(90deg, #f6b3c6, #fbe38e, #b6e3b6, #a8d0f0, #f4a0a0, #cfd4da);
}
.stTextInput input {
    border: 2px solid #c9d6e6;
    border-radius: 12px;
    padding: 12px 16px;
    background: white;
}
.stTextInput input:focus { border-color: #1f6feb; }
[data-testid="stForm"],
[data-testid="stColumn"],
[data-testid="column"] {
    background: rgba(255, 255, 255, 0.93);
    border: 2px solid #dbe6f2;
    border-radius: 16px;
    padding: 14px 18px;
}
.stButton button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 10px;
    border: 2px solid #a8d0f0;
    background: #eaf4fd;
    color: #12355b;
}
[data-testid="stMetricValue"] { color: #1f6feb; font-weight: 600; }
</style>
""".replace("__FOND__", FOND)


def enlever_accents(texte):
    texte = texte.strip().replace("œ", "oe").replace("’", "'")
    texte = unicodedata.normalize("NFD", texte)
    return "".join(ch for ch in texte if unicodedata.category(ch) != "Mn")


def temperature_ebullition(nom):
    res = {"erreur": None, "T_K": None, "methode": None, "fiabilite": None}
    try:
        c = Chemical(enlever_accents(nom), P=P_ATM)
    except Exception:
        res["erreur"] = "Molécule introuvable. Essayez le nom anglais, la formule ou le SMILES."
        return res

    res["nom_officiel"] = c.name
    res["formule"] = c.formula
    res["smiles"] = c.smiles

    if c.Tb:
        res.update(T_K=c.Tb, methode="Valeur tabulée", fiabilite="très bonne")
        return res
    try:
        T = c.VaporPressure.solve_prop(P_ATM)
        if T:
            res.update(T_K=T, methode="Pression de vapeur : Psat(T) = 1 atm",
                       fiabilite="très bonne")
            return res
    except Exception:
        pass
    if Joback and c.smiles:
        try:
            T = Joback(c.smiles).estimate()["Tb"]
            if T:
                res.update(T_K=T, methode="Estimation de Joback",
                           fiabilite="moyenne (± 10 à 30 K)")
                return res
        except Exception:
            pass
    if c.Hvap_Tbm:
        res.update(T_K=c.Hvap_Tbm / TROUTON, methode="Règle de Trouton",
                   fiabilite="faible (fausse pour les liquides associés)")
        return res

    res["erreur"] = "Aucune méthode n'a pu calculer T_éb pour cette molécule."
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
    st.title("🔐 Connexion")
    st.markdown('<div class="bandeau"></div>', unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Nom d'utilisateur")
        p = st.text_input("Mot de passe", type="password")
        ok = st.form_submit_button("Se connecter")
    if ok:
        try:
            users = st.secrets["users"]
        except Exception:
            st.error("Aucun compte configuré (section [users] manquante dans les Secrets).")
            return False
        if u in users and hmac.compare_digest(p, str(users[u])):
            st.session_state["auth"] = True
            st.session_state["user"] = u
            st.rerun()
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")
    return False


# ---------------------- Config (doit être la 1re commande Streamlit) ----------------------
st.set_page_config(page_title="Température d'ébullition", page_icon="🧪", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------- Connexion ----------------------
if not verifier_connexion():
    st.stop()

with st.sidebar:
    st.write(f"Connecté : {st.session_state['user']}")
    if st.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

# ---------------------- Accueil ----------------------
st.title("🧪 Température d'ébullition + structure 3D")
st.markdown('<div class="bandeau"></div>', unsafe_allow_html=True)
st.caption("Entrez une molécule : température d'ébullition et structure 3D.")

nom = st.text_input("Molécule (nom anglais, formule ou SMILES) :", placeholder="ethanol")

if nom.strip():
    r = temperature_ebullition(nom)
    if r["erreur"]:
        st.error(r["erreur"])
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"{r['nom_officiel']} ({r['formule']})")
            st.metric("T_éb", f"{r['T_K']:.1f} K")
            st.write(f"**{r['T_K'] - 273.15:.1f} °C**")
            st.write("**Méthode :**", r["methode"])
            st.write("**Fiabilité :**", r["fiabilite"])
        with col2:
            sdf = telecharger_sdf(r["smiles"], r["nom_officiel"])
            if sdf:
                afficher_3d(sdf)
            else:
                st.info("Structure 3D indisponible (internet ou molécule absente).")
