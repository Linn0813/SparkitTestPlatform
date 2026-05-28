import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: { name: 'workbench' } },
        {
          path: 'workbench',
          name: 'workbench',
          component: () => import('@/views/workbench/WorkbenchView.vue'),
        },
        {
          path: 'case-modules',
          name: 'case-modules',
          component: () => import('@/views/case/CaseModuleListView.vue'),
        },
        { path: 'cases', name: 'cases', component: () => import('@/views/case/CaseListView.vue') },
        {
          path: 'cases/:id',
          redirect: (to) => ({
            name: 'cases',
            query: { ...to.query, caseId: to.params.id as string },
          }),
        },
        {
          path: 'requirements',
          name: 'requirements',
          component: () => import('@/views/requirement/RequirementListView.vue'),
        },
        {
          path: 'member-schedule',
          name: 'member-schedule',
          component: () => import('@/views/schedule/MemberScheduleView.vue'),
        },
        {
          path: 'versions',
          name: 'versions',
          component: () => import('@/views/version/VersionListView.vue'),
        },
        {
          path: 'versions/:id',
          redirect: (to) => ({
            name: 'versions',
            query: { ...to.query, versionId: to.params.id as string },
          }),
        },
        { path: 'plans', name: 'plans', component: () => import('@/views/plan/PlanListView.vue') },
        {
          path: 'plans/:id',
          name: 'plan-detail',
          component: () => import('@/views/plan/PlanDetailView.vue'),
        },
        { path: 'bugs', name: 'bugs', component: () => import('@/views/bug/BugListView.vue') },
        {
          path: 'bugs/:id',
          redirect: (to) => ({
            name: 'bugs',
            query: { ...to.query, bugId: to.params.id as string },
          }),
        },
        {
          path: 'setting/users',
          name: 'setting-users',
          component: () => import('@/views/setting/SystemUsersView.vue'),
          meta: { hideContextSwitcher: true },
        },
        {
          path: 'setting/project-config',
          name: 'setting-project-config',
          component: () => import('@/views/setting/ProjectConfigView.vue'),
        },
        {
          path: 'setting/project-members',
          redirect: { name: 'setting-project-config', query: { tab: 'members' } },
        },
        {
          path: 'setting/templates',
          redirect: { name: 'setting-project-config', query: { tab: 'templates' } },
        },
        {
          path: 'setting/projects-manage',
          name: 'setting-projects-manage',
          component: () => import('@/views/setting/ProjectManagementView.vue'),
          meta: { hideContextSwitcher: true },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue'),
          meta: { hideContextSwitcher: true },
        },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    if (auth.token) return { name: 'workbench' };
    return true;
  }
  if (!auth.token) return { name: 'login', query: { redirect: to.fullPath } };
  if (!auth.user) {
    try {
      await auth.loadMe();
    } catch {
      auth.logout();
      return { name: 'login' };
    }
  }
  return true;
});

export default router;
