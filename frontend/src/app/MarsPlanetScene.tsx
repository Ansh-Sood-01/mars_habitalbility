'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export type MarsPhase = 'dawn' | 'day' | 'dust' | 'night';

const PALETTES: Record<MarsPhase, { key: string; fill: string; glow: string; stars: string; intensity: number }> = {
  dawn:  { key: '#ffd0a3', fill: '#b65e4b', glow: '#e77852', stars: '#d8c4b6', intensity: 2.5 },
  day:   { key: '#fff0c2', fill: '#c78b5a', glow: '#f09a5c', stars: '#e7d8b8', intensity: 3.1 },
  dust:  { key: '#f3a17f', fill: '#8e4b54', glow: '#be5e54', stars: '#d9a49a', intensity: 1.9 },
  night: { key: '#b6d7e5', fill: '#526a9a', glow: '#688bc1', stars: '#a9c8e4', intensity: 1.25 },
};

function createSurfaceTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 2048;
  canvas.height = 1024;
  const context = canvas.getContext('2d');
  if (!context) return null;

  const base = context.createLinearGradient(0, 0, canvas.width, canvas.height);
  base.addColorStop(0, '#b86b4c');
  base.addColorStop(0.34, '#8c4939');
  base.addColorStop(0.7, '#c17c54');
  base.addColorStop(1, '#6f3c35');
  context.fillStyle = base;
  context.fillRect(0, 0, canvas.width, canvas.height);

  let seed = 1729;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  context.save();
  context.filter = 'blur(22px)';
  for (let i = 0; i < 190; i += 1) {
    const x = random() * canvas.width;
    const y = random() * canvas.height;
    const rx = 18 + random() * 110;
    const ry = 8 + random() * 45;
    context.fillStyle = random() > 0.5 ? 'rgba(54,29,28,.30)' : 'rgba(231,157,105,.24)';
    context.beginPath();
    context.ellipse(x, y, rx, ry, random() * Math.PI, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();

  for (let i = 0; i < 115; i += 1) {
    const x = random() * canvas.width;
    const y = random() * canvas.height;
    const radius = 5 + random() * 31;
    const shade = random() > 0.5;
    const crater = context.createRadialGradient(x - radius * 0.22, y - radius * 0.25, radius * 0.08, x, y, radius);
    crater.addColorStop(0, shade ? 'rgba(47,25,25,.66)' : 'rgba(230,158,112,.52)');
    crater.addColorStop(0.48, shade ? 'rgba(91,48,39,.48)' : 'rgba(170,91,62,.54)');
    crater.addColorStop(0.78, shade ? 'rgba(212,142,100,.46)' : 'rgba(83,42,37,.44)');
    crater.addColorStop(1, 'rgba(49,28,29,0)');
    context.fillStyle = crater;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = shade ? 'rgba(235,167,119,.15)' : 'rgba(48,28,29,.24)';
    context.lineWidth = 2 + random() * 4;
    context.beginPath();
    context.arc(x, y, radius * 0.76, 0.1, Math.PI * 1.82);
    context.stroke();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

export default function MarsPlanetScene({ phase }: { phase: MarsPhase }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const phaseRef = useRef<MarsPhase>(phase);

  useEffect(() => { phaseRef.current = phase; }, [phase]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let renderer: THREE.WebGLRenderer | null = null;
    let frame = 0;
    let disposed = false;
    let resizeObserver: ResizeObserver | null = null;

    try {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 80);
      camera.position.set(0, 0, 5.8);

      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.65));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.18;
      renderer.setClearColor(0x000000, 0);
      renderer.domElement.setAttribute('aria-hidden', 'true');
      renderer.domElement.className = 'ml-planet-webgl';
      host.appendChild(renderer.domElement);

      const ambient = new THREE.HemisphereLight(0xb8c5d2, 0x502f2a, 1.15);
      scene.add(ambient);

      const keyLight = new THREE.DirectionalLight(0xffd0a3, 2.5);
      keyLight.position.set(-3.5, 2.6, 4.5);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0xb65e4b, 0.8);
      fillLight.position.set(3.8, -1.5, 1.2);
      scene.add(fillLight);

      const texture = createSurfaceTexture();
      const planetMaterial = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        map: texture || undefined,
        bumpMap: texture || undefined,
        bumpScale: 0.075,
        roughness: 0.96,
        metalness: 0.015,
        emissive: new THREE.Color('#421b16'),
        emissiveIntensity: 0.08,
      });
      const planet = new THREE.Mesh(new THREE.SphereGeometry(1.38, 112, 112), planetMaterial);
      planet.rotation.z = -0.13;
      scene.add(planet);

      const atmosphereMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(PALETTES[phaseRef.current].glow),
        transparent: true,
        opacity: 0.18,
        side: THREE.BackSide,
        depthWrite: false,
      });
      const atmosphere = new THREE.Mesh(new THREE.SphereGeometry(1.48, 80, 80), atmosphereMaterial);
      scene.add(atmosphere);

      const outerHalo = new THREE.Mesh(
        new THREE.SphereGeometry(1.62, 64, 64),
        new THREE.MeshBasicMaterial({ color: '#d36b4c', transparent: true, opacity: 0.035, side: THREE.BackSide, depthWrite: false }),
      );
      scene.add(outerHalo);

      const orbit = new THREE.Mesh(
        new THREE.TorusGeometry(2.02, 0.006, 8, 180),
        new THREE.MeshBasicMaterial({ color: '#e9b18d', transparent: true, opacity: 0.38 }),
      );
      orbit.rotation.set(1.05, 0.16, -0.22);
      scene.add(orbit);

      const moonPath = new THREE.Group();
      scene.add(moonPath);
      const moon = new THREE.Mesh(
        new THREE.SphereGeometry(0.17, 36, 36),
        new THREE.MeshStandardMaterial({ color: '#b7a99b', roughness: 1, bumpScale: 0.025 }),
      );
      moon.position.set(2.02, 0.06, 0);
      moonPath.add(moon);
      const moonGlow = new THREE.Mesh(
        new THREE.SphereGeometry(0.205, 24, 24),
        new THREE.MeshBasicMaterial({ color: '#e4b28a', transparent: true, opacity: 0.07, side: THREE.BackSide }),
      );
      moon.add(moonGlow);

      const satellite = new THREE.Group();
      satellite.position.set(-1.84, 0.46, 0.2);
      const body = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.075, 0),
        new THREE.MeshStandardMaterial({ color: '#d8d6c9', metalness: 0.58, roughness: 0.42, emissive: '#463b32', emissiveIntensity: 0.18 }),
      );
      satellite.add(body);
      const panelMaterial = new THREE.MeshStandardMaterial({ color: '#4c7892', metalness: 0.65, roughness: 0.35, emissive: '#142d43', emissiveIntensity: 0.22 });
      const panelA = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.012, 0.11), panelMaterial);
      panelA.position.x = -0.18;
      satellite.add(panelA);
      const panelB = panelA.clone();
      panelB.position.x = 0.18;
      satellite.add(panelB);
      moonPath.add(satellite);

      const starPositions = new Float32Array(1050 * 3);
      let seed = 91;
      const randomStar = () => {
        seed = (seed * 1103515245 + 12345) % 2147483648;
        return seed / 2147483648;
      };
      for (let i = 0; i < 1050; i += 1) {
        starPositions[i * 3] = (randomStar() - 0.5) * 13;
        starPositions[i * 3 + 1] = (randomStar() - 0.5) * 7;
        starPositions[i * 3 + 2] = -1.4 - randomStar() * 8;
      }
      const starGeometry = new THREE.BufferGeometry();
      starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
      const starMaterial = new THREE.PointsMaterial({ color: '#d8c4b6', size: 0.014, transparent: true, opacity: 0.9, sizeAttenuation: true });
      const stars = new THREE.Points(starGeometry, starMaterial);
      scene.add(stars);

      const dustPositions = new Float32Array(110 * 3);
      for (let i = 0; i < 110; i += 1) {
        const angle = randomStar() * Math.PI * 2;
        const radius = 1.7 + randomStar() * 1.8;
        dustPositions[i * 3] = Math.cos(angle) * radius;
        dustPositions[i * 3 + 1] = (randomStar() - 0.5) * 2.6;
        dustPositions[i * 3 + 2] = Math.sin(angle) * radius * 0.55;
      }
      const dustGeometry = new THREE.BufferGeometry();
      dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
      const dustMaterial = new THREE.PointsMaterial({ color: '#d99573', size: 0.022, transparent: true, opacity: 0.35, sizeAttenuation: true });
      const dust = new THREE.Points(dustGeometry, dustMaterial);
      scene.add(dust);

      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const clock = new THREE.Clock();
      let elapsed = 0;

      const resize = () => {
        if (!renderer || !host) return;
        const width = Math.max(1, host.clientWidth);
        const height = Math.max(1, host.clientHeight);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      };

      resize();
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(host);

      const renderFrame = () => {
        if (disposed || !renderer) return;
        const delta = Math.min(clock.getDelta(), 0.05);
        elapsed += delta;
        const palette = PALETTES[phaseRef.current];

        if (!reducedMotion) {
          planet.rotation.y += delta * 0.055;
          moonPath.rotation.y += delta * 0.17;
          moonPath.rotation.z = Math.sin(elapsed * 0.12) * 0.08;
          satellite.rotation.x += delta * 0.22;
          dust.rotation.y -= delta * 0.018;
          stars.rotation.y += delta * 0.002;
          planet.position.y = Math.sin(elapsed * 0.34) * 0.025;
          atmosphere.scale.setScalar(1 + Math.sin(elapsed * 0.55) * 0.006);
        }

        keyLight.color.lerp(new THREE.Color(palette.key), 0.018);
        fillLight.color.lerp(new THREE.Color(palette.fill), 0.018);
        keyLight.intensity += (palette.intensity - keyLight.intensity) * 0.018;
        atmosphereMaterial.color.lerp(new THREE.Color(palette.glow), 0.018);
        starMaterial.color.lerp(new THREE.Color(palette.stars), 0.012);

        renderer.render(scene, camera);
        if (!reducedMotion) frame = window.requestAnimationFrame(renderFrame);
      };

      renderFrame();

      const handleVisibility = () => {
        if (!document.hidden && !reducedMotion && !frame) frame = window.requestAnimationFrame(renderFrame);
      };
      document.addEventListener('visibilitychange', handleVisibility);

      return () => {
        disposed = true;
        window.cancelAnimationFrame(frame);
        document.removeEventListener('visibilitychange', handleVisibility);
        resizeObserver?.disconnect();
        planet.geometry.dispose();
        planetMaterial.dispose();
        texture?.dispose();
        atmosphere.geometry.dispose();
        atmosphereMaterial.dispose();
        outerHalo.geometry.dispose();
        (outerHalo.material as THREE.Material).dispose();
        orbit.geometry.dispose();
        (orbit.material as THREE.Material).dispose();
        moon.geometry.dispose();
        (moon.material as THREE.Material).dispose();
        moonGlow.geometry.dispose();
        (moonGlow.material as THREE.Material).dispose();
        body.geometry.dispose();
        (body.material as THREE.Material).dispose();
        panelA.geometry.dispose();
        panelMaterial.dispose();
        starGeometry.dispose();
        starMaterial.dispose();
        dustGeometry.dispose();
        dustMaterial.dispose();
        renderer?.dispose();
        renderer?.domElement.remove();
      };
    } catch {
      host.classList.add('ml-webgl-unavailable');
    }
  }, []);

  return (
    <div className="ml-planet-stage ml-planet-stage-3d" aria-label="Animated three-dimensional Mars scene">
      <div className="ml-planet-fallback" aria-hidden="true" />
      <div className="ml-planet-canvas" ref={hostRef} aria-hidden="true" />
      <div className="ml-planet-scanline" aria-hidden="true" />
      <div className="ml-planet-caption"><span>OBJECT 04 / SOL</span><strong>MARS</strong><small>SIMULATED SURFACE LIGHTING</small></div>
      <div className="ml-planet-hud ml-hud-top"><span className="ml-hud-dot" /> ORBITAL VIEW <b>3D</b></div>
      <div className="ml-planet-hud ml-hud-bottom">QMS SIGNAL <i /> DATA / 01</div>
      <div className="ml-phase-readout"><span>ATMOSPHERE CYCLE</span><strong>{phase.toUpperCase()}</strong><small>SIMULATED · NOT LIVE WEATHER</small></div>
    </div>
  );
}
