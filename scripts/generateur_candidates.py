import json
import os
import re
import urllib.request
import urllib.parse

CANDIDATES_FILE = 'data/candidates.json'
FICHES_FILE = 'data/fiches.json'

THEMES_INITIALS = [
    {"sujet": "Phryctorie", "domaine": "HISTOIRE", "theme": "Grèce antique"},
    {"sujet": "Effet Mpemba", "domaine": "SCIENCES", "theme": "Physique"},
    {"sujet": "Mécanisme de Anticythère", "domaine": "INGÉNIERIE", "theme": "Archéologie technologique"},
    {"sujet": "Végétalisme", "domaine": "NATURE", "theme": "Environnement"},
    {"sujet": "Symphonie nº 45 de Haydn", "domaine": "CULTURE", "theme": "Musique classique"},
    {"sujet": "Tour de transmission de Kharkiv", "domaine": "INGÉNIERIE", "theme": "Architecture"},
    {"sujet": "Lac Hillier", "domaine": "NATURE", "theme": "Géographie"}
]

def charger_json(fichier):
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def sauvegarder_json(fichier, donnees):
    os.makedirs(os.path.dirname(fichier), exist_ok=True)
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

def charger_sujets_fiches_existantes():
    """Charge la liste des sujets déjà validés et stockés dans fiches.json."""
    fiches = charger_json(FICHES_FILE)
    return {f.get('sujet', '').strip().lower() for f in fiches if f.get('sujet')}

def rendre_fait_captivant(extract_texte):
    if not extract_texte:
        return ""

    texte = re.sub(r'\([^)]*\)', '', extract_texte)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()

    phrases = re.split(r'(?<=[.!?])\s+', texte)
    if not phrases:
        return ""

    phrase_principale = phrases[0]
    phrase_anecdote = ""
    mots_cles = ['premi', 'plus', 'unique', 'permet', 'utilis', 'grâce', 'découvert', 'record', 'km', 'siècle', 'particulier']

    for p in phrases[1:4]:
        if any(mot in p.lower() for mot in mots_cles):
            phrase_anecdote = p
            break

    if phrase_anecdote and len(phrase_principale + " " + phrase_anecdote) <= 280:
        fait_final = f"{phrase_principale} {phrase_anecdote}"
    else:
        fait_final = phrase_principale

    if len(fait_final) > 280:
        fait_final = fait_final[:280].rsplit(' ', 1)[0].rstrip(' ,;:—–-') + '.'

    if not fait_final.endswith(('.', '!', '?')):
        fait_final += '.'

    return fait_final

def recuperer_fiche_wikipedia(element):
    sujet = element['sujet']
    titre_encode = urllib.parse.quote(sujet.replace(" ", "_"))
    url_api = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre_encode}"

    try:
        req = urllib.request.Request(url_api, headers={'User-Agent': 'NoseyBot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            extract = data.get('extract', '')
            fait_texte = rendre_fait_captivant(extract)

            if not fait_texte:
                return None

            return {
                "id": data.get('wikibase_item', f"id_{hash(sujet)}"),
                "sujet": data.get('title', sujet),
                "domaine": element.get('domaine', 'CURIOSITÉ'),
                "theme": element.get('theme', 'Découverte'),
                "fait_texte": fait_texte,
                "source_nom": "Wikipédia",
                "source_url": data.get('content_urls', {}).get('desktop', {}).get('page', f"https://fr.wikipedia.org/wiki/{titre_encode}"),
                "image_url": data.get('thumbnail', {}).get('source', ''),
                "emojis": {
                    "passer": "🌧️",
                    "positif": "☀️"
                }
            }
    except Exception as e:
        print(f"⚠️ Erreur récupération Wikipédia pour '{sujet}' : {e}")
        return None

def main():
    print("🚀 Vérification des candidates à générer...")
    
    # Récupération des sujets déjà validés dans fiches.json
    sujets_fiches = charger_sujets_fiches_existantes()
    candidates_existantes = charger_json(CANDIDATES_FILE)
    
    # Dictionnaire des sujets déjà présents en attente dans candidates.json
    sujets_candidates = {c.get('sujet', '').strip().lower() for c in candidates_existantes if c.get('sujet')}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    for item in THEMES_INITIALS:
        sujet_cle = item['sujet'].strip().lower()
        
        # Le sujet est ignoré S'IL EST DÉJÀ DANS fiches.json OU DANS candidates.json
        if sujet_cle in sujets_fiches:
            print(f"ℹ️ Sauté (déjà publié dans fiches.json) : {item['sujet']}")
            continue
        if sujet_cle in sujets_candidates:
            print(f"ℹ️ Sauté (déjà en attente dans candidates.json) : {item['sujet']}")
            continue

        print(f"🔍 Traitement du sujet : {item['sujet']}...")
        fiche = recuperer_fiche_wikipedia(item)
        if fiche:
            nouvelles_candidates.append(fiche)
            sujets_candidates.add(sujet_cle)
            ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        print(f"💾 {ajouts} nouvelle(s) candidate(s) ajoutée(s) dans {CANDIDATES_FILE}.\n")
    else:
        print("✅ Aucun nouveau sujet à traiter (tous déjà présents dans fiches.json ou candidates.json).\n")

if __name__ == "__main__":
    main()