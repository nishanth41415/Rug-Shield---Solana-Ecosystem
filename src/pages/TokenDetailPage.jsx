import { Link, useParams } from 'react-router-dom'
import HolderChart from '../components/HolderChart'
import RiskGauge from '../components/RiskGauge'
import SignalBreakdown from '../components/SignalBreakdown'
import tokens from '../data/mock_data.json'

function TokenDetailPage() {
  const { mint } = useParams()
  const token = tokens.find((item) => item.mint === mint)

  if (!token) {
    return (
      <main className="grid min-h-screen place-items-center bg-gray-950 px-4 text-gray-100">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center shadow-xl shadow-black/30">
          <h1 className="text-2xl font-semibold text-white">Token not found</h1>
          <p className="mt-2 text-gray-400">The requested mint is not in mock_data.json.</p>
          <Link
            className="mt-6 inline-flex rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-gray-950 transition hover:bg-cyan-200"
            to="/"
          >
            Back to feed
          </Link>
        </div>
      </main>
    )
  }

  const triggeredCount = token.signals.filter((signal) => signal.triggered).length

  return (
    <main className="min-h-screen bg-[#0a0f16] px-4 py-6 text-gray-100 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_18%_18%,rgba(34,211,238,0.11),transparent_28%),radial-gradient(circle_at_82%_12%,rgba(251,113,133,0.09),transparent_24%),linear-gradient(180deg,#0a0f16_0%,#0c121b_52%,#10151d_100%)]" />
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <Link
          className="w-fit rounded-full border border-white/10 bg-white/[0.035] px-4 py-2 text-sm font-semibold text-gray-300 shadow-lg shadow-black/20 backdrop-blur-md transition duration-200 hover:-translate-y-0.5 hover:border-cyan-300/40 hover:text-white active:translate-y-0"
          to="/"
        >
          Back to feed
        </Link>

        <header className="relative overflow-hidden rounded-[1.45rem] border border-white/10 bg-[#101822]/82 p-5 shadow-[0_28px_90px_rgba(0,0,0,0.34)] backdrop-blur-xl sm:p-6">
          <span className="pointer-events-none absolute -right-16 -top-20 h-52 w-52 rounded-full bg-cyan-300/8 blur-3xl" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-cyan-200">
                Token Detail
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <img
                  alt={`${token.name} logo`}
                  className="h-12 w-12 rounded-full border border-white/10 shadow-lg shadow-black/30"
                  src={token.logo_url}
                />
                <h1 className="text-3xl font-black tracking-[-0.02em] text-white sm:text-5xl">
                  {token.name}
                </h1>
                <span className="rounded-lg bg-white/[0.04] px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-gray-300 ring-1 ring-white/10">
                  {token.symbol}
                </span>
              </div>
              <code className="mt-5 block overflow-x-auto rounded-xl bg-black/18 px-4 py-3 text-sm text-gray-400 ring-1 ring-white/10">
                {token.mint}
              </code>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-left sm:min-w-96">
              <div className="rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3">
                <div className="text-2xl font-black text-white">{token.signals.length}</div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  Signals
                </div>
              </div>
              <div className="translate-y-1 rounded-2xl border border-rose-200/12 bg-rose-300/[0.035] px-4 py-3">
                <div className="text-2xl font-black text-rose-200">{triggeredCount}</div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  Triggered
                </div>
              </div>
              <div className="-translate-y-0.5 rounded-2xl border border-cyan-200/12 bg-cyan-300/[0.035] px-4 py-3">
                <div className="text-2xl font-black capitalize text-cyan-200">
                  {token.risk_level}
                </div>
                <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                  Risk Level
                </div>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <RiskGauge score={token.risk_score} />
          <SignalBreakdown signals={token.signals} />
        </section>

        <HolderChart holders={token.holders} />
      </div>
    </main>
  )
}

export default TokenDetailPage
