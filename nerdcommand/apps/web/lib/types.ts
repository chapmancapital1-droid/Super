// Type definitions mirroring the FastAPI Pydantic models (app/models/schemas.py).

export type TaskStatus =
  | "queued"
  | "running"
  | "waiting"
  | "complete"
  | "failed"
  | "blocked"
  | "approval_required";

export interface TaskView {
  id: string;
  agent_id: string;
  goal: string;
  status: TaskStatus;
  depends_on: string[];
}

export interface ApprovalRequest {
  id: string;
  task_id: string;
  agent_id: string;
  action: string;
  description: string;
  permission_class: string;
  status: string;
  trace_id: string;
}

export interface AgentManifest {
  id: string;
  version: string;
  display_name: string;
  purpose: string;
  model_policy: string;
  temperature: number;
  tools: string[];
  permissions: string[];
  input_schema: string;
  output_schema: string;
  requires_approval: boolean;
  max_cost_usd: number;
}

export interface SensesStatus {
  hearing_enabled: boolean;
  room: {
    activity: string;
    peak_level: number;
    avg_level: number;
    speech_heard: boolean;
    last_transcript: string;
  };
  vision_enabled: boolean;
  last_frame_at: number | null;
}

export interface ChatResponse {
  session_id: string;
  task_id: string;
  graph_id: string;
  status: string;
  trace_id: string;
  plan: TaskView[];
  summary: string;
  approvals: ApprovalRequest[];
  senses?: SensesStatus | null;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  project_id?: string;
  metadata?: Record<string, unknown>;
}
