import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import CockpitPage from './pages/CockpitPage'
import ChapterPage from './pages/ChapterPage'
import { RunCoordinatorProvider } from './run/RunCoordinator'

export default function App() {
  const location = useLocation()

  return (
    <RunCoordinatorProvider>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<CockpitPage />} />
          <Route path="/chapter/:id" element={<ChapterPage />} />
        </Routes>
      </AnimatePresence>
    </RunCoordinatorProvider>
  )
}
