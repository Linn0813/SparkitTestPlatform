import http from './http';
import type { PlanCase, PlanStats, TestPlan } from '@/types/business';

export function listPlans(params?: { version_id?: string }) {
  return http.get<TestPlan[]>('/plans', { params });
}

export function getPlan(id: string) {
  return http.get<TestPlan>(`/plans/${id}`);
}

export function createPlan(data: Partial<TestPlan>) {
  return http.post<TestPlan>('/plans', data);
}

export function updatePlan(id: string, data: Partial<TestPlan>) {
  return http.patch<TestPlan>(`/plans/${id}`, data);
}

export function deletePlan(id: string) {
  return http.delete(`/plans/${id}`);
}

export function listPlanCases(planId: string) {
  return http.get<PlanCase[]>(`/plans/${planId}/cases`);
}

export function addPlanCases(planId: string, caseIds: string[]) {
  return http.post<PlanCase[]>(`/plans/${planId}/cases`, { case_ids: caseIds });
}

export function removePlanCase(planId: string, planCaseId: string) {
  return http.delete(`/plans/${planId}/cases/${planCaseId}`);
}

export function updatePlanResult(planId: string, data: { plan_case_id: string; result: string; comment?: string }) {
  return http.post(`/plans/${planId}/results`, data);
}

export function getPlanStats(planId: string) {
  return http.get<PlanStats>(`/plans/${planId}/stats`);
}
