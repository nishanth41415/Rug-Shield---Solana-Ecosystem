import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import tokens from '../data/mock_data.json'
import { getRiskTone } from './riskUtils'

const shortenMint = (mint) => `${mint.slice(0, 6)}...${mint.slice(-6)}`

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          className="animate-pulse rounded-xl border border-gray-800 bg-gray-950/70 p-4"
          key={index}
        >
          <div className="h-5 w-36 rounded bg-gray-800" />
          <div className="mt-3 h-4 w-56 rounded bg-gray-800/80" />
        </div>
      ))}
    </div>
  )
}

function LiveTokenFeed() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 450)
    return () => clearTimeout(timer)
  }, [])

  const filteredTokens = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    if (!normalizedQuery) {
      return tokens
    }

    return tokens.filter((token) => {
      return (
        token.name.toLowerCase().includes(normalizedQuery) ||
        token.mint.toLowerCase().includes(normalizedQuery)
      )
    })
  }, [query])

  return (
    <main className="min-h-screen bg-gray-900 px-4 py-6 text-gray-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-col gap-4 rounded-xl border border-gray-800 bg-gray-950/80 p-5 shadow-lg sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-emerald-300">
              RugShield
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-white sm:text-4xl">
              Live Token Feed
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-400">
              Local mock feed for token mint risk, contract signals, and review status.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
              <div className="text-2xl font-semibold text-white">{tokens.length}</div>
              <div className="text-xs text-gray-500">Tokens</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
              <div className="text-2xl font-semibold text-emerald-300">
                {tokens.filter((token) => token.riskScore >= 70).length}
              </div>
              <div className="text-xs text-gray-500">Low Risk</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
              <div className="text-2xl font-semibold text-rose-300">
                {tokens.filter((token) => token.riskScore < 40).length}
              </div>
              <div className="text-xs text-gray-500">High Risk</div>
            </div>
          </div>
        </header>

        <section className="rounded-xl border border-gray-800 bg-gray-950/80 p-4 shadow-lg">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Market Watch</h2>
              <p className="text-sm text-gray-500">Click a row to inspect every signal.</p>
            </div>
            <label className="relative block sm:w-80">
              <span className="sr-only">Search tokens</span>
              <input
                className="w-full rounded-xl border border-gray-700 bg-gray-900 px-4 py-3 text-sm text-gray-100 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/20"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search name or mint"
                type="search"
                value={query}
              />
            </label>
          </div>

          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <div className="max-h-[620px] overflow-y-auto pr-1">
              <div className="min-w-full space-y-3">
                {filteredTokens.map((token) => {
                  const tone = getRiskTone(token.riskScore)

                  return (
                    <Link
                      className="group grid grid-cols-1 gap-3 rounded-xl border border-gray-800 bg-gray-900/70 p-4 shadow-lg transition duration-200 hover:-translate-y-0.5 hover:border-emerald-400/40 hover:bg-gray-800/80 hover:shadow-emerald-950/30 sm:grid-cols-[1.3fr_1fr_auto] sm:items-center"
                      key={token.mint}
                      to={`/token/${token.mint}`}
                    >
                      <div>
                        <div className="font-semibold text-white transition group-hover:text-emerald-200">
                          {token.name}
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          {token.signals.filter((signal) => signal.triggered).length} triggered signals
                        </div>
                      </div>
                      <code className="w-fit rounded-lg bg-gray-950 px-3 py-2 text-xs text-gray-300 ring-1 ring-gray-800">
                        {shortenMint(token.mint)}
                      </code>
                      <span
                        className={`w-fit rounded-full px-3 py-1 text-sm font-semibold ring-1 ${tone.badge}`}
                      >
                        {token.riskScore}
                      </span>
                    </Link>
                  )
                })}
              </div>

              {filteredTokens.length === 0 && (
                <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center text-gray-400">
                  No tokens match this search.
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

export default LiveTokenFeed
