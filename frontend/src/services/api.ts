export type Reports = Record<"phase_1" | "phase_2" | "phase_3" | "conclusion" | "executive_summary", string>;
export interface ChatResponse { session: { id: string; title: string }; message: { id: string; content: string; timestamp: string }; reports: Reports; metrics: { total: number; completed: number; blocked: number; completion_rate: number } }
const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
export async function sendChat(payload: { message: string; search_filter: string; analysis_requested: string; session_id?: string }): Promise<ChatResponse> {
  const response = await fetch(`${baseUrl}/chat/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error("No fue posible completar el análisis.");
  return response.json() as Promise<ChatResponse>;
}
