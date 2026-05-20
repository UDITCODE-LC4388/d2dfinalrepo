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

export interface LanguageStat {
  language: string;
  file_count: number;
  bytes: number;
  percentage: number;
}

export interface HotspotStat {
  filepath: string;
  churn: number;
  insertions: number;
  deletions: number;
  risk_score: number;
}

export interface DangerousCommit {
  hash: string;
  author: string;
  date: string;
  health_drop: number;
  affected_files: string[];
  ai_explanation: string;
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
  languages?: LanguageStat[];
  hotspots?: HotspotStat[];
  dangerous_commit?: DangerousCommit;
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


export interface SandboxRefactorResponse {
  advisory: string;
  before_code: string;
  after_code: string;
  model: string;
}

export async function getSandboxRefactor(
  repoUrl: string,
  filepath: string,
  antiPattern: string
): Promise<SandboxRefactorResponse> {
  const { data } = await axios.post<SandboxRefactorResponse>(
    `${API_BASE}/sandbox/refactor`,
    { repo_url: repoUrl, filepath, anti_pattern: antiPattern },
    { timeout: 30000 }
  );
  return data;
}

export interface CicdCheckResponse {
  passed: boolean;
  risk_score: number;
  base_risk: number;
  report: string;
  model: string;
}

export async function getCicdCheck(
  repoUrl: string,
  filepath: string,
  insertions: number,
  deletions: number
): Promise<CicdCheckResponse> {
  const { data } = await axios.post<CicdCheckResponse>(
    `${API_BASE}/cicd/check`,
    { repo_url: repoUrl, filepath, insertions, deletions },
    { timeout: 30000 }
  );
  return data;
}

export interface ForecastResponse {
  projected_score: number;
  report: string;
  model: string;
}

export async function getForecastSimulate(
  repoUrl: string,
  refactorHotspots: boolean,
  addTests: boolean,
  onboardDevs: number,
  churnVelocity: number,
  baseHealth: number
): Promise<ForecastResponse> {
  const { data } = await axios.post<ForecastResponse>(
    `${API_BASE}/forecast/simulate`,
    {
      repo_url: repoUrl,
      refactor_hotspots: refactorHotspots,
      add_tests: addTests,
      onboard_devs: onboardDevs,
      churn_velocity: churnVelocity,
      base_health: baseHealth
    },
    { timeout: 30000 }
  );
  return data;
}

