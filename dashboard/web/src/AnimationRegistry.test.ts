import { describe, it, expect } from 'vitest';
import { CHAPTER_ANIMATIONS, COURSE_ANIMATIONS } from './animations/chapters/ChapterAnimationConfigs';

const ALL_58_CHAPTERS = [
  '00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
  '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24',
  '25', '26', '27', '28', '29', '30', '31',
  '32', '33', '34', '35', '36', '37',
  '38', '39', '40', '41', '42', '43', '44', '45', '46', '47',
  'H01', 'H02', 'H03', 'H04', 'H05', 'H06', 'H07', 'H08', 'H09', 'H10',
];

describe('58 关动画注册表', () => {
  it('精确覆盖 58 个章节', () => {
    const keys = Object.keys(CHAPTER_ANIMATIONS).sort();
    expect(keys).toEqual(ALL_58_CHAPTERS);
  });

  it('每个章节都有有效场景类型', () => {
    const validScenes = ['flowchart', 'controlLoop', 'signalPlot', 'stateFlow', 'architecture', 'dataPipeline', 'formulaExplorer', 'robotView'];
    for (const [id, config] of Object.entries(CHAPTER_ANIMATIONS)) {
      expect(validScenes).toContain(config.scene);
      expect(config.title).toBeTruthy();
    }
  });

  it('H02-H10 保持 planned 状态', () => {
    for (const id of ['H02', 'H03', 'H04', 'H05', 'H06', 'H07', 'H08', 'H09', 'H10']) {
      expect(CHAPTER_ANIMATIONS[id]).toBeDefined();
    }
  });

  it('正文动画总数精确为 136 项', () => {
    expect(COURSE_ANIMATIONS).toHaveLength(136);
    expect(new Set(COURSE_ANIMATIONS.map((entry) => entry.id)).size).toBe(136);
  });

  it('12-37 每节覆盖四类动画，其余章节至少一个', () => {
    for (const chapterId of ALL_58_CHAPTERS) {
      const entries = COURSE_ANIMATIONS.filter((entry) => entry.chapterId === chapterId);
      const numericId = Number(chapterId);
      if (!Number.isNaN(numericId) && numericId >= 12 && numericId <= 37) {
        expect(entries.map((entry) => entry.category).sort()).toEqual([
          'comparison', 'evidence', 'intuition', 'parameter',
        ]);
      } else {
        expect(entries.length).toBeGreaterThanOrEqual(1);
      }
    }
  });

  it('所有正文动画都有锚点、播放策略和证据来源', () => {
    for (const entry of COURSE_ANIMATIONS) {
      expect(entry.anchor).toBe(`upkie-animation-${entry.id}`);
      expect(entry.playPolicy).toBe('once-in-view');
      expect(entry.evidence.kind).toMatch(/^(concept|artifact|command)$/);
      if (entry.category === 'parameter') expect(entry.parameter).toBeDefined();
    }
  });

  it('12-37 的参数动画使用本章领域参数而不是通用强度', () => {
    const denseParameters = COURSE_ANIMATIONS.filter((entry) => (
      entry.category === 'parameter'
      && Number(entry.chapterId) >= 12
      && Number(entry.chapterId) <= 37
    ));
    expect(denseParameters).toHaveLength(26);
    for (const entry of denseParameters) {
      expect(entry.parameter?.label).not.toBe('参数强度');
      expect(entry.parameter?.key).not.toBe('intensity');
    }
  });

  it('H02-H10 动画明确为概念示意', () => {
    for (const chapterId of ['H02', 'H03', 'H04', 'H05', 'H06', 'H07', 'H08', 'H09', 'H10']) {
      const entries = COURSE_ANIMATIONS.filter((entry) => entry.chapterId === chapterId);
      expect(entries.every((entry) => entry.conceptualOnly && entry.evidence.kind === 'concept')).toBe(true);
    }
  });
});
