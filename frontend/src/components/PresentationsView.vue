<script setup>
const emit = defineEmits(['new-presentation'])
const filters = ['Toutes', 'Terminées', 'En cours', 'Types']

const rows = [
  {
    name: 'Traitement de données',
    type: 'Audit',
    client: 'Afriksearch',
    status: 'Terminé',
    date: '12/11/26',
    slide: 8,
    action: 'Téléchargé',
    highlight: true,
  },
  {
    name: 'Nettoyage',
    type: 'Audit',
    client: 'Yango',
    status: 'Terminé',
    date: '05/03/26',
    slide: 8,
    action: 'Téléchargé',
  },
  {
    name: 'Assignation',
    type: 'Audit',
    client: 'PIDG',
    status: 'En cours',
    date: '23/07/26',
    slide: 10,
    action: 'Téléchargé',
  },
]
</script>

<template>
  <section>
    <header class="flex items-start justify-between">
      <div>
        <p class="text-3xl font-semibold text-brand-600">Mes présentations</p>
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
        class="rounded-full px-6 py-2 text-sm font-semibold"
        :class="item === 'Terminées' ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-700'"
      >
        {{ item }}
      </button>
    </div>

    <section class="mt-10 card overflow-hidden">
      <div class="grid grid-cols-[1.6fr_0.9fr_1fr_0.8fr_0.8fr_0.6fr_0.8fr] bg-slate-900 px-6 py-3 text-sm font-semibold text-white">
        <span>Présentation</span>
        <span>Type</span>
        <span>Client</span>
        <span>Statut</span>
        <span>Date</span>
        <span>Slide</span>
        <span class="text-right">Action</span>
      </div>
      <div class="divide-y divide-slate-100">
        <div
          v-for="row in rows"
          :key="row.name"
          class="grid grid-cols-[1.6fr_0.9fr_1fr_0.8fr_0.8fr_0.6fr_0.8fr] items-center px-6 py-4 text-sm"
          :class="row.highlight ? 'bg-brand-50 text-slate-900' : 'bg-white'"
        >
          <span class="font-semibold">{{ row.name }}</span>
          <span class="font-semibold text-slate-700">{{ row.type }}</span>
          <span class="font-semibold text-slate-900">{{ row.client }}</span>
          <span class="font-semibold text-slate-700">{{ row.status }}</span>
          <span class="text-slate-600">{{ row.date }}</span>
          <span class="text-slate-600">{{ row.slide }}</span>
          <span class="text-right font-semibold text-slate-700">{{ row.action }}</span>
        </div>
      </div>
    </section>
  </section>
</template>
