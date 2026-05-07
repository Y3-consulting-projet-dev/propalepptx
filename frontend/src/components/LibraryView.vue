<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { getTemplates } from '../api.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const emit = defineEmits(['use-template'])

function getSlidesUrl(filename, mode = 'images') {
  return `${API_BASE}/api/templates/${encodeURIComponent(filename)}/slides?mode=${mode}`
}

// ─── State ────────────────────────────────────────────────────────────────────
// const filters     = ['Tous', 'Audit', 'Stratégie', 'Rapports', 'Client']
const activeFilter= ref('Tous')
const cards       = ref([])
const searchQuery = ref('')
const error       = ref('')
const loading     = ref(true)

// Preview modal
const isOpen          = ref(false)
const activeCard      = ref(null)
const slides          = ref([])
const slideMode       = ref(null)
const currentSlide    = ref(0)
const previewLoading  = ref(false)
const previewError    = ref(null)
const fallbackAvailable = ref(false)

// Upload
const isDragging      = ref(false)
const uploading       = ref(false)
const uploadResults   = ref([])   // [{ filename, slide_count, error? }]
const showUploadToast = ref(false)
const fileInputRef    = ref(null)
let toastTimer        = null

// ─── Load templates ───────────────────────────────────────────────────────────
async function loadCards() {
  loading.value = true
  try {
    const data = await getTemplates({ scan: true })
    cards.value = (data.items || []).map((item, i) => ({
      id:       item.filename || String(i),
      title:    item.filename?.replace(/\.pptx$/i, '') || 'Modèle',
      filename: item.filename,
      slides:   item.slide_count ?? 0,
      lastUse:  'Il y a 2j',
      used:     23,
    }))
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCards()
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))

// ─── Upload logic ─────────────────────────────────────────────────────────────
function triggerFilePicker() {
  fileInputRef.value?.click()
}

function onFileInputChange(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) uploadFiles(files)
  e.target.value = ''   // reset so same file can be re-uploaded
}

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}
function onDragLeave() {
  isDragging.value = false
}
function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files || [])
  if (files.length) uploadFiles(files)
}

async function uploadFiles(files) {
  // Client-side filter: only .pptx
  const pptxFiles = files.filter(f => f.name.toLowerCase().endsWith('.pptx'))
  const rejected  = files.filter(f => !f.name.toLowerCase().endsWith('.pptx'))

  const results = rejected.map(f => ({ filename: f.name, error: 'Fichier non supporté (uniquement .pptx)' }))

  if (!pptxFiles.length) {
    uploadResults.value = results
    showToast()
    return
  }

  uploading.value = true
  const fd = new FormData()
  pptxFiles.forEach(f => fd.append('files', f))

  try {
    const res  = await fetch(`${API_BASE}/api/templates/upload`, { method: 'POST', body: fd })
    const data = await res.json()

    results.push(...(data.uploaded || []).map(u => ({ ...u, success: true })))
    results.push(...(data.errors   || []))
    uploadResults.value = results

    // Refresh the card list if at least one file succeeded
    if ((data.uploaded || []).length > 0) {
      await loadCards()
    }
  } catch (e) {
    uploadResults.value = [{ filename: 'Upload', error: e.message }]
  } finally {
    uploading.value = false
    showToast()
  }
}

function showToast() {
  showUploadToast.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { showUploadToast.value = false }, 4000)
}

// ─── Preview logic ────────────────────────────────────────────────────────────
async function fetchSlides(filename, mode = 'images') {
  previewLoading.value    = true
  previewError.value      = null
  fallbackAvailable.value = false
  slides.value            = []
  currentSlide.value      = 0

  try {
    const res  = await fetch(getSlidesUrl(filename, mode))
    const data = await res.json()
    if (!res.ok) {
      previewError.value = data.error || 'Erreur lors du chargement'
      if (data.fallback_url) fallbackAvailable.value = true
      return
    }
    slides.value    = data.slides || []
    slideMode.value = data.mode
  } catch {
    previewError.value = 'Impossible de contacter le serveur.'
  } finally {
    previewLoading.value = false
  }
}

function openPreview(card) {
  activeCard.value = card
  isOpen.value     = true
  fetchSlides(card.filename, 'images')
}
function closePreview() {
  isOpen.value     = false
  activeCard.value = null
  slides.value     = []
  previewError.value = null
}
function useFallback() {
  if (activeCard.value) fetchSlides(activeCard.value.filename, 'text')
}
function prev() { if (currentSlide.value > 0) currentSlide.value-- }
function next() { if (currentSlide.value < slides.value.length - 1) currentSlide.value++ }

function onKeyDown(e) {
  if (!isOpen.value) return
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft')  prev()
  if (e.key === 'Escape')     closePreview()
}

// ─── Filtered cards ───────────────────────────────────────────────────────────
function filteredCards() {
  return cards.value.filter(c =>
    c.title.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
}
</script>

<template>
  <section
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- ── Hidden file input ── -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".pptx"
      multiple
      class="hidden"
      @change="onFileInputChange"
    />

    <!-- ── Drag overlay ── -->
    <Teleport to="body">
      <div
        v-if="isDragging"
        class="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-brand-500/20 backdrop-blur-sm"
      >
        <div class="flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-brand-500 bg-white px-16 py-12 shadow-2xl">
          <svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" class="text-brand-500">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <p class="text-base font-semibold text-brand-600">Déposer les fichiers .pptx ici</p>
        </div>
      </div>
    </Teleport>

    <!-- ── Upload toast ── -->
    <Teleport to="body">
      <div
        v-if="showUploadToast"
        class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 rounded-xl bg-white px-5 py-4 shadow-2xl border border-slate-100 min-w-64"
      >
        <p class="text-sm font-semibold text-slate-800 mb-1">Résultat de l'import</p>
        <div v-for="r in uploadResults" :key="r.filename" class="flex items-start gap-2 text-xs">
          <span v-if="r.success" class="mt-0.5 flex-shrink-0 text-green-500">✓</span>
          <span v-else class="mt-0.5 flex-shrink-0 text-red-400">✕</span>
          <div>
            <p class="font-medium" :class="r.success ? 'text-slate-700' : 'text-red-600'">
              {{ r.filename }}
            </p>
            <p v-if="r.success" class="text-slate-400">{{ r.slide_count }} slides ajoutées</p>
            <p v-else class="text-red-400">{{ r.error }}</p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Header ── -->
    <header class="flex items-start justify-between">
      <p class="text-3xl font-semibold text-brand-600">Mes modèles</p>
      <div class="flex items-center gap-3">

        <!-- Import button -->
        <button
          class="flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
          :disabled="uploading"
          @click="triggerFilePicker"
        >
          <template v-if="uploading">
            <span class="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
            Import en cours…
          </template>
          <template v-else>
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Importer un modèle
          </template>
        </button>

        <button class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white">
          Créer un modèle
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
      <!-- <div class="flex flex-wrap items-center gap-3">
        <button
          v-for="item in filters"
          :key="item"
          class="rounded-full px-5 py-2 text-sm font-semibold transition"
          :class="activeFilter === item
            ? 'bg-brand-500 text-white'
            : 'bg-white text-slate-700 border border-slate-200 hover:border-brand-300'"
          @click="activeFilter = item"
        >
          {{ item }}
          <span v-if="item === 'Tous'" class="ml-1 text-xs opacity-70">({{ cards.length }})</span>
        </button>
      </div> -->
    </div>

    <!-- ── Cards ── -->
    <div v-if="loading" class="mt-10 text-sm text-slate-500">Chargement...</div>
    <div v-else-if="error" class="mt-10 text-sm text-red-600">{{ error }}</div>

    <div v-else class="mt-8 grid gap-6 lg:grid-cols-3">
      <article
        v-for="card in filteredCards()"
        :key="card.id"
        class="card flex flex-col overflow-hidden"
      >
        <div class="px-5 py-4">
          <p class="text-sm font-semibold text-slate-900">{{ card.title }}</p>
          <p class="mt-1 text-xs text-slate-500">
            {{ card.slides }} slides — Dernière utilisation : {{ card.lastUse }}
          </p>
          <p class="mt-2 text-xs text-slate-500">Utilisé {{ card.used }} fois</p>
        </div>
        <div class="mt-auto border-t border-slate-100 px-5 py-4">
          <div class="flex items-center justify-between">
            <button
              class="rounded-full bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white"
              @click="emit('use-template', card.filename)"
            >
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

      <!-- Import drop zone card -->
      <div
        class="card flex cursor-pointer items-center justify-center bg-slate-700 text-white transition hover:bg-slate-600"
        :class="isDragging ? 'ring-2 ring-brand-400 ring-offset-2' : ''"
        @click="triggerFilePicker"
      >
        <div class="flex flex-col items-center gap-3 py-12">
          <div
            class="flex h-12 w-12 items-center justify-center rounded-full border border-white/40 text-2xl transition"
            :class="uploading ? 'animate-pulse' : ''"
          >
            <template v-if="uploading">
              <span class="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white inline-block"></span>
            </template>
            <template v-else>+</template>
          </div>
          <p class="text-sm font-semibold">Importer un modèle</p>
          <p class="text-xs text-white/70">Cliquer ou glisser un fichier .pptx</p>
        </div>
      </div>
    </div>

    <!-- ── Preview Modal ── -->
    <Teleport to="body">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="closePreview" />
        <div
          class="relative flex w-[1000px] max-w-[95vw] flex-col rounded-2xl bg-white shadow-2xl overflow-hidden"
          style="max-height: 90vh;"
        >
          <!-- Header -->
          <div class="flex flex-shrink-0 items-center justify-between border-b border-slate-100 px-6 py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4" stroke-linecap="round"/>
                </svg>
              </div>
              <div>
                <p class="text-sm font-semibold text-slate-900">{{ activeCard?.title }}</p>
                <p class="flex items-center gap-2 text-xs text-slate-400">
                  <template v-if="previewLoading">Génération des aperçus…</template>
                  <template v-else-if="slides.length">
                    {{ slides.length }} diapositive{{ slides.length > 1 ? 's' : '' }}
                    <span v-if="slideMode === 'text'"
                          class="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700 font-semibold">mode texte</span>
                  </template>
                </p>
              </div>
            </div>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-500 hover:bg-slate-100"
              @click="closePreview"
            >✕</button>
          </div>

          <!-- Body -->
          <div class="flex flex-1 flex-col overflow-hidden">
            <div v-if="previewLoading" class="flex flex-1 flex-col items-center justify-center gap-3 py-16">
              <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-brand-500"></div>
              <p class="text-sm text-slate-500">Conversion des slides en cours…</p>
            </div>

            <div v-else-if="previewError" class="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-12">
              <div class="max-w-md rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
                <p class="mb-2 font-semibold text-slate-800">Aperçu indisponible</p>
                <p class="mb-4 rounded bg-white p-3 text-left font-mono text-xs text-slate-500">{{ previewError }}</p>
                <button v-if="fallbackAvailable"
                        class="rounded-full bg-amber-500 px-5 py-2 text-sm font-semibold text-white"
                        @click="useFallback">
                  Utiliser l'aperçu texte
                </button>
              </div>
            </div>

            <template v-else-if="slides.length">
              <div class="flex flex-1 items-center justify-center gap-4 overflow-hidden px-4 py-4 min-h-0">
                <button class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:opacity-20"
                        :disabled="currentSlide === 0" @click="prev">
                  <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <path d="M15 18l-6-6 6-6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>

                <div class="relative flex min-h-0 flex-1 items-center justify-center">
                  <img v-if="slideMode === 'images'" :key="currentSlide"
                       :src="`data:image/png;base64,${slides[currentSlide]}`"
                       :alt="`Slide ${currentSlide + 1}`"
                       class="max-h-full max-w-full rounded-lg object-contain shadow-md"
                       style="max-height: calc(90vh - 240px)" />
                  <div v-else class="flex w-full max-w-2xl flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-slate-50 p-10 text-center" style="min-height:360px">
                    <img v-if="slides[currentSlide]?.image" :src="`data:image/jpeg;base64,${slides[currentSlide].image}`" class="max-h-40 max-w-full rounded object-contain" alt="" />
                    <p v-if="slides[currentSlide]?.title" class="text-xl font-bold text-slate-800">{{ slides[currentSlide].title }}</p>
                    <p v-if="slides[currentSlide]?.text" class="whitespace-pre-line text-sm leading-relaxed text-slate-600">{{ slides[currentSlide].text }}</p>
                    <p v-if="!slides[currentSlide]?.title && !slides[currentSlide]?.text && !slides[currentSlide]?.image" class="italic text-slate-400">Diapositive vide</p>
                  </div>
                  <div class="absolute bottom-2 right-2 rounded-full bg-black/50 px-2.5 py-0.5 text-xs font-semibold text-white">
                    {{ currentSlide + 1 }} / {{ slides.length }}
                  </div>
                </div>

                <button class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:opacity-20"
                        :disabled="currentSlide === slides.value?.length - 1" @click="next">
                  <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>

              <!-- Filmstrip -->
              <div class="flex gap-2 overflow-x-auto border-t border-slate-100 px-4 py-3 flex-shrink-0">
                <button v-for="(slide, i) in slides" :key="i"
                        class="relative flex-shrink-0 overflow-hidden rounded-md border-2 transition-all"
                        :class="i === currentSlide ? 'border-brand-500 shadow-md shadow-brand-100' : 'border-transparent hover:border-slate-300'"
                        style="width:88px" @click="currentSlide = i">
                  <img v-if="slideMode === 'images'" :src="`data:image/png;base64,${slide}`"
                       class="block w-full" style="aspect-ratio:16/9;object-fit:cover" />
                  <div v-else class="flex flex-col items-center justify-center bg-slate-100 text-center" style="aspect-ratio:16/9">
                    <span class="text-xs font-bold text-slate-400">{{ i + 1 }}</span>
                    <span v-if="slide.title" class="mt-0.5 line-clamp-2 px-1 text-[9px] leading-tight text-slate-600">{{ slide.title }}</span>
                  </div>
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
