// Clés de stockage LocalStorage
const CLE_STOCKAGE_DATE = 'nosey_derniere_lecture_date';
const CLE_STOCKAGE_FICHE = 'nosey_fiche_du_jour';
const CLE_HISTORIQUE_VUS = 'nosey_fiches_vues_ids';

document.addEventListener('DOMContentLoaded', () => {
  chargerFicheDuJour();
});

/**
 * Mélange un tableau de manière équitable (Algorithme Fisher-Yates)
 */
function melangerTableau(tableau) {
  const arr = [...tableau];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/**
 * Charge et affiche la fiche du jour sans répétition
 */
async function chargerFicheDuJour() {
  const aujourdhui = new Date().toISOString().split('T')[0];
  const derniereLecture = localStorage.getItem(CLE_STOCKAGE_DATE);

  // 1. Si l'utilisateur a déjà lu sa fiche aujourd'hui -> Écran "À demain"
  if (derniereLecture === aujourdhui) {
    afficherEcranDejaLu();
    return;
  }

  try {
    const reponse = await fetch('data/fiches.json');
    const fiches = await reponse.json();

    if (!fiches || fiches.length === 0) {
      afficherErreur("Aucune curiosité disponible pour le moment.");
      return;
    }

    // 2. Récupérer la fiche verrouillée pour la journée en cours
    let ficheDuJour = null;
    const ficheSauvegardee = localStorage.getItem(CLE_STOCKAGE_FICHE);

    if (ficheSauvegardee) {
      ficheDuJour = JSON.parse(ficheSauvegardee);
    } else {
      // 3. Récupérer l'historique des cartes déjà vues
      let vuesIds = JSON.parse(localStorage.getItem(CLE_HISTORIQUE_VUS) || '[]');

      // Filtrer pour ne garder que les fiches non encore vues
      let nonVues = fiches.filter(f => !vuesIds.includes(f.id || f.sujet));

      // Si toutes les fiches ont été vues, réinitialiser le cycle
      if (nonVues.length === 0) {
        vuesIds = [];
        localStorage.setItem(CLE_HISTORIQUE_VUS, JSON.stringify(vuesIds));
        nonVues = fiches;
      }

      // 4. Mélanger les fiches disponibles et sélectionner la première
      const fichesMelangees = melangerTableau(nonVues);
      ficheDuJour = fichesMelangees[0];

      // Mémoriser le tirage pour la journée
      localStorage.setItem(CLE_STOCKAGE_FICHE, JSON.stringify(ficheDuJour));
    }

    // 5. Affichage de la carte
    afficherFiche(ficheDuJour);

  } catch (erreur) {
    console.error("Erreur lors du chargement des fiches :", erreur);
    afficherErreur("Impossible de charger la curiosité du jour.");
  }
}

/**
 * Génère le rendu HTML de la carte
 */
function afficherFiche(fiche) {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  const imageBackground = fiche.image_url 
    ? `style="background-image: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.85)), url('${fiche.image_url}'); color: white;"` 
    : '';

  carteContainer.innerHTML = `
    <article class="carte ${fiche.image_url ? 'avec-image' : ''}" data-domaine="${fiche.domaine || ''}" ${imageBackground}>
      <header class="carte-header">
        <span class="badge-domaine">${fiche.domaine || 'CURIOSITÉ'}</span>
        <span class="theme-label">${fiche.theme || ''}</span>
      </header>

      <div class="carte-corps">
        <h2 class="titre-sujet">${fiche.sujet || ''}</h2>
        <p class="texte-fait">${fiche.fait_texte || ''}</p>
      </div>

      <footer class="carte-footer">
        <a href="${fiche.source_url || '#'}" target="_blank" rel="noopener noreferrer" class="lien-source">
          Source : ${fiche.source_nom || 'Wikipédia'} ↗
        </a>

        <div class="actions-emojis">
          <button class="btn-emoji" onclick="reagir('${fiche.id || fiche.sujet}', 'passer')" title="Passer">
            ${fiche.emojis?.passer || '🌧️'}
          </button>
          <button class="btn-emoji" onclick="reagir('${fiche.id || fiche.sujet}', 'positif')" title="Intéressant">
            ${fiche.emojis?.positif || '☀️'}
          </button>
        </div>
      </footer>
    </article>
  `;
}

/**
 * Gère la réaction utilisateur, déclenche l'animation de sortie et enregistre la lecture
 */
function reagir(ficheId, typeReaction) {
  const carteElement = document.querySelector('.carte');

  if (carteElement) {
    carteElement.classList.add('carte-sortie');

    setTimeout(() => {
      enregistrerLectureAujourdhui(ficheId);
      afficherEcranDejaLu();
    }, 300);
  } else {
    enregistrerLectureAujourdhui(ficheId);
    afficherEcranDejaLu();
  }
}

/**
 * Enregistre la lecture, ajoute la fiche à l'historique et réinitialise la fiche temporaire
 */
function enregistrerLectureAujourdhui(ficheId) {
  const aujourdhui = new Date().toISOString().split('T')[0];
  
  // Enregistrer la date de lecture
  localStorage.setItem(CLE_STOCKAGE_DATE, aujourdhui);

  // Ajouter la fiche à l'historique des fiches vues
  const ficheCourante = JSON.parse(localStorage.getItem(CLE_STOCKAGE_FICHE) || '{}');
  const idAAjouter = ficheId || ficheCourante.id || ficheCourante.sujet;

  if (idAAjouter) {
    const vuesIds = JSON.parse(localStorage.getItem(CLE_HISTORIQUE_VUS) || '[]');
    if (!vuesIds.includes(idAAjouter)) {
      vuesIds.push(idAAjouter);
      localStorage.setItem(CLE_HISTORIQUE_VUS, JSON.stringify(vuesIds));
    }
  }

  // Nettoyage du tirage temporaire
  localStorage.removeItem(CLE_STOCKAGE_FICHE);
}

/**
 * Affiche l'écran de fin « À demain »
 */
function afficherEcranDejaLu() {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <div class="ecran-fin">
      <div class="icon-fin">🧐</div>
      <h2>C'est tout pour aujourd'hui !</h2>
      <p>Reviens demain pour découvrir une nouvelle curiosité.</p>
      <p class="sous-texte">Nosey — Un fait vérifié par jour.</p>
    </div>
  `;
}

/**
 * Affiche un message d'erreur
 */
function afficherErreur(message) {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <div class="ecran-erreur">
      <p>⚠️ ${message}</p>
    </div>
  `;
}

// Enregistrement du Service Worker PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then((reg) => console.log('Service Worker enregistré :', reg.scope))
      .catch((err) => console.error('Échec enregistrement Service Worker :', err));
  });
}