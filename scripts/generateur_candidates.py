import json
import os
import re
import random
import urllib.request
import urllib.parse

CANDIDATES_FILE = 'data/candidates.json'
BLACKLIST_FILE = 'data/blacklist.json'
FICHES_FILE = 'data/fiches.json'

MOTS_CLES_VALEUR = [
    'plus long', 'plus grand', 'plus haut', 'plus profond', 'plus ancien', 
    'premi', 'unique', 'record', 'seul', 'particularité', 'prouesse', 
    'exploit', 'découvert', 'inhabituel', 'exceptionnel'
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

def est_phrase_meta_ou_vide(phrase):
    """Détecte les phrases d'introduction abstraites qui ne contiennent aucun fait précis."""
    mot_cles_meta = [
        "peuvent être déterminés", "en fonction de divers critères", "se réfère à",
        "désigne l'ensemble", "est une notion", "est un terme", "peut désigner",
        "regroupe les", "fait référence à"
    ]
    p_lower = phrase.lower()
    return any(m in p_lower for m in mot_cles_meta)

def rendre_fait_captivant(extract_texte):
    if not extract_texte:
        return ""

    texte = re.sub(r'\([^)]*\)', '', extract_texte)
    texte = re.sub(r'\[[^\]]*\]', '', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()

    phrases = re.split(r'(?<=[.!?])\s+', texte)
    if not phrases:
        return ""

    # Éliminer les phrases d'introduction vagues/méta
    phrases_utiles = [p for p in phrases if not est_phrase_meta_ou_vide(p)]

    if not phrases_utiles:
        return ""

    phrase_principale = phrases_utiles[0]
    phrase_anecdote = ""

    # Chercher une phrase secondaire avec un fait concret ou une entité nommée
    for p in phrases_utiles[1:4]:
        if any(mot in p.lower() for mot in MOTS_CLES_VALEUR):
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

def recuperer_fait_remarquable(requetes_recherche, domaine, theme):
    """Effectue une recherche ciblée sur Wikipédia avec un mot-clé orienté 'prouesse/record'."""
    requete = random.choice(requetes_recherche)
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
                return structurer_fiche(data_summary, domaine=domaine, theme=theme)
    except Exception as e:
        print(f"⚠️ Erreur recherche {domaine} ({requete}) : {e}")
    
    return None

def main():
    print("🚀 Génération des candidates...")
    
    sujets_fiches = charger_sujets_fiches_existantes()
    candidates_existantes = charger_json(CANDIDATES_FILE)
    sujets_candidates = {c.get('sujet', '').strip().lower() for c in candidates_existantes if c.get('sujet')}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    # 1. Recherche ciblée d'exploits d'ingénierie
    recherches_ingenerie = [
        "plus long pont d'Europe", "plus grand pont du monde", "prouesse architecturale",
        "tunnel le plus long", "record ingénierie", "structure la plus haute du monde", "machine la plus grande"
    ]
    print("🏗️ Recherche d'une prouesse d'ingénierie...")
    fiche_ing = recuperer_fait_remarquable(recherches_ingenerie, domaine="INGÉNIERIE", theme="Prouesse technique")
    if fiche_ing:
        sujet_ing = fiche_ing['sujet'].strip().lower()
        if sujet_ing not in sujets_fiches and sujet_ing not in sujets_candidates:
            print(f"✨ Prouesse trouvée : {fiche_ing['sujet']}")
            nouvelles_candidates.append(fiche_ing)
            sujets_candidates.add(sujet_ing)
            ajouts += 1

    # 2. Recherche ciblée sur un fait scientifique étonnant
    recherches_sciences = [
        "découverte scientifique insolite", "phénomène physique unique", "adaptation animale exceptionnelle",
        "organisme le plus ancien", "record biologique"
    ]
    print("🔬 Recherche d'une curiosité scientifique...")
    fiche_sci = recuperer_fait_remarquable(recherches_sciences, domaine="SCIENCES", theme="Découverte")
    if fiche_sci:
        sujet_sci = fiche_sci['sujet'].strip().lower()
        if sujet_sci not in sujets_fiches and sujet_sci not in sujets_candidates:
            print(f"✨ Curiosité scientifique trouvée : {fiche_sci['sujet']}")
            nouvelles_candidates.append(fiche_sci)
            sujets_candidates.add(sujet_sci)
            ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        print(f"💾 {ajouts} nouvelle(s) candidate(s) enregistrée(s).\n")
    else:
        print("✅ Aucun nouvel ajout requis.\n")

if __name__ == "__main__":
    main()