import {
  HealthStatus,
  ModelMetrics,
  PredictionResult,
  Ticket,
  TicketListResponse,
  TicketStats,
} from '../types/ticket';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async predictTicket(title: string, description: string): Promise<PredictionResult> {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description }),
    });
    if (!res.ok) throw new Error('Prediction request failed');
    return res.json();
  },

  async createTicket(title: string, description: string): Promise<Ticket> {
    const res = await fetch(`${API_BASE}/api/tickets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.[0]?.msg || err.detail || 'Failed to submit ticket');
    }
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
    if (params.status) query.set('status', params.status);
    if (params.category) query.set('category', params.category);
    if (params.priority) query.set('priority', params.priority);
    if (params.search) query.set('search', params.search);
    if (params.page) query.set('page', params.page.toString());
    if (params.page_size) query.set('page_size', params.page_size.toString());

    const res = await fetch(`${API_BASE}/api/tickets?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch tickets');
    return res.json();
  },

  async updateTicket(
    id: number,
    updates: { status?: string; corrected_category?: string }
  ): Promise<Ticket> {
    const res = await fetch(`${API_BASE}/api/tickets/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update ticket');
    return res.json();
  },

  async getStats(): Promise<TicketStats> {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error('Failed to fetch statistics');
    return res.json();
  },

  async getModelMetrics(): Promise<ModelMetrics> {
    const res = await fetch(`${API_BASE}/api/model/metrics`);
    if (!res.ok) throw new Error('Failed to fetch model metrics');
    return res.json();
  },
};
