/**
 * RilievoViewer3D — Parametric 3D viewer for Rilievo measurements.
 * Manual touch/mouse rotation (no OrbitControls).
 */
import { useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import * as THREE from 'three';

// ── RAL color map (approximate hex) ──
const RAL_HEX = {
    'RAL 9005': 0x0a0a0a, 'RAL 9010': 0xf5f0e8, 'RAL 7016': 0x383e42,
    'RAL 7035': 0xc5c7c4, 'RAL 6005': 0x1e3a2b, 'RAL 3000': 0xa52019,
    'RAL 5010': 0x004f7c, 'RAL 8017': 0x3e2b23,
};
const DEFAULT_COLOR = 0x383e42;

function getColor(m) {
    return RAL_HEX[m?.colore] ?? DEFAULT_COLOR;
}

function parseDim(profilo) {
    if (!profilo) return [30, 30];
    const nums = profilo.replace(/[^0-9.x]/gi, '').split('x').map(Number).filter(Boolean);
    return nums.length >= 2 ? nums : nums.length === 1 ? [nums[0], nums[0]] : [30, 30];
}

// ── Box helper (centered at origin, use position to place) ──
function box(w, h, d, color) {
    const g = new THREE.BoxGeometry(w, h, d);
    const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.3 });
    return new THREE.Mesh(g, mat);
}

function cylinder(radius, height, color) {
    const g = new THREE.CylinderGeometry(radius, radius, height, 16);
    const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.4 });
    return new THREE.Mesh(g, mat);
}

// ══════════════════════════════════════════
// RENDERERS
// ══════════════════════════════════════════

function renderInferriata(m) {
    const group = new THREE.Group();
    const L = (m.luce_larghezza || 1500) / 1000;
    const H = (m.luce_altezza || 1200) / 1000;
    const interasse = (m.interasse_montanti || 120) / 1000;
    const nTraversi = m.numero_traversi || 2;
    const [mw, md] = parseDim(m.profilo_montante).map(v => v / 1000);
    const [tw, td] = parseDim(m.profilo_traverso).map(v => v / 1000);
    const col = getColor(m);

    // Montanti
    const nMont = Math.max(2, Math.ceil(L / interasse) + 1);
    for (let i = 0; i < nMont; i++) {
        const x = -L / 2 + (i * L) / (nMont - 1);
        const b = box(mw, H, md, col);
        b.position.set(x, H / 2, 0);
        group.add(b);
    }
    // Traversi
    for (let i = 0; i < nTraversi; i++) {
        const y = ((i + 1) * H) / (nTraversi + 1);
        const b = box(L, tw, td, col);
        b.position.set(0, y, 0);
        group.add(b);
    }
    // Frame outline
    const frame = box(L + mw, 0.008, md + 0.002, 0x222222);
    frame.position.set(0, 0, 0);
    group.add(frame);
    const frameTop = frame.clone();
    frameTop.position.set(0, H, 0);
    group.add(frameTop);

    return group;
}

function renderCancello(m, pedonale) {
    const group = new THREE.Group();
    const L = (m.luce_netta || (pedonale ? 1000 : 4000)) / 1000;
    const H = (m.altezza || 1800) / 1000;
    const [tw, td] = parseDim(m.profilo_telaio).map(v => v / 1000);
    const [iw, id] = parseDim(m.profilo_infisso).map(v => v / 1000);
    const interasse = (m.interasse_infissi || 100) / 1000;
    const col = getColor(m);
    const nAnte = m.numero_ante || (pedonale ? 1 : 2);
    const anteW = L / nAnte;

    for (let a = 0; a < nAnte; a++) {
        const ox = -L / 2 + a * anteW + anteW / 2;
        // Telaio anta
        const top = box(anteW, tw, td, col); top.position.set(ox, H, 0); group.add(top);
        const bot = box(anteW, tw, td, col); bot.position.set(ox, 0, 0); group.add(bot);
        const left = box(tw, H, td, col); left.position.set(ox - anteW / 2, H / 2, 0); group.add(left);
        const right = box(tw, H, td, col); right.position.set(ox + anteW / 2, H / 2, 0); group.add(right);
        // Infissi verticali
        const nInf = Math.max(1, Math.ceil(anteW / interasse) - 1);
        for (let i = 1; i <= nInf; i++) {
            const x = ox - anteW / 2 + (i * anteW) / (nInf + 1);
            const b = box(iw, H - tw * 2, id, col);
            b.position.set(x, H / 2, 0);
            group.add(b);
        }
    }
    // Pilastri
    if (m.pilastri_esistenti) {
        const pw = (m.larghezza_pilastro || 300) / 1000;
        const pH = H + 0.2;
        const pl = box(pw, pH, pw, 0x888888);
        pl.position.set(-L / 2 - pw / 2 - 0.05, pH / 2, 0);
        group.add(pl);
        const pr = pl.clone();
        pr.position.set(L / 2 + pw / 2 + 0.05, pH / 2, 0);
        group.add(pr);
    }
    // Guida scorrevole
    if (m.tipo_apertura === 'scorrevole') {
        const rail = box(L * 1.3, 0.02, 0.06, 0x555555);
        rail.position.set(L * 0.15, 0.01, 0);
        group.add(rail);
    }
    // Motore
    if (!pedonale && m.motorizzazione) {
        const mot = box(0.3, 0.2, 0.2, 0x444444);
        mot.position.set(-L / 2 - 0.35, 0.15, 0);
        group.add(mot);
    }
    return group;
}

function renderScala(m) {
    const group = new THREE.Group();
    const nGradini = m.numero_gradini || 10;
    const alz = (m.alzata || 175) / 1000;
    const ped = (m.pedata || 280) / 1000;
    const largh = (m.larghezza || 900) / 1000;
    const spessore = (m.spessore_gradino || 4) / 1000;
    const col = getColor(m);

    // Gradini: pedata orizzontale + alzata verticale
    for (let i = 0; i < nGradini; i++) {
        const y = i * alz;
        const z = i * ped;
        // Pedata (piattaforma orizzontale)
        const g = box(largh, spessore, ped, col);
        g.position.set(0, y + alz + spessore / 2, z + ped / 2);
        group.add(g);
        // Alzata (pannello verticale)
        const a = box(largh, alz, spessore, col);
        a.position.set(0, y + alz / 2, z);
        group.add(a);
    }

    // Longheroni (struttura laterale lungo la diagonale)
    const totH = nGradini * alz;
    const totD = nGradini * ped;
    const diagL = Math.sqrt(totH * totH + totD * totD);
    const angle = Math.atan2(totH, totD);
    const [sw, sh] = parseDim(m.profilo_struttura).map(v => v / 1000);
    for (const side of [-1, 1]) {
        const b = box(sw, sh, diagL, 0x666666);
        b.rotation.x = -angle;
        b.position.set(side * (largh / 2 - sw / 2), totH / 2, totD / 2);
        group.add(b);
    }

    // Corrimano
    if (m.corrimano) {
        const hCorr = 1.0;
        const lato = m.lato_corrimano || 'dx';
        const sides = lato === 'entrambi' ? [-1, 1] : lato === 'sx' ? [-1] : [1];
        for (const s of sides) {
            const x = s * (largh / 2 + 0.02);
            // Montanti corrimano
            const interM = (m.interasse_montanti || 150) / 1000;
            const nM = Math.max(2, Math.ceil(diagL / interM));
            for (let i = 0; i <= nM; i++) {
                const frac = i / nM;
                const y = frac * totH;
                const z = frac * totD;
                const post = box(0.02, hCorr, 0.02, col);
                post.position.set(x, y + hCorr / 2, z);
                group.add(post);
            }
            // Rail corrimano (parallelo alla diagonale)
            const rail = cylinder(0.02, diagL, col);
            rail.rotation.x = -angle;
            rail.position.set(x, totH / 2 + hCorr, totD / 2);
            group.add(rail);
        }
    }
    return group;
}

function renderRecinzione(m) {
    const group = new THREE.Group();
    const lungTot = (m.lunghezza_totale || 5000) / 1000;
    const H = (m.altezza || 1500) / 1000;
    const interassePali = (m.interasse_pali || 2500) / 1000;
    const nPali = Math.max(2, Math.ceil(lungTot / interassePali) + 1);
    const actualSpacing = lungTot / (nPali - 1);
    const [pw, pd] = parseDim(m.profilo_palo).map(v => v / 1000);
    const nOrizz = m.numero_orizzontali || 3;
    const [ow, od] = parseDim(m.profilo_orizzontale).map(v => v / 1000);
    const [vw, vd] = parseDim(m.profilo_verticale).map(v => v / 1000);
    const interasseV = (m.interasse_verticali || 120) / 1000;
    const col = getColor(m);

    for (let i = 0; i < nPali; i++) {
        const x = -lungTot / 2 + i * actualSpacing;
        // Palo (extra 0.3m interrato)
        const p = box(pw, H + 0.3, pd, 0x555555);
        p.position.set(x, (H + 0.3) / 2 - 0.3, 0);
        group.add(p);
        // Pannello tra pali
        if (i < nPali - 1) {
            const cx = x + actualSpacing / 2;
            // Orizzontali
            for (let j = 0; j < nOrizz; j++) {
                const y = ((j + 1) * H) / (nOrizz + 1);
                const o = box(actualSpacing - pw, ow, od, col);
                o.position.set(cx, y, 0);
                group.add(o);
            }
            // Verticali
            const nV = Math.max(1, Math.ceil(actualSpacing / interasseV) - 1);
            for (let j = 1; j <= nV; j++) {
                const vx = x + pw / 2 + (j * (actualSpacing - pw)) / (nV + 1);
                const v = box(vw, H - 0.1, vd, col);
                v.position.set(vx, H / 2, 0);
                group.add(v);
            }
        }
    }
    // Terreno
    const ground = box(lungTot + 1, 0.02, 2, 0x8B7355);
    ground.position.set(0, -0.01, 0);
    group.add(ground);
    return group;
}

function renderRinghiera(m) {
    const group = new THREE.Group();
    const L = (m.lunghezza || 3000) / 1000;
    const H = (m.altezza || 900) / 1000;
    const [cw, cd] = parseDim(m.profilo_corrente).map(v => v / 1000);
    const [mw, md] = parseDim(m.profilo_montante).map(v => v / 1000);
    const interasseM = (m.interasse_montanti || 1000) / 1000;
    const interasseI = (m.interasse_infissi || 100) / 1000;
    const col = getColor(m);

    // Corrente superiore e inferiore
    const topRail = box(L, cw, cd, col); topRail.position.set(0, H, 0); group.add(topRail);
    const botRail = box(L, cw, cd, col); botRail.position.set(0, cw / 2, 0); group.add(botRail);

    // Montanti principali
    const nMont = Math.max(2, Math.ceil(L / interasseM) + 1);
    for (let i = 0; i < nMont; i++) {
        const x = -L / 2 + (i * L) / (nMont - 1);
        const p = box(mw, H, md, col);
        p.position.set(x, H / 2, 0);
        group.add(p);
    }
    // Infissi
    const nInf = Math.max(1, Math.ceil(L / interasseI));
    for (let i = 1; i < nInf; i++) {
        const x = -L / 2 + (i * L) / nInf;
        const inf = box(0.012, H - cw * 2, 0.012, col);
        inf.position.set(x, H / 2, 0);
        group.add(inf);
    }
    // Corrimano
    const cr = cylinder(0.02, L, col);
    cr.rotation.z = Math.PI / 2;
    cr.position.set(0, H + cw / 2 + 0.02, 0);
    group.add(cr);

    return group;
}

const RENDERERS = {
    inferriata_fissa: renderInferriata,
    cancello_carrabile: (m) => renderCancello(m, false),
    cancello_pedonale: (m) => renderCancello(m, true),
    scala: renderScala,
    recinzione: renderRecinzione,
    ringhiera: renderRinghiera,
};

// ══════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════

const RilievoViewer3D = forwardRef(function RilievoViewer3D({ tipologia, misure }, ref) {
    const mountRef = useRef(null);
    const stateRef = useRef({ renderer: null, scene: null, camera: null, animId: null });
    const dragRef = useRef({ active: false, prevX: 0, prevY: 0, rotX: 0.4, rotY: -0.6 });

    useImperativeHandle(ref, () => ({
        captureScreenshot: () => {
            const st = stateRef.current;
            if (!st.renderer || !st.scene || !st.camera) return null;
            st.renderer.render(st.scene, st.camera);
            return st.renderer.domElement.toDataURL('image/png');
        }
    }));

    const buildScene = useCallback(() => {
        const st = stateRef.current;
        if (!st.scene) return;
        // Clear old meshes
        while (st.scene.children.length > 0) st.scene.remove(st.scene.children[0]);

        // Lights
        st.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
        const dir = new THREE.DirectionalLight(0xffffff, 0.9);
        dir.position.set(5, 10, 7);
        st.scene.add(dir);
        const fill = new THREE.DirectionalLight(0xffffff, 0.3);
        fill.position.set(-3, 5, -5);
        st.scene.add(fill);

        // Grid floor
        const grid = new THREE.GridHelper(10, 20, 0xcccccc, 0xe8e8e8);
        grid.position.y = -0.01;
        st.scene.add(grid);

        // Build mesh
        const fn = RENDERERS[tipologia];
        if (!fn || !misure) return;
        const mesh = fn(misure);
        st.scene.add(mesh);

        // Auto-fit camera
        const bbox = new THREE.Box3().setFromObject(mesh);
        const center = bbox.getCenter(new THREE.Vector3());
        const size = bbox.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = maxDim * 2;
        st.camera.position.set(center.x + dist * 0.6, center.y + dist * 0.5, center.z + dist * 0.8);
        st.camera.lookAt(center);
        st.camera.userData.target = center.clone();
        st.camera.userData.dist = dist;
    }, [tipologia, misure]);

    useEffect(() => {
        const el = mountRef.current;
        if (!el) return;
        const w = el.clientWidth;
        const h = el.clientHeight || 400;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf8f8f8);
        const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        el.appendChild(renderer.domElement);

        const st = stateRef.current;
        st.renderer = renderer;
        st.scene = scene;
        st.camera = camera;

        // Animate
        const animate = () => {
            st.animId = requestAnimationFrame(animate);
            const drag = dragRef.current;
            const target = camera.userData.target || new THREE.Vector3();
            const dist = camera.userData.dist || 5;
            camera.position.x = target.x + dist * Math.sin(drag.rotY) * Math.cos(drag.rotX);
            camera.position.y = target.y + dist * Math.sin(drag.rotX);
            camera.position.z = target.z + dist * Math.cos(drag.rotY) * Math.cos(drag.rotX);
            camera.lookAt(target);
            renderer.render(scene, camera);
        };
        animate();

        // Resize
        const onResize = () => {
            const nw = el.clientWidth;
            const nh = el.clientHeight || 400;
            camera.aspect = nw / nh;
            camera.updateProjectionMatrix();
            renderer.setSize(nw, nh);
        };
        window.addEventListener('resize', onResize);

        return () => {
            window.removeEventListener('resize', onResize);
            cancelAnimationFrame(st.animId);
            renderer.dispose();
            if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
            st.renderer = null;
            st.scene = null;
            st.camera = null;
        };
    }, []);

    // Manual mouse/touch rotation
    useEffect(() => {
        const el = mountRef.current;
        if (!el) return;
        const drag = dragRef.current;

        const onDown = (x, y) => { drag.active = true; drag.prevX = x; drag.prevY = y; };
        const onMove = (x, y) => {
            if (!drag.active) return;
            const dx = x - drag.prevX;
            const dy = y - drag.prevY;
            drag.rotY += dx * 0.008;
            drag.rotX = Math.max(-1.2, Math.min(1.2, drag.rotX + dy * 0.008));
            drag.prevX = x;
            drag.prevY = y;
        };
        const onUp = () => { drag.active = false; };

        const mouseDown = (e) => onDown(e.clientX, e.clientY);
        const mouseMove = (e) => onMove(e.clientX, e.clientY);
        const touchStart = (e) => { if (e.touches.length === 1) { e.preventDefault(); onDown(e.touches[0].clientX, e.touches[0].clientY); } };
        const touchMove = (e) => { if (e.touches.length === 1) { e.preventDefault(); onMove(e.touches[0].clientX, e.touches[0].clientY); } };

        // Zoom with wheel
        const onWheel = (e) => {
            e.preventDefault();
            const st = stateRef.current;
            if (!st.camera) return;
            const d = st.camera.userData.dist || 5;
            st.camera.userData.dist = Math.max(1, Math.min(30, d + e.deltaY * 0.005));
        };

        el.addEventListener('mousedown', mouseDown);
        window.addEventListener('mousemove', mouseMove);
        window.addEventListener('mouseup', onUp);
        el.addEventListener('touchstart', touchStart, { passive: false });
        el.addEventListener('touchmove', touchMove, { passive: false });
        el.addEventListener('touchend', onUp);
        el.addEventListener('wheel', onWheel, { passive: false });

        return () => {
            el.removeEventListener('mousedown', mouseDown);
            window.removeEventListener('mousemove', mouseMove);
            window.removeEventListener('mouseup', onUp);
            el.removeEventListener('touchstart', touchStart);
            el.removeEventListener('touchmove', touchMove);
            el.removeEventListener('touchend', onUp);
            el.removeEventListener('wheel', onWheel);
        };
    }, []);

    // Rebuild scene when tipologia/misure change
    useEffect(() => {
        buildScene();
    }, [buildScene]);

    return (
        <div
            ref={mountRef}
            data-testid="rilievo-3d-viewer"
            className="w-full h-[400px] md:h-[500px] rounded-lg border border-slate-200 bg-[#f8f8f8] cursor-grab active:cursor-grabbing touch-manipulation"
            style={{ touchAction: 'none' }}
        />
    );
});

export default RilievoViewer3D;
