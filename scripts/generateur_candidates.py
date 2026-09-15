import base64
import json
import os
import re
import random
import unicodedata
import urllib.request
import urllib.parse
from html.parser import HTMLParser

CANDIDATES_FILE = 'data/candidates.json'
BLACKLIST_FILE = 'data/blacklist.json'
FICHES_FILE = 'data/fiches.json'
SOURCES_FIABLES_FILE = 'data/sources_fiables.json'
RECHERCHES_FILE = 'data/recherches.json'
CATEGORIES_FILE = 'data/categories_recherche.json'

MOTS_CLES_VALEUR = [
    'plus long', 'plus grand', 'plus haut', 'plus profond', 'plus ancien', 
    'premi', 'unique', 'record', 'seul', 'particularité', 'prouesse', 
    'exploit', 'découvert', 'inhabituel', 'exceptionnel'
]

class ResultatsRechercheParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resultats = []
        self.lien_courant = None
        self.texte_courant = []
        self.est_extrait = False

    def handle_starttag(self, tag, attrs):
        attributs = dict(attrs)
        classes = attributs.get('class', '').split()
        if tag == 'a' and 'result__a' in classes:
            self.lien_courant = attributs.get('href')
            self.texte_courant = []
        elif tag in ('a', 'div') and 'result__snippet' in classes:
            self.est_extrait = True
            self.texte_courant = []

    def handle_data(self, data):
        if self.lien_courant is not None or self.est_extrait:
            self.texte_courant.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.lien_courant is not None:
            self.resultats.append({
                'url': self.lien_courant,
                'titre': ' '.join(self.texte_courant).strip(),
                'extrait': ''
            })
            self.lien_courant = None
            self.texte_courant = []
        elif tag == 'div' and self.est_extrait:
            if self.resultats:
                self.resultats[-1]['extrait'] = ' '.join(self.texte_courant).strip()
            self.est_extrait = False

class ResultatsBingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resultats = []
        self.resultat_courant = None
        self.champ_courant = None
        self.texte_courant = []

    def handle_starttag(self, tag, attrs):
        attributs = dict(attrs)
        classes = attributs.get('class', '').split()
        if tag == 'li' and 'b_algo' in classes:
            self.resultat_courant = {'url': '', 'titre': '', 'extrait': ''}
        elif self.resultat_courant is not None and tag == 'a' and not self.resultat_courant['url']:
            self.resultat_courant['url'] = attributs.get('href', '')
            self.champ_courant = 'titre'
            self.texte_courant = []
        elif self.resultat_courant is not None and tag == 'p':
            self.champ_courant = 'extrait'
            self.texte_courant = []

    def handle_data(self, data):
        if self.champ_courant:
            self.texte_courant.append(data)

    def handle_endtag(self, tag):
        if tag in ('a', 'p') and self.champ_courant:
            self.resultat_courant[self.champ_courant] = ' '.join(self.texte_courant).strip()
            self.champ_courant = None
            self.texte_courant = []
        elif tag == 'li' and self.resultat_courant is not None:
            if self.resultat_courant['url']:
                self.resultats.append(self.resultat_courant)
            self.resultat_courant = None
            self.texte_courant = []

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

def normaliser_sujet(sujet):
    texte = unicodedata.normalize('NFKD', str(sujet or '').strip().lower())
    return ''.join(caractere for caractere in texte if not unicodedata.combining(caractere))

def charger_sujets_fiches_existantes():
    fiches = charger_json(FICHES_FILE)
    blacklist = charger_json(BLACKLIST_FILE)
    
    sujets = {normaliser_sujet(f.get('sujet')) for f in fiches if f.get('sujet')}
    sujets.update({normaliser_sujet(s) for s in blacklist if isinstance(s, str)})
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

def chercher_source_secondaire(sujet, fait_texte, sources_fiables):
    mots_fait = {mot.lower() for mot in re.findall(r"[A-Za-zÀ-ÿ]{5,}", fait_texte)}

    try:
        for source in sources_fiables:
            domaines = source.get('domaines', [])
            if not domaines:
                continue
            requete = urllib.parse.quote(f'"{sujet}" site:{domaines[0]}')
            url_recherche = f'https://www.bing.com/search?q={requete}'
            req = urllib.request.Request(url_recherche, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                parser = ResultatsBingParser()
                parser.feed(resp.read().decode('utf-8', errors='replace'))

            for resultat in parser.resultats:
                url = resultat['url']
                parametres = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                lien_encode = parametres.get('u', [''])[0]
                if lien_encode.startswith('a1'):
                    try:
                        url = base64.urlsafe_b64decode(lien_encode[2:] + '===').decode('utf-8')
                    except (ValueError, UnicodeDecodeError):
                        continue
                if not any(domaine in url for domaine in domaines):
                    continue
                texte_source = f"{resultat['titre']} {resultat['extrait']}".lower()
                mots_source = set(re.findall(r"[A-Za-zÀ-ÿ]{5,}", texte_source))
                if len(mots_fait.intersection(mots_source)) >= 2:
                    return {
                        'nom': source.get('nom', 'Source fiable'),
                        'url': url,
                        'extrait': resultat['extrait']
                    }
    except Exception as erreur:
        print(f"⚠️ Recherche de source secondaire impossible pour '{sujet}' : {erreur}")

    return None

def structurer_fiche(data_wiki, source_secondaire, domaine="CURIOSITÉ", theme="Découverte"):
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
        "sources": [
            {
                "nom": "Wikipédia",
                "url": data_wiki.get('content_urls', {}).get('desktop', {}).get('page', '')
            },
            source_secondaire
        ],
        "image_url": data_wiki.get('thumbnail', {}).get('source', ''),
        "emojis": {
            "passer": "🌧️",
            "positif": "☀️"
        }
    }

def recuperer_fait_remarquable(requetes_recherche, sources_fiables, domaine, theme):
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
                fait_texte = rendre_fait_captivant(data_summary.get('extract', ''))
                source_secondaire = chercher_source_secondaire(titre, fait_texte, sources_fiables)
                if not source_secondaire:
                    print(f"⚠️ Aucune seconde source fiable pour '{titre}'")
                    return None
                return structurer_fiche(data_summary, source_secondaire, domaine=domaine, theme=theme)
    except Exception as e:
        print(f"⚠️ Erreur recherche {domaine} ({requete}) : {e}")
    
    return None

def choisir_sujet_dynamique(categories, historique, sujets_exclus):
    sujets_deja_recherches = {
        normaliser_sujet(entree.get('sujet'))
        for entree in historique
        if isinstance(entree, dict) and entree.get('sujet')
    }
    sujets_exclus = sujets_exclus | sujets_deja_recherches

    categories_melangees = random.sample(categories, len(categories))
    for categorie in categories_melangees:
        nom_categorie = categorie.get('categorie_wikipedia')
        if not nom_categorie:
            continue

        parametres = urllib.parse.urlencode({
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Catégorie:{nom_categorie}',
            'cmnamespace': '0',
            'cmlimit': '50',
            'format': 'json'
        })
        url = f'https://fr.wikipedia.org/w/api.php?{parametres}'

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                donnees = json.loads(resp.read().decode('utf-8'))
            articles = donnees.get('query', {}).get('categorymembers', [])
            articles = [
                article for article in articles
                if normaliser_sujet(article.get('title')) not in sujets_exclus
            ]
            if articles:
                return categorie, random.choice(articles)['title']
        except Exception as erreur:
            print(f"⚠️ Catégorie Wikipédia inaccessible ({nom_categorie}) : {erreur}")

    return None, None

def main():
    print("🚀 Génération des candidates...")
    
    sujets_fiches = charger_sujets_fiches_existantes()
    candidates_existantes = charger_json(CANDIDATES_FILE)
    sources_fiables = charger_json(SOURCES_FIABLES_FILE)
    historique_recherches = charger_json(RECHERCHES_FILE)
    categories = charger_json(CATEGORIES_FILE)
    sujets_candidates = {normaliser_sujet(c.get('sujet')) for c in candidates_existantes if c.get('sujet')}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    if not sources_fiables or not categories:
        print("⚠️ Configuration de catégories ou de sources fiables absente.")
        return

    categorie, sujet_recherche = choisir_sujet_dynamique(
        categories,
        historique_recherches,
        sujets_fiches | sujets_candidates
    )
    if not categorie or not sujet_recherche:
        print("✅ Aucun nouveau sujet trouvé dans les catégories disponibles.")
        return

    nom_categorie = categorie.get('categorie', 'CURIOSITÉ')
    domaine = categorie.get('domaine', 'CURIOSITÉ')
    print(f"🔎 Recherche dynamique : {nom_categorie} — {sujet_recherche}")
    fiche = recuperer_fait_remarquable(
        [sujet_recherche],
        sources_fiables=sources_fiables,
        domaine=domaine,
        theme=f"Découverte {nom_categorie}"
    )
    historique_recherches.append({
        'categorie': nom_categorie,
        'sujet': sujet_recherche
    })
    sauvegarder_json(RECHERCHES_FILE, historique_recherches)
    if fiche:
        sujet = normaliser_sujet(fiche['sujet'])
        if sujet not in sujets_fiches and sujet not in sujets_candidates:
            print(f"✨ Curiosité confirmée : {fiche['sujet']}")
            nouvelles_candidates.append(fiche)
            sujets_candidates.add(sujet)
            ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        print(f"💾 {ajouts} nouvelle(s) candidate(s) enregistrée(s).\n")
    else:
        print("✅ Aucun nouvel ajout requis.\n")

if __name__ == "__main__":
    main()