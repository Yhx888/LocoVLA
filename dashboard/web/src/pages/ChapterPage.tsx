import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import {
  ArrowLeft, BookOpen, Play, FileText,
  PanelRightOpen, X,
  ChevronDown, ChevronRight, Maximize2, Terminal, Sparkles
} from 'lucide-react'
import type { ChapterDto, StageSummary, RunRecord } from '../api/types'
import { getChapter, getCourseSummary, listRuns } from '../api/client'
import CourseTree from '../components/course/CourseTree'
import MarkdownView from '../components/course/MarkdownView'
import ProgressPanel from '../components/course/ProgressPanel'
import RunnerPanel from '../components/runner/RunnerPanel'
import InlineCourseAnimation from '../animations/InlineCourseAnimation'
import AnimationLoader from '../animations/chapters/AnimationLoader'
import { animationsForChapter, CHAPTER_ANIMATIONS } from '../animations/chapters/ChapterAnimationConfigs'
import ResultsView from '../components/course/ResultsView'
import AiAssistantPanel, { type ExplainRequest } from '../components/ai/AiAssistantPanel'

type Tab = 'learn' | 'animation' | 'results'

/* 内容入场统一缓动：expo 快出缓停 */
const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1]

// 用选中文本在原始 markdown 中定位，取前后各 500 字作为 AI 解释的上下文
function extractContext(content: string, selectedText: string): string {
  const probe = selectedText.slice(0, 60).trim()
  if (!probe) return ''
  const index = content.indexOf(probe)
  if (index < 0) return ''
  const start = Math.max(0, index - 500)
  const end = Math.min(content.length, index + selectedText.length + 500)
  return content.slice(start, end)
}

interface SelectionPopup {
  x: number
  y: number
  text: string
}

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
  const [aiOpen, setAiOpen] = useState(false)

  const [selectedAnimation, setSelectedAnimation] = useState<string | null>(null)
  const [pendingAnimation, setPendingAnimation] = useState<string | null>(null)
  const reduce = useReducedMotion()

  const [selectionPopup, setSelectionPopup] = useState<SelectionPopup | null>(null)
  const [explainRequest, setExplainRequest] = useState<ExplainRequest | null>(null)
  const markdownRef = useRef<HTMLDivElement>(null)

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

  // 教程正文圈选后浮出「AI 解释」按钮
  const handleTextSelection = useCallback(() => {
    window.setTimeout(() => {
      const selection = window.getSelection()
      const text = selection?.toString().trim() ?? ''
      if (!selection || selection.isCollapsed || text.length < 2 || text.length > 2000) {
        setSelectionPopup(null)
        return
      }
      // 只响应教程正文内的选区
      const anchor = selection.anchorNode
      if (!anchor || !markdownRef.current?.contains(anchor)) {
        setSelectionPopup(null)
        return
      }
      const rect = selection.getRangeAt(0).getBoundingClientRect()
      setSelectionPopup({
        x: rect.left + rect.width / 2,
        y: rect.top,
        text,
      })
    }, 0)
  }, [])

  const handleExplainSelection = useCallback(() => {
    if (!selectionPopup || !chapter) return
    const context = extractContext(chapter.content, selectionPopup.text)
    setExplainRequest({ text: selectionPopup.text, context, nonce: Date.now() })
    setSelectionPopup(null)
    setAiOpen(true)
    setRunnerCollapsed(false)
    window.getSelection()?.removeAllRanges()
  }, [selectionPopup, chapter])

  // 点击页面其他位置或滚动时关闭圈选按钮
  useEffect(() => {
    if (!selectionPopup) return
    const dismiss = () => setSelectionPopup(null)
    window.addEventListener('scroll', dismiss, true)
    return () => window.removeEventListener('scroll', dismiss, true)
  }, [selectionPopup])

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
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={reduce ? { duration: 0 } : { duration: 0.3, ease: EASE_OUT_EXPO }}
            className="tab-content-inner"
          >
            <div className="markdown-content mb-6" ref={markdownRef} onMouseUp={handleTextSelection}>
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
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={reduce ? { duration: 0 } : { duration: 0.25, ease: EASE_OUT_EXPO }}
          >
            {CHAPTER_ANIMATIONS[chapter.id] && (
              <div className="featured-animation">
                <h2>本章大屏动画</h2>
                <p className="featured-animation-hint">播放 / 暂停 / 步进 / 重置 · 拖动滑块实验参数</p>
                <AnimationLoader chapterId={chapter.id} />
              </div>
            )}
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
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={reduce ? { duration: 0 } : { duration: 0.3, ease: EASE_OUT_EXPO }}
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
                  experimentAccepted={chapter.experiment_accepted}
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

            <div className={`runner-section-block ${aiOpen ? 'open' : ''}`}>
              <button
                className="runner-section-title w-full flex items-center gap-2 border-b-0 mb-0"
                onClick={() => setAiOpen((v) => !v)}
              >
                <Sparkles size={14} />
                <span>AI 助教</span>
                <span className="ml-auto">{aiOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
              </button>
              <div className={`runner-section-body ${aiOpen ? '' : 'collapsed'}`}>
                <AiAssistantPanel
                  chapterId={chapter.id}
                  chapterTitle={chapter.title}
                  explainRequest={explainRequest}
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

      {selectionPopup && (
        <button
          type="button"
          className="selection-explain-btn"
          style={{ left: selectionPopup.x, top: selectionPopup.y }}
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleExplainSelection}
        >
          <Sparkles size={13} />
          AI 解释
        </button>
      )}

      <AnimatePresence>
        {selectedAnimation && (
          <motion.div
            key="overlay"
            className="animation-modal-overlay"
            onClick={() => setSelectedAnimation(null)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.2, ease: 'easeIn' } }}
            transition={reduce ? { duration: 0 } : { duration: 0.25, ease: 'easeOut' }}
          >
            <motion.div
              key="modal"
              className="animation-modal"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 28, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.98, transition: { duration: 0.2, ease: 'easeIn' } }}
              /* 内容比背景晚 0.06s 入场：先见背景渐暗，再看内容上浮放大 */
              transition={reduce ? { duration: 0 } : { duration: 0.34, ease: EASE_OUT_EXPO, delay: 0.06 }}
            >
              <button className="animation-modal-close" onClick={() => setSelectedAnimation(null)}>
                <X size={20} />
              </button>
              <div className="animation-modal-body">
                <InlineCourseAnimation animationId={selectedAnimation} large />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
