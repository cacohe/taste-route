<template>
  <article class="profile-card">
    <p class="label">TASTE DNA</p>
    <h2>Your cultural route profile</h2>
    <div v-if="tags.length" class="tags">
      <span v-for="tag in tags" :key="tag">{{ tag }}</span>
    </div>
    <p v-else class="empty">Qloo returned no displayable tags for these places.</p>
  </article>
</template>

<script setup lang="ts">
defineProps<{ tags: string[] }>()
</script>

<style scoped>
.profile-card { padding: 24px; border-radius: 18px; color: #fff; background: linear-gradient(145deg, #251b3e, #5c3ba4); box-shadow: 0 18px 45px rgba(45,30,80,.2); }
.label { margin: 0; color: #cabaff; font-size: .72rem; font-weight: 800; letter-spacing: .18em; }.profile-card h2 { margin: .6rem 0 1rem; }
.tags { display: flex; flex-wrap: wrap; gap: .5rem; }.tags span { padding: .45rem .7rem; border: 1px solid rgba(255,255,255,.23); border-radius: 999px; background: rgba(255,255,255,.1); }.empty { color: #d7cfeb; }
</style>
