import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, RoundedRect } from '../primitives/DrawingPrimitives'

interface BlockDef {
  id: string
  label: string
  x: number
  y: number
  w: number
  h: number
  color: string
}

const BLOCKS: BlockDef[] = [
  { id: 'ref',    label: '参考输入\nr(t)',     x: 60,   y: 230, w: 110, h: 50, color: '#6366f1' },
  { id: 'error',  label: '误差\ne(t)',          x: 210,  y: 230, w: 90,  h: 50, color: '#8b5cf6' },
  { id: 'ctrl',   label: '控制器',              x: 340,  y: 220, w: 100, h: 70, color: '#3b82f6' },
  { id: 'act',    label: '执行器',              x: 480,  y: 220, w: 100, h: 70, color: '#0ea5e9' },
  { id: 'plant',  label: '被控对象\nP(s)',       x: 620,  y: 220, w: 100, h: 70, color: '#22c55e' },
  { id: 'out',    label: '输出\ny(t)',          x: 770,  y: 230, w: 90,  h: 50, color: '#eab308' },
  { id: 'sensor', label: '传感器',              x: 480,  y: 400, w: 100, h: 50, color: '#f97316' },
]

interface EdgeDef {
  from: string; to: string; label?: string
}

const EDGES: EdgeDef[] = [
  { from: 'ref', to: 'error', label: '+' },
  { from: 'error', to: 'ctrl' },
  { from: 'ctrl', to: 'act' },
  { from: 'act', to: 'plant' },
  { from: 'plant', to: 'out' },
  { from: 'out', to: 'sensor' },
  { from: 'sensor', to: 'error', label: '−' },
]

function getBlockRight(b: BlockDef) { return { x: b.x + b.w, y: b.y + b.h / 2 } }
function getBlockLeft(b: BlockDef) { return { x: b.x, y: b.y + b.h / 2 } }
function getBlockBottom(b: BlockDef) { return { x: b.x + b.w / 2, y: b.y + b.h } }
function getBlockTop(b: BlockDef) { return { x: b.x + b.w / 2, y: b.y } }

function edgeEndpoints(edge: EdgeDef, m: Map<string, BlockDef>) {
  const f = m.get(edge.from)!
  const t = m.get(edge.to)!
  if (edge.from === 'sensor' && edge.to === 'error')
    return { x1: getBlockTop(f).x, y1: getBlockTop(f).y, x2: getBlockBottom(t).x, y2: getBlockBottom(t).y }
  if (edge.from === 'out' && edge.to === 'sensor')
    return { x1: getBlockBottom(f).x, y1: getBlockBottom(f).y + 10, x2: getBlockTop(t).x, y2: getBlockTop(t).y - 10 }
  return { x1: getBlockRight(f).x, y1: getBlockRight(f).y, x2: getBlockLeft(t).x, y2: getBlockLeft(t).y }
}

function signalPos(edge: EdgeDef, m: Map<string, BlockDef>, p: number) {
  const { x1, y1, x2, y2 } = edgeEndpoints(edge, m)
  return { x: x1 + (x2 - x1) * p, y: y1 + (y2 - y1) * p }
}

export default function Chapter12Animation() {
  return (
    <AnimationCanvas
      controls
      duration={8000}
      sliders={[
        { key: 'gain', label: '增益 K', min: 0, max: 5, step: 0.1 },
        { key: 'speed', label: '信号速度', min: 0.2, max: 3, step: 0.1 },
      ]}
    >
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params } = useAnimation()
  const blockMap = new Map(BLOCKS.map(b => [b.id, b]))
  const speed = params.speed ?? 1
  const gain = params.gain ?? 1

  const dotPaths: EdgeDef[] = [
    { from: 'ref', to: 'error' }, { from: 'error', to: 'ctrl' },
    { from: 'ctrl', to: 'act' }, { from: 'act', to: 'plant' },
    { from: 'plant', to: 'out' }, { from: 'out', to: 'sensor' },
    { from: 'sensor', to: 'error' },
  ]

  const dotPts = dotPaths.map((edge, i) => {
    const p = ((progress * speed + i * 0.14) % 1)
    return signalPos(edge, blockMap, p)
  })

  const feedbackProgress = Math.min(progress * 2, 1)
  const refProgress = Math.min(progress * 4, 1)

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      <text x="480" y="30" textAnchor="middle" fill="#374151" fontSize={18} fontWeight={700} fontFamily="system-ui, sans-serif">
        反馈控制闭环框图
      </text>

      {EDGES.map((edge, i) => {
        const { x1, y1, x2, y2 } = edgeEndpoints(edge, blockMap)
        const color = edge.from === 'sensor' || edge.to === 'error' ? '#f97316' : '#6366f1'
        const visible = edge.from === 'ref' ? refProgress > 0.01 : (edge.from === 'sensor' ? feedbackProgress > 0.01 : true)
        if (!visible) return null
        return <Arrow key={i} x1={x1} y1={y1} x2={x2} y2={y2} color={color} strokeWidth={2} headSize={7} />
      })}

      {BLOCKS.map((b) => {
        const lines = b.label.split('\n')
        return (
          <g key={b.id}>
            <RoundedRect x={b.x} y={b.y} width={b.w} height={b.h} fill={b.color} rx={6} />
            {lines.map((line, li) => (
              <text
                key={li}
                x={b.x + b.w / 2} y={b.y + b.h / 2 + (li - (lines.length - 1) / 2) * 16}
                textAnchor="middle" dominantBaseline="central"
                fill="#fff" fontSize={13} fontWeight={600}
                fontFamily="system-ui, sans-serif"
              >
                {line}
              </text>
            ))}
          </g>
        )
      })}

      {dotPts.map((pt, i) => (
        <circle key={i} cx={pt.x} cy={pt.y} r={5} fill={['#6366f1','#8b5cf6','#3b82f6','#0ea5e9','#22c55e','#eab308','#f97316'][i]} opacity={0.8}>
          <animate attributeName="r" values="4;6;4" dur="0.5s" repeatCount="indefinite" />
        </circle>
      ))}

      <g transform="translate(680, 40)">
        <text fill="#6b7280" fontSize={12} fontFamily="monospace">增益 K = {gain.toFixed(2)}</text>
      </g>

      <text x="480" y="510" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily="system-ui, sans-serif">
        彩色圆点表示信号传播 · 拖动增益滑块改变系统响应 · 速度滑块控制信号流动快慢
      </text>
    </>
  )
}
