import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { SignalCurve } from '../primitives/DrawingPrimitives'

function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)) }

export default function Chapter13Animation() {
  return (
    <AnimationCanvas
      controls
      duration={10000}
      sliders={[
        { key: 'Kp', label: 'Kp', min: 0, max: 5, step: 0.1 },
        { key: 'Ki', label: 'Ki', min: 0, max: 3, step: 0.1 },
        { key: 'Kd', label: 'Kd', min: 0, max: 2, step: 0.05 },
      ]}
    >
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params } = useAnimation()

  const Kp = params.Kp ?? 1.5
  const Ki = params.Ki ?? 0.6
  const Kd = params.Kd ?? 0.3
  const setpoint = 1.0

  const t = progress * 10
  const N = 120
  const dt = 10 / N

  const timeData: number[] = Array.from({ length: N }, (_, i) => i * dt)
  const errData: number[] = timeData.map(ti => {
    const target = ti < 0.5 ? 0 : setpoint
    const raw = target - (ti < 1 ? 0 : setpoint * (1 - Math.exp(-2 * (ti - 1))))
    const noise = (Math.random() - 0.5) * 0.02
    return raw + noise
  })

  const pData = errData.map(e => Kp * e)
  const iData: number[] = []
  let iAcc = 0
  for (let j = 0; j < N; j++) {
    iAcc += errData[j] * dt
    iAcc = clamp(iAcc, -1, 1)
    iData.push(Ki * iAcc)
  }
  const dData = errData.map((e, j) => {
    if (j === 0) return 0
    return Kd * (errData[j] - errData[j - 1]) / dt
  })
  const totalData = errData.map((_, j) => clamp(pData[j] + iData[j] + dData[j], -1, 1))

  const displayValue = totalData.length > 0 ? totalData[Math.min(Math.floor(progress * N), N - 1)] : 0

  const CHART_X = 500
  const CHART_Y = 120
  const CHART_W = 400
  const CHART_H = 160

  const BAR_X = 60
  const BAR_W = 380
  const BAR_H = 22
  const BAR_GAP = 8
  const BAR_START_Y = 110

  function ContributionBar({ label, value, color, y }: { label: string; value: number; color: string; y: number }) {
    const norm = clamp((value + 1) / 2, 0, 1)
    const barLen = norm * BAR_W
    return (
      <g>
        <rect x={BAR_X} y={y} width={BAR_W} height={BAR_H} rx={4} fill="#f3f4f6" stroke="#e5e7eb" strokeWidth={1} />
        <rect x={BAR_X} y={y} width={barLen} height={BAR_H} rx={4} fill={color} opacity={0.7} />
        <text x={BAR_X - 8} y={y + BAR_H / 2} textAnchor="end" dominantBaseline="central" fill="#374151" fontSize={13} fontWeight={600} fontFamily="system-ui, sans-serif">
          {label}
        </text>
        <text x={BAR_X + BAR_W + 8} y={y + BAR_H / 2} dominantBaseline="central" fill="#6b7280" fontSize={12} fontFamily="monospace">
          {value.toFixed(3)}
        </text>
      </g>
    )
  }

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      <text x="480" y="30" textAnchor="middle" fill="#374151" fontSize={18} fontWeight={700} fontFamily="system-ui, sans-serif">
        PID 控制可视化
      </text>

      <text x={BAR_X} y={BAR_START_Y - 16} fill="#6b7280" fontSize={12} fontFamily="system-ui, sans-serif">
        各分量贡献
      </text>

      <ContributionBar label="P" value={pData[Math.min(Math.floor(progress * N), N - 1)] ?? 0} color="#3b82f6" y={BAR_START_Y} />
      <ContributionBar label="I" value={iData[Math.min(Math.floor(progress * N), N - 1)] ?? 0} color="#22c55e" y={BAR_START_Y + BAR_H + BAR_GAP} />
      <ContributionBar label="D" value={dData[Math.min(Math.floor(progress * N), N - 1)] ?? 0} color="#f59e0b" y={BAR_START_Y + (BAR_H + BAR_GAP) * 2} />
      <ContributionBar label="Total" value={displayValue} color="#ef4444" y={BAR_START_Y + (BAR_H + BAR_GAP) * 3} />

      <text x={CHART_X + CHART_W / 2} y={CHART_Y - 6} textAnchor="middle" fill="#6b7280" fontSize={12} fontFamily="system-ui, sans-serif">
        输出信号
      </text>

      <rect x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} fill="#fff" stroke="#e5e7eb" strokeWidth={1} rx={4} />

      <line x1={CHART_X} y1={CHART_Y + CHART_H / 2} x2={CHART_X + CHART_W} y2={CHART_Y + CHART_H / 2} stroke="#f3f4f6" strokeWidth={1} />
      <line x1={CHART_X + CHART_W / 3} y1={CHART_Y} x2={CHART_X + CHART_W / 3} y2={CHART_Y + CHART_H} stroke="#f9fafb" strokeWidth={1} />
      <line x1={CHART_X + CHART_W * 2 / 3} y1={CHART_Y} x2={CHART_X + CHART_W * 2 / 3} y2={CHART_Y + CHART_H} stroke="#f9fafb" strokeWidth={1} />

      <SignalCurve data={pData.slice(0, Math.max(2, Math.floor(progress * N)))} x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} color="#3b82f6" strokeWidth={1.5} />
      <SignalCurve data={iData.slice(0, Math.max(2, Math.floor(progress * N)))} x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} color="#22c55e" strokeWidth={1.5} />
      <SignalCurve data={dData.slice(0, Math.max(2, Math.floor(progress * N)))} x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} color="#f59e0b" strokeWidth={1.5} />
      <SignalCurve data={totalData.slice(0, Math.max(2, Math.floor(progress * N)))} x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} color="#ef4444" strokeWidth={2.5} />

      <text x={CHART_X + CHART_W / 2} y={CHART_Y + CHART_H + 14} textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">时间 (s)</text>
      <text x={CHART_X - 4} y={CHART_Y + CHART_H / 2 + 4} textAnchor="end" fill="#9ca3af" fontSize={10} fontFamily="monospace">0</text>
      <text x={CHART_X - 4} y={CHART_Y + 4} textAnchor="end" fill="#9ca3af" fontSize={10} fontFamily="monospace">1</text>

      <g transform={`translate(${CHART_X}, ${CHART_Y + CHART_H + 24})`}>
        {[
          { label: 'P', color: '#3b82f6' },
          { label: 'I', color: '#22c55e' },
          { label: 'D', color: '#f59e0b' },
          { label: '总计', color: '#ef4444' },
        ].map((item, i) => (
          <g key={i} transform={`translate(${i * 90}, 0)`}>
            <line x1={0} y1={6} x2={16} y2={6} stroke={item.color} strokeWidth={2} />
            <text x={20} y={10} fill="#6b7280" fontSize={11} fontFamily="system-ui, sans-serif">{item.label}</text>
          </g>
        ))}
      </g>

      <text x="480" y="510" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
        拖动 Kp/Ki/Kd 滑块调节各分量 · 红色曲线为总控制输出
      </text>
    </>
  )
}
