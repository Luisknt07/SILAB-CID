const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto, createHash } = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/verificacion_documental.js'), 'utf8');

async function verificar(contenido) {
  const hashes = ['original', 'aprobado'].map(x => createHash('sha256').update(x).digest('hex'));
  const salida = { textContent: '' };
  const button = { addEventListener(type, handler) { this.click = handler; } };
  const root = {
    dataset: { sha256: hashes[0], hashes: hashes.join(' ') },
    querySelector(selector) {
      if (selector === '[data-resultado-archivo]') return salida;
      if (selector === '[data-comprobar-archivo]') return button;
      return { files: [{ size: contenido.length,
        arrayBuffer: async () => new TextEncoder().encode(contenido).buffer }] };
    },
  };
  vm.runInNewContext(source, { document: { querySelector: () => root }, crypto: webcrypto });
  await button.click();
  return salida.textContent;
}

test('el mismo QR comprueba el original emitido y la copia con ambos responsables', async () => {
  for (const archivo of ['original', 'aprobado']) {
    assert.match(await verificar(archivo), /^El archivo coincide/);
  }
});

test('una alteración del PDF aprobado no se reconoce como copia válida', async () => {
  assert.match(await verificar('aprobado alterado'), /^El archivo no coincide/);
});
