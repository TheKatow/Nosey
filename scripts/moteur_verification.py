import json
import os
import re
import urllib.request

CANDIDATES_FILE = 'data/candidates.json'
BLACKLIST_FILE = 'data/blacklist.json'
FICHES_FILE = 'data/fiches.json'

MOTS_VALEUR_EXPLICITE = [
    'record', 'plus grand', 'plus haut', 'plus long', 'plus profond',
    'premier', 'unique', 'monumental', 'exceptionnel', 'seul',
    'prouesse', 'exploit', 'particulier', 'pionnier'
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

def normaliser_sujet(sujet):
    return str(sujet or '').strip().lower()

def nettoyer_blacklist(candidates, fiches):
    """Retire les sujets blacklistés des fiches publiées et des candidates."""
    blacklist = charger_json(BLACKLIST_FILE)
    sujets_blacklistes = {
        normaliser_sujet(sujet)
        for sujet in blacklist
        if isinstance(sujet, str) and normaliser_sujet(sujet)
    }

    if not sujets_blacklistes:
        return candidates, fiches, 0, 0

    candidates_filtrees = [
        candidate for candidate in candidates
        if normaliser_sujet(candidate.get('sujet')) not in sujets_blacklistes
    ]
    fiches_filtrees = [
        fiche for fiche in fiches
        if normaliser_sujet(fiche.get('sujet')) not in sujets_blacklistes
    ]

    return (
        candidates_filtrees,
        fiches_filtrees,
        len(candidates) - len(candidates_filtrees),
        len(fiches) - len(fiches_filtrees)
    )

def verifier_url(url):
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NoseyBot/1.0'}, method='HEAD')
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def verifier_valeur_ajoutee_et_contexte(fiche):
    """Refuse les fiches chiffrées (ex: 12 km) dépourvues de superlatifs ou de contexte remarquable."""
    texte = fiche.get('fait_texte', '').lower()
    
    # Exigence spécifique pour l'ingénierie
    if fiche.get('domaine') == 'INGÉNIERIE':
        mots_impact = MOTS_VALEUR_EXPLICITE + ['tonne', 'mètre', 'km', 'milliards', 'géant']
        if not any(mot in texte for mot in mots_impact):
            return False, "Ingénierie sans chiffre ni fait marquant"

    # Vérification anti-banalité globale : présence d'une donnée chiffrée
    contient_mesure = bool(re.search(r'\d+\s*(km|m|mètres|kilomètres|ans|siècles|tonnes|kilos)', texte))
    contient_qualification = any(mot in texte for mot in MOTS_VALEUR_EXPLICITE)

    if contient_mesure and not contient_qualification:
        return False, "Donnée chiffrée présente mais contexte/record non précisé"

    return True, "OK"

def verifier_valeur_ajoutee_et_contexte(fiche):
    texte = fiche.get('fait_texte', '').strip()
    texte_lower = texte.lower()

    # 1. Rejet des tournures méta/abstrait sans faits
    mots_cles_meta = [
        "peuvent être déterminés", "en fonction de divers critères", "se réfère à",
        "désigne l'ensemble", "est une notion", "est un terme", "peut désigner"
    ]
    if any(m in texte_lower for m in mots_cles_meta):
        return False, "Phrase d'introduction abstraite sans fait concret"

    # 2. Exigence d'au moins un nom propre/exemple précis OU d'un chiffre
    mots = texte.split()
    # On cherche s'il y a des mots capitalisés au milieu de la phrase (exemples d'espèces, lieux, noms)
    a_nom_propre_ou_exemple = any(m[0].isupper() for m in mots[1:] if m.isalpha())
    a_chiffre = bool(re.search(r'\d+', texte))

    if not (a_nom_propre_ou_exemple or a_chiffre):
        return False, "Absence d'exemple précis, de nom propre ou de chiffre"

    # 3. Exigence spécifique pour l'ingénierie
    if fiche.get('domaine') == 'INGÉNIERIE':
        mots_impact = MOTS_VALEUR_EXPLICITE + ['tonne', 'mètre', 'km', 'milliards', 'géant']
        if not any(mot in texte_lower for mot in mots_impact):
            return False, "Ingénierie sans chiffre ni fait marquant"

    # 4. Vérification anti-banalité : mesure sans qualificatif
    contient_mesure = bool(re.search(r'\d+\s*(km|m|mètres|kilomètres|ans|siècles|tonnes|kilos)', texte_lower))
    contient_qualification = any(mot in texte_lower for mot in MOTS_VALEUR_EXPLICITE)

    if contient_mesure and not contient_qualification:
        return False, "Donnée chiffrée présente mais contexte/record non précisé"

    return True, "OK"

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

    sources = fiche.get('sources', [])
    urls_sources = {
        source.get('url') for source in sources
        if isinstance(source, dict) and source.get('url')
    }
    if len(urls_sources) < 2:
        return False, "Moins de deux sources distinctes"

    sources_secondaires = [
        source for source in sources
        if isinstance(source, dict)
        and source.get('url')
        and source.get('url') != fiche.get('source_url')
    ]
    if not sources_secondaires:
        return False, "Aucune seconde source fiable détectée"

    valide_contexte, raison_contexte = verifier_valeur_ajoutee_et_contexte(fiche)
    if not valide_contexte:
        return False, raison_contexte

    if not verifier_url(fiche.get('source_url')):
        return False, "Lien source inaccessible"

    return True, "Valide"

def main():
    print("🔍 Vérification des candidates...")
    candidates = charger_json(CANDIDATES_FILE)
    fiches_validees = charger_json(FICHES_FILE)

    candidates, fiches_validees, candidates_retirees, fiches_retirees = nettoyer_blacklist(
        candidates,
        fiches_validees
    )
    if candidates_retirees or fiches_retirees:
        print(
            f"🚫 Blacklist : {fiches_retirees} fiche(s) et "
            f"{candidates_retirees} candidate(s) retirée(s)."
        )

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

    # Nettoyage de la liste candidates après traitement
    sauvegarder_json(CANDIDATES_FILE, candidates_restantes)
    
    if nouveaux_ajouts > 0 or fiches_retirees > 0:
        sauvegarder_json(FICHES_FILE, fiches_validees)
        if nouveaux_ajouts > 0:
            print(f"\n💾 {nouveaux_ajouts} fiche(s) ajoutée(s) à {FICHES_FILE}.")
        elif fiches_retirees > 0:
            print(f"\n💾 {fiches_retirees} fiche(s) blacklistée(s) retirée(s) de {FICHES_FILE}.")
    else:
        print("\nℹ️ Aucune nouvelle fiche validée.")

if __name__ == "__main__":
    main()