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

export default function ControlBar({ sliders = [] }: Props) {
  const anim = useAnimation()

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        borderTop: '1px solid #e5e7eb',
        background: '#f9fafb',
        fontSize: 13,
        userSelect: 'none',
      }}
    >
      {/* Play/Pause */}
      <button
        onClick={anim.playing ? anim.pause : anim.play}
        title={anim.playing ? '暂停' : '播放'}
        style={{
          border: '1px solid #d1d5db', borderRadius: 4, padding: '2px 10px',
          cursor: 'pointer', background: '#fff', lineHeight: '24px',
        }}
      >
        {anim.playing ? '⏸' : '▶'}
      </button>

      {/* Step */}
      <button
        onClick={anim.step}
        title="步进"
        style={{
          border: '1px solid #d1d5db', borderRadius: 4, padding: '2px 10px',
          cursor: 'pointer', background: '#fff', lineHeight: '24px',
        }}
      >
        ⏭
      </button>

      {/* Reset */}
      <button
        onClick={anim.reset}
        title="重置"
        style={{
          border: '1px solid #d1d5db', borderRadius: 4, padding: '2px 10px',
          cursor: 'pointer', background: '#fff', lineHeight: '24px',
        }}
      >
        ⏹
      </button>

      {/* Time info */}
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#6b7280', minWidth: 80 }}>
        {formatTime(anim.time)} / {formatTime(anim.duration)}
      </span>

      {/* Progress bar */}
      <div
        style={{
          flex: 1, minWidth: 60, height: 6, background: '#e5e7eb',
          borderRadius: 3, cursor: 'pointer', position: 'relative',
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
            background: '#3b82f6', borderRadius: 3,
            transition: 'width 50ms linear',
          }}
        />
      </div>

      {/* Sliders */}
      {sliders.map((s) => (
        <label
          key={s.key}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            fontSize: 12, whiteSpace: 'nowrap',
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
            style={{ width: 80, height: 4, margin: 0, verticalAlign: 'middle' }}
          />
          <span style={{ fontFamily: 'monospace', color: '#6b7280', minWidth: 28 }}>
            {(anim.params[s.key] ?? s.min).toFixed(s.step && s.step >= 1 ? 0 : 2)}
          </span>
        </label>
      ))}
    </div>
  )
}
