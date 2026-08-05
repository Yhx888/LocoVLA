import { useEffect } from 'react'
import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, CoordinateAxes, DashedLine, RoundedRect } from '../primitives/DrawingPrimitives'

const FONT = 'system-ui, "Noto Sans SC", sans-serif'

const SLIDERS = [{ key: 'angle', label: '旋转角 θ', min: -180, max: 180, step: 1 }]
const DEFAULTS = { angle: 30 }

/* ------------------------------------------------------------------ */
/*  缓动工具                                                            */
/* ------------------------------------------------------------------ */

const clamp01 = (t: number) => Math.max(0, Math.min(1, t))
/* 过冲回弹：接近 1 时先越过目标再回落，模拟"定位"的物理感 */
const easeOutBack = (t: number) => {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

export default function Chapter03Animation() {
  return (
    <AnimationCanvas controls duration={6000} sliders={SLIDERS}>
      <Content />
    </AnimationCanvas>
  )
}

function Content() {
  const { progress, params, setParam, playing, time } = useAnimation()
  /* 重置（或挂载）时参数回归默认：time 归零且未播放即回到初始帧 */
  useEffect(() => {
    if (!playing && time === 0) Object.entries(DEFAULTS).forEach(([k, v]) => setParam(k, v))
  }, [playing, time, setParam])

  const p = progress
  const fade = (t0: number) => clamp01((p - t0) / 0.06)

  /* 滑块目标角（红色参考）与动画旋转角（蓝色主对象，缓动逼近目标） */
  const target = ((params.angle ?? DEFAULTS.angle) * Math.PI) / 180
  const animated = p >= 0.6 ? target : target * easeOutBack(clamp01(p / 0.6))

  const vecLen = 130
  const origX = 280
  const origY = 300

  const blueX = origX + vecLen * Math.cos(animated)
  const blueY = origY - vecLen * Math.sin(animated)
  const redX = origX + vecLen * Math.cos(target)
  const redY = origY - vecLen * Math.sin(target)

  const deg = (r: number) => (r * 180) / Math.PI
  /* 完成脉冲：蓝向量到位瞬间，尖端亮一下 */
  const pulse = Math.sin(Math.PI * clamp01((p - 0.58) / 0.14))

  /* 角度弧线（从 x 轴正方向到蓝向量） */
  const arcR = 38
  const arcEnd = { x: origX + arcR * Math.cos(animated), y: origY - arcR * Math.sin(animated) }
  const arcMid = { x: origX + (arcR + 16) * Math.cos(animated / 2), y: origY - (arcR + 16) * Math.sin(animated / 2) }

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      {/* 标题（静态） */}
      <text x="480" y="28" textAnchor="middle" fill="#111827" fontSize={20} fontWeight={700} fontFamily={FONT}>
        坐标变换可视化
      </text>
      <text x="480" y="47" textAnchor="middle" fill="#9ca3af" fontSize={12} fontFamily={FONT}>
        向量长度不变 · 方向旋转 θ · 投影即 cos / sin 分量
      </text>

      {/* 坐标系与轨迹圆 */}
      <g opacity={fade(0.05)}>
        <CoordinateAxes originX={origX} originY={origY} length={180} />
        <circle cx={origX} cy={origY} r={vecLen} fill="none" stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4,4" />
      </g>

      {/* 蓝色动画向量：从 0° 旋转到目标角 */}
      <g opacity={fade(0.14)}>
        <Arrow x1={origX} y1={origY} x2={blueX} y2={blueY} color="#3b82f6" strokeWidth={4} headSize={11} />
        {/* 长度标注（旋转不改变长度） */}
        <text x={origX + 62 * Math.cos(animated)} y={origY - 62 * Math.sin(animated) - 10}
          textAnchor="middle" fill="#60a5fa" fontSize={11} fontFamily="monospace" opacity={fade(0.3)}>
          |v| = {vecLen}
        </text>
      </g>

      {/* 红色目标参考向量（动画逼近完成后淡入对比） */}
      <g opacity={fade(0.46) * 0.85}>
        <Arrow x1={origX} y1={origY} x2={redX} y2={redY} color="#ef4444" strokeWidth={2} headSize={8} />
      </g>

      {/* 蓝向量投影（随旋转实时分解） */}
      <g opacity={fade(0.22)}>
        <DashedLine x1={blueX} y1={origY} x2={blueX} y2={blueY} color="#60a5fa" dashArray="4,3" />
        <DashedLine x1={origX} y1={blueY} x2={blueX} y2={blueY} color="#60a5fa" dashArray="4,3" />
        <text x={blueX} y={origY - 8} textAnchor="middle" fill="#3b82f6" fontSize={11} fontFamily="monospace">
          v·cosθ = {(vecLen * Math.cos(animated)).toFixed(1)}
        </text>
        <text x={origX + 10} y={blueY + 4} fill="#3b82f6" fontSize={11} fontFamily="monospace">
          v·sinθ = {(vecLen * Math.sin(animated)).toFixed(1)}
        </text>
      </g>

      {/* 角度弧线与 θ 数值 */}
      <g opacity={fade(0.2)}>
        <path d={`M ${origX + arcR},${origY} A ${arcR},${arcR} 0 0,${animated >= 0 ? 1 : 0} ${arcEnd.x},${arcEnd.y}`}
          fill="none" stroke="#f59e0b" strokeWidth={1.5} />
        <text x={arcMid.x} y={arcMid.y} fill="#f59e0b" fontSize={12} fontWeight={600} fontFamily="monospace">
          θ = {deg(animated).toFixed(1)}°
        </text>
      </g>

      {/* 旋转完成脉冲 */}
      {p >= 0.58 && p < 0.72 && (
        <circle cx={blueX} cy={blueY} r={5 + 6 * pulse} fill="#3b82f6" opacity={0.5 * pulse} />
      )}

      {/* 旋转矩阵公式卡（右滑入场，数值随蓝向量实时刷新） */}
      <g opacity={fade(0.26)} transform={`translate(${26 * (1 - fade(0.26))} 0)`}>
        <RoundedRect x={580} y={80} width={330} height={170} fill="#f8fafc" stroke="#e2e8f0" rx={10} />
        <text x="745" y="102" textAnchor="middle" fill="#475569" fontSize={14} fontWeight={600} fontFamily={FONT}>
          旋转矩阵
        </text>
        <text x="600" y="128" fill="#64748b" fontSize={12} fontFamily={FONT}>
          x' = x·cosθ − y·sinθ
        </text>
        <text x="600" y="148" fill="#64748b" fontSize={12} fontFamily={FONT}>
          y' = x·sinθ + y·cosθ
        </text>
        <line x1="600" y1="162" x2="890" y2="162" stroke="#e2e8f0" strokeWidth={1} />
        <text x="600" y="186" fill="#3b82f6" fontSize={15} fontWeight={700} fontFamily="monospace">
          θ = {deg(animated).toFixed(1)}°
        </text>
        <text x="600" y="210" fill="#3b82f6" fontSize={11} fontFamily="monospace">
          cos θ = {Math.cos(animated).toFixed(4)}
        </text>
        <text x="600" y="228" fill="#ef4444" fontSize={11} fontFamily="monospace">
          sin θ = {Math.sin(animated).toFixed(4)}
        </text>
      </g>

      {/* 底部提示 */}
      <g opacity={fade(0.75)}>
        <text x="480" y="512" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          红色向量 = 滑块目标角 θ · 蓝色向量 = 从 0° 旋转到目标 · 拖动滑块实时调整
        </text>
      </g>
    </>
  )
}
