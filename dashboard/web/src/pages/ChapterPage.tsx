import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, BookOpen, Play, FileText,
  PanelRightOpen, X,
  ChevronDown, ChevronRight, Maximize2, Terminal
} from 'lucide-react'
import type { ChapterDto, StageSummary, RunRecord } from '../api/types'
import { getChapter, getCourseSummary, listRuns } from '../api/client'
import CourseTree from '../components/course/CourseTree'
import MarkdownView from '../components/course/MarkdownView'
import ProgressPanel from '../components/course/ProgressPanel'
import RunnerPanel from '../components/runner/RunnerPanel'
import InlineCourseAnimation from '../animations/InlineCourseAnimation'
import { animationsForChapter } from '../animations/chapters/ChapterAnimationConfigs'
import ResultsView from '../components/course/ResultsView'

type Tab = 'learn' | 'animation' | 'results'

export default function ChapterPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [chapter, setChapter] = useState<ChapterDto | null>(null)
  const [stages, setStages] = useState<StageSummary[]>([])
  const [runs, setRuns] = useState<RunRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('learn')
  const [runnerCollapsed, setRunnerCollapsed] = useState(false)
  const [progressKey, setProgressKey] = useState(0)

  const [s1Open, setS1Open] = useState(true)
  const [s3Open, setS3Open] = useState(true)

  const [selectedAnimation, setSelectedAnimation] = useState<string | null>(null)
  const [pendingAnimation, setPendingAnimation] = useState<string | null>(null)

  useEffect(() => {
    const checkWidth = () => {
      setRunnerCollapsed(window.innerWidth < 1180)
    }
    checkWidth()
    window.addEventListener('resize', checkWidth)
    return () => window.removeEventListener('resize', checkWidth)
  }, [])

  useEffect(() => {
    getCourseSummary().then((s) => setStages(s.stages)).catch(() => {})
  }, [])

  const loadChapter = useCallback(async (chapterId: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getChapter(chapterId)
      setChapter(data)
      setActiveTab('learn')
      const runList = await listRuns(chapterId)
      setRuns(runList)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载章节失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (id) loadChapter(id)
    if (id) localStorage.setItem('upkie_last_chapter', id)
  }, [id, loadChapter])

  const handleSelectChapter = useCallback((chapterId: string) => {
    navigate(`/chapter/${chapterId}`)
  }, [navigate])

  const handleProgressUpdate = useCallback(() => {
    if (id) {
      getChapter(id).then((data) => {
        setChapter(data);
        setStages((prev) =>
          prev.map((stage) => ({
            ...stage,
            chapters: stage.chapters.map((ch) =>
              ch.id === id
                ? { ...ch, reading_complete: data.reading_complete, reading_percent: data.reading_percent, completed: data.completed }
                : ch,
            ),
          })),
        );
      }).catch(() => {});
      getCourseSummary().then((s) => setStages(s.stages)).catch(() => {});
    }
  }, [id])

  const handleExperimentComplete = useCallback(() => {
    if (id) {
      Promise.all([getChapter(id), listRuns(id), getCourseSummary()])
        .then(([data, runList, summary]) => {
          setChapter(data)
          setRuns(runList)
          setStages(summary.stages)
          setProgressKey((key) => key + 1)
        })
        .catch(() => {})
    }
  }, [id])

  const handleRerunRequest = useCallback(() => {
    setS1Open(true)
    setRunnerCollapsed(false)
  }, [])

  const allChapters = useMemo(
    () => stages.flatMap((s) => s.chapters),
    [stages]
  )

  const chapterAnimations = useMemo(
    () => chapter ? animationsForChapter(chapter.id) : [],
    [chapter],
  )

  const jumpToAnimation = useCallback((animationId: string) => {
    setPendingAnimation(animationId)
    setActiveTab('learn')
  }, [])

  useEffect(() => {
    if (activeTab !== 'learn' || !pendingAnimation) return
    const timer = window.setTimeout(() => {
      document.getElementById(`upkie-animation-${pendingAnimation}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setPendingAnimation(null)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [activeTab, pendingAnimation])

  const currentIndex = useMemo(
    () => allChapters.findIndex((c) => c.id === id),
    [allChapters, id]
  )

  const prevChapter = useMemo(
    () => (currentIndex > 0 ? allChapters[currentIndex - 1] : null),
    [allChapters, currentIndex]
  )

  const nextChapter = useMemo(
    () => (currentIndex >= 0 && currentIndex < allChapters.length - 1 ? allChapters[currentIndex + 1] : null),
    [allChapters, currentIndex]
  )

  if (loading) {
    return (
      <div className="loading-spinner" style={{ height: '100vh' }}>
        <div className="spinner" />
        <p>加载章节...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-card" style={{ height: '100vh' }}>
        <h3>加载失败</h3>
        <p>{error}</p>
        <button className="btn btn-outline mt-4" onClick={() => id && loadChapter(id)}>
          重试
        </button>
      </div>
    )
  }

  if (!chapter) {
    return (
      <div className="empty-state" style={{ height: '100vh' }}>
        <BookOpen />
        <p>未找到章节</p>
      </div>
    )
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'learn':
        return (
          <motion.div
            key="learn"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="tab-content-inner"
          >
            <div className="markdown-content mb-6">
              <MarkdownView content={chapter.content} chapterId={chapter.id} onExperimentComplete={handleExperimentComplete} />
            </div>
            <ProgressPanel
              key={progressKey}
              chapterId={chapter.id}
              readingPercent={chapter.reading_percent}
              readingComplete={chapter.reading_complete}
              selfCheckIds={chapter.self_check_ids}
              selfCheckItems={chapter.self_check_items}
              experimentAccepted={chapter.experiment_accepted}
              completed={chapter.completed}
              onProgressUpdate={handleProgressUpdate}
            />
            <div className="chapter-nav">
              {prevChapter ? (
                <Link to={`/chapter/${prevChapter.id}`} className="chapter-nav-btn">
                  <div className="nav-direction">← 上一节</div>
                  <div className="nav-title">{prevChapter.title}</div>
                </Link>
              ) : <div />}
              {nextChapter ? (
                <Link to={`/chapter/${nextChapter.id}`} className="chapter-nav-btn next">
                  <div className="nav-direction">下一节 →</div>
                  <div className="nav-title">{nextChapter.title}</div>
                </Link>
              ) : <div />}
            </div>
          </motion.div>
        )
      case 'animation':
        return (
          <motion.div
            key="animation"
            className="tab-content-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="animation-index">
              <h2>本章动画索引</h2>
              {chapterAnimations.map((animation) => (
                <div key={animation.id} className="animation-list-item">
                  <button type="button" className="animation-index-link" onClick={() => jumpToAnimation(animation.id)}>
                    <Play size={15} />
                    <span>{animation.title}</span>
                  </button>
                  <button
                    type="button"
                    className="icon-button"
                    title="大屏重播"
                    onClick={() => setSelectedAnimation(animation.id)}
                  >
                    <Maximize2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )
      case 'results':
        return (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <ResultsView
              chapterId={chapter.id}
              artifacts={chapter.artifacts}
              runs={runs}
              onRerun={handleRerunRequest}
            />
          </motion.div>
        )
    }
  }

  const sidebarTabs: { id: Tab; label: string; icon: typeof BookOpen }[] = [
    { id: 'learn', label: '学习', icon: BookOpen },
    { id: 'animation', label: '动画', icon: Play },
    { id: 'results', label: '结果', icon: FileText },
  ]

  return (
    <>
      <motion.div
        className="chapter-layout"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        <aside className="chapter-tree">
          <div className="chapter-tree-inner">
            <Link to="/" className="back-home">
              <ArrowLeft size={16} />
              返回主页
            </Link>

            <CourseTree
              stages={stages}
              currentChapterId={chapter.id}
              onSelectChapter={handleSelectChapter}
            />

            <div className="sidebar-tabs">
              {sidebarTabs.map((tab) => (
                <button
                  key={tab.id}
                  className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <tab.icon size={15} />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="chapter-main">
          <div className="tab-content">
            <AnimatePresence mode="wait">
              {renderTabContent()}
            </AnimatePresence>
          </div>
        </main>

        <aside className={`chapter-runner ${runnerCollapsed ? 'collapsed' : ''}`}>
          <button
            type="button"
            className="runner-toggle"
            onClick={() => setRunnerCollapsed(true)}
            aria-label="收起实验面板"
            title="收起实验面板"
          >
            <X size={16} />
          </button>
          <div className="runner-content">
            <div className={`runner-section-block ${s1Open ? 'open' : ''}`}>
              <button
                className="runner-section-title w-full flex items-center gap-2 border-b-0 mb-0"
                onClick={() => setS1Open((v) => !v)}
              >
                <Terminal size={14} />
                <span>运行任务</span>
                <span className="ml-auto">{s1Open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
              </button>
              <div className={`runner-section-body ${s1Open ? '' : 'collapsed'}`}>
                <RunnerPanel
                  chapterId={chapter.id}
                  checkpoints={chapter.checkpoints}
                  onExperimentComplete={handleExperimentComplete}
                />
              </div>
            </div>

            <div className={`runner-section-block ${s3Open ? 'open' : ''}`}>
              <button
                className="runner-section-title w-full flex items-center gap-2 border-b-0 mb-0"
                onClick={() => setS3Open((v) => !v)}
              >
                <FileText size={14} />
                <span>结果</span>
                <span className="ml-auto">{s3Open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
              </button>
              <div className={`runner-section-body ${s3Open ? '' : 'collapsed'}`}>
                <ResultsView
                  chapterId={chapter.id}
                  artifacts={chapter.artifacts}
                  runs={runs}
                  onRerun={handleRerunRequest}
                />
              </div>
            </div>
          </div>
        </aside>
      </motion.div>

      {runnerCollapsed && (
        <button
          className="runner-float-toggle"
          onClick={() => setRunnerCollapsed(false)}
          aria-label="展开实验面板"
          title="展开实验面板"
        >
          <PanelRightOpen size={20} />
        </button>
      )}

      {selectedAnimation && (
        <div className="animation-modal-overlay" onClick={() => setSelectedAnimation(null)}>
          <div className="animation-modal" onClick={(e) => e.stopPropagation()}>
            <button className="animation-modal-close" onClick={() => setSelectedAnimation(null)}>
              <X size={20} />
            </button>
            <div className="animation-modal-body">
              <InlineCourseAnimation animationId={selectedAnimation} large />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
