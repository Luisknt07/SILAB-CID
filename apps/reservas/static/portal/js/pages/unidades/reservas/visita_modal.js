(function () {
  'use strict';
  const tr = (text) => typeof gettext === 'function' ? gettext(text) : text;

  function visitCostEstimate(visitors, guides, guideReference, materials, taxes) {
    const round = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
    const material = round(materials.reduce((total, item) => total
      + visitors * Number(item.cantidad || 0) * Number(item.precio_unitario || 0), 0));
    const tax = taxes.aplica ? round(material * Number(taxes.porcentaje || 0) / 100) : 0;
    return { material, tax, total: round(material + tax), institutional: round(guides * guideReference) };
  }
  window.visitCostEstimate = visitCostEstimate;

  function visitCalendarSelection(form, route) {
    const areas = Array.from(form.querySelectorAll('[name="visita_recorrido"]:checked'));
    const visitors = Number(form.elements.visita_personas.value || 0);
    const perGuide = Math.max(1, Number(route.dataset.personasPorGuia || 15));
    return {
      unidades: [], software: [], espacios: areas.map((input) => Number(input.value)),
      incluyeEspacio: true, alcanceEspacio: areas.length ? 'areas' : 'unidad_completa',
      visitantes: visitors, participantes: visitors + Math.max(1, Math.ceil(visitors / perGuide)),
    };
  }

  window.createVisitReservationFlow = function (options) {
    const { form, shell, dataCard, dataGrid, requesterProfile, resourceCard, resourceGrid, resources,
      calendar, integratedCalendar, calendarParticipantSummary, requirementsCard, confirmationCard,
      formatSchedule, hasCalendarSelection, showCalendarSelectionError } = options;
    const group = form.querySelector('#visitaDatosReserva');
    const route = form.querySelector('#visitaRecorridoReserva');
    const conditions = form.querySelector('#visitaCondicionesReserva');
    const recap = form.querySelector('#visitaResumenReserva');
    if (!group || !route || !conditions || !recap) throw new Error('Faltan los campos de la visita en el modal.');
    const groupEditor = window.createVisitGroupEditor(form);
    [group, route, conditions, recap].forEach((node) => node.classList.remove('reservation-legacy-region'));
    dataGrid.appendChild(group);
    resourceGrid.insertBefore(route, calendar);
    requirementsCard.insertBefore(conditions, requirementsCard.querySelector('.rw-actions'));
    confirmationCard.insertBefore(recap, confirmationCard.querySelector('.rw-confirmation-terms'));
    const hidden = new Map();
    const disabled = new Map();
    const texts = new Map();
    let active = false;
    const error = document.createElement('p');
    error.className = 'reservation-step-message';
    error.hidden = true;
    error.setAttribute('role', 'alert');
    group.appendChild(error);
    function show(node, visible) {
      if (!node) return;
      if (!hidden.has(node)) hidden.set(node, node.hidden);
      node.hidden = !visible;
    }
    function text(node, value) {
      if (!node) return;
      if (!texts.has(node)) texts.set(node, node.textContent);
      node.textContent = value;
    }
    function header(card, title, copy) {
      text(card.querySelector('.rw-panel__header h3'), title);
      text(card.querySelector('.rw-panel__header p'), copy);
    }
    function setSummary(key, value) { recap.querySelector(`[data-visit-summary="${key}"]`).textContent = value; }
    function currentSelection() { return visitCalendarSelection(form, route); }
    function updateSummary() {
      const selection = currentSelection();
      const visitors = selection.visitantes;
      const guides = selection.participantes - visitors;
      const visitorLabel = visitors === 1 ? tr('visitante') : tr('visitantes');
      const guideLabel = guides === 1 ? tr('guía') : tr('guías');
      const materials = JSON.parse(form.querySelector('#visitaMaterialesPorPersona')?.textContent || '[]');
      const taxes = JSON.parse(form.querySelector('#visitaImpuestos')?.textContent || '{}');
      const estimate = visitCostEstimate(visitors, guides,
        Number(String(route.dataset.costoPorGuia || '0').replace(',', '.')), materials, taxes);
      const money = (amount) => new Intl.NumberFormat(document.documentElement.lang || 'es', { style: 'currency', currency: 'USD' }).format(amount);
      const value = money(estimate.total);
      const selected = Array.from(route.querySelectorAll('input:checked'));
      const capacities = selected.map((input) => Number(input.dataset.capacidad)).filter((value) => value > 0);
      const capacity = capacities.length ? Math.min(...capacities) : (!route.querySelector('input') ? Number(route.dataset.aforoUnidad || 0) : 0);
      route.querySelector('[data-visit-capacity]').textContent = capacity
        ? `${tr('Capacidad del recorrido:')} ${capacity} ${tr('visitantes por grupo.')}`
        : tr('El aforo y el recorrido se confirmarán al revisar la solicitud.');
      conditions.querySelector('[data-visit-estimate]').textContent = `${visitors} ${visitorLabel} · ${guides} ${guideLabel}. ${tr('Guías a cargo de la UPEC:')} ${money(estimate.institutional)}. ${tr('Materiales de protección:')} ${money(estimate.material)}${taxes.aplica ? ` · IVA ${money(estimate.tax)}` : ''}. ${tr('Valor estimado a tu cargo:')} ${value}. ${tr('Solo se cobran los materiales consumidos; la UPEC asume el recorrido y los guías.')}`;
      setSummary('responsable', (group.dataset.authenticated !== 'true' ? form.elements.visita_responsable_nombre.value.trim() : '') || document.getElementById('solicitanteNombre')?.value || document.getElementById('solicitanteEmail')?.value || tr('Persona responsable de la solicitud'));
      setSummary('institucion', form.elements.visita_institucion.value.trim() || tr('Por completar'));
      setSummary('grupo', `${visitors} ${visitorLabel} · ${guides} ${guideLabel}`);
      setSummary('recorrido', selected.map((input) => input.dataset.nombre).join(' · ') || tr('Presentación y orientación; recorrido por confirmar con la unidad'));
      setSummary('horario', formatSchedule(document.getElementById('fechaInicio')?.value, document.getElementById('horasSeleccionadas')?.value));
      setSummary('descripcion', form.elements.visita_descripcion.value.trim() || tr('Presentación y orientación de la unidad'));
      setSummary('valor', value);
      calendarParticipantSummary.querySelector('[data-calendar-participant-count]').textContent = `${visitors} ${visitorLabel} + ${guides} ${guideLabel}`;
    }
    function activate() {
      active = true;
      shell.classList.add('rw-visit-active');
      resourceGrid.classList.add('is-visit-flow');
      // Solo se deshabilitan controles de las otras rutas; sus valores se conservan.
      form.querySelectorAll('input,select,textarea').forEach((input) => {
        if (!disabled.has(input)) disabled.set(input, input.disabled);
        input.disabled = !input.closest('.rw-visit-section') && ![
          'csrfmiddlewaretoken', 'unidad_id', 'tipo_solicitud', 'fecha_inicio', 'fecha_fin', 'horas_seleccionadas', 'aceptar_terminos',
        ].includes(input.name);
      });
      Array.from(dataCard.children).forEach((node) => show(node, node === dataGrid || node.matches('.rw-panel__header,.rw-actions')));
      Array.from(dataGrid.children).forEach((node) => show(node, node === requesterProfile || node === group));
      show(resources, false);
      show(route, true);
      show(integratedCalendar, true);
      Array.from(calendar.children).forEach((node) => show(node, node === integratedCalendar || node === calendarParticipantSummary || node.tagName === 'H4'));
      show(document.getElementById('frecuenciaReservaCampo'), false);
      Array.from(requirementsCard.children).forEach((node) => show(node, node === conditions || node.matches('.rw-panel__header,.rw-actions')));
      Array.from(confirmationCard.children).forEach((node) => show(node, node === recap || node.matches('.rw-panel__header,.rw-actions,.rw-confirmation-terms')));
      show(group, true); show(conditions, true); show(recap, true);
      header(dataCard, tr('Grupo y finalidad de la visita'), tr('Tú eres la persona responsable. Indica quién visita y qué desea conocer.'));
      header(resourceCard, tr('Recorrido y calendario'), tr('Elige las áreas y consulta la misma agenda integrada de la unidad para reservar fecha y horario.'));
      header(requirementsCard, tr('Requisitos y condiciones de la visita'), tr('Revisa lo que ofrece la unidad, las zonas excluidas y las condiciones para tu grupo.'));
      text(calendar.querySelector('h4'), tr('2. Fecha y horario en la agenda integrada'));
      const steps = [
        [2, tr('Grupo y finalidad'), tr('Datos del grupo y qué desea conocer')],
        [3, tr('Recorrido y calendario'), tr('Áreas, ocupación y selección de horario')],
        [4, tr('Requisitos y condiciones'), tr('Acceso, guías y valor estimado')],
      ];
      steps.forEach(([number, title, copy]) => {
        text(shell.querySelector(`[data-rw-step="${number}"] strong`), title);
        text(shell.querySelector(`[data-rw-step="${number}"] small`), copy);
      });
      text(confirmationCard.querySelector('.rw-confirmation-commitment'), tr('La visita se registra pendiente de aprobación. La unidad confirma el recorrido, las condiciones de acceso y los guías antes de recibir al grupo.'));
      groupEditor.sync({ notify: false });
      show(requesterProfile, group.dataset.authenticated === 'true');
      updateSummary();
    }
    function deactivate() {
      if (!active) return;
      hidden.forEach((value, node) => { node.hidden = value; });
      disabled.forEach((value, input) => { input.disabled = value; });
      texts.forEach((value, node) => { node.textContent = value; });
      hidden.clear(); disabled.clear(); texts.clear();
      resourceGrid.classList.remove('is-visit-flow');
      shell.classList.remove('rw-visit-active');
      [group, route, conditions, recap].forEach((node) => { node.hidden = true; });
      group.querySelectorAll('input,select,textarea').forEach(input => { input.disabled = true; });
      active = false;
      const submit = document.getElementById('btnEnviarReserva');
      if (submit) submit.disabled = submit.dataset.authenticated !== 'true';
      error.hidden = true;
    }
    function fail(message, input) {
      error.textContent = message;
      error.hidden = false;
      const card = input?.closest('.rw-panel-card') || dataCard;
      card.insertBefore(error, card.querySelector('.rw-actions'));
      error.scrollIntoView?.({ block: 'center' });
      input?.focus?.();
      return false;
    }
    function validate(step) {
      error.hidden = true;
      if (step === 5) {
        for (const previousStep of [2, 3, 4]) {
          if (!validate(previousStep)) { options.showStep(previousStep, true); return false; }
        }
      }
      if (step === 2) {
        const problem = groupEditor.validate();
        if (problem) return fail(problem.message, problem.input);
        for (const input of group.querySelectorAll('input,select,textarea')) {
          if (!input.checkValidity()) { input.reportValidity(); return false; }
        }
        if (!form.elements.visita_institucion.value.trim()) return fail(tr('Indica la institución o grupo que visita.'), form.elements.visita_institucion);
      }
      if (step === 3) {
        if (window.calendarState?.loading || window.calendarState?.visitAvailabilityError) {
          return fail(tr('Espera a que la agenda confirme la disponibilidad o vuelve a consultarla.'), calendar);
        }
        const inputs = Array.from(route.querySelectorAll('[name="visita_recorrido"]'));
        const selected = inputs.filter((input) => input.checked);
        if (inputs.length && !selected.length) return fail(tr('Elige al menos un área para la visita.'), inputs[0]);
        const capacities = selected.map((input) => Number(input.dataset.capacidad)).filter((value) => value > 0);
        const capacity = capacities.length ? Math.min(...capacities) : (!inputs.length ? Number(route.dataset.aforoUnidad || 0) : 0);
        if (capacity && Number(form.elements.visita_personas.value) > capacity) return fail(`${tr('El recorrido admite hasta')} ${capacity} ${tr('visitantes. Reduce el grupo o ajusta las áreas.')}`, selected[0]);
        if (!hasCalendarSelection()) return showCalendarSelectionError();
      }
      if (step === 4 && !form.elements.visita_requisitos_aceptados.checked) return fail(tr('Acepta los requisitos y condiciones de la visita.'), form.elements.visita_requisitos_aceptados);
      if (step === 5 && !document.getElementById('aceptarTerminos').checked) {
        document.getElementById('aceptarTerminos').reportValidity();
        return false;
      }
      return true;
    }
    form.addEventListener('change', (event) => {
      if (!active || !event.target.closest('.rw-visit-section')) return;
      error.hidden = true;
      updateSummary();
      if (event.target.matches('[name="visita_personas"],[name="visita_recorrido"]')) window.refreshCalendarAvailability?.();
    });
    return { activate, deactivate, validate, updateSummary, calendarSelection: currentSelection, get active() { return active; } };
  };
  window.visitCalendarSelection = visitCalendarSelection;
})();
