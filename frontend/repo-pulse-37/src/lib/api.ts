import axios from "axios";

export interface Commit {
  hash: string;
  author: string;
  message: string;
  files_changed: number;
  insertions: number;
  deletions: number;
  health_score: number;
  ai_explanation: string;
  timestamp: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "developer" | "commit" | "module" | "dependency";
  weight?: number;
}
export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  label?: string;
}
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RiskItem {
  id: string;
  type: "coupling" | "instability" | "drift" | "maintainability";
  severity: "low" | "medium" | "high";
  title: string;
  description: string;
}

export interface AnalyzeResponse {
  repo_name: string;
  total_commits: number;
  health_score: number;
  risk_level: "Low" | "Medium" | "High";
  bus_factor: number;
  architecture_stability: number;
  health_timeline: { commit: number; score: number; date: string }[];
  ai_insight: string;
  commits: Commit[];
  graph: GraphData;
  risks: RiskItem[];
}

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export async function analyzeRepo(url: string): Promise<AnalyzeResponse> {
  const { data } = await axios.post<AnalyzeResponse>(
    `${API_BASE}/analyze`,
    { url },
    { timeout: 120000 },
  );

  return data;
}


export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  model_used: string;
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  const { data } = await axios.post<ChatResponse>(
    `${API_BASE}/chat`,
    {
      message,
      chat_history: history,
    },
    { timeout: 30000 },
  );
  return data;
}

