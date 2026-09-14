let fiches = [];
let ficheActuelle = null;

async function chargerFiches() {
  try {
    const timestamp = new Date().getTime();
    const reponse = await fetch(`data/fiches.json?v=${timestamp}`);
    if (!reponse.ok) throw new Error('Erreur de chargement');
    
    const fiches = await reponse.json();
    initialiserApp(fiches);
  } catch (erreur) {
    console.error("Impossible de charger les fiches Nosey :", erreur);
  }
}

function initialiserApp(fiches) {
  if (!fiches || fiches.length === 0) return;
  // Logique d'affichage des cartes...
}

document.addEventListener('DOMContentLoaded', chargerFiches);

function afficherFicheAleatoire() {
  if (!fiches || fiches.length === 0) return;

  // Filtrer les fiches masquées dans le stockage local
  const masquees = JSON.parse(localStorage.getItem('fiches_masquees') || '[]');
  const fichesDisponibles = fiches.filter(f => !masquees.includes(f.id));

  if (fichesDisponibles.length === 0) {
    document.getElementById('card-domaine').textContent = "FIN DE LA SÉLECTION";
    document.getElementById('card-sujet').textContent = "Vous avez tout découvert !";
    document.getElementById('card-texte').textContent = "Revenez bientôt pour de nouvelles connaissances rares.";
    document.getElementById('card-source').style.display = "none";
    document.getElementById('btn-positif').style.display = "none";
    document.getElementById('btn-passer').style.display = "none";
    return;
  }

  const index = Math.floor(Math.random() * fichesDisponibles.length);
  ficheActuelle = fichesDisponibles[index];

  document.getElementById('card-domaine').textContent = ficheActuelle.domaine;
  document.getElementById('card-sujet').textContent = ficheActuelle.sujet;
  document.getElementById('card-texte').textContent = ficheActuelle.fait_texte;
  
  const sourceEl = document.getElementById('card-source');
  sourceEl.textContent = `Source : ${ficheActuelle.source_nom}`;
  sourceEl.href = ficheActuelle.source_url;
  sourceEl.style.display = "inline";

  const btnPositif = document.getElementById('btn-positif');
  const btnPasser = document.getElementById('btn-passer');

  btnPositif.textContent = ficheActuelle.emojis.positif;
  btnPasser.textContent = ficheActuelle.emojis.passer;

  btnPositif.onclick = () => enregistrerAction('LIKE');
  btnPasser.onclick = () => enregistrerAction('HIDE');
}

function enregistrerAction(action) {
  if (!ficheActuelle) return;

  if (action === 'HIDE') {
    const masquees = JSON.parse(localStorage.getItem('fiches_masquees') || '[]');
    masquees.push(ficheActuelle.id);
    localStorage.setItem('fiches_masquees', JSON.stringify(masquees));
  }

  // Passer à l'information suivante
  afficherFicheAleatoire();
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', chargerFiches);