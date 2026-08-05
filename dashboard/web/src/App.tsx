import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import CockpitPage from './pages/CockpitPage'
import ChapterPage from './pages/ChapterPage'
import { RunCoordinatorProvider } from './run/RunCoordinator'

/* 路由级过渡：轻微上浮 + 淡入，避免全屏闪烁 */
const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1]

export default function App() {
  const location = useLocation()
  const reduce = useReducedMotion()
  const transition = reduce
    ? { duration: 0 }
    : { duration: 0.35, ease: EASE_OUT_EXPO }

  return (
    <RunCoordinatorProvider>
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={transition}
        >
          <Routes location={location}>
            <Route path="/" element={<CockpitPage />} />
            <Route path="/chapter/:id" element={<ChapterPage />} />
          </Routes>
        </motion.div>
      </AnimatePresence>
    </RunCoordinatorProvider>
  )
}
