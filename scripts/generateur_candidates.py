import json
import urllib.request
import urllib.parse
import re
import os
import random
from datetime import datetime

CANDIDATES_FILE = 'data/candidates.json'
FICHES_FILE = 'data/fiches.json'
MAX_CANDIDATES_PENDING = 30  # Parade #2 : Plafond anti-saturation

# Parade #5 : Catégories élargies pour éviter l'épuisement
CATEGORIES = {
    "NATURE": [
        "Catégorie:Arbre_remarquable",
        "Catégorie:Espèce_animale_remarquable",
        "Catégorie:Champignon_(nom_vernaculaire)",
        "Catégorie:Minéral",
        "Catégorie:Écosystème"
    ],
    "SCIENCES": [
        "Catégorie:Anatomie_humaine",
        "Catégorie:Découverte_scientifique",
        "Catégorie:Phénomène_physique",
        "Catégorie:Astronomie",
        "Catégorie:Concept_mathématique"
    ],
    "HISTOIRE": [
        "Catégorie:Événement_historique",
        "Catégorie:Objet_archéologique",
        "Catégorie:Personnalité_du_Moyen-Âge",
        "Catégorie:Civilisation_ancienne",
        "Catégorie:Bataille_historique"
    ],
    "CULTURE": [
        "Catégorie:Œuvre_d'art",
        "Catégorie:Instrument_de_musique_rare",
        "Catégorie:Monument_historique",
        "Catégorie:Tradition_populaire",
        "Catégorie:Mythologie"
    ],
    "INGENIERIE": [
        "Catégorie:Matériau",
        "Catégorie:Invention",
        "Catégorie:Structure_ingénieuse",
        "Catégorie:Pont_remarquable",
        "Catégorie:Technologie_obsolète"
    ]
}

EMOJIS_DOMAINES = {
    "NATURE": {"positif": "🌿", "passer": "🍂"},
    "SCIENCES": {"positif": "🔬", "passer": "💨"},
    "HISTOIRE": {"positif": "📜", "passer": "⏳"},
    "CULTURE": {"positif": "🎨", "passer": "🌫️"},
    "INGENIERIE": {"positif": "⚙️", "passer": "🔩"}
}

def charger_json(fichier):
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def sujet_deja_existant(titre, candidates, fiches):
    """Vérifie si le sujet existe dans candidates.json ou fiches.json."""
    titre_lower = titre.lower()
    if any(c.get('sujet', '').lower() == titre_lower for c in candidates):
        return True
    if any(f.get('sujet', '').lower() == titre_lower for f in fiches):
        return True
    return False

def obtenir_articles_par_categorie(categorie_name):
    cat_query = urllib.parse.quote(categorie_name)
    url = f"https://fr.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle={cat_query}&cmlimit=50&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            members = data.get('query', {}).get('categorymembers', [])
            return [m['title'] for m in members if m.get('ns') == 0]
    except Exception:
        return []

def obtenir_resume_article(titre):
    titre_query = urllib.parse.quote(titre)
    url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre_query}"
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

def est_texte_valide(texte):
    """Parade #1 : Filtre les résumés jargonneux ou tronqués."""
    mots = texte.split()
    if len(mots) < 30 or len(mots) > 80:
        return False
    # Exclusion des tournures floues/relatives
    mots_interdits = ["récemment", "l'année dernière", "actuellement", "voir ci-dessous"]
    if any(m in texte.lower() for m in mots_interdits):
        return False
    return True

def nettoyer_texte(texte_brut, max_mots=55):
    texte = re.sub(r'\([^)]*\)', '', texte_brut)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    mots = texte.split()
    if len(mots) > max_mots:
        texte = " ".join(mots[:max_mots]) + "..."
    return texte

def alimenter_candidates(nb_par_domaine=2):
    candidates = charger_json(CANDIDATES_FILE)
    fiches = charger_json(FICHES_FILE)

    # Parade #2 : Arrêt si la file est saturée
    if len(candidates) >= MAX_CANDIDATES_PENDING:
        print(f"🛑 File temporaire saturée ({len(candidates)}/{MAX_CANDIDATES_PENDING} candidates). Pas d'extraction.")
        return

    nouvelles_ajoutees = 0

    for domaine, cat_list in CATEGORIES.items():
        if len(candidates) >= MAX_CANDIDATES_PENDING:
            break

        cat_choisie = random.choice(cat_list)
        articles = obtenir_articles_par_categorie(cat_choisie)
        if not articles:
            continue

        random.shuffle(articles)
        ajoutees_domaine = 0

        for titre in articles:
            if ajoutees_domaine >= nb_par_domaine or len(candidates) >= MAX_CANDIDATES_PENDING:
                break

            if sujet_deja_existant(titre, candidates, fiches):
                continue

            summary = obtenir_resume_article(titre)
            if not summary or summary.get('type') != 'standard':
                continue

            extract = summary.get('extract', '')
            if not est_texte_valide(extract):
                continue

            fait_texte = nettoyer_texte(extract)
            timestamp_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))

            candidate = {
                "id": f"{domaine[:3]}_{timestamp_id}",
                "domaine": domaine,
                "theme": cat_choisie.replace("Catégorie:", "").replace("_", " "),
                "sujet": titre,
                "fait_texte": fait_texte,
                "localisation": "Monde",
                "emojis": EMOJIS_DOMAINES.get(domaine, {"positif": "☀️", "passer": "🌧️"}),
                "source_nom": "Wikipédia",
                "source_url": summary.get('content_urls', {}).get('desktop', {}).get('page', ''),
                "statut": "A_VERIFIER",
                "date_generation": datetime.now().strftime('%Y-%m-%d')
            }

            candidates.append(candidate)
            ajoutees_domaine += 1
            nouvelles_ajoutees += 1
            print(f"➕ [{domaine}] Candidate ajoutée : {titre}")

    with open(CANDIDATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Terminé : {nouvelles_ajoutees} candidate(s) ajoutée(s). Total file : {len(candidates)}.")

if __name__ == "__main__":
    alimenter_candidates(nb_par_domaine=2)