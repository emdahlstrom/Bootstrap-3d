import * as THREE from 'three';
import { getHeight } from './terrain.js';
import { convertToBasicMaterials, rand } from './utils.js';

const NATURE_ASSETS = [
    { url: '/nature/CommonTree_1.glb', count: 8, rMin: 15, rMax: 21, sMin: 1.5, sMax: 2.5, collision: 1.5, ring: true },
    { url: '/nature/PineTree_1.glb', count: 5, rMin: 19, rMax: 25, sMin: 2, sMax: 3, collision: 1.2, ring: true, offset: 0.3 },
    { url: '/nature/BirchTree_1.glb', count: 3, xMin: -15, xMax: -8, zMin: -5, zMax: 5, sMin: 1.5, sMax: 2.2, collision: 1.0 },
    { url: '/nature/Grass.glb', count: 20, xMin: -12, xMax: 12, zMin: -12, zMax: 12, sMin: 0.8, sMax: 1.5 },
    { url: '/nature/Bush_1.glb', count: 10, xMin: -15, xMax: 15, zMin: -15, zMax: 15, sMin: 1, sMax: 1.5, collision: 0.8 },
    { url: '/nature/Flowers.glb', count: 8, xMin: -10, xMax: 10, zMin: -10, zMax: 10, sMin: 0.6, sMax: 1.2 },
    { url: '/nature/Rock_1.glb', count: 3, xMin: -15, xMax: 15, zMin: -15, zMax: 15, sMin: 1.5, sMax: 3, collision: 1.5 },
    { url: '/nature/Rock_Moss_1.glb', count: 2, xMin: -10, xMax: 10, zMin: -10, zMax: 10, sMin: 1.5, sMax: 2.5, collision: 1.5 },
];

export function loadAllNature(loader, scene, obstacles) {
    for (const asset of NATURE_ASSETS) {
        loader.load(asset.url, (gltf) => {
            for (let i = 0; i < asset.count; i++) {
                let x, z;
                if (asset.ring) {
                    const angle = (i / asset.count) * Math.PI * 2 + (asset.offset || 0);
                    const r = rand(asset.rMin, asset.rMax);
                    x = Math.cos(angle) * r;
                    z = Math.sin(angle) * r;
                } else {
                    x = rand(asset.xMin, asset.xMax);
                    z = rand(asset.zMin, asset.zMax);
                }
                const y = getHeight(x, z);
                const model = gltf.scene.clone();
                model.position.set(x, y, z);
                model.rotation.y = rand(0, Math.PI * 2);
                model.scale.setScalar(rand(asset.sMin, asset.sMax));
                convertToBasicMaterials(model, 0x55aa33);
                scene.add(model);

                if (asset.collision) {
                    obstacles.push({ position: new THREE.Vector3(x, y, z), radius: asset.collision });
                }
            }
        });
    }
}
