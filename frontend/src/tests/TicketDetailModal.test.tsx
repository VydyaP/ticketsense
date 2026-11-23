import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TicketDetailModal } from "../components/TicketDetailModal";
import { api } from "../services/api";
import { Ticket } from "../types/ticket";

vi.mock("../services/api", () => ({
  api: { getCategories: vi.fn(), updateTicket: vi.fn() },
}));

const ticket: Ticket = {
  id: 7,
  title: "Monitor request",
  description: "Please provide a second monitor",
  status: "open",
  predicted_category: "Hardware & Equipment",
  category_confidence: 0.91,
  predicted_priority: "Low",
  priority_confidence: 0.88,
  corrected_category: null,
  effective_category: "Hardware & Equipment",
  created_at: "2026-11-23T10:00:00Z",
  updated_at: "2026-11-23T10:00:00Z",
};

describe("TicketDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCategories).mockResolvedValue([
      "Hardware & Equipment",
      "Procurement & Quotes",
    ]);
  });

  it("offers the model categories from the API and sends a correction", async () => {
    vi.mocked(api.updateTicket).mockResolvedValueOnce({
      ...ticket,
      corrected_category: "Procurement & Quotes",
      effective_category: "Procurement & Quotes",
    });
    render(
      <TicketDetailModal
        ticket={ticket}
        onClose={vi.fn()}
        onTicketUpdated={vi.fn()}
      />,
    );

    const select = screen.getByLabelText(/Category Feedback/i);
    await screen.findByRole("option", { name: "Procurement & Quotes" });
    fireEvent.change(select, { target: { value: "Procurement & Quotes" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    expect(api.updateTicket).toHaveBeenCalledWith(7, {
      corrected_category: "Procurement & Quotes",
    });
  });

  it("shows the API error message when saving fails", async () => {
    vi.mocked(api.updateTicket).mockRejectedValueOnce(
      new Error("Unknown category"),
    );
    render(
      <TicketDetailModal
        ticket={ticket}
        onClose={vi.fn()}
        onTicketUpdated={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Workflow Status/i), {
      target: { value: "resolved" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unknown category",
    );
  });
});
