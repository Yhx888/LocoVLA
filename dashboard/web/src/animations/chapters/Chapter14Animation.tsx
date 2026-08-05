import { useEffect, useMemo } from 'react'
import AnimationCanvas, { useAnimation } from '../primitives/AnimationCanvas'
import { Arrow, DashedLine } from '../primitives/DrawingPrimitives'

const FONT = 'system-ui, "Noto Sans SC", sans-serif'

const SLIDERS = [
  { key: 'angle', label: '初始扰动 θ₀', min: -30, max: 30, step: 1 },
  { key: 'force', label: '驱动力 F', min: 0, max: 50, step: 1 },
]
const DEFAULTS = { angle: 15, force: 20 }

const N = 150            // 仿真帧数
const GROUND_Y = 420
const CART_W = 120
const CART_H = 36
const POLE_LEN = 190
const WHEEL_R = 11

const clamp01 = (t: number) => Math.max(0, Math.min(1, t))
const easeOutBack = (t: number) => {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

/* ------------------------------------------------------------------ */
/*  动力学仿真：小车解析往复 + 摆杆欠阻尼二阶响应                       */
/*  θ₀ 为初始扰动；F 决定小车振幅（驱动力越大，移动与倾斜越剧烈）        */
/* ------------------------------------------------------------------ */

interface Frame { x: number; v: number; th: number; w: number }

function simulate(angle: number, force: number): Frame[] {
  const dt = 1 / N
  const omega = 2 * Math.PI * 1.25        // 1.25 个往复周期
  const amp = 40 + force                  // 小车振幅随驱动力
  const th0 = (angle * Math.PI) / 180     // 初始扰动角
  let th = th0
  let w = 0
  const k = 60                            // 摆杆回复刚度（rad/s² 每弧度）
  const zeta = 0.25                       // 欠阻尼：摆动带惯性滞后，多次衰减
  const wn = Math.sqrt(k)
  const frames: Frame[] = []
  for (let i = 0; i <= N; i++) {
    const t = i / N
    const env = Math.pow(Math.sin(Math.PI * t), 0.55)   // 起步/收尾缓启缓停
    const ph = omega * t
    const x = amp * Math.sin(ph) * env
    const v = amp * omega * Math.cos(ph) * env
    /* 等效重力倾斜：小车加速度让"平衡方向"偏移（简化为直接参数化） */
    const thEq = -(amp / 40) * (8 * Math.PI / 180) * Math.sin(ph) * env
    const acc = k * (thEq - th) - 2 * zeta * wn * w
    frames.push({ x, v, th, w })
    w += acc * dt
    th += w * dt
  }
  return frames
}

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

export default function Chapter14Animation() {
  return (
    <AnimationCanvas controls duration={7000} sliders={SLIDERS}>
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
  const fade = (t0: number) => clamp01((p - t0) / 0.08)

  const angle = params.angle ?? DEFAULTS.angle
  const force = params.force ?? DEFAULTS.force
  /* 滑块变化 → 重新仿真；播放头取当前帧（保持连续） */
  const frames = useMemo(() => simulate(angle, force), [angle, force])
  const fr = frames[Math.min(Math.floor(p * N), N)]

  const cartX = 400 + fr.x
  const pivotX = cartX
  const pivotY = GROUND_Y - CART_H
  const ballX = pivotX + POLE_LEN * Math.sin(fr.th)
  const ballY = pivotY - POLE_LEN * Math.cos(fr.th)

  /* 力箭头：向右推，长度随 F */
  const forceLen = 8 + force * 1.2
  /* θ 弧线（从竖直参考到摆杆） */
  const arcR = 42
  const arcEnd = { x: pivotX + arcR * Math.sin(fr.th), y: pivotY - arcR * Math.cos(fr.th) }
  const arcMid = { x: pivotX + (arcR + 15) * Math.sin(fr.th / 2), y: pivotY - (arcR + 15) * Math.cos(fr.th / 2) }
  const deg = (r: number) => (r * 180) / Math.PI

  const pop = (t0: number) => 0.55 + 0.45 * easeOutBack(clamp01((p - t0) / 0.1))

  return (
    <>
      <rect x="0" y="0" width="960" height="540" fill="#fafafa" />

      {/* 标题（静态） */}
      <text x="480" y="28" textAnchor="middle" fill="#111827" fontSize={20} fontWeight={700} fontFamily={FONT}>
        轮式倒立摆动力学
      </text>
      <text x="480" y="47" textAnchor="middle" fill="#9ca3af" fontSize={12} fontFamily={FONT}>
        小车往复驱动 → 摆杆惯性响应 → 平衡修正
      </text>

      {/* 地面与刻度 */}
      <g opacity={fade(0.06)}>
        <line x1={40} y1={GROUND_Y} x2={920} y2={GROUND_Y} stroke="#374151" strokeWidth={2} />
        {Array.from({ length: 20 }, (_, i) => (
          <line key={i} x1={80 + i * 44} y1={GROUND_Y} x2={75 + i * 44} y2={GROUND_Y + 8} stroke="#9ca3af" strokeWidth={1.5} />
        ))}
      </g>

      {/* 平衡参考虚线（随小车移动） */}
      <g opacity={fade(0.10) * 0.7}>
        <DashedLine x1={pivotX} y1={pivotY} x2={pivotX} y2={pivotY - POLE_LEN - 24} color="#d1d5db" dashArray="5,4" />
      </g>

      {/* 小车 + 轮子（弹性入场） */}
      <g opacity={fade(0.10)} transform={`translate(${cartX} ${GROUND_Y - CART_H / 2}) scale(${pop(0.10)}) translate(${-cartX} ${-(GROUND_Y - CART_H / 2)})`}>
        <rect x={cartX - CART_W / 2} y={GROUND_Y - CART_H} width={CART_W} height={CART_H} rx={4} fill="#6366f1" stroke="#4f46e5" strokeWidth={2} />
        <circle cx={cartX - CART_W / 3} cy={GROUND_Y} r={WHEEL_R} fill="#374151" />
        <circle cx={cartX + CART_W / 3} cy={GROUND_Y} r={WHEEL_R} fill="#374151" />
      </g>

      {/* 主摆杆（动力学仿真，主元素）+ 质量球 */}
      <g opacity={fade(0.12)}>
        <g transform={`translate(${pivotX} ${pivotY}) scale(${pop(0.12)}) translate(${-pivotX} ${-pivotY})`}>
          <line x1={pivotX} y1={pivotY} x2={ballX} y2={ballY} stroke="#3b82f6" strokeWidth={4} strokeLinecap="round" />
        </g>
        <g transform={`translate(${ballX} ${ballY}) scale(${pop(0.14)}) translate(${-ballX} ${-ballY})`}>
          <circle cx={ballX} cy={ballY} r={11} fill="#3b82f6" stroke="#2563eb" strokeWidth={2} />
          <text x={ballX} y={ballY + 1} textAnchor="middle" dominantBaseline="central" fill="#fff" fontSize={10} fontFamily={FONT}>
            m
          </text>
        </g>
      </g>

      {/* θ 弧线与角度 */}
      <g opacity={fade(0.22)}>
        <path d={`M ${pivotX},${pivotY - arcR} A ${arcR},${arcR} 0 0,${fr.th >= 0 ? 1 : 0} ${arcEnd.x},${arcEnd.y}`}
          fill="none" stroke="#f59e0b" strokeWidth={1.5} />
        <text x={arcMid.x} y={arcMid.y} fill="#f59e0b" fontSize={12} fontWeight={600} fontFamily="monospace">
          θ = {deg(fr.th).toFixed(1)}°
        </text>
      </g>

      {/* 驱动力 F（向右，长度随 F） */}
      <g opacity={fade(0.2) * (force > 1 ? 1 : 0.4)}>
        <Arrow x1={cartX + CART_W / 2} y1={GROUND_Y - CART_H / 2} x2={cartX + CART_W / 2 + forceLen} y2={GROUND_Y - CART_H / 2}
          color="#ef4444" strokeWidth={3} headSize={10} />
        <text x={cartX + CART_W / 2 + forceLen + 12} y={GROUND_Y - CART_H / 2 + 4} fill="#ef4444" fontSize={13} fontWeight={600} fontFamily={FONT}>
          F
        </text>
      </g>

      {/* 重力 mg（始终向下） */}
      <g opacity={fade(0.24)}>
        <Arrow x1={ballX} y1={ballY} x2={ballX} y2={ballY + 52} color="#22c55e" strokeWidth={2.5} headSize={8} />
        <text x={ballX + 10} y={ballY + 30} fill="#22c55e" fontSize={12} fontWeight={600} fontFamily={FONT}>
          mg
        </text>
      </g>

      {/* 动力学遥测卡（右滑入场，数值随仿真实时刷新） */}
      <g opacity={fade(0.28)} transform={`translate(${30 * (1 - fade(0.28))} 0)`}>
        <rect x="620" y="64" width="300" height="186" rx={8} fill="#f8fafc" stroke="#e2e8f0" strokeWidth={1} />
        <text x="770" y="86" textAnchor="middle" fill="#475569" fontSize={13} fontWeight={600} fontFamily={FONT}>
          动力学遥测
        </text>
        <text x="636" y="110" fill="#64748b" fontSize={12} fontFamily="monospace">
          θ = {deg(fr.th).toFixed(1)}°    θ̇ = {deg(fr.w).toFixed(1)}°/s
        </text>
        <text x="636" y="130" fill="#64748b" fontSize={12} fontFamily="monospace">
          x = {fr.x.toFixed(0)} px    v = {fr.v.toFixed(1)}
        </text>
        <text x="636" y="150" fill="#64748b" fontSize={12} fontFamily="monospace">
          F = {force.toFixed(0)} N    θ₀ = {angle.toFixed(0)}°
        </text>
        <line x1="636" y1="160" x2="904" y2="160" stroke="#e2e8f0" strokeWidth={1} />
        <text x="636" y="176" fill="#9ca3af" fontSize={10} fontFamily="monospace">
          M·ẍ = F − m·l·θ̈·cosθ + m·l·θ̇²·sinθ
        </text>
        <text x="636" y="192" fill="#9ca3af" fontSize={10} fontFamily="monospace">
          (m·l²)·θ̈ = m·g·l·sinθ − m·l·ẍ·cosθ
        </text>
        <text x="636" y="212" fill="#9ca3af" fontSize={10} fontFamily="monospace">
          ζ = 0.25（欠阻尼 · 摆动带惯性滞后）
        </text>
        <text x="636" y="228" fill="#9ca3af" fontSize={10} fontFamily="monospace">
          F 越大 → 振幅与倾斜越剧烈
        </text>
      </g>

      {/* 底部提示 */}
      <g opacity={fade(0.85)}>
        <text x="480" y="512" textAnchor="middle" fill="#9ca3af" fontSize={11} fontFamily={FONT}>
          θ₀ 滑块 = 初始扰动 · F 滑块 = 驱动力 · 摆杆为欠阻尼动力学仿真（有惯性与衰减）
        </text>
      </g>
    </>
  )
}
