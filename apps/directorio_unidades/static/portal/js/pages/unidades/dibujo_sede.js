/* Dibujo a mano del contorno y los edificios de una sede, sobre el mapa del
   editor de sedes. Cada figura se marca esquina por esquina; al tocarla se
   renombra, se ajusta arrastrando sus vértices o se elimina. Lo dibujado viaja
   en los campos ocultos «contorno» y «edificios» del formulario. */
(function () {
    'use strict';

    const traducir = mensaje => (typeof window.gettext === 'function' ? window.gettext(mensaje) : mensaje);
    const vertice = punto => [Number(punto.lat.toFixed(7)), Number(punto.lng.toFixed(7))];

    function leer(campo) {
        try {
            const valor = JSON.parse(campo.value || '[]');
            return Array.isArray(valor) ? valor : [];
        } catch (_error) {
            return [];
        }
    }

    function boton(texto, alPulsar, principal) {
        const elemento = L.DomUtil.create('button', principal ? 'mapa-dibujo__boton is-principal' : 'mapa-dibujo__boton');
        elemento.type = 'button';
        elemento.textContent = texto;
        L.DomEvent.on(elemento, 'click', evento => {
            L.DomEvent.stop(evento);
            alPulsar();
        });
        return elemento;
    }

    // Enter dentro del formulario del editor lo enviaría: aquí confirma la acción del mapa.
    function campoDeTexto(valor, alConfirmar) {
        const entrada = L.DomUtil.create('input', 'mapa-dibujo__nombre');
        entrada.type = 'text';
        entrada.value = valor;
        entrada.maxLength = 120;
        entrada.setAttribute('aria-label', traducir('Nombre del edificio'));
        L.DomEvent.on(entrada, 'keydown', evento => {
            if (evento.key !== 'Enter') return;
            evento.preventDefault();
            alConfirmar();
        });
        return entrada;
    }

    function activar(elemento, { mapa, puntoMarcado, pausarPunto }) {
        const formulario = elemento.closest('form');
        const campoContorno = formulario?.querySelector('[name="contorno"]');
        const campoEdificios = formulario?.querySelector('[name="edificios"]');
        if (!campoContorno || !campoEdificios) return;
        const estado = { contorno: leer(campoContorno), edificios: leer(campoEdificios) };
        const figuras = L.featureGroup().addTo(mapa);
        let trazo = null;
        let ajuste = null;

        const Barra = L.Control.extend({
            onAdd() {
                const caja = L.DomUtil.create('div', 'mapa-dibujo');
                L.DomEvent.disableClickPropagation(caja);
                return caja;
            },
        });
        // Abajo, para dejar libre la zona donde se marcan las esquinas.
        const barra = new Barra({ position: 'bottomleft' }).addTo(mapa);

        const guardar = () => {
            campoContorno.value = JSON.stringify(estado.contorno);
            campoEdificios.value = JSON.stringify(estado.edificios);
            dibujar();
        };

        function dibujar() {
            figuras.clearLayers();
            const agregar = (vertices, tipo, indice) => {
                const poligono = L.polygon(vertices, {
                    className: `mapa-unidad__area mapa-unidad__area--${tipo}`, bubblingMouseEvents: false,
                });
                if (tipo === 'edificio') {
                    poligono.bindTooltip(estado.edificios[indice].nombre, {
                        permanent: true, direction: 'center', className: 'mapa-unidad__edificio',
                    });
                }
                // Mientras se traza, tocar una figura también marca una esquina.
                poligono.on('click', evento => (trazo ? agregarVertice(evento) : menu(poligono, tipo, indice, evento.latlng)));
                figuras.addLayer(poligono);
                return poligono;
            };
            if (estado.contorno.length) agregar(estado.contorno, 'campus');
            estado.edificios.forEach((edificio, indice) => agregar(edificio.contorno, 'edificio', indice));
        }

        function pintarBarra() {
            const caja = barra.getContainer();
            caja.replaceChildren();
            const aviso = texto => {
                const nota = L.DomUtil.create('span', 'mapa-dibujo__aviso', caja);
                nota.textContent = texto;
            };
            if (trazo) {
                aviso(trazo.tipo === 'edificio'
                    ? traducir('Toque las esquinas del edificio en orden.')
                    : traducir('Toque los vértices del contorno en orden.'));
                if (trazo.tipo === 'edificio') caja.append(trazo.nombre);
                const terminar = boton(traducir('Terminar'), terminarTrazo, true);
                terminar.disabled = trazo.vertices.length < 3;
                caja.append(terminar);
                if (trazo.vertices.length) caja.append(boton(traducir('Deshacer esquina'), deshacer));
                caja.append(boton(traducir('Cancelar'), limpiarTrazo));
            } else if (ajuste) {
                aviso(traducir('Arrastre los vértices hasta su lugar.'));
                caja.append(boton(traducir('Listo'), terminarAjuste, true));
            } else {
                caja.append(boton(`+ ${traducir('Dibujar edificio')}`, () => empezar('edificio')));
                caja.append(boton(`+ ${estado.contorno.length ? traducir('Redibujar contorno') : traducir('Dibujar contorno')}`,
                    () => empezar('contorno')));
            }
        }

        function empezar(tipo) {
            mapa.closePopup();
            trazo = {
                tipo,
                vertices: [],
                figura: L.polygon([], { className: `mapa-unidad__area mapa-unidad__area--${tipo} is-trazo`, interactive: false }).addTo(mapa),
                esquinas: L.layerGroup().addTo(mapa),
                nombre: tipo === 'edificio'
                    ? campoDeTexto(`${traducir('Edificio')} ${estado.edificios.length + 1}`, () => terminarTrazo())
                    : null,
            };
            pausarPunto(true);
            elemento.classList.add('is-dibujando');
            mapa.on('click', agregarVertice);
            pintarBarra();
        }

        function agregarVertice(evento) {
            trazo.vertices.push(evento.latlng);
            trazo.figura.setLatLngs(trazo.vertices);
            L.circleMarker(evento.latlng, { radius: 4, className: 'mapa-dibujo__esquina', interactive: false }).addTo(trazo.esquinas);
            pintarBarra();
        }

        function deshacer() {
            trazo.vertices.pop();
            trazo.figura.setLatLngs(trazo.vertices);
            const esquinas = trazo.esquinas.getLayers();
            trazo.esquinas.removeLayer(esquinas[esquinas.length - 1]);
            pintarBarra();
        }

        function terminarTrazo() {
            if (!trazo || trazo.vertices.length < 3) return;
            const vertices = trazo.vertices.map(vertice);
            if (trazo.tipo === 'edificio') {
                const nombre = trazo.nombre.value.trim() || `${traducir('Edificio')} ${estado.edificios.length + 1}`;
                estado.edificios.push({ nombre, contorno: vertices });
            } else {
                estado.contorno = vertices;
            }
            limpiarTrazo();
            guardar();
        }

        function limpiarTrazo() {
            mapa.removeLayer(trazo.figura).removeLayer(trazo.esquinas);
            mapa.off('click', agregarVertice);
            elemento.classList.remove('is-dibujando');
            pausarPunto(false);
            trazo = null;
            pintarBarra();
        }

        function menu(poligono, tipo, indice, lugar) {
            if (ajuste) return;
            const caja = document.createElement('div');
            caja.className = 'mapa-dibujo__menu';
            const cerrar = () => mapa.closePopup();
            if (tipo === 'edificio') {
                const renombrar = () => {
                    estado.edificios[indice].nombre = entrada.value.trim() || estado.edificios[indice].nombre;
                    cerrar();
                    guardar();
                };
                const entrada = campoDeTexto(estado.edificios[indice].nombre, renombrar);
                caja.append(entrada, boton(traducir('Guardar nombre'), renombrar, true));
            } else {
                const titulo = document.createElement('strong');
                titulo.textContent = traducir('Contorno del predio');
                caja.append(titulo);
            }
            caja.append(boton(traducir('Ajustar vértices'), () => {
                cerrar();
                empezarAjuste(poligono, tipo === 'edificio' ? estado.edificios[indice].contorno : estado.contorno);
            }));
            caja.append(boton(traducir('Eliminar'), () => {
                const pregunta = tipo === 'edificio' ? traducir('¿Eliminar este edificio?') : traducir('¿Eliminar el contorno?');
                if (!window.confirm(pregunta)) return;
                if (tipo === 'edificio') estado.edificios.splice(indice, 1);
                else estado.contorno = [];
                cerrar();
                guardar();
            }));
            L.popup({ maxWidth: 260 }).setLatLng(lugar).setContent(caja).openOn(mapa);
        }

        function empezarAjuste(poligono, vertices) {
            pausarPunto(true);
            const asas = vertices.map((esquina, posicion) => L.marker(esquina, {
                draggable: true,
                icon: L.divIcon({ className: 'mapa-dibujo__asa', iconSize: [12, 12] }),
            }).on('drag', evento => {
                vertices[posicion] = vertice(evento.target.getLatLng());
                poligono.setLatLngs(vertices);
            }).addTo(mapa));
            ajuste = { asas };
            pintarBarra();
        }

        function terminarAjuste() {
            ajuste.asas.forEach(asa => mapa.removeLayer(asa));
            ajuste = null;
            pausarPunto(false);
            guardar();
            pintarBarra();
        }

        dibujar();
        pintarBarra();
        // Una sede sin punto pero con dibujo se abre sobre lo dibujado.
        if (!puntoMarcado && figuras.getLayers().length) mapa.fitBounds(figuras.getBounds(), { padding: [24, 24], maxZoom: 18 });
    }

    document.addEventListener('mapa-unidad:editor', evento => {
        if (evento.target.dataset.dibujo !== undefined) activar(evento.target, evento.detail);
    });
}());
