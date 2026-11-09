import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from scripts import actualiser_referentiels, generateur_candidates, moteur_verification


class RechercheCandidatesTests(unittest.TestCase):
    def test_quota_gemini_falls_back_without_repeating_call(self):
        client = mock.Mock()
        client.models.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED"
        )
        generateur_candidates.GEMINI_LIMITEE = False
        with (
            mock.patch.object(generateur_candidates, "client", client),
            mock.patch.object(
                generateur_candidates,
                "extraire_fait_depuis_wikipedia",
                return_value="Fait local vérifié.",
            ),
            mock.patch.object(generateur_candidates.time, "sleep"),
        ):
            fait = generateur_candidates.sommer_article_en_fait(
                "Sujet", "Extrait Wikipédia suffisamment long pour être résumé."
            )

        self.assertEqual(fait, "Fait local vérifié.")
        self.assertTrue(generateur_candidates.GEMINI_LIMITEE)
        client.models.generate_content.assert_called_once()
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["model"],
            "gemini-2.5-flash",
        )

    def test_precise_categories_are_searched_before_general_categories(self):
        categories = [
            {"categorie_wikipedia": "Animal"},
            {"categorie_wikipedia": "Animal_de_record"},
        ]
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "query": {
                "categorymembers": [{"title": "Exemple remarquable"}]
            }
        }).encode("utf-8")

        with (
            mock.patch.object(
                generateur_candidates.random,
                "sample",
                side_effect=lambda items, _: list(items),
            ),
            mock.patch.object(
                generateur_candidates.urllib.request,
                "urlopen",
                return_value=response,
            ) as urlopen,
        ):
            categorie, sujet = generateur_candidates.choisir_sujet_dynamique(
                categories, [], set()
            )

        self.assertEqual(categorie, categories[1])
        self.assertEqual(sujet, "Exemple remarquable")
        urlopen.assert_called_once()
        self.assertIn("Animal_de_record", urlopen.call_args.args[0].full_url)

    def test_wikipedia_quota_stops_category_search_immediately(self):
        erreur = urllib.error.HTTPError(
            "https://fr.wikipedia.org/w/api.php", 429, "limited", {}, None
        )
        with mock.patch.object(
            generateur_candidates.urllib.request, "urlopen", side_effect=erreur
        ) as urlopen:
            with self.assertRaises(generateur_candidates.LimitationReseau):
                generateur_candidates.choisir_sujet_dynamique(
                    [{"categorie_wikipedia": "Animal"}], [], set()
                )

        urlopen.assert_called_once()


class VerificationCandidatesTests(unittest.TestCase):
    def test_json_files_with_invalid_shape_are_treated_as_empty(self):
        with tempfile.TemporaryDirectory() as repertoire:
            chemin_candidates = os.path.join(repertoire, "candidates.json")
            chemin_fiches = os.path.join(repertoire, "fiches.json")
            chemin_blacklist = os.path.join(repertoire, "blacklist.json")

            with open(chemin_candidates, "w", encoding="utf-8") as fichier:
                json.dump({"sujet": "Pas une liste"}, fichier)
            with open(chemin_fiches, "w", encoding="utf-8") as fichier:
                json.dump(None, fichier)
            with open(chemin_blacklist, "w", encoding="utf-8") as fichier:
                json.dump("[]", fichier)

            self.assertEqual(moteur_verification.charger_json(chemin_candidates), [])
            self.assertEqual(moteur_verification.charger_json(chemin_fiches), [])
            self.assertEqual(moteur_verification.charger_json(chemin_blacklist), [])

    def test_rejected_candidate_is_kept_for_later_retry(self):
        with tempfile.TemporaryDirectory() as repertoire:
            chemin_candidates = os.path.join(repertoire, "candidates.json")
            chemin_fiches = os.path.join(repertoire, "fiches.json")
            chemin_blacklist = os.path.join(repertoire, "blacklist.json")
            candidate = {"id": "c1", "sujet": "À vérifier", "fait_texte": ""}

            for chemin, donnees in (
                (chemin_candidates, [candidate]),
                (chemin_fiches, []),
                (chemin_blacklist, []),
            ):
                with open(chemin, "w", encoding="utf-8") as fichier:
                    json.dump(donnees, fichier)

            with (
                mock.patch.object(
                    moteur_verification, "CANDIDATES_FILE", chemin_candidates
                ),
                mock.patch.object(
                    moteur_verification, "FICHES_FILE", chemin_fiches
                ),
                mock.patch.object(
                    moteur_verification, "BLACKLIST_FILE", chemin_blacklist
                ),
                mock.patch("builtins.print"),
            ):
                moteur_verification.main()

            with open(chemin_candidates, encoding="utf-8") as fichier:
                candidates_apres = json.load(fichier)

        self.assertEqual(candidates_apres, [candidate])


class ActualisationReferentielsTests(unittest.TestCase):
    def test_only_recognized_source_domains_are_added_once(self):
        sources = [
            {"nom": "UNESCO", "domaines": ["whc.unesco.org"]},
            {"nom": "Source existante", "domaines": ["example.org"]},
        ]

        updated, added = actualiser_referentiels.ajouter_sources_reconnues(sources)

        self.assertEqual(len(added), len(actualiser_referentiels.SOURCES_RECONNUES) - 1)
        self.assertEqual(
            len(actualiser_referentiels.ajouter_sources_reconnues(updated)[1]),
            0,
        )
        self.assertIn(
            {"nom": "Source existante", "domaines": ["example.org"]},
            updated,
        )

    def test_only_relevant_categories_from_reliably_sourced_pages_are_added(self):
        sources = [{"nom": "UNESCO", "domaines": ["whc.unesco.org"]}]
        fiches = [
            {
                "domaine": "HISTOIRE",
                "theme": "Découverte HISTOIRE",
                "sources": [{"url": "https://whc.unesco.org/en/list/323/"}],
                "categories_wikipedia": [
                    {"ns": 14, "title": "Catégorie:Monument_remarquable"},
                    {"ns": 14, "title": "Catégorie:Portail:Histoire/Articles liés"},
                    {"ns": 14, "title": "Catégorie:Ville au Bénin"},
                ],
            },
            {
                "domaine": "NATURE",
                "theme": "Découverte NATURE",
                "sources": [{"url": "https://untrusted.example/page"}],
                "categories_wikipedia": [
                    {"ns": 14, "title": "Catégorie:Espèce rare"},
                ],
            },
        ]

        updated, added = actualiser_referentiels.categories_issues_des_fiches(
            [], fiches, sources
        )

        self.assertEqual(
            updated,
            [{
                "categorie": "HISTOIRE",
                "domaine": "HISTOIRE",
                "categorie_wikipedia": "Monument_remarquable",
            }],
        )
        self.assertEqual(added, updated)

    def test_requested_fiches_have_complete_notable_summaries(self):
        with open("data/fiches.json", encoding="utf-8") as fichier:
            fiches = json.load(fichier)

        fiches_par_sujet = {fiche.get("sujet"): fiche for fiche in fiches}
        for sujet in ("Excavatrice à godets", "Abomey", "Guillaume Le Gentil"):
            with self.subTest(sujet=sujet):
                fiche = fiches_par_sujet[sujet]
                texte = fiche["fait_texte"]
                self.assertTrue(texte.endswith((".", "!", "?")))
                self.assertEqual(
                    moteur_verification.verifier_texte_complet(texte),
                    (True, "OK"),
                )
                self.assertTrue(
                    moteur_verification.verifier_valeur_ajoutee_et_contexte(fiche)[0]
                )


if __name__ == "__main__":
    unittest.main()
