<script setup>
import { computed, ref } from 'vue'
import DashboardHome from './components/DashboardHome.vue'
import PresentationsView from './components/PresentationsView.vue'
import LibraryView from './components/LibraryView.vue'
import NewPresentationView from './components/NewPresentationView.vue'
import SectionPlaceholder from './components/SectionPlaceholder.vue'

const sections = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'presentations', label: 'Mes Présentations' },
  { key: 'library', label: 'Bibliothèque modèles' },
  { key: 'stats', label: 'Statistiques' },
  { key: 'ai', label: 'Génération IA' },
  { key: 'account', label: 'Mon compte' },
  { key: 'settings', label: 'Paramètres IA' },
]

const activeSection = ref('dashboard')
const lastSection = ref('dashboard')

function goToSection(key) {
  activeSection.value = key
}

function openNewPresentation() {
  lastSection.value = activeSection.value
  activeSection.value = 'new-presentation'
}

function goBack() {
  activeSection.value = lastSection.value
}

const activeComponent = computed(() => {
  if (activeSection.value === 'dashboard') return DashboardHome
  if (activeSection.value === 'presentations') return PresentationsView
  if (activeSection.value === 'library') return LibraryView
  if (activeSection.value === 'new-presentation') return NewPresentationView

  const section = sections.find((item) => item.key === activeSection.value)
  return {
    component: SectionPlaceholder,
    props: {
      title: section?.label ?? 'Section',
      description: 'Contenu à définir pour cette section.',
    },
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-25">
    <div class="grid min-h-screen grid-cols-[260px_1fr] bg-white">
      <aside class="relative flex flex-col gap-10 border-r border-slate-200/70 px-6 py-8 pt-44">
        <div class="absolute left-0 top-0 flex items-center gap-3">
          <img src="/logo.png" alt="Logo" class="h-40" />
        </div>

        <nav class="flex flex-col gap-2 text-sm font-semibold text-slate-600">
          <button
            v-for="item in sections"
            :key="item.key"
            type="button"
            @click="goToSection(item.key)"
            :class="[
              'flex items-center gap-3 rounded-full px-4 py-3 transition',
              activeSection === item.key
                ? 'bg-brand-500 text-white'
                : 'text-slate-600 hover:bg-slate-100',
            ]"
          >
            <span
              :class="[
                'h-2 w-2 rounded-full',
                activeSection === item.key ? 'bg-white' : 'bg-slate-300',
              ]"
            ></span>
            {{ item.label }}
          </button>
        </nav>

        <button class="mt-auto flex items-center justify-center gap-3 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white">
          Déconnexion
        </button>
      </aside>

      <main class="bg-slate-25 px-10 py-8">
        <component
          :is="activeComponent.component ?? activeComponent"
          v-bind="activeComponent.props ?? {}"
          @new-presentation="openNewPresentation"
          @back="goBack"
        />
      </main>
    </div>
  </div>
</template>
