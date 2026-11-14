/* Lector de equipos: lee con la cámara o en una foto (components/lectura_codigos.js) la etiqueta de bodega o
   el QR del sistema, busca el equipo y muestra su ficha completa: trazabilidad, hermanos y familia de
   producto. Si el código es nuevo, pide primero qué equipo es (o lo toma del reporte de bodega) y con ese
   nombre muestra solo lo relacionado: los equipos de la unidad sin código, los modelos que ya existen y las
   áreas donde suele estar; registrar abre el alta completa de la gestión con todo eso ya puesto. */
(function () {
    'use strict';
    const $ = selector => document.querySelector(selector);
    const t = texto => (window.gettext ? window.gettext(texto) : texto);
    const estado = $('[data-estado]');
    const inicio = $('[data-inicio]');
    const resultado = $('[data-resultado]');
    const registro = $('[data-registro]');
    const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    let ultimo = '';

    const escapar = texto => String(texto ?? '').replace(/[&<>"']/g, caracter => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[caracter]));
    const avisar = texto => { estado.textContent = texto; };

    const lectura = window.LecturaCodigos.crear({
        video: $('[data-video]'),
        visor: $('[data-visor]'),
        zxing: window.LECTOR.zxing,
        avisar,
        alLeer: codigo => encontrado(codigo),
        alCambiar: activa => { $('[data-activar]').hidden = activa; $('[data-detener]').hidden = !activa; },
    });

    // --- Búsqueda y ficha ----------------------------------------------------------------------
    async function encontrado(codigo) {
        codigo = (codigo || '').trim();
        if (!codigo || codigo === ultimo) return;
        ultimo = codigo;
        lectura.detener();
        avisar(t('Código leído:') + ' ' + codigo);
        $('[data-codigo]').value = codigo;
        let datos = null;
        try {
            const respuesta = await fetch(`${window.LECTOR.buscar}?codigo=${encodeURIComponent(codigo)}`, { credentials: 'same-origin' });
            datos = await respuesta.json();
            if (!respuesta.ok) throw new Error(datos.error || '');
        } catch (error) {
            ultimo = '';
            avisar(error.message || t('No se pudo consultar el código. Revisa la conexión e inténtalo de nuevo.'));
            return;
        }
        if (datos.encontrado) mostrarEquipo(datos);
        else mostrarRegistro(datos);
    }

    const enlaceLector = codigo => `?codigo=${encodeURIComponent(codigo)}`;
    const lista = (elementos, plantilla, vacio) => (elementos && elementos.length
        ? `<ul class="lector__lista">${elementos.map(plantilla).join('')}</ul>` : `<p class="lector__vacio">${escapar(vacio)}</p>`);

    function pariente(item, conUnidad) {
        const detalle = [item.codigo_bien ? `${t('Bien')} ${item.codigo_bien}` : item.codigo, conUnidad ? item.unidad : '', item.area]
            .filter(Boolean).map(escapar).join(' · ');
        return `<li><a href="${enlaceLector(item.codigo)}" data-abrir="${escapar(item.codigo)}">
            <strong>${escapar(item.nombre)}</strong><small>${detalle}</small>
            <b class="${item.disponible ? 'is-disponible' : ''}">${escapar(item.estado)}</b></a></li>`;
    }

    function porUnidad(items, unidadActual) {
        const grupos = new Map();
        items.forEach(item => {
            if (!grupos.has(item.unidad)) grupos.set(item.unidad, []);
            grupos.get(item.unidad).push(item);
        });
        return Array.from(grupos.entries()).map(([unidad, propios]) => `<details class="lector__grupo"${unidad === unidadActual ? ' open' : ''}>
            <summary><span>${escapar(unidad)}</span><b>${propios.length}</b></summary>
            <ul class="lector__parientes">${propios.map(item => pariente(item, false)).join('')}</ul></details>`).join('');
    }

    function seccionParentela(d) {
        const p = d.parentela || {};
        const hermanos = p.hermanos || [];
        const mismo = p.mismo_modelo || [];
        const familia = p.familia;
        const unidadesFamilia = familia ? familia.unidades.map(u => `<li class="${u.esta ? 'is-actual' : ''}"><strong>${escapar(u.total)}</strong>
            <span>${escapar(u.unidad)}</span><small>${escapar(u.disponibles)} ${t('disponibles')}</small></li>`).join('') : '';
        return `<section class="ficha__tarjeta is-ancha">
          <header><span>${t('UBICAR TODOS LOS EQUIPOS')}</span><h2>${t('Hermanos y familia')}</h2></header>
          <h3>${t('Hermanos: el mismo modelo en')} ${escapar(d.unidad)}</h3>
          ${hermanos.length ? `<p class="lector__resumen-cifra"><strong>${hermanos.length + 1}</strong> ${t('equipos de este modelo en la unidad, contando este.')}</p>
            <ul class="lector__parientes">${hermanos.map(item => pariente(item, false)).join('')}</ul>`
            : `<p class="lector__vacio">${t('Es el único equipo de su modelo en la unidad.')}</p>`}
          <h3>${t('El mismo modelo en otras unidades')}</h3>
          ${mismo.length ? porUnidad(mismo, '') : `<p class="lector__vacio">${t('Ninguna otra unidad tiene este modelo.')}</p>`}
          <h3>${t('Familia de producto')}${familia ? ': ' + escapar(familia.nombre) : ''}</h3>
          ${familia ? `<p class="lector__resumen-cifra"><strong>${escapar(familia.total)}</strong> ${t('equipos de esta familia en la Universidad, por unidad:')}</p>
            <ul class="lector__familia-unidades">${unidadesFamilia}</ul>
            ${familia.parientes.length ? `<h3>${t('Otros modelos de la familia, por unidad')}</h3>${porUnidad(familia.parientes, d.unidad)}` : ''}
            ${familia.url ? `<p><a class="lector__boton" href="${escapar(familia.url)}"><i class="fas fa-sitemap" aria-hidden="true"></i> ${t('Ver la familia en el tablero institucional')}</a></p>` : ''}`
            : `<p class="lector__vacio">${t('Este modelo aún no tiene familia de producto. Asígnala en el catálogo para compararlo con los de otras unidades.')}</p>`}
        </section>`;
    }

    function mostrarEquipo(d) {
        inicio.hidden = true;
        registro.hidden = true;
        const foto = d.imagen ? `<img src="${escapar(d.imagen)}" alt="">` : `<i class="${escapar(d.icono)}" aria-hidden="true"></i>`;
        const dato = (titulo, valor, nota) => (valor || nota
            ? `<div><dt>${titulo}</dt><dd>${valor || '—'}${nota ? `<small>${nota}</small>` : ''}</dd></div>` : '');
        const motivos = (d.motivos || []).map(motivo => `<li>${escapar(motivo)}</li>`).join('');
        const etiquetas = [d.categoria, d.familia_nombre, d.modelo_codigo].filter(Boolean)
            .map(texto => `<span>${escapar(texto)}</span>`).join('');
        const recorrido = (d.recorrido || []).map((parada, indice, todas) => `<li class="${indice === todas.length - 1 ? 'is-actual' : ''}">
            <strong>${escapar(parada.unidad)}</strong><small>${escapar(parada.como)} · ${escapar(parada.desde)}</small></li>`).join('');
        let avisos = '';
        if (d.requiere_cambio) avisos += `<p class="lector__alerta is-critico"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i> ${t('Cumplió su vida útil: conviene planificar su reemplazo.')}</p>`;
        else if (d.vida_alerta) avisos += `<p class="lector__alerta"><i class="fas fa-hourglass-half" aria-hidden="true"></i> ${t('Se acerca al fin de su vida útil')} (${escapar(Math.round(d.vida_consumida))} %).</p>`;
        if (d.prestamo) avisos += `<p class="lector__alerta${d.prestamo.vencido ? ' is-critico' : ''}"><i class="fas fa-hand-holding" aria-hidden="true"></i> ${escapar(d.prestamo.tipo)} · ${t('debe volver el')} ${escapar(d.prestamo.devuelve)}${d.prestamo.vencido ? ' · ' + t('vencido') : ''}</p>`;
        if (!d.activa) avisos += `<p class="lector__alerta is-critico"><i class="fas fa-archive" aria-hidden="true"></i> ${t('Equipo retirado del inventario activo.')}</p>`;
        resultado.innerHTML = `
          <article class="ficha__tarjeta">
            <div class="lector__equipo is-${escapar(d.semaforo)}">
              <div class="lector__equipo-foto">${foto}</div>
              <div class="lector__equipo-datos">
                <span class="lector__semaforo">${escapar(d.semaforo_texto)}</span>
                <h2>${escapar(d.nombre)}</h2>
                ${d.marca_modelo ? `<p>${escapar(d.marca_modelo)}</p>` : ''}
                ${etiquetas ? `<div class="lector__etiquetas">${etiquetas}</div>` : ''}
                ${avisos}
                ${motivos ? `<ul class="lector__motivos">${motivos}</ul>` : ''}
              </div>
            </div>
            <dl class="lector__datos lector__datos--registro">
              ${dato(t('Código del bien'), `<span class="lector__codigo">${escapar(d.codigo_bien || t('Pendiente de bodega'))}</span>`, escapar(d.tipo_bien))}
              ${dato(t('Código del sistema'), `<span class="lector__codigo">${escapar(d.codigo_sistema)}</span>`, (d.codigos_anteriores || []).length ? t('Antes:') + ' ' + d.codigos_anteriores.map(escapar).join(', ') : '')}
              ${dato(t('Unidad'), escapar(d.unidad))}
              ${dato(t('Área'), escapar((d.areas || []).join(', ') || '—'), (d.areas || []).includes(d.ubicacion) ? '' : escapar(d.ubicacion))}
              ${dato(t('Estado'), escapar(d.estado), escapar(d.criticidad))}
              ${dato(t('Número de serie'), escapar(d.serie || '—'))}
              ${dato(t('Clase del bien'), escapar(d.clase_bien))}
              ${dato(t('Uso acumulado'), `${escapar(d.horas_de_uso)} h`, `${escapar(d.sesiones)} ${t('sesiones en el último año')}`)}
              ${dato(t('Custodio'), escapar(d.custodio), escapar(d.ubicacion_bodega))}
              ${dato(t('Valor contable'), d.valor_contable ? `${escapar(d.valor_contable)} USD` : '')}
            </dl>
            <div class="lector__enlaces">
              ${d.ficha_url ? `<a class="lector__boton is-principal" href="${escapar(d.ficha_url)}">${t('Ficha del equipo')}</a>` : ''}
              ${d.ficha_interna_url ? `<a class="lector__boton" href="${escapar(d.ficha_interna_url)}"><i class="fas fa-tools" aria-hidden="true"></i> ${t('Mantenimiento e historia')}</a>` : ''}
              ${d.editar_url ? `<a class="lector__boton" href="${escapar(d.editar_url)}"><i class="fas fa-pen" aria-hidden="true"></i> ${t('Editar sus datos')}</a>` : ''}
              ${d.etiqueta_url ? `<a class="lector__boton" href="${escapar(d.etiqueta_url)}" data-ver-pdf data-pdf-titulo="${t('Etiqueta del equipo')}"><i class="fas fa-print" aria-hidden="true"></i> ${t('Imprimir etiqueta')}</a>` : ''}
              <button type="button" class="lector__boton" data-otra><i class="fas fa-redo" aria-hidden="true"></i> ${t('Leer otro código')}</button>
            </div>
          </article>
          <div class="lector__secciones">
            ${seccionParentela(d)}
            <section class="ficha__tarjeta">
              <header><span>${t('TRAZABILIDAD')}</span><h2>${t('Origen y recorrido')}</h2></header>
              <dl class="lector__datos">
                ${dato(t('Origen'), escapar(d.origen.adquisicion), escapar(d.origen.documento))}
                ${dato(t('Adquirido'), escapar(d.origen.fecha_adquisicion))}
                ${dato(t('Ingreso a bodega'), escapar(d.origen.fecha_ingreso_bodega))}
                ${dato(t('Garantía hasta'), escapar(d.garantia))}
              </dl>
              <h3>${t('Unidades por las que ha pasado')}</h3>
              ${recorrido ? `<ol class="lector__recorrido">${recorrido}</ol>` : `<p class="lector__vacio">${t('Sin registro de alta en el sistema.')}</p>`}
            </section>
            <section class="ficha__tarjeta">
              <header><span>${t('SITUACIÓN TÉCNICA')}</span><h2>${t('Mantenimiento e incidencias')}</h2></header>
              <dl class="lector__datos">
                ${dato(t('Último mantenimiento'), escapar(d.ultimo_mantenimiento || '—'))}
                ${dato(t('Próximo mantenimiento'), escapar(d.proximo_mantenimiento || '—'))}
                ${dato(t('Incidencias abiertas'), escapar(d.incidencias_abiertas))}
              </dl>
              <h3>${t('Incidencias abiertas')}</h3>
              ${lista(d.incidencias, item => `<li><time>${escapar(item.fecha)}</time><strong>${escapar(item.titulo)}</strong><span>${escapar(item.estado)}</span></li>`, t('Ninguna.'))}
              <h3>${t('Últimos mantenimientos')}</h3>
              ${lista(d.mantenimientos, item => `<li><time>${escapar(item.fecha)}</time><strong>${escapar(item.titulo)}</strong><span>${escapar(item.estado)}</span></li>`, t('Sin mantenimientos registrados.'))}
            </section>
            <section class="ficha__tarjeta is-ancha">
              <header><span>${t('LO QUE USA')}</span><h2>${t('Software e insumos')}</h2></header>
              <h3>${t('Software instalado')}</h3>
              ${(d.software || []).length ? `<ul class="lector__chips">${d.software.map(nombre => `<li>${escapar(nombre)}</li>`).join('')}</ul>` : `<p class="lector__vacio">${t('Sin software asociado.')}</p>`}
              <h3>${t('Insumos y materiales')}</h3>
              ${(d.insumos || []).length ? `<ul class="lector__chips">${d.insumos.map(nombre => `<li>${escapar(nombre)}</li>`).join('')}</ul>` : `<p class="lector__vacio">${t('Sin insumos asociados.')}</p>`}
            </section>
            <section class="ficha__tarjeta is-ancha">
              <header><span>${t('HISTORIA')}</span><h2>${t('Todo lo que le ha pasado')}</h2></header>
              ${lista(d.historia, h => `<li><time>${escapar(h.fecha)}</time><strong>${escapar(h.titulo)}</strong><span>${escapar(h.detalle)}</span></li>`, t('Aún no tiene hechos registrados.'))}
            </section>
          </div>`;
        resultado.hidden = false;
        resultado.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // --- Registro de un código nuevo: primero qué equipo es, después solo lo relacionado ----------
    const unidades = JSON.parse(document.getElementById('lector-unidades')?.textContent || '[]');
    const nombre = registro.querySelector('[data-nombre]');
    const bloqueSugerencias = registro.querySelector('[data-sugerencias]');
    const formulario = registro.querySelector('[data-formulario]');
    let bodega = null;
    let propuesta = null;
    let pedido = 0;
    const unidadElegida = () => unidades.find(item => item.slug === registro.querySelector('[data-unidad]')?.value);

    function mostrarRegistro(datos) {
        inicio.hidden = true;
        resultado.hidden = true;
        registro.hidden = false;
        registro.dataset.codigo = datos.codigo;
        bodega = datos.bodega || null;
        propuesta = null;
        registro.querySelectorAll('[data-codigo-nuevo]').forEach(nodo => { nodo.textContent = datos.codigo; });
        registro.querySelector('[data-invalido]').hidden = Boolean(datos.valido);
        registro.querySelector('[data-registrable]').hidden = !datos.valido;
        const cajaBodega = registro.querySelector('[data-bodega]');
        if (cajaBodega) {
            cajaBodega.hidden = !bodega;
            if (bodega) {
                registro.querySelector('[data-bodega-texto]').textContent = [bodega.descripcion,
                    [bodega.marca, bodega.modelo].filter(Boolean).join(' '), bodega.unidad_nombre, bodega.area_nombre]
                    .filter(Boolean).join(' · ');
            }
        }
        // Lo que bodega sabe del bien: su unidad y los datos de la etiqueta.
        const selector = registro.querySelector('[data-unidad]');
        if (selector && bodega?.unidad && unidades.some(item => item.slug === bodega.unidad)) selector.value = bodega.unidad;
        if (formulario) {
            formulario.reset();
            if (bodega?.serie) formulario.elements.serie.value = bodega.serie;
            if (bodega?.tipo_bien) formulario.elements.tipo_bien.value = bodega.tipo_bien;
            if (bodega?.custodio) formulario.elements.custodio.value = bodega.custodio;
        }
        if (bloqueSugerencias) bloqueSugerencias.hidden = true;
        if (nombre) {
            nombre.value = bodega?.nombre || '';
            if (nombre.value) pedirSugerencias();
            else nombre.focus({ preventScroll: true });
        }
        registro.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async function pedirSugerencias() {
        const unidad = unidadElegida();
        const texto = (nombre?.value || '').trim();
        if (!unidad || texto.length < 3) {
            if (bloqueSugerencias) bloqueSugerencias.hidden = true;
            return;
        }
        const numero = ++pedido;
        const parametros = new URLSearchParams({
            unidad: unidad.slug, nombre: texto, codigo: registro.dataset.codigo || '',
            marca: bodega?.marca || '', modelo: bodega?.modelo || '',
        });
        try {
            const respuesta = await fetch(`${window.LECTOR.sugerencias}?${parametros.toString()}`, { credentials: 'same-origin' });
            const datos = await respuesta.json();
            if (!respuesta.ok) throw new Error(datos.error || '');
            if (numero !== pedido) return; // Llegó tarde: ya se escribió otra cosa.
            propuesta = datos;
            pintarSugerencias(texto);
        } catch (error) {
            avisar(error.message || t('No se pudieron buscar los equipos relacionados.'));
        }
    }

    function pintarSugerencias(texto) {
        const p = propuesta;
        const familia = registro.querySelector('[data-familia]');
        familia.hidden = !p.familia;
        if (p.familia) familia.innerHTML = `<i class="fas fa-sitemap" aria-hidden="true"></i> ${t('Familia de producto:')} <strong>${escapar(p.familia.nombre)}</strong>`;
        // Áreas: primero las que ya tienen equipos parecidos; la de bodega, si es de esta unidad, elegida.
        const area = registro.querySelector('[data-area]');
        const deBodega = bodega && bodega.unidad === unidadElegida()?.slug ? bodega.area : null;
        area.innerHTML = `<option value="">${t('Sin área por ahora')}</option>` + p.areas.map(item => `
            <option value="${item.id}">${item.sugerida ? '★ ' : ''}${escapar(item.nombre)}</option>`).join('');
        if (deBodega) area.value = String(deBodega);
        else if (p.areas[0]?.sugerida) area.value = String(p.areas[0].id);
        // 1. Los equipos de la unidad que aún no tienen código y se parecen.
        registro.querySelector('[data-candidatos]').innerHTML = p.equipos.map(equipo => `
            <li><label><input type="radio" name="candidato" value="${equipo.id}"${p.equipos.length === 1 ? ' checked' : ''}>
              <span><strong>${escapar(equipo.nombre)}</strong><small>${escapar(equipo.codigo)}${equipo.area ? ' · ' + escapar(equipo.area) : ''}</small></span></label></li>`).join('')
            || `<li class="lector__vacio">${t('Ningún equipo sin código de la unidad se parece a')} «${escapar(texto)}».</li>`;
        registro.querySelector('[data-asignar]').hidden = !p.equipos.length;
        registro.querySelector('.lector__etiqueta').hidden = !p.equipos.length;
        // 2. Los modelos del catálogo que se parecen, con dónde están.
        registro.querySelector('[data-modelos]').innerHTML = p.modelos.map(modelo => {
            const donde = modelo.presencia.map(lugar => `${lugar.total} ${t('en')} ${lugar.unidad}`).join(' · ');
            const foto = modelo.imagen ? `<img src="${escapar(modelo.imagen)}" alt="">` : `<i class="${escapar(modelo.icono)}" aria-hidden="true"></i>`;
            return `<li><span class="lector__modelo-foto">${foto}</span>
                <span><strong>${escapar(modelo.nombre)}</strong><small>${escapar([modelo.marca_modelo, modelo.familia].filter(Boolean).join(' · '))}</small><small>${escapar(donde)}</small></span>
                <a class="lector__boton${modelo.en_la_unidad ? ' is-principal' : ''}" href="#" data-modelo="${modelo.id}">${t('Registrar como este modelo')}</a></li>`;
        }).join('') || `<li class="lector__vacio">${t('Ningún modelo del catálogo se parece a')} «${escapar(texto)}».</li>`;
        // 3. Un modelo nuevo, con el nombre y la familia que se detectaron.
        registro.querySelector('[data-nuevo-texto]').textContent = `${t('Se crea el modelo')} «${texto}»`
            + `${p.familia ? ` ${t('en la familia')} ${p.familia.nombre}` : ''}.`;
        actualizarAltaNueva();
        bloqueSugerencias.hidden = false;
    }

    // El alta completa en la gestión de la unidad, con lo elegido aquí ya puesto.
    function altaUrl(extra) {
        const parametros = new URLSearchParams({ nuevo_equipo: registro.dataset.codigo || '' });
        const area = registro.querySelector('[data-area]')?.value;
        if (area) parametros.set('espacio', area);
        if (propuesta?.modelos?.length) parametros.set('relacionados', propuesta.modelos.map(modelo => modelo.id).join(','));
        Object.entries(extra).forEach(([clave, valor]) => { if (valor) parametros.set(clave, valor); });
        return `${unidadElegida().gestion}&${parametros.toString()}`;
    }

    function actualizarAltaNueva() {
        const enlace = registro.querySelector('[data-alta-nuevo]');
        if (!enlace || !propuesta) return;
        enlace.href = altaUrl({
            nombre_catalogo: (nombre?.value || '').trim().slice(0, 100),
            familia_equipo: propuesta.familia?.id || '', marca: bodega?.marca || '', modelo: bodega?.modelo || '',
        });
    }

    async function asignar(evento) {
        evento.preventDefault();
        const datos = Object.fromEntries(new FormData(formulario).entries());
        datos.codigo = registro.dataset.codigo;
        datos.equipo_id = formulario.querySelector('[name=candidato]:checked')?.value || '';
        const error = registro.querySelector('[data-error]');
        if (!datos.equipo_id) {
            error.textContent = t('Elige el equipo al que pertenece la etiqueta.');
            error.hidden = false;
            return;
        }
        const respuesta = await fetch(window.LECTOR.registrar, {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
            body: JSON.stringify(datos),
        });
        const cuerpo = await respuesta.json();
        if (!respuesta.ok) {
            error.textContent = cuerpo.error || t('No se pudo guardar.');
            error.hidden = false;
            return;
        }
        error.hidden = true;
        avisar(t('Código asignado. Completa sus datos con «Editar sus datos».'));
        mostrarEquipo(cuerpo);
    }

    function limpiar() {
        ultimo = '';
        resultado.hidden = true;
        registro.hidden = true;
        inicio.hidden = false;
        $('[data-codigo]').value = '';
    }

    document.addEventListener('click', evento => {
        if (evento.target.closest('[data-activar]')) { ultimo = ''; lectura.iniciar(); }
        if (evento.target.closest('[data-detener]')) { lectura.detener(); avisar(t('Cámara detenida.')); }
        if (evento.target.closest('[data-otra]')) { limpiar(); lectura.iniciar(); }
        const abrir = evento.target.closest('[data-abrir]');
        if (abrir && !evento.ctrlKey && !evento.metaKey) {
            evento.preventDefault();
            ultimo = '';
            encontrado(abrir.dataset.abrir);
        }
        const modelo = evento.target.closest('[data-modelo]');
        if (modelo) {
            evento.preventDefault();
            window.location.href = altaUrl({ equipo_catalogo_id: modelo.dataset.modelo });
        }
    });
    $('[data-manual]').addEventListener('submit', evento => {
        evento.preventDefault();
        ultimo = '';
        encontrado($('[data-codigo]').value);
    });
    $('[data-foto]').addEventListener('change', evento => {
        lectura.leerFoto(evento.target.files[0]).finally(() => { evento.target.value = ''; });
    });
    let espera = null;
    nombre?.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(pedirSugerencias, 450); });
    registro.querySelector('[data-nombre-form]')?.addEventListener('submit', evento => {
        evento.preventDefault();
        clearTimeout(espera);
        pedirSugerencias();
    });
    registro.querySelector('[data-unidad]')?.addEventListener('change', pedirSugerencias);
    registro.querySelector('[data-area]')?.addEventListener('change', actualizarAltaNueva);
    formulario?.addEventListener('submit', asignar);
    const inicial = new URLSearchParams(window.location.search).get('codigo');
    if (inicial) encontrado(inicial);
}());
