import * as THREE from 'three';
import * as YUKA from 'yuka';
import { getHeight } from './terrain.js';
import { rand, BOUNDS, showToast } from './utils.js';

// Hunter states (Yuka FSM)
class SneakState extends YUKA.State {
    enter(hunter) {
        showToast('🔫 A hunter appears!');
    }
    execute(hunter, delta) {
        // Walk toward the exit point (opposite edge), crossing the whole meadow
        const target = hunter._exitTarget;
        if (target) {
            const dx = target.x - hunter.position.x;
            const dz = target.z - hunter.position.z;
            const d = Math.sqrt(dx * dx + dz * dz);
            if (d > 2) {
                hunter.velocity.set((dx / d) * 1.5, 0, (dz / d) * 1.5);
            } else {
                // Reached the other side — just leave
                hunter.stateMachine.changeTo('gone');
                return;
            }
        }
        if (hunter._attackerCount > 0 || hunter._confidence < 0.7) {
            hunter.stateMachine.changeTo('panic');
        }
    }
}

class PanicState extends YUKA.State {
    enter(hunter) {
        showToast('😱 The animals attack! Hunter panics!');
    }
    execute(hunter, delta) {
        hunter._wobble += delta * 15;
        const mesh = hunter._renderMesh;
        if (!mesh) return;

        mesh.rotation.z = Math.sin(hunter._wobble) * 0.2;
        const mouth = mesh.getObjectByName('mouth');
        if (mouth) mouth.scale.setScalar(1 + (1 - hunter._confidence) * 2);
        const armL = mesh.getObjectByName('armL');
        const armR = mesh.getObjectByName('armR');
        if (armL) armL.rotation.z = 0.3 + Math.sin(hunter._wobble * 1.3) * 0.8;
        if (armR) armR.rotation.z = -0.3 + Math.cos(hunter._wobble * 1.5) * 0.8;
        const gun = mesh.getObjectByName('gun');
        if (gun && hunter._confidence < 0.4) gun.visible = false;

        // Flee away from animals
        hunter._fleeDir.set(0, 0, 0);
        for (const entity of hunter._entityManager.entities) {
            if (!entity._type) continue;
            const dx = hunter.position.x - entity.position.x;
            const dz = hunter.position.z - entity.position.z;
            const d = Math.sqrt(dx * dx + dz * dz);
            if (d < 10 && d > 0.1) {
                hunter._fleeDir.x += dx / (d * d);
                hunter._fleeDir.z += dz / (d * d);
            }
        }
        if (hunter._fleeDir.length() > 0.01) {
            hunter._fleeDir.normalize();
        } else {
            const pos = hunter.position;
            hunter._fleeDir.set(pos.x, 0, pos.z).normalize();
        }

        const speed = 3 + (1 - hunter._confidence) * 5;
        hunter.velocity.x += (hunter._fleeDir.x * speed - hunter.velocity.x) * delta * 3;
        hunter.velocity.z += (hunter._fleeDir.z * speed - hunter.velocity.z) * delta * 3;

        // Check if escaped
        const dist = Math.sqrt(hunter.position.x ** 2 + hunter.position.z ** 2);
        if ((hunter._confidence <= 0 && dist > BOUNDS) || dist > BOUNDS + 15) {
            hunter.stateMachine.changeTo('gone');
        }
    }
}

class GoneState extends YUKA.State {
    enter(hunter) {
        hunter.active = false;
        hunter._renderMesh.visible = false;
        // Reset mesh
        const gun = hunter._renderMesh.getObjectByName('gun');
        if (gun) gun.visible = true;
        const mouth = hunter._renderMesh.getObjectByName('mouth');
        if (mouth) mouth.scale.setScalar(1);
        hunter._renderMesh.rotation.z = 0;
        showToast('🏃 The hunter flees! The meadow is safe.');
    }
    execute() {}
}

function buildHunterMesh() {
    const g = new THREE.Group();
    const boot = new THREE.MeshBasicMaterial({ color: 0x3a2510 });
    const leg = new THREE.MeshBasicMaterial({ color: 0x8b7d5a });
    const vest = new THREE.MeshBasicMaterial({ color: 0x5a6b3a });
    const flannel = new THREE.MeshBasicMaterial({ color: 0xcc3333 });
    const skin = new THREE.MeshBasicMaterial({ color: 0xf0c090 });
    const hat = new THREE.MeshBasicMaterial({ color: 0xff6600 });
    const eye = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const pupil = new THREE.MeshBasicMaterial({ color: 0x111111 });
    const gunMat = new THREE.MeshBasicMaterial({ color: 0x4a3520 });
    const mouthMat = new THREE.MeshBasicMaterial({ color: 0x331111 });

    // Boots
    g.add(Object.assign(new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.2, 0.35), boot), { position: new THREE.Vector3(-0.15, 0.1, 0.05) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.2, 0.35), boot), { position: new THREE.Vector3(0.15, 0.1, 0.05) }));
    // Legs
    g.add(Object.assign(new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.6, 8), leg), { position: new THREE.Vector3(-0.15, 0.5, 0) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.6, 8), leg), { position: new THREE.Vector3(0.15, 0.5, 0) }));
    // Body
    g.add(Object.assign(new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.6, 0.3), vest), { position: new THREE.Vector3(0, 1.1, 0) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.15, 0.25), flannel), { position: new THREE.Vector3(0, 0.78, 0) }));
    // Arms
    const armL = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.5, 8), leg);
    armL.position.set(-0.35, 1.05, 0); armL.rotation.z = 0.3; armL.name = 'armL'; g.add(armL);
    const armR = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.5, 8), leg);
    armR.position.set(0.35, 1.05, 0); armR.rotation.z = -0.3; armR.name = 'armR'; g.add(armR);
    // Head
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 8), skin);
    head.position.set(0, 1.6, 0); head.name = 'head'; g.add(head);
    // Hat
    g.add(Object.assign(new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, 0.2, 12), hat), { position: new THREE.Vector3(0, 1.82, 0) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.04, 12), hat), { position: new THREE.Vector3(0, 1.72, 0) }));
    // Eyes
    g.add(Object.assign(new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), eye), { position: new THREE.Vector3(-0.08, 1.63, 0.18) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), eye), { position: new THREE.Vector3(0.08, 1.63, 0.18) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 4), pupil), { position: new THREE.Vector3(-0.08, 1.63, 0.22) }));
    g.add(Object.assign(new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 4), pupil), { position: new THREE.Vector3(0.08, 1.63, 0.22) }));
    // Gun
    const gun = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.03, 1.0, 6), gunMat);
    gun.position.set(0.4, 1.1, 0.15); gun.rotation.z = -0.6; gun.rotation.x = 0.2; gun.name = 'gun'; g.add(gun);
    // Mouth
    const mouth = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 6), mouthMat);
    mouth.position.set(0, 1.53, 0.19); mouth.name = 'mouth'; g.add(mouth);

    g.visible = false;
    return g;
}

export function createHunter(entityManager, scene) {
    const mesh = buildHunterMesh();
    scene.add(mesh);

    const hunter = new YUKA.Vehicle();
    hunter.active = false;
    hunter._type = 'hunter';
    hunter._renderMesh = mesh;
    hunter._entityManager = entityManager;
    hunter._confidence = 1.0;
    hunter._attackerCount = 0;
    hunter._wobble = 0;
    hunter._fleeDir = new YUKA.Vector3();

    hunter.setRenderComponent(mesh, (entity, renderMesh) => {
        renderMesh.position.set(entity.position.x, entity.position.y, entity.position.z);
        if (entity.velocity.length() > 0.1) {
            renderMesh.rotation.y = Math.atan2(entity.velocity.x, entity.velocity.z);
        }
    });

    // State machine
    hunter.stateMachine = new YUKA.StateMachine(hunter);
    hunter.stateMachine.add('sneak', new SneakState());
    hunter.stateMachine.add('panic', new PanicState());
    hunter.stateMachine.add('gone', new GoneState());

    entityManager.add(hunter);
    return hunter;
}

export function spawnHunter(hunter) {
    const angle = rand(0, Math.PI * 2);
    const edge = BOUNDS + 3;
    hunter.position.set(Math.cos(angle) * edge, 0, Math.sin(angle) * edge);
    hunter.position.y = getHeight(hunter.position.x, hunter.position.z);
    // Exit target: opposite side of the meadow (cross the whole area)
    const exitAngle = angle + Math.PI + rand(-0.5, 0.5);
    hunter._exitTarget = { x: Math.cos(exitAngle) * edge, z: Math.sin(exitAngle) * edge };
    hunter.velocity.set(0, 0, 0);
    hunter._confidence = 1.0;
    hunter._attackerCount = 0;
    hunter._wobble = 0;
    hunter.active = true;
    hunter._renderMesh.visible = true;
    hunter.stateMachine.changeTo('sneak');
}

export function updateHunter(hunter, entityManager, delta) {
    if (!hunter.active) return;

    const pos = hunter.position;
    pos.y = getHeight(pos.x, pos.z);

    // Count attackers + apply charge forces to animals
    hunter._attackerCount = 0;
    for (const entity of entityManager.entities) {
        if (!entity._type || entity._type === 'hunter' || entity._type === 'fox') continue;
        const dx = pos.x - entity.position.x;
        const dz = pos.z - entity.position.z;
        const d = Math.sqrt(dx * dx + dz * dz);
        if (d < 16) {
            const charge = 6 * (1 - d / 10);
            entity.velocity.x -= (dx / d) * charge * delta;
            entity.velocity.z -= (dz / d) * charge * delta;
        }
        if (d < 5) {
            hunter._attackerCount++;
            hunter._confidence -= delta * 0.4;
        }
    }

    // Run state machine
    hunter.stateMachine.update(delta);

    // Move
    pos.x += hunter.velocity.x * delta;
    pos.z += hunter.velocity.z * delta;
    pos.y = getHeight(pos.x, pos.z);

    hunter._renderMesh.position.y += Math.abs(Math.sin(hunter._wobble * 0.8)) * 0.05;
}
