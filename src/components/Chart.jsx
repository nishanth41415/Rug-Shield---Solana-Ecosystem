import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function Chart({ signals }) {
  const risky = signals.filter((signal) => signal.triggered).length
  const safe = signals.length - risky
  const data = [
    { name: 'Safe', value: safe, color: '#34d399' },
    { name: 'Risky', value: risky, color: '#fb7185' },
  ]

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/80 p-5 shadow-lg">
      <div className="mb-5 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">Signal Distribution</h2>
        <span className="text-sm text-gray-400">
          {safe} safe / {risky} risky
        </span>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 6, left: -24, bottom: 0 }}>
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#6b7280', fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: 'rgba(255,255,255,0.04)' }}
              contentStyle={{
                background: '#111827',
                border: '1px solid #374151',
                borderRadius: '10px',
                color: '#f9fafb',
              }}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {data.map((entry) => (
                <Cell fill={entry.color} key={entry.name} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default Chart
