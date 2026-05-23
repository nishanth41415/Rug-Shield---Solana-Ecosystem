function Filters({ filters, maxPrice, onChange }) {
  const updateFilter = (key, value) => {
    onChange((current) => ({ ...current, [key]: value }))
  }

  const inputClass =
    'w-full rounded-xl border border-white/10 bg-[#0d141d]/80 px-4 py-3 text-sm text-gray-100 outline-none shadow-inner shadow-black/20 transition duration-200 placeholder:text-gray-600 focus:border-cyan-300/50 focus:bg-[#101923] focus:ring-2 focus:ring-cyan-300/10'
  const labelClass = 'mb-2 block text-[11px] font-bold uppercase tracking-[0.18em] text-gray-500'

  return (
    <section className="rounded-[1.2rem] border border-white/8 bg-[#101720]/78 p-4 shadow-[0_22px_70px_rgba(0,0,0,0.24)] backdrop-blur-xl sm:p-5">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">Desk Filters</h2>
          <p className="text-sm text-gray-500">Affects Market Watch only. Risk Feed stays unfiltered.</p>
        </div>
        <span className="w-fit rounded-full bg-cyan-300/8 px-3 py-1 text-xs font-semibold text-cyan-100 ring-1 ring-cyan-200/10">
          updated just now
        </span>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1.35fr_0.75fr_1.05fr_0.8fr]">
        <label className="block translate-y-px">
          <span className={labelClass}>Search</span>
          <input
            className={inputClass}
            onChange={(event) => updateFilter('query', event.target.value)}
            placeholder="Name, symbol, or mint"
            type="search"
            value={filters.query}
          />
        </label>

        <label className="block">
          <span className={labelClass}>Risk Level</span>
          <select
            className={inputClass}
            onChange={(event) => updateFilter('riskLevel', event.target.value)}
            value={filters.riskLevel}
          >
            <option value="all">All</option>
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
          </select>
        </label>

        <div className="grid grid-cols-2 gap-3 lg:translate-y-1">
          <label className="block">
            <span className={labelClass}>Min Price</span>
            <input
              className={inputClass}
              min="0"
              onChange={(event) => updateFilter('minPrice', event.target.value)}
              placeholder="0"
              type="number"
              value={filters.minPrice}
            />
          </label>

          <label className="block">
            <span className={labelClass}>Max Price</span>
            <input
              className={inputClass}
              min="0"
              onChange={(event) => updateFilter('maxPrice', event.target.value)}
              placeholder={String(maxPrice)}
              type="number"
              value={filters.maxPrice}
            />
          </label>
        </div>

        <label className="block lg:-translate-y-px">
          <span className={labelClass}>Sort</span>
          <select
            className={inputClass}
            onChange={(event) => updateFilter('sortBy', event.target.value)}
            value={filters.sortBy}
          >
            <option value="volume">Volume</option>
            <option value="price-desc">Price High</option>
            <option value="price-asc">Price Low</option>
            <option value="risk-desc">Risk High</option>
            <option value="risk-asc">Risk Low</option>
          </select>
        </label>
      </div>
    </section>
  )
}

export default Filters
