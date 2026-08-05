/**
 * 58 关统一可配置动画 — 章节目录与交互场景定义。
 *
 * 每个章节指定：
 *  - scene:     渲染场景类型（flowchart/controlLoop/signalPlot/stateFlow/architecture/dataPipeline/formulaExplorer/robotView）
 *  - title:     场景内标题
 *  - sliders:   交互参数 [{key, label, min, max, step?}]
 *  - items:     场景特有元素（节点、连线、阶段等）
 */

export type SceneType =
  | 'flowchart'
  | 'controlLoop'
  | 'signalPlot'
  | 'stateFlow'
  | 'architecture'
  | 'dataPipeline'
  | 'formulaExplorer'
  | 'robotView'

export interface SliderDef {
  key: string
  label: string
  min: number
  max: number
  step?: number
}

export type AnimationItemType =
  | 'stage' | 'arrow' | 'node' | 'formula' | 'note' | 'curve'
  | 'layer' | 'sensor' | 'pidBar'

export interface AnimationItem {
  type: AnimationItemType
  id?: string
  label?: string
  text?: string
  from?: string
  to?: string
  x?: number
  y?: number
  w?: number
  h?: number
  value?: number
  color?: string
  dashed?: boolean
}

export interface ChapterAnimationConfig {
  scene: SceneType
  title: string
  subtitle?: string
  sliders: SliderDef[]
  items: AnimationItem[]
}

export type AnimationCategory = 'intuition' | 'parameter' | 'comparison' | 'evidence'
export type InlineSceneType = 'mechanism' | 'parameter' | 'comparison' | 'evidence'

export interface AnimationEvidence {
  kind: 'concept' | 'artifact' | 'command'
  description: string
  path?: string
  command?: string
}

export interface CourseAnimationEntry {
  id: string
  chapterId: string
  title: string
  anchor: string
  category: AnimationCategory
  scene: InlineSceneType
  playPolicy: 'once-in-view'
  evidence: AnimationEvidence
  chapterConfig: ChapterAnimationConfig
  parameter?: SliderDef & { initial: number }
  conceptualOnly: boolean
}

// ═══════════════════════════════════════════════════════════
// 各章动画配置
// ═══════════════════════════════════════════════════════════

export const CHAPTER_ANIMATIONS: Record<string, ChapterAnimationConfig> = {
  // ── 阶段 0：数学与工具 ──
  '00': {
    scene: 'flowchart',
    title: '课程能力地图',
    subtitle: '9 个阶段 · 58 个关卡',
    sliders: [],
    items: [
      { type: 'stage', id: '0', label: '数学与工具', x: 50, y: 40, w: 140, h: 36, color: '#3b82f6' },
      { type: 'stage', id: '1', label: '机器人仿真', x: 230, y: 40, w: 140, h: 36, color: '#3b82f6' },
      { type: 'stage', id: '2', label: '经典控制', x: 410, y: 40, w: 140, h: 36, color: '#3b82f6' },
      { type: 'stage', id: '3', label: '状态估计与优化', x: 590, y: 40, w: 140, h: 36, color: '#3b82f6' },
      { type: 'stage', id: '4', label: '学习控制(RL)', x: 770, y: 40, w: 140, h: 36, color: '#8b5cf6' },
      { type: 'stage', id: '5', label: '应用型 VLA', x: 50, y: 120, w: 140, h: 36, color: '#06b6d4' },
      { type: 'stage', id: '6', label: '工程部署', x: 230, y: 120, w: 140, h: 36, color: '#f59e0b' },
      { type: 'stage', id: '7', label: '岗位毕业项目', x: 410, y: 120, w: 140, h: 36, color: '#ef4444' },
      { type: 'stage', id: 'H', label: '硬件选修', x: 590, y: 120, w: 140, h: 36, color: '#6b7280' },
      { type: 'arrow', from: '0', to: '1' },
      { type: 'arrow', from: '1', to: '2' },
      { type: 'arrow', from: '2', to: '3' },
      { type: 'arrow', from: '3', to: '4' },
      { type: 'arrow', from: '4', to: '5', dashed: true },
      { type: 'arrow', from: '5', to: '6', dashed: true },
      { type: 'arrow', from: '6', to: '7', dashed: true },
    ],
  },

  // 01-05 基础数学
  '01': {
    scene: 'formulaExplorer',
    title: 'Python 科学计算环境',
    subtitle: '数组形状 · 数值微分 · 有限性验证',
    sliders: [
      { key: 'samples', label: '采样点', min: 10, max: 200 },
    ],
    items: [
      { type: 'formula', text: 'f\'(x) ≈ [f(x+h)−f(x−h)] / 2h', x: 480, y: 60 },
      { type: 'note', text: '中心差分 · O(h²) 精度', x: 480, y: 100 },
    ],
  },
  '02': {
    scene: 'stateFlow',
    title: 'Git 可复现实验流程',
    subtitle: 'commit → config → seed → hash → result',
    sliders: [],
    items: [
      { type: 'node', id: 'commit', label: 'Commit', x: 60, y: 200, w: 120, h: 36 },
      { type: 'node', id: 'config', label: 'Config', x: 220, y: 200, w: 120, h: 36 },
      { type: 'node', id: 'seed', label: 'Seed', x: 380, y: 200, w: 120, h: 36 },
      { type: 'node', id: 'hash', label: 'Hash', x: 540, y: 200, w: 120, h: 36 },
      { type: 'node', id: 'result', label: 'Result', x: 700, y: 200, w: 120, h: 36 },
      { type: 'arrow', from: 'commit', to: 'config', color: '#3b82f6' },
      { type: 'arrow', from: 'config', to: 'seed', color: '#3b82f6' },
      { type: 'arrow', from: 'seed', to: 'hash', color: '#3b82f6' },
      { type: 'arrow', from: 'hash', to: 'result', color: '#10b981' },
    ],
  },
  '03': {
    scene: 'formulaExplorer',
    title: '向量、矩阵与坐标变换',
    subtitle: 'SVD · 条件数 · 旋转矩阵',
    sliders: [
      { key: 'angle', label: '旋转角(°)', min: -180, max: 180 },
    ],
    items: [
      { type: 'formula', text: 'R(θ) = [[cosθ, −sinθ], [sinθ, cosθ]]', x: 480, y: 60 },
      { type: 'note', text: '正交矩阵 · det(R)=1', x: 480, y: 100 },
    ],
  },
  '04': {
    scene: 'signalPlot',
    title: '线性化与非线性',
    subtitle: '非线性摆 vs 小角度近似 · 中心差分梯度',
    sliders: [
      { key: 'amplitude', label: '振幅(°)', min: 1, max: 90 },
    ],
    items: [
      { type: 'curve', label: 'sin(x)', color: '#ef4444' },
      { type: 'curve', label: 'x (线性化)', color: '#3b82f6', dashed: true },
    ],
  },
  '05': {
    scene: 'signalPlot',
    title: '概率、噪声与数字信号',
    subtitle: '带噪信号 · 滤波降噪 · 响应滞后',
    sliders: [
      { key: 'noise', label: '噪声幅度', min: 0, max: 100 },
    ],
    items: [
      { type: 'curve', label: '原始信号', color: '#3b82f6' },
      { type: 'curve', label: '滤波后', color: '#10b981' },
    ],
  },

  // ── 阶段 1：机器人仿真 ──
  '06': {
    scene: 'robotView',
    title: 'MuJoCo 状态与时间步进',
    subtitle: 'dt=0.002s · frame_skip=5',
    sliders: [
      { key: 'timestep', label: '仿真步数', min: 1, max: 50 },
    ],
    items: [
      { type: 'sensor', label: '基座位置', x: 60, y: 40 },
      { type: 'sensor', label: '关节速度', x: 200, y: 40 },
      { type: 'sensor', label: 'IMU加速度计', x: 340, y: 40 },
    ],
  },
  '07': {
    scene: 'architecture',
    title: 'URDF/MJCF 模型审计',
    subtitle: '关节映射 · 传感器字段 · 采样周期',
    sliders: [],
    items: [
      { type: 'layer', label: 'URDF 定义', y: 80, color: '#3b82f6' },
      { type: 'layer', label: 'MJCF 编译', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: 'MuJoCo 运行时验证', y: 240, color: '#10b981' },
    ],
  },
  '08': {
    scene: 'formulaExplorer',
    title: '自由基座与空间姿态',
    subtitle: 'quaternion(wxyz) · euler · 旋转矩阵',
    sliders: [
      { key: 'roll', label: 'Roll(°)', min: -180, max: 180 },
      { key: 'pitch', label: 'Pitch(°)', min: -90, max: 90 },
    ],
    items: [
      { type: 'formula', text: '四元数 → 旋转矩阵 → 欧拉角', x: 480, y: 60 },
    ],
  },
  '09': {
    scene: 'architecture',
    title: '执行器与传感器接口',
    subtitle: '位置执行器(rad) · 力矩执行器(N·m)',
    sliders: [],
    items: [
      { type: 'layer', label: '控制指令 nu=6', y: 60, color: '#3b82f6' },
      { type: 'layer', label: '执行器：4位置+2力矩', y: 140, color: '#8b5cf6' },
      { type: 'layer', label: '传感器：11字段 × shape', y: 220, color: '#10b981' },
      { type: 'layer', label: 'MuJoCo sensordata 输出', y: 300, color: '#f59e0b' },
    ],
  },
  '10': {
    scene: 'robotView',
    title: '轮地接触、摩擦与碰撞',
    subtitle: '摩擦锥 · 接触力 · 碰撞检测',
    sliders: [
      { key: 'friction', label: '摩擦系数', min: 0.1, max: 2 },
    ],
    items: [
      { type: 'sensor', label: 'contact_force', x: 400, y: 300 },
      { type: 'arrow', from: 'wheel', to: 'ground', color: '#ef4444' },
    ],
  },
  '11': {
    scene: 'dataPipeline',
    title: '可替换机器人模型契约',
    subtitle: 'nq=13 · nv=12 · nu=6 · 轮端力矩',
    sliders: [],
    items: [
      { type: 'stage', id: 'validate', label: '契约校验', x: 60, y: 180, w: 130, h: 40 },
      { type: 'stage', id: 'compare', label: '字段对比', x: 240, y: 180, w: 130, h: 40 },
      { type: 'stage', id: 'report', label: '审计报告', x: 420, y: 180, w: 130, h: 40 },
      { type: 'arrow', from: 'validate', to: 'compare', color: '#3b82f6' },
      { type: 'arrow', from: 'compare', to: 'report', color: '#10b981' },
    ],
  },

  // ── 阶段 2：经典控制 ──
  '12': {
    scene: 'controlLoop',
    title: '反馈控制闭环',
    subtitle: '传感器→控制器→执行器→被控对象',
    sliders: [
      { key: 'gain', label: '增益K', min: 0.1, max: 10, step: 0.1 },
    ],
    items: [],
  },
  '13': {
    scene: 'controlLoop',
    title: 'PID 控制与抗饱和',
    subtitle: 'P + I + D + 抗积分饱和',
    sliders: [
      { key: 'Kp', label: 'Kp', min: 0, max: 50, step: 0.5 },
      { key: 'Ki', label: 'Ki', min: 0, max: 20, step: 0.1 },
      { key: 'Kd', label: 'Kd', min: 0, max: 10, step: 0.1 },
    ],
    items: [
      { type: 'pidBar', label: 'P', color: '#3b82f6' },
      { type: 'pidBar', label: 'I', color: '#ef4444' },
      { type: 'pidBar', label: 'D', color: '#10b981' },
    ],
  },
  '14': {
    scene: 'formulaExplorer',
    title: '轮式倒立摆动力学',
    subtitle: '俯仰动力学 · 小角度线性化 · 轮端力矩',
    sliders: [
      { key: 'theta', label: '俯仰角(°)', min: -30, max: 30 },
    ],
    items: [
      { type: 'formula', text: 'Iθ̈ = mgl sinθ + τ', x: 480, y: 60 },
    ],
  },
  '15': {
    scene: 'signalPlot',
    title: '极点/时域/频域关系',
    subtitle: '实部→收敛速度 · 虚部→振荡频率',
    sliders: [
      { key: 'real', label: '极点实部', min: -5, max: 1, step: 0.1 },
      { key: 'imag', label: '极点虚部', min: 0, max: 10, step: 0.1 },
    ],
    items: [
      { type: 'curve', label: '时域响应', color: '#3b82f6' },
      { type: 'curve', label: '频域Bode', color: '#f59e0b' },
    ],
  },
  '16': {
    scene: 'formulaExplorer',
    title: '状态空间与可控性',
    subtitle: '四状态线性模型 · 可控性矩阵秩',
    sliders: [],
    items: [
      { type: 'formula', text: 'ẋ = Ax + Bu  ·  rank([B AB A²B ...]) = n', x: 480, y: 60 },
    ],
  },
  '17': {
    scene: 'formulaExplorer',
    title: 'LQR 与 Riccati 方程',
    subtitle: 'ARE 求解 · 最优增益 · 闭环极点',
    sliders: [
      { key: 'Q_diag', label: 'Q对角权重', min: 0.1, max: 100, step: 0.1 },
      { key: 'R', label: 'R控制代价', min: 0.01, max: 10, step: 0.1 },
    ],
    items: [
      { type: 'formula', text: 'AᵀP + PA − PBR⁻¹BᵀP + Q = 0', x: 480, y: 60 },
    ],
  },
  '18': {
    scene: 'controlLoop',
    title: '动作接口：速度/偏航/高度',
    subtitle: '受限动作映射 · 安全边界',
    sliders: [
      { key: 'vx', label: '速度 vx', min: -1, max: 1, step: 0.05 },
      { key: 'yaw', label: '偏航率', min: -0.5, max: 0.5, step: 0.05 },
    ],
    items: [],
  },

  // ── 阶段 3：状态估计与优化 ──
  '19': {
    scene: 'signalPlot',
    title: '互补滤波融合',
    subtitle: '高通陀螺 + 低通加速度计',
    sliders: [
      { key: 'alpha', label: '互补系数 α', min: 0, max: 1, step: 0.01 },
    ],
    items: [
      { type: 'curve', label: '陀螺仪(高通)', color: '#ef4444' },
      { type: 'curve', label: '加速度计(低通)', color: '#3b82f6' },
      { type: 'curve', label: '融合姿态', color: '#10b981' },
    ],
  },
  '20': {
    scene: 'dataPipeline',
    title: 'Kalman Filter',
    subtitle: '预测→更新 · RMSE · 协方差收敛',
    sliders: [
      { key: 'Q', label: '过程噪声 Q', min: 0.001, max: 1, step: 0.001 },
      { key: 'R', label: '测量噪声 R', min: 0.001, max: 1, step: 0.001 },
    ],
    items: [
      { type: 'stage', id: 'predict', label: '预测 ẋ=Ax+Bu', x: 100, y: 180, w: 160 },
      { type: 'stage', id: 'update', label: '更新 K=PCᵀ(CPCᵀ+R)⁻¹', x: 340, y: 180, w: 200 },
      { type: 'stage', id: 'output', label: '状态估计', x: 620, y: 180, w: 140 },
      { type: 'arrow', from: 'predict', to: 'update', color: '#3b82f6' },
      { type: 'arrow', from: 'update', to: 'output', color: '#10b981' },
    ],
  },
  '21': {
    scene: 'dataPipeline',
    title: '扩展 Kalman Filter',
    subtitle: 'EKF/UKF · IMU+编码器融合 · 闭环存活',
    sliders: [
      { key: 'sigma', label: 'Sigma点散布', min: 0.1, max: 3, step: 0.1 },
    ],
    items: [
      { type: 'stage', id: 'ekf', label: 'EKF 线性化', x: 100, y: 150, w: 160 },
      { type: 'stage', id: 'ukf', label: 'UKF Sigma点', x: 340, y: 150, w: 160 },
      { type: 'stage', id: 'compare', label: 'RMSE对比', x: 580, y: 150, w: 160 },
      { type: 'arrow', from: 'ekf', to: 'compare', color: '#3b82f6' },
      { type: 'arrow', from: 'ukf', to: 'compare', color: '#8b5cf6' },
    ],
  },
  '22': {
    scene: 'dataPipeline',
    title: '参数辨识与模型验证',
    subtitle: '最小二乘 · 训练/测试分离',
    sliders: [],
    items: [
      { type: 'stage', id: 'data', label: '采集数据', x: 80, y: 180, w: 130 },
      { type: 'stage', id: 'split', label: '训练/测试分离', x: 250, y: 180, w: 140 },
      { type: 'stage', id: 'fit', label: '最小二乘拟合', x: 430, y: 180, w: 140 },
      { type: 'stage', id: 'validate', label: '交叉验证', x: 610, y: 180, w: 130 },
      { type: 'arrow', from: 'data', to: 'split', color: '#3b82f6' },
      { type: 'arrow', from: 'split', to: 'fit', color: '#3b82f6' },
      { type: 'arrow', from: 'fit', to: 'validate', color: '#10b981' },
    ],
  },
  '23': {
    scene: 'formulaExplorer',
    title: '二次规划与约束',
    subtitle: '凸QP · 轮端边界 · 约束残差',
    sliders: [
      { key: 'bound', label: '轮端约束(N·m)', min: 0.1, max: 2, step: 0.1 },
    ],
    items: [
      { type: 'formula', text: 'min ½xᵀPx + qᵀx  s.t. Ax ≤ b', x: 480, y: 60 },
    ],
  },
  '24': {
    scene: 'controlLoop',
    title: '模型预测控制 MPC',
    subtitle: '直接配点 vs 单次打靶 · 约束MPC闭环',
    sliders: [
      { key: 'horizon', label: '预测时域N', min: 5, max: 50, step: 5 },
    ],
    items: [],
  },

  // ── 阶段 4：学习控制 ──
  '25': {
    scene: 'architecture',
    title: 'Gymnasium 环境契约',
    subtitle: 'obs/action shape · seed复现 · step耗时',
    sliders: [],
    items: [
      { type: 'layer', label: 'reset() → obs', y: 60, color: '#3b82f6' },
      { type: 'layer', label: 'step(action) → obs,reward,done,info', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: 'render() → 可视化', y: 260, color: '#10b981' },
    ],
  },
  '26': {
    scene: 'signalPlot',
    title: '奖励设计与分解',
    subtitle: '各项奖励均值/方差 · 中性动作基线',
    sliders: [
      { key: 'r_scale', label: '奖励缩放', min: 0.1, max: 10, step: 0.1 },
    ],
    items: [
      { type: 'curve', label: 'survival奖励', color: '#10b981' },
      { type: 'curve', label: '姿态奖励', color: '#3b82f6' },
      { type: 'curve', label: '动作代价', color: '#ef4444' },
    ],
  },
  '27': {
    scene: 'signalPlot',
    title: 'MDP 与策略梯度',
    subtitle: 'REINFORCE · 解析梯度 · 价值基线',
    sliders: [
      { key: 'gamma', label: '折扣γ', min: 0.8, max: 0.999, step: 0.001 },
    ],
    items: [
      { type: 'curve', label: '策略梯度', color: '#3b82f6' },
      { type: 'curve', label: '带基线梯度', color: '#10b981' },
    ],
  },
  '28': {
    scene: 'signalPlot',
    title: 'PPO 训练诊断',
    subtitle: '回报曲线 · 存活率 · 俯仰安全边界',
    sliders: [
      { key: 'steps', label: '训练步数', min: 100, max: 50000, step: 100 },
    ],
    items: [
      { type: 'curve', label: '平均回报', color: '#3b82f6' },
      { type: 'curve', label: '存活率', color: '#10b981' },
    ],
  },
  '29': {
    scene: 'architecture',
    title: '域随机化与鲁棒性',
    subtitle: '覆盖率/均值/方差验证',
    sliders: [
      { key: 'friction', label: '摩擦随机化', min: 0.1, max: 2, step: 0.1 },
      { key: 'mass', label: '质量随机化', min: 0.5, max: 1.5, step: 0.05 },
    ],
    items: [
      { type: 'layer', label: '随机化分布采样', y: 80, color: '#3b82f6' },
      { type: 'layer', label: '多环境并行训练', y: 180, color: '#8b5cf6' },
      { type: 'layer', label: '鲁棒性评估', y: 280, color: '#10b981' },
    ],
  },
  '30': {
    scene: 'architecture',
    title: '残差强化学习',
    subtitle: '经典控制器基底 + PPO残差',
    sliders: [
      { key: 'residual_scale', label: '残差幅度', min: 0, max: 2, step: 0.1 },
    ],
    items: [
      { type: 'layer', label: '经典控制器 τ_base', y: 60, color: '#3b82f6' },
      { type: 'layer', label: 'RL残差 Δτ', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: '混合: τ = τ_base + α·Δτ', y: 260, color: '#10b981' },
    ],
  },
  '31': {
    scene: 'dataPipeline',
    title: 'Sim2Real 评估协议',
    subtitle: '配对评估 · bootstrap 置信区间',
    sliders: [],
    items: [
      { type: 'stage', id: 'sim', label: 'MuJoCo仿真', x: 80, y: 180, w: 150 },
      { type: 'stage', id: 'domain_rand', label: '域随机化', x: 280, y: 180, w: 150 },
      { type: 'stage', id: 'eval', label: '配对评估', x: 480, y: 180, w: 150 },
      { type: 'stage', id: 'report', label: 'Bootstrap CI', x: 680, y: 180, w: 150 },
      { type: 'arrow', from: 'sim', to: 'domain_rand', color: '#3b82f6' },
      { type: 'arrow', from: 'domain_rand', to: 'eval', color: '#3b82f6' },
      { type: 'arrow', from: 'eval', to: 'report', color: '#10b981' },
    ],
  },

  // ── 阶段 5：应用型 VLA ──
  '32': {
    scene: 'architecture',
    title: '分层任务架构',
    subtitle: '高层任务→低层命令 · 安全层级分离',
    sliders: [],
    items: [
      { type: 'layer', label: '自然语言指令', y: 60, color: '#06b6d4' },
      { type: 'layer', label: '任务规划层', y: 150, color: '#3b82f6' },
      { type: 'layer', label: '运动控制层', y: 240, color: '#8b5cf6' },
      { type: 'layer', label: '安全门控层', y: 330, color: '#ef4444' },
    ],
  },
  '33': {
    scene: 'dataPipeline',
    title: 'RGB-D 目标检测',
    subtitle: '颜色检测 · 质心误差 · 深度统计',
    sliders: [],
    items: [
      { type: 'stage', id: 'capture', label: 'RGB-D采集', x: 80, y: 200, w: 140 },
      { type: 'stage', id: 'detect', label: '颜色目标检测', x: 280, y: 200, w: 150 },
      { type: 'stage', id: 'locate', label: '像素质心+深度', x: 490, y: 200, w: 150 },
      { type: 'stage', id: 'nav', label: '导航决策', x: 700, y: 200, w: 130 },
      { type: 'arrow', from: 'capture', to: 'detect', color: '#3b82f6' },
      { type: 'arrow', from: 'detect', to: 'locate', color: '#8b5cf6' },
      { type: 'arrow', from: 'locate', to: 'nav', color: '#10b981' },
    ],
  },
  '34': {
    scene: 'controlLoop',
    title: '语言任务与安全命令',
    subtitle: 'target/verb/stop 结构化解析',
    sliders: [],
    items: [],
  },
  '35': {
    scene: 'dataPipeline',
    title: '示范数据与脚本专家',
    subtitle: 'RGB-D 示范集 · npz契约',
    sliders: [],
    items: [
      { type: 'stage', id: 'expert', label: '脚本专家控制', x: 80, y: 180, w: 150 },
      { type: 'stage', id: 'record', label: '录制 RGB-D', x: 290, y: 180, w: 150 },
      { type: 'stage', id: 'package', label: '打包 npz', x: 500, y: 180, w: 130 },
      { type: 'stage', id: 'split', label: '训练/验证切分', x: 670, y: 180, w: 150 },
      { type: 'arrow', from: 'expert', to: 'record', color: '#3b82f6' },
      { type: 'arrow', from: 'record', to: 'package', color: '#8b5cf6' },
      { type: 'arrow', from: 'package', to: 'split', color: '#10b981' },
    ],
  },
  '36': {
    scene: 'dataPipeline',
    title: '行为克隆与视觉语言融合',
    subtitle: 'BC 策略 · train/val loss · checkpoint',
    sliders: [
      { key: 'lr', label: '学习率', min: 1e-5, max: 1e-2, step: 1e-5 },
    ],
    items: [
      { type: 'stage', id: 'load', label: '加载示范', x: 80, y: 180, w: 130 },
      { type: 'stage', id: 'train', label: 'BC训练', x: 260, y: 180, w: 130 },
      { type: 'stage', id: 'eval', label: '评估loss', x: 440, y: 180, w: 130 },
      { type: 'stage', id: 'save', label: '保存checkpoint', x: 620, y: 180, w: 160 },
      { type: 'arrow', from: 'load', to: 'train', color: '#3b82f6' },
      { type: 'arrow', from: 'train', to: 'eval', color: '#8b5cf6' },
      { type: 'arrow', from: 'eval', to: 'save', color: '#10b981' },
    ],
  },
  '37': {
    scene: 'dataPipeline',
    title: '闭环泛化与失败分析',
    subtitle: '三色闭环 · 成功率/碰撞率 · 推理指标',
    sliders: [],
    items: [
      { type: 'stage', id: 'load_ckpt', label: '加载BC checkpoint', x: 80, y: 140, w: 160 },
      { type: 'stage', id: 'run', label: '三色MuJoCo闭环', x: 290, y: 140, w: 160 },
      { type: 'stage', id: 'metrics', label: '成功率·碰撞·推理', x: 500, y: 140, w: 160 },
      { type: 'stage', id: 'analyze', label: '失败分析报告', x: 710, y: 140, w: 160 },
      { type: 'arrow', from: 'load_ckpt', to: 'run', color: '#3b82f6' },
      { type: 'arrow', from: 'run', to: 'metrics', color: '#8b5cf6' },
      { type: 'arrow', from: 'metrics', to: 'analyze', color: '#10b981' },
    ],
  },

  // ── 阶段 6：工程部署 ──
  '38': {
    scene: 'dataPipeline',
    title: 'C++/Eigen 数值一致性',
    subtitle: 'CMake构建 · CTest · 1000组验证',
    sliders: [],
    items: [
      { type: 'stage', id: 'python', label: 'Python参考', x: 60, y: 180, w: 140 },
      { type: 'stage', id: 'cpp', label: 'C++实现', x: 260, y: 180, w: 140 },
      { type: 'stage', id: 'test', label: 'CTest验证', x: 460, y: 180, w: 130 },
      { type: 'stage', id: 'compare', label: '数值对比', x: 630, y: 180, w: 150 },
      { type: 'arrow', from: 'python', to: 'cpp', color: '#3b82f6' },
      { type: 'arrow', from: 'cpp', to: 'test', color: '#8b5cf6' },
      { type: 'arrow', from: 'test', to: 'compare', color: '#10b981' },
    ],
  },
  '39': {
    scene: 'architecture',
    title: 'CMake 工程结构',
    subtitle: '依赖图 · 干净构建 · 接口边界',
    sliders: [],
    items: [
      { type: 'layer', label: '顶层 CMakeLists.txt', y: 60, color: '#3b82f6' },
      { type: 'layer', label: '库目标 (add_library)', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: '测试目标 (add_test)', y: 260, color: '#10b981' },
    ],
  },
  '40': {
    scene: 'architecture',
    title: 'ROS2 控制节点',
    subtitle: 'colcon · /imu→/wheel_torque · 100Hz',
    sliders: [],
    items: [
      { type: 'layer', label: '/imu 话题输入', y: 60, color: '#3b82f6' },
      { type: 'layer', label: '控制节点 (100Hz)', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: '/wheel_torque 话题输出', y: 260, color: '#10b981' },
    ],
  },
  '41': {
    scene: 'signalPlot',
    title: '实时循环与并发',
    subtitle: '60秒100Hz · 抖动分布 · deadline miss',
    sliders: [
      { key: 'target_hz', label: '目标频率(Hz)', min: 10, max: 200, step: 10 },
    ],
    items: [
      { type: 'curve', label: '实际周期(ms)', color: '#3b82f6' },
      { type: 'curve', label: 'deadline=10ms', color: '#ef4444', dashed: true },
    ],
  },
  '42': {
    scene: 'dataPipeline',
    title: '日志、测试与性能分析',
    subtitle: 'JSON lines · gtest · 100Hz deadline',
    sliders: [],
    items: [
      { type: 'stage', id: 'log', label: '9字段JSON日志', x: 60, y: 180, w: 150 },
      { type: 'stage', id: 'test', label: 'gtest验证', x: 260, y: 180, w: 150 },
      { type: 'stage', id: 'profile', label: '性能剖面', x: 460, y: 180, w: 150 },
      { type: 'stage', id: 'report', label: '测试报告', x: 660, y: 180, w: 150 },
      { type: 'arrow', from: 'log', to: 'test', color: '#3b82f6' },
      { type: 'arrow', from: 'test', to: 'profile', color: '#8b5cf6' },
      { type: 'arrow', from: 'profile', to: 'report', color: '#10b981' },
    ],
  },
  '43': {
    scene: 'stateFlow',
    title: '安全状态机',
    subtitle: 'BOOT→SELF_CHECK→DISARMED→ARMED→FAULT',
    sliders: [],
    items: [
      { type: 'node', id: 'boot', label: 'BOOT', x: 60, y: 100, w: 100, h: 36 },
      { type: 'node', id: 'check', label: 'SELF_CHECK', x: 200, y: 100, w: 120, h: 36 },
      { type: 'node', id: 'disarmed', label: 'DISARMED', x: 360, y: 100, w: 110, h: 36 },
      { type: 'node', id: 'armed', label: 'ARMED', x: 520, y: 100, w: 90, h: 36 },
      { type: 'node', id: 'fault', label: 'FAULT', x: 350, y: 240, w: 80, h: 36, color: '#ef4444' },
      { type: 'arrow', from: 'boot', to: 'check', color: '#3b82f6' },
      { type: 'arrow', from: 'check', to: 'disarmed', color: '#10b981' },
      { type: 'arrow', from: 'disarmed', to: 'armed', color: '#3b82f6' },
      { type: 'arrow', from: 'armed', to: 'fault', color: '#ef4444', dashed: true },
      { type: 'arrow', from: 'disarmed', to: 'fault', color: '#ef4444', dashed: true },
    ],
  },

  // ── 阶段 7：岗位毕业项目 ──
  '44': {
    scene: 'architecture',
    title: '系统设计与接口评审',
    subtitle: '需求→接口→风险→验证 四层链路',
    sliders: [],
    items: [
      { type: 'layer', label: '需求文档', y: 60, color: '#3b82f6' },
      { type: 'layer', label: '接口契约(QoS/单位/限幅)', y: 160, color: '#8b5cf6' },
      { type: 'layer', label: '风险评估(FMEA)', y: 260, color: '#f59e0b' },
      { type: 'layer', label: '验证证据', y: 360, color: '#10b981' },
    ],
  },
  '45': {
    scene: 'flowchart',
    title: '综合毕业项目全链路',
    subtitle: '仿真→控制→安全→日志→分析',
    sliders: [],
    items: [
      { type: 'stage', id: 'sim', label: 'MuJoCo仿真', x: 50, y: 180, w: 130, h: 36, color: '#3b82f6' },
      { type: 'stage', id: 'ctrl', label: '控制算法', x: 220, y: 180, w: 130, h: 36, color: '#8b5cf6' },
      { type: 'stage', id: 'safety', label: '安全状态机', x: 390, y: 180, w: 130, h: 36, color: '#ef4444' },
      { type: 'stage', id: 'log', label: '日志系统', x: 560, y: 180, w: 130, h: 36, color: '#f59e0b' },
      { type: 'stage', id: 'analysis', label: '数据分析', x: 730, y: 180, w: 130, h: 36, color: '#10b981' },
      { type: 'arrow', from: 'sim', to: 'ctrl', color: '#3b82f6' },
      { type: 'arrow', from: 'ctrl', to: 'safety', color: '#8b5cf6' },
      { type: 'arrow', from: 'safety', to: 'log', color: '#ef4444' },
      { type: 'arrow', from: 'log', to: 'analysis', color: '#10b981' },
    ],
  },
  '46': {
    scene: 'flowchart',
    title: '故障演练',
    subtitle: '4大类9种故障 · 检测覆盖率100%',
    sliders: [],
    items: [
      { type: 'stage', id: 'sensor', label: '传感器故障', x: 50, y: 100, w: 130, h: 36, color: '#ef4444' },
      { type: 'stage', id: 'actuator', label: '执行器故障', x: 230, y: 100, w: 130, h: 36, color: '#f59e0b' },
      { type: 'stage', id: 'comm', label: '通信故障', x: 410, y: 100, w: 130, h: 36, color: '#ef4444' },
      { type: 'stage', id: 'soft', label: '软件故障', x: 590, y: 100, w: 130, h: 36, color: '#f59e0b' },
      { type: 'stage', id: 'detect', label: '检测→根因→修复', x: 330, y: 240, w: 200, h: 36, color: '#10b981' },
      { type: 'arrow', from: 'sensor', to: 'detect', color: '#6b7280' },
      { type: 'arrow', from: 'actuator', to: 'detect', color: '#6b7280' },
      { type: 'arrow', from: 'comm', to: 'detect', color: '#6b7280' },
      { type: 'arrow', from: 'soft', to: 'detect', color: '#6b7280' },
    ],
  },
  '47': {
    scene: 'dataPipeline',
    title: '代码评审与答辩',
    subtitle: '静态分析 · 覆盖率 · 面试题库',
    sliders: [],
    items: [
      { type: 'stage', id: 'static', label: '静态分析', x: 60, y: 180, w: 120 },
      { type: 'stage', id: 'coverage', label: '覆盖率', x: 220, y: 180, w: 120 },
      { type: 'stage', id: 'complexity', label: '复杂度', x: 380, y: 180, w: 120 },
      { type: 'stage', id: 'review', label: '答辩材料', x: 540, y: 180, w: 120 },
      { type: 'stage', id: 'interview', label: '47题面试', x: 700, y: 180, w: 120 },
    ],
  },

  // ── 阶段 H：硬件选修 ──
  'H01': {
    scene: 'architecture',
    title: 'BOM 审计与许可证',
    subtitle: '锁定 external repo revision · 审计根许可证',
    sliders: [],
    items: [
      { type: 'layer', label: 'Repo版本锁定', y: 80, color: '#3b82f6' },
      { type: 'layer', label: '许可证审计', y: 180, color: '#f59e0b' },
      { type: 'layer', label: 'BOM证据收集', y: 280, color: '#10b981' },
    ],
  },
  'H02': {
    scene: 'architecture',
    title: '机械加工与装配公差',
    subtitle: 'CNC加工 · 3D打印 · 配合间隙',
    sliders: [
      { key: 'tolerance', label: '公差(mm)', min: 0.01, max: 0.5, step: 0.01 },
    ],
    items: [
      { type: 'layer', label: '设计CAD', y: 80, color: '#3b82f6' },
      { type: 'layer', label: '加工制造', y: 180, color: '#8b5cf6' },
      { type: 'layer', label: '装配校验', y: 280, color: '#10b981' },
    ],
  },
  'H03': {
    scene: 'architecture',
    title: '供电、PCB 与安全检查',
    subtitle: '电池选型 · 稳压 · 短路保护',
    sliders: [
      { key: 'voltage', label: '供电电压(V)', min: 5, max: 24, step: 0.5 },
    ],
    items: [
      { type: 'layer', label: '电池/电源', y: 80, color: '#3b82f6' },
      { type: 'layer', label: 'PCB设计', y: 180, color: '#8b5cf6' },
      { type: 'layer', label: '安全测试', y: 280, color: '#ef4444' },
    ],
  },
  'H04': {
    scene: 'architecture',
    title: 'ESP32 · SimpleFOC · 无刷电机',
    subtitle: 'FOC控制 · 电流环 · 速度环',
    sliders: [
      { key: 'pwm_freq', label: 'PWM频率(kHz)', min: 10, max: 50, step: 5 },
    ],
    items: [
      { type: 'layer', label: 'ESP32 主控', y: 80, color: '#3b82f6' },
      { type: 'layer', label: 'SimpleFOC 算法', y: 180, color: '#8b5cf6' },
      { type: 'layer', label: 'BLDC 电机驱动', y: 280, color: '#10b981' },
    ],
  },
  'H05': {
    scene: 'dataPipeline',
    title: 'AS5600 编码器与标定',
    subtitle: 'I²C读取 · 角度标定 · 分辨率',
    sliders: [],
    items: [
      { type: 'stage', id: 'connect', label: 'I²C连接', x: 80, y: 200, w: 120 },
      { type: 'stage', id: 'read', label: '角度读取', x: 250, y: 200, w: 120 },
      { type: 'stage', id: 'calib', label: '零点标定', x: 420, y: 200, w: 120 },
      { type: 'stage', id: 'verify', label: '精度验证', x: 590, y: 200, w: 120 },
      { type: 'arrow', from: 'connect', to: 'read', color: '#3b82f6' },
      { type: 'arrow', from: 'read', to: 'calib', color: '#8b5cf6' },
      { type: 'arrow', from: 'calib', to: 'verify', color: '#10b981' },
    ],
  },
  'H06': {
    scene: 'dataPipeline',
    title: 'MPU6050 与姿态估计',
    subtitle: 'IMU融合 · 9轴 · 姿态角',
    sliders: [
      { key: 'gyro_trust', label: '陀螺仪信任度', min: 0.5, max: 0.995, step: 0.005 },
    ],
    items: [
      { type: 'stage', id: 'accel', label: '加速度计', x: 80, y: 160, w: 120 },
      { type: 'stage', id: 'gyro', label: '陀螺仪', x: 250, y: 160, w: 120 },
      { type: 'stage', id: 'fuse', label: '融合姿态', x: 420, y: 160, w: 120 },
      { type: 'stage', id: 'output', label: 'Roll/Pitch/Yaw', x: 590, y: 160, w: 150 },
      { type: 'arrow', from: 'accel', to: 'fuse', color: '#3b82f6' },
      { type: 'arrow', from: 'gyro', to: 'fuse', color: '#8b5cf6' },
      { type: 'arrow', from: 'fuse', to: 'output', color: '#10b981' },
    ],
  },
  'H07': {
    scene: 'robotView',
    title: '总线舵机与腿部机构',
    subtitle: 'PWM控制 · 角度范围 · 力矩限幅',
    sliders: [
      { key: 'hip_angle', label: '髋关节角(°)', min: -45, max: 45 },
      { key: 'knee_angle', label: '膝关节角(°)', min: -90, max: 90 },
    ],
    items: [
      { type: 'sensor', label: 'hip_servo', x: 60, y: 80 },
      { type: 'sensor', label: 'knee_servo', x: 60, y: 180 },
    ],
  },
  'H08': {
    scene: 'controlLoop',
    title: '实机 LQR · 限幅 · 急停',
    subtitle: '实机安全验证',
    sliders: [
      { key: 'torque_limit', label: '力矩限幅(N·m)', min: 0.1, max: 1, step: 0.05 },
    ],
    items: [],
  },
  'H09': {
    scene: 'architecture',
    title: 'WebSocket 遥测与安全',
    subtitle: '实时数据流 · 命令协议 · 新鲜度',
    sliders: [],
    items: [
      { type: 'layer', label: 'ESP32 WebSocket服务', y: 80, color: '#3b82f6' },
      { type: 'layer', label: '遥测数据流(IMU/编码器)', y: 180, color: '#8b5cf6' },
      { type: 'layer', label: '控制命令下行', y: 280, color: '#10b981' },
    ],
  },
  'H10': {
    scene: 'dataPipeline',
    title: 'Sim2Real 参数覆盖',
    subtitle: '参数辨识 · Sim2Real · 实机答辩',
    sliders: [],
    items: [
      { type: 'stage', id: 'identify', label: '实机参数辨识', x: 80, y: 180, w: 150 },
      { type: 'stage', id: 'map', label: 'Sim2Real映射', x: 280, y: 180, w: 150 },
      { type: 'stage', id: 'deploy', label: '实机部署验证', x: 480, y: 180, w: 150 },
      { type: 'stage', id: 'defense', label: '实机答辩', x: 680, y: 180, w: 130 },
      { type: 'arrow', from: 'identify', to: 'map', color: '#3b82f6' },
      { type: 'arrow', from: 'map', to: 'deploy', color: '#8b5cf6' },
      { type: 'arrow', from: 'deploy', to: 'defense', color: '#10b981' },
    ],
  },
}

const DENSE_CHAPTERS = new Set(
  Array.from({ length: 26 }, (_, index) => String(index + 12).padStart(2, '0')),
)

const DENSE_PARAMETER_DEFAULTS: Record<string, SliderDef> = {
  '16': { key: 'controllabilityRank', label: '可控性矩阵秩', min: 1, max: 4, step: 1 },
  '22': { key: 'sampleCount', label: '辨识样本数', min: 20, max: 500, step: 20 },
  '25': { key: 'actionScale', label: '动作缩放', min: 0.1, max: 1, step: 0.05 },
  '31': { key: 'bootstrapSamples', label: 'Bootstrap 重采样数', min: 100, max: 2000, step: 100 },
  '32': { key: 'commandRate', label: '高层命令频率 (Hz)', min: 1, max: 20, step: 1 },
  '33': { key: 'colorThreshold', label: '颜色检测阈值', min: 0.05, max: 0.95, step: 0.05 },
  '34': { key: 'commandTimeout', label: '命令超时 (ms)', min: 50, max: 1000, step: 50 },
  '35': { key: 'demoEpisodes', label: '示范回合数', min: 2, max: 20, step: 1 },
  '37': { key: 'stopDistance', label: '停车距离 (m)', min: 0.1, max: 2, step: 0.1 },
}

const CATEGORY_META: Record<AnimationCategory, { label: string; scene: InlineSceneType }> = {
  intuition: { label: '直觉机制', scene: 'mechanism' },
  parameter: { label: '公式与参数', scene: 'parameter' },
  comparison: { label: '正确与故障对比', scene: 'comparison' },
  evidence: { label: '真实证据与诊断', scene: 'evidence' },
}

function createCourseAnimation(
  chapterId: string,
  config: ChapterAnimationConfig,
  category: AnimationCategory,
): CourseAnimationEntry {
  const suffix = DENSE_CHAPTERS.has(chapterId) ? category : 'core'
  const id = `${chapterId.toLowerCase()}-${suffix}`
  const planned = /^H(?:0[2-9]|10)$/.test(chapterId)
  const firstSlider = config.sliders[0] ?? DENSE_PARAMETER_DEFAULTS[chapterId]
  const command = `python scripts/course_checkpoint.py --chapter ${chapterId} --seed 0 --no-viewer`
  const evidence: AnimationEvidence = planned
    ? { kind: 'concept', description: '规划章节概念示意，不计入验收证据' }
    : category === 'evidence'
      ? {
          kind: 'artifact',
          description: '固定 seed 的正式 checkpoint 图表',
          path: `outputs/plots/checkpoint_${chapterId}.png`,
          command,
        }
      : { kind: 'concept', description: '基于本章教程、配置与控制链路的概念示意' }

  return {
    id,
    chapterId,
    title: `${CATEGORY_META[category].label}：${config.title}`,
    anchor: `upkie-animation-${id}`,
    category,
    scene: CATEGORY_META[category].scene,
    playPolicy: 'once-in-view',
    evidence,
    chapterConfig: config,
    parameter: category === 'parameter'
      ? { ...firstSlider, initial: (firstSlider.min + firstSlider.max) / 2 }
      : undefined,
    conceptualOnly: planned,
  }
}

export const COURSE_ANIMATIONS: CourseAnimationEntry[] = Object.entries(CHAPTER_ANIMATIONS)
  .flatMap(([chapterId, config]) => {
    const categories: AnimationCategory[] = DENSE_CHAPTERS.has(chapterId)
      ? ['intuition', 'parameter', 'comparison', 'evidence']
      : ['intuition']
    return categories.map((category) => createCourseAnimation(chapterId, config, category))
  })

export const COURSE_ANIMATION_BY_ID: ReadonlyMap<string, CourseAnimationEntry> = new Map(
  COURSE_ANIMATIONS.map((entry) => [entry.id, entry]),
)

export function animationsForChapter(chapterId: string): CourseAnimationEntry[] {
  return COURSE_ANIMATIONS.filter((entry) => entry.chapterId === chapterId)
}
