<script setup>
const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['new-presentation'])

const initials = (user) => {
  const first = (user?.first_name || '').trim()
  const last = (user?.last_name || '').trim()
  const a = first ? first[0] : ''
  const b = last ? last[0] : ''
  return (a + b).toUpperCase() || 'U'
}
const stats = [
  { value: '47', label: 'Présentations générées', badge: 'P' },
  { value: '50h', label: 'Temps économisé ce mois', badge: 'T' },
  { value: '94%', label: 'Taux de satisfaction', badge: 'S' },
  { value: '11', label: 'Utilisateurs actifs', badge: 'U' },
]

const presentations = [
  { name: 'Collaborateur A', date: '12/11/2020', status: 'Terminé', dot: 'bg-brand-500' },
  { name: 'Collaborateur B', date: '12/11/2020', status: 'En cours...', dot: 'bg-red-500' },
  { name: 'Collaborateur C', date: '12/11/2020', status: 'Terminé', dot: 'bg-brand-500' },
]

const activities = [
  { title: 'Audit RH — Généré et téléchargé', time: 'Il y a 2h' },
  { title: 'Thomas D. a modifié le template Stratégie', time: 'Hier' },
]
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
      <div class="flex items-center gap-4">
        <button class="h-10 w-10 rounded-full border border-slate-200 bg-white text-slate-600">!</button>
        <button
          class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white"
          @click="emit('new-presentation')"
        >
          Nouvelle présentation
        </button>
      </div>
    </header>

    <section class="mt-8 grid gap-4 xl:grid-cols-4">
      <div v-for="stat in stats" :key="stat.label" class="card px-6 py-5">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-3xl font-bold text-brand-600">{{ stat.value }}</p>
            <p class="text-sm font-semibold text-slate-600">{{ stat.label }}</p>
          </div>
          <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-sm font-bold text-brand-700">
            {{ stat.badge }}
          </span>
        </div>
      </div>
    </section>

    <div class="mt-6 flex items-center justify-end">
      <div class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500">
        <span>Rechercher un collaborateur</span>
        <span class="text-slate-400">⌕</span>
      </div>
    </div>

    <section class="mt-6 card">
      <div class="grid grid-cols-[1.6fr_0.7fr_0.7fr_0.6fr] table-head px-6 py-3 text-sm font-semibold">
        <span>Présentation</span>
        <span>Type</span>
        <span>Statut</span>
        <span>Dates</span>
      </div>
      <div class="divide-y divide-slate-100">
        <div
          v-for="presentation in presentations"
          :key="presentation.name"
          class="grid grid-cols-[1.6fr_0.7fr_0.7fr_0.6fr] items-center px-6 py-4 text-sm"
        >
          <span class="font-semibold text-slate-900">{{ presentation.name }}</span>
          <span class="text-slate-500">Audit RH</span>
          <span class="text-slate-700">{{ presentation.status }}</span>
          <div class="flex items-center justify-end gap-3">
            <span class="text-slate-500">{{ presentation.date }}</span>
            <span :class="['h-3 w-3 rounded-full', presentation.dot]"></span>
          </div>
        </div>
      </div>
    </section>

    <section class="mt-6 grid gap-6 xl:grid-cols-[2fr_1fr]">
      <div class="card px-6 py-6">
        <div class="flex items-center justify-between">
          <p class="text-sm font-semibold text-slate-600">Performance collaborateurs</p>
          <div class="stat-pill">Tâche vs Exécution</div>
        </div>
        <div class="mt-6 h-56 rounded-xl border border-dashed border-slate-200 bg-slate-50/70"></div>
      </div>

      <div class="card px-6 py-6">
        <h3 class="text-lg font-semibold text-brand-600">Activité récente</h3>
        <div class="mt-4 space-y-5">
          <div v-for="activity in activities" :key="activity.title" class="flex items-start justify-between">
            <p class="text-sm font-semibold text-slate-800">{{ activity.title }}</p>
            <span class="text-xs text-slate-500">{{ activity.time }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
