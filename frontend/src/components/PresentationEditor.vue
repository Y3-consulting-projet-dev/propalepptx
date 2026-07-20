<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { getAuthHeaders, getCurrentUser } from '../api.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const props = defineProps({
  presentationId: {
    type: String,
    required: true,
  },
})
const emit = defineEmits(['back'])

//â”€ State
const presId       = props.presentationId
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
const successMessage  = ref('')

// Download
const downloading = ref(false)
const renameDraft = ref('')
const renaming = ref(false)
const commentDraft = ref('')
const commentSaving = ref(false)
const returningForCorrections = ref(false)
const validating = ref(false)
const currentUser = getCurrentUser()

//â”€ Load presentation metadataâ”€
async function loadPresentation() {
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}`, {
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur')
    presentation.value = data
    renameDraft.value = String(data.filename || '').replace(/\.pptx$/i, '')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

//â”€ Load slide images
async function loadSlides(mode = 'images') {
  slidesLoading.value = true
  slides.value = []
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}/slides?mode=${mode}`, {
      headers: getAuthHeaders(),
    })
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

//â”€ Load editable shapes for current slideâ”€
async function loadEditShapes() {
  try {
    const res  = await fetch(`${API_BASE}/api/presentations/${presId}/slides/${currentIdx.value}/shapes`, {
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error)
    // text mode returns slide objects with title/text â€” we need shapes
    // We'll use the text slide data as editable content
    editShapes.value = (data.shapes || []).map((shape, index) => ({
      shape_id: shape.shape_id,
      label: shape.shape_name || `Bloc ${index + 1}`,
      value: (shape.texts || []).join('\n'),
    }))
  } catch (e) {
    console.error(e)
  }
}

//â”€ Save edited shapesâ”€
async function saveEdits() {
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/slide/${currentIdx.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        shapes: editShapes.value.map(s => ({
          shape_id: s.shape_id,
          texts: s.value.split('\n'),
        })),
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors de la sauvegarde')
    editing.value = false
    // Reload slide images
    await loadSlides('images')
  } catch (e) {
    alert('Erreur lors de la sauvegarde : ' + e.message)
  } finally {
    saving.value = false
  }
}

//â”€ Navigationâ”€
async function savePresentationName() {
  const cleanName = String(renameDraft.value || '').trim()
  if (!cleanName) {
    alert('Le nom du document est requis')
    return
  }

  renaming.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ filename: cleanName }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors du renommage')

    const finalFilename = String(data.filename || `${cleanName}.pptx`)
    renameDraft.value = finalFilename.replace(/\.pptx$/i, '')
    if (presentation.value) {
      presentation.value = { ...presentation.value, filename: finalFilename }
    }
  } catch (e) {
    alert(e.message)
  } finally {
    renaming.value = false
  }
}

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

function showSuccess(message) {
  successMessage.value = message
  window.setTimeout(() => {
    if (successMessage.value === message) {
      successMessage.value = ''
    }
  }, 3000)
}

//â”€ Submitâ”€
async function submitToAssociate() {
  submitting.value = true
  try {
    const shouldReturnToListAfterSubmit =
      presentation.value?.is_owner !== true && presentation.value?.is_reviewer === true
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/submit`, {
      method: 'POST',
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors de la soumission')
    showSubmitModal.value = false
    showSuccess('Présentation soumise avec succès.')
    if (shouldReturnToListAfterSubmit) {
      emit('back')
      return
    }
    await loadPresentation()
  } catch (e) {
    alert(e.message)
  } finally {
    submitting.value = false
  }
}

async function addComment() {
  const text = String(commentDraft.value || '').trim()
  if (!text) return

  commentSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        slide_index: currentIdx.value,
        text,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors de l’ajout du commentaire')

    const comments = Array.isArray(presentation.value?.slide_comments)
      ? [...presentation.value.slide_comments, data.comment]
      : [data.comment]

    if (presentation.value) {
      presentation.value = {
        ...presentation.value,
        slide_comments: comments,
      }
    }
    commentDraft.value = ''
    showSuccess('Commentaire ajouté.')
  } catch (e) {
    alert(e.message)
  } finally {
    commentSaving.value = false
  }
}

async function returnToAssistantForCorrections() {
  returningForCorrections.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/return`, {
      method: 'POST',
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors du renvoi pour correction')
    showSuccess('Présentation renvoyée pour correction.')
    emit('back')
  } catch (e) {
    alert(e.message)
  } finally {
    returningForCorrections.value = false
  }
}

async function validatePresentation() {
  validating.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/validate`, {
      method: 'POST',
      headers: getAuthHeaders(),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Erreur lors de la validation')
    showSuccess('Présentation validée avec succès.')
    emit('back')
  } catch (e) {
    alert(e.message)
  } finally {
    validating.value = false
  }
}

//â”€ Downloadâ”€
async function downloadPptx() {
  downloading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/download`, {
      headers: getAuthHeaders(),
    })
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

//â”€ Computedâ”€
const currentSlide = computed(() => slides.value[currentIdx.value])
const totalSlides  = computed(() => slides.value.length)
const clientName   = computed(() => presentation.value?.form?.clientName || 'Présentation')
const presFilename = computed(() => presentation.value?.filename || '')
const submitActionLabel = computed(() => presentation.value?.submit_action_label || "Soumettre Ã  l'associé")
const currentReviewerName = computed(() => presentation.value?.next_reviewer_name || '')
const canSubmit = computed(() => presentation.value?.can_submit === true)
const canValidate = computed(() => presentation.value?.can_validate === true)
const canComment = computed(() => presentation.value?.can_comment === true)
const canReturnForCorrections = computed(() => presentation.value?.can_return_for_corrections === true)
const slideComments = computed(() =>
  (presentation.value?.slide_comments || []).filter(
    (comment) => Number(comment.slide_index) === currentIdx.value,
  ),
)

function formatCommentDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('fr-FR')
}

function isOwnComment(comment) {
  return Boolean(currentUser?.id) && String(comment?.author_user_id || '') === String(currentUser.id)
}

//â”€ Lifecycle
onMounted(async () => {
  window.addEventListener('keydown', onKeyDown)
  await loadPresentation()
  await loadSlides('images')
})
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <div class="flex h-screen flex-col bg-slate-100 font-sans">
    <div
      v-if="successMessage"
      class="fixed right-6 top-6 z-50 rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-xl"
    >
      {{ successMessage }}
    </div>

    <!-- Top bar -->
    <header class="flex min-h-[3rem] flex-shrink-0 flex-wrap items-center justify-between gap-2 bg-brand-500 px-4 py-2 shadow">

      <!-- Left: back + menu -->
      <div class="flex items-center gap-3 sm:gap-6">
        <button
          class="flex items-center gap-1.5 text-xs font-semibold text-white/80 hover:text-white"
          @click="emit('back')"
        >
          <span class="text-base">←</span> Retour
        </button>
        <nav class="hidden items-center gap-5 lg:flex">
          <button v-for="item in ['Fichier','Édition','Insertion','Placeholders']" :key="item"
                  class="text-xs font-semibold text-white/90 hover:text-white">
            {{ item }}
          </button>
        </nav>
      </div>

      <!-- Center: filename -->
      <div class="hidden items-center gap-2 md:flex max-w-xl min-w-0">
        <input
          v-model="renameDraft"
          type="text"
          class="min-w-0 flex-1 rounded-md border border-white/25 bg-white/15 px-3 py-1 text-xs font-semibold text-white placeholder:text-white/70 outline-none"
          placeholder="Nom du document"
          @keydown.enter.prevent="savePresentationName"
        />
        <button
          class="rounded-md border border-white/30 bg-white/10 px-3 py-1 text-xs font-semibold text-white hover:bg-white/20 disabled:opacity-50"
          :disabled="renaming"
          @click="savePresentationName"
        >
          {{ renaming ? 'Enregistrement…' : 'Renommer' }}
        </button>
      </div>

      <!-- Right: actions -->
      <div class="flex flex-wrap items-center gap-2">
        <!-- Download -->
        <button
          class="flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20 disabled:opacity-50"
          :disabled="downloading"
          @click="downloadPptx"
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">{{ downloading ? 'Exporter' : 'Télécharger' }}</span>
        </button>

        <!-- Submit -->
        <button
          v-if="canSubmit"
          class="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
          @click="showSubmitModal = true"
        >
          {{ submitActionLabel }}
        </button>
        <button
          v-if="canValidate"
          class="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          :disabled="validating"
          @click="validatePresentation"
        >
          {{ validating ? 'Validation…' : 'Valider' }}
        </button>
        <button
          v-if="canReturnForCorrections"
          class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
          :disabled="returningForCorrections"
          @click="returnToAssistantForCorrections"
        >
          {{ returningForCorrections ? 'Renvoi…' : 'Renvoyer pour correction' }}
        </button>
      </div>
    </header>

    <!-- Main area -->
    <div class="flex flex-1 overflow-hidden">

      <!-- Filmstrip (left sidebar) -->
      <aside class="flex w-24 flex-shrink-0 flex-col gap-0 overflow-y-auto border-r border-slate-200 bg-white py-3 sm:w-44">
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

      <!-- Central view -->
      <main class="flex flex-1 flex-col items-center justify-center overflow-auto bg-slate-200 p-3 gap-4 sm:p-6">

        <!-- Error state -->
        <div v-if="error" class="rounded-xl bg-white p-8 text-center shadow">
          <p class="font-semibold text-slate-800">Erreur</p>
          <p class="mt-2 text-sm text-slate-500">{{ error }}</p>
        </div>

        <!-- Loading state -->
        <div v-else-if="slidesLoading" class="flex flex-col items-center gap-3">
          <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-300 border-t-brand-500"></div>
          <p class="text-sm text-slate-500">Chargement des slides</p>
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
                {{ saving ? 'Sauvegarder' : 'Enregistrer' }}
              </button>
              <button
                class="rounded-lg bg-white px-4 py-2 text-xs font-semibold text-slate-600 shadow hover:bg-slate-50"
                @click="editing = false"
              >
                Annuler
              </button>
            </template>
          </div>

          <section class="w-full max-w-4xl rounded-2xl bg-white p-5 shadow">
            <div class="flex items-center justify-between gap-4">
              <div>
                <h3 class="text-sm font-semibold text-slate-900">Commentaires de la slide {{ currentIdx + 1 }}</h3>
                <p class="mt-1 text-xs text-slate-500">Le manager peut laisser des indications, et l’assistant peut répondre avant une nouvelle soumission.</p>
              </div>
              <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {{ slideComments.length }} commentaire{{ slideComments.length > 1 ? 's' : '' }}
              </span>
            </div>

            <div class="mt-4 space-y-3">
              <div
                v-for="comment in slideComments"
                :key="comment.comment_id"
                class="rounded-xl border px-4 py-3"
                :class="isOwnComment(comment) ? 'border-brand-100 bg-brand-50/40' : 'border-slate-200 bg-slate-50'"
              >
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-slate-900">{{ comment.author_name || 'Utilisateur' }}</p>
                    <p class="text-xs text-slate-500">{{ comment.author_grade || '-' }}</p>
                  </div>
                  <span class="text-xs text-slate-400">{{ formatCommentDate(comment.created_at) }}</span>
                </div>
                <p class="mt-3 whitespace-pre-wrap text-sm text-slate-700">{{ comment.text }}</p>
              </div>

              <div v-if="!slideComments.length" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-400">
                Aucun commentaire sur cette slide pour le moment.
              </div>
            </div>

            <div v-if="canComment" class="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label class="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Ajouter un commentaire
              </label>
              <textarea
                v-model="commentDraft"
                rows="3"
                class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-brand-500"
                placeholder="Exemple : revoir la formulation de cette slide, préciser le contexte client, ajouter une source…"
              />
              <div class="mt-3 flex justify-end">
                <button
                  class="rounded-lg bg-brand-500 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                  :disabled="commentSaving || !commentDraft.trim()"
                  @click="addComment"
                >
                  {{ commentSaving ? 'Enregistrement…' : 'Publier le commentaire' }}
                </button>
              </div>
            </div>
          </section>
        </template>
      </main>
    </div>

    <!-- Submit confirmation modal -->
    <Teleport to="body">
      <div v-if="showSubmitModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
        <div class="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
          <h2 class="text-lg font-semibold text-slate-900">{{ submitActionLabel }}</h2>
          <p class="mt-3 text-sm text-slate-600">
            La présentation <strong>{{ clientName }}</strong> sera transmise au validateur suivant.
            <span v-if="currentReviewerName">Validateur actuel : <strong>{{ currentReviewerName }}</strong>.</span>
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
              {{ submitting ? 'Envoier' : 'Confirmer la soumission' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>