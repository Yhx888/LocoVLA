/**
 * 统一可配置动画渲染器 — 根据 ChapterAnimationConfig 驱动 SVG 场景。
 * 覆盖 flowchart / controlLoop / signalPlot / stateFlow / architecture / dataPipeline / formulaExplorer / robotView。
 *
 * 性能约定：章节树里 136 条动画可能同时渲染，每帧只允许轻量属性变化
 * （transform / opacity / 少量点坐标）；曲线路径、静态几何一律 useMemo 缓存，
 * 不在渲染函数内循环拼接大数组。
 */

import { useMemo } from 'react'
import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import type { AnimationItem, ChapterAnimationConfig } from './ChapterAnimationConfigs'

interface Props {
  config: ChapterAnimationConfig
}

export default function ConfigurableAnimation({ config }: Props) {
  return (
    <AnimationCanvas controls duration={8000} sliders={config.sliders}>
      <SceneRenderer config={config} />
    </AnimationCanvas>
  )
}

/* ------------------------------------------------------------------ */
/*  场景分发                                                           */
/* ------------------------------------------------------------------ */

function SceneRenderer({ config }: { config: ChapterAnimationConfig }) {
  switch (config.scene) {
    case 'flowchart': return <FlowGraphScene config={config} kind="flowchart" />
    case 'stateFlow': return <FlowGraphScene config={config} kind="stateFlow" />
    case 'dataPipeline': return <FlowGraphScene config={config} kind="pipeline" />
    case 'controlLoop': return <ControlLoopScene config={config} />
    case 'signalPlot': return <SignalPlotScene config={config} />
    case 'architecture': return <ArchitectureScene config={config} />
    case 'formulaExplorer': return <FormulaExplorerScene config={config} />
    case 'robotView': return <RobotViewScene config={config} />
    default: return <DefaultScene config={config} />
  }
}

/* ------------------------------------------------------------------ */
/*  通用工具与常量                                                     */
/* ------------------------------------------------------------------ */

const TEXT = { fontFamily: 'system-ui, "Noto Sans SC", sans-serif' }
const COLOR = {
  blue: '#3b82f6', green: '#10b981', red: '#ef4444', amber: '#f59e0b',
  purple: '#8b5cf6', cyan: '#06b6d4', gray: '#6b7280', faint: '#9ca3af',
  line: '#d1d5db',
}

const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v)
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
const frac = (v: number) => ((v % 1) + 1) % 1
/** 长标签截断，避免溢出节点框 */
const compact = (s: string, max = 14) => (s.length > max ? `${s.slice(0, max - 1)}…` : s)

/** 第一个 slider 的当前值 → [0,1]；无 slider 时返回 0.5 */
function param01(config: ChapterAnimationConfig, params: Record<string, number>): number {
  const s = config.sliders[0]
  if (!s) return 0.5
  const v = params[s.key] ?? s.min
  return clamp01((v - s.min) / Math.max(s.max - s.min, 1e-9))
}

/** 指定 key 的 slider 归一化值 */
function slider01(config: ChapterAnimationConfig, params: Record<string, number>, key: string): number {
  const s = config.sliders.find((x) => x.key === key)
  if (!s) return 0.5
  const v = params[key] ?? s.min
  return clamp01((v - s.min) / Math.max(s.max - s.min, 1e-9))
}

/* 折线路径定位：光点 / 数据包沿路径流动 */
interface PathSeg { x1: number; y1: number; x2: number; y2: number; len: number; start: number }
interface FlowPath { segs: PathSeg[]; total: number }

function buildFlowPath(pts: Array<[number, number]>): FlowPath {
  const segs: PathSeg[] = []
  let total = 0
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0]
    const dy = pts[i][1] - pts[i - 1][1]
    const len = Math.hypot(dx, dy)
    segs.push({ x1: pts[i - 1][0], y1: pts[i - 1][1], x2: pts[i][0], y2: pts[i][1], len, start: total })
    total += len
  }
  return { segs, total }
}

function pointAt(path: FlowPath, d: number): { x: number; y: number } {
  const dist = frac(d / path.total) * path.total
  for (const s of path.segs) {
    if (dist <= s.start + s.len) {
      const t = s.len === 0 ? 0 : (dist - s.start) / s.len
      return { x: s.x1 + (s.x2 - s.x1) * t, y: s.y1 + (s.y2 - s.y1) * t }
    }
  }
  const last = path.segs[path.segs.length - 1]
  return { x: last.x2, y: last.y2 }
}

/** 周期脉冲：delay 后到达、宽度 width 的激活窗口（到达后衰减） */
function pulseAt(timeMs: number, delayMs: number, periodMs: number, widthMs = 440): number {
  const d = ((timeMs - delayMs) % periodMs + periodMs) % periodMs
  const half = widthMs / 2
  if (d < half) return 1 - d / half
  if (d > periodMs - half) return (d - (periodMs - half)) / half
  return 0
}

function TitleArea({ config, y = 40 }: { config: ChapterAnimationConfig; y?: number }) {
  return (
    <g>
      <text x={480} y={y} textAnchor="middle" fill="#111827" fontSize={22} fontWeight={600} {...TEXT}>
        {config.title}
      </text>
      {config.subtitle && (
        <text x={480} y={y + 26} textAnchor="middle" fill={COLOR.gray} fontSize={13} {...TEXT}>
          {config.subtitle}
        </text>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  图场景：flowchart / stateFlow / dataPipeline                        */
/*  动效：主链光点逐跳传播（节点按到达顺序点亮：未到/当前/已过），      */
/*  分支箭头独立流动；pipeline 用批量数据方块表达数据流。               */
/* ------------------------------------------------------------------ */

const GRAPH_STEP = 700      // 主链每跳耗时 ms
const BRANCH_PERIOD = 2600  // 分支箭头循环周期 ms

interface NodeGeom { id?: string; x: number; y: number; w: number; h: number; color: string; label: string }
interface ArrowGeom { from: string; to: string; color: string; dashed?: boolean }

function collectNodes(config: ChapterAnimationConfig, kind: 'stage' | 'node'): NodeGeom[] {
  return config.items
    .filter((it) => it.type === kind && typeof it.x === 'number' && typeof it.y === 'number')
    .map((it) => ({
      id: it.id, x: it.x as number, y: it.y as number,
      w: it.w ?? 120, h: it.h ?? 40,
      color: it.color ?? COLOR.blue,
      label: it.label ?? '',
    }))
}

function collectArrows(config: ChapterAnimationConfig): ArrowGeom[] {
  return config.items
    .filter((it) => it.type === 'arrow' && it.from && it.to)
    .map((it) => ({ from: it.from as string, to: it.to as string, color: it.color ?? COLOR.blue, dashed: it.dashed }))
}

/** 从节点边到节点边的连线端点（按主方向水平/垂直出边） */
function edgePoints(f: NodeGeom, t: NodeGeom): Array<[number, number]> {
  const fcx = f.x + f.w / 2, fcy = f.y + f.h / 2
  const tcx = t.x + t.w / 2, tcy = t.y + t.h / 2
  const dx = tcx - fcx, dy = tcy - fcy
  if (Math.abs(dx) >= Math.abs(dy)) {
    return [
      [f.x + (dx >= 0 ? f.w : 0), fcy],
      [t.x + (dx >= 0 ? 0 : t.w), tcy],
    ]
  }
  return [
    [fcx, f.y + (dy >= 0 ? f.h : 0)],
    [tcx, t.y + (dy >= 0 ? 0 : t.h)],
  ]
}

/** 找最长有向链（教学主线）；无箭头时按 x 排序自动连线 */
function findMainChain(nodes: NodeGeom[], arrows: ArrowGeom[]): string[] {
  if (arrows.length === 0) {
    return [...nodes].sort((a, b) => a.x - b.x).map((n) => n.id as string).filter(Boolean)
  }
  const out = new Map<string, string[]>()
  const indeg = new Map<string, number>()
  for (const a of arrows) {
    out.set(a.from, [...(out.get(a.from) ?? []), a.to])
    indeg.set(a.to, (indeg.get(a.to) ?? 0) + 1)
  }
  const start = nodes.find((n) => n.id && !indeg.has(n.id))?.id ?? nodes[0]?.id ?? ''
  let best: string[] = []
  const walk = (cur: string, path: string[]) => {
    const nexts = out.get(cur) ?? []
    if (nexts.length === 0) {
      if (path.length > best.length) best = [...path]
      return
    }
    for (const nxt of nexts) walk(nxt, [...path, nxt])
  }
  walk(start, [start])
  return best.length ? best : [start]
}

function FlowGraphScene({ config, kind }: { config: ChapterAnimationConfig; kind: 'flowchart' | 'stateFlow' | 'pipeline' }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const nodeType = kind === 'stateFlow' ? 'node' : 'stage'
  const rx = kind === 'stateFlow' ? 14 : 6

  const nodes = useMemo(() => collectNodes(config, nodeType), [config, nodeType])
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])

  // 箭头（无箭头配置自动补连线）
  const arrows = useMemo(() => {
    const raw = collectArrows(config)
    if (raw.length || nodes.length < 2) return raw
    const sorted = [...nodes].sort((a, b) => a.x - b.x)
    return sorted.slice(0, -1).map((n, i) => ({
      from: n.id as string, to: sorted[i + 1].id as string, color: '#94a3b8', dashed: true,
    }))
  }, [config, nodes])

  const chain = useMemo(() => findMainChain(nodes, arrows), [nodes, arrows])
  const chainIdx = useMemo(() => new Map(chain.map((id, i) => [id, i])), [chain])
  const totalMain = Math.max(chain.length - 1, 1) * GRAPH_STEP
  const cycleT = Math.max(totalMain + 900, 3400)

  // 箭头几何（静态缓存）：kind 为主链序号，-1 为分支
  const links = useMemo(() => {
    const main = new Map<string, number>()
    for (let k = 0; k + 1 < chain.length; k++) main.set(`${chain[k]}→${chain[k + 1]}`, k)
    return arrows.map((a, i) => {
      const f = byId.get(a.from), to = byId.get(a.to)
      if (!f || !to) return null
      return {
        i, from: a.from, to: a.to, color: a.color, dashed: a.dashed,
        kind: main.get(`${a.from}→${a.to}`) ?? -1,
        path: buildFlowPath(edgePoints(f, to)),
      }
    }).filter((x): x is NonNullable<typeof x> => x !== null)
  }, [arrows, chain, byId])

  // 分支到达脉冲（以节点为目标的分支箭头）
  const branchGlow = (nodeId: string) => {
    let act = 0
    for (const l of links) {
      if (l.to === nodeId && l.kind === -1) act = Math.max(act, pulseAt(t, l.i * 380, BRANCH_PERIOD) * 0.8)
    }
    return act
  }

  const isPipeline = kind === 'pipeline'

  return (
    <g>
      <TitleArea config={config} />
      {/* 箭头：静态淡线 + 主链/分支光点 */}
      {links.map((l) => {
        const mainPos = (() => {
          if (l.kind === -1) return -1
          const d = ((t - l.kind * GRAPH_STEP) % cycleT + cycleT) % cycleT
          return d < GRAPH_STEP ? d / GRAPH_STEP : -1
        })()
        const branchPos = l.kind === -1 ? (((t - l.i * 380) % BRANCH_PERIOD) + BRANCH_PERIOD) % BRANCH_PERIOD / BRANCH_PERIOD : -1
        const p = mainPos >= 0 ? pointAt(l.path, mainPos * l.path.total)
          : branchPos >= 0 ? pointAt(l.path, branchPos * l.path.total)
          : null
        const fade = mainPos >= 0
          ? (mainPos < 0.06 ? mainPos / 0.06 : mainPos > 0.94 ? (1 - mainPos) / 0.06 : 1)
          : 0
        const bfade = branchPos >= 0
          ? (branchPos < 0.04 ? branchPos / 0.04 : branchPos > 0.96 ? (1 - branchPos) / 0.04 : 1)
          : 0
        return (
          <g key={`a${l.i}`}>
            <line
              x1={l.path.segs[0].x1} y1={l.path.segs[0].y1}
              x2={l.path.segs[l.path.segs.length - 1].x2} y2={l.path.segs[l.path.segs.length - 1].y2}
              stroke={l.color} strokeWidth={1.5} opacity={(l.kind === -1 ? 0.55 : 0.75) * 0.45}
              strokeDasharray={l.dashed ? '5,4' : undefined}
            />
            {p && (isPipeline
              ? [0, 1, 2].map((j) => {
                  const q = pointAt(l.path, (mainPos * l.path.total - j * 26) % l.path.total)
                  const op = mainPos >= 0 ? (1 - j * 0.28) * fade : 0.3 * bfade
                  return <rect key={j} x={q.x - 3.5} y={q.y - 3.5} width={7} height={7} rx={1.5}
                    fill={l.color} opacity={op} />
                })
              : (
                <g opacity={l.kind === -1 ? 0.65 * bfade : fade}>
                  <circle cx={p.x} cy={p.y} r={l.kind === -1 ? 3.5 : 8} fill={l.color} opacity={l.kind === -1 ? 0.35 : 0.3} />
                  <circle cx={p.x} cy={p.y} r={l.kind === -1 ? 2.4 : 4} fill="#fff" stroke={l.color} strokeWidth={1.6} />
                </g>
              ))}
          </g>
        )
      })}

      {/* 节点：未到 / 当前 / 已过 三态 */}
      {nodes.map((n) => {
        const ci = n.id ? chainIdx.get(n.id) : undefined
        const mainAct = ci !== undefined ? pulseAt(t, ci * GRAPH_STEP, cycleT) : 0
        const act = clamp01(mainAct + (n.id ? branchGlow(n.id) : 0))
        let passed = false
        if (ci !== undefined) {
          const d = ((t - ci * GRAPH_STEP) % cycleT + cycleT) % cycleT
          passed = d >= 500 && d < 1800
        }
        const color = n.color
        const glow = act > 0
        return (
          <g key={n.id ?? `n${n.x}-${n.y}`}>
            {glow && (
              <rect x={n.x - 4} y={n.y - 4} width={n.w + 8} height={n.h + 8} rx={rx + 2}
                fill="none" stroke={color} strokeWidth={2}
                opacity={0.3 + 0.25 * Math.sin(t / 150)} />
            )}
            <rect x={n.x} y={n.y} width={n.w} height={n.h} rx={rx}
              fill={glow ? `${color}38` : passed ? `${color}26` : `${color}0f`}
              stroke={color} strokeWidth={glow ? 2.4 : passed ? 1.8 : 1.4}
            />
            {passed && <rect x={n.x + 4} y={n.y + 6} width={3} height={n.h - 12} rx={1.5} fill={color} opacity={0.8} />}
            <text
              x={n.x + n.w / 2} y={n.y + n.h / 2 + 4}
              textAnchor="middle" fontSize={11} fontWeight={glow ? 600 : 500}
              fill={glow ? color : passed ? color : COLOR.faint} {...TEXT}
            >
              {compact(n.label, Math.max(5, Math.floor(n.w / 11)))}
            </text>
          </g>
        )
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：controlLoop — 闭环信号传播 + PID 数值柱                       */
/*  动效：信号脉冲沿链路错峰传播（能量递减形成衰减节奏），              */
/*  脉冲到达时节点点亮；PID 柱高度 = 各分量对误差信号的实时贡献。       */
/* ------------------------------------------------------------------ */

// 节点配色按功能语义区分：参考输入→绿、控制器→紫、执行器/被控对象→橙、
// 传感器→青、误差求和→蓝；fill/text 为同色系浅底与深色文字，保证对比度。
const LOOP_NODES = [
  { id: 'ref', label: '参考输入', cx: 80, cy: 222, color: '#16a34a', fill: '#dcfce7', text: '#166534' },
  { id: 'err', label: '误差 Σ', cx: 230, cy: 222, color: '#2563eb', fill: '#dbeafe', text: '#1e40af' },
  { id: 'ctrl', label: '控制器', cx: 380, cy: 222, color: '#6366f1', fill: '#e0e7ff', text: '#4338ca' },
  { id: 'act', label: '执行器', cx: 530, cy: 222, color: '#f59e0b', fill: '#fef3c7', text: '#b45309' },
  { id: 'plant', label: '被控对象', cx: 680, cy: 222, color: '#f97316', fill: '#ffedd5', text: '#9a3412' },
  { id: 'sensor', label: '传感器', cx: 680, cy: 352, color: '#06b6d4', fill: '#cffafe', text: '#0e7490' },
]

// 节点到达时刻（信号错峰传播）；反馈链路从底部绕回误差节点
const LOOP_ARRIVAL = [0, 880, 1360, 1840, 2320, 2800]
const LOOP_PERIOD = 3600
const LOOP_FLOW_MS = 880 // 单条链路脉冲流动耗时

// 链路颜色 = 信号语义色：前向按目标环节（绿→紫→橙→橙→青），反馈为红色系
const LOOP_LINKS: Array<{ pts: Array<[number, number]>; delay: number; energy: number; color: string }> = [
  { pts: [[80, 222], [180, 222]], delay: 0, energy: 0.8, color: '#16a34a' },
  { pts: [[230, 222], [330, 222]], delay: 880, energy: 1.0, color: '#6366f1' },
  { pts: [[380, 222], [480, 222]], delay: 1360, energy: 0.88, color: '#f59e0b' },
  { pts: [[530, 222], [630, 222]], delay: 1840, energy: 0.7, color: '#f97316' },
  { pts: [[680, 244], [680, 330]], delay: 2320, energy: 0.55, color: '#06b6d4' },
  { pts: [[680, 352], [680, 435], [230, 435], [230, 244]], delay: 2800, energy: 0.4, color: '#dc2626' },
]

function ControlLoopScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const boost = 0.45 + param01(config, ctrl.params) * 0.75 // 增益 → 脉冲强度

  const linkPaths = useMemo(() => LOOP_LINKS.map((l) => ({ ...l, path: buildFlowPath(l.pts) })), [])
  const pidItems = config.items.filter((it) => it.type === 'pidBar')

  // 误差信号（慢振荡）与 P/I/D 分量：柱高 = 分量对当前误差的实时贡献
  const wErr = (2 * Math.PI) / 2600
  const errSig = Math.sin(wErr * t)
  const pidVals = pidItems.map((it) => {
    const key = it.label === 'P' ? 'Kp' : it.label === 'I' ? 'Ki' : 'Kd'
    const maxK = config.sliders.find((s) => s.key === key)?.max ?? 10
    const K = ctrl.params[key] ?? 0
    const sig = it.label === 'P' ? errSig : it.label === 'I' ? -Math.cos(wErr * t) : Math.cos(wErr * t)
    return { item: it, value: K * sig, h: clamp01(Math.abs(K * sig) / maxK) }
  })

  const slider = config.sliders[0]

  return (
    <g>
      <TitleArea config={config} />
      {/* 节点：脉冲到达时点亮 */}
      {LOOP_NODES.map((n, i) => {
        const glow = pulseAt(t, LOOP_ARRIVAL[i], LOOP_PERIOD)
        return (
          <g key={n.id}>
            {glow > 0 && (
              <rect x={n.cx - 56} y={n.cy - 26} width={112} height={52} rx={11}
                fill="none" stroke={n.color} strokeWidth={2} opacity={glow * 0.55} />
            )}
            <rect x={n.cx - 50} y={n.cy - 20} width={100} height={40} rx={8}
              fill={glow > 0 ? n.fill : '#f8fafc'} stroke={n.color} strokeWidth={1.5} />
            <text x={n.cx} y={n.cy + 5} textAnchor="middle" fill={n.text} fontSize={12} fontWeight={500} {...TEXT}>
              {n.label}
            </text>
          </g>
        )
      })}

      {/* 链路：静态淡线 + 脉冲（含衰减拖尾） */}
      {linkPaths.map((l, i) => {
        const d = ((t - l.delay) % LOOP_PERIOD + LOOP_PERIOD) % LOOP_PERIOD
        const pos = d < LOOP_FLOW_MS ? d / LOOP_FLOW_MS : -1
        const e = l.energy * boost
        return (
          <g key={`l${i}`}>
            <polyline points={l.pts.map((p) => p.join(',')).join(' ')}
              fill="none" stroke={l.color} strokeWidth={1.8}
              opacity={i === 5 ? 0.2 : 0.3} strokeDasharray={i === 5 ? '3,4' : undefined}
            />
            {pos >= 0 && (
              <g>
                {[0.12, 0.06].map((back, j) => {
                  const q = pointAt(l.path, (pos - back) * l.path.total)
                  return <circle key={j} cx={q.x} cy={q.y} r={3.5 + 3 * e * (1 - j * 0.35)}
                    fill={l.color} opacity={0.3 * (1 - j * 0.5)} />
                })}
                <circle cx={pointAt(l.path, pos * l.path.total).x} cy={pointAt(l.path, pos * l.path.total).y}
                  r={3 + 4.4 * e} fill="#fff" stroke={l.color} strokeWidth={2}
                  opacity={0.45 + 0.55 * clamp01(e)} />
              </g>
            )}
          </g>
        )
      })}

      {/* 反馈标签 */}
      <text x={452} y={428} textAnchor="middle" fill={COLOR.faint} fontSize={10} {...TEXT}>反馈</text>

      {/* PID 数值柱（可配置） */}
      {pidVals.length > 0 && (
        <g>
          <line x1={300} y1={412} x2={500} y2={412} stroke="#e5e7eb" strokeWidth={1} />
          {pidVals.map(({ item, value, h }, i) => {
            const x = 320 + i * 64
            const color = (item.color as string) || COLOR.blue
            const barH = 8 + h * 104
            return (
              <g key={`pid${i}`}>
                <rect x={x} y={412 - barH} width={34} height={barH} rx={3}
                  fill={color} opacity={0.75} />
                <text x={x + 17} y={412 - barH - 5} textAnchor="middle" fill={color}
                  fontSize={10} fontWeight={600} {...TEXT}>
                  {value.toFixed(2)}
                </text>
                <text x={x + 17} y={428} textAnchor="middle" fill={COLOR.gray} fontSize={10} {...TEXT}>
                  {item.label as string}
                </text>
              </g>
            )
          })}
        </g>
      )}

      {/* 参数当前值（gain / vx / horizon 等），弱化显示 */}
      {slider && (
        <text x={80} y={270} fill={COLOR.faint} fontSize={10} {...TEXT}>
          {slider.label} = {(ctrl.params[slider.key] ?? slider.min).toFixed(2)}
        </text>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：signalPlot — 曲线滚动 + 探头游标                              */
/*  动效：周期波形无缝滚动（路径静态，仅平移 transform），探头与游标   */
/*  沿曲线同步扫描；带衰减的曲线（极点实部）切换为绘制生长模式。       */
/* ------------------------------------------------------------------ */

interface CurveStyle { amp: number; freq: number; noise: number; decay: number; phase: number; speed: number }

/** 由 sliders 推导曲线形态（参数变化 → 曲线形状联动） */
function resolveCurve(ci: number, curve: AnimationItem, config: ChapterAnimationConfig, params: Record<string, number>): CurveStyle {
  const base: CurveStyle = {
    amp: 62 - ci * 10,
    freq: 1.2 + ci * 0.5,
    noise: curve.dashed ? 0 : 0.055,
    decay: 0,
    phase: ci * 0.9,
    speed: 78 + ci * 10,
  }
  const s = config.sliders[0]
  if (!s) return base
  const v = params[s.key] ?? s.min
  const n = clamp01((v - s.min) / Math.max(s.max - s.min, 1e-9))
  switch (s.key) {
    case 'amplitude': base.amp = 18 + n * 88; break
    case 'noise': base.noise = n * 0.22; break
    case 'real': {
      base.decay = -n * 2.6
      const imagS = config.sliders.find((x) => x.key === 'imag')
      if (imagS) {
        const iv = params.imag ?? imagS.min
        base.freq = 0.8 + clamp01((iv - imagS.min) / Math.max(imagS.max - imagS.min, 1e-9)) * 3.4
      }
      break
    }
    case 'imag': base.freq = 0.8 + n * 3.4; break
    case 'alpha': base.noise = (1 - n) * 0.07; base.amp = 34 + n * 46; break
    case 'gamma': base.speed = 40 + n * 70; base.amp = 30 + n * 55; break
    case 'r_scale': base.amp = 18 + n * 80; break
    case 'steps': base.speed = 36 + n * 90; base.amp = 24 + n * 60; break
    case 'target_hz': base.speed = 44 + n * 55; break
    default: base.amp = 26 + n * 62; break
  }
  // 滚动模式要求波形周期闭合：主频取 0.5 的倍数，噪声用整数频率
  if (base.decay === 0) {
    base.freq = Math.round(base.freq * 2) / 2
  }
  return base
}

/** 波形值：u ∈ [0,2) 对应两个滚动周期宽；与路径生成共用，保证探头与曲线严格一致 */
function waveValue(u: number, st: CurveStyle): number {
  const main = st.amp * Math.sin(Math.PI * st.freq * u + st.phase)
  const decayF = st.decay !== 0 ? Math.exp(st.decay * (u - 0.9)) : 1
  const nz = st.noise * (Math.sin(Math.PI * 26 * u + st.phase * 3) * 0.55 + Math.sin(Math.PI * 38 * u + st.phase * 5) * 0.45)
  return (main + nz) * decayF
}

const PLOT = { left: 90, right: 870, top: 130, bottom: 440 }
const PLOT_W = 780
const PLOT_H = 310
const MID_Y = 285
const DRAW_MS = 4200 // 生长模式单轮绘制耗时

function SignalPlotScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const curves = config.items.filter((it) => it.type === 'curve')
  const colors = [COLOR.blue, COLOR.red, COLOR.green, COLOR.amber, COLOR.purple]

  // 曲线形态缓存 key：参数变化才重建路径
  const styles = useMemo(
    () => curves.map((c, ci) => ({ c, ci, color: (c.color as string) || colors[ci % colors.length], st: resolveCurve(ci, c, config, ctrl.params) })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [curves, config, JSON.stringify(config.sliders.map((s) => [s.key, ctrl.params[s.key] ?? s.min]))],
  )

  const paths = useMemo(() => {
    return styles.map(({ st }) => {
      const growing = st.decay !== 0
      // 滚动模式：两屏宽周期路径（u∈[0,2)）；生长模式：一屏宽（u∈[0,1)）
      const span = growing ? PLOT_W : PLOT_W * 2
      const baseX = growing ? PLOT.left : 0
      const N = growing ? 72 : 96
      const pts: string[] = []
      let len = 0
      let prev: [number, number] | null = null
      for (let i = 0; i <= N; i++) {
        const u = (i / N) * (growing ? 1 : 2)
        const x = baseX + (i / N) * span
        const y = MID_Y - waveValue(u, st)
        if (prev) len += Math.hypot(x - prev[0], y - prev[1])
        prev = [x, y]
        pts.push(`${x.toFixed(1)},${y.toFixed(1)}`)
      }
      return { d: pts.join(' '), len, st, growing }
    })
  }, [styles])

  return (
    <g>
      <TitleArea config={config} />
      {/* 绘图区与网格 */}
      <rect x={PLOT.left} y={PLOT.top} width={PLOT_W} height={PLOT_H} fill="#fafbfc" stroke="#e5e7eb" strokeWidth={1} />
      {[205, 285, 365].map((y) => (
        <line key={y} x1={PLOT.left} y1={y} x2={PLOT.right} y2={y} stroke="#eef1f5" strokeWidth={1} />
      ))}
      <text x={PLOT.left - 10} y={PLOT.top - 5} textAnchor="end" fill={COLOR.faint} fontSize={11} {...TEXT}>y</text>
      <text x={PLOT.right + 10} y={PLOT.bottom + 5} textAnchor="start" fill={COLOR.faint} fontSize={11} {...TEXT}>t</text>

      {paths.map(({ d, len, st, growing }, ci) => {
        const color = styles[ci].color
        if (growing) {
          // 生长模式：路径静态，绘制前沿 + 预期虚线
          const prog = frac((t - ci * 350) / DRAW_MS)
          const head = prog * len
          const uHead = prog
          const px = PLOT.left + prog * PLOT_W
          const py = MID_Y - waveValue(uHead, st)
          return (
            <g key={ci}>
              <path d={`M${PLOT.left} ${MID_Y} L${d}`} fill="none" stroke={color}
                strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
                strokeDasharray="5,5" opacity={0.14} />
              <path d={`M${PLOT.left} ${MID_Y} L${d}`} fill="none" stroke={color}
                strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
                strokeDasharray={`${head} ${len}`} />
              <line x1={px} y1={PLOT.top + 6} x2={px} y2={PLOT.bottom - 6} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3,4" />
              <circle cx={px} cy={py} r={5} fill={color} stroke="#fff" strokeWidth={2} />
              <text x={px + 8} y={py - 8} fill={color} fontSize={10} {...TEXT}>{waveValue(uHead, st).toFixed(1)}</text>
            </g>
          )
        }
        // 滚动模式：两屏宽路径平移，offset 循环 → 无缝
        const offset = (t * st.speed + ci * (PLOT_W / 3)) % PLOT_W
        const uProbe = (PLOT_W - 10 + offset) / PLOT_W
        const py = MID_Y - waveValue(uProbe, st)
        const px = PLOT.right - 10
        return (
          <g key={ci}>
            <path d={`M0 ${MID_Y} L${d}`} fill="none" stroke={color}
              strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
              transform={`translate(${PLOT.left - offset} 0)`} />
            <line x1={px} y1={PLOT.top + 6} x2={px} y2={PLOT.bottom - 6} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3,4" />
            <circle cx={px} cy={py} r={5} fill={color} stroke="#fff" strokeWidth={2} />
            <text x={px - 8} y={py - 8} textAnchor="end" fill={color} fontSize={10} {...TEXT}>{waveValue(uProbe, st).toFixed(1)}</text>
          </g>
        )
      })}

      {/* 图例（弱化，右下角） */}
      {styles.map(({ color, ci }) => (
        <g key={`lg${ci}`} transform={`translate(750 ${120 + ci * 20})`}>
          <circle cx={0} cy={0} r={3.5} fill={color} opacity={0.85} />
          <text x={10} y={4} fill={COLOR.gray} fontSize={11} {...TEXT}>{compact((curves[ci].label as string) ?? '', 12)}</text>
        </g>
      ))}

      {/* 参数当前值 */}
      {config.sliders[0] && (
        <text x={PLOT.left} y={PLOT.top + 16} fill={COLOR.faint} fontSize={10} {...TEXT}>
          {config.sliders[0].label} = {(ctrl.params[config.sliders[0].key] ?? config.sliders[0].min).toFixed(2)}
        </text>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：architecture — 层级生长叙事                                    */
/*  动效：层级自中心水平生长（逐层错峰），根光点沿中心轴线逐层下探，    */
/*  光点到达处层级点亮；宽度随第一个参数联动。                          */
/* ------------------------------------------------------------------ */

const ARCH_LAYER_H = 52

function ArchitectureScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const layers = useMemo(() => config.items.filter((it) => it.type === 'layer'), [config])
  const n01 = param01(config, ctrl.params)

  // 层级几何（静态缓存）
  const geoms = useMemo(() => {
    return layers.map((l, i) => ({
      y: (l.y as number) ?? 80 + i * 100,
      color: (l.color as string) || COLOR.blue,
      label: (l.label as string) ?? '',
    }))
  }, [layers])

  // 根光点路径：层中心垂直轴线
  const probePath = useMemo(() => {
    const pts = geoms.map((g, i) => [480, g.y + ARCH_LAYER_H / 2] as [number, number])
    return pts.length > 1 ? buildFlowPath(pts) : null
  }, [geoms])

  // 参数联动：层宽与光点速度
  const layerW = 560 + 160 * n01
  const speedPx = 190 * (0.85 + 0.3 * n01)
  const probeD = probePath ? (t * speedPx / 1000) % probePath.total : 0
  const probe = probePath ? pointAt(probePath, probeD) : null

  return (
    <g>
      <TitleArea config={config} />
      {geoms.map((g, i) => {
        const grow = easeOut(clamp01((t - i * 430) / 560))
        const cx = 480
        const cy = g.y + ARCH_LAYER_H / 2
        // 光点接近时层级点亮
        const glow = probe && probePath ? 1 - Math.min(1, Math.abs(probe.y - cy) / 46) : 0
        return (
          <g key={`ly${i}`}>
            {grow > 0 && i < geoms.length - 1 && (
              <line x1={cx} y1={g.y + ARCH_LAYER_H} x2={cx} y2={geoms[i + 1].y}
                stroke="#d7dde6" strokeWidth={1} strokeDasharray="4,5" opacity={0.5} />
            )}
            {glow > 0.05 && (
              <rect x={cx - layerW / 2 - 6} y={g.y - 6} width={layerW + 12} height={ARCH_LAYER_H + 12} rx={14}
                fill="none" stroke={g.color} strokeWidth={1.6} opacity={glow * 0.55} />
            )}
            {/* 层级主体：以中心为原点水平生长，标签不随缩放 */}
            <g transform={`translate(${cx} ${g.y}) scale(${0.02 + 0.98 * grow} 1)`} opacity={grow}>
              <rect x={-layerW / 2} y={0} width={layerW} height={ARCH_LAYER_H} rx={9}
                fill={`${g.color}14`} stroke={g.color} strokeWidth={1.6} />
            </g>
            <g opacity={grow}>
              <rect x={cx - layerW / 2 + 14} y={g.y + 16} width={10} height={10} rx={3} fill={g.color} opacity={0.9} />
              <text x={cx - layerW / 2 + 34} y={g.y + 33} fill="#374151" fontSize={13} fontWeight={500} {...TEXT}>
                {compact(g.label, 22)}
              </text>
              <text x={cx + layerW / 2 - 14} y={g.y + 32} textAnchor="end" fill={COLOR.faint} fontSize={10} {...TEXT}>
                L{i}
              </text>
            </g>
          </g>
        )
      })}
      {/* 根光点 */}
      {probe && (
        <g>
          <circle cx={probe.x} cy={probe.y} r={9} fill="#fff" stroke={COLOR.blue} strokeWidth={1.5} opacity={0.5} />
          <circle cx={probe.x} cy={probe.y} r={4.5} fill={COLOR.blue} />
        </g>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：robotView — 带物理感的腿足摆动                                 */
/*  动效：髋关节受扰后做阻尼振荡（回摆衰减），双腿对称反相；            */
/*  膝点随摆动，关节以圆点 + 标签清晰标注；轮子滚动、摩擦锥联动参数。   */
/*  几何：真实 Upkie 正视图比例（URDF 米制 → scale 480 px/m）           */
/* ------------------------------------------------------------------ */

/* 真实几何（米制，来源：assets/upkie/upkie_description/urdf/upkie.urdf）：
   轮半径 0.05，半轮距 0.30；机身 0.17 × 0.25、中心离地 0.165；
   髋 y=±0.085 离地 0.131；膝 y=±0.197 离地 0.087；把手高 0.035 */
const UPKIE = {
  wheelR: 0.05,
  trackHalf: 0.3,
  bodyW: 0.17,
  bodyH: 0.25,
  bodyCenterZ: 0.165,
  hipY: 0.085,
  hipZ: 0.131,
  kneeY: 0.197,
  kneeZ: 0.087,
  handleH: 0.035,
  handleW: 0.07,
}

/* 米制 → SVG 坐标：scale px/m，groundY 地面线，cx 中心 x */
function upkiePose(scale: number, groundY: number, cx: number) {
  const px = (y: number) => cx + y * scale
  const py = (z: number) => groundY - z * scale
  const bodyTop = py(UPKIE.bodyCenterZ + UPKIE.bodyH / 2)
  return {
    r: UPKIE.wheelR * scale,
    wheelL: { x: px(-UPKIE.trackHalf), y: py(UPKIE.wheelR) },
    wheelR: { x: px(UPKIE.trackHalf), y: py(UPKIE.wheelR) },
    hipL: { x: px(-UPKIE.hipY), y: py(UPKIE.hipZ) },
    hipR: { x: px(UPKIE.hipY), y: py(UPKIE.hipZ) },
    kneeL: { x: px(-UPKIE.kneeY), y: py(UPKIE.kneeZ) },
    kneeR: { x: px(UPKIE.kneeY), y: py(UPKIE.kneeZ) },
    body: { x: px(-UPKIE.bodyW / 2), y: bodyTop, w: UPKIE.bodyW * scale, h: UPKIE.bodyH * scale },
    handle: {
      x: px(-UPKIE.handleW / 2),
      y: bodyTop - UPKIE.handleH * scale,
      w: UPKIE.handleW * scale,
      h: UPKIE.handleH * scale,
    },
  }
}

function RobotViewScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const GROUND = 472
  const pose = upkiePose(480, GROUND, 480)

  // 扰动循环：每 3.2s 施加一次，阻尼振荡 ω≈2π/1.1s，ζ=0.18
  const tau = ((t % 3200) + 3200) % 3200 / 1000
  const w0 = (2 * Math.PI) / 1.1
  const swing = 10 * Math.exp(-0.18 * w0 * tau) * Math.sin(w0 * tau)

  // 参数联动：hip/knee 滑杆直接控制关节角；friction 控制摩擦锥；其余影响轮速
  const hipS = config.sliders.find((s) => s.key.includes('hip'))
  const kneeS = config.sliders.find((s) => s.key.includes('knee'))
  const frictionS = config.sliders.find((s) => s.key.includes('friction'))
  const hipOff = hipS ? (ctrl.params[hipS.key] ?? hipS.min) : 0
  const kneeOff = kneeS ? (ctrl.params[kneeS.key] ?? kneeS.min) : 0
  const staticMode = Boolean(hipS || kneeS)
  const swingAmp = staticMode ? 3.5 : 10
  const hipDeg = hipOff + swingAmp * Math.sin(w0 * tau * 0.6) // 静态模式下仅微摆
  const kneeDeg = kneeOff

  // 腿链几何：大腿绕髋摆动（静息方向斜向外展），膝点随角度移动，轮心固定贴地
  const thighLen = Math.hypot(pose.kneeL.x - pose.hipL.x, pose.kneeL.y - pose.hipL.y)
  const restL = Math.atan2(pose.kneeL.y - pose.hipL.y, pose.kneeL.x - pose.hipL.x)
  const restR = Math.atan2(pose.kneeR.y - pose.hipR.y, pose.kneeR.x - pose.hipR.x)
  const bend = (kneeDeg * Math.PI) / 180 * 0.5
  const kneeL = {
    x: pose.hipL.x + thighLen * Math.cos(restL + (hipDeg * Math.PI) / 180 + bend),
    y: pose.hipL.y + thighLen * Math.sin(restL + (hipDeg * Math.PI) / 180 + bend),
  }
  const kneeR = {
    x: pose.hipR.x + thighLen * Math.cos(restR - (hipDeg * Math.PI) / 180 + bend),
    y: pose.hipR.y + thighLen * Math.sin(restR - (hipDeg * Math.PI) / 180 + bend),
  }

  // 轮子滚动（辐条旋转）
  const nSpeed = param01(config, ctrl.params)
  const rot = (t * 0.0022 * (0.7 + 0.7 * nSpeed)) % 360

  // 摩擦锥（friction 滑杆或默认 μ=0.5）
  const mu = frictionS ? slider01(config, ctrl.params, frictionS.key) : 0.5
  const coneLen = 26 + 30 * mu

  const sensors = config.items.filter((it) => it.type === 'sensor')

  return (
    <g>
      <TitleArea config={config} y={30} />
      {/* 地面与平衡参考线 */}
      <line x1={80} y1={GROUND} x2={880} y2={GROUND} stroke={COLOR.line} strokeWidth={2} />
      <line x1={480} y1={pose.handle.y} x2={480} y2={GROUND - 12} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="5,5" />
      <text x={870} y={GROUND - 8} textAnchor="end" fill={COLOR.faint} fontSize={10} {...TEXT}>地面</text>

      {/* 机身（陶土配色）+ 把手 */}
      <rect x={pose.body.x} y={pose.body.y} width={pose.body.w} height={pose.body.h} rx={10} fill="#f5e6d8" stroke="#c2703d" strokeWidth={2.5} />
      <rect x={pose.handle.x} y={pose.handle.y} width={pose.handle.w} height={pose.handle.h} rx={4} fill="#c2703d" />
      <text x={480} y={pose.body.y + pose.body.h / 2 + 5} textAnchor="middle" fill="#92400e" fontSize={13} fontWeight={600} {...TEXT}>Upkie</text>

      {/* 摩擦锥（接触点） */}
      {[pose.wheelL, pose.wheelR].map((w, i) => (
        <g key={`cone${i}`}>
          <line x1={w.x} y1={GROUND} x2={w.x - coneLen * 0.55} y2={GROUND - coneLen} stroke={COLOR.red} strokeWidth={1.6} opacity={0.25 + 0.55 * mu} />
          <line x1={w.x} y1={GROUND} x2={w.x + coneLen * 0.55} y2={GROUND - coneLen} stroke={COLOR.red} strokeWidth={1.6} opacity={0.25 + 0.55 * mu} />
        </g>
      ))}
      <text x={480} y={GROUND + 33} textAnchor="middle" fill={COLOR.faint} fontSize={10} {...TEXT}>
        {frictionS ? `μ = ${(ctrl.params[frictionS.key] ?? frictionS.min).toFixed(2)}` : '摩擦锥示意'}
      </text>

      {/* 双腿：大腿 / 小腿 / 关节（细杆 + 关节点） */}
      {([
        { hip: pose.hipL, knee: kneeL, wheel: pose.wheelL, tagHip: '左髋', tagKnee: '左膝', tx: -6 },
        { hip: pose.hipR, knee: kneeR, wheel: pose.wheelR, tagHip: '右髋', tagKnee: '右膝', tx: 16 },
      ]).map((leg, i) => (
        <g key={`leg${i}`}>
          <line x1={leg.hip.x} y1={leg.hip.y} x2={leg.knee.x} y2={leg.knee.y}
            stroke="#94a3b8" strokeWidth={5} strokeLinecap="round" />
          <line x1={leg.knee.x} y1={leg.knee.y} x2={leg.wheel.x} y2={leg.wheel.y - pose.r + 1}
            stroke="#94a3b8" strokeWidth={4} strokeLinecap="round" />
          {/* 髋关节 */}
          <circle cx={leg.hip.x} cy={leg.hip.y} r={5.5} fill="#7c2d12" stroke="#fff" strokeWidth={1.5} />
          <text x={leg.hip.x + leg.tx} y={leg.hip.y - 10} fill="#7c2d12" fontSize={9} {...TEXT}>{leg.tagHip}</text>
          {/* 膝关节 */}
          <circle cx={leg.knee.x} cy={leg.knee.y} r={4.2} fill="#7c2d12" stroke="#fff" strokeWidth={1.5} />
          <text x={leg.knee.x + leg.tx - 4} y={leg.knee.y + 16} fill="#7c2d12" fontSize={9} {...TEXT}>{leg.tagKnee}</text>
        </g>
      ))}

      {/* 轮子（黑轮 + 轮毂，含滚动辐条） */}
      {[pose.wheelL, pose.wheelR].map((w, i) => (
        <g key={`wheel${i}`}>
          <circle cx={w.x} cy={w.y} r={pose.r} fill="#1f2937" stroke="#374151" strokeWidth={2} />
          <g transform={`rotate(${rot} ${w.x} ${w.y})`} stroke="#6b7280" strokeWidth={1.5}>
            <line x1={w.x - pose.r * 0.5} y1={w.y} x2={w.x + pose.r * 0.5} y2={w.y} />
            <line x1={w.x} y1={w.y - pose.r * 0.5} x2={w.x} y2={w.y + pose.r * 0.5} />
          </g>
          <circle cx={w.x} cy={w.y} r={3} fill="#9ca3af" />
        </g>
      ))}

      {/* 传感器标注（弱化） */}
      {sensors.map((s, i) => (
        <text key={`se${i}`} x={(s.x as number) || 480} y={(s.y as number) || GROUND + 28}
          textAnchor="start" fill="#6366f1" fontSize={10.5} {...TEXT}>
          {(s.label as string) ?? ''}
        </text>
      ))}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：formulaExplorer — 公式 + 参数联动量规                          */
/*  动效：公式逐条淡入，参数经虚线脉冲流入量规；量规指针随参数转动，    */
/*  无参数时指针做教学摆动。                                            */
/* ------------------------------------------------------------------ */

const GAUGE = { cx: 480, cy: 368, r: 84 }

function FormulaExplorerScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const t = ctrl.time
  const formulas = config.items.filter((it) => it.type === 'formula')
  const notes = config.items.filter((it) => it.type === 'note')
  const slider = config.sliders[0]
  const n = param01(config, ctrl.params)

  // 指针角度：有参数 → 随滑块；无参数 → 教学摆动
  const angleDeg = slider ? -90 + n * 180 : -90 + 26 * Math.sin((2 * Math.PI * t) / 4200)
  const rad = (angleDeg * Math.PI) / 180
  const tipX = GAUGE.cx + Math.sin(rad) * (GAUGE.r - 14)
  const tipY = GAUGE.cy - Math.cos(rad) * (GAUGE.r - 14)

  // 刻度（静态）
  const ticks = useMemo(() => {
    const arr: Array<{ angle: number; major: boolean }> = []
    for (let a = -90; a <= 90; a += 15) arr.push({ angle: a, major: a % 30 === 0 })
    return arr
  }, [])

  // 参数流入脉冲：公式卡片 → 量规
  const pulsePos = pulseAt(t, 0, 1900, 300)
  const lastFormulaY = formulas.length ? ((formulas[formulas.length - 1].y as number) || 140) + 52 : 190

  return (
    <g>
      <TitleArea config={config} />
      {/* 公式卡片：逐条淡入 */}
      {formulas.map((f, i) => {
        const y = (f.y as number) || 140
        const fadeIn = clamp01((t - i * 450) / 420)
        return (
          <g key={`f${i}`} opacity={fadeIn}>
            <rect x={190} y={y} width={580} height={52} rx={8}
              fill="#fafbfc" stroke="#dbe2ea" strokeWidth={1} />
            {slider && <rect x={190} y={y} width={3 + 9 * n} height={52} rx={1.5} fill={COLOR.blue} opacity={0.7} />}
            <text x={480} y={y + 34} textAnchor="middle" fill="#374151" fontSize={15} fontWeight={500}
              fontFamily="'JetBrains Mono', Consolas, monospace">
              {(f.text as string) ?? ''}
            </text>
          </g>
        )
      })}
      {notes.map((nd, i) => (
        <text key={`n${i}`} x={480} y={(nd.y as number) || 200}
          textAnchor="middle" fill={COLOR.gray} fontSize={13} {...TEXT}>
          {(nd.text as string) ?? ''}
        </text>
      ))}

      {/* 参数流入虚线 + 脉冲 */}
      <line x1={480} y1={lastFormulaY} x2={480} y2={GAUGE.cy - GAUGE.r}
        stroke="#cbd5e1" strokeWidth={1} strokeDasharray="4,4" />
      {slider && pulsePos > 0 && (
        <circle cx={480} cy={lastFormulaY + (GAUGE.cy - GAUGE.r - lastFormulaY) * (1 - pulsePos)}
          r={3} fill={COLOR.blue} />
      )}

      {/* 量规 */}
      <path d={`M ${GAUGE.cx - GAUGE.r} ${GAUGE.cy} A ${GAUGE.r} ${GAUGE.r} 0 0 1 ${GAUGE.cx + GAUGE.r} ${GAUGE.cy}`}
        fill="none" stroke="#e5e7eb" strokeWidth={10} strokeLinecap="round" />
      {ticks.map((tk, i) => {
        const a = (tk.angle * Math.PI) / 180
        const r1 = tk.major ? GAUGE.r - 16 : GAUGE.r - 10
        return (
          <line key={i}
            x1={GAUGE.cx + Math.sin(a) * r1} y1={GAUGE.cy - Math.cos(a) * r1}
            x2={GAUGE.cx + Math.sin(a) * (GAUGE.r - 3)} y2={GAUGE.cy - Math.cos(a) * (GAUGE.r - 3)}
            stroke="#b6c2d1" strokeWidth={tk.major ? 2 : 1} />
        )
      })}
      {/* 指针 */}
      <line x1={GAUGE.cx} y1={GAUGE.cy} x2={tipX} y2={tipY} stroke={COLOR.blue} strokeWidth={3.5} strokeLinecap="round" />
      <circle cx={tipX} cy={tipY} r={5} fill={COLOR.blue} stroke="#fff" strokeWidth={1.5} />
      <circle cx={GAUGE.cx} cy={GAUGE.cy} r={7} fill="#fff" stroke={COLOR.blue} strokeWidth={2.5} />

      {/* 量规读数 */}
      <text x={GAUGE.cx} y={GAUGE.cy + 46} textAnchor="middle" fill="#111827" fontSize={17} fontWeight={600} {...TEXT}>
        {slider ? (ctrl.params[slider.key] ?? slider.min).toFixed(2) : '—'}
      </text>
      <text x={GAUGE.cx} y={GAUGE.cy + 66} textAnchor="middle" fill={COLOR.faint} fontSize={11} {...TEXT}>
        {slider ? slider.label : '参数联动示意'}
      </text>
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  场景：default — 占位                                               */
/* ------------------------------------------------------------------ */

function DefaultScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      <text x={480} y={260} textAnchor="middle" fill={COLOR.faint} fontSize={16} {...TEXT}>
        暂无可交互动画
      </text>
    </g>
  )
}


