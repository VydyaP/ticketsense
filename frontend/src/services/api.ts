import {
  HealthStatus,
  ModelMetrics,
  PredictionResult,
  Ticket,
  TicketListResponse,
  TicketStats,
} from "../types/ticket";

const API_BASE = import.meta.env.VITE_API_URL || "";

/** Turn a FastAPI error body into a readable message (422 bodies hold a list of errors). */
async function errorMessage(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({}));
  if (Array.isArray(body.detail))
    return body.detail.map((d: { msg: string }) => d.msg).join("; ");
  return typeof body.detail === "string"
    ? body.detail
    : `${fallback} (HTTP ${res.status})`;
}

let metricsPromise: Promise<ModelMetrics> | null = null;

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async predictTicket(
    title: string,
    description: string,
  ): Promise<PredictionResult> {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    if (!res.ok)
      throw new Error(await errorMessage(res, "Prediction request failed"));
    return res.json();
  },

  async createTicket(title: string, description: string): Promise<Ticket> {
    const res = await fetch(`${API_BASE}/api/tickets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    if (!res.ok)
      throw new Error(await errorMessage(res, "Failed to submit ticket"));
    return res.json();
  },

  async getTickets(params: {
    status?: string;
    category?: string;
    priority?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<TicketListResponse> {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.category) query.set("category", params.category);
    if (params.priority) query.set("priority", params.priority);
    if (params.search) query.set("search", params.search);
    if (params.page) query.set("page", params.page.toString());
    if (params.page_size) query.set("page_size", params.page_size.toString());

    const res = await fetch(`${API_BASE}/api/tickets?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch tickets");
    return res.json();
  },

  async updateTicket(
    id: number,
    updates: { status?: string; corrected_category?: string },
  ): Promise<Ticket> {
    const res = await fetch(`${API_BASE}/api/tickets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok)
      throw new Error(await errorMessage(res, "Failed to update ticket"));
    return res.json();
  },

  async getStats(): Promise<TicketStats> {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error("Failed to fetch statistics");
    return res.json();
  },

  /** Metrics never change while the server runs, so fetch once and share the result. */
  getModelMetrics(): Promise<ModelMetrics> {
    if (!metricsPromise) {
      metricsPromise = fetch(`${API_BASE}/api/model/metrics`).then(
        async (res) => {
          if (!res.ok) {
            metricsPromise = null; // allow a retry later
            throw new Error(
              await errorMessage(res, "Failed to fetch model metrics"),
            );
          }
          return res.json();
        },
      );
    }
    return metricsPromise;
  },

  /** The categories the model can predict: the single source of truth for dropdowns. */
  async getCategories(): Promise<string[]> {
    return (await api.getModelMetrics()).category_model.classes;
  },
};
