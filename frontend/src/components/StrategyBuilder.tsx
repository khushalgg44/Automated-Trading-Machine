import { useState } from "react";

interface Rule {
  id: number;
  indicator: string;
  comparator: string;
  value: string;
  action: "BUY" | "SELL";
}

const INDICATORS = ["RSI", "EMA_FAST", "EMA_SLOW", "PRICE", "BOLLINGER_UPPER", "BOLLINGER_LOWER"];
const COMPARATORS = ["above", "below", "crosses_above", "crosses_below"];

let ruleIdCounter = 0;

export default function StrategyBuilder() {
  const [rules, setRules] = useState<Rule[]>([
    { id: ++ruleIdCounter, indicator: "RSI", comparator: "below", value: "25", action: "BUY" },
    { id: ++ruleIdCounter, indicator: "RSI", comparator: "above", value: "75", action: "SELL" },
  ]);
  const [strategyName, setStrategyName] = useState("my_custom_strategy");
  const [status, setStatus] = useState<{ type: "success" | "error" | null; message: string }>({ type: null, message: "" });
  const [submitting, setSubmitting] = useState(false);

  const addRule = () => {
    setRules([...rules, { id: ++ruleIdCounter, indicator: "RSI", comparator: "below", value: "30", action: "BUY" }]);
  };

  const removeRule = (id: number) => {
    setRules(rules.filter(r => r.id !== id));
  };

  const updateRule = (id: number, field: keyof Rule, value: string) => {
    setRules(rules.map(r => r.id === id ? { ...r, [field]: value } : r));
  };

  const handleCreate = async () => {
    if (rules.length === 0) { setStatus({ type: "error", message: "Add at least one rule" }); return; }
    if (!strategyName.trim()) { setStatus({ type: "error", message: "Enter a strategy name" }); return; }

    setSubmitting(true);
    setStatus({ type: null, message: "" });

    try {
      const res = await fetch("/api/strategy-builder/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: strategyName, rules }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus({ type: "error", message: data.detail || "Failed to create" });
      } else {
        setStatus({ type: "success", message: `Strategy "${strategyName}" created and started!` });
      }
    } catch (err: any) {
      setStatus({ type: "error", message: err.message || "Network error" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
        Strategy Builder
      </h2>

      {/* Strategy name */}
      <div className="mb-4">
        <label className="text-xs text-gray-500 block mb-1">Strategy Name</label>
        <input
          value={strategyName}
          onChange={(e) => setStrategyName(e.target.value.replace(/\s/g, "_").toLowerCase())}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white w-64 focus:outline-none focus:border-blue-500"
          placeholder="my_strategy"
        />
      </div>

      {/* Rules */}
      <div className="space-y-2 mb-4">
        {rules.map((rule, idx) => (
          <div key={rule.id} className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 w-8">{idx === 0 ? "IF" : "OR"}</span>

            <select value={rule.indicator} onChange={(e) => updateRule(rule.id, "indicator", e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-blue-400 focus:outline-none">
              {INDICATORS.map(i => <option key={i} value={i}>{i}</option>)}
            </select>

            <select value={rule.comparator} onChange={(e) => updateRule(rule.id, "comparator", e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 focus:outline-none">
              {COMPARATORS.map(c => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
            </select>

            <input value={rule.value} onChange={(e) => updateRule(rule.id, "value", e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-yellow-400 w-16 focus:outline-none font-mono"
            />

            <span className="text-xs text-gray-500">THEN</span>

            <select value={rule.action} onChange={(e) => updateRule(rule.id, "action", e.target.value as "BUY" | "SELL")}
              className={`bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs font-bold focus:outline-none ${
                rule.action === "BUY" ? "text-green-400" : "text-red-400"
              }`}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>

            <button onClick={() => removeRule(rule.id)}
              className="text-gray-600 hover:text-red-400 text-xs ml-1">✕</button>
          </div>
        ))}
      </div>

      {/* Add rule button */}
      <button onClick={addRule}
        className="text-xs text-gray-400 hover:text-white border border-dashed border-gray-700 rounded px-3 py-1.5 mb-4 hover:border-gray-500">
        + Add Rule
      </button>

      {/* Create button */}
      <div className="flex items-center gap-3">
        <button onClick={handleCreate} disabled={submitting}
          className="px-4 py-2 rounded font-bold text-sm bg-green-600 hover:bg-green-500 text-white disabled:opacity-50">
          {submitting ? "Creating..." : "Create & Start Strategy"}
        </button>
        {status.type && (
          <span className={`text-xs ${status.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {status.message}
          </span>
        )}
      </div>

      {/* Info */}
      <p className="text-xs text-gray-600 mt-4">
        Custom strategies use the same risk management chain and paper engine as built-in strategies.
      </p>
    </div>
  );
}
