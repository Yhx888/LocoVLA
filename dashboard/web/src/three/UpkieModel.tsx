import { useState, useCallback, useEffect, useRef, Component, type ReactNode } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
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
/*  Joint labels helper                                                 */
/* ------------------------------------------------------------------ */
function JointLabels({ show }: { show: boolean }) {
  const joints = [
    { label: '左髋', pos: [-0.22, 0.02, 0] },
    { label: '左膝', pos: [-0.22, -0.28, 0] },
    { label: '左轮', pos: [-0.22, -0.52, 0] },
    { label: '右髋', pos: [0.22, 0.02, 0] },
    { label: '右膝', pos: [0.22, -0.28, 0] },
    { label: '右轮', pos: [0.22, -0.52, 0] },
  ]

  if (!show) return null

  return (
    <group>
      {joints.map((j, i) => (
        <sprite key={i} position={new THREE.Vector3(j.pos[0], j.pos[1], j.pos[2] + 0.15)} scale={[0.12, 0.06, 1]}>
          <spriteMaterial
            attach="material"
            transparent
            opacity={0.9}
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
                ctx.fillText(j.label, 128, 32)
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
/*  Robot scene                                                         */
/* ------------------------------------------------------------------ */
function RobotScene({ jointAngles, autoRotate }: { jointAngles?: Record<string, number>; autoRotate?: boolean }) {
  const groupRef = useRef<THREE.Group>(null)
  const [showLabels, setShowLabels] = useState(false)

  const angles = jointAngles ?? {}

  const hipL = (angles.left_hip ?? 0)
  const kneeL = (angles.left_knee ?? 0)
  const hipR = (angles.right_hip ?? 0)
  const kneeR = (angles.right_knee ?? 0)

  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.5
    }
  })

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'l' || e.key === 'L') setShowLabels(prev => !prev)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const silver = '#b0b0b0'
  const darkGray = '#3a3a3a'
  const black = '#1a1a1a'

  return (
    <group ref={groupRef}>
      {/* Body / torso */}
      <mesh position={[0, 0.15, 0]}>
        <boxGeometry args={[0.4, 0.18, 0.2]} />
        <meshStandardMaterial color={darkGray} />
      </mesh>

      {/* Left leg */}
      <group position={[-0.22, 0.06, 0]}>
        <group rotation={[0, 0, hipL]}>
          <mesh position={[0, -0.15, 0]}>
            <cylinderGeometry args={[0.04, 0.06, 0.28, 8]} />
            <meshStandardMaterial color={silver} />
          </mesh>
          <group position={[0, -0.28, 0]}>
            <group rotation={[0, 0, kneeL]}>
              <mesh position={[0, -0.12, 0]}>
                <cylinderGeometry args={[0.04, 0.05, 0.22, 8]} />
                <meshStandardMaterial color={silver} />
              </mesh>
              <mesh position={[0, -0.2, 0]}>
                <cylinderGeometry args={[0.07, 0.07, 0.04, 12]} />
                <meshStandardMaterial color={black} />
              </mesh>
            </group>
          </group>
        </group>
      </group>

      {/* Right leg */}
      <group position={[0.22, 0.06, 0]}>
        <group rotation={[0, 0, hipR]}>
          <mesh position={[0, -0.15, 0]}>
            <cylinderGeometry args={[0.04, 0.06, 0.28, 8]} />
            <meshStandardMaterial color={silver} />
          </mesh>
          <group position={[0, -0.28, 0]}>
            <group rotation={[0, 0, kneeR]}>
              <mesh position={[0, -0.12, 0]}>
                <cylinderGeometry args={[0.04, 0.05, 0.22, 8]} />
                <meshStandardMaterial color={silver} />
              </mesh>
              <mesh position={[0, -0.2, 0]}>
                <cylinderGeometry args={[0.07, 0.07, 0.04, 12]} />
                <meshStandardMaterial color={black} />
              </mesh>
            </group>
          </group>
        </group>
      </group>

      <JointLabels show={showLabels} />
    </group>
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

function CameraResetter() {
  const { camera, gl } = useThree()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'r' || e.key === 'R') {
        camera.position.set(0.8, 0.6, 0.8)
        camera.lookAt(0, 0, 0)
        gl.domElement.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [camera, gl])
  return null
}

/* ------------------------------------------------------------------ */
/*  Main component                                                      */
/* ------------------------------------------------------------------ */
export default function UpkieModel({ jointAngles, autoRotate = true, height = '400px' }: UpkieModelProps) {
  return (
    <ErrorBoundary fallback={<UpkieModelFallback />}>
      <div style={{ width: '100%', height, position: 'relative', background: '#f0f0f0', borderRadius: 8, overflow: 'hidden' }}>
        <Canvas>
          <PerspectiveCamera makeDefault position={[0.8, 0.6, 0.8]} fov={40} />
          <CameraController />
          <CameraResetter />
          <RobotScene jointAngles={jointAngles} autoRotate={autoRotate} />
          <OrbitControls enablePan enableZoom />
        </Canvas>

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

        {/* Label toggle hint */}
        <span
          style={{
            position: 'absolute', bottom: 8, right: 8,
            padding: '4px 8px', fontSize: 11, borderRadius: 4,
            background: 'rgba(0,0,0,0.5)', color: '#fff',
          }}
        >
          按 L 显示/隐藏关节标签
        </span>
      </div>
    </ErrorBoundary>
  )
}
