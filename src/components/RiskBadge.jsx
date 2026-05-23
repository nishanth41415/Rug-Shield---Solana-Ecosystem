import { getRiskTone } from './riskUtils'

const riskCopy = {
  low: 'Clean holder spread and fewer severe contract signals.',
  medium: 'Some pressure showing. Worth a slower review before entry.',
  high: 'Elevated signal stack. Treat this like a live incident.',
}

const riskStyles = {
  low: {
    shell:
      'border-emerald-300/25 bg-emerald-300/8 text-emerald-100 shadow-[0_0_22px_rgba(52,211,153,0.13)]',
    accent: 'from-emerald-200 via-emerald-400 to-cyan-300',
    dot: 'bg-emerald-300 shadow-[0_0_12px_rgba(52,211,153,0.8)]',
  },
  medium: {
    shell:
      'border-amber-300/25 bg-amber-300/10 text-amber-100 shadow-[0_0_22px_rgba(251,191,36,0.12)]',
    accent: 'from-amber-200 via-yellow-400 to-orange-300',
    dot: 'bg-amber-300 shadow-[0_0_12px_rgba(251,191,36,0.85)]',
  },
  high: {
    shell:
      'border-rose-300/30 bg-rose-400/10 text-rose-100 shadow-[0_0_26px_rgba(251,113,133,0.18)]',
    accent: 'from-rose-200 via-red-400 to-fuchsia-400',
    dot: 'risk-dot-hot bg-rose-300 shadow-[0_0_14px_rgba(251,113,133,0.9)]',
  },
}

function RiskBadge({ level, score }) {
  const tone = getRiskTone(score)
  const styles = riskStyles[level] ?? riskStyles.medium

  return (
    <span
      className={`group relative inline-flex w-fit items-center gap-2 overflow-visible rounded-full border py-1 pl-1.5 pr-3 text-xs font-semibold capitalize backdrop-blur-md transition duration-200 hover:-translate-y-px ${styles.shell}`}
    >
      <span className={`h-5 w-1 rounded-full bg-gradient-to-b ${styles.accent}`} />
      <span className={`h-2 w-2 rounded-full ${styles.dot}`} />
      <span>{tone.label} Risk</span>
      <span className="pointer-events-none absolute bottom-full left-4 z-20 mb-2 hidden w-52 rounded-lg border border-white/10 bg-[#101620]/95 px-3 py-2 text-left text-xs font-medium normal-case leading-relaxed text-gray-300 shadow-2xl shadow-black/40 backdrop-blur-md group-hover:block">
        {riskCopy[level]}
      </span>
    </span>
  )
}

export default RiskBadge
