function SignalList({ signals }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/80 p-5 shadow-lg">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">Signals</h2>
        <span className="text-sm text-gray-400">{signals.length} checks</span>
      </div>

      <div className="space-y-3">
        {signals.map((signal) => {
          const isRisky = signal.triggered

          return (
            <div
              className="flex items-center justify-between gap-4 rounded-xl border border-gray-800 bg-gray-900/70 px-4 py-3"
              key={signal.name}
            >
              <span className="min-w-0 truncate text-sm font-medium text-gray-100">
                {signal.name}
              </span>
              <span
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
                  isRisky
                    ? 'bg-rose-500/15 text-rose-100 ring-rose-400/30'
                    : 'bg-emerald-500/15 text-emerald-100 ring-emerald-400/30'
                }`}
              >
                {isRisky ? 'Triggered' : 'Not Triggered'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default SignalList
