# SkillBridge - personagens 3D, versão 2

Modelagem procedural original inspirada nas duas referências visuais fornecidas pelo responsável pelo projeto. Esta é uma interpretação estilizada, não uma reconstrução fiel das imagens.

| Arquivo | Tamanho | Triângulos | Malhas |
| --- | ---: | ---: | ---: |
| profissional-blazer.glb | 858.008 bytes | 50.534 | 85 |
| profissional-camisa.glb | 884.580 bytes | 49.102 | 78 |

Os arquivos são GLB 2.0, sem texturas ou recursos externos. Os materiais estão incorporados. As maletas fazem parte da hierarquia da mão esquerda.

## Animações

- `Acenar`: gesto curto com o braço direito (4,8 segundos).
- `Respirar`: expansão sutil do tronco, sem elevar os pés (5 segundos).
- `Celebrar`: gesto coordenado de braço, punho e cabeça (4,8 segundos).
- `Caminhar`: passos no lugar (5,6 segundos).

O rig usa grupos articulados rígidos, com nomes como `Character`, `Head`, `ShoulderRight`, `ElbowRight`, `WristLeft`, `HipLeft` e `KneeRight`. Não é um esqueleto com skinning, rig facial ou animação de caminhada com deslocamento. Partes podem ser reposicionadas no Three.js ou em um editor compatível com GLB.

## Visualizar e usar

Prévia interativa: https://skillbridge-two-rosy.vercel.app/personagens.html

No projeto: `cd frontend`, `npm ci`, `npm run dev`, depois abrir http://127.0.0.1:5173/personagens.html.

```ts
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const asset = await new GLTFLoader().loadAsync('/models/profissional-blazer.glb')
scene.add(asset.scene)
const mixer = new THREE.AnimationMixer(asset.scene)
const clip = asset.animations.find(clip => clip.name === 'Acenar')!
const action = mixer.clipAction(clip)
action.setLoop(THREE.LoopOnce, 1)
action.play()
// No loop do aplicativo: mixer.update(deltaEmSegundos).
// Ao desmontar: parar ações e liberar geometrias, materiais e renderer.
```

## Reproduzir a geração e verificar

Na raiz do projeto:

```powershell
node frontend/scripts/create-characters.mjs
node frontend/scripts/validate-characters.mjs
```

`manifest.json` registra medidas reais dos modelos. `validation.json` registra o resultado do glTF Validator e uma verificação de movimento/restauração da articulação. Ambos os GLB passaram com zero erros e zero avisos; há mensagens informativas de atributos não utilizados. A prévia respeita movimento reduzido na reprodução inicial, permite parar e executa animações finitas.

## Estado e limites

Primeira versão para revisão visual. Ainda exige aprovação do acabamento antes de incorporar os personagens às páginas da jornada. A aplicação principal e a apresentação permanecem em suas rotas existentes. Testado tecnicamente em navegador desktop e viewport de 390px, sem medição em aparelho móvel físico ou validação com usuários reais.

## Movimento revisado
Curvas analíticas amostradas a 60 Hz, aceleração/desaceleração quintic e retorno à pose inicial. A taxa de amostragem não promete 60 FPS no dispositivo. O estúdio aplica transições de 450 ms entre gestos e retorno de 500 ms ao parar. Verificação de continuidade: maior passo angular amostrado de 2,884 graus; início/fim coincidem. O rig permanece articulado rígido, sem deformação por skinning.
