import { useEffect, useMemo, useState } from 'react'
import { getRiskTone } from './riskUtils'

const clampScore = (score) => Math.max(0, Math.min(100, Number(score) || 0))

function RiskGauge({ score, compact = false }) {
  const target = clampScore(score)
  const [displayScore, setDisplayScore] = useState(0)
  const tone = useMemo(() => getRiskTone(target), [target])
  const radius = compact ? 46 : 72
  const strokeWidth = compact ? 9 : 12
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (displayScore / 100) * circumference

  useEffect(() => {
    let frameId
    const duration = 700
    const startTime = performance.now()

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayScore(Math.round(target * eased))

      if (progress < 1) {
        frameId = requestAnimationFrame(tick)
      }
    }

    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [target])

  return (
    <div
      className={`relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-[#101720]/82 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl ${tone.glow}`}
    >
      <span className="pointer-events-none absolute -right-16 -top-16 h-36 w-36 rounded-full bg-white/6 blur-3xl" />
      <span className="pointer-events-none absolute bottom-0 left-8 h-px w-44 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      <div className="relative mx-auto grid place-items-center">
        <svg
          className={compact ? 'h-32 w-32 -rotate-90' : 'h-48 w-48 -rotate-90'}
          viewBox="0 0 180 180"
          aria-hidden="true"
        >
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke="#1f2937"
            strokeWidth={strokeWidth}
          />
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke={tone.stroke}
            strokeLinecap="round"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-300"
          />
        </svg>
        <div className="absolute text-center">
          <div className={`text-6xl font-black leading-none tracking-[-0.03em] ${tone.text}`}>
            {displayScore}
          </div>
          <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">
            Risk Score
          </div>
        </div>
      </div>
      <div className="mt-5 flex justify-center">
        <span className={`rounded-full px-4 py-1.5 text-sm font-bold ring-1 ${tone.badge}`}>
          {tone.label}
        </span>
      </div>
    </div>
  )
}

export default RiskGauge
