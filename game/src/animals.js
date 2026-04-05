import * as THREE from 'three';
import * as YUKA from 'yuka';
import { getHeight, getNormal } from './terrain.js';
import { convertToBasicMaterials, rand, BOUNDS } from './utils.js';

// Sync a Yuka entity's transform to a Three.js mesh
function syncRenderComponent(entity, mesh) {
    mesh.position.copy(entity.position);
    mesh.quaternion.copy(entity.rotation);
}

export function createDeer(entityManager, scene, loader, gltf, spawnPos) {
    const model = gltf.scene.clone();
    model.scale.setScalar(rand(0.9, 1.1));
    convertToBasicMaterials(model);
    scene.add(model);

    const vehicle = new YUKA.Vehicle();
    vehicle.position.set(spawnPos.x, getHeight(spawnPos.x, spawnPos.z), spawnPos.z);
    vehicle.maxSpeed = 3.0;
    vehicle.maxForce = 2.0;
    vehicle.mass = 1;
    vehicle.updateNeighborhood = true;
    vehicle.neighborhoodRadius = 12;
    vehicle.setRenderComponent(model, syncRenderComponent);
    vehicle._type = 'deer';
    vehicle._mixer = null;
    vehicle._grazeTimer = 0;

    if (gltf.animations.length > 0) {
        const mixer = new THREE.AnimationMixer(model);
        const walkClip = gltf.animations.find(a => a.name.includes('Walk'));
        if (walkClip) {
            const action = mixer.clipAction(walkClip);
            action.timeScale = 1.5;
            action.play();
        }
        vehicle._mixer = mixer;
        vehicle._animations = gltf.animations;
    }

    const wander = new YUKA.WanderBehavior();
    wander.jitter = 5;
    wander.radius = 3;
    wander.distance = 5;
    wander.weight = 0.5;
    vehicle.steering.add(wander);

    const separation = new YUKA.SeparationBehavior();
    separation.weight = 2.5;
    vehicle.steering.add(separation);

    const alignment = new YUKA.AlignmentBehavior();
    alignment.weight = 0.8;
    vehicle.steering.add(alignment);

    const cohesion = new YUKA.CohesionBehavior();
    cohesion.weight = 0.6;
    vehicle.steering.add(cohesion);

    entityManager.add(vehicle);
    return vehicle;
}

export function createFox(entityManager, scene, loader, gltf, spawnPos) {
    const model = gltf.scene.clone();
    model.scale.setScalar(0.8);
    convertToBasicMaterials(model);
    scene.add(model);

    const vehicle = new YUKA.Vehicle();
    vehicle.position.set(spawnPos.x, getHeight(spawnPos.x, spawnPos.z), spawnPos.z);
    vehicle.maxSpeed = 4.2;
    vehicle.maxForce = 2.5;
    vehicle.mass = 1;
    vehicle.setRenderComponent(model, syncRenderComponent);
    vehicle._type = 'fox';
    vehicle._mixer = null;

    if (gltf.animations.length > 0) {
        const mixer = new THREE.AnimationMixer(model);
        const clip = gltf.animations.find(a => a.name.includes('Gallop'));
        if (clip) {
            const action = mixer.clipAction(clip);
            action.timeScale = 1.5;
            action.play();
        }
        vehicle._mixer = mixer;
        vehicle._animations = gltf.animations;
    }

    const wander = new YUKA.WanderBehavior();
    wander.jitter = 8;
    wander.radius = 4;
    wander.distance = 6;
    wander.weight = 0.3;
    vehicle.steering.add(wander);

    // Pursuit is added dynamically when a deer is targeted
    vehicle._pursuitBehavior = new YUKA.PursuitBehavior();
    vehicle._pursuitBehavior.weight = 1.2;
    vehicle._pursuitBehavior.active = false;
    vehicle.steering.add(vehicle._pursuitBehavior);

    entityManager.add(vehicle);
    return vehicle;
}

// Per-frame update: terrain following, boundary, fox targeting, grazing
export function updateAnimals(entityManager, delta) {
    const entities = entityManager.entities;
    let nearestDeerToFox = null;
    let nearestDeerDist = Infinity;

    for (const entity of entities) {
        if (!entity._type || entity._playerControlled) continue;

        // Terrain following
        const pos = entity.position;
        pos.y = getHeight(pos.x, pos.z);

        // Boundary force
        const limit = BOUNDS - 3;
        if (pos.x > limit) entity.velocity.x -= 3 * delta;
        if (pos.x < -limit) entity.velocity.x += 3 * delta;
        if (pos.z > limit) entity.velocity.z -= 3 * delta;
        if (pos.z < -limit) entity.velocity.z += 3 * delta;

        // Slope slowdown
        const normal = getNormal(pos.x, pos.z);
        const slopeSlowdown = Math.max(0.3, normal.y);
        const speed = entity.velocity.length();
        if (speed > entity.maxSpeed * slopeSlowdown) {
            entity.velocity.normalize().multiplyScalar(entity.maxSpeed * slopeSlowdown);
        }

        // Animation mixer
        if (entity._mixer) entity._mixer.update(delta * 1.5);

        // Grazing timer
        if (entity._grazeTimer > 0) {
            entity._grazeTimer -= delta;
            entity.velocity.multiplyScalar(0.9);
        }

        // Fox: track nearest deer
        if (entity._type === 'fox') {
            for (const other of entities) {
                if (other._type !== 'deer') continue;
                const d = entity.position.distanceTo(other.position);
                if (d < nearestDeerDist) {
                    nearestDeerDist = d;
                    nearestDeerToFox = other;
                }
            }
            if (nearestDeerToFox && nearestDeerDist < 15) {
                entity._pursuitBehavior.evader = nearestDeerToFox;
                entity._pursuitBehavior.active = true;
            } else {
                entity._pursuitBehavior.active = false;
            }
        }

        // Deer: flee from fox
        if (entity._type === 'deer') {
            for (const other of entities) {
                if (other._type !== 'fox') continue;
                const d = entity.position.distanceTo(other.position);
                if (d < 8) {
                    const flee = entity.position.clone().sub(other.position).normalize();
                    const strength = 4.0 * (1 - d / 8);
                    entity.velocity.x += flee.x * strength;
                    entity.velocity.z += flee.z * strength;
                }
            }
        }
    }
}
