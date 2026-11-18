// Recepción de existencias y consumo en el panel de gestión: el total se calcula solo, lo opcional no bloquea
// y una presentación cerrada se abre en el mismo paso en que se consume.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');

function element(dataset = {}) {
  const listeners = new Map(), classes = new Set();
  return { dataset, listeners, hidden: true, attributes: [],
    classList: { contains: key => classes.has(key), add: key => classes.add(key),
      remove: key => classes.delete(key), toggle() {} },
    querySelector: () => null, querySelectorAll: () => [],
    setAttribute(name, value) { this[name] = value; },
    addEventListener(type, callback) { if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(callback); },
    fire(type, extra = {}) { for (const callback of listeners.get(type) || []) callback({ preventDefault() {}, stopPropagation() {}, ...extra }); },
    focus() { this.focused = true; } };
}

function control(value = '', extra = {}) {
  return Object.assign(element(), { type: 'text', value, required: false, disabled: false, hidden: false }, extra);
}

function option(value, dataset = {}) {
  return { value, dataset, hidden: false, disabled: false };
}

// Un <select>: el valor decide la opción elegida, como en el navegador.
function select(options, value = '') {
  const field = control(value, { type: 'select-one', options });
  Object.defineProperty(field, 'selectedOptions', {
    get() { const chosen = options.find(item => item.value === field.value); return chosen ? [chosen] : []; },
  });
  return field;
}

function setup(kind, controls, nodes = {}, lists = {}) {
  const root = element({ selectiveLoading: 'true', initialView: 'recursos', managementUrl: '/unidades/mi-unidad/gestion/' });
  const drawer = element(), button = element({ agendaOperationOpen: kind });
  const form = element({ agendaOperationForm: kind });
  const defaults = Object.fromEntries(Object.entries(controls).map(([name, field]) => [name, field.value]));
  form.elements = { namedItem: name => controls[name] || null };
  form.reset = () => { Object.entries(defaults).forEach(([name, value]) => { controls[name].value = value; }); };
  form.querySelector = selector => nodes[selector] || null;
  form.querySelectorAll = selector => lists[selector] || [];
  root.querySelector = selector => selector === '#agendaManagementDrawer' ? drawer : null;
  root.querySelectorAll = selector => {
    if (selector === '[data-agenda-operation-form]') return [form];
    if (selector === '[data-agenda-operation-open]') return [button];
    return [];
  };
  const context = { URL, URLSearchParams, Map, Set, gettext: value => value,
    document: { getElementById: () => root },
    location: { href: 'https://example.test/unidades/mi-unidad/gestion/', search: '', hash: '' },
    history: { replaceState() {} } };
  context.window = context;
  vm.runInNewContext(source, context);
  return { root, drawer, button, form, controls, nodes };
}

function recepcion({ contenido = '1000.000', equipos = ['31', '32'], requiere = '1' } = {}) {
  const insumo = option('7', { inventoryUnit: 'g', presentationSize: contenido, presentationName: 'bobinas',
    presentationSingular: 'bobina', compatibleEquipmentIds: equipos.join(','), requiresEquipment: requiere });
  const controls = {
    registro_id: control('', { type: 'hidden' }),
    consumible_id: select([option(''), insumo]),
    cantidad_inicial: control('', { type: 'hidden' }),
    numero_presentaciones: control('1', { type: 'number' }),
    estado: select([option('bodega'), option('en_uso')], 'bodega'),
    equipo_en_uso_id: select([option(''), ...equipos.map(id => option(id))]),
    bodega: control(''),
    codigo: control(''),
  };
  controls.numero_presentaciones.setCustomValidity = () => {};
  const nodes = { '[data-inventory-quantity-help]': element(), '[data-operation-more]': Object.assign(element(), { open: false }),
    '[data-inventory-presentation-count]': controls.numero_presentaciones };
  const alCrear = element(), alEditar = element();
  const app = setup('lote_consumible', controls, nodes, { '[data-operation-more]': [nodes['[data-operation-more]']],
    '[data-lot-on-create]': [alCrear], '[data-lot-on-edit]': [alEditar] });
  return Object.assign(app, { alCrear, alEditar, resumen: nodes['[data-inventory-quantity-help]'], mas: nodes['[data-operation-more]'] });
}

test('recibir existencias desde la tarjeta de un insumo calcula el total con una presentación por omisión', () => {
  const app = recepcion();
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }];
  app.button.fire('click');
  assert.equal(app.controls.consumible_id.value, '7');
  assert.equal(app.controls.numero_presentaciones.value, '1');
  assert.equal(app.controls.cantidad_inicial.value, '1000');
  assert.match(app.resumen.textContent, /^1 bobina = 1\.?000 g → total 1\.?000 g$/);
  // Lo opcional queda plegado y no bloquea: ni el código ni la bodega son obligatorios.
  assert.equal(app.mas.open, false);
  assert.equal(app.controls.bodega.required, false);
  assert.equal(app.controls.codigo.required, false);
  assert.equal(app.controls.equipo_en_uso_id.required, false);
  assert.equal(app.alCrear.hidden, false);
  assert.equal(app.alEditar.hidden, true);
});

test('varias presentaciones multiplican el contenido sin decimales espurios', () => {
  const app = recepcion({ contenido: '0.100' });
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }];
  app.button.fire('click');
  app.controls.numero_presentaciones.value = '3';
  app.controls.numero_presentaciones.fire('input');
  // 0,1 × 3 daría 0,30000000000000004 y el navegador rechazaría el valor.
  assert.equal(app.controls.cantidad_inicial.value, '0.3');
  assert.match(app.resumen.textContent, /^3 bobinas × 0,1 g → total 0,3 g\. Cada una queda como un lote con su código\.$/);
});

test('un contenido con coma decimal dejaría el total sin calcular: el atributo debe llegar con punto', () => {
  const app = recepcion({ contenido: '1000,000' });
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }];
  app.button.fire('click');
  // Es el fallo que bloqueaba la recepción: la plantilla ya no localiza el número y la pantalla lo dice si falta.
  assert.equal(app.controls.cantidad_inicial.value, '');
  assert.match(app.resumen.textContent, /Contenido por presentación/);
});

test('poner en uso una presentación abre los datos opcionales y elige el único equipo posible', () => {
  const app = recepcion({ equipos: ['31'] });
  app.button.attributes = [{ name: 'data-field-registro_id', value: '90' }, { name: 'data-field-consumible_id', value: '7' },
    { name: 'data-field-cantidad_inicial', value: '1000.000' }, { name: 'data-field-estado', value: 'en_uso' }];
  app.button.fire('click');
  assert.equal(app.mas.open, true);
  assert.equal(app.controls.equipo_en_uso_id.value, '31');
  assert.equal(app.controls.equipo_en_uso_id.required, true);
  assert.equal(app.controls.numero_presentaciones.disabled, true);
  assert.equal(app.controls.numero_presentaciones.value, '1');
  assert.equal(app.alCrear.hidden, true);
  assert.equal(app.alEditar.hidden, false);
  // Al volver a recibir, el pliegue se cierra y el contador se habilita.
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }];
  app.button.fire('click');
  assert.equal(app.mas.open, false);
  assert.equal(app.controls.numero_presentaciones.disabled, false);
});

function movimiento(lotes, requiere = '1') {
  const insumo = option('7', { inventoryUnit: 'g', presentationSize: '1000.000', presentationName: 'bobinas',
    compatibleEquipmentIds: '31', unitCost: '0.0300', requiresEquipment: requiere });
  const controls = {
    consumible_id: select([option(''), insumo]),
    tipo: select([option('ingreso'), option('salida'), option('ajuste')], 'ingreso'),
    motivo: select([option('recepcion', { inventoryDirection: 'ingreso' }),
      option('consumo_practica', { inventoryDirection: 'salida' }), option('caducidad', { inventoryDirection: 'salida' })], 'recepcion'),
    lote_inventario_id: select([option(''), ...lotes]),
    equipo_id: select([option(''), option('31')]),
    incidencia_id: select([option('')]),
    costo_unitario: control('', { type: 'number' }),
    abrir_presentacion: control('', { type: 'hidden' }),
    nota: control('', { type: 'textarea' }),
  };
  const nodes = { '[data-inventory-open-lot]': element(), '[data-inventory-lot-help]': element(),
    '[data-inventory-type]': controls.tipo, '[data-inventory-reason]': controls.motivo, '[data-inventory-lot]': controls.lote_inventario_id };
  const app = setup('inventario', controls, nodes);
  return Object.assign(app, { aviso: nodes['[data-inventory-open-lot]'], ayuda: nodes['[data-inventory-lot-help]'] });
}

test('consumir de una presentación cerrada la abre en el mismo paso y pide el equipo', () => {
  const cerrada = option('50', { consumibleId: '7', lotStatus: 'bodega', unitCost: '0.0300' });
  const app = movimiento([cerrada]);
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }, { name: 'data-field-tipo', value: 'salida' }];
  app.button.fire('click');
  assert.equal(app.controls.motivo.value, 'consumo_practica');
  assert.equal(app.controls.lote_inventario_id.value, '50');
  assert.equal(app.controls.abrir_presentacion.value, '1');
  assert.equal(app.aviso.hidden, false);
  assert.equal(app.controls.equipo_id.required, true);
  assert.equal(app.controls.equipo_id.value, '31');
  assert.equal(app.controls.costo_unitario.value, '0.0300');
  // La nota solo se exige al ajustar el saldo.
  assert.equal(app.controls.nota.required, false);
  app.controls.tipo.value = 'ajuste';
  app.controls.tipo.fire('change');
  assert.equal(app.controls.nota.required, true);
  assert.equal(app.controls.abrir_presentacion.value, '');
  assert.equal(app.aviso.hidden, true);
});

test('un insumo sin equipos compatibles abre la presentación cerrada sin pedir equipo', () => {
  const cerrada = option('50', { consumibleId: '7', lotStatus: 'bodega' });
  const app = movimiento([cerrada], '');
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }, { name: 'data-field-tipo', value: 'salida' }];
  app.button.fire('click');
  assert.equal(app.controls.lote_inventario_id.value, '50');
  assert.equal(app.controls.abrir_presentacion.value, '1');
  assert.equal(app.aviso.hidden, false);
  assert.equal(app.controls.equipo_id.required, false);
  assert.equal(app.controls.equipo_id.value, '');
});

test('poner en uso un insumo sin equipos compatibles no exige ni elige equipo', () => {
  const app = recepcion({ equipos: ['31'], requiere: '' });
  app.button.attributes = [{ name: 'data-field-registro_id', value: '90' }, { name: 'data-field-consumible_id', value: '7' },
    { name: 'data-field-cantidad_inicial', value: '1000.000' }, { name: 'data-field-estado', value: 'en_uso' }];
  app.button.fire('click');
  assert.equal(app.controls.equipo_en_uso_id.required, false);
  assert.equal(app.controls.equipo_en_uso_id.value, '');
});

test('con una presentación ya abierta el consumo la prefiere y no abre otra', () => {
  const cerrada = option('50', { consumibleId: '7', lotStatus: 'bodega' });
  const abierta = option('51', { consumibleId: '7', lotStatus: 'en_uso', equipmentId: '31' });
  const ajena = option('60', { consumibleId: '8', lotStatus: 'en_uso' });
  const app = movimiento([cerrada, abierta, ajena]);
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }, { name: 'data-field-tipo', value: 'salida' }];
  app.button.fire('click');
  assert.equal(app.controls.lote_inventario_id.value, '51');
  assert.equal(app.controls.abrir_presentacion.value, '');
  assert.equal(app.aviso.hidden, true);
  assert.equal(app.controls.equipo_id.required, false);
  assert.equal(app.controls.equipo_id.value, '31');
  assert.equal(ajena.disabled, true);
});

test('sin presentaciones con saldo la ayuda del lote dice que primero hay que recibir existencias', () => {
  const app = movimiento([]);
  app.button.attributes = [{ name: 'data-field-consumible_id', value: '7' }, { name: 'data-field-tipo', value: 'salida' }];
  app.button.fire('click');
  assert.match(app.ayuda.textContent, /Recibir existencias/);
  assert.equal(app.controls.lote_inventario_id.required, true);
});
