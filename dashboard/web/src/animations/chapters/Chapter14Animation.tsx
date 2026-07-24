import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, DashedLine } from '../primitives/DrawingPrimitives'

export default function Chapter14Animation() {
  return (
    <AnimationCanvas
      controls
      duration={6000}
      sliders={[
        { key: 'angle', label: '摆杆角度 θ', min: -30, max: 30, step: 1 },
        { key: 'force', label: '施加力 F', min: 0, max: 50, step: 1 },
      ]}
    >
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params } = useAnimation()

  const theta = ((params.angle ?? 15) * Math.PI) / 180
  const cartX = 400 + Math.sin(progress * 2 * Math.PI) * 80
  const groundY = 400
  const cartW = 120
  const cartH = 40
  const poleLen = 180

  const massX = cartX + poleLen * Math.sin(theta)
  const massY = groundY - cartH / 2 - poleLen * Math.cos(theta)

  const force = params.force ?? 20
  const forceScale = force / 30

  const animTheta = ((params.angle ?? 15) + Math.sin(progress * 2 * Math.PI) * 8) * Math.PI / 180
  const animPoleX = cartX + poleLen * Math.sin(animTheta)
  const animPoleY = groundY - cartH / 2 - poleLen * Math.cos(animTheta)
  const showAnim = Math.min(progress * 2, 1)

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      <text x="480" y="28" textAnchor="middle" fill="#374151" fontSize={18} fontWeight={700} fontFamily="system-ui, sans-serif">
        轮式倒立摆动力学
      </text>

      <line x1={40} y1={groundY} x2={920} y2={groundY} stroke="#374151" strokeWidth={2} />
      {Array.from({ length: 20 }, (_, i) => (
        <line key={i} x1={80 + i * 44} y1={groundY} x2={75 + i * 44} y2={groundY + 8} stroke="#9ca3af" strokeWidth={1.5} />
      ))}

      <rect x={cartX - cartW / 2} y={groundY - cartH} width={cartW} height={cartH} rx={4} fill="#6366f1" stroke="#4f46e5" strokeWidth={2} />
      <circle cx={cartX - cartW / 3} cy={groundY} r={10} fill="#374151" />
      <circle cx={cartX + cartW / 3} cy={groundY} r={10} fill="#374151" />

      <line x1={cartX} y1={groundY - cartH / 2} x2={massX} y2={massY} stroke="#374151" strokeWidth={4} strokeLinecap="round" />

      <g opacity={showAnim}>
        <line x1={cartX} y1={groundY - cartH / 2} x2={animPoleX} y2={animPoleY} stroke="#3b82f6" strokeWidth={2} strokeLinecap="round" strokeDasharray="4,3" />
      </g>

      <circle cx={massX} cy={massY} r={10} fill="#ef4444" />
      <text x={massX} y={massY + 1} textAnchor="middle" dominantBaseline="central" fill="#fff" fontSize={9} fontFamily="system-ui, sans-serif">
        m
      </text>

      <Arrow x1={cartX - cartW / 2 - 30 * forceScale} y1={groundY - cartH / 2} x2={cartX - cartW / 2} y2={groundY - cartH / 2} color="#ef4444" strokeWidth={3} headSize={10} />
      <text x={cartX - cartW / 2 - 30 * forceScale - 12} y={groundY - cartH / 2 + 4} textAnchor="end" fill="#ef4444" fontSize={13} fontWeight={600} fontFamily="system-ui, sans-serif">
        F
      </text>

      <Arrow x1={massX} y1={massY} x2={massX} y2={massY + 60} color="#22c55e" strokeWidth={2.5} headSize={8} />
      <text x={massX + 10} y={massY + 34} fill="#22c55e" fontSize={13} fontWeight={600} fontFamily="system-ui, sans-serif">
        mg
      </text>

      <path
        d={`M ${cartX + 30},${groundY - cartH / 2} A 30,30 0 0,1 ${cartX + 30 * Math.sin(theta)},${groundY - cartH / 2 - 30 * Math.cos(theta)}`}
        fill="none" stroke="#f59e0b" strokeWidth={1.5}
      />
      <text x={cartX + 38} y={groundY - cartH / 2 - 18} fill="#f59e0b" fontSize={12} fontFamily="monospace">
        θ
      </text>

      <DashedLine x1={cartX} y1={groundY - cartH / 2} x2={cartX} y2={groundY - cartH / 2 - poleLen - 20} color="#d1d5db" />

      <g transform="translate(680, 60)">
        <rect x="0" y="0" width="240" height="120" rx={6} fill="#f8fafc" stroke="#e2e8f0" strokeWidth={1} />
        <text x="120" y="20" textAnchor="middle" fill="#475569" fontSize={13} fontWeight={600} fontFamily="system-ui, sans-serif">
          参数
        </text>
        <text x="16" y="44" fill="#64748b" fontSize={12} fontFamily="monospace">
          θ = {(params.angle ?? 15).toFixed(1)}°
        </text>
        <text x="16" y="62" fill="#64748b" fontSize={12} fontFamily="monospace">
          F = {force.toFixed(1)} N
        </text>
        <text x="16" y="80" fill="#64748b" fontSize={12} fontFamily="monospace">
          m·g 向下
        </text>
        <text x="16" y="98" fill="#64748b" fontSize={12} fontFamily="monospace">
          M·ẍ = F − m·l·θ̈·cosθ + m·l·θ̇²·sinθ
        </text>
      </g>

      <text x="480" y="510" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
        红色力 F 作用于小车 · 蓝色虚线 = 动画摆动 · 绿色箭头 = 重力 mg
      </text>
    </>
  )
}
