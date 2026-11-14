const projectConfig = document.getElementById('hublabProjectConfig').dataset;

window.proyectoActual = {
    id: Number(projectConfig.projectId),
    nombre: projectConfig.projectName,
    slug: projectConfig.projectSlug
};

function shareProject() {
    if (navigator.share) {
        navigator.share({
            title: window.proyectoActual.nombre,
            text: 'Mira este proyecto en la Unidad Experimental',
            url: window.location.href
        }).catch(error => {
            if (error.name !== 'AbortError') {
                console.error('No se pudo compartir el proyecto:', error);
            }
        });
        return;
    }

    const text = encodeURIComponent(`Mira este proyecto: ${window.proyectoActual.nombre}`);
    const url = encodeURIComponent(window.location.href);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank', 'noopener');
}

function mostrarModalRestringido(nombreRecurso, recursoId) {
    document.getElementById('nombreRecursoRestringido').textContent = nombreRecurso;
    window.recursoRestringidoActual = { id: recursoId, nombre: nombreRecurso };
    $('#recursoRestringidoModal').modal('show');
}

function solicitarAcceso() {
    const recurso = window.recursoRestringidoActual;
    if (!recurso) {
        alert(gettext('Error: No se ha seleccionado ningún recurso'));
        return;
    }

    const subject = `Solicitud de acceso: ${recurso.nombre}`;
    const body = [
        `Unidad: ${window.proyectoActual.nombre}`,
        `Recurso: ${recurso.nombre}`,
        `Identificador: ${recurso.id}`,
        '',
        gettext('Motivo de la solicitud:')
    ].join('\n');

    $('#recursoRestringidoModal').modal('hide');
    window.location.href = `mailto:laboratorio@upec.edu.ec?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function abrirModalEquipos() {
    if (document.getElementById('equiposReservaModal')) {
        $('#equiposReservaModal').modal('show');
        return;
    }

    console.error('No se encontró el modal de equipos.');
    alert(gettext('No se pudo abrir el sistema de reservas. Recarga la página e intenta nuevamente.'));
}

function setActive(button, resourceId) {
    if (!button || button.classList.contains('is-disabled')) {
        return;
    }

    document.querySelectorAll('.project-detail-resource-button.active, .project-detail-resource-button[aria-current="true"]')
        .forEach(item => {
            item.classList.remove('active');
            item.removeAttribute('aria-current');
        });

    button.classList.add('active');
    button.setAttribute('aria-current', 'true');
    const modulo = button.closest('.modulo-carpeta-list[data-modulo]')?.dataset.modulo;
    if (modulo && window.moduloTabs?.getActiveTab() !== modulo) {
        window.moduloTabs?.setActiveTab(modulo, { reiniciarVisor: false });
    }

    // Un enlace directo o un cambio de recurso puede apuntar a un proceso que
    // vive dentro de dos niveles plegados. Se abren su sección y su familia;
    // Bootstrap cierra sus carpetas hermanas mediante data-parent.
    const paneles = [];
    let ancestro = button.parentElement;
    while (ancestro) {
        if (ancestro.classList?.contains('collapse')) paneles.unshift(ancestro);
        ancestro = ancestro.parentElement;
    }
    paneles.forEach(panel => {
        if (window.jQuery?.fn?.collapse) {
            window.jQuery(panel).collapse('show');
        } else {
            panel.classList.add('show');
        }
    });

    if (resourceId) {
        button.dataset.activeResourceId = String(resourceId);
    }

    // El nombre, sin el subtítulo del botón («Proceso técnico · 9 etapas») pegado.
    const resourceName = button.dataset.sectionTitle
        || button.dataset.nombre
        || button.querySelector('span strong')?.textContent?.trim()
        || button.querySelector('span')?.textContent?.trim()
        || 'Recurso seleccionado';
    encabezarVisor(button.dataset.sectionTitle ? gettext('Sección') : gettext('Archivo activo'), resourceName);
}

window.setActive = setActive;

function encabezarVisor(etiqueta, titulo) {
    const eyebrow = document.getElementById('viewer-eyebrow');
    if (eyebrow) eyebrow.textContent = etiqueta;
    const viewerTitle = document.getElementById('viewer-title');
    if (viewerTitle) {
        viewerTitle.textContent = titulo;
        viewerTitle.title = titulo;
    }
}

/* La portada de una pestaña: lo que el visor muestra cuando no hay ningún
   documento abierto. Antes se quedaba con el de la pestaña anterior, y el
   encabezado seguía diciendo su nombre. */
function mostrarPortadaModulo(modulo) {
    const container = document.getElementById('dynamic-content');
    const plantilla = document.querySelector(`template[data-portada-modulo="${modulo}"]`);
    if (!container || !plantilla) return false;

    container.replaceChildren(plantilla.content.cloneNode(true));
    container.dataset.view = 'portada';

    document.querySelectorAll('.project-detail-resource-button.active, .project-detail-resource-button[aria-current="true"]')
        .forEach(item => {
            item.classList.remove('active');
            item.removeAttribute('aria-current');
        });

    const tab = document.querySelector(`#modulo-tabs .nav-link[data-modulo="${modulo}"]`);
    encabezarVisor('Sección', tab?.textContent?.trim() || 'Sección');
    return true;
}

window.mostrarPortadaModulo = mostrarPortadaModulo;

function loadInitialUnitVideo() {
    const container = document.getElementById('dynamic-content');
    const initialContentUrl = projectConfig.initialContentUrl;
    if (!container || !initialContentUrl) return;

    const source = new URL(initialContentUrl, window.location.href);
    source.searchParams.set('video', projectConfig.initialVideoId || 'IJxxIxTuMb8');
    source.searchParams.set('titulo', projectConfig.initialVideoTitle || 'Laboratorios y Unidades experimentales');
    source.searchParams.set('subtitulo', projectConfig.initialVideoSubtitle || 'Universidad Politécnica Estatal del Carchi');
    source.searchParams.set(
        'descripcion',
        projectConfig.initialVideoDescription || 'Vinculando el conocimiento científico con el desarrollo productivo y social de la región'
    );

    const frame = document.createElement('iframe');
    frame.src = source.toString();
    frame.className = 'content-iframe';
    frame.title = `Video institucional de ${window.proyectoActual.nombre}`;
    frame.setAttribute('allow', 'autoplay');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    container.replaceChildren(frame);
}

window.loadInitialUnitVideo = loadInitialUnitVideo;

function loadIntegratedSection(sectionId) {
    const container = document.getElementById('dynamic-content');
    const template = document.querySelector(`template[data-seccion-integrada="${sectionId}"]`);
    if (!container || !template) return false;

    container.replaceChildren(template.content.cloneNode(true));
    container.dataset.view = 'seccion';
    return true;
}

window.loadIntegratedSection = loadIntegratedSection;

// El mapa se abre igual desde el menú, el panel de información o «La unidad»;
// si el menú tiene la entrada, queda marcada en él.
function abrirUbicacion(url) {
    replaceContent(url, 'ubicacion-unidad.html', false);
    const entrada = document.querySelector('#accordion [data-id="ubicacion-unidad"]');
    if (entrada) setActive(entrada, 'ubicacion-unidad');
}

window.abrirUbicacion = abrirUbicacion;

// Al elegir un contenido, el visualizador queda a la vista bajo la cabecera fija:
// centrado si cabe en la pantalla; si es más alto, con su encabezado arriba.
function llevarAlVisualizador() {
    const visor = document.querySelector('.unit-detail__viewer');
    if (!visor) return;
    const cabecera = document.querySelector('.home-top');
    const bajoCabecera = cabecera ? Math.max(0, cabecera.getBoundingClientRect().bottom) : 0;
    const caja = visor.getBoundingClientRect();
    const holgura = Math.max(12, (window.innerHeight - bajoCabecera - caja.height) / 2);
    const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: window.scrollY + caja.top - bajoCabecera - holgura, behavior: quieto ? 'auto' : 'smooth' });
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.reservasFunctions) {
        window.reservasFunctions.setProyectoActual(window.proyectoActual);
    }

    window.requestAnimationFrame(() => {
        if (window.moduloTabs?.abrirEnlaceDirecto()) return;
        const paginaDirecta = new URLSearchParams(window.location.search).get('abrir') || '';
        if (paginaDirecta.startsWith('/') && !paginaDirecta.startsWith('//')) return;
        const nativeInitialButton = document.querySelector(
            '.modulo-carpeta-list:not(.hublab-module-hidden) [data-id="logistica-identidad"]'
        );
        if (nativeInitialButton) {
            // Cargar la portada solo cuando ningún enlace directo pidió otro contenido.
            const initialFrame = document.querySelector('#dynamic-content iframe[data-initial-src]');
            if (initialFrame) {
                initialFrame.src = initialFrame.dataset.initialSrc;
                initialFrame.removeAttribute('data-initial-src');
            }
            setActive(nativeInitialButton, 'logistica-identidad');
            return;
        }
        const initialVideoButton = document.querySelector(
            '.modulo-carpeta-list:not(.hublab-module-hidden) [data-id="video-institucional"]'
        );
        initialVideoButton?.click();
    });

    // ?abrir=<página de la unidad>: el escáner de otra unidad trae aquí con la ficha del equipo en el visor.
    const paginaSolicitada = new URLSearchParams(window.location.search).get('abrir') || '';
    if (paginaSolicitada.startsWith('/') && !paginaSolicitada.startsWith('//')) {
        window.setTimeout(() => {
            const boton = [...document.querySelectorAll('.project-detail-resource-button[data-url]')]
                .find(item => item.dataset.url === paginaSolicitada);
            if (boton) boton.click();
            else window.replaceContent?.(paginaSolicitada, 'pagina.html', false);
            llevarAlVisualizador();
        }, 400);
    }

    const servicioSolicitado = new URLSearchParams(window.location.search).get('servicio');
    if (servicioSolicitado) {
        window.setTimeout(() => {
            abrirModalEquipos();
            window.seleccionarServicioReserva?.(servicioSolicitado);
        }, 150);
    }

    document.addEventListener('click', event => {
        const resourceButton = event.target.closest('button.project-detail-resource-button[data-id]');
        if (resourceButton) {
            setActive(resourceButton, resourceButton.dataset.id);
        }
        // Solo el clic de la persona: el video inicial también se abre con un clic, pero del script.
        if (event.isTrusted && (resourceButton || event.target.closest('.unit-map-link'))) {
            llevarAlVisualizador();
        }
    });

    const viewer = document.querySelector('.unit-detail__viewer');
    const fullscreenButton = document.getElementById('unitViewerFullscreen');

    if (viewer && fullscreenButton) {
        const fullscreenElement = () => document.fullscreenElement || document.webkitFullscreenElement;
        const updateFullscreenControl = () => {
            const isFullscreen = fullscreenElement() === viewer;
            const icon = fullscreenButton.querySelector('i');

            fullscreenButton.setAttribute('aria-pressed', String(isFullscreen));
            fullscreenButton.setAttribute(
                'aria-label',
                isFullscreen ? gettext('Salir de pantalla completa') : gettext('Ver visualizador en pantalla completa')
            );
            fullscreenButton.title = isFullscreen ? gettext('Salir de pantalla completa') : gettext('Pantalla completa');

            if (icon) {
                icon.classList.toggle('fa-expand', !isFullscreen);
                icon.classList.toggle('fa-compress', isFullscreen);
            }
        };

        fullscreenButton.addEventListener('click', async () => {
            try {
                if (fullscreenElement() === viewer) {
                    if (document.exitFullscreen) {
                        await document.exitFullscreen();
                    } else if (document.webkitExitFullscreen) {
                        document.webkitExitFullscreen();
                    }
                } else if (viewer.requestFullscreen) {
                    await viewer.requestFullscreen();
                } else if (viewer.webkitRequestFullscreen) {
                    viewer.webkitRequestFullscreen();
                }
            } catch (error) {
                console.error('No se pudo cambiar el modo de pantalla completa:', error);
            }
        });

        document.addEventListener('fullscreenchange', updateFullscreenControl);
        document.addEventListener('webkitfullscreenchange', updateFullscreenControl);
        updateFullscreenControl();
    }
});

$('#recursoRestringidoModal').on('hidden.bs.modal', () => {
    window.recursoRestringidoActual = null;
});
