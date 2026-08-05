import { useEffect, useMemo } from 'react'
import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'

const FONT = 'system-ui, "Noto Sans SC", sans-serif'

const SLIDERS = [
  { key: 'Kp', label: 'Kp', min: 0, max: 5, step: 0.1 },
  { key: 'Ki', label: 'Ki', min: 0, max: 3, step: 0.1 },
  { key: 'Kd', label: 'Kd', min: 0, max: 2, step: 0.05 },
]
const DEFAULTS = { Kp: 1.5, Ki: 0.6, Kd: 0.3 }

const N = 150
const T_END = 10
const DT = T_END / N
/* 固定值域映射：曲线始终对齐同一坐标系，不随数据跳动 */
const PLOT_MIN = -0.4
const PLOT_MAX = 1.4

const CHART_X = 500
const CHART_Y = 100
const CHART_W = 420
const CHART_H = 200
const BAR_X = 60
const BAR_W = 380
const BAR_H = 20
const BAR_GAP = 30
const BAR_Y0 = 120

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
const clamp01 = (t: number) => clamp(t, 0, 1)
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)
const mapY = (v: number) => CHART_Y + CHART_H - ((v - PLOT_MIN) / (PLOT_MAX - PLOT_MIN)) * CHART_H

/* ------------------------------------------------------------------ */
/*  确定性信号数据：目标 2.5s 阶跃，被控量 3s 起延迟上升（带固定噪声）  */
/* ------------------------------------------------------------------ */

function buildErrData(): number[] {
  const out: number[] = []
  for (let i = 0; i < N; i++) {
    const t = i * DT
    const r = t < 2.5 ? 0 : 1                                    // 目标阶跃
    const y = t < 3 ? 0 : 1 - Math.exp(-1.1 * (t - 3))           // 被控量延迟响应
    const noise = 0.012 * Math.sin(31 * t) + 0.009 * Math.sin(83 * t + 1.7) // 确定性测量噪声
    out.push(r - y + noise)
  }
  return out
}

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

export default function Chapter13Animation() {
  return (
    <AnimationCanvas controls duration={10000} sliders={SLIDERS}>
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params, setParam, playing, time } = useAnimation()
  /* 重置（或挂载）时参数回归默认 */
  useEffect(() => {
    if (!playing && time === 0) Object.entries(DEFAULTS).forEach(([k, v]) => setParam(k, v))
  }, [playing, time, setParam])

  const p = progress
  const fade = (t0: number) => clamp01((p - t0) / 0.1)
  const grow = (t0: number) => easeOutCubic(clamp01((p - t0) / 0.14))

  const Kp = params.Kp ?? DEFAULTS.Kp
  const Ki = params.Ki ?? DEFAULTS.Ki
  const Kd = params.Kd ?? DEFAULTS.Kd

  const errData = useMemo(buildErrData, [])
  /* P/I/D/Total 由当前增益实时计算 */
  const pData = errData.map(e => Kp * e)
  const iData: number[] = []
  let iAcc = 0
  for (let j = 0; j < N; j++) {
    iAcc += errData[j] * DT
    iAcc = clamp(iAcc, -1, 1)
    iData.push(Ki * iAcc)
  }
  const dData = errData.map((e, j) => (j === 0 ? 0 : (Kd * (errData[j] - errData[j - 1])) / DT))
  const totalData = errData.map((_, j) => clamp(pData[j] + iData[j] + dData[j], -1, 1))

  const toIdx = Math.max(2, Math.floor(p * N))
  const iCur = Math.min(Math.floor(p * N), N - 1)
  const tCur = iCur * DT
  const scanX = CHART_X + p * CHART_W

  /* D 通道可视化：当前点切线（斜率 = de/dt） */
  const slope = iCur > 0 ? (errData[iCur] - errData[iCur - 1]) / DT : 0
  const tanK = Math.max(-12, Math.min(12, slope * 0.35))
  const ePt = { x: scanX, y: mapY(errData[iCur]) }

  /* 积分面积（I 分量 = 曲线下面积，随扫描线推进） */
  const areaD = (() => {
    if (toIdx < 2) return null
    const stepX = CHART_W / (N - 1)
    let d = `M${CHART_X},${mapY(0)}`
    for (let i = 0; i < toIdx; i++) d += ` L${CHART_X + i * stepX},${mapY(errData[i])}`
    d += ` L${CHART_X + (toIdx - 1) * stepX},${mapY(0)} Z`
    return d
  })()

  /* 固定坐标曲线 */
  const curveD = (data: number[]) => {
    const stepX = CHART_W / (N - 1)
    let d = ''
    for (let i = 0; i < toIdx; i++) {
      d += `${i === 0 ? 'M' : 'L'}${(CHART_X + i * stepX).toFixed(1)},${mapY(data[i]).toFixed(1)}`
    }
    return d
  }

  return (
    <>
      <style>{`
        .ch13-bar { transition: width 130ms ease-out; }
        @media (prefers-reduced-motion: reduce) { .ch13-bar { transition: none; } }
      `}</style>

      <defs>
        <clipPath id="ch13-plot">
          <rect x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} />
        </clipPath>
      </defs>

      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      {/* 标题（静态） */}
      <text x="480" y="30" textAnchor="middle" fill="#111827" fontSize={20} fontWeight={700} fontFamily={FONT}>
        PID 控制可视化
      </text>
      <text x="480" y="50" textAnchor="middle" fill="#9ca3af" fontSize={12} fontFamily={FONT}>
        误差进来 → 三个通道各算各的 → 相加成控制量
      </text>

      {/* 左区：三通道贡献柱 */}
      <text x={BAR_X} y={BAR_Y0 - 16} fill="#6b7280" fontSize={12} fontFamily={FONT}>
        三通道贡献 · u = P + I + D
      </text>
      {[
        { label: 'P', value: pData[iCur], color: '#3b82f6', t0: 0.16 },
        { label: 'I', value: iData[iCur], color: '#22c55e', t0: 0.20 },
        { label: 'D', value: dData[iCur], color: '#f59e0b', t0: 0.24 },
        { label: 'Total', value: totalData[iCur], color: '#ef4444', t0: 0.30 },
      ].map((item, i) => {
        const o = fade(item.t0)
        if (o <= 0.01) return null
        const y = BAR_Y0 + i * (BAR_H + BAR_GAP)
        const norm = clamp((item.value + 1) / 2, 0, 1)
        const len = norm * BAR_W * grow(item.t0)
        return (
          <g key={item.label}>
            <rect x={BAR_X} y={y} width={BAR_W} height={BAR_H} rx={4} fill="#f3f4f6" stroke="#e5e7eb" strokeWidth={1} />
            <rect className="ch13-bar" x={BAR_X} y={y} width={Math.max(0, len)} height={BAR_H} rx={4}
              fill={item.color} opacity={0.75} />
            <text x={BAR_X - 10} y={y + BAR_H / 2} textAnchor="end" dominantBaseline="central"
              fill="#374151" fontSize={13} fontWeight={600} fontFamily={FONT}>
              {item.label}
            </text>
            <text x={BAR_X + BAR_W + 10} y={y + BAR_H / 2} dominantBaseline="central"
              fill="#6b7280" fontSize={12} fontFamily="monospace">
              {item.value.toFixed(3)}
            </text>
          </g>
        )
      })}

      {/* 左区：公式行（弱化，静态） */}
      <g opacity={fade(0.55)}>
        <text x={BAR_X} y={256} fill="#9ca3af" fontSize={11} fontFamily={FONT}>P = Kp · e(t)</text>
        <text x={BAR_X} y={274} fill="#9ca3af" fontSize={11} fontFamily={FONT}>I = Ki · ∫ e dt（曲线下面积）</text>
        <text x={BAR_X} y={292} fill="#9ca3af" fontSize={11} fontFamily={FONT}>D = Kd · de/dt（切线斜率）</text>
        <text x={BAR_X} y={314} fill="#6b7280" fontSize={12} fontWeight={600} fontFamily={FONT}>
          u(t) = P + I + D
        </text>
      </g>

      {/* 右区：图表 */}
      <g opacity={fade(0.06)}>
        <text x={CHART_X + CHART_W / 2} y={CHART_Y - 12} textAnchor="middle" fill="#6b7280" fontSize={12} fontFamily={FONT}>
          误差 e(t) 与输出 u(t)
        </text>
        <text x={CHART_X + CHART_W} y={CHART_Y - 12} textAnchor="end" fill="#9ca3af" fontSize={11} fontFamily="monospace">
          t = {tCur.toFixed(1)}s
        </text>
        <rect x={CHART_X} y={CHART_Y} width={CHART_W} height={CHART_H} fill="#fff" stroke="#e5e7eb" strokeWidth={1} rx={4} />
        {/* 目标线与零线 */}
        <line x1={CHART_X} y1={mapY(1)} x2={CHART_X + CHART_W} y2={mapY(1)}
          stroke="#d1d5db" strokeWidth={1} strokeDasharray="5,4" />
        <text x={CHART_X + CHART_W - 4} y={mapY(1) - 5} textAnchor="end" fill="#9ca3af" fontSize={10} fontFamily={FONT}>目标</text>
        <line x1={CHART_X} y1={mapY(0)} x2={CHART_X + CHART_W} y2={mapY(0)} stroke="#f3f4f6" strokeWidth={1} />
      </g>

      {/* 积分面积（I 分量可视化） */}
      <g opacity={fade(0.18)}>
        {areaD && <path d={areaD} fill="#22c55e" opacity={0.14} />}
      </g>

      {/* 曲线（固定映射，超界裁剪 = 饱和顶格） */}
      <g clipPath="url(#ch13-plot)">
        <g opacity={fade(0.16)}>
          <path d={curveD(pData)} fill="none" stroke="#3b82f6" strokeWidth={1.2} />
        </g>
        <g opacity={fade(0.20)}>
          <path d={curveD(iData)} fill="none" stroke="#22c55e" strokeWidth={1.2} />
        </g>
        <g opacity={fade(0.24)}>
          <path d={curveD(dData)} fill="none" stroke="#f59e0b" strokeWidth={1.2} />
        </g>
        <g opacity={fade(0.10)}>
          <path d={curveD(errData)} fill="none" stroke="#111827" strokeWidth={2.5} />
        </g>
        <g opacity={fade(0.30)}>
          <path d={curveD(totalData)} fill="none" stroke="#ef4444" strokeWidth={2.5} />
        </g>

        {/* 扫描线与当前点 */}
        <g opacity={fade(0.10)}>
          <line x1={scanX} y1={CHART_Y} x2={scanX} y2={CHART_Y + CHART_H} stroke="#94a3b8" strokeWidth={1} />
          <circle cx={scanX} cy={mapY(errData[iCur])} r={4} fill="#111827" stroke="#fff" strokeWidth={1.5} />
          <circle cx={scanX} cy={mapY(totalData[iCur])} r={4} fill="#ef4444" stroke="#fff" strokeWidth={1.5} />
        </g>

        {/* D 通道：当前点切线 */}
        <g opacity={fade(0.26)}>
          <line x1={ePt.x - 14} y1={ePt.y + tanK} x2={ePt.x + 14} y2={ePt.y - tanK}
            stroke="#f59e0b" strokeWidth={2} />
        </g>
      </g>

      {/* 图例 */}
      <g opacity={fade(0.60)}>
        {[
          { label: 'e(t)', color: '#111827', wide: true },
          { label: 'P', color: '#3b82f6' },
          { label: 'I', color: '#22c55e' },
          { label: 'D', color: '#f59e0b' },
          { label: 'Total', color: '#ef4444', wide: true },
        ].map((item, i) => (
          <g key={item.label} transform={`translate(${CHART_X + i * 86}, ${CHART_Y + CHART_H + 18})`}>
            <line x1={0} y1={6} x2={18} y2={6} stroke={item.color} strokeWidth={item.wide ? 2.5 : 1.5} />
            <text x={22} y={10} fill="#6b7280" fontSize={11} fontFamily={FONT}>{item.label}</text>
          </g>
        ))}
        <text x={CHART_X + CHART_W} y={CHART_Y + CHART_H + 18} textAnchor="end" fill="#9ca3af" fontSize={10} fontFamily={FONT}>
          扫描线 = 当前时刻
        </text>
      </g>

      {/* 底部提示 */}
      <g opacity={fade(0.72)}>
        <text x="480" y="512" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          拖动 Kp/Ki/Kd：P 跟随误差 · I 累积曲线下面积 · D 响应变化率（阶跃处尖峰）
        </text>
      </g>
    </>
  )
}
