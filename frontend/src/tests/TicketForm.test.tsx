import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TicketForm } from '../components/TicketForm';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    predictTicket: vi.fn(),
    createTicket: vi.fn(),
  },
}));

describe('TicketForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders title, description inputs and submit button', () => {
    render(<TicketForm onTicketCreated={vi.fn()} />);

    expect(screen.getByLabelText(/ticket title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/issue description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit ticket/i })).toBeInTheDocument();
  });

  it('populates fields when a quick template is clicked', () => {
    render(<TicketForm onTicketCreated={vi.fn()} />);

    const templateBtn = screen.getByText(/VPN Drop/i);
    fireEvent.click(templateBtn);

    const titleInput = screen.getByLabelText(/ticket title/i) as HTMLInputElement;
    expect(titleInput.value).toContain('VPN');
  });

  it('submits ticket and triggers onTicketCreated callback', async () => {
    const mockOnCreated = vi.fn();
    (api.createTicket as any).mockResolvedValueOnce({
      id: 1,
      title: 'Valid Ticket Title',
      description: 'Valid issue description text',
      status: 'open',
      predicted_category: 'Network',
      category_confidence: 0.95,
      predicted_priority: 'High',
      priority_confidence: 0.88,
    });

    render(<TicketForm onTicketCreated={mockOnCreated} />);

    fireEvent.change(screen.getByLabelText(/ticket title/i), {
      target: { value: 'Valid Ticket Title' },
    });
    fireEvent.change(screen.getByLabelText(/issue description/i), {
      target: { value: 'Valid issue description text' },
    });

    fireEvent.click(screen.getByRole('button', { name: /submit ticket/i }));

    await waitFor(() => {
      expect(api.createTicket).toHaveBeenCalledWith(
        'Valid Ticket Title',
        'Valid issue description text'
      );
    });
  });
});
