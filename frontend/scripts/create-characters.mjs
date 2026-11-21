import * as T from 'three'
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { writeFile, readFile, mkdir } from 'node:fs/promises'

// GLTFExporter uses the browser FileReader API only to assemble the binary Blob.
globalThis.FileReader = class {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then(result => { this.result = result; this.onloadend?.() }) }
  readAsDataURL(blob) { blob.arrayBuffer().then(result => { this.result = `data:${blob.type};base64,${Buffer.from(result).toString('base64')}`; this.onloadend?.() }) }
}

const out = new URL('../public/models/', import.meta.url)
await mkdir(out, { recursive: true })
const sphere = new T.SphereGeometry(1, 24, 18)
const materials = {}
function material(name, color, roughness = .6, metalness = 0) {
  return materials[name] ??= new T.MeshStandardMaterial({ name, color, roughness, metalness })
}
const skin = material('Pele', '#e9b091', .7)
const blush = material('Bochechas', '#dd947f', .8)
const white = material('Marfim', '#fff5e6', .65)
const eyeWhite = material('Olhos_branco', '#fffdf4', .3)
const iris = material('Olhos_castanho', '#714027', .3)
const black = material('Pupilas', '#211c24', .25)
const hair = material('Cabelo_castanho', '#402922', .56)
const hairLight = material('Cabelo_mechas', '#684337', .6)
const navy = material('Azul_SkillBridge', '#25365d', .7)
const violet = material('Violeta_SkillBridge', '#8263bd', .6)
const dark = material('Sapatos', '#302b3c', .45)
const leather = material('Maleta', '#77513c', .52)
const gold = material('Metal_dourado', '#cba86c', .32, .65)
const smile = material('Sorriso', '#8c453c', .7)

function group(parent, name, position = [0,0,0]) {
  const g = new T.Group(); g.name = name; g.position.set(...position); parent.add(g); return g
}
function mesh(parent, geometry, mat, position = [0,0,0], scale = [1,1,1]) {
  const m = new T.Mesh(geometry, mat); m.position.set(...position); m.scale.set(...scale)
  m.castShadow = true; m.receiveShadow = true; parent.add(m); return m
}
const ball = (parent, mat, p, scale) => mesh(parent,sphere,mat,p,scale)
function tube(parent, points, radius, mat, segments = 24) {
  const curve = new T.CatmullRomCurve3(points.map(p => new T.Vector3(...p)))
  return mesh(parent,new T.TubeGeometry(curve,segments,radius,8,false),mat)
}
function shape(parent, points, mat, z, depth = .018) {
  const path = new T.Shape(); path.moveTo(...points[0]); points.slice(1).forEach(p => path.lineTo(...p)); path.closePath()
  return mesh(parent,new T.ExtrudeGeometry(path,{depth,bevelEnabled:false}),mat,[0,0,z])
}
function lock(parent, points, radius, mat) {
  const curve = new T.CatmullRomCurve3(points.map(p => new T.Vector3(...p)))
  const frames = curve.computeFrenetFrames(24,false), vertices=[], indices=[], uv=[]
  for(let i=0;i<=24;i++) {
    const t=i/24, center=curve.getPointAt(t), r=radius*(.12+.88*Math.pow(Math.sin(Math.PI*t),.35))
    for(let j=0;j<=8;j++) {
      const a=j/8*Math.PI*2
      const v=center.clone().addScaledVector(frames.normals[i],Math.cos(a)*r).addScaledVector(frames.binormals[i],Math.sin(a)*r)
      vertices.push(v.x,v.y,v.z);uv.push(t,j/8)
      if(i<24&&j<8){const k=i*9+j;indices.push(k,k+1,k+9,k+1,k+10,k+9)}
    }
  }
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.setIndex(indices);geo.computeVertexNormals()
  return mesh(parent,geo,mat)
}
function roundedBox(parent, mat, position, scale) {
  // Capsule-like silhouette with a bevelled rectangular profile.
  const path=new T.Shape(), r=.12
  path.moveTo(-.5+r,-.5);path.lineTo(.5-r,-.5);path.quadraticCurveTo(.5,-.5,.5,-.5+r)
  path.lineTo(.5,.5-r);path.quadraticCurveTo(.5,.5,.5-r,.5);path.lineTo(-.5+r,.5)
  path.quadraticCurveTo(-.5,.5,-.5,.5-r);path.lineTo(-.5,-.5+r);path.quadraticCurveTo(-.5,-.5,-.5+r,-.5)
  const geo=new T.ExtrudeGeometry(path,{depth:1,bevelEnabled:true,bevelSize:.04,bevelThickness:.04,bevelSegments:3,steps:1,curveSegments:6});geo.translate(0,0,-.5)
  return mesh(parent,geo,mat,position,scale)
}
function briefcase(parent) {
  const g=group(parent,'Maleta',[0,-.43,.04])
  roundedBox(g,leather,[0,0,0],[.60,.64,.23])
  roundedBox(g,hairLight,[0,.02,.127],[.51,.48,.018])
  tube(g,[[-.13,.33,0],[-.12,.45,0],[.12,.45,0],[.13,.33,0]],.026,dark)
  for(const x of [-.18,.18]) roundedBox(g,gold,[x,.19,.15],[.065,.09,.02])
  tube(g,[[-.27,.10,.13],[0,.08,.14],[.27,.10,.13]],.009,gold)
}
function hand(parent) {
  ball(parent,skin,[0,-.07,0],[.12,.14,.075])
  for(let i=0;i<4;i++) ball(parent,skin,[-.075+i*.049,-.16,0],[.027,.08,.034])
  const thumb=ball(parent,skin,[-.11,-.05,.025],[.047,.085,.045]);thumb.rotation.z=-.55
}
function arm(body, side, feminine) {
  const s=side==='Right'?1:-1
  const shoulder=group(body,`Shoulder${side}`,[s*.43,2.40,0]); shoulder.rotation.z=s===1?1.30:-.13
  ball(shoulder,feminine?navy:white,[0,-.22,0],[.15,.28,.16])
  const elbow=group(shoulder,`Elbow${side}`,[0,-.43,0]); elbow.rotation.z=s===1?1.45:0
  ball(elbow,feminine?navy:skin,[0,-.16,0],[.115,.22,.12])
  if(!feminine) ball(elbow,white,[0,.005,0],[.135,.07,.135])
  else ball(elbow,white,[0,-.33,0],[.105,.045,.105])
  const wrist=group(elbow,`Wrist${side}`,[0,-.36,0]);hand(wrist)
  if(s===-1) briefcase(wrist)
  return shoulder
}
function leg(body, side, feminine) {
  const s=side==='Right'?1:-1
  const hip=group(body,`Hip${side}`,[s*.18,1.24,0])
  mesh(hip,new T.CylinderGeometry(feminine?.12:.155,feminine?.105:.13,.60,20),feminine?dark:navy,[0,-.30,0]);ball(hip,feminine?dark:navy,[0,-.59,0],[.12,.12,.12])
  const knee=group(hip,`Knee${side}`,[0,-.60,0])
  mesh(knee,new T.CylinderGeometry(.115,.095,.43,20),feminine?dark:navy,[0,-.20,0])
  const shoe=ball(knee,dark,[0,-.48,.11],[.16,.105,.27])
  ball(knee,navy,[0,-.54,.11],[.165,.035,.275])
  if(feminine) ball(knee,gold,[0,-.43,.28],[.04,.025,.025])
  shoe.name=`Shoe${side}`
}
function head(body, feminine) {
  const h=group(body,'Head',[0,3.43,0])
  ball(h,skin,[0,0,0],[.72,.79,.61])
  for(const s of [-1,1]) {
    ball(h,skin,[s*.71,-.02,0],[.12,.18,.10]);ball(h,blush,[s*.755,-.02,.065],[.038,.10,.03])
    const eye=group(h,s===-1?'EyeLeft':'EyeRight',[s*.275,.09,.537])
    ball(eye,eyeWhite,[0,0,0],[.205,.235,.075]);ball(eye,iris,[s*-.014,-.005,.068],[.125,.16,.035])
    ball(eye,black,[s*-.014,-.005,.096],[.077,.112,.016]);ball(eye,eyeWhite,[-.04,.065,.117],[.032,.041,.013])
    ball(eye,eyeWhite,[.035,-.055,.115],[.013,.018,.008])
    tube(h,[[s*.10,.40,.50],[s*.25,.44,.52],[s*.43,.38,.45]],feminine?.023:.035,hair)
    if(feminine) tube(h,[[s*.12,.24,.568],[s*.28,.32,.57],[s*.44,.24,.51]],.018,hair)
    ball(h,blush,[s*.43,-.18,.50],[.13,.065,.018])
  }
  ball(h,skin,[0,-.10,.625],[.105,.11,.12])
  const mouth=new T.Shape(); mouth.moveTo(-.23,-.30);mouth.quadraticCurveTo(0,-.39,.23,-.30);mouth.quadraticCurveTo(0,-.60,-.23,-.30)
  mesh(h,new T.ExtrudeGeometry(mouth,{depth:.018,bevelEnabled:false}),smile,[0,0,.555])
  const teeth=new T.Shape();teeth.moveTo(-.185,-.326);teeth.quadraticCurveTo(0,-.39,.185,-.326);teeth.quadraticCurveTo(0,-.445,-.185,-.326)
  mesh(h,new T.ShapeGeometry(teeth),eyeWhite,[0,0,.576])
  const cap=new T.SphereGeometry(1,28,16,0,Math.PI*2,0,1.05)
  mesh(h,cap,hair,[0,.04,-.035],[.77,.82,.66])
  if(feminine) {
    ball(h,hair,[0,-.12,-.32],[.78,.99,.38])
    for(let i=0;i<5;i++) {
      const x=-.66-i*.026, z=.04-i*.075
      lock(h,[[.18,.74,z],[x,.51,z+.24],[x-.10,-.17,z+.14],[x+.08,-.81,z-.03],[x+.30,-.95,z-.1]],.16,hair)
    }
    for(let i=0;i<4;i++) lock(h,[[.12,.75,-.12-i*.10],[.65,.52,-.06-i*.10],[.76,-.35,-.04-i*.10],[.66,-.91,-.1-i*.1],[.86,-.88,-.1-i*.1]],.17,hair)
    for(let i=0;i<4;i++) lock(h,[[.35,.72,.12+i*.02],[-.14,.75,.50],[-.57,.40,.54-i*.045],[-.67,-.10,.28-i*.03]],.12,hairLight)
  } else {
    ball(h,hair,[0,.25,-.28],[.74,.55,.42])
    const sweep=ball(h,hair,[-.10,.65,.34],[.64,.23,.29]);sweep.rotation.z=.16
    const top=ball(h,hair,[.15,.76,.08],[.55,.20,.30]);top.rotation.z=-.13
    for(let i=0;i<5;i++) {
      const x=-.49+i*.19
      lock(h,[[x-.10,.50,.48],[x-.16,.69,.54],[x+.12,.83,.28],[x+.25,.72,.03]],.065,i%2===0?hairLight:hair)
    }
    for(const s of [-1,1]) ball(h,hair,[s*.65,.32,.07],[.11,.28,.18])
  }
}
// Sample smooth analytic curves at 60 Hz: no piecewise-linear pose changes.
const smooth = x => { const t=T.MathUtils.clamp(x,0,1); return t*t*t*(t*(t*6-15)+10) }
function motionClips() {
  return ['Acenar','Respirar','Celebrar','Caminhar'].map(name=>{
    const duration=name==='Caminhar'?5.6:name==='Respirar'?5:4.8
    const times=Array.from({length:Math.round(duration*60)+1},(_,i)=>i/60)
    const rotations=['Character','Head','ShoulderRight','ElbowRight','WristRight','ShoulderLeft','ElbowLeft','HipLeft','HipRight','KneeLeft','KneeRight','ShoeLeft','ShoeRight']
    const values=Object.fromEntries(rotations.map(key=>[key,[]]))
    const positions=[],scales=[]
    for(const t of times) {
      const e=smooth(t/.8)*smooth((duration-t)/.9)
      const cycle=Math.sin(2*Math.PI*(t-.8)/1.3), swing=Math.sin(2*Math.PI*(t-.8)/1.15)
      const angles=Object.fromEntries(rotations.map(key=>[key,[0,0,0]]))
      angles.ShoulderRight=[0,0,1.30];angles.ElbowRight=[0,0,1.45];angles.ShoulderLeft=[0,0,-.13]
      let rise=0, breath=0
      if(name==='Acenar') {
        angles.ShoulderRight=[.04*e,.025*e,1.30+.065*e*cycle]
        angles.ElbowRight=[.035*e,0,1.45+.11*e*Math.sin(2*Math.PI*(t-.9)/1.3)]
        angles.WristRight=[0,.10*e, .24*e*Math.sin(2*Math.PI*(t-1)/.75)]
        angles.Head=[0,-.055*e,.028*e]
      } else if(name==='Respirar') {
        breath=.014*e*Math.sin(Math.PI*t/duration)**2
        angles.Head=[.012*e*Math.sin(Math.PI*t/duration),.018*e*Math.sin(2*Math.PI*t/duration),0]
        angles.ShoulderRight=[0,0,1.30+.012*e*Math.sin(2*Math.PI*t/duration)]
      } else if(name==='Celebrar') {
        angles.ShoulderRight=[-.05*e,.08*e,1.30+.57*e+.06*e*cycle]
        angles.ElbowRight=[0,0,1.45-.22*e+.08*e*cycle]
        angles.WristRight=[0,0,.13*e*cycle]
        angles.Head=[-.045*e,.035*e*Math.sin(2*Math.PI*t/2.4),-.028*e*cycle]
        angles.ShoulderLeft=[.035*e*cycle,0,-.13]
      } else {
        angles.HipLeft=[.17*e*swing,0,0];angles.HipRight=[-.17*e*swing,0,0]
        angles.KneeLeft=[.25*e*Math.max(0,-swing)**2,0,0]
        angles.KneeRight=[.25*e*Math.max(0,swing)**2,0,0]
        angles.ShoeLeft=[-.06*e*swing,0,0];angles.ShoeRight=[.06*e*swing,0,0]
        angles.ShoulderLeft=[-.09*e*swing,0,-.13]
        angles.ShoulderRight=[.12*e*swing,0,1.30*(1-e)+.06*e]
        angles.ElbowRight=[0,0,1.45*(1-e)+.16*e]
        angles.Character=[0,.025*e*swing,0]
        angles.Head=[0,-.020*e*swing,0]
        rise=.012*e*Math.sin(2*Math.PI*(t-.8)/1.15)**2
      }
      for(const key of rotations) values[key].push(...new T.Quaternion().setFromEuler(new T.Euler(...angles[key])).toArray())
      positions.push(0,rise,0);scales.push(.43,.60*(1+breath),.27)
    }
    const tracks=rotations.map(key=>new T.QuaternionKeyframeTrack(`${key}.quaternion`,times,values[key]))
    tracks.push(new T.VectorKeyframeTrack('Character.position',times,positions),new T.VectorKeyframeTrack('Torso.scale',times,scales))
    return new T.AnimationClip(name,duration,tracks)
  })
}
function build(feminine) {
  const scene=new T.Scene();scene.name=feminine?'SkillBridge_Profissional':'SkillBridge_Profissional_Camisa'
  scene.userData={title:feminine?'Profissional de blazer':'Profissional de camisa',version:'1.1',creation:'Modelagem procedural original para SkillBridge; inspirada nas referências fornecidas.',rig:'Hierarquia de articulações rígidas; sem skinning ou rig facial.'}
  const body=group(scene,'Character')
  ball(body,skin,[0,2.70,0],[.14,.20,.14])
  ball(body,feminine?navy:white,[0,1.98,0],[.43,.60,.27]).name='Torso'
  if(feminine) {
    mesh(body,new T.CylinderGeometry(.30,.43,.49,28),navy,[0,1.37,0])
    shape(body,[[-.22,2.50],[.22,2.50],[.10,2.04],[-.10,2.04]],white,.25)
    shape(body,[[-.25,2.50],[-.04,2.10],[-.27,2.25],[-.34,2.40]],violet,.275)
    shape(body,[[.25,2.50],[.04,2.10],[.27,2.25],[.34,2.40]],violet,.275)
    for(const y of [1.77,1.95]) ball(body,gold,[0,y,.267],[.025,.025,.014])
  } else {
    ball(body,navy,[0,1.40,0],[.34,.25,.24])
    roundedBox(body,dark,[0,1.55,.02],[.65,.085,.46])
    roundedBox(body,gold,[0,1.55,.265],[.14,.085,.02])
    shape(body,[[-.20,2.51],[-.025,2.45],[-.15,2.28],[-.27,2.43]],eyeWhite,.255)
    shape(body,[[.20,2.51],[.025,2.45],[.15,2.28],[.27,2.43]],eyeWhite,.255)
    roundedBox(body,white,[.25,2.08,.248],[.16,.21,.028])
    tube(body,[[.19,2.14,.275],[.31,2.14,.275]],.012,navy)
  }
  shape(body,[[-.045,2.46],[.045,2.46],[.065,2.36],[0,2.29],[-.065,2.36]],feminine?navy:violet,.29)
  shape(body,[[0,2.32],[-.065,1.95],[0,1.88],[.065,1.95]],feminine?navy:violet,.295)
  arm(body,'Left',feminine);arm(body,'Right',feminine);leg(body,'Left',feminine);leg(body,'Right',feminine);head(body,feminine)
  const clips=motionClips()
  return {scene,clips}
}

const manifest=[]
for(const [name,feminine] of [['profissional-blazer',true],['profissional-camisa',false]]) {
  const {scene,clips}=build(feminine)
  const result=await new GLTFExporter().parseAsync(scene,{binary:true,animations:clips,trs:true})
  await writeFile(new URL(`${name}.glb`,out),Buffer.from(result))
  const loaded=await new GLTFLoader().parseAsync(result,'')
  let meshes=0,triangles=0
  loaded.scene.traverse(o=>{if(o.isMesh){meshes++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3}})
  if(loaded.animations.length!==4||!loaded.scene.getObjectByName('ShoulderRight')) throw new Error('Exportação sem articulações/animações')
  manifest.push({file:`${name}.glb`,bytes:result.byteLength,meshes,triangles,animations:loaded.animations.map(a=>a.name)})
}
await writeFile(new URL('manifest.json',out),JSON.stringify(manifest,null,2)+'\n')
console.log(JSON.stringify(manifest,null,2))
// Verify the GLB magic independently of the exporter/loader roundtrip.
for(const item of manifest) if((await readFile(new URL(item.file,out))).readUInt32LE(0)!==0x46546c67) throw new Error('GLB inválido')
