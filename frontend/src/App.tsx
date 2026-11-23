import { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { DashboardStats } from "./components/DashboardStats";
import { TicketList } from "./components/TicketList";
import { TicketForm } from "./components/TicketForm";

type Tab = "dashboard" | "tickets" | "new";
const TABS: Tab[] = ["dashboard", "tickets", "new"];

/** Read the tab from the URL hash (e.g. /#tickets) so views can be linked and bookmarked. */
function tabFromHash(): Tab {
  const hash = window.location.hash.replace("#", "") as Tab;
  return TABS.includes(hash) ? hash : "dashboard";
}

export default function App() {
  const [activeTab, setActiveTabState] = useState<Tab>(tabFromHash);

  const setActiveTab = (tab: Tab) => {
    window.location.hash = tab;
    setActiveTabState(tab);
  };

  // Keep the view in sync with the browser's back/forward buttons.
  useEffect(() => {
    const onHashChange = () => setActiveTabState(tabFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "dashboard" && <DashboardStats />}
        {activeTab === "tickets" && <TicketList />}
        {activeTab === "new" && (
          <TicketForm onTicketCreated={() => setActiveTab("tickets")} />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <p>TicketSense — portfolio project by Vydya Pandith</p>
        <p className="mt-1 text-slate-400">
          FastAPI · React · PostgreSQL · Scikit-Learn NLP · Prometheus · Docker
        </p>
      </footer>
    </div>
  );
}
