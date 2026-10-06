const API = "/backend";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(init.headers || {}),
      },
    });
  } catch {
    throw new ApiError(503, "NOT_READY", "Waking the city servers…");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.error?.code || "ERROR", errorMessage(data, res.statusText));
  return data as T;
}

function errorMessage(data: { error?: { message?: string }; detail?: unknown }, fallback: string) {
  if (data?.error?.message) return data.error.message;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail) && data.detail[0]?.msg) return String(data.detail[0].msg);
  return fallback;
}

export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.error?.code || "ERROR", errorMessage(data, res.statusText));
  return data as T;
}

export type Me = { user: { id: string; email: string; role: string } };
export type Ticket = {
  public_id: string;
  status: string;
  type: string;
  severity?: string;
  lat: number;
  lng: number;
  neighborhood: string;
  circle?: string;
  circle_label?: string;
  ward?: string;
  title: string;
  body: string;
  confirmation_count: number;
  days_open?: number;
  created_at: string | null;
  resolve_note: string | null;
  media: { id: string; url: string; kind?: string }[];
  timeline?: { type: string; at: string | null }[];
  nearby?: (Ticket & { meters: number })[];
};
