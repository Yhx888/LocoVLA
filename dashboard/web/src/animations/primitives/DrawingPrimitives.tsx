import type { CSSProperties } from 'react'

/* ------------------------------------------------------------------ */
/*  Arrow                                                              */
/* ------------------------------------------------------------------ */
interface ArrowProps {
  x1: number; y1: number; x2: number; y2: number
  color?: string; strokeWidth?: number; headSize?: number; dashed?: boolean; opacity?: number
}

export function Arrow({
  x1, y1, x2, y2, color = '#666', strokeWidth = 2,
  headSize = 8, dashed = false, opacity = 1,
}: ArrowProps) {
  const angle = Math.atan2(y2 - y1, x2 - x1)
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const hs = headSize
  const hx1 = x2 - hs * cos + hs * 0.35 * sin
  const hy1 = y2 - hs * sin - hs * 0.35 * cos
  const hx2 = x2 - hs * cos - hs * 0.35 * sin
  const hy2 = y2 - hs * sin + hs * 0.35 * cos

  return (
    <g opacity={opacity}>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={dashed ? '6,4' : undefined}
      />
      <polygon points={`${x2},${y2} ${hx1},${hy1} ${hx2},${hy2}`} fill={color} />
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  DashedLine                                                         */
/* ------------------------------------------------------------------ */
interface DashedLineProps {
  x1: number; y1: number; x2: number; y2: number
  color?: string; strokeWidth?: number; dashArray?: string; opacity?: number
}

export function DashedLine({
  x1, y1, x2, y2, color = '#999',
  strokeWidth = 1.5, dashArray = '6,4', opacity = 1,
}: DashedLineProps) {
  return (
    <line
      x1={x1} y1={y1} x2={x2} y2={y2}
      stroke={color} strokeWidth={strokeWidth}
      strokeDasharray={dashArray} opacity={opacity}
    />
  )
}

/* ------------------------------------------------------------------ */
/*  StateCircle                                                        */
/* ------------------------------------------------------------------ */
interface StateCircleProps {
  cx: number; cy: number; r?: number
  label: string
  state?: 'active' | 'completed' | 'locked' | 'current'
  color?: string
  fontSize?: number
}

const STATE_COLORS: Record<string, string> = {
  active: '#3b82f6',
  completed: '#22c55e',
  locked: '#d1d5db',
  current: '#f59e0b',
}

export function StateCircle({
  cx, cy, r = 22, label, state = 'locked',
  color, fontSize = 11,
}: StateCircleProps) {
  const fill = color ?? STATE_COLORS[state] ?? '#d1d5db'
  const textColor = state === 'locked' ? '#9ca3af' : '#fff'

  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={fill} stroke={state === 'current' ? '#b45309' : 'none'} strokeWidth={2} />
      <text
        x={cx} y={cy} textAnchor="middle" dominantBaseline="central"
        fill={textColor} fontSize={fontSize} fontWeight={600}
        fontFamily="system-ui, sans-serif"
      >
        {label}
      </text>
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  CoordinateAxes                                                     */
/* ------------------------------------------------------------------ */
interface CoordAxesProps {
  originX?: number; originY?: number
  length?: number
  color?: string
  labels?: boolean
}

export function CoordinateAxes({
  originX = 80, originY = 420, length = 200,
  color = '#888', labels = true,
}: CoordAxesProps) {
  return (
    <g>
      <Arrow x1={originX} y1={originY} x2={originX + length} y2={originY} color={color} headSize={7} />
      <Arrow x1={originX} y1={originY} x2={originX} y2={originY - length} color={color} headSize={7} />
      {labels && (
        <>
          <text x={originX + length + 8} y={originY + 4} fill={color} fontSize={13} fontFamily="system-ui, sans-serif">x</text>
          <text x={originX - 4} y={originY - length - 6} fill={color} fontSize={13} fontFamily="system-ui, sans-serif">y</text>
          <text x={originX - 4} y={originY + 14} fill={color} fontSize={10} fontFamily="system-ui, sans-serif">O</text>
        </>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  TimelineBar                                                        */
/* ------------------------------------------------------------------ */
interface TimelineBarProps {
  x?: number; y?: number
  width?: number; height?: number
  progress: number
  color?: string
  label?: string
}

export function TimelineBar({
  x = 100, y = 500, width = 760, height = 6,
  progress, color = '#3b82f6', label,
}: TimelineBarProps) {
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={3} fill="#e5e7eb" />
      <rect x={x} y={y} width={width * Math.max(0, Math.min(1, progress))} height={height} rx={3} fill={color} />
      {label && (
        <text x={x + width / 2} y={y - 6} textAnchor="middle" fill="#6b7280" fontSize={11} fontFamily="system-ui, sans-serif">
          {label}
        </text>
      )}
    </g>
  )
}

/* ------------------------------------------------------------------ */
/*  RoundedRect                                                        */
/* ------------------------------------------------------------------ */
interface RoundedRectProps {
  x: number; y: number; width: number; height: number
  rx?: number; fill?: string; stroke?: string; strokeWidth?: number
  opacity?: number
}

export function RoundedRect({
  x, y, width, height, rx = 6,
  fill = '#fff', stroke = '#d1d5db', strokeWidth = 1.5, opacity = 1,
}: RoundedRectProps) {
  return (
    <rect
      x={x} y={y} width={width} height={height} rx={rx}
      fill={fill} stroke={stroke} strokeWidth={strokeWidth} opacity={opacity}
    />
  )
}

/* ------------------------------------------------------------------ */
/*  SignalCurve                                                        */
/* ------------------------------------------------------------------ */
interface SignalCurveProps {
  data: number[]
  x: number; y: number; width: number; height: number
  color?: string; strokeWidth?: number
}

export function SignalCurve({ data, x, y, width, height, color = '#3b82f6', strokeWidth = 2 }: SignalCurveProps) {
  if (data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data) || 1
  const range = max - min || 1
  const stepX = width / (data.length - 1)
  const pts = data.map((v, i) => {
    const px = x + i * stepX
    const py = y + height - ((v - min) / range) * height
    return `${i === 0 ? 'M' : 'L'}${px.toFixed(1)},${py.toFixed(1)}`
  }).join(' ')

  return (
    <path d={pts} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" strokeLinecap="round" />
  )
}

/* ------------------------------------------------------------------ */
/*  ArrowHead (standalone)                                             */
/* ------------------------------------------------------------------ */
interface ArrowHeadProps {
  x: number; y: number; angle: number; size?: number; color?: string
}

export function ArrowHead({ x, y, angle, size = 8, color = '#666' }: ArrowHeadProps) {
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const hx1 = x - size * cos + size * 0.35 * sin
  const hy1 = y - size * sin - size * 0.35 * cos
  const hx2 = x - size * cos - size * 0.35 * sin
  const hy2 = y - size * sin + size * 0.35 * cos
  return <polygon points={`${x},${y} ${hx1},${hy1} ${hx2},${hy2}`} fill={color} />
}
