import { readFile, writeFile } from 'node:fs/promises'
import validator from 'gltf-validator'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const directory = new URL('../public/models/', import.meta.url)
const manifest = JSON.parse(await readFile(new URL('manifest.json', directory), 'utf8'))
const reports = []
for (const item of manifest) {
  const data = await readFile(new URL(item.file, directory))
  const validation = await validator.validateBytes(new Uint8Array(data), { uri: item.file })
  if (validation.issues.numErrors || validation.issues.numWarnings) throw new Error(`${item.file}: ${JSON.stringify(validation.issues)}`)
  const loaded = await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '')
  if (loaded.animations.length !== 4) throw new Error('Faltam animações')
  const mixer = new THREE.AnimationMixer(loaded.scene)
  const shoulder = loaded.scene.getObjectByName('ShoulderRight')
  const original = shoulder.quaternion.clone()
  mixer.clipAction(loaded.animations.find(clip => clip.name === 'Acenar')).play()
  mixer.update(1.8)
  if (shoulder.quaternion.angleTo(original) < .01) throw new Error('A animação não move a articulação')
  mixer.stopAllAction()
  if (shoulder.quaternion.angleTo(original) > .001) throw new Error('A pose não foi restaurada')
  for (const clip of loaded.animations) {
    mixer.clipAction(clip).play(); mixer.update(clip.duration / 2)
    loaded.scene.updateMatrixWorld(true)
    loaded.scene.traverse(node => { if (!node.matrixWorld.elements.every(Number.isFinite)) throw new Error('Transformação inválida') })
    mixer.stopAllAction()
  }
  let maxFrameAngle=0
  for(const clip of loaded.animations) {
    for(const track of clip.tracks.filter(track=>track.name.endsWith('.quaternion'))) {
      const v=track.values
      const first=new THREE.Quaternion().fromArray(v,0).normalize(),last=new THREE.Quaternion().fromArray(v,v.length-4).normalize()
      if(first.angleTo(last)>.0001) throw new Error('Pose final difere da inicial')
      for(let i=4;i<v.length;i+=4) {
        const step=new THREE.Quaternion().fromArray(v,i-4).normalize().angleTo(new THREE.Quaternion().fromArray(v,i).normalize())
        maxFrameAngle=Math.max(maxFrameAngle,step)
        if(step>.065)throw new Error('Descontinuidade angular entre frames')
      }
      const startStep=first.angleTo(new THREE.Quaternion().fromArray(v,4).normalize())
      if(startStep>.0004)throw new Error('Arranque sem aceleração suave')
    }
    if(clip.name==='Respirar') {
      const position=clip.tracks.find(track=>track.name==='Character.position')
      if([...position.values].some(value=>value!==0))throw new Error('Respiração desloca os pés')
    }
  }
  const report = { file: item.file, bytes: data.byteLength, errors: validation.issues.numErrors,
    warnings: validation.issues.numWarnings, infos: validation.issues.numInfos,
    animatedJointVerified: true, smoothStartAndReturnVerified: true, maxFrameAngleDegrees: maxFrameAngle*180/Math.PI, clips: loaded.animations.map(clip => clip.name) }
  reports.push(report)
}
await writeFile(new URL('validation.json', directory), JSON.stringify(reports, null, 2) + '\n')
console.log(JSON.stringify(reports, null, 2))
