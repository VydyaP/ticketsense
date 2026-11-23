import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardStats } from '../components/DashboardStats';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getStats: vi.fn(),
    getModelMetrics: vi.fn(),
  },
}));

describe('DashboardStats Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders KPI summary cards and model evaluation benchmark', async () => {
    (api.getStats as any).mockResolvedValueOnce({
      total_tickets: 42,
      total_corrections: 2,
      feedback_accuracy_rate: 95.2,
      status_counts: { open: 15, in_progress: 10, resolved: 17 },
      category_counts: { Network: 18, Hardware: 14, 'Access/Account': 10 },
      priority_counts: { High: 12, Medium: 20, Low: 10 },
    });

    (api.getModelMetrics as any).mockResolvedValueOnce({
      dataset: {
        name: 'Public IT Helpdesk Support Dataset',
        license: 'MIT License',
        source: 'https://example.com',
        total_samples: 48545,
        train_samples: 38836,
        test_samples: 9709,
      },
      category_model: {
        algorithm: 'TF-IDF + Logistic Regression',
        accuracy: 0.8397,
        macro_f1: 0.6519,
        weighted_f1: 0.8514,
        classes: ['Access/Account', 'Hardware', 'Network'],
        per_class: {
          Network: { precision: 0.408, recall: 0.738, f1_score: 0.525, support: 526 },
        },
      },
      priority_model: {
        algorithm: 'TF-IDF + Logistic Regression',
        accuracy: 0.8815,
        macro_f1: 0.7432,
        weighted_f1: 0.883,
        classes: ['High', 'Medium', 'Low'],
        per_class: {
          High: { precision: 0.715, recall: 0.679, f1_score: 0.697, support: 1703 },
        },
      },
    });

    render(<DashboardStats />);

    expect(await screen.findByText('Total Logged')).toBeInTheDocument();
    expect(await screen.findByText('42')).toBeInTheDocument();
    expect(await screen.findByText('Active Queue')).toBeInTheDocument();
    expect(await screen.findByText('ML Acceptance')).toBeInTheDocument();
    expect(await screen.findByText('NLP Model Benchmark & Evaluation')).toBeInTheDocument();
  });
});
