import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { ArrowHead } from '../primitives/DrawingPrimitives'

const FONT = 'system-ui, "Noto Sans SC", sans-serif'

/* ------------------------------------------------------------------ */
/*  阶段数据：9 个节点 + 依赖边（树状课程地图）                         */
/* ------------------------------------------------------------------ */

interface StageDef { id: string; label: string; title: string; x: number; y: number; branch?: boolean }

const STAGES: StageDef[] = [
  { id: '0', label: '0', title: '数学与工具',    x: 410, y: 56 },
  { id: '1', label: '1', title: '机器人仿真',     x: 205, y: 156 },
  { id: '2', label: '2', title: '经典控制',       x: 605, y: 156, branch: true },
  { id: '3', label: '3', title: '状态估计与优化', x: 165, y: 256 },
  { id: '4', label: '4', title: '学习控制',       x: 655, y: 256, branch: true },
  { id: '5', label: '5', title: '应用型 VLA',     x: 410, y: 356 },
  { id: '6', label: '6', title: '工程部署',       x: 205, y: 456 },
  { id: '7', label: '7', title: '毕业项目',       x: 615, y: 456 },
  { id: 'H', label: 'H', title: '硬件选修',       x: 410, y: 456, branch: true },
]

const STAGE_COLORS: Record<string, string> = {
  '0': '#6366f1', '1': '#8b5cf6', '2': '#a855f7',
  '3': '#06b6d4', '4': '#0ea5e9', '5': '#22c55e',
  '6': '#eab308', '7': '#f97316', 'H': '#ef4444',
}

const NODE_W = 140
const NODE_H = 44
const BY_ID = new Map(STAGES.map(s => [s.id, s]))
type Pt = [number, number]
const nodeTop = (s: StageDef): Pt => [s.x + NODE_W / 2, s.y]
const nodeBottom = (s: StageDef): Pt => [s.x + NODE_W / 2, s.y + NODE_H]
const nodeRight = (s: StageDef): Pt => [s.x + NODE_W, s.y + NODE_H / 2]

/* 主线（建议学习路径）：0→1→3→5→6→7，按段描画 */
const MAIN_EDGES: { pts: Pt[] }[] = [
  { pts: [nodeBottom(BY_ID.get('0')!), [480, 128], [275, 128], nodeTop(BY_ID.get('1')!)] as Pt[] },
  { pts: [nodeBottom(BY_ID.get('1')!), [275, 240], [235, 240], nodeTop(BY_ID.get('3')!)] as Pt[] },
  { pts: [nodeBottom(BY_ID.get('3')!), [235, 340], [480, 340], nodeTop(BY_ID.get('5')!)] as Pt[] },
  { pts: [nodeBottom(BY_ID.get('5')!), [480, 430], [275, 430], nodeTop(BY_ID.get('6')!)] as Pt[] },
  { pts: [nodeRight(BY_ID.get('6')!), nodeRight(BY_ID.get('7')!)] },
]
/* 主线节点入场顺序（0 在初始帧即显示，形成"起点"） */
const MAIN_ORDER = ['0', '1', '3', '5', '6', '7']
const MAIN_NODE_T: Record<string, number> = { '0': -0.1, '1': 0.14, '3': 0.23, '5': 0.32, '6': 0.40, '7': 0.48 }
const BRANCH_NODE_T: Record<string, number> = { '2': 0.58, '4': 0.64, 'H': 0.74 }

/* 光点完整路径：主线 + 穿过节点内部（节点内权重低 = 信号"处理中"减速） */
const TRAVEL_PTS: Pt[] = [
  [480, 100], [480, 128], [275, 128], [275, 156],   // 0 底 → 1 顶
  [275, 200],                                        // 穿过 1
  [275, 240], [235, 240], [235, 256],                // → 3 顶
  [235, 300],                                        // 穿过 3
  [235, 340], [480, 340], [480, 356],                // → 5 顶
  [480, 400],                                        // 穿过 5
  [480, 430], [275, 430], [275, 456],                // → 6 顶
  [275, 478], [345, 478],                            // 穿过 6
  [615, 478],                                        // → 7 左缘
]
const INSIDE_SEGS = new Set<number>([3, 5, 7, 9, 10]) // 节点内部段（较慢）

/* 分支依赖边（先画，弱化） */
interface BranchEdge { pts: Pt[]; from: string; t: number; dashed?: boolean }
const BRANCH_EDGES: BranchEdge[] = [
  { pts: [[550, 78], [675, 78], [675, 156]], from: '0', t: 0.56 },
  { pts: [[675, 200], [675, 248], [165, 248], [165, 278]], from: '2', t: 0.60 },
  { pts: [[275, 200], [275, 235], [725, 235], [725, 278]], from: '1', t: 0.64 },
  { pts: [[675, 200], [675, 235], [725, 235], [725, 278]], from: '2', t: 0.68 },
  { pts: [[725, 300], [725, 340], [480, 340], [480, 356]], from: '4', t: 0.72 },
  { pts: [[550, 78], [920, 78], [920, 478], [550, 478]], from: '0', t: 0.74, dashed: true },
  { pts: [[685, 500], [685, 524], [480, 524], [480, 456]], from: '7', t: 0.78, dashed: true },
]

/* ------------------------------------------------------------------ */
/*  缓动与几何工具                                                      */
/* ------------------------------------------------------------------ */

const clamp01 = (t: number) => Math.max(0, Math.min(1, t))
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)
const easeOutBack = (t: number) => {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

/* 过滤出合法坐标点，避免异常数据触发崩溃 */
const validPts = (pts: Pt[]) => pts.filter(pt => Array.isArray(pt) && pt.length === 2)

function polylineLength(pts: Pt[], weight = (i: number) => 1) {
  const safe = validPts(pts)
  let len = 0
  for (let i = 1; i < safe.length; i++) {
    len += Math.hypot(safe[i][0] - safe[i - 1][0], safe[i][1] - safe[i - 1][1]) * weight(i)
  }
  return len
}

function pointAlong(pts: Pt[], s: number, weight = (i: number) => 1): Pt | null {
  const safe = validPts(pts)
  if (safe.length < 2) return null
  const total = polylineLength(safe, weight)
  const d = clamp01(s) * total
  let acc = 0
  for (let i = 1; i < safe.length; i++) {
    const segLen = Math.hypot(safe[i][0] - safe[i - 1][0], safe[i][1] - safe[i - 1][1]) * weight(i)
    if (acc + segLen >= d) {
      const t = segLen > 0 ? (d - acc) / segLen : 0
      return [safe[i - 1][0] + (safe[i][0] - safe[i - 1][0]) * t, safe[i - 1][1] + (safe[i][1] - safe[i - 1][1]) * t]
    }
    acc += segLen
  }
  return safe[safe.length - 1]
}

function endAngle(pts: Pt[]) {
  const safe = validPts(pts)
  if (safe.length < 2) return 0
  const a = safe[safe.length - 2]
  const b = safe[safe.length - 1]
  return Math.atan2(b[1] - a[1], b[0] - a[0])
}

const TRAVEL_WEIGHT = (i: number) => (INSIDE_SEGS.has(i) ? 0.3 : 1)

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

export default function Chapter00Animation() {
  return (
    <AnimationCanvas controls sliders={[]} duration={9000}>
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress } = useAnimation()

  const p = progress
  const fade = (t0: number) => clamp01((p - t0) / 0.05)

  /* 主线各段描画进度（错峰，easeInOut 缓动） */
  const MAIN_T0 = [0.10, 0.17, 0.26, 0.35, 0.44]
  const reveals = MAIN_EDGES.map((_, i) => easeInOut(clamp01((p - MAIN_T0[i]) / 0.08)))

  /* 光点：主程走一遍 + 结尾再循环一圈 */
  const phase1 = (p - 0.10) / 0.42
  const phase2 = (p - 0.86) / 0.14
  const spot = phase1 >= 0 && phase1 < 1
    ? pointAlong(TRAVEL_PTS, phase1, TRAVEL_WEIGHT)
    : phase2 >= 0 && phase2 < 1
      ? pointAlong(TRAVEL_PTS, phase2, TRAVEL_WEIGHT)
      : null
  const spotDim = phase2 >= 0 ? 0.55 : 1
  /* 当前光点所在的节点 = 高亮 */
  const highlightId = phase1 >= 0 && phase1 < 1
    ? MAIN_ORDER[Math.min(Math.floor(phase1 * MAIN_ORDER.length), MAIN_ORDER.length - 1)]
    : phase2 >= 0 && phase2 < 1
      ? MAIN_ORDER[Math.min(Math.floor(phase2 * MAIN_ORDER.length), MAIN_ORDER.length - 1)]
      : null

  /* 折线转 SVG points 字符串；对异常数据容错（跳过非数组元素），保证任何数据都不会让渲染崩溃 */
  const ptsStr = (pts: Pt[]) => pts
    .filter(pt => Array.isArray(pt) && pt.length === 2)
    .map(pt => `${pt[0]},${pt[1]}`)
    .join(' ')

  return (
    <>
      <style>{`
        @keyframes ch00Glow { 0%,100% { opacity: 0.15 } 50% { opacity: 0.45 } }
        .ch00-glow { animation: ch00Glow 1.6s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) { .ch00-glow { animation: none; opacity: 0.25; } }
      `}</style>

      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      {/* 标题与副题（静态信息，始终可见） */}
      <g>
        <text x="480" y="28" textAnchor="middle" fill="#111827" fontSize={20} fontWeight={700} fontFamily={FONT}>
          课程依赖地图
        </text>
        <text x="480" y="47" textAnchor="middle" fill="#9ca3af" fontSize={12} fontFamily={FONT}>
          9 个阶段 · 主线先行 · 分支并行
        </text>
      </g>

      {/* 分支依赖边（弱化，后于主线出现） */}
      {BRANCH_EDGES.map((e, i) => {
        const o = fade(e.t) * (e.dashed ? 0.75 : 0.55)
        if (o <= 0.01) return null
        const color = e.dashed ? '#94a3b8' : STAGE_COLORS[e.from]
        const tip = e.pts[e.pts.length - 1]
        return (
          <g key={`b${i}`} opacity={o}>
            <polyline points={ptsStr(e.pts)} fill="none" stroke={color} strokeWidth={1.5}
              strokeDasharray={e.dashed ? '5,4' : undefined} />
            {tip && Array.isArray(tip) && (
              <ArrowHead x={tip[0]} y={tip[1]} angle={endAngle(e.pts)} size={6} color={color} />
            )}
          </g>
        )
      })}

      {/* 主线边：按段描画 */}
      {MAIN_EDGES.map((e, i) => {
        const visible = reveals[i] > 0.01
        if (!visible) return null
        return (
          <polyline key={`m${i}`} points={ptsStr(e.pts)} fill="none" stroke="#3b82f6" strokeWidth={2.5}
            pathLength={1} strokeDasharray="1" strokeDashoffset={1 - reveals[i]} strokeLinecap="round" />
        )
      })}
      {/* 主线箭头（描画完成后出现） */}
      {MAIN_EDGES.map((e, i) => {
        const tip = e.pts[e.pts.length - 1]
        return reveals[i] >= 1 && tip && Array.isArray(tip) && (
          <ArrowHead key={`ma${i}`} x={tip[0]} y={tip[1]} angle={endAngle(e.pts)} size={7} color="#3b82f6" />
        )
      })}

      {/* 节点：主线节点实心弹性弹出，分支节点浅色，H 选修描边 */}
      {STAGES.map(s => {
        const isH = s.id === 'H'
        const t0 = s.branch ? BRANCH_NODE_T[s.id] : MAIN_NODE_T[s.id]
        const o = fade(t0)
        if (o <= 0.01) return null
        const pop = 0.55 + 0.45 * easeOutBack(clamp01((p - t0) / 0.07))
        const cx = s.x + NODE_W / 2
        const cy = s.y + NODE_H / 2
        const color = STAGE_COLORS[s.id]
        const highlight = highlightId === s.id
        return (
          <g key={s.id} opacity={o} transform={`translate(${cx} ${cy}) scale(${pop}) translate(${-cx} ${-cy})`}>
            {/* 当前阶段光晕 */}
            {highlight && (
              <rect className="ch00-glow" x={s.x - 9} y={s.y - 9} width={NODE_W + 18} height={NODE_H + 18}
                rx={12} fill={color} />
            )}
            {isH ? (
              /* 选修节点：描边 + 浅填充 */
              <rect x={s.x} y={s.y} width={NODE_W} height={NODE_H} rx={10} fill="#ef4444" fillOpacity={0.12}
                stroke="#ef4444" strokeWidth={1.5} strokeDasharray="5,4" />
            ) : s.branch ? (
              <rect x={s.x} y={s.y} width={NODE_W} height={NODE_H} rx={10} fill={color} fillOpacity={0.16}
                stroke={color} strokeWidth={1.5} />
            ) : (
              <rect x={s.x} y={s.y} width={NODE_W} height={NODE_H} rx={10} fill={color}
                stroke={highlight ? '#ffffff' : 'none'} strokeWidth={2.5} />
            )}
            {/* 编号徽章 */}
            <circle cx={s.x + 24} cy={cy} r={13} fill={isH || s.branch ? color : '#ffffff'} fillOpacity={isH || s.branch ? 1 : 0.25} />
            <text x={s.x + 24} y={cy + 1} textAnchor="middle" dominantBaseline="central"
              fill="#fff" fontSize={12} fontWeight={700} fontFamily={FONT}>
              {s.label}
            </text>
            {/* 标题 */}
            <text x={s.x + 44} y={cy + 1} dominantBaseline="central" fill={isH || s.branch ? color : '#fff'}
              fontSize={13} fontWeight={600} fontFamily={FONT}>
              {s.title}
            </text>
          </g>
        )
      })}

      {/* 学习路径光点（沿主线行走，节点内减速） */}
      {spot && (
        <g opacity={spotDim}>
          <circle cx={spot[0]} cy={spot[1]} r={8} fill="#f59e0b" opacity={0.35} className="ch00-glow" />
          <circle cx={spot[0]} cy={spot[1]} r={4.5} fill="#f59e0b" stroke="#fff" strokeWidth={1.5} />
        </g>
      )}

      {/* 图例（静态信息） */}
      <g>
        <text x="30" y="512" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          主线箭头 = 建议学习路径 · 分支 = 先修依赖 · 虚线 = 可选
        </text>
        <text x="30" y="528" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          点击播放：光点沿主线推进，带你走完课程主线
        </text>
      </g>
    </>
  )
}
