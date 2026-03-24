<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getTemplates } from '../api.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const router  = useRouter()

const sectorOptions = ['Télécommunications et TIC', 'Transport']
const missionOptions = ['Audit légal', 'IFRS 9', 'CAC']
const standardsOptions = ['IFRS', 'SYSCOHADA', 'OHADA']
const partnerOptions = ['Geoges Yao Yao', 'Yves Dodo']
const managerOptions = ['Revite Oule', 'Ibrahim Kamissoko']
const feesOptions = ['1–5 M FCFA', '5–10 M FCFA', '10–15 M FCFA']

const countryOptions = [
  'Afghanistan','Albania','Algeria','Andorra','Angola','Antigua and Barbuda','Argentina','Armenia','Australia','Austria','Azerbaijan',
  'Bahamas','Bahrain','Bangladesh','Barbados','Belarus','Belgium','Belize','Benin','Bhutan','Bolivia','Bosnia and Herzegovina','Botswana','Brazil','Brunei','Bulgaria','Burkina Faso','Burundi',
  'Cabo Verde','Cambodia','Cameroon','Canada','Central African Republic','Chad','Chile','China','Colombia','Comoros','Congo','Costa Rica','Croatia','Cuba','Cyprus','Czechia',
  "Côte d'Ivoire",
  'Democratic Republic of the Congo','Denmark','Djibouti','Dominica','Dominican Republic',
  'Ecuador','Egypt','El Salvador','Equatorial Guinea','Eritrea','Estonia','Eswatini','Ethiopia',
  'Fiji','Finland','France',
  'Gabon','Gambia','Georgia','Germany','Ghana','Greece','Grenada','Guatemala','Guinea','Guinea-Bissau','Guyana',
  'Haiti','Honduras','Hungary',
  'Iceland','India','Indonesia','Iran','Iraq','Ireland','Israel','Italy',
  'Jamaica','Japan','Jordan',
  'Kazakhstan','Kenya','Kiribati','Kuwait','Kyrgyzstan',
  'Laos','Latvia','Lebanon','Lesotho','Liberia','Libya','Liechtenstein','Lithuania','Luxembourg',
  'Madagascar','Malawi','Malaysia','Maldives','Mali','Malta','Marshall Islands','Mauritania','Mauritius','Mexico','Micronesia','Moldova','Monaco','Mongolia','Montenegro','Morocco','Mozambique','Myanmar',
  'Namibia','Nauru','Nepal','Netherlands','New Zealand','Nicaragua','Niger','Nigeria','North Korea','North Macedonia','Norway',
  'Oman',
  'Pakistan','Palau','Palestine','Panama','Papua New Guinea','Paraguay','Peru','Philippines','Poland','Portugal',
  'Qatar',
  'Romania','Russia','Rwanda',
  'Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines','Samoa','San Marino','Sao Tome and Principe','Saudi Arabia','Senegal','Serbia','Seychelles','Sierra Leone','Singapore','Slovakia','Slovenia','Solomon Islands','Somalia','South Africa','South Korea','South Sudan','Spain','Sri Lanka','Sudan','Suriname','Sweden','Switzerland','Syria',
  'Taiwan','Tajikistan','Tanzania','Thailand','Timor-Leste','Togo','Tonga','Trinidad and Tobago','Tunisia','Turkey','Turkmenistan','Tuvalu',
  'Uganda','Ukraine','United Arab Emirates','United Kingdom','United States','Uruguay','Uzbekistan',
  'Vanuatu','Vatican City','Venezuela','Vietnam',
  'Yemen',
  'Zambia','Zimbabwe'
]

const form = reactive({
  clientName: '',
  sector: '',
  country: '',
  missionType: '',
  standards: '',
  context: '',
  objectives: '',
  partner: '',
  manager: '',
  fees: '',
  deadline: '',
  duration: '',
})

// ─── Model chooser ────────────────────────────────────────────────────────────
const isModelOpen   = ref(false)
const models        = ref([])
const modelError    = ref('')
const selectedModel = ref(null)

// ─── Generation state ─────────────────────────────────────────────────────────
const generating    = ref(false)
const genError      = ref('')
const genStep       = ref('')    // status message shown to user

const STEPS = [
  'Lecture du modèle…',
  'Analyse de la structure…',
  'Génération du contenu par IA…',
  'Injection dans le fichier PPTX…',
  'Création des aperçus…',
  'Presque terminé…',
]

// ─── Load templates ───────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await getTemplates()
    models.value = (data.items || []).map((item, index) => ({
      id:       item.filename || String(index),
      title:    item.filename?.replace(/\.pptx$/i, '') || 'Modèle',
      filename: item.filename,
      slides:   [],
      loading:  false,
      error:    null,
      slideMode: null,
    }))
  } catch (err) {
    modelError.value = err.message
  }
})

// ─── Lazy-load slide thumbnails ───────────────────────────────────────────────
async function loadSlides(model) {
  if (model.slides.length || model.loading || model.error) return
  model.loading = true
  try {
    const res  = await fetch(`${API_BASE}/api/templates/${encodeURIComponent(model.filename)}/slides?mode=images`)
    const data = await res.json()
    if (!res.ok) {
      if (data.fallback_url) {
        const res2  = await fetch(`${API_BASE}/api/templates/${encodeURIComponent(model.filename)}/slides?mode=text`)
        const data2 = await res2.json()
        model.slides    = (data2.slides || []).map(s => ({ type: 'text', ...s }))
        model.slideMode = 'text'
      } else {
        model.error = data.error || 'Erreur'
      }
    } else {
      model.slides    = data.slides
      model.slideMode = 'images'
    }
  } catch {
    model.error = 'Impossible de charger les slides.'
  } finally {
    model.loading = false
  }
}

function openModal() {
  isModelOpen.value = true
  models.value.forEach(m => loadSlides(m))
}

function selectModel(model) {
  selectedModel.value = model
  isModelOpen.value   = false
}

// ─── Generate ─────────────────────────────────────────────────────────────────
async function generate() {
  if (!selectedModel.value) {
    alert('Veuillez choisir un modèle avant de générer.')
    return
  }
  if (!form.clientName.trim()) {
    alert('Le nom du client est requis.')
    return
  }

  generating.value = true
  genError.value   = ''
  genStep.value    = STEPS[0]

  // Animate steps for UX (the actual work is done server-side)
  let stepIdx = 0
  const stepTimer = setInterval(() => {
    stepIdx = Math.min(stepIdx + 1, STEPS.length - 1)
    genStep.value = STEPS[stepIdx]
  }, 2500)

  try {
    const res  = await fetch(`${API_BASE}/api/generate`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        template_filename: selectedModel.value.filename,
        form: { ...form },
      }),
    })
    const data = await res.json()
    clearInterval(stepTimer)

    if (!res.ok) {
      genError.value = data.error || 'Erreur lors de la génération'
      return
    }

    // Redirect to editor
    router.push({ name: 'editor', params: { id: data.presentation_id } })

  } catch (e) {
    clearInterval(stepTimer)
    genError.value = 'Impossible de contacter le serveur : ' + e.message
  } finally {
    generating.value = false
    genStep.value    = ''
  }
}

defineEmits(['back'])
</script>

<template>
  <section>
  <header class="flex items-start justify-between">
      <p class="text-2xl font-semibold text-brand-600">Générer une nouvelle présentation</p>
      <div class="flex items-center gap-3">
        <button class="h-10 w-10 rounded-full border border-slate-200 bg-white text-slate-600">🔔</button>
        <button
          class="rounded-full px-5 py-2 text-sm font-semibold transition"
          :class="selectedModel
            ? 'bg-brand-500 text-white'
            : 'bg-slate-100 text-slate-600 border border-slate-200'"
          @click="openModal"
        >
          {{ selectedModel ? `✓ ${selectedModel.title}` : 'Choisir un modèle' }}
        </button>
      </div>
  </header>

    <button
      class="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white"
      @click="$emit('back')"
    >← Retour</button>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Nom du client *
        <input v-model="form.clientName" type="text" placeholder="NSIA Bank Guinée"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none" />
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Secteur d'activité
        <select
          v-model="form.sector"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in sectorOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Pays
        <input
          v-model="form.country"
          type="text"
          list="country-list"
          placeholder="Saisir pour rechercher"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
        <datalist id="country-list">
          <option v-for="item in countryOptions" :key="item" :value="item"></option>
        </datalist>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Nature de la mission
        <select
          v-model="form.missionType"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in missionOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Normes applicables
        <select
          v-model="form.standards"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in standardsOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Contexte de la demande
        <input
          v-model="form.context"
          type="text"
          placeholder="Appel d'offres suite à..."
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Objectifs poursuivi par le client
        <input
          v-model="form.objectives"
          type="text"
          placeholder="Conformité BCRG, ..."
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Associé responsable de la mission
        <select
          v-model="form.partner"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in partnerOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Manager responsable de la mission
        <select
          v-model="form.manager"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in managerOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Fourchette d'honoraires
        <select
          v-model="form.fees"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in feesOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Date limite de remise de l'offre
        <input
          v-model="form.deadline"
          type="date"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Durée estimée de la mission
        <input
          v-model="form.duration"
          type="text"
          placeholder="6 semaines"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
      </label>
    </div>

    <!-- ── Error ── -->
    <div v-if="genError" class="mt-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
      {{ genError }}
    </div>

    <!-- ── Generate button ── -->
    <div class="mt-10 flex flex-col items-center gap-3">
      <button
        class="flex items-center gap-3 rounded-2xl bg-slate-900 px-12 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="generating"
        @click="generate"
      >
        <template v-if="generating">
          <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
          {{ genStep }}
        </template>
        <template v-else>
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Générer la présentation
        </template>
      </button>
      <p v-if="generating" class="text-xs text-slate-400">
        L'IA génère le contenu… cela peut prendre 20-40 secondes.
      </p>
    </div>

    <!-- ── Model chooser modal ── -->
    <Teleport to="body">
      <div v-if="isModelOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="isModelOpen = false" />
        <div class="relative flex flex-col rounded-2xl bg-white shadow-2xl"
             style="width:min(95vw,1020px); max-height:88vh;">

          <div class="flex flex-shrink-0 items-center justify-between rounded-t-2xl bg-white px-6 py-4 shadow-sm">
            <p class="text-sm font-semibold text-slate-800">Choisir un modèle</p>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500 text-white"
              @click="isModelOpen = false"
            >✕</button>
          </div>

          <div v-if="modelError" class="p-6 text-sm text-red-600">{{ modelError }}</div>

          <div v-else class="overflow-y-auto p-6">
            <div class="grid gap-5 lg:grid-cols-3">
              <article
                v-for="model in models" :key="model.id"
                class="group flex cursor-pointer flex-col rounded-2xl bg-white shadow transition hover:shadow-md hover:ring-2 hover:ring-brand-400"
                :class="selectedModel?.id === model.id ? 'ring-2 ring-brand-500' : ''"
                @click="selectModel(model)"
              >
                <!-- Main preview -->
                <div class="relative overflow-hidden rounded-t-2xl bg-slate-200" style="aspect-ratio:16/9">
                  <div v-if="model.loading" class="absolute inset-0 flex items-center justify-center bg-slate-100">
                    <div class="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-brand-500"></div>
                  </div>
                  <div v-else-if="model.error" class="absolute inset-0 flex items-center justify-center text-xs text-slate-400">
                    Aperçu indisponible
                  </div>
                  <img v-else-if="model.slideMode === 'images' && model.slides.length"
                       :src="`data:image/png;base64,${model.slides[0]}`"
                       :alt="model.title"
                       class="h-full w-full object-cover" />
                  <div v-else-if="model.slideMode === 'text' && model.slides.length"
                       class="flex h-full w-full flex-col items-center justify-center gap-2 bg-slate-50 p-4 text-center">
                    <p class="text-sm font-semibold text-slate-700">{{ model.slides[0].title || model.title }}</p>
                  </div>
                  <div v-if="selectedModel?.id === model.id"
                       class="absolute right-2 top-2 rounded-full bg-brand-500 px-2 py-0.5 text-xs font-bold text-white">
                    ✓ Sélectionné
                  </div>
                </div>

                <!-- Card footer -->
                <div class="flex flex-col gap-3 p-4">
                  <p class="truncate text-sm font-semibold text-brand-600" :title="model.title">{{ model.title }}</p>

                  <!-- Filmstrip thumbnails -->
                  <div class="flex items-center gap-1.5">
                    <template v-if="model.loading">
                      <div v-for="n in 3" :key="n"
                           class="h-10 w-16 flex-shrink-0 animate-pulse rounded border border-slate-200 bg-slate-200" />
                    </template>
                    <template v-else-if="model.slideMode === 'images'">
                      <div v-for="(slide, i) in model.slides.slice(1, 4)" :key="i"
                           class="h-10 w-16 flex-shrink-0 overflow-hidden rounded border border-slate-200">
                        <img :src="`data:image/png;base64,${slide}`"
                             class="h-full w-full object-cover" />
                      </div>
                    </template>
                    <template v-else-if="model.slideMode === 'text'">
                      <div v-for="(slide, i) in model.slides.slice(1, 4)" :key="i"
                           class="flex h-10 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded border border-slate-200 bg-slate-50">
                        <span class="line-clamp-3 px-1 text-center text-[9px] leading-tight text-slate-500">
                          {{ slide.title || `Slide ${i+2}` }}
                        </span>
                      </div>
                    </template>
                    <span v-if="!model.loading && model.slides.length > 4"
                          class="ml-1 text-xs font-semibold text-brand-500">
                      +{{ model.slides.length - 4 }}
                    </span>
                  </div>

                  <button
                    class="mt-1 w-full rounded-xl bg-brand-500 py-2 text-xs font-semibold text-white hover:bg-brand-600"
                    @click.stop="selectModel(model)"
                  >
                    Utiliser ce modèle
                  </button>
                </div>
              </article>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Generation loading overlay ── -->
    <Teleport to="body">
      <div v-if="generating"
           class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-900/70 backdrop-blur-md">
        <div class="flex flex-col items-center gap-6 rounded-2xl bg-white px-12 py-10 shadow-2xl text-center max-w-sm">
          <!-- Animated icon -->
          <div class="relative flex h-16 w-16 items-center justify-center">
            <div class="absolute inset-0 animate-ping rounded-full bg-brand-100 opacity-75"></div>
            <div class="relative flex h-12 w-12 items-center justify-center rounded-full bg-brand-500">
              <svg width="24" height="24" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
          <div>
            <p class="text-base font-semibold text-slate-900">Génération en cours</p>
            <p class="mt-2 text-sm text-slate-500">{{ genStep }}</p>
          </div>
          <!-- Progress dots -->
          <div class="flex gap-1.5">
            <span v-for="n in 5" :key="n"
                  class="h-1.5 w-1.5 rounded-full bg-brand-300 animate-pulse"
                  :style="`animation-delay:${n * 0.15}s`"></span>
          </div>
          <p class="text-xs text-slate-400">L'IA rédige le contenu pour <strong>{{ form.clientName }}</strong></p>
        </div>
      </div>
    </Teleport>
  </section>
</template>
