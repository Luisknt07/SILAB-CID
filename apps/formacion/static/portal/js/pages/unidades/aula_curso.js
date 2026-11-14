(() => {
    'use strict';
    // Marca la lección como vista cuando la persona cumple con el recurso: un video terminado (o visto en un 90 %),
    // una lectura recorrida hasta el final o un material abierto. Avisa al servidor sin recargar la página y pone al
    // día la barra de avance, el programa y el botón. El botón «Completar» sigue disponible por si algo falla.
    const leccion = document.querySelector('[data-leccion-auto]');
    if (!leccion) return;
    const formulario = leccion.querySelector('[data-completar]');
    if (!formulario) return;
    const token = formulario.querySelector('[name="csrfmiddlewaretoken"]').value;
    const PROPORCION_VISTA = 0.9;
    let enviado = false;
    let intentos = 0;
    const INTENTOS_MAXIMOS = 3;

    function pintarAvance(datos) {
        document.querySelectorAll('[data-avance]').forEach(barra => {
            barra.setAttribute('aria-valuenow', datos.porcentaje);
            const relleno = barra.querySelector('[data-avance-relleno]');
            const cifra = barra.querySelector('[data-avance-cifra]');
            const detalle = barra.querySelector('[data-avance-detalle]');
            if (relleno) relleno.style.width = `${datos.porcentaje}%`;
            if (cifra) cifra.textContent = `${datos.porcentaje} %`;
            if (detalle) detalle.textContent = `${datos.completadas} de ${datos.total} lecciones obligatorias`;
        });
        const enlace = document.querySelector(`[data-programa-leccion="${leccion.dataset.leccionAuto}"] i`);
        if (enlace) enlace.className = 'fas fa-check-circle is-hecha';
        const unidad = document.querySelector(`[data-programa-unidad="${datos.modulo.id}"]`);
        if (unidad) {
            const cuenta = unidad.querySelector('[data-unidad-hechas]');
            if (cuenta) cuenta.textContent = `${datos.modulo.hechas} de ${datos.modulo.total} completadas`;
            const barra = unidad.querySelector('[data-unidad-relleno]');
            if (barra) barra.style.width = `${datos.modulo.total ? Math.round(100 * datos.modulo.hechas / datos.modulo.total) : 0}%`;
            if (datos.modulo.completo) unidad.classList.add('is-completa');
        }
        const insignia = document.createElement('span');
        insignia.className = 'aula-curso__hecha';
        insignia.innerHTML = '<i class="fas fa-check-circle" aria-hidden="true"></i> Visto';
        formulario.replaceWith(insignia);
        if (datos.certificado) window.location.reload();
    }

    async function marcarVista() {
        if (enviado || intentos >= INTENTOS_MAXIMOS) return;
        enviado = true;
        intentos += 1;
        const cuerpo = new FormData();
        cuerpo.append('csrfmiddlewaretoken', token);
        try {
            const respuesta = await fetch(formulario.action, {
                method: 'POST', body: cuerpo, credentials: 'same-origin',
                headers: {'X-CSRFToken': token, 'X-Requested-With': 'fetch'},
            });
            // Si el servidor no acepta (sesión vencida, sin acceso), no se insiste: queda el botón «Completar».
            if (!respuesta.ok) return;
            const datos = await respuesta.json();
            if (datos.ok) pintarAvance(datos);
        } catch (_) {
            // Un fallo de red se reintenta con una pausa creciente, hasta tres veces.
            setTimeout(() => { enviado = false; }, 5000 * intentos);
        }
    }

    // Video de YouTube: el reproductor incrustado informa su avance por mensajes (sin cargar scripts externos).
    const marco = leccion.querySelector('iframe[data-youtube]');
    if (marco) {
        const escuchar = () => marco.contentWindow.postMessage(JSON.stringify({event: 'listening', id: 1}), '*');
        marco.addEventListener('load', escuchar);
        const intervalo = setInterval(escuchar, 3000);
        window.addEventListener('message', evento => {
            if (evento.source !== marco.contentWindow || typeof evento.data !== 'string') return;
            let datos;
            try {
                datos = JSON.parse(evento.data);
            } catch (_) {
                return;
            }
            const info = datos.info || {};
            const terminado = info.playerState === 0;
            const casi = info.duration > 0 && info.currentTime / info.duration >= PROPORCION_VISTA;
            if (datos.event === 'infoDelivery' || datos.event === 'onStateChange') clearInterval(intervalo);
            if (terminado || casi || datos.info === 0) marcarVista();
        });
    }

    // Video subido como archivo.
    const reproductor = leccion.querySelector('video');
    if (reproductor) {
        reproductor.addEventListener('ended', marcarVista);
        reproductor.addEventListener('timeupdate', () => {
            if (reproductor.duration && reproductor.currentTime / reproductor.duration >= PROPORCION_VISTA) marcarVista();
        });
    }

    // Material: se cumple al abrirlo.
    leccion.querySelectorAll('[data-abre-material]').forEach(enlace => enlace.addEventListener('click', marcarVista));

    // Lectura: se cumple al llegar al final del texto, después de un tiempo mínimo de lectura.
    const final = leccion.querySelector('[data-final-lectura]');
    if (final && 'IntersectionObserver' in window) {
        const minimo = Math.min(Number(leccion.dataset.minutos || 5) * 60 * 250, 45000);
        const desde = Date.now();
        let alFinal = false;
        const revisar = () => {
            if (alFinal && Date.now() - desde >= minimo) marcarVista();
        };
        new IntersectionObserver(entradas => {
            alFinal = entradas.some(entrada => entrada.isIntersecting);
            revisar();
        }).observe(final);
        setInterval(revisar, 2000);
    }
})();
