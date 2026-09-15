import json
import os
import urllib.request

CANDIDATES_FILE = 'data/candidates.json'
FICHES_FILE = 'data/fiches.json'

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

def verifier_url(url):
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'}, method='HEAD')
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def verifier_impact_ingenerie(fiche):
    """Exige des notions de grandeur ou d'exploit si la fiche est classée en ingénierie."""
    if fiche.get('domaine') != 'INGÉNIERIE':
        return True

    mots_impact = [
        'record', 'plus grand', 'plus haut', 'plus long', 'premier',
        'tonne', 'mètre', 'km', 'milliards', 'prouesse', 'unique',
        'monumental', 'géant', 'exceptionnel'
    ]
    texte = fiche.get('fait_texte', '').lower()
    return any(mot in texte for mot in mots_impact)

def valider_fiche(fiche):
    texte = fiche.get('fait_texte', '').strip()
    if not texte:
        return False, "Texte vide"

    mots = texte.split()
    if len(mots) < 15:
        return False, f"Trop court ({len(mots)} mots, min 15)"

    if texte.endswith('...'):
        return False, "Texte tronqué"

    if not texte.endswith(('.', '!', '?')):
        return False, "Absence de ponctuation finale"

    if not verifier_impact_ingenerie(fiche):
        return False, "Ingénierie sans fait marquant ou grandeur"

    if not verifier_url(fiche.get('source_url')):
        return False, "Lien source inacessible"

    return True, "Valide"

def main():
    print("🔍 Vérification des candidates...")
    candidates = charger_json(CANDIDATES_FILE)
    fiches_validees = charger_json(FICHES_FILE)

    ids_existants = {f.get('id') for f in fiches_validees if f.get('id')}
    candidates_restantes = []
    nouveaux_ajouts = 0

    for candidate in candidates:
        cand_id = candidate.get('id')
        if cand_id in ids_existants:
            continue

        est_valide, raison = valider_fiche(candidate)
        if est_valide:
            print(f"✅ Validée : {candidate.get('sujet')}")
            fiches_validees.append(candidate)
            ids_existants.add(cand_id)
            nouveaux_ajouts += 1
        else:
            print(f"❌ Rejetée ({candidate.get('sujet')}) : {raison}")

    # Reset du fichier candidates après traitement
    sauvegarder_json(CANDIDATES_FILE, candidates_restantes)
    
    if nouveaux_ajouts > 0:
        sauvegarder_json(FICHES_FILE, fiches_validees)
        print(f"\n💾 {nouveaux_ajouts} fiche(s) ajoutée(s) à {FICHES_FILE}.")
    else:
        print("\nℹ️ Aucune nouvelle fiche validée.")

if __name__ == "__main__":
    main()