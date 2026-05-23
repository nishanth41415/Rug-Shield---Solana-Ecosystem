import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'

const formatPrice = (price) => {
  if (price < 0.01) return `$${price.toFixed(5)}`
  if (price < 1) return `$${price.toFixed(3)}`
  return `$${price.toFixed(2)}`
}

const cardTone = {
  low: 'border-emerald-300/20 shadow-[0_18px_42px_rgba(16,185,129,0.08)] hover:shadow-[0_22px_52px_rgba(16,185,129,0.15)]',
  medium:
    'border-amber-300/20 shadow-[0_18px_42px_rgba(245,158,11,0.08)] hover:shadow-[0_22px_52px_rgba(245,158,11,0.14)]',
  high: 'border-rose-300/25 shadow-[0_18px_42px_rgba(244,63,94,0.1)] hover:shadow-[0_22px_56px_rgba(244,63,94,0.2)]',
}

function TokenCard({ token, index = 0 }) {
  const isPositive = token.price_change_24h >= 0
  const offsetClass = index % 3 === 1 ? 'mt-2' : index % 3 === 2 ? 'mt-1' : ''
  const widthClass = index % 4 === 2 ? 'min-w-[19.5rem]' : 'min-w-[18rem]'
  const tone = cardTone[token.risk_level] ?? cardTone.medium

  return (
    <Link
      className={`group relative flex ${widthClass} ${offsetClass} origin-center items-center gap-3 overflow-hidden rounded-[1.1rem] border bg-[#101823]/88 p-[15px] backdrop-blur-xl transition duration-200 ease-out hover:-translate-y-1 hover:rotate-[0.35deg] hover:scale-[1.018] active:translate-y-0 active:scale-[0.99] ${tone}`}
      to={`/token/${token.mint}`}
    >
      <span className="absolute -right-10 -top-12 h-24 w-24 rounded-full bg-cyan-300/8 blur-2xl transition duration-200 group-hover:bg-cyan-300/14" />
      <span className="absolute bottom-0 left-5 right-7 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <div className="relative">
        <img
          alt={`${token.name} logo`}
          className="h-12 w-12 shrink-0 rounded-full border border-white/10 bg-gray-900 shadow-lg shadow-black/30"
          loading="lazy"
          src={token.logo_url}
        />
        <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#101823] bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.8)]" />
      </div>

      <div className="relative min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 pt-0.5">
            <div className="truncate text-[15px] font-semibold leading-tight text-white transition group-hover:text-cyan-100">
              {token.name}
            </div>
            <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
              {token.symbol}
            </div>
          </div>
          <RiskBadge level={token.risk_level} score={token.risk_score} />
        </div>

        <div className="mt-3 flex items-end gap-3">
          <span className="text-[1.05rem] font-bold leading-none text-white">
            {formatPrice(token.price)}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-bold ${
              isPositive ? 'bg-emerald-300/10 text-emerald-200' : 'bg-rose-300/10 text-rose-200'
            }`}
          >
            {isPositive ? '+' : ''}
            {token.price_change_24h.toFixed(2)}%
          </span>
        </div>
      </div>
    </Link>
  )
}

export default TokenCard
