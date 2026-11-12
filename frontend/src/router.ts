import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'

import ApplicationsView from './views/ApplicationsView.vue'
import NotFoundView from './views/NotFoundView.vue'
import OrganizationsView from './views/OrganizationsView.vue'

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [
      { path: '/', redirect: '/applications' },
      { path: '/applications', name: 'applications', component: ApplicationsView },
      { path: '/organizations', name: 'organizations', component: OrganizationsView },
      { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
    ],
  })
}
