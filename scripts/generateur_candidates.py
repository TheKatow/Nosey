import json
import os
import re
import random
import urllib.request
import urllib.parse

CANDIDATES_FILE = 'data/candidates.json'
BLACKLIST_FILE = 'data/blacklist.json'
FICHES_FILE = 'data/fiches.json'

THEMES_INITIALS = [
    {"sujet": "Phryctorie", "domaine": "HISTOIRE", "theme": "Grèce antique"},
    {"sujet": "Effet Mpemba", "domaine": "SCIENCES", "theme": "Physique"},
    {"sujet": "Mécanisme d'Anticythère", "domaine": "INGÉNIERIE", "theme": "Archéologie technologique"},
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
    fiches = charger_json(FICHES_FILE)
    blacklist = charger_json(BLACKLIST_FILE)
    
    sujets = {f.get('sujet', '').strip().lower() for f in fiches if f.get('sujet')}
    sujets.update({s.strip().lower() for s in blacklist if isinstance(s, str)})
    return sujets

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

def structurer_fiche(data_wiki, domaine="CURIOSITÉ", theme="Découverte"):
    sujet = data_wiki.get('title', '')
    extract = data_wiki.get('extract', '')
    fait_texte = rendre_fait_captivant(extract)

    if not fait_texte:
        return None

    return {
        "id": data_wiki.get('wikibase_item', f"id_{hash(sujet)}"),
        "sujet": sujet,
        "domaine": domaine,
        "theme": theme,
        "fait_texte": fait_texte,
        "source_nom": "Wikipédia",
        "source_url": data_wiki.get('content_urls', {}).get('desktop', {}).get('page', ''),
        "image_url": data_wiki.get('thumbnail', {}).get('source', ''),
        "emojis": {
            "passer": "🌧️",
            "positif": "☀️"
        }
    }

def recuperer_ingenerie_extraordinaire():
    """Recherche ciblée sur des prouesses et exploits d'ingénierie."""
    mots_cles_recherche = [
        "plus grand pont du monde",
        "prouesse architecturale",
        "tunnel le plus long",
        "record ingénierie",
        "structure la plus haute",
        "machine la plus grande",
        "exploit technologique"
    ]
    
    requete = random.choice(mots_cles_recherche)
    url_search = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(requete)}&utf8=&format=json"

    try:
        req = urllib.request.Request(url_search, headers={'User-Agent': 'NoseyBot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            resultats = data.get('query', {}).get('search', [])
            
            if not resultats:
                return None
            
            choix = random.choice(resultats[:5])
            titre = choix['title']
            titre_encode = urllib.parse.quote(titre.replace(" ", "_"))
            url_summary = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre_encode}"
            
            req_sum = urllib.request.Request(url_summary, headers={'User-Agent': 'NoseyBot/1.0'})
            with urllib.request.urlopen(req_sum, timeout=5) as resp_sum:
                data_summary = json.loads(resp_sum.read().decode('utf-8'))
                return structurer_fiche(data_summary, domaine="INGÉNIERIE", theme="Prouesse technique")
    except Exception as e:
        print(f"⚠️ Erreur recherche ingénierie : {e}")
    
    return None

def main():
    print("🚀 Génération des candidates...")
    
    sujets_fiches = charger_sujets_fiches_existantes()
    candidates_existantes = charger_json(CANDIDATES_FILE)
    sujets_candidates = {c.get('sujet', '').strip().lower() for c in candidates_existantes if c.get('sujet')}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    # 1. Traitement des thèmes de la liste fixe s'ils sont inédits
    for item in THEMES_INITIALS:
        sujet_cle = item['sujet'].strip().lower()
        if sujet_cle in sujets_fiches or sujet_cle in sujets_candidates:
            continue

        print(f"🔍 Traitement du sujet : {item['sujet']}...")
        titre_encode = urllib.parse.quote(item['sujet'].replace(" ", "_"))
        url_api = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre_encode}"
        try:
            req = urllib.request.Request(url_api, headers={'User-Agent': 'NoseyBot/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                fiche = structurer_fiche(data, domaine=item.get('domaine'), theme=item.get('theme'))
                if fiche:
                    nouvelles_candidates.append(fiche)
                    sujets_candidates.add(sujet_cle)
                    ajouts += 1
        except Exception as e:
            print(f"⚠️ Erreur sur '{item['sujet']}' : {e}")

    # 2. Ajout automatique d'un fait d'ingénierie d'exception
    print("🏗️ Recherche d'une prouesse d'ingénierie...")
    fiche_ingenerie = recuperer_ingenerie_extraordinaire()
    if fiche_ingenerie:
        sujet_ing = fiche_ingenerie['sujet'].strip().lower()
        if sujet_ing not in sujets_fiches and sujet_ing not in sujets_candidates:
            print(f"✨ Prouesse trouvée : {fiche_ingenerie['sujet']}")
            nouvelles_candidates.append(fiche_ingenerie)
            ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        print(f"💾 {ajouts} nouvelle(s) candidate(s) enregistrée(s).\n")
    else:
        print("✅ Aucun nouvel ajout requis.\n")

if __name__ == "__main__":
    main()