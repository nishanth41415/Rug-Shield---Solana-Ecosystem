const clampScore = (score) => Math.max(0, Math.min(100, Number(score) || 0))

export const getRiskTone = (score) => {
  const value = clampScore(score)

  if (value >= 70) {
    return {
      label: 'Low Risk',
      text: 'text-emerald-300',
      badge: 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/30',
      stroke: '#34d399',
      glow: 'shadow-emerald-950/40',
    }
  }

  if (value >= 40) {
    return {
      label: 'Watch',
      text: 'text-amber-300',
      badge: 'bg-amber-500/15 text-amber-100 ring-amber-400/30',
      stroke: '#fbbf24',
      glow: 'shadow-amber-950/40',
    }
  }

  return {
    label: 'High Risk',
    text: 'text-rose-300',
    badge: 'bg-rose-500/15 text-rose-100 ring-rose-400/30',
    stroke: '#fb7185',
    glow: 'shadow-rose-950/40',
  }
}
