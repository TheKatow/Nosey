import json
import urllib.request
import urllib.parse
import re
import os
import random
from datetime import datetime

CANDIDATES_FILE = 'data/candidates.json'

# Catégories Wikipédia ciblées selon la taxonomie de Nosey
CATEGORIES = {
    "NATURE": [
        "Catégorie:Arbre_remarquable",
        "Catégorie:Espèce_animale_remarquable",
        "Catégorie:Champignon_(nom_vernaculaire)"
    ],
    "SCIENCES": [
        "Catégorie:Anatomie_humaine",
        "Catégorie:Découverte_scientifique",
        "Catégorie:Phénomène_physique"
    ],
    "HISTOIRE": [
        "Catégorie:Événement_historique",
        "Catégorie:Objet_archéologique",
        "Catégorie:Personnalité_du_Moyen-Âge"
    ],
    "CULTURE": [
        "Catégorie:Œuvre_d'art",
        "Catégorie:Instrument_de_musique_rare",
        "Catégorie:Monument_historique"
    ],
    "INGENIERIE": [
        "Catégorie:Matériau",
        "Catégorie:Invention",
        "Catégorie:Structure_ingénieuse"
    ]
}

def obtenir_articles_par_categorie(categorie_name):
    """Récupère une liste d'articles appartenant à une catégorie Wikipédia."""
    cat_query = urllib.parse.quote(categorie_name)
    url = f"https://fr.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle={cat_query}&cmlimit=50&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            members = data.get('query', {}).get('categorymembers', [])
            # Filtrer les sous-catégories (ns = 0 pour les vrais articles)
            articles = [m['title'] for m in members if m.get('ns') == 0]
            return articles
    except Exception as e:
        print(f"⚠️ Erreur catégorie {categorie_name} : {e}")
        return []

def obtenir_resume_article(titre):
    """Récupère le résumé Wikipédia d'un article spécifique."""
    titre_query = urllib.parse.quote(titre)
    url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre_query}"
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except Exception:
        return None

def nettoyer_texte(texte_brut, max_mots=55):
    """Nettoie le résumé à ~50 mots."""
    texte = re.sub(r'\([^)]*\)', '', texte_brut)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    mots = texte.split()
    if len(mots) > max_mots:
        texte = " ".join(mots[:max_mots]) + "..."
    return texte

def sujet_deja_existant(titre, candidates):
    """Vérifie si le sujet existe dans candidates.json OU dans fiches.json."""
    # 1. Vérification dans candidates.json
    if any(c['sujet'].lower() == titre.lower() for c in candidates):
        return True

    # 2. Vérification dans fiches.json
    if os.path.exists('data/fiches.json'):
        try:
            with open('data/fiches.json', 'r', encoding='utf-8') as f:
                fiches = json.load(f)
                if any(f_item['sujet'].lower() == titre.lower() for f_item in fiches):
                    return True
        except json.JSONDecodeError:
            pass

    return False

def alimenter_candidates(domaine_cible=None, nb_par_domaine=2):
    """Génère des candidates pour un ou tous les domaines."""
    if os.path.exists(CANDIDATES_FILE):
        with open(CANDIDATES_FILE, 'r', encoding='utf-8') as f:
            try:
                candidates = json.load(f)
            except json.JSONDecodeError:
                candidates = []
    else:
        candidates = []

    domaines_a_traiter = [domaine_cible] if domaine_cible in CATEGORIES else list(CATEGORIES.keys())
    
    nouvelles_ajoutees = 0

    for domaine in domaines_a_traiter:
        categories_domaine = CATEGORIES[domaine]
        cat_choisie = random.choice(categories_domaine)
        articles = obtenir_articles_par_categorie(cat_choisie)
        
        if not articles:
            continue
            
        random.shuffle(articles)
        ajoutees_domaine = 0
        
        for titre in articles:
            if ajoutees_domaine >= nb_par_domaine:
                break
                
            # Éviter les doublons
            if any(c['sujet'].lower() == titre.lower() for c in candidates):
                continue

            summary = obtenir_resume_article(titre)
            if not summary or summary.get('type') != 'standard':
                continue

            extract = summary.get('extract', '')
            if not extract or len(extract.split()) < 25:
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
                "emojis": {
                    "positif": "☀️",
                    "passer": "🌧️"
                },
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

    print(f"\n✅ Total : {nouvelles_ajoutees} nouvelle(s) candidate(s) enregistrée(s) dans {CANDIDATES_FILE}.")

if __name__ == "__main__":
    # Exécution : génère 2 sujets par domaine (Nature, Sciences, Histoire, Culture, Ingénierie)
    alimenter_candidates(nb_par_domaine=2)
