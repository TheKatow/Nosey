// Clé utilisée dans le stockage local du navigateur pour le suivi utilisateur
const STORAGE_KEY_VUS = 'nosey_fiches_vues';

let fichesInedites = [];
let ficheActuelleIndex = 0;

// -----------------------------------------------------------------------------
// 1. Gestion du Stockage Local (Suivi Utilisateur)
// -----------------------------------------------------------------------------

function obtenirFichesVues() {
  const vues = localStorage.getItem(STORAGE_KEY_VUS);
  return vues ? JSON.parse(vues) : [];
}

function marquerCommeVue(ficheId) {
  const vues = obtenirFichesVues();
  if (!vues.includes(ficheId)) {
    vues.push(ficheId);
    localStorage.setItem(STORAGE_KEY_VUS, JSON.stringify(vues));
  }
}

function filtrerFichesInedites(toutesLesFiches) {
  const vues = obtenirFichesVues();
  return toutesLesFiches.filter(fiche => !vues.includes(fiche.id));
}

// Optionnel : Réinitialiser l'historique si l'utilisateur souhaite tout revoir
function reinitialiserHistorique() {
  localStorage.removeItem(STORAGE_KEY_VUS);
  chargerFiches();
}

// -----------------------------------------------------------------------------
// 2. Chargement des données avec Anti-Cache (Parade #4)
// -----------------------------------------------------------------------------

async function chargerFiches() {
  try {
    // Timestamp dynamique pour contourner le cache navigateur
    const timestamp = new Date().getTime();
    const reponse = await fetch(`data/fiches.json?v=${timestamp}`);
    
    if (!reponse.ok) {
      throw new Error(`Erreur HTTP: ${reponse.status}`);
    }

    const toutesLesFiches = await reponse.json();
    
    // Filtrage pour ne garder que les fiches non lues par cet utilisateur
    fichesInedites = filtrerFichesInedites(toutesLesFiches);
    ficheActuelleIndex = 0;

    afficherFiche();
  } catch (erreur) {
    console.error("Erreur lors du chargement des fiches Nosey :", erreur);
    afficherErreur("Impossible de charger les curiosités du jour.");
  }
}

// -----------------------------------------------------------------------------
// 3. Affichage et Interactions
// -----------------------------------------------------------------------------

function afficherFiche() {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  // Si aucune fiche inédite n'est disponible
  if (fichesInedites.length === 0 || ficheActuelleIndex >= fichesInedites.length) {
    afficherEcranFin();
    return;
  }

  const fiche = fichesInedites[ficheActuelleIndex];

  // Injection du HTML de la carte avec émojis et badge domaine
  carteContainer.innerHTML = `
    <article class="carte" data-domaine="${fiche.domaine}">
      <header class="carte-header">
        <span class="badge-domaine">${fiche.domaine}</span>
        <span class="theme-label">${fiche.theme || ''}</span>
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
  // 1. Enregistrer la fiche comme vue dans le localStorage
  marquerCommeVue(ficheId);

  // 2. Passer à la fiche suivante dans la file
  ficheActuelleIndex++;
  afficherFiche();
}

function afficherEcranFin() {
  const carteContainer = document.getElementById('carte-container');
  if (!carteContainer) return;

  carteContainer.innerHTML = `
    <div class="ecran-fin">
      <div class="icon-fin">✨</div>
      <h2>Vous êtes à jour !</h2>
      <p>Vous avez consulté toutes les curiosités disponibles pour le moment.</p>
      <p class="sous-texte">De nouvelles fiches seront ajoutées lors de la prochaine mise à jour quotidienne.</p>
      <button class="btn-reset" onclick="reinitialiserHistorique()">
        Revoir les anciennes fiches
      </button>
    </div>
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