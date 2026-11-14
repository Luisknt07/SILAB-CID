const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/unidades/expediente_editor.js'), 'utf8');
const inicio = source.indexOf('  function refrescarCronograma()');
const fin = source.indexOf('  // --- avance:', inicio);
assert.ok(inicio >= 0 && fin > inicio);

function elemento() {
  return { children: [], appendChild(hijo) { this.children.push(hijo); } };
}
function fila(nombre, meses, { propia = false, excluida = false, nombreReporte = '' } = {}) {
  return {
    hasAttribute() { return false; },
    querySelector(selector) {
      if (selector === '[data-plan-exigencia]' && excluida) return { value: 'no_aplica' };
      if (selector === '[data-otra-nombre]') return propia ? { value: nombre } : null;
      if (selector === '[data-plan-nombre]' && nombreReporte) return {textContent:nombreReporte};
      if (selector === 'strong') return { textContent: nombre };
      return null;
    },
    querySelectorAll() {
      return meses.map((checked) => propia
        ? { matches: () => true, checked }
        : { matches: () => false, dataset: { planProgramado: String(checked) } });
    },
  };
}
function dibujar(filas) {
  const cuerpo = elemento();
  const tabla = {
    querySelector: () => cuerpo,
    querySelectorAll: () => Array.from({ length: 4 }, elemento),
  };
  const contexto = {
    raiz: { querySelector: () => tabla },
    plan: { querySelectorAll: () => filas },
    document: { createElement: elemento },
  };
  vm.runInNewContext(source.slice(inicio, fin) + '\nrefrescarCronograma();', contexto);
  return cuerpo.children;
}

test('el cronograma combina meses automáticos reales y actividades propias sin falsear sus marcas', () => {
  const filas = dibujar([
    fila('Prácticas', [true, false, true]),
    fila('Visita propia', [false, true, false], { propia: true }),
  ]);
  assert.deepEqual(filas.map((tr) => tr.children[0].textContent), ['Prácticas', 'Visita propia']);
  assert.deepEqual(filas.map((tr) => tr.children.slice(1).map((td) => td.className === 'is-on')),
    [[true, false, true], [false, true, false]]);
});

test('sin actividades aplicables no crea meses ni ejecución ficticios', () => {
  const filas = dibujar([fila('No programada', [true, true, true], { excluida: true })]);
  assert.equal(filas.length, 1);
  assert.equal(filas[0].children[0].className, 'is-empty');
  assert.equal(filas[0].children[0].colSpan, 4);
  assert.match(filas[0].children[0].textContent, /cronograma se completa automáticamente/);
});

test('el cronograma usa el nombre del reporte y no el texto de obligatoriedad', () => {
  const filas = dibujar([fila('Obligatoria institucional', [true, false, true],
    {nombreReporte:'FT02 · Planificación de uso de laboratorios'})]);
  assert.equal(filas[0].children[0].textContent, 'FT02 · Planificación de uso de laboratorios');
});

test('una nueva actividad propia conserva los meses predeterminados del tramo al clonar', () => {
  const controles = [
    { type: 'checkbox', dataset: { planDefault: 'true' }, checked: false },
    { type: 'checkbox', dataset: {}, checked: true },
    { type: 'text', dataset: {}, value: 'Actividad anterior' },
  ];
  const nueva = { removeAttribute() {}, querySelectorAll: () => controles };
  const plantilla = { cloneNode: () => nueva, parentElement: { insertBefore() {} } };
  const contexto = { prepararFila() {}, renumerarOtras() {} };
  const desde = source.indexOf('  function clonarFila(tabla)');
  const hasta = source.indexOf("  raiz.querySelectorAll('[data-tabla]')", desde);
  assert.ok(desde >= 0 && hasta > desde);
  vm.runInNewContext(source.slice(desde, hasta), contexto);
  contexto.clonarFila({ querySelector: () => plantilla });
  assert.equal(controles[0].checked, true);
  assert.equal(controles[1].checked, false);
  assert.equal(controles[2].value, '');
});

test('renumerar filas mantiene el marcador de meses junto con la selección de su actividad', () => {
  const meses = [{ name: 'viejo0' }, { name: 'viejo1' }];
  const presentes = [{ name: 'viejo0', value: '' }, { name: 'viejo1', value: '' }];
  const filas = meses.map((mes, i) => ({ dataset: {},
    querySelectorAll: () => [mes], querySelector: () => presentes[i] }));
  const contexto = { raiz: { querySelector: () => ({ querySelectorAll: () => filas }) } };
  const desde = source.indexOf('  function renumerarOtras()');
  const hasta = source.indexOf("  const plan = raiz.querySelector('[data-plan]')", desde);
  assert.ok(desde >= 0 && hasta > desde);
  vm.runInNewContext(source.slice(desde, hasta), contexto);
  contexto.renumerarOtras();
  assert.deepEqual(meses.map((mes) => mes.name), ['otra__meses__0', 'otra__meses__1']);
  assert.deepEqual(presentes.map((marcador) => marcador.name),
    ['otra__meses_presentes__0', 'otra__meses_presentes__1']);
  assert.ok(presentes.every((marcador) => marcador.value === '1'));
});
