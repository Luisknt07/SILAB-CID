/* Mapa de ubicación de la unidad: el punto exacto con su dirección y las sedes
   de la institución resaltadas, cada una con el contorno y los edificios que
   se dibujaron en su editor. Las unidades que comparten punto quedan en un
   solo marcador con su lista por piso; cada una se reconoce por su foto. Lo
   usan la pestaña «Ubicación» de la ficha y los editores de la unidad y de
   las sedes, donde el punto se marca con un clic o arrastrando el marcador. */
(function () {
    'use strict';

    const ZOOM_PUNTO = 18;
    const ZOOM_SEDE = 17;
    const ZOOM_NOMBRES = 18;
    const DECIMALES = 6;
    // Igual que MISMO_PUNTO_METROS en el servidor: más cerca, es el mismo edificio.
    const MISMO_PUNTO_METROS = 20;
    const traducir = mensaje => (typeof window.gettext === 'function' ? window.gettext(mensaje) : mensaje);

    function crearMapa(elemento, opciones) {
        const mapa = L.map(elemento, opciones);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            // Los servidores de OpenStreetMap exigen saber desde qué sitio se piden las teselas.
            referrerPolicy: 'strict-origin-when-cross-origin',
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
        }).addTo(mapa);
        return mapa;
    }

    function foto(imagen, clase) {
        const marco = document.createElement('span');
        marco.className = clase;
        if (imagen) {
            const img = document.createElement('img');
            img.src = imagen;
            img.alt = '';
            marco.append(img);
        }
        return marco;
    }

    // Con foto, la unidad se reconoce en el círculo; sin ella queda la gota. El número dice cuántas comparten el punto.
    function pin(imagen, cantidad) {
        if (!imagen && !(cantidad > 1)) {
            return L.divIcon({
                className: 'mapa-unidad__pin',
                html: '<span></span>',
                // El cuadrado de 28 px girado 45° deja su punta a 14 + 14·√2 ≈ 34 px del borde superior.
                iconSize: [28, 34],
                iconAnchor: [14, 34],
                popupAnchor: [0, -32],
            });
        }
        const caja = document.createElement('div');
        caja.append(foto(imagen, 'mapa-unidad__foto'));
        if (cantidad > 1) {
            const cuenta = document.createElement('b');
            cuenta.className = 'mapa-unidad__cuenta';
            cuenta.textContent = String(cantidad);
            caja.append(cuenta);
        }
        return L.divIcon({ className: 'mapa-unidad__pin-foto', html: caja, iconSize: [44, 54], iconAnchor: [22, 54], popupAnchor: [0, -50] });
    }

    // Textos armados con nodos: nunca se interpreta como HTML lo que escribió el editor.
    function etiqueta(datos) {
        const bloque = document.createElement('div');
        bloque.className = 'mapa-unidad__etiqueta';
        const nombre = document.createElement('strong');
        nombre.textContent = datos.nombre;
        if (datos.imagen) {
            const cabecera = document.createElement('div');
            cabecera.className = 'mapa-unidad__cabecera';
            cabecera.append(foto(datos.imagen, 'mapa-unidad__avatar'), nombre);
            bloque.append(cabecera);
        } else {
            bloque.append(nombre);
        }
        [datos.espacio, datos.direccion].filter(Boolean).forEach(texto => {
            const linea = document.createElement('span');
            linea.textContent = texto;
            bloque.append(linea);
        });
        if (datos.comoLlegar) {
            const enlace = document.createElement('a');
            enlace.href = datos.comoLlegar;
            enlace.target = '_blank';
            enlace.rel = 'noopener';
            enlace.textContent = traducir('Cómo llegar') + ' ↗';
            bloque.append(enlace);
        }
        return bloque;
    }

    // Las unidades de un mismo punto, de la planta baja hacia arriba, cada una con su foto y su ficha.
    function listaDelPunto(datos) {
        const bloque = document.createElement('div');
        bloque.className = 'mapa-unidad__etiqueta mapa-unidad__punto';
        const titulo = document.createElement('strong');
        titulo.textContent = `${datos.enElMismoPunto.length} ${traducir('unidades en este punto')}`;
        bloque.append(titulo);
        const actual = datos.enElMismoPunto.find(unidad => unidad.actual);
        [actual?.edificio, datos.direccion].filter(Boolean).forEach(texto => {
            const linea = document.createElement('span');
            linea.textContent = texto;
            bloque.append(linea);
        });
        const lista = document.createElement('ul');
        let piso = null;
        datos.enElMismoPunto.forEach(unidad => {
            if (unidad.piso !== piso) {
                piso = unidad.piso;
                const nivel = document.createElement('li');
                nivel.className = 'mapa-unidad__nivel';
                nivel.textContent = piso || traducir('Piso sin registrar');
                lista.append(nivel);
            }
            const fila = document.createElement('li');
            const enlace = document.createElement(unidad.actual ? 'span' : 'a');
            enlace.className = unidad.actual ? 'mapa-unidad__unidad is-actual' : 'mapa-unidad__unidad';
            if (!unidad.actual) {
                enlace.href = unidad.url;
                enlace.target = '_top';
            }
            const nombre = document.createElement('b');
            nombre.textContent = unidad.nombre;
            const nota = document.createElement('small');
            nota.textContent = unidad.actual ? traducir('Esta unidad') : `${traducir('Ver su ficha')} →`;
            const texto = document.createElement('span');
            texto.append(nombre, nota);
            enlace.append(foto(unidad.imagen, 'mapa-unidad__avatar'), texto);
            fila.append(enlace);
            lista.append(fila);
        });
        bloque.append(lista);
        if (datos.comoLlegar) {
            const enlace = document.createElement('a');
            enlace.href = datos.comoLlegar;
            enlace.target = '_blank';
            enlace.rel = 'noopener';
            enlace.textContent = traducir('Cómo llegar') + ' ↗';
            bloque.append(enlace);
        }
        return bloque;
    }

    // Agrupa las unidades que están a menos de MISMO_PUNTO_METROS, tomando el punto de la primera.
    function agruparPorPunto(mapa, unidades) {
        const grupos = [];
        unidades.forEach(unidad => {
            const grupo = grupos.find(otro => mapa.distance(otro.punto, unidad.punto) <= MISMO_PUNTO_METROS);
            if (grupo) grupo.unidades.push(unidad);
            else grupos.push({ punto: unidad.punto, unidades: [unidad] });
        });
        return grupos;
    }

    function limitesDe(sedes) {
        const limites = L.latLngBounds([]);
        sedes.forEach(sede => {
            if (sede.punto) limites.extend(sede.punto);
            sede.contorno.forEach(vertice => limites.extend(vertice));
            sede.edificios.forEach(edificio => edificio.contorno.forEach(vertice => limites.extend(vertice)));
        });
        return limites;
    }

    // Contorno y edificios de cada sede; de cerca los edificios llevan su nombre fijo y de lejos al pasar el cursor.
    function dibujarGeometria(mapa, sedes, alTocar) {
        const capa = L.featureGroup().addTo(mapa);
        sedes.forEach(sede => {
            const figuras = sede.edificios.map(edificio => ({ tipo: 'edificio', nombre: edificio.nombre, vertices: edificio.contorno }));
            if (sede.contorno.length) figuras.unshift({ tipo: 'campus', nombre: '', vertices: sede.contorno });
            figuras.forEach(figura => {
                const poligono = L.polygon(figura.vertices, { className: `mapa-unidad__area mapa-unidad__area--${figura.tipo}` });
                poligono.figura = figura;
                if (alTocar) poligono.on('click', () => alTocar(figura, sede));
                capa.addLayer(poligono);
            });
        });
        const rotular = () => {
            const cerca = mapa.getZoom() >= ZOOM_NOMBRES;
            capa.eachLayer(poligono => {
                const { tipo, nombre } = poligono.figura;
                if (tipo !== 'edificio') return;
                poligono.unbindTooltip().bindTooltip(nombre, cerca
                    ? { permanent: true, direction: 'center', className: 'mapa-unidad__edificio' }
                    : { direction: 'top', sticky: true });
            });
        };
        mapa.on('zoomend', rotular);
        rotular();
    }

    function distintivoDeSede(sede) {
        const rotulo = document.createElement('b');
        rotulo.textContent = sede.nombre;
        if (sede.localidad) {
            const lugar = document.createElement('small');
            lugar.textContent = sede.localidad;
            rotulo.append(lugar);
        }
        const caja = document.createElement('div');
        caja.append(document.createElement('i'), rotulo);
        return L.divIcon({ className: 'mapa-unidad__sede', html: caja, iconSize: [0, 0], iconAnchor: [0, 0] });
    }

    // Un distintivo por sede ubicada. En la ficha abre su dirección; en el editor el clic pasa al mapa.
    function dibujarSedes(mapa, sedes, alTocar) {
        const marcas = L.featureGroup().addTo(mapa);
        sedes.filter(sede => sede.punto).forEach(sede => {
            const marca = L.marker(sede.punto, {
                icon: distintivoDeSede(sede), interactive: Boolean(alTocar), keyboard: Boolean(alTocar), title: sede.nombre,
            });
            marca.sede = sede;
            if (alTocar) marca.on('click', () => alTocar(marca));
            marcas.addLayer(marca);
        });
        // Cerca de una sede con edificios su distintivo cede el lugar a los nombres de esos
        // edificios; de lejos, el que se encima con otro se reduce a su punto, en el orden de las sedes.
        const separar = () => {
            const cerca = mapa.getZoom() >= ZOOM_NOMBRES;
            const libres = [];
            marcas.eachLayer(marca => {
                const elemento = marca.getElement();
                if (!elemento) return;
                elemento.classList.remove('is-compacta');
                elemento.classList.toggle('is-oculta', cerca && marca.sede.edificios.length > 0);
            });
            marcas.eachLayer(marca => {
                const elemento = marca.getElement();
                if (!elemento || elemento.classList.contains('is-oculta')) return;
                const caja = elemento.querySelector('b').getBoundingClientRect();
                const choca = libres.some(otra => caja.left < otra.right && caja.right > otra.left
                    && caja.top < otra.bottom && caja.bottom > otra.top);
                if (choca) elemento.classList.add('is-compacta');
                else libres.push(caja);
            });
        };
        mapa.on('zoomend', separar);
        return separar;
    }

    function irA(mapa, sede) {
        if (sede.punto) mapa.setView(sede.punto, ZOOM_SEDE);
        else mapa.fitBounds(limitesDe([sede]), { padding: [30, 30], maxZoom: ZOOM_SEDE });
    }

    // Todas las sedes por separado; la que aún no tiene punto ni dibujo figura sin poder elegirse.
    function controlDeSedes(mapa, sedes, verTodas) {
        if (!sedes.length) return;
        const Control = L.Control.extend({
            onAdd() {
                const caja = L.DomUtil.create('div', 'mapa-unidad__ir');
                const lista = L.DomUtil.create('select', '', caja);
                lista.setAttribute('aria-label', traducir('Ir a una sede'));
                lista.add(new Option(traducir('Ir a una sede…'), ''));
                sedes.forEach((sede, indice) => {
                    const ubicada = limitesDe([sede]).isValid();
                    const nombre = sede.localidad ? `${sede.nombre} · ${sede.localidad}` : sede.nombre;
                    const opcion = new Option(ubicada ? nombre : `${nombre} (${traducir('por ubicar')})`, String(indice));
                    opcion.disabled = !ubicada;
                    lista.add(opcion);
                });
                lista.add(new Option(traducir('Todas las sedes'), 'todas'));
                L.DomEvent.disableClickPropagation(caja);
                L.DomEvent.on(lista, 'change', () => {
                    if (lista.value === 'todas') verTodas();
                    else if (lista.value) irA(mapa, sedes[Number(lista.value)]);
                    lista.value = '';
                });
                return caja;
            },
        });
        new Control({ position: 'topright' }).addTo(mapa);
    }

    function encuadrarSedes(mapa, sedes, relleno) {
        const limites = limitesDe(sedes);
        if (limites.isValid()) mapa.fitBounds(limites, { padding: [relleno, relleno], maxZoom: ZOOM_SEDE });
        else mapa.fitWorld();
    }

    function montarFicha(elemento, datos) {
        const mapa = crearMapa(elemento, { zoomControl: true });
        const verTodas = () => encuadrarSedes(mapa, datos.sedes, 40);
        dibujarGeometria(mapa, datos.sedes);
        // Reducido a su punto, el distintivo acerca su sede; entero, abre su dirección.
        const separar = dibujarSedes(mapa, datos.sedes, marca => {
            if (marca.getElement()?.classList.contains('is-compacta')) {
                mapa.setView(marca.sede.punto, ZOOM_SEDE);
                return;
            }
            const { nombre, localidad, direccion, comoLlegar } = marca.sede;
            L.popup({ offset: [0, -44], maxWidth: 300 }).setLatLng(marca.sede.punto)
                .setContent(etiqueta({ nombre, espacio: localidad, direccion, comoLlegar })).openOn(mapa);
        });
        if (datos.punto) {
            mapa.setView(datos.punto, ZOOM_PUNTO);
            // Varias unidades en el mismo punto comparten un marcador y su lista por piso.
            const compartido = datos.enElMismoPunto.length > 1;
            const marcador = L.marker(datos.punto, {
                icon: pin(datos.imagen, datos.enElMismoPunto.length), title: datos.nombre, zIndexOffset: 1000,
            }).addTo(mapa);
            marcador.bindPopup(compartido ? listaDelPunto(datos) : etiqueta(datos), {
                autoClose: false, closeOnClick: false, maxWidth: 320,
            }).openPopup();
            document.querySelector('[data-mapa-ver="unidad"]')?.addEventListener('click', () => {
                mapa.setView(datos.punto, ZOOM_PUNTO);
                marcador.openPopup();
            });
        } else {
            verTodas();
        }
        separar();
        controlDeSedes(mapa, datos.sedes, verTodas);
    }

    function montarEditor(elemento) {
        const contenedor = elemento.closest('.mapa-unidad-editor');
        const formulario = elemento.closest('form');
        const campo = nombre => formulario?.querySelector(`[name="${nombre}"]`);
        const latitud = campo('latitud');
        const longitud = campo('longitud');
        // Quien solo puede consultar ve los campos como texto: no hay punto que mover.
        if (!latitud || !longitud) {
            contenedor.hidden = true;
            return;
        }
        const espacio = campo('ubicacion');
        const direccion = campo('direccion');
        const sedes = JSON.parse(elemento.dataset.sedes || '[]');
        const otras = JSON.parse(elemento.dataset.unidades || '[]');
        const mapa = crearMapa(elemento, { scrollWheelZoom: false });
        let marcarPunto = true;
        let marcador = null;

        const leerPunto = () => {
            const lat = Number.parseFloat(latitud.value.replace(',', '.'));
            const lng = Number.parseFloat(longitud.value.replace(',', '.'));
            return Number.isFinite(lat) && Number.isFinite(lng) ? L.latLng(lat, lng) : null;
        };
        const vistaPrevia = () => etiqueta({
            nombre: campo('nombre')?.value.trim() || elemento.dataset.nombre || traducir('La unidad'),
            espacio: (espacio || campo('localidad'))?.value.trim(),
            direccion: direccion?.value.trim(),
        });
        const colocar = punto => {
            if (marcador) {
                marcador.setLatLng(punto).setPopupContent(vistaPrevia());
                return;
            }
            marcador = L.marker(punto, { icon: pin(elemento.dataset.imagen), draggable: true, autoPan: true, zIndexOffset: 1000 }).addTo(mapa);
            marcador.bindPopup(vistaPrevia(), { autoClose: false, closeOnClick: false, maxWidth: 300 });
            marcador.on('dragend', () => escribir(marcador.getLatLng()));
        };
        const escribir = punto => {
            latitud.value = punto.lat.toFixed(DECIMALES);
            longitud.value = punto.lng.toFixed(DECIMALES);
            colocar(punto);
            marcador.openPopup();
        };
        // Un edificio propone su nombre y la dirección de su sede, sin pisar lo ya escrito.
        const proponer = (figura, sede) => {
            if (espacio && !espacio.value.trim() && figura.tipo === 'edificio') espacio.value = figura.nombre;
            if (direccion && !direccion.value.trim()) direccion.value = sede.direccion;
        };
        const verTodas = () => encuadrarSedes(mapa, sedes, 24);
        // Las demás unidades ubicadas: tocar su foto copia su punto y propone su edificio y dirección.
        const copiarPunto = grupo => {
            const referencia = grupo.unidades[0];
            if (espacio && !espacio.value.trim()) espacio.value = referencia.edificio;
            if (direccion && !direccion.value.trim()) direccion.value = referencia.direccion;
            escribir(L.latLng(grupo.punto));
        };

        // Solo el formulario de la unidad tiene «espacio»: en el de sedes, tocar otra sede no propone nada.
        dibujarGeometria(mapa, sedes, espacio ? proponer : null);
        const separar = dibujarSedes(mapa, sedes, null);
        agruparPorPunto(mapa, otras).forEach(grupo => {
            const vecina = L.marker(grupo.punto, {
                icon: pin(grupo.unidades[0].imagen, grupo.unidades.length), opacity: 0.85, riseOnHover: true,
            }).addTo(mapa);
            const pista = document.createElement('div');
            grupo.unidades.forEach(unidad => {
                const linea = document.createElement('div');
                linea.textContent = unidad.piso ? `${unidad.nombre} · ${unidad.piso}` : unidad.nombre;
                pista.append(linea);
            });
            const accion = document.createElement('em');
            accion.textContent = traducir('Toque para usar este mismo punto');
            pista.append(accion);
            vecina.bindTooltip(pista, { direction: 'top', offset: [0, -50], className: 'mapa-unidad__vecinas' });
            vecina.on('click', () => copiarPunto(grupo));
        });
        mapa.on('click', evento => {
            if (marcarPunto) escribir(evento.latlng);
        });
        [latitud, longitud].forEach(entrada => entrada.addEventListener('change', () => {
            const punto = leerPunto();
            if (!punto) return;
            colocar(punto);
            mapa.panTo(punto);
        }));
        [espacio, direccion, campo('localidad')].forEach(entrada => entrada?.addEventListener('input', () => {
            marcador?.setPopupContent(vistaPrevia());
        }));

        const inicial = leerPunto();
        if (inicial) {
            mapa.setView(inicial, ZOOM_PUNTO);
            colocar(inicial);
        } else {
            verTodas();
        }
        separar();
        controlDeSedes(mapa, sedes, verTodas);
        // El editor de sedes suma sus herramientas de dibujo sobre este mismo mapa.
        elemento.dispatchEvent(new CustomEvent('mapa-unidad:editor', {
            bubbles: true,
            detail: { mapa, puntoMarcado: Boolean(inicial), pausarPunto: pausa => { marcarPunto = !pausa; } },
        }));
    }

    document.addEventListener('DOMContentLoaded', () => {
        const ficha = document.querySelector('[data-mapa-unidad]');
        const datos = document.getElementById('datosMapaUnidad');
        if (ficha && datos) montarFicha(ficha, JSON.parse(datos.textContent));
        document.querySelectorAll('[data-mapa-editor]').forEach(montarEditor);
    });
}());
