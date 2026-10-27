import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import 'maplibre-gl/dist/maplibre-gl.css'
import App from './App.vue'
import Home from './views/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: Home
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('./views/Result.vue')
    }
  ]
})

const app = createApp(App)

app.use(router)
app.mount('#app')

