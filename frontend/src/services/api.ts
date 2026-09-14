export interface ReportData {
  phase_1: string;
  phase_2: string;
  phase_3: string;
  conclusion: string;
  executive_summary: string;
}

export interface ArtifactFiles {
  word: Record<string, string>;
  pdf: Record<string, string>;
}

export interface MetricsData {
  total: number;
  completed: number;
  in_progress?: number;
  new?: number;
  blocked: number;
  completion_rate: number;
  status_distribution?: Record<string, number>;
  debug_issues?: Array<{
    key: string;
    summary: string;
    status: string;
    category: string;
    priority: string;
    type: string;
    assignee?: string;
    blocked: boolean;
  }>;
}

export interface AgentContext {
  intent: string;
  action: string;
  message?: string;
  data?: Record<string, unknown>;
}

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  reports?: ReportData;
  metrics?: MetricsData;
  artifacts?: ArtifactFiles;
  jobId?: string;
  agent?: AgentContext;
}

export interface SessionListItem {
  id: string;
  title: string;
  filter?: string;
  analysis?: string;
  created_at?: string;
  updated_at?: string;
  message_count?: number;
}

export interface SessionDetailResponse {
  session: {
    id: string;
    title: string;
    search_filter: string;
    analysis_requested: string;
    created_at: string;
    updated_at: string;
  };
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: string;
  }>;
  reports?: ReportData | null;
  metrics?: MetricsData | null;
  artifacts?: ArtifactFiles | null;
  job?: {
    id: string;
    status: string;
    progress: number;
  } | null;
}

export interface ChatResponse {
  session: {
    id: string;
    title: string;
    created_at?: string;
    updated_at?: string;
  };
  message: {
    id: string;
    content: string;
    timestamp: string;
  };
  reports: ReportData;
  metrics: MetricsData;
  execution_id: string;
  job?: {
    id: string;
    status: string;
    progress: number;
  };
  agent?: AgentContext;
  artifacts?: ArtifactFiles;
}

export interface ArtifactFileItem {
  phase: string;
  format: "word" | "pdf";
  filename: string;
  exists_on_disk: boolean;
  size_bytes: number;
  download_url: string;
}

export interface ArtifactInventoryItem {
  job_id: string;
  session_id: string;
  session_title: string;
  created_at: string;
  files: ArtifactFileItem[];
}

export interface GlobalArtifactsResponse {
  total_jobs: number;
  inventory: ArtifactInventoryItem[];
}

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export function getArtifactUrl(format: "word" | "pdf", filename: string, jobId: string): string {
  return `${API_BASE}/jobs/${jobId}/artifacts/${format}/${encodeURIComponent(filename)}`;
}

export async function fetchSessions(): Promise<SessionListItem[]> {
  const response = await fetch(`${API_BASE}/sessions/`);
  if (!response.ok) {
    throw new Error("No fue posible cargar el listado de sesiones.");
  }
  return response.json();
}

export async function fetchSessionDetail(sessionId: string): Promise<SessionDetailResponse> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/`);
  if (!response.ok) {
    throw new Error("No fue posible cargar los detalles de la sesión.");
  }
  return response.json();
}

export async function renameSession(sessionId: string, newTitle: string): Promise<{ id: string; title: string }> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: newTitle }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "No fue posible renombrar la sesión.");
  }
  return response.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("No fue posible eliminar la sesión.");
  }
}

export async function fetchGlobalArtifacts(): Promise<GlobalArtifactsResponse> {
  const response = await fetch(`${API_BASE}/artifacts/`);
  if (!response.ok) {
    throw new Error("No fue posible consultar el repositorio de artefactos.");
  }
  return response.json();
}

export async function sendChatMessage(payload: {
  message: string;
  search_filter?: string;
  analysis_requested?: string;
  session_id?: string;
}): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const detail = errorData.detail || "Error en el procesamiento del mensaje.";
    throw new Error(detail);
  }

  return response.json();
}
