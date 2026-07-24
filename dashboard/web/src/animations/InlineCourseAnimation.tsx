import { useEffect, useId, useRef, useState } from 'react';
import { Play, RotateCcw, TriangleAlert } from 'lucide-react';
import {
  COURSE_ANIMATION_BY_ID,
  type AnimationItem,
  type CourseAnimationEntry,
} from './chapters/ChapterAnimationConfigs';
import { useRunCoordinator } from '../run/RunCoordinator';

const ARTIFACT_BASE = '/api/artifacts/';
const MOTION_QUERY = '(prefers-reduced-motion: reduce)';

export default function InlineCourseAnimation({ animationId, large = false }: {
  animationId: string;
  large?: boolean;
}) {
  const entry = COURSE_ANIMATION_BY_ID.get(animationId);
  const rootRef = useRef<HTMLElement>(null);
  const playedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const instanceId = useId().replace(/:/g, '');
  const markerId = `inline-arrow-${instanceId}`;
  const [reducedMotion, setReducedMotion] = useState(
    () => window.matchMedia?.(MOTION_QUERY).matches ?? false,
  );
  const [playing, setPlaying] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [replayKey, setReplayKey] = useState(0);

  useEffect(() => {
    const media = window.matchMedia?.(MOTION_QUERY);
    if (!media) return;
    const handleChange = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches);
      if (event.matches) {
        setPlaying(false);
        setCompleted(true);
        if (timerRef.current) clearTimeout(timerRef.current);
      }
    };
    media.addEventListener?.('change', handleChange);
    return () => media.removeEventListener?.('change', handleChange);
  }, []);

  useEffect(() => {
    if (!entry || reducedMotion || !rootRef.current) return;
    const observer = new IntersectionObserver(([observed]) => {
      if (observed.isIntersecting && !playedRef.current) {
        playedRef.current = true;
        setCompleted(false);
        setPlaying(true);
        timerRef.current = setTimeout(() => {
          setPlaying(false);
          setCompleted(true);
        }, 3600);
      } else if (!observed.isIntersecting) {
        setPlaying(false);
        if (timerRef.current) clearTimeout(timerRef.current);
      }
    }, { threshold: 0.35 });
    observer.observe(rootRef.current);
    return () => {
      observer.disconnect();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [entry, reducedMotion, replayKey]);

  if (!entry) return null;

  const replay = () => {
    if (reducedMotion) return;
    playedRef.current = false;
    setPlaying(false);
    setCompleted(false);
    setReplayKey((key) => key + 1);
  };

  return (
    <section
      ref={rootRef}
      id={large ? undefined : entry.anchor}
      className={`inline-course-animation ${large ? 'is-large' : ''}`}
      data-testid="inline-animation"
      data-playing={String(playing)}
      data-motion={reducedMotion ? 'reduced' : 'full'}
      aria-label={entry.title}
    >
      <header className="inline-animation-header">
        <div>
          <span className="inline-animation-kicker">{categoryLabel(entry)}</span>
          <h3>{entry.title}</h3>
        </div>
        <button type="button" className="icon-button" onClick={replay} title="重播动画" disabled={reducedMotion}>
          <RotateCcw size={16} />
        </button>
      </header>
      {entry.conceptualOnly && <p className="concept-notice">概念示意 · 规划中章节，不计入验收证据</p>}
      <div className="inline-animation-stage" key={replayKey}>
        <InlineScene
          entry={entry}
          playing={playing}
          completed={completed}
          reducedMotion={reducedMotion}
          markerId={markerId}
        />
      </div>
      <p className="inline-animation-source">来源：{entry.evidence.description}</p>
    </section>
  );
}

function categoryLabel(entry: CourseAnimationEntry): string {
  return {
    intuition: '直觉机制',
    parameter: '公式与参数',
    comparison: '正确 / 故障',
    evidence: '固定 seed 证据',
  }[entry.category];
}

function InlineScene({ entry, playing, completed, reducedMotion, markerId }: {
  entry: CourseAnimationEntry;
  playing: boolean;
  completed: boolean;
  reducedMotion: boolean;
  markerId: string;
}) {
  if (entry.scene === 'parameter') return <ParameterScene entry={entry} />;
  if (entry.scene === 'comparison') {
    return <ComparisonScene entry={entry} playing={playing} completed={completed} reducedMotion={reducedMotion} markerId={markerId} />;
  }
  if (entry.scene === 'evidence') return <EvidenceScene entry={entry} />;
  return <MechanismScene entry={entry} playing={playing} completed={completed} reducedMotion={reducedMotion} markerId={markerId} />;
}

function ArrowMarker({ id, color = '#2563eb' }: { id: string; color?: string }) {
  return (
    <defs>
      <marker id={id} markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
        <path d="M0,0 L8,4 L0,8 Z" fill={color} />
      </marker>
    </defs>
  );
}

function SceneHeading({ entry }: { entry: CourseAnimationEntry }) {
  return (
    <>
      <text x="380" y="26" textAnchor="middle" className="compare-title">{entry.chapterConfig.title}</text>
      <text x="380" y="47" textAnchor="middle" className="anim-subtext">
        {compact(entry.chapterConfig.subtitle ?? '本章核心机制', 42)}
      </text>
    </>
  );
}

function MechanismScene({ entry, playing, completed, reducedMotion, markerId }: {
  entry: CourseAnimationEntry;
  playing: boolean;
  completed: boolean;
  reducedMotion: boolean;
  markerId: string;
}) {
  const labels = mechanismLabels(entry);
  const marker = `url(#${markerId})`;
  const items = itemLabels(entry);

  return (
    <svg data-testid="mechanism-scene" viewBox="0 0 760 260" role="img" aria-label={`${entry.chapterConfig.title} 机制示意`}>
      <ArrowMarker id={markerId} />
      <SceneHeading entry={entry} />
      <MechanismGeometry
        entry={entry}
        labels={labels}
        items={items}
        marker={marker}
        playing={playing}
        completed={completed}
        reducedMotion={reducedMotion}
      />
    </svg>
  );
}

function MechanismGeometry({ entry, labels, items, marker, playing, completed, reducedMotion }: {
  entry: CourseAnimationEntry;
  labels: [string, string, string];
  items: string[];
  marker: string;
  playing: boolean;
  completed: boolean;
  reducedMotion: boolean;
}) {
  const showFinalFrame = reducedMotion || completed;
  switch (entry.chapterConfig.scene) {
    case 'signalPlot':
      return (
        <g>
          <line x1="70" y1="215" x2="700" y2="215" className="parameter-axis" />
          <line x1="70" y1="70" x2="70" y2="215" className="parameter-axis" />
          <path d="M70 170 C130 70 190 70 250 170 S370 270 430 170 S550 70 610 170 S670 220 700 165" fill="none" stroke="#2563eb" strokeWidth="4" />
          <path d="M70 175 C170 140 250 120 340 112 S540 90 700 86" fill="none" stroke="#0f766e" strokeWidth="4" strokeDasharray="8 6" />
          <text x="205" y="88" className="anim-subtext">{items[0] ?? labels[0]}</text>
          <text x="520" y="78" className="anim-subtext">{items[1] ?? labels[2]}</text>
          <circle data-testid="motion-token" cx={showFinalFrame ? 392 : 92} cy="166" r="7" className={`anim-pulse ${playing ? 'is-playing' : ''}`} />
        </g>
      );
    case 'formulaExplorer': {
      const formula = entry.chapterConfig.items.find((item) => item.type === 'formula')?.text ?? labels[1];
      return (
        <g>
          <rect x="70" y="68" width="620" height="56" rx="6" className="anim-node decide" />
          <text x="380" y="102" textAnchor="middle">{compact(formula, 48)}</text>
          <line x1="170" y1="214" x2="330" y2="214" className="parameter-axis" markerEnd={marker} />
          <line x1="170" y1="214" x2="170" y2="142" className="parameter-axis" markerEnd={marker} />
          <line x1="170" y1="214" x2="286" y2="154" stroke="#0f766e" strokeWidth="5" markerEnd={marker} />
          <circle cx="550" cy="178" r="46" fill="#eff6ff" stroke="#2563eb" strokeWidth="3" />
          <text x="550" y="174" textAnchor="middle">{labels[2]}</text>
          <text x="550" y="197" textAnchor="middle" className="anim-subtext">代入即可验证</text>
        </g>
      );
    }
    case 'dataPipeline':
      return (
        <g>
          <ConfiguredGraph entry={entry} marker={marker} fallbackLabels={items.length ? items : labels} kind="stage" />
          <circle data-testid="motion-token" cx={showFinalFrame ? 382 : 82} cy="65" r="7" className={`anim-pulse ${playing ? 'is-playing' : ''}`} />
          <text x="380" y="252" textAnchor="middle" className="anim-subtext">数据逐级变换，最终形成可复核产物</text>
        </g>
      );
    case 'flowchart':
      return (
        <g>
          <ConfiguredGraph entry={entry} marker={marker} fallbackLabels={items.length ? items : labels} kind="stage" />
        </g>
      );
    case 'stateFlow':
      return (
        <g>
          <ConfiguredGraph entry={entry} marker={marker} fallbackLabels={items.length ? items : labels} kind="node" />
        </g>
      );
    case 'architecture': {
      const layers = (items.length ? items : labels).slice(0, 4);
      return (
        <g>
          {layers.map((label, index) => {
            const width = 520 - index * 58;
            const x = (760 - width) / 2;
            const y = 66 + index * 43;
            return (
              <g key={`${label}-${index}`}>
                <rect x={x} y={y} width={width} height="32" rx="5" fill={index % 2 ? '#ecfdf5' : '#eff6ff'} stroke={index % 2 ? '#0f766e' : '#2563eb'} strokeWidth="2" />
                <text x="380" y={y + 21} textAnchor="middle">{label}</text>
                {index < layers.length - 1 && <line x1="380" y1={y + 32} x2="380" y2={y + 41} className="anim-link" markerEnd={marker} />}
              </g>
            );
          })}
        </g>
      );
    }
    case 'controlLoop':
      return (
        <g>
          <circle cx="82" cy="122" r="28" fill="#eff6ff" stroke="#2563eb" strokeWidth="3" />
          <rect x="164" y="88" width="150" height="68" rx="6" className="anim-node decide" />
          <rect x="392" y="88" width="150" height="68" rx="6" className="anim-node act" />
          <rect x="598" y="88" width="120" height="68" rx="6" className="anim-node observe" />
          <text x="82" y="127" textAnchor="middle">目标</text>
          <text x="239" y="118" textAnchor="middle">{labels[1]}</text>
          <text x="239" y="141" textAnchor="middle" className="anim-subtext">误差 → 控制量</text>
          <text x="467" y="128" textAnchor="middle">{labels[2]}</text>
          <text x="658" y="118" textAnchor="middle">传感器</text>
          <text x="658" y="141" textAnchor="middle" className="anim-subtext">{labels[0]}</text>
          <line x1="110" y1="122" x2="154" y2="122" className="anim-link" markerEnd={marker} />
          <line x1="314" y1="122" x2="382" y2="122" className="anim-link" markerEnd={marker} />
          <line x1="542" y1="122" x2="588" y2="122" className="anim-link" markerEnd={marker} />
          <polyline points="658,156 658,208 82,208 82,160" fill="none" className="anim-link feedback" markerEnd={marker} />
          <circle data-testid="motion-token" cx={showFinalFrame ? 426 : 126} cy="208" r="7" className={`anim-pulse ${playing ? 'is-playing' : ''}`} />
        </g>
      );
    case 'robotView':
      return (
        <g>
          <line x1="70" y1="213" x2="690" y2="213" className="parameter-axis" />
          <circle cx="320" cy="196" r="29" className="robot-wheel" />
          <circle cx="440" cy="196" r="29" className="robot-wheel" />
          <line x1="380" y1="185" x2="380" y2="86" className="robot-body" />
          <circle cx="380" cy="78" r="12" fill="#0f766e" />
          {items.slice(0, 3).map((label, index) => (
            <g key={`${label}-${index}`}>
              <rect x={72 + index * 215} y="65" width="180" height="34" rx="5" fill="#f8fafc" stroke="#64748b" />
              <text x={162 + index * 215} y="87" textAnchor="middle" className="anim-subtext">{label}</text>
            </g>
          ))}
          <line x1="380" y1="111" x2="522" y2="146" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" markerEnd={marker} />
          <text x="570" y="151" className="anim-subtext">状态观测</text>
        </g>
      );
  }
}

function ConfiguredGraph({ entry, marker, fallbackLabels, kind }: {
  entry: CourseAnimationEntry;
  marker: string;
  fallbackLabels: string[];
  kind: 'stage' | 'node';
}) {
  const nodes = entry.chapterConfig.items.filter(isPositionedNode);
  if (nodes.length < 2) return <>{pipelineNodes(fallbackLabels, marker, kind)}</>;

  const byId = new Map(nodes.flatMap((node) => node.id ? [[node.id, node]] : []));
  const arrows = entry.chapterConfig.items.filter((item) => item.type === 'arrow');
  return (
    <g data-testid="configured-graph" transform="translate(28 43) scale(.72)">
      {arrows.map((arrow, index) => {
        const from = arrow.from ? byId.get(arrow.from) : undefined;
        const to = arrow.to ? byId.get(arrow.to) : undefined;
        if (!from || !to) return null;
        const fromWidth = from.w ?? 120;
        const fromHeight = from.h ?? 44;
        const toWidth = to.w ?? 120;
        const toHeight = to.h ?? 44;
        const fromCenterX = from.x + fromWidth / 2;
        const fromCenterY = from.y + fromHeight / 2;
        const toCenterX = to.x + toWidth / 2;
        const toCenterY = to.y + toHeight / 2;
        const horizontal = Math.abs(toCenterX - fromCenterX) >= Math.abs(toCenterY - fromCenterY);
        const x1 = horizontal ? from.x + (toCenterX >= fromCenterX ? fromWidth : 0) : fromCenterX;
        const y1 = horizontal ? fromCenterY : from.y + (toCenterY >= fromCenterY ? fromHeight : 0);
        const x2 = horizontal ? to.x + (toCenterX >= fromCenterX ? 0 : toWidth) : toCenterX;
        const y2 = horizontal ? toCenterY : to.y + (toCenterY >= fromCenterY ? 0 : toHeight);
        return (
          <line
            key={`configured-arrow-${index}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={arrow.color ?? '#2563eb'}
            strokeWidth="3"
            strokeDasharray={arrow.dashed ? '8 6' : undefined}
            markerEnd={marker}
          />
        );
      })}
      {nodes.map((node, index) => {
        const width = node.w ?? 120;
        const height = node.h ?? 44;
        const color = node.color ?? (kind === 'node' ? '#0f766e' : '#2563eb');
        return (
          <g key={node.id ?? `configured-node-${index}`}>
            <rect
              x={node.x}
              y={node.y}
              width={width}
              height={height}
              rx={kind === 'node' ? 12 : 6}
              fill={color}
              fillOpacity=".12"
              stroke={color}
              strokeWidth="2.5"
            />
            <text x={node.x + width / 2} y={node.y + height / 2 + 5} textAnchor="middle">
              {compact(node.label ?? node.text ?? '', Math.max(5, Math.floor(width / 13)))}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function isPositionedNode(item: AnimationItem): item is AnimationItem & { x: number; y: number } {
  return (item.type === 'stage' || item.type === 'node')
    && typeof item.x === 'number'
    && typeof item.y === 'number';
}

function pipelineNodes(labels: string[], marker: string, kind: 'stage' | 'node') {
  const shown = labels;
  const count = Math.max(shown.length, 1);
  const columns = Math.min(count, 4);
  const gap = 18;
  const width = (700 - (columns - 1) * gap) / columns;
  const start = 30;
  return shown.map((label, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const x = start + column * (width + gap);
    const y = 78 + row * 58;
    const connectsSameRow = index < count - 1 && (index + 1) % columns !== 0;
    return (
      <g key={`${kind}-${label}-${index}`}>
        <rect x={x} y={y} width={width} height="42" rx={kind === 'node' ? 14 : 6} className={index % 2 ? 'anim-node decide' : 'anim-node observe'} />
        <text x={x + width / 2} y={y + 26} textAnchor="middle">{compact(label, Math.max(6, Math.floor(width / 13)))}</text>
        {connectsSameRow && <line x1={x + width} y1={y + 21} x2={x + width + gap - 8} y2={y + 21} className="anim-link" markerEnd={marker} />}
      </g>
    );
  });
}

function ParameterScene({ entry }: { entry: CourseAnimationEntry }) {
  const parameter = entry.parameter!;
  const [value, setValue] = useState(parameter.initial);
  const normalized = (value - parameter.min) / Math.max(parameter.max - parameter.min, Number.EPSILON);
  const offset = (normalized * 16).toFixed(2);

  return (
    <div className="parameter-scene">
      <svg viewBox="0 0 760 220" role="img" aria-label={`${parameter.label} 参数变化`}>
        <text x="380" y="24" textAnchor="middle" className="compare-title">{entry.chapterConfig.title}</text>
        <text x="380" y="44" textAnchor="middle" className="anim-subtext">{compact(entry.chapterConfig.subtitle ?? parameter.label, 42)}</text>
        <g data-testid="parameter-geometry" transform={`translate(${offset} 0)`}>
          <ParameterGeometry entry={entry} normalized={normalized} />
        </g>
      </svg>
      <label className="animation-slider-label">
        <span>{parameter.label}</span>
        <input
          type="range"
          aria-label={parameter.label}
          min={parameter.min}
          max={parameter.max}
          step={parameter.step ?? 0.01}
          value={value}
          onChange={(event) => setValue(Number(event.target.value))}
        />
        <output data-testid="animation-output" data-value={value}>
          {value.toFixed(parameter.step && parameter.step >= 1 ? 0 : 2)}
        </output>
      </label>
    </div>
  );
}

function ParameterGeometry({ entry, normalized }: { entry: CourseAnimationEntry; normalized: number }) {
  const labels = mechanismLabels(entry);
  const items = itemLabels(entry);
  switch (entry.chapterConfig.scene) {
    case 'signalPlot': {
      const amplitude = 16 + normalized * 54;
      const path = wavePath(amplitude, 120 + normalized * 30);
      return (
        <g>
          <line x1="70" y1="184" x2="670" y2="184" className="parameter-axis" />
          <line x1="70" y1="62" x2="70" y2="184" className="parameter-axis" />
          <path d={path} fill="none" stroke="#2563eb" strokeWidth={2 + normalized * 3} />
          <line x1="70" y1={122 - amplitude} x2="670" y2={122 - amplitude} stroke="#dc2626" strokeDasharray="7 5" />
          <text x="500" y="78" className="anim-subtext">{items[0] ?? labels[2]}随参数改变</text>
        </g>
      );
    }
    case 'formulaExplorer': {
      const angle = -55 + normalized * 110;
      const radians = angle * Math.PI / 180;
      const x2 = 210 + Math.cos(radians) * (70 + normalized * 60);
      const y2 = 157 - Math.sin(radians) * (70 + normalized * 60);
      const formula = entry.chapterConfig.items.find((item) => item.type === 'formula')?.text ?? labels[1];
      return (
        <g>
          <rect x="360" y="70" width="300" height="72" rx="6" className="anim-node decide" />
          <text x="510" y="111" textAnchor="middle">{compact(formula, 34)}</text>
          <line x1="80" y1="157" x2="330" y2="157" className="parameter-axis" />
          <line x1="210" y1="198" x2="210" y2="66" className="parameter-axis" />
          <line x1="210" y1="157" x2={x2} y2={y2} stroke="#0f766e" strokeWidth="6" />
          <circle cx={x2} cy={y2} r={7 + normalized * 5} fill="#f59e0b" />
          <text x="210" y="215" textAnchor="middle" className="anim-subtext">向量几何与数值同步</text>
        </g>
      );
    }
    case 'dataPipeline': {
      const tokenX = 98 + normalized * 520;
      return (
        <g>
          {[0, 1, 2, 3].map((index) => (
            <g key={index}>
              <rect x={64 + index * 170} y="96" width="132" height="62" rx="5" className={index % 2 ? 'anim-node decide' : 'anim-node observe'} opacity={0.55 + normalized * 0.45} />
              <text x={130 + index * 170} y="132" textAnchor="middle">{compact(items[index] ?? labels[index % 3], 13)}</text>
            </g>
          ))}
          <line x1="96" y1="176" x2="640" y2="176" stroke="#2563eb" strokeWidth={2 + normalized * 5} />
          <circle cx={tokenX} cy="176" r={8 + normalized * 5} fill="#f59e0b" />
        </g>
      );
    }
    case 'flowchart': {
      const scale = 0.72 + normalized * 0.48;
      return (
        <g>
          <rect x="60" y="105" width="150" height="58" rx="6" className="anim-node observe" />
          <polygon points="370,72 470,134 370,196 270,134" fill="#ecfdf5" stroke="#0f766e" strokeWidth={2 + normalized * 4} transform={`translate(${370 * (1 - scale)} ${134 * (1 - scale)}) scale(${scale})`} />
          <rect x="530" y="105" width="150" height="58" rx="6" className="anim-node act" />
          <text x="135" y="140" textAnchor="middle">{items[0] ?? labels[0]}</text>
          <text x="370" y="139" textAnchor="middle">阈值 {Math.round(normalized * 100)}%</text>
          <text x="605" y="140" textAnchor="middle">{items[2] ?? labels[2]}</text>
        </g>
      );
    }
    case 'stateFlow': {
      const activeX = 95 + normalized * 540;
      return (
        <g>
          {[0, 1, 2, 3].map((index) => (
            <g key={index}>
              <circle cx={95 + index * 180} cy="132" r="39" fill="#eff6ff" stroke="#2563eb" strokeWidth="3" />
              <text x={95 + index * 180} y="137" textAnchor="middle">{compact(items[index] ?? labels[index % 3], 10)}</text>
            </g>
          ))}
          <line x1="95" y1="187" x2="635" y2="187" className="parameter-axis" />
          <circle cx={activeX} cy="187" r={8 + normalized * 6} fill="#0f766e" />
        </g>
      );
    }
    case 'architecture':
      return (
        <g>
          {(items.length ? items : labels).slice(0, 4).map((label, index) => {
            const width = 300 + normalized * 250 - index * 32;
            return (
              <g key={`${label}-${index}`}>
                <rect x={(720 - width) / 2} y={64 + index * 36} width={width} height="28" rx="4" fill={index % 2 ? '#ecfdf5' : '#eff6ff'} stroke={index % 2 ? '#0f766e' : '#2563eb'} strokeWidth={1.5 + normalized * 2} />
                <text x="360" y={83 + index * 36} textAnchor="middle" className="anim-subtext">{label}</text>
              </g>
            );
          })}
        </g>
      );
    case 'controlLoop': {
      const response = -16 + normalized * 32;
      const strokeWidth = 2 + normalized * 6;
      return (
        <g>
          <rect x="70" y="90" width="150" height="64" rx="6" className="anim-node observe" />
          <rect x="300" y="90" width="150" height="64" rx="6" className="anim-node decide" />
          <text x="145" y="127" textAnchor="middle">误差输入</text>
          <text x="375" y="117" textAnchor="middle">{entry.parameter?.label}</text>
          <text x="375" y="140" textAnchor="middle" className="anim-subtext">反馈强度</text>
          <line x1="220" y1="122" x2={280 + normalized * 20} y2="122" stroke="#0f766e" strokeWidth={strokeWidth} />
          <circle cx="575" cy="172" r="24" className="robot-wheel" />
          <circle cx="655" cy="172" r="24" className="robot-wheel" />
          <line x1="615" y1="162" x2="615" y2="76" className="robot-body" transform={`rotate(${response} 615 162)`} />
          <text x="615" y="210" textAnchor="middle" className="anim-subtext">闭环响应 {response.toFixed(1)}°</text>
        </g>
      );
    }
    case 'robotView': {
      const tilt = -22 + normalized * 44;
      const force = 40 + normalized * 130;
      return (
        <g>
          <line x1="65" y1="185" x2="690" y2="185" className="parameter-axis" />
          <circle cx="310" cy="171" r={22 + normalized * 8} className="robot-wheel" />
          <circle cx="430" cy="171" r={22 + normalized * 8} className="robot-wheel" />
          <line x1="370" y1="160" x2="370" y2="65" className="robot-body" transform={`rotate(${tilt} 370 160)`} />
          <line x1="430" y1="171" x2={430 + force} y2="171" stroke="#dc2626" strokeWidth="5" />
          <text x="370" y="214" textAnchor="middle" className="anim-subtext">{labels[1]}：姿态与接触几何同步</text>
        </g>
      );
    }
  }
}

function ComparisonScene({ entry, playing, completed, reducedMotion, markerId }: {
  entry: CourseAnimationEntry;
  playing: boolean;
  completed: boolean;
  reducedMotion: boolean;
  markerId: string;
}) {
  const labels = mechanismLabels(entry);
  const items = itemLabels(entry);
  const marker = `url(#${markerId})`;
  return (
    <svg data-testid="comparison-scene" viewBox="0 0 760 260" role="img" aria-label={`${entry.chapterConfig.title} 正确与故障对比`}>
      <ArrowMarker id={markerId} />
      <text x="380" y="18" textAnchor="middle" className="compare-title">{entry.chapterConfig.title}</text>
      <rect x="24" y="28" width="344" height="210" rx="6" className="compare-panel healthy" />
      <rect x="392" y="28" width="344" height="210" rx="6" className="compare-panel faulty" />
      <text x="196" y="55" textAnchor="middle" className="compare-title healthy">正确：契约成立</text>
      <text x="564" y="55" textAnchor="middle" className="compare-title faulty">故障：诊断触发</text>
      <ComparisonGeometry
        entry={entry}
        labels={labels}
        items={items}
        marker={marker}
        playing={playing}
        completed={completed}
        reducedMotion={reducedMotion}
      />
    </svg>
  );
}

function ComparisonGeometry({ entry, labels, items, marker, playing, completed, reducedMotion }: {
  entry: CourseAnimationEntry;
  labels: [string, string, string];
  items: string[];
  marker: string;
  playing: boolean;
  completed: boolean;
  reducedMotion: boolean;
}) {
  const left = compact(items[0] ?? labels[0], 16);
  const right = compact(items[1] ?? labels[1], 16);
  switch (entry.chapterConfig.scene) {
    case 'signalPlot':
      return (
        <g>
          <path d="M52 158 C88 92 126 92 162 158 S236 224 272 158 S326 110 344 138" fill="none" stroke="#16a34a" strokeWidth="4" />
          <path d="M420 155 L450 91 L482 201 L515 76 L550 218 L590 88 L628 210 L706 68" fill="none" stroke="#dc2626" strokeWidth="4" />
          <line x1="48" y1="190" x2="344" y2="190" className="parameter-axis" />
          <line x1="416" y1="190" x2="708" y2="190" className="parameter-axis" />
          <text x="196" y="220" textAnchor="middle" className="anim-subtext">{left}：收敛且平滑</text>
          <text x="564" y="220" textAnchor="middle" className="anim-subtext">{right}：发散或噪声超限</text>
        </g>
      );
    case 'formulaExplorer': {
      const formula = compact(entry.chapterConfig.items.find((item) => item.type === 'formula')?.text ?? labels[1], 23);
      return (
        <g>
          <circle cx="196" cy="128" r="50" fill="#ecfdf5" stroke="#16a34a" strokeWidth="3" />
          <text x="196" y="124" textAnchor="middle">{formula}</text>
          <text x="196" y="150" textAnchor="middle" fill="#15803d">残差 ≈ 0</text>
          <polygon points="564,76 628,184 500,184" fill="#fef2f2" stroke="#dc2626" strokeWidth="3" />
          <text x="564" y="137" textAnchor="middle">越界</text>
          <text x="564" y="162" textAnchor="middle" fill="#b91c1c">残差 &gt; 阈值</text>
          <text x="380" y="224" textAnchor="middle" className="anim-subtext">同一公式必须同时满足数值与约束</text>
        </g>
      );
    }
    case 'dataPipeline':
      return <PipelineComparison labels={[left, right, compact(items[2] ?? labels[2], 16)]} marker={marker} brokenLabel="数据断链" />;
    case 'flowchart':
      return (
        <g>
          <rect x="50" y="96" width="96" height="54" rx="5" className="anim-node observe" />
          <polygon points="220,78 278,123 220,168 162,123" fill="#ecfdf5" stroke="#16a34a" strokeWidth="3" />
          <rect x="292" y="96" width="54" height="54" rx="5" className="anim-node act" />
          <line x1="146" y1="123" x2="156" y2="123" className="anim-link" markerEnd={marker} />
          <line x1="278" y1="123" x2="286" y2="123" className="anim-link" markerEnd={marker} />
          <rect x="418" y="96" width="96" height="54" rx="5" fill="#fef2f2" stroke="#dc2626" />
          <polygon points="588,78 646,123 588,168 530,123" fill="#fef2f2" stroke="#dc2626" strokeWidth="3" />
          <line x1="514" y1="123" x2="524" y2="123" stroke="#dc2626" strokeWidth="3" />
          <text x="98" y="128" textAnchor="middle">{left}</text>
          <text x="220" y="128" textAnchor="middle">条件明确</text>
          <text x="466" y="128" textAnchor="middle">{left}</text>
          <text x="588" y="128" textAnchor="middle">条件冲突</text>
          <text x="196" y="215" textAnchor="middle" className="anim-subtext">分支可达验收结果</text>
          <text x="564" y="215" textAnchor="middle" className="anim-subtext">错误分支无法收敛</text>
        </g>
      );
    case 'stateFlow':
      return (
        <g>
          {[75, 196, 317].map((x, index) => <circle key={x} cx={x} cy="126" r="32" fill="#ecfdf5" stroke="#16a34a" strokeWidth="3" />)}
          <line x1="107" y1="126" x2="154" y2="126" className="anim-link" markerEnd={marker} />
          <line x1="228" y1="126" x2="275" y2="126" className="anim-link" markerEnd={marker} />
          {[443, 564].map((x) => <circle key={x} cx={x} cy="126" r="32" fill="#fef2f2" stroke="#dc2626" strokeWidth="3" />)}
          <circle cx="684" cy="126" r="32" fill="#b91c1c" stroke="#7f1d1d" strokeWidth="3" />
          <line x1="475" y1="126" x2="522" y2="126" stroke="#dc2626" strokeWidth="3" markerEnd={marker} />
          <line x1="596" y1="126" x2="642" y2="126" stroke="#dc2626" strokeWidth="3" strokeDasharray="7 5" markerEnd={marker} />
          <text x="196" y="194" textAnchor="middle" className="anim-subtext">合法状态按条件推进</text>
          <text x="564" y="194" textAnchor="middle" className="anim-subtext">非法转移进入 FAULT</text>
        </g>
      );
    case 'architecture':
      return (
        <g>
          {[0, 1, 2].map((index) => (
            <g key={index}>
              <rect x={64 + index * 18} y={72 + index * 48} width={264 - index * 36} height="32" rx="4" fill="#ecfdf5" stroke="#16a34a" />
              <text x="196" y={93 + index * 48} textAnchor="middle" className="anim-subtext">{compact(items[index] ?? labels[index], 20)}</text>
              <rect x={430 + index * 16} y={72 + index * 48 + (index === 1 ? 15 : 0)} width={268 - index * 32} height="32" rx="4" fill="#fef2f2" stroke="#dc2626" strokeWidth={index === 1 ? 3 : 1} />
              <text x="564" y={93 + index * 48 + (index === 1 ? 15 : 0)} textAnchor="middle" className="anim-subtext">{compact(items[index] ?? labels[index], 20)}</text>
            </g>
          ))}
          <text x="196" y="224" textAnchor="middle" className="anim-subtext">层级接口对齐</text>
          <text x="564" y="224" textAnchor="middle" className="anim-subtext">接口失配并越过边界</text>
        </g>
      );
    case 'controlLoop':
      return (
        <g>
          <circle cx="100" cy="126" r="28" fill="#ecfdf5" stroke="#16a34a" strokeWidth="3" />
          <rect x="160" y="96" width="126" height="60" rx="5" className="anim-node decide" />
          <line x1="128" y1="126" x2="150" y2="126" className="anim-link" markerEnd={marker} />
          <path d="M286 126 Q330 126 330 178 Q210 210 100 160" fill="none" stroke="#16a34a" strokeWidth="3" markerEnd={marker} />
          <circle cx="468" cy="126" r="28" fill="#fef2f2" stroke="#dc2626" strokeWidth="3" />
          <rect x="528" y="96" width="126" height="60" rx="5" fill="#fef2f2" stroke="#dc2626" />
          <line x1="496" y1="126" x2="518" y2="126" stroke="#dc2626" strokeWidth="3" strokeDasharray="7 5" markerEnd={marker} />
          <line x1="654" y1="126" x2="706" y2="126" stroke="#dc2626" strokeWidth="8" />
          <text x="223" y="132" textAnchor="middle">{right}</text>
          <text x="591" y="132" textAnchor="middle">延迟 / 饱和</text>
          <text x="196" y="222" textAnchor="middle" className="anim-subtext">反馈闭合，响应稳定</text>
          <text x="564" y="222" textAnchor="middle" className="anim-subtext">反馈断裂，控制量越界</text>
        </g>
      );
    case 'robotView':
      return (
        <g>
          <line x1="48" y1="194" x2="344" y2="194" className="parameter-axis" />
          <circle cx="160" cy="180" r="24" className="robot-wheel" />
          <circle cx="232" cy="180" r="24" className="robot-wheel" />
          <line
            x1="196"
            y1="168"
            x2="196"
            y2="82"
            className={`compare-robot healthy ${playing ? 'is-playing' : ''}`}
            transform={reducedMotion || completed ? 'rotate(-2 196 168)' : undefined}
          />
          <line x1="416" y1="194" x2="708" y2="194" stroke="#dc2626" strokeWidth="2" strokeDasharray="10 5" />
          <circle cx="528" cy="180" r="24" className="robot-wheel faulty" />
          <circle cx="600" cy="180" r="24" className="robot-wheel faulty" />
          <line
            x1="564"
            y1="168"
            x2="564"
            y2="82"
            className={`compare-robot faulty ${playing ? 'is-playing' : ''}`}
            transform={reducedMotion || completed ? 'rotate(28 564 168)' : undefined}
          />
          <line x1="600" y1="180" x2="684" y2="180" stroke="#dc2626" strokeWidth="5" markerEnd={marker} />
          <text x="196" y="224" textAnchor="middle" className="anim-subtext">接触正确，传感器有效</text>
          <text x="564" y="224" textAnchor="middle" className="anim-subtext">滑移 / 跌倒 / 观测异常</text>
        </g>
      );
  }
}

function PipelineComparison({ labels, marker, brokenLabel }: {
  labels: [string, string, string];
  marker: string;
  brokenLabel: string;
}) {
  return (
    <g>
      {labels.map((label, index) => (
        <g key={`healthy-${label}-${index}`}>
          <rect x={46 + index * 104} y="96" width="84" height="54" rx="5" fill="#ecfdf5" stroke="#16a34a" />
          <text x={88 + index * 104} y="128" textAnchor="middle" className="anim-subtext">{compact(label, 9)}</text>
          {index < 2 && <line x1={130 + index * 104} y1="123" x2={142 + index * 104} y2="123" stroke="#16a34a" strokeWidth="3" markerEnd={marker} />}
        </g>
      ))}
      {labels.map((label, index) => (
        <g key={`faulty-${label}-${index}`}>
          <rect x={414 + index * 104} y="96" width="84" height="54" rx="5" fill="#fef2f2" stroke="#dc2626" />
          <text x={456 + index * 104} y="128" textAnchor="middle" className="anim-subtext">{compact(label, 9)}</text>
          {index === 0 && <line x1="498" y1="123" x2="510" y2="123" stroke="#dc2626" strokeWidth="3" />}
          {index === 1 && <line x1="602" y1="123" x2="614" y2="123" stroke="#dc2626" strokeWidth="3" strokeDasharray="3 6" />}
        </g>
      ))}
      <text x="196" y="205" textAnchor="middle" className="anim-subtext">字段完整，顺序可追溯</text>
      <text x="564" y="205" textAnchor="middle" className="anim-subtext">{brokenLabel}：缺失或类型不匹配</text>
    </g>
  );
}

function itemLabels(entry: CourseAnimationEntry): string[] {
  return entry.chapterConfig.items
    .filter((item) => item.type !== 'arrow')
    .map((item) => item.label ?? item.text)
    .filter((value): value is string => Boolean(value))
    .map((value) => compact(value));
}

function mechanismLabels(entry: CourseAnimationEntry): [string, string, string] {
  const labels = itemLabels(entry);
  const fallbacks: Record<string, [string, string, string]> = {
    controlLoop: ['目标与观测', '控制律计算', '执行与反馈'],
    signalPlot: ['原始信号', '参数作用', '响应曲线'],
    formulaExplorer: ['物理量输入', '公式关系', '数值响应'],
    robotView: ['机器人状态', '仿真步进', '传感器输出'],
    architecture: ['上游接口', '系统边界', '下游契约'],
    dataPipeline: ['数据输入', '处理管线', '证据输出'],
    flowchart: ['起始条件', '关键阶段', '验收结果'],
    stateFlow: ['初始状态', '状态转移', '终态记录'],
  };
  const defaults = fallbacks[entry.chapterConfig.scene];
  return [labels[0] ?? defaults[0], labels[1] ?? defaults[1], labels[2] ?? defaults[2]];
}

function wavePath(amplitude: number, wavelength: number): string {
  const points = Array.from({ length: 25 }, (_, index) => {
    const x = 70 + index * 25;
    const y = 122 - Math.sin((index * 25 / wavelength) * Math.PI * 2) * amplitude;
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  return points.join(' ');
}

function compact(value: string, maxLength = 18): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function EvidenceScene({ entry }: { entry: CourseAnimationEntry }) {
  const [missing, setMissing] = useState(false);
  const [revision, setRevision] = useState(0);
  const { activeOwnerId, tasks, startRun } = useRunCoordinator();
  const ownerId = `animation-evidence:${entry.id}`;
  const snapshot = tasks[ownerId];
  const command = entry.evidence.command;
  const path = entry.evidence.path;
  const run = async () => {
    if (!command) return;
    const status = await startRun(ownerId, entry.chapterId, 'animation-evidence', command);
    if (status === 'succeeded') {
      setMissing(false);
      setRevision((current) => current + 1);
    }
  };

  if (!path || missing) {
    return (
      <div className="evidence-missing">
        <TriangleAlert size={28} />
        <strong>尚无可读取的固定 seed 证据</strong>
        {command && <code>{command}</code>}
        {command && (
          <button type="button" onClick={() => void run()} disabled={activeOwnerId !== null}>
            <Play size={15} /> {snapshot?.status === 'running' || snapshot?.status === 'queued' ? '生成中' : '生成证据'}
          </button>
        )}
      </div>
    );
  }

  return (
    <figure className="evidence-figure">
      <img
        src={`${ARTIFACT_BASE}${path}?v=${revision}`}
        alt={`${entry.chapterId} 固定 seed 验收图表`}
        onError={() => setMissing(true)}
      />
      <figcaption>仅展示后端已有产物；图像不存在时不会生成替代数据。</figcaption>
    </figure>
  );
}
