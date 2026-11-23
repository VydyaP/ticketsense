import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle,
  AlertTriangle,
  Layers,
  ListFilter,
  PlusCircle,
} from "lucide-react";
import { api } from "../services/api";
import { HealthStatus } from "../types/ticket";

interface NavbarProps {
  activeTab: "dashboard" | "tickets" | "new";
  setActiveTab: (tab: "dashboard" | "tickets" | "new") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch {
        setHealth({
          status: "degraded",
          database: "disconnected",
          model_loaded: false,
          version: "1.0.0",
          timestamp: new Date().toISOString(),
        });
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo & Pitch */}
          <div
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => setActiveTab("dashboard")}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-100">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
                TicketSense
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 font-medium border border-sky-100">
                ITSM ML Triage
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "dashboard"
                  ? "bg-sky-50 text-sky-700 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab("tickets")}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "tickets"
                  ? "bg-sky-50 text-sky-700 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <ListFilter className="w-4 h-4" />
              <span>Tickets</span>
            </button>
            <button
              onClick={() => setActiveTab("new")}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "new"
                  ? "bg-sky-600 text-white shadow-sm hover:bg-sky-700"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Ticket</span>
            </button>
          </nav>

          {/* Health Indicator Pill */}
          <div className="hidden md:flex items-center space-x-2 pl-4 border-l border-slate-200">
            {health?.status === "healthy" ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                API Healthy
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-500" />
                API Degraded
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
