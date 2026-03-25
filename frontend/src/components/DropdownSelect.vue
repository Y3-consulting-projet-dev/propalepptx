<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Sélectionner' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const rootEl = ref(null)
const open = ref(false)

const normalizedOptions = computed(() => {
  const values = Array.isArray(props.options) ? props.options : []
  const uniq = Array.from(new Set(values.map((v) => (v == null ? '' : String(v))).filter(Boolean)))
  return uniq
})

const displayValue = computed(() => (props.modelValue ? props.modelValue : props.placeholder))

function close() {
  open.value = false
}

function toggle() {
  if (props.disabled) return
  open.value = !open.value
}

function selectValue(value) {
  emit('update:modelValue', value)
  close()
}

function onDocumentClick(e) {
  const root = rootEl.value
  if (!root) return
  if (!root.contains(e.target)) close()
}

function onKeyDown(e) {
  if (!open.value) return
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocumentClick)
  document.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocumentClick)
  document.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div ref="rootEl" class="relative">
    <label class="text-xs font-semibold text-slate-500">{{ label }}</label>

    <button
      type="button"
      class="mt-2 flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold outline-none transition focus:border-brand-400 focus:bg-white"
      :class="disabled ? 'cursor-not-allowed opacity-60' : 'hover:bg-white'"
      :disabled="disabled"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggle"
    >
      <span class="min-w-0 flex-1 truncate" :class="modelValue ? 'text-slate-900' : 'text-slate-500'">
        {{ displayValue }}
      </span>
      <svg viewBox="0 0 24 24" class="h-5 w-5 flex-none text-brand-600" aria-hidden="true">
        <path
          d="M6 9l6 6 6-6"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <div
      v-if="open"
      class="absolute left-0 right-0 z-50 mt-2 max-h-60 overflow-auto rounded-2xl border border-slate-200 bg-white py-2 shadow-soft"
    >
      <button
        type="button"
        class="w-full px-4 py-2 text-left text-sm font-semibold text-slate-600 hover:bg-slate-50"
        @click="selectValue('')"
      >
        {{ placeholder }}
      </button>
      <button
        v-for="opt in normalizedOptions"
        :key="opt"
        type="button"
        class="w-full px-4 py-2 text-left text-sm font-semibold hover:bg-brand-50"
        :class="opt === modelValue ? 'text-brand-800' : 'text-slate-800'"
        @click="selectValue(opt)"
      >
        {{ opt }}
      </button>
    </div>
  </div>
</template>

