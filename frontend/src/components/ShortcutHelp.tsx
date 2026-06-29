import { useState } from "react";

const SHORTCUTS = [
  ["Ctrl+K", "Open command palette"],
  ["Space", "Pause/resume all strategies"],
  ["R", "Reset portfolio"],
  ["1 / 2 / 3", "Switch chart to watchlist stock"],
  ["Esc", "Close modal/panel"],
];

export default function ShortcutHelp() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-gray-500 hover:text-white transition-colors text-sm"
        title="Keyboard shortcuts"
      >
        ?
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="relative bg-gray-800 border border-gray-600 rounded-xl p-5 shadow-2xl max-w-sm w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Keyboard Shortcuts</h3>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            <div className="space-y-2">
              {SHORTCUTS.map(([key, desc]) => (
                <div key={key} className="flex items-center justify-between">
                  <kbd className="px-2 py-0.5 bg-gray-700 rounded text-xs font-mono text-gray-300 border border-gray-600">
                    {key}
                  </kbd>
                  <span className="text-sm text-gray-400">{desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
