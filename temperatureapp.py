import base64
import pathlib
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

# Molécules proposées sous la barre de recherche (modifiable)
SUGGESTIONS = ["ethanol", "water", "acetone", "benzene",
               "methanol", "toluene", "ammonia", "chloroform"]


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
    """Molécule 3D, fond transparent, rotation lente (modifiable avec la souris)."""
    sdf_js = sdf.replace("\\", "\\\\").replace("`", "\\`")
    components.html(f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="mol" style="width:100%;height:380px;position:relative;"></div>
    <script>
      const v = $3Dmol.createViewer("mol", {{backgroundAlpha: 0}});
      v.addModel(`{sdf_js}`, "sdf");
      v.setStyle({{}}, {{stick: {{}}, sphere: {{scale: 0.25}}}});
      v.zoomTo();
      v.render();
      v.spin("y", 0.4);   // rotation lente : plus petit = plus lent
    </script>
    """, height=400)


def choisir(molecule):
    """Appelée par un clic sur une suggestion : remplit la barre de recherche."""
    st.session_state["saisie"] = molecule


st.set_page_config(page_title="molVap", layout="centered")


def css_fond(fichier="fond.jpg"):
    chemin = pathlib.Path(__file__).parent / fichier
    if chemin.exists():
        b64 = base64.b64encode(chemin.read_bytes()).decode()
        return f'url("data:image/jpeg;base64,{b64}")'
    return "#e9edf2"


STYLE = """
<style>
/* Décor : dessins de chimie en gris clair */
.stApp { background: FOND center / cover fixed no-repeat; background-color: #e9edf2; }
[data-testid="stHeader"] { background: transparent; }

/* Carte en verre, bleu foncé */
.block-container {
    max-width: 720px;
    margin-top: 4vh;
    padding: 2.5rem !important;
    background: rgba(11, 37, 69, 0.88);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 2px solid rgba(255, 255, 255, 0.65);
    border-radius: 28px;
    box-shadow: 0 10px 40px rgba(11, 37, 69, 0.35);
}

/* Textes en blanc */
h1, h2, h3, p, label, [data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"], [data-testid="stMetricLabel"] {
    color: white !important;
}
h1 { font-size: 2.6rem !important; letter-spacing: 1px; }

/* Zone de saisie arrondie */
.stTextInput div[data-baseweb="input"],
.stTextInput div[data-baseweb="base-input"] {
    background: rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px;
    border: 1.5px solid rgba(255, 255, 255, 0.6);
}
.stTextInput input { color: white !important; padding: 14px 18px; }
.stTextInput input::placeholder { color: rgba(255, 255, 255, 0.65); }

/* Boutons de suggestion */
.stButton button {
    width: 100%;
    background: rgba(255, 255, 255, 0.10);
    color: white;
    border: 1.5px solid rgba(255, 255, 255, 0.45);
    border-radius: 20px;
    padding: 4px 8px;
}
.stButton button:hover {
    background: rgba(142, 203, 255, 0.25);
    border-color: #8ecbff;
    color: white;
}
.stButton button p { color: white !important; }

/* Température */
[data-testid="stMetricValue"] { color: #8ecbff !important; font-weight: 600; }
</style>
"""
st.markdown(STYLE.replace("FOND", css_fond()), unsafe_allow_html=True)

st.title("molVap")
st.caption("Température d'ébullition et structure 3D de n'importe quelle molécule.")

nom = st.text_input("Molécule (nom anglais, formule ou SMILES) :",
                    placeholder="ethanol", key="saisie")

# Suggestions sous la barre de recherche
st.caption("Suggestions :")
for debut in range(0, len(SUGGESTIONS), 4):
    colonnes = st.columns(4)
    for col, molecule in zip(colonnes, SUGGESTIONS[debut:debut + 4]):
        col.button(molecule, key="sug_" + molecule,
                   on_click=choisir, args=(molecule,))

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
