import http from './http';
import type { PlanCase, PlanCaseResultComment, PlanStats, TestPlan } from '@/types/business';

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

export function updatePlanResult(planId: string, data: { plan_case_id: string; result: string }) {
  return http.post(`/plans/${planId}/results`, data);
}

export function listPlanCaseComments(planId: string, planCaseId: string) {
  return http.get<PlanCaseResultComment[]>(`/plans/${planId}/cases/${planCaseId}/comments`);
}

export function createPlanCaseComment(planId: string, planCaseId: string, body: string) {
  return http.post<PlanCaseResultComment>(`/plans/${planId}/cases/${planCaseId}/comments`, { body });
}

export function getPlanStats(planId: string) {
  return http.get<PlanStats>(`/plans/${planId}/stats`);
}
