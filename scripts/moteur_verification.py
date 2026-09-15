import json
import os
import urllib.request
import urllib.parse

CANDIDATES_FILE = 'data/candidates.json'
FICHES_FILE = 'data/fiches.json'
NTFY_TOPIC_URL = "https://ntfy.sh/Nosey"

MOTS_INTERDITS = [
    "récemment", "l'année dernière", "actuellement", 
    "voir ci-dessous", "cliquez ici", "sponsorisé"
]

def envoyer_notification_ntfy(titre, message, priorite="default"):
    """Envoie une notification synthétique via Ntfy.sh."""
    try:
        req = urllib.request.Request(
            NTFY_TOPIC_URL,
            data=message.encode('utf-8'),
            headers={
                "Title": titre.encode('utf-8'),
                "Priority": priorite,
                "Tags": "mag_right,robot"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"⚠️ Impossible d'envoyer la notification Ntfy : {e}")

def charger_json(fichier):
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def sauvegarder_json(fichier, donnees):
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

def tester_url(url):
    """Vérifie que l'URL source répond correctement avec un code HTTP 200."""
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def verifier_et_nettoyer_fiches_publiees():
    """Parade #3 : Vérifie l'accessibilité des sources dans fiches.json et retire les liens cassés."""
    fiches = charger_json(FICHES_FILE)
    if not fiches:
        return 0

    fiches_valides = []
    liens_casses = 0

    for fiche in fiches:
        url = fiche.get('source_url', '')
        if tester_url(url):
            fiches_valides.append(fiche)
        else:
            liens_casses += 1
            print(f"🗑️ Lien cassé détecté dans fiches.json : {fiche.get('sujet')} ({url})")

    if liens_casses > 0:
        sauvegarder_json(FICHES_FILE, fiches_valides)
        print(f"🧹 Nettoyage terminé : {liens_casses} fiche(s) retirée(s) de fiches.json.")

    return liens_casses

def valider_candidate(candidate):
    """Contrôle la validité d'une candidate avant ingestion."""
    sujet = candidate.get('sujet', '').strip()
    fait = candidate.get('fait_texte', '').strip()
    url = candidate.get('source_url', '').strip()

    if not sujet or not fait or not url:
        return False, "Champs requis manquants"

    mots = fait.split()
    if len(mots) < 20 or len(mots) > 80:
        return False, f"Longueur de texte invalide ({len(mots)} mots)"

    fait_lower = fait.lower()
    for mot in MOTS_INTERDITS:
        if mot in fait_lower:
            return False, f"Mot interdit détecté : '{mot}'"

    if not tester_url(url):
        return False, "URL source inaccessible (HTTP != 200)"

    return True, "Valide"

def traiter_candidates():
    """Traite candidates.json, transfère les fiches validées vers fiches.json."""
    candidates = charger_json(CANDIDATES_FILE)
    fiches_existantes = charger_json(FICHES_FILE)

    candidates_restantes = []
    nouvelles_fiches = 0
    rejets = 0

    for candidate in candidates:
        statut = candidate.get('statut', 'A_VERIFIER')
        
        # Si la candidate est marquée pour vérification
        if statut == 'A_VERIFIER':
            est_valide, raison = valider_candidate(candidate)
            if est_valide:
                candidate['statut'] = 'VALIDE'
                fiches_existantes.append(candidate)
                nouvelles_fiches += 1
                print(f"✅ Fiche validée : {candidate.get('sujet')}")
            else:
                rejets += 1
                print(f"❌ Candidate rejetée [{candidate.get('sujet')}] : {raison}")
        else:
            candidates_restantes.append(candidate)

    if nouvelles_fiches > 0:
        sauvegarder_json(FICHES_FILE, fiches_existantes)

    sauvegarder_json(CANDIDATES_FILE, candidates_restantes)

    return nouvelles_fiches, rejets, len(candidates_restantes)

def main():
    print("🔍 Démarrage du moteur de vérification Nosey...\n")

    # 1. Purge des liens cassés sur les fiches déjà publiées (Parade #3)
    liens_retires = verifier_et_nettoyer_fiches_publiees()

    # 2. Validation et transfert des candidates
    nouvelles, rejets, en_attente = traiter_candidates()

    # 3. Rapport d'exécution synthétique pour Ntfy
    message_ntfy = (
        f"📊 Bilan Nosey :\n"
        f"• Nouvelles fiches publiées : {nouvelles}\n"
        f"• Candidates rejetées : {rejets}\n"
        f"• En attente dans la file : {en_attente}\n"
        f"• Liens cassés purges : {liens_retires}"
    )

    print(f"\n{message_ntfy}")
    envoyer_notification_ntfy("Nosey — Bilan de vérification", message_ntfy)

if __name__ == "__main__":
    main()