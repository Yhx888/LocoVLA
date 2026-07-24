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
      <text x="200" y="24" textAnchor="middle" fill="#374151" fontSize={14} fontWeight={700} fontFamily="system-ui, sans-serif">
        Upkie 结构示意图
      </text>

      {/* Ground line */}
      <line x1={50} y1={460} x2={350} y2={460} stroke="#9ca3af" strokeWidth={2} />
      <line x1={80} y1={460} x2={75} y2={468} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={160} y1={460} x2={155} y2={468} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={240} y1={460} x2={235} y2={468} stroke="#9ca3af" strokeWidth={1.5} />
      <line x1={320} y1={460} x2={315} y2={468} stroke="#9ca3af" strokeWidth={1.5} />

      {/* Body / torso */}
      <rect x={150} y={160} width={100} height={60} rx={6} fill="#3a3a3a" />

      {/* Left leg */}
      <g>
        {/* Left hip */}
        <circle cx={165} cy={220} r={6} fill="#4a4a4a" />
        {/* Left thigh */}
        <polygon points="165,226 158,310 172,310" fill="#b0b0b0" />
        {/* Left knee */}
        <circle cx={165} cy={310} r={5} fill="#4a4a4a" />
        {/* Left shin */}
        <polygon points="165,315 160,390 170,390" fill="#b0b0b0" />
        {/* Left wheel */}
        <circle cx={165} cy={420} r={22} fill="#1a1a1a" />
        <circle cx={165} cy={420} r={14} fill="#333" />
      </g>

      {/* Right leg */}
      <g>
        <circle cx={235} cy={220} r={6} fill="#4a4a4a" />
        <polygon points="235,226 228,310 242,310" fill="#b0b0b0" />
        <circle cx={235} cy={310} r={5} fill="#4a4a4a" />
        <polygon points="235,315 230,390 240,390" fill="#b0b0b0" />
        <circle cx={235} cy={420} r={22} fill="#1a1a1a" />
        <circle cx={235} cy={420} r={14} fill="#333" />
      </g>

      {/* Labels */}
      <g fontSize={10} fontFamily="system-ui, sans-serif" fill="#6b7280">
        <text x={200} y={148} textAnchor="middle">机身（Body）</text>

        <text x={165} y={266} textAnchor="middle">左大腿</text>
        <text x={235} y={266} textAnchor="middle">右大腿</text>

        <text x={165} y={355} textAnchor="middle">左小腿</text>
        <text x={235} y={355} textAnchor="middle">右小腿</text>

        <text x={165} y={458} textAnchor="middle">左轮</text>
        <text x={235} y={458} textAnchor="middle">右轮</text>
      </g>

      {/* Joint labels */}
      <g fontSize={8} fontFamily="system-ui, sans-serif" fill="#9ca3af">
        <text x={148} y={216} textAnchor="end">左髋</text>
        <text x={148} y={306} textAnchor="end">左膝</text>
        <text x={252} y={216} textAnchor="start">右髋</text>
        <text x={252} y={306} textAnchor="start">右膝</text>
      </g>

      {/* Note */}
      <text x={200} y={490} textAnchor="middle" fill="#9ca3af" fontSize={10} fontFamily="system-ui, sans-serif">
        WebGL 不可用，SVG 示意结构替代 · 6 个关节：髋、膝、轮各 × 2
      </text>
    </svg>
  )
}
