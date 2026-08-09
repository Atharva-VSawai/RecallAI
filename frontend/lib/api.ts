// Use an explicit IPv4 loopback address for local development. On some
// machines `localhost` resolves to IPv6 (`::1`) while uvicorn is listening on
// IPv4 only, which makes every browser request fail with the unhelpful
// `Failed to fetch` message.
const RAW_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const BASE = RAW_BASE.replace("localhost", "127.0.0.1");
import { supabase } from "@/lib/supabase";

async function getValidSession() {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error) throw new Error("Your session could not be checked. Please sign in again.");
  if (!session) throw new Error("Your session has expired. Please sign in again.");

  // Supabase normally refreshes automatically, but getSession can still return a
  // token that is just past its expiry while the refresh timer is catching up.
  // Refresh it before protected requests when it is expired or about to expire.
  const expiresAt = session.expires_at ?? 0;
  if (expiresAt <= Math.floor(Date.now() / 1000) + 30) {
    const { data, error: refreshError } = await supabase.auth.refreshSession();
    if (refreshError || !data.session) {
      await supabase.auth.signOut();
      throw new Error("Your session has expired. Please sign in again.");
    }
    return data.session;
  }
  return session;
}

async function authenticatedHeaders(headers: HeadersInit = {}): Promise<Headers> {
  const session = await getValidSession();
  const result = new Headers(headers);
  result.set("Authorization", `Bearer ${session.access_token}`);
  const projectId = getActiveProjectId();
  if (projectId) result.set("X-Project-ID", projectId);
  return result;
}

async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  // Resolve authentication before entering the network-error handler. A
  // Supabase/session failure is not the same thing as the Recall API being
  // offline and must not be reported as a localhost connection error.
  const requestHeaders = await authenticatedHeaders(init.headers);
  let response: Response;
  try {
    response = await fetch(input, { ...init, headers: requestHeaders });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Cannot reach the Recall.AI API at ${BASE}. Start the backend on port 8000 and try again.`);
    }
    throw error;
  }
  if (response.status !== 401) return response;

  // Recover once if the token expired between the initial session check and
  // the request. This covers long-running document uploads as well.
  const { data, error } = await supabase.auth.refreshSession();
  if (error || !data.session) return response;
  const retryHeaders = new Headers(init.headers);
  retryHeaders.set("Authorization", `Bearer ${data.session.access_token}`);
  return fetch(input, { ...init, headers: retryHeaders });
}

async function readApiError(res: Response, fallback: string): Promise<Error> {
  const body = await res.json().catch(() => null);
  const message = body?.error?.message ?? body?.detail ?? fallback;
  return new Error(`${message} (HTTP ${res.status})`);
}

function getLlmProvider(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('llm_provider') || 'groq';
  }
  return 'groq';
}

function getActiveProjectId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("recallai_active_project_id");
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  organization_id: string;
  role: "OWNER" | "ADMIN" | "MANAGER" | "CONTRIBUTOR" | "VIEWER";
  permissions: string[];
  created_at?: string;
}

export interface SourceTrace {
  tool: string;
  args: Record<string, string>;
  result_preview: string;
}

export interface QueryResponse {
  question: string;
  agent_used: "QUERY" | "IMPACT";
  answer: string;
  reasoning: string;
  source_trace: SourceTrace[];
  timestamp: string;
}

export interface IngestSlackResponse {
  status: string;
  result: Record<string, unknown>;
  suggested_questions?: string[];
}

export interface ActivityEvent {
  id: string;
  type: "slack" | "gmail" | "query" | "impact" | "ingest";
  title: string;
  description: string;
  timestamp: string;
  source?: string;
  project_id?: string;
}

export interface FileMetadata {
  filename: string;
  hash: string;
  type: string;
  source: string;
  uploaded_at: string;
  project_id?: string;
}

export async function listProjects(): Promise<Project[]> {
  const res = await authenticatedFetch(`${BASE}/projects`, { cache: "no-store" });
  if (!res.ok) throw await readApiError(res, "Failed to fetch projects");
  const data = await res.json();
  return Array.isArray(data.projects) ? uniqueProjects(data.projects) : [];
}

export async function createProject(name: string): Promise<Project> {
  const res = await authenticatedFetch(`${BASE}/projects`, {
    method: "POST",
    headers: await authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw await readApiError(res, "Failed to create project");
  const data = await res.json();
  return data.project;
}

export async function updateProject(projectId: string, name: string): Promise<Project> {
  const res = await authenticatedFetch(`${BASE}/projects/${encodeURIComponent(projectId)}`, {
    method: "PATCH",
    headers: await authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw await readApiError(res, "Failed to update workspace");
  const data = await res.json();
  return data.project;
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw await readApiError(res, "Failed to delete project");
}

export function uniqueProjects(projects: Project[]): Project[] {
  const byKey = new Map<string, Project>();
  for (const project of projects) {
    const key = `${project.organization_id}:${project.slug || project.id}`;
    if (!byKey.has(key)) byKey.set(key, project);
  }
  return Array.from(byKey.values());
}

export async function getActivityFeed(userId?: string): Promise<ActivityEvent[]> {
  try {
    const url = userId ? `${BASE}/activity?user_id=${encodeURIComponent(userId)}` : `${BASE}/activity`;
    const res = await authenticatedFetch(url, { cache: 'no-store' });
    if (!res.ok) {
      console.error('Activity API error:', res.status, res.statusText);
      return [];
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Failed to fetch activity:', error);
    return [];
  }
}

export async function queryKnowledge(question: string, sourceFilter?: string): Promise<QueryResponse> {
  const res = await authenticatedFetch(`${BASE}/query`, {
    method: "POST",
    headers: await authenticatedHeaders({
      "Content-Type": "application/json",
      "x-llm-provider": getLlmProvider(),
    }),
    body: JSON.stringify({ question, source_filter: sourceFilter }),
  });
  if (!res.ok) {
    throw await readApiError(res, "Query failed");
  }
  return res.json();
}

export async function ingestSlack(
  channel_id: string,
  limit = 100,
): Promise<IngestSlackResponse> {
  const headers = await authenticatedHeaders({
    "Content-Type": "application/json",
    "x-llm-provider": getLlmProvider(),
  });
  
  const res = await authenticatedFetch(`${BASE}/ingest/slack`, {
    method: "POST",
    headers,
    body: JSON.stringify({ channel_id, limit }),
  });
  if (!res.ok) {
    throw await readApiError(res, "Slack ingest failed");
  }
  return res.json();
}

export async function ingestFile(file: File): Promise<IngestSlackResponse> {
  const form = new FormData();
  form.append("file", file);
  const headers = await authenticatedHeaders({
    "x-llm-provider": getLlmProvider(),
  });
  
  const res = await authenticatedFetch(`${BASE}/ingest/upload`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!res.ok) {
    throw await readApiError(res, "File ingest failed");
  }
  return res.json();
}

export async function ingestExcel(file: File): Promise<IngestSlackResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await authenticatedFetch(`${BASE}/ingest/upload`, {
    method: "POST",
    headers: await authenticatedHeaders({ "x-llm-provider": getLlmProvider() }),
    body: form,
  });
  if (!res.ok) {
    throw await readApiError(res, "Excel ingest failed");
  }
  return res.json();
}

export async function ingestAudio(file: File): Promise<IngestSlackResponse & { transcript?: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await authenticatedFetch(`${BASE}/ingest/audio`, {
    method: "POST",
    headers: await authenticatedHeaders({ "x-llm-provider": getLlmProvider() }),
    body: form,
  });
  if (!res.ok) {
    throw await readApiError(res, "Audio ingest failed");
  }
  return res.json();
}

export async function ingestImage(file: File): Promise<IngestSlackResponse & { extracted_text?: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await authenticatedFetch(`${BASE}/ingest/image`, {
    method: "POST",
    headers: await authenticatedHeaders({ "x-llm-provider": getLlmProvider() }),
    body: form,
  });
  if (!res.ok) {
    throw await readApiError(res, "Image ingest failed");
  }
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return false;
    const data = await res.json();
    // The API process is online even when an optional/remote dependency such
    // as Neo4j is degraded. Keep the navbar status about API reachability;
    // endpoint-specific calls will still show the storage error clearly.
    return data.api === "running" || data.status === "running" || data.status === "healthy";
  } catch (error) {
    console.error("Health check failed:", error);
    return false;
  }
}

export async function listFiles(): Promise<FileMetadata[]> {
  let res: Response | null = null;
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
  try {
    // Let authenticatedFetch handle the Authorization header internally —
    // passing headers here would call getValidSession() twice.
    res = await authenticatedFetch(`${BASE}/files/list`, { cache: 'no-store' });
    if (![502, 503, 504].includes(res.status) || attempt === 3) break;
    await new Promise((resolve) => window.setTimeout(resolve, 300 * 2 ** (attempt - 1)));
  } catch (err) {
    lastError = err;
    if (attempt === 3) break;
    await new Promise((resolve) => window.setTimeout(resolve, 300 * 2 ** (attempt - 1)));
  }
  }
  if (!res) {
    const err = lastError;
    // Re-throw auth/session errors with a recognisable prefix so
    // callers can tell them apart from genuine network failures.
    const msg = err instanceof Error ? err.message : String(err);
    if (
      msg.toLowerCase().includes('session') ||
      msg.toLowerCase().includes('sign in') ||
      msg.toLowerCase().includes('expired')
    ) {
      throw new Error(`Session error: ${msg}`);
    }
    throw err;
  }
  if (!res.ok) throw await readApiError(res, "Failed to fetch files");
  const data = await res.json();
  return Array.isArray(data.files) ? data.files : [];
}

export interface GraphNode {
  id: string;
  label: string;
  type: "Decision" | "Person" | "Reason" | "Alternative";
  source?: string;
  subject?: string;
  impact?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "MADE_BY" | "BASED_ON" | "ALTERNATIVE";
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  pagination: {
    limit: number;
    offset: number;
    returned_decisions: number;
    total_decisions: number;
    has_more: boolean;
  };
}

let graphRequest: Promise<GraphData> | null = null;

export async function getGraphData(offset = 0, limit = 100): Promise<GraphData> {
  // This also deduplicates React Strict Mode's development-only effect replay
  // and multiple mounts during navigation.
  if (graphRequest) return graphRequest;
  graphRequest = (async () => {
    let delay = 400;
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 15_000);
      try {
        const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
        const res = await authenticatedFetch(`${BASE}/graph/data?${params}`, { cache: "no-store", signal: controller.signal });
        if (res.ok) return res.json();
        const retryable = [429, 502, 503, 504].includes(res.status);
        if (!retryable || attempt === 4) throw await readApiError(res, "Failed to fetch graph data");
        console.warn(`Graph request transient failure (HTTP ${res.status}); retrying in ${delay}ms`);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const statusMatch = message.match(/HTTP (\d{3})/);
        const status = statusMatch ? Number(statusMatch[1]) : null;
        const retryable = status === null || [429, 502, 503, 504].includes(status);
        if (attempt === 4 || !retryable || message.toLowerCase().includes("session")) throw error;
        console.warn(`Graph request failed; retrying in ${delay}ms`, error);
      } finally {
        window.clearTimeout(timeout);
      }
      await new Promise((resolve) => window.setTimeout(resolve, delay));
      delay *= 2;
    }
    throw new Error("Failed to fetch graph data");
  })();
  try {
    return await graphRequest;
  } finally {
    graphRequest = null;
  }
}

export async function checkFileBySource(source: string): Promise<{ exists: boolean; file?: FileMetadata }> {
  try {
    const res = await authenticatedFetch(`${BASE}/files/check/${encodeURIComponent(source)}`);
    if (!res.ok) return { exists: false };
    return res.json();
  } catch (error) {
    console.error("Failed to check file:", error);
    return { exists: false };
  }
}

export async function deleteFile(source: string): Promise<boolean> {
  try {
    const res = await authenticatedFetch(`${BASE}/files/${encodeURIComponent(source)}`, {
      method: "DELETE",
      headers: await authenticatedHeaders(),
    });
    if (!res.ok) {
      console.error("Failed to delete file:", res.status, res.statusText);
      return false;
    }
    return true;
  } catch (error) {
    console.error("Error deleting file:", error);
    return false;
  }
}

export interface TeamsStatus { connected: boolean; provider: string; status?: string; email?: string | null; updated_at?: number | null; subscription_configured?: boolean; mock_transcripts_enabled?: boolean; }
export interface TeamsMeeting { id: string; title: string; source: string; start?: string; end?: string; synced_at?: number; }
export interface TeamsSyncResponse { status: string; count: number; mocked_count: number; meetings: unknown[]; transcript_access: "available" | "mock" | "requires_admin_consent"; message?: string; }

export async function getTeamsStatus(): Promise<TeamsStatus> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/status`, { cache: "no-store" });
  if (!res.ok) throw await readApiError(res, "Failed to load Teams status");
  return res.json();
}

export async function connectTeams(): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/connect`);
  if (!res.ok) throw await readApiError(res, "Could not start Teams connection");
  const data = await res.json();
  window.location.href = data.url;
}

export async function disconnectTeams(): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/connection`, { method: "DELETE" });
  if (!res.ok) throw await readApiError(res, "Could not disconnect Teams");
}

export async function syncTeams(): Promise<TeamsSyncResponse> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/sync`, { method: "POST", headers: await authenticatedHeaders({ "x-llm-provider": getLlmProvider() }) });
  if (!res.ok) throw await readApiError(res, "Teams sync failed");
  return res.json();
}

export async function listTeamsMeetings(): Promise<TeamsMeeting[]> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/meetings`, { cache: "no-store" });
  if (!res.ok) throw await readApiError(res, "Failed to load Teams meetings");
  const data = await res.json();
  return data.meetings ?? [];
}

export async function getTeamsMeeting(id: string): Promise<TeamsMeeting & { knowledge: Record<string, unknown>[]; participants: string[] }> {
  const res = await authenticatedFetch(`${BASE}/integrations/teams/meetings/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!res.ok) throw await readApiError(res, "Failed to load meeting details");
  return res.json();
}
