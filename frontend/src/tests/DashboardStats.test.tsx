import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardStats } from "../components/DashboardStats";
import { api } from "../services/api";

vi.mock("../services/api", () => ({
  api: {
    getStats: vi.fn(),
    getModelMetrics: vi.fn(),
  },
}));

describe("DashboardStats Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders KPI summary cards and model evaluation benchmark", async () => {
    vi.mocked(api.getStats).mockResolvedValueOnce({
      total_tickets: 42,
      total_corrections: 2,
      uncorrected_rate: 95.2,
      status_counts: { open: 15, in_progress: 10, resolved: 17 },
      category_counts: {
        "Hardware & Equipment": 18,
        "Accounts & Applications": 24,
      },
      priority_counts: { High: 12, Medium: 20, Low: 10 },
    });

    const report = {
      algorithm: "TF-IDF + Logistic Regression",
      accuracy: 0.8487,
      macro_f1: 0.6306,
      weighted_f1: 0.8588,
      baseline_majority_class: { accuracy: 0.7015, macro_f1: 0.1178 },
      classes: ["Hardware & Equipment"],
      per_class: {
        "Hardware & Equipment": {
          precision: 0.79,
          recall: 0.81,
          f1_score: 0.8,
          support: 1926,
        },
      },
    };
    vi.mocked(api.getModelMetrics).mockResolvedValueOnce({
      dataset: {
        name: "Endava IT support tickets (anonymized)",
        original_source:
          "https://github.com/karolzak/support-tickets-classification",
        original_license: "MIT",
        total_samples: 48545,
        train_samples: 38836,
        test_samples: 9709,
        label_note:
          "Category names are our interpretation of anonymized codes.",
      },
      category_model: report,
      priority_model: { ...report, classes: ["High", "Medium", "Low"] },
    });

    render(<DashboardStats />);

    expect(await screen.findByText("Total Logged")).toBeInTheDocument();
    expect(await screen.findByText("42")).toBeInTheDocument();
    expect(await screen.findByText("Active Queue")).toBeInTheDocument();
    expect(await screen.findByText("Uncorrected")).toBeInTheDocument();
    expect(await screen.findByText("95.2%")).toBeInTheDocument();
    expect(await screen.findByText(/most common category/)).toBeInTheDocument();
    expect(
      await screen.findByText("NLP Model Benchmark & Evaluation"),
    ).toBeInTheDocument();
  });
});
