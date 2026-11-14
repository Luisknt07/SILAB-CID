const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/unidades/expediente_sugerencias_compras.js'), 'utf8');

function control(value = '', options) {
  return {value, tagName: options ? 'SELECT' : 'INPUT', maxLength: 300,
    options: (options || []).map(value => ({value})), disabled: false, readOnly: false,
    matches() {return this.disabled;}, focus() {this.focused = true;}};
}
function button(index) {
  const handlers = new Map(), classes = new Set(), label = {textContent: 'Incorporar al plan'};
  return {dataset: {sugerenciaCompra: String(index)}, disabled: false,
    classList: {toggle(name, on) {if (on) classes.add(name); else classes.delete(name);}},
    querySelector: () => label, addEventListener(event, fn) {handlers.set(event, fn);},
    click() {handlers.get('click')?.();}, label, classes};
}
function fixture({tabla = 'compras', sugerencias, existentes = [], soloLectura = false, pacV2 = false, conResumen = false} = {}) {
  sugerencias ??= [{clave: 'equipo:11', categoria: 'equipos', item: 'Reemplazo de impresora 3D',
    motivo: 'Vida útil cumplida y reparación no viable.', prioridad: 'alta', codigo_equipo: 'FAB-IMP-001', referencia: '300.00'}];
  function row(values = {}) {
    const fields = {
      categoria: control(values.categoria || '', ['', 'equipos', 'insumos', 'mantenimiento']),
      item: control(values.item || ''), cantidad: control(values.cantidad || ''),
      justificacion: control(values.justificacion || ''),
      prioridad: control(values.prioridad || '', ['', 'alta', 'media', 'baja']),
      costo_unitario: control(values.costo_unitario || ''),
      fuente: control(values.fuente || '', ['', 'institucional', 'proyecto']),
    };
    const selectorEquipos = {options: [{value: 'eq-1', selected: false}, {value: 'eq-2', selected: false}]};
    if (pacV2) Object.assign(fields, {
      area_id: control('', ['', 'unidad', '2']),
      tipo_necesidad: control('', ['', 'reposicion', 'dotacion', 'otro']),
      mes_compra: control('', ['', ...Array.from({length: 12}, (_, i) => String(i + 1))]),
      equipos_referencia: control('[]'),
      clase_bien: control('', ['', 'equipos', 'software', 'materiales', 'insumos', 'reactivos', 'repuestos', 'servicios']),
      especificaciones: control(''), unidad_medida: control(''),
    });
    if (tabla === 'compras') fields.trimestre = control(values.trimestre || '', ['', '1', '2', '3', '4']);
    return {dataset: {}, fields, selectorEquipos, scrolled: false, scrollIntoView() {this.scrolled = true;},
      querySelector(selector) {
        if (pacV2 && selector === '[data-pac-equipos]') return selectorEquipos;
        const name = selector.match(/^\[name="([^"]+)"\]$/)?.[1];
        return name?.startsWith(tabla + '__') ? fields[name.slice(tabla.length + 2)] || null : null;
      }};
  }
  const plantilla = row(), rows = existentes.map(row), status = {textContent: ''};
  rows.push(plantilla);
  const table = {querySelectorAll: () => rows, querySelector: () => plantilla};
  const buttons = sugerencias.map((_, i) => button(i));
  const zone = {dataset: {sugerenciasCompras: tabla}, querySelector: () => status,
    querySelectorAll: () => buttons};
  const resumen = {querySelectorAll() {throw new Error('El resumen económico no es una tabla editable.');}};
  const box = {querySelector: selector => selector === 'table' && conResumen ? resumen : table, addEventListener() {}};
  const root = {dataset: {redaccionSoloLectura: String(soloLectura)},
    querySelector(selector) {
      return selector === '[data-sugerencias-compras]' ? zone
        : selector === `[data-tabla="${tabla}"]` ? box : null;
    }};
  const document = {getElementById: () => ({textContent: JSON.stringify(sugerencias)})};
  const reveladas = [];
  const window = {ExpedientePAC: {mostrarFila(caja, fila) {reveladas.push(fila);}}};
  vm.runInNewContext(source, {document, window});
  let changes = 0, blocked = false;
  const api = window.ExpedienteCompras.iniciar(root, {
    anadirFila() {const r = row(); rows.splice(rows.length - 1, 0, r); return r;},
    cambio() {changes++;}, bloqueado: () => blocked,
  });
  return {rows, plantilla, buttons, status, root, api, sugerencias, reveladas,
    get changes() {return changes;}, block() {blocked = true; api?.refrescar();}};
}

test('incorporar crea una fila editable y marca el borrador para su autosave habitual', () => {
  const f = fixture();
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  const fields = f.rows[0].fields;
  assert.equal(fields.categoria.value, 'equipos');
  assert.equal(fields.item.value, 'Reemplazo de impresora 3D');
  assert.equal(fields.cantidad.value, '1');
  assert.equal(fields.justificacion.value, f.sugerencias[0].motivo);
  assert.equal(fields.prioridad.value, 'alta');
  assert.equal(fields.costo_unitario.value, '');
  assert.equal(fields.fuente.value, '');
  assert.equal(fields.trimestre.value, '');
  assert.equal(fields.item.readOnly, false);
  assert.equal(f.changes, 1);
  assert.ok(fields.item.focused);
  assert.match(f.status.textContent, /incorporada al borrador/);
});

test('un resumen anterior a la matriz no recibe las filas incorporadas desde el diagnóstico', () => {
  const f = fixture({conResumen: true, pacV2: true});
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.changes, 1);
  assert.equal(f.rows[0].fields.item.value, 'Reemplazo de impresora 3D');
});

test('incorporar y reenfocar una sugerencia revela su propia clase sin cambiarla por la pestaña activa', () => {
  const f = fixture({pacV2: true, sugerencias: [{clave: 'reactivo:1', item: 'Reactivo de laboratorio',
    clase_bien: 'reactivos', area_id: '2', tipo_necesidad: 'dotacion', motivo: 'Sustento del reactivo.'}]});
  f.buttons[0].click();
  assert.equal(f.rows[0].fields.clase_bien.value, 'reactivos');
  assert.equal(f.reveladas[0], f.rows[0]);
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.reveladas[1], f.rows[0]);
  assert.equal(f.rows[0].fields.clase_bien.value, 'reactivos');
});

test('una referencia de área o proceso sin cantidad no inventa una unidad para comprar', () => {
  for (const metadatos of [{estado: 'por_verificar'}, {clave: 'referencia-area:2:ficha_area:5'},
                          {origen: 'ficha_area'}, {origen: 'etapa_proceso'}]) {
    const f = fixture({pacV2: true, sugerencias: [{item: 'Equipo por verificar', cantidad: '',
      clase_bien: 'equipos', area_id: '2', tipo_necesidad: 'dotacion', motivo: 'Referencia funcional.', ...metadatos}]});
    f.buttons[0].click();
    assert.equal(f.rows[0].fields.cantidad.value, '');
    assert.match(f.status.textContent, /completa la cantidad/);
  }
  const cuantificada = fixture({pacV2: true, sugerencias: [{item: 'Equipo por verificar', cantidad: '3',
    estado: 'por_verificar', clase_bien: 'equipos', motivo: 'Cantidad declarada expresamente.'}]});
  cuantificada.buttons[0].click();
  assert.equal(cuantificada.rows[0].fields.cantidad.value, '3');
  const individual = fixture({pacV2: true, sugerencias: [{item: 'Equipo individual', equipo_id: 11,
    clase_bien: 'equipos', motivo: 'Activo identificado.'}]});
  individual.buttons[0].click();
  assert.equal(individual.rows[0].fields.cantidad.value, '1');
});

test('un segundo clic no duplica ni sobrescribe cotización, fuente o programación ya escritas', () => {
  const f = fixture();
  f.buttons[0].click();
  f.rows[0].fields.costo_unitario.value = '650';
  f.rows[0].fields.fuente.value = 'proyecto';
  f.rows[0].fields.trimestre.value = '2';
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.changes, 1);
  assert.equal(f.rows[0].fields.costo_unitario.value, '650');
  assert.equal(f.rows[0].fields.fuente.value, 'proyecto');
  assert.equal(f.rows[0].fields.trimestre.value, '2');
  assert.equal(f.buttons[0].label.textContent, 'Ya incorporado');
  assert.match(f.status.textContent, /ya está incorporada/);
});

test('reconoce una fila guardada por el código del equipo sin depender de metadatos del navegador', () => {
  const f = fixture({existentes: [{item: 'Reemplazar IMPRESORA · fab-imp-001', cantidad: '2'}]});
  assert.equal(f.buttons[0].label.textContent, 'Ya incorporado');
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.changes, 0);
  assert.equal(f.rows[0].fields.cantidad.value, '2');
});

test('los códigos de equipos distintos no se confunden por prefijo', () => {
  const f = fixture({existentes: [{item: 'Reemplazar impresora · FAB-IMP-0010'}]});
  f.buttons[0].click();
  assert.equal(f.rows.length, 3);
  assert.equal(f.changes, 1);
});

test('las sugerencias se incorporan sólo al plan anual y no duplican compras en el semestre', () => {
  const f = fixture({tabla: 'inversion'});
  assert.equal(f.api, null);
  f.buttons[0].click();
  assert.equal(f.rows.length, 1);
  assert.equal(f.rows[0].fields.item.value, '');
  assert.equal(f.rows[0].fields.trimestre, undefined);
  assert.equal(f.rows[0].fields.fuente.value, '');
  assert.equal(f.changes, 0);
});

test('documento enviado y conflicto de versión impiden incorporar necesidades', () => {
  for (const soloLectura of [true, false]) {
    const f = fixture({soloLectura});
    if (!soloLectura) f.block();
    assert.equal(f.buttons[0].disabled, true);
    f.buttons[0].click();
    assert.equal(f.rows.length, 1);
    assert.equal(f.changes, 0);
    assert.match(f.status.textContent, /bloqueado para edición/);
  }
});

test('una tabla deshabilitada o de solo lectura conserva su contenido', () => {
  for (const key of ['disabled', 'readOnly']) {
    const f = fixture();
    f.plantilla.fields.item[key] = true;
    f.buttons[0].click();
    assert.equal(f.rows.length, 1);
    assert.equal(f.changes, 0);
    assert.match(f.status.textContent, /no está disponible para edición/);
  }
});

test('quitar una propuesta permite incorporarla nuevamente sin añadir códigos al nombre del bien', () => {
  const f = fixture();
  f.buttons[0].click();
  f.rows.splice(0, 1);
  f.api.refrescar();
  assert.equal(f.buttons[0].label.textContent, 'Incorporar al plan');
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.rows[0].fields.item.value, 'Reemplazo de impresora 3D');
});

test('una etiqueta larga respeta el límite sin añadir códigos al nombre del bien', () => {
  const f = fixture({sugerencias: [{clave: 'equipo:11', categoria: 'equipos',
    item: 'Impresora '.repeat(50), motivo: 'Necesidad registrada.', prioridad: 'alta', codigo_equipo: 'FAB-IMP-001', referencia: 300}]});
  f.buttons[0].click();
  assert.ok(f.rows[0].fields.item.value.length <= 300);
  assert.doesNotMatch(f.rows[0].fields.item.value, /FAB-IMP-001/);
});

test('sugerencias incompletas no agregan filas ni fabrican categorías o prioridades', () => {
  const f = fixture({sugerencias: [{item: '', codigo_equipo: 'FAB-IMP-001', referencia: 300},
    {item: 'Necesidad adicional', categoria: 'sin_catalogar', prioridad: 'urgente'}]});
  f.buttons[0].click();
  assert.equal(f.rows.length, 1);
  f.buttons[1].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.rows[0].fields.categoria.value, '');
  assert.equal(f.rows[0].fields.prioridad.value, '');
});

test('dos activos del mismo valor registrado mantienen sus códigos y propuestas independientes', () => {
  const f = fixture({sugerencias: [
    {clave: 'equipo:11', categoria: 'equipos', item: 'Impresora 3D (FAB-IMP-001)',
      codigo_equipo: 'FAB-IMP-001', referencia: '300.00', motivo: 'Obsolescencia.', prioridad: 'alta'},
    {clave: 'equipo:12', categoria: 'equipos', item: 'Impresora 3D (FAB-IMP-002)',
      codigo_equipo: 'FAB-IMP-002', referencia: '300.00', motivo: 'Falla no reparable.', prioridad: 'alta'},
  ]});
  f.buttons[0].click();
  f.buttons[1].click();
  assert.equal(f.rows.length, 3);
  assert.equal(f.changes, 2);
  assert.equal(f.rows[0].fields.item.value, 'Impresora 3D (FAB-IMP-001)');
  assert.equal(f.rows[1].fields.item.value, 'Impresora 3D (FAB-IMP-002)');
  for (const r of f.rows.slice(0, 2)) {
    assert.doesNotMatch(r.fields.item.value, /300/);
    assert.equal(r.fields.costo_unitario.value, '');
  }
});

test('un insumo sin código de equipo se identifica por clave e ítem, nunca por su referencia monetaria', () => {
  const f = fixture({sugerencias: [
    {clave: 'insumo:21', categoria: 'insumos', item: 'Resina transparente', referencia: null,
      motivo: 'Existencia agotada.', prioridad: 'alta'},
    {clave: 'insumo:22', categoria: 'insumos', item: 'Alcohol de limpieza', referencia: null,
      motivo: 'Stock insuficiente.', prioridad: 'media'},
  ]});
  f.buttons[0].click();
  f.buttons[1].click();
  f.buttons[0].click();
  assert.equal(f.rows.length, 3);
  assert.equal(f.changes, 2);
  assert.equal(f.rows[0].fields.item.value, 'Resina transparente');
  assert.equal(f.rows[1].fields.item.value, 'Alcohol de limpieza');
});

test('una propuesta por área conserva su diagnóstico y equipos autorizados sin inventar el mes', () => {
  const f = fixture({pacV2: true, sugerencias: [{clave: 'equipo:1', item: 'Reemplazar medidor',
    area_id: '2', tipo_necesidad: 'reposicion', equipos_referencia: ['eq-1', 'equipo-ajeno'],
    motivo: 'Falla documentada en el área de medición.', prioridad: 'alta'}]});
  f.buttons[0].click();
  const fila = f.rows[0];
  assert.equal(fila.fields.area_id.value, '2');
  assert.equal(fila.fields.tipo_necesidad.value, 'reposicion');
  assert.equal(fila.fields.justificacion.value, 'Falla documentada en el área de medición.');
  assert.deepEqual(JSON.parse(fila.fields.equipos_referencia.value), ['eq-1']);
  assert.equal(fila.selectorEquipos.options[0].selected, true);
  assert.equal(fila.selectorEquipos.options[1].selected, false);
  assert.equal(fila.fields.mes_compra.value, '');
});

test('una propuesta compartida respeta el contexto de toda la unidad en vez de atribuirla a un área', () => {
  const f = fixture({pacV2: true, sugerencias: [{item: 'Equipo de uso compartido', area_id: 2,
    area_clave: 'unidad', tipo_necesidad: 'dotacion', motivo: 'Atiende varias áreas.'}]});
  f.buttons[0].click();
  assert.equal(f.rows[0].fields.area_id.value, 'unidad');
  assert.equal(f.rows[0].fields.tipo_necesidad.value, 'dotacion');
});

test('nombre simple, especificaciones y licencia se incorporan en campos independientes', () => {
  const f = fixture({pacV2: true, sugerencias: [{clave: 'licencia:1', item: 'Licencia CAD',
    clase_bien: 'software', especificaciones: 'Vigencia de 12 meses, 10 usuarios.', unidad_medida: 'usuario/año',
    cantidad: '10', area_id: '2', tipo_necesidad: 'dotacion', motivo: 'Actualización requerida.'}]});
  f.buttons[0].click();
  const fields = f.rows[0].fields;
  assert.equal(fields.item.value, 'Licencia CAD');
  assert.equal(fields.clase_bien.value, 'software');
  assert.equal(fields.especificaciones.value, 'Vigencia de 12 meses, 10 usuarios.');
  assert.equal(fields.unidad_medida.value, 'usuario/año');
  assert.equal(fields.cantidad.value, '10');
});

test('una brecha sin bien identificado no se convierte en un nombre genérico de compra', () => {
  const f = fixture({pacV2: true, sugerencias: [{clave: 'brecha:2', item: '',
    requiere_nombre_bien: true, area_id: '2', tipo_necesidad: 'dotacion', motivo: 'Falta capacidad.'}]});
  assert.match(f.buttons[0].label.textContent, /Definir bien/);
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
  assert.equal(f.rows[0].fields.item.value, '');
  assert.equal(f.rows[0].fields.justificacion.value, 'Falta capacidad.');
  assert.ok(f.rows[0].fields.item.focused);
  f.buttons[0].click();
  assert.equal(f.rows.length, 2);
});

test('dos equipos iguales conservan propuestas separadas por su referencia real', () => {
  const f = fixture({pacV2: true, sugerencias: [
    {clave: 'equipo:1', item: 'Impresora 3D', codigo_equipo: 'FAB-IMP-001', equipos_referencia: ['eq-1'], area_id: '2'},
    {clave: 'equipo:2', item: 'Impresora 3D', codigo_equipo: 'FAB-IMP-002', equipos_referencia: ['eq-2'], area_id: '2'},
  ]});
  f.buttons[0].click(); f.buttons[1].click();
  assert.equal(f.rows.length, 3);
  assert.deepEqual(f.rows.slice(0, 2).map(r => r.fields.item.value), ['Impresora 3D', 'Impresora 3D']);
  assert.deepEqual(f.rows.slice(0, 2).map(r => JSON.parse(r.fields.equipos_referencia.value)), [['eq-1'], ['eq-2']]);
});
