export default function StrategyBuilder() {
  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Strategy Builder
        </h2>
        <span className="text-xs bg-yellow-900/50 text-yellow-400 px-2 py-0.5 rounded-full">
          Coming Soon
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Custom strategy builder — combine indicators into automated trading rules
      </p>

      {/* Mockup rule rows */}
      <div className="space-y-2 mb-4">
        <RuleRow condition="IF" indicator="RSI" comparator="below" value="25" action="BUY" />
        <RuleRow condition="IF" indicator="EMA(9)" comparator="crosses above" value="EMA(21)" action="BUY" />
        <RuleRow condition="IF" indicator="RSI" comparator="above" value="75" action="SELL" />
      </div>

      <button
        disabled
        className="w-full py-2 px-4 rounded-lg bg-gray-700 text-gray-500 text-sm font-medium cursor-not-allowed"
      >
        Create Strategy
      </button>
    </div>
  );
}

function RuleRow({
  condition,
  indicator,
  comparator,
  value,
  action,
}: {
  condition: string;
  indicator: string;
  comparator: string;
  value: string;
  action: string;
}) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-500 w-6">{condition}</span>
      <span className="bg-gray-700 text-blue-400 px-2 py-1 rounded">{indicator}</span>
      <span className="text-gray-500">{comparator}</span>
      <span className="bg-gray-700 text-yellow-400 px-2 py-1 rounded">{value}</span>
      <span className="text-gray-500">THEN</span>
      <span
        className={`px-2 py-1 rounded font-bold ${
          action === "BUY"
            ? "bg-green-900/50 text-green-400"
            : "bg-red-900/50 text-red-400"
        }`}
      >
        {action}
      </span>
    </div>
  );
}
