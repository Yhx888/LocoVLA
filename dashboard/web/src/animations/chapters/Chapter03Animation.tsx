import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, CoordinateAxes, DashedLine, RoundedRect } from '../primitives/DrawingPrimitives'

export default function Chapter03Animation() {
  return (
    <AnimationCanvas
      controls
      duration={6000}
      sliders={[
        { key: 'angle', label: '旋转角 θ', min: -180, max: 180, step: 1 },
      ]}
    >
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params } = useAnimation()

  const angleRad = (params.angle ?? 30) * Math.PI / 180
  const vecLen = 120
  const origX = 300
  const origY = 300
  const dotX = origX + vecLen * Math.cos(angleRad)
  const dotY = origY - vecLen * Math.sin(angleRad)

  const animAngle = progress * 2 * Math.PI
  const animDotX = origX + vecLen * Math.cos(animAngle)
  const animDotY = origY - vecLen * Math.sin(animAngle)
  const activeProgress = Math.min(progress * 1.5, 1)

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      <text x="480" y="32" textAnchor="middle" fill="#374151" fontSize={18} fontWeight={700} fontFamily="system-ui, sans-serif">
        坐标变换可视化
      </text>

      <CoordinateAxes originX={origX} originY={origY} length={180} />
      <circle cx={origX} cy={origY} r={vecLen} fill="none" stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4,4" />

      <g opacity={activeProgress}>
        <Arrow x1={origX} y1={origY} x2={animDotX} y2={animDotY} color="#3b82f6" strokeWidth={3} headSize={10} />
      </g>

      <Arrow x1={origX} y1={origY} x2={dotX} y2={dotY} color="#ef4444" strokeWidth={2.5} headSize={9} />

      <DashedLine x1={dotX} y1={origY} x2={dotX} y2={dotY} color="#f87171" />
      <DashedLine x1={origX} y1={dotY} x2={dotX} y2={dotY} color="#f87171" />

      <text x={dotX + 6} y={origY - 4} fill="#f87171" fontSize={11} fontFamily="monospace">
        v cos({(params.angle ?? 30).toFixed(0)}°)
      </text>
      <text x={origX + 6} y={dotY + 4} fill="#f87171" fontSize={11} fontFamily="monospace">
        v sin({(params.angle ?? 30).toFixed(0)}°)
      </text>

      <g transform="translate(580, 120)">
        <RoundedRect x={0} y={0} width={320} height={120} fill="#f8fafc" stroke="#e2e8f0" rx={8} />
        <text x="160" y="22" textAnchor="middle" fill="#475569" fontSize={14} fontWeight={600} fontFamily="system-ui, sans-serif">
          旋转矩阵
        </text>
        <text x="40" y="50" fill="#64748b" fontSize={12} fontFamily="system-ui, sans-serif">
          x' = x cos θ − y sin θ
        </text>
        <text x="40" y="70" fill="#64748b" fontSize={12} fontFamily="system-ui, sans-serif">
          y' = x sin θ + y cos θ
        </text>
        <text x="40" y="95" fill="#3b82f6" fontSize={12} fontFamily="monospace">
          cos θ = {Math.cos(angleRad).toFixed(4)}
        </text>
        <text x="40" y="113" fill="#ef4444" fontSize={12} fontFamily="monospace">
          sin θ = {Math.sin(angleRad).toFixed(4)}
        </text>
      </g>

      <text x="300" y="500" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
        拖动滑块改变旋转角 · 红色向量 = 当前角度 · 蓝色向量 = 动画面板
      </text>
    </>
  )
}
