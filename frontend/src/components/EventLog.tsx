import { useEffect, useRef, useState } from "react";

interface EventEntry {
  timestamp: string;
  event: string;
  detail: string;
}

interface Props {
  events: EventEntry[] | null;
}

export default function EventLog({ events }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [prevCount, setPrevCount] = useState(0);
  const [newIndices, setNewIndices] = useState<Set<number>>(new Set());

  // Detect new events and highlight them
  useEffect(() => {
    if (!events) return;
    const currentCount = events.length;

    if (currentCount > prevCount && prevCount > 0) {
      // Mark the new entries for highlight
      const indices = new Set<number>();
      for (let i = prevCount; i < currentCount; i++) {
        indices.add(i);
      }
      setNewIndices(indices);

      // Clear highlights after 1 second
      setTimeout(() => setNewIndices(new Set()), 1000);
    }

    setPrevCount(currentCount);
  }, [events]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div id="event-log-section" className="bg-gray-800 rounded-lg p-5 border border-gray-700 flex flex-col h-full">
      <h2 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wide">
        Event Log
      </h2>

      {!events ? (
        <p className="text-gray-500 text-sm">Connecting...</p>
      ) : events.length === 0 ? (
        <p className="text-gray-500 text-sm">No events yet</p>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto max-h-64 space-y-1 pr-1"
        >
          {events.map((evt, i) => (
            <div
              key={i}
              className={`flex gap-2 text-xs py-1 border-b border-gray-700/50 rounded transition-colors duration-1000 ${
                newIndices.has(i) ? "bg-green-900/30" : "bg-transparent"
              }`}
            >
              <span className="text-gray-500 font-mono shrink-0">
                {formatTime(evt.timestamp)}
              </span>
              <span className={`font-bold shrink-0 ${getEventColor(evt.event)}`}>
                {formatEventType(evt.event)}
              </span>
              <span className="text-gray-300 truncate">{evt.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function getEventColor(event: string): string {
  switch (event) {
    case "SIGNAL_GENERATED":
      return "text-yellow-400";
    case "ORDER_FILLED":
      return "text-green-400";
    case "ORDER_REJECTED":
      return "text-red-400";
    case "STRATEGY_STARTED":
      return "text-blue-400";
    case "STRATEGY_STOPPED":
      return "text-orange-400";
    case "PORTFOLIO_RESET":
      return "text-purple-400";
    case "STRATEGY_CONFIG_CHANGED":
      return "text-cyan-400";
    default:
      return "text-gray-400";
  }
}

function formatEventType(event: string): string {
  return event.replaceAll("_", " ");
}
