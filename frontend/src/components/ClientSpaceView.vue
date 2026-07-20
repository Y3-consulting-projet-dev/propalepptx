<script setup>
import { onMounted, ref, reactive, computed, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

// ─── Fallback static options (enrichies dynamiquement depuis la BDD) ──────────
const BASE_SECTORS = [
  'Banque & Finance', 'Télécommunications et TIC', 'Transport & Logistique',
  'Énergie & Mines', 'Agro-industrie', 'Santé', 'Immobilier & BTP',
  'Construction et travaux publics (BTP)',
  'Commerce & Distribution', 'Administration publique', 'Assurance', 'Autre',
]
const BASE_COUNTRIES = [
  "Côte d'Ivoire", 'Sénégal', 'Mali', 'Burkina Faso', 'Guinée', 'Togo',
  'Bénin', 'Niger', 'Cameroun', 'Gabon', 'Congo', 'RDC', 'Madagascar',
  'Mauritanie', 'Maroc', 'Tunisie', 'Algérie', 'France', 'Autre',
]

const sectorOptions  = ref([...BASE_SECTORS])
const countryOptions = ref([...BASE_COUNTRIES])

// Charge les valeurs distinctes depuis la BDD et fusionne avec les options statiques
async function loadMetaOptions() {
  try {
    const [sRes, cRes] = await Promise.all([
      fetch(`${API_BASE}/api/clients/meta/sectors`),
      fetch(`${API_BASE}/api/clients/meta/countries`),
    ])
    const sData = await sRes.json()
    const cData = await cRes.json()

    const merged = (base, fromDb) => {
      const set = new Set([...base, ...(fromDb || [])])
      return [...set].sort((a, b) => a.localeCompare(b, 'fr'))
    }
    sectorOptions.value  = merged(BASE_SECTORS,  sData.items)
    countryOptions.value = merged(BASE_COUNTRIES, cData.items)
  } catch {
    // silently keep static fallback
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatDate(isoStr) {
  if (!isoStr) return '—'
  // Handle both "2026-01-15" and ISO datetime strings
  const d = new Date(isoStr.includes('T') ? isoStr : isoStr + 'T00:00:00')
  if (isNaN(d)) return isoStr
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const EMPTY_FORM = () => ({
  company_name: '',
  sector: '',
  country: '',
  civility: '',
  responsable_name: '',
  responsable_function: '',
  legal_form: '',
  RCCM: '',
  address: '',
  creation_date: '',
})

// ─── State ────────────────────────────────────────────────────────────────────
const clients     = ref([])
const total       = ref(0)
const totalPages  = ref(1)
const page        = ref(1)
const limit       = 25
const searchQuery = ref('')
const loading     = ref(true)
const tableError  = ref('')

// Create modal
const showCreate  = ref(false)
const createForm  = reactive(EMPTY_FORM())
const createError = ref('')
const creating    = ref(false)

// View / Edit modal
const showEdit    = ref(false)
const editForm    = reactive(EMPTY_FORM())
const editId      = ref(null)
const editError   = ref('')
const saving      = ref(false)
const isEditMode  = ref(false)

// Delete confirm
const showDelete  = ref(false)
const deleting    = ref(false)

// ─── Load clients ─────────────────────────────────────────────────────────────
let searchTimer = null
watch(searchQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadClients() }, 350)
})

async function loadClients() {
  loading.value    = true
  tableError.value = ''
  try {
    const params = new URLSearchParams({ page: page.value, limit, q: searchQuery.value })
    const res    = await fetch(`${API_BASE}/api/clients?${params}`)
    const data   = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur')
    clients.value    = data.items     || []
    total.value      = data.total     || 0
    totalPages.value = data.totalPages || 1
  } catch (e) {
    tableError.value = e.message
  } finally {
    loading.value = false
  }
}

function goToPage(p) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  loadClients()
}

onMounted(async () => {
  await loadMetaOptions()
  await loadClients()
})

// ─── Create ───────────────────────────────────────────────────────────────────
function openCreate() {
  Object.assign(createForm, EMPTY_FORM())
  createError.value = ''
  showCreate.value  = true
}

async function submitCreate() {
  if (!createForm.company_name.trim()) { createError.value = 'Le nom du client est requis'; return }
  creating.value    = true
  createError.value = ''
  try {
    const res  = await fetch(`${API_BASE}/api/clients`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...createForm }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur')
    showCreate.value = false
    page.value       = 1
    await loadMetaOptions()   // refresh options after new client
    await loadClients()
  } catch (e) {
    createError.value = e.message
  } finally {
    creating.value = false
  }
}

// ─── View / Edit ──────────────────────────────────────────────────────────────
function openView(client) {
  editId.value     = client._id
  isEditMode.value = false
  editError.value  = ''
  Object.assign(editForm, {
    company_name:         client.company_name         || '',
    sector:               client.sector               || '',
    country:              client.country              || '',
    civility:             client.civility             || '',
    responsable_name:     client.responsable_name     || '',
    responsable_function: client.responsable_function || '',
    legal_form:           client.legal_form           || '',
    RCCM:                 client.RCCM                 || '',
    address:              client.address              || '',
    // Keep raw ISO for the date input, display formatted in read mode
    creation_date: client.creation_date
      ? (client.creation_date.includes('T')
          ? client.creation_date.split('T')[0]
          : client.creation_date)
      : '',
  })
  showEdit.value   = true
  showDelete.value = false
}

async function submitEdit() {
  if (!editForm.company_name.trim()) { editError.value = 'Le nom du client est requis'; return }
  saving.value    = true
  editError.value = ''
  try {
    const res  = await fetch(`${API_BASE}/api/clients/${editId.value}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...editForm }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur')
    isEditMode.value = false
    await loadMetaOptions()
    await loadClients()
  } catch (e) {
    editError.value = e.message
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  deleting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/clients/${editId.value}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Erreur lors de la suppression')
    showEdit.value   = false
    showDelete.value = false
    await loadClients()
  } catch (e) {
    editError.value = e.message
  } finally {
    deleting.value = false
  }
}

// ─── Pagination ───────────────────────────────────────────────────────────────
const pageRange = computed(() => {
  const range = []
  const start = Math.max(1, page.value - 2)
  const end   = Math.min(totalPages.value, page.value + 2)
  for (let i = start; i <= end; i++) range.push(i)
  return range
})
const rowStart = computed(() => (page.value - 1) * limit + 1)
const rowEnd   = computed(() => Math.min(page.value * limit, total.value))
</script>

<template>
  <section>

    <!-- ── Header ── -->
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-3xl font-semibold text-brand-600">Espace clients</p>
        <p class="mt-1 text-sm text-slate-500">{{ total }} client{{ total > 1 ? 's' : '' }} au total</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          class="flex items-center gap-2 rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600"
          @click="openCreate"
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path d="M12 5v14M5 12h14" stroke-linecap="round"/>
          </svg>
          Nouveau client
        </button>
      </div>
    </header>

    <!-- ── Search bar ── -->
    <div class="mt-6 flex items-center gap-3">
      <div class="flex flex-1 max-w-sm items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="flex-shrink-0 text-slate-400">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher par nom du client ou secteur d'activités"
          class="flex-1 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
        />
        <button v-if="searchQuery" class="text-slate-400 hover:text-slate-600" @click="searchQuery = ''">✕</button>
      </div>
    </div>

    <!-- ── Table ── -->
    <div class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div v-if="loading" class="flex items-center justify-center py-16">
        <div class="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-brand-500"></div>
      </div>
      <div v-else-if="tableError" class="py-12 text-center text-sm text-red-500">{{ tableError }}</div>
      <div v-else-if="!clients.length" class="flex flex-col items-center gap-3 py-16 text-slate-400">
        <svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p class="text-sm font-medium">Aucun client trouvé</p>
        <button class="text-xs text-brand-500 underline" @click="openCreate">Créer le premier client</button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[760px] text-sm">
          <thead>
            <tr class="border-b border-slate-100 bg-slate-50">
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">#</th>
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Nom de l'entreprise</th>
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Responsable</th>
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Secteur d'activité</th>
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Pays</th>
              <th class="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">RCCM</th>
              <th class="px-5 py-3.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="(client, i) in clients" :key="client._id"
              class="group cursor-pointer transition hover:bg-brand-50/40"
              @click="openView(client)"
            >
              <td class="px-5 py-4 text-xs text-slate-400">{{ rowStart + i }}</td>
              <td class="px-5 py-4 font-semibold text-slate-900">{{ client.company_name }}</td>
              <td class="px-5 py-4 text-slate-600">
                {{ [client.civility, client.responsable_name].filter(Boolean).join(' ') || '—' }}
              </td>
              <td class="px-5 py-4">
                <span v-if="client.sector" class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                  {{ client.sector }}
                </span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="px-5 py-4 text-slate-600">{{ client.country || '—' }}</td>
              <td class="px-5 py-4 text-xs text-slate-500">{{ client.RCCM || '—' }}</td>
              <td class="px-5 py-4 text-right" @click.stop>
                <button
                  class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 opacity-0 transition group-hover:opacity-100 hover:border-brand-400 hover:text-brand-600"
                  @click="openView(client)"
                >Voir</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="totalPages > 1" class="mt-4 flex items-center justify-between text-sm">
      <p class="text-xs text-slate-500">{{ rowStart }}–{{ rowEnd }} sur {{ total }} clients</p>
      <div class="flex items-center gap-1">
        <button class="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 disabled:opacity-30"
                :disabled="page === 1" @click="goToPage(page - 1)">‹</button>
        <button v-for="p in pageRange" :key="p"
                class="flex h-8 w-8 items-center justify-center rounded-lg border text-xs font-semibold transition"
                :class="p === page ? 'border-brand-500 bg-brand-500 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-brand-400'"
                @click="goToPage(p)">{{ p }}</button>
        <button class="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 disabled:opacity-30"
                :disabled="page === totalPages" @click="goToPage(page + 1)">›</button>
      </div>
    </div>

    <!-- ══ CREATE MODAL ══════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
        <div class="relative flex w-full max-w-xl flex-col rounded-2xl bg-white shadow-2xl" style="max-height:90vh">
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <p class="text-base font-semibold text-slate-900">Nouveau client</p>
            <button class="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-slate-400 hover:bg-slate-50" @click="showCreate = false">✕</button>
          </div>
          <div class="overflow-y-auto px-6 py-5">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600 sm:col-span-2">
                Nom de l'entreprise *
                <input v-model="createForm.company_name" type="text" placeholder="Ex : NSIA Bank"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Civilité
                <select v-model="createForm.civility"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white">
                  <option value="">—</option>
                  <option>M.</option><option>Mme</option>
                </select>
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Responsable
                <input v-model="createForm.responsable_name" type="text" placeholder="Nom du responsable"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Fonction du responsable
                <input v-model="createForm.responsable_function" type="text" placeholder="Directeur Général…"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Forme juridique
                <input v-model="createForm.legal_form" type="text" placeholder="SARL, SA, SAS…"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                RCCM
                <input v-model="createForm.RCCM" type="text" placeholder="CI-ABJ-2020-…"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Secteur d'activité
                <!-- Combobox : saisie libre ou sélection dans la liste existante -->
                <input v-model="createForm.sector" type="text" list="sector-list-c" placeholder="Saisir ou choisir…"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
                <datalist id="sector-list-c">
                  <option v-for="s in sectorOptions" :key="s" :value="s" />
                </datalist>
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Pays
                <input v-model="createForm.country" type="text" list="country-list-c" placeholder="Rechercher…"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
                <datalist id="country-list-c">
                  <option v-for="c in countryOptions" :key="c" :value="c" />
                </datalist>
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600 sm:col-span-2">
                Adresse
                <input v-model="createForm.address" type="text" placeholder="Cocody, Abidjan"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Date de création
                <input v-model="createForm.creation_date" type="date"
                  class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:bg-white" />
              </label>
            </div>
            <p v-if="createError" class="mt-3 text-xs text-red-500">{{ createError }}</p>
          </div>
          <div class="flex justify-end gap-3 border-t border-slate-100 px-6 py-4">
            <button class="rounded-xl border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50" @click="showCreate = false">Annuler</button>
            <button
              class="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
              :disabled="creating" @click="submitCreate"
            >
              <span v-if="creating" class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
              {{ creating ? 'Création…' : 'Créer le client' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ══ VIEW / EDIT MODAL ════════════════════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="showEdit" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
        <div class="relative flex w-full max-w-xl flex-col rounded-2xl bg-white shadow-2xl" style="max-height:90vh">

          <!-- Header -->
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div>
              <p class="text-sm font-semibold text-slate-900">{{ editForm.company_name }}</p>
              <p class="text-xs text-slate-400">{{ editForm.sector || 'Secteur non défini' }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button v-if="!isEditMode"
                class="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-brand-400 hover:text-brand-600"
                @click="isEditMode = true">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke-linecap="round"/>
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke-linecap="round"/>
                </svg>
                Modifier
              </button>
              <button v-if="!isEditMode"
                class="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-50"
                @click="showDelete = true">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path d="M3 6h18M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke-linecap="round"/>
                </svg>
                Supprimer
              </button>
              <button class="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-slate-400 hover:bg-slate-50"
                      @click="showEdit = false; isEditMode = false">✕</button>
            </div>
          </div>

          <!-- Delete confirm banner -->
          <div v-if="showDelete" class="flex items-center justify-between bg-red-50 px-6 py-3 text-sm">
            <p class="font-medium text-red-700">Supprimer ce client ?</p>
            <div class="flex gap-2">
              <button class="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600" @click="showDelete = false">Annuler</button>
              <button class="rounded-lg bg-red-500 px-3 py-1 text-xs font-semibold text-white disabled:opacity-60"
                      :disabled="deleting" @click="confirmDelete">{{ deleting ? '…' : 'Confirmer' }}</button>
            </div>
          </div>

          <!-- Fields -->
          <div class="overflow-y-auto px-6 py-5">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600 sm:col-span-2">
                Nom de l'entreprise *
                <input v-model="editForm.company_name" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Civilité
                <!-- Mode lecture : simple input, Mode édition : select -->
                <select v-if="isEditMode" v-model="editForm.civility"
                  class="rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none">
                  <option value="">—</option>
                  <option>M.</option><option>Mme</option><option>Dr</option><option>Pr</option>
                </select>
                <input v-else :value="editForm.civility || '—'" disabled
                  class="rounded-xl border border-transparent bg-slate-50 px-4 py-2.5 text-sm text-slate-800 cursor-default" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Responsable
                <input v-model="editForm.responsable_name" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Fonction du responsable
                <input v-model="editForm.responsable_function" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Forme juridique
                <input v-model="editForm.legal_form" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                RCCM
                <input v-model="editForm.RCCM" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <!-- ✅ SECTEUR : combobox en édition, texte brut en lecture -->
              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Secteur d'activité
                <template v-if="isEditMode">
                  <input v-model="editForm.sector" type="text" list="sector-list-e" placeholder="Saisir ou choisir…"
                    class="rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none" />
                  <datalist id="sector-list-e">
                    <option v-for="s in sectorOptions" :key="s" :value="s" />
                  </datalist>
                </template>
                <input v-else :value="editForm.sector || '—'" disabled
                  class="rounded-xl border border-transparent bg-slate-50 px-4 py-2.5 text-sm text-slate-800 cursor-default" />
              </label>

              <!-- ✅ PAYS : combobox en édition, texte brut en lecture -->
              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Pays
                <template v-if="isEditMode">
                  <input v-model="editForm.country" type="text" list="country-list-e" placeholder="Rechercher…"
                    class="rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none" />
                  <datalist id="country-list-e">
                    <option v-for="c in countryOptions" :key="c" :value="c" />
                  </datalist>
                </template>
                <input v-else :value="editForm.country || '—'" disabled
                  class="rounded-xl border border-transparent bg-slate-50 px-4 py-2.5 text-sm text-slate-800 cursor-default" />
              </label>

              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600 sm:col-span-2">
                Adresse
                <input v-model="editForm.address" type="text" :disabled="!isEditMode"
                  class="rounded-xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-800 focus:outline-none transition"
                  :class="isEditMode ? 'border-brand-200 focus:border-brand-500 bg-white' : 'border-transparent cursor-default'" />
              </label>

              <!-- ✅ DATE : input date en édition, formatée en lecture -->
              <label class="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
                Date de création
                <input v-if="isEditMode" v-model="editForm.creation_date" type="date"
                  class="rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none" />
                <input v-else :value="formatDate(editForm.creation_date)" disabled
                  class="rounded-xl border border-transparent bg-slate-50 px-4 py-2.5 text-sm text-slate-800 cursor-default" />
              </label>
            </div>
            <p v-if="editError" class="mt-3 text-xs text-red-500">{{ editError }}</p>
          </div>

          <!-- Footer -->
          <div class="flex justify-end gap-3 border-t border-slate-100 px-6 py-4">
            <template v-if="isEditMode">
              <button class="rounded-xl border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                      @click="isEditMode = false; editError = ''">Annuler</button>
              <button
                class="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
                :disabled="saving" @click="submitEdit">
                <span v-if="saving" class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
                {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
              </button>
            </template>
            <button v-else class="rounded-xl border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                    @click="showEdit = false">Fermer</button>
          </div>
        </div>
      </div>
    </Teleport>

  </section>
</template>