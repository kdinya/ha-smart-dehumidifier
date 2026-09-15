import { html } from '../files/lit-proxy.js';

import {
  toFiniteNumber,
  toPositiveNumber,
  clamp,
  layoutUnit,
  isEntityOn,
  getLayoutBaseWidth,
} from '../dh-utils.js';


function speedToDuration(value) {
  const speed = clamp(value, 1, 100);
  return 100 / speed;
}

function ensureParticles(card, count) {
  if (!Array.isArray(card._efxParticles) || card._efxParticles.length !== count) {
    card._efxParticles = Array.from({ length: count }, () => ({
      angle: Math.random() * Math.PI * 2,
      distMod: Math.random(),
      durMod: Math.random(),
      delayMod: Math.random(),
    }));
  }

  return card._efxParticles;
}

// Функцію getParticleCss видалено повністю! Тепер код значно легший.

export function renderVisualEffects(card, config = {}) {
  const fanEntity = config.fan_entity;
  const fanOn = isEntityOn(card, fanEntity);

  const layoutBaseWidth = getLayoutBaseWidth(config);

  const color = config.efx_color ?? '#00ffff';
  const offsetY = toFiniteNumber(config.efx_offset_y, 13);

  const showFan = config.efx_fan_show ?? true;
  const fanSize = toPositiveNumber(config.efx_fan_size, 400);
  const fanOpacity = clamp(toFiniteNumber(config.efx_fan_opacity, 10), 0, 100) / 100;
  const fanDur = speedToDuration(toFiniteNumber(config.efx_fan_speed, 70));

  const showComet = config.efx_comet_show ?? false;
  const cometSize = toPositiveNumber(config.efx_comet_size, 350);
  const cometDur = speedToDuration(toFiniteNumber(config.efx_comet_speed, 83));

  const showParts = config.efx_part_show ?? false;
  const numParts = Math.round(clamp(toFiniteNumber(config.efx_part_count, 55), 5, 100));
  const partSpread = toPositiveNumber(config.efx_part_spread, 400);
  const partDurBase = speedToDuration(toFiniteNumber(config.efx_part_speed, 86));

  if (!fanOn) {
    return html`
      <div class="efx-layer" style="opacity: 0; transition: opacity 1s ease;"></div>
    `;
  }

  const particles = showParts ? ensureParticles(card, numParts) : [];
  const particleSizeCss = layoutUnit(3, layoutBaseWidth);
  const fanSizeCss = layoutUnit(fanSize, layoutBaseWidth);
  const cometSizeCss = layoutUnit(cometSize, layoutBaseWidth);
  const offsetYCss = layoutUnit(offsetY, layoutBaseWidth);

  const isDragging = !!card._dragging;

  return html`
    <style>
      .efx-layer {
        position: absolute;
        inset: 0;
        z-index: 0;
        overflow: hidden;
        pointer-events: none;
        border-radius: inherit;
        opacity: 1;
        transition: opacity 1s ease;
      }

      .efx-group {
        position: absolute;
        inset: 0;
        transform: translateY(${offsetYCss});
      }

      .is-dragging .efx-bg-fan,
      .is-dragging .efx-comet-tail,
      .is-dragging .efx-particle,
      .dh-suspended .efx-bg-fan,
      .dh-suspended .efx-comet-tail,
      .dh-suspended .efx-particle {
        animation-play-state: paused !important;
      }

      .is-dragging .efx-particles,
      .dh-suspended .efx-particles {
        opacity: 0 !important;
        transition: opacity 0.1s ease;
      }

      .efx-bg-fan {
        position: absolute;
        top: 50%;
        left: 50%;
        display: ${showFan ? 'block' : 'none'};
        color: ${color};
        opacity: ${fanOpacity};
        --mdc-icon-size: ${fanSizeCss};
        animation: efx-bg-spin ${fanDur}s linear infinite;
      }

      .efx-comet-orbit {
        position: absolute;
        top: 50%;
        left: 50%;
        display: ${showComet ? 'block' : 'none'};
        width: ${cometSizeCss};
        height: ${cometSizeCss};
        transform: translate(-50%, -50%);
        border-radius: 50%;
        -webkit-mask: radial-gradient(transparent 68%, black 70%);
        mask: radial-gradient(transparent 68%, black 70%);
      }

      .efx-comet-tail {
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: conic-gradient(
          from 0deg,
          transparent 50%,
          ${color}66 80%,
          ${color} 100%
        );
        animation: efx-rotate ${cometDur}s linear infinite;
      }

      .efx-particles {
        position: absolute;
        inset: 0;
        display: ${showParts ? 'block' : 'none'};
        transition: opacity 0.4s ease;
      }

      .efx-particle {
        position: absolute;
        top: 50%;
        left: 50%;
        width: ${particleSizeCss};
        height: ${particleSizeCss};
        opacity: 0;
        background: #fff;
        border-radius: 50%;
        box-shadow: 0 0 8px 2px ${color};
      }

      @keyframes efx-bg-spin {
        0% { transform: translate(-50%, -50%) rotate(0deg); }
        100% { transform: translate(-50%, -50%) rotate(360deg); }
      }

      @keyframes efx-rotate {
        100% { transform: rotate(360deg); }
      }

      @keyframes efx-particle-fly {
        0% {
          transform: translate(-50%, -50%) scale(0.1);
          opacity: 0;
        }
        20% {
          opacity: 0.9;
        }
        80% {
          opacity: 0.9;
        }
        100% {
          transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(2.5);
          opacity: 0;
        }
      }
    </style>

    <div class="efx-layer ${isDragging ? 'is-dragging' : ''}">
      <div class="efx-group">
        <ha-icon icon="mdi:fan" class="efx-bg-fan"></ha-icon>

        <div class="efx-comet-orbit">
          <div class="efx-comet-tail"></div>
        </div>

        <div class="efx-particles">
          ${showParts
            ? particles.map((p) => {
                // ОПТИМІЗАЦІЯ: Усі розрахунки відбуваються тут, а стилі вставляються інлайн
                const dist = 30 + p.distMod * partSpread;
                const dx = layoutUnit(Math.cos(p.angle) * dist, layoutBaseWidth);
                const dy = layoutUnit(Math.sin(p.angle) * dist, layoutBaseWidth);
                const duration = partDurBase + p.durMod * 2;
                const delay = -(p.delayMod * duration);

                return html`<div class="efx-particle" style="--dx: ${dx}; --dy: ${dy}; animation: efx-particle-fly ${duration}s ease-out infinite ${delay}s;"></div>`;
              })
            : html``}
        </div>
      </div>
    </div>
  `;
}