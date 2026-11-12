import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'

import ApplicationDetailView from './views/ApplicationDetailView.vue'
import ApplicationsView from './views/ApplicationsView.vue'
import NotFoundView from './views/NotFoundView.vue'
import OrganizationFormView from './views/OrganizationFormView.vue'
import OrganizationsView from './views/OrganizationsView.vue'

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [
      { path: '/', redirect: '/applications' },
      { path: '/applications', name: 'applications', component: ApplicationsView },
      {
        path: '/applications/:id(\\d+)',
        name: 'application-detail',
        component: ApplicationDetailView,
      },
      { path: '/organizations', name: 'organizations', component: OrganizationsView },
      { path: '/organizations/new', name: 'organization-new', component: OrganizationFormView },
      {
        path: '/organizations/:id(\\d+)',
        name: 'organization-edit',
        component: OrganizationFormView,
        props: true,
      },
      { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
    ],
  })
}
