/* Cálculos educativos puros; sin persistencia, red ni control de equipos. */
(function (root) {
  'use strict';
  function number(value, name, min, max) {
    if (value === '' || value === null || value === undefined) throw new Error('Completa ' + name + '.');
    const n = Number(value);
    if (!Number.isFinite(n) || n < min || n > max) throw new Error('Revisa ' + name + ' (' + min + ' a ' + max + ').');
    return n;
  }
  function calcular(p) {
    if (!['lavado', 'honey', 'natural'].includes(p.ruta)) throw new Error('Selecciona una ruta válida.');
    const cereza = number(p.cereza, 'cereza', .001, 1e7);
    const seco = cereza * number(p.beneficio, 'rendimiento de beneficio', .001, 100) / 100;
    const verde = seco * number(p.trilla, 'rendimiento de trilla', .001, 100) / 100;
    const tostado = verde * (1 - number(p.perdida, 'pérdida de tueste', 0, 99.999) / 100);
    const empacado = tostado * number(p.empaque, 'rendimiento de empaque', .001, 100) / 100;
    const gramos = number(p.gramos, 'gramos por bolsa', 1, 1e6);
    const unidades = empacado * 1000 / gramos;
    // Corrige sólo ruido binario próximo a un entero, nunca redondea bolsas parciales.
    const bolsas = Math.floor(unidades + Number.EPSILON * Math.max(1, unidades) * 4);
    const remanente = Math.max(0, empacado - bolsas * gramos / 1000);
    const costo = number(p.costo, 'costo del lote', 0, 1e7);
    const masaHumeda = number(p.masaHumeda, 'masa húmeda', .001, 1e7);
    const hi = number(p.humedadInicial, 'humedad inicial', .001, 99.999) / 100;
    const hf = number(p.humedadFinal, 'humedad final', 0, 99.999) / 100;
    if (hf >= hi) throw new Error('La humedad final debe ser menor que la inicial para este cálculo de secado.');
    const masaSeca = masaHumeda * (1 - hi) / (1 - hf);
    return {cereza, seco, verde, tostado, empacado, bolsas, remanente,
      costoKg: costo / empacado, costoBolsa: costo / empacado * gramos / 1000,
      masaSeca, agua: masaHumeda - masaSeca};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {calcular};
  root.CafeCalculadora = {calcular};
  if (typeof document === 'undefined') return;
  const form = document.getElementById('cafe-calculadora');
  if (!form) return;
  const format = n => new Intl.NumberFormat('es-EC', {maximumFractionDigits: 3}).format(n);
  function card(label, value, unit) {
    const a = document.createElement('article'), s = document.createElement('span'), b = document.createElement('strong');
    s.textContent = label; b.textContent = format(value) + (unit ? ' ' + unit : ''); a.append(s, b); return a;
  }
  function update() {
    const error = document.getElementById('cafe-error');
    try {
      const p = Object.fromEntries(new FormData(form)), r = calcular(p);
      const flow = document.getElementById('cafe-flujo'), results = document.getElementById('cafe-resultados'), bars = document.getElementById('cafe-barras');
      flow.replaceChildren(); results.replaceChildren(); bars.replaceChildren();
      const stages = [['Cereza', r.cereza], [p.ruta === 'natural' ? 'Fruto seco' : 'Pergamino seco', r.seco], ['Verde aceptado', r.verde], ['Tostado', r.tostado], ['Para empaque', r.empacado]];
      stages.forEach(([label, value]) => {
        flow.append(card(label, value, 'kg'));
        const row = document.createElement('div'), text = document.createElement('span'), bar = document.createElement('i');
        row.className = 'bar'; text.textContent = label + ': ' + format(value) + ' kg';
        bar.style.width = (value / r.cereza * 100) + '%'; bar.setAttribute('aria-hidden', 'true'); row.append(text, bar); bars.append(row);
      });
      [['Bolsas completas', r.bolsas, ''], ['Remanente', r.remanente, 'kg'], ['Costo por kg', r.costoKg, 'USD'], ['Costo por bolsa', r.costoBolsa, 'USD'], ['Masa final del secado', r.masaSeca, 'kg'], ['Agua retirada', r.agua, 'kg']].forEach(x => results.append(card(...x)));
      error.hidden = true;
    } catch (e) {
      error.textContent = e.message; error.hidden = false;
      ['cafe-flujo', 'cafe-resultados', 'cafe-barras'].forEach(id => document.getElementById(id).replaceChildren());
    }
  }
  form.addEventListener('submit', e => {e.preventDefault(); update();});
  form.addEventListener('reset', () => setTimeout(update, 0));
  form.elements.ruta.addEventListener('change', () => {
    const natural = form.elements.ruta.value === 'natural';
    form.elements.beneficio.value = natural ? 40 : 20; form.elements.trilla.value = natural ? 40 : 80; update();
  });
  update();
})(typeof globalThis !== 'undefined' ? globalThis : this);
