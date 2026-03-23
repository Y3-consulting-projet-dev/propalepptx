<script setup>
import { ref, onMounted } from 'vue'
import { getProposals, generateProposal, logout } from '../api.js'

const proposals = ref([])
const loading = ref(false)
const showForm = ref(false)
const title = ref('')
const content = ref('')
const generating = ref(false)

const fetchProposals = async () => {
  try {
    loading.value = true
    const data = await getProposals()
    proposals.value = data.proposals
  } catch (err) {
    alert('Erreur lors du chargement des propositions: ' + err.message)
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (!title.value || !content.value) {
    alert('Veuillez remplir le titre et le contenu')
    return
  }

  try {
    generating.value = true
    const result = await generateProposal(title.value, content.value)

    // Reset form
    title.value = ''
    content.value = ''
    showForm.value = false

    // Refresh proposals
    await fetchProposals()

    alert('Proposition générée avec succès!')
  } catch (err) {
    alert('Erreur lors de la génération: ' + err.message)
  } finally {
    generating.value = false
  }
}

const handleDownload = (pptxUrl) => {
  window.open(pptxUrl, '_blank')
}

const handleLogout = () => {
  logout()
  window.location.reload()
}

onMounted(() => {
  fetchProposals()
})
</script>

<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>Outil Générateur de Présentations</h1>
      <button @click="handleLogout" class="logout-btn">Déconnexion</button>
    </header>

    <main class="dashboard-content">
      <div class="actions">
        <button @click="showForm = !showForm" class="primary-btn">
          {{ showForm ? 'Annuler' : '+ Nouvelle Proposition' }}
        </button>
      </div>

      <!-- Form to create new proposal -->
      <div v-if="showForm" class="proposal-form">
        <h3>Créer une Nouvelle Proposition</h3>
        <form @submit.prevent="handleGenerate">
          <div class="form-group">
            <label for="title">Titre de la Proposition</label>
            <input
              id="title"
              v-model="title"
              type="text"
              placeholder="Entrez le titre..."
              required
            >
          </div>
          <div class="form-group">
            <label for="content">Contenu</label>
            <textarea
              id="content"
              v-model="content"
              rows="6"
              placeholder="Entrez le contenu de votre proposition..."
              required
            ></textarea>
          </div>
          <button type="submit" :disabled="generating" class="primary-btn">
            {{ generating ? 'Génération...' : 'Générer PPTX' }}
          </button>
        </form>
      </div>

      <!-- Proposals list -->
      <div class="proposals-section">
        <h3>Mes Propositions</h3>

        <div v-if="loading" class="loading">
          Chargement...
        </div>

        <div v-else-if="proposals.length === 0" class="empty-state">
          <p>Aucune proposition trouvée. Créez votre première proposition !</p>
        </div>

        <div v-else class="proposals-list">
          <div
            v-for="proposal in proposals"
            :key="proposal._id"
            class="proposal-card"
          >
            <div class="proposal-header">
              <h4>{{ proposal.title }}</h4>
              <span class="date">{{ new Date(proposal.created_at).toLocaleDateString('fr-FR') }}</span>
            </div>
            <div class="proposal-content">
              <p>{{ proposal.content.substring(0, 150) }}{{ proposal.content.length > 150 ? '...' : '' }}</p>
            </div>
            <div class="proposal-actions">
              <button
                v-if="proposal.pptx_url"
                @click="handleDownload(proposal.pptx_url)"
                class="download-btn"
              >
                Télécharger PPTX
              </button>
              <span v-else class="processing">En cours de traitement...</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f5f5f5;
}

.dashboard-header {
  background: #7ec33b;
  color: white;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.dashboard-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.logout-btn {
  background: rgba(255,255,255,0.2);
  color: white;
  border: 1px solid rgba(255,255,255,0.3);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255,255,255,0.3);
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px 20px;
}

.actions {
  margin-bottom: 30px;
}

.primary-btn {
  background: #7ec33b;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.primary-btn:hover:not(:disabled) {
  background: #6ab32f;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(122, 195, 59, 0.3);
}

.primary-btn:disabled {
  background: #999;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.proposal-form {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  margin-bottom: 30px;
}

.proposal-form h3 {
  margin-top: 0;
  margin-bottom: 24px;
  color: #333;
  font-size: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e1e1e1;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #7ec33b;
}

.form-group textarea {
  resize: vertical;
  min-height: 120px;
}

.proposals-section h3 {
  margin-bottom: 20px;
  color: #333;
  font-size: 20px;
}

.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.proposals-list {
  display: grid;
  gap: 20px;
}

.proposal-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.proposal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 25px rgba(0,0,0,0.15);
}

.proposal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.proposal-header h4 {
  margin: 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

.date {
  color: #666;
  font-size: 12px;
  font-weight: 500;
}

.proposal-content {
  margin-bottom: 16px;
}

.proposal-content p {
  margin: 0;
  color: #555;
  line-height: 1.6;
}

.proposal-actions {
  display: flex;
  justify-content: flex-end;
}

.download-btn {
  background: #0066cc;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.download-btn:hover {
  background: #0052a3;
}

.processing {
  color: #666;
  font-style: italic;
  font-size: 14px;
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .dashboard-content {
    padding: 20px 15px;
  }

  .proposal-form {
    padding: 20px;
  }

  .proposals-list {
    grid-template-columns: 1fr;
  }
}
</style>
