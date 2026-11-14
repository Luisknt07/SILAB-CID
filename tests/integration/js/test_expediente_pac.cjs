const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/unidades/expediente_pac.js'), 'utf8');

function fixture({pestanas = false, fichas = false, contraste = null} = {}) {
  const elemento = tipo => {
    const e = {tipo, textContent: '', children: [], append(...hijos) {this.children.push(...hijos);},
      replaceChildren(...hijos) {this.children = hijos;}};
    Object.defineProperty(e, 'innerHTML', {set() {throw new Error('El contraste no interpreta HTML de los registros.');}});
    return e;
  };
  const handlers = new Map(), rows = [], general = {textContent: ''}, vacio = {hidden: false};
  const filtroClase = {value: ''}, filtroArea = {value: '', options: ['', 'unidad', 'a', 'b'].map(value => ({value}))};
  const tabs = pestanas ? ['', 'equipos', 'software', 'materiales', 'insumos', 'servicios', 'por_clasificar'].map(clase => {
    const atributos = {}, contador = {textContent: ''};
    return {id: 'pac-tab-' + (clase || 'todas'), dataset: {pacTabClase: clase}, hidden: false, disabled: false, tabIndex: -1, atributos, contador,
      setAttribute(clave, valor) {atributos[clave] = valor;}, focus() {this.enfocada = true;},
      querySelector: selector => selector === '[data-pac-tab-numero]' ? contador : null,
      closest(selector) {return selector === '[data-pac-tab-clase]' ? this : null;}};
  }) : [];
  const panel = {atributos: {}, setAttribute(clave, valor) {this.atributos[clave] = valor;}};
  const caja = {dataset: {}, querySelectorAll: selector => selector === '[data-pac-tab-clase]' ? tabs : rows,
    addEventListener(event, fn) {handlers.set(event, fn);},
    querySelector(selector) {return selector === '[data-pac-total-general]' ? general
      : selector === '[data-pac-vacio]' ? vacio
      : selector === '[data-pac-panel-clases]' ? panel
      : pestanas && selector === '[data-pac-filtro-clase]' ? filtroClase
      : pestanas && selector === '[data-pac-filtro-area]' ? filtroArea : null;}};
  const document = {querySelector: () => caja, createElement: elemento,
    getElementById: id => id === 'pacComprasContraste' && contraste ? {textContent: JSON.stringify(contraste)} : null};
  const window = {};
  vm.runInNewContext(source, {window, document, Intl});
  function fila(cantidad, unitario, plantilla = false) {
    const numero = {textContent: ''}, grupo = {textContent: ''}, semestre = {textContent: ''};
    const sustento = {textContent: ''}, salida = {textContent: '', dataset: {}};
    const campos = {cantidad: {value: cantidad}, costo_unitario: {value: unitario}, partida: {value: ''},
      mes_compra: {value: ''}, justificacion: {value: ''}, equipos_referencia: {value: '[]'}};
    Object.assign(campos, {id_necesidad: {value: ''}, item: {value: ''},
      clase_bien: {value: '', options: ['', 'equipos', 'software', 'materiales', 'repuestos', 'insumos', 'reactivos', 'servicios'].map(value => ({value}))},
      area_id: {value: '', options: ['', 'unidad', 'a', 'b'].map(value => ({value, text: {unidad: 'Toda la unidad', a: 'Área A', b: 'Área B'}[value] || ''}))},
      unidad_medida: {value: ''}, tipo_necesidad: {value: ''}});
    campos.mes_compra.options = ['', '1', '2', '7'].map(value => ({value, text: {'1': 'Enero', '2': 'Febrero', '7': 'Julio'}[value] || ''}));
    const ficha = {hidden: false, id: ''}, contrastePanel = elemento('div');
    const resumen = Object.fromEntries(['nombre', 'area', 'cantidad', 'total', 'mes'].map(clave => [clave, {textContent: ''}]));
    const atributos = {}, boton = {atributos, setAttribute(clave, valor) {atributos[clave] = valor;},
      closest(selector) {return selector === '[data-pac-resumen-fila]' ? this : selector === 'tr' ? row : null;}};
    const row = {dataset: {}, hasAttribute: () => plantilla, numero, salida, campos, grupo, semestre, sustento,
      ficha, boton, resumen, contrastePanel,
      querySelector(selector) {
        if (contraste && selector === '[data-pac-contraste]') return contrastePanel;
        if (fichas && selector === '[data-pac-ficha]') return ficha;
        if (fichas && selector === '[data-pac-resumen-fila]') return boton;
        const claveResumen = selector.match(/data-pac-fila-(\w+)/)?.[1];
        if (fichas && claveResumen) return resumen[claveResumen] || null;
        if (selector === '[data-pac-numero]') return numero;
        if (selector === '[data-pac-total]') return salida;
        if (selector === '[data-pac-grupo]') return grupo;
        if (selector === '[data-pac-semestre]') return semestre;
        if (selector === '[data-pac-sustento]') return sustento;
        const clave = selector.match(/compras__(\w+)/)?.[1];
        return campos[clave] || null;
      }};
    rows.push(row);
    return row;
  }
  return {api: window.ExpedientePAC, root: document, caja, rows, general, vacio, fila, tabs, panel, filtroClase, filtroArea,
    input() {handlers.get('input')();}, change(target) {handlers.get('change')({target});},
    click(target) {handlers.get('click')({target});},
    key(target, key) {let prevented = false; handlers.get('keydown')({target, key, preventDefault() {prevented = true;}}); return prevented;}};
}

test('un importe incompleto o inválido permanece sin calcular, distinto del costo cero', () => {
  const f = fixture();
  for (const [cantidad, unitario] of [['', '0'], ['2', ''], ['0', '5'], ['-1', '5'],
                                   ['2', '-1'], ['Infinity', '2'], ['2', 'NaN']]) {
    assert.equal(f.api.importe(cantidad, unitario), null);
  }
  assert.equal(f.api.importe('2', '0'), 0);
  assert.equal(f.api.importe('2', '10,50'), 21);
  assert.equal(f.api.importe('1e308', '1e308'), null);
  assert.equal(f.api.importe('1000000000001', '1'), null);
  assert.equal(f.api.importe('1', '1000000000001'), null);
  assert.equal(f.api.importe('1000000000000', '1000000000000'), 1e24);
});

test('resumen por cuatro clases conserva reactivos y repuestos sin duplicar importes', () => {
  const f = fixture();
  const lectura = f.api.resumenFilas([
    {clase: 'equipos', importe: 20, semestre: 1},
    {clase: 'software', importe: 10, semestre: 2},
    {clase: 'materiales', importe: 7, semestre: 1},
    {clase: 'repuestos', importe: 3, semestre: 2},
    {clase: 'insumos', importe: 4, semestre: 2},
    {clase: 'reactivos', importe: 6, semestre: null},
  ]);
  assert.equal(lectura.total.total, 50);
  assert.equal(lectura.total.numero, 6);
  assert.equal(lectura.grupos.materiales.total, 10);
  assert.equal(lectura.grupos.insumos.total, 10);
  assert.equal(lectura.total.s1, 27);
  assert.equal(lectura.total.s2, 17);
  assert.equal(lectura.sinMes, 1);
  assert.equal(f.api.claseResumen('servicios'), 'servicios');
  assert.equal(f.api.claseResumen('invalido'), 'por_clasificar');
});

test('el redondeo por necesidad coincide con los centavos del servidor, sin error binario', () => {
  const f = fixture();
  assert.equal(f.api.importeRedondeado('1', '10.075'), 10.08);
  assert.equal(f.api.importeRedondeado('3', '0.335'), 1.01);
  assert.equal(f.api.importeRedondeado('1', '0.334'), 0.33);
  assert.equal(f.api.importeRedondeado('1e2', '0.075'), 7.5);
  assert.equal(f.api.importeRedondeado('0.5', '3.35'), 1.68);
  assert.equal(f.api.importeRedondeado('2', '0'), 0);
  assert.equal(f.api.importeRedondeado('', '10'), null);
});

test('resumen no presenta suma parcial ante precio pendiente aunque otras clases estén completas', () => {
  const f = fixture();
  const lectura = f.api.resumenFilas([
    {clase: 'equipos', importe: null, semestre: 1},
    {clase: 'software', importe: 10, semestre: 2},
  ]);
  assert.equal(lectura.total.total, null);
  assert.equal(lectura.total.s1, null);
  assert.equal(lectura.total.s2, 10);
  assert.equal(lectura.grupos.equipos.total, null);
  assert.equal(lectura.grupos.software.total, 10);
});

test('actualiza cada tarjeta y el total visible, sin contar la fila plantilla', () => {
  const f = fixture(), primera = f.fila('2', '10.5'), segunda = f.fila('1', '0');
  const plantilla = f.fila('100', '100', true);
  f.api.iniciar(f.root).refrescar();
  assert.equal(primera.salida.textContent, '21,00');
  assert.equal(segunda.salida.textContent, '0,00');
  assert.equal(f.general.textContent, '21,00');
  assert.equal(plantilla.salida.textContent, '');
  assert.equal(primera.numero.textContent, 'Necesidad 1');
  assert.equal(segunda.numero.textContent, 'Necesidad 2');
});

test('la edición y las nuevas filas usan eventos delegados sin tocar los campos guardados', () => {
  const f = fixture(), primera = f.fila('2', '10');
  f.api.iniciar(f.root);
  primera.campos.cantidad.value = '3';
  f.input();
  assert.equal(primera.salida.textContent, '30,00');
  const nueva = f.fila('2', '7');
  f.change();
  assert.equal(nueva.numero.textContent, 'Necesidad 2');
  assert.equal(nueva.salida.textContent, '14,00');
  assert.equal(f.general.textContent, '44,00');
  assert.equal(primera.campos.costo_unitario.value, '10');
  primera.campos.cantidad.value = '';
  f.input();
  assert.equal(primera.salida.textContent, '—');
  assert.equal(f.general.textContent, '—');
});

test('no actúa en formularios que no tengan editor PAC', () => {
  const f = fixture();
  assert.equal(f.api.iniciar({querySelector: () => null}), null);
});

test('el grupo se obtiene de la partida y no inventa un código cuando falta', () => {
  const f = fixture(), fila = f.fila('1', '5');
  f.api.iniciar(f.root);
  assert.equal(fila.grupo.textContent, 'Por definir');
  fila.campos.partida.value = '530814';
  f.input();
  assert.equal(fila.grupo.textContent, '53');
  fila.campos.partida.value = 'AB123';
  f.input();
  assert.equal(fila.grupo.textContent, 'AB');
  assert.equal(fila.campos.partida.value, 'AB123');
  fila.campos.partida.value = '';
  f.input();
  assert.equal(fila.grupo.textContent, 'Por definir');
  assert.equal(f.vacio.hidden, true);
});

test('el total previsto no muestra una suma parcial mientras falte un importe', () => {
  for (const [cantidad, unitario] of [['2', ''], ['', '10'], ['0', '10']]) {
    const f = fixture(), completa = f.fila('2', '7'), incompleta = f.fila(cantidad, unitario);
    f.api.iniciar(f.root);
    assert.equal(completa.salida.textContent, '14,00');
    assert.equal(incompleta.salida.textContent, '—');
    assert.equal(f.general.textContent, '—');
    incompleta.campos.cantidad.value = '1';
    incompleta.campos.costo_unitario.value = '0';
    f.input();
    assert.equal(incompleta.salida.textContent, '0,00');
    assert.equal(f.general.textContent, '14,00');
  }
});

test('un plan sin necesidades no presenta un cero como total calculado', () => {
  const f = fixture();
  f.fila('', '', true);
  f.api.iniciar(f.root);
  assert.equal(f.general.textContent, '—');
  assert.equal(f.vacio.hidden, false);
});

test('el mes determina el semestre sin crear un dato editable independiente', () => {
  const f = fixture(), fila = f.fila('1', '5');
  for (let mes = 1; mes <= 12; mes++) assert.equal(f.api.semestre(String(mes)), mes <= 6 ? 1 : 2);
  for (const mes of ['', '0', '13', '6.5', 'mes']) assert.equal(f.api.semestre(mes), null);
  f.api.iniciar(f.root);
  assert.equal(fila.semestre.textContent, '—');
  fila.campos.mes_compra.value = '6';
  f.change();
  assert.equal(fila.semestre.textContent, '1.º');
  fila.campos.mes_compra.value = '7';
  f.change();
  assert.equal(fila.semestre.textContent, '2.º');
  fila.campos.justificacion.value = 'Se reemplaza el equipo con falla documentada.';
  fila.campos.clase_bien.value = 'equipos';
  f.input();
  assert.equal(fila.sustento.textContent, 'Sustento registrado');
});

test('las fases se describen sin alterar cantidades, importes o el semestre', () => {
  const f = fixture();
  assert.equal(f.api.etiquetaFase('', ''), 'Sin fases');
  assert.equal(f.api.etiquetaFase('', '2'), 'Proyecto por indicar');
  assert.equal(f.api.etiquetaFase('Renovación', '2'), 'Fase 2 · Renovación');
  assert.equal(f.api.etiquetaFase('Renovación', '21'), 'Fase por indicar · Renovación');
  assert.equal(f.api.etiquetaFase('Renovación', '1.5'), 'Fase por indicar · Renovación');
  const fila = f.fila('2', '10');
  const etiqueta = {textContent: ''};
  fila.campos.grupo_fases = {value: 'Ampliación'};
  fila.campos.fase_numero = {value: '3'};
  const anterior = fila.querySelector;
  fila.querySelector = selector => selector === '[data-pac-fase]' ? etiqueta : anterior(selector);
  f.api.iniciar(f.root);
  assert.equal(etiqueta.textContent, 'Fase 3 · Ampliación');
  assert.equal(f.general.textContent, '20,00');
  assert.equal(fila.campos.cantidad.value, '2');
  assert.equal(fila.campos.mes_compra.value, '');
});

test('sólo una selección real de equipos actualiza el JSON guardado, sin borrar referencias al abrir', () => {
  const f = fixture(), fila = f.fila('1', '5');
  fila.campos.equipos_referencia.value = '["referencia-anterior"]';
  f.api.iniciar(f.root);
  assert.equal(fila.campos.equipos_referencia.value, '["referencia-anterior"]');
  const selector = {options: [{value: 'eq-1', selected: true}, {value: 'eq-2', selected: false},
                             {value: 'eq-3', selected: true}],
    matches: () => true, closest: () => fila};
  f.change(selector);
  assert.deepEqual(JSON.parse(fila.campos.equipos_referencia.value), ['eq-1', 'eq-3']);
  selector.options.forEach(opcion => {opcion.selected = false;});
  f.change(selector);
  assert.equal(fila.campos.equipos_referencia.value, '[]');
});

test('las pestañas filtran clases sin quitar campos, identidades ni importes de las otras compras', () => {
  const f = fixture({pestanas: true}), equipo = f.fila('2', '10'), software = f.fila('1', '7');
  equipo.campos.clase_bien.value = 'equipos'; equipo.campos.id_necesidad.value = 'equipo-id';
  software.campos.clase_bien.value = 'software'; software.campos.id_necesidad.value = 'licencia-id';
  f.api.iniciar(f.root);
  const pestana = f.tabs.find(t => t.dataset.pacTabClase === 'software');
  f.click(pestana);
  assert.equal(f.filtroClase.value, 'software');
  assert.equal(pestana.atributos['aria-selected'], 'true');
  assert.equal(pestana.tabIndex, 0);
  assert.equal(f.panel.atributos['aria-labelledby'], 'pac-tab-software');
  assert.equal(equipo.hidden, true);
  assert.equal(software.hidden, false);
  assert.equal(f.general.textContent, '27,00');
  assert.equal(f.rows.length, 2);
  assert.equal(equipo.campos.id_necesidad.value, 'equipo-id');
  assert.equal(software.campos.id_necesidad.value, 'licencia-id');
  assert.equal(f.tabs.find(t => t.dataset.pacTabClase === 'equipos').contador.textContent, '1');
});

test('materiales y repuestos comparten pestaña, insumos y reactivos conservan su clase original', () => {
  const f = fixture({pestanas: true});
  const filas = ['materiales', 'repuestos', 'insumos', 'reactivos', 'servicios'].map(clase => {
    const fila = f.fila('1', '5'); fila.campos.clase_bien.value = clase; return fila;
  });
  f.api.iniciar(f.root);
  f.click(f.tabs.find(t => t.dataset.pacTabClase === 'materiales'));
  assert.deepEqual(filas.map(f => f.hidden), [false, false, true, true, true]);
  f.click(f.tabs.find(t => t.dataset.pacTabClase === 'insumos'));
  assert.deepEqual(filas.map(f => f.hidden), [true, true, false, false, true]);
  assert.equal(filas[1].campos.clase_bien.value, 'repuestos');
  assert.equal(filas[3].campos.clase_bien.value, 'reactivos');
  assert.equal(f.general.textContent, '25,00');
});

test('flechas, Inicio y Fin recorren pestañas visibles con un solo punto de tabulación', () => {
  const f = fixture({pestanas: true}), fila = f.fila('1', '5');
  fila.campos.clase_bien.value = 'equipos';
  f.api.iniciar(f.root);
  const todas = f.tabs[0], ultima = f.tabs.find(t => t.dataset.pacTabClase === 'servicios');
  assert.equal(f.tabs.at(-1).hidden, true);
  assert.equal(f.key(todas, 'ArrowLeft'), true);
  assert.equal(f.filtroClase.value, 'servicios');
  assert.equal(ultima.enfocada, true);
  assert.equal(f.key(ultima, 'Home'), true);
  assert.equal(f.filtroClase.value, '');
  assert.equal(f.key(todas, 'End'), true);
  assert.equal(f.filtroClase.value, 'servicios');
  assert.equal(f.tabs.filter(t => t.tabIndex === 0).length, 1);
  assert.equal(f.key(ultima, 'ArrowRight'), true);
  assert.equal(f.filtroClase.value, '');
  assert.equal(f.key(todas, 'Tab'), false);
});

test('Por clasificar aparece sólo con filas pendientes y vuelve a Todas al clasificar la última', () => {
  const f = fixture({pestanas: true}), fila = f.fila('1', '5');
  const pendiente = f.tabs.find(t => t.dataset.pacTabClase === 'por_clasificar');
  f.api.iniciar(f.root);
  assert.equal(pendiente.hidden, false);
  f.click(pendiente);
  assert.equal(f.filtroClase.value, 'por_clasificar');
  fila.campos.clase_bien.value = 'equipos';
  f.change();
  assert.equal(pendiente.hidden, true);
  assert.equal(f.filtroClase.value, '');
  assert.equal(f.tabs[0].atributos['aria-selected'], 'true');
  assert.equal(fila.hidden, false);
});

test('añadir desde una pestaña aplica su clase y área sólo a la nueva fila', () => {
  const f = fixture({pestanas: true}), anterior = f.fila('2', '10');
  anterior.campos.clase_bien.value = 'equipos'; anterior.campos.area_id.value = 'a';
  anterior.campos.id_necesidad.value = 'anterior-id';
  f.api.iniciar(f.root);
  f.filtroArea.value = 'b';
  f.click(f.tabs.find(t => t.dataset.pacTabClase === 'software'));
  const nueva = f.fila('', '');
  const anadir = {disabled: false, closest(selector) {return selector === '[data-anadir-fila]' ? this : null;}};
  f.click(anadir);
  assert.equal(nueva.campos.clase_bien.value, 'software');
  assert.equal(nueva.campos.area_id.value, 'b');
  assert.equal(nueva.hidden, false);
  assert.equal(anterior.campos.clase_bien.value, 'equipos');
  assert.equal(anterior.campos.area_id.value, 'a');
  assert.equal(anterior.campos.id_necesidad.value, 'anterior-id');
  assert.equal(nueva.campos.id_necesidad.value, '');
});

test('revelar una sugerencia cambia sólo los filtros que la ocultaban, sin reclasificarla', () => {
  const f = fixture({pestanas: true}), fila = f.fila('1', '5');
  fila.campos.clase_bien.value = 'reactivos'; fila.campos.area_id.value = 'b';
  f.api.iniciar(f.root);
  f.click(f.tabs.find(t => t.dataset.pacTabClase === 'equipos'));
  f.filtroArea.value = 'a'; f.change();
  assert.equal(fila.hidden, true);
  f.api.mostrarFila({querySelectorAll: selector => selector === '[data-pac-tab-clase]' ? f.tabs : f.rows,
    querySelector: selector => selector === '[data-pac-filtro-clase]' ? f.filtroClase
      : selector === '[data-pac-filtro-area]' ? f.filtroArea : null}, fila);
  assert.equal(f.filtroClase.value, 'insumos');
  assert.equal(f.filtroArea.value, 'b');
  assert.equal(fila.campos.clase_bien.value, 'reactivos');
  assert.equal(fila.hidden, false);
});

test('todas las fichas de la clase y área filtradas conservan sus campos visibles y habilitados', () => {
  const f = fixture({pestanas: true, fichas: true}), primera = f.fila('1', '5'), segunda = f.fila('2', '7');
  for (const fila of [primera, segunda]) {
    fila.campos.clase_bien.value = 'software'; fila.campos.area_id.value = 'b';
  }
  f.api.iniciar(f.root);
  f.click(f.tabs.find(t => t.dataset.pacTabClase === 'software'));
  f.filtroArea.value = 'b'; f.change();
  assert.equal(primera.hidden, false);
  assert.equal(segunda.hidden, false);
  assert.equal(primera.ficha.hidden, false);
  assert.equal(segunda.ficha.hidden, false);
  assert.equal(f.caja.dataset.pacSeleccionActiva, undefined);
  assert.equal(primera.campos.cantidad.disabled, undefined);
  assert.equal(segunda.campos.cantidad.disabled, undefined);
  primera.campos.item.value = 'Licencia anual CAD'; primera.campos.mes_compra.value = '2';
  primera.campos.unidad_medida.value = 'licencia';
  f.input();
  assert.equal(primera.resumen.nombre.textContent, 'Licencia anual CAD');
  assert.equal(primera.resumen.area.textContent, 'Área B');
  assert.equal(primera.resumen.cantidad.textContent, '1 licencia');
  assert.equal(primera.resumen.mes.textContent, 'Febrero · Semestre 1');
  assert.equal(segunda.ficha.hidden, false);
});

test('el contraste vigente enlaza equipos y alternativas sólo con los mismos datos de la fila', () => {
  const f = fixture(), fila = f.fila('2', '90');
  Object.assign(fila.campos, {item: {value: '  Computador portátil  '}, clase_bien: {value: 'equipos'},
    area_id: {value: 'a'}, tipo_necesidad: {value: 'ampliacion'}, cantidad: {value: '2'},
    unidad_medida: {value: 'equipo'}, equipos_referencia: {value: '["11","12"]'}});
  const referencia = f.api.referenciaFormulario(fila);
  const fuentes = {por_equipo: {'11': {id: 11, nombre: 'Computador actual'}, '12': {id: 12, nombre: 'Computador compartido'}},
    por_necesidad: {'necesidad-id': {referencia_formulario: {...referencia, equipos_referencia: ['12', '11']},
      etiqueta: 'Comparar recursos existentes', resumen: 'Revisar capacidad antes de ampliar.',
      pendientes: ['Confirmar compatibilidad.'], alternativas: [{id: 13, nombre: 'Alternativa por revisar'}]}}};
  const lectura = f.api.lecturaContraste(referencia, 'necesidad-id', fuentes);
  assert.equal(lectura.vigente, true);
  assert.equal(lectura.etiqueta, 'Comparar recursos existentes');
  assert.equal(lectura.existentes.length, 2);
  assert.equal(lectura.alternativas[0].id, 13);
  assert.equal(referencia.item, 'Computador portátil');
});

test('cambiar nombre, clase, área, motivo, cantidad, presentación o referencias invalida el análisis anterior', () => {
  const f = fixture();
  const base = {item: 'Computador', clase_bien: 'equipos', area_id: 'a', tipo_necesidad: 'ampliacion',
    cantidad: '2', unidad_medida: 'equipo', equipos_referencia: ['11']};
  const fuentes = {por_equipo: {'11': {id: 11, nombre: 'Equipo antiguo'}, '22': {id: 22, nombre: 'Equipo recién seleccionado'}},
    por_necesidad: {'necesidad-id': {referencia_formulario: base, etiqueta: 'Análisis anterior favorable',
      resumen: 'No debe mantenerse tras los cambios.', pendientes: ['Advertencia del análisis anterior.'],
      alternativas: [{id: 33, nombre: 'Alternativa anterior'}], existencias: [{nombre: 'Existencia anterior'}],
      referencias_tecnicas: [{nombre: 'Referencia anterior'}]}}};
  for (const [campo, valor] of Object.entries({item: 'Otro bien', clase_bien: 'software', area_id: 'b',
      tipo_necesidad: 'reposicion', cantidad: '4', unidad_medida: 'licencia', equipos_referencia: ['22']})) {
    const lectura = f.api.lecturaContraste({...base, [campo]: valor}, 'necesidad-id', fuentes);
    assert.equal(lectura.vigente, false, campo);
    assert.equal(lectura.etiqueta, 'Contraste por actualizar', campo);
    assert.equal(lectura.alternativas.length, 0, campo);
    assert.equal(lectura.existencias.length, 0, campo);
    assert.equal(lectura.referencias_tecnicas.length, 0, campo);
    assert.match(lectura.resumen, /Guarda y vuelve a abrir el plan/);
    assert.equal(lectura.pendientes.includes('Advertencia del análisis anterior.'), false, campo);
    if (campo === 'equipos_referencia') assert.equal(lectura.existentes[0].id, 22);
  }
  assert.equal(fuentes.por_necesidad['necesidad-id'].alternativas.length, 1);
  assert.equal(fuentes.por_necesidad['necesidad-id'].referencia_formulario.equipos_referencia[0], '11');
});

test('el contraste vigente presenta las coincidencias detectadas aunque no se seleccionaran activos', () => {
  const f = fixture();
  const referencia = {item: 'Computador', clase_bien: 'equipos', area_id: 'a', tipo_necesidad: 'ampliacion',
    cantidad: '2', unidad_medida: 'equipo', equipos_referencia: []};
  const existentes = [1, 2, 3].map(id => ({id, nombre: 'Computador ' + id}));
  const fuentes = {por_necesidad: {'id': {referencia_formulario: referencia, existentes,
    etiqueta: 'Recursos identificados', resumen: 'Tres activos detectados.', pendientes: []}}, por_equipo: {}};
  const actual = f.api.lecturaContraste(referencia, 'id', fuentes);
  assert.equal(actual.vigente, true);
  assert.equal(actual.existentes.length, 3);
  assert.equal(actual.existentes[2].id, 3);
  const cambiado = f.api.lecturaContraste({...referencia, item: 'Otro equipo'}, 'id', fuentes);
  assert.equal(cambiado.vigente, false);
  assert.equal(cambiado.existentes.length, 0);
});

test('una referencia no presente en el inventario actual permanece guardada y se señala para revisión', () => {
  const f = fixture(), fila = f.fila('1', '5');
  fila.campos.equipos_referencia.value = '["equipo-anterior"]';
  const referencia = f.api.referenciaFormulario(fila);
  const lectura = f.api.lecturaContraste(referencia, '', {por_equipo: {}, por_necesidad: {}});
  assert.equal(lectura.vigente, false);
  assert.equal(lectura.existentes.length, 0);
  assert.equal(lectura.pendientes.length, 1);
  assert.match(lectura.pendientes[0], /no aparece en la lectura actual/);
  assert.equal(fila.campos.equipos_referencia.value, '["equipo-anterior"]');
});

test('el panel muestra fuentes y contadores técnicos actuales sin ejecutar etiquetas ni enlaces ajenos', () => {
  const referencia = {item: 'Computador', clase_bien: 'equipos', area_id: 'a', tipo_necesidad: 'reposicion',
    cantidad: '1', unidad_medida: 'equipo', equipos_referencia: ['11']};
  const fuentes = {fecha_corte: '2026-10-21', por_necesidad: {'id': {referencia_formulario: referencia,
    etiqueta: 'Revisar reparación', resumen: 'Contrastar la incidencia antes de reponer.', pendientes: [], alternativas: []}},
    por_equipo: {'11': {id: 11, codigo: 'EQ-11', nombre: '<img src=x onerror=alert(1)>',
      estado: 'Dañado', horas: 12, areas: [{nombre: 'Área A'}], vida_util: {fin: '2030-10-21'},
      incidencias: Array.from({length: 8}, () => ({})), mantenimiento: Array.from({length: 9}, () => ({})),
      incidencias_abiertas: 1, mantenimiento_pendiente: 0,
      periodos: [{periodo: '2026-A', reservas: 4, horas: 12},
        {periodo: '2025-B', reservas: [1, 2, 3], sesiones: 3, horas: 6},
        {periodo: '2025-A', reservas: [], sesiones: null, horas: 2}],
      garantia: {fin: '2027-10-21', vigente: true, cobertura: 'Componentes electrónicos'},
      uso_pendiente: [{reserva: 17, motivos: ['Falta identificar el equipo real', 'Revisar el cierre']}, 242],
      url: 'javascript:alert(1)'}}};
  const f = fixture({contraste: fuentes}), fila = f.fila('1', '5');
  Object.entries(referencia).forEach(([clave, valor]) => {
    fila.campos[clave] = {value: clave === 'equipos_referencia' ? JSON.stringify(valor) : valor};
  });
  fila.campos.id_necesidad.value = 'id';
  f.api.iniciar(f.root);
  const descendientes = e => [e, ...e.children.flatMap(descendientes)];
  const elementos = descendientes(fila.contrastePanel);
  const texto = elementos.map(e => e.textContent).join(' ');
  assert.match(texto, /Revisar reparación/);
  assert.match(texto, /Registros consultados al 21\/10\/2026/);
  assert.match(texto, /12 h registradas del activo/);
  assert.match(texto, /Incidencias abiertas: 1 · Mantenimiento pendiente: 0/);
  assert.match(texto, /2026-A: 4 atenciones con uso · 12 h/);
  assert.match(texto, /2025-B: 3 atenciones con uso · 6 h/);
  assert.match(texto, /2025-A: Atenciones: sin total verificable · 2 h/);
  assert.doesNotMatch(texto, /2025-A: 0 atenciones/);
  assert.match(texto, /Reserva 17: Falta identificar el equipo real; Revisar el cierre/);
  assert.match(texto, /Reserva 242: cierre con uso del activo pendiente de verificar/);
  assert.match(texto, /Garantía vigente al corte · hasta 2027-10-21/);
  assert.match(texto, /Cobertura registrada: Componentes electrónicos/);
  assert.doesNotMatch(texto, /\[object Object\]/);
  assert.doesNotMatch(texto, /Incidencias abiertas: 8/);
  assert.equal(elementos.some(e => e.tipo === 'img' || e.tipo === 'a'), false);
  assert.match(texto, /<img src=x onerror=alert\(1\)>/);
  fila.campos.item.value = 'Nuevo computador';
  f.input();
  assert.match(descendientes(fila.contrastePanel).map(e => e.textContent).join(' '), /Contraste por actualizar/);
});

test('el panel diferencia existencias y licencias de las cantidades técnicas de repuestos sin stock', () => {
  for (const clase of ['software', 'materiales', 'insumos', 'reactivos', 'repuestos']) {
    const referencia = {item: 'Recurso requerido', clase_bien: clase, area_id: 'a', tipo_necesidad: 'dotacion',
      cantidad: '2', unidad_medida: 'unidad', equipos_referencia: []};
    const fuentes = {por_necesidad: {'id': {referencia_formulario: referencia, existentes: [], alternativas: [],
      etiqueta: 'Existencias registradas', resumen: 'Revisar las existencias antes de comprar.', pendientes: [],
      existencias: [{nombre: 'Recurso en inventario', cantidad: '6', unidad_medida: 'cajas',
        estado: 'Disponible', areas: 'Área A', detalle: 'Presentación registrada.', licencias_disponibles: clase === 'software' ? 3 : null}],
      referencias_tecnicas: [{nombre: 'Pieza del catálogo', cantidad: '4', unidad_medida: 'por equipo del modelo',
        es_referencia: true, estado: 'Referencia técnica', detalle: 'Compatibilidad por verificar.'}]}}, por_equipo: {}};
    const f = fixture({contraste: fuentes}), fila = f.fila('2', '5');
    Object.entries(referencia).forEach(([clave, valor]) => {
      fila.campos[clave] = {value: clave === 'equipos_referencia' ? JSON.stringify(valor) : valor};
    });
    fila.campos.id_necesidad.value = 'id';
    f.api.iniciar(f.root);
    const textos = e => [e.textContent, ...e.children.flatMap(textos)];
    const texto = textos(fila.contrastePanel).join(' ');
    assert.match(texto, /Existencias y licencias registradas/);
    assert.match(texto, /Cantidad registrada: 6 cajas/);
    assert.match(texto, /Referencias técnicas de piezas · no representan stock/);
    assert.match(texto, /Cantidad de referencia: 4 por equipo del modelo/);
    assert.doesNotMatch(texto, /Cantidad registrada: 4/);
    assert.match(texto, /no acredita existencias en bodega/);
    if (clase === 'software') assert.match(texto, /Licencias disponibles registradas: 3/);
  }
});
