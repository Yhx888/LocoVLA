import { lazy, Suspense } from 'react'
import AnimationCanvas from '../primitives/AnimationCanvas'
import { CHAPTER_ANIMATIONS } from './ChapterAnimationConfigs'

const CUSTOM_ANIMATIONS: Record<string, () => Promise<{ default: React.ComponentType }>> = {
  '00': () => import('./Chapter00Animation'),
  '03': () => import('./Chapter03Animation'),
  '12': () => import('./Chapter12Animation'),
  '13': () => import('./Chapter13Animation'),
  '14': () => import('./Chapter14Animation'),
}

const LazyComponents: Record<string, React.LazyExoticComponent<React.ComponentType>> = {}
for (const [id, imp] of Object.entries(CUSTOM_ANIMATIONS)) {
  LazyComponents[id] = lazy(imp)
}

let ConfigurableModule: React.ComponentType<{ config: unknown }> | null = null
function getConfigurable() {
  if (!ConfigurableModule) {
    ConfigurableModule = lazy(() => import('./ConfigurableAnimation')) as unknown as React.ComponentType<{ config: unknown }>
  }
  return ConfigurableModule
}

export default function AnimationLoader({ chapterId }: { chapterId: string }) {
  const LazyComp = LazyComponents[chapterId]

  if (LazyComp) {
    return (
      <Suspense fallback={<LoadingFallback />}>
        <LazyComp />
      </Suspense>
    )
  }

  const config = CHAPTER_ANIMATIONS[chapterId]
  if (config) {
    const ConfComp = getConfigurable()
    return (
      <Suspense fallback={<LoadingFallback />}>
        <ConfComp config={config} />
      </Suspense>
    )
  }

  return <PlaceholderAnimation chapterId={chapterId} />
}

function LoadingFallback() {
  return (
    <AnimationCanvas controls={false}>
      <rect x="0" y="0" width="960" height="540" fill="#f9fafb" />
      <text x="480" y="270" textAnchor="middle" fill="#9ca3af" fontSize={16} fontFamily="system-ui, sans-serif">
        加载动画中…
      </text>
    </AnimationCanvas>
  )
}

function PlaceholderAnimation({ chapterId }: { chapterId: string }) {
  return (
    <AnimationCanvas controls={false} duration={4000}>
      <rect x="0" y="0" width="960" height="540" fill="#f3f4f6" />
      <text x="480" y="260" textAnchor="middle" fill="#9ca3af"
        fontSize={18} fontFamily="system-ui, sans-serif">
        {chapterId}
      </text>
      <text x="480" y="290" textAnchor="middle" fill="#d1d5db"
        fontSize={14} fontFamily="system-ui, sans-serif">
        暂无可交互动画
      </text>
    </AnimationCanvas>
  )
}
