import { useEffect, useRef } from 'react'
import { useReducedMotion } from 'motion/react'

/** Ornamento local: nenhuma informação da avaliação é enviada ou representada. */
export function JourneyScene() {
  const host = useRef<HTMLDivElement>(null)
  const reduced = useReducedMotion()
  useEffect(() => {
    const element = host.current
    if (!element || reduced || !window.WebGL2RenderingContext) return
    let disposed = false
    let release = () => {}
    void import('three').then(THREE => {
      if (disposed) return
      let renderer: InstanceType<typeof THREE.WebGLRenderer>
      try { renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true }) } catch { return }
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(38, 1, .1, 100)
      camera.position.z = 4
      const group = new THREE.Group()
      scene.add(group)
      const geometry = new THREE.IcosahedronGeometry(.28, 0)
      const material = new THREE.MeshBasicMaterial({ color: 0x9874e4, wireframe: true })
      const points = Array.from({ length: 9 }, (_, i) => new THREE.Vector3((i - 4) * .85, Math.sin(i * .6) * .7, Math.cos(i) * .5))
      points.forEach(position => { const node = new THREE.Mesh(geometry, material); node.position.copy(position); group.add(node) })
      const lineGeometry = new THREE.BufferGeometry().setFromPoints(points)
      const lineMaterial = new THREE.LineBasicMaterial({ color: 0x9874e4, transparent: true, opacity: .6 })
      group.add(new THREE.Line(lineGeometry, lineMaterial))
      element.appendChild(renderer.domElement)
      const resize = () => {
        const width = element.clientWidth, height = element.clientHeight
        if (!width || !height) return
        const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
        renderer.setSize(Math.round(width * ratio), Math.round(height * ratio), false)
        camera.aspect = width / height; camera.updateProjectionMatrix()
        renderer.render(scene, camera)
      }
      const observer = new ResizeObserver(resize)
      observer.observe(element); resize()
      let frame = 0
      const start = performance.now()
      const draw = (now: number) => {
        if (disposed || document.hidden) return
        const elapsed = Math.min((now - start) / 1000, 4)
        group.rotation.y = Math.sin(elapsed * .7) * .3
        group.rotation.z = Math.sin(elapsed) * .04
        group.children.forEach((node, i) => { if (node instanceof THREE.Mesh) node.rotation.y = elapsed * .5 + i })
        renderer.render(scene, camera)
        if (elapsed < 4) frame = requestAnimationFrame(draw)
      }
      frame = requestAnimationFrame(draw)
      release = () => { cancelAnimationFrame(frame); observer.disconnect(); geometry.dispose(); material.dispose(); lineGeometry.dispose(); lineMaterial.dispose(); renderer.dispose(); renderer.domElement.remove() }
    }).catch(() => { /* O ornamento CSS permanece disponível sem WebGL. */ })
    return () => { disposed = true; release() }
  }, [reduced])
  return <div className="journey-scene" ref={host} aria-hidden="true"><span/><span/><span/><span/></div>
}
