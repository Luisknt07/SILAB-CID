(function () {
  'use strict';
  const tr = value => typeof gettext === 'function' ? gettext(value) : value;
  const FIELDS = [
    ['documento', 'Cédula / documento', 'text', 40], ['nombre', 'Nombres completos', 'text', 150],
    ['rol', 'Rol', 'select', 20], ['telefono', 'Celular', 'tel', 30], ['correo', 'Correo', 'email', 254],
  ];
  const ROLES = [['', 'Seleccionar'], ['estudiante', 'Estudiante'], ['docente', 'Profesor'], ['administrativo', 'Administrativo'], ['otro', 'Otro']];

  function visitWritingModels(purpose, context) {
    const unit = context.unit || tr('esta unidad');
    const group = context.institution || tr('Nuestro grupo');
    const size = Number(context.people) > 0 ? `${context.people} ${Number(context.people) === 1 ? tr('visitante') : tr('visitantes')}` : tr('el grupo participante');
    const topics = (context.topics || []).slice(0, 3).join(', ') || tr('las capacidades y el trabajo de la unidad');
    const opening = `${group} solicita una visita a ${unit}, con ${size}.`;
    const ending = tr('El recorrido y las demostraciones se coordinarán con el equipo de la unidad, según las áreas autorizadas y sus condiciones de atención.');
    const models = {
      academica: [
        ['aprendizaje', 'Aprendizaje y formación', `${opening} El propósito es complementar nuestra formación mediante una presentación guiada sobre ${topics}. Queremos comprender cómo se relacionan estos temas con aplicaciones reales, conocer los procesos de trabajo y plantear preguntas al personal responsable. Utilizaremos lo aprendido para fortalecer nuestras actividades académicas y compartir las principales conclusiones con el grupo. ${ending}`],
        ['orientacion', 'Orientación y acercamiento a la unidad', `${opening} Nos interesa conocer ${topics}, identificar oportunidades de aprendizaje y comprender qué actividades se desarrollan en la unidad. Solicitamos una explicación introductoria adecuada al grupo, con espacio para preguntas sobre formación, recursos y posibles actividades académicas futuras. ${ending}`],
      ],
      institucional: [
        ['cooperacion', 'Cooperación entre instituciones', `${opening} Buscamos conocer ${topics} e identificar posibles puntos de colaboración institucional. Nos interesa intercambiar experiencias con el equipo responsable, comprender las capacidades disponibles y conversar sobre actividades conjuntas de formación, investigación o vinculación que puedan evaluarse posteriormente. ${ending}`],
        ['intercambio', 'Intercambio de experiencias', `${opening} El objetivo es conocer la organización del trabajo y las experiencias relacionadas con ${topics}. Queremos dialogar sobre buenas prácticas, procesos y aprendizajes que puedan orientar mejoras en nuestras instituciones. La visita servirá para documentar los temas de interés y acordar posibles acciones de seguimiento. ${ending}`],
      ],
      comercial: [
        ['servicios', 'Conocer capacidades y servicios', `${opening} Queremos conocer ${topics} y comprender qué servicios o apoyos podrían responder a nuestras necesidades. Solicitamos una presentación de las capacidades disponibles y orientación sobre el proceso para plantear un requerimiento técnico, definir su alcance y solicitar una evaluación o cotización posterior. ${ending}`],
        ['necesidades', 'Explorar una necesidad de la organización', `${opening} Nos interesa conversar con el equipo sobre una necesidad de nuestra organización relacionada con ${topics}. Buscamos comprender las posibilidades de apoyo, la información que debemos preparar y los pasos para evaluar una futura solicitud de servicio. En la visita presentaremos el contexto de la necesidad y resolveremos dudas generales. ${ending}`],
      ],
    };
    return (models[purpose] || models.academica).map(([id, label, text]) => ({ id, label: tr(label), text }));
  }

  window.createVisitGroupEditor = function (form) {
    const group = form.querySelector('#visitaDatosReserva');
    const body = group.querySelector('[data-visit-attendees-body]');
    const add = group.querySelector('[data-add-visit-attendee]');
    const modelSelect = group.querySelector('[data-visit-template]');
    const description = form.elements.visita_descripcion;
    const people = form.elements.visita_personas;
    const mode = form.elements.visita_conteo;
    const json = form.elements.visita_asistentes_json;
    const category = form.elements.visita_categoria;
    const userIds = form.elements.visita_usuarios_json;
    const authenticated = group.dataset.authenticated === 'true';
    const internalAccount = group.dataset.internalAccount === 'true';
    const internalSearch = group.querySelector('[data-visit-internal-search]');
    const userSearch = group.querySelector('[data-visit-user-search]');
    const userResults = group.querySelector('[data-visit-user-results]');
    const userStatus = group.querySelector('[data-visit-user-status]');
    const savedGroups = new Map();
    let previousCategory = category.value;
    let searchVersion = 0;
    let searchTimer;
    let lastAutoText = null;
    let selectedPurpose = '';
    let models = [];
    let topics = [];
    try { topics = JSON.parse(document.getElementById('visitaTemasReserva')?.textContent || '[]'); } catch (_) { /* Usa el contexto general de la unidad. */ }
    function active() { return document.getElementById('tipoSolicitudReserva')?.value === 'visita'; }
    function internal() { return category.value === 'interna'; }
    function syncIdentity() {
      category.querySelector('[value="interna"]').disabled = authenticated && !internalAccount;
      group.querySelectorAll('[data-visit-category]').forEach(button => {
        const selected = button.dataset.visitCategory === category.value;
        button.setAttribute('aria-pressed', String(selected));
        button.disabled = !active() || (button.dataset.visitCategory === 'interna' && authenticated && !internalAccount);
        button.querySelector('[data-visit-category-state]').textContent = selected ? tr('Seleccionada') : tr('Elegir');
      });
      const countHelp = group.querySelector('[data-visit-count-mode-help]');
      if (countHelp) countHelp.textContent = internal()
        ? tr('Se calcula con los usuarios que añadas desde la búsqueda institucional.')
        : tr('Completa la tabla o elige una cantidad estimada si aún no conoces los nombres.');
      const guest = !authenticated && !internal();
      group.querySelector('[data-visit-guest]').hidden = !guest;
      group.querySelectorAll('[data-visit-guest] input').forEach(input => {
        input.disabled = !active() || !guest;
        input.required = guest;
      });
      group.querySelector('[data-visit-login]').hidden = authenticated || !internal();
      internalSearch.hidden = !internal();
      userSearch.disabled = !active() || !internal() || !authenticated;
      add.hidden = internal();
      mode.disabled = !active() || internal();
      if (internal()) mode.value = 'lista';
      const submit = document.getElementById('btnEnviarReserva');
      if (submit) submit.disabled = !authenticated && !(active() && guest);
    }
    function rows() {
      return Array.from(body.children, row => Object.fromEntries(FIELDS.map(([key]) => [key, row.querySelector(`[data-attendee-field="${key}"]`).value.trim()])));
    }
    function occupiedRows() { return rows().filter(row => Object.values(row).some(Boolean)); }
    function refreshModels(force = false) {
      const purpose = form.elements.visita_proposito.value;
      const previous = modelSelect.value;
      models = visitWritingModels(purpose, {
        unit: group.dataset.unitName, institution: form.elements.visita_institucion.value.trim(), people: people.value, topics,
      });
      if (purpose !== selectedPurpose || !modelSelect.options.length) {
        modelSelect.replaceChildren();
        models.forEach(model => {
          const option = document.createElement('option'); option.value = model.id; option.textContent = model.label;
          modelSelect.appendChild(option);
        });
        if (models.some(model => model.id === previous)) modelSelect.value = previous;
        selectedPurpose = purpose;
      }
      const model = models.find(item => item.id === modelSelect.value) || models[0];
      group.querySelector('[data-visit-template-preview]').textContent = model.text;
      if (force || !description.value.trim() || description.value === lastAutoText) {
        description.value = model.text;
        lastAutoText = model.text;
      }
    }
    function sync({ notify = true } = {}) {
      syncIdentity();
      const attendees = occupiedRows();
      const oldCount = people.value;
      people.readOnly = mode.value === 'lista';
      const countState = group.querySelector('[data-visit-count-state]');
      if (countState) countState.textContent = people.readOnly ? tr('Automático') : tr('Editable · cantidad estimada');
      if (people.readOnly) people.setAttribute('readonly', ''); else people.removeAttribute('readonly');
      people.value = String(people.readOnly ? attendees.length : Math.max(1, Number(people.value) || 1, attendees.length));
      json.value = JSON.stringify(attendees);
      userIds.value = JSON.stringify(internal() ? Array.from(body.children).filter(row => row.dataset.userId).map(row => Number(row.dataset.userId)) : []);
      const documents = new Set();
      Array.from(body.children).forEach((row, index) => {
        row.querySelector('[data-attendee-index]').textContent = String(index + 1);
        const fields = Object.fromEntries(FIELDS.map(([key]) => [key, row.querySelector(`[data-attendee-field="${key}"]`)]));
        Object.entries(fields).forEach(([key, field]) => {
          if (key === 'rol') field.disabled = !active() || internal();
          else field.readOnly = internal();
        });
        const hasData = Object.values(fields).some(field => field.value.trim());
        fields.nombre.required = hasData;
        fields.rol.required = hasData;
        const documentKey = fields.documento.value.trim().toLocaleLowerCase();
        fields.documento.setCustomValidity(documentKey && documents.has(documentKey) ? tr('Esta cédula o documento ya está en la lista.') : '');
        if (documentKey) documents.add(documentKey);
        FIELDS.forEach(([key, label]) => fields[key].setAttribute('aria-label', `${tr(label)} · ${tr('fila')} ${index + 1}`));
        row.querySelector('[data-remove-visit-attendee]').setAttribute('aria-label', `${tr('Quitar asistente de la fila')} ${index + 1}`);
      });
      add.disabled = body.children.length >= 200;
      group.querySelector('[data-visit-attendees-count]').textContent = `${attendees.length} ${attendees.length === 1 ? tr('asistente en la tabla') : tr('asistentes en la tabla')} · ${people.value} ${Number(people.value) === 1 ? tr('visitante previsto') : tr('visitantes previstos')}`;
      group.querySelector('[data-visit-count-help]').textContent = people.readOnly
        ? tr('Conteo automático de las filas con datos; no incluye a los guías de la unidad.')
        : tr('Cantidad estimada del grupo. Puedes completar la lista después; no puede ser menor que los asistentes registrados.');
      refreshModels();
      if (notify && oldCount !== people.value && active()) people.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function addRow(record = {}, userId = '') {
      if (body.children.length >= 200) return;
      const row = document.createElement('tr');
      if (userId) row.dataset.userId = String(userId);
      const index = document.createElement('td'); index.dataset.attendeeIndex = ''; row.appendChild(index);
      FIELDS.forEach(([key, label, type, maximum]) => {
        const cell = document.createElement('td');
        const input = document.createElement(type === 'select' ? 'select' : 'input');
        input.dataset.attendeeField = key;
        input.disabled = !active();
        if (type === 'select') ROLES.forEach(([value, name]) => {
          const option = document.createElement('option'); option.value = value; option.textContent = tr(name); input.appendChild(option);
        });
        else { input.type = type; input.maxLength = maximum; input.autocomplete = 'off'; }
        input.value = record[key] || '';
        input.setAttribute('aria-label', tr(label));
        cell.appendChild(input); row.appendChild(cell);
      });
      const action = document.createElement('td');
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'rw-button rw-visit-remove';
      remove.dataset.removeVisitAttendee = ''; remove.textContent = '×'; remove.title = tr('Quitar asistente');
      action.appendChild(remove); row.appendChild(action); body.appendChild(row);
      sync();
      return row;
    }
    function focusRow(row) {
      if (!row) return;
      row.querySelector('input')?.focus({ preventScroll: true });
      const scroll = group.querySelector('.rw-visit-attendees__scroll');
      const bounds = scroll.getBoundingClientRect();
      const rowBounds = row.getBoundingClientRect();
      const visibleTop = bounds.top + scroll.querySelector('thead').getBoundingClientRect().height;
      if (rowBounds.top < visibleTop) scroll.scrollTop += rowBounds.top - visibleTop;
      else if (rowBounds.bottom > bounds.bottom) scroll.scrollTop += rowBounds.bottom - bounds.bottom;
    }
    add.addEventListener('click', () => focusRow(addRow()));
    group.querySelectorAll('[data-visit-category]').forEach(button => button.addEventListener('click', () => {
      if (!active() || button.disabled || category.value === button.dataset.visitCategory) return;
      category.value = button.dataset.visitCategory;
      category.dispatchEvent(new Event('change', { bubbles: true }));
    }));
    category.addEventListener('change', () => {
      savedGroups.set(previousCategory, Array.from(body.children).map(row => ({
        fields: Object.fromEntries(FIELDS.map(([key]) => [key, row.querySelector(`[data-attendee-field="${key}"]`).value])),
        userId: row.dataset.userId || '',
      })));
      previousCategory = category.value;
      searchVersion += 1;
      userResults.replaceChildren(); userResults.hidden = true; userSearch.value = ''; userStatus.textContent = '';
      body.replaceChildren();
      const saved = savedGroups.get(category.value) || [];
      saved.forEach(row => addRow(row.fields, row.userId));
      if (!body.children.length) addRow();
      sync();
    });
    userSearch.addEventListener('input', () => {
      clearTimeout(searchTimer);
      const version = ++searchVersion;
      const query = userSearch.value.trim();
      userResults.hidden = true; userStatus.textContent = '';
      if (!internal() || !authenticated || query.length < 2) return;
      searchTimer = setTimeout(async () => {
        try {
          const url = new URL(document.getElementById('equiposReservaModal').dataset.participantSearchUrl, window.location.origin);
          url.searchParams.set('q', query); url.searchParams.set('contexto', 'visitas_internas');
          const response = await fetch(url, { credentials: 'same-origin' });
          const result = await response.json();
          if (version !== searchVersion || !internal() || !active()) return;
          if (!response.ok || !result.success) throw new Error(result.error || tr('No se pudo consultar las cuentas.'));
          const selected = new Set(Array.from(body.children, row => Number(row.dataset.userId)));
          userResults.replaceChildren();
          (result.usuarios || []).filter(person => !selected.has(Number(person.id))).forEach(person => {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'reservation-participant-result';
            button.dataset.visitUserId = String(person.id); button._visitor = person;
            button.disabled = person.habilitado === false;
            const name = document.createElement('strong'); name.textContent = person.nombre;
            const detail = document.createElement('small');
            detail.textContent = person.habilitado === false ? `${tr('Perfil incompleto:')} ${(person.faltantes || []).join(', ')}` : `${person.tipo} · ${person.carrera} · ${person.correo}`;
            button.append(name, detail); userResults.appendChild(button);
          });
          userResults.hidden = !userResults.children.length;
          userStatus.textContent = userResults.hidden ? tr('No se encontraron cuentas disponibles.') : '';
        } catch (error) {
          if (version === searchVersion) userStatus.textContent = error.message || tr('No se pudo consultar las cuentas.');
        }
      }, 250);
    });
    userResults.addEventListener('click', event => {
      const button = event.target.closest('[data-visit-user-id]');
      if (!button || button.disabled || !button._visitor || !internal() || !authenticated) return;
      const person = button._visitor;
      if (Array.from(body.children).some(row => Number(row.dataset.userId) === Number(person.id))) return;
      if (occupiedRows().length >= 200) {
        userStatus.textContent = tr('Cada solicitud admite hasta 200 visitantes.');
        return;
      }
      if (!occupiedRows().length) body.replaceChildren();
      const rol = ['estudiante', 'docente', 'administrativo'].includes(person.tipo_codigo) ? person.tipo_codigo : 'otro';
      focusRow(addRow({ nombre: person.nombre, documento: person.documento, rol, telefono: person.telefono, correo: person.correo }, person.id));
      userResults.hidden = true; userSearch.value = ''; searchVersion += 1;
      userStatus.textContent = tr('Visitante añadido a la tabla.');
    });
    body.addEventListener('keydown', event => {
      if (event.key !== 'Enter' || event.target.dataset.attendeeField !== 'correo' || internal()) return;
      event.preventDefault();
      focusRow(event.target.closest('tr').nextElementSibling || addRow());
    });
    body.addEventListener('click', event => {
      const remove = event.target.closest('[data-remove-visit-attendee]');
      if (!remove) return;
      remove.closest('tr').remove();
      if (!body.children.length) addRow();
      sync();
    });
    body.addEventListener('input', () => sync());
    body.addEventListener('change', () => sync());
    mode.addEventListener('change', () => sync());
    people.addEventListener('change', () => sync({ notify: false }));
    form.elements.visita_institucion.addEventListener('input', () => refreshModels());
    form.elements.visita_proposito.addEventListener('change', () => refreshModels());
    modelSelect.addEventListener('change', () => refreshModels());
    group.querySelector('[data-use-visit-template]').addEventListener('click', () => {
      refreshModels(true); description.dispatchEvent(new Event('change', { bubbles: true }));
    });
    form.addEventListener('reset', () => setTimeout(() => {
      savedGroups.clear(); searchVersion += 1; previousCategory = category.value;
      body.replaceChildren(); lastAutoText = null; selectedPurpose = ''; addRow(); sync({ notify: false });
    }, 0));
    function validate() {
      sync({ notify: false });
      if (internal() && !authenticated) {
        return { message: tr('Inicia sesión con tu cuenta institucional para solicitar una visita interna.'), input: category };
      }
      if (mode.value === 'lista' && !occupiedRows().length) {
        return { message: tr('Completa al menos un asistente o elige una cantidad estimada para terminar la lista después.'), input: body.querySelector('[data-attendee-field="nombre"]') };
      }
      for (const input of body.querySelectorAll('input,select')) {
        if (!input.checkValidity()) { input.reportValidity(); return { message: tr('Revisa los datos de la tabla de asistentes.'), input }; }
      }
      return null;
    }
    addRow(); sync({ notify: false });
    return { validate, sync, refreshModels };
  };
  window.visitWritingModels = visitWritingModels;
})();
