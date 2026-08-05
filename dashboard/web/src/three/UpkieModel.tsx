import { useState, useEffect, useRef, Component, type ReactNode, type MutableRefObject } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import URDFLoader from 'urdf-loader'
import type { URDFRobot } from 'urdf-loader'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import UpkieModelFallback from './UpkieModelFallback'

/* ------------------------------------------------------------------ */
/*  Error Boundary                                                      */
/* ------------------------------------------------------------------ */
class ErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode; fallback: ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  render() {
    if (this.state.hasError) return this.props.fallback
    return this.props.children
  }
}

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */
export interface UpkieModelProps {
  jointAngles?: Record<string, number>
  autoRotate?: boolean
  height?: string
}

/* ------------------------------------------------------------------ */
/*  真实 Upkie URDF 资产                                                */
/* ------------------------------------------------------------------ */
const URDF_URL = '/upkie/upkie_description/urdf/upkie.urdf'
const PACKAGE_ROOT = '/upkie/upkie_description'

const JOINT_NAMES = ['left_hip', 'left_knee', 'left_wheel', 'right_hip', 'right_knee', 'right_wheel'] as const

const JOINT_LABELS: Record<string, string> = {
  left_hip: '左髋',
  left_knee: '左膝',
  left_wheel: '左轮',
  right_hip: '右髋',
  right_knee: '右膝',
  right_wheel: '右轮',
}

// 关节 frame 不可用时的回退坐标（Y-up 空间，与手写几何体时代一致）
const FALLBACK_POSES: Record<string, [number, number, number]> = {
  left_hip: [-0.22, 0.02, 0],
  left_knee: [-0.22, -0.28, 0],
  left_wheel: [-0.22, -0.52, 0],
  right_hip: [0.22, 0.02, 0],
  right_knee: [0.22, -0.28, 0],
  right_wheel: [0.22, -0.52, 0],
}

/* ------------------------------------------------------------------ */
/*  Joint labels helper：常驻渲染，按 show 淡入淡出                      */
/*  位置取自真实模型关节 frame（局部坐标），frame 缺失时回退手写坐标      */
/* ------------------------------------------------------------------ */
function JointLabels({ show, positions }: { show: boolean; positions: Record<string, THREE.Vector3> }) {
  const items = JOINT_NAMES.map((name) => ({
    key: name,
    label: JOINT_LABELS[name],
    // 沿模型外侧抬高一点，避免标签被几何体遮挡
    pos: (positions[name] ?? new THREE.Vector3(...FALLBACK_POSES[name])).clone().add(new THREE.Vector3(0, 0.06, 0.14)),
  }))

  const materialRefs = useRef<(THREE.SpriteMaterial | null)[]>([])
  const targetOpacity = show ? 0.9 : 0

  // 透明度指数逼近目标值，避免标签瞬间出现/消失
  useFrame((_, delta) => {
    const damp = 1 - Math.exp(-delta * 10)
    for (const m of materialRefs.current) {
      if (!m) continue
      m.opacity += (targetOpacity - m.opacity) * damp
      m.visible = m.opacity > 0.02
    }
  })

  return (
    <group>
      {items.map((item, i) => (
        <sprite key={item.key} position={item.pos} scale={[0.12, 0.06, 1]}>
          <spriteMaterial
            ref={(el) => { materialRefs.current[i] = el }}
            attach="material"
            transparent
            opacity={0}
          >
            <canvasTexture
              attach="map"
              image={(() => {
                const c = document.createElement('canvas')
                c.width = 256; c.height = 64
                const ctx = c.getContext('2d')!
                ctx.fillStyle = '#1f2937'
                ctx.font = 'bold 28px system-ui, sans-serif'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                ctx.fillText(item.label, 128, 32)
                return c
              })()}
            />
          </spriteMaterial>
        </sprite>
      ))}
    </group>
  )
}

/* ------------------------------------------------------------------ */
/*  Robot scene：渲染真实 URDF 模型                                      */
/* ------------------------------------------------------------------ */
function RobotScene({
  robot,
  jointAngles,
  autoRotate,
  homeRef,
  showLabels,
}: {
  robot: URDFRobot
  jointAngles?: Record<string, number>
  autoRotate?: boolean
  homeRef: MutableRefObject<{ pos: THREE.Vector3; lookAt: THREE.Vector3 }>
  showLabels: boolean
}) {
  const groupRef = useRef<THREE.Group>(null)
  const controlsRef = useRef<OrbitControlsImpl>(null)
  const { camera } = useThree()
  const [labelPoses, setLabelPoses] = useState<Record<string, THREE.Vector3> | null>(null)

  // 自动旋转：目标角匀速前进，当前角指数阻尼逼近；
  // 鼠标拖拽视角时目标暂停前进，松手后平滑恢复
  const rotTargetRef = useRef(0)
  const rotCurrentRef = useRef(0)
  const interactingRef = useRef(false)

  // 加载完成后只执行一次：坐标系修正、放开轮子限位、标签定位、相机适配
  useEffect(() => {
    // urdf-loader 不做 Z-up → Y-up 转换（其文档明确"instanced without frame transforms"）。
    // Upkie URDF 的 +z 是"上"，绕 X 轴旋转 -90° 后 +z 指向 three.js 的 +y
    robot.rotation.x = -Math.PI / 2

    // wheel 关节在 URDF 中是 revolute 但 limit 无 lower/upper，
    // urdf-loader 会把 limit 解析为 [0, 0]，不放开限位则非零角度全被钳到 0
    for (const name of ['left_wheel', 'right_wheel']) {
      const joint = robot.joints[name]
      if (joint) joint.ignoreLimits = true
    }

    // 从真实模型关节 frame 读取位置，转成 group 局部坐标
    // （加载完成时 autoRotate 可能已转了几帧，局部坐标才与标签同空间）
    const poses: Record<string, THREE.Vector3> = {}
    if (groupRef.current) {
      groupRef.current.updateWorldMatrix(true, false)
      robot.updateMatrixWorld(true)
      for (const name of JOINT_NAMES) {
        const frame = robot.getFrame(name)
        if (frame) {
          const v = frame.getWorldPosition(new THREE.Vector3())
          groupRef.current.worldToLocal(v)
          poses[name] = v
        }
      }
      if (Object.keys(poses).length > 0) setLabelPoses(poses)
    }

    // 相机适配：按真实模型包围盒动态计算合适距离，替代手写几何体的固定值
    const box = new THREE.Box3().setFromObject(robot)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const radius = Math.max(size.x, size.y, size.z)
    const dist = radius * 2.2
    const pos = center.clone().add(new THREE.Vector3(dist * 0.68, dist * 0.48, dist * 0.68))
    camera.position.copy(pos)
    camera.lookAt(center)
    homeRef.current.pos.copy(pos)
    homeRef.current.lookAt.copy(center)
    if (controlsRef.current) controlsRef.current.target.copy(center)

    console.log('[UpkieModel] 真实 URDF 模型已加载', {
      robot: robot.robotName,
      boundingBox: { size: size.toArray(), center: center.toArray() },
      joints: Object.fromEntries(JOINT_NAMES.map((n) => {
        const j = robot.joints[n]
        return [n, j ? { type: j.jointType, lower: j.limit.lower, upper: j.limit.upper } : null]
      })),
    })
  }, [robot, camera, homeRef])

  useFrame((_, delta) => {
    // 自动旋转（阻尼逼近）
    if (groupRef.current) {
      if (autoRotate && !interactingRef.current) {
        rotTargetRef.current += delta * 0.5
      }
      const damp = 1 - Math.exp(-delta * 4)
      rotCurrentRef.current += (rotTargetRef.current - rotCurrentRef.current) * damp
      groupRef.current.rotation.y = rotCurrentRef.current
    }

    // 关节驱动：写入真实 URDF 关节（弧度），setJointValue 自动钳制限位
    const angles = jointAngles ?? {}
    for (const name of JOINT_NAMES) {
      const joint = robot.joints[name]
      if (!joint) continue
      joint.setJointValue(angles[name] ?? 0)
    }
  })

  return (
    <>
      <group ref={groupRef}>
        <primitive object={robot} />
        {labelPoses && <JointLabels show={showLabels} positions={labelPoses} />}
      </group>

      {/* OrbitControls 放这里以共享 interactingRef：拖拽开始/结束暂停自动旋转 */}
      <OrbitControls
        ref={controlsRef}
        enablePan
        enableZoom
        onStart={() => { interactingRef.current = true }}
        onEnd={() => { interactingRef.current = false }}
      />
    </>
  )
}

/* ------------------------------------------------------------------ */
/*  Camera controller                                                   */
/* ------------------------------------------------------------------ */
function CameraController() {
  return (
    <group>
      <ambientLight intensity={0.6} />
      <directionalLight position={[2, 3, 2]} intensity={0.8} />
      <directionalLight position={[-1, 1, -1]} intensity={0.3} />
    </group>
  )
}

function CameraResetter({ homeRef }: { homeRef: MutableRefObject<{ pos: THREE.Vector3; lookAt: THREE.Vector3 }> }) {
  const { camera, gl } = useThree()
  const resettingRef = useRef(false)

  // 按 R 后镜头阻尼滑回默认位，而非瞬间跳变
  useFrame((_, delta) => {
    if (!resettingRef.current) return
    const damp = 1 - Math.exp(-delta * 8)
    camera.position.lerp(homeRef.current.pos, damp)
    camera.lookAt(homeRef.current.lookAt)
    if (camera.position.distanceTo(homeRef.current.pos) < 0.002) {
      camera.position.copy(homeRef.current.pos)
      camera.lookAt(homeRef.current.lookAt)
      resettingRef.current = false
    }
  })

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'r' || e.key === 'R') {
        resettingRef.current = true
        gl.domElement.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [camera, gl])
  return null
}

/* ------------------------------------------------------------------ */
/*  Main component（加载状态机，失败抛错由 ErrorBoundary 兜底）           */
/* ------------------------------------------------------------------ */
export default function UpkieModel({ jointAngles, autoRotate = true, height = '400px' }: UpkieModelProps) {
  return (
    <ErrorBoundary fallback={<UpkieModelFallback />}>
      <UpkieModelInner jointAngles={jointAngles} autoRotate={autoRotate} height={height} />
    </ErrorBoundary>
  )
}

function UpkieModelInner({ jointAngles, autoRotate = true, height = '400px' }: UpkieModelProps) {
  const [robot, setRobot] = useState<URDFRobot | null>(null)
  const [loadError, setLoadError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [showLabels, setShowLabels] = useState(false)
  const homeRef = useRef({ pos: new THREE.Vector3(0.8, 0.6, 0.8), lookAt: new THREE.Vector3(0, 0, 0) })

  useEffect(() => {
    let cancelled = false
    const loader = new URDFLoader()
    loader.packages = { upkie_description: PACKAGE_ROOT }
    loader
      .loadAsync(URDF_URL)
      .then((loaded) => {
        if (cancelled) return
        setRobot(loaded)
        setLoading(false)
      })
      .catch((err) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err : new Error(String(err)))
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // 加载失败：在 render 阶段抛错，由外层 ErrorBoundary 兜底
  if (loadError) throw loadError

  return (
    <div style={{ width: '100%', height, position: 'relative', background: '#f0f0f0', borderRadius: 8, overflow: 'hidden' }}>
      <Canvas>
        <PerspectiveCamera makeDefault position={[0.8, 0.6, 0.8]} fov={40} />
        <CameraController />
        <CameraResetter homeRef={homeRef} />
        {robot && (
          <RobotScene
            robot={robot}
            jointAngles={jointAngles}
            autoRotate={autoRotate}
            homeRef={homeRef}
            showLabels={showLabels}
          />
        )}
      </Canvas>

      {/* 加载占位 */}
      {loading && (
        <div
          style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#6b7280', fontSize: 13, pointerEvents: 'none',
          }}
        >
          正在加载 Upkie 模型…
        </div>
      )}

      {/* Camera reset button */}
      <button
        onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r' }))}
        style={{
          position: 'absolute', bottom: 8, left: 8,
          padding: '4px 10px', fontSize: 12, borderRadius: 4,
          border: '1px solid #d1d5db', background: '#fff',
          cursor: 'pointer', lineHeight: '22px',
        }}
        title="重置视角 (R)"
      >
        ⟲ 重置
      </button>

      {/* Label toggle button */}
      <button
        onClick={() => setShowLabels(v => !v)}
        style={{
          position: 'absolute', bottom: 8, right: 8,
          padding: '4px 10px', fontSize: 12, borderRadius: 4,
          border: '1px solid #d1d5db', background: '#fff',
          cursor: 'pointer', lineHeight: '22px',
        }}
        title="显示/隐藏关节标签"
      >
        标签
      </button>
    </div>
  )
}
