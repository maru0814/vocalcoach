const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type RecordingListItem = {
  id: number;
  title: string;
  total_score: number | null;
  created_at: string;
};

export type RecordingDetail = {
  id: number;
  title: string;
  note: string | null;
  status: string;
  created_at: string;
  evaluation: {
    pitch_score: number;
    rhythm_score: number;
    expression_score: number;
    total_score: number;
    feedback_text: string;
    created_at: string;
  } | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

/** ログイン状態の確認。未ログインなら例外（401）。 */
export async function getMe() {
  return request<{ user_id: number; email: string }>("/api/v1/auth/me");
}

export async function register(email: string, password: string) {
  return request<{ user_id: number }>("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string) {
  return request<{ access_token: string }>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function uploadRecording(formData: FormData) {
  return request<{ recording_id: number; status: string }>("/api/v1/recordings", {
    method: "POST",
    body: formData,
  });
}

export type RecordingListResponse = {
  items: RecordingListItem[];
  locked_count: number;
};

export async function listRecordings() {
  return request<RecordingListResponse>("/api/v1/recordings");
}

/** アップロード時の402(上限到達)を判定するためのエラー型 */
export class LimitReachedError extends Error {}

export async function uploadRecordingChecked(formData: FormData) {
  try {
    return await uploadRecording(formData);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (msg.includes("LIMIT_REACHED")) throw new LimitReachedError("LIMIT_REACHED");
    throw err;
  }
}

export type PaywallSource = "limit" | "report" | "history";

export async function logPaywallEvent(
  event: "paywall_view" | "paywall_click" | "checkout_start",
  source: PaywallSource,
) {
  try {
    await request("/api/v1/billing/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, source }),
    });
  } catch {
    /* 計測失敗はUXに影響させない */
  }
}

export async function getRecording(id: string | number) {
  return request<RecordingDetail>(`/api/v1/recordings/${id}`);
}

// ---------- Coach (chat) ----------
export const COACH_API_BASE = API_BASE;

export type CoachMessage = {
  id: number;
  role: "coach" | "user";
  type: "text" | "audio" | "feedback" | "practice" | "judge" | "progress" | "diagnosis";
  text?: string | null;
  audio_url?: string | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
};

export type ChatResponse = {
  phase: string;
  current_task: string | null;
  messages: CoachMessage[];
};

export type SessionSummary = {
  id: number;
  song_title: string | null;
  phase: string;
  current_task: string | null;
  updated_at: string;
};

export type SessionDetail = {
  id: number;
  song_title: string | null;
  song_ref_url: string | null;
  user_range: string | null;
  phase: string;
  current_task: string | null;
  has_reference: boolean;
  messages: CoachMessage[];
};

export async function createCoachSession() {
  return request<ChatResponse>("/api/v1/coach/sessions", { method: "POST" });
}

export async function listCoachSessions() {
  return request<SessionSummary[]>("/api/v1/coach/sessions");
}

export async function getCoachSession(id: string | number) {
  return request<SessionDetail>(`/api/v1/coach/sessions/${id}`);
}

export async function renameCoachSession(id: string | number, songTitle: string) {
  return request<SessionSummary>(`/api/v1/coach/sessions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ song_title: songTitle }),
  });
}

export async function sendCoachText(id: string | number, text: string) {
  return request<ChatResponse>(`/api/v1/coach/sessions/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function sendCoachAudio(
  id: string | number,
  blob: Blob,
  kind: "song" | "practice" | "auto",
  filename = "recording.webm",
  comment?: string,
) {
  const fd = new FormData();
  fd.append("audio_file", blob, filename);
  fd.append("kind", kind);
  if (comment) fd.append("comment", comment);
  return request<ChatResponse>(`/api/v1/coach/sessions/${id}/audio`, {
    method: "POST",
    body: fd,
  });
}

export async function uploadCoachReference(
  id: string | number,
  file: Blob,
  filename = "reference.mp3",
) {
  const fd = new FormData();
  fd.append("audio_file", file, filename);
  return request<ChatResponse>(`/api/v1/coach/sessions/${id}/reference`, {
    method: "POST",
    body: fd,
  });
}

export async function submitMessageFeedback(
  sessionId: string | number,
  messageId: number,
  rating: "up" | "down",
  reason?: string,
  comment?: string,
) {
  return request<{ ok: boolean; rating: string }>(
    `/api/v1/coach/sessions/${sessionId}/messages/${messageId}/feedback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, reason, comment }),
    },
  );
}

export async function sendCoachAction(id: string | number, action: string) {
  return request<ChatResponse>(`/api/v1/coach/sessions/${id}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}

// ---------- Voice Type（独立機能：声タイプ診断） ----------
export type VoiceType = {
  id: string;
  name: string;
  emoji: string;
  desc: string;
  artists?: { female?: string[]; male?: string[] };
  axes_jp?: { register?: string; power?: string; color?: string };
  near?: { register?: boolean; power?: boolean; color?: boolean };
};

export type VoiceTypeResult = {
  voice_type: VoiceType;
  score: number;
  scores?: Record<string, number>;
  duration_sec?: number;
};

export type VoiceTypeStats = {
  total: number;
  distribution: { id: string; name: string; count: number; pct: number }[];
  top: { id: string; name: string; count: number } | null;
};

/** 社会的証明用の集計（累計件数・タイプ分布）。公開・認証不要。 */
export async function getVoiceTypeStats() {
  return request<VoiceTypeStats>("/api/v1/voice-type/stats");
}

/** 録音1本を送って声タイプ（8種）を診断。チャットセッション非依存。 */
export async function analyzeVoiceType(blob: Blob, filename = "voice.webm") {
  const fd = new FormData();
  fd.append("audio_file", blob, filename);
  const response = await fetch(`${API_BASE}/api/v1/voice-type/analyze`, {
    method: "POST",
    credentials: "include",
    body: fd,
  });
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data?.message || data?.detail?.message || message;
    } catch {
      /* ignore parse error */
    }
    const err = new Error(message) as Error & { status?: number };
    err.status = response.status;
    throw err;
  }
  return (await response.json()) as VoiceTypeResult;
}

// --- 詳細添削レポート（有料・docs/31 FR-04） ---

export type ReportIssue = { time: string | null; observation: string; cause: string };
export type PracticeDay = { day: number; title: string; steps: string };
export type DetailedReport = {
  issues: ReportIssue[];
  priority: string;
  practice_menu: PracticeDay[];
  next_checks: string[];
};
export type ReportResponse = {
  status: "none" | "generating" | "failed" | "ready";
  report: DetailedReport | null;
};

export async function startReport(recordingId: string | number) {
  return request<{ status: string }>(`/api/v1/recordings/${recordingId}/report`, {
    method: "POST",
  });
}

export async function getReport(recordingId: string | number) {
  return request<ReportResponse>(`/api/v1/recordings/${recordingId}/report`);
}

export type BillingMe = {
  billing_enabled: boolean;
  plan: "free" | "premium";
  period_end: string | null;
  analysis_used: number;
  analysis_limit: number | null;
};

export async function getBillingMe() {
  return request<BillingMe>("/api/v1/billing/me");
}

// --- Stripe決済（docs/31 FR-02/03） ---

export async function startCheckout() {
  return request<{ url: string }>("/api/v1/billing/checkout", { method: "POST" });
}

export async function openPortal() {
  return request<{ url: string }>("/api/v1/billing/portal", { method: "POST" });
}
