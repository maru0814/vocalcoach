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

export async function listRecordings() {
  return request<RecordingListItem[]>("/api/v1/recordings");
}

export async function getRecording(id: string | number) {
  return request<RecordingDetail>(`/api/v1/recordings/${id}`);
}
