import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, useMotionValue, useTransform, animate, useReducedMotion, type Variants } from 'framer-motion'
import {
  Award,
  BookOpen,
  Box,
  Brain,
  ChevronRight,
  Cpu,
  Eye,
  Gauge,
  Layout,
  TrendingUp,
  Wrench,
} from 'lucide-react'
import type { CourseSummary } from '../api/types'
import { getCourseSummary, getHealth } from '../api/client'
import UpkieModel from '../three/UpkieModel'

/* 数字冲刺 + 卡片错峰共用缓动 */
const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1]

/* 卡片入场：容器错峰，子项上浮淡入 */
const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
}
const staggerItem: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT_EXPO } },
}

const stageIcons: Record<string, typeof Layout> = {
  '0': BookOpen,
  '1': Box,
  '2': Gauge,
  '3': TrendingUp,
  '4': Brain,
  '5': Eye,
  '6': Wrench,
  '7': Award,
  H: Cpu,
}

export default function CockpitPage() {
  const [summary, setSummary] = useState<CourseSummary | null>(null)
  const [health, setHealth] = useState<'checking' | 'ready' | 'degraded' | 'offline'>('checking')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastChapter, setLastChapter] = useState<string | null>(
    () => localStorage.getItem('upkie_last_chapter')
  )
  const navigate = useNavigate()
  const reduce = useReducedMotion()

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [s, h] = await Promise.all([
          getCourseSummary(),
          getHealth().catch(() => null),
        ])
        if (cancelled) return
        setSummary(s)
        setHealth(h?.status ?? 'offline')
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const refresh = () => {
      getCourseSummary()
        .then((s) => setSummary(s))
        .catch(() => {});
    };
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, []);


  const readingDone = useMemo(() =>
    summary
      ? summary.stages.reduce((sum, s) => sum + (s.chapters?.filter((c) => c.reading_complete).length ?? 0), 0)
      : 0,
    [summary]
  )

  const pct = useMemo(() => {
    if (!summary || summary.total_chapters === 0) return 0
    const readWeight = (readingDone / summary.total_chapters) * 50
    const expWeight = (summary.completed_chapters / summary.total_chapters) * 50
    return Math.round(readWeight + expWeight)
  }, [summary, readingDone])

  const readingPct = useMemo(() =>
    summary
      ? (summary.total_chapters > 0 ? Math.round((readingDone / summary.total_chapters) * 50) : 0)
      : 0,
    [summary, readingDone]
  )

  const expPct = useMemo(() =>
    summary
      ? (summary.total_chapters > 0 ? Math.round((summary.completed_chapters / summary.total_chapters) * 50) : 0)
      : 0,
    [summary]
  )

  const lastChapterInfo = useMemo(() => {
    if (!lastChapter || !summary) return null
    for (const stage of summary.stages) {
      for (const ch of stage.chapters ?? []) {
        if (ch.id === lastChapter) return { stageTitle: stage.title, chapterTitle: ch.title }
      }
    }
    return { stageTitle: lastChapter, chapterTitle: '' }
  }, [lastChapter, summary])

  const count = useMotionValue(0)
  const rounded = useTransform(count, (v) => Math.round(v))
  useEffect(() => {
    if (pct > 0) {
      // easeOutExpo：数字先快后慢"冲刺"到目标
      const ctrl = animate(count, pct, { duration: reduce ? 0 : 1.6, ease: EASE_OUT_EXPO })
      return () => ctrl.stop()
    }
  }, [pct, reduce])

  const totalCh = summary?.total_chapters ?? 0
  const totalCount = useMotionValue(0)
  const totalRounded = useTransform(totalCount, (v) => Math.round(v))
  useEffect(() => {
    if (totalCh > 0) {
      const ctrl = animate(totalCount, totalCh, { duration: reduce ? 0 : 1.3, ease: EASE_OUT_EXPO })
      return () => ctrl.stop()
    }
  }, [totalCh, reduce])

  const compCh = summary?.completed_chapters ?? 0
  const completedCount = useMotionValue(0)
  const completedRounded = useTransform(completedCount, (v) => Math.round(v))
  useEffect(() => {
    if (compCh > 0) {
      const ctrl = animate(completedCount, compCh, { duration: reduce ? 0 : 1.3, ease: EASE_OUT_EXPO })
      return () => ctrl.stop()
    }
  }, [compCh, reduce])

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner" />
        加载课程概要...
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-card">
        <h3>加载失败</h3>
        <p>{error}</p>
        <button className="btn btn-outline mt-4" onClick={() => window.location.reload()}>
          重试
        </button>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="empty-state">
        <BookOpen />
        <p>暂无课程数据</p>
      </div>
    )
  }

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className="page-header">
        <h1>{summary.title}</h1>
        <p>
          版本 {summary.version} &middot;{' '}
          {summary.completed_chapters}/{summary.total_chapters} 章节完成
        </p>
      </div>

      <motion.div
        className="stats-grid"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        <motion.div className="stat-card" variants={staggerItem}>
          <span className="stat-label">总章节</span>
          <span className="stat-value"><motion.span>{totalRounded}</motion.span></span>
        </motion.div>
        <motion.div className="stat-card" variants={staggerItem}>
          <span className="stat-label">已完成</span>
          <span className="stat-value"><motion.span>{completedRounded}</motion.span></span>
        </motion.div>
        <motion.div className="stat-card" variants={staggerItem}>
          <span className="stat-label">环境状态</span>
          <div className="flex items-center gap-2" style={{ marginTop: 4 }}>
            <span className={`env-dot ${health}`} />
            <span className="stat-value" style={{ fontSize: 16 }}>
              {health === 'ready' ? '就绪' : health === 'degraded' ? '部分缺失' : health === 'offline' ? '离线' : '检查中...'}
            </span>
          </div>
        </motion.div>
      </motion.div>

      {(lastChapter || summary.next_chapter) && (() => {
        const continueId = lastChapter || summary.next_chapter?.id;
        const continueTitle = lastChapterInfo
          ? `${lastChapterInfo.stageTitle} — ${lastChapterInfo.chapterTitle}`
          : lastChapter
            ? `上次学习：章节 ${lastChapter}`
            : `${summary.next_chapter!.stage_title} — ${summary.next_chapter!.title}`;
        return (
          <motion.div
            className="next-chapter-card pulse-glow"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE_OUT_EXPO, delay: reduce ? 0 : 0.12 }}
          >
            <div className="next-info">
              <span className="next-label">{lastChapter ? '继续学习（上次位置）' : '继续学习'}</span>
              <span className="next-title">{continueTitle}</span>
            </div>
            <Link to={`/chapter/${continueId}`} className="next-link">
              开始 <ChevronRight size={16} />
            </Link>
          </motion.div>
        );
      })()}

      <div className="section-title">总体进度</div>

      <motion.div
        className="overall-progress mb-6"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: EASE_OUT_EXPO, delay: reduce ? 0 : 0.2 }}
      >
        <div className="overall-bar">
          <div className="overall-fill overall-fill-done" style={{ width: `${expPct}%` }} />
          <div className="overall-fill overall-fill-read" style={{ left: `${expPct}%`, width: `${Math.max(0, pct - expPct)}%` }} />
        </div>
        <div className="overall-stats">
          <span className="text-sm text-gray-600">
            实验 <strong className="text-green-600">{summary.completed_chapters}</strong>
            {' · '}阅读 <strong className="text-emerald-500">{readingDone}</strong>
            {' · '}共 <strong>{summary.total_chapters}</strong> 关
          </span>
          <span className="text-sm font-bold text-gray-700"><motion.span>{rounded}</motion.span>%</span>
        </div>
      </motion.div>

      <div className="model-card">
        <div className="model-card-header">
          <span className="model-card-title">Upkie 双轮足机器人</span>
          <span className="model-card-hint">拖拽旋转 · L 键标签 · 重置相机</span>
        </div>
        <UpkieModel height="340px" />
      </div>

      <div className="section-title">课程阶段</div>

      <motion.div
        className="stage-sections"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        {summary.stages.map((stage) => {
          const Icon = stageIcons[stage.id] || Layout
          const done = stage.completed
          const read = stage.chapters?.filter((c) => c.reading_complete).length ?? 0
          const total = stage.total
          const donePct = total > 0 ? Math.round((done / total) * 50) : 0
          const readPct = total > 0 ? Math.round((read / total) * 50) : 0
          const stagePct = donePct + readPct
          const firstId = stage.chapters?.[0]?.id

          return (
            <motion.div
              key={stage.id}
              className="stage-card-clickable"
              variants={staggerItem}
              onClick={() => firstId && navigate(`/chapter/${firstId}`)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon size={18} className="text-gray-500" />
                  <h3 className="text-base font-semibold text-gray-800">{stage.title}</h3>
                  <span className="badge gray">{stage.project}</span>
                </div>
                <ChevronRight size={16} className="text-gray-300" />
              </div>
              <div className="overall-bar stage-bar">
                <div className="overall-fill overall-fill-done" style={{ width: `${donePct}%` }} />
                <div className="overall-fill overall-fill-read" style={{ left: `${donePct}%`, width: `${Math.max(0, stagePct - donePct)}%` }} />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-400">
                  阅 {read} · 验 {done} / {total}
                </span>
                <span className="text-xs font-medium text-gray-500">{stagePct}%</span>
              </div>
            </motion.div>
          )
        })}
      </motion.div>
    </motion.div>
  )
}
