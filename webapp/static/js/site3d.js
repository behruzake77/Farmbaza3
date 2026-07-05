/* ══════════════════════════════════════════════════════
   SITE 3D — butun sayt bo'ylab ishlaydigan 3D fon animatsiyasi
   Uslublar: pills | particles | molecules | waves | none
   Uslubni admin panel > Sozlamalar bo'limidan tanlash mumkin.
═══════════════════════════════════════════════════════ */
(function () {
  const canvas = document.getElementById('site-3d');
  if (!canvas) return;

  const style = (canvas.dataset.style || 'pills').toLowerCase();
  if (style === 'none') return;
  if (typeof THREE === 'undefined') return;

  const W = () => window.innerWidth;
  const H = () => window.innerHeight;

  /* ── Renderer ── */
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W(), H());

  /* ── Scene & Camera ── */
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0xeef4fa, 0.035);

  const camera = new THREE.PerspectiveCamera(45, W() / H(), 0.1, 100);
  camera.position.set(0, 0, 15);

  /* ── Lights ── */
  scene.add(new THREE.AmbientLight(0xd6e8f8, 0.7));
  const sun = new THREE.DirectionalLight(0xffffff, 1.3);
  sun.position.set(5, 8, 6);
  scene.add(sun);
  const rim = new THREE.PointLight(0x1a6fa8, 1.1, 28);
  rim.position.set(3, 6, -4);
  scene.add(rim);
  const rimR = new THREE.PointLight(0x2a9d8f, 0.6, 22);
  rimR.position.set(-5, -3, 2);
  scene.add(rimR);

  const movers = []; // { mesh, update(t) }

  /* ═══ PILLS uslubi ═══ */
  function buildPills() {
    const PILLS = [
      { color: 0x1a6fa8, metalness: 0.08, roughness: 0.25, opacity: 0.85 },
      { color: 0xffffff, metalness: 0.1, roughness: 0.15, opacity: 0.8 },
      { color: 0xe8f4fb, metalness: 0.05, roughness: 0.2, opacity: 0.75 },
      { color: 0x2a9d8f, metalness: 0.1, roughness: 0.3, opacity: 0.72 },
      { color: 0xf0c040, metalness: 0.12, roughness: 0.22, opacity: 0.74 },
      { color: 0xd64550, metalness: 0.08, roughness: 0.28, opacity: 0.7 },
      { color: 0x90c8f0, metalness: 0.06, roughness: 0.18, opacity: 0.8 },
    ];
    const COUNT = 26;
    for (let i = 0; i < COUNT; i++) {
      const cfg = PILLS[i % PILLS.length];
      const other = PILLS[(i + 3) % PILLS.length];
      const isHalf = i % 3 === 0;

      const mat1 = new THREE.MeshStandardMaterial({ color: cfg.color, metalness: cfg.metalness, roughness: cfg.roughness, transparent: true, opacity: cfg.opacity });
      const mat2 = new THREE.MeshStandardMaterial({ color: isHalf ? other.color : cfg.color, metalness: cfg.metalness, roughness: cfg.roughness, transparent: true, opacity: cfg.opacity });

      const r = 0.11 + Math.random() * 0.1;
      const len = 0.28 + Math.random() * 0.5;
      const group = new THREE.Group();

      const top = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), mat1);
      top.position.y = len / 2;
      const bot = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), mat2);
      bot.position.y = -len / 2;
      const cylTop = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len / 2, 20), mat1);
      cylTop.position.y = len / 4;
      const cylBot = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len / 2, 20), mat2);
      cylBot.position.y = -len / 4;
      group.add(top, bot, cylTop, cylBot);

      const spread = 9;
      group.position.set((Math.random() - 0.5) * spread * 2.2, (Math.random() - 0.5) * spread * 1.3, (Math.random() - 0.5) * 6 - 1);
      group.rotation.set(Math.random() * Math.PI * 2, Math.random() * Math.PI * 2, Math.random() * Math.PI * 2);
      group.scale.setScalar(0.7 + Math.random() * 0.65);
      scene.add(group);

      const vy = (Math.random() - 0.5) * 0.003;
      const vx = (Math.random() - 0.5) * 0.002;
      const rx = (Math.random() - 0.5) * 0.008;
      const ry = (Math.random() - 0.5) * 0.006;
      const rz = (Math.random() - 0.5) * 0.004;
      const phase = Math.random() * Math.PI * 2;

      movers.push({
        mesh: group,
        update(t) {
          group.position.y += Math.sin(t * 0.6 + phase) * 0.0015 + vy;
          group.position.x += Math.cos(t * 0.4 + phase * 1.3) * 0.001 + vx;
          if (group.position.y > 7) group.position.y = -7;
          if (group.position.y < -7) group.position.y = 7;
          if (group.position.x > 13) group.position.x = -13;
          if (group.position.x < -13) group.position.x = 13;
          group.rotation.x += rx;
          group.rotation.y += ry;
          group.rotation.z += rz;
        },
      });
    }
  }

  /* ═══ PARTICLES uslubi — suzib yuruvchi nurli zarrachalar tarmog'i ═══ */
  function buildParticles() {
    const COUNT = 70;
    const nodes = [];
    const colors = [0x1a6fa8, 0x2a9d8f, 0x90c8f0, 0xf0c040];

    for (let i = 0; i < COUNT; i++) {
      const color = colors[i % colors.length];
      const geo = new THREE.SphereGeometry(0.05 + Math.random() * 0.06, 10, 8);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.75 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set((Math.random() - 0.5) * 24, (Math.random() - 0.5) * 14, (Math.random() - 0.5) * 8 - 1);
      scene.add(mesh);
      nodes.push(mesh);

      const vy = (Math.random() - 0.5) * 0.004;
      const vx = (Math.random() - 0.5) * 0.003;
      const phase = Math.random() * Math.PI * 2;
      movers.push({
        mesh,
        update(t) {
          mesh.position.y += Math.sin(t * 0.5 + phase) * 0.001 + vy;
          mesh.position.x += Math.cos(t * 0.35 + phase) * 0.0008 + vx;
          if (mesh.position.y > 8) mesh.position.y = -8;
          if (mesh.position.y < -8) mesh.position.y = 8;
          if (mesh.position.x > 13) mesh.position.x = -13;
          if (mesh.position.x < -13) mesh.position.x = 13;
        },
      });
    }

    // Yaqin nuqtalarni chiziq bilan bog'lash (statik topologiya, tez ishlashi uchun)
    const lineGeo = new THREE.BufferGeometry();
    const maxLines = COUNT * 2;
    const positions = new Float32Array(maxLines * 2 * 3);
    const pairs = [];
    for (let i = 0; i < COUNT; i++) {
      let closest = null, closestDist = Infinity;
      for (let j = 0; j < COUNT; j++) {
        if (i === j) continue;
        const d = nodes[i].position.distanceTo(nodes[j].position);
        if (d < closestDist) { closestDist = d; closest = j; }
      }
      if (closest !== null && closestDist < 7) pairs.push([i, closest]);
    }
    lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const lineMat = new THREE.LineBasicMaterial({ color: 0x1a6fa8, transparent: true, opacity: 0.15 });
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    movers.push({
      mesh: lines,
      update() {
        const arr = lineGeo.attributes.position.array;
        for (let k = 0; k < pairs.length; k++) {
          const [a, b] = pairs[k];
          const pa = nodes[a].position, pb = nodes[b].position;
          arr[k * 6] = pa.x; arr[k * 6 + 1] = pa.y; arr[k * 6 + 2] = pa.z;
          arr[k * 6 + 3] = pb.x; arr[k * 6 + 4] = pb.y; arr[k * 6 + 5] = pb.z;
        }
        lineGeo.attributes.position.needsUpdate = true;
        lineGeo.setDrawRange(0, pairs.length * 2);
      },
    });
  }

  /* ═══ MOLECULES uslubi — molekula/atom klasterlari ═══ */
  function buildMolecules() {
    const CLUSTERS = 9;
    const palette = [0x1a6fa8, 0x2a9d8f, 0xf0c040, 0xd64550, 0x90c8f0];

    for (let c = 0; c < CLUSTERS; c++) {
      const group = new THREE.Group();
      const centerColor = palette[c % palette.length];
      const centerMat = new THREE.MeshStandardMaterial({ color: centerColor, metalness: 0.15, roughness: 0.25, transparent: true, opacity: 0.85 });
      const center = new THREE.Mesh(new THREE.SphereGeometry(0.32, 20, 16), centerMat);
      group.add(center);

      const satelliteCount = 3 + Math.floor(Math.random() * 3);
      for (let s = 0; s < satelliteCount; s++) {
        const dir = new THREE.Vector3((Math.random() - 0.5), (Math.random() - 0.5), (Math.random() - 0.5)).normalize();
        const dist = 0.75 + Math.random() * 0.35;
        const satPos = dir.clone().multiplyScalar(dist);

        const satMat = new THREE.MeshStandardMaterial({ color: palette[(c + s + 1) % palette.length], metalness: 0.1, roughness: 0.3, transparent: true, opacity: 0.78 });
        const sat = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 12), satMat);
        sat.position.copy(satPos);
        group.add(sat);

        const bondMat = new THREE.MeshBasicMaterial({ color: 0xbddcf0, transparent: true, opacity: 0.4 });
        const bondLen = dist;
        const bond = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, bondLen, 8), bondMat);
        bond.position.copy(satPos.clone().multiplyScalar(0.5));
        bond.lookAt(satPos);
        bond.rotateX(Math.PI / 2);
        group.add(bond);
      }

      group.position.set((Math.random() - 0.5) * 20, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 6 - 1);
      group.scale.setScalar(1.1 + Math.random() * 0.9);
      scene.add(group);

      const vy = (Math.random() - 0.5) * 0.0025;
      const vx = (Math.random() - 0.5) * 0.0018;
      const ry = 0.002 + Math.random() * 0.004;
      const rx = (Math.random() - 0.5) * 0.002;
      const phase = Math.random() * Math.PI * 2;

      movers.push({
        mesh: group,
        update(t) {
          group.position.y += Math.sin(t * 0.5 + phase) * 0.0012 + vy;
          group.position.x += vx;
          if (group.position.y > 7) group.position.y = -7;
          if (group.position.y < -7) group.position.y = 7;
          if (group.position.x > 12) group.position.x = -12;
          if (group.position.x < -12) group.position.x = 12;
          group.rotation.y += ry;
          group.rotation.x += rx;
        },
      });
    }
  }

  /* ═══ WAVES uslubi — sokin to'lqinlanuvchi katak yuzasi ═══ */
  function buildWaves() {
    const geo = new THREE.PlaneGeometry(34, 20, 46, 26);
    const mat = new THREE.MeshBasicMaterial({ color: 0x1a6fa8, wireframe: true, transparent: true, opacity: 0.16 });
    const plane = new THREE.Mesh(geo, mat);
    plane.rotation.x = -Math.PI / 2.6;
    plane.position.set(0, -3.5, -3);
    scene.add(plane);

    const basePositions = geo.attributes.position.array.slice();

    movers.push({
      mesh: plane,
      update(t) {
        const pos = geo.attributes.position.array;
        for (let i = 0; i < pos.length; i += 3) {
          const x = basePositions[i];
          const y = basePositions[i + 1];
          pos[i + 2] = Math.sin(x * 0.35 + t * 0.7) * 0.5 + Math.cos(y * 0.3 + t * 0.5) * 0.4;
        }
        geo.attributes.position.needsUpdate = true;
      },
    });

    // Suzib yuruvchi yorug' zarralar to'lqin ustida
    const dots = [];
    for (let i = 0; i < 24; i++) {
      const mat2 = new THREE.MeshBasicMaterial({ color: 0x2a9d8f, transparent: true, opacity: 0.6 });
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.05, 10, 8), mat2);
      dot.position.set((Math.random() - 0.5) * 22, (Math.random() - 0.5) * 10, (Math.random() - 0.5) * 6);
      scene.add(dot);
      dots.push(dot);
      const vy = (Math.random() - 0.5) * 0.003;
      const phase = Math.random() * Math.PI * 2;
      movers.push({
        mesh: dot,
        update(t) {
          dot.position.y += Math.sin(t * 0.6 + phase) * 0.001 + vy;
          if (dot.position.y > 6) dot.position.y = -6;
          if (dot.position.y < -6) dot.position.y = 6;
        },
      });
    }
  }

  const BUILDERS = { pills: buildPills, particles: buildParticles, molecules: buildMolecules, waves: buildWaves };
  (BUILDERS[style] || buildPills)();

  /* ── Mouse parallax ── */
  let mx = 0, my = 0;
  window.addEventListener('mousemove', (e) => {
    mx = (e.clientX / window.innerWidth - 0.5) * 0.4;
    my = (e.clientY / window.innerHeight - 0.5) * 0.2;
  });

  /* ── Resize ── */
  window.addEventListener('resize', () => {
    renderer.setSize(W(), H());
    camera.aspect = W() / H();
    camera.updateProjectionMatrix();
  });

  /* ── Animation loop ── */
  let t = 0;
  function animate() {
    requestAnimationFrame(animate);
    t += 0.016;
    for (let i = 0; i < movers.length; i++) movers[i].update(t);

    camera.position.x += (mx - camera.position.x) * 0.03;
    camera.position.y += (-my - camera.position.y) * 0.03;
    camera.lookAt(0, 0, 0);

    renderer.render(scene, camera);
  }
  animate();
})();
