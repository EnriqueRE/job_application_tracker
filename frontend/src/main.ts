import './style.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createApp } from 'vue'

import App from './App.vue'
import { createAppRouter } from './router'

createApp(App).use(createAppRouter()).use(VueQueryPlugin).mount('#app')
