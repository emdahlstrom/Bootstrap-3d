import * as THREE from 'three';
import { getHeight } from './terrain.js';
import { showToast } from './utils.js';

const WALK_SPEED = 3.0;
const RUN_SPEED = 7.0;
const JUMP_VELOCITY = 8.0;
const GRAVITY = -20;
const TURN_SPEED = 4.0;
const CAM_HEIGHT = 4;
const CAM_DISTANCE = 8;

export function createPlayerController(camera, controls, entityManager) {
    const state = {
        active: false,
        entity: null,       // possessed Yuka entity
        mesh: null,         // Three.js mesh
        running: false,
        jumping: false,
        verticalVel: 0,
        input: { forward: false, backward: false, left: false, right: false, jump: false },
        heading: 0,
    };

    // Raycaster for click-to-possess
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    function possess(entity) {
        if (!entity || !entity._type) return;
        state.entity = entity;
        state.mesh = entity._renderComponent?.mesh || entity._renderMesh;
        // Find the Three.js mesh from the render component
        for (const child of entity._renderComponent ? [] : []) { /* noop */ }
        // The mesh is set via setRenderComponent — grab it
        if (!state.mesh) {
            // Walk the scene to find it by matching position
            entityManager.entities.forEach(e => {
                if (e === entity && e._mixer?._root) {
                    state.mesh = e._mixer._root;
                }
            });
        }

        state.active = true;
        state.running = false;
        state.jumping = false;
        state.verticalVel = 0;
        state.heading = entity.rotation?.y || Math.atan2(entity.velocity.x, entity.velocity.z);

        // Disable AI steering while player controls
        entity._playerControlled = true;
        entity.steering?.behaviors?.forEach(b => { b.active = false; });

        // Switch to walk/gallop animation
        switchAnimation(entity, state.running ? 'Gallop' : 'Walk');

        controls.enabled = false;
        showToast(`🎮 Controlling ${entity._type}! Tap buttons to move.`);
        document.getElementById('player-controls').style.display = 'flex';
        document.getElementById('player-side-controls').style.display = 'flex';
        document.getElementById('btn-exit-animal').style.display = 'block';
    }

    function release() {
        if (!state.entity) return;
        const entity = state.entity;

        // Re-enable AI
        entity._playerControlled = false;
        entity.steering?.behaviors?.forEach(b => { b.active = true; });
        switchAnimation(entity, 'Walk');

        state.active = false;
        state.entity = null;
        state.mesh = null;
        state.input = { forward: false, backward: false, left: false, right: false, jump: false };

        controls.enabled = true;
        document.getElementById('player-controls').style.display = 'none';
        document.getElementById('player-side-controls').style.display = 'none';
        document.getElementById('btn-exit-animal').style.display = 'none';
        showToast('Released animal');
    }

    function switchAnimation(entity, name) {
        if (!entity._mixer || !entity._mixer._root) return;
        const mixer = entity._mixer;
        // Stop all current actions
        mixer.stopAllAction();
        // Find and play the target clip
        const animations = entity._animations || [];
        const clip = animations.find(a => a.name.includes(name));
        if (clip) {
            const action = mixer.clipAction(clip);
            action.timeScale = name === 'Gallop' ? 1.8 : 1.5;
            action.play();
        }
    }

    function update(delta) {
        if (!state.active || !state.entity) return;
        const entity = state.entity;
        const pos = entity.position;
        const inp = state.input;

        // Turn
        if (inp.left) state.heading += TURN_SPEED * delta;
        if (inp.right) state.heading -= TURN_SPEED * delta;

        // Move forward/backward
        const speed = state.running ? RUN_SPEED : WALK_SPEED;
        let moveX = 0, moveZ = 0;
        if (inp.forward) {
            moveX = Math.sin(state.heading) * speed;
            moveZ = Math.cos(state.heading) * speed;
        }
        if (inp.backward) {
            moveX = -Math.sin(state.heading) * speed * 0.5;
            moveZ = -Math.cos(state.heading) * speed * 0.5;
        }

        // Apply movement
        entity.velocity.x = moveX;
        entity.velocity.z = moveZ;
        pos.x += moveX * delta;
        pos.z += moveZ * delta;

        // Jump / gravity
        const groundY = getHeight(pos.x, pos.z);
        if (inp.jump && !state.jumping) {
            state.jumping = true;
            state.verticalVel = JUMP_VELOCITY;
            inp.jump = false;
        }
        if (state.jumping) {
            state.verticalVel += GRAVITY * delta;
            pos.y += state.verticalVel * delta;
            if (pos.y <= groundY) {
                pos.y = groundY;
                state.jumping = false;
                state.verticalVel = 0;
            }
        } else {
            pos.y = groundY;
        }

        // Rotation
        if (state.mesh) {
            state.mesh.rotation.y = state.heading;
        }
        // Also set on entity for Yuka sync
        entity.rotation = entity.rotation || {};

        // Third-person camera
        const camX = pos.x - Math.sin(state.heading) * CAM_DISTANCE;
        const camZ = pos.z - Math.cos(state.heading) * CAM_DISTANCE;
        const camY = pos.y + CAM_HEIGHT;
        camera.position.lerp(new THREE.Vector3(camX, camY, camZ), delta * 3);
        camera.lookAt(pos.x, pos.y + 1.5, pos.z);

        // Update animation mixer
        if (entity._mixer) entity._mixer.update(delta * 1.5);
    }

    // Click handler for possessing animals
    function onPointerDown(event) {
        if (state.active) return;
        const rect = event.target.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);

        // Collect all animal meshes
        const meshes = [];
        for (const entity of entityManager.entities) {
            if (entity._type === 'deer' || entity._type === 'fox') {
                if (entity._mixer?._root) {
                    entity._mixer._root.traverse(child => {
                        if (child.isMesh) {
                            child._yukaEntity = entity;
                            meshes.push(child);
                        }
                    });
                }
            }
        }

        const hits = raycaster.intersectObjects(meshes, false);
        if (hits.length > 0) {
            const entity = hits[0].object._yukaEntity;
            if (entity) possess(entity);
        }
    }

    return { state, possess, release, update, onPointerDown };
}
