import base64
import hashlib
import json
import logging
import re
import random
import time
import unicodedata
import urllib.request
import urllib.parse
from html.parser import HTMLParser
import os
from google import genai
from google.genai import types

cle_api = os.environ.get('GEMINI_API_KEY')
if not cle_api:
    raise RuntimeError(
        "GEMINI_API_KEY est absente. Définissez-la dans vos secrets GitHub."
    )

client = genai.Client(api_key=cle_api)
MODELE_GEMINI = 'gemini-3.6-flash'
CONFIG_GEMINI_SANS_AFC = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class LimitationReseau(Exception):
    pass

CANDIDATES_FILE = 'data/candidates.json'
BLACKLIST_FILE = 'data/blacklist.json'
FICHES_FILE = 'data/fiches.json'
SOURCES_FIABLES_FILE = 'data/sources_fiables.json'
RECHERCHES_FILE = 'data/recherches.json'
CATEGORIES_FILE = 'data/categories_recherche.json'

MOTS_CLES_VALEUR = [
    'plus long', 'plus grand', 'plus haut', 'plus profond', 'plus ancien', 
    'premier', 'unique', 'record', 'seul', 'particularité', 'prouesse', 
    'exploit', 'découvert', 'inhabituel', 'exceptionnel', 'extrême'
]

MOTS_CLES_RECORD = [
    'record', 'meilleur', 'champion', 'classement', 'performance',
    'plus grand', 'plus haut', 'plus long', 'plus rapide', 'premier',
    'victoire', 'médaille', 'titre mondial', 'fois', 'km', 'kilomètre',
    'mètre', 'seconde', 'minute', 'heure', '%'
]

CATEGORIES_WIKIPEDIA_REMARQUABLES = [
    'record', 'remarquable', 'exceptionnel', 'extrême', 'extrêmophile',
    'anomalie', 'superlatif', 'atypique', 'insolite', 'rare', 'plus grand',
    'plus haut', 'plus profond', 'plus ancien', 'plus rapide', 'hors norme',
    'sans nom commun'
]

EMOJIS_PAR_DOMAINE = {
    'animal': {'positif': '🐾', 'passer': '🍂'},
    'biologie': {'positif': '🧬', 'passer': '🍃'},
    'nature': {'positif': '🌿', 'passer': '🍂'},
    'plantes': {'positif': '🌱', 'passer': '🥀'},
    'geographie': {'positif': '🗺️', 'passer': '🌫️'},
    'phenomenes_naturels': {'positif': '🌋', 'passer': '🌪️'},
    'meteorologie': {'positif': '🌤️', 'passer': '⛈️'},
    'sciences': {'positif': '🔬', 'passer': '🧪'},
    'astronomie': {'positif': '🌠', 'passer': '🌑'},
    'espace': {'positif': '🚀', 'passer': '🛰️'},
    'ingenierie': {'positif': '⚙️', 'passer': '🔧'},
    'architecture': {'positif': '🏗️', 'passer': '🏚️'},
    'technologie': {'positif': '💡', 'passer': '📟'},
    'histoire': {'positif': '🏛️', 'passer': '⌛'},
    'historique': {'positif': '📜', 'passer': '🕰️'},
    'archeologie': {'positif': '🏺', 'passer': '⛏️'},
    'patrimoine': {'positif': '🏰', 'passer': '🗿'},
    'culture': {'positif': '🎨', 'passer': '🌫️'},
    'records': {'positif': '🏆', 'passer': '🥈'},
    'records_animaux': {'positif': '🥇', 'passer': '📉'},
    'superlatifs': {'positif': '👑', 'passer': '📏'},
    'chimie': {'positif': '⚗️', 'passer': '💥'},
    'physique': {'positif': '⚛️', 'passer': '🌀'},
    'materiaux': {'positif': '🧱', 'passer': '🪨'},
    'paleontologie': {'positif': '🦴', 'passer': '🦕'},
    'infrastructures': {'positif': '🌉', 'passer': '🚧'},
    'lieux_remarquables': {'positif': '📍', 'passer': '🧭'},
    'curiosite': {'positif': '✨', 'passer': '🌫️'},
}

def choisir_emojis(domaine):
    """Sélectionne les emojis uniquement selon le domaine de la fiche."""
    domaine_normalise = normaliser_sujet(domaine)
    return EMOJIS_PAR_DOMAINE.get(
        domaine_normalise,
        EMOJIS_PAR_DOMAINE['curiosite']
    ).copy()

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

def extraire_fait_depuis_wikipedia(sujet, extract_texte):
    """Construit un fait court depuis Wikipédia quand Gemini est limité."""
    texte = ' '.join(str(extract_texte or '').split())
    if len(texte) < 180:
        logger.info(
            "Résumé Wikipédia trop court pour '%s' (%d caractères).",
            sujet,
            len(texte)
        )
        return ""

    phrases = [
        phrase.strip()
        for phrase in re.split(r'(?<=[.!?])\s+', texte)
        if phrase.strip()
    ]
    phrases_factuelles = [
        phrase for phrase in phrases
        if re.search(r'\d', phrase)
        and len(re.findall(r"[A-Za-zÀ-ÿ]+", phrase)) >= 8
    ]
    phrases_localisees = [
        phrase for phrase in phrases
        if re.search(
            r"\b(?:en|à|au|aux|dans|sur|près de|originaire de)\s+"
            r"[A-ZÀ-ÖØ-Ý][\wÀ-ÿ'-]*",
            phrase
        )
    ]

    selection = []
    for phrase in phrases_factuelles + phrases_localisees:
        if phrase not in selection:
            selection.append(phrase)
        if len(selection) == 2:
            break

    phrase_localisee = next(
        (phrase for phrase in phrases_localisees if phrase in selection),
        None
    )
    if phrase_localisee is None and phrases_localisees:
        selection[-1] = phrases_localisees[0]

    if not selection:
        logger.info("Aucun fait chiffré exploitable dans Wikipédia pour '%s'.", sujet)
        return ""

    fait = ' '.join(selection)
    mots = fait.split()
    if len(mots) > 80:
        fait = ' '.join(mots[:80]).rstrip(' ,;:') + '.'

    if not re.search(r'\d', fait) or not extraire_localisation(fait):
        logger.info("Fait Wikipédia insuffisant pour '%s'.", sujet)
        return ""

    return fait

def sommer_articles_en_faits(articles):
    """Résume plusieurs extraits en un seul appel Gemini, indexé par article."""
    articles_exploitables = [
        article for article in articles
        if len(str(article.get('extract', '')).strip()) >= 50
    ]
    if not articles_exploitables:
        return {}

    extraits = '\n\n'.join(
        f"[{index}] {article['title']}\n{article['extract']}"
        for index, article in enumerate(articles_exploitables, start=1)
    )
    prompt = f"""
Tu es l'éditeur de l'application Nosey. Pour chaque extrait Wikipédia numéroté ci-dessous, écris un fait marquant.

{extraits}

Consignes strictes pour chaque fait :
1. 15 à 80 mots, terminé par un point.
2. Contenir une donnée chiffrée, un exemple concret et une localisation explicite.
3. Écarter les phrases vagues ou génériques.
4. Si l'extrait ne permet pas un fait précis, sa valeur est "INVALIDE".

Réponds uniquement avec un objet JSON dont les clés sont les numéros entre guillemets et les valeurs les faits. Ne mélange pas les articles.
"""

    for tentative in range(3):
        try:
            response = client.models.generate_content(
                model=MODELE_GEMINI,
                contents=prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                    response_mime_type='application/json',
                ),
            )
            resultats = json.loads(response.text)
            if not isinstance(resultats, dict):
                raise ValueError("La réponse Gemini n'est pas un objet JSON.")
            faits = {}
            for index, article in enumerate(articles_exploitables, start=1):
                fait = resultats.get(str(index), '')
                if isinstance(fait, str) and not re.fullmatch(
                    r'INVALIDE[.!]?', fait.strip(), re.IGNORECASE
                ):
                    faits[article['title']] = fait.strip()
            return faits
        except Exception as erreur:
            erreur_texte = str(erreur)
            if '429' in erreur_texte or 'RESOURCE_EXHAUSTED' in erreur_texte:
                logger.warning(
                    "Quota Gemini atteint pour le lot de %d articles; "
                    "l'extraction Wikipédia locale sera utilisée.",
                    len(articles_exploitables)
                )
                return {}
            est_indisponible = '503' in erreur_texte or 'UNAVAILABLE' in erreur_texte
            if not est_indisponible or tentative == 2:
                logger.warning("Échec du résumé Gemini par lot : %s", erreur)
                return {}
            delai = 2 ** tentative
            logger.warning("Gemini indisponible; nouvelle tentative dans %d s.", delai)
            time.sleep(delai)
    return {}

def sommer_article_en_fait(sujet, extract_texte):
    """Conserve le traitement unitaire utilisé par structurer_fiche."""
    faits = sommer_articles_en_faits([{
        'title': sujet,
        'extract': extract_texte
    }])
    return faits.get(sujet) or extraire_fait_depuis_wikipedia(sujet, extract_texte)

def extraire_localisation(fait_texte):
    correspondance = re.search(
        r"\b(?:en|à|au|aux|dans|sur|près de|originaire de)\s+"
        r"([A-ZÀ-ÖØ-Ý][\wÀ-ÿ'-]*(?:\s+(?:de|du|des|d'|la|le|les|[A-ZÀ-ÖØ-Ý][\wÀ-ÿ'-]*)){0,4})",
        fait_texte,
        re.IGNORECASE
    )
    return correspondance.group(1).strip() if correspondance else ''

def structurer_fiche(data_wiki, source_secondaire, domaine="CURIOSITÉ", theme="Découverte", fait_texte=None, categories_wikipedia=None):
    sujet = data_wiki.get('title', '').strip()
    if fait_texte is None:
        fait_texte = sommer_article_en_fait(sujet, data_wiki.get('extract', ''))
    
    source_url = data_wiki.get('content_urls', {}).get('desktop', {}).get('page', '')
    localisation = extraire_localisation(fait_texte)

    if not fait_texte or not localisation or not source_url or not source_secondaire:
        return None

    identifiant = data_wiki.get('wikibase_item')
    if not identifiant:
        identifiant = 'id_' + hashlib.sha1(sujet.encode('utf-8')).hexdigest()[:12]

    return {
        "id": identifiant,
        "sujet": sujet,
        "domaine": domaine,
        "theme": theme,
        "fait_texte": fait_texte,
        "categories_wikipedia": categories_wikipedia or [],
        "source_nom": "Wikipédia",
        "source_url": source_url,
        "sources": [
            {"nom": "Wikipédia", "url": source_url},
            source_secondaire
        ],
        "localisation": localisation,
        "image_url": data_wiki.get('thumbnail', {}).get('source', ''),
        "emojis": choisir_emojis(domaine)
    }

def categories_indiquent_fait_remarquable(categories):
    for categorie in categories:
        titre = categorie.get('title', '') if isinstance(categorie, dict) else categorie
        nom = str(titre).lower().replace('catégorie:', '').replace('_', ' ')
        if any(marqueur in nom for marqueur in CATEGORIES_WIKIPEDIA_REMARQUABLES):
            return True
    return False

def recuperer_categories_wikipedia(titre):
    parametres = urllib.parse.urlencode({
        'action': 'query',
        'prop': 'categories',
        'titles': titre,
        'cllimit': 'max',
        'format': 'json'
    })
    url = f'https://fr.wikipedia.org/w/api.php?{parametres}'
    req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            donnees = json.loads(resp.read().decode('utf-8'))
        pages = donnees.get('query', {}).get('pages', {}).values()
        return next((page.get('categories', []) for page in pages), [])
    except urllib.error.HTTPError as erreur:
        if erreur.code == 429:
            raise LimitationReseau(f"Wikipédia limite la recherche de catégories pour '{titre}'") from erreur
        logger.warning("Catégories Wikipédia indisponibles pour '%s' : %s", titre, erreur)
    except Exception as erreur:
        logger.warning("Catégories Wikipédia indisponibles pour '%s' : %s", titre, erreur)
    return []

def fait_remarquable(fait_texte, domaine, categories_wikipedia=None):
    texte = normaliser_sujet(fait_texte)
    if not texte:
        return False

    if categories_indiquent_fait_remarquable(categories_wikipedia or []):
        return True

    phrases_generiques = (
        'est une espece de',
        'est une plante de',
        'est un genre de',
        'est une famille de',
        'est un ensemble de',
        'designe une',
        'fait partie de'
    )
    if any(texte.startswith(phrase) for phrase in phrases_generiques):
        return False

    if domaine.lower() == 'records':
        return any(mot in texte for mot in MOTS_CLES_RECORD)

    return any(mot in texte for mot in MOTS_CLES_VALEUR) or bool(re.search(r'\d', texte))

def chercher_source_secondaire(sujet, fait_texte, sources_fiables, liens_externes=None):
    mots_fait = {mot.lower() for mot in re.findall(r"[A-Za-zÀ-ÿ]{5,}", fait_texte)}
    logger.info("Seconde source pour '%s' : %d mots-clés.", sujet, len(mots_fait))

    try:
        if liens_externes is None:
            parametres = urllib.parse.urlencode({
                'action': 'query',
                'prop': 'extlinks',
                'titles': sujet,
                'ellimit': 'max',
                'format': 'json'
            })
            url_wikipedia = f'https://fr.wikipedia.org/w/api.php?{parametres}'
            req = urllib.request.Request(url_wikipedia, headers={'User-Agent': 'NoseyBot/1.0'})
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    donnees = json.loads(resp.read().decode('utf-8'))
            except urllib.error.HTTPError as erreur:
                if erreur.code == 429:
                    raise LimitationReseau(f"Wikipédia limite la recherche de '{sujet}'") from erreur
                raise

            liens_externes = [
                lien.get('*', '')
                for page in donnees.get('query', {}).get('pages', {}).values()
                for lien in page.get('extlinks', [])
            ]

        for source in sources_fiables:
            domaines = source.get('domaines', [])
            for url in liens_externes:
                hote = urllib.parse.urlparse(url).hostname or ''
                if not any(hote == domaine or hote.endswith(f'.{domaine}') for domaine in domaines):
                    continue
                logger.info("Seconde source trouvée via Wikipédia : %s (%s).", source.get('nom'), hote)
                return {
                    'nom': source.get('nom', 'Source fiable'),
                    'url': url,
                    'extrait': 'Source externe référencée par Wikipédia.'
                }

        for source in sources_fiables:
            domaines = source.get('domaines', [])
            if not domaines:
                continue
            requete = urllib.parse.quote(f'"{sujet}" site:{domaines[0]}')
            url_recherche = f'https://www.bing.com/search?q={requete}'
            req = urllib.request.Request(url_recherche, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    parser = ResultatsBingParser()
                    parser.feed(resp.read().decode('utf-8', errors='replace'))
            except urllib.error.HTTPError as erreur:
                if erreur.code == 429:
                    raise LimitationReseau(f"Bing limite la recherche de '{sujet}'") from erreur
                continue

            for resultat in parser.resultats:
                url = resultat['url']
                parametres = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                lien_encode = parametres.get('u', [''])[0]
                if lien_encode.startswith('a1'):
                    try:
                        url = base64.urlsafe_b64decode(lien_encode[2:] + '===').decode('utf-8')
                    except (ValueError, UnicodeDecodeError):
                        continue
                hote = urllib.parse.urlparse(url).hostname or ''
                if not any(hote == domaine or hote.endswith(f'.{domaine}') for domaine in domaines):
                    continue
                texte_source = f"{resultat['titre']} {resultat['extrait']}".lower()
                mots_source = set(re.findall(r"[A-Za-zÀ-ÿ]{5,}", texte_source))
                if len(mots_fait.intersection(mots_source)) >= 2:
                    logger.info("Seconde source trouvée via Bing : %s.", url)
                    return {
                        'nom': source.get('nom', 'Source fiable'),
                        'url': url,
                        'extrait': resultat['extrait']
                    }
    except LimitationReseau:
        raise
    except Exception as erreur:
        logger.exception("Recherche de source secondaire impossible pour '%s' : %s", sujet, erreur)

    return None

def construire_requete_remarquable(sujet):
    """Oriente la recherche vers des sujets inhabituels dans la catégorie choisie."""
    qualificatifs = 'exceptionnel OR extraordinaire OR remarquable OR rare'
    return f'{sujet} ({qualificatifs})'

def recuperer_pages_wikipedia(titres):
    """Récupère les extraits et liens externes de plusieurs pages en un appel."""
    parametres = urllib.parse.urlencode({
        'action': 'query',
        'prop': 'extracts|pageimages|info|pageprops|extlinks|categories',
        'titles': '|'.join(titres),
        'exintro': '1',
        'explaintext': '1',
        'exchars': '3500',
        'piprop': 'thumbnail',
        'pithumbsize': '600',
        'inprop': 'url',
        'ellimit': 'max',
        'cllimit': 'max',
        'redirects': '1',
        'format': 'json'
    })
    url_wikipedia = f'https://fr.wikipedia.org/w/api.php?{parametres}'
    req = urllib.request.Request(url_wikipedia, headers={'User-Agent': 'NoseyBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            donnees = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as erreur:
        if erreur.code == 429:
            raise LimitationReseau("Wikipédia limite la récupération du lot de pages") from erreur
        raise

    pages_par_titre = {}
    for page in donnees.get('query', {}).get('pages', {}).values():
        titre = page.get('title', '')
        if not titre or 'missing' in page:
            continue
        pages_par_titre[normaliser_sujet(titre)] = {
            'title': titre,
            'extract': page.get('extract', ''),
            'content_urls': {'desktop': {'page': page.get('fullurl', '')}},
            'thumbnail': page.get('thumbnail', {}),
            'wikibase_item': page.get('pageprops', {}).get('wikibase_item'),
            'extlinks': [
                lien.get('*', '') for lien in page.get('extlinks', [])
            ],
            'categories_wikipedia': page.get('categories', [])
        }

    return [
        pages_par_titre[normaliser_sujet(titre)]
        for titre in titres
        if normaliser_sujet(titre) in pages_par_titre
    ]

def recuperer_fait_remarquable(requetes_recherche, sources_fiables, domaine, theme):
    sujet = random.choice(requetes_recherche)
    requete = construire_requete_remarquable(sujet)
    logger.info("Recherche Wikipédia dans le domaine %s avec la requête '%s'.", domaine, requete)
    url_search = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(requete)}&utf8=&format=json"

    try:
        req = urllib.request.Request(url_search, headers={'User-Agent': 'NoseyBot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            resultats = data.get('query', {}).get('search', [])
            
            if not resultats:
                return None
            
            titres_a_tester = list(dict.fromkeys(
                resultat.get('title', '') for resultat in resultats
                if resultat.get('title')
            ))[:6]
            articles = recuperer_pages_wikipedia(titres_a_tester)
            faits_gemini = sommer_articles_en_faits(articles)

            for data_summary in articles:
                titre = data_summary['title']
                categories_wikipedia = data_summary.get('categories_wikipedia', [])
                fait_texte = faits_gemini.get(titre, '')
                if not fait_texte:
                    fait_texte = extraire_fait_depuis_wikipedia(
                        titre,
                        data_summary.get('extract', '')
                    )
                if not fait_texte or not fait_remarquable(
                    fait_texte,
                    domaine,
                    categories_wikipedia
                ):
                    continue

                source_secondaire = chercher_source_secondaire(
                    titre,
                    fait_texte,
                    sources_fiables,
                    liens_externes=data_summary.get('extlinks', [])
                )
                if source_secondaire:
                    logger.info("Article retenu : '%s'.", titre)
                    return structurer_fiche(
                        data_summary,
                        source_secondaire,
                        domaine=domaine,
                        theme=theme,
                        fait_texte=fait_texte,
                        categories_wikipedia=categories_wikipedia
                    )

            return None
    except LimitationReseau:
        raise
    except Exception as e:
        logger.exception("Erreur recherche %s (%s) : %s", domaine, requete, e)
    
    return None

def choisir_sujet_dynamique(categories, historique, sujets_exclus):
    """Choisit un terme de recherche parmi les catégories configurées en dur."""
    sujets_deja_recherches = {
        normaliser_sujet(entree.get('sujet'))
        for entree in historique
        if isinstance(entree, dict) and entree.get('sujet')
    }
    sujets_exclus = sujets_exclus | sujets_deja_recherches

    categories_disponibles = [
        categorie for categorie in categories
        if categorie.get('categorie_wikipedia')
        and normaliser_sujet(categorie['categorie_wikipedia']) not in sujets_exclus
    ]
    if categories_disponibles:
        categorie = random.choice(categories_disponibles)
        return categorie, categorie['categorie_wikipedia']

    return None, None

def main():
    logger.info("Recherche d'articles extraordinaires pour Nosey...")

    sujets_fiches = charger_sujets_fiches_existantes()
    candidates_existantes = charger_json(CANDIDATES_FILE)
    sources_fiables = charger_json(SOURCES_FIABLES_FILE)
    historique_recherches = charger_json(RECHERCHES_FILE)
    categories = charger_json(CATEGORIES_FILE)
    sujets_candidates = {normaliser_sujet(c.get('sujet')) for c in candidates_existantes if c.get('sujet')}

    nouvelles_candidates = list(candidates_existantes)
    ajouts = 0

    if not sources_fiables or not categories:
        logger.error("Configuration absente (categories_recherche.json ou sources_fiables.json).")
        return

    categorie, sujet_recherche = choisir_sujet_dynamique(
        categories,
        historique_recherches,
        sujets_fiches | sujets_candidates
    )
    if not categorie or not sujet_recherche:
        logger.info("Aucun nouveau sujet disponible dans les catégories actuelles.")
        return

    nom_categorie = categorie.get('categorie', 'CURIOSITÉ')
    domaine = categorie.get('domaine', 'CURIOSITÉ')
    logger.info("Traitement du sujet : %s (%s)", sujet_recherche, nom_categorie)

    try:
        fiche = recuperer_fait_remarquable(
            [sujet_recherche],
            sources_fiables=sources_fiables,
            domaine=domaine,
            theme=f"Découverte {nom_categorie}"
        )
    except LimitationReseau as erreur:
        logger.warning("%s. Sujet reporté : '%s'.", erreur, sujet_recherche)
        return 75

    if fiche:
        historique_recherches.append({'categorie': nom_categorie, 'sujet': sujet_recherche})
        sauvegarder_json(RECHERCHES_FILE, historique_recherches)
        
        sujet = normaliser_sujet(fiche['sujet'])
        if sujet not in sujets_fiches and sujet not in sujets_candidates:
            logger.info("Nouvelle fiche candidate retenue : %s", fiche['sujet'])
            nouvelles_candidates.append(fiche)
            ajouts += 1

    if ajouts > 0:
        sauvegarder_json(CANDIDATES_FILE, nouvelles_candidates)
        logger.info("%d nouvelle candidate enregistrée.", ajouts)

if __name__ == "__main__":
    raise SystemExit(main() or 0)