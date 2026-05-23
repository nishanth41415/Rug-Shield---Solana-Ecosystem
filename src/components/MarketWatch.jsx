import TokenCard from './TokenCard'

function MarketWatch({ tokens }) {
  return (
    <section className="relative overflow-hidden rounded-[1.35rem] border border-white/8 bg-[#111925]/82 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl sm:p-5">
      <div className="pointer-events-none absolute -left-12 top-8 h-32 w-32 rounded-full bg-cyan-300/6 blur-3xl" />
      <div className="pointer-events-none absolute right-16 top-0 h-px w-44 bg-gradient-to-r from-transparent via-cyan-200/30 to-transparent" />

      <div className="relative mb-4 flex items-end justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(34,211,238,0.8)]" />
            <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-200/80">
              Live board
            </span>
          </div>
          <h2 className="text-[1.35rem] font-semibold leading-tight text-white">Market Watch</h2>
          <p className="mt-1 text-sm text-gray-500">Drag the tape. Filters only shape this lane.</p>
        </div>
        <span className="mb-1 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-semibold text-gray-300">
          {tokens.length} visible
        </span>
      </div>

      {tokens.length > 0 ? (
        <div className="market-scroll overflow-x-auto scroll-smooth pb-4">
          <div className="flex w-max items-start gap-3 pr-5 sm:gap-4">
            {tokens.map((token, index) => (
              <TokenCard index={index} key={token.mint} token={token} />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-[1rem] border border-dashed border-white/12 bg-black/10 p-8 text-center text-gray-400">
          No tokens match the current filters.
        </div>
      )}
    </section>
  )
}

export default MarketWatch
