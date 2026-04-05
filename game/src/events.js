import * as YUKA from 'yuka';
import { rand, showToast } from './utils.js';
import { spawnHunter } from './hunter.js';

const EVENT_MIN = 8;
const EVENT_MAX = 20;

export function createEventSystem(entityManager, weatherSystem, hunter) {
    let timer = 5;

    function trigger() {
        const pool = ['weather', 'stampede', 'grazing_halt', 'fox_frenzy', 'scatter'];
        if (!hunter.active) pool.push('hunter', 'hunter'); // double weight

        const type = pool[Math.floor(rand(0, pool.length))];
        const entities = entityManager.entities;

        switch (type) {
            case 'weather': {
                const options = ['clear', 'cloudy', 'rain', 'storm', 'fog', 'golden_hour']
                    .filter(w => w !== weatherSystem.state.current);
                weatherSystem.setWeather(options[Math.floor(rand(0, options.length))]);
                break;
            }
            case 'stampede': {
                const angle = rand(0, Math.PI * 2);
                for (const e of entities) {
                    if (e._type === 'deer') {
                        e.velocity.x = Math.cos(angle) * e.maxSpeed * 1.5;
                        e.velocity.z = Math.sin(angle) * e.maxSpeed * 1.5;
                    }
                }
                showToast('🦌 The herd stampedes!');
                break;
            }
            case 'grazing_halt': {
                for (const e of entities) {
                    if (e._type === 'deer') {
                        e.velocity.multiplyScalar(0.05);
                        e._grazeTimer = rand(3, 6);
                    }
                }
                showToast('🌿 The herd stops to graze');
                break;
            }
            case 'fox_frenzy': {
                for (const e of entities) {
                    if (e._type === 'fox') {
                        const original = e.maxSpeed;
                        e.maxSpeed *= 2;
                        setTimeout(() => { e.maxSpeed = original; }, 4000);
                    }
                }
                showToast('🦊 The fox charges!');
                break;
            }
            case 'scatter': {
                for (const e of entities) {
                    if (!e._type || e._type === 'hunter') continue;
                    const d = Math.sqrt(e.position.x ** 2 + e.position.z ** 2) || 1;
                    e.velocity.x = (e.position.x / d) * e.maxSpeed * 1.5;
                    e.velocity.z = (e.position.z / d) * e.maxSpeed * 1.5;
                }
                showToast('💨 Something spooks the animals!');
                break;
            }
            case 'hunter': {
                spawnHunter(hunter);
                break;
            }
        }
    }

    function update(rawDelta) {
        timer -= rawDelta;
        if (timer <= 0) {
            trigger();
            timer = rand(EVENT_MIN, EVENT_MAX);
        }
    }

    return { update };
}
