// Clés de stockage LocalStorage
const CLE_STOCKAGE_DATE = 'nosey_derniere_lecture_date';
const CLE_STOCKAGE_FICHE = 'nosey_fiche_du_jour';

document.addEventListener('DOMContentLoaded', () => {
  chargerFicheDuJour();
});

/**
 * Charge et affiche la fiche du jour
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

    // 2. Récupérer la fiche déjà tirée aujourd'hui ou en choisir une au hasard
    let ficheDuJour = null;
    const ficheSauvegardee = localStorage.getItem(CLE_STOCKAGE_FICHE);

    if (ficheSauvegardee) {
      ficheDuJour = JSON.parse(ficheSauvegardee);
    } else {
      // Tirage au sort aléatoire parmi l'ensemble des fiches
      const indexAleatoire = Math.floor(Math.random() * fiches.length);
      ficheDuJour = fiches[indexAleatoire];
      
      // Mémorisation de la fiche tirée pour la journée en cours
      localStorage.setItem(CLE_STOCKAGE_FICHE, JSON.stringify(ficheDuJour));
    }

    // 3. Affichage de la carte
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
          <button class="btn-emoji" onclick="reagir('${fiche.id}', 'passer')" title="Passer">
            ${fiche.emojis?.passer || '🌧️'}
          </button>
          <button class="btn-emoji" onclick="reagir('${fiche.id}', 'positif')" title="Intéressant">
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
    // Déclenchement de l'animation CSS de sortie
    carteElement.classList.add('carte-sortie');

    // Attente de la fin de l'animation (300 ms) avant le basculement d'écran
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
 * Enregistre la date de lecture du jour et nettoie le tirage temporaire
 */
function enregistrerLectureAujourdhui(ficheId) {
  const aujourdhui = new Date().toISOString().split('T')[0];
  localStorage.setItem(CLE_STOCKAGE_DATE, aujourdhui);
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