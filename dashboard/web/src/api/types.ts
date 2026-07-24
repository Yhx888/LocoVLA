export interface ChapterDto {
  id: string;
  stage: string;
  stage_title: string;
  title: string;
  task: string;
  status: 'ready' | 'planned';
  prerequisites: string[];
  content: string;
  reading_percent: number;
  reading_complete: boolean;
  self_check_ids: string[];
  self_check_items: SelfCheckItem[];
  experiment_accepted: boolean;
  completed: boolean;
  presets: RunPreset[];
  checkpoints: CheckpointDto[];
  artifacts: ArtifactDto[];
}

export interface ProgressRecord {
  reading_percent: number;
  reading_complete: boolean;
  self_check_ids: string[];
}

export interface RunPreset {
  id: string;
  label: string;
  mode: 'demo' | 'full';
  estimated_seconds: number;
  requires: string[];
  counts_for_acceptance: boolean;
  commands: string[];
}

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'interrupted';

export interface RunRecord {
  id: string;
  chapter_id: string;
  preset_id: string;
  status: RunStatus;
  created_at: string;
  finished_at: string;
  exit_code: number | null;
  error_category: string | null;
}

export interface RunEvent {
  run_id: string;
  sequence: number;
  timestamp: string;
  kind: 'stdout' | 'stderr' | 'status';
  stream: string;
  text: string;
  status: string | null;
}

export interface HealthDto {
  status: 'ready' | 'degraded';
  python: Record<string, unknown>;
  dependencies: Record<string, string | null>;
  mujoco: Record<string, unknown>;
  outputs: Record<string, unknown>;
}

export interface ArtifactDto {
  path: string;
  type: string;
  size: number;
  modified_at: string;
  url: string;
  evidence_valid: boolean;
}

export interface CourseSummary {
  title: string;
  version: string;
  total_chapters: number;
  completed_chapters: number;
  next_chapter: ChapterDto | null;
  stages: StageSummary[];
}

export interface StageSummary {
  id: string;
  title: string;
  project: string;
  total: number;
  ready: number;
  completed: number;
  chapters: { id: string; title: string; status: string; completed: boolean; reading_complete: boolean; reading_percent: number }[];
}

export interface CheckpointDto {
  id: string;
  command: string;
  acceptance: string;
}

export interface SelfCheckItem {
  id: string;
  text: string;
  checked: boolean;
}
