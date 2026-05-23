import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import tokens from '../data/mock_data.json'
import Filters from './Filters'
import MarketWatch from './MarketWatch'
import RiskBadge from './RiskBadge'
import { getRiskTone } from './riskUtils'

const shortenMint = (mint) => `${mint.slice(0, 6)}...${mint.slice(-6)}`
const formatCompact = (value) => Intl.NumberFormat('en', { notation: 'compact' }).format(value)

const initialFilters = {
  query: '',
  riskLevel: 'all',
  minPrice: '',
  maxPrice: '',
  sortBy: 'volume',
}

const rowTone = {
  low: {
    border: 'border-emerald-300/15 hover:border-emerald-300/35',
    accent: 'from-emerald-300/80 via-emerald-400/40 to-transparent',
    haze: 'bg-emerald-300/5',
  },
  medium: {
    border: 'border-amber-300/15 hover:border-amber-300/35',
    accent: 'from-amber-300/80 via-amber-400/40 to-transparent',
    haze: 'bg-amber-300/5',
  },
  high: {
    border: 'border-rose-300/20 hover:border-rose-300/45',
    accent: 'from-rose-300/90 via-rose-400/50 to-transparent',
    haze: 'bg-rose-300/6',
  },
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          className="h-24 animate-pulse rounded-[1.1rem] border border-white/10 bg-white/[0.04]"
          key={index}
        />
      ))}
    </div>
  )
}

function LiveTokenFeed() {
  const [filters, setFilters] = useState(initialFilters)
  const [isLoading] = useState(false)

  const maxPrice = useMemo(() => {
    return Math.ceil(Math.max(...tokens.map((token) => token.price)))
  }, [])

  const marketTokens = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()
    const minPrice = filters.minPrice === '' ? 0 : Number(filters.minPrice)
    const maxFilterPrice = filters.maxPrice === '' ? Infinity : Number(filters.maxPrice)

    return tokens
      .filter((token) => {
        const matchesQuery =
          !normalizedQuery ||
          token.name.toLowerCase().includes(normalizedQuery) ||
          token.symbol.toLowerCase().includes(normalizedQuery) ||
          token.mint.toLowerCase().includes(normalizedQuery)

        const matchesRisk =
          filters.riskLevel === 'all' || token.risk_level === filters.riskLevel

        const matchesPrice = token.price >= minPrice && token.price <= maxFilterPrice

        return matchesQuery && matchesRisk && matchesPrice
      })
      .sort((a, b) => {
        if (filters.sortBy === 'price-desc') return b.price - a.price
        if (filters.sortBy === 'price-asc') return a.price - b.price
        if (filters.sortBy === 'risk-desc') return b.risk_score - a.risk_score
        if (filters.sortBy === 'risk-asc') return a.risk_score - b.risk_score
        return b.volume_24h - a.volume_24h
      })
  }, [filters])

  const highRiskCount = tokens.filter((token) => token.risk_level === 'high').length
  const lowRiskCount = tokens.filter((token) => token.risk_level === 'low').length

  return (
    <main className="min-h-screen overflow-hidden bg-[#0a0f16] px-4 py-6 text-gray-100 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_12%_18%,rgba(34,211,238,0.12),transparent_28%),radial-gradient(circle_at_82%_8%,rgba(251,113,133,0.1),transparent_24%),linear-gradient(180deg,#0a0f16_0%,#0c121b_46%,#10151d_100%)]" />
      <div className="pointer-events-none fixed left-0 top-24 -z-10 h-72 w-px bg-gradient-to-b from-transparent via-cyan-200/30 to-transparent" />

      <div className="mx-auto flex max-w-6xl flex-col gap-5 lg:gap-6">
        <header className="relative overflow-hidden rounded-[1.45rem] border border-white/10 bg-[#101822]/82 p-5 shadow-[0_28px_90px_rgba(0,0,0,0.34)] backdrop-blur-xl sm:p-6">
          <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-cyan-300/8 blur-3xl" />
          <div className="absolute bottom-0 left-10 h-px w-64 bg-gradient-to-r from-transparent via-cyan-200/35 to-transparent" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-cyan-200/15 bg-cyan-200/8 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.22em] text-cyan-100">
                  RugShield
                </span>
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-300/8 px-3 py-1 text-xs font-semibold text-emerald-100 ring-1 ring-emerald-200/10">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(52,211,153,0.9)]" />
                  live
                </span>
              </div>
              <h1 className="max-w-2xl text-[2.15rem] font-black leading-[0.95] tracking-[-0.02em] text-white sm:text-5xl">
                Crypto Risk Dashboard
              </h1>
              <p className="mt-4 max-w-xl text-[15px] leading-6 text-gray-400">
                Mock token pricing, market movement, contract signals, and holder concentration.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-left sm:min-w-[22rem]">
              <div className="rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3 shadow-inner shadow-white/[0.02]">
                <div className="text-2xl font-black text-white">{tokens.length}</div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  Tokens
                </div>
              </div>
              <div className="translate-y-1 rounded-2xl border border-rose-200/12 bg-rose-300/[0.035] px-4 py-3">
                <div className="text-2xl font-black text-rose-200">{highRiskCount}</div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  High Risk
                </div>
              </div>
              <div className="-translate-y-0.5 rounded-2xl border border-emerald-200/12 bg-emerald-300/[0.035] px-4 py-3">
                <div className="text-2xl font-black text-emerald-200">{lowRiskCount}</div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  Low Risk
                </div>
              </div>
            </div>
          </div>
        </header>

        <Filters filters={filters} maxPrice={maxPrice} onChange={setFilters} />

        {isLoading ? <LoadingSkeleton /> : <MarketWatch tokens={marketTokens} />}

        <section className="relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-[#101720]/82 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.3)] backdrop-blur-xl sm:p-5">
          <div className="pointer-events-none absolute right-8 top-0 h-px w-52 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h2 className="text-[1.35rem] font-semibold leading-tight text-white">Risk Feed</h2>
              <p className="mt-1 text-sm text-gray-500">
                Unfiltered review queue. Click a row to inspect scoring details.
              </p>
            </div>
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-semibold text-gray-300">
              {tokens.length} shown
            </span>
          </div>

          <div className="space-y-2.5">
            {tokens.map((token, index) => {
              const tone = getRiskTone(token.risk_score)
              const rowStyle = rowTone[token.risk_level] ?? rowTone.medium
              const triggeredCount = token.signals.filter((signal) => signal.triggered).length
              const priceMovePositive = token.price_change_24h >= 0
              const rowOffset = index % 4 === 1 ? 'sm:ml-3' : index % 4 === 3 ? 'sm:mr-2' : ''

              return (
                <Link
                  className={`group relative grid grid-cols-1 gap-3 overflow-hidden rounded-[1.05rem] border bg-[#0d141d]/78 p-4 shadow-[0_14px_38px_rgba(0,0,0,0.2)] backdrop-blur-md transition duration-200 ease-out hover:-translate-y-0.5 hover:bg-[#121b26] active:translate-y-0 active:scale-[0.995] sm:grid-cols-[1.42fr_0.74fr_0.7fr_auto] sm:items-center ${rowOffset} ${rowStyle.border}`}
                  key={token.mint}
                  to={`/token/${token.mint}`}
                >
                  <span className={`absolute inset-y-3 left-0 w-1 rounded-r-full bg-gradient-to-b ${rowStyle.accent}`} />
                  <span className={`absolute -right-12 top-1/2 h-24 w-24 -translate-y-1/2 rounded-full blur-3xl transition group-hover:opacity-100 ${rowStyle.haze}`} />
                  <div className="flex min-w-0 items-center gap-3">
                    <img
                      alt={`${token.name} logo`}
                      className="h-11 w-11 rounded-full border border-white/10 bg-gray-900 shadow-md shadow-black/30"
                      loading="lazy"
                      src={token.logo_url}
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-white transition group-hover:text-cyan-100">
                          {token.name}
                        </span>
                        <span className="rounded-md bg-white/[0.04] px-2 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-gray-400 ring-1 ring-white/10">
                          {token.symbol}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {triggeredCount} of {token.signals.length} signals triggered
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-bold text-white">${token.price}</div>
                    <div
                      className={`text-xs font-semibold ${
                        priceMovePositive ? 'text-emerald-300' : 'text-rose-300'
                      }`}
                    >
                      {priceMovePositive ? '+' : ''}
                      {token.price_change_24h.toFixed(2)}%
                    </div>
                  </div>

                  <div>
                    <div className={`text-2xl font-black leading-none ${tone.text}`}>
                      {token.risk_score}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      Vol {formatCompact(token.volume_24h)}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 sm:justify-end">
                    <RiskBadge level={token.risk_level} score={token.risk_score} />
                    <code className="rounded-lg bg-black/18 px-3 py-2 text-xs text-gray-400 ring-1 ring-white/10">
                      {shortenMint(token.mint)}
                    </code>
                  </div>
                </Link>
              )
            })}
          </div>

        </section>
      </div>
    </main>
  )
}

export default LiveTokenFeed
