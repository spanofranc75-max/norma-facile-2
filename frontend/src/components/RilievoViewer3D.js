/**
 * RilievoViewer3D — Parametric 3D viewer for Rilievo measurements.
 * Professional CAD-style rendering: orthographic camera, wireframe edges,
 * 3-point lighting, RAL metal materials. All units in mm.
 */
import { useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import * as THREE from 'three';

// ── RAL color map (carpenteria più comuni) ──
const RAL_COLORS = {
    'RAL 9005': 0x0a0a0a,  'RAL 9010': 0xffffff,
    'RAL 7016': 0x383e42,  'RAL 7035': 0xcbcfcf,
    'RAL 6005': 0x114232,  'RAL 3000': 0xaa2b1d,
    'RAL 8017': 0x442f24,  'RAL 1021': 0xf6a800,
    'RAL 5010': 0x0e4c96,
};
const DEFAULT_COLOR = 0x383e42;

function getColor(m) { return RAL_COLORS[m?.colore] ?? DEFAULT_COLOR; }

function parseDim(profilo) {
    if (!profilo) return [30, 30];
    const nums = profilo.replace(/[^0-9.x]/gi, '').split('x').map(Number).filter(Boolean);
    return nums.length >= 2 ? nums : nums.length === 1 ? [nums[0], nums[0]] : [30, 30];
}

// ── Professional materials ──
function getMat(color) {
    const c = typeof color === 'string' ? (RAL_COLORS[color] ?? DEFAULT_COLOR) : color;
    return new THREE.MeshPhongMaterial({ color: c, specular: 0x333333, shininess: 60 });
}
const WIRE_MAT = new THREE.MeshBasicMaterial({ color: 0x000000, wireframe: true, transparent: true, opacity: 0.12 });

function profMesh(geo, color) {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(geo, getMat(color)));
    g.add(new THREE.Mesh(geo.clone(), WIRE_MAT));
    return g;
}

function addBox(group, w, h, d, x, y, z, color) {
    const m = profMesh(new THREE.BoxGeometry(w, h, d), color);
    m.position.set(x, y, z);
    group.add(m);
}

function addCyl(group, r, len, x, y, z, color, rot) {
    const m = profMesh(new THREE.CylinderGeometry(r, r, len, 16), color);
    m.position.set(x, y, z);
    if (rot) { m.rotation.x = rot.x || 0; m.rotation.y = rot.y || 0; m.rotation.z = rot.z || 0; }
    group.add(m);
}

// ══════════════════════════════════════════
// RENDERERS (all dimensions in mm)
// ══════════════════════════════════════════

function renderInferriata(m) {
    const group = new THREE.Group();
    const L = m.luce_larghezza || 1200;
    const H = m.luce_altezza || 1500;
    const interasse = m.interasse_montanti || 120;
    const nTraversi = m.numero_traversi || 2;
    const [mw, md] = parseDim(m.profilo_montante);
    const [tw, td] = parseDim(m.profilo_traverso);
    const col = getColor(m);

    // Telaio esterno (profilo più spesso)
    const telW = Math.max(mw * 1.5, 40);
    addBox(group, L + telW * 2, telW, telW, 0, H + telW / 2, 0, col);       // top
    addBox(group, L + telW * 2, telW, telW, 0, -telW / 2, 0, col);          // bottom
    addBox(group, telW, H + telW * 2, telW, -L / 2 - telW / 2, H / 2, 0, col); // left
    addBox(group, telW, H + telW * 2, telW, L / 2 + telW / 2, H / 2, 0, col);  // right

    // Montanti interni
    const nMont = Math.max(2, Math.floor(L / interasse) + 1);
    for (let i = 0; i < nMont; i++) {
        const x = -L / 2 + i * (L / (nMont - 1));
        addBox(group, mw, H, md, x, H / 2, 0, col);
    }
    // Traversi orizzontali
    for (let i = 1; i <= nTraversi; i++) {
        const y = (H / (nTraversi + 1)) * i;
        addBox(group, L, td, tw, 0, y, 0, col);
    }
    return group;
}

function renderCancello(m, pedonale) {
    const group = new THREE.Group();
    const L = m.luce_netta || (pedonale ? 1000 : 4000);
    const H = m.altezza || 1800;
    const [tw, td] = parseDim(m.profilo_telaio);
    const [iw, id] = parseDim(m.profilo_infisso);
    const interasse = m.interasse_infissi || 100;
    const col = getColor(m);
    const nAnte = m.numero_ante || (pedonale ? 1 : 2);
    const anteW = L / nAnte;

    for (let a = 0; a < nAnte; a++) {
        const ox = -L / 2 + a * anteW + anteW / 2;
        // Telaio anta
        addBox(group, anteW, tw, td, ox, H, 0, col);
        addBox(group, anteW, tw, td, ox, 0, 0, col);
        addBox(group, tw, H, td, ox - anteW / 2, H / 2, 0, col);
        addBox(group, tw, H, td, ox + anteW / 2, H / 2, 0, col);
        // Infissi verticali
        const nInf = Math.max(1, Math.ceil(anteW / interasse) - 1);
        for (let i = 1; i <= nInf; i++) {
            const x = ox - anteW / 2 + (i * anteW) / (nInf + 1);
            addBox(group, iw, H - tw * 2, id, x, H / 2, 0, col);
        }
    }
    // Pilastri
    if (m.pilastri_esistenti) {
        const pw = m.larghezza_pilastro || 300;
        const pH = H + 200;
        addBox(group, pw, pH, pw, -L / 2 - pw / 2 - 50, pH / 2, 0, 0x888888);
        addBox(group, pw, pH, pw, L / 2 + pw / 2 + 50, pH / 2, 0, 0x888888);
    }
    // Guida scorrevole
    if (m.tipo_apertura === 'scorrevole') {
        addBox(group, L * 1.3, 20, 60, L * 0.15, 10, 0, 0x555555);
    }
    // Motore
    if (!pedonale && m.motorizzazione) {
        addBox(group, 300, 200, 200, -L / 2 - 350, 150, 0, 0x444444);
    }
    return group;
}

function renderScala(m) {
    const group = new THREE.Group();
    const nGradini = m.numero_gradini || 10;
    const alz = m.alzata || 175;
    const ped = m.pedata || 280;
    const largh = m.larghezza || 900;
    const spG = m.spessore_gradino || 4;
    const col = getColor(m);

    // Gradini: pedata orizzontale + alzata verticale
    for (let i = 0; i < nGradini; i++) {
        const y = i * alz;
        const z = i * ped;
        addBox(group, largh, spG, ped, 0, y + alz + spG / 2, z + ped / 2, col);
        addBox(group, largh, alz - spG, spG, 0, y + alz / 2, z, col);
    }

    // Longheroni laterali (diagonale)
    const totH = nGradini * alz;
    const totD = nGradini * ped;
    const diagL = Math.sqrt(totH * totH + totD * totD);
    const angle = Math.atan2(totH, totD);
    const [sw, sh] = parseDim(m.profilo_struttura);

    for (const side of [-1, 1]) {
        const geo = new THREE.BoxGeometry(sw, sh, diagL);
        const mesh = profMesh(geo, 0x666666);
        mesh.rotation.x = -angle;
        mesh.position.set(side * (largh / 2 - sw / 2), totH / 2, totD / 2);
        group.add(mesh);
    }

    // Corrimano
    if (m.corrimano) {
        const hCorr = 900;
        const lato = m.lato_corrimano || 'dx';
        const sides = lato === 'entrambi' ? [-1, 1] : lato === 'sx' ? [-1] : [1];
        for (const s of sides) {
            const x = s * (largh / 2 + 30);
            // Montanti
            const interM = m.interasse_montanti || 150;
            const nM = Math.max(2, Math.ceil(diagL / interM));
            for (let i = 0; i <= nM; i++) {
                const frac = i / nM;
                const y = frac * totH;
                const z = frac * totD;
                addBox(group, 20, hCorr, 20, x, y + hCorr / 2, z, col);
            }
            // Rail
            const rGeo = new THREE.CylinderGeometry(20, 20, diagL, 12);
            const rail = profMesh(rGeo, col);
            rail.rotation.x = Math.PI / 2 - angle;
            rail.position.set(x, totH / 2 + hCorr, totD / 2);
            group.add(rail);
        }
    }
    return group;
}

function renderRecinzione(m) {
    const group = new THREE.Group();
    const lungTot = m.lunghezza_totale || 5000;
    const H = m.altezza || 1500;
    const interassePali = m.interasse_pali || 2500;
    const nPali = Math.max(2, Math.ceil(lungTot / interassePali) + 1);
    const actualSpacing = lungTot / (nPali - 1);
    const [pw, pd] = parseDim(m.profilo_palo);
    const nOrizz = m.numero_orizzontali || 3;
    const [ow, od] = parseDim(m.profilo_orizzontale);
    const [vw, vd] = parseDim(m.profilo_verticale);
    const interasseV = m.interasse_verticali || 120;
    const col = getColor(m);

    for (let i = 0; i < nPali; i++) {
        const x = -lungTot / 2 + i * actualSpacing;
        // Palo (+400mm interrato)
        addBox(group, pw, H + 400, pd, x, (H + 400) / 2 - 400, 0, 0x555555);
        // Pannello tra pali
        if (i < nPali - 1) {
            const cx = x + actualSpacing / 2;
            for (let j = 0; j < nOrizz; j++) {
                const y = ((j + 1) * H) / (nOrizz + 1);
                addBox(group, actualSpacing - pw, ow, od, cx, y, 0, col);
            }
            const nV = Math.max(1, Math.ceil(actualSpacing / interasseV) - 1);
            for (let j = 1; j <= nV; j++) {
                const vx = x + pw / 2 + (j * (actualSpacing - pw)) / (nV + 1);
                addBox(group, vw, H - 100, vd, vx, H / 2, 0, col);
            }
        }
    }
    // Terreno
    addBox(group, lungTot + 1000, 20, 2000, 0, -10, 0, 0x8B7355);
    return group;
}

function renderRinghiera(m) {
    const group = new THREE.Group();
    const L = m.lunghezza || 3000;
    const H = m.altezza || 900;
    const [cw, cd] = parseDim(m.profilo_corrente);
    const [mw, md] = parseDim(m.profilo_montante);
    const interasseM = m.interasse_montanti || 1000;
    const interasseI = m.interasse_infissi || 100;
    const col = getColor(m);

    // Correnti superiore e inferiore
    addBox(group, L, cw, cd, 0, H, 0, col);
    addBox(group, L, cw, cd, 0, cw / 2, 0, col);

    // Montanti principali
    const nMont = Math.max(2, Math.ceil(L / interasseM) + 1);
    for (let i = 0; i < nMont; i++) {
        const x = -L / 2 + (i * L) / (nMont - 1);
        addBox(group, mw, H, md, x, H / 2, 0, col);
    }
    // Infissi
    const nInf = Math.max(1, Math.ceil(L / interasseI));
    for (let i = 1; i < nInf; i++) {
        const x = -L / 2 + (i * L) / nInf;
        addBox(group, 12, H - cw * 2, 12, x, H / 2, 0, col);
    }
    // Corrimano
    addCyl(group, 20, L, 0, H + cw / 2 + 20, 0, col, { z: Math.PI / 2 });

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

// ── Auto-fit OrthographicCamera to object ──
function fitCamera(camera, object, aspect) {
    const bbox = new THREE.Box3().setFromObject(object);
    const center = bbox.getCenter(new THREE.Vector3());
    const size = bbox.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const pad = maxDim * 0.7;

    camera.left = -pad * aspect;
    camera.right = pad * aspect;
    camera.top = pad;
    camera.bottom = -pad;
    camera.updateProjectionMatrix();

    camera.userData.target = center.clone();
    camera.userData.baseFrustum = pad;
    camera.userData.zoom = 1;
    camera.userData.maxDim = maxDim;
}

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
        // Clear
        while (st.scene.children.length > 0) st.scene.remove(st.scene.children[0]);

        // Background grigio tecnico
        st.scene.background = new THREE.Color(0xf0f2f5);

        // Griglia di riferimento (stile CAD)
        const grid = new THREE.GridHelper(10000, 20, 0xcccccc, 0xe0e0e0);
        grid.position.y = -1;
        st.scene.add(grid);

        // Piano d'appoggio trasparente
        const planeMat = new THREE.MeshLambertMaterial({
            color: 0xfafafa, transparent: true, opacity: 0.5, side: THREE.DoubleSide
        });
        const plane = new THREE.Mesh(new THREE.PlaneGeometry(10000, 10000), planeMat);
        plane.rotation.x = -Math.PI / 2;
        plane.position.y = -2;
        st.scene.add(plane);

        // 3-point lighting professionale
        st.scene.add(new THREE.AmbientLight(0xffffff, 0.4));
        const key = new THREE.DirectionalLight(0xffffff, 0.8);
        key.position.set(5000, 8000, 5000);
        st.scene.add(key);
        const fill = new THREE.DirectionalLight(0xffffff, 0.3);
        fill.position.set(-5000, 3000, -5000);
        st.scene.add(fill);
        const rim = new THREE.DirectionalLight(0xffffff, 0.2);
        rim.position.set(0, -2000, 5000);
        st.scene.add(rim);

        // Build mesh
        const fn = RENDERERS[tipologia];
        if (!fn || !misure) return;
        const mesh = fn(misure);
        st.scene.add(mesh);

        // Auto-fit camera
        const el = mountRef.current;
        const aspect = el ? (el.clientWidth / (el.clientHeight || 400)) : 1.5;
        fitCamera(st.camera, mesh, aspect);
    }, [tipologia, misure]);

    useEffect(() => {
        const el = mountRef.current;
        if (!el) return;
        const w = el.clientWidth;
        const h = el.clientHeight || 400;
        const aspect = w / h;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f2f5);

        // OrthographicCamera (assonometria tecnica)
        const frustum = 3000;
        const camera = new THREE.OrthographicCamera(
            -frustum * aspect, frustum * aspect,
            frustum, -frustum,
            -50000, 50000
        );
        camera.position.set(2000, 2000, 2000);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        el.appendChild(renderer.domElement);

        const st = stateRef.current;
        st.renderer = renderer;
        st.scene = scene;
        st.camera = camera;

        // Animate (orbit via drag)
        const animate = () => {
            st.animId = requestAnimationFrame(animate);
            const drag = dragRef.current;
            const target = camera.userData.target || new THREE.Vector3();
            const dist = (camera.userData.maxDim || 3000) * 2;
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
            const a = nw / nh;
            const base = camera.userData.baseFrustum || 3000;
            const z = camera.userData.zoom || 1;
            camera.left = -base * a / z;
            camera.right = base * a / z;
            camera.top = base / z;
            camera.bottom = -base / z;
            camera.updateProjectionMatrix();
            renderer.setSize(nw, nh);
        };
        window.addEventListener('resize', onResize);

        return () => {
            window.removeEventListener('resize', onResize);
            cancelAnimationFrame(st.animId);
            renderer.dispose();
            if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
            st.renderer = null; st.scene = null; st.camera = null;
        };
    }, []);

    // Manual mouse/touch rotation + zoom
    useEffect(() => {
        const el = mountRef.current;
        if (!el) return;
        const drag = dragRef.current;

        const onDown = (x, y) => { drag.active = true; drag.prevX = x; drag.prevY = y; };
        const onMove = (x, y) => {
            if (!drag.active) return;
            drag.rotY += (x - drag.prevX) * 0.008;
            drag.rotX = Math.max(-1.2, Math.min(1.2, drag.rotX + (y - drag.prevY) * 0.008));
            drag.prevX = x; drag.prevY = y;
        };
        const onUp = () => { drag.active = false; };

        const mouseDown = (e) => onDown(e.clientX, e.clientY);
        const mouseMove = (e) => onMove(e.clientX, e.clientY);
        const touchStart = (e) => { if (e.touches.length === 1) { e.preventDefault(); onDown(e.touches[0].clientX, e.touches[0].clientY); } };
        const touchMove = (e) => { if (e.touches.length === 1) { e.preventDefault(); onMove(e.touches[0].clientX, e.touches[0].clientY); } };

        // Zoom: change orthographic frustum
        const onWheel = (e) => {
            e.preventDefault();
            const cam = stateRef.current.camera;
            if (!cam) return;
            const z = (cam.userData.zoom || 1) * (e.deltaY > 0 ? 0.9 : 1.1);
            cam.userData.zoom = Math.max(0.2, Math.min(5, z));
            const base = cam.userData.baseFrustum || 3000;
            const a = el.clientWidth / (el.clientHeight || 400);
            cam.left = -base * a / cam.userData.zoom;
            cam.right = base * a / cam.userData.zoom;
            cam.top = base / cam.userData.zoom;
            cam.bottom = -base / cam.userData.zoom;
            cam.updateProjectionMatrix();
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

    useEffect(() => { buildScene(); }, [buildScene]);

    return (
        <div
            ref={mountRef}
            data-testid="rilievo-3d-viewer"
            className="w-full h-[400px] md:h-[500px] rounded-lg border border-slate-300 bg-[#f0f2f5] cursor-grab active:cursor-grabbing touch-manipulation"
            style={{ touchAction: 'none' }}
        />
    );
});

export default RilievoViewer3D;
