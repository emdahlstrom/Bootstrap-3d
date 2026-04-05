import * as THREE from 'three';
import * as YUKA from 'yuka';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

import { createMesh as createTerrain, getHeight } from './terrain.js';
import { createDeer, createFox, updateAnimals } from './animals.js';
import { createHunter, updateHunter } from './hunter.js';
import { createWeatherSystem } from './weather.js';
import { createEventSystem } from './events.js';
import { loadAllNature } from './nature.js';
import { createPlayerController } from './player.js';
import { rand } from './utils.js';

// ─── Renderer ───
const canvas = document.getElementById('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.LinearToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;

// ─── Scene ───
const scene = new THREE.Scene();

const bgCanvas = document.createElement('canvas');
bgCanvas.width = 2; bgCanvas.height = 512;
const bgCtx = bgCanvas.getContext('2d');
const grad = bgCtx.createLinearGradient(0, 0, 0, 512);
grad.addColorStop(0, '#4488cc'); grad.addColorStop(0.4, '#7ab0dd');
grad.addColorStop(0.7, '#b8d8e8'); grad.addColorStop(1, '#d8e8d0');
bgCtx.fillStyle = grad;
bgCtx.fillRect(0, 0, 2, 512);
scene.background = new THREE.CanvasTexture(bgCanvas);

// ─── Camera ───
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 500);
camera.position.set(15, 8, 15);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 1, 0);
controls.maxDistance = 80;
controls.update();

// ─── Lighting ───
const ambientLight = new THREE.AmbientLight(0x8899aa, 0.6);
scene.add(ambientLight);
const sunLight = new THREE.DirectionalLight(0xffeedd, 0.5);
sunLight.position.set(8, 12, -6);
scene.add(sunLight);

// ─── Terrain ───
scene.add(createTerrain());

// ─── Yuka Entity Manager ───
const entityManager = new YUKA.EntityManager();
const obstacles = [];

// ─── Systems ───
const weatherSystem = createWeatherSystem(scene, ambientLight, sunLight, bgCtx);
const hunter = createHunter(entityManager, scene);
const eventSystem = createEventSystem(entityManager, weatherSystem, hunter);

// ─── Player Controller ───
const player = createPlayerController(camera, controls, entityManager);
canvas.addEventListener('pointerdown', player.onPointerDown);

// ─── Load Assets ───
const loader = new GLTFLoader();

// Nature
loadAllNature(loader, scene, obstacles);

// Animals — load GLTFs then spawn
const deerGltfP = new Promise(r => loader.load('/animals/Deer.glb', r));
const stagGltfP = new Promise(r => loader.load('/animals/Stag.glb', r));
const foxGltfP = new Promise(r => loader.load('/animals/Fox.glb', r));

Promise.all([deerGltfP, stagGltfP, foxGltfP]).then(([deerGltf, stagGltf, foxGltf]) => {
    // Deer herd
    for (let i = 0; i < 5; i++) {
        const a = rand(0, Math.PI * 2), r = rand(2, 6);
        createDeer(entityManager, scene, loader, deerGltf, { x: Math.cos(a) * r, z: Math.sin(a) * r });
    }
    // Stags
    for (let i = 0; i < 2; i++) {
        createDeer(entityManager, scene, loader, stagGltf, { x: rand(-8, -4), z: rand(-6, 6) });
    }
    // Fox
    createFox(entityManager, scene, loader, foxGltf, { x: 12, z: 0 });
});

// ─── Game Loop ───
const clock = new THREE.Clock();
let autoOrbit = true;
let speedMultiplier = 1.5;

function animate() {
    requestAnimationFrame(animate);
    const rawDelta = clock.getDelta();
    const delta = rawDelta * speedMultiplier;

    // Yuka entity updates (steering behaviors)
    entityManager.update(delta);

    // Terrain following, boundary forces, fox targeting
    updateAnimals(entityManager, delta);

    // Wind on animals
    for (const entity of entityManager.entities) {
        if (entity._type && entity._type !== 'hunter') {
            entity.velocity.x += weatherSystem.state.windX * 0.3 * delta;
            entity.velocity.z += weatherSystem.state.windZ * 0.3 * delta;
        }
    }

    // Hunter
    updateHunter(hunter, entityManager, delta);

    // Player control
    player.update(delta);

    // Weather + events
    weatherSystem.update(delta);
    eventSystem.update(rawDelta);

    // Camera orbit follows terrain (only when not controlling an animal)
    if (autoOrbit && !player.state.active) {
        const t = clock.elapsedTime * 0.12;
        const cx = Math.cos(t) * 25;
        const cz = Math.sin(t) * 25;
        camera.position.set(cx, getHeight(cx, cz) + 10 + Math.sin(t * 0.5) * 3, cz);
        controls.target.set(0, 2, 0);
    }

    controls.update();
    renderer.render(scene, camera);
}
animate();

// ─── UI ───
document.getElementById('btn-spin').addEventListener('click', (e) => {
    autoOrbit = !autoOrbit;
    e.target.classList.toggle('active', autoOrbit);
});

const speeds = [1.5, 2.5, 1, 0.5];
let speedIdx = 0;
document.getElementById('btn-speed').addEventListener('click', (e) => {
    speedIdx = (speedIdx + 1) % speeds.length;
    speedMultiplier = speeds[speedIdx];
    e.target.textContent = `Speed: ${speedMultiplier}x`;
});

// Player control buttons
document.getElementById('btn-exit-animal')?.addEventListener('click', () => player.release());

// Touch/click directional buttons
for (const [id, key] of [['btn-up','forward'],['btn-down','backward'],['btn-left','left'],['btn-right','right']]) {
    const el = document.getElementById(id);
    if (!el) continue;
    const setInput = (val) => { player.state.input[key] = val; };
    el.addEventListener('pointerdown', (e) => { e.preventDefault(); setInput(true); });
    el.addEventListener('pointerup', () => setInput(false));
    el.addEventListener('pointerleave', () => setInput(false));
}
document.getElementById('btn-jump')?.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    player.state.input.jump = true;
});
document.getElementById('btn-run')?.addEventListener('click', (e) => {
    player.state.running = !player.state.running;
    e.target.classList.toggle('active', player.state.running);
    e.target.textContent = player.state.running ? '🏃 Run' : '🚶 Walk';
    // Switch animation
    if (player.state.entity?._mixer) {
        const name = player.state.running ? 'Gallop' : 'Walk';
        const mixer = player.state.entity._mixer;
        mixer.stopAllAction();
        const clip = player.state.entity._animations?.find(a => a.name.includes(name));
        if (clip) {
            const action = mixer.clipAction(clip);
            action.timeScale = player.state.running ? 1.8 : 1.5;
            action.play();
        }
    }
});

// Keyboard controls (for desktop)
window.addEventListener('keydown', (e) => {
    if (!player.state.active) return;
    if (e.key === 'w' || e.key === 'ArrowUp') player.state.input.forward = true;
    if (e.key === 's' || e.key === 'ArrowDown') player.state.input.backward = true;
    if (e.key === 'a' || e.key === 'ArrowLeft') player.state.input.left = true;
    if (e.key === 'd' || e.key === 'ArrowRight') player.state.input.right = true;
    if (e.key === ' ') player.state.input.jump = true;
    if (e.key === 'Shift') {
        player.state.running = true;
        document.getElementById('btn-run')?.classList.add('active');
    }
    if (e.key === 'Escape') player.release();
});
window.addEventListener('keyup', (e) => {
    if (e.key === 'w' || e.key === 'ArrowUp') player.state.input.forward = false;
    if (e.key === 's' || e.key === 'ArrowDown') player.state.input.backward = false;
    if (e.key === 'a' || e.key === 'ArrowLeft') player.state.input.left = false;
    if (e.key === 'd' || e.key === 'ArrowRight') player.state.input.right = false;
    if (e.key === 'Shift') {
        player.state.running = false;
        const btn = document.getElementById('btn-run');
        if (btn) { btn.classList.remove('active'); btn.textContent = '🚶 Walk'; }
    }
});

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

setTimeout(() => {
    const info = document.getElementById('info');
    if (info) info.style.opacity = '0';
}, 5000);
