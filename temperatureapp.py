import base64
import hmac
import math
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


# ---------------------- Calcul ----------------------
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
    """Molécule 3D du résultat, fond transparent, rotation lente."""
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


# ---------------------- Décor : molécules 3D en rotation lente ----------------------
# Éléments : (rayon relatif, couleur claire, couleur sombre)
ELEMENTS = {
    "H": (0.30, "#f1f5f9", "#aab9ca"),
    "C": (0.50, "#a3b1c2", "#46566a"),
    "N": (0.48, "#8aa6d8", "#2c4a85"),
    "O": (0.46, "#7f9fd6", "#2a4a88"),
}

_t = 0.63
MOTIFS = [
    # nom, atomes [(élément, x, y, z)], liaisons [(i, j)], position (% x, % y), échelle, durée (s)
    ("benzene",
     [("C", 1.4 * math.cos(math.radians(a)), 1.4 * math.sin(math.radians(a)), 0) for a in range(0, 360, 60)]
     + [("H", 2.48 * math.cos(math.radians(a)), 2.48 * math.sin(math.radians(a)), 0) for a in range(0, 360, 60)],
     [(i, (i + 1) % 6) for i in range(6)] + [(i, i + 6) for i in range(6)],
     (7, 14), 26, 80),
    ("eau",
     [("O", 0, 0, 0), ("H", 0.76, 0.59, 0), ("H", -0.76, 0.59, 0)],
     [(0, 1), (0, 2)],
     (6, 66), 52, 55),
    ("methane",
     [("C", 0, 0, 0), ("H", _t, _t, _t), ("H", _t, -_t, -_t),
      ("H", -_t, _t, -_t), ("H", -_t, -_t, _t)],
     [(0, 1), (0, 2), (0, 3), (0, 4)],
     (93, 20), 50, 65),
    ("dioxyde de carbone",
     [("C", 0, 0, 0), ("O", -1.16, 0, 0), ("O", 1.16, 0, 0)],
     [(0, 1), (0, 2)],
     (94, 68), 46, 60),
    ("ammoniac",
     [("N", 0, -0.1, 0), ("H", 0.94, 0.4, 0), ("H", -0.47, 0.4, 0.81), ("H", -0.47, 0.4, -0.81)],
     [(0, 1), (0, 2), (0, 3)],
     (15, 90), 44, 70),
]


def construire_decor():
    """Fabrique des molécules en CSS 3D (sphères et liaisons) qui tournent lentement."""
    morceaux = ['<div class="decor">']
    for _, atomes, liaisons, (px, py), S, duree in MOTIFS:
        morceaux.append(f'<div class="m" style="left:{px}%;top:{py}%;--d:{duree}s">'
                        f'<div class="rot">')
        for el, x, y, z in atomes:
            r = ELEMENTS[el][0] * S
            morceaux.append(
                f'<div class="a" style="transform:translate3d({x*S:.1f}px,{y*S:.1f}px,{z*S:.1f}px)">'
                f'<span style="width:{2*r:.1f}px;height:{2*r:.1f}px;left:-{r:.1f}px;top:-{r:.1f}px;'
                f'--c:{ELEMENTS[el][1]};--k:{ELEMENTS[el][2]}"></span></div>')
        for i, j in liaisons:
            _, x1, y1, z1 = atomes[i]
            _, x2, y2, z2 = atomes[j]
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            long = math.sqrt(dx * dx + dy * dy + dz * dz)
            phi = math.degrees(math.atan2(dy, dx))
            theta = math.degrees(math.asin(dz / long))
            mx, my, mz = (x1 + x2) / 2 * S, (y1 + y2) / 2 * S, (z1 + z2) / 2 * S
            L = long * S
            w = max(3.0, 0.09 * S)
            barre = f'style="height:{w:.1f}px;top:-{w/2:.1f}px"'
            morceaux.append(
                f'<div class="b" style="width:{L:.1f}px;margin-left:-{L/2:.1f}px;'
                f'transform:translate3d({mx:.1f}px,{my:.1f}px,{mz:.1f}px) '
                f'rotateZ({phi:.1f}deg) rotateY({-theta:.1f}deg)">'
                f'<span {barre}></span><span {barre}></span></div>')
        morceaux.append('</div></div>')
    morceaux.append('</div>')
    return "".join(morceaux)   # pas de saut de ligne : évite les erreurs de rendu


# ---------------------- Interface ----------------------
def choisir(molecule):
    """Clic sur une suggestion : remplit la barre de recherche."""
    st.session_state["saisie"] = molecule


def verifier_acces():
    """Page de connexion : renvoie True quand le mot de passe est correct."""
    if st.session_state.get("acces"):
        return True

    st.title("molVap")
    st.markdown("<p class='phrase'>Connectez-vous pour accéder à l'application.</p>",
                unsafe_allow_html=True)

    with st.form("connexion"):
        mdp = st.text_input("Mot de passe", type="password")
        envoye = st.form_submit_button("Se connecter")

    if envoye:
        try:
            attendu = st.secrets["MOT_DE_PASSE"]
        except Exception:
            st.error("Mot de passe non configuré (voir les secrets de l'app).")
            return False
        if hmac.compare_digest(mdp.encode(), str(attendu).encode()):
            st.session_state["acces"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    return False


st.set_page_config(page_title="molVap", layout="centered")


def css_fond(fichier="fond.jpg"):
    chemin = pathlib.Path(__file__).parent / fichier
    if chemin.exists():
        b64 = base64.b64encode(chemin.read_bytes()).decode()
        return f'url("data:image/jpeg;base64,{b64}")'
    return "#e9edf2"


STYLE = """
<style>
/* Fond : dessins de chimie en gris clair */
.stApp { background: FOND center / cover fixed no-repeat; background-color: #e9edf2; }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 760px; padding-top: 4vh !important; }

/* Décor 3D : derrière la carte */
div[data-testid="stElementContainer"]:has(.decor),
.element-container:has(.decor) { position: absolute; }
.decor { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.decor .m { position: absolute; width: 0; height: 0; perspective: 1000px; opacity: 0.7; }
.decor .rot { position: absolute; width: 0; height: 0; transform-style: preserve-3d;
              animation: tourne var(--d) linear infinite; }
.decor .a { position: absolute; width: 0; height: 0; transform-style: preserve-3d; }
.decor .a span { position: absolute; display: block; border-radius: 50%;
                 background: radial-gradient(circle at 35% 30%, #ffffff 0%, var(--c) 40%, var(--k) 100%);
                 animation: contre var(--d) linear infinite; }
.decor .b { position: absolute; left: 0; top: 0; height: 0; transform-style: preserve-3d; }
.decor .b span { position: absolute; display: block; left: 0; width: 100%;
                 background: linear-gradient(#dde5ee, #8796a8); }
.decor .b span:nth-child(2) { transform: rotateX(90deg); }
@keyframes tourne { from { transform: rotateX(18deg) rotateY(0deg); }
                    to   { transform: rotateX(18deg) rotateY(360deg); } }
@keyframes contre { from { transform: rotateY(0deg); } to { transform: rotateY(-360deg); } }

/* Carte en verre, bleu foncé */
.st-key-carte {
    position: relative; z-index: 1;
    padding: 2.5rem;
    background: rgba(11, 37, 69, 0.90);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 2px solid rgba(255, 255, 255, 0.65);
    border-radius: 28px;
    box-shadow: 0 10px 40px rgba(11, 37, 69, 0.35);
}

/* Textes en blanc */
.st-key-carte h1, .st-key-carte h2, .st-key-carte h3, .st-key-carte p,
.st-key-carte label, .st-key-carte [data-testid="stMarkdownContainer"],
.st-key-carte [data-testid="stCaptionContainer"],
.st-key-carte [data-testid="stMetricLabel"] { color: white !important; }
.st-key-carte h1 { font-size: 2.6rem !important; letter-spacing: 1px; }
.st-key-carte p.phrase { font-size: 1.15rem; letter-spacing: 1px;
                         color: #8ecbff !important; margin-top: -10px; }

/* Zones de saisie arrondies */
.st-key-carte .stTextInput div[data-baseweb="input"],
.st-key-carte .stTextInput div[data-baseweb="base-input"] {
    background: rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px;
    border: 1.5px solid rgba(255, 255, 255, 0.6);
}
.st-key-carte .stTextInput input { color: white !important; padding: 14px 18px; }
.st-key-carte .stTextInput input::placeholder { color: rgba(255, 255, 255, 0.65); }

/* Boutons de suggestion */
.st-key-carte .stButton button {
    width: 100%;
    background: rgba(255, 255, 255, 0.10);
    color: white;
    border: 1.5px solid rgba(255, 255, 255, 0.45);
    border-radius: 20px;
    padding: 4px 8px;
}
.st-key-carte .stButton button:hover {
    background: rgba(142, 203, 255, 0.25);
    border-color: #8ecbff;
}
.st-key-carte .stButton button p { color: white !important; }

/* Bouton Se connecter */
.st-key-carte [data-testid="stFormSubmitButton"] button {
    width: 100%;
    background: linear-gradient(90deg, #3a7bd5, #1f4e9c);
    color: white; border: none; border-radius: 16px; padding: 8px;
}
.st-key-carte [data-testid="stFormSubmitButton"] button p { color: white !important; }
.st-key-carte [data-testid="stForm"] { border: none; padding: 0; }

/* Température */
.st-key-carte [data-testid="stMetricValue"] { color: #8ecbff !important; font-weight: 600; }
</style>
"""
st.markdown(STYLE.replace("FOND", css_fond()), unsafe_allow_html=True)
st.markdown(construire_decor(), unsafe_allow_html=True)

# ---------------------- Contenu (dans la carte) ----------------------
with st.container(key="carte"):

    # Sécurité
    if not verifier_acces():
        st.stop()

    # Application
    st.title("molVap")
    st.markdown("<p class='phrase'>De la formule à la température d'ébullition, en un clic.</p>",
                unsafe_allow_html=True)

    nom = st.text_input("Molécule (nom anglais, formule ou SMILES) :",
                        placeholder="ethanol", key="saisie")

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
