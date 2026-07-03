import { useState, useEffect, useCallback, useRef } from "react";
import Header from "./components/Header";
import SessionStats from "./components/SessionStats";
import PortfolioCard from "./components/PortfolioCard";
import RiskGauge from "./components/RiskGauge";
import PositionsTable from "./components/PositionsTable";
import TradesTable from "./components/TradesTable";
import Watchlist from "./components/Watchlist";
import StrategyStatus from "./components/StrategyStatus";
import EquityCurve from "./components/EquityCurve";
import ManualTrade from "./components/ManualTrade";
import EventLog from "./components/EventLog";
import AnalyticsCard from "./components/AnalyticsCard";
import BacktestPanel from "./components/BacktestPanel";
import SystemHealth from "./components/SystemHealth";
import CommandPalette from "./components/CommandPalette";
import ReportView from "./components/ReportView";
import ArchitectureDocs from "./components/ArchitectureDocs";
import HistoricalChart from "./components/HistoricalChart";
import Heatmap from "./components/Heatmap";
import PnLCalendar from "./components/PnLCalendar";
import CorrelationMatrix from "./components/CorrelationMatrix";
import PortfolioComparison from "./components/PortfolioComparison";
import StrategyBuilder from "./components/StrategyBuilder";
import { usePolling } from "./hooks/usePolling";
import { useTheme } from "./hooks/useTheme";
import { Prices } from "./types";

interface EventEntry {
  timestamp: string;
  event: string;
  detail: string;
}

type TabId = "dashboard" | "charts" | "analytics" | "trading" | "research";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "charts", label: "Charts", icon: "📈" },
  { id: "analytics", label: "Analytics", icon: "📉" },
  { id: "trading", label: "Trading", icon: "💹" },
  { id: "research", label: "Research", icon: "🔬" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [archDocsOpen, setArchDocsOpen] = useState(false);
  const { theme, toggle: toggleTheme } = useTheme();

  const [recentEventCount, setRecentEventCount] = useState(0);
  const [hasRejection, setHasRejection] = useState(false);
  const [demoActive, setDemoActive] = useState(false);
  const lastSeenCountRef = useRef(0);
  const notifPermissionRef = useRef(false);

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().then((perm) => { notifPermissionRef.current = perm === "granted"; });
    } else if ("Notification" in window) {
      notifPermissionRef.current = Notification.permission === "granted";
    }
  }, []);

  const { data: prices } = usePolling<Prices>("/api/prices", 1000);
  const { data: events } = usePolling<EventEntry[]>("/api/events", 2000);
  const { data: watchlistData } = usePolling<string[]>("/api/watchlist", 5000);
  const watchlist = watchlistData || ["RELIANCE", "TCS", "INFY"];
  const strategies = ["ema_cross", "rsi_mean_reversion", "bollinger_bands"];

  const { data: demoData } = usePolling<{ active: boolean }>("/api/demo/status", 3000);
  useEffect(() => { if (demoData) setDemoActive(demoData.active); }, [demoData]);

  const toggleDemo = async () => {
    if (demoActive) {
      await fetch("/api/demo/stop", { method: "POST" });
      setDemoActive(false);
    } else {
      if (confirm("Start Demo Mode? This resets the portfolio and runs at 10x speed.")) {
        await fetch("/api/demo/start", { method: "POST" });
        setDemoActive(true);
      }
    }
  };

  useEffect(() => {
    if (!events) return;
    const currentCount = events.length;
    if (currentCount > lastSeenCountRef.current && lastSeenCountRef.current > 0) {
      const newEvents = events.slice(lastSeenCountRef.current);
      const now = Date.now();
      const recentCount = events.filter((e) => { try { return now - new Date(e.timestamp).getTime() < 30000; } catch { return false; } }).length;
      setRecentEventCount(recentCount);
      const rejections = newEvents.filter((e) => e.event === "ORDER_REJECTED");
      setHasRejection(rejections.length > 0);
      if (rejections.length > 0 && notifPermissionRef.current && document.hidden) {
        new Notification("Order Rejected", { body: rejections[0].detail, icon: "/favicon.svg" });
      }
      setTimeout(() => { setRecentEventCount(0); setHasRejection(false); }, 30000);
    }
    lastSeenCountRef.current = currentCount;
  }, [events]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const tag = (document.activeElement?.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); setCmdPaletteOpen(true); return; }
    if (e.key === "Escape") { setCmdPaletteOpen(false); setReportOpen(false); setArchDocsOpen(false); return; }
    if (e.key === "t" || e.key === "T") { toggleTheme(); return; }
    if (e.key === "d" || e.key === "D") { toggleDemo(); return; }
    if (e.key === " ") { e.preventDefault(); strategies.forEach((s) => { fetch(`/api/strategy/${s}/stop`, { method: "POST" }); }); return; }
    if (e.key === "r" || e.key === "R") { if (confirm("Reset portfolio?")) fetch("/api/reset-portfolio", { method: "POST" }); return; }
    if (e.key === "1") setActiveTab("dashboard");
    if (e.key === "2") setActiveTab("charts");
    if (e.key === "3") setActiveTab("analytics");
  }, [strategies, toggleTheme, toggleDemo]);

  useEffect(() => { window.addEventListener("keydown", handleKeyDown); return () => window.removeEventListener("keydown", handleKeyDown); }, [handleKeyDown]);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <Header theme={theme} onToggleTheme={toggleTheme} recentEventCount={recentEventCount} hasRejection={hasRejection} demoActive={demoActive} onToggleDemo={toggleDemo} />
      <SessionStats />
      {demoActive && (
        <div className="bg-orange-900/50 border-b border-orange-700 px-4 py-1.5 text-center text-xs text-orange-300 font-mono animate-pulse">
          🎬 DEMO MODE — 10x speed
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-700 bg-gray-800/50">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex gap-1 overflow-x-auto py-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium rounded-t whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "bg-gray-900 text-white border-t-2 border-green-400"
                    : "text-gray-400 hover:text-white hover:bg-gray-700/50"
                }`}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-6">

        {/* ═══ DASHBOARD TAB ═══ */}
        {activeTab === "dashboard" && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              <PortfolioCard />
              <Watchlist prices={prices} />
              <StrategyStatus />
            </div>
            <div className="mb-4"><RiskGauge /></div>
            <div className="mb-4"><EquityCurve prices={prices} /></div>
            <div className="mb-4"><Heatmap /></div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              <ManualTrade prices={prices} />
              <div className="lg:col-span-2"><EventLog events={events} /></div>
            </div>
          </>
        )}

        {/* ═══ CHARTS TAB ═══ */}
        {activeTab === "charts" && (
          <>
            <div className="mb-4"><HistoricalChart /></div>
          </>
        )}

        {/* ═══ ANALYTICS TAB ═══ */}
        {activeTab === "analytics" && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              <div className="lg:col-span-2"><AnalyticsCard /></div>
              <PortfolioComparison />
            </div>
            <div className="mb-4"><PnLCalendar /></div>
            <div className="mb-4"><CorrelationMatrix /></div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              <PositionsTable prices={prices} />
              <TradesTable />
            </div>
          </>
        )}

        {/* ═══ TRADING TAB ═══ */}
        {activeTab === "trading" && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
              <ManualTrade prices={prices} />
              <div className="lg:col-span-2"><EventLog events={events} /></div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              <PositionsTable prices={prices} />
              <TradesTable />
            </div>
          </>
        )}

        {/* ═══ RESEARCH TAB ═══ */}
        {activeTab === "research" && (
          <>
            <div className="mb-4" data-section="backtest"><BacktestPanel /></div>
            <div className="mb-4"><StrategyBuilder /></div>
          </>
        )}

      </main>

      <footer className="text-center py-4 text-xs text-gray-600">
        AlgoTradeX Paper Trading • No real money involved • Demo only
      </footer>

      <SystemHealth />
      <CommandPalette isOpen={cmdPaletteOpen} onClose={() => setCmdPaletteOpen(false)} watchlist={watchlist} strategies={strategies}
        onOpenReport={() => { setCmdPaletteOpen(false); setReportOpen(true); }}
        onOpenArchDocs={() => { setCmdPaletteOpen(false); setArchDocsOpen(true); }}
        onToggleDemo={toggleDemo} />
      <ReportView isOpen={reportOpen} onClose={() => setReportOpen(false)} />
      <ArchitectureDocs isOpen={archDocsOpen} onClose={() => setArchDocsOpen(false)} />
    </div>
  );
}
