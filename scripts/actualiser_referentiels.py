import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "data" / "sources_fiables.json"
CATEGORIES_FILE = ROOT / "data" / "categories_recherche.json"
FICHES_FILE = ROOT / "data" / "fiches.json"

SOURCES_RECONNUES = [
    {"nom": "UNESCO", "domaines": ["whc.unesco.org"]},
    {"nom": "NASA", "domaines": ["nasa.gov"]},
    {"nom": "Agence spatiale européenne (ESA)", "domaines": ["esa.int"]},
    {"nom": "Bibliothèque nationale de France", "domaines": ["bnf.fr"]},
    {"nom": "TAKRAF", "domaines": ["takraf.com"]},
]

MARQUEURS_CATEGORIES_REMARQUABLES = (
    "record",
    "remarquable",
    "exceptionnel",
    "extreme",
    "extremophile",
    "anomalie",
    "superlatif",
    "atypique",
    "insolite",
    "rare",
    "plus grand",
    "plus haut",
    "plus profond",
    "plus ancien",
    "plus rapide",
    "hors norme",
    "sans nom commun",
)


def charger_liste(chemin):
    try:
        with chemin.open(encoding="utf-8") as fichier:
            donnees = json.load(fichier)
    except (OSError, json.JSONDecodeError) as erreur:
        raise RuntimeError(f"Impossible de lire {chemin}: {erreur}") from erreur

    if not isinstance(donnees, list):
        raise ValueError(f"{chemin} doit contenir une liste JSON.")
    return donnees


def normaliser(texte):
    texte = unicodedata.normalize("NFKD", str(texte or "").casefold())
    return "".join(caractere for caractere in texte if not unicodedata.combining(caractere))


def domaines_reconnus(sources):
    return {
        str(domaine).casefold().lstrip(".")
        for source in sources
        if isinstance(source, dict)
        for domaine in source.get("domaines", [])
        if isinstance(domaine, str) and domaine.strip()
    }


def ajouter_sources_reconnues(sources):
    resultat = list(sources)
    domaines_existants = domaines_reconnus(resultat)
    ajouts = []

    for source in SOURCES_RECONNUES:
        domaines = [
            domaine for domaine in source["domaines"]
            if domaine.casefold() not in domaines_existants
        ]
        if not domaines:
            continue
        nouvelle_source = {"nom": source["nom"], "domaines": domaines}
        resultat.append(nouvelle_source)
        domaines_existants.update(domaine.casefold() for domaine in domaines)
        ajouts.append(nouvelle_source)

    return resultat, ajouts


def fiche_appuyee_par_source_fiable(fiche, domaines_fiables):
    urls = [fiche.get("source_url", "")]
    sources = fiche.get("sources", [])
    if isinstance(sources, list):
        urls.extend(
            source.get("url", "")
            for source in sources
            if isinstance(source, dict)
        )

    for url in urls:
        if not isinstance(url, str):
            continue
        hote = (urlparse(url).hostname or "").casefold()
        if any(hote == domaine or hote.endswith(f".{domaine}") for domaine in domaines_fiables):
            return True
    return False


def categorie_principale(fiche):
    theme = str(fiche.get("theme", "")).strip()
    correspondance = re.match(r"Découverte\s+(.+)", theme, re.IGNORECASE)
    if correspondance:
        return correspondance.group(1).strip().upper()
    return ""


def categories_issues_des_fiches(categories, fiches, sources):
    resultat = list(categories)
    domaines_fiables = domaines_reconnus(sources)
    categories_existantes = {
        (
            str(categorie.get("categorie", "")).casefold(),
            str(categorie.get("domaine", "")).casefold(),
            str(categorie.get("categorie_wikipedia", "")).casefold(),
        )
        for categorie in resultat
        if isinstance(categorie, dict)
    }
    ajouts = []

    for fiche in fiches:
        if not isinstance(fiche, dict) or not fiche_appuyee_par_source_fiable(
            fiche, domaines_fiables
        ):
            continue

        categorie_principale_fiche = categorie_principale(fiche)
        domaine = str(fiche.get("domaine", "")).strip().upper()
        categories_wikipedia = fiche.get("categories_wikipedia", [])
        if not categorie_principale_fiche or not domaine or not isinstance(
            categories_wikipedia, list
        ):
            continue

        for categorie in categories_wikipedia:
            if not isinstance(categorie, dict) or categorie.get("ns") not in (None, 14):
                continue
            titre = str(categorie.get("title", "")).strip()
            titre_normalise = normaliser(titre)
            if titre.startswith("Catégorie:"):
                titre = titre[len("Catégorie:"):].strip()
            elif titre.startswith("Category:"):
                titre = titre[len("Category:"):].strip()
            else:
                continue

            if not titre or titre_normalise.startswith(
                ("categorie:portail:", "category:portal:", "categorie:wikipedia:")
            ):
                continue
            if any(
                marqueur in titre_normalise
                for marqueur in ("article ", "page utilisant", "page pointant", "portail:")
            ):
                continue
            if not any(
                marqueur in titre_normalise
                for marqueur in MARQUEURS_CATEGORIES_REMARQUABLES
            ):
                continue

            categorie_wikipedia = titre.replace(" ", "_")
            cle = (
                categorie_principale_fiche.casefold(),
                domaine.casefold(),
                categorie_wikipedia.casefold(),
            )
            if cle in categories_existantes:
                continue

            nouvelle_categorie = {
                "categorie": categorie_principale_fiche,
                "domaine": domaine,
                "categorie_wikipedia": categorie_wikipedia,
            }
            resultat.append(nouvelle_categorie)
            ajouts.append(nouvelle_categorie)
            categories_existantes.add(cle)

    return resultat, ajouts


def ajouter_entrees_au_fichier(chemin, ajouts):
    if not ajouts:
        return False

    contenu = chemin.read_text(encoding="utf-8")
    position_fermeture = contenu.rfind("]")
    if position_fermeture < 0:
        raise ValueError(f"{chemin} ne contient pas de liste JSON.")

    prefixe = contenu[:position_fermeture].rstrip()
    separateur = "" if prefixe.endswith("[") else ","
    objets = [
        "\n".join(
            f"  {ligne}"
            for ligne in json.dumps(entree, ensure_ascii=False, indent=2).splitlines()
        )
        for entree in ajouts
    ]
    texte_objets = ",\n".join(objets)
    contenu_actualise = (
        f"{prefixe}{separateur}\n{texte_objets}\n]"
        f"{contenu[position_fermeture + 1:]}"
    )
    chemin.write_text(contenu_actualise, encoding="utf-8")
    return True


def main():
    sources = charger_liste(SOURCES_FILE)
    categories = charger_liste(CATEGORIES_FILE)
    fiches = charger_liste(FICHES_FILE)

    nouvelles_sources, sources_ajoutees = ajouter_sources_reconnues(sources)
    nouvelles_categories, categories_ajoutees = categories_issues_des_fiches(
        categories, fiches, nouvelles_sources
    )

    ajouter_entrees_au_fichier(SOURCES_FILE, sources_ajoutees)
    ajouter_entrees_au_fichier(CATEGORIES_FILE, categories_ajoutees)

    print(f"Sources reconnues ajoutées : {len(sources_ajoutees)}")
    print(f"Catégories utiles issues de fiches sourcées ajoutées : {len(categories_ajoutees)}")


if __name__ == "__main__":
    main()
