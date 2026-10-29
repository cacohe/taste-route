<template>
  <div class="taste-search">
    <div class="search-row">
      <input
        v-model="query"
        data-test="taste-query"
        type="search"
        placeholder="Search for a film, artist, book, brand, or place"
        aria-label="Search taste entities"
      />
      <select v-model="entityType" class="category-select" aria-label="Taste category">
        <option value="">All categories</option>
        <option value="movie">Film</option>
        <option value="artist">Music</option>
        <option value="book">Book</option>
        <option value="place">Place</option>
        <option value="brand">Brand</option>
      </select>
    </div>

    <p v-if="loading" class="status">Asking Qloo…</p>
    <p v-else-if="error" class="status error">{{ error }}</p>
    <div v-else-if="results.length" class="results" role="listbox">
      <button
        v-for="entity in results"
        :key="entity.id"
        type="button"
        class="result"
        :data-test="`result-${entity.id}`"
        :disabled="isSelected(entity.id)"
        @click="select(entity)"
      >
        <img v-if="entity.image_url" :src="entity.image_url" alt="" />
        <span><strong>{{ entity.name }}</strong><small>{{ entity.entity_type }}</small></span>
        <span>{{ isSelected(entity.id) ? 'Selected' : 'Add' }}</span>
      </button>
    </div>

    <div v-if="modelValue.length" class="selected" aria-label="Selected taste signals">
      <TasteSeedChip
        v-for="seed in modelValue"
        :key="seed.id ?? `${seed.entity_type}-${seed.name}`"
        :seed="seed"
        @remove="remove(seed)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import TasteSeedChip from './TasteSeedChip.vue'
import { searchTasteEntities } from '@/services/api'
import type { TasteEntity, TasteSeed } from '@/types/taste'

const props = defineProps<{ modelValue: TasteSeed[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: TasteSeed[]] }>()

const query = ref('')
const entityType = ref('')
const results = ref<TasteEntity[]>([])
const loading = ref(false)
const error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let requestVersion = 0

async function runSearch() {
  const version = ++requestVersion
  const value = query.value.trim()
  if (value.length < 2) {
    results.value = []
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await searchTasteEntities(value, entityType.value || undefined)
    if (version === requestVersion) results.value = response.items
  } catch (searchError) {
    if (version === requestVersion) {
      results.value = []
      error.value = searchError instanceof Error ? searchError.message : 'Search is temporarily unavailable.'
    }
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch([query, entityType], () => {
  requestVersion += 1
  results.value = []
  error.value = ''
  loading.value = false
  if (timer) clearTimeout(timer)
  timer = setTimeout(runSearch, 300)
})

onBeforeUnmount(() => { if (timer) clearTimeout(timer) })

const isSelected = (id: string) => props.modelValue.some((seed) => seed.id === id)

function select(entity: TasteEntity) {
  if (isSelected(entity.id)) return
  emit('update:modelValue', [
    ...props.modelValue,
    { id: entity.id, name: entity.name, entity_type: entity.entity_type },
  ])
}

function remove(seed: TasteSeed) {
  emit('update:modelValue', props.modelValue.filter((item) => item.id !== seed.id))
}
</script>

<style scoped>
.taste-search { display: grid; gap: .9rem; }
.search-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(11.5rem, max-content); gap: .65rem; }
input, select { width: 100%; box-sizing: border-box; padding: .8rem .9rem; border: 1px solid #d9d4e8; border-radius: 10px; background: white; color: #241b3a; }
.search-row input { min-width: 0; }
.category-select { min-width: 11.5rem; padding-right: 2.5rem; }
.results { display: grid; gap: .4rem; max-height: 240px; overflow: auto; }
.result { display: grid; grid-template-columns: 42px 1fr auto; align-items: center; gap: .75rem; width: 100%; padding: .65rem; text-align: left; border: 1px solid #eee9f8; border-radius: 10px; background: white; cursor: pointer; }
.result:disabled { opacity: .6; cursor: default; }
.result img { width: 42px; height: 42px; object-fit: cover; border-radius: 7px; }
.result span { display: grid; }
.result small, .status { color: #776b8e; }
.error { color: #aa3344; }
.selected { display: flex; flex-wrap: wrap; gap: .5rem; }
@media (max-width: 640px) { .search-row { grid-template-columns: 1fr; } }
</style>
