import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, RoundedRect } from '../primitives/DrawingPrimitives'

const STAGES = [
  { id: '0',  label: '0', title: '数学与工具',      x: 180, y: 60 },
  { id: '1',  label: '1', title: '机器人仿真',       x: 60,  y: 190 },
  { id: '2',  label: '2', title: '经典控制',         x: 300, y: 190 },
  { id: '3',  label: '3', title: '状态估计与优化',   x: 60,  y: 320 },
  { id: '4',  label: '4', title: '学习控制',         x: 300, y: 320 },
  { id: '5',  label: '5', title: '应用型 VLA',       x: 180, y: 420 },
  { id: '6',  label: '6', title: '工程部署',         x: 180, y: 510 },
  { id: '7',  label: '7', title: '毕业项目',         x: 60,  y: 600 },
  { id: 'H',  label: 'H', title: '硬件选修',         x: 300, y: 600 },
]

const EDGES: [string, string][] = [
  ['0', '1'], ['0', '2'],
  ['1', '3'], ['2', '3'],
  ['1', '4'], ['2', '4'],
  ['3', '5'], ['4', '5'],
  ['5', '6'], ['6', '7'],
  ['0', 'H'], ['7', 'H'],
]

const STAGE_COLORS: Record<string, string> = {
  '0': '#6366f1', '1': '#8b5cf6', '2': '#a855f7',
  '3': '#06b6d4', '4': '#0ea5e9', '5': '#22c55e',
  '6': '#eab308', '7': '#f97316', 'H': '#ef4444',
}

export default function Chapter00Animation() {
  return (
    <AnimationCanvas controls sliders={[]} duration={6000}>
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress } = useAnimation()
  const reveal = Math.min(progress * 2, 1)
  const nodeMap = new Map(STAGES.map(s => [s.id, s]))

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      <text x="480" y="32" textAnchor="middle" fill="#374151" fontSize={18} fontWeight={700} fontFamily="system-ui, sans-serif">
        课程依赖地图
      </text>

      {EDGES.map(([from, to], i) => {
        const src = nodeMap.get(from)!
        const dst = nodeMap.get(to)!
        const visible = reveal > i / EDGES.length
        if (!visible) return null
        return (
          <Arrow
            key={i}
            x1={src.x + 80} y1={src.y + 30}
            x2={dst.x + 80} y2={dst.y}
            color="#cbd5e1" strokeWidth={2}
            opacity={Math.min(1, reveal * (1 + (EDGES.length - i) * 0.05))}
          />
        )
      })}

      {STAGES.map((s, i) => {
        const visible = reveal > i / STAGES.length
        if (!visible) return null
        const color = STAGE_COLORS[s.id]
        return (
          <g key={s.id}>
            <RoundedRect x={s.x} y={s.y} width={160} height={50} fill={color} rx={8} />
            <text x={s.x + 16} y={s.y + 30} fill="#fff" fontSize={16} fontWeight={700} fontFamily="system-ui, sans-serif">
              {s.label}
            </text>
            <text x={s.x + 160} y={s.y + 30} textAnchor="end" fill="#fff" fontSize={13} fontFamily="system-ui, sans-serif">
              {s.title}
            </text>
          </g>
        )
      })}

      <g opacity={0.5}>
        <text x="30" y="510" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
          箭头 = 先修依赖 · 各阶段按顺序推进
        </text>
        <text x="30" y="528" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
          点击播放查看课程路径
        </text>
      </g>
    </>
  )
}
