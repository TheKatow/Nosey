import json
import urllib.request
import urllib.parse
import re
import os
from datetime import datetime

CANDIDATES_FILE = 'data/candidates.json'

def obtenir_article_wikipedia_aléa():
    """Récupère un résumé d'article aléatoire depuis l'API Wikipédia fr."""
    url = "https://fr.wikipedia.org/api/rest_v1/page/random/summary"
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0 (contact@nosey.app)'})
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération Wikipédia : {e}")
        return None

def nettoyer_et_formater_texte(texte_brut, max_mots=55):
    """Nettoie le texte et le limite à ~50 mots."""
    # Suppression des parenthèses/crochets d'annotations
    texte = re.sub(r'\([^)]*\)', '', texte_brut)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    
    mots = texte.split()
    if len(mots) > max_mots:
        texte = " ".join(mots[:max_mots]) + "..."
    return texte

def generer_nouvelle_candidate():
    """Extrait un sujet Wikipédia et crée une structure de fiche candidate."""
    article = obtenir_article_wikipedia_aléa()
    if not article or article.get('type') != 'standard':
        return None

    sujet = article.get('title', '')
    extract = article.get('extract', '')
    page_url = article.get('content_urls', {}).get('desktop', {}).get('page', '')

    if not sujet or not extract or len(extract.split()) < 25:
        return None

    fait_texte = nettoyer_et_formater_texte(extract)
    
    timestamp_id = datetime.now().strftime('%Y%m%d%H%M%S')
    
    candidate = {
        "id": f"CAND_{timestamp_id}",
        "domaine": "CULTURE",
        "theme": "Découverte",
        "sujet": sujet,
        "fait_texte": fait_texte,
        "localisation": "Monde",
        "emojis": {
            "positif": "🔍",
            "passer": "⏭️"
        },
        "source_nom": "Wikipédia",
        "source_url": page_url,
        "statut": "A_VERIFIER",
        "date_generation": datetime.now().strftime('%Y-%m-%d')
    }
    
    return candidate

def ajouter_candidates(nb_candidates=3):
    """Génère plusieurs candidates et les sauvegarde dans candidates.json."""
    if os.path.exists(CANDIDATES_FILE):
        with open(CANDIDATES_FILE, 'r', encoding='utf-8') as f:
            try:
                candidates = json.load(f)
            except json.JSONDecodeError:
                candidates = []
    else:
        candidates = []

    ajoutees = 0
    tentatives = 0

    while ajoutees < nb_candidates and tentatives < 10:
        tentatives += 1
        nouvelle = generer_nouvelle_candidate()
        if nouvelle:
            # Éviter les doublons de sujet
            if not any(c['sujet'] == nouvelle['sujet'] for c in candidates):
                candidates.append(nouvelle)
                ajoutees += 1
                print(f"➕ Candidate ajoutée : {nouvelle['sujet']}")

    with open(CANDIDATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(f"✅ Terminé : {ajoutees} nouvelle(s) candidate(s) enregistrée(s) dans {CANDIDATES_FILE}.")

if __name__ == "__main__":
    ajouter_candidates(nb_candidates=2)
