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

export type WecomEntityType = 'bug' | 'requirement';
export type WecomRuleKind = 'create' | 'transition' | 'comment';

export interface WecomNotifyRule {
  id: string;
  project_id: string;
  entity_type: WecomEntityType;
  kind: WecomRuleKind;
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

export type VersionType = 'app_release' | 'hotfix';

export type VersionStatus = 'planning' | 'developing' | 'releasing' | 'reviewing' | 'ended';

export type VersionNodeKey = string;

export type VersionNodeState = 'pending' | 'in_progress' | 'completed';

export interface VersionNodeProgress {
  node_key: string;
  state: VersionNodeState;
  completed_at?: string | null;
  operator_id?: string | null;
  assignee_id?: string | null;
  scheduled_start?: string | null;
  scheduled_end?: string | null;
}

export interface VersionWorkflowNodeDef {
  id: string;
  project_id: string;
  version_type: VersionType;
  node_key: string;
  label: string;
  lane_index: number;
  lane_indexes: number[];
  sort_in_lane: number;
}

export interface VersionBrief {
  id: string;
  num: number;
  name: string;
  /** 选填的构建号，例如 1234 或 1.2.0.456 */
  build_number?: string | null;
  /** 上线日期 YYYY-MM-DD */
  released_at?: string | null;
  status?: VersionStatus;
  version_type?: VersionType;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  num: number;
  name: string;
  /** 选填的构建号 */
  build_number: string | null;
  version_type: VersionType;
  status: VersionStatus;
  nodes: VersionNodeProgress[];
  workflow_defs: VersionWorkflowNodeDef[];
  /** 上线日期 YYYY-MM-DD */
  released_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface VersionWecomIntegration {
  project_id: string;
  version_wecom_webhook_url?: string | null;
  version_wecom_enabled: boolean;
  app_public_url?: string | null;
}

export interface VersionWecomNotifyRule {
  id: string;
  project_id: string;
  node_key: string;
  node_label: string;
  message_template: string;
  notify_user_ids: string[];
  enabled: boolean;
}

export interface VersionWecomNotifyRuleOption {
  node_key: string;
  node_label: string;
  default_message_template: string;
  configured: boolean;
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
  | 'completed'
  | 'closed';

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
  planned_schedule_start?: string | null;
  planned_schedule_end?: string | null;
}

export interface RequirementNodeTask {
  id: string;
  requirement_id: string;
  node_key: string;
  title: string;
  role_key: string;
  assignee_id: string | null;
  assignee?: UserBrief | null;
  estimate_points: number | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  sort: number;
  created_at: string;
  updated_at: string;
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

/** 需求状态推导规则 */
export type RequirementStatusRuleTrigger = 'lane' | 'node_completed' | 'status_hold';

export interface RequirementStatusRule {
  id: string;
  project_id: string;
  status: RequirementStatus;
  node_keys: string[];
  sort: number;
  trigger_type: RequirementStatusRuleTrigger;
}

/** 版本状态推导规则 */
export type VersionStatusRuleTrigger = 'lane' | 'node_completed' | 'status_hold';

export interface VersionStatusRule {
  id: string;
  project_id: string;
  version_type: VersionType;
  status: VersionStatus;
  node_keys: string[];
  sort: number;
  trigger_type: VersionStatusRuleTrigger;
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
  selected_role_keys?: string[];
  custom_fields?: Record<string, unknown>;
  dev_handoff_date?: string | null;
  estimated_completion_date?: string | null;
  developers?: UserBrief[];
  nodes: RequirementNodeProgress[];
  node_tasks?: RequirementNodeTask[];
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

export interface PlanCaseResultComment {
  id: string;
  plan_case_id: string;
  user_id: string;
  body: string;
  created_at: string;
  user?: { id: string; name: string; email: string } | null;
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
  follower_schedules?: BugFollowerSchedule[];
}

export interface BugFollowerSchedule {
  link_id: string;
  user_id: string;
  fix_estimate_points: number | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
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

export type MemberScheduleItemType = 'requirement_node_task' | 'bug';

export interface MemberScheduleItem {
  item_type: MemberScheduleItemType;
  id: string;
  title: string;
  assignee_id: string;
  estimate_points: number | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  requirement_id?: string | null;
  requirement_num?: number | null;
  requirement_title?: string | null;
  requirement_task_count?: number | null;  // 该需求下总节点任务数
  node_key?: string | null;
  node_label?: string | null;
  role_key?: string | null;
  bug_id?: string | null;
  bug_num?: number | null;
  bug_title?: string | null;
}

export interface MemberScheduleRow {
  user_id: string;
  name: string;
  scheduled_count: number;
  total_estimate_points: number;
  unscheduled_count: number;
  scheduled_items: MemberScheduleItem[];
  unscheduled_items: MemberScheduleItem[];
}

export interface MemberSchedule {
  range_start: string;
  range_end: string;
  members: MemberScheduleRow[];
}

// ---------------------------------------------------------------------------
// UI 自动化
// ---------------------------------------------------------------------------

export type MobilePlatform = 'android' | 'ios';
export type UITestCaseStatus = 'draft' | 'active';
export type UIRunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'error';
export type UIStepStatus = 'pending' | 'passed' | 'failed' | 'skipped';

export interface UIElement {
  id: string;
  project_id: string;
  platform: MobilePlatform;
  name: string;
  selector: string;
  description: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface UITestStep {
  action: string;
  selector_key?: string;
  value?: string;
}

export interface UITestAssertion {
  type?: string;
  selector_key?: string;
  value?: string;
}

export interface UITestCase {
  id: string;
  project_id: string;
  name: string;
  platform: MobilePlatform;
  description: string | null;
  status: UITestCaseStatus;
  selectors: Record<string, string>;
  steps: UITestStep[];
  assertion: UITestAssertion;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface UITestCaseListItem {
  id: string;
  name: string;
  platform: MobilePlatform;
  status: UITestCaseStatus;
  created_at: string;
  updated_at: string;
}

export interface MobileApp {
  id: string;
  project_id: string;
  platform: MobilePlatform;
  version: string;
  filename: string;
  size: number;
  uploaded_by: string;
  uploaded_at: string;
}

export interface UIRunner {
  id: string;
  project_id: string;
  name: string;
  platform: MobilePlatform;
  last_heartbeat_at: string | null;
  created_at: string;
}

export interface UITestStepResult {
  id: string;
  run_id: string;
  step_index: number;
  status: UIStepStatus;
  error_message: string | null;
  screenshot_key: string | null;
  screenshot_url: string | null;
  duration_ms: number | null;
  executed_at: string | null;
}

export interface UITestRun {
  id: string;
  project_id: string;
  case_id: string;
  app_id: string;
  runner_id: string | null;
  status: UIRunStatus;
  error_message: string | null;
  video_key: string | null;
  video_url: string | null;
  triggered_by: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  step_results: UITestStepResult[];
}

export interface UITestRunListItem {
  id: string;
  case_id: string;
  app_id: string;
  runner_id: string | null;
  status: UIRunStatus;
  triggered_by: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}
