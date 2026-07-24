/**
 * 统一可配置动画渲染器 — 根据 ChapterAnimationConfig 驱动 SVG 场景。
 * 覆盖 flowchart / controlLoop / signalPlot / stateFlow / architecture / dataPipeline / formulaExplorer / robotView。
 */

import { useAnimation, AnimationCtx, type AnimationControls } from '../primitives/AnimationCanvas'
import AnimationCanvas from '../primitives/AnimationCanvas'
import type { ChapterAnimationConfig } from './ChapterAnimationConfigs'

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
    case 'flowchart': return <FlowchartScene config={config} />
    case 'controlLoop': return <ControlLoopScene config={config} />
    case 'signalPlot': return <SignalPlotScene config={config} />
    case 'stateFlow': return <StateFlowScene config={config} />
    case 'architecture': return <ArchitectureScene config={config} />
    case 'dataPipeline': return <DataPipelineScene config={config} />
    case 'formulaExplorer': return <FormulaExplorerScene config={config} />
    case 'robotView': return <RobotViewScene config={config} />
    default: return <DefaultScene config={config} />
  }
}

/* ------------------------------------------------------------------ */
/*  通用样式常量                                                       */
/* ------------------------------------------------------------------ */

const TEXT_STYLE = { fontFamily: 'system-ui, "Noto Sans SC", sans-serif' }

function TitleArea({ config, y = 40 }: { config: ChapterAnimationConfig; y?: number }) {
  return (
    <g>
      <text x={480} y={y} textAnchor="middle" fill="#111827" fontSize={22} fontWeight={600} {...TEXT_STYLE}>
        {config.title}
      </text>
      {config.subtitle && (
        <text x={480} y={y + 26} textAnchor="middle" fill="#6b7280" fontSize={13} {...TEXT_STYLE}>
          {config.subtitle}
        </text>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: flowchart — 阶段方框 + 箭头                               */
/* ------------------------------------------------------------------ */

function FlowchartScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      {config.items.map((item, i) => {
        if (item.type === 'stage') {
          return (
            <g key={`s${i}`}>
              <rect
                x={(item.x as number)} y={(item.y as number)}
                width={(item.w as number) || 120} height={(item.h as number) || 36}
                rx={6} fill={(item.color as string) || '#3b82f6'} opacity={0.15}
                stroke={(item.color as string) || '#3b82f6'} strokeWidth={1.5}
              />
              <text
                x={(item.x as number) + ((item.w as number) || 120) / 2}
                y={(item.y as number) + ((item.h as number) || 36) / 2 + 5}
                textAnchor="middle" fill={(item.color as string) || '#3b82f6'}
                fontSize={12} fontWeight={500} {...TEXT_STYLE}
              >
                {item.label as string}
              </text>
            </g>
          )
        }
        if (item.type === 'arrow') {
          const fromItem = config.items.find(s => s.id === item.from) as Record<string, number> | undefined
          const toItem = config.items.find(s => s.id === item.to) as Record<string, number> | undefined
          if (!fromItem || !toItem) return null
          const fx = fromItem.x + (fromItem.w || 120) / 2
          const fy = fromItem.y + (fromItem.h || 36)
          const tx = toItem.x + (toItem.w || 120) / 2
          const ty = toItem.y
          const midY = (fy + ty) / 2
          return (
            <g key={`a${i}`}>
              <polyline
                points={`${fx},${fy} ${fx},${midY} ${tx},${midY} ${tx},${ty}`}
                fill="none" stroke={(item.color as string) || '#3b82f6'}
                strokeWidth={1.5} strokeDasharray={item.dashed ? '6,4' : undefined}
              />
              <polygon
                points={`${tx},${ty} ${tx-5},${ty-8} ${tx+5},${ty-8}`}
                fill={(item.color as string) || '#3b82f6'}
              />
            </g>
          )
        }
        return null
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: controlLoop — 反馈控制闭环节点                            */
/* ------------------------------------------------------------------ */

function ControlLoopScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const pulse = Math.sin((ctrl.time / 1000) * Math.PI * 2) * 0.5 + 0.5

  const nodes = [
    { id: 'ref', label: '参考输入', x: 60, y: 220 },
    { id: 'err', label: '误差 Σ', x: 220, y: 220 },
    { id: 'controller', label: '控制器', x: 380, y: 220 },
    { id: 'actuator', label: '执行器', x: 540, y: 220 },
    { id: 'plant', label: '被控对象', x: 700, y: 220 },
    { id: 'sensor', label: '传感器', x: 700, y: 340 },
  ]

  return (
    <g>
      <TitleArea config={config} />
      {nodes.map(n => (
        <g key={n.id}>
          <rect x={n.x - 50} y={n.y - 20} width={100} height={40} rx={8}
            fill="#f0f9ff" stroke="#3b82f6" strokeWidth={1.5} />
          <text x={n.x} y={n.y + 5} textAnchor="middle" fill="#1e40af" fontSize={12} fontWeight={500} {...TEXT_STYLE}>
            {n.label}
          </text>
        </g>
      ))}
      {([
        { from: 'ref', to: 'err', x1: 110, y1: 220, x2: 170, y2: 220 },
        { from: 'err', to: 'controller', x1: 270, y1: 220, x2: 330, y2: 220 },
        { from: 'controller', to: 'actuator', x1: 430, y1: 220, x2: 490, y2: 220 },
        { from: 'actuator', to: 'plant', x1: 590, y1: 220, x2: 650, y2: 220 },
        { from: 'plant', to: 'sensor', x1: 700, y1: 260, x2: 700, y2: 320 },
        { from: 'sensor', to: 'err', x1: 750, y1: 340, x2: 850, y2: 340, corner: true },
      ] as Array<{ from: string; to: string; x1: number; y1: number; x2: number; y2: number; corner?: boolean }>).map((a, i) => {
        if (a.corner) {
          return (
            <polyline key={i}
              points={`${a.x1},${a.y1} ${880},${a.y1} ${880},${a.y2-20} ${270},${a.y2-20} ${270},${a.y2}`}
              fill="none" stroke="#3b82f6" strokeWidth={2} opacity={0.7 + pulse * 0.3}
              markerEnd="url(#arrowBlue)"
            />
          )
        }
        return (
          <g key={i}>
            <line x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2}
              stroke="#3b82f6" strokeWidth={2} opacity={0.7 + pulse * 0.3} />
            <polygon points={`${a.x2},${a.y2} ${a.x2-6},${a.y2-4} ${a.x2-6},${a.y2+4}`} fill="#3b82f6" />
          </g>
        )
      })}
      {config.items.filter(i => i.type === 'pidBar').map((item, i) => (
        <g key={`pid${i}`}>
          <rect x={380 + i * 60} y={280} width={30} height={(item.value as number || 20) * 3}
            fill={(item.color as string) || '#3b82f6'} rx={3} opacity={0.6} />
          <text x={395 + i * 60} y={300 + (item.value as number || 20) * 3 + 14}
            textAnchor="middle" fill="#6b7280" fontSize={10} {...TEXT_STYLE}>
            {item.label as string}
          </text>
        </g>
      ))}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: signalPlot — 信号曲线                                       */
/* ------------------------------------------------------------------ */

function SignalPlotScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()

  const curves = config.items.filter(i => i.type === 'curve')
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']

  const plotLeft = 100; const plotRight = 860; const plotTop = 120; const plotBottom = 460

  return (
    <g>
      <TitleArea config={config} />
      {/* 坐标轴 */}
      <line x1={plotLeft} y1={plotBottom} x2={plotRight} y2={plotBottom} stroke="#d1d5db" strokeWidth={1} />
      <line x1={plotLeft} y1={plotTop} x2={plotLeft} y2={plotBottom} stroke="#d1d5db" strokeWidth={1} />
      <text x={plotLeft - 10} y={plotTop - 5} textAnchor="end" fill="#9ca3af" fontSize={11} {...TEXT_STYLE}>y</text>
      <text x={plotRight + 10} y={plotBottom + 5} textAnchor="start" fill="#9ca3af" fontSize={11} {...TEXT_STYLE}>t</text>

      {/* 各条曲线 */}
      {curves.map((curve, ci) => {
        const points: string[] = []
        const plotW = plotRight - plotLeft
        const plotH = plotBottom - plotTop
        const midY = plotTop + plotH / 2
        const color = (curve.color as string) || colors[ci % colors.length]
        const dashed = curve.dashed ? '6,4' : undefined

        for (let i = 0; i <= 80; i++) {
          const t = i / 80
          const x = plotLeft + t * plotW
          const phase = (ci + 1) * 1.5
          const noise = Math.sin(t * 10 + ci) * 0.05
          const y = midY - Math.sin(t * phase * Math.PI + ctrl.time / 3000) * (plotH * 0.35) * (0.5 + noise)
          points.push(`${x.toFixed(1)},${y.toFixed(1)}`)
        }

        return (
          <g key={ci}>
            <polyline points={points.join(' ')} fill="none" stroke={color}
              strokeWidth={2.5} strokeDasharray={dashed} strokeLinecap="round" />
            <text x={plotRight + 10} y={plotTop + 30 + ci * 22}
              fill={color} fontSize={12} fontWeight={500} {...TEXT_STYLE}>
              {curve.label as string}
            </text>
            <circle cx={plotRight + 4} cy={plotTop + 25 + ci * 22} r={4} fill={color} opacity={0.8} />
          </g>
        )
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: stateFlow — 状态机节点                                      */
/* ------------------------------------------------------------------ */

function StateFlowScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      {config.items.map((item, i) => {
        if (item.type === 'node') {
          return (
            <g key={`n${i}`}>
              <rect x={(item.x as number)} y={(item.y as number)}
                width={(item.w as number) || 100} height={(item.h as number) || 36}
                rx={6} fill={(item.color as string || '#3b82f6') + '20'}
                stroke={(item.color as string) || '#3b82f6'} strokeWidth={1.5}
              />
              <text
                x={(item.x as number) + ((item.w as number) || 100) / 2}
                y={(item.y as number) + ((item.h as number) || 36) / 2 + 5}
                textAnchor="middle" fill={(item.color as string) || '#3b82f6'}
                fontSize={12} fontWeight={500} {...TEXT_STYLE}
              >
                {item.label as string}
              </text>
            </g>
          )
        }
        if (item.type === 'arrow') {
          const fromNode = config.items.find(s => s.id === item.from) as Record<string, number> | undefined
          const toNode = config.items.find(s => s.id === item.to) as Record<string, number> | undefined
          if (!fromNode || !toNode) return null
          const fx = fromNode.x + (fromNode.w || 100) / 2
          const fy = fromNode.y + (fromNode.h || 36) / 2
          const tx = toNode.x + (toNode.w || 100) / 2
          const ty = toNode.y + (toNode.h || 36) / 2
          const dx = tx - fx; const dy = ty - fy
          const len = Math.sqrt(dx * dx + dy * dy)
          const ux = dx / len; const uy = dy / len
          const arrowStartX = fx + ux * ((fromNode.w || 100) / 2 + 4)
          const arrowStartY = fy + uy * ((fromNode.h || 36) / 2 + 4)
          const arrowEndX = tx - ux * ((toNode.w || 100) / 2 + 4)
          const arrowEndY = ty - uy * ((toNode.h || 36) / 2 + 4)
          return (
            <g key={`a${i}`}>
              <line x1={arrowStartX} y1={arrowStartY} x2={arrowEndX} y2={arrowEndY}
                stroke={(item.color as string) || '#3b82f6'} strokeWidth={1.5}
                strokeDasharray={item.dashed ? '6,4' : undefined}
              />
              <polygon
                points={`${arrowEndX},${arrowEndY} ${arrowEndX-ux*8+uy*4},${arrowEndY-uy*8-ux*4} ${arrowEndX-ux*8-uy*4},${arrowEndY-uy*8+ux*4}`}
                fill={(item.color as string) || '#3b82f6'}
              />
            </g>
          )
        }
        return null
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: architecture — 分层架构建图                                  */
/* ------------------------------------------------------------------ */

function ArchitectureScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const layers = config.items.filter(i => i.type === 'layer')
  return (
    <g>
      <TitleArea config={config} />
      {layers.map((layer, i) => {
        const y = layer.y as number
        const progress = Math.min(1, Math.max(0, (ctrl.time / 1000 - i * 0.3) / 0.6))
        const w = 780 * progress
        return (
          <g key={i}>
            <rect x={90} y={y} width={w} height={60} rx={8}
              fill={(layer.color as string || '#3b82f6') + '15'}
              stroke={(layer.color as string) || '#3b82f6'} strokeWidth={1.5} opacity={Math.min(1, progress * 2)}
            />
            <text x={110} y={y + 38} fill={(layer.color as string) || '#3b82f6'}
              fontSize={14} fontWeight={500} opacity={Math.min(1, progress * 2)} {...TEXT_STYLE}>
              {layer.label as string}
            </text>
            {i < layers.length - 1 && (
              <Arrow x1={480} y1={y + 60} x2={480 - 30 + (i % 2) * 60} y2={(layers[i + 1].y as number)}
                color="#d1d5db" />
            )}
          </g>
        )
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: dataPipeline — 数据流水线                                   */
/* ------------------------------------------------------------------ */

function DataPipelineScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      {config.items.map((item, i) => {
        if (item.type === 'stage') {
          const x = (item.x as number); const y = (item.y as number)
          const w = (item.w as number) || 130; const h = (item.h as number) || 40
          return (
            <g key={`s${i}`}>
              <rect x={x} y={y} width={w} height={h} rx={6}
                fill={(item.color as string || '#3b82f6') + '15'}
                stroke={(item.color as string) || '#3b82f6'} strokeWidth={1.5}
              />
              <text x={x + w / 2} y={y + h / 2 + 5}
                textAnchor="middle" fill={(item.color as string) || '#3b82f6'}
                fontSize={11} fontWeight={500} {...TEXT_STYLE}>
                {item.label as string}
              </text>
            </g>
          )
        }
        if (item.type === 'arrow') {
          const fromStage = config.items.find(s => s.id === item.from) as Record<string, number> | undefined
          const toStage = config.items.find(s => s.id === item.to) as Record<string, number> | undefined
          if (!fromStage || !toStage) return null
          const fx = fromStage.x + (fromStage.w || 130)
          const fy = fromStage.y + (fromStage.h || 40) / 2
          const tx = toStage.x
          const ty = toStage.y + (toStage.h || 40) / 2
          return (
            <g key={`a${i}`}>
              <line x1={fx + 4} y1={fy} x2={tx - 4} y2={ty}
                stroke={(item.color as string) || '#3b82f6'} strokeWidth={2} />
              <polygon points={`${tx-4},${ty} ${tx-12},${ty-5} ${tx-12},${ty+5}`}
                fill={(item.color as string) || '#3b82f6'} />
            </g>
          )
        }
        return null
      })}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: formulaExplorer — 公式展示                                  */
/* ------------------------------------------------------------------ */

function FormulaExplorerScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      {config.items.filter(i => i.type === 'formula').map((item, i) => (
        <g key={`f${i}`}>
          <rect x={150} y={(item.y as number) || 140} width={660} height={40} rx={6}
            fill="#f9fafb" stroke="#e5e7eb" strokeWidth={1} />
          <text x={480} y={((item.y as number) || 140) + 27}
            textAnchor="middle" fill="#111827" fontSize={15} fontWeight={500}
            fontFamily="monospace">
            {item.text as string}
          </text>
        </g>
      ))}
      {config.items.filter(i => i.type === 'note').map((item, i) => (
        <text key={`n${i}`} x={480} y={(item.y as number) || 200}
          textAnchor="middle" fill="#6b7280" fontSize={13} {...TEXT_STYLE}>
          {item.text as string}
        </text>
      ))}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: robotView — 简化 Upkie 正视图                              */
/* ------------------------------------------------------------------ */

function RobotViewScene({ config }: { config: ChapterAnimationConfig }) {
  const ctrl = useAnimation()
  const sway = Math.sin(ctrl.time / 2000) * 5

  return (
    <g>
      <TitleArea config={config} y={30} />
      {/* 地面 */}
      <line x1={80} y1={440} x2={880} y2={440} stroke="#d1d5db" strokeWidth={2} />
      <text x={870} y={430} textAnchor="end" fill="#9ca3af" fontSize={11} {...TEXT_STYLE}>地面</text>
      {/* 机身 */}
      <rect x={400} y={200} width={160} height={100} rx={8} fill="#4b5563" />
      <text x={480} y={260} textAnchor="middle" fill="#fff" fontSize={12} fontWeight={600} {...TEXT_STYLE}>Upkie</text>
      {/* 左腿 */}
      <line x1={420} y1={300} x2={380 + sway} y2={380} stroke="#9ca3af" strokeWidth={6} strokeLinecap="round" />
      <line x1={380 + sway} y1={380} x2={360 + sway} y2={440} stroke="#6b7280" strokeWidth={4} strokeLinecap="round" />
      {/* 右腿 */}
      <line x1={540} y1={300} x2={580 - sway} y2={380} stroke="#9ca3af" strokeWidth={6} strokeLinecap="round" />
      <line x1={580 - sway} y1={380} x2={600 - sway} y2={440} stroke="#6b7280" strokeWidth={4} strokeLinecap="round" />
      {/* 左轮 */}
      <circle cx={360 + sway} cy={445} r={18} fill="#1f2937" stroke="#374151" strokeWidth={2} />
      <text x={360 + sway} y={470} textAnchor="middle" fill="#6b7280" fontSize={10} {...TEXT_STYLE}>左轮</text>
      {/* 右轮 */}
      <circle cx={600 - sway} cy={445} r={18} fill="#1f2937" stroke="#374151" strokeWidth={2} />
      <text x={600 - sway} y={470} textAnchor="middle" fill="#6b7280" fontSize={10} {...TEXT_STYLE}>右轮</text>
      {/* 关节标签 */}
      <text x={340} y={295} fill="#3b82f6" fontSize={9} {...TEXT_STYLE}>左髋</text>
      <text x={610} y={295} fill="#3b82f6" fontSize={9} {...TEXT_STYLE}>右髋</text>
      <text x={320} y={385} fill="#8b5cf6" fontSize={9} {...TEXT_STYLE}>左膝</text>
      <text x={630} y={385} fill="#8b5cf6" fontSize={9} {...TEXT_STYLE}>右膝</text>
      {/* 传感器标注 */}
      {config.items.filter(i => i.type === 'sensor').map((item, i) => (
        <text key={`se${i}`} x={(item.x as number) || 480} y={(item.y as number) || 480}
          textAnchor="middle" fill="#6366f1" fontSize={11} fontWeight={500} {...TEXT_STYLE}>
          {(item.label as string)}
        </text>
      ))}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  Scene: default — 占位                                              */
/* ------------------------------------------------------------------ */

function DefaultScene({ config }: { config: ChapterAnimationConfig }) {
  return (
    <g>
      <TitleArea config={config} />
      <text x={480} y={260} textAnchor="middle" fill="#9ca3af" fontSize={16} {...TEXT_STYLE}>
        暂无可交互动画
      </text>
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  小工具                                                              */
/* ------------------------------------------------------------------ */

function Arrow({ x1, y1, x2, y2, color }: { x1: number; y1: number; x2: number; y2: number; color: string }) {
  const dx = x2 - x1; const dy = y2 - y1
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={1.5} />
      <polygon points={`${x2},${y2} ${x2-5},${y2-3} ${x2-5},${y2+3}`} fill={color}
        transform={`rotate(${Math.atan2(dy, dx) * 180 / Math.PI}, ${x2}, ${y2})`} />
    </g>
  )
}
