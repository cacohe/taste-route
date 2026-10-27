<template>
  <main class="home-shell">
    <section class="hero">
      <p class="eyebrow">QLOO-POWERED TRAVEL AGENT</p>
      <h1>从你的品味出发，<br />找到真正对味的城市路线。</h1>
      <p class="intro">选择你喜欢的电影、艺术家、书或地点。TasteRoute 用 Qloo 的文化关联寻找目的地中的真实地点，再由 AI 组织成可执行行程。</p>
    </section>

    <form class="planner" @submit.prevent="handleSubmit">
      <section>
        <span class="step">01</span>
        <div>
          <h2>要去哪里？</h2>
          <div class="grid three">
            <label>目的地<input v-model.trim="destination" required placeholder="例如 Tokyo / Lisbon" /></label>
            <label>开始日期<input v-model="startDate" required type="date" /></label>
            <label>结束日期<input v-model="endDate" required type="date" :min="startDate" /></label>
          </div>
        </div>
      </section>

      <section>
        <span class="step">02</span>
        <div>
          <h2>告诉我们你的文化坐标</h2>
          <p class="hint">至少选择一个 Qloo 实体。跨类型组合通常会得到更有意思的路线。</p>
          <TasteEntitySearch v-model="tasteSeeds" />
        </div>
      </section>

      <section>
        <span class="step">03</span>
        <div>
          <h2>调整旅行节奏</h2>
          <div class="grid three">
            <label>节奏
              <select v-model="pace"><option value="relaxed">松弛</option><option value="balanced">均衡</option><option value="packed">充实</option></select>
            </label>
            <label>预算
              <select v-model="budget"><option value="budget">经济</option><option value="medium">适中</option><option value="comfort">舒适</option></select>
            </label>
            <label>额外约束<input v-model="constraintsText" placeholder="步行为主、无障碍…" /></label>
          </div>
        </div>
      </section>

      <div class="submit-row">
        <p v-if="validationError" class="error">{{ validationError }}</p>
        <p v-else class="privacy">Qloo 密钥只保存在服务端；结果会标注推荐依据。</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '正在构建你的 TasteRoute…' : '生成 TasteRoute →' }}
        </button>
      </div>
    </form>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import TasteEntitySearch from '@/components/taste/TasteEntitySearch.vue'
import { generateTripPlan } from '@/services/api'
import type { TasteRouteRequest, TasteSeed } from '@/types/taste'

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

async function handleSubmit() {
  validationError.value = ''
  if (!destination.value || !startDate.value || !endDate.value) {
    validationError.value = '请填写目的地和旅行日期。'
    return
  }
  if (endDate.value < startDate.value) {
    validationError.value = '结束日期不能早于开始日期。'
    return
  }
  if (!tasteSeeds.value.length) {
    validationError.value = '请至少选择一个文化品味坐标。'
    return
  }

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
  try {
    const response = await generateTripPlan(request)
    if (!response.success || !response.data) throw new Error(response.message || '行程生成失败')
    sessionStorage.setItem('tasteRoutePlan', JSON.stringify(response.data))
    await router.push('/result')
  } catch (error) {
    validationError.value = error instanceof Error ? error.message : '行程生成失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-shell { min-height: 100vh; padding: 64px clamp(20px, 6vw, 92px); color: #241b3a; background: radial-gradient(circle at 85% 8%, #ffe3be 0, transparent 28%), linear-gradient(135deg, #f9f6ef 0%, #eee8ff 100%); }
.hero { max-width: 850px; margin: 0 auto 42px; }
.eyebrow { color: #7957ce; font-size: .75rem; font-weight: 800; letter-spacing: .18em; }
h1 { margin: .4rem 0 1rem; font-family: Georgia, serif; font-size: clamp(2.5rem, 6vw, 5.2rem); line-height: 1.02; font-weight: 500; }
.intro { max-width: 710px; color: #6d627c; font-size: 1.05rem; line-height: 1.75; }
.planner { max-width: 1050px; margin: auto; padding: 8px 38px 30px; border: 1px solid rgba(83, 60, 128, .13); border-radius: 24px; background: rgba(255,255,255,.82); box-shadow: 0 28px 80px rgba(50,35,78,.12); backdrop-filter: blur(18px); }
section { display: grid; grid-template-columns: 56px 1fr; gap: 20px; padding: 30px 0; border-bottom: 1px solid #e8e1ef; }
section > div { min-width: 0; }
.step { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; background: #2d2144; color: white; font-size: .75rem; }
h2 { margin: 4px 0 18px; font-size: 1.35rem; }
.hint, .privacy { color: #776c85; }
.grid { display: grid; gap: 14px; }.three { grid-template-columns: repeat(3, 1fr); }
label { display: grid; gap: 7px; color: #665b75; font-size: .82rem; font-weight: 650; }
input, select { box-sizing: border-box; width: 100%; padding: .82rem .9rem; border: 1px solid #d9d1e3; border-radius: 10px; background: #fff; color: #241b3a; font: inherit; }
.submit-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding-top: 28px; }
.submit-row p { margin: 0; }.error { color: #a92f47; }
button { padding: .95rem 1.45rem; border: 0; border-radius: 999px; background: #6242b3; color: white; font-weight: 750; cursor: pointer; white-space: nowrap; }
button:disabled { opacity: .6; cursor: wait; }
@media (max-width: 760px) { .home-shell { padding: 34px 14px; } .planner { padding: 4px 18px 24px; } section { grid-template-columns: 1fr; } .three { grid-template-columns: 1fr; } .submit-row { align-items: stretch; flex-direction: column; } }
</style>
