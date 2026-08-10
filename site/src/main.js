import './style.css'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const MODEL_URL = `${import.meta.env.BASE_URL}models/surround1x0-akdk.glb`

const canvas = document.querySelector('#viewport')
const loadingCard = document.querySelector('#loadingCard')
const loadingDetail = document.querySelector('#loadingDetail')
const modelCount = document.querySelector('#modelCount')
const colorwaySelect = document.querySelector('#colorwaySelect')
const visibilitySelect = document.querySelector('#visibilitySelect')
const switchOptions = document.querySelector('#switchOptions')
const visibilityHelp = document.querySelector('#visibilityHelp')
const explodeAmount = document.querySelector('#explodeAmount')
const explodeOutput = document.querySelector('#explodeOutput')
const modeButtons = [...document.querySelectorAll('[data-view-mode]')]
const fitButton = document.querySelector('#fitButton')
const resetButton = document.querySelector('#resetButton')
const swatches = document.querySelector('#swatches')

const scene = new THREE.Scene()
const camera = new THREE.PerspectiveCamera(36, 1, 0.001, 100)
camera.position.set(0.32, 0.26, 0.38)

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.toneMapping = THREE.ACESFilmicToneMapping
renderer.toneMappingExposure = 1.08
renderer.shadowMap.enabled = true
renderer.shadowMap.type = THREE.PCFShadowMap

const controls = new OrbitControls(camera, canvas)
controls.enableDamping = true
controls.dampingFactor = 0.075
controls.screenSpacePanning = true
controls.minDistance = 0.035
controls.maxDistance = 3

scene.add(new THREE.HemisphereLight(0xc8dbff, 0x202027, 2.2))

const keyLight = new THREE.DirectionalLight(0xffffff, 4.2)
keyLight.position.set(-0.3, 0.55, 0.4)
keyLight.castShadow = true
keyLight.shadow.mapSize.set(2048, 2048)
keyLight.shadow.camera.near = 0.01
keyLight.shadow.camera.far = 2
scene.add(keyLight)

const rimLight = new THREE.DirectionalLight(0x7ca7ff, 2.4)
rimLight.position.set(0.45, 0.2, -0.25)
scene.add(rimLight)

const fillLight = new THREE.DirectionalLight(0xffd4bb, 1.5)
fillLight.position.set(0.1, -0.1, 0.5)
scene.add(fillLight)

const state = {
  model: null,
  renderables: [],
  materials: [],
  materialDefaults: new Map(),
  layerNodes: [],
  itemById: new Map(),
  switchItems: [],
  selectedItem: null,
  explodeSpacing: 0.03,
  switchExplodeSpacing: 0.006,
  explodeCurrent: 0,
  explodeTarget: 0,
  explodeAmount: 1,
  mode: 'assembled',
  initialCamera: null,
  floor: null,
  grid: null,
}

const colorways = {
  black: {
    case: '#090b0f',
    keycap: '#14171c',
    accent: '#343b43',
    legend: '#e4e8ed',
    trackball: '#5b1424',
    swatches: ['#101216', '#5b1424', '#8ea0ad'],
  },
  ivory: {
    case: '#d7d0be',
    keycap: '#e7dfcd',
    accent: '#8b9194',
    legend: '#263642',
    trackball: '#5b1424',
    swatches: ['#e7dfcd', '#8b9194', '#5b1424'],
  },
}

function classifyMaterial(material) {
  const name = material.name.toLowerCase()
  if (name.includes('trackball')) return 'trackball'
  if (name.includes('legend')) return 'legend'
  if (name.includes('keycap_cool') || name.includes('accent')) return 'accent'
  if (name.includes('keycap')) return 'keycap'
  if (name.includes('case_')) return 'case'
  return null
}

function setColorway(name) {
  for (const material of state.materials) {
    const original = state.materialDefaults.get(material.uuid)
    const category = classifyMaterial(material)
    if (name === 'original' || !category) {
      if (original) {
        material.color.copy(original.color)
        material.roughness = original.roughness
        material.metalness = original.metalness
        material.opacity = original.opacity
        material.transparent = original.transparent
      }
    } else {
      material.color.set(colorways[name][category])
      if (category === 'case' || category === 'keycap' || category === 'accent') {
        material.roughness = 0.56
        material.metalness = 0
      }
      if (category === 'trackball') {
        material.roughness = 0.28
        material.metalness = 0.16
      }
    }
    material.needsUpdate = true
  }

  const palette = colorways[name]?.swatches ?? ['#77818e', '#d7d0be', '#5b1424']
  ;[...swatches.children].forEach((swatch, index) => {
    swatch.style.setProperty('--swatch', palette[index])
  })
}

function ancestorLayer(object) {
  let cursor = object
  while (cursor) {
    if (cursor.userData?.exploded_view_layer) return cursor.userData.exploded_view_layer
    cursor = cursor.parent
  }
  return null
}

function isConnector(object) {
  if (isSocket(object)) return false
  let cursor = object
  while (cursor) {
    if (/connector|usb|trrs|insert/i.test(cursor.name)) return true
    cursor = cursor.parent
  }
  return false
}

function isSocket(object) {
  let cursor = object
  while (cursor) {
    if (/^(Left|Right)_Sockets?_/.test(cursor.name)) return true
    if (cursor.userData?.socket_part_number === 'CPG135001S30') return true
    cursor = cursor.parent
  }
  return false
}

function componentFamily(object) {
  let cursor = object
  while (cursor) {
    if (cursor.userData?.component_family) return cursor.userData.component_family
    cursor = cursor.parent
  }
  return null
}

function objectSide(object) {
  let cursor = object
  while (cursor) {
    if (/^Left(?:_|$)/.test(cursor.name)) return 'left'
    if (/^Right(?:_|$)/.test(cursor.name)) return 'right'
    cursor = cursor.parent
  }
  return null
}

function switchRootFor(object) {
  let cursor = object
  while (cursor) {
    if (/^(Left|Right)_Switch_\d+$/.test(cursor.name)) return cursor
    cursor = cursor.parent
  }
  return null
}

function switchPartOrder(name) {
  const orderBySuffix = [
    ['_Base', -2.2],
    ['_Fix_Pin', -1.7],
    ['_Fixed_Contact', -1.2],
    ['_Moving_Contact', -0.8],
    ['_Torsion_Spring', -0.35],
    ['_Click_Bar', 0],
    ['_Coil_Spring', 0.45],
    ['_Push_Rod', 0.9],
    ['_Stem', 1.5],
    ['_Cover', 2.4],
  ]
  return orderBySuffix.find(([suffix]) => name.endsWith(suffix))?.[1] ?? 0
}

function objectMatchesGroup(object, group) {
  const layer = ancestorLayer(object)
  if (group === 'left' || group === 'right') return objectSide(object) === group
  if (group === 'case') return layer === 'top_case' || layer === 'bottom_case'
  if (group === 'sockets') return isSocket(object)
  if (group === 'controller') return componentFamily(object) === 'controller'
  if (group === 'conthrough') return componentFamily(object) === 'conthrough'
  if (group === 'mouse_sensor') return componentFamily(object) === 'mouse_sensor'
  if (group === 'connectors') return isConnector(object)
  return layer === group
}

function applyVisibility(value) {
  state.selectedItem = value.startsWith('item:')
    ? state.itemById.get(value.slice(5)) ?? null
    : null

  state.renderables.forEach((object) => {
    object.visible = value === 'all'
  })

  if (value.startsWith('group:')) {
    const group = value.slice(6)
    state.renderables.forEach((object) => {
      object.visible = objectMatchesGroup(object, group)
    })
  } else if (state.selectedItem) {
    state.selectedItem.renderables.forEach((object) => {
      object.visible = true
    })
  }

  const selected = visibilitySelect.selectedOptions[0]
  if (state.selectedItem?.type === 'switch') {
    visibilityHelp.textContent = `${state.selectedItem.label}を一式で表示します。「分解」で内部パーツを展開します。`
  } else if (value === 'all') {
    visibilityHelp.textContent = '全オブジェクトを表示します。'
  } else {
    visibilityHelp.textContent = selected
      ? `${selected.textContent.trim()}のみをプレビューします。`
      : '表示対象を切り替えます。'
  }
}

function applyExplode(factor) {
  const selectedSwitch = state.selectedItem?.type === 'switch' ? state.selectedItem : null
  const assemblyFactor = selectedSwitch ? 0 : factor

  for (const entry of state.layerNodes) {
    entry.node.position.z = entry.baseZ + entry.order * state.explodeSpacing * assemblyFactor
  }

  for (const switchItem of state.switchItems) {
    const switchFactor = switchItem === selectedSwitch ? factor : 0
    for (const part of switchItem.parts) {
      part.node.position.z =
        part.baseZ + part.order * state.switchExplodeSpacing * switchFactor
    }
  }
}

function setViewMode(mode) {
  state.mode = mode
  modeButtons.forEach((button) => {
    button.classList.toggle('is-active', button.dataset.viewMode === mode)
  })
  state.explodeTarget = mode === 'exploded' ? state.explodeAmount : 0

  if (state.selectedItem?.type === 'switch') {
    window.setTimeout(() => fitCamera(), mode === 'exploded' ? 520 : 30)
  }
}

function visibleBounds() {
  const bounds = new THREE.Box3()
  const scratch = new THREE.Box3()
  let hasVisible = false
  state.renderables.forEach((object) => {
    if (!object.visible) return
    scratch.setFromObject(object)
    if (scratch.isEmpty()) return
    bounds.union(scratch)
    hasVisible = true
  })
  return hasVisible ? bounds : null
}

function fitCamera({ remember = false } = {}) {
  const bounds = visibleBounds()
  if (!bounds) return

  const center = bounds.getCenter(new THREE.Vector3())
  const size = bounds.getSize(new THREE.Vector3())
  const maxSize = Math.max(size.x, size.y, size.z, 0.01)
  const fov = THREE.MathUtils.degToRad(camera.fov)
  const distance = (maxSize / (2 * Math.tan(fov / 2))) * 1.28
  const direction = new THREE.Vector3(0.9, 0.68, 1.05).normalize()

  camera.position.copy(center).addScaledVector(direction, distance)
  camera.near = Math.max(distance / 1000, 0.0005)
  camera.far = distance * 20
  camera.updateProjectionMatrix()
  controls.target.copy(center)
  controls.minDistance = maxSize * 0.12
  controls.maxDistance = maxSize * 8
  controls.update()

  if (remember) {
    state.initialCamera = {
      position: camera.position.clone(),
      target: controls.target.clone(),
    }
  }
}

function resetCamera() {
  if (!state.initialCamera) return
  camera.position.copy(state.initialCamera.position)
  controls.target.copy(state.initialCamera.target)
  controls.update()
}

function createFloor(bounds) {
  if (state.floor) scene.remove(state.floor)
  if (state.grid) scene.remove(state.grid)
  const size = bounds.getSize(new THREE.Vector3())
  const center = bounds.getCenter(new THREE.Vector3())
  const floorGeometry = new THREE.PlaneGeometry(size.x * 2.6, size.z * 2.6)
  const floorMaterial = new THREE.ShadowMaterial({ color: 0x000000, opacity: 0.22 })
  const floor = new THREE.Mesh(floorGeometry, floorMaterial)
  floor.rotation.x = -Math.PI / 2
  floor.position.set(center.x, bounds.min.y - size.y * 0.04, center.z)
  floor.receiveShadow = true
  floor.name = 'Preview_Shadow_Floor'
  scene.add(floor)
  state.floor = floor

  const grid = new THREE.GridHelper(size.x * 1.85, 22, 0x46505f, 0x242b35)
  grid.position.copy(floor.position)
  grid.position.y += size.y * 0.002
  grid.material.opacity = 0.16
  grid.material.transparent = true
  scene.add(grid)
  state.grid = grid
}

function populateItems(model) {
  const collator = new Intl.Collator('ja', { numeric: true })
  const switchRoots = []
  model.traverse((object) => {
    if (/^(Left|Right)_Switch_\d+$/.test(object.name)) switchRoots.push(object)
  })
  switchRoots.sort((a, b) => collator.compare(a.name, b.name))

  switchRoots.forEach((root) => {
    const renderables = state.renderables.filter((object) => switchRootFor(object) === root)
    const stem = renderables.find((object) => object.name.endsWith('_Stem'))
    const stemMaterials = Array.isArray(stem?.material) ? stem.material : [stem?.material]
    const variant = stemMaterials.some((material) => /blue/i.test(material?.name ?? ''))
      ? 'blue'
      : 'brown'
    const id = `switch:${root.name}`
    const item = {
      id,
      type: 'switch',
      label: root.name,
      variant,
      root,
      renderables,
      parts: renderables.map((node) => ({
        node,
        baseZ: node.position.z,
        order: switchPartOrder(node.name),
      })),
    }
    state.itemById.set(id, item)
    state.switchItems.push(item)
  })

  ;[
    ['brown', 'Choc V2 茶軸（単体）'],
    ['blue', 'Choc V2 青軸（単体）'],
  ].forEach(([variant, label]) => {
    const item = state.switchItems.find((candidate) => candidate.variant === variant)
    if (!item) return
    item.label = label.replace('（単体）', '')
    const option = document.createElement('option')
    option.value = `item:${item.id}`
    option.textContent = label
    switchOptions.append(option)
  })

}

function enableControls() {
  ;[
    colorwaySelect,
    visibilitySelect,
    explodeAmount,
    fitButton,
    resetButton,
    ...modeButtons,
  ].forEach((control) => {
    control.disabled = false
  })
}

function onModelLoaded(gltf) {
  const model = gltf.scene
  model.name = 'Surround1x0-AKDK_GLTF'
  model.rotation.x = -Math.PI / 2
  scene.add(model)
  state.model = model

  const materialSet = new Set()
  model.traverse((object) => {
    if (object.isMesh || object.isLine || object.isPoints) {
      state.renderables.push(object)
      object.castShadow = object.isMesh
      object.receiveShadow = object.isMesh
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.filter(Boolean).forEach((material) => materialSet.add(material))
    }

    if (
      object.userData?.exploded_view_layer &&
      Number.isFinite(Number(object.userData.exploded_view_order))
    ) {
      state.layerNodes.push({
        node: object,
        order: Number(object.userData.exploded_view_order ?? 0),
        baseZ: object.position.z,
      })
    }
  })

  state.materials = [...materialSet]
  state.materials.forEach((material) => {
    state.materialDefaults.set(material.uuid, {
      color: material.color?.clone() ?? new THREE.Color(0xffffff),
      roughness: material.roughness,
      metalness: material.metalness,
      opacity: material.opacity,
      transparent: material.transparent,
    })
  })

  model.updateMatrixWorld(true)
  const assembledBounds = new THREE.Box3().setFromObject(model)
  const assembledSize = assembledBounds.getSize(new THREE.Vector3())
  state.explodeSpacing = assembledSize.x > 10 ? 30 : 0.03
  state.switchExplodeSpacing = assembledSize.x > 10 ? 6 : 0.006

  populateItems(model)
  setColorway('black')
  applyExplode(0)
  createFloor(assembledBounds)
  fitCamera({ remember: true })
  enableControls()

  modelCount.textContent = `${visibilitySelect.options.length} views`
  loadingCard.classList.add('is-hidden')
}

function onLoadError(error) {
  console.error(error)
  loadingCard.classList.add('is-error')
  loadingDetail.textContent = 'GLBを読み込めませんでした。npm run model:exportを確認してください。'
}

const loader = new GLTFLoader()
loader.load(
  MODEL_URL,
  onModelLoaded,
  (event) => {
    if (!event.total) return
    const progress = Math.round((event.loaded / event.total) * 100)
    loadingDetail.textContent = `GLBを読み込み中… ${progress}%`
  },
  onLoadError,
)

colorwaySelect.addEventListener('change', () => setColorway(colorwaySelect.value))
visibilitySelect.addEventListener('change', () => {
  applyVisibility(visibilitySelect.value)
  if (state.selectedItem?.type === 'switch') {
    window.setTimeout(() => fitCamera(), state.mode === 'exploded' ? 520 : 30)
  }
})

modeButtons.forEach((button) => {
  button.addEventListener('click', () => setViewMode(button.dataset.viewMode))
})

explodeAmount.addEventListener('input', () => {
  state.explodeAmount = Number(explodeAmount.value) / 100
  explodeOutput.value = `${explodeAmount.value}%`
  if (state.mode === 'exploded') state.explodeTarget = state.explodeAmount
})

fitButton.addEventListener('click', () => fitCamera())
resetButton.addEventListener('click', resetCamera)

function resize() {
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  if (!width || !height) return
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

const resizeObserver = new ResizeObserver(resize)
resizeObserver.observe(canvas)
resize()

function animate() {
  requestAnimationFrame(animate)
  state.explodeCurrent = THREE.MathUtils.damp(
    state.explodeCurrent,
    state.explodeTarget,
    7.5,
    1 / 60,
  )
  applyExplode(state.explodeCurrent)
  controls.update()
  renderer.render(scene, camera)
}

animate()
