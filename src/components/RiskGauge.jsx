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
      className={`rounded-xl border border-gray-800 bg-gray-950/80 p-6 shadow-lg ${tone.glow}`}
    >
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
          <div className={`text-5xl font-semibold tracking-normal ${tone.text}`}>
            {displayScore}
          </div>
          <div className="mt-1 text-xs font-medium uppercase tracking-[0.2em] text-gray-500">
            Risk Score
          </div>
        </div>
      </div>
      <div className="mt-5 flex justify-center">
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ring-1 ${tone.badge}`}>
          {tone.label}
        </span>
      </div>
    </div>
  )
}

export default RiskGauge
