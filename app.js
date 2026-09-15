// Clé de stockage LocalStorage
const CLE_HISTORIQUE_VUS = 'nosey_fiches_vues_ids';
const CLE_BLACKLIST_SUJETS = 'nosey_blacklist_sujets';
let fichesDisponibles = [];
let ficheActuelle = null;

document.addEventListener('DOMContentLoaded', () => {
  chargerFicheDuJour();
});

window.addEventListener('storage', evenement => {
  if (evenement.key === CLE_BLACKLIST_SUJETS) {
    appliquerBlacklistLocale();
  }
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
 * Charge et affiche une fiche sans répétition jusqu'à épuisement du cycle
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

    afficherFiche(choisirProchaineFiche());

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
  const ficheSupprimee = ficheActuelle && sujetsBlacklistes.has(normaliserSujet(ficheActuelle.sujet));
  fichesDisponibles = fichesDisponibles.filter(fiche => !sujetsBlacklistes.has(normaliserSujet(fiche.sujet)));

  if (!ficheSupprimee) return;

  if (fichesDisponibles.length === 0) {
    ficheActuelle = null;
    afficherErreur("Aucune curiosité disponible pour le moment.");
    return;
  }

  afficherFiche(choisirProchaineFiche());
}

function obtenirVues() {
  try {
    return JSON.parse(localStorage.getItem(CLE_HISTORIQUE_VUS) || '[]');
  } catch (erreur) {
    return [];
  }
}

function identifiantFiche(fiche) {
  return String(fiche.id || fiche.sujet);
}

function choisirProchaineFiche() {
  let vuesIds = obtenirVues();
  let nonVues = fichesDisponibles.filter(fiche => !vuesIds.includes(identifiantFiche(fiche)));

  if (nonVues.length === 0) {
    vuesIds = [];
    localStorage.setItem(CLE_HISTORIQUE_VUS, JSON.stringify(vuesIds));
    nonVues = fichesDisponibles;
  }

  const fiche = melangerTableau(nonVues)[0];
  ficheActuelle = fiche;
  enregistrerFicheVue(fiche);
  return fiche;
}

function enregistrerFicheVue(fiche) {
  const vuesIds = obtenirVues();
  const id = identifiantFiche(fiche);

  if (!vuesIds.includes(id)) {
    vuesIds.push(id);
    localStorage.setItem(CLE_HISTORIQUE_VUS, JSON.stringify(vuesIds));
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
    <div class="navigation-fiche">
      <button class="fleche-navigation fleche-gauche" onclick="afficherFicheSuivante()" aria-label="Afficher une autre curiosité" title="Autre curiosité">←</button>
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
      <button class="fleche-navigation fleche-droite" onclick="afficherFicheSuivante()" aria-label="Afficher la curiosité suivante" title="Curiosité suivante">→</button>
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
  if (!ficheActuelle || fichesDisponibles.length === 0) return;

  const carteElement = document.querySelector('.carte');
  if (carteElement) {
    carteElement.classList.add('carte-sortie');
  }

  setTimeout(() => afficherFiche(choisirProchaineFiche()), 250);
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