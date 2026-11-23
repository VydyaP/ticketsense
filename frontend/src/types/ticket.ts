export interface Ticket {
  id: number;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  predicted_category: string;
  category_confidence: number;
  predicted_priority: 'Low' | 'Medium' | 'High';
  priority_confidence: number;
  corrected_category: string | null;
  effective_category: string;
  category_probabilities?: Record<string, number>;
  priority_probabilities?: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PredictionResult {
  category: string;
  category_confidence: number;
  category_probabilities: Record<string, number>;
  priority: 'Low' | 'Medium' | 'High';
  priority_confidence: number;
  priority_probabilities: Record<string, number>;
}

export interface TicketStats {
  total_tickets: number;
  total_corrections: number;
  feedback_accuracy_rate: number;
  status_counts: Record<string, number>;
  category_counts: Record<string, number>;
  priority_counts: Record<string, number>;
}

export interface ModelMetrics {
  dataset: {
    name: string;
    license: string;
    source: string;
    total_samples: number;
    train_samples: number;
    test_samples: number;
  };
  category_model: {
    algorithm: string;
    accuracy: number;
    macro_f1: number;
    weighted_f1: number;
    classes: string[];
    per_class: Record<string, { precision: number; recall: number; f1_score: number; support: number }>;
  };
  priority_model: {
    algorithm: string;
    accuracy: number;
    macro_f1: number;
    weighted_f1: number;
    classes: string[];
    per_class: Record<string, { precision: number; recall: number; f1_score: number; support: number }>;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  database: string;
  model_loaded: boolean;
  version: string;
  timestamp: string;
}
