export interface TemplateField {
  id: string;
  name: string;
  type: string;
  required: boolean;
  options: string[];
  sort: number;
}

export interface FieldTemplate {
  project_id: string;
  scene: string;
  fields: TemplateField[];
}

export interface BugStatusDef {
  id: string;
  project_id: string;
  key: string;
  label: string;
  sort: number;
  is_terminal: boolean;
  notify_wecom: boolean;
  notify_roles: string[];
}

export interface WecomIntegration {
  project_id: string;
  wecom_webhook_url: string | null;
  wecom_enabled: boolean;
  app_public_url: string | null;
  status_notify_template: string | null;
  create_notify_template: string | null;
  notify_on_create: boolean;
}

export interface WecomNotifyRule {
  id: string;
  project_id: string;
  kind: 'create' | 'transition';
  from_status_key: string | null;
  to_status_key: string | null;
  from_status_keys?: string[];
  to_status_keys?: string[];
  message_template: string;
  notify_roles: string[];
  enabled: boolean;
  created_at: string;
  from_status_label?: string | null;
  to_status_label?: string | null;
}

export interface CaseModule {
  id: string;
  project_id: string;
  parent_id: string | null;
  name: string;
  sort: number;
  created_at: string;
}

export interface CaseStep {
  desc: string;
  expected: string;
}

export interface VersionBrief {
  id: string;
  num: number;
  name: string;
  /** 上线日期 YYYY-MM-DD */
  released_at?: string | null;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  num: number;
  name: string;
  /** 上线日期 YYYY-MM-DD */
  released_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface UserBrief {
  id: string;
  name: string;
  email: string;
}

export type RequirementStatus =
  | 'draft'
  | 'pending_review'
  | 'designing'
  | 'developing'
  | 'testing'
  | 'pending_release'
  | 'released'
  | 'rejected';

export type RequirementPriority = string;
export type RequirementType = string;
export type RequirementNodeState = 'pending' | 'in_progress' | 'completed' | 'skipped';

export interface RequirementNodeProgress {
  node_key: string;
  label: string;
  state: RequirementNodeState;
  role_keys: string[];
  enabled: boolean;
  lane_index: number;
  lane_indexes: number[];
  blocks_lane_gate: boolean;
  sort_in_lane: number;
  started_at: string | null;
  completed_at: string | null;
  operator_id: string | null;
}

export interface RequirementRoleDef {
  id: string;
  project_id: string;
  role_key: string;
  label: string;
  sort: number;
}

export interface RequirementOptionDef {
  id: string;
  project_id: string;
  category: 'priority' | 'req_type';
  option_key: string;
  label: string;
  sort: number;
}

export interface RequirementWorkflowNodeDef {
  id: string;
  project_id: string;
  node_key: string;
  label: string;
  role_keys: string[];
  lane_index: number;
  lane_indexes: number[];
  blocks_lane_gate: boolean;
  sort_in_lane: number;
}

export interface RequirementWorkflowOut {
  defs: RequirementWorkflowNodeDef[];
  nodes: RequirementNodeProgress[];
}

export interface Requirement {
  id: string;
  project_id: string;
  num: number;
  title: string;
  external_url: string | null;
  version_id: string | null;
  version?: VersionBrief | null;
  priority: RequirementPriority;
  req_type: RequirementType;
  status: RequirementStatus;
  frontend_rd_id: string | null;
  backend_rd_id: string | null;
  pm_id: string | null;
  tech_owner_id: string | null;
  qa_id: string | null;
  designer_id: string | null;
  frontend_rd?: UserBrief | null;
  backend_rd?: UserBrief | null;
  pm?: UserBrief | null;
  tech_owner?: UserBrief | null;
  qa?: UserBrief | null;
  designer?: UserBrief | null;
  role_assignee_ids?: Record<string, string[]>;
  custom_fields?: Record<string, unknown>;
  nodes: RequirementNodeProgress[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface RequirementActivity {
  id: string;
  action_type: string;
  summary: string;
  detail: Record<string, unknown>;
  actor?: UserBrief | null;
  created_at: string;
}

export interface RequirementComment {
  id: string;
  requirement_id: string;
  user_id: string;
  body: string;
  created_at: string;
  user?: UserBrief | null;
}

export interface TestCase {
  id: string;
  project_id: string;
  module_id: string;
  module_path?: string | null;
  title: string;
  priority: string;
  precondition: string | null;
  step_text: string | null;
  expected_result: string | null;
  steps: CaseStep[];
  tags: string[];
  custom_fields: Record<string, unknown>;
  requirement_ids: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TestPlan {
  id: string;
  project_id: string;
  name: string;
  status: string;
  version_id: string | null;
  version?: VersionBrief | null;
  owner_id: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  /** 列表接口汇总字段 */
  case_total?: number;
  pass_count?: number;
  fail_count?: number;
  block_count?: number;
  skip_count?: number;
  not_run_count?: number;
  pass_rate?: number;
}

export interface PlanCaseResult {
  id: string;
  plan_case_id: string;
  executor_id: string | null;
  result: string;
  comment: string | null;
  executed_at: string | null;
}

export interface PlanCase {
  id: string;
  plan_id: string;
  case_id: string;
  sort: number;
  case?: TestCase;
  result?: PlanCaseResult;
}

export interface PlanStats {
  total: number;
  not_run: number;
  pass_count: number;
  fail_count: number;
  block_count: number;
  skip_count: number;
  pass_rate: number;
}

export interface BugItem {
  id: string;
  project_id: string;
  num: number;
  title: string;
  status_key: string;
  assignee_id: string | null;
  reporter_id: string;
  description: string | null;
  custom_fields: Record<string, unknown>;
  requirement_ids: string[];
  plan_ids: string[];
  plan_version_id: string | null;
  found_version_id: string | null;
  plan_version?: VersionBrief | null;
  found_version?: VersionBrief | null;
  follower_ids: string[];
  created_at: string;
  updated_at: string;
  assignee?: { id: string; name: string; email: string };
  reporter?: { id: string; name: string; email: string };
  followers?: { id: string; name: string; email: string }[];
}

export interface BugComment {
  id: string;
  bug_id: string;
  user_id: string;
  body: string;
  created_at: string;
  user?: { id: string; name: string; email: string };
}

export interface BugAttachment {
  id: string;
  bug_id: string;
  object_key: string;
  filename: string;
  size: number;
  created_at: string;
  url: string;
}

export interface BugActivity {
  id: string;
  source: string;
  action_type: string;
  summary: string;
  detail: Record<string, unknown>;
  actor?: { id: string; name: string; email: string };
  created_at: string;
}

export interface DashboardSummary {
  version_count: number;
  requirement_count: number;
  case_count: number;
  bug_count: number;
}

export interface ActivePlanBrief {
  id: string;
  name: string;
  status: string;
  case_total: number;
  not_run: number;
  pass_rate: number | null;
  version?: VersionBrief | null;
}

export interface StatusCountItem {
  key: string;
  label: string;
  count: number;
}

export interface StatusBreakdown {
  total: number;
  by_status: StatusCountItem[];
}

export interface BugOverviewCell {
  status_key: string;
  version_id: string | null;
  count: number;
}

export interface BugOverviewChart {
  total: number;
  by_status: StatusCountItem[];
  versions: VersionBrief[];
  cells: BugOverviewCell[];
}

export interface VersionFocus {
  version: VersionBrief | null;
  versions: VersionBrief[];
  requirements: StatusBreakdown;
  bugs: StatusBreakdown;
  plans: StatusBreakdown;
}

export interface PlanChartPoint {
  plan_id: string;
  plan_name: string;
  status: string;
  by_result: StatusCountItem[];
  pass_rate: number | null;
}

export interface PlanExecutionChart {
  points: PlanChartPoint[];
}

export interface FollowerBrief {
  id: string | null;
  label: string;
}

export interface BugFollowerCell {
  follower_id: string | null;
  version_id: string | null;
  count: number;
}

export interface BugFollowerOverviewChart {
  followers: FollowerBrief[];
  versions: VersionBrief[];
  cells: BugFollowerCell[];
}

export interface BugFocus {
  by_version_status: BugOverviewChart;
  follower_by_version: BugFollowerOverviewChart;
}

export interface PlanFocus {
  unfinished_plans: ActivePlanBrief[];
  execution_chart: PlanExecutionChart;
}

export interface DashboardOverview {
  version_focus: VersionFocus;
  bug_focus: BugFocus;
  plan_focus: PlanFocus;
}

export interface RequirementTodoBrief {
  id: string;
  num: number;
  title: string;
  status: RequirementStatus;
  version?: VersionBrief | null;
}

export interface DashboardTodo {
  draft_plans: ActivePlanBrief[];
  active_plans_todo: ActivePlanBrief[];
  fixed_bugs: BugItem[];
  not_tested_requirements: RequirementTodoBrief[];
  testing_requirements: RequirementTodoBrief[];
  follower_todo_bugs: BugItem[];
}

export interface DashboardWorkbench {
  summary: DashboardSummary;
  overview: DashboardOverview;
  todo: DashboardTodo;
  project_roles: string[];
}
