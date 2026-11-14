const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const panel = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');
const wizard = fs.readFileSync(path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js'), 'utf8');
const appendSource = panel.slice(panel.indexOf('  function appendResource('), panel.indexOf('  const reservationDrawer ='));

function element(tagName) {
  return { tagName, children: [], attributes: {},
    append(...items) { this.children.push(...items); },
    setAttribute(name, value) { this.attributes[name] = value; } };
}

function resource(options) {
  const context = { document: { createElement: element } };
  vm.runInNewContext(appendSource + '\nthis.appendResource = appendResource;', context);
  const container = element('section');
  context.appendResource(container, options);
  return container.children[0].children[1].children[0];
}

test('archivo técnico privado usa el visor por extensión aunque la ruta no termine en .pdf', () => {
  const link = resource({ title: 'Plano del equipo', url: '/archivos-tecnicos/42/', archivo: true, extension: '.PDF' });
  assert.equal(link.attributes['data-ver-pdf'], '');
  assert.equal(link.attributes['data-pdf-descarga'], '/archivos-tecnicos/42/');
  assert.equal(link.attributes['data-pdf-titulo'], 'Plano del equipo');
  assert.equal(link.target, undefined);
});

test('archivo técnico sin visor descarga y el enlace web conserva su comportamiento', () => {
  const archive = resource({ title: 'Modelo CAD', url: '/archivos-tecnicos/43/', archivo: true, extension: 'step' });
  assert.equal(archive.attributes.download, '');
  assert.equal(archive.target, undefined);
  const web = resource({ title: 'Fabricante', url: 'https://example.test/producto/' });
  assert.equal(web.target, '_blank');
  assert.equal(web.attributes.download, undefined);
});

function manual(url) {
  const source = wizard.slice(wizard.indexOf('      const manualIsPdf ='), wizard.indexOf('      openResourceSheet({', wizard.indexOf('      const manualIsPdf =')));
  const context = { equipment: { manual_url: url, equipo_nombre: 'Equipo 1' }, escapeHtml: value => String(value),
    window: { interfaz: { html: (parts, ...values) => parts.reduce((all, part, index) => all + part + (values[index] ?? ''), '') } } };
  vm.runInNewContext(source + '\nthis.files = files;', context);
  return context.files[0];
}

test('manual adjunto abre el visor y otro formato descarga sin crear pestañas', () => {
  const pdf = manual('/media/manual.PDF?firma=123');
  assert.match(pdf, /data-ver-pdf/);
  assert.match(pdf, /data-pdf-descarga="\/media\/manual.PDF\?firma=123"/);
  assert.doesNotMatch(pdf, /target=|>PDF /);
  const other = manual('/media/manual.docx');
  assert.match(other, / download>/);
  assert.match(other, /Descargar manual/);
  assert.doesNotMatch(other, /target=|data-ver-pdf/);
});
