/**
 * api.ts
 * BankQueue API Client for https://queue-wiz-home.lovable.app
 * Connects the Lovable frontend UI to the Python (FastAPI) or Java backend.
 */

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface BankService {
  id: number;
  code: string;
  name: string;
  description: string;
  estimated_time: string;
  duration_minutes: number;
  prefix: string;
  icon: string;
}

export interface CounterStatus {
  id: number;
  name: string;
  desk_label: string;
  description: string;
  status: "ONLINE" | "BUSY" | "PAUSED" | "OFFLINE";
  staff_name: string;
  current_token_number: string | null;
  waiting_count: number;
}

export interface LiveQueueData {
  total_waiting: number;
  total_served_today: number;
  active_counters_count: number;
  average_wait_minutes: number;
  counters: CounterStatus[];
  now_serving: Array<{
    token_number: string;
    customer_name?: string;
    counter_name: string;
    desk_label: string;
  }>;
  upcoming_tokens: Array<{
    token_number: string;
    customer_name: string;
    service_name: string;
    counter_name: string;
    status: string;
    estimated_wait_minutes: number;
    recommended_arrival_time: string;
    time_slot: string;
  }>;
  recent_updates: Array<{
    id: string;
    text: string;
    timestamp: string;
  }>;
}

export interface BookTokenPayload {
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  customer_account_number?: string;
  service_id: number;
  booking_date: string;
  time_slot: string;
}

export interface TokenResponse {
  id: number;
  token_number: string;
  service_id: number;
  service_name: string;
  customer_name: string;
  customer_phone: string;
  booking_date: string;
  time_slot: string;
  status: string;
  counter_name: string;
  desk_label: string;
  people_ahead: number;
  estimated_wait_minutes: number;
  recommended_arrival_time: string;
  created_at: string;
}

export interface TokenTrackingResponse {
  token_number: string;
  service_name: string;
  customer_name: string;
  status: string;
  counter_name: string;
  desk_label: string;
  people_ahead: number;
  estimated_wait_minutes: number;
  recommended_arrival_time: string;
  notice: string;
  booking_date: string;
  time_slot: string;
}

export const bankApi = {
  // 1. Fetch all banking services (/services)
  async getServices(): Promise<BankService[]> {
    const res = await fetch(`${BACKEND_URL}/api/v1/services`);
    if (!res.ok) throw new Error("Failed to load services");
    return res.json();
  },

  // 2. Fetch live queue status (/live-queue)
  async getLiveQueue(): Promise<LiveQueueData> {
    const res = await fetch(`${BACKEND_URL}/api/v1/queue/live`);
    if (!res.ok) throw new Error("Failed to load live queue");
    return res.json();
  },

  // 3. Book a new token (/get-token)
  async bookToken(payload: BookTokenPayload): Promise<TokenResponse> {
    const res = await fetch(`${BACKEND_URL}/api/v1/tokens/book`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to book token");
    }
    return res.json();
  },

  // 4. Track token status (/check-token)
  async trackToken(tokenNumber: string): Promise<TokenTrackingResponse> {
    const res = await fetch(`${BACKEND_URL}/api/v1/tokens/track/${encodeURIComponent(tokenNumber.trim().toUpperCase())}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Token not found. Please verify your token number.");
    }
    return res.json();
  },

  // 5. Submit contact message (/contact)
  async submitContact(payload: { name: string; email: string; message: string }): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${BACKEND_URL}/api/v1/contact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to submit message");
    return res.json();
  },

  // 6. Connect to live WebSocket stream
  connectWebSocket(onMessage: (data: any) => void): WebSocket {
    const wsUrl = BACKEND_URL.replace(/^http/, "ws") + "/ws";
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("WebSocket message parse error", e);
      }
    };
    return ws;
  }
};
