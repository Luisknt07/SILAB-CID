/* Progressive editor; the server validates the only submitted JSON payload. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-calendario-widget]').forEach(widget => {
    const raw = widget.querySelector('textarea');
    const editor = widget.querySelector('[data-calendario-editor]');
    const strings = widget.dataset;
    if (raw.hasAttribute('data-payload-rechazado')) return;
    let data;
    try {
      data = JSON.parse(raw.value);
      const rowKeys = ['ciclos', 'ciclos_historicos', 'ambitos', 'ambitos_historicos'];
      const keys = [...rowKeys, 'ambitos_operacion', 'ambito_predeterminado',
        'semanas_minimas', 'semanas_maximas', 'semanas_predeterminadas'];
      if (!data || typeof data !== 'object' || Array.isArray(data) || raw.value.length > 100000 ||
          Object.keys(data).some(k => !keys.includes(k))) return;
      for (const key of rowKeys) {
        const columns = key.startsWith('ciclos') ? 3 : 2;
        if (!Array.isArray(data[key]) || data[key].length > (columns === 3 ? 36 : 200) ||
            data[key].some(row => !Array.isArray(row) || row.length !== columns ||
              row.some(v => typeof v !== 'string'))) return;
      }
      if (!Array.isArray(data.ambitos_operacion) || data.ambitos_operacion.some(v => typeof v !== 'string') ||
          typeof data.ambito_predeterminado !== 'string' ||
          ['semanas_minimas', 'semanas_maximas', 'semanas_predeterminadas'].some(k => !Number.isInteger(data[k]))) return;
    } catch (_) { return; }
    let rawEdited = false;
    raw.addEventListener('input', () => { rawEdited = true; editor.hidden = true; });
    const sync = () => { if (!rawEdited) raw.value = JSON.stringify(data, null, 2); };
    const element = (tag, text) => {
      const node = document.createElement(tag);
      if (text) node.textContent = text;
      return node;
    };
    const button = (text, action) => {
      const node = element('button', text);
      node.type = 'button'; node.addEventListener('click', action);
      return node;
    };
    const field = (label, input) => {
      const container = element('div'); const title = element('label', label);
      title.append(input); container.append(title); return container;
    };
    const render = () => {
      editor.replaceChildren();
      for (const [key, label] of [['ciclos', strings.activeCycles], ['ciclos_historicos', strings.historyCycles],
        ['ambitos', strings.activeScopes], ['ambitos_historicos', strings.historyScopes]]) {
        const group = element('fieldset'); group.append(element('legend', label));
        data[key].forEach((row, index) => {
          const container = element('div'); container.className = 'catalogo-fila';
          for (const [column, title] of [[0, strings.code], [1, strings.name]]) {
            const input = element('input'); input.type = 'text'; input.value = row[column];
            input.maxLength = column === 0 ? (key.startsWith('ciclos') ? 1 : 30) : 250;
            input.addEventListener('input', () => {
              const previous = row[column]; row[column] = input.value;
              if (key === 'ambitos' && column === 0) {
                data.ambitos_operacion = data.ambitos_operacion.map(c => c === previous ? input.value : c);
                if (data.ambito_predeterminado === previous) data.ambito_predeterminado = input.value;
              }
              if (key === 'ambitos') updateDefault();
              sync();
            });
            container.append(field(title, input));
          }
          if (key.startsWith('ciclos')) {
            const select = element('select');
            for (const [code, name] of [['ordinario', strings.ordinary], ['extraordinario', strings.extra], ['interperiodo', strings.inter]]) {
              select.add(new Option(name, code));
            }
            select.value = row[2]; select.addEventListener('change', () => { row[2] = select.value; sync(); });
            container.append(field(strings.type, select));
          } else if (key === 'ambitos') {
            const input = element('input'); input.type = 'checkbox'; input.checked = data.ambitos_operacion.includes(row[0]);
            input.addEventListener('change', () => {
              data.ambitos_operacion = data.ambitos_operacion.filter(c => c !== row[0]);
              if (input.checked) data.ambitos_operacion.push(row[0]); sync();
            });
            container.append(field(strings.operation, input));
          }
          const actions = element('div'); actions.className = 'catalogo-fila-acciones';
          actions.append(button(strings.remove, () => { data[key].splice(index, 1); sync(); render(); }));
          if (!key.endsWith('_historicos')) actions.append(button(strings.retire, () => {
            data[key + '_historicos'].push(row); data[key].splice(index, 1);
            if (key === 'ambitos') data.ambitos_operacion = data.ambitos_operacion.filter(c => c !== row[0]);
            sync(); render();
          }));
          container.append(actions); group.append(container);
        });
        group.append(button(strings.add, () => { data[key].push(key.startsWith('ciclos') ? ['', '', 'ordinario'] : ['', '']); sync(); render(); }));
        editor.append(group);
      }
      defaultSelect = element('select'); updateDefault();
      defaultSelect.addEventListener('change', () => { data.ambito_predeterminado = defaultSelect.value; sync(); });
      editor.append(field(strings.default, defaultSelect));
      for (const [key, title] of [['semanas_minimas', strings.min], ['semanas_maximas', strings.max], ['semanas_predeterminadas', strings.weeks]]) {
        const input = element('input'); input.type = 'number'; input.min = '1'; input.max = '24'; input.step = '1'; input.value = data[key];
        input.addEventListener('input', () => { data[key] = input.value === '' ? null : Number(input.value); sync(); });
        editor.append(field(title, input));
      }
    };
    let defaultSelect;
    const updateDefault = () => {
      if (!defaultSelect) return;
      defaultSelect.replaceChildren(new Option('—', ''));
      for (const [code, name] of data.ambitos) defaultSelect.add(new Option(name || code || '—', code));
      defaultSelect.value = data.ambito_predeterminado;
    };
    render(); editor.hidden = false; widget.querySelector('[data-calendario-json]').open = false;
    widget.closest('form').addEventListener('submit', sync);
  });
});
