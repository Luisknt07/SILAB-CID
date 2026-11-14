/* Inventario de equipos del panel de gestión: buscador, filtros por situación y confirmación de existencia sin
   recargar. El panel también se inyecta dentro de la ficha de la unidad, así que
   todo se atiende por delegación en el documento. Sin JavaScript se ve todo y la confirmación abre la ficha. */
(function () {
    'use strict';

    const aplicar = inventario => {
        const texto = (inventario.querySelector('[data-inventario-buscar]')?.value || '').trim().toLowerCase();
        const filtro = inventario.querySelector('[data-inventario-filtro][aria-pressed="true"]')?.dataset.inventarioFiltro || '';
        let visibles = 0;
        inventario.querySelectorAll('[data-inventario-area]').forEach(area => {
            let enArea = 0;
            area.querySelectorAll('[data-inventario-modelo]').forEach(modelo => {
                let enModelo = 0;
                modelo.querySelectorAll('[data-inventario-unidad]').forEach(fila => {
                    const ver = (!texto || fila.dataset.texto.includes(texto))
                        && (!filtro || fila.dataset.filtros.split(' ').includes(filtro));
                    fila.hidden = !ver;
                    enModelo += ver;
                });
                modelo.hidden = !enModelo;
                if (texto || filtro) modelo.open = enModelo > 0;
                enArea += enModelo;
            });
            area.querySelectorAll('[data-inventario-categoria]').forEach(categoria => {
                categoria.hidden = !categoria.querySelector('[data-inventario-modelo]:not([hidden])');
            });
            area.hidden = !enArea;
            // Al buscar o filtrar se abre lo que tiene resultados.
            if (texto || filtro) area.open = enArea > 0;
            visibles += enArea;
        });
        const vacio = inventario.querySelector('[data-inventario-vacio]');
        if (vacio) vacio.hidden = visibles > 0;
    };

    document.addEventListener('input', evento => {
        const buscar = evento.target.closest('[data-inventario-buscar]');
        if (buscar) aplicar(buscar.closest('[data-inventario]'));
        // Tablas simples (insumos): una fila por registro con su texto de búsqueda.
        const enTabla = evento.target.closest('[data-tabla-buscar]');
        if (enTabla) {
            const tabla = enTabla.closest('[data-tabla]');
            const texto = enTabla.value.trim().toLowerCase();
            let visibles = 0;
            tabla.querySelectorAll('tr[data-texto], [data-catalogo-item]').forEach(fila => {
                fila.hidden = Boolean(texto) && !fila.dataset.texto.includes(texto);
                visibles += !fila.hidden;
            });
            const vacio = tabla.querySelector('[data-tabla-vacio]');
            if (vacio) vacio.hidden = visibles > 0;
        }
    });

    document.addEventListener('click', evento => {
        const filtro = evento.target.closest('[data-inventario-filtro]');
        if (filtro) {
            const inventario = filtro.closest('[data-inventario]');
            inventario.querySelectorAll('[data-inventario-filtro]').forEach(boton => boton.setAttribute('aria-pressed', String(boton === filtro)));
            aplicar(inventario);
            return;
        }
        const plegar = evento.target.closest('[data-inventario-plegar]');
        if (plegar) {
            const grupos = [...plegar.closest('[data-inventario]').querySelectorAll('[data-inventario-area]:not([hidden]), [data-inventario-modelo]:not([hidden])')];
            const abrir = grupos.some(grupo => !grupo.open);
            grupos.forEach(grupo => { grupo.open = abrir; });
            return;
        }
    });

    // Existencias y consumo: cada minuto se traen las cifras, la gráfica de consumo y los movimientos recientes.
    const refrescarExistencias = async () => {
        const vivo = document.querySelector('[data-inventario-vivo="kardex"]');
        const consola = vivo?.closest('[data-management-url]');
        if (!vivo || !consola || vivo.closest('[hidden]') || document.hidden) return;
        const url = new URL(consola.dataset.managementUrl, window.location.href);
        url.searchParams.set('view', 'recursos');
        url.searchParams.set('modo_recursos', 'inventario');
        url.searchParams.set('fragment', '1');
        try {
            const respuesta = await fetch(url, { credentials: 'same-origin' });
            if (!respuesta.ok) return;
            const nuevo = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
            nuevo.querySelectorAll('[data-inventario-vivo]').forEach(bloque => {
                const actual = document.querySelector(`[data-inventario-vivo="${bloque.dataset.inventarioVivo}"]`);
                if (actual) actual.replaceChildren(...bloque.childNodes);
            });
            const hora = document.querySelector('[data-inventario-hora]');
            if (hora) hora.textContent = `Actualizado a las ${new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' })}`;
        } catch (_) { /* Sin red: se intenta en el siguiente minuto. */ }
    };
    window.setInterval(refrescarExistencias, 60000);

    // Confirmar la existencia de un equipo sin salir del panel.
    document.addEventListener('submit', async evento => {
        const formulario = evento.target.closest('.inventario__verificar');
        if (!formulario) return;
        evento.preventDefault();
        const boton = formulario.querySelector('button');
        boton.disabled = true;
        try {
            const datos = new FormData(formulario);
            datos.set('resultado', 'existe');
            const respuesta = await fetch(formulario.action, {
                method: 'POST', body: datos, credentials: 'same-origin', headers: { Accept: 'application/json' },
            });
            if (!respuesta.ok) throw new Error(String(respuesta.status));
            const fila = formulario.closest('[data-inventario-unidad]');
            const marca = document.createElement('span');
            marca.className = 'inventario__estado is-ok';
            marca.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i> ';
            marca.append(boton.dataset.hecho || 'Verificada');
            formulario.replaceWith(marca);
            if (fila) fila.dataset.filtros = fila.dataset.filtros.split(' ').filter(etiqueta => etiqueta !== 'verificar').join(' ');
        } catch (_) {
            boton.disabled = false;
            formulario.submit();
        }
    });
}());
