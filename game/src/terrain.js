import * as THREE from 'three';

// Value noise with smoothstep interpolation
function hashNoise(x, z) {
    let n = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
    return n - Math.floor(n);
}

function valueNoise(x, z) {
    const ix = Math.floor(x), iz = Math.floor(z);
    const fx = x - ix, fz = z - iz;
    const sx = fx * fx * (3 - 2 * fx), sz = fz * fz * (3 - 2 * fz);
    const a = hashNoise(ix, iz), b = hashNoise(ix + 1, iz);
    const c = hashNoise(ix, iz + 1), d = hashNoise(ix + 1, iz + 1);
    return a + (b - a) * sx + (c - a) * sz + (a - b - c + d) * sx * sz;
}

function fbm(x, z, octaves = 4) {
    let val = 0, amp = 1, freq = 1, total = 0;
    for (let i = 0; i < octaves; i++) {
        val += valueNoise(x * freq, z * freq) * amp;
        total += amp;
        amp *= 0.5;
        freq *= 2;
    }
    return val / total;
}

const SIZE = 60;
const SEGMENTS = 128;
const MAX_HEIGHT = 10.0;
const SCALE = 0.06;

export function getHeight(x, z) {
    const h = fbm(x * SCALE + 50, z * SCALE + 50, 5);
    const ridge = Math.exp(-((x + 12) ** 2) / 30) * 3.0;
    const valley = -Math.exp(-(z * z) / 60) * 1.5;
    const dist = Math.sqrt(x * x + z * z);
    const edge = Math.min(dist / 12, 1);
    return (h * MAX_HEIGHT * edge + ridge + valley) * edge;
}

// Reusable vector for normal output
const _nrm = new THREE.Vector3();

export function getNormal(x, z) {
    const eps = 0.3;
    const hL = getHeight(x - eps, z), hR = getHeight(x + eps, z);
    const hD = getHeight(x, z - eps), hU = getHeight(x, z + eps);
    return _nrm.set(hL - hR, 2 * eps, hD - hU).normalize();
}

export function createMesh() {
    const geo = new THREE.PlaneGeometry(SIZE, SIZE, SEGMENTS, SEGMENTS);
    geo.rotateX(-Math.PI / 2);

    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), z = pos.getZ(i);
        const y = getHeight(x, z);
        pos.setY(i, y);

        const slope = 1 - getNormal(x, z).y;
        const t = Math.min(y / MAX_HEIGHT, 1);
        let r, g, b;

        if (t < 0.3) {
            r = 0.22 + slope * 0.15;
            g = 0.50 + fbm(x * 0.3, z * 0.3, 2) * 0.15;
            b = 0.12;
        } else if (t < 0.6) {
            const f = (t - 0.3) / 0.3;
            r = 0.22 + f * 0.3; g = 0.50 - f * 0.1; b = 0.12 + f * 0.05;
        } else {
            const f = (t - 0.6) / 0.4;
            r = 0.45 + f * 0.15; g = 0.38 - f * 0.1; b = 0.20 + f * 0.1;
        }
        colors[i * 3] = r; colors[i * 3 + 1] = g; colors[i * 3 + 2] = b;
    }

    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true }));
}
