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


st.set_page_config(page_title="Température d'ébullition", layout="wide")
st.title("Température d'ébullition + structure 3D")

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
            
            
            
            
