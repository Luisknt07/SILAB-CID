/* Progressive editor: one validated JSON payload; no markup from user data. */
(() => {
  'use strict';
  const initialize = () => document.querySelectorAll('[data-level-editor]').forEach(editor => {
    const raw = editor.querySelector('textarea');
    let data;
    try {
      if (raw.value.length > 100000) return;
      data = JSON.parse(raw.value);
      const keys = ['niveles', 'historicos', 'estudiantes', 'secuencias', 'etiqueta_faltante'];
      if (!data || typeof data !== 'object' || Array.isArray(data) || Object.keys(data).some(k => !keys.includes(k))) return;
      if (!['niveles', 'historicos'].every(k => Array.isArray(data[k]) && data[k].length <= 200 && data[k].every(r => Array.isArray(r) && r.length === 2 && r.every(v => typeof v === 'string')))) return;
      if (!Array.isArray(data.estudiantes) || data.estudiantes.length > 200 || !data.estudiantes.every(v => typeof v === 'string')) return;
      if (!Array.isArray(data.secuencias) || data.secuencias.length > 200 || !data.secuencias.every(r => Array.isArray(r) && r.length <= 200 && r.every(v => typeof v === 'string'))) return;
      if (typeof data.etiqueta_faltante !== 'string') return;
    } catch (_) { return; }
    const active = editor.querySelector('[data-levels]');
    const history = editor.querySelector('[data-history]');
    const routes = editor.querySelector('[data-routes]');
    const missing = editor.querySelector('[data-missing]');
    missing.value = data.etiqueta_faltante;
    const node = (tag, cls = '') => { const el = document.createElement(tag); el.className = cls; return el; };
    const button = (text, action) => { const el = node('button'); el.type = 'button'; el.textContent = text; el.addEventListener('click', action); return el; };
    const pair = row => [...row.querySelectorAll('input[type=text]')].map(input => input.value);
    const studentCodes = () => [...active.children].filter(r => r.querySelector('[type=checkbox]').checked).map(r => pair(r)[0]);
    const refresh = () => {
      const codes = studentCodes();
      routes.querySelectorAll('select').forEach(select => {
        const selected = select.value;
        select.replaceChildren(new Option(editor.dataset.choice, ''));
        [...active.children].forEach(row => {
          const [code, label] = pair(row);
          if (codes.includes(code)) select.add(new Option(`${label || code} (${code})`, code));
        });
        if (selected && !codes.includes(selected)) select.add(new Option(selected, selected));
        select.value = selected;
      });
    };
    const sync = () => {
      data = {niveles: [...active.children].map(pair), historicos: [...history.children].map(pair),
        estudiantes: studentCodes(), secuencias: [...routes.children].map(route => [...route.querySelectorAll('select')].map(s => s.value)),
        etiqueta_faltante: missing.value};
      raw.value = JSON.stringify(data);
      editor.querySelector('[data-add-level]').disabled = active.children.length >= 200;
      editor.querySelector('[data-add-history]').disabled = history.children.length >= 200;
      editor.querySelector('[data-add-route]').disabled = routes.children.length >= 200;
    };
    const addRow = (container, values, student = false) => {
      if (container.children.length >= 200) return;
      const row = node('div', 'catalogo-fila');
      [editor.dataset.code, editor.dataset.label].forEach((caption, index) => {
        const wrapper = node('div'); const label = node('label'); const input = node('input');
        input.type = 'text'; input.maxLength = index === 0 ? 30 : 250; input.value = values[index];
        label.textContent = caption; label.append(input); wrapper.append(label); row.append(wrapper);
      });
      const actions = node('div', 'catalogo-fila-acciones');
      if (container === active) {
        const label = node('label'); const checkbox = node('input'); checkbox.type = 'checkbox'; checkbox.checked = student;
        label.append(checkbox, document.createTextNode(editor.dataset.student)); row.append(label);
        actions.append(button(editor.dataset.retire, () => {
          if (history.children.length >= 200) return;
          const code = pair(row)[0]; addRow(history, pair(row)); row.remove();
          routes.querySelectorAll('select').forEach(select => { if (select.value === code) select.closest('.nivel-ruta-paso').remove(); });
          [...routes.children].forEach(route => { if (route.querySelectorAll('select').length < 2) route.remove(); });
          refresh(); sync();
        }));
      }
      actions.append(button(editor.dataset.remove, () => { row.remove(); refresh(); sync(); }));
      row.append(actions); container.append(row);
    };
    const addStep = (route, value) => {
      if (route.querySelectorAll('select').length >= 200) return;
      const step = node('div', 'nivel-ruta-paso'); const label = node('label'); const select = node('select');
      label.textContent = editor.dataset.step; label.append(select);
      select.add(new Option(value, value)); step.append(label, button(editor.dataset.remove, () => { step.remove(); sync(); }));
      route.querySelector('[data-steps]').append(step);
    };
    const addRoute = values => {
      if (routes.children.length >= 200) return;
      const route = node('div', 'nivel-ruta'); const steps = node('div'); steps.dataset.steps = '';
      route.append(steps, button(editor.dataset.step + ' +', () => { addStep(route, ''); refresh(); sync(); }),
        button(editor.dataset.remove, () => { route.remove(); sync(); }));
      routes.append(route); values.forEach(value => addStep(route, value));
    };
    data.niveles.forEach(values => addRow(active, values, data.estudiantes.includes(values[0])));
    data.historicos.forEach(values => addRow(history, values)); data.secuencias.forEach(addRoute);
    editor.querySelector('[data-add-level]').addEventListener('click', () => { addRow(active, ['', '']); sync(); });
    editor.querySelector('[data-add-history]').addEventListener('click', () => { addRow(history, ['', '']); sync(); });
    editor.querySelector('[data-add-route]').addEventListener('click', () => { addRoute(['', '']); refresh(); sync(); });
    editor.addEventListener('input', () => { refresh(); sync(); });
    editor.addEventListener('change', () => { refresh(); sync(); });
    editor.closest('form').addEventListener('submit', sync);
    refresh(); sync(); raw.hidden = true; editor.querySelector('[data-guided]').hidden = false;
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize); else initialize();
})();
