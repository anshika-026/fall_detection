// A module's headline KPI cards: icon + title, then a 2x2 (4-up on wide
// screens) grid of big numbers. Every value comes from recorded detections;
// "—" while loading. tone "warn" highlights a number that needs attention.
export default function KpiPanel({ icon: Icon, title, items, note }) {
  return (
    <div className="card p-5 mb-5">
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon size={18} className="text-brand-600" />}
        <h3 className="font-semibold text-ink-900">{title}</h3>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-5">
        {items.map((k) => (
          <div key={k.label} className="min-w-0">
            <p className="text-sm text-slate-500">{k.label}</p>
            <p className={`text-3xl font-semibold leading-tight mt-1 ${k.tone === "warn" && k.value && k.value !== "0" ? "text-danger-500" : "text-ink-900"}`}>
              {k.value ?? "—"}
            </p>
            {k.sub && <p className="text-xs text-slate-400 mt-1">{k.sub}</p>}
          </div>
        ))}
      </div>
      {note && <p className="text-xs text-slate-400 mt-4">{note}</p>}
    </div>
  );
}
