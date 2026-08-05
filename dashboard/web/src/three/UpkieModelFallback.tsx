/* 真实 Upkie 正视图比例（米制 → scale 440 px/m，中心 x=200，地面 y=460）：
   轮半径 0.05、半轮距 0.30；机身 0.17 × 0.25、中心离地 0.165；
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
};

const SCALE = 440;
const GROUND = 460;
const CX = 200;
const px = (y: number) => CX + y * SCALE;
const py = (z: number) => GROUND - z * SCALE;
const pose = {
  r: UPKIE.wheelR * SCALE,
  wheelL: { x: px(-UPKIE.trackHalf), y: py(UPKIE.wheelR) },
  wheelR: { x: px(UPKIE.trackHalf), y: py(UPKIE.wheelR) },
  hipL: { x: px(-UPKIE.hipY), y: py(UPKIE.hipZ) },
  hipR: { x: px(UPKIE.hipY), y: py(UPKIE.hipZ) },
  kneeL: { x: px(-UPKIE.kneeY), y: py(UPKIE.kneeZ) },
  kneeR: { x: px(UPKIE.kneeY), y: py(UPKIE.kneeZ) },
  body: {
    x: px(-UPKIE.bodyW / 2),
    y: py(UPKIE.bodyCenterZ + UPKIE.bodyH / 2),
    w: UPKIE.bodyW * SCALE,
    h: UPKIE.bodyH * SCALE,
  },
  handle: {
    x: px(-UPKIE.handleW / 2),
    y: py(UPKIE.bodyCenterZ + UPKIE.bodyH / 2 + UPKIE.handleH),
    w: UPKIE.handleW * SCALE,
    h: UPKIE.handleH * SCALE,
  },
};

export default function UpkieModelFallback() {
  return (
    <svg
      viewBox="0 0 400 500"
      style={{ width: '100%', height: '100%', maxHeight: 500, background: '#f8fafc', borderRadius: 8 }}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Upkie 机器人结构示意图（WebGL 不可用时的备选视图）"
    >
      {/* Title */}
      <text x={CX} y="24" textAnchor="middle" fill="#374151" fontSize={14} fontWeight={700} fontFamily="system-ui, sans-serif">
        Upkie 结构示意图
      </text>

      {/* Ground line */}
      <line x1={50} y1={GROUND} x2={350} y2={GROUND} stroke="#9ca3af" strokeWidth={2} />
      <line x1={80} y1={GROUND} x2={75} y2={GROUND + 8} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={160} y1={GROUND} x2={155} y2={GROUND + 8} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={240} y1={GROUND} x2={235} y2={GROUND + 8} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={320} y1={GROUND} x2={315} y2={GROUND + 8} stroke="#9ca3af" strokeWidth={1.5} />

      {/* 机身（陶土配色）+ 把手 */}
      <rect x={pose.body.x} y={pose.body.y} width={pose.body.w} height={pose.body.h} rx={8} fill="#f5e6d8" stroke="#c2703d" strokeWidth={2} />
      <rect x={pose.handle.x} y={pose.handle.y} width={pose.handle.w} height={pose.handle.h} rx={3.5} fill="#c2703d" />

      {/* 双腿：大腿 / 小腿细杆 + 关节圆点 */}
      {([
        { hip: pose.hipL, knee: pose.kneeL, wheel: pose.wheelL },
        { hip: pose.hipR, knee: pose.kneeR, wheel: pose.wheelR },
      ]).map((leg, i) => (
        <g key={`leg${i}`}>
          <line x1={leg.hip.x} y1={leg.hip.y} x2={leg.knee.x} y2={leg.knee.y} stroke="#94a3b8" strokeWidth={4} strokeLinecap="round" />
          <line x1={leg.knee.x} y1={leg.knee.y} x2={leg.wheel.x} y2={leg.wheel.y - pose.r + 1} stroke="#94a3b8" strokeWidth={4} strokeLinecap="round" />
          <circle cx={leg.hip.x} cy={leg.hip.y} r={4.5} fill="#7c2d12" />
          <circle cx={leg.knee.x} cy={leg.knee.y} r={3.5} fill="#7c2d12" />
        </g>
      ))}

      {/* 轮子：黑轮 + 轮毂 */}
      {[pose.wheelL, pose.wheelR].map((w, i) => (
        <g key={`wheel${i}`}>
          <circle cx={w.x} cy={w.y} r={pose.r} fill="#1f2937" stroke="#374151" strokeWidth={2} />
          <circle cx={w.x} cy={w.y} r={pose.r * 0.42} fill="#374151" />
          <circle cx={w.x} cy={w.y} r={pose.r * 0.16} fill="#9ca3af" />
        </g>
      ))}

      {/* Labels */}
      <g fontSize={10} fontFamily="system-ui, sans-serif" fill="#6b7280">
        <text x={CX} y={pose.body.y + 62} textAnchor="middle">机身（Body）</text>

        <text x={pose.kneeL.x - 8} y={pose.hipL.y + 2} textAnchor="end">左大腿</text>
        <text x={pose.kneeR.x + 8} y={pose.hipR.y + 2} textAnchor="start">右大腿</text>

        <text x={pose.kneeL.x + 8} y={pose.kneeL.y + 12} textAnchor="start">左小腿</text>
        <text x={pose.kneeR.x - 8} y={pose.kneeR.y + 12} textAnchor="end">右小腿</text>

        <text x={pose.wheelL.x} y={GROUND + 16} textAnchor="middle">左轮</text>
        <text x={pose.wheelR.x} y={GROUND + 16} textAnchor="middle">右轮</text>
      </g>

      {/* Joint labels */}
      <g fontSize={8} fontFamily="system-ui, sans-serif" fill="#9ca3af">
        <text x={pose.hipL.x - 8} y={pose.hipL.y - 6} textAnchor="end">左髋</text>
        <text x={pose.hipR.x + 8} y={pose.hipR.y - 6} textAnchor="start">右髋</text>
        <text x={pose.kneeL.x + 8} y={pose.kneeL.y - 6} textAnchor="start">左膝</text>
        <text x={pose.kneeR.x - 8} y={pose.kneeR.y - 6} textAnchor="end">右膝</text>
      </g>

      {/* Note */}
      <text x={CX} y={490} textAnchor="middle" fill="#9ca3af" fontSize={10} fontFamily="system-ui, sans-serif">
        WebGL 不可用，SVG 示意结构替代 · 6 个关节：髋、膝、轮各 × 2
      </text>
    </svg>
  )
}
