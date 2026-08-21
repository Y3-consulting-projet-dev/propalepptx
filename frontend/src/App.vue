<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import DashboardHome from './views/DashboardHome.vue'
import PresentationsView from './views/PresentationsView.vue'
import LibraryView from './views/LibraryView.vue'
import NewPresentationView from './views/NewPresentationView.vue'
import PresentationEditor from './views/PresentationEditor.vue'
import SectionPlaceholder from './components/SectionPlaceholder.vue'
import Login from './views/Login.vue'
import Moncompte from './views/Moncompte.vue'
import Statistique from './views/Statistique.vue'
import { APP_NAVIGATION_STORAGE_KEY, getCurrentUser, getNotifications, isLoggedIn, logout, markNotificationsRead, sendSessionHeartbeat } from './services'
import ClientSpaceView from './views/ClientSpaceView.vue'

const defaultSection = 'dashboard'

const isAuthenticated = ref(false)
const currentUser = ref(null)
const activeSection = ref(defaultSection)
const lastSection = ref(defaultSection)
const selectedPresentationId = ref(null)
const selectedTemplateFilename = ref(null)
const notifications = ref([])
const unreadNotifications = ref(0)
const showNotifications = ref(false)
const showNotificationsModal = ref(false)
const sidebarOpen = ref(false)
let notificationsTimer = null
let heartbeatTimer = null

const sections = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'presentations', label: 'Mes Présentations' },
  { key: 'library', label: 'Bibliothèque modèles' },
  { key: 'clients-load', label: 'Clients' },
  // { key: 'ai', label: 'Génération IA' },
  { key: 'account', label: 'Mon compte' },
  // { key: 'settings', label: 'Paramètres IA' },
]

function resetNavigation() {
  activeSection.value = defaultSection
  lastSection.value = defaultSection
  selectedPresentationId.value = null
  selectedTemplateFilename.value = null
  localStorage.removeItem(APP_NAVIGATION_STORAGE_KEY)
  notifications.value = []
  unreadNotifications.value = 0
  showNotifications.value = false
  showNotificationsModal.value = false
}

function restoreNavigation() {
  if (!isLoggedIn()) {
    resetNavigation()
    return
  }

  const raw = localStorage.getItem(APP_NAVIGATION_STORAGE_KEY)
  if (!raw) return

  try {
    const saved = JSON.parse(raw)
    activeSection.value = typeof saved.activeSection === 'string' ? saved.activeSection : defaultSection
    lastSection.value = typeof saved.lastSection === 'string' ? saved.lastSection : defaultSection
    selectedPresentationId.value = typeof saved.selectedPresentationId === 'string' ? saved.selectedPresentationId : null
    selectedTemplateFilename.value = typeof saved.selectedTemplateFilename === 'string' ? saved.selectedTemplateFilename : null
  } catch {
    resetNavigation()
  }
}

function persistNavigation() {
  if (!isAuthenticated.value) return

  localStorage.setItem(
    APP_NAVIGATION_STORAGE_KEY,
    JSON.stringify({
      activeSection: activeSection.value,
      lastSection: lastSection.value,
      selectedPresentationId: selectedPresentationId.value,
      selectedTemplateFilename: selectedTemplateFilename.value,
    }),
  )
}

const checkAuth = () => {
  isAuthenticated.value = isLoggedIn()
  currentUser.value = getCurrentUser()
}

const handleLogin = () => {
  checkAuth()
  resetNavigation()
}

const handleLogout = () => {
  logout()
  resetNavigation()
  checkAuth()
}

async function loadNotifications() {
  if (!isLoggedIn()) return
  try {
    const data = await getNotifications()
    notifications.value = data.items || []
    unreadNotifications.value = data.unread_count || 0
  } catch {
    notifications.value = []
    unreadNotifications.value = 0
  }
}

async function toggleNotifications() {
  showNotifications.value = !showNotifications.value
  if (!showNotifications.value) return
  await loadNotifications()
}

async function openNotification(item) {
  if (!item) return

  try {
    if (item.presentation_id) {
      await markNotificationsRead(item.presentation_id)
    }
  } catch {
  } finally {
    await loadNotifications()
  }

  showNotifications.value = false

  if (item.presentation_id) {
    lastSection.value = 'presentations'
    openPresentationEditor(item.presentation_id)
  }
}

async function openNotificationsModal() {
  showNotificationsModal.value = true
  await loadNotifications()
}

const handleStorage = (e) => {
  if (e.key === 'access_token') {
    checkAuth()
    if (!isLoggedIn()) {
      resetNavigation()
    }
  }
}

function goToSection(key) {
  activeSection.value = key
  sidebarOpen.value = false
}

function openNewPresentation() {
  selectedTemplateFilename.value = null
  lastSection.value = activeSection.value
  activeSection.value = 'new-presentation'
  sidebarOpen.value = false
}

function useTemplateFromLibrary(templateFilename) {
  selectedTemplateFilename.value = templateFilename
  lastSection.value = activeSection.value
  activeSection.value = 'new-presentation'
  sidebarOpen.value = false
}

function openPresentationEditor(presentationId) {
  selectedPresentationId.value = presentationId
  lastSection.value = activeSection.value
  activeSection.value = 'presentation-editor'
  sidebarOpen.value = false
}

function goBack() {
  activeSection.value = lastSection.value
}

const activeComponent = computed(() => {
  if (activeSection.value === 'dashboard') return DashboardHome
  if (activeSection.value === 'presentations') return PresentationsView
  if (activeSection.value === 'library') return LibraryView
  if (activeSection.value === 'stats') return Statistique
  if (activeSection.value === 'new-presentation') {
    return {
      component: NewPresentationView,
      props: {
        initialTemplateFilename: selectedTemplateFilename.value,
      },
    }
  }
  if (activeSection.value === 'presentation-editor') {
    return {
      component: PresentationEditor,
      props: {
        presentationId: selectedPresentationId.value,
      },
    }
  }
  if (activeSection.value === 'account') return Moncompte
  if (activeSection.value === 'clients-load') return ClientSpaceView

  const section = sections.find((item) => item.key === activeSection.value)
  return {
    component: SectionPlaceholder,
    props: {
      title: section?.label ?? 'Section',
      description: 'Contenu à définir pour cette section.',
    },
  }
})

onMounted(() => {
  checkAuth()
  restoreNavigation()
  loadNotifications()
  sendSessionHeartbeat().catch(() => {})
  notificationsTimer = window.setInterval(loadNotifications, 15000)
  heartbeatTimer = window.setInterval(() => {
    sendSessionHeartbeat().catch(() => {})
  }, 60000)
  window.addEventListener('storage', handleStorage)
})

onBeforeUnmount(() => {
  if (notificationsTimer) {
    window.clearInterval(notificationsTimer)
  }
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer)
  }
  window.removeEventListener('storage', handleStorage)
})

watch([activeSection, lastSection, selectedPresentationId, selectedTemplateFilename, isAuthenticated], persistNavigation, {
  immediate: true,
})

watch(isAuthenticated, (value) => {
  if (value) {
    loadNotifications()
    return
  }
  notifications.value = []
  unreadNotifications.value = 0
  showNotifications.value = false
})
</script>

<template>
  <Login v-if="!isAuthenticated" @login="handleLogin" />

  <div v-else class="min-h-screen bg-slate-25">
    <div class="flex min-h-screen bg-white lg:grid lg:grid-cols-[260px_1fr]">
      <!-- Mobile overlay behind the drawer -->
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
        @click="sidebarOpen = false"
      ></div>

      <aside
        class="fixed inset-y-0 left-0 z-40 flex w-72 max-w-[85vw] transform flex-col gap-8 overflow-y-auto border-r border-slate-200/70 bg-white px-6 py-8 pt-24 transition-transform duration-200 ease-in-out lg:static lg:z-auto lg:w-auto lg:max-w-none lg:translate-x-0 lg:gap-10 lg:pt-44"
        :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
      >
        <button
          type="button"
          class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500 lg:hidden"
          @click="sidebarOpen = false"
        >
          ✕
        </button>

        <div class="absolute left-0 top-0 flex items-center gap-3">
          <img src="/logo.png" alt="Logo" class="h-20 lg:h-40" />
        </div>

        <div class="relative">
          <button
            class="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm"
            @click="toggleNotifications"
          >
            <span>Notifications</span>
            <span
              class="rounded-full px-2 py-0.5 text-xs font-bold"
              :class="unreadNotifications ? 'bg-rose-500 text-white' : 'bg-slate-100 text-slate-500'"
            >
              {{ unreadNotifications }}
            </span>
          </button>

          <div
            v-if="showNotifications"
            class="absolute left-0 right-0 top-full z-20 mt-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl"
          >
            <div v-if="notifications.length" class="space-y-2">
              <button
                v-for="item in notifications.slice(0, 5)"
                :key="item.notification_id"
                type="button"
                class="block w-full rounded-xl px-3 py-2 text-left transition hover:bg-slate-100"
                :class="item.read_at ? 'bg-slate-50' : 'bg-rose-50'"
                @click="openNotification(item)"
              >
                <p class="text-xs font-semibold text-slate-800">{{ item.message }}</p>
                <p class="mt-1 text-[11px] text-slate-500">{{ item.filename || 'Présentation' }}</p>
              </button>
              <button
                v-if="notifications.length > 5"
                type="button"
                class="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-brand-600 transition hover:bg-slate-50"
                @click="openNotificationsModal"
              >
                Voir plus
              </button>
            </div>
            <p v-else class="text-sm text-slate-400">Aucune notification.</p>
          </div>
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

        <button
          class="mt-auto flex items-center justify-center gap-3 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white"
          @click="handleLogout"
        >
          Déconnexion
        </button>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col">
        <!-- Mobile top bar -->
        <header class="flex items-center justify-between border-b border-slate-200/70 bg-white px-4 py-3 lg:hidden">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-600"
            @click="sidebarOpen = true"
          >
            ☰
          </button>
          <img src="/logo.png" alt="Logo" class="h-8" />
          <div class="h-9 w-9"></div>
        </header>

        <main class="flex-1 bg-slate-25 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <component
            :is="activeComponent.component ?? activeComponent"
            v-bind="activeComponent.props ?? {}"
            :user="currentUser"
            @new-presentation="openNewPresentation"
            @open-editor="openPresentationEditor"
            @use-template="useTemplateFromLibrary"
            @logout="handleLogout"
            @back="goBack"
          />
        </main>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showNotificationsModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4 backdrop-blur-sm"
      >
        <div class="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-3xl bg-white shadow-2xl">
          <div class="flex items-center justify-between border-b border-slate-200 px-6 py-5">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">Toutes les notifications</h2>
              <p class="mt-1 text-sm text-slate-500">De la plus récente à la plus ancienne.</p>
            </div>
            <button
              type="button"
              class="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-600 hover:bg-slate-200"
              @click="showNotificationsModal = false"
            >
              Fermer
            </button>
          </div>

          <div class="overflow-y-auto px-6 py-5">
            <div v-if="notifications.length" class="space-y-3">
              <button
                v-for="item in notifications"
                :key="item.notification_id"
                type="button"
                class="block w-full rounded-2xl px-4 py-3 text-left transition hover:bg-slate-50"
                :class="item.read_at ? 'bg-slate-50' : 'bg-rose-50'"
                @click="openNotification(item)"
              >
                <p class="text-sm font-semibold text-slate-800">{{ item.message }}</p>
                <p class="mt-1 text-xs text-slate-500">{{ item.filename || 'Présentation' }}</p>
              </button>
            </div>
            <p v-else class="text-sm text-slate-400">Aucune notification.</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
