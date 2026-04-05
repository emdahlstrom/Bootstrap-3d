import * as THREE from 'three';
import { rand, showToast } from './utils.js';

const STATES = {
    clear:       { ambient: 0x8899aa, sun: 0xffeedd, sunI: 0.5, ambI: 0.6, fog: null, wind: [0, 0] },
    cloudy:      { ambient: 0x778899, sun: 0xcccccc, sunI: 0.2, ambI: 0.7, fog: null, wind: 'light' },
    rain:        { ambient: 0x556677, sun: 0x889999, sunI: 0.1, ambI: 0.5, fog: 0x667788, wind: 'medium' },
    storm:       { ambient: 0x334455, sun: 0x556666, sunI: 0.05, ambI: 0.4, fog: 0x445566, wind: 'heavy' },
    fog:         { ambient: 0x99aabb, sun: 0xdddddd, sunI: 0.15, ambI: 0.8, fog: 0xbbcccc, wind: [0, 0] },
    golden_hour: { ambient: 0xcc8855, sun: 0xffaa44, sunI: 0.7, ambI: 0.5, fog: null, wind: [0, 0] },
};

const SKY_GRADIENTS = {
    clear:       [['#4488cc', 0], ['#7ab0dd', 0.4], ['#b8d8e8', 0.7], ['#d8e8d0', 1]],
    cloudy:      [['#5577aa', 0], ['#99aabb', 1]],
    rain:        [['#446688', 0], ['#667788', 1]],
    storm:       [['#223344', 0], ['#334455', 1]],
    fog:         [['#8899aa', 0], ['#aabbbb', 1]],
    golden_hour: [['#cc6633', 0], ['#dd9955', 0.5], ['#eebb77', 1]],
};

const EMOJIS = { clear: '☀️', cloudy: '☁️', rain: '🌧️', storm: '⛈️', fog: '🌫️', golden_hour: '🌅' };
const LABELS = { clear: 'Clear skies', cloudy: 'Clouds rolling in', rain: 'Rain begins to fall',
    storm: 'A storm approaches!', fog: 'Fog descends on the meadow', golden_hour: 'Golden hour' };

export function createWeatherSystem(scene, ambientLight, sunLight, bgCtx) {
    // Rain particles
    const rainGeo = new THREE.BufferGeometry();
    const rainCount = 3000;
    const rainPos = new Float32Array(rainCount * 3);
    for (let i = 0; i < rainCount; i++) {
        rainPos[i * 3] = rand(-30, 30);
        rainPos[i * 3 + 1] = rand(0, 25);
        rainPos[i * 3 + 2] = rand(-30, 30);
    }
    rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
    const rainMat = new THREE.PointsMaterial({ color: 0xaaccee, size: 0.08, transparent: true, opacity: 0 });
    const rain = new THREE.Points(rainGeo, rainMat);
    scene.add(rain);

    // Lightning
    const lightning = new THREE.PointLight(0xffffff, 0, 100);
    lightning.position.set(0, 30, 0);
    scene.add(lightning);

    const state = {
        current: 'clear',
        windX: 0, windZ: 0,
        _lightningTimer: 0,
    };

    function setWeather(name) {
        state.current = name;
        const cfg = STATES[name];
        const wind = cfg.wind === 'light' ? [rand(-0.3, 0.3), rand(-0.3, 0.3)]
            : cfg.wind === 'medium' ? [rand(-0.8, 0.8), rand(-0.8, 0.8)]
            : cfg.wind === 'heavy' ? [rand(-2, 2), rand(-2, 2)]
            : cfg.wind;
        state.windX = wind[0]; state.windZ = wind[1];
        showToast(`${EMOJIS[name]} ${LABELS[name]}`);
    }

    function update(delta) {
        const cfg = STATES[state.current];
        const targetAmbient = new THREE.Color(cfg.ambient);
        const targetSun = new THREE.Color(cfg.sun);

        ambientLight.color.lerp(targetAmbient, delta * 0.5);
        ambientLight.intensity += (cfg.ambI - ambientLight.intensity) * delta * 0.5;
        sunLight.color.lerp(targetSun, delta * 0.5);
        sunLight.intensity += (cfg.sunI - sunLight.intensity) * delta * 0.5;

        // Fog
        if (cfg.fog) {
            const fogColor = new THREE.Color(cfg.fog);
            if (!scene.fog) scene.fog = new THREE.Fog(fogColor, 15, 50);
            scene.fog.color.lerp(fogColor, delta * 0.3);
            const targetFar = state.current === 'fog' ? 30 : state.current === 'storm' ? 35 : 50;
            scene.fog.far += (targetFar - scene.fog.far) * delta * 0.3;
        } else if (scene.fog) {
            scene.fog.far += (200 - scene.fog.far) * delta * 0.3;
            if (scene.fog.far > 180) scene.fog = null;
        }

        // Rain
        const isRaining = state.current === 'rain' || state.current === 'storm';
        const targetOp = isRaining ? (state.current === 'storm' ? 0.7 : 0.4) : 0;
        rainMat.opacity += (targetOp - rainMat.opacity) * delta * 0.5;

        if (rainMat.opacity > 0.01) {
            const positions = rainGeo.attributes.position;
            const speed = state.current === 'storm' ? 40 : 20;
            for (let i = 0; i < rainCount; i++) {
                positions.array[i * 3 + 1] -= delta * speed;
                positions.array[i * 3] += state.windX * delta * 3;
                positions.array[i * 3 + 2] += state.windZ * delta * 3;
                if (positions.array[i * 3 + 1] < 0) {
                    positions.array[i * 3] = rand(-30, 30);
                    positions.array[i * 3 + 1] = rand(15, 25);
                    positions.array[i * 3 + 2] = rand(-30, 30);
                }
            }
            positions.needsUpdate = true;
        }

        // Lightning
        if (state.current === 'storm') {
            state._lightningTimer -= delta;
            if (state._lightningTimer <= 0) {
                lightning.intensity = rand(3, 8);
                lightning.position.set(rand(-15, 15), 25, rand(-15, 15));
                state._lightningTimer = rand(1, 6);
                setTimeout(() => { lightning.intensity = 0; }, 100);
            }
        } else {
            lightning.intensity = 0;
        }

        // Sky
        const stops = SKY_GRADIENTS[state.current];
        const skyGrad = bgCtx.createLinearGradient(0, 0, 0, 512);
        for (const [color, pos] of stops) skyGrad.addColorStop(pos, color);
        bgCtx.fillStyle = skyGrad;
        bgCtx.fillRect(0, 0, 2, 512);
        scene.background.needsUpdate = true;
    }

    return { state, setWeather, update };
}
