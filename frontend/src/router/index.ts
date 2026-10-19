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
    }
  ]
});

export default router;
