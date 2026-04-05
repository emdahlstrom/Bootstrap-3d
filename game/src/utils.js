import * as THREE from 'three';

export const BOUNDS = 18;

export function rand(min, max) {
    return min + Math.random() * (max - min);
}

export function convertToBasicMaterials(model, fallback = 0xcccccc) {
    model.traverse((child) => {
        if (!child.isMesh || !child.material) return;
        const old = child.material;
        child.material = new THREE.MeshBasicMaterial({
            color: old.color ? old.color.clone() : new THREE.Color(fallback),
        });
        old.dispose();
    });
}

let _toastEl = null;
let _toastTimeout = null;

export function showToast(text) {
    if (!_toastEl) _toastEl = document.getElementById('event-toast');
    if (!_toastEl) return;
    _toastEl.textContent = text;
    _toastEl.style.opacity = '1';
    clearTimeout(_toastTimeout);
    _toastTimeout = setTimeout(() => { _toastEl.style.opacity = '0'; }, 3000);
}
