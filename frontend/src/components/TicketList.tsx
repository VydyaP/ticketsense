import React, { useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight, Eye, RefreshCw, Filter } from 'lucide-react';
import { api } from '../services/api';
import { Ticket } from '../types/ticket';
import { TicketDetailModal } from './TicketDetailModal';

export const TicketList: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  // Selected for modal
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  const fetchTickets = React.useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getTickets({
        page,
        page_size: 10,
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        search: search.trim() || undefined,
      });
      setTickets(res.items);
      setTotalPages(res.total_pages);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, categoryFilter, priorityFilter, search]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTickets();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'in_progress':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'resolved':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'closed':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case 'High':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Medium':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Low':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 justify-between items-center">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tickets by title or issue..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 placeholder:text-slate-400"
          />
        </form>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500 mr-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-300 px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-300 px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="">All Categories</option>
            <option value="Access/Account">Access/Account</option>
            <option value="Hardware">Hardware</option>
            <option value="Network">Network</option>
            <option value="Software">Software</option>
            <option value="Facilities">Facilities</option>
            <option value="Other">Other</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-300 px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="">All Priorities</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          <button
            onClick={() => {
              setSearch('');
              setStatusFilter('');
              setCategoryFilter('');
              setPriorityFilter('');
              setPage(1);
              fetchTickets();
            }}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tickets Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3.5">ID</th>
                <th className="px-5 py-3.5">Title & Subject</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Category (Triage)</th>
                <th className="px-5 py-3.5">Priority</th>
                <th className="px-5 py-3.5">ML Conf.</th>
                <th className="px-5 py-3.5">Created</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-5 py-12 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-sky-500" />
                    <span>Loading tickets queue...</span>
                  </td>
                </tr>
              ) : tickets.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-12 text-center text-slate-400">
                    No tickets found matching your query.
                  </td>
                </tr>
              ) : (
                tickets.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-slate-500">
                      #{t.id}
                    </td>
                    <td className="px-5 py-3.5 font-medium text-slate-900 max-w-xs truncate">
                      {t.title}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${getStatusBadge(
                          t.status
                        )}`}
                      >
                        {t.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-xs text-slate-800">
                          {t.effective_category}
                        </span>
                        {t.corrected_category && (
                          <span
                            className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded font-medium"
                            title={`Corrected from ${t.predicted_category}`}
                          >
                            Edited
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-bold uppercase border ${getPriorityBadge(
                          t.predicted_priority
                        )}`}
                      >
                        {t.predicted_priority}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-xs text-slate-500 font-mono">
                      {(t.category_confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-xs text-slate-500">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-right">
                      <button
                        onClick={() => setSelectedTicket(t)}
                        className="inline-flex items-center space-x-1 text-xs text-sky-600 hover:text-sky-800 font-semibold px-2 py-1 rounded-md hover:bg-sky-50 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Triage</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-5 py-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
          <div>
            Showing <span className="font-bold text-slate-700">{tickets.length}</span> of{' '}
            <span className="font-bold text-slate-700">{total}</span> total tickets
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded border border-slate-300 hover:bg-white disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-medium text-slate-700">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded border border-slate-300 hover:bg-white disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Ticket Details Modal */}
      {selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          onClose={() => setSelectedTicket(null)}
          onTicketUpdated={() => {
            fetchTickets();
          }}
        />
      )}
    </div>
  );
};
