// Typed client for the backend. The browser calls the backend directly, so the
// base URL is a public (browser-visible) env var. Nothing here knows the game
// rules — it only relays what GET /api/challenge returns.

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ChallengePublic {
  title: string;
  tagline: string;
  instructions_vi: string;
  instructions_en: string;
  max_attempts: number;
}

export interface SessionInfo {
  session_id: string;
  player_id: string;
  max_attempts: number;
  attempts_remaining: number;
}

export type SessionStatus = "active" | "won" | "lost";

export interface ChatResult {
  reply: string;
  recommendation: string | null;
  success: boolean;
  status: SessionStatus;
  attempt: number;
  attempts_remaining: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Không kết nối được tới máy chủ. Kiểm tra kết nối mạng.");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

export const api = {
  getChallenge: () => request<ChallengePublic>("/api/challenge"),

  createSession: (nickname?: string) =>
    request<SessionInfo>("/api/session", {
      method: "POST",
      body: JSON.stringify({ nickname: nickname?.trim() || null }),
    }),

  chat: (sessionId: string, prompt: string) =>
    request<ChatResult>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, prompt }),
    }),
};
