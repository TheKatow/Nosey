import json
import urllib.request
import os
from datetime import datetime

NTFY_CHANNEL = "Nosey"
MOTS_INTERDITS = ["magique", "incroyable", "miraculeux", "jamais vu", "unique au monde"]

def envoyer_notification(message):
    """Envoie une notification push instantanée via Ntfy."""
    if not message.strip():
        return
    url = f"https://ntfy.sh/{NTFY_CHANNEL}"
    try:
        req = urllib.request.Request(
            url, 
            data=message.encode('utf-8'),
            headers={"Title": "Culture Rare - Validation"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print("🔔 Notification envoyée !")
    except Exception as e:
        print(f"⚠️ Échec notification : {e}")

def verifier_url(url):
    """Vérifie l'accessibilité HTTP de la source."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def verifier_texte(texte):
    """Vérifie la longueur (~50 mots) et l'absence de mots interdits."""
    mots = texte.split()
    nb_mots = len(mots)
    if not (30 <= nb_mots <= 70):
        return False, f"Longueur incorrecte ({nb_mots} mots)"
    for mot in MOTS_INTERDITS:
        if mot in texte.lower():
            return False, f"Mot interdit '{mot}' présent"
    return True, "OK"

def traiter_validation():
    """Traite les candidates : déplace les VALIDE_100 vers fiches.json et alerte sur le reste."""
    fiches_file = 'data/fiches.json'
    candidates_file = 'data/candidates.json'

    if not os.path.exists(candidates_file):
        return

    with open(candidates_file, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    if not os.path.exists(fiches_file):
        fiches = []
    else:
        with open(fiches_file, 'r', encoding='utf-8') as f:
            fiches = json.load(f)

    nouvelles_validees = []
    erreurs = []
    candidates_restantes = []

    for fiche in candidates:
        sujet = fiche.get('sujet', 'Inconnu')

        # Si tu as validé la fiche
        if fiche.get('statut') == 'VALIDE_100':
            # Tests de garde-fou automatisés
            if not verifier_url(fiche.get('source_url', '')):
                erreurs.append(f"Source URL HS pour '{sujet}'")
                candidates_restantes.append(fiche)
                continue

            conforme, raison = verifier_texte(fiche.get('fait_texte', ''))
            if not conforme:
                erreurs.append(f"Texte non conforme pour '{sujet}' ({raison})")
                candidates_restantes.append(fiche)
                continue

            # Ingestion définitive
            fiche['date_validation'] = datetime.now().strftime('%Y-%m-%d')
            fiches.append(fiche)
            nouvelles_validees.append(sujet)
        else:
            candidates_restantes.append(fiche)

    # Écriture des bases mise à jour
    if nouvelles_validees:
        with open(fiches_file, 'w', encoding='utf-8') as f:
            json.dump(fiches, f, ensure_ascii=False, indent=2)

    with open(candidates_file, 'w', encoding='utf-8') as f:
        json.dump(candidates_restantes, f, ensure_ascii=False, indent=2)

    # Récapitulatif unique envoyé sur ton téléphone
    generer_et_envoyer_rapport(nouvelles_validees, erreurs, len(candidates_restantes))

def generer_et_envoyer_rapport(validees, erreurs, nb_en_attente):
    if not validees and not erreurs and nb_en_attente == 0:
        return

    rapport = []
    if erreurs:
        rapport.append(f"🚨 {len(erreurs)} erreur(s) détectée(s) :")
        for err in erreurs:
            rapport.append(f"- {err}")

    if validees:
        if rapport:
            rapport.append("")
        rapport.append(f"✅ {len(validees)} fiche(s) intégrée(s) définitivement :")
        for sujet in validees:
            rapport.append(f"- {sujet}")

    if nb_en_attente > 0:
        if rapport:
            rapport.append("")
        rapport.append(f"⏳ {nb_en_attente} fiche(s) en attente de ta relecture dans candidates.json.")

    envoyer_notification("\n".join(rapport))

if __name__ == "__main__":
    traiter_validation()