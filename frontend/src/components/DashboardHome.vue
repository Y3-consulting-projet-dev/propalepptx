<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getDashboardSummary } from '../api.js'

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['new-presentation', 'open-editor'])

const loading = ref(true)
const loadError = ref('')
const activeUsersCount = ref(0)
const recentPresentations = ref([])
const searchQuery = ref('')

const initials = (user) => {
  const first = (user?.first_name || '').trim()
  const last = (user?.last_name || '').trim()
  const a = first ? first[0] : ''
  const b = last ? last[0] : ''
  return (a + b).toUpperCase() || 'U'
}

const activities = [
  { title: 'Commentaires et validations centralisés', time: 'Nouveau' },
  { title: 'Suivi des soumissions assistant → manager → associé', time: 'Actif' },
]

function normalizeStatus(status) {
  if (status === 'completed') {
    return { label: 'Terminée', dot: 'bg-emerald-500' }
  }
  if (status === 'changes_requested') {
    return { label: 'Corrections demandées', dot: 'bg-rose-500' }
  }
  if (status === 'submitted_to_associate') {
    return { label: "Soumise à l'associé", dot: 'bg-emerald-400' }
  }
  if (status === 'submitted_to_manager') {
    return { label: 'Soumise au manager', dot: 'bg-sky-500' }
  }
  return { label: 'Brouillon', dot: 'bg-amber-500' }
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('fr-FR')
}

async function loadSummary() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getDashboardSummary(searchQuery.value)
    activeUsersCount.value = Number(data.active_users_count || 0)
    recentPresentations.value = data.recent_presentations || []
  } catch (error) {
    loadError.value = error.message || 'Erreur de chargement du dashboard'
  } finally {
    loading.value = false
  }
}

const activeUsersLabel = computed(() => {
  return `${activeUsersCount.value} actif${activeUsersCount.value > 1 ? 's' : ''}`
})

onMounted(loadSummary)
watch(searchQuery, loadSummary)
</script>

<template>
  <div>
    <header class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
          {{ initials(props.user) }}
        </div>
        <div>
          <p class="text-sm font-semibold text-slate-900">{{ props.user?.name }}</p>
          <p class="text-xs text-slate-500">{{ props.user?.grade }}</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button class="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">
          En ligne : {{ activeUsersLabel }}
        </button>
        <button
          class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white"
          @click="emit('new-presentation')"
        >
          Nouvelle présentation
        </button>
      </div>
    </header>

    <div class="mt-6 flex items-center justify-end">
      <div class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500">
        <input
          v-model="searchQuery"
          type="text"
          class="w-64 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
          placeholder="Rechercher une présentation ou un client"
        />
        <span class="text-slate-400">⌕</span>
      </div>
    </div>

    <section class="mt-6 card">
      <div class="flex items-center justify-between px-6 py-4">
        <div>
          <h3 class="text-lg font-semibold text-brand-600">
            {{ searchQuery.trim() ? 'Résultats de recherche' : 'Présentations récentes' }}
          </h3>
          <p class="mt-1 text-sm text-slate-500">
            {{ searchQuery.trim() ? 'Recherche parmi toutes les présentations accessibles.' : 'Les dernières présentations générées dans la plateforme.' }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-[1.6fr_0.8fr_0.9fr_0.7fr] table-head px-6 py-3 text-sm font-semibold">
        <span>Présentation</span>
        <span>Client</span>
        <span>Statut</span>
        <span>Date</span>
      </div>

      <div v-if="loading" class="space-y-3 px-6 py-6">
        <div v-for="n in 3" :key="n" class="h-12 animate-pulse rounded-lg bg-slate-100"></div>
      </div>

      <div v-else-if="loadError" class="px-6 py-6 text-sm text-red-600">
        {{ loadError }}
      </div>

      <div v-else-if="!recentPresentations.length" class="px-6 py-8 text-sm text-slate-400">
        {{ searchQuery.trim() ? 'Aucune présentation trouvée pour cette recherche.' : 'Aucune présentation récente disponible.' }}
      </div>

      <div v-else class="divide-y divide-slate-100">
        <button
          v-for="presentation in recentPresentations"
          :key="presentation.presentation_id"
          type="button"
          class="grid w-full grid-cols-[1.6fr_0.8fr_0.9fr_0.7fr] items-center px-6 py-4 text-left text-sm transition hover:bg-brand-50/50"
          @click="emit('open-editor', presentation.presentation_id)"
        >
          <div class="min-w-0">
            <p class="truncate font-semibold text-slate-900">{{ presentation.title }}</p>
            <p class="mt-1 truncate text-xs text-slate-400">
              {{ presentation.mission_type || '-' }} · {{ presentation.owner_name || 'Utilisateur' }}
            </p>
          </div>
          <span class="font-medium text-slate-600">{{ presentation.client_name || '-' }}</span>
          <div class="flex items-center gap-3">
            <span class="text-slate-700">{{ normalizeStatus(presentation.status).label }}</span>
            <span :class="['h-3 w-3 rounded-full', normalizeStatus(presentation.status).dot]"></span>
          </div>
          <span class="text-slate-500">{{ formatDate(presentation.created_at || presentation.updated_at) }}</span>
        </button>
      </div>
    </section>

    <!-- <section class="mt-6 grid gap-6 xl:grid-cols-[2fr_1fr]">
      <div class="card px-6 py-6">
        <div class="flex items-center justify-between">
          <p class="text-sm font-semibold text-slate-600">Performance collaborateurs</p>
          <div class="stat-pill">Tâche vs Exécution</div>
        </div>
        <div class="mt-6 flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/70 text-sm text-slate-400">
          Visualisation à brancher
        </div>
      </div>

      <div class="card px-6 py-6">
        <h3 class="text-lg font-semibold text-brand-600">Activité récente</h3>
        <div class="mt-4 space-y-5">
          <div v-for="activity in activities" :key="activity.title" class="flex items-start justify-between gap-4">
            <p class="text-sm font-semibold text-slate-800">{{ activity.title }}</p>
            <span class="text-xs text-slate-500">{{ activity.time }}</span>
          </div>
        </div>
      </div>
    </section> -->
  </div>
</template>
