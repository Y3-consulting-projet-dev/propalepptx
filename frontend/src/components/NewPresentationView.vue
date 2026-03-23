<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getTemplates } from '../api.js'
import previewImage from '../assets/hero.png'

const options = ['A', 'B', 'C', 'D']

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

const isModelOpen = ref(false)
const models = ref([])
const modelError = ref('')

const slides = [previewImage, previewImage, previewImage]

defineEmits(['back', 'submit'])

onMounted(async () => {
  try {
    const data = await getTemplates()
    models.value = (data.items || []).map((item, index) => ({
      id: item.filename || String(index),
      title: item.filename?.replace(/\.pptx$/i, '') || 'Modèle',
    }))
  } catch (err) {
    modelError.value = err.message
  }
})
</script>

<template>
  <section>
    <header class="flex items-start justify-between">
      <div>
        <p class="text-2xl font-semibold text-brand-600">Générer une nouvelle présentation</p>
      </div>
      <div class="flex items-center gap-3">
        <button class="h-10 w-10 rounded-full border border-slate-200 bg-white text-slate-600">🔔</button>
        <button
          class="rounded-full bg-brand-500 px-5 py-2 text-sm font-semibold text-white"
          @click="isModelOpen = true"
        >
          Choisir un modèle
        </button>
      </div>
    </header>

    <button
      class="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white"
      @click="$emit('back')"
    >
      ← Retour
    </button>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Nom du client
        <input
          v-model="form.clientName"
          type="text"
          placeholder="NSIA Bank Guinée"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        />
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Secteur d'activité
        <select
          v-model="form.sector"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Pays
        <select
          v-model="form.country"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Nature de la mission
        <select
          v-model="form.missionType"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Normes applicables
        <select
          v-model="form.standards"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
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
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Manager responsable de la mission
        <select
          v-model="form.manager"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        Fourchette d'honoraires
        <select
          v-model="form.fees"
          class="rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          <option disabled value="">Choisir</option>
          <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
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

    <div class="mt-12 flex justify-center">
      <button class="rounded-2xl bg-slate-900 px-10 py-3 text-sm font-semibold text-white">Générer</button>
    </div>

    <div v-if="isModelOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-slate-900/40" @click="isModelOpen = false"></div>
      <div class="relative w-[980px] max-w-[95vw] rounded-2xl bg-slate-100 p-8 shadow-2xl">
        <button
          class="absolute right-6 top-6 flex h-10 w-10 items-center justify-center rounded-full bg-brand-500 text-white"
          @click="isModelOpen = false"
        >
          ✕
        </button>

        <div v-if="modelError" class="text-sm text-red-600">{{ modelError }}</div>

        <div v-else class="grid gap-6 lg:grid-cols-3">
          <article v-for="model in models" :key="model.id" class="rounded-xl bg-white p-4 shadow">
            <p class="text-sm font-semibold text-brand-600">{{ model.title }}</p>
            <div class="mt-3 overflow-hidden rounded-lg bg-slate-200">
              <img :src="previewImage" alt="Aperçu" class="h-28 w-full object-cover" />
            </div>
            <div class="mt-3 flex items-center gap-2">
              <button
                v-for="(slide, index) in slides"
                :key="index"
                class="h-10 w-16 overflow-hidden rounded border border-slate-200"
              >
                <img :src="slide" alt="Mini" class="h-full w-full object-cover" />
              </button>
              <span class="text-brand-500">›</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
