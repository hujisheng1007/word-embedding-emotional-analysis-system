import { createRouter, createWebHistory } from "vue-router";

import DashboardView from "../views/dashboard/DashboardView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: DashboardView
    },
    {
      path: "/resources",
      name: "resources",
      component: () => import("../views/resources/ResourceLibraryView.vue")
    },
    {
      path: "/collection",
      name: "collection",
      component: () => import("../views/collection/CollectionCenterView.vue")
    },
    {
      path: "/knowledge",
      name: "knowledge",
      component: () => import("../views/knowledge/KnowledgeResearchView.vue")
    }
  ]
});

export default router;
