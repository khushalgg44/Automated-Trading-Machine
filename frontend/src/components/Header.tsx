import { usePolling } from "../hooks/usePolling";
import { HealthStatus } from "../types";
import ShortcutHelp from "./ShortcutHelp";

interface Props {
  theme: string;
  onToggleTheme: () => void;
  recentEventCount: number;
  hasRejection: boolean;
}

export default function Header({ theme, onToggleTheme, recentEventCount, hasRejection }: Props) {
  const { data, error } = usePolling<HealthStatus>("/api/health", 3000);

  const isHealthy = data?.status === "ok" && !error;

  const scrollToEventLog = () => {
    document.getElementById("event-log-section")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-gray-800 border-b border-gray-700">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          AlgoTradeX
        </h1>
        <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
          PAPER
        </span>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode (T)`}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
        <ShortcutHelp />
        <span className="text-xs text-gray-500 hidden lg:inline">Ctrl+K</span>

        {/* Notification badge */}
        {recentEventCount > 0 && (
          <button
            onClick={scrollToEventLog}
            className={`min-w-[20px] h-5 px-1.5 rounded-full text-xs font-bold text-white flex items-center justify-center animate-pulse ${
              hasRejection ? "bg-red-500" : "bg-green-500"
            }`}
            title="Recent events — click to view"
          >
            {recentEventCount}
          </button>
        )}

        <span
          className={`w-2.5 h-2.5 rounded-full ${
            isHealthy ? "bg-green-400 animate-pulse" : "bg-red-500"
          }`}
        />
        <span className={isHealthy ? "text-green-400" : "text-red-400"}>
          {error ? "Disconnected" : isHealthy ? "Live" : "Connecting..."}
        </span>
        {data?.generator_running && (
          <span className="text-gray-500 ml-1">• Ticking</span>
        )}
      </div>
    </header>
  );
}
