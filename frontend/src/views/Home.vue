<template>
  <main class="home-shell">
    <section class="hero">
      <div class="route-motif" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="eyebrow">QLOO-POWERED TRAVEL AGENT</p>
      <h1>Travel through the lens of what you already love.</h1>
      <p class="intro">Choose films, artists, books, or places you love. TasteRoute uses Qloo's cultural intelligence to discover real places at your destination, then turns that evidence into a practical itinerary.</p>
    </section>

    <form class="planner" :aria-busy="loading" @submit.prevent="handleSubmit">
      <section class="planner-step">
        <span class="step">01</span>
        <div>
          <h2>Where are you going?</h2>
          <div class="grid three">
            <label>Destination<input v-model.trim="destination" required placeholder="Tokyo / Lisbon" /></label>
            <label>Start date<input v-model="startDate" required type="date" /></label>
            <label>End date<input v-model="endDate" required type="date" :min="startDate" /></label>
          </div>
        </div>
      </section>

      <section class="planner-step">
        <span class="step">02</span>
        <div>
          <h2>Choose your taste signals</h2>
          <p class="hint">Select at least one Qloo entity. Mixing categories usually creates a more distinctive route.</p>
          <TasteEntitySearch v-model="tasteSeeds" />
        </div>
      </section>

      <section class="planner-step">
        <span class="step">03</span>
        <div>
          <h2>Shape the trip</h2>
          <div class="grid three">
            <label>Pace
              <select v-model="pace"><option value="relaxed">Relaxed</option><option value="balanced">Balanced</option><option value="packed">Packed</option></select>
            </label>
            <label>Budget
              <select v-model="budget"><option value="budget">Budget</option><option value="medium">Moderate</option><option value="comfort">Comfort</option></select>
            </label>
            <label>Extra constraints<input v-model="constraintsText" placeholder="Walkable, accessible…" /></label>
          </div>
        </div>
      </section>

      <GenerationProgress
        v-if="loading"
        :events="progressEvents"
        :elapsed-seconds="elapsedSeconds"
      />

      <div class="submit-row">
        <p v-if="validationError" class="error">{{ validationError }}</p>
        <p v-else class="privacy">Your credentials stay server-side. Every recommendation keeps its Qloo evidence.</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Building your TasteRoute…' : retryAvailable ? 'Try generation again →' : 'Generate TasteRoute →' }}
        </button>
      </div>
    </form>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import TasteEntitySearch from '@/components/taste/TasteEntitySearch.vue'
import GenerationProgress from '@/components/trip/GenerationProgress.vue'
import { generateTripPlanStream } from '@/services/api'
import type { TasteRouteRequest, TasteSeed, WorkflowStep } from '@/types/taste'
import { validateTasteRouteDraft } from '@/utils/tasteRoute'

const router = useRouter()
const destination = ref('')
const startDate = ref('')
const endDate = ref('')
const pace = ref<TasteRouteRequest['pace']>('balanced')
const budget = ref<TasteRouteRequest['budget']>('medium')
const constraintsText = ref('')
const tasteSeeds = ref<TasteSeed[]>([])
const loading = ref(false)
const validationError = ref('')
const progressEvents = ref<WorkflowStep[]>([])
const elapsedSeconds = ref(0)
const retryAvailable = ref(false)
let elapsedTimer: ReturnType<typeof setInterval> | null = null

function stopElapsedTimer() {
  if (elapsedTimer !== null) clearInterval(elapsedTimer)
  elapsedTimer = null
}

onBeforeUnmount(stopElapsedTimer)

async function handleSubmit() {
  validationError.value = ''
  const invalid = validateTasteRouteDraft({
    destination: destination.value,
    startDate: startDate.value,
    endDate: endDate.value,
    tasteSeedCount: tasteSeeds.value.length,
  })
  if (invalid) { validationError.value = invalid; return }

  const request: TasteRouteRequest = {
    destination: destination.value,
    start_date: startDate.value,
    end_date: endDate.value,
    pace: pace.value,
    budget: budget.value,
    taste_seeds: tasteSeeds.value,
    constraints: constraintsText.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    excluded_place_ids: [],
  }

  loading.value = true
  retryAvailable.value = false
  progressEvents.value = []
  elapsedSeconds.value = 0
  const startedAt = Date.now()
  elapsedTimer = setInterval(() => {
    elapsedSeconds.value = Math.max(1, Math.floor((Date.now() - startedAt) / 1000))
  }, 1000)
  try {
    const response = await generateTripPlanStream(request, (step) => {
      progressEvents.value.push(step)
    })
    if (!response.success || !response.data) throw new Error(response.message || 'Could not generate the itinerary.')
    sessionStorage.setItem('tasteRoutePlan', JSON.stringify(response.data))
    await router.push('/result')
  } catch (error) {
    validationError.value = error instanceof Error ? error.message : 'Could not generate the itinerary. Please retry.'
    retryAvailable.value = true
  } finally {
    stopElapsedTimer()
    loading.value = false
  }
}
</script>

<style scoped>
.home-shell { min-height: 100vh; padding: 42px clamp(20px, 6vw, 92px) 64px; color: #241b3a; background: radial-gradient(circle at 85% 8%, #ffe3be 0, transparent 28%), linear-gradient(135deg, #f9f6ef 0%, #eee8ff 100%); }
.hero { position: relative; max-width: 980px; margin: 0 auto 30px; padding-right: 120px; }
.eyebrow { margin: 0; color: #7957ce; font-size: .72rem; font-weight: 800; letter-spacing: .16em; }
h1 { max-width: 900px; margin: .45rem 0 .8rem; font-family: Georgia, serif; font-size: clamp(2.65rem, 5vw, 4.35rem); line-height: 1.01; font-weight: 500; letter-spacing: -.035em; }
.intro { max-width: 720px; margin: 0; color: #6d627c; font-size: 1rem; line-height: 1.65; }
.route-motif { position: absolute; top: 9px; right: 8px; width: 92px; height: 92px; border: 1px solid #b9a8dc; border-left-color: transparent; border-radius: 50%; transform: rotate(-24deg); }
.route-motif::before { content: ''; position: absolute; inset: 16px; border: 1px dashed #c8b8e5; border-left-color: transparent; border-radius: 50%; }
.route-motif span { position: absolute; width: 9px; height: 9px; border: 2px solid #fff; border-radius: 50%; background: #6242b3; box-shadow: 0 2px 6px #4e397044; }
.route-motif span:nth-child(1) { top: 2px; left: 27px; }.route-motif span:nth-child(2) { top: 46px; right: -4px; }.route-motif span:nth-child(3) { bottom: 2px; left: 16px; }
.planner { max-width: 1050px; margin: auto; padding: 6px 38px 28px; border: 1px solid rgba(83, 60, 128, .13); border-radius: 24px; background: rgba(255,255,255,.86); box-shadow: 0 24px 70px rgba(50,35,78,.11); backdrop-filter: blur(18px); }
.planner-step { display: grid; grid-template-columns: 56px 1fr; gap: 20px; padding: 26px 0; border-bottom: 1px solid #e8e1ef; }
.planner-step > div { min-width: 0; }
.step { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; background: #2d2144; color: white; font-size: .75rem; }
h2 { margin: 4px 0 18px; font-size: 1.35rem; }
.hint, .privacy { color: #776c85; }
.grid { display: grid; gap: 14px; }.three { grid-template-columns: repeat(3, 1fr); }
label { display: grid; gap: 7px; color: #665b75; font-size: .82rem; font-weight: 650; }
input, select { box-sizing: border-box; width: 100%; padding: .82rem .9rem; border: 1px solid #d9d1e3; border-radius: 10px; background: #fff; color: #241b3a; font: inherit; }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 3px solid #bda9ed; outline-offset: 2px; }
.submit-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding-top: 28px; }
.submit-row p { margin: 0; }.error { color: #a92f47; }
button { padding: .95rem 1.45rem; border: 0; border-radius: 999px; background: #6242b3; color: white; font-weight: 750; cursor: pointer; white-space: nowrap; }
button:disabled { opacity: .6; cursor: wait; }
@media (max-width: 760px) { .home-shell { padding: 30px 14px 44px; } .hero { padding-right: 0; }.route-motif { display: none; } h1 { font-size: clamp(2.45rem, 12vw, 3.4rem); } .planner { padding: 4px 18px 24px; } .planner-step { grid-template-columns: 1fr; } .three { grid-template-columns: 1fr; } .submit-row { align-items: stretch; flex-direction: column; } }
</style>
