<script setup>
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const router = useRoute()
const $router = useRouter()

// ─── State ────────────────────────────────────────────────────────────────────
const presId       = router.params.id
const presentation = ref(null)
const slides       = ref([])           // base64 PNG strings
const slideMode    = ref('images')
const currentIdx   = ref(0)
const loading      = ref(true)
const slidesLoading= ref(true)
const error        = ref(null)

// Edit mode
const editing       = ref(false)
const editShapes    = ref([])          // shapes of current slide for editing
const saving        = ref(false)

// Submit modal
const showSubmitModal = ref(false)
const submitting      = ref(false)
const submitted       = ref(false)

// Download
const downloading = ref(false)

// ─── Load presentation metadata ───────────────────────────────────────────────
async function loadPresentation() {
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur')
    presentation.value = data
    submitted.value = data.status === 'submitted'
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ─── Load slide images ────────────────────────────────────────────────────────
async function loadSlides(mode = 'images') {
  slidesLoading.value = true
  slides.value = []
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}/slides?mode=${mode}`)
    const data = await res.json()
    if (!res.ok) {
      if (data.fallback_url) {
        await loadSlides('text')
        return
      }
      throw new Error(data.error)
    }
    slides.value  = data.slides || []
    slideMode.value = data.mode
  } catch (e) {
    error.value = e.message
  } finally {
    slidesLoading.value = false
  }
}

// ─── Load editable shapes for current slide ───────────────────────────────────
async function loadEditShapes() {
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}/slides?mode=text`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error)
    // text mode returns slide objects with title/text — we need shapes
    // We'll use the text slide data as editable content
    const slideData = (data.slides || [])[currentIdx.value]
    editShapes.value = slideData ? [
      { shape_id: 0, label: 'Titre', value: slideData.title || '' },
      { shape_id: 1, label: 'Contenu', value: slideData.text || '' },
    ] : []
  } catch (e) {
    console.error(e)
  }
}

// ─── Save edited shapes ───────────────────────────────────────────────────────
async function saveEdits() {
  saving.value = true
  try {
    await fetch(`${API_BASE}/api/presentations/${presId}/slide/${currentIdx.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shapes: editShapes.value.map(s => ({
          shape_id: s.shape_id,
          texts: s.value.split('\n'),
        })),
      }),
    })
    editing.value = false
    // Reload slide images
    await loadSlides('images')
  } catch (e) {
    alert('Erreur lors de la sauvegarde : ' + e.message)
  } finally {
    saving.value = false
  }
}

// ─── Navigation ───────────────────────────────────────────────────────────────
function goTo(idx) {
  if (idx < 0 || idx >= slides.value.length) return
  currentIdx.value = idx
  editing.value    = false
}

function onKeyDown(e) {
  if (editing.value) return
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown')  goTo(currentIdx.value + 1)
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')    goTo(currentIdx.value - 1)
}

// ─── Submit ───────────────────────────────────────────────────────────────────
async function submitToAssociate() {
  submitting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/submit`, { method: 'POST' })
    if (!res.ok) throw new Error('Erreur lors de la soumission')
    submitted.value      = true
    showSubmitModal.value = false
  } catch (e) {
    alert(e.message)
  } finally {
    submitting.value = false
  }
}

// ─── Download ─────────────────────────────────────────────────────────────────
async function downloadPptx() {
  downloading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/download`)
    if (!res.ok) throw new Error('Téléchargement échoué')
    const blob     = await res.blob()
    const url      = URL.createObjectURL(blob)
    const a        = document.createElement('a')
    const filename = res.headers.get('Content-Disposition')?.match(/filename="?([^"]+)"?/)?.[1]
                     || 'presentation.pptx'
    a.href         = url
    a.download     = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.message)
  } finally {
    downloading.value = false
  }
}

// ─── Computed ─────────────────────────────────────────────────────────────────
const currentSlide = computed(() => slides.value[currentIdx.value])
const totalSlides  = computed(() => slides.value.length)
const clientName   = computed(() => presentation.value?.form?.clientName || 'Présentation')
const presFilename = computed(() => presentation.value?.filename || '')

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  window.addEventListener('keydown', onKeyDown)
  await loadPresentation()
  await loadSlides('images')
})
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <div class="flex h-screen flex-col bg-slate-100 font-sans">

    <!-- ── Top bar ── -->
    <header class="flex h-12 flex-shrink-0 items-center justify-between bg-brand-500 px-4 shadow">

      <!-- Left: back + menu -->
      <div class="flex items-center gap-6">
        <button
          class="flex items-center gap-1.5 text-xs font-semibold text-white/80 hover:text-white"
          @click="$router.back()"
        >
          <span class="text-base">←</span> Retour
        </button>
        <nav class="hidden items-center gap-5 sm:flex">
          <button v-for="item in ['Fichier','Édition','Insertion','IA']" :key="item"
                  class="text-xs font-semibold text-white/90 hover:text-white">
            {{ item }}
          </button>
        </nav>
      </div>

      <!-- Center: filename -->
      <span class="hidden truncate text-xs font-semibold text-white sm:block max-w-xs" :title="presFilename">
        {{ presFilename }}
      </span>

      <!-- Right: actions -->
      <div class="flex items-center gap-2">
        <!-- Download -->
        <button
          class="flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20 disabled:opacity-50"
          :disabled="downloading"
          @click="downloadPptx"
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ downloading ? 'Export…' : 'Télécharger' }}
        </button>

        <!-- Submit -->
        <button
          v-if="!submitted"
          class="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
          @click="showSubmitModal = true"
        >
          Soumettre à l'associé
        </button>
        <span v-else class="rounded-lg bg-green-700 px-4 py-1.5 text-xs font-semibold text-white">
          ✓ Soumis
        </span>
      </div>
    </header>

    <!-- ── Main area ── -->
    <div class="flex flex-1 overflow-hidden">

      <!-- ── Filmstrip (left sidebar) ── -->
      <aside class="flex w-44 flex-shrink-0 flex-col gap-0 overflow-y-auto border-r border-slate-200 bg-white py-3">
        <template v-if="slidesLoading">
          <div v-for="n in 6" :key="n"
               class="mx-3 mb-3 animate-pulse rounded bg-slate-200"
               style="aspect-ratio:16/9"></div>
        </template>
        <template v-else>
          <button
            v-for="(slide, i) in slides"
            :key="i"
            class="group relative mx-3 mb-3 flex-shrink-0 overflow-hidden rounded border-2 text-left transition-all"
            :class="i === currentIdx
              ? 'border-brand-500 shadow-md shadow-brand-100'
              : 'border-transparent hover:border-slate-300'"
            @click="goTo(i)"
          >
            <!-- Slide number -->
            <span class="absolute left-1 top-1 z-10 text-[10px] font-bold leading-none"
                  :class="i === currentIdx ? 'text-brand-600' : 'text-slate-400'">
              {{ i + 1 }}
            </span>

            <!-- Image thumbnail (image mode) -->
            <img
              v-if="slideMode === 'images'"
              :src="`data:image/png;base64,${slide}`"
              :alt="`Slide ${i+1}`"
              style="aspect-ratio:16/9; object-fit:cover"
              class="block w-full"
            />

            <!-- Text thumbnail (fallback mode) -->
            <div
              v-else
              class="flex flex-col items-center justify-center bg-slate-50 p-2 text-center"
              style="aspect-ratio:16/9"
            >
              <span class="line-clamp-3 text-[9px] leading-tight text-slate-600">
                {{ slide.title || `Slide ${i+1}` }}
              </span>
            </div>

            <!-- Active indicator bar -->
            <div v-if="i === currentIdx"
                 class="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500"></div>
          </button>
        </template>
      </aside>

      <!-- ── Central view ── -->
      <main class="flex flex-1 flex-col items-center justify-center overflow-auto bg-slate-200 p-6 gap-4">

        <!-- Error state -->
        <div v-if="error" class="rounded-xl bg-white p-8 text-center shadow">
          <p class="font-semibold text-slate-800">Erreur</p>
          <p class="mt-2 text-sm text-slate-500">{{ error }}</p>
        </div>

        <!-- Loading state -->
        <div v-else-if="slidesLoading" class="flex flex-col items-center gap-3">
          <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-300 border-t-brand-500"></div>
          <p class="text-sm text-slate-500">Chargement des slides…</p>
        </div>

        <!-- Slide view -->
        <template v-else-if="slides.length">

          <!-- Nav + slide -->
          <div class="flex w-full max-w-4xl items-center gap-4">
            <!-- Prev -->
            <button
              class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-white shadow transition hover:bg-slate-50 disabled:opacity-20"
              :disabled="currentIdx === 0"
              @click="goTo(currentIdx - 1)"
            >
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>

            <!-- Slide display -->
            <div class="relative flex-1">
              <!-- Image mode -->
              <img
                v-if="slideMode === 'images' && !editing"
                :key="currentIdx"
                :src="`data:image/png;base64,${currentSlide}`"
                :alt="`Slide ${currentIdx+1}`"
                class="w-full rounded-lg shadow-xl"
                style="aspect-ratio:16/9; object-fit:contain; background:#fff"
              />

              <!-- Text/edit mode -->
              <div
                v-else
                class="flex w-full flex-col gap-4 rounded-lg bg-white p-8 shadow-xl"
                style="aspect-ratio:16/9; overflow:auto"
              >
                <div v-for="shape in editShapes" :key="shape.shape_id" class="flex flex-col gap-1">
                  <label class="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {{ shape.label }}
                  </label>
                  <textarea
                    v-model="shape.value"
                    rows="3"
                    class="w-full resize-none rounded-lg border border-brand-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none"
                  />
                </div>
              </div>

              <!-- Counter badge -->
              <div class="absolute bottom-3 right-3 rounded-full bg-black/50 px-2.5 py-0.5 text-xs font-semibold text-white">
                {{ currentIdx + 1 }} / {{ totalSlides }}
              </div>
            </div>

            <!-- Next -->
            <button
              class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-white shadow transition hover:bg-slate-50 disabled:opacity-20"
              :disabled="currentIdx === slides.length - 1"
              @click="goTo(currentIdx + 1)"
            >
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

          <!-- Action bar below slide -->
          <div class="flex items-center gap-3">
            <!-- Edit / Save / Cancel -->
            <template v-if="!editing">
              <button
                class="flex items-center gap-1.5 rounded-lg bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow hover:bg-slate-50"
                @click="editing = true; loadEditShapes()"
              >
                <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke-linecap="round"/>
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke-linecap="round"/>
                </svg>
                Modifier cette slide
              </button>
            </template>
            <template v-else>
              <button
                class="rounded-lg bg-brand-500 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-brand-600 disabled:opacity-50"
                :disabled="saving"
                @click="saveEdits"
              >
                {{ saving ? 'Sauvegarde…' : 'Enregistrer' }}
              </button>
              <button
                class="rounded-lg bg-white px-4 py-2 text-xs font-semibold text-slate-600 shadow hover:bg-slate-50"
                @click="editing = false"
              >
                Annuler
              </button>
            </template>
          </div>
        </template>
      </main>
    </div>

    <!-- ── Submit confirmation modal ── -->
    <Teleport to="body">
      <div v-if="showSubmitModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
        <div class="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
          <h2 class="text-lg font-semibold text-slate-900">Soumettre à l'associé</h2>
          <p class="mt-3 text-sm text-slate-600">
            La présentation <strong>{{ clientName }}</strong> sera transmise à l'associé responsable pour validation.
            Cette action ne peut pas être annulée.
          </p>
          <div class="mt-6 flex justify-end gap-3">
            <button
              class="rounded-xl border border-slate-200 bg-white px-5 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              @click="showSubmitModal = false"
            >
              Annuler
            </button>
            <button
              class="rounded-xl bg-slate-900 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              :disabled="submitting"
              @click="submitToAssociate"
            >
              {{ submitting ? 'Envoi…' : 'Confirmer la soumission' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>