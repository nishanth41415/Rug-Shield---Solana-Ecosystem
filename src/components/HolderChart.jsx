import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const shortenAddress = (address) => `${address.slice(0, 4)}...${address.slice(-4)}`

function HolderChart({ holders }) {
  const chartData = holders.map((holder, index) => ({
    name: `#${index + 1}`,
    address: holder.address,
    percentage: holder.percentage,
  }))

  return (
    <div className="relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-[#101720]/82 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl">
      <span className="pointer-events-none absolute -right-12 top-8 h-32 w-32 rounded-full bg-cyan-300/7 blur-3xl" />
      <div className="relative mb-5 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-[1.35rem] font-semibold leading-tight text-white">
            Holder Distribution
          </h2>
          <p className="mt-1 text-sm text-gray-500">Top wallets by visible supply share.</p>
        </div>
        <span className="w-fit rounded-full bg-white/[0.04] px-3 py-1 text-xs font-semibold text-gray-300 ring-1 ring-white/10">
          Top {holders.length}
        </span>
      </div>

      <div className="relative h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 12, left: -14, bottom: 0 }}>
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <YAxis
              axisLine={false}
              tickFormatter={(value) => `${value}%`}
              tickLine={false}
              tick={{ fill: '#6b7280', fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: 'rgba(34, 211, 238, 0.08)' }}
              formatter={(value) => [`${value}%`, 'Holding']}
              labelFormatter={(_, payload) => {
                const address = payload?.[0]?.payload?.address
                return address ? shortenAddress(address) : 'Holder'
              }}
              contentStyle={{
                background: '#101620',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '12px',
                color: '#f9fafb',
              }}
            />
            <Bar dataKey="percentage" fill="#22d3ee" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-5 grid gap-2 md:grid-cols-2">
        {holders.map((holder, index) => (
          <div
            className={`flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2 shadow-sm shadow-black/10 ${
              index % 4 === 1 ? 'md:translate-x-1' : ''
            }`}
            key={holder.address}
          >
            <code className="truncate text-xs text-gray-400">
              #{index + 1} {shortenAddress(holder.address)}
            </code>
            <span className="shrink-0 text-sm font-semibold text-cyan-200">
              {holder.percentage}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default HolderChart
