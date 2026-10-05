const CLE_BLACKLIST_SUJETS = 'nosey_blacklist_sujets';
let fichesDisponibles = [];
let ficheActuelle = null;
let indexFicheActuelle = -1;

document.addEventListener('DOMContentLoaded', () => {
  chargerFicheDuJour();
});

document.addEventListener('keydown', evenement => {
  if (
    !(evenement.target instanceof Element)
    || evenement.target.closest('button, a, input, textarea, select, [contenteditable="true"]')
  ) {
    return;
  }

  if (evenement.key === 'ArrowLeft') {
    evenement.preventDefault();
    afficherFichePrecedente();
  } else if (evenement.key === 'ArrowRight') {
    evenement.preventDefault();
    afficherFicheSuivante();
  }
});

window.addEventListener('storage', evenement => {
  if (evenement.key === CLE_BLACKLIST_SUJETS) {
    appliquerBlacklistLocale();
  }
});

/**
 * Charge les fiches dans l'ordre du fichier et affiche la première disponible.
 */
async function chargerFicheDuJour() {
  try {
    const reponse = await fetch('data/fiches.json');
    fichesDisponibles = await reponse.json();
    let blacklist = [];
    try {
      const reponseBlacklist = await fetch('data/blacklist.json');
      blacklist = await reponseBlacklist.json();
    } catch (erreur) {
      console.warn("Impossible de charger la blacklist distante, utilisation de la blacklist locale.");
    }
    const blacklistLocale = obtenirBlacklistLocale();
    const sujetsBlacklistes = new Set([
      ...blacklist,
      ...blacklistLocale
    ].map(normaliserSujet));
    fichesDisponibles = fichesDisponibles.filter(fiche => !sujetsBlacklistes.has(normaliserSujet(fiche.sujet)));

    if (!fichesDisponibles || fichesDisponibles.length === 0) {
      afficherErreur("Aucune curiosité disponible pour le moment.");
      return;
    }

    indexFicheActuelle = 0;
    ficheActuelle = fichesDisponibles[indexFicheActuelle];
    afficherFiche(ficheActuelle);

  } catch (erreur) {
    console.error("Erreur lors du chargement des fiches :", erreur);
    afficherErreur("Impossible de charger les curiosités.");
  }
}

function normaliserSujet(sujet) {
  return String(sujet || '').trim().toLowerCase();
}

function obtenirBlacklistLocale() {
  try {
    const blacklist = JSON.parse(localStorage.getItem(CLE_BLACKLIST_SUJETS) || '[]');
    return Array.isArray(blacklist) ? blacklist : [];
  } catch (erreur) {
    return [];
  }
}

function appliquerBlacklistLocale() {
  const sujetsBlacklistes = new Set(obtenirBlacklistLocale().map(normaliserSujet));
  const indexPrecedent = indexFicheActuelle;
  const ficheActuelleEstBlacklistee = ficheActuelle
    && sujetsBlacklistes.has(normaliserSujet(ficheActuelle.sujet));
  fichesDisponibles = fichesDisponibles.filter(fiche => !sujetsBlacklistes.has(normaliserSujet(fiche.sujet)));

  if (fichesDisponibles.length === 0) {
    ficheActuelle = null;
    indexFicheActuelle = -1;
    afficherErreur("Aucune curiosité disponible pour le moment.");
    return;
  }

  const indexFicheToujoursDisponible = fichesDisponibles.findIndex(
    fiche => fiche.id === ficheActuelle?.id && fiche.sujet === ficheActuelle?.sujet
  );
  indexFicheActuelle = ficheActuelleEstBlacklistee
    ? Math.min(Math.max(indexPrecedent, 0), fichesDisponibles.length - 1)
    : Math.max(indexFicheToujoursDisponible, 0);
  ficheActuelle = fichesDisponibles[indexFicheActuelle];
  afficherFiche(ficheActuelle);
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
    <div class="navigation-fiche">
      <button class="fleche-navigation" onclick="afficherFichePrecedente()" aria-label="Revenir à la fiche précédente" title="Fiche précédente" ${indexFicheActuelle <= 0 ? 'disabled' : ''}>&lt;</button>
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
      <button class="fleche-navigation" onclick="afficherFicheSuivante()" aria-label="Afficher la fiche suivante" title="Fiche suivante" ${indexFicheActuelle >= fichesDisponibles.length - 1 ? 'disabled' : ''}>&gt;</button>
    </div>
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
      afficherFicheSuivante();
    }, 300);
  } else {
    afficherFicheSuivante();
  }
}

function afficherFicheSuivante() {
  if (indexFicheActuelle >= fichesDisponibles.length - 1) return;
  indexFicheActuelle += 1;
  ficheActuelle = fichesDisponibles[indexFicheActuelle];
  afficherFiche(ficheActuelle);
}

function afficherFichePrecedente() {
  if (indexFicheActuelle <= 0) return;
  indexFicheActuelle -= 1;
  ficheActuelle = fichesDisponibles[indexFicheActuelle];
  afficherFiche(ficheActuelle);
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