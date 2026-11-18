// Los filtros de la tabla de anexos con los documentos generados dentro de cada categoría temática.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/components/filtros_metas.js'), 'utf8');

function encabezado(titulo) {
  return { titulo, hidden: false, dataset: {}, classList: { contains: clase => clase === 'cierre-grupo' },
    matches: () => false };
}

// Un cuerpo de la tabla: un anexo (con su meta) o un documento generado (estado «neutro»).
function bloque(nombre, exigencia, estado, texto = '') {
  const fila = { dataset: { metaEstado: estado, metaCodigo: '' }, textContent: `${nombre} ${texto}` };
  return { nombre, hidden: false, dataset: { metaExigencia: exigencia }, textContent: fila.textContent,
    classList: { contains: () => false },
    matches: selector => selector === '[data-meta-bloque]',
    querySelector: selector => (selector === '.cierre-evidencia-nombre' ? { textContent: nombre } : null),
    querySelectorAll: () => [fila] };
}

function montar() {
  const cuerpos = [
    encabezado('Uso, equipamiento e inventario'),
    bloque('Registro de uso', 'obligatorio', 'cumple'),
    bloque('Calibración de equipos', 'respaldo', 'neutro', 'Respaldo para auditoría 6 equipos con calibración'),
    encabezado('Personal, formación y difusión'),
    bloque('Personal de la unidad', 'respaldo', 'neutro', 'Respaldo para auditoría 4 personas'),
    encabezado('Seguimiento y mejora'),
    bloque('Auditoría y trazabilidad', 'gestion', 'neutro', 'Consulta de gestión Se genera al consultar'),
  ];
  const controles = { buscar: { value: '' }, estado: { value: '' }, exigencia: { value: '' } };
  const conteo = { textContent: '' };
  const tabla = { tBodies: cuerpos, querySelectorAll: () => cuerpos.filter(c => c.matches('[data-meta-bloque]')) };
  const seccion = {
    matches: () => true,
    querySelector: selector => ({
      '[data-cierre-evidencias]': tabla, '[data-metas-buscar]': controles.buscar,
      '[data-metas-estado]': controles.estado, '[data-metas-exigencia]': controles.exigencia,
      '[data-metas-conteo]': conteo, '[data-metas-vacio]': { hidden: true },
    })[selector] || null,
    querySelectorAll: () => [],
  };
  const oyentes = {};
  const document = {
    readyState: 'complete', documentElement: {},
    addEventListener: (tipo, funcion) => { oyentes[tipo] = funcion; },
    querySelectorAll: () => [seccion],
  };
  class MutationObserver { observe() {} }
  vm.runInNewContext(source, { window: {}, document, MutationObserver, Node: { ELEMENT_NODE: 1 } });
  const filtrar = (cambios) => {
    Object.entries(cambios).forEach(([clave, valor]) => { controles[clave].value = valor; });
    oyentes.input({ target: { matches: () => true, closest: () => seccion } });
  };
  const visibles = () => cuerpos.filter(c => !c.hidden).map(c => c.titulo || c.nombre);
  return { filtrar, visibles, conteo };
}

test('sin filtros se ven todas las categorías con sus documentos generados', () => {
  const tabla = montar();
  assert.equal(tabla.visibles().length, 7);
  assert.equal(tabla.conteo.textContent, '4 de 4 documentos y actividades');
});

test('el buscador encuentra un documento generado por su nombre y oculta las categorías vacías', () => {
  const tabla = montar();
  tabla.filtrar({ buscar: 'personal' });
  assert.deepEqual(tabla.visibles(), ['Personal, formación y difusión', 'Personal de la unidad']);
});

test('el filtro de exigencia incluye los documentos bajo su etiqueta nueva', () => {
  const tabla = montar();
  tabla.filtrar({ exigencia: 'respaldo' });
  assert.deepEqual(tabla.visibles(), ['Uso, equipamiento e inventario', 'Calibración de equipos',
    'Personal, formación y difusión', 'Personal de la unidad']);
  tabla.filtrar({ exigencia: 'gestion' });
  assert.deepEqual(tabla.visibles(), ['Seguimiento y mejora', 'Auditoría y trazabilidad']);
});

test('un encabezado con un anexo visible se conserva aunque su documento generado no coincida', () => {
  const tabla = montar();
  tabla.filtrar({ exigencia: '', estado: 'cumple' });
  assert.deepEqual(tabla.visibles(), ['Uso, equipamiento e inventario', 'Registro de uso']);
});
