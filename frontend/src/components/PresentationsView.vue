<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAuthHeaders } from '../api.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const emit = defineEmits(['new-presentation', 'open-editor'])

const loading = ref(true)
const error = ref('')
const presentations = ref([])
const activeFilter = ref('Toutes')

const filters = ['Toutes', 'Brouillons', 'Soumises']

function formatPresentationTitle(row) {
  const filename = String(row?.filename || '').trim()
  if (!filename) {
    const mission = String(row?.form?.missionType || '').trim()
    const client = String(row?.form?.clientName || '').trim()
    if (mission || client) {
      return ['Propale', mission, client].filter(Boolean).join('_')
    }
    return 'Présentation'
  }
  return filename.replace(/\.pptx$/i, '')
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('fr-FR')
}

function normalizeStatus(status) {
  if (status === 'completed') {
    return { label: 'Terminée', classes: 'bg-emerald-100 text-emerald-700' }
  }
  if (status === 'changes_requested') {
    return { label: 'Corrections demandées', classes: 'bg-rose-100 text-rose-700' }
  }
  if (status === 'submitted_to_manager') {
    return { label: 'Soumise au manager', classes: 'bg-sky-100 text-sky-700' }
  }
  if (status === 'submitted_to_associate') {
    return { label: "Soumise à  l'associé", classes: 'bg-emerald-100 text-emerald-700' }
  }
  return { label: 'Brouillon', classes: 'bg-amber-100 text-amber-700' }
}

async function loadPresentations() {
  loading.value = true
  error.value = ''

  try {
    const res = await fetch(`${API_BASE}/api/presentations`, {
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors du chargement')

    presentations.value = (data.items || []).sort((left, right) => {
      const leftDate = new Date(left.updated_at || left.created_at || 0).getTime()
      const rightDate = new Date(right.updated_at || right.created_at || 0).getTime()
      return rightDate - leftDate
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const filteredPresentations = computed(() => {
  if (activeFilter.value === 'Brouillons') {
    return presentations.value.filter((item) => !String(item.status || '').startsWith('submitted'))
  }
  if (activeFilter.value === 'Soumises') {
    return presentations.value.filter((item) => String(item.status || '').startsWith('submitted'))
  }
  return presentations.value
})

onMounted(loadPresentations)
</script>

<template>
  <section>
    <header class="flex items-start justify-between">
      <div>
        <p class="text-3xl font-semibold text-brand-600">Mes présentations</p>
        <p class="mt-2 text-sm text-slate-500">Retrouvez ici toutes les présentations générées depuis vos modèles.</p>
      </div>
      <div class="flex items-center gap-4">
        <button
          class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white"
          @click="emit('new-presentation')"
        >
          Nouvelle présentation
        </button>
      </div>
    </header>

    <div class="mt-10 flex items-center justify-center gap-4">
      <button
        v-for="item in filters"
        :key="item"
        class="rounded-full px-6 py-2 text-sm font-semibold transition"
        :class="activeFilter === item ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-700'"
        @click="activeFilter = item"
      >
        {{ item }}
      </button>
    </div>

    <section class="mt-10 card overflow-hidden">
      <div class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr] bg-slate-900 px-6 py-3 text-sm font-semibold text-white">
        <span>Présentation</span>
        <span>Type</span>
        <span>Client</span>
        <span>Statut</span>
        <span>Date</span>
        <span>Slides</span>
        <span class="text-right">Action</span>
      </div>

      <div v-if="loading" class="space-y-3 bg-white px-6 py-6">
        <div v-for="n in 5" :key="n" class="h-12 animate-pulse rounded-lg bg-slate-100"></div>
      </div>

      <div v-else-if="error" class="bg-white px-6 py-8 text-sm text-red-600">
        {{ error }}
      </div>

      <div v-else-if="!filteredPresentations.length" class="bg-white px-6 py-10 text-center">
        <p class="text-sm font-semibold text-slate-700">Aucune présentation trouvée</p>
        <p class="mt-2 text-sm text-slate-400">Générez votre première présentation pour la voir apparaître ici.</p>
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="row in filteredPresentations"
          :key="row.presentation_id"
          class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr] items-center bg-white px-6 py-4 text-sm transition hover:bg-brand-50/50"
        >
          <div class="min-w-0">
            <p class="truncate font-semibold text-slate-900">
              {{ formatPresentationTitle(row) }}
            </p>
            <p class="mt-1 truncate text-xs text-slate-400">{{ row.template || '-' }}</p>
          </div>

          <span class="font-semibold text-slate-700">{{ row.form?.missionType || '-' }}</span>
          <span class="font-semibold text-slate-900">{{ row.form?.clientName || '-' }}</span>

          <span>
            <span
              class="rounded-full px-3 py-1 text-xs font-semibold"
              :class="normalizeStatus(row.status).classes"
            >
              {{ normalizeStatus(row.status).label }}
            </span>
          </span>

          <span class="text-slate-600">{{ formatDate(row.updated_at || row.created_at) }}</span>
          <span class="text-slate-600">{{ row.slide_count || 0 }}</span>

          <div class="text-right">
            <button
              class="rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
              @click="emit('open-editor', row.presentation_id)"
            >
              Ouvrir
            </button>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>
