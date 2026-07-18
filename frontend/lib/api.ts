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
}

export interface FileMetadata {
  filename: string;
  hash: string;
  type: string;
  source: string;
  uploaded_at: string;
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
  let res: Response;
  try {
    // Let authenticatedFetch handle the Authorization header internally —
    // passing headers here would call getValidSession() twice.
    res = await authenticatedFetch(`${BASE}/files/list`, { cache: 'no-store' });
  } catch (err) {
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
}

export async function getGraphData(): Promise<GraphData> {
  const res = await authenticatedFetch(`${BASE}/graph/data`, { cache: "no-store" });
  if (!res.ok) throw await readApiError(res, "Failed to fetch graph data");
  return res.json();
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
