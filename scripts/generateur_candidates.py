import json
import os
import re
import urllib.request
import urllib.parse

CANDIDATES_FILE = 'data/candidates.json'

# Liste de catégories/sujets de départ pour varier les domaines
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

def rendre_fait_captivant(extract_texte):
    """
    Nettoie le texte Wikipédia et extrait une seconde phrase 
    d'impact (chiffre, record, spécificité) pour rendre le fait intéressant.
    """
    if not extract_texte:
        return ""

    # Supprime les dates entre parenthèses, prononciations et appels de notes
    texte = re.sub(r'\([^)]*\)', '', extract_texte)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()

    # Découpage en phrases
    phrases = re.split(r'(?<=[.!?])\s+', texte)
    if not phrases:
        return ""

    phrase_principale = phrases[0]
    phrase_anecdote = ""

    # Mots-clés recherchant l'élément d'impact ou la valeur ajoutée
    mots_cles = ['premi', 'plus', 'unique', 'permet', 'utilis', 'grâce', 'découvert', 'record', 'km', 'siècle', 'particulier']

    for p in phrases[1:4]:
        if any(mot in p.lower() for mot in mots_cles):
            phrase_anecdote = p
            break

    # Assemblage
    if phrase_anecdote and len(phrase_principale + " " + phrase_anecdote) <= 280:
        fait_final = f"{phrase_principale} {phrase_anecdote}"
    else:
        fait_final = phrase_principale

    # Sécurité sur la longueur totale et la ponctuation
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
        print(f"⚠️ Erreur lors de la récupération de '{sujet}' : {e}")
        return None

def main():
    print("🚀 Génération des candidates...")
    candidates_existantes = charger_json(CANDIDATES_FILE)
    sujets_existants = {c.get('sujet') for c in candidates_existantes}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    for item in THEMES_INITIALS:
        if item['sujet'] not in sujets_existants:
            print(f"🔍 Traitement de : {item['sujet']}...")
            fiche = recuperer_fiche_wikipedia(item)
            if fiche:
                nouvelles_candidates.append(fiche)
                sujets_existants.add(item['sujet'])
                ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        print(f"💾 {ajouts} nouvelle(s) fiche(s) ajoutée(s) à {CANDIDATES_FILE}.")
    else:
        print("✅ Aucune nouvelle candidate à ajouter.")

if __name__ == "__main__":
    main()