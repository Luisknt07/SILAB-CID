/* Lectura de códigos de barras y QR con la cámara o en una foto: el motor común del lector de equipos de la
   gestión y del escáner de la página de la unidad. Usa el lector nativo del navegador (BarcodeDetector) y,
   donde no existe, ZXing (copia local, se carga solo cuando hace falta).

   const lectura = LecturaCodigos.crear({ video, visor, zxing: url, avisar(texto), alLeer(codigo), alCambiar(activa) });
   lectura.iniciar(); lectura.detener(); lectura.leerFoto(archivo); */
(function () {
    'use strict';
    const t = texto => (window.gettext ? window.gettext(texto) : texto);
    const formatos = ['code_128', 'code_39', 'ean_13', 'ean_8', 'itf', 'upc_a', 'qr_code'];
    let zxing = null;

    function cargarScript(url) {
        return new Promise((resolver, rechazar) => {
            const script = document.createElement('script');
            script.src = url;
            script.onload = resolver;
            script.onerror = rechazar;
            document.head.appendChild(script);
        });
    }

    async function motorZxing(url) {
        if (zxing) return zxing;
        if (!window.ZXing) await cargarScript(url);
        const Z = window.ZXing;
        const pistas = new Map();
        pistas.set(Z.DecodeHintType.TRY_HARDER, true);
        pistas.set(Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.CODE_128, Z.BarcodeFormat.CODE_39, Z.BarcodeFormat.EAN_13,
            Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.ITF, Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.QR_CODE]);
        const lector = new Z.MultiFormatReader();
        lector.setHints(pistas);
        zxing = { Z, lector };
        return zxing;
    }

    function decodificar({ Z, lector }, lienzo, binarizadores) {
        for (const Binarizador of binarizadores || [Z.HybridBinarizer, Z.GlobalHistogramBinarizer]) {
            try {
                const fuente = new Z.HTMLCanvasElementLuminanceSource(lienzo);
                return lector.decode(new Z.BinaryBitmap(new Binarizador(fuente))).getText();
            } catch (_error) {
                lector.reset();
            }
        }
        return '';
    }

    // Dibuja un recorte de la imagen girado y escalado: una etiqueta se fotografía de lado o pequeña.
    function lienzoDe(fuente, recorte, giro, escala) {
        const [sx, sy, sw, sh] = recorte;
        const ancho = Math.round(sw * escala);
        const alto = Math.round(sh * escala);
        const lienzo = document.createElement('canvas');
        lienzo.width = giro % 180 ? alto : ancho;
        lienzo.height = giro % 180 ? ancho : alto;
        const contexto = lienzo.getContext('2d', { willReadFrequently: true });
        contexto.imageSmoothingQuality = 'high';
        contexto.translate(lienzo.width / 2, lienzo.height / 2);
        contexto.rotate((giro * Math.PI) / 180);
        contexto.drawImage(fuente, sx, sy, sw, sh, -ancho / 2, -alto / 2, ancho, alto);
        return lienzo;
    }

    async function detectorNativo() {
        if (!('BarcodeDetector' in window)) return null;
        try {
            const soportados = await window.BarcodeDetector.getSupportedFormats();
            const usables = formatos.filter(formato => soportados.includes(formato));
            return usables.length ? new window.BarcodeDetector({ formats: usables }) : null;
        } catch (_error) {
            return null;
        }
    }

    function crear({ video, visor, zxing: urlZxing, avisar, alLeer, alCambiar }) {
        let flujo = null;
        let leyendo = false;

        function detener() {
            leyendo = false;
            flujo?.getTracks().forEach(pista => pista.stop());
            flujo = null;
            visor?.classList.remove('is-leyendo');
            alCambiar?.(false);
        }

        function leido(texto) {
            navigator.vibrate?.(80);
            detener();
            alLeer(texto.trim());
        }

        async function iniciar() {
            if (!navigator.mediaDevices?.getUserMedia) {
                avisar(t('Este navegador no permite usar la cámara. Lee una foto o escribe el código.'));
                return;
            }
            try {
                flujo = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false,
                });
            } catch (_error) {
                avisar(t('No se pudo abrir la cámara. Revisa el permiso del navegador, lee una foto o escribe el código.'));
                return;
            }
            video.srcObject = flujo;
            await video.play();
            leyendo = true;
            visor?.classList.add('is-leyendo');
            alCambiar?.(true);
            avisar(t('Acerca la etiqueta al recuadro…'));
            const nativo = await detectorNativo();
            const motor = nativo ? null : await motorZxing(urlZxing).catch(() => null);
            if (!nativo && !motor) {
                detener();
                avisar(t('No se pudo cargar el lector. Escribe el código.'));
                return;
            }
            let vuelta = 0;
            const ciclo = async () => {
                if (!leyendo) return;
                if (video.readyState >= 2) {
                    let texto = '';
                    if (nativo) {
                        try { texto = (await nativo.detect(video))[0]?.rawValue || ''; } catch (_error) { /* Cuadro aún no listo. */ }
                    } else {
                        // El recuadro de la mira: el centro del cuadro, en tres tamaños; cada cuarta vuelta, de lado.
                        const recorte = [video.videoWidth * 0.08, video.videoHeight * 0.18, video.videoWidth * 0.84, video.videoHeight * 0.64];
                        vuelta += 1;
                        const escala = [1, 0.75, 1.5][vuelta % 3];
                        texto = decodificar(motor, lienzoDe(video, recorte, 0, escala), [motor.Z.HybridBinarizer])
                            || (vuelta % 4 === 0 ? decodificar(motor, lienzoDe(video, recorte, 90, 1), [motor.Z.HybridBinarizer]) : '');
                    }
                    if (texto) { leido(texto); return; }
                }
                setTimeout(ciclo, 180);
            };
            ciclo();
        }

        async function leerFoto(archivo) {
            if (!archivo) return;
            detener();
            avisar(t('Leyendo la foto…'));
            let imagen = null;
            try {
                imagen = await createImageBitmap(archivo);
            } catch (_error) {
                avisar(t('No se pudo abrir la foto. Prueba con otra imagen.'));
                return;
            }
            const nativo = await detectorNativo();
            if (nativo) {
                try {
                    const codigos = await nativo.detect(imagen);
                    if (codigos.length) { leido(codigos[0].rawValue); return; }
                } catch (_error) { /* Se intenta con ZXing. */ }
            }
            try {
                const motor = await motorZxing(urlZxing);
                // Con barras finas solo algunos tamaños se leen (el pixelado las funde): se prueban varios.
                const lado = Math.max(imagen.width, imagen.height);
                const base = Math.min(1, 2400 / lado);
                const escalas = [base, base * 1.5, base * 2].filter(escala => escala * lado <= 4000);
                const recorte = [0, 0, imagen.width, imagen.height];
                for (const giro of [0, 90, 270]) {
                    for (const escala of escalas) {
                        const texto = decodificar(motor, lienzoDe(imagen, recorte, giro, escala));
                        if (texto) { leido(texto); return; }
                    }
                }
            } catch (_error) { /* Se avisa abajo. */ }
            avisar(t('No se encontró un código en la foto. Acércate a la etiqueta, con buena luz y de frente, o escribe el código.'));
        }

        window.addEventListener('pagehide', detener);
        return { iniciar, detener, leerFoto };
    }

    window.LecturaCodigos = { crear };
}());
