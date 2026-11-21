import './characters-studio.css'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const host = document.getElementById('stage')!
const status = document.getElementById('status')!
const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button'))
buttons.forEach(button => { button.disabled = true })
const reduced = matchMedia('(prefers-reduced-motion: reduce)')

async function start() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.15
  host.appendChild(renderer.domElement)
  host.tabIndex = 0
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(32, 1, .1, 80)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false; controls.enableDamping = false
  controls.minDistance = 4; controls.maxDistance = 24
  controls.minPolarAngle = .65; controls.maxPolarAngle = Math.PI / 2 + .12
  scene.add(new THREE.HemisphereLight(0xf5f2ff, 0x8b839c, 2.3))
  const key = new THREE.DirectionalLight(0xffedd9, 3.2)
  key.position.set(-4, 7, 6);key.castShadow = true;key.shadow.mapSize.set(1024,1024)
  key.shadow.camera.left=-5;key.shadow.camera.right=5;key.shadow.camera.top=6;key.shadow.camera.bottom=-5
  key.shadow.bias=-.0004;key.shadow.normalBias=.025;scene.add(key)
  const fill = new THREE.DirectionalLight(0xd2caff, 2.1);fill.position.set(4,4,-4);scene.add(fill)
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({opacity:.14}))
  floor.rotation.x=-Math.PI/2;floor.position.y=-.015;floor.receiveShadow=true;scene.add(floor)
  let frame=0, playing=false, remaining=0, previous=0, currentName='', disposed=false
  const render=()=>{ if(!disposed) renderer.render(scene,camera) }
  const loader=new GLTFLoader()
  const loaded=await Promise.all([
    loader.loadAsync('/models/profissional-blazer.glb'),
    loader.loadAsync('/models/profissional-camisa.glb'),
  ])
  const models=loaded.map(item=>{
    item.scene.traverse(object=>{ if(object instanceof THREE.Mesh){object.castShadow=true;object.receiveShadow=true} })
    scene.add(item.scene)
    return {root:item.scene,mixer:new THREE.AnimationMixer(item.scene),clips:item.animations,actions:[] as THREE.AnimationAction[]}
  })
  function resetPose() {
    playing=false;cancelAnimationFrame(frame)
    models.forEach(model=>{model.mixer.stopAllAction();model.actions.forEach(action=>model.mixer.uncacheClip(action.getClip()));model.actions=[];model.mixer.update(0)})
    status.textContent='Pose inicial';render()
  }
  let selection='both'
  function fit() {
    const width=host.clientWidth,height=host.clientHeight
    renderer.setSize(width,height,false);camera.aspect=width/height
    const extent=selection==='both'?6.2:3.3
    const distance=Math.max(4.7,extent/camera.aspect)/2/Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*1.12
    camera.position.set(.3,2.4,distance);controls.target.set(0,2.05,0)
    camera.updateProjectionMatrix();controls.update();render()
  }
  function choose(value:string) {
    resetPose();selection=value
    models.forEach((model,i)=>{model.root.visible=value==='both'||(value==='woman'?i===0:i===1);model.root.position.x=value==='both'?(i===0?-1.5:1.5):0})
    document.querySelectorAll<HTMLButtonElement>('[data-model]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.model===value)))
    fit()
  }
  function animate(now:number) {
    if(disposed||!playing||document.hidden)return
    const delta=Math.max(0,Math.min((now-previous)/1000,.1));previous=now;remaining-=delta
    models.forEach(model=>{
      model.mixer.update(delta)
      model.actions=model.actions.filter(action=>{
        if(action.getEffectiveWeight()>0||action.time===0)return true
        action.stop();model.mixer.uncacheClip(action.getClip());return false
      })
    });render()
    if(remaining>0)frame=requestAnimationFrame(animate)
    else {resetPose();status.textContent='Movimento concluído com retorno suave'}
  }
  function stop() {
    if(!playing)return
    models.forEach(model=>model.actions.forEach(action=>action.setEffectiveWeight(action.getEffectiveWeight()).fadeOut(.5)))
    remaining=.55;currentName='';status.textContent='Retornando suavemente à pose inicial'
  }
  function play(name:string) {
    if(playing&&currentName===name)return
    cancelAnimationFrame(frame)
    let duration=0
    models.forEach(model=>{
      model.actions.forEach(action=>action.setEffectiveWeight(action.getEffectiveWeight()).fadeOut(.45))
      const clip=model.clips.find(clip=>clip.name===name)!
      const action=model.mixer.clipAction(clip.clone())
      action.reset().setEffectiveWeight(1).setEffectiveTimeScale(1).fadeIn(.45)
      action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play()
      model.actions=model.actions.filter(previous=>previous!==action);model.actions.push(action)
      duration=Math.max(duration,clip.duration)
    })
    playing=true;currentName=name;previous=performance.now();remaining=duration+.12
    status.textContent=`${name} · movimento suave`;frame=requestAnimationFrame(animate)
  }
  const onKey=(event:KeyboardEvent)=>{
    if(!['ArrowLeft','ArrowRight'].includes(event.key))return
    event.preventDefault()
    const offset=camera.position.clone().sub(controls.target)
    offset.applyAxisAngle(new THREE.Vector3(0,1,0),event.key==='ArrowLeft'?.15:-.15)
    camera.position.copy(controls.target).add(offset);controls.update();render()
  }
  host.addEventListener('keydown',onKey)
  controls.addEventListener('change',render)
  const observer=new ResizeObserver(fit);observer.observe(host)
  const onVisibility=()=>{if(document.hidden||reduced.matches)resetPose()}
  document.addEventListener('visibilitychange',onVisibility);reduced.addEventListener('change',onVisibility)
  document.querySelectorAll<HTMLButtonElement>('[data-model]').forEach(button=>button.addEventListener('click',()=>choose(button.dataset.model!)))
  document.querySelectorAll<HTMLButtonElement>('[data-animation]').forEach(button=>button.addEventListener('click',()=>play(button.dataset.animation!)))
  document.getElementById('stop')!.addEventListener('click',stop)
  buttons.forEach(button=>{button.disabled=false})
  choose(innerWidth<700?'woman':'both')
  status.textContent='Modelos 3D carregados'
  if(!reduced.matches)play('Acenar')
  window.addEventListener('pagehide',()=>{
    resetPose();disposed=true;observer.disconnect();controls.dispose();host.removeEventListener('keydown',onKey)
    document.removeEventListener('visibilitychange',onVisibility);reduced.removeEventListener('change',onVisibility)
    const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>()
    scene.traverse(object=>{if(object instanceof THREE.Mesh){geometries.add(object.geometry);(Array.isArray(object.material)?object.material:[object.material]).forEach(material=>materials.add(material))}})
    geometries.forEach(geometry=>geometry.dispose());materials.forEach(material=>material.dispose());renderer.dispose()
  },{once:true})
}
void start().catch(()=>{
  host.replaceChildren()
  const fallback=document.createElement('p');fallback.className='fallback'
  fallback.textContent='A visualização 3D não está disponível neste navegador. Você pode baixar os modelos e abri-los em um visualizador compatível com GLB.'
  host.appendChild(fallback);status.textContent='Prévia indisponível'
})
