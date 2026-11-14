class ContentHandler {
    showLoading(container, message = 'Cargando contenido...') {
        container.innerHTML = window.interfaz.html`
            <div class="loading-container">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Cargando...</span>
                </div>
                <p class="mt-3 content-status-message">${message}</p>
            </div>
        `;
    }

    showError(container, message) {
        container.innerHTML = window.interfaz.html`
            <div class="alert alert-danger p-4 content-error" role="alert">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Error:</strong>
                <span>${message}</span>
            </div>
        `;
    }

    showRestricted(container) {
        container.innerHTML = window.interfaz.html`
            <div class="restricted-content">
                <div class="card border-warning">
                    <div class="card-body text-center p-5">
                        <i class="fas fa-lock fa-5x text-warning mb-4"></i>
                        <h3 class="text-warning mb-3">Contenido Restringido</h3>
                        <p class="text-muted mb-4">
                            Este recurso requiere que inicies sesión para poder visualizarlo.
                        </p>
                        <div class="alert alert-warning" role="alert">
                            <strong>Acceso denegado:</strong> Debes iniciar sesión para acceder a este contenido.
                        </div>
                        <div class="mt-4">
                            <a href="/login/" class="btn btn-primary btn-lg">
                                <i class="fas fa-sign-in-alt"></i> Iniciar Sesión
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    handleZipFile(container, zipUrl, indexUrl) {
        const iframe = document.createElement('iframe');
        iframe.src = indexUrl;
        iframe.className = 'content-iframe resource-frame';
        iframe.title = 'Contenido interactivo';

        iframe.onerror = () => {
            this.showError(container, window.interfaz.html`
                No se pudo cargar el contenido del archivo ZIP.
                <ul class="content-error-list">
                    <li>Comprueba que contenga un archivo index.html en la raíz.</li>
                    <li>Comprueba los permisos del recurso.</li>
                </ul>
                <a href="${zipUrl}" class="btn btn-outline-danger btn-sm" download>
                    <i class="fas fa-download"></i> Descargar ZIP
                </a>
            `);
        };

        container.replaceChildren(iframe);
    }

    handleZipResource(container, zipUrl, _fileName, indexUrl, isRestricted = false) {
        if (isRestricted) {
            this.showRestricted(container);
            return;
        }
        this.handleZipFile(container, zipUrl, indexUrl);
    }

    esFormacionNativa(url) {
        try {
            const destino = new URL(url, window.location.href);
            return destino.origin === window.location.origin
                && /^\/(?:[a-z]{2}\/)?laboratorio\/[^/]+\/cursos(?:\/|$)/.test(destino.pathname);
        } catch (_error) {
            return false;
        }
    }

    mostrarFalloHtml(container, url) {
        const aviso = document.createElement('section');
        aviso.className = 'alert alert-warning p-4 content-error';
        aviso.setAttribute('role', 'alert');
        const titulo = document.createElement('h3');
        titulo.textContent = gettext('No se pudo mostrar el contenido en el visor');
        const detalle = document.createElement('p');
        detalle.textContent = gettext('Reintenta la carga para consultar el contenido aquí.');
        const reintentar = document.createElement('button');
        reintentar.type = 'button';
        reintentar.className = 'btn btn-primary mr-2';
        reintentar.textContent = gettext('Reintentar');
        reintentar.addEventListener('click', () => {
            if (container.contains(aviso)) this.handleHtmlFile(container, url);
        });
        aviso.append(titulo, detalle, reintentar);
        container.replaceChildren(aviso);
    }

    handleHtmlFile(container, url) {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.className = 'content-iframe resource-frame';
        iframe.title = 'Recurso HTML';
        iframe.setAttribute('allow', 'camera; microphone; display-capture; fullscreen; autoplay; clipboard-write');
        const formacion = this.esFormacionNativa(url);
        const fallo = () => {
            if (!container.contains(iframe)) return;
            if (formacion) this.mostrarFalloHtml(container, url);
            else this.showError(container, 'Error al cargar el archivo HTML.');
        };
        // El bloqueo X-Frame-Options no dispara onerror en todos los navegadores.
        // Comprobamos sólo páginas nativas; no inspeccionamos sitios externos.
        const espera = formacion ? window.setTimeout(fallo, 20000) : null;
        iframe.addEventListener('load', () => {
            if (espera !== null) window.clearTimeout(espera);
            if (!container.contains(iframe)) return;
            if (formacion) {
                try {
                    if (!iframe.contentDocument?.documentElement) {
                        fallo();
                        return;
                    }
                } catch (_error) {
                    fallo();
                    return;
                }
            }
            this.sincronizarMenu(iframe);
        });
        iframe.onerror = () => {
            if (espera !== null) window.clearTimeout(espera);
            fallo();
        };
        container.replaceChildren(iframe);
    }

    sincronizarMenu(iframe) {
        let ruta;
        let titulo = '';
        try {
            ruta = new URL(iframe.contentWindow.location.href);
            titulo = (iframe.contentDocument.title || '').split(' · ')[0].trim();
        } catch (_error) {
            return;
        }
        const botones = [...document.querySelectorAll('.project-detail-resource-button[data-url]')]
            .map(item => {
                try { return { item, url: new URL(item.dataset.url, window.location.href) }; }
                catch (_error) { return null; }
            })
            .filter(opcion => opcion && opcion.url.origin === ruta.origin && opcion.url.pathname === ruta.pathname);
        const categoria = ruta.searchParams.get('categoria');
        const opcion = botones.find(opcion => opcion.url.search === ruta.search)
            || (categoria && botones.find(opcion => opcion.url.searchParams.get('categoria') === categoria))
            || botones.find(opcion => !opcion.url.search);
        if (opcion) {
            if (!opcion.item.classList.contains('active')) window.setActive?.(opcion.item);
            return;
        }
        if (document.querySelector('.project-detail-resource-button.active:not([data-url])')) return;
        document.querySelectorAll('.project-detail-resource-button.active').forEach(item => {
            item.classList.remove('active');
            item.removeAttribute('aria-current');
        });
        if (titulo) window.encabezarVisor?.(gettext('Archivo activo'), titulo);
    }

    handlePdfFile(container, url, fileName) {
        if (!window.visorPdfModal) {
            this.showError(container, 'El visor PDF no está disponible en este momento.');
            return;
        }
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.dataset.pdfTitulo = String(fileName || 'Documento PDF').replace(/[.]pdf$/i, '');
        enlace.dataset.pdfDescarga = url;
        const disparador = document.activeElement;
        window.visorPdfModal.abrir(enlace, () => { if (disparador?.isConnected) disparador.focus(); });
    }

    handleImageFile(container, url) {
        const img = document.createElement('img');
        img.src = url;
        img.className = 'resource-image';
        img.alt = 'Recurso del laboratorio';
        
        container.replaceChildren(img);
        
        img.onerror = () => {
            this.showError(container, 'Error al cargar la imagen.');
        };
    }

    handleVideoFile(container, url) {
        const video = document.createElement('video');
        video.src = url;
        video.controls = true;
        video.className = 'resource-video';
        video.playsInline = true;
        
        container.replaceChildren(video);
        
        video.onerror = () => {
            this.showError(container, 'Error al cargar el video.');
        };
    }

    inferFileExtension(url, fileName) {
        const normalizedName = String(fileName || '').trim().toLowerCase();
        const nameMatch = normalizedName.match(/\.([a-z0-9]+)(?:[?#].*)?$/);
        if (nameMatch) {
            return nameMatch[1];
        }

        try {
            const resourceUrl = new URL(url, window.location.href);
            if (resourceUrl.searchParams.get('preview') === 'pdf') {
                return 'pdf';
            }
            const pathMatch = resourceUrl.pathname.toLowerCase().match(/\.([a-z0-9]+)$/);
            return pathMatch ? pathMatch[1] : '';
        } catch (_error) {
            return '';
        }
    }

    replaceContent(url, fileName, isRestricted = false) {
        const contentContainer = document.getElementById('dynamic-content');
        if (!contentContainer) {
            console.error('No se encontró el contenedor de recursos.');
            return;
        }

        // Verificar restricciones
        if (isRestricted) {
            this.showRestricted(contentContainer);
            return;
        }

        const fileExtension = this.inferFileExtension(url, fileName);
        if (fileExtension === "pdf") {
            this.handlePdfFile(contentContainer, url, fileName);
            return;
        }
        this.showLoading(contentContainer);

        switch (fileExtension) {
            case 'html':
                this.handleHtmlFile(contentContainer, url);
                break;
            case 'png':
            case 'jpg':
            case 'jpeg':
            case 'gif':
            case 'webp':
                this.handleImageFile(contentContainer, url);
                break;
            case 'mp4':
            case 'avi':
            case 'mov':
            case 'mkv':
            case 'webm':
                this.handleVideoFile(contentContainer, url);
                break;
            default:
                this.showError(
                    contentContainer,
                    fileExtension
                        ? `El tipo de archivo "${fileExtension}" no es soportado.`
                        : gettext('No se pudo identificar el formato del recurso.')
                );
        }
    }
}

// Crear instancia global
window.contentHandler = new ContentHandler();

window.replaceContent = (url, fileName, isRestricted = false) => {
    window.contentHandler.replaceContent(url, fileName, isRestricted);
};

window.handleZipResource = (zipUrl, fileName, indexUrl, isRestricted = false) => {
    const contentContainer = document.getElementById('dynamic-content');
    if (!contentContainer) {
        console.error('No se encontró el contenedor de recursos.');
        return;
    }
    
    window.contentHandler.handleZipResource(contentContainer, zipUrl, fileName, indexUrl, isRestricted);
};
