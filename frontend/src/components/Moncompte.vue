<script setup>
import { computed, ref, watch } from 'vue'
import { changePassword } from '../api.js'
import DropdownSelect from './DropdownSelect.vue'

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const activePanel = ref('personal')
const saveState = ref({ saving: false, message: '' })
const passwordState = ref({
  old: '',
  next: '',
  confirm: '',
  showOld: false,
  showNext: false,
  showConfirm: false,
  loading: false,
  error: '',
  success: '',
})
const draft = ref({
  first_name: '',
  last_name: '',
  name: '',
  email: '',
  grade: '',
  department: '',
})

const safe = (value) => {
  const v = value == null ? '' : String(value).trim()
  return v || null
}

const userId = computed(() => safe(props.user?.id) || safe(props.user?._id))

function hydrateDraft() {
  draft.value = {
    first_name: safe(props.user?.first_name) || '',
    last_name: safe(props.user?.last_name) || '',
    name: safe(props.user?.name) || '',
    email: safe(props.user?.email) || '',
    grade: safe(props.user?.grade) || '',
    department: safe(props.user?.department) || '',
  }
}

watch(
  () => props.user,
  () => hydrateDraft(),
  { immediate: true }
)

const displayName = computed(() => safe(`${draft.value.first_name} ${draft.value.last_name}`) || safe(draft.value.name))
const displayEmail = computed(() => safe(draft.value.email))

const baseGradeOptions = [
  'Assistant',
  'Senior',
  'Assistant manager',
  'Manager',
  'Senior manager',
  'Associé',
]

const baseDepartmentOptions = [
  'Conseil operationnel',
  'Conseil financier',
  'Expertise comptable',
  'Audit',
]

const gradeOptions = computed(() => {
  const current = safe(draft.value.grade)
  const set = new Set(baseGradeOptions)
  if (current) set.add(current)
  return Array.from(set)
})

const departmentOptions = computed(() => {
  const current = safe(draft.value.department)
  const set = new Set(baseDepartmentOptions)
  if (current) set.add(current)
  return Array.from(set)
})

const initials = computed(() => {
  const source = displayName.value || displayEmail.value || 'U'
  const parts = source.split(/[\s.@_-]+/).filter(Boolean)
  const a = parts[0]?.[0] ?? 'U'
  const b = parts[1]?.[0] ?? ''
  return (a + b).toUpperCase()
})

function downloadProfile() {
  const payload = {
    id: userId.value,
    name: safe(draft.value.name) || null,
    first_name: safe(draft.value.first_name) || null,
    last_name: safe(draft.value.last_name) || null,
    email: safe(draft.value.email) || null,
    grade: safe(draft.value.grade) || null,
    department: safe(draft.value.department) || null,
    exported_at: new Date().toISOString(),
  }

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'mon-compte.json'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function discardChanges() {
  hydrateDraft()
  saveState.value = { saving: false, message: 'Modifications annulées.' }
  window.setTimeout(() => {
    if (saveState.value.message === 'Modifications annulées.') saveState.value = { saving: false, message: '' }
  }, 1500)
}

function saveChanges() {
  // No backend endpoint yet: provide a useful export instead of a silent no-op.
  saveState.value = { saving: true, message: '' }
  window.setTimeout(() => {
    downloadProfile()
    saveState.value = { saving: false, message: 'Export effectué. La sauvegarde en base sera ajoutée ensuite.' }
    window.setTimeout(() => {
      if (saveState.value.message) saveState.value = { saving: false, message: '' }
    }, 2500)
  }, 350)
}

async function handleChangePassword() {
  passwordState.value.error = ''
  passwordState.value.success = ''

  const oldPwd = passwordState.value.old
  const nextPwd = passwordState.value.next
  const confirmPwd = passwordState.value.confirm

  if (!oldPwd || !nextPwd || !confirmPwd) {
    passwordState.value.error = 'Veuillez remplir tous les champs.'
    return
  }
  if (nextPwd !== confirmPwd) {
    passwordState.value.error = 'Le nouveau mot de passe et la confirmation ne correspondent pas.'
    return
  }
  if (oldPwd === nextPwd) {
    passwordState.value.error = 'Le nouveau mot de passe doit être différent de l’ancien.'
    return
  }

  try {
    passwordState.value.loading = true
    await changePassword(oldPwd, nextPwd)
    passwordState.value.success = 'Mot de passe modifié avec succès.'
    passwordState.value.old = ''
    passwordState.value.next = ''
    passwordState.value.confirm = ''
  } catch (e) {
    passwordState.value.error = e?.message || 'Erreur lors de la modification du mot de passe.'
  } finally {
    passwordState.value.loading = false
  }
}
</script>

<template>
  <section class="grid gap-6 lg:grid-cols-[320px_1fr]">
    <aside class="card px-6 py-6">
      <div class="flex items-center gap-4">
        <div class="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
          {{ initials }}
        </div>
        <div class="min-w-0">
          <p class="truncate text-base font-semibold text-slate-900">{{ displayName ?? 'Utilisateur' }}</p>
          <p class="truncate text-xs text-slate-500">{{ displayEmail ?? 'Email non disponible' }}</p>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-[11px] font-semibold text-brand-700">
              {{ safe(draft.grade) || 'Profil' }}
            </span>
          </div>
        </div>
      </div>

      <nav class="mt-7 flex flex-col gap-2 text-sm font-semibold">
        <button
          type="button"
          class="flex items-center justify-between rounded-2xl px-4 py-3 text-left transition"
          :class="activePanel === 'personal' ? 'bg-brand-500 text-white' : 'bg-slate-50 text-slate-700 hover:bg-slate-100'"
          @click="activePanel = 'personal'"
        >
          <span>Informations personnelles</span>
          <span class="text-xs opacity-80">1</span>
        </button>

        <button
          type="button"
          class="flex items-center justify-between rounded-2xl px-4 py-3 text-left transition"
          :class="activePanel === 'security' ? 'bg-brand-500 text-white' : 'bg-slate-50 text-slate-700 hover:bg-slate-100'"
          @click="activePanel = 'security'"
        >
          <span>Connexion & mot de passe</span>
          <span class="text-xs opacity-80">2</span>
        </button>

        <button
          type="button"
          class="mt-2 flex items-center justify-between rounded-2xl bg-slate-900 px-4 py-3 text-left text-sm font-semibold text-white"
          @click="emit('logout')"
        >
          <span>Déconnexion</span>
          <span class="text-xs opacity-80">⏻</span>
        </button>
      </nav>

    </aside>

    <div class="card px-6 py-6">
      <header class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-lg font-semibold text-slate-900">
            {{ activePanel === 'personal' ? 'Informations personnelles' : 'Connexion & mot de passe' }}
          </h1>
          <p class="mt-1 text-xs text-slate-500">
            {{ activePanel === 'personal'
              ? 'Profil de votre compte sur l’outil de génération de présentations.'
              : 'Sécurité du compte et gestion du mot de passe.' }}
          </p>
        </div>
      </header>

      <div v-if="saveState.message" class="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold text-slate-700">
        {{ saveState.message }}
      </div>

      <div v-if="!props.user" class="mt-6 rounded-2xl border border-slate-200/70 bg-white p-6 text-sm text-slate-600">
        Aucune session utilisateur trouvée. Déconnectez-vous puis reconnectez-vous.
      </div>

      <div v-else class="mt-6">
        <div v-if="activePanel === 'personal'" class="grid gap-4 lg:grid-cols-2">
          <div>
            <label class="text-xs font-semibold text-slate-500">Prénoms</label>
            <input
              v-model="draft.first_name"
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-brand-400 focus:bg-white"
              placeholder="Prénoms"
            />
          </div>

          <div>
            <label class="text-xs font-semibold text-slate-500">Nom</label>
            <input
              v-model="draft.last_name"
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-brand-400 focus:bg-white"
              placeholder="Nom"
            />
          </div>

          <div class="lg:col-span-2">
            <label class="text-xs font-semibold text-slate-500">Email</label>
            <div class="mt-2 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <input
                v-model="draft.email"
                class="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-900 outline-none"
                placeholder="email@domaine.com"
              />
              <span class="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold text-slate-700">
                <span class="h-2 w-2 rounded-full" :class="draft.email ? 'bg-brand-500' : 'bg-slate-300'"></span>
                {{ draft.email ? 'Renseigné' : 'Manquant' }}
              </span>
            </div>
          </div>

          <div>
            <DropdownSelect v-model="draft.grade" label="Grade" :options="gradeOptions" />
          </div>

          <div>
            <DropdownSelect v-model="draft.department" label="Département" :options="departmentOptions" />
          </div>

          <div class="lg:col-span-2 mt-2 flex flex-wrap items-center justify-end gap-3">
            <button
              type="button"
              class="rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              @click="discardChanges"
            >
              Annuler
            </button>
            <button
              type="button"
              class="rounded-full bg-brand-500 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
              :disabled="saveState.saving"
              @click="saveChanges"
            >
              {{ saveState.saving ? 'Sauvegarde…' : 'Enregistrer' }}
            </button>
          </div>
        </div>

        <div v-else class="space-y-4">
          <div class="rounded-2xl border border-slate-200/70 bg-white p-6">
            <div class="flex items-center justify-between gap-4">
              <p class="text-sm font-semibold text-slate-900">Changer le mot de passe</p>
              <span class="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-[11px] font-semibold text-brand-700">
                Règles de sécurité appliquées
              </span>
            </div>

            <p class="mt-2 text-xs text-slate-500">
              Renseignez votre ancien mot de passe, puis un nouveau mot de passe (au moins 8 caractères, majuscule, minuscule, chiffre, caractère spécial).
            </p>

            <div v-if="passwordState.error" class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
              {{ passwordState.error }}
            </div>
            <div v-if="passwordState.success" class="mt-4 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-800">
              {{ passwordState.success }}
            </div>

            <div class="mt-5 grid gap-4 lg:grid-cols-3">
              <div>
                <label class="text-xs font-semibold text-slate-500">Ancien mot de passe</label>
                <div class="mt-2 flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <input
                    v-model="passwordState.old"
                    :type="passwordState.showOld ? 'text' : 'password'"
                    class="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-900 outline-none"
                    autocomplete="current-password"
                    placeholder="Ancien mot de passe"
                  />
                  <button
                    type="button"
                    class="grid h-9 w-9 place-items-center rounded-full text-brand-600 hover:bg-brand-50 hover:text-brand-800"
                    @click="passwordState.showOld = !passwordState.showOld"
                    :aria-label="passwordState.showOld ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
                  >
                    <svg v-if="!passwordState.showOld" viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2" />
                    </svg>
                    <svg v-else viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M3 3l18 18"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M10.6 10.6a2 2 0 0 0 2.8 2.8"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M9.9 5.2A11.4 11.4 0 0 1 12 5c6.5 0 10 7 10 7a18.7 18.7 0 0 1-4.3 5"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M6.2 6.2A18.8 18.8 0 0 0 2 12s3.5 7 10 7a11.3 11.3 0 0 0 5-1.1"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              <div>
                <label class="text-xs font-semibold text-slate-500">Nouveau mot de passe</label>
                <div class="mt-2 flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <input
                    v-model="passwordState.next"
                    :type="passwordState.showNext ? 'text' : 'password'"
                    class="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-900 outline-none"
                    autocomplete="new-password"
                    placeholder="Nouveau mot de passe"
                  />
                  <button
                    type="button"
                    class="grid h-9 w-9 place-items-center rounded-full text-brand-600 hover:bg-brand-50 hover:text-brand-800"
                    @click="passwordState.showNext = !passwordState.showNext"
                    :aria-label="passwordState.showNext ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
                  >
                    <svg v-if="!passwordState.showNext" viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2" />
                    </svg>
                    <svg v-else viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M3 3l18 18"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M10.6 10.6a2 2 0 0 0 2.8 2.8"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M9.9 5.2A11.4 11.4 0 0 1 12 5c6.5 0 10 7 10 7a18.7 18.7 0 0 1-4.3 5"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M6.2 6.2A18.8 18.8 0 0 0 2 12s3.5 7 10 7a11.3 11.3 0 0 0 5-1.1"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              <div>
                <label class="text-xs font-semibold text-slate-500">Confirmer</label>
                <div class="mt-2 flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <input
                    v-model="passwordState.confirm"
                    :type="passwordState.showConfirm ? 'text' : 'password'"
                    class="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-900 outline-none"
                    autocomplete="new-password"
                    placeholder="Confirmer le mot de passe"
                  />
                  <button
                    type="button"
                    class="grid h-9 w-9 place-items-center rounded-full text-brand-600 hover:bg-brand-50 hover:text-brand-800"
                    @click="passwordState.showConfirm = !passwordState.showConfirm"
                    :aria-label="passwordState.showConfirm ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
                  >
                    <svg v-if="!passwordState.showConfirm" viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2" />
                    </svg>
                    <svg v-else viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
                      <path
                        d="M3 3l18 18"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M10.6 10.6a2 2 0 0 0 2.8 2.8"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M9.9 5.2A11.4 11.4 0 0 1 12 5c6.5 0 10 7 10 7a18.7 18.7 0 0 1-4.3 5"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      <path
                        d="M6.2 6.2A18.8 18.8 0 0 0 2 12s3.5 7 10 7a11.3 11.3 0 0 0 5-1.1"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div class="mt-5 flex flex-wrap items-center justify-end gap-3">
              <button
                type="button"
                class="rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                :disabled="passwordState.loading"
                @click="passwordState.old=''; passwordState.next=''; passwordState.confirm=''; passwordState.error=''; passwordState.success=''"
              >
                Effacer
              </button>
              <button
                type="button"
                class="rounded-full bg-brand-500 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
                :disabled="passwordState.loading"
                @click="handleChangePassword"
              >
                {{ passwordState.loading ? 'Modification…' : 'Modifier le mot de passe' }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  </section>
</template>
