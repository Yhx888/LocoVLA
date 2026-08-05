import { createContext, useContext, useState, useRef, useCallback, useEffect, type ReactNode } from 'react'
import ControlBar from './ControlBar'

export interface AnimationControls {
  playing: boolean
  progress: number
  time: number
  duration: number
  play: () => void
  pause: () => void
  reset: () => void
  step: () => void
  setDuration: (ms: number) => void
  setProgress: (p: number) => void
  params: Record<string, number>
  setParam: (key: string, value: number) => void
}

export const AnimationCtx = createContext<AnimationControls | null>(null)

export function useAnimation(): AnimationControls {
  const ctx = useContext(AnimationCtx)
  if (!ctx) throw new Error('useAnimation must be used inside <AnimationCanvas>')
  return ctx
}

interface SliderDef {
  key: string
  label: string
  min: number
  max: number
  step?: number
}

interface Props {
  children: ReactNode
  controls?: boolean
  width?: number
  height?: number
  sliders?: SliderDef[]
  duration?: number
}

const VIEW_W = 960
const VIEW_H = 540

export default function AnimationCanvas({
  children,
  controls = true,
  width,
  height,
  sliders = [],
  duration: defaultDuration = 8000,
}: Props) {
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(defaultDuration)
  const [params, setParams] = useState<Record<string, number>>({})
  const rafRef = useRef<number>(0)
  const lastRef = useRef<number>(0)
  const reducedRef = useRef(false)
  // 挂载时的滑块定义，作为"初始参数"快照：reset 需要把参数回归到它
  const initialSlidersRef = useRef(sliders)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    reducedRef.current = mq.matches
    const handler = (e: MediaQueryListEvent) => { reducedRef.current = e.matches }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const tick = useCallback((now: number) => {
    if (!lastRef.current) lastRef.current = now
    const dt = Math.min(now - lastRef.current, 100)
    lastRef.current = now
    setTime(prev => {
      const next = prev + dt
      if (next >= duration) return 0
      return next
    })
    rafRef.current = requestAnimationFrame(tick)
  }, [duration])

  useEffect(() => {
    if (playing && !reducedRef.current) {
      lastRef.current = 0
      rafRef.current = requestAnimationFrame(tick)
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [playing, tick])

  const play = useCallback(() => setPlaying(true), [])
  const pause = useCallback(() => setPlaying(false), [])
  // 完整重置：播放状态、时间、所有参数滑块都回归初始值（滑块初始值 = min）
  const reset = useCallback(() => {
    setPlaying(false)
    setTime(0)
    const defaults: Record<string, number> = {}
    for (const s of initialSlidersRef.current) defaults[s.key] = s.min
    setParams(defaults)
  }, [])
  const step = useCallback(() => {
    setPlaying(false)
    setTime(prev => {
      const next = prev + duration / 60
      return next >= duration ? 0 : next
    })
  }, [duration])

  const progress = duration > 0 ? time / duration : 0

  const setParam = useCallback((key: string, value: number) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }, [])

  const value: AnimationControls = {
    playing, progress, time, duration,
    play, pause, reset, step,
    setDuration, setProgress: setTime,
    params, setParam,
  }

  const aspect = VIEW_W / VIEW_H
  const containerStyle: React.CSSProperties = width
    ? { width, height: height ?? width / aspect }
    : { width: '100%', maxWidth: VIEW_W, aspectRatio: `${VIEW_W}/${VIEW_H}` }

  return (
    <AnimationCtx.Provider value={value}>
      <div style={{ position: 'relative', ...containerStyle }} className="bg-white border rounded-lg overflow-hidden">
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          style={{ width: '100%', height: '100%', display: 'block' }}
          xmlns="http://www.w3.org/2000/svg"
          role="img"
        >
          {children}
        </svg>
        {controls && (
          <ControlBar sliders={sliders} />
        )}
      </div>
    </AnimationCtx.Provider>
  )
}

export { VIEW_W, VIEW_H }
