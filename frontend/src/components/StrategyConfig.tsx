import { useState, useEffect } from "react";

interface Props {
  strategyName: string;
  currentConfig: Record<string, number>;
  onClose: () => void;
  onSuccess: () => void;
}

interface FieldDef {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
}

const FIELD_DEFS: Record<string, FieldDef[]> = {
  ema_cross: [
    { key: "fast_period", label: "Fast Period", min: 2, max: 50, step: 1 },
    { key: "slow_period", label: "Slow Period", min: 5, max: 200, step: 1 },
  ],
  rsi_mean_reversion: [
    { key: "period", label: "RSI Period", min: 5, max: 50, step: 1 },
    { key: "oversold", label: "Oversold", min: 10, max: 40, step: 1 },
    { key: "overbought", label: "Overbought", min: 60, max: 90, step: 1 },
  ],
  bollinger_bands: [
    { key: "period", label: "Period", min: 5, max: 50, step: 1 },
    { key: "std_dev_multiplier", label: "Std Dev Multiplier", min: 0.5, max: 4.0, step: 0.1 },
  ],
};

export default function StrategyConfig({ strategyName, currentConfig, onClose, onSuccess }: Props) {
  const fields = FIELD_DEFS[strategyName] || [];
  const [values, setValues] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Map currentConfig to the field keys (handle std_dev -> std_dev_multiplier)
    const init: Record<string, number> = {};
    for (const f of fields) {
      if (f.key === "std_dev_multiplier" && currentConfig["std_dev"] !== undefined) {
        init[f.key] = currentConfig["std_dev"];
      } else {
        init[f.key] = currentConfig[f.key] ?? 0;
      }
    }
    setValues(init);
  }, [currentConfig, strategyName]);

  const validate = (): string | null => {
    for (const f of fields) {
      const v = values[f.key];
      if (v < f.min || v > f.max) {
        return `${f.label} must be between ${f.min} and ${f.max}`;
      }
    }
    if (strategyName === "ema_cross" && values.fast_period >= values.slow_period) {
      return "Fast period must be less than slow period";
    }
    return null;
  };

  const handleSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`/api/strategy/${strategyName}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Update failed");
      } else {
        onSuccess();
        onClose();
      }
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-2 p-3 bg-gray-800 border border-gray-600 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-bold text-gray-300 uppercase">Configure {strategyName}</h4>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xs">✕</button>
      </div>

      <div className="space-y-2">
        {fields.map((f) => (
          <div key={f.key} className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-28 shrink-0">{f.label}</label>
            <input
              type="number"
              min={f.min}
              max={f.max}
              step={f.step}
              value={values[f.key] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [f.key]: parseFloat(e.target.value) || 0 }))}
              className={`flex-1 bg-gray-900 border rounded px-2 py-1 text-xs font-mono text-white focus:outline-none ${
                values[f.key] < f.min || values[f.key] > f.max
                  ? "border-red-500 focus:border-red-500"
                  : "border-gray-700 focus:border-blue-500"
              }`}
            />
            <span className="text-xs text-gray-600 w-16 shrink-0">{f.min}–{f.max}</span>
          </div>
        ))}
      </div>

      {error && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}

      <div className="flex gap-2 mt-3">
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-3 py-1 rounded text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50"
        >
          {submitting ? "Applying..." : "Apply"}
        </button>
        <button
          onClick={onClose}
          className="px-3 py-1 rounded text-xs font-bold bg-gray-700 hover:bg-gray-600 text-gray-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
