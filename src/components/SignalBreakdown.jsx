function SignalBreakdown({ signals }) {
  return (
    <div className="rounded-[1.35rem] border border-white/10 bg-[#101720]/82 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl">
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-[1.35rem] font-semibold leading-tight text-white">
            Signal Breakdown
          </h2>
          <p className="mt-1 text-sm text-gray-500">Weighted checks from the mock scoring engine.</p>
        </div>
        <span className="rounded-full bg-white/[0.04] px-3 py-1 text-xs font-semibold text-gray-300 ring-1 ring-white/10">
          {signals.length} checks
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {signals.map((signal, index) => (
          <div
            className={`grid gap-3 rounded-[1rem] border p-4 shadow-lg shadow-black/10 transition duration-200 hover:-translate-y-0.5 sm:grid-cols-[1fr_auto_auto] sm:items-center ${
              signal.triggered
                ? 'border-rose-300/15 bg-rose-300/[0.045]'
                : 'border-white/8 bg-white/[0.025]'
            } ${index % 5 === 2 ? 'md:translate-y-1' : ''}`}
            key={signal.name}
          >
            <span className="min-w-0 text-sm font-semibold text-gray-100">{signal.name}</span>
            <span className="w-fit rounded-md bg-black/20 px-2 py-1 text-xs font-semibold text-gray-300 ring-1 ring-white/10">
              Weight {signal.weight}
            </span>
            <span
              className={`w-fit rounded-full px-3 py-1 text-xs font-bold ring-1 ${
                signal.triggered
                  ? 'bg-rose-500/12 text-rose-100 ring-rose-400/25'
                  : 'bg-emerald-500/10 text-emerald-100 ring-emerald-400/20'
              }`}
            >
              {signal.triggered ? '✅ Triggered' : '❌ Not Triggered'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default SignalBreakdown
