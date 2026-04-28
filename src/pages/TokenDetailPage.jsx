import { Link, useParams } from 'react-router-dom'
import Chart from '../components/Chart'
import RiskGauge from '../components/RiskGauge'
import SignalList from '../components/SignalList'
import tokens from '../data/mock_data.json'

function TokenDetailPage() {
  const { mint } = useParams()
  const token = tokens.find((item) => item.mint === mint)

  if (!token) {
    return (
      <main className="grid min-h-screen place-items-center bg-gray-900 px-4 text-gray-100">
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-8 text-center shadow-lg">
          <h1 className="text-2xl font-semibold text-white">Token not found</h1>
          <p className="mt-2 text-gray-400">The requested mint is not in mock_data.json.</p>
          <Link
            className="mt-6 inline-flex rounded-xl bg-emerald-400 px-4 py-2 text-sm font-semibold text-gray-950 transition hover:bg-emerald-300"
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
    <main className="min-h-screen bg-gray-900 px-4 py-6 text-gray-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <Link
          className="w-fit rounded-xl border border-gray-800 bg-gray-950 px-4 py-2 text-sm font-semibold text-gray-300 transition hover:border-emerald-400/50 hover:text-white"
          to="/"
        >
          Back to feed
        </Link>

        <header className="rounded-xl border border-gray-800 bg-gray-950/80 p-5 shadow-lg">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium uppercase tracking-[0.24em] text-emerald-300">
                Token Detail
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal text-white sm:text-4xl">
                {token.name}
              </h1>
              <code className="mt-4 block overflow-x-auto rounded-xl bg-gray-900 px-4 py-3 text-sm text-gray-300 ring-1 ring-gray-800">
                {token.mint}
              </code>
            </div>

            <div className="grid grid-cols-2 gap-3 text-center sm:min-w-72">
              <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
                <div className="text-2xl font-semibold text-white">{token.signals.length}</div>
                <div className="text-xs text-gray-500">Signals</div>
              </div>
              <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
                <div className="text-2xl font-semibold text-rose-300">{triggeredCount}</div>
                <div className="text-xs text-gray-500">Triggered</div>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <RiskGauge score={token.riskScore} />
          <SignalList signals={token.signals} />
        </section>

        <Chart signals={token.signals} />
      </div>
    </main>
  )
}

export default TokenDetailPage
