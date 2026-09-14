// Clés utilisées dans le stockage local du navigateur
const STORAGE_KEY_VUS = 'nosey_fiches_vues';
const STORAGE_KEY_DERNIERE_DATE = 'nosey_derniere_date_lecture';

let fichesInedites = [];
let ficheDuJour = null;

// -----------------------------------------------------------------------------
// 1. Utilitaires Date & Stockage Local
// -----------------------------------------------------------------------------

function obtenirDateAujourdhui() {
  const aujourdhui = new Date();
  const annee = aujourdhui.getFullYear();
  const mois = String(aujourdhui.getMonth() + 1).padStart(2, '0');
  const jour = String(aujourdhui.getDate()).padStart(2, '0');
  return `${annee}-${mois}-${jour}`;
}

function aDejaLuAujourdhui() {
  const derniereDate = localStorage.getItem(STORAGE_KEY_DERNIERE_DATE);
  return derniereDate === obtenirDateAujourdhui();
}

function enregistrerLectureAujourdhui(ficheId) {
  // 1. Enregistrer la date du jour
  localStorage.setItem(STORAGE_KEY_DERNIERE_DATE, obtenirDateAujourdhui());

  // 2. Ajouter l'ID aux fiches vues pour ne plus la recharger ultérieurement
  const vues = obtenirFichesVues();
  if (!vues.includes(ficheId)) {
    vues.push(ficheId);
    localStorage.setItem(STORAGE_KEY_VUS, JSON.stringify(vues));
  }
}

function obtenirFichesVues() {
  const vues = localStorage.getItem(STORAGE_KEY_VUS);
  return vues ? JSON.parse(vues) : [];
}

function filtrerFichesInedites(toutesLesFiches) {
  const vues = obtenirFichesVues();
  return toutesLesFiches.filter(fiche => !vues.includes(fiche.id));
}

// Optionnel : Réinitialiser pour les tests
function reinitialiserHistorique() {
  localStorage.removeItem(STORAGE_KEY_VUS);
  localStorage.removeItem(STORAGE_KEY_DERNIERE_DATE);
  chargerFiches();
}

// -----------------------------------------------------------------------------
// 2. Chargement des données
// -----------------------------------------------------------------------------

async function chargerFiches() {
  try {
    const timestamp = new Date().getTime();
    const reponse = await fetch(`data/fiches.json?v=${timestamp}`);
    
    if (!reponse.ok) {
      throw new Error(`Erreur HTTP: ${reponse.status}`);
    }

    const toutesLesFiches = await reponse.json();
    fichesInedites = filtrerFichesInedites(toutesLesFiches);

    // Si une fiche a déjà été lue aujourd'hui, on bloque l'affichage
    if (aDejaLuAujourdhui()) {
      afficherEcranDejaLu();
      return;
    }

    // Sinon, on sélectionne la première fiche inédite disponible
    if (fichesInedites.length > 0) {
      ficheDuJour = fichesInedites[0];
      afficherFiche(ficheDuJour);
    } else {
      afficherEcranFinSujets();
    }
  } catch (erreur) {
    console.error("Erreur lors du chargement de la fiche Nosey :", erreur);
    afficherErreur("Impossible de charger la curiosité du jour.");
  }
}

// -----------------------------------------------------------------------------
// 3. Affichage & Actions
// -----------------------------------------------------------------------------

function afficherFiche(fiche) {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <article class="carte" data-domaine="${fiche.domaine}">
      <header class="carte-header">
        <span class="badge-domaine">${fiche.domaine}</span>
      </header>

      <div class="carte-corps">
        <h2 class="titre-sujet">${fiche.sujet}</h2>
        <p class="texte-fait">${fiche.fait_texte}</p>
      </div>

      <footer class="carte-footer">
        <a href="${fiche.source_url}" target="_blank" rel="noopener noreferrer" class="lien-source">
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

function reagir(ficheId, typeReaction) {
  const carteElement = document.querySelector('.carte');

  if (carteElement) {
    // 1. Ajouter la classe d'animation de sortie
    carteElement.classList.add('carte-sortie');

    // 2. Attendre la fin de l'animation CSS (300 ms) avant de verrouiller la lecture
    setTimeout(() => {
      enregistrerLectureAujourdhui(ficheId);
      afficherEcranDejaLu();
    }, 300);
  } else {
    enregistrerLectureAujourdhui(ficheId);
    afficherEcranDejaLu();
  }
}

function afficherEcranDejaLu() {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <div class="ecran-fin">
      <div class="icon-fin">☀️</div>
      <h2>À demain pour un nouveau fait !</h2>
      <p>Vous avez déjà découvert votre curiosité du jour.</p>
      <p class="sous-texte">Revenez demain pour une nouvelle anecdote vérifiée.</p>
    </div>
  `;
}

function afficherEcranFinSujets() {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  const imageBackground = fiche.image_url 
    ? `style="background-image: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.8)), url('${fiche.image_url}'); color: white;"` 
    : '';

  carteContainer.innerHTML = `
    <article class="carte ${fiche.image_url ? 'avec-image' : ''}" data-domaine="${fiche.domaine}" ${imageBackground}>
      <header class="carte-header">
        <span class="badge-domaine">${fiche.domaine}</span>
      </header>

      <div class="carte-corps">
        <h2 class="titre-sujet">${fiche.sujet}</h2>
        <p class="texte-fait">${fiche.fait_texte}</p>
      </div>

      <footer class="carte-footer">
        <a href="${fiche.source_url}" target="_blank" rel="noopener noreferrer" class="lien-source">
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

function afficherErreur(message) {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <div class="ecran-erreur">
      <p>⚠️ ${message}</p>
    </div>
  `;
}

// Initialisation au chargement du DOM
document.addEventListener('DOMContentLoaded', chargerFiches);

// Enregistrement du Service Worker pour la PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then((reg) => console.log('Service Worker enregistré avec succès :', reg.scope))
      .catch((err) => console.error('Échec de l\'enregistrement du Service Worker :', err));
  });
}