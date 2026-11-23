import React, { useState, useEffect } from 'react';
import { Sparkles, Send, RefreshCw, AlertCircle, Check } from 'lucide-react';
import { api } from '../services/api';
import { PredictionResult } from '../types/ticket';

interface TicketFormProps {
  onTicketCreated: () => void;
}

const SAMPLE_TEMPLATES = [
  {
    label: 'VPN Drop (Network)',
    title: 'Pulse Secure VPN disconnects every 10 minutes',
    desc: 'Whenever I connect to the office gateway from home, the connection drops packet loss ping to intranet hosts fails.',
  },
  {
    label: 'Password Reset (Access)',
    title: 'Locked out of Oracle ERP account',
    desc: 'Password expired over the weekend and repeated login attempts have locked my corporate access profile.',
  },
  {
    label: 'Monitor Issue (Hardware)',
    title: 'Dual monitor screen flickering after docking station update',
    desc: 'Dell USB-C dock is causing secondary display to go black intermittently. Need new HDMI or DisplayPort cable.',
  },
  {
    label: 'Badge Access (Facilities)',
    title: 'Employee ID keycard not working at 4th floor turnstile',
    desc: 'Security card reader beeps red when scanning my badge at building main entrance and office floor entrance.',
  },
];

export const TicketForm: React.FC<TicketFormProps> = ({ onTicketCreated }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Debounced auto-preview when user types enough characters
  useEffect(() => {
    if (title.trim().length >= 5 && description.trim().length >= 10) {
      const handler = setTimeout(async () => {
        try {
          setPreviewing(true);
          const res = await api.predictTicket(title, description);
          setPrediction(res);
        } catch {
          // Silent catch for auto-preview
        } finally {
          setPreviewing(false);
        }
      }, 500);
      return () => clearTimeout(handler);
    } else {
      setPrediction(null);
    }
  }, [title, description]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim().length < 3) {
      setError('Title must be at least 3 characters long');
      return;
    }
    if (description.trim().length < 5) {
      setError('Description must be at least 5 characters long');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await api.createTicket(title, description);
      setSuccess(true);
      setTitle('');
      setDescription('');
      setPrediction(null);
      setTimeout(() => {
        setSuccess(false);
        onTicketCreated();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to submit ticket');
    } finally {
      setSubmitting(false);
    }
  };

  const loadTemplate = (tmpl: { title: string; desc: string }) => {
    setTitle(tmpl.title);
    setDescription(tmpl.desc);
    setError(null);
  };

  const getPriorityBadgeColor = (prio: string) => {
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
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold">Submit Support Ticket</h2>
            <p className="text-xs text-slate-300 mt-0.5">
              Natural Language Processing automatically classifies category and priority in real-time.
            </p>
          </div>
          <div className="flex items-center space-x-1.5 text-xs text-sky-400 bg-sky-950/60 px-3 py-1.5 rounded-lg border border-sky-800/50">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            <span>AI Triage Active</span>
          </div>
        </div>

        {/* Quick Demo Templates */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Quick Templates:</span>
          {SAMPLE_TEMPLATES.map((tmpl, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => loadTemplate(tmpl)}
              className="text-xs bg-white hover:bg-sky-50 text-slate-700 hover:text-sky-700 border border-slate-200 hover:border-sky-300 px-2.5 py-1 rounded-md transition-colors"
            >
              {tmpl.label}
            </button>
          ))}
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center space-x-2">
              <Check className="w-4 h-4 flex-shrink-0 text-emerald-600" />
              <span>Ticket created successfully! Redirecting to ticket queue...</span>
            </div>
          )}

          <div>
            <label htmlFor="ticket-title" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Ticket Title / Subject
            </label>
            <input
              id="ticket-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Cannot access shared network drive from laptop"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-sm placeholder:text-slate-400"
              required
            />
          </div>

          <div>
            <label htmlFor="ticket-desc" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Issue Description
            </label>
            <textarea
              id="ticket-desc"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide symptoms, error messages, and affected hardware or software..."
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-sm placeholder:text-slate-400"
              required
            />
          </div>

          {/* Real-time ML Prediction Card */}
          {prediction && (
            <div className="p-4 rounded-xl bg-sky-50/70 border border-sky-100 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-sky-900 uppercase tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                  <span>Real-time Triage Prediction</span>
                </span>
                {previewing && <span className="text-xs text-sky-600 animate-pulse">Analyzing...</span>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Predicted Category */}
                <div className="bg-white p-3.5 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Predicted Category</div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-bold text-slate-900 text-base">{prediction.category}</span>
                    <span className="text-xs font-bold text-sky-700 bg-sky-100 px-2 py-0.5 rounded-full">
                      {(prediction.category_confidence * 100).toFixed(1)}% conf.
                    </span>
                  </div>
                  {/* Confidence progress bar */}
                  <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className="bg-sky-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.round(prediction.category_confidence * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Predicted Priority */}
                <div className="bg-white p-3.5 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Predicted Priority</div>
                  <div className="flex items-center justify-between mt-1">
                    <span
                      className={`font-bold text-xs uppercase px-2.5 py-1 rounded-full border ${getPriorityBadgeColor(
                        prediction.priority
                      )}`}
                    >
                      {prediction.priority} Priority
                    </span>
                    <span className="text-xs font-medium text-slate-500">
                      {(prediction.priority_confidence * 100).toFixed(1)}% conf.
                    </span>
                  </div>
                  {/* Confidence progress bar */}
                  <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className="bg-slate-400 h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.round(prediction.priority_confidence * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end items-center space-x-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setTitle('');
                setDescription('');
                setPrediction(null);
                setError(null);
              }}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Clear
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-sm shadow-sm transition-colors disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Submit Ticket</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
