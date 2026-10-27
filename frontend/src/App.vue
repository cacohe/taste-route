<template>
  <div id="app-shell">
    <header class="site-header"><router-link to="/">◌ TasteRoute</router-link></header>
    <router-view />
    <footer>TasteRoute ©2026 · Powered by Qloo cultural intelligence</footer>
  </div>
</template>

<style>
:root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #251d35; background: #f7f4ed; font-synthesis: none; }
* { box-sizing: border-box; }
body { margin: 0; }
button, input, select { font: inherit; }
.site-header { height: 64px; display: flex; align-items: center; padding: 0 clamp(20px, 5vw, 76px); background: #251b3e; }
.site-header a { color: white; font-size: 1.25rem; font-weight: 800; text-decoration: none; }
footer { padding: 24px; text-align: center; color: #776c85; background: #eee9df; }
</style>
