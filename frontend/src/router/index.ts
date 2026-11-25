import { createRouter, createWebHistory } from "vue-router";

import DashboardView from "../views/dashboard/DashboardView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/analysis", redirect: "/" },
    { path: "/legacy-profile", redirect: "/" },
    { path: "/", name: "profile", component: DashboardView },
    {
      path: "/moral",
      name: "moral",
      component: () => import("../views/moral/MoralAnalysisView.vue")
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
