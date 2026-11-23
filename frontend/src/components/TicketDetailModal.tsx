import React, { useState } from 'react';
import { X, Check, ArrowRight, Clock, Tag, AlertOctagon } from 'lucide-react';
import { api } from '../services/api';
import { Ticket } from '../types/ticket';

interface TicketDetailModalProps {
  ticket: Ticket;
  onClose: () => void;
  onTicketUpdated: (updatedTicket: Ticket) => void;
}

const CATEGORY_OPTIONS = [
  'Access/Account',
  'Hardware',
  'Network',
  'Software',
  'Facilities',
  'Other',
];

export const TicketDetailModal: React.FC<TicketDetailModalProps> = ({
  ticket,
  onClose,
  onTicketUpdated,
}) => {
  const [selectedStatus, setSelectedStatus] = useState(ticket.status);
  const [selectedCategory, setSelectedCategory] = useState(ticket.effective_category);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = async () => {
    try {
      setSaving(true);
      const updates: { status?: string; corrected_category?: string } = {};

      if (selectedStatus !== ticket.status) {
        updates.status = selectedStatus;
      }

      if (selectedCategory !== ticket.effective_category) {
        updates.corrected_category = selectedCategory;
      }

      if (Object.keys(updates).length > 0) {
        const updated = await api.updateTicket(ticket.id, updates);
        setSaveSuccess(true);
        setTimeout(() => {
          onTicketUpdated(updated);
          onClose();
        }, 600);
      } else {
        onClose();
      }
    } catch (err) {
      console.error('Failed to update ticket:', err);
    } finally {
      setSaving(false);
    }
  };

  const getPriorityColor = (prio: string) => {
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
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full shadow-xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-bold">
              #{ticket.id}
            </span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase border ${getPriorityColor(
                ticket.predicted_priority
              )}`}
            >
              {ticket.predicted_priority} Priority
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6">
          {/* Title & Description */}
          <div>
            <h3 className="text-xl font-bold text-slate-900">{ticket.title}</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200 whitespace-pre-wrap">
              {ticket.description}
            </p>
          </div>

          {/* ML Triage Info Card */}
          <div className="bg-sky-50/70 p-4 rounded-xl border border-sky-100 space-y-3">
            <div className="text-xs font-bold text-sky-900 uppercase tracking-wider flex items-center space-x-1.5">
              <Tag className="w-3.5 h-3.5 text-sky-600" />
              <span>Machine Learning Classification Metadata</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-500">Predicted Category:</span>
                <span className="ml-1.5 font-bold text-slate-900">{ticket.predicted_category}</span>
                <span className="ml-1 text-sky-700 font-medium">
                  ({(ticket.category_confidence * 100).toFixed(1)}% conf.)
                </span>
              </div>
              <div>
                <span className="text-slate-500">Predicted Priority:</span>
                <span className="ml-1.5 font-bold text-slate-900">{ticket.predicted_priority}</span>
                <span className="ml-1 text-sky-700 font-medium">
                  ({(ticket.priority_confidence * 100).toFixed(1)}% conf.)
                </span>
              </div>
            </div>

            {ticket.corrected_category && (
              <div className="text-xs bg-amber-50 border border-amber-200 p-2.5 rounded-lg text-amber-800 flex items-center space-x-1.5">
                <AlertOctagon className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>
                  Corrected by agent from <b>{ticket.predicted_category}</b> to{' '}
                  <b>{ticket.corrected_category}</b> (Stored as model retraining feedback).
                </span>
              </div>
            )}
          </div>

          {/* Interactive Agent Triage Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
            {/* Status Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1.5">
                Workflow Status
              </label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value as any)}
                className="w-full text-sm rounded-xl border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            {/* Human Category Feedback Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1.5">
                Category Feedback / Correction
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full text-sm rounded-xl border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {CATEGORY_OPTIONS.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat} {cat === ticket.predicted_category ? '(ML Predicted)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Timestamps */}
          <div className="flex items-center space-x-4 text-xs text-slate-400">
            <span className="flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Created: {new Date(ticket.created_at).toLocaleString()}</span>
            </span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end items-center space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center space-x-2 px-5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-sm shadow-sm transition-colors disabled:opacity-50"
          >
            {saveSuccess ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Saved!</span>
              </>
            ) : (
              <>
                <span>Save Changes</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
