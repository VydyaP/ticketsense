import React, { useEffect, useState } from "react";
import {
  TicketCheck,
  Clock,
  CheckCircle2,
  Cpu,
  BarChart2,
  Percent,
} from "lucide-react";
import { api } from "../services/api";
import { ModelMetrics, TicketStats } from "../types/ticket";

export const DashboardStats: React.FC = () => {
  const [stats, setStats] = useState<TicketStats | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const [statsData, metricsData] = await Promise.all([
          api.getStats().catch(() => null),
          api.getModelMetrics().catch(() => null),
        ]);
        setStats(statsData);
        setModelMetrics(metricsData);
      } catch (err) {
        console.error("Failed to load dashboard statistics:", err);
      } finally {
        setLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm">
          Loading triage metrics & operational telemetry...
        </p>
      </div>
    );
  }

  const openTickets = stats?.status_counts?.["open"] || 0;
  const inProgressTickets = stats?.status_counts?.["in_progress"] || 0;
  const resolvedTickets = stats?.status_counts?.["resolved"] || 0;

  return (
    <div className="space-y-6">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Tickets */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
            <TicketCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Logged
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {stats?.total_tickets ?? 0}
            </div>
          </div>
        </div>

        {/* Active Open / In Progress */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Active Queue
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {openTickets + inProgressTickets}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {openTickets} Open · {inProgressTickets} In Progress
            </div>
          </div>
        </div>

        {/* Resolved */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Resolved
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {resolvedTickets}
            </div>
          </div>
        </div>

        {/* Uncorrected / Feedback Rate */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Percent className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Uncorrected
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {stats?.uncorrected_rate != null
                ? `${stats.uncorrected_rate}%`
                : "—"}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {stats?.total_corrections ?? 0} human corrections
            </div>
          </div>
        </div>
      </div>

      {/* Visual Breakdowns: Category & Priority */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center space-x-2">
            <BarChart2 className="w-4 h-4 text-sky-600" />
            <span>Tickets by Category</span>
          </h3>
          <div className="space-y-3">
            {stats?.category_counts &&
            Object.keys(stats.category_counts).length > 0 ? (
              Object.entries(stats.category_counts).map(([cat, count]) => {
                const total = stats.total_tickets || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="text-slate-700">{cat}</span>
                      <span className="text-slate-500">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-sky-500 h-full rounded-full transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400 italic">
                No tickets recorded yet.
              </p>
            )}
          </div>
        </div>

        {/* Priority Breakdown */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <span>Tickets by Priority</span>
          </h3>
          <div className="space-y-3">
            {stats?.priority_counts &&
            Object.keys(stats.priority_counts).length > 0 ? (
              Object.entries(stats.priority_counts).map(([prio, count]) => {
                const total = stats.total_tickets || 1;
                const pct = Math.round((count / total) * 100);
                const color =
                  prio === "High"
                    ? "bg-rose-500"
                    : prio === "Medium"
                      ? "bg-amber-500"
                      : "bg-emerald-500";
                return (
                  <div key={prio} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="text-slate-700">{prio} Priority</span>
                      <span className="text-slate-500">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className={`${color} h-full rounded-full transition-all duration-300`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400 italic">
                No tickets recorded yet.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Model Performance & Evaluation Metrics Card */}
      {modelMetrics && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 border-b border-slate-200 mb-4 gap-2">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Cpu className="w-5 h-5 text-sky-600" />
                <span>NLP Model Benchmark & Evaluation</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Evaluated on held-out test split of{" "}
                {modelMetrics.dataset.test_samples.toLocaleString()} tickets
                (Total: {modelMetrics.dataset.total_samples.toLocaleString()})
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Baseline (always predict the most common category): accuracy{" "}
                {(
                  modelMetrics.category_model.baseline_majority_class.accuracy *
                  100
                ).toFixed(1)}
                %, macro F1{" "}
                {modelMetrics.category_model.baseline_majority_class.macro_f1.toFixed(
                  3,
                )}
                . Priority model: accuracy{" "}
                {(modelMetrics.priority_model.accuracy * 100).toFixed(1)}%,
                macro F1 {modelMetrics.priority_model.macro_f1.toFixed(3)}.
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {modelMetrics.dataset.label_note}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <div className="text-xs text-slate-400 font-medium">
                  Category Accuracy
                </div>
                <div className="text-lg font-bold text-sky-600">
                  {(modelMetrics.category_model.accuracy * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-right pl-3 border-l border-slate-200">
                <div className="text-xs text-slate-400 font-medium">
                  Macro F1
                </div>
                <div className="text-lg font-bold text-indigo-600">
                  {modelMetrics.category_model.macro_f1.toFixed(3)}
                </div>
              </div>
            </div>
          </div>

          {/* Per-class Metrics Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Class / Category</th>
                  <th className="px-4 py-2.5">Precision</th>
                  <th className="px-4 py-2.5">Recall</th>
                  <th className="px-4 py-2.5">F1-Score</th>
                  <th className="px-4 py-2.5 text-right">Test Support</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {Object.entries(modelMetrics.category_model.per_class).map(
                  ([cls, scores]) => (
                    <tr key={cls} className="hover:bg-slate-50/50">
                      <td className="px-4 py-2 font-semibold text-slate-900">
                        {cls}
                      </td>
                      <td className="px-4 py-2 font-mono">
                        {(scores.precision * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2 font-mono">
                        {(scores.recall * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2 font-mono">
                        {(scores.f1_score * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-500">
                        {scores.support}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
