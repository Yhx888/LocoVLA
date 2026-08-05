import { useEffect } from 'react'
import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { ArrowHead, RoundedRect } from '../primitives/DrawingPrimitives'

const FONT = 'system-ui, "Noto Sans SC", sans-serif'

const SLIDERS = [
  { key: 'gain', label: '增益 K', min: 0, max: 5, step: 0.1 },
  { key: 'speed', label: '信号速度', min: 0.2, max: 3, step: 0.1 },
]
const DEFAULTS = { gain: 1, speed: 1 }

/* ------------------------------------------------------------------ */
/*  框图布局与正交折线路径                                              */
/* ------------------------------------------------------------------ */

interface BlockDef { id: string; label: string; x: number; y: number; w: number; h: number; color: string }

const BLOCKS: BlockDef[] = [
  { id: 'ref',    label: '参考输入\nr(t)',     x: 60,   y: 230, w: 110, h: 50, color: '#6366f1' },
  { id: 'error',  label: '误差\ne(t)',          x: 210,  y: 230, w: 90,  h: 50, color: '#8b5cf6' },
  { id: 'ctrl',   label: '控制器',              x: 340,  y: 220, w: 100, h: 70, color: '#3b82f6' },
  { id: 'act',    label: '执行器',              x: 480,  y: 220, w: 100, h: 70, color: '#0ea5e9' },
  { id: 'plant',  label: '被控对象\nP(s)',       x: 620,  y: 220, w: 100, h: 70, color: '#22c55e' },
  { id: 'out',    label: '输出\ny(t)',          x: 770,  y: 230, w: 90,  h: 50, color: '#eab308' },
  { id: 'sensor', label: '传感器',              x: 480,  y: 400, w: 100, h: 50, color: '#f97316' },
]

type Pt = [number, number]

/* 每段信号路径：正交折线（避免斜穿框图） */
interface EdgeDef { id: string; pts: Pt[]; color: string; feedback?: boolean }

const EDGES: EdgeDef[] = [
  { id: 'ref-error',  pts: [[170, 255], [210, 255]], color: '#6366f1' },
  { id: 'error-ctrl', pts: [[300, 255], [340, 255]], color: '#8b5cf6' },
  { id: 'ctrl-act',   pts: [[440, 255], [480, 255]], color: '#3b82f6' },
  { id: 'act-plant',  pts: [[580, 255], [620, 255]], color: '#0ea5e9' },
  { id: 'plant-out',  pts: [[720, 255], [770, 255]], color: '#22c55e' },
  { id: 'out-sensor', pts: [[815, 280], [815, 460], [530, 460], [530, 400]], color: '#f59e0b', feedback: true },
  { id: 'sensor-error', pts: [[530, 400], [530, 320], [255, 320], [255, 280]], color: '#f97316', feedback: true },
]

const FWD = EDGES.slice(0, 5)      // 前向通路（开环）
const FB = EDGES.slice(5)          // 反馈通路
const RING = EDGES                 // 闭环环路径（首尾相接）

/* ------------------------------------------------------------------ */
/*  工具：折线几何                                                      */
/* ------------------------------------------------------------------ */

const clamp01 = (t: number) => Math.max(0, Math.min(1, t))
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

function polylineLen(pts: Pt[]) {
  let len = 0
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
  return len
}

function pointAlong(pts: Pt[], s: number): Pt {
  const total = polylineLen(pts)
  const d = clamp01(s) * total
  let acc = 0
  for (let i = 1; i < pts.length; i++) {
    const segLen = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    if (acc + segLen >= d) {
      const t = segLen > 0 ? (d - acc) / segLen : 0
      return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t]
    }
    acc += segLen
  }
  return pts[pts.length - 1]
}

function endAngle(pts: Pt[]) {
  const a = pts[pts.length - 2]
  const b = pts[pts.length - 1]
  return Math.atan2(b[1] - a[1], b[0] - a[0])
}

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

export default function Chapter12Animation() {
  return (
    <AnimationCanvas controls duration={9000} sliders={SLIDERS}>
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
  const fade = (t0: number) => clamp01((p - t0) / 0.05)
  const speed = params.speed ?? DEFAULTS.speed
  const gain = params.gain ?? DEFAULTS.gain

  /* 阶段 A：前向通路依次点亮（开环） */
  const FWD_T0 = [0.05, 0.10, 0.15, 0.20, 0.25]
  /* 阶段 B：反馈通路点亮 + 单脉冲绕环 */
  const FB_T0 = [0.32, 0.36]
  /* 阶段 C：稳态循环 */
  const pC = clamp01((p - 0.62) / 0.38)

  /* 段内信号点相位：阶段 A/B 沿段推进，阶段 C 循环 */
  const dotPhase = (i: number) => {
    const edge = EDGES[i]
    if (edge.feedback) {
      if (p >= 0.62) return (pC * speed * 1.6 + i * 0.13) % 1
      const idx = edge.id === 'out-sensor' ? 0 : 1
      const t0 = FB_T0[idx] + 0.02
      if (p < t0) return null
      return easeInOut(clamp01((p - t0) / 0.12))
    }
    if (p < 0.62) return p < FWD_T0[i] + 0.02 ? null : easeInOut(clamp01((p - FWD_T0[i] - 0.02) / 0.05))
    return (pC * speed * 1.6 + i * 0.13) % 1
  }

  /* 单脉冲绕环（阶段 B）：一个参考输入走完整个闭环 */
  const ringPts = RING.flatMap(e => e.pts)
  const pulseS = p >= 0.38 && p < 0.62 ? easeInOut(clamp01((p - 0.38) / 0.22)) : null

  /* 增益可视化：稳态误差 e ≈ 1/(1+K)，y ≈ K/(1+K) */
  const eSteady = 1 / (1 + gain)
  const ySteady = 1 - eSteady
  /* 控制信号强度：前向信号点随增益放大 */
  const signalBoost = 1 + 1.2 * Math.min(gain, 5) / 5
  const ctrlScale = 1 + 0.05 * Math.min(gain, 5) / 5

  const ptsStr = (pts: Pt[]) => pts.map(pt => pt.join(',')).join(' ')

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      {/* 标题与副题（静态） */}
      <text x="480" y="30" textAnchor="middle" fill="#111827" fontSize={20} fontWeight={700} fontFamily={FONT}>
        反馈控制闭环框图
      </text>
      <text x="480" y="50" textAnchor="middle" fill="#9ca3af" fontSize={12} fontFamily={FONT}>
        前向通路开环驱动 · 反馈通路闭环修正
      </text>

      {/* 增益实时显示 */}
      <text x="680" y="40" fill="#6b7280" fontSize={12} fontFamily="monospace">
        增益 K = {gain.toFixed(2)} · 稳态误差 e ≈ {eSteady.toFixed(2)}
      </text>

      {/* 信号路径：前向/反馈按时间线描画 */}
      {EDGES.map((e, i) => {
        const lit = e.feedback
          ? p > FB_T0[e.id === 'out-sensor' ? 0 : 1]
          : p > FWD_T0[i] + 0.005
        if (!lit) return null
        const reveal = e.feedback
          ? easeInOut(clamp01((p - FB_T0[e.id === 'out-sensor' ? 0 : 1]) / 0.05))
          : easeInOut(clamp01((p - FWD_T0[i]) / 0.06))
        return (
          <g key={e.id}>
            <polyline points={ptsStr(e.pts)} fill="none" stroke={e.color} strokeWidth={e.feedback ? 2 : 2.5}
              pathLength={1} strokeDasharray="1" strokeDashoffset={1 - reveal} strokeLinecap="round"
              opacity={e.feedback ? 0.85 : 1} />
            <ArrowHead x={e.pts[e.pts.length - 1][0]} y={e.pts[e.pts.length - 1][1]}
              angle={endAngle(e.pts)} size={7} color={e.color} />
          </g>
        )
      })}

      {/* 信号点：实心 + 白描边 + 尾迹（相位差递减的小圆） */}
      {EDGES.map((e, i) => {
        const ph = dotPhase(i)
        if (ph === null) return null
        const r = e.feedback ? 4.5 : 4.5 * signalBoost
        return (
          <g key={`dot${i}`}>
            {[0.05, 0.1].map((off, j) => {
              const trail = pointAlong(e.pts, (ph - off + 1) % 1)
              return (
                <circle key={j} cx={trail[0]} cy={trail[1]} r={r * (1 - j * 0.4)}
                  fill={e.color} opacity={0.28 - j * 0.12} />
              )
            })}
            <circle cx={pointAlong(e.pts, ph)[0]} cy={pointAlong(e.pts, ph)[1]} r={r}
              fill={e.color} stroke="#fff" strokeWidth={1.5} />
          </g>
        )
      })}

      {/* 单脉冲绕环：一个脉冲走完闭环（阶段 B） */}
      {pulseS !== null && (
        <g>
          {[0.05, 0.1].map((off, j) => {
            const tr = pointAlong(ringPts, pulseS - off)
            return (
              <circle key={j} cx={tr[0]} cy={tr[1]} r={4.5 * (1 - j * 0.4)}
                fill="#f59e0b" opacity={0.35 - j * 0.15} />
            )
          })}
          <circle cx={pointAlong(ringPts, pulseS)[0]} cy={pointAlong(ringPts, pulseS)[1]} r={5.5}
            fill="#f59e0b" stroke="#fff" strokeWidth={1.5}>
            <animate attributeName="r" values="5.5;7;5.5" dur="0.6s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* 框图（错峰淡入） */}
      {BLOCKS.map((b, bi) => (
        <g key={b.id} opacity={fade(0.03 + bi * 0.006)}>
          <RoundedRect x={b.x} y={b.y} width={b.w} height={b.h} fill={b.color} rx={6} />
          {b.label.split('\n').map((line, li) => (
            <text key={li}
              x={b.x + b.w / 2} y={b.y + b.h / 2 + (li - (b.label.split('\n').length - 1) / 2) * 16}
              textAnchor="middle" dominantBaseline="central"
              fill="#fff" fontSize={13} fontWeight={600} fontFamily={FONT}>
              {line}
            </text>
          ))}
          {/* 控制器 ×K：增益直接作用于控制量 */}
          {b.id === 'ctrl' && (
            <g transform={`translate(${b.x + b.w / 2} ${b.y + b.h / 2}) scale(${ctrlScale}) translate(${-(b.x + b.w / 2)} ${-(b.y + b.h / 2)})`}>
              <text x={b.x + b.w / 2} y={b.y + b.h - 10} textAnchor="middle" fill="#fff" fontSize={12} fontWeight={700} fontFamily="monospace">
                ×{gain.toFixed(1)}
              </text>
            </g>
          )}
          {/* 误差/输出节点说明（阶段 C 显示稳态值） */}
          {b.id === 'error' && pC > 0 && (
            <text x={b.x + b.w / 2} y={b.y - 12} textAnchor="middle" fill="#ef4444" fontSize={12} fontFamily="monospace">
              e ≈ {eSteady.toFixed(2)}
            </text>
          )}
          {b.id === 'out' && pC > 0 && (
            <text x={b.x + b.w + 14} y={b.y + b.h / 2} dominantBaseline="central" fill="#16a34a" fontSize={12} fontFamily="monospace">
              y ≈ {ySteady.toFixed(2)}
            </text>
          )}
        </g>
      ))}

      {/* 求和符号：r 从左侧进入（+），反馈从下方进入（−） */}
      <g opacity={fade(0.06)}>
        <text x="210" y="240" textAnchor="middle" fill="#8b5cf6" fontSize={13} fontWeight={700} fontFamily={FONT}>+</text>
        <text x="267" y="293" fill="#f97316" fontSize={13} fontWeight={700} fontFamily={FONT}>−</text>
      </g>

      {/* 底部提示 */}
      <g opacity={fade(0.66)}>
        <text x="480" y="512" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          彩色圆点 = 信号传播 · 增益 K 越大稳态误差越小 · 速度滑块调节信号流速
        </text>
      </g>
    </>
  )
}
