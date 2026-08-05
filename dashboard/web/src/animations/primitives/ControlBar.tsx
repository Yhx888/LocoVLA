import { useAnimation } from './AnimationCanvas'
import type { AnimationControls } from './AnimationCanvas'

interface SliderDef {
  key: string
  label: string
  min: number
  max: number
  step?: number
}

interface Props {
  sliders?: SliderDef[]
}

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000)
  const cs = Math.floor((ms % 1000) / 10)
  return `${s}.${cs.toString().padStart(2, '0')}s`
}

/* 控制条按钮：白底描边，hover 上浮微反馈 */
function BarButton({ onClick, title, children }: { onClick: () => void; title: string; children: string }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        border: '1px solid var(--gray-300)',
        borderRadius: 4,
        padding: '2px 10px',
        cursor: 'pointer',
        background: 'var(--white)',
        color: 'var(--gray-700)',
        lineHeight: '24px',
        transition: 'background var(--transition-fast), transform var(--transition-fast)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--gray-100)'
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'var(--white)'
        e.currentTarget.style.transform = ''
      }}
    >
      {children}
    </button>
  )
}

export default function ControlBar({ sliders = [] }: Props) {
  const anim = useAnimation()

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        borderTop: '1px solid var(--gray-200)',
        background: 'var(--gray-50)',
        fontSize: 13,
        userSelect: 'none',
      }}
    >
      {/* Play/Pause */}
      <BarButton onClick={anim.playing ? anim.pause : anim.play} title={anim.playing ? '暂停' : '播放'}>
        {anim.playing ? '⏸' : '▶'}
      </BarButton>

      {/* Step */}
      <BarButton onClick={anim.step} title="步进一帧">
        ⏭
      </BarButton>

      {/* Reset：完整重置（时间 + 参数滑块） */}
      <BarButton onClick={anim.reset} title="重置（时间与参数滑块）">
        ⏹
      </BarButton>

      {/* Time info */}
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--gray-500)', minWidth: 80 }}>
        {formatTime(anim.time)} / {formatTime(anim.duration)}
      </span>

      {/* Progress bar：点击/拖动跳转，悬停微增高 */}
      <div
        style={{
          flex: 1, minWidth: 60, height: 6, background: 'var(--gray-200)',
          borderRadius: 3, cursor: 'pointer', position: 'relative',
          transition: 'height var(--transition-fast)',
        }}
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const pct = (e.clientX - rect.left) / rect.width
          anim.setProgress(pct * anim.duration)
        }}
      >
        <div
          style={{
            height: '100%', width: `${anim.progress * 100}%`,
            background: 'var(--blue-500)', borderRadius: 3,
            transition: 'width 50ms linear',
          }}
        />
      </div>

      {/* Sliders：value 来自 anim.params，reset 后自动回位到 min */}
      {sliders.map((s) => (
        <label
          key={s.key}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            fontSize: 12, whiteSpace: 'nowrap', color: 'var(--gray-700)',
          }}
        >
          {s.label}
          <input
            type="range"
            min={s.min}
            max={s.max}
            step={s.step ?? 0.01}
            value={anim.params[s.key] ?? s.min}
            onChange={(e) => anim.setParam(s.key, parseFloat(e.target.value))}
            style={{ width: 80, height: 4, margin: 0, verticalAlign: 'middle', accentColor: 'var(--blue-600)' }}
          />
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--gray-600)', minWidth: 28 }}>
            {(anim.params[s.key] ?? s.min).toFixed(s.step && s.step >= 1 ? 0 : 2)}
          </span>
        </label>
      ))}
    </div>
  )
}
