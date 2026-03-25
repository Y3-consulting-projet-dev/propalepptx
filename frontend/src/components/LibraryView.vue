<script setup>
import { onMounted, ref, watch } from 'vue'
import { getTemplates } from '../api.js'

// ─── Config ──────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function getSlidesUrl(filename, mode = 'images') {
  return `${API_BASE}/api/templates/${encodeURIComponent(filename)}/slides?mode=${mode}`
}

// ─── State ───────────────────────────────────────────────────────────────────
const filters = ['Tous(9)', 'Audit(3)', 'Stratégie(2)', 'Rapports(2)', 'Client(2)']
const cards = ref([])
const searchQuery = ref('')
const error = ref('')
const loading = ref(true)

const isOpen = ref(false)
const activeCard = ref(null)

// Preview state
const slides = ref([])
const slideMode = ref(null)
const currentSlide = ref(0)
const previewLoading = ref(false)
const previewError = ref(null)
const fallbackAvailable = ref(false)

// ─── Load templates ───────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await getTemplates({ scan: true })
    cards.value = (data.items || []).map((item, index) => ({
      id: item.filename || String(index),
      title: item.filename?.replace(/\.pptx$/i, '') || 'Modèle',
      filename: item.filename,
      slides: item.slide_count ?? 0,
      lastUse: 'Il y a 2j',
      used: 23,
    }))
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

// ─── Preview logic ────────────────────────────────────────────────────────────
async function fetchSlides(filename, mode = 'images') {
  previewLoading.value = true
  previewError.value = null
  fallbackAvailable.value = false
  slides.value = []
  currentSlide.value = 0

  try {
    const res = await fetch(getSlidesUrl(filename, mode))
    const data = await res.json()

    if (!res.ok) {
      previewError.value = data.error || 'Erreur lors du chargement'
      if (data.fallback_url) fallbackAvailable.value = true
      return
    }

    slides.value = data.slides || []
    slideMode.value = data.mode
  } catch {
    previewError.value = 'Impossible de contacter le serveur.'
  } finally {
    previewLoading.value = false
  }
}

function openPreview(card) {
  activeCard.value = card
  isOpen.value = true
  fetchSlides(card.filename, 'images')
}

function closePreview() {
  isOpen.value = false
  activeCard.value = null
  slides.value = []
  previewError.value = null
}

function useFallback() {
  if (activeCard.value) fetchSlides(activeCard.value.filename, 'text')
}

function prev() { if (currentSlide.value > 0) currentSlide.value-- }
function next() { if (currentSlide.value < slides.value.length - 1) currentSlide.value++ }

// Keyboard navigation
function onKeyDown(e) {
  if (!isOpen.value) return
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'Escape') closePreview()
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
</script>

<template>
  <section>
    <!-- ── Header ── -->
    <header class="flex items-start justify-between">
      <div>
        <p class="text-3xl font-semibold text-brand-600">Mes modèles</p>
      </div>
      <div class="flex items-center gap-3">
        <button class="h-10 w-10 rounded-full border border-slate-200 bg-white text-slate-600">🔔</button>
        <button class="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white">
          Importer un model
        </button>
        <button class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white">
          Créer un model
        </button>
      </div>
    </header>

    <!-- ── Filters ── -->
    <div class="mt-8 flex flex-wrap items-center gap-4">
      <div class="flex items-center rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher"
          class="w-48 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
        />
        <span class="text-slate-400">⌕</span>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <button
          v-for="item in filters"
          :key="item"
          class="rounded-full px-5 py-2 text-sm font-semibold"
          :class="item.startsWith('Tous') ? 'bg-brand-500 text-white' : 'bg-white text-slate-700 border border-slate-200'"
        >
          {{ item }}
        </button>
      </div>
    </div>

    <!-- ── Cards ── -->
    <div v-if="loading" class="mt-10 text-sm text-slate-500">Chargement...</div>
    <div v-else-if="error" class="mt-10 text-sm text-red-600">{{ error }}</div>

    <div v-else class="mt-8 grid gap-6 lg:grid-cols-3">
      <!-- ✅ CORRECTION : ajout de flex flex-col -->
      <article
        v-for="card in cards.filter((c) =>
          c.title.toLowerCase().includes(searchQuery.toLowerCase())
        )"
        :key="card.id"
        class="card overflow-hidden flex flex-col"
      >
        <div class="px-5 py-4">
          <p class="text-sm font-semibold text-slate-900">{{ card.title }}</p>
          <p class="mt-1 text-xs text-slate-500">
            {{ card.slides }} slides — Dernière utilisation : {{ card.lastUse }}
          </p>
          <p class="mt-2 text-xs text-slate-500">Utilisé {{ card.used }} fois</p>
        </div>
        <!-- ✅ CORRECTION : ajout de mt-auto pour coller le footer en bas -->
        <div class="border-t border-slate-100 px-5 py-4 mt-auto">
          <div class="flex items-center justify-between">
            <button class="rounded-full bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white">
              Utiliser
            </button>
            <button
              class="rounded-full bg-brand-50 px-4 py-1.5 text-xs font-semibold text-slate-700"
              @click="openPreview(card)"
            >
              Aperçu
            </button>
          </div>
        </div>
      </article>

      <!-- Import card -->
      <div class="card flex items-center justify-center bg-slate-700 text-white">
        <div class="flex flex-col items-center gap-3 py-12">
          <div class="flex h-12 w-12 items-center justify-center rounded-full border border-white/40 text-2xl">+</div>
          <p class="text-sm font-semibold">Importer un modèle</p>
          <p class="text-xs text-white/70">Glissez un fichier .pptx</p>
        </div>
      </div>
    </div>

    <!-- ── Preview Modal ── -->
    <Teleport to="body">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">

        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="closePreview" />

        <!-- Modal -->
        <div class="relative flex w-[1000px] max-w-[95vw] flex-col rounded-2xl bg-white shadow-2xl overflow-hidden"
             style="max-height: 90vh;">

          <!-- Modal header -->
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4 flex-shrink-0">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4" stroke-linecap="round"/>
                </svg>
              </div>
              <div>
                <p class="text-sm font-semibold text-slate-900">{{ activeCard?.title }}</p>
                <p class="text-xs text-slate-400 flex items-center gap-2">
                  <template v-if="previewLoading">Génération des aperçus…</template>
                  <template v-else-if="slides.length">
                    {{ slides.length }} diapositive{{ slides.length > 1 ? 's' : '' }}
                    <span v-if="slideMode === 'text'"
                          class="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700 font-semibold">
                      mode texte
                    </span>
                  </template>
                </p>
              </div>
            </div>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-500 hover:bg-slate-100"
              @click="closePreview"
            >✕</button>
          </div>

          <!-- Modal body -->
          <div class="flex flex-1 flex-col overflow-hidden">

            <!-- Loading state -->
            <div v-if="previewLoading" class="flex flex-1 flex-col items-center justify-center gap-3 py-16">
              <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-brand-500"></div>
              <p class="text-sm text-slate-500">Conversion des slides en cours…</p>
            </div>

            <!-- Error state -->
            <div v-else-if="previewError" class="flex flex-1 flex-col items-center justify-center gap-4 py-12 px-6">
              <div class="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center max-w-md">
                <p class="font-semibold text-slate-800 mb-2">Aperçu indisponible</p>
                <p class="text-xs text-slate-500 font-mono bg-white rounded p-3 text-left mb-4">{{ previewError }}</p>
                <button
                  v-if="fallbackAvailable"
                  class="rounded-full bg-amber-500 px-5 py-2 text-sm font-semibold text-white"
                  @click="useFallback"
                >
                  Utiliser l'aperçu texte
                </button>
              </div>
            </div>

            <!-- Slides view -->
            <template v-else-if="slides.length">

              <!-- Main slide -->
              <div class="flex flex-1 items-center justify-center gap-4 px-4 py-4 overflow-hidden min-h-0">

                <!-- Prev button -->
                <button
                  class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:opacity-20"
                  :disabled="currentSlide === 0"
                  @click="prev"
                >
                  <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <path d="M15 18l-6-6 6-6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>

                <!-- Slide image or text -->
                <div class="relative flex min-h-0 flex-1 items-center justify-center">

                  <!-- Image mode -->
                  <img
                    v-if="slideMode === 'images'"
                    :key="currentSlide"
                    :src="`data:image/png;base64,${slides[currentSlide]}`"
                    :alt="`Slide ${currentSlide + 1}`"
                    class="max-h-full max-w-full rounded-lg object-contain shadow-md"
                    style="max-height: calc(90vh - 240px)"
                  />

                  <!-- Text / fallback mode -->
                  <div
                    v-else
                    class="flex w-full max-w-2xl flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-slate-50 p-10 text-center"
                    style="min-height: 360px;"
                  >
                    <img
                      v-if="slides[currentSlide]?.image"
                      :src="`data:image/jpeg;base64,${slides[currentSlide].image}`"
                      class="max-h-40 max-w-full rounded object-contain"
                      alt=""
                    />
                    <p v-if="slides[currentSlide]?.title" class="text-xl font-bold text-slate-800">
                      {{ slides[currentSlide].title }}
                    </p>
                    <p v-if="slides[currentSlide]?.text" class="text-sm leading-relaxed text-slate-600 whitespace-pre-line">
                      {{ slides[currentSlide].text }}
                    </p>
                    <p v-if="!slides[currentSlide]?.title && !slides[currentSlide]?.text && !slides[currentSlide]?.image"
                       class="italic text-slate-400">
                      Diapositive vide
                    </p>
                  </div>

                  <!-- Slide counter badge -->
                  <div class="absolute bottom-2 right-2 rounded-full bg-black/50 px-2.5 py-0.5 text-xs font-semibold text-white">
                    {{ currentSlide + 1 }} / {{ slides.length }}
                  </div>
                </div>

                <!-- Next button -->
                <button
                  class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:opacity-20"
                  :disabled="currentSlide === slides.length - 1"
                  @click="next"
                >
                  <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>

              <!-- Filmstrip -->
              <div class="flex gap-2 overflow-x-auto border-t border-slate-100 px-4 py-3 flex-shrink-0">
                <button
                  v-for="(slide, i) in slides"
                  :key="i"
                  class="relative flex-shrink-0 overflow-hidden rounded-md border-2 transition-all"
                  :class="i === currentSlide
                    ? 'border-brand-500 shadow-md shadow-brand-100'
                    : 'border-transparent hover:border-slate-300'"
                  style="width: 88px;"
                  @click="currentSlide = i"
                >
                  <!-- Image thumbnail -->
                  <img
                    v-if="slideMode === 'images'"
                    :src="`data:image/png;base64,${slide}`"
                    :alt="`Miniature ${i + 1}`"
                    class="block w-full"
                    style="aspect-ratio: 16/9; object-fit: cover;"
                  />
                  <!-- Text thumbnail -->
                  <div
                    v-else
                    class="flex flex-col items-center justify-center bg-slate-100 text-center"
                    style="aspect-ratio: 16/9;"
                  >
                    <span class="text-xs font-bold text-slate-400">{{ i + 1 }}</span>
                    <span v-if="slide.title" class="mt-0.5 line-clamp-2 px-1 text-[9px] leading-tight text-slate-600">
                      {{ slide.title }}
                    </span>
                  </div>

                  <!-- Active indicator -->
                  <div v-if="i === currentSlide" class="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500" />
                </button>
              </div>

            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>
