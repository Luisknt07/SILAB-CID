(function () {
  'use strict';

  const MODAL_ID = 'equiposReservaModal';
  const FORM_ID = 'reservaForm';
  const TOTAL_STEPS = 5;
  const EXPECTED_BUILD = '20260917-imagenes-v150';
  let activeRoot = document;

  function ready(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
      callback();
    }
  }

  // Cómo llama esta unidad a lo que produce, con su género: hay laboratorios
  // que cuentan muestras y otros que cuentan prototipos.
  function palabraTrabajo(plural = false) {
    const datos = document.getElementById('equiposReservaModal')?.dataset || {};
    if (plural) return gettext(datos.trabajoPlural || 'piezas');
    return gettext(datos.trabajoSingular || 'pieza');
  }

  function trabajoEsFemenino() {
    const datos = document.getElementById('equiposReservaModal')?.dataset || {};
    return (datos.trabajoGenero || 'f') === 'f';
  }

  function contarTrabajo(cantidad) {
    return `${cantidad} ${cantidad === 1 ? palabraTrabajo() : palabraTrabajo(true)}`;
  }

  function element(id) {
    return activeRoot.querySelector(`#${id}`) || document.getElementById(id);
  }

  function create(tag, className, html) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof html === 'string') node.innerHTML = html;
    return node;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[character]));
  }

  // La tarjeta orienta sobre el área; las unidades y sus códigos se eligen
  // después. La identidad del modelo evita mezclar equipos con igual nombre.
  function summarizeAreaEquipment(ids, units, limit = 3) {
    const associated = new Set(ids.map(String));
    const seen = new Set();
    const models = new Map();
    units.forEach((unit) => {
      const id = String(unit.id);
      if (!associated.has(id) || seen.has(id)) return;
      seen.add(id);
      const key = unit.equipo_id ? `equipo-${unit.equipo_id}` : `unidad-${id}`;
      if (!models.has(key)) models.set(key, {
        name: unit.equipo_nombre || gettext('Equipo'),
        category: unit.categoria || '',
        quantity: 0
      });
      models.get(key).quantity += 1;
    });
    const all = Array.from(models.values()).sort((a, b) => (
      a.category.localeCompare(b.category, 'es') || a.name.localeCompare(b.name, 'es')
    ));
    return {
      quantity: seen.size, models: all.length,
      visible: all.slice(0, limit), remaining: Math.max(0, all.length - limit)
    };
  }

  function areaEquipmentSummaryHtml(summary) {
    if (!summary.quantity) return '';
    return window.interfaz.html`
      <section class="reservation-area-resources"><h4>${gettext('Equipos asociados')}</h4><p>${summary.quantity} ${summary.quantity === 1 ? gettext('unidad asociada') : gettext('unidades asociadas')} · ${summary.models} ${summary.models === 1 ? gettext('modelo') : gettext('modelos')}</p>
      <ul class="reservation-space-item__models">${summary.visible.map((model) => window.interfaz.html`
        <li><span>${escapeHtml(model.name)}${model.category ? window.interfaz.html`<small>${escapeHtml(model.category)}</small>` : ''}</span><b aria-label="${model.quantity} ${gettext('unidades')}">×${model.quantity}</b></li>
      `).join('')}</ul>
      ${summary.remaining ? window.interfaz.html`<small class="reservation-space-item__more">+${summary.remaining} ${summary.remaining === 1 ? gettext('modelo más') : gettext('modelos más')} · ${gettext('consulta los recursos abajo')}</small>` : ''}</section>`;
  }

  function appendUnique(target, node) {
    if (target && node && !target.contains(node)) target.appendChild(node);
  }

  function safelyMove(target, id) {
    const node = element(id);
    if (!node || !target || node === target || node.contains(target)) return null;
    node.classList.remove('reservation-legacy-region');
    appendUnique(target, node);
    return node;
  }

  function buildShell() {
    const shell = create('div', 'rw-shell');
    shell.innerHTML = window.interfaz.html`
      <nav class="rw-steps" aria-label="Etapas de la solicitud">
        ${[
          [gettext('Forma de atención'), gettext('Elige recursos, servicios o visitas')],
          [gettext('Contexto y guía'), gettext('Solo define el tipo de actividad')],
          [gettext('Selección y disponibilidad'), gettext('Según el tipo de solicitud')],
          [gettext('Identificación y guía'), gettext('Recibe datos y sugerencias automáticas')],
          [gettext('Confirmación'), gettext('Revisa y envía')]
        ].map((step, index) => window.interfaz.html`
          <button type="button" class="rw-step${index === 0 ? ' is-active' : ''}" data-rw-step="${index + 1}">
            <span class="rw-step__number">${index + 1}</span>
            <span class="rw-step__text"><strong>${step[0]}</strong><small>${step[1]}</small></span>
          </button>
        `).join('')}
      </nav>
      <div class="rw-workspace">
        <main class="rw-main">
          <section class="rw-panel is-active" data-rw-panel="1"></section>
          <section class="rw-panel" data-rw-panel="2"></section>
          <section class="rw-panel" data-rw-panel="3"></section>
          <section class="rw-panel" data-rw-panel="4"></section>
          <section class="rw-panel" data-rw-panel="5"></section>
        </main>
      </div>`;
    return shell;
  }

  function panelCard(panel, icon, title, copy) {
    const card = create('div', 'rw-panel-card');
    const icons = { '▦': 'fa-calendar-check', '♙': 'fa-users', '▣': 'fa-calendar-alt', '◇': 'fa-clipboard-list', '✓': 'fa-check-circle' };
    const headingIcon = icons[icon] ? `<i class="fas ${icons[icon]}" aria-hidden="true"></i>` : icon;
    card.innerHTML = window.interfaz.html`
      <div class="rw-panel__header">
        <span class="rw-panel__icon">${headingIcon}</span>
        <div><h3>${title}</h3><p>${copy}</p></div>
      </div>`;
    panel.appendChild(card);
    return card;
  }

  function addActions(card, step) {
    const actions = create('div', 'rw-actions');
    const left = step > 1
      ? window.interfaz.html`<button type="button" class="rw-button" data-rw-action="previous">← Volver</button>`
      : window.interfaz.html`<span></span>`;
    const right = step < TOTAL_STEPS
      ? window.interfaz.html`<button type="button" class="rw-button rw-button--primary" data-rw-action="next">Continuar →</button>`
      : window.interfaz.html`<button type="button" class="rw-button rw-button--gold" data-rw-action="submit">Enviar solicitud →</button>`;
    actions.innerHTML = window.interfaz.html`${left}<div class="rw-actions__group">${right}</div>`;
    card.appendChild(actions);
  }

  function init() {
    const modal = document.getElementById(MODAL_ID);
    if (modal) activeRoot = modal;
    const form = modal?.querySelector(`#${FORM_ID}`);
    if (!modal || !form || modal.dataset.reservationWizardReady === 'true') return;

    let staleTemplateBuild = '';
    if (modal.dataset.reservationBuild !== EXPECTED_BUILD) {
      staleTemplateBuild = modal.dataset.reservationBuild || 'sin versión';
      /*
       * El servidor puede mantener una plantilla anterior en memoria mientras
       * los estáticos ya fueron actualizados. La compatibilidad real se valida
       * con los nodos requeridos de abajo; una etiqueta de versión distinta no
       * debe dejar al usuario atrapado en el formulario base.
       */
      console.warn(
        'El asistente de reservas se inicializó sobre una plantilla compatible anterior.',
        { template: modal.dataset.reservationBuild || 'sin-versión', script: EXPECTED_BUILD }
      );
      modal.dataset.reservationBuild = EXPECTED_BUILD;
    }

    const requiredNodes = [
      'solicitantePrincipal', 'participantesReserva', 'propositoReserva',
      'contextoActividadReserva', 'tituloAutomaticoReserva', 'descripcionProyecto'
    ];
    if (modal.dataset.reservasSoftware === 'true') requiredNodes.push('softwareReservaCatalogo');
    const missingNodes = requiredNodes.filter((id) => !modal.querySelector(`#${id}`));
    if (missingNodes.length) {
      const incompatibility = create('div', 'reservation-template-error');
      incompatibility.innerHTML = window.interfaz.html`<strong>El asistente no pudo cargarse completo.</strong><span>Recarga la página. Si el mensaje continúa, reinicia el servidor activo.</span>`;
      form.prepend(incompatibility);
      return;
    }

    modal.dataset.reservationWizardReady = 'true';
    modal.classList.add('reservation-wizard-enhanced');

    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.has('_reservation_build')) {
      currentUrl.searchParams.delete('_reservation_build');
      window.history.replaceState(window.history.state, '', currentUrl.toString());
    }

    const mount = form;
    Array.from(mount.children).forEach((child) => child.classList.add('reservation-legacy-region'));

    const shell = buildShell();
    mount.insertBefore(shell, mount.firstChild);
    if (staleTemplateBuild) {
      const notice = create('div', 'rw-stale-notice');
      notice.setAttribute('role', 'status');
      notice.innerHTML = window.interfaz.html`<i class="fas fa-sync-alt"></i><div><strong>El servidor está entregando una versión anterior de este formulario.</strong><span>Plantilla ${escapeHtml(staleTemplateBuild)} · scripts ${EXPECTED_BUILD}. Detén el servidor que atiende el puerto y vuelve a iniciarlo (scripts/iniciar_desarrollo.ps1 o scripts/iniciar_produccion.ps1); luego recarga la página. Si el puerto sigue ocupado por un proceso anterior, el reinicio no surte efecto.</span></div>`;
      shell.insertBefore(notice, shell.firstChild);
    }

    const panels = Array.from(shell.querySelectorAll('[data-rw-panel]'));
    const resourceAvailability = {
      equipo: modal.dataset.reservasEquipos !== 'false',
      espacio: modal.dataset.reservasEspacios !== 'false',
      software: modal.dataset.reservasSoftware === 'true'
    };
    const resourceChoiceImages = {
      espacio: modal.dataset.spaceResourceImageUrl || '',
      equipo: modal.dataset.equipmentResourceImageUrl || '',
      software: modal.dataset.softwareResourceImageUrl || ''
    };
    const guideLogoUrl = modal.dataset.guideLogoUrl || '';
    const guideInstitutionName = modal.dataset.guideInstitutionName || '';
    const guideInstitutionCode = modal.dataset.guideInstitutionCode || '';
    const serviceAvailable = modal.dataset.solicitudesServicio !== 'false';
    const reservationUserType = modal.dataset.reservationUserType || '';
    const canAuthorGuides = modal.dataset.canAuthorGuides === 'true';
    const profileStatusKnown = ['true', 'false'].includes(modal.dataset.profileComplete);
    const profileComplete = modal.dataset.profileComplete !== 'false';
    const hasResourceFlow = Object.values(resourceAvailability).some(Boolean);
    const availableTypeCount = Number(hasResourceFlow) + Number(serviceAvailable);
    const initialType = availableTypeCount === 1
      ? (hasResourceFlow ? 'recursos' : 'servicio')
      : '';
    const state = {
      step: 1,
      type: initialType,
      resources: { equipo: false, espacio: false, software: false }
    };

    const requestType = element('tipoSolicitudReserva') || create('input');
    requestType.type = 'hidden';
    requestType.id = 'tipoSolicitudReserva';
    requestType.name = 'tipo_solicitud';
    requestType.value = state.type;
    form.appendChild(requestType);

    const routeInfo = document.getElementById('rutasReservaUnidad')?.dataset || {};
    const visitAvailable = routeInfo.visitAvailable === 'true';
    const typeCard = panelCard(panels[0], '▦', gettext('¿Qué necesitas hacer en esta unidad?'), gettext('Elige una ruta y continúa en este asistente para completar la solicitud.'));
    const types = create('div', 'rw-types');
    const resourceIllustration = modal.dataset.resourceIllustrationUrl || '';
    const serviceIllustration = modal.dataset.serviceIllustrationUrl || '';
    // Cada tarjeta reune todo lo que la persona necesita para decidir: que
    // hara, con que prepararse y un videotutorial; no hay ayuda aparte.
    types.innerHTML = window.interfaz.html`
      <article class="rw-type${initialType === 'recursos' ? ' is-selected' : ''}" data-type-card="recursos">
        <button type="button" class="rw-type__select" data-type="recursos" aria-pressed="${initialType === 'recursos'}">
          <span class="rw-type__visual"><img src="${resourceIllustration}" alt="" loading="lazy" decoding="async"><span><i class="fas fa-user-check"></i> Tú utilizas los recursos</span></span>
          <span class="rw-type__body">
            <span class="rw-type__heading"><span class="rw-type__icon"><i class="fas fa-layer-group"></i></span><span><small>Ruta de reserva</small><h4>Reservar recursos</h4></span></span>
            <p>${escapeHtml(routeInfo.resourceDescription || gettext('Tú o tu grupo utilizan los recursos habilitados de esta unidad para prácticas, investigación o trabajo autónomo.'))}</p>
            <span class="rw-type__benefits"><span><i class="fas fa-check"></i> Seleccionas los recursos</span><span><i class="fas fa-check"></i> Eliges fecha y horario</span><span><i class="fas fa-check"></i> La unidad revisa disponibilidad y requisitos</span></span>
            <span class="rw-type__cta"><i class="fas fa-arrow-right"></i> Elegir esta ruta</span>
          </span>
        </button>
        <div class="rw-type__prepare"><strong>Prepárate con:</strong><span><i class="fas fa-cubes"></i> Recursos que utilizarás</span><span><i class="fas fa-users"></i> Participantes registrados</span><span><i class="fas fa-calendar-alt"></i> Fecha y horario preferidos</span></div>
        <button type="button" class="rw-type__tutorial" data-generic-tutorial="recursos"><i class="fas fa-play" aria-hidden="true"></i><span><small>Videotutorial</small><strong>Cómo reservar recursos paso a paso</strong></span><b>Ver</b></button>
      </article>
      <article class="rw-type${initialType === 'servicio' ? ' is-selected' : ''}" data-type-card="servicio">
        <button type="button" class="rw-type__select" data-type="servicio" aria-pressed="${initialType === 'servicio'}">
          <span class="rw-type__visual"><img src="${serviceIllustration}" alt="" loading="lazy" decoding="async"><span><i class="fas fa-hands-helping"></i> El equipo de la unidad realiza el trabajo</span></span>
          <span class="rw-type__body">
            <span class="rw-type__heading"><span class="rw-type__icon"><i class="fas fa-drafting-compass"></i></span><span><small>Ruta de servicio</small><h4>Solicitar un servicio</h4></span></span>
            <p>${escapeHtml(routeInfo.serviceDescription || gettext('Solicita un trabajo especializado según las capacidades de esta unidad.'))}</p>
            <span class="rw-type__benefits"><span><i class="fas fa-check"></i> Describes el trabajo y sus materiales</span><span><i class="fas fa-check"></i> Recibes fecha propuesta y valor estimado</span><span><i class="fas fa-check"></i> La unidad revisa el alcance y los requisitos</span></span>
            <span class="rw-type__cta"><i class="fas fa-arrow-right"></i> Elegir esta ruta</span>
          </span>
        </button>
        <div class="rw-type__prepare"><strong>Prepárate con:</strong><span><i class="fas fa-cube"></i> Resultado y especificaciones</span><span><i class="fas fa-file-upload"></i> Archivos o información de partida</span><span><i class="fas fa-bolt"></i> Urgencia y fecha preferida</span></div>
        <button type="button" class="rw-type__tutorial" data-generic-tutorial="servicio"><i class="fas fa-play" aria-hidden="true"></i><span><small>Videotutorial</small><strong>Cómo encargar un servicio paso a paso</strong></span><b>Ver</b></button>
      </article>
      <article class="rw-type rw-type--visit${visitAvailable ? '' : ' is-unavailable'}" data-type-card="visita">
        <button type="button" class="rw-type__select" data-type="visita" aria-pressed="false" ${visitAvailable ? '' : 'disabled'}>
          <span class="rw-type__visual rw-type__visual--visit">${routeInfo.unitImage ? `<img src="${escapeHtml(routeInfo.unitImage)}" alt="" loading="lazy" decoding="async">` : '<i class="fas fa-users rw-type__visit-symbol" aria-hidden="true"></i>'}<span><i class="fas fa-route"></i> Conoce la unidad con tu grupo</span></span>
          <span class="rw-type__body">
            <span class="rw-type__heading"><span class="rw-type__icon"><i class="fas fa-users"></i></span><span><small>Ruta de visita</small><h4>Reservar una visita</h4></span></span>
            <p>${escapeHtml(routeInfo.visitDescription || gettext('Organiza un recorrido guiado para conocer las áreas y el trabajo de esta unidad. La persona responsable hace la solicitud por todo el grupo.'))}</p>
            <span class="rw-type__benefits"><span><i class="fas fa-check"></i> Indicas el grupo y sus integrantes</span><span><i class="fas fa-check"></i> Eliges recorrido, fecha y horario</span><span><i class="fas fa-check"></i> La unidad confirma y asigna los guías</span></span>
            <span class="rw-type__cta"><i class="fas ${visitAvailable ? 'fa-arrow-right' : 'fa-info-circle'}"></i> ${visitAvailable ? gettext('Elegir esta ruta') : gettext('Visitas aún no habilitadas')}</span>
          </span>
        </button>
        <div class="rw-type__prepare"><strong>Prepárate con:</strong><span><i class="fas fa-school"></i> Institución o grupo</span><span><i class="fas fa-users"></i> Número de visitantes</span><span><i class="fas fa-calendar-alt"></i> Fecha y horario preferidos</span></div>
        <div class="rw-type__visit-help"><i class="fas ${visitAvailable ? 'fa-clipboard-list' : 'fa-info-circle'}" aria-hidden="true"></i><span><strong>${visitAvailable ? gettext('Grupo, recorrido y calendario') : gettext('Consulta la disponibilidad con la unidad')}</strong><small>${visitAvailable ? gettext('Continúa aquí para elegir fecha y horario.') : gettext('La unidad debe publicar las áreas y condiciones del recorrido.')}</small></span></div>
      </article>`;
    types.querySelectorAll('[data-type]').forEach((button) => {
      if ((button.dataset.type === 'recursos' && !hasResourceFlow)
          || (button.dataset.type === 'servicio' && !serviceAvailable)) {
        const card = button.closest('[data-type-card]');
        button.disabled = true;
        card.classList.add('is-unavailable');
        card.querySelector('.rw-type__cta').textContent = gettext('Ruta no habilitada en esta unidad');
        card.querySelector('[data-generic-tutorial]').disabled = true;
      }
    });
    typeCard.appendChild(types);
    const typesNote = create('p', 'rw-types__note', '<i class="fas fa-lightbulb" aria-hidden="true"></i> Puedes revisar y corregir los pasos anteriores. La solicitud solo se registra al confirmar el envío.');

    const primaryResourceChoices = create('fieldset', 'rw-resource-choices rw-resource-choices--primary');
    primaryResourceChoices.innerHTML = window.interfaz.html`
      <legend>¿Qué vas a utilizar durante la reserva? *</legend>
      <p class="rw-resource-choices__intro">Selecciona desde ahora solo lo que realmente usarás. Puedes combinar opciones; el sistema mostrará después únicamente los catálogos y compatibilidades necesarias.</p>
      <div class="rw-resource-choices__grid">
        <label data-resource-option="espacio"><input type="checkbox" data-resource-kind-toggle="espacio"><span class="rw-resource-choice"><span class="rw-resource-choice__visual"><img src="${resourceChoiceImages.espacio}" alt="Sala con mobiliario del laboratorio" loading="lazy" decoding="async"><span><i class="fas fa-door-open"></i> Uso físico</span></span><span class="rw-resource-choice__body"><strong>Espacio y mobiliario</strong><small>Para salas, reuniones, clases o puestos de uso general. No agrega máquinas ni programas.</small><em>Elegir espacios <i class="fas fa-arrow-right"></i></em></span></span></label>
        <label data-resource-option="equipo"><input type="checkbox" data-resource-kind-toggle="equipo"><span class="rw-resource-choice"><span class="rw-resource-choice__visual"><img src="${resourceChoiceImages.equipo}" alt="Equipo especializado disponible" loading="lazy" decoding="async"><span><i class="fas fa-cogs"></i> Uso técnico</span></span><span class="rw-resource-choice__body"><strong>Equipo o instrumento</strong><small>Para operar una máquina o activo concreto. El software sigue siendo opcional.</small><em>Elegir equipos <i class="fas fa-arrow-right"></i></em></span></span></label>
        <label data-resource-option="software"><input type="checkbox" data-resource-kind-toggle="software"><span class="rw-resource-choice"><span class="rw-resource-choice__visual"><img src="${resourceChoiceImages.software}" alt="Estación de trabajo con software especializado" loading="lazy" decoding="async"><span><i class="fas fa-laptop-code"></i> Uso digital</span></span><span class="rw-resource-choice__body"><strong>Software o licencia</strong><small>Márcalo solo si lo necesitas. Deberás confirmar un equipo compatible y su ubicación.</small><em>Elegir software <i class="fas fa-arrow-right"></i></em></span></span></label>
      </div>
      <aside class="rw-resource-plan" aria-label="Cómo se relacionan los recursos">
        <span><i class="fas fa-chair"></i><b>Solo espacio</b><small>Incluye únicamente mobiliario e infraestructura publicados.</small></span>
        <span><i class="fas fa-cog"></i><b>Equipo sin software</b><small>Es válido; su área física se incorpora para evitar cruces.</small></span>
        <span><i class="fas fa-laptop-code"></i><b>Con software</b><small>Se exige un equipo donde esté disponible y se incorpora su área.</small></span>
      </aside>`;
    primaryResourceChoices.querySelectorAll('[data-resource-option]').forEach((option) => {
      if (!resourceAvailability[option.dataset.resourceOption]) option.remove();
    });
    const serviceCatalog = element('serviciosReservaCatalogo');
    const intentionValidationMessage = create('div', 'reservation-step-message');
    intentionValidationMessage.hidden = true;
    intentionValidationMessage.setAttribute('role', 'alert');
    typeCard.appendChild(intentionValidationMessage);
    addActions(typeCard, 1);
    typeCard.querySelector('.rw-actions > span').replaceWith(typesNote);

    // Fit the complete route chooser in the space left by the real modal chrome.
    // Re-measure without zoom so repeated resizes never compound the scale.
    let routeFitFrame = 0;
    function fitRouteCards() {
      routeFitFrame = 0;
      if (!panels[0].classList.contains('is-active') || !modal.getClientRects().length) return;
      types.style.removeProperty('zoom');
      if (window.innerWidth < 700) return;
      const body = modal.querySelector('.modal-body');
      body.scrollTop = 0;
      const actions = typeCard.querySelector('.rw-actions');
      const bounds = types.getBoundingClientRect();
      const bottom = Math.min(window.visualViewport?.height || window.innerHeight,
        modal.querySelector('.modal-content').getBoundingClientRect().bottom);
      const available = bottom - bounds.top - actions.getBoundingClientRect().height - 28;
      if (available <= 0 || !bounds.height) return;
      types.style.zoom = String(Math.min(1, available / bounds.height));
    }
    function scheduleRouteFit() {
      if (!routeFitFrame) routeFitFrame = window.requestAnimationFrame(fitRouteCards);
    }
    window.addEventListener('resize', scheduleRouteFit);
    window.visualViewport?.addEventListener('resize', scheduleRouteFit);
    modal.addEventListener('shown.bs.modal', scheduleRouteFit);
    panels[0].addEventListener('animationend', scheduleRouteFit);
    if (window.ResizeObserver) {
      const routeResize = new window.ResizeObserver(scheduleRouteFit);
      routeResize.observe(modal.querySelector('.modal-content'));
      routeResize.observe(typeCard.querySelector('.rw-panel__header'));
      routeResize.observe(typeCard.querySelector('.rw-actions'));
    }

    const dataCard = panelCard(panels[1], '♙', gettext('Contexto y participantes'), gettext('Clasifica el uso, indica si llevará guía e identifica a las personas que asistirán. El nombre y el contenido se completan al final.'));
    const dataGrid = create('div', 'rw-grid');
    dataCard.appendChild(dataGrid);
    let requesterProfile = safelyMove(dataGrid, 'solicitantePrincipal');
    if (!requesterProfile) {
      requesterProfile = create('div', 'reservation-field-wide reservation-primary-user');
      requesterProfile.id = 'solicitantePrincipal';
      requesterProfile.innerHTML = window.interfaz.html`
        <span class="reservation-requester__avatar"><i class="fas fa-user-check"></i></span>
        <div><small>Solicitante principal</small><strong data-fallback-requester-name></strong>
        <span data-fallback-requester-email></span>
        <em>La clasificación institucional se validará antes de enviar.</em></div>`;
      requesterProfile.querySelector('[data-fallback-requester-name]').textContent = element('solicitanteNombre')?.value || 'Usuario autenticado';
      requesterProfile.querySelector('[data-fallback-requester-email]').textContent = element('solicitanteEmail')?.value || 'Datos tomados de la cuenta';
      dataGrid.appendChild(requesterProfile);
    }
    let purposeSection = safelyMove(dataGrid, 'propositoReserva');
    if (!purposeSection) {
      purposeSection = create('fieldset', 'reservation-field-wide reservation-purpose');
      purposeSection.id = 'propositoReserva';
      const purposeOptions = [
        ['docencia_practica', 'fa-chalkboard-teacher', gettext('Docencia y práctica curricular')],
        ['investigacion_innovacion', 'fa-microscope', gettext('Investigación e innovación')],
        ['vinculacion', 'fa-users', gettext('Vinculación con la sociedad')],
        ['capacitacion', 'fa-graduation-cap', gettext('Capacitación y educación continua')],
        ['servicio_cientifico_tecnologico', 'fa-tools', gettext('Servicio científico-tecnológico')],
        ['titulacion', 'fa-book', gettext('Trabajo de titulación')],
        ['otro', 'fa-ellipsis-h', gettext('Otro propósito')]
      ];
      purposeSection.innerHTML = window.interfaz.html`<legend>Propósito institucional de la solicitud *</legend><div class="reservation-purpose-labels">${purposeOptions.map(([value, icon, label]) => window.interfaz.html`<label><input type="radio" name="proposito_codigo" value="${value}" required><span><i class="fas ${icon}"></i><b>${label}</b></span></label>`).join('')}</div>`;
      dataGrid.appendChild(purposeSection);
    }
    safelyMove(dataGrid, 'contextoActividadReserva');
    safelyMove(dataGrid, 'participantesReserva');
    // Servicios: en lugar de clasificar y registrar participantes, la
    // descripcion del trabajo; el solicitante es la persona responsable.
    const servicePurpose = safelyMove(dataGrid, 'finalidadServicioReserva');

    // Descripcion obligatoria de lo que se pretende realizar (50-200 palabras).
    // Orienta la revision del laboratorio y alimenta las sugerencias de la
    // guia; no se publica en la guia. Un solo componente para ambas rutas.
    // Solo docencia genera guia: su descripcion (50-200 palabras) alimenta las
    // sugerencias. En los demas propositos, y en un servicio, el texto acompaña
    // la solicitud en el comprobante y orienta la revision; fuera de docencia
    // se pide mas breve (30-150 palabras).
    const INTENT_BRIEF_HINT = 'Entre 30 y 150 palabras. Acompaña la solicitud en el comprobante y orienta la revisión del laboratorio; en este propósito no se genera guía de práctica.';
    const INTENT_BRIEF_CHECKLIST = [
      gettext('Qué necesitas realizar y en el marco de qué proyecto, programa o trabajo.'),
      gettext('Qué harás con cada recurso: equipos, software, espacio o insumos.'),
      gettext('Qué resultado, producto o entregable esperas obtener.'),
      gettext('Cuántas sesiones u horas necesitas y quiénes participan.')
    ];
    function briefIntent(title, sample) {
      return { min: 30, max: 150, title, hint: INTENT_BRIEF_HINT, checklist: INTENT_BRIEF_CHECKLIST, sample };
    }
    const INTENT_COPY = {
      servicio: {
        min: 50,
        max: 200,
        title: gettext('Describe el trabajo que necesitas que realice el laboratorio *'),
        hint: 'Entre 50 y 200 palabras. El laboratorista lo lee antes de revisar los archivos y la cotización.',
        checklist: [
          gettext('Qué necesitas que haga el laboratorio y para qué proyecto, asignatura o uso.'),
          gettext('Cuántas unidades y con qué características, medidas o condiciones.'),
          gettext('Qué entregas tú y qué pone el laboratorio.'),
          gettext('Cómo quieres recibir el resultado y qué harás con él.'),
          gettext('Fecha en la que lo necesitas y cualquier restricción.')
        ],
        sample: 'Necesito que el laboratorio realice este trabajo para mi proyecto de titulación. Son cuatro unidades con las mismas características, que detallo en la información que entrego junto a la solicitud; si alguna condición no puede cumplirse, prefiero saberlo en la revisión técnica para ajustar el alcance antes de aprobar la cotización. El laboratorio pone los materiales que constan en el servicio y yo entrego la información de partida. Necesito el resultado en la fecha que indico porque lo presento ante el tribunal la semana siguiente.'
      },
      docencia_practica: {
        min: 50,
        max: 200,
        title: gettext('Describe lo que pretendes realizar en la reserva *'),
        hint: 'Entre 50 y 200 palabras. Con esta descripción la guía de práctica propone contenidos más exactos; el texto no se publica en la guía.',
        checklist: [
          gettext('Qué actividad harás y con quiénes (grupo, semestre, asignatura o proyecto).'),
          gettext('Qué harán con cada recurso: equipos, software, espacio o insumos.'),
          gettext('Qué resultado, producto o evidencia esperan obtener.'),
          gettext('Qué conocimientos o competencias aplicarán o evaluarán.'),
          gettext('Cuántas sesiones u horas necesitan y cómo se organizarán.')
        ],
        sample: 'Con el grupo de tercer semestre de la asignatura realizaremos la práctica prevista en el programa. Cada estudiante trabajará en su puesto con el equipo y el material que solicito, siguiendo paso a paso el procedimiento de la guía y anotando lo que observe. Buscamos que apliquen lo visto en clase, comparen sus resultados entre grupos y expliquen las diferencias; la evidencia será el informe de cada equipo con sus datos. Necesitamos dos horas por sesión durante cuatro semanas y pedimos el acompañamiento del laboratorista en la primera.'
      },
      investigacion_innovacion: briefIntent(
        'Describe lo que necesitas realizar en el laboratorio *',
        'Para el proyecto de investigación del grupo necesitamos el equipo y el espacio del laboratorio durante dos sesiones de tres horas. Participamos dos investigadores; traemos lo que vamos a trabajar y usaremos el material que solicito. En la primera sesión ajustaremos las condiciones de trabajo y en la segunda tomaremos los datos definitivos, que dejaremos registrados junto al consumo real de material.'
      ),
      vinculacion: briefIntent(
        'Describe lo que necesitas realizar para la actividad de vinculación *',
        'Con el programa de vinculación con la junta parroquial prepararemos lo que entregaremos a la organización beneficiaria. Participan cuatro estudiantes y el docente responsable; usaremos el equipo y el material del laboratorio que solicito. Esperamos tener el resultado listo para la fecha de entrega acordada con la comunidad y necesitamos dos sesiones de dos horas.'
      ),
      capacitacion: briefIntent(
        'Describe la capacitación que realizarás en el laboratorio *',
        'Dictaremos un taller de introducción para doce docentes de la facultad. Usaremos la sala con proyector y el equipo del laboratorio para la demostración final. Necesitamos tres sesiones de dos horas; los participantes no traen materiales y el laboratorio provee los que solicito en la solicitud.'
      ),
      servicio_cientifico_tecnologico: briefIntent(
        'Describe el ensayo o trabajo técnico que realizarás *',
        'Realizaremos el ensayo que solicitó una empresa local. Usaremos el equipo y el espacio del laboratorio y entregaremos un informe con los resultados y su interpretación. Necesitamos una sesión de tres horas y traemos lo que se va a analizar con la documentación de su origen.'
      ),
      titulacion: briefIntent(
        'Describe lo que necesitas realizar para tu trabajo de titulación *',
        'Para mi trabajo de titulación necesito el equipo del laboratorio durante dos sesiones de tres horas. Traigo preparado lo que voy a trabajar y usaré el material que solicito; pido el acompañamiento del laboratorista en la primera sesión. Los resultados que obtenga son los que analizaré en el capítulo de resultados de mi tesis.'
      ),
      otro: briefIntent(
        'Describe lo que necesitas realizar en el laboratorio *',
        'Necesitamos la sala de trabajo con su mobiliario para la reunión de planificación del grupo, con diez integrantes. Solo requerimos el proyector para presentar los avances; no usaremos equipos ni insumos del laboratorio. La sesión durará dos horas.'
      )
    };
    const intentField = create('section', 'reservation-intent');
    intentField.innerHTML = window.interfaz.html`
      <div class="reservation-intent__grid">
        <div class="reservation-intent__write">
          <label for="intencionSolicitud"><span data-intent-title></span><small data-intent-hint></small></label>
          <textarea class="form-control" id="intencionSolicitud" name="intencion_solicitud" rows="9" maxlength="2500"></textarea>
          <div class="reservation-intent__meta"><span data-intent-count></span><button type="button" class="reservation-intent__example" data-intent-example><i class="fas fa-magic" aria-hidden="true"></i> Usar el ejemplo redactado</button></div>
        </div>
        <aside class="reservation-intent__help" aria-label="Qué incluir y ejemplo de redacción">
          <strong><i class="fas fa-lightbulb" aria-hidden="true"></i> Qué incluir</strong>
          <ul data-intent-checklist></ul>
          <strong><i class="fas fa-quote-left" aria-hidden="true"></i> Ejemplo de redacción</strong>
          <blockquote data-intent-sample></blockquote>
        </aside>
      </div>`;
    const intentInput = intentField.querySelector('textarea');

    function intentWords(text = intentInput?.value || '') {
      return text.trim() ? text.trim().split(/\s+/).length : 0;
    }

    // Lo que publica la unidad: su ejemplo y, si lo definió, su propia lista.
    const EJEMPLOS_UNIDAD = (() => {
      try {
        return JSON.parse(document.getElementById('ejemplosSolicitudReserva')?.textContent || '{}');
      } catch (error) {
        return {};
      }
    })();

    function intentCopy() {
      const clave = state.type === 'servicio' ? 'servicio' : selectedPurpose();
      const base = INTENT_COPY[clave] || INTENT_COPY.docencia_practica;
      const propio = EJEMPLOS_UNIDAD[clave];
      if (!propio) return base;
      return {
        ...base,
        sample: propio.ejemplo || base.sample,
        checklist: propio.checklist?.length ? propio.checklist : base.checklist,
      };
    }

    function refreshIntentField() {
      const copy = intentCopy();
      intentField.querySelector('[data-intent-title]').textContent = copy.title;
      intentField.querySelector('[data-intent-hint]').textContent = copy.hint;
      intentField.querySelector('[data-intent-checklist]').innerHTML = copy.checklist.map((item) => window.interfaz.html`<li>${escapeHtml(item)}</li>`).join('');
      intentField.querySelector('[data-intent-sample]').textContent = copy.sample;
      const words = intentWords();
      const counter = intentField.querySelector('[data-intent-count]');
      counter.textContent = words < copy.min
        ? `${words} palabra${words === 1 ? '' : 's'} · faltan ${copy.min - words} para el mínimo`
        : words > copy.max
          ? `${words} palabras · supera el máximo de ${copy.max}`
          : `${words} palabras · dentro del rango ${copy.min}–${copy.max}`;
      counter.classList.toggle('is-ok', words >= copy.min && words <= copy.max);
      counter.classList.toggle('is-over', words > copy.max);
    }

    function placeIntentField() {
      if (state.type === 'servicio') {
        const slot = servicePurpose?.querySelector('[data-intent-slot]');
        if (slot && !slot.contains(intentField)) slot.appendChild(intentField);
        intentField.hidden = false;
      } else {
        if (purposeContext && purposeContext.nextElementSibling !== intentField) purposeContext.after(intentField);
        intentField.hidden = !(selectedPurpose() && subtypeSelect?.value);
      }
      refreshIntentField();
    }

    function validateIntent() {
      const words = intentWords();
      const { min, max } = intentCopy();
      if (words < min) {
        return showValidationMessage(
          dataValidationMessage,
          `Describe lo que pretendes realizar con al menos ${min} palabras (llevas ${words}). Puedes partir del ejemplo redactado.`,
          intentInput
        );
      }
      if (words > max) {
        return showValidationMessage(
          dataValidationMessage,
          `La descripción admite hasta ${max} palabras (llevas ${words}); resume lo esencial.`,
          intentInput
        );
      }
      return true;
    }

    intentInput?.addEventListener('input', refreshIntentField);
    intentField.querySelector('[data-intent-example]')?.addEventListener('click', () => {
      const sample = intentCopy().sample;
      intentInput.value = intentInput.value.trim() ? `${intentInput.value.trim()}\n${sample}` : sample;
      intentInput.dispatchEvent(new Event('input', { bubbles: true }));
      intentInput.focus();
    });
    let automaticTitle = element('tituloAutomaticoReserva');
    if (!automaticTitle) {
      automaticTitle = create('div', 'reservation-field-wide reservation-auto-title');
      automaticTitle.id = 'tituloAutomaticoReserva';
      automaticTitle.innerHTML = '<small>Nombre inteligente de tu solicitud</small><strong id="tituloSolicitudVista">Se completará con tu selección</strong>';
    }
    const profileMessage = create('div', 'reservation-profile-message');
    profileMessage.id = 'mensajePerfilReserva';
    profileMessage.hidden = true;
    profileMessage.setAttribute('role', 'alert');
    profileMessage.innerHTML = window.interfaz.html`Para enviar la solicitud debes completar tus datos institucionales en <a href="/profile/" target="_blank">Mi perfil</a>.`;
    dataGrid.appendChild(profileMessage);
    const dataValidationMessage = create('div', 'reservation-step-message');
    dataValidationMessage.hidden = true;
    dataValidationMessage.setAttribute('role', 'alert');
    dataGrid.appendChild(dataValidationMessage);
    const descriptionInput = element('descripcionProyecto');
    if (descriptionInput) {
      descriptionInput.required = false;
      descriptionInput.setAttribute('type', 'hidden');
    }
    const technicalFiles = element('archivosTecnicosReserva');
    const technicalFileInput = element('archivosTecnicos');
    const technicalFileList = element('archivosTecnicosLista');
    const technicalFileRequirement = element('archivosTecnicosRequisito');
    const technicalFileHelp = element('archivosTecnicosAyuda');
    const technicalFileNotes = element('indicacionesArchivos');
    const technicalFileDropZone = element('zonaCargaArchivos');
    const technicalFileStatus = element('archivosTecnicosEstado');
    const technicalFileProgress = element('archivosTecnicosProgreso');
    const technicalFileProgressBar = element('archivosTecnicosProgresoBarra');
    const technicalFileProgressText = element('archivosTecnicosProgresoTexto');
    const technicalFileProgressValue = element('archivosTecnicosPorcentaje');
    const technicalFileType = element('archivosTecnicosTipo');
    const technicalFileAttachments = element('archivosTecnicosAdjuntos');
    const technicalFileCount = element('archivosTecnicosCantidad');
    const technicalFileNoteCache = new Map();
    addActions(dataCard, 2);

    const resourceCard = panelCard(panels[2], '▣', gettext('Selección y disponibilidad'), gettext('El contenido de este paso cambia según el tipo de solicitud.'));
    const resourceGrid = create('div', 'rw-resource-grid');
    resourceCard.appendChild(resourceGrid);
    const resources = create('div', 'rw-resource-card');
    resources.innerHTML = window.interfaz.html`<h4>1. Recursos disponibles</h4>`;
    const resourcesTitle = resources.querySelector('h4');
    resources.appendChild(primaryResourceChoices);
    if (serviceCatalog) {
      serviceCatalog.classList.remove('reservation-legacy-region');
      resources.appendChild(serviceCatalog);
    }
    const equipmentCatalog = safelyMove(resources, 'unidadesEquipoCard');
    const serviceScope = safelyMove(resources, 'alcanceServicioReserva');
    const serviceModeGuidance = create('div', 'rw-mode-guidance');
    serviceModeGuidance.hidden = true;
    serviceModeGuidance.setAttribute('role', 'status');
    serviceScope?.appendChild(serviceModeGuidance);
    const complementaryChoices = create('fieldset', 'rw-resource-choices rw-resource-choices--complementary');
    complementaryChoices.innerHTML = window.interfaz.html`
      <legend>Recursos complementarios para diseñar en el laboratorio</legend>
      <p>Activa solo lo que utilizarás durante la sesión asistida.</p>
      <div class="rw-resource-choices__grid">
        <label data-resource-option="espacio" data-assisted-space-indicator><input type="checkbox" data-resource-kind-toggle="espacio" disabled><span><i class="fas fa-door-open"></i><strong>Espacio incluido</strong><small>Se reserva automáticamente porque diseñarás dentro del laboratorio.</small></span></label>
        <label data-resource-option="equipo"><input type="checkbox" data-resource-kind-toggle="equipo"><span><i class="fas fa-cogs"></i><strong>Equipos</strong><small>Separa los equipos que manipularás.</small></span></label>
        <label data-resource-option="software"><input type="checkbox" data-resource-kind-toggle="software"><span><i class="fas fa-laptop-code"></i><strong>Software</strong><small>Incluye un equipo compatible y su espacio.</small></span></label>
      </div>`;
    complementaryChoices.querySelectorAll('[data-resource-option]').forEach((option) => {
      if (!resourceAvailability[option.dataset.resourceOption]) option.remove();
    });
    resources.appendChild(complementaryChoices);
    const spaceSelection = create('div', 'rw-space-selection');
    spaceSelection.innerHTML = window.interfaz.html`<i class="fas fa-door-open" aria-hidden="true"></i><div><strong>Espacio incluido</strong><span>La solicitud reservará esta unidad como lugar de trabajo en el horario seleccionado.</span></div>`;
    resources.appendChild(spaceSelection);
    const spaceCatalog = safelyMove(resources, 'espaciosReservaCatalogo');
    const spaceInputs = Array.from(resources.querySelectorAll('[name="espacios_solicitados"]'));
    const spaceScopeInputs = Array.from(resources.querySelectorAll('[name="alcance_espacio"]'));
    if (serviceScope) resources.appendChild(serviceScope);
    if (technicalFiles) {
      technicalFiles.classList.add('is-inline-service');
      appendUnique(serviceScope || resources, technicalFiles);
    }
    // Detalles del trabajo (piezas, equipo y materiales) despues de la modalidad.
    const serviceWork = safelyMove(serviceScope || resources, 'trabajoServicioReserva');
    const softwareCatalog = safelyMove(resources, 'softwareReservaCatalogo');
    const serviceInputs = Array.from(serviceCatalog?.querySelectorAll('[name="servicios_solicitados"]') || []);
    const serviceModes = Array.from(resources.querySelectorAll('[name="modalidad_servicio"]'));
    const softwareInputs = Array.from(resources.querySelectorAll('[name="software_solicitado"]'));
    // ------------------------------------------------------------------
    // Práctica por proceso dentro del asistente: la planta marca lo que el
    // proceso exige (áreas, equipos con sus auxiliares, software e insumos),
    // muestra solo eso y la persona indica la materia prima y ajusta insumos.
    const processField = element('procesoReservaCampo');
    const processSelect = element('procesoReserva');
    const processRecipeInput = element('recetaReservaId');
    const processProductInput = element('productoReservaId');
    const processScaleField = processField?.querySelector('[data-process-scale]');
    const processScaleInput = element('materiaPrimaProceso');
    const processScaleHint = processField?.querySelector('[data-process-scale-hint]');
    const processFactorInput = element('factorProceso');
    const processSummary = processField?.querySelector('[data-process-summary]');
    const processCatalogNote = create('div', 'rw-process-note');
    processCatalogNote.hidden = true;
    processCatalogNote.setAttribute('role', 'status');
    resourcesTitle?.insertAdjacentElement('afterend', processCatalogNote);
    const processRoute = create('section', 'rw-process-route');
    processRoute.hidden = true;
    processRoute.setAttribute('aria-live', 'polite');
    processCatalogNote.insertAdjacentElement('afterend', processRoute);
    // En plantas piloto la receta se decide antes que la clasificación de uso.
    // El mismo paso sigue conservando propósito, actividad y participantes.
    if (processField && purposeSection) dataGrid.insertBefore(processField, purposeSection);
    // El cronograma por sesión: al programar varias sesiones, qué práctica y qué
    // proceso lleva cada una (las funciones van antes de validateStep).
    const schedulePlan = element('cronogramaReserva');
    const scheduleRows = schedulePlan?.querySelector('[data-schedule-rows]');
    const scheduleStatus = schedulePlan?.querySelector('[data-schedule-status]');
    const scheduleInput = element('cronogramaSesiones');
    const scheduleState = { fechas: [], filas: new Map(), timer: null, sequence: 0, periodo: '', omitidas: [], key: '' };
    const scheduleDescriptions = new Map();
    const processState = {
      seleccion: null, spaceIds: new Set(), unitIds: new Set(), softwareIds: new Set(),
      insumos: new Map(), showAll: false, timer: null, sequence: 0,
    };
    function processActive() {
      return Boolean(processState.seleccion) && state.type === 'recursos';
    }
    function processRequired() {
      return Boolean(processField && !processField.hidden && state.type === 'recursos');
    }
    function selectedProcessOption() {
      const option = processSelect?.selectedOptions?.[0];
      return option && option.dataset.recipeId ? option : null;
    }
    function selectedCatalogOption() {
      const option = processSelect?.selectedOptions?.[0];
      return option && option.value && option.value !== 'ninguno' ? option : null;
    }
    function syncProcessField() {
      if (!processField || !processSelect) return;
      const visible = state.type === 'recursos';
      processField.hidden = !visible;
      if (!visible && processSelect.value) {
        processSelect.value = '';
        clearProcessMode();
      }
    }
    function processFactor() {
      const option = selectedProcessOption();
      if (!option) return null;
      const base = Number(option.dataset.base) || 1;
      const cantidad = Number(processScaleInput?.value);
      if (!(cantidad > 0)) return null;
      return Math.round((cantidad / base) * 1000) / 1000;
    }
    function scheduleProcessRefresh() {
      if (!selectedProcessOption()) return;
      window.clearTimeout(processState.timer);
      processState.timer = window.setTimeout(() => fetchProcessSelection(), 250);
    }
    async function fetchProcessSelection() {
      const option = selectedProcessOption();
      const factor = processFactor();
      if (!option || !factor || !processField) return;
      if (processFactorInput) processFactorInput.value = String(factor);
      const url = new URL((processField.dataset.selectionUrlTemplate || '').replace('/0/', `/${option.dataset.recipeId}/`), window.location.href);
      url.searchParams.set('factor', String(factor));
      url.searchParams.set('personas', String(selectedParticipants.size + 1));
      url.searchParams.set('guia', '1');
      const sequence = processState.sequence + 1;
      processState.sequence = sequence;
      try {
        const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        const data = await response.json().catch(() => ({}));
        if (sequence !== processState.sequence) return;
        if (!response.ok || !data.success) throw new Error(data.error || 'No fue posible calcular el proceso.');
        processState.seleccion = data;
        processState.spaceIds = new Set((data.espacios || []).map((item) => String(item.id)));
        processState.unitIds = new Set((data.equipos || []).map((item) => String(item.id)));
        processState.softwareIds = new Set((data.software || []).map((item) => String(item.id)));
        processState.insumos = new Map((data.insumos || []).map((item) => [String(item.id), item]));
        renderProcessSummary();
        applyProcessMode();
      } catch (error) {
        if (processSummary) {
          processSummary.hidden = false;
          processSummary.innerHTML = window.interfaz.html`<p class="is-error"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i> ${escapeHtml(error.message)}</p>`;
        }
      }
    }
    function processSummaryText() {
      const sel = processState.seleccion;
      if (!sel || state.type !== 'recursos') return 'Sin proceso definido';
      return `${sel.proceso} · ${sel.escala} → ${sel.producto_esperado} · ${sel.espacios.length} áreas, ${sel.equipos.length} equipos, ${sel.insumos.length} insumos`;
    }
    function renderProcessSummary() {
      const sel = processState.seleccion;
      if (!processSummary || !sel) return;
      const s = sel.sesion || {};
      const faltantes = (sel.faltantes || []).length
        ? window.interfaz.html`<p class="is-warning"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i> La planta no tiene hoy: ${escapeHtml(sel.faltantes.join('; '))}. La solicitud se envía igual y el laboratorista decide.</p>`
        : '';
      processSummary.hidden = false;
      processSummary.innerHTML = window.interfaz.html`
        <div class="reservation-process__facts">
          <span><b>${escapeHtml(sel.escala)}</b><small>materia prima</small></span>
          <span><b>${escapeHtml(sel.producto_esperado)}</b><small>de ${escapeHtml(sel.producto)}</small></span>
          <span><b>${escapeHtml(String((s.horas || []).length))} h</b><small>de línea seguidas${s.dias_extra ? ` · sigue ${s.dias_extra} día${s.dias_extra === 1 ? '' : 's'} más` : ''}</small></span>
          <span><b>${escapeHtml(String(sel.personas_max || 1))}</b><small>personas como máximo por etapa</small></span>
        </div>
        <p>La planta marcará ${sel.espacios.length} área${sel.espacios.length === 1 ? '' : 's'}, ${sel.equipos.length} equipo${sel.equipos.length === 1 ? '' : 's'} con sus auxiliares${sel.software.length ? `, ${sel.software.length} software` : ''} y ${sel.insumos.length} insumo${sel.insumos.length === 1 ? '' : 's'} en el paso de recursos; al elegir la hora de inicio se toman las ${(s.horas || []).length} horas seguidas que la corrida necesita.</p>
        ${faltantes}`;
      const route = Array.isArray(sel.ruta) ? sel.ruta : [];
      processRoute.hidden = route.length === 0;
      processRoute.innerHTML = route.length ? window.interfaz.html`
        <header><div><small>Propuesta automática</small><strong>Ruta de elaboración y recursos necesarios</strong><p>Recorre horizontalmente las etapas. Los recursos obligatorios quedan marcados y protegidos; puedes ajustar cantidades y agregar complementarios.</p></div><span>${route.length} etapas</span></header>
        <div class="rw-process-route__viewport" tabindex="0" aria-label="Ruta horizontal del proceso ${escapeHtml(sel.proceso)}">
          <ol class="rw-process-route__track">
            ${route.map((stage) => window.interfaz.html`
              <li${stage.punto_critico ? ' class="is-critical"' : ''}>
                <span class="rw-process-route__number">${escapeHtml(String(stage.orden))}</span>
                <div><small>${escapeHtml(stage.simbolo)} ${escapeHtml(stage.tipo)}</small><strong>${escapeHtml(stage.nombre)}</strong>
                <p>${stage.espacio ? window.interfaz.html`<span><i class="fas fa-map-marker-alt"></i>${escapeHtml(stage.espacio)}</span>` : ''}${stage.equipo ? window.interfaz.html`<span><i class="fas fa-cog"></i>${escapeHtml(stage.equipo)}</span>` : ''}</p>
                <footer><span><i class="far fa-clock"></i>${escapeHtml(String(stage.duracion_min))} min${stage.espera_min ? ` + ${escapeHtml(String(stage.espera_min))} min de espera` : ''}</span>${stage.insumos?.length ? window.interfaz.html`<em>${escapeHtml(stage.insumos.join(', '))}</em>` : ''}${stage.punto_critico ? window.interfaz.html`<b>Punto crítico</b>` : ''}</footer></div>
              </li>`).join('')}
          </ol>
        </div>` : '';
    }
    function updateProcessCatalogNote() {
      const sel = processState.seleccion;
      if (!sel) return;
      processCatalogNote.hidden = false;
      processCatalogNote.innerHTML = window.interfaz.html`<i class="fas fa-industry" aria-hidden="true"></i><div><strong>${escapeHtml(sel.proceso)} · ${escapeHtml(sel.escala)}</strong><span>La planta marcó ${sel.espacios.length} áreas, ${sel.equipos.length} equipos y ${sel.insumos.length} insumos; lo obligatorio no se puede quitar. Ajusta las cantidades de los insumos si tu práctica lo requiere.</span></div><button type="button" data-process-show-all>${processState.showAll ? gettext('Mostrar solo lo del proceso') : gettext('Mostrar todos los recursos de la planta')}</button>`;
    }
    function applyProcessMode() {
      const sel = processState.seleccion;
      if (!sel || state.type !== 'recursos') return;
      modal.classList.add('is-process-selection-active');
      resources.classList.add('has-process-selection');
      spaceSelectedExplicitly = Boolean(resourceAvailability.espacio);
      equipmentSelectedExplicitly = true;
      state.resources.espacio = Boolean(resourceAvailability.espacio);
      state.resources.equipo = true;
      state.resources.software = processState.softwareIds.size > 0 && Boolean(resourceAvailability.software);
      const areasOption = spaceScopeInputs.find((input) => input.value === 'areas');
      if (areasOption) areasOption.checked = true;
      spaceInputs.forEach((input) => {
        const locked = processState.spaceIds.has(String(input.value));
        if (locked) input.dataset.processLocked = 'true';
        else delete input.dataset.processLocked;
        const card = input.closest('.reservation-space-item');
        card?.classList.toggle('is-process-locked', locked);
        card?.classList.toggle('rw-process-hidden', !locked && !processState.showAll);
        if (locked) input.checked = true;
        else if (!processState.showAll) input.checked = false;
      });
      window.reservaProcesoActivo = true;
      if (window.calendarState) window.calendarState.processHours = (sel.sesion?.horas || []).length;
      syncResourceChoices();
      syncSpaceScope();
      syncEquipmentAvailability();
      updateProcessCatalogNote();
      if (typeof window.renderCalendarSurface === 'function') window.renderCalendarSurface();
    }
    function applyProcessLocks() {
      if (!processActive()) return;
      let changed = false;
      form.querySelectorAll('.unidad-checkbox').forEach((input) => {
        const locked = processState.unitIds.has(String(input.value));
        const row = input.closest('[data-unit-row]');
        if (locked) {
          input.dataset.processLocked = 'true';
          if (input.disabled && input.dataset.rwDisabledByFlow === 'true') {
            input.disabled = false;
            delete input.dataset.rwDisabledByFlow;
          }
          if (!input.checked) { input.checked = true; changed = true; }
        } else {
          delete input.dataset.processLocked;
          if (!processState.showAll && input.checked) { input.checked = false; changed = true; }
        }
        row?.classList.toggle('is-process-locked', locked);
        row?.classList.toggle('rw-process-hidden', !locked && !processState.showAll);
      });
      equipmentGroups().forEach((group) => {
        const rows = Array.from(group.querySelectorAll('[data-unit-row]'));
        const anyLocked = rows.some((row) => row.classList.contains('is-process-locked'));
        group.classList.toggle('is-process-locked', anyLocked);
        group.classList.toggle('rw-process-hidden', !anyLocked && !processState.showAll);
      });
      equipmentCatalog?.querySelectorAll('[data-equipment-category]').forEach((section) => {
        const groups = Array.from(section.querySelectorAll('[data-equipment-row]'));
        section.classList.toggle('rw-process-hidden', groups.length > 0 && groups.every((group) => group.classList.contains('rw-process-hidden')));
      });
      if (changed && typeof window.actualizarSeleccionUnidades === 'function') window.actualizarSeleccionUnidades();
      softwareInputs.forEach((input) => {
        if (processState.softwareIds.has(String(input.value)) && !input.disabled && !input.checked) input.checked = true;
      });
      // Insumos del proceso: marcados con su cantidad; los obligatorios no se quitan.
      processState.insumos.forEach((item, id) => {
        const card = form.querySelector(`.reservation-consumable[data-consumible-id="${id}"]:not(.is-mirror)`);
        if (!card) return;
        const check = card.querySelector('.reservation-consumable__check');
        const quantity = card.querySelector('.reservation-consumable__quantity');
        if (!check) return;
        if (item.obligatorio) {
          check.dataset.processLocked = 'true';
          card.classList.add('is-process-locked');
        } else {
          delete check.dataset.processLocked;
          card.classList.remove('is-process-locked');
        }
        if (!check.checked) {
          check.disabled = false;
          check.checked = true;
          card.classList.add('is-selected');
        }
        if (quantity && quantity.dataset.processQuantity !== String(item.cantidad)) {
          quantity.disabled = false;
          quantity.value = String(item.cantidad);
          quantity.dataset.processQuantity = String(item.cantidad);
        }
        card.classList.remove('rw-process-hidden');
      });
      form.querySelectorAll('.reservation-consumable:not(.is-mirror)').forEach((card) => {
        if (!processState.insumos.has(String(card.dataset.consumibleId))) {
          card.classList.toggle('rw-process-hidden', !processState.showAll);
        }
      });
      updateConsumableGuidance();
    }
    function clearProcessMode() {
      const wasActive = Boolean(processState.seleccion);
      processState.seleccion = null;
      processState.spaceIds = new Set();
      processState.unitIds = new Set();
      processState.softwareIds = new Set();
      processState.insumos = new Map();
      processState.showAll = false;
      if (processRecipeInput) processRecipeInput.value = '';
      if (processProductInput) processProductInput.value = '';
      if (processFactorInput) processFactorInput.value = '';
      if (processScaleField) processScaleField.hidden = true;
      if (processSummary) { processSummary.hidden = true; processSummary.innerHTML = ''; }
      processCatalogNote.hidden = true;
      processRoute.hidden = true;
      processRoute.innerHTML = '';
      modal.classList.remove('is-process-selection-active');
      resources.classList.remove('has-process-selection');
      window.reservaProcesoActivo = false;
      if (window.calendarState) window.calendarState.processHours = 0;
      if (!wasActive) return;
      form.querySelectorAll('[data-process-locked]').forEach((input) => delete input.dataset.processLocked);
      form.querySelectorAll('.is-process-locked').forEach((node) => node.classList.remove('is-process-locked'));
      form.querySelectorAll('.rw-process-hidden').forEach((node) => node.classList.remove('rw-process-hidden'));
      form.querySelectorAll('.reservation-consumable__quantity[data-process-quantity]').forEach((input) => delete input.dataset.processQuantity);
      syncSpaceScope();
      syncEquipmentAvailability();
      updateConsumableGuidance();
      if (typeof window.renderCalendarSurface === 'function') window.renderCalendarSurface();
    }
    processSelect?.addEventListener('change', () => {
      prioritizePublishedGuides();
      const catalogOption = selectedCatalogOption();
      const option = selectedProcessOption();
      clearProcessMode();
      if (processProductInput) processProductInput.value = catalogOption?.dataset.productId || '';
      if (processRecipeInput) processRecipeInput.value = option?.dataset.recipeId || '';
      if (processScaleField) processScaleField.hidden = !option;
      if (!catalogOption) return;
      if (!option) {
        if (processSummary) {
          processSummary.hidden = false;
          processSummary.innerHTML = window.interfaz.html`<p><i class="fas fa-box-open" aria-hidden="true"></i> <b>${escapeHtml(catalogOption.dataset.producto || catalogOption.textContent.trim())}</b> pertenece al catálogo institucional. Su proceso técnico está pendiente de configuración; selecciona manualmente las áreas, equipos, software e insumos que necesitas.</p>`;
        }
        return;
      }
      if (processScaleInput) processScaleInput.value = option.dataset.base || '1';
      if (processScaleHint) {
        processScaleHint.textContent = `${option.dataset.unidadBase || 'unidades'} · corrida base: ${option.dataset.base} · rinde ${option.dataset.rinde} ${option.dataset.unidadProducto} de ${option.dataset.producto} por corrida`;
      }
      fetchProcessSelection();
    });
    processScaleInput?.addEventListener('input', scheduleProcessRefresh);
    processCatalogNote.addEventListener('click', (event) => {
      if (!event.target.closest('[data-process-show-all]')) return;
      processState.showAll = !processState.showAll;
      applyProcessMode();
    });
    // Lo que el proceso exige no se desmarca con un clic.
    form.addEventListener('click', (event) => {
      const input = event.target.closest('input[data-process-locked]');
      if (input) event.preventDefault();
    }, true);

    if (!equipmentCatalog && !softwareCatalog && !resourceAvailability.espacio) {
      const fallback = create('div', 'rw-empty-note', gettext('La unidad todavía no tiene recursos activos para este tipo de solicitud. Puedes continuar y registrar el requerimiento para revisión.'));
      resources.appendChild(fallback);
    }
    resourceGrid.appendChild(resources);

    const calendar = create('div', 'rw-resource-card');
    calendar.innerHTML = window.interfaz.html`<h4>2. Fecha y horario</h4>`;
    const calendarParticipantSummary = create('aside', 'reservation-calendar-participants');
    calendarParticipantSummary.innerHTML = window.interfaz.html`<i class="fas fa-users" aria-hidden="true"></i><div><small>Personas consideradas para disponibilidad y capacidad</small><strong data-calendar-participant-count>1 persona · solo el solicitante</strong></div><button type="button"><i class="fas fa-user-edit"></i> Editar participantes</button>`;
    calendarParticipantSummary.querySelector('button')?.addEventListener('click', () => {
      showStep(2, true);
      window.requestAnimationFrame(() => participantsContainer?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }));
    });
    calendar.appendChild(calendarParticipantSummary);
    // Servicios: urgencia y propuesta de fecha antes del calendario, que solo
    // se despliega si la persona quiere elegir otra fecha.
    const serviceSchedule = safelyMove(calendar, 'entregaServicioReserva');
    let showCalendarForService = false;
    const integratedCalendar = create('div', 'reservation-calendar-planner rw-integrated-calendar');
    safelyMove(integratedCalendar, 'frecuenciaReservaCampo');
    const originalCalendarBox = element('monthGrid')?.closest('.cal-box');
    if (originalCalendarBox) integratedCalendar.appendChild(originalCalendarBox);
    calendar.appendChild(integratedCalendar);
    resourceGrid.appendChild(calendar);
    const responsibleCatalog = safelyMove(resources, 'responsablesReservaCatalogo');
    const resourceValidationMessage = create('div', 'reservation-step-message rw-resource-validation');
    resourceValidationMessage.hidden = true;
    resourceValidationMessage.setAttribute('role', 'alert');
    resourceCard.appendChild(resourceValidationMessage);
    addActions(resourceCard, 3);

    const requirementsCard = panelCard(panels[3], '◇', gettext('Requisitos de la solicitud'), gettext('Este paso mostrará inventario para reservas o cotización y pago para servicios.'));
    const requirementsGrid = create('div', 'rw-grid');
    requirementsCard.appendChild(requirementsGrid);
    const inventoryCatalog = safelyMove(requirementsGrid, 'consumiblesReservaCatalogo');
    const serviceQuote = element('cotizacionServicioReserva');
    if (serviceQuote) resources.insertBefore(serviceQuote, responsibleCatalog || null);
    const servicePayment = safelyMove(requirementsGrid, 'pagoServicioSeccion');
    // Apoyo del laboratorio: nota fija. El campo oculto "requisitos_especiales"
    // solo lo usa el servidor para anotar el software por habilitar.
    const specialRequirementsField = safelyMove(requirementsGrid, 'apoyoLaboratorioNota');

    // ------------------------------------------------------------------
    // Cascada de recursos (ruta "recursos"): primero donde, despues con que,
    // luego software y por ultimo insumos. Los catalogos existentes se
    // reordenan y se filtran por las relaciones publicadas por la unidad;
    // no se vuelven a construir.
    // ------------------------------------------------------------------
    // Cantidades de insumos indicadas por la persona en la cotizacion del servicio.
    const serviceQuantities = {};
    const serviceConsumablesInput = document.createElement('input');
    serviceConsumablesInput.type = 'hidden';
    serviceConsumablesInput.name = 'consumibles_servicio';
    serviceConsumablesInput.value = '{}';
    form.appendChild(serviceConsumablesInput);
    // Los programas por instalar se piden dentro de la tarjeta de cada equipo
    // que lo admite; aqui solo viaja el texto consolidado ("Equipo: programa").
    const softwareAdicionalTextoInput = document.createElement('input');
    softwareAdicionalTextoInput.type = 'hidden';
    softwareAdicionalTextoInput.name = 'software_adicional_texto';
    form.appendChild(softwareAdicionalTextoInput);
    const cascadeCatalogs = {
      espacio: spaceCatalog,
      equipo: equipmentCatalog,
      software: softwareCatalog,
      insumos: inventoryCatalog,
    };
    (function arrangeCascade() {
      // Cada catalogo trae su propia cabecera: espacio, equipo (con software e
      // insumos en la tarjeta) y los insumos que la unidad no ligo a un equipo.
      ['espacio', 'equipo', 'insumos'].forEach((key) => {
        const catalog = cascadeCatalogs[key];
        if (catalog) resources.appendChild(catalog);
      });
      // El software vive en la tarjeta de su equipo; el catalogo general solo
      // sirve al servicio con diseno asistido.
      if (softwareCatalog) resources.appendChild(softwareCatalog);
      if (responsibleCatalog) resources.appendChild(responsibleCatalog);
    })();

    const finalActivityIdentity = create('section', 'reservation-final-activity');
    finalActivityIdentity.id = 'identificacionFinalActividad';
    finalActivityIdentity.hidden = true;
    finalActivityIdentity.innerHTML = window.interfaz.html`
      <header class="reservation-final-activity__header">
        <span><i class="fas fa-magic"></i></span>
        <div><small>Identificación al final · datos ya disponibles</small><h3>Confirma el nombre de la actividad</h3><p>El sistema propone un nombre después de conocer el tipo de práctica y los recursos elegidos. Puedes corregirlo antes de generar la guía.</p></div>
        <span class="reservation-final-activity__badge"><i class="fas fa-robot"></i> Asistencia automática</span>
      </header>
      <div class="reservation-final-activity__suggestion" data-activity-suggestion-box>
        <span><small>Sugerencia basada en tu solicitud</small><strong data-activity-suggestion-text>Se calculará al llegar a este paso</strong></span>
        <button type="button" class="rw-button rw-button--gold" data-use-activity-suggestion><i class="fas fa-magic"></i> Usar sugerencia</button>
      </div>
      <div class="reservation-final-activity__fields" data-final-activity-fields>
        <label class="reservation-context-field reservation-context-field--wide" data-subject-catalog-field hidden><span>Asignatura registrada en la unidad</span><select class="form-control" name="asignatura_id"><option value="">Sin registrar: escribe el nombre abajo</option></select><small>Al elegirla, la guía general lleva el cronograma de sus temas y cada sesión nace con su guía prellenada.</small></label>
        <label class="reservation-context-field reservation-context-field--wide" data-final-subject-field><span>Asignatura o módulo formativo *</span><input class="form-control" type="text" name="guia_asignatura" maxlength="220" placeholder="Ej. Química Analítica · Biología Celular · Diseño y fabricación digital"><small>Nombre oficial de la asignatura o módulo al que pertenece la práctica. No es el nombre de la práctica.</small></label>
      </div>
      <div class="reservation-activity-naming" data-activity-naming>
        <small><i class="fas fa-signature"></i> ¿Cómo nombrar la práctica? Elige un enfoque: el patrón se copia al campo y solo reemplazas los corchetes.</small>
        <div class="reservation-activity-naming__options">
          <button type="button" data-naming-pattern="[Problema real]: [Técnica académica]"><b>Aplicado o por retos</b><span>[Problema real]: [Técnica académica]</span><em>Control de calidad en la industria alimentaria: Análisis de acidez en leche comercial</em></button>
          <button type="button" data-naming-pattern="[Nombre de la técnica] aplicada a [Caso de estudio]"><b>Técnico o metodológico</b><span>[Nombre de la técnica] aplicada a [Caso de estudio]</span><em>Cromatografía en capa fina para la separación de pigmentos fotosintéticos</em></button>
          <button type="button" data-naming-pattern="[Proceso o fenómeno] de [Sustancia u objeto]"><b>Directo u objetivo</b><span>[Proceso o fenómeno] de [Sustancia u objeto]</span><em>Determinación de la aceleración de la gravedad mediante un péndulo</em></button>
        </div>
      </div>
      <div class="reservation-step-message reservation-final-activity__error" data-final-activity-error hidden role="alert"></div>`;
    requirementsCard.appendChild(finalActivityIdentity);

    const guideBuilder = create('section', 'reservation-guide-builder');
    guideBuilder.id = 'guiaPracticaIntegrada';
    guideBuilder.hidden = true;
    guideBuilder.innerHTML = window.interfaz.html`
      <div class="reservation-guide-builder__institutional">
        <div class="reservation-guide-builder__logo">${guideLogoUrl ? `<img src="${escapeHtml(guideLogoUrl)}" alt="${escapeHtml(guideInstitutionName)}">` : `<strong style="color:#fff">${escapeHtml(guideInstitutionCode)}</strong>`}</div>
        <div><strong>FORMATO GUÍA DE PRÁCTICA</strong><span>${escapeHtml(guideInstitutionName)}</span></div>
        <div><b>Código: UPEC-P10-S01-FT04</b><span>Revisión: 01</span><span>Versión: se asigna al guardar</span></div>
      </div>
      <header class="reservation-guide-builder__header">
        <span class="reservation-guide-builder__icon"><i class="fas fa-book-open"></i></span>
        <div><small>Formato institucional FT04 · paso final de la solicitud</small><h3 data-guide-auto="title">Guía de práctica por completar</h3><p>El sistema ya incorporó horario, participantes y recursos. Completa únicamente la asignatura y los apartados académicos faltantes.</p></div>
        <span class="reservation-guide-builder__status"><i class="fas fa-pencil-alt"></i> Borrador académico</span>
      </header>
      <section class="reservation-guide-builder__general">
        <div class="reservation-guide-builder__section-title"><b>01</b><span><strong>Datos generales</strong><small>Los datos automáticos se actualizan mientras completas la solicitud.</small></span></div>
        <div class="reservation-guide-builder__general-grid">
          <div><small>Código de la guía</small><strong data-guide-auto="code">Se genera al guardar</strong></div>
          <div><small>Asignatura o módulo</small><strong data-guide-auto="subject">Se indica arriba, en la identificación</strong></div>
          <div><small>Carrera / semestre</small><strong data-guide-auto="career">Se toma del perfil y la actividad</strong></div>
          <div><small>Docente responsable</small><strong data-guide-auto="responsible">Solicitante principal</strong></div>
          <div><small>Laboratorio</small><strong data-guide-auto="laboratory">Unidad de laboratorio</strong></div>
          <div><small>Categoría de uso</small><strong data-guide-auto="purpose">Docencia y práctica curricular</strong></div>
          <div><small>Duración estimada</small><strong data-guide-auto="duration">Se calcula en el paso 3</strong></div>
          <div><small>N.º de estudiantes</small><strong data-guide-auto="participants">1 persona</strong></div>
        </div>
      </section>
      <div class="reservation-guide-builder__section-title reservation-guide-builder__section-title--resources"><b>05</b><span><strong>Equipos, software, materiales e insumos requeridos</strong><small>Se incorporan desde las selecciones verificadas de la reserva.</small></span></div>
      <div class="reservation-guide-builder__automatic reservation-guide-builder__automatic--resources">
        <div><small>Equipos</small><strong data-guide-auto="equipment">Se seleccionan en el paso 3</strong></div>
        <div><small>Software y licencias</small><strong data-guide-auto="software">Se seleccionan en el paso 3</strong></div>
        <div><small>Materiales e insumos</small><strong data-guide-auto="consumables">Se toman de la reserva</strong></div>
      </div>
      <p class="reservation-guide-builder__automatic-note"><i class="fas fa-magic"></i> Estos datos provienen de la selección final de la reserva. Equipos, software e insumos no se vuelven a escribir y quedarán trazados en la misma versión de la guía.</p>
      <div class="reservation-guide-builder__suggestion">
        <span><i class="fas fa-lightbulb"></i></span>
        <div><strong>Genera un borrador académico editable</strong><small>Usaremos el nombre, el tipo de práctica y los recursos seleccionados para completar únicamente los campos vacíos. Revisa y ajusta el contenido antes de firmarlo.</small><em data-guide-suggestion-status>La propuesta nunca sobrescribe lo que ya escribiste.</em></div>
        <button type="button" class="rw-button rw-button--gold" data-guide-suggest><i class="fas fa-magic"></i> Completar campos sugeridos</button>
      </div>
      <div class="reservation-guide-content">
        <div class="reservation-guide-content__intro">
          <span><i class="fas fa-file-alt"></i></span>
          <div><strong>Redacta la guía sobre su propio formato</strong><small>Resultado de aprendizaje, objetivos, fundamento, precauciones, procedimiento, resultados y criterios se escriben directamente en el documento FT04: con subtítulos, listas, tablas e imágenes, y pegando desde Word. El encabezado, los datos de la reserva, las políticas y las firmas quedan protegidos.</small><em data-guide-completeness>Faltan: resultado de aprendizaje, objetivos y procedimiento.</em></div>
          <button type="button" class="rw-button rw-button--primary" data-guide-open><i class="fas fa-edit"></i> Revisar y completar guía</button>
        </div>
        <input type="hidden" name="guia_formato_procedimiento" value="numerado">
        <fieldset class="reservation-guide-content__refs" hidden>
          <legend>Materiales complementarios y bibliografía (se editan dentro de la guía)</legend>
          <label class="reservation-guide-field reservation-guide-field--wide"><span>Bibliografía <em>(opcional)</em></span><textarea name="guia_bibliografia" rows="5" disabled placeholder="Pega aquí tus entradas BibTeX ya listas (@article{…}, @book{…}, @inproceedings{…}, @online{…}); también puedes escribir una referencia por línea."></textarea><small>El sistema convierte cada entrada BibTeX al estilo IEEE, numerada [1], [2]… en el HTML y en el PDF. Exporta el BibTeX desde tu gestor de referencias (Zotero, Mendeley, Google Académico) y pégalo tal cual.</small></label>
          <label class="reservation-guide-field reservation-guide-field--wide"><span>Materiales complementarios <em>(opcional)</em></span><span class="reservation-guide-rich-toolbar" data-materials-toolbar><button type="button" data-material-template>+ Enlace</button></span><textarea name="guia_materiales_complementarios" rows="2" disabled placeholder="Un recurso por línea: Título | https://enlace"></textarea><small>Videos, lecturas, simuladores o datos de apoyo; cada línea se muestra como enlace en la guía.</small></label>
        </fieldset>
        <input type="hidden" name="guia_formato_contenido" value="html">
        <input type="hidden" name="guia_imagenes_token" value="">
        <input type="hidden" name="guia_firmas" value="">
        <input type="hidden" name="guia_resultado_aprendizaje" data-guide-field="resultado_aprendizaje" data-guide-required data-guide-label="Resultado de aprendizaje">
        <input type="hidden" name="guia_objetivos" data-guide-field="objetivos" data-guide-required data-guide-label="Objetivos de la práctica">
        <input type="hidden" name="guia_fundamento_teorico" data-guide-field="fundamento_teorico" data-guide-label="Fundamento teórico">
        <input type="hidden" name="guia_medidas_seguridad" data-guide-field="medidas_seguridad" data-guide-label="Precauciones de la actividad">
        <input type="hidden" name="guia_procedimiento" data-guide-field="procedimiento" data-guide-required data-guide-label="Procedimiento">
        <input type="hidden" name="guia_resultados_esperados" data-guide-field="resultados_esperados" data-guide-label="Resultados esperados">
        <input type="hidden" name="guia_criterios_evaluacion" data-guide-field="criterios_evaluacion" data-guide-label="Criterios de evaluación">
      </div>
      <div class="reservation-guide-builder__options">
        <label><input type="checkbox" name="guia_permite_descarga" value="1" checked disabled><span><strong>Permitir descarga del PDF aprobado</strong><small>Los participantes podrán conservar una copia de la versión vigente.</small></span></label>
        <label><input type="checkbox" name="guia_solicitar_publicacion" value="1" disabled><span><strong>Solicitar publicación en la unidad</strong><small>La guía podrá mostrarse en Recursos y prácticas cuando sea aprobada.</small></span></label>
      </div>
      <div class="reservation-step-message reservation-guide-builder__error" data-guide-error hidden role="alert"></div>`;
    requirementsCard.appendChild(guideBuilder);

    const guideFinalReview = create('section', 'reservation-guide-final');
    guideFinalReview.id = 'revisionFinalGuiaIntegrada';
    guideFinalReview.hidden = true;
    guideFinalReview.innerHTML = window.interfaz.html`
      <header>
        <span><i class="fas fa-file-signature"></i></span>
        <div><small>Paso final de la guía FT04</small><h3>Firma electrónica de la guía</h3><p>Abre «Revisar y completar guía», comprueba la vista final (o el PDF) y pulsa «Contenido revisado»; después confirma tu firma aquí.</p></div>
      </header>
      <div class="reservation-guide-final__actions">
        <label><input type="checkbox" name="guia_confirmada_solicitante" value="1" required disabled data-guide-confirm><span><strong>Firmo electrónicamente como autor/a esta versión</strong><small>La aceptación se guardará con tu usuario, fecha, reserva y huella de integridad. Si cambia cualquier dato, deberá firmarse nuevamente.</small></span></label>
      </div>
      <div class="reservation-step-message reservation-guide-final__error" data-guide-final-error hidden role="alert"></div>`;
    requirementsCard.appendChild(guideFinalReview);

    const guidePreview = create('div', 'reservation-guide-preview');
    guidePreview.id = 'vistaPreviaGuiaIntegrada';
    guidePreview.hidden = true;
    guidePreview.setAttribute('role', 'dialog');
    guidePreview.setAttribute('aria-modal', 'true');
    guidePreview.setAttribute('aria-labelledby', 'vistaPreviaGuiaTitulo');
    guidePreview.innerHTML = window.interfaz.html`
      <div class="reservation-guide-preview__dialog">
        <header><div><small>Formato institucional FT04</small><h3 id="vistaPreviaGuiaTitulo">Revisar y completar guía</h3><p>Edita solo los apartados autorizados, directamente donde aparecen en la guía.</p></div><div class="reservation-guide-preview__modes guide-editor-keep" role="tablist" aria-label="Modo de la guía"><button type="button" class="is-on" data-guide-mode="edicion" role="tab" aria-selected="true"><i class="fas fa-pencil-alt"></i> Editar contenido</button><button type="button" data-guide-mode="final" role="tab" aria-selected="false"><i class="fas fa-eye"></i> Vista final</button></div><button type="button" data-guide-preview-close aria-label="Cerrar"><i class="fas fa-times"></i></button></header>
        <div class="reservation-guide-preview__status" data-guide-preview-status hidden></div>
        <div class="reservation-guide-preview__document" data-guide-preview-document></div>
        <footer class="guide-editor-keep"><small class="reservation-guide-preview__footnote" data-guide-preview-footnote></small><span class="reservation-guide-preview__pending" data-guide-pending hidden><i class="fas fa-spinner fa-spin"></i> Cargando imágenes…</span><button type="button" class="rw-button" data-guide-pdf-preview><i class="fas fa-file-pdf"></i> Ver documento</button><button type="button" class="rw-button rw-button--primary" data-guide-preview-accept><i class="fas fa-check"></i> Contenido revisado</button></footer>
      </div>`;
    form.appendChild(guidePreview);

    const guideInputs = Array.from(guideBuilder.querySelectorAll('textarea, input, select'));
    const guideRequiredInputs = Array.from(guideBuilder.querySelectorAll('[data-guide-required]'));
    const guideSubjectInput = finalActivityIdentity.querySelector('[name="guia_asignatura"]');
    // Las asignaturas registradas en la unidad: al elegir una, su nombre llena la asignatura de la guía.
    const subjectCatalogField = finalActivityIdentity.querySelector('[data-subject-catalog-field]');
    const subjectCatalogSelect = subjectCatalogField?.querySelector('[name="asignatura_id"]');
    const subjectCatalog = (() => {
      try { return JSON.parse(document.getElementById('asignaturasDocente')?.textContent || '[]'); } catch (error) { return []; }
    })();
    if (subjectCatalogField && subjectCatalogSelect && Array.isArray(subjectCatalog) && subjectCatalog.length) {
      subjectCatalog.forEach((item) => {
        const option = document.createElement('option');
        option.value = String(item.id);
        const totalTemas = Array.isArray(item.temas) ? item.temas.length : (Number(item.temas) || 0);
        option.textContent = `${item.codigo} · ${item.nombre}${totalTemas ? ` (${totalTemas} temas)` : ''}`;
        option.dataset.nombre = item.nombre;
        subjectCatalogSelect.appendChild(option);
      });
      subjectCatalogField.hidden = false;
      subjectCatalogSelect.addEventListener('change', () => {
        const selected = subjectCatalogSelect.selectedOptions[0];
        if (!selected || !selected.value || !guideSubjectInput) return;
        guideSubjectInput.value = selected.dataset.nombre || selected.textContent;
        guideSubjectInput.dispatchEvent(new Event('input', { bubbles: true }));
      });
    }
    const guideSuggestionButton = guideBuilder.querySelector('[data-guide-suggest]');
    const guideSuggestionStatus = guideBuilder.querySelector('[data-guide-suggestion-status]');
    const guideConfirmation = guideFinalReview.querySelector('[data-guide-confirm]');
    const guideError = guideBuilder.querySelector('[data-guide-error]');
    const guideFinalError = guideFinalReview.querySelector('[data-guide-final-error]');
    const guidePreviewStatus = guidePreview.querySelector('[data-guide-preview-status]');
    const guidePreviewAccept = guidePreview.querySelector('[data-guide-preview-accept]');
    let guidePreviewTrigger = null;
    let guidePreviewSignature = '';
    let guideEditor = null;
    const guideFieldInputs = Array.from(guideBuilder.querySelectorAll('[data-guide-field]'));
    const guideTokenInput = guideBuilder.querySelector('[name="guia_imagenes_token"]');
    const guideSignaturesInput = guideBuilder.querySelector('[name="guia_firmas"]');
    if (guideTokenInput) {
      guideTokenInput.value = (window.crypto && window.crypto.randomUUID)
        ? window.crypto.randomUUID().replace(/-/g, '')
        : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
    }

    const quoteResult = element('resultadoCotizacionServicio');
    const quoteRecap = form.querySelector('[data-quote-recap]');
    const piecesInput = element('cantidadPiezasServicio');
    const serviceEquipmentBox = form.querySelector('[data-service-equipment]');
    const serviceEquipmentOptions = form.querySelector('[data-service-equipment-options]');
    const serviceMaterialsList = form.querySelector('[data-service-materials-list]');
    const serviceMaterialsEmpty = form.querySelector('[data-service-materials-empty]');
    const serviceMaterialsInput = element('materialesSeleccionadosServicio');
    // Quien no sabe cuanto material necesita lo declara: sin eso, la cantidad
    // es obligatoria, porque sin ella la estimacion no vale.
    const serviceEquipmentInput = element('equipoServicio');
    const urgencyInputs = Array.from(form.querySelectorAll('[name="urgencia_servicio"]'));
    const proposeButton = element('proponerEntregaServicio');
    const otherDateButton = element('elegirOtraFechaServicio');
    const proposalBox = form.querySelector('[data-delivery-proposal]');
    const deliveryDateInput = element('fechaEntregaPrevista');
    // Estado del trabajo del servicio: propuesta de entrega pendiente.
    let proposalPending = null;
    const quotePayment = element('pagoServicioReserva');
    const quoteAcceptance = element('aceptarCotizacionServicio');
    const paymentMethod = element('metodoPagoServicio');
    const resourceCost = element('costoReferencialRecursos');
    const resourceCostResult = element('resultadoCostoReferencialRecursos');
    const resourceReferenceRates = {
      espacio: Number(modal.dataset.referenceSpaceHour || 0),
      equipo: Number(modal.dataset.referenceEquipmentHour || 0),
      software: Number(modal.dataset.referenceSoftwareHour || 0),
      acompanamiento: Number(modal.dataset.referenceSupportHour || 0),
      // Regla institucional fija, también para perfiles externos o sin aprobar.
      aporte: 100,
      // IVA: solo cuando la unidad lo activa; se muestra como fila propia.
      taxApplies: modal.dataset.taxApplies === 'true',
      taxRate: Number(modal.dataset.taxRate || 0)
    };
    function money(value) {
      return `$${(Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100).toFixed(2)}`;
    }
    function taxFor(base) {
      return resourceReferenceRates.taxApplies
        ? Math.round((base * resourceReferenceRates.taxRate / 100 + Number.EPSILON) * 100) / 100 : 0;
    }
    let currentQuote = null;

    const consumableSelection = element('consumiblesSeleccionados');
    // El catalogo de insumos vive en el paso 3 (cascada) y sus tarjetas se
    // mueven a la tarjeta de su equipo: se consultan en todo el formulario.
    const consumableInputs = Array.from(form.querySelectorAll('.reservation-consumable__quantity'));
    const consumableChecks = Array.from(form.querySelectorAll('.reservation-consumable__check'));
    const consumableCatalog = element('catalogoConsumiblesOpciones');
    // Sin opciones de provision: marcar un insumo lo solicita a la unidad y no
    // marcar ninguno registra la reserva sin insumos.
    const provisionInput = element('provisionConsumibles');
    const consumableCompatibility = form.querySelector('[data-consumable-compatibility]');
    const inventoryOffered = inventoryCatalog?.dataset.moduleEnabled === 'true'
      && Number(inventoryCatalog.dataset.catalogCount || 0) > 0;
    let unitRegulation = {};
    try {
      unitRegulation = JSON.parse(element('unitRegulationData')?.textContent || '{}');
    } catch (_error) {
      unitRegulation = {};
    }
    const materialViewer = element('visorMaterialReserva');
    const materialViewerImage = element('visorMaterialImagen');
    const materialViewerTitle = element('visorMaterialTitulo');
    let materialViewerTrigger = null;
    if (materialViewer && materialViewer.parentElement !== document.body) {
      document.body.appendChild(materialViewer);
    }

    function closeMaterialViewer() {
      if (!materialViewer) return;
      materialViewer.hidden = true;
      materialViewer.classList.remove('is-layout');
      document.body.classList.remove('reservation-viewer-open');
      if (materialViewerImage) materialViewerImage.src = '';
      materialViewerTrigger?.focus();
      materialViewerTrigger = null;
    }

    form.addEventListener('click', (event) => {
      const button = event.target.closest('[data-material-image]');
      if (!button || !materialViewer || !materialViewerImage) return;
      event.preventDefault();
      materialViewerTrigger = button;
      materialViewerImage.src = button.dataset.materialImage;
      materialViewerImage.alt = button.dataset.materialName || 'Imagen del catálogo';
      if (materialViewerTitle) materialViewerTitle.textContent = button.dataset.materialName || 'Imagen del catálogo';
      const layoutMode = button.dataset.materialViewerMode === 'layout';
      materialViewer.classList.toggle('is-layout', layoutMode);
      document.body.classList.toggle('reservation-viewer-open', layoutMode);
      materialViewer.hidden = false;
      materialViewer.querySelector('[data-material-viewer-close]')?.focus();
    });
    materialViewer?.addEventListener('click', (event) => {
      if (event.target === materialViewer || event.target.closest('[data-material-viewer-close]')) {
        closeMaterialViewer();
      }
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && materialViewer && !materialViewer.hidden) closeMaterialViewer();
    });

    const tutorialViewer = element('visorTutorialReserva');
    const tutorialFrame = element('visorTutorialIframe');
    const tutorialTitle = element('visorTutorialTitulo');
    const tutorialDescription = element('visorTutorialDescripcion');
    let tutorialTrigger = null;
    if (tutorialViewer && tutorialViewer.parentElement !== document.body) {
      document.body.appendChild(tutorialViewer);
    }

    function youtubeVideoId(rawUrl) {
      if (!rawUrl) return '';
      try {
        const url = new URL(rawUrl, window.location.origin);
        if (!['http:', 'https:'].includes(url.protocol)) return '';
        const host = url.hostname.toLowerCase().replace(/^www\./, '');
        let candidate = '';
        if (host === 'youtu.be') candidate = url.pathname.split('/').filter(Boolean)[0] || '';
        if (['youtube.com', 'm.youtube.com', 'youtube-nocookie.com'].includes(host)) {
          candidate = url.searchParams.get('v') || '';
          if (!candidate) {
            const parts = url.pathname.split('/').filter(Boolean);
            if (['embed', 'shorts', 'live'].includes(parts[0])) candidate = parts[1] || '';
          }
        }
        return /^[A-Za-z0-9_-]{11}$/.test(candidate) ? candidate : '';
      } catch (_error) {
        return '';
      }
    }

    function closeTutorialViewer() {
      if (!tutorialViewer) return;
      tutorialViewer.hidden = true;
      if (tutorialFrame) tutorialFrame.src = 'about:blank';
      tutorialTrigger?.focus();
      tutorialTrigger = null;
    }

    types.querySelectorAll('[data-generic-tutorial]').forEach((button) => {
      const tutorialKind = button.dataset.genericTutorial;
      const rawUrl = tutorialKind === 'servicio'
        ? modal.dataset.serviceTutorialUrl
        : modal.dataset.resourceTutorialUrl;
      const videoId = youtubeVideoId(rawUrl);
      if (!videoId) {
        button.disabled = true;
        button.title = 'La unidad todavía no ha publicado este videotutorial.';
        button.querySelector('strong').textContent = gettext('Videotutorial por publicar');
        button.querySelector('b').textContent = gettext('No disponible');
        return;
      }
      const configured = tutorialKind === 'servicio'
        ? modal.dataset.serviceTutorialConfigured === 'true'
        : modal.dataset.resourceTutorialConfigured === 'true';
      if (!configured) button.querySelector('small').textContent = gettext('Video demostrativo temporal');
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (!tutorialViewer || !tutorialFrame) return;
        tutorialTrigger = button;
        tutorialFrame.src = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1`;
        if (tutorialTitle) tutorialTitle.textContent = tutorialKind === 'servicio'
          ? gettext('Cómo encargar un servicio al laboratorio')
          : gettext('Cómo reservar recursos para utilizarlos');
        if (tutorialDescription) tutorialDescription.textContent = tutorialKind === 'servicio'
          ? gettext('Conoce cómo definir el resultado, elegir la modalidad, adjuntar archivos y revisar la cotización.')
          : gettext('Conoce cómo seleccionar recursos, registrar participantes, consultar disponibilidad y confirmar la reserva.');
        tutorialViewer.hidden = false;
        tutorialViewer.querySelector('[data-tutorial-viewer-close]')?.focus();
      });
    });
    tutorialViewer?.addEventListener('click', (event) => {
      if (event.target === tutorialViewer || event.target.closest('[data-tutorial-viewer-close]')) closeTutorialViewer();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && tutorialViewer && !tutorialViewer.hidden) closeTutorialViewer();
    });

    const includeSpaceInput = element('incluyeEspacioReserva');
    const requestedSpaceInput = element('solicitoEspacioReserva');
    const requestedEquipmentInput = element('solicitoEquipoReserva');
    const requestedSoftwareInput = element('solicitoSoftwareReserva');
    const resourceKindToggles = Array.from(shell.querySelectorAll('[data-resource-kind-toggle]'));
    let spaceSelectedExplicitly = false;
    let equipmentSelectedExplicitly = false;

    // Las palabras del encargo salen de lo que el servicio hace. Un laboratorio
    // que fabrica, uno que analiza y uno que asesora no piden lo mismo, aunque
    // el flujo sea el mismo. Quien no declare su tipo usa el texto neutro.
    const PALABRAS_SERVICIO = {
      fabricacion: {
        titulo: '¿Qué vas a fabricar y con qué material?',
        modelo_listo: [gettext('Entrego el modelo listo'), 'Adjunto el archivo preparado; el laboratorio revisa y fabrica.'],
        diseno_asistido: [gettext('Diseño con asesoría'), gettext('Diseñaré en la instalación, con espacio, equipos o software reservados y apoyo del laboratorista.')],
        diseno_completo: [gettext('Diseño completo del laboratorio'), gettext('El equipo técnico diseña y ejecuta el trabajo desde el requerimiento.')],
      },
      analisis: {
        titulo: '¿Qué vas a analizar y con qué material?',
        modelo_listo: [gettext('Entrego la muestra lista'), 'Traigo el material preparado y rotulado; el laboratorio lo recibe y lo analiza.'],
        diseno_asistido: [gettext('Analizo con acompañamiento'), gettext('Trabajaré en la instalación, con espacio, equipos o software reservados y apoyo del laboratorista.')],
        diseno_completo: [gettext('El laboratorio hace el análisis completo'), gettext('El equipo técnico toma o prepara el material y ejecuta el análisis.')],
      },
      produccion: {
        titulo: '¿Qué vas a producir y con qué material?',
        modelo_listo: [gettext('Entrego la especificación lista'), 'Adjunto lo que debe producirse; el laboratorio revisa y ejecuta.'],
        diseno_asistido: [gettext('Produzco con acompañamiento'), gettext('Trabajaré en la instalación, con espacio, equipos o software reservados y apoyo del laboratorista.')],
        diseno_completo: [gettext('El laboratorio produce por completo'), gettext('El equipo técnico define y ejecuta la producción desde el requerimiento.')],
      },
      desarrollo_producto: {
        titulo: '¿Qué producto quieres desarrollar?',
        modelo_listo: [gettext('Entrego la formulación inicial'), gettext('Adjunto la formulación y los requisitos que debe revisar la planta.')],
        diseno_asistido: [gettext('Desarrollo con acompañamiento'), gettext('Trabajaré con la planta para ajustar formulación, proceso y controles.')],
        diseno_completo: [gettext('La planta desarrolla la propuesta'), gettext('El equipo técnico plantea y ejecuta el desarrollo desde el requerimiento.')],
      },
      maquila_academica: {
        titulo: '¿Qué lote necesitas producir y con qué materia prima?',
        modelo_listo: [gettext('Entrego la especificación del lote'), 'Aporto la materia prima y la especificación; la planta revisa y procesa.'],
        diseno_asistido: [gettext('Produzco con acompañamiento'), gettext('Participaré en la corrida con los recursos reservados y apoyo técnico.')],
        diseno_completo: [gettext('La planta ejecuta la maquila'), gettext('El equipo técnico recibe la materia prima y entrega el lote acordado.')],
      },
      escalamiento: {
        titulo: '¿Qué producto necesitas llevar a escala piloto?',
        modelo_listo: [gettext('Entrego el prototipo y su formulación'), gettext('Adjunto los parámetros conocidos para que la planta prepare el escalamiento.')],
        diseno_asistido: [gettext('Escalo con acompañamiento'), gettext('Ajustaremos juntos cantidades, equipos, tiempos y controles.')],
        diseno_completo: [gettext('La planta realiza el escalamiento'), gettext('El equipo técnico diseña y ejecuta las corridas piloto necesarias.')],
      },
      capacitacion: {
        titulo: '¿Qué capacitación necesita el grupo?',
        modelo_listo: [gettext('Entrego el temario requerido'), gettext('Indico contenidos, participantes y resultado esperado para organizar la sesión.')],
        diseno_asistido: [gettext('Preparo la capacitación con la planta'), gettext('Acordaremos contenidos, práctica y recursos con el equipo técnico.')],
        diseno_completo: [gettext('La planta diseña la capacitación'), gettext('El equipo técnico prepara y dirige la actividad completa.')],
      },
      practica: {
        titulo: '¿Qué práctica necesitas y con qué material?',
        modelo_listo: [gettext('Traigo la práctica preparada'), 'Entrego la guía y el procedimiento; el laboratorio los revisa y monta.'],
        diseno_asistido: [gettext('Preparo la práctica con acompañamiento'), gettext('La montaré en la instalación, con los recursos reservados y apoyo del laboratorista.')],
        diseno_completo: [gettext('El laboratorio prepara y dirige la práctica'), gettext('El equipo técnico arma la práctica y la conduce con el grupo.')],
      },
      uso_equipo: {
        titulo: '¿Qué vas a hacer en el equipo y con qué material?',
        modelo_listo: [gettext('Traigo el trabajo listo'), 'Entrego lo que hay que procesar; el laboratorio opera el equipo.'],
        diseno_asistido: [gettext('Opero con acompañamiento'), gettext('Operaré el equipo en la instalación con apoyo del laboratorista.')],
        diseno_completo: [gettext('El laboratorio opera el equipo'), gettext('El equipo técnico ejecuta el trabajo completo en la máquina.')],
      },
      visita: {
        titulo: '¿Qué quieren conocer en la visita?',
        hint: 'Indica cuántas personas asisten y qué esperan ver; con eso el laboratorio prepara el recorrido y confirma la fecha.',
        modelo_listo: [gettext('Traigo el grupo y el guion'), gettext('Llego con el grupo organizado y lo que queremos ver definido.')],
        diseno_asistido: [gettext('Organizo la visita con asesoría'), gettext('Prepararemos el recorrido junto con el laboratorio.')],
        diseno_completo: [gettext('El laboratorio organiza la visita'), gettext('El equipo técnico arma el recorrido y lo conduce.')],
      },
      soporte: {
        titulo: '¿En qué necesitas el apoyo del laboratorio?',
        modelo_listo: [gettext('Entrego el caso documentado'), 'Adjunto la información del caso; el laboratorio la revisa y responde.'],
        diseno_asistido: [gettext('Trabajo con acompañamiento'), gettext('Trabajaré en la instalación con apoyo del personal del laboratorio.')],
        diseno_completo: [gettext('El laboratorio se hace cargo'), gettext('El equipo técnico resuelve el caso desde el requerimiento.')],
      },
    };
    const PALABRAS_SERVICIO_NEUTRAS = {
      titulo: '¿Qué necesitas que haga el laboratorio?',
      modelo_listo: [gettext('Entrego el trabajo listo'), 'Entrego lo que hay que trabajar; el laboratorio lo revisa y lo ejecuta.'],
      diseno_asistido: [gettext('Trabajo con acompañamiento'), gettext('Trabajaré en la instalación, con espacio, equipos o software reservados y apoyo del laboratorista.')],
      diseno_completo: [gettext('El laboratorio lo hace todo'), gettext('El equipo técnico se hace cargo del trabajo desde el requerimiento.')],
    };

    function palabrasServicio() {
      const tipos = new Set(selectedServiceInputs().map((input) => (
        input.closest('.reservation-service')?.dataset.tipoServicio || ''
      )));
      // Con dos tipos distintos en la misma solicitud, ninguna palabra concreta
      // sirve para las dos: se vuelve al texto neutro.
      if (tipos.size !== 1) return PALABRAS_SERVICIO_NEUTRAS;
      return PALABRAS_SERVICIO[[...tipos][0]] || PALABRAS_SERVICIO_NEUTRAS;
    }

    function syncServiceWording() {
      const palabras = palabrasServicio();
      const titulo = serviceWork?.querySelector('[data-service-work-title]');
      if (titulo) titulo.textContent = palabras.titulo;
      const ayuda = serviceWork?.querySelector('[data-service-work-hint]');
      if (ayuda && palabras.hint) ayuda.textContent = palabras.hint;
      serviceModes.forEach((input) => {
        const etiqueta = input.closest('[data-service-mode]');
        const [nombre, detalle] = palabras[input.value] || [];
        const strong = etiqueta?.querySelector('[data-mode-title]');
        const small = etiqueta?.querySelector('[data-mode-hint]');
        if (strong && nombre && strong.textContent !== nombre) strong.textContent = nombre;
        if (small && detalle && small.textContent !== detalle) small.textContent = detalle;
      });
    }

    function selectedServiceMode() {
      return serviceModes.find((input) => input.checked)?.value || '';
    }

    function selectedServiceInputs() {
      return serviceInputs.filter((input) => input.checked);
    }

    function isAssistedService() {
      return state.type === 'servicio' && selectedServiceMode() === 'diseno_asistido';
    }

    function isModelReadyService() {
      return state.type === 'servicio' && selectedServiceMode() === 'modelo_listo';
    }

    function serviceRequiresPreparedFile() {
      return isModelReadyService() && selectedServiceInputs().some((input) => (
        input.closest('.reservation-service')?.dataset.requiresFiles === 'true'
      ));
    }

    function resourceKindActive(kind) {
      return Boolean(state.resources[kind]
        && (state.type === 'recursos' || isAssistedService()));
    }

    // Instalado en una máquina del laboratorio: para usarlo hay que reservarla.
    // Una licencia que se abre en el navegador no ocupa puesto alguno.
    function softwareNeedsEquipment(input) {
      const item = input.closest('.reservation-software-item');
      return softwareEquipmentIds(input).length > 0
        || item?.dataset.accessType === 'instalacion';
    }

    // Licencias que no cuelgan de ninguna máquina: se piden por sí solas.
    function hayLicenciasSinEquipo() {
      return softwareInputs.some((input) => !softwareNeedsEquipment(input));
    }

    function softwareRequiresEquipment() {
      return softwareInputs.some((input) => (
        input.checked && !input.disabled && softwareNeedsEquipment(input)
      ));
    }

    function spaceEquipmentIds(input) {
      return (input.closest('.reservation-space-item')?.dataset.equipmentIds || '')
        .split(',')
        .map((value) => Number.parseInt(value, 10))
        .filter(Number.isInteger);
    }

    function physicalSpaceRequired() {
      return Boolean(
        isAssistedService()
        || resourceKindActive('equipo')
        || softwareRequiresEquipment()
      );
    }

    function cascadeSelectedSpaceIds() {
      return new Set(
        spaceInputs
          .filter((input) => input.checked && !input.disabled)
          .map((input) => Number.parseInt(input.value, 10))
          .filter(Number.isInteger)
      );
    }

    function cascadeSelectedEquipmentCount() {
      return form.querySelectorAll('.unidad-checkbox:checked').length;
    }

    function cascadeEquipmentStageOpen() {
      if (state.type !== 'recursos' || !equipmentCatalog) return false;
      if (!resourceAvailability.espacio) return true;
      // Sin areas publicadas, el espacio unico de la unidad se incluye solo.
      if (!spaceInputs.length) return true;
      if (selectedSpaceScope() === 'unidad_completa') return true;
      return cascadeSelectedSpaceIds().size > 0;
    }

    function cascadeSoftwareStageOpen() {
      if (state.type !== 'recursos' || !softwareCatalog || !softwareInputs.length) return false;
      if (cascadeSelectedEquipmentCount() > 0) return true;
      // Las licencias del navegador no dependen de una máquina: basta con haber
      // resuelto dónde se trabaja para poder pedirlas.
      return softwareInputs.some((input) => !softwareNeedsEquipment(input))
        && cascadeEquipmentStageOpen();
    }

    function cascadeHasAnyResource() {
      if (state.type !== 'recursos') return true;
      if (resourceAvailability.espacio) {
        if (!spaceInputs.length) return true;
        return cascadeSelectedSpaceIds().size > 0 || selectedSpaceScope() === 'unidad_completa';
      }
      return cascadeSelectedEquipmentCount() > 0
        || softwareInputs.some((input) => input.checked && !input.disabled);
    }

    function syncCascadeState() {
      // Los "tipos" de recurso se deducen de la seleccion real; ya no se marcan.
      if (state.type !== 'recursos') return;
      const equipmentChecked = cascadeSelectedEquipmentCount() > 0;
      const softwareChecked = softwareInputs.some((input) => input.checked && !input.disabled);
      if (resourceAvailability.espacio) {
        state.resources.espacio = true;
        spaceSelectedExplicitly = true;
      }
      state.resources.equipo = equipmentChecked;
      equipmentSelectedExplicitly = equipmentChecked;
      state.resources.software = softwareChecked;
    }

    function filterEquipmentBySelectedSpaces() {
      if (state.type !== 'recursos' || !equipmentCatalog) return 0;
      const fullUnit = selectedSpaceScope() === 'unidad_completa';
      const selectedSpaceIds = cascadeSelectedSpaceIds();
      // Solo los equipos ligados a un area marcada; un equipo sin area asignada
      // aparece unicamente con la unidad completa (o si la unidad no define areas).
      const matchesSpaces = (locations) => fullUnit
        || !resourceAvailability.espacio
        || (locations.length > 0 && locations.some((spaceId) => selectedSpaceIds.has(spaceId)));
      let visible = 0;
      let changed = false;
      equipmentCatalog.querySelectorAll('[data-unit-row]').forEach((row) => {
        const input = row.querySelector('.unidad-checkbox');
        if (!input) return;
        const show = matchesSpaces(equipmentSpaceIds(input));
        row.classList.toggle('rw-cascade-hidden', !show);
        if (!show && input.checked) {
          input.checked = false;
          changed = true;
        }
        if (show) visible += 1;
      });
      // Una tarjeta sin unidades visibles (y una categoria sin tarjetas) se oculta.
      equipmentGroups().forEach((group) => {
        const rows = Array.from(group.querySelectorAll('[data-unit-row]'));
        group.classList.toggle('rw-cascade-hidden', rows.length > 0 && rows.every((row) => row.classList.contains('rw-cascade-hidden')));
      });
      equipmentCatalog.querySelectorAll('[data-equipment-category]').forEach((section) => {
        const groups = Array.from(section.querySelectorAll('[data-equipment-row]'));
        section.classList.toggle('rw-cascade-hidden', groups.length > 0 && groups.every((group) => group.classList.contains('rw-cascade-hidden')));
      });
      // Los equipos no disponibles siguen el mismo filtro de areas.
      const unavailable = element('equiposNoDisponibles');
      if (unavailable) {
        let shown = 0;
        unavailable.querySelectorAll('[data-unavailable-list] li[data-unit-id]').forEach((item) => {
          const show = matchesSpaces(equipmentSpaceIds({ value: item.dataset.unitId }));
          item.hidden = !show;
          if (show) shown += 1;
        });
        unavailable.hidden = !shown;
        const summary = unavailable.querySelector('[data-unavailable-summary]');
        if (summary && shown) {
          const plural = shown === 1 ? '' : 's';
          summary.textContent = `${shown} equipo${plural} no disponible${plural} por mantenimiento, daño o uso`;
        }
      }
      if (changed && typeof window.actualizarSeleccionUnidades === 'function') {
        window.actualizarSeleccionUnidades();
      }
      return visible;
    }

    function syncSoftwareAdicional() {
      syncSoftwareAdicionalTexto();
    }

    // Texto de "otro programa" de cada equipo marcado que admite instalaciones.
    function syncSoftwareAdicionalTexto() {
      const parts = [];
      equipmentGroups().forEach((group) => {
        const field = group.querySelector('[data-equipment-extra-software-input]');
        const text = field?.value.trim();
        const selected = Array.from(group.querySelectorAll('.unidad-checkbox'))
          .some((input) => input.checked && !input.disabled);
        if (!field || field.closest('[hidden]') || !selected || !text) return;
        const name = group.querySelector('.reservation-equipment__identity strong')?.textContent.trim() || 'Equipo';
        parts.push(`${name}: ${text}`);
      });
      softwareAdicionalTextoInput.value = parts.join('; ').slice(0, 300);
    }
    form.addEventListener('input', (event) => {
      if (event.target.matches?.('[data-equipment-extra-software-input]')) syncSoftwareAdicionalTexto();
    });
    // El software propio del equipo no se desmarca: viaja con la reserva del equipo.
    form.addEventListener('click', (event) => {
      const input = event.target.closest?.('input[name="software_solicitado"]');
      if (!input || input.dataset.rwRequired !== 'true') return;
      event.preventDefault();
      const badge = input.closest('.reservation-software-item')?.querySelector('[data-software-badge]');
      badge?.classList.add('is-flash');
      window.setTimeout(() => badge?.classList.remove('is-flash'), 900);
    }, true);

    function filterSoftwareBySelectedEquipment() {
      if (state.type !== 'recursos') return { installed: 0, extra: 0 };
      const selectedEquipmentIds = new Set(
        Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
          .map((input) => Number.parseInt(input.value, 10))
          .filter(Number.isInteger)
      );
      let installed = 0;
      let requiredChanged = false;
      softwareInputs.forEach((input) => {
        const item = input.closest('.reservation-software-item');
        if (!item) return;
        const linkedUnitIds = softwareEquipmentIds(input);
        const isInstalled = linkedUnitIds.some((id) => selectedEquipmentIds.has(id));
        const integrated = item.classList.contains('is-integrated');
        // Propio del equipo (laminador, controlador...): se incluye al marcar el
        // equipo y no se puede desmarcar. Lo opcional lo decide la persona.
        const required = item.dataset.softwareUsage === 'obligatorio' && linkedUnitIds.length > 0;
        // El software instalado vive en la tarjeta de su equipo. El que se abre
        // en el navegador no tiene equipo: se queda en el catálogo y se ofrece
        // solo, porque nada lo ata a una máquina.
        const enLaNube = !linkedUnitIds.length && item.dataset.accessType !== 'instalacion';
        item.classList.toggle('rw-cascade-hidden', !integrated && !enLaNube);
        item.classList.toggle('is-installed-here', isInstalled);
        item.classList.toggle('is-required', required);
        if (enLaNube) {
          if (input.dataset.rwFlowDisabled === 'true') {
            input.disabled = false;
            delete input.dataset.rwFlowDisabled;
          }
        } else if (!integrated || !isInstalled) {
          if (!input.disabled) {
            input.disabled = true;
            input.dataset.rwFlowDisabled = 'true';
            input.checked = false;
          }
        } else if (input.dataset.rwFlowDisabled === 'true') {
          input.disabled = false;
          delete input.dataset.rwFlowDisabled;
        }
        if (required && isInstalled && !input.disabled) {
          if (!input.checked) {
            input.checked = true;
            requiredChanged = true;
          }
          input.dataset.rwRequired = 'true';
        } else if (input.dataset.rwRequired === 'true') {
          delete input.dataset.rwRequired;
          if (input.checked) {
            input.checked = false;
            requiredChanged = true;
          }
        }
        let badge = item.querySelector('[data-software-badge]');
        if (!badge) {
          badge = document.createElement('em');
          badge.dataset.softwareBadge = '';
          badge.className = 'reservation-software-item__badge';
          item.querySelector('.reservation-software-item__content')?.appendChild(badge);
        }
        // Solo el propio del equipo lleva distintivo; el opcional ya tiene casilla.
        badge.textContent = required ? (isInstalled ? gettext('Incluido con el equipo') : gettext('Se incluye al marcar el equipo')) : '';
        badge.hidden = !badge.textContent;
        if (isInstalled) installed += 1;
      });
      if (requiredChanged) syncCascadeState();
      syncSoftwareAdicional();
      return { installed, extra: 0 };
    }

    function cascadeConsumablesStageOpen() {
      if (state.type !== 'recursos' || !inventoryCatalog) return false;
      // Quien reserva solo el espacio también puede pedir material del catálogo.
      if (!cascadeSelectedEquipmentCount() && !spaceOnlySelection()) return false;
      const { compatibleCount } = filterConsumablesByService();
      return compatibleCount > 0;
    }

    function placeInventoryCatalog() {
      if (!inventoryCatalog) return;
      // El servicio ya pregunta por sus piezas en el detalle del trabajo.
      syncCatalogWorkUnits();
      if (state.type === 'recursos') {
        if (inventoryCatalog.parentElement !== resources) {
          resources.insertBefore(inventoryCatalog, responsibleCatalog || null);
        }
      } else if (inventoryCatalog.parentElement !== requirementsGrid) {
        requirementsGrid.insertBefore(inventoryCatalog, requirementsGrid.firstChild);
      }
    }

    let cascadeSyncing = false;
    function syncCascadeVisibility() {
      if (state.type !== 'recursos' || cascadeSyncing) return;
      cascadeSyncing = true;
      try {
        const visibleEquipment = filterEquipmentBySelectedSpaces();
        const equipmentOpen = cascadeEquipmentStageOpen() && visibleEquipment > 0;
        const softwareOpen = cascadeSoftwareStageOpen();
        softwareInputs.forEach((input) => {
          if (softwareOpen && input.dataset.rwStageDisabled === 'true') {
            input.disabled = false;
            delete input.dataset.rwStageDisabled;
          } else if (!softwareOpen && !input.disabled) {
            input.disabled = true;
            input.dataset.rwStageDisabled = 'true';
            input.checked = false;
          }
        });
        if (softwareOpen) filterSoftwareBySelectedEquipment();
        const consumablesOpen = cascadeConsumablesStageOpen();

        if (equipmentCatalog) equipmentCatalog.hidden = !equipmentOpen;
        // El software instalado se elige dentro de la tarjeta de su equipo. El
        // del navegador no tiene tarjeta: conserva su catálogo propio.
        if (softwareCatalog) {
          softwareCatalog.hidden = !(softwareOpen && hayLicenciasSinEquipo());
        }
        if (inventoryCatalog) inventoryCatalog.hidden = !consumablesOpen;
        if (!consumablesOpen && consumableChecks.some((check) => check.checked)) updateConsumableGuidance();
        syncConsumables();
      } finally {
        cascadeSyncing = false;
      }
    }

    function syncResourceChoices() {
      const equipmentRequiredForSoftware = softwareRequiresEquipment();
      syncCascadeState();
      const equipmentRequired = equipmentRequiredForSoftware;
      if (equipmentRequired && resourceAvailability.equipo) {
        state.resources.equipo = true;
      } else if (!equipmentRequired && !equipmentSelectedExplicitly) {
        state.resources.equipo = false;
      }
      const required = physicalSpaceRequired();
      if (required && resourceAvailability.espacio) {
        state.resources.espacio = true;
      } else if (!required && !spaceSelectedExplicitly) {
        state.resources.espacio = false;
      }
      resourceKindToggles.forEach((input) => {
        const kind = input.dataset.resourceKindToggle;
        const option = input.closest('label');
        input.checked = Boolean(state.resources[kind]);
        if (kind === 'espacio') input.disabled = required;
        if (kind === 'equipo') input.disabled = equipmentRequired;
        option?.classList.toggle('is-selected', input.checked);
        option?.classList.toggle(
          'is-required',
          (kind === 'espacio' && required) || (kind === 'equipo' && equipmentRequired)
        );
        const action = option?.querySelector('.rw-resource-choice__body em');
        let actionHtml = '';
        if (kind === 'espacio') {
          actionHtml = required
            ? window.interfaz.html`Incluido automáticamente <i class="fas fa-check-circle"></i>`
            : window.interfaz.html`Revisar espacios <i class="fas fa-arrow-right"></i>`;
        }
        if (kind === 'equipo') {
          actionHtml = equipmentRequired
            ? window.interfaz.html`Confirma dónde ejecutarás el software <i class="fas fa-link"></i>`
            : window.interfaz.html`Elegir equipos <i class="fas fa-arrow-right"></i>`;
        }
        // Solo se reescribe cuando cambia: cada escritura es una mutacion del DOM.
        if (action && actionHtml && action.innerHTML !== actionHtml) action.innerHTML = actionHtml;
      });
      if (includeSpaceInput) includeSpaceInput.value = resourceKindActive('espacio') ? 'true' : 'false';
      if (requestedSpaceInput) requestedSpaceInput.value = spaceSelectedExplicitly ? 'true' : 'false';
      if (requestedEquipmentInput) requestedEquipmentInput.value = equipmentSelectedExplicitly ? 'true' : 'false';
      if (requestedSoftwareInput) requestedSoftwareInput.value = state.resources.software ? 'true' : 'false';
    }

    function selectedSpaceScope() {
      return spaceScopeInputs.find((input) => input.type === 'radio' && input.checked)?.value
        || spaceScopeInputs.find((input) => input.type === 'hidden')?.value
        || (spaceInputs.length ? 'areas' : 'espacio_unico');
    }

    function syncSpaceScope() {
      const usesSpace = resourceKindActive('espacio');
      // La unidad completa se reserva para docencia: bloquea todo el laboratorio
      // y suele programarse por sesiones largas o todo el periodo.
      const fullUnitOption = spaceScopeInputs.find((input) => input.value === 'unidad_completa');
      const fullUnitAllowed = state.type !== 'recursos' || selectedPurpose() === 'docencia_practica';
      if (fullUnitOption) {
        const fullUnitLabel = fullUnitOption.closest('label');
        if (fullUnitLabel) fullUnitLabel.hidden = !fullUnitAllowed;
        // Con una sola opcion posible no hay decision que tomar: se oculta el bloque.
        const scopeFieldset = fullUnitOption.closest('fieldset');
        if (scopeFieldset) scopeFieldset.hidden = !fullUnitAllowed;
        if (!fullUnitAllowed && fullUnitOption.checked) {
          fullUnitOption.checked = false;
          const areasOption = spaceScopeInputs.find((input) => input.value === 'areas');
          if (areasOption) areasOption.checked = true;
        }
      }
      const scope = selectedSpaceScope();
      const fullUnit = scope === 'unidad_completa';
      const singleConfiguredSpace = scope === 'areas' && spaceInputs.length === 1;
      const declaredTechnicalUse = state.type === 'recursos'
        || resourceKindActive('equipo') || resourceKindActive('software');
      spaceScopeInputs.forEach((input) => {
        input.disabled = !usesSpace;
        input.closest('label')?.classList.toggle('is-selected', input.checked && usesSpace);
      });
      spaceInputs.forEach((input) => {
        const card = input.closest('.reservation-space-item');
        const unavailable = card?.classList.contains('is-unavailable');
        const technicalOnly = card?.dataset.spacePolicy === 'tecnico';
        const incompatiblePlan = Boolean(
          usesSpace && !fullUnit && technicalOnly && !declaredTechnicalUse
        );
        input.disabled = !usesSpace || fullUnit || unavailable || incompatiblePlan;
        if (!usesSpace || fullUnit || incompatiblePlan) input.checked = false;
        if (usesSpace && singleConfiguredSpace && !unavailable && !incompatiblePlan) input.checked = true;
        if (input.dataset.processLocked === 'true') {
          input.disabled = false;
          input.checked = true;
        }
        card?.classList.toggle('is-selected', input.checked);
        card?.classList.toggle('is-plan-incompatible', incompatiblePlan);
      });
      spaceCatalog?.classList.toggle('is-full-unit', usesSpace && fullUnit);
    }

    function clearEquipmentSelection() {
      let changed = false;
      form.querySelectorAll('.unidad-checkbox:checked').forEach((input) => {
        input.checked = false;
        changed = true;
      });
      if (changed && typeof window.actualizarSeleccionUnidades === 'function') {
        window.actualizarSeleccionUnidades();
      }
    }

    function clearComplementaryResources() {
      state.resources.equipo = false;
      state.resources.espacio = false;
      state.resources.software = false;
      spaceSelectedExplicitly = false;
      equipmentSelectedExplicitly = false;
      softwareInputs.forEach((input) => { input.checked = false; });
      clearEquipmentSelection();
      syncResourceChoices();
    }

    function syncEquipmentAvailability() {
      const active = state.type === 'recursos' ? cascadeEquipmentStageOpen() : resourceKindActive('equipo');
      integrateResourcesIntoEquipment();
      form.querySelectorAll('.unidad-checkbox').forEach((input) => {
        if (!active && !input.disabled) {
          input.dataset.rwDisabledByFlow = 'true';
          input.disabled = true;
        } else if (active && input.dataset.rwDisabledByFlow === 'true') {
          input.disabled = false;
          delete input.dataset.rwDisabledByFlow;
        }
      });
      syncSoftwareEquipmentCompatibility({ autoSelect: true });
      syncSpaceEquipmentCompatibility({ autoSelect: false });
      syncSpacesFromSelectedEquipment();
      if (state.type === 'recursos') {
        syncResourceChoices();
        syncCascadeVisibility();
      }
      applyProcessLocks();
    }

    function equipmentSpaceIds(input) {
      const source = form.querySelector(`[data-equipment-unit="${input.value}"]`);
      return (source?.dataset.equipmentSpaceIds || '')
        .split(',')
        .map((value) => Number.parseInt(value, 10))
        .filter(Number.isInteger);
    }

    function syncSpacesFromSelectedEquipment() {
      if (!resourceKindActive('espacio') || selectedSpaceScope() === 'unidad_completa') return;
      const selectedEquipment = Array.from(form.querySelectorAll('.unidad-checkbox:checked'));
      const compatibleSpaceIds = new Set(
        selectedEquipment.flatMap((input) => equipmentSpaceIds(input))
      );
      const requiredSpaceIds = new Set(
        selectedEquipment.flatMap((input) => {
          const locations = equipmentSpaceIds(input);
          return locations.length === 1 ? locations : [];
        })
      );
      let changed = false;
      spaceInputs.forEach((input) => {
        input.closest('.reservation-space-item')?.classList.toggle(
          'is-equipment-location',
          compatibleSpaceIds.has(Number.parseInt(input.value, 10))
        );
        if (requiredSpaceIds.has(Number.parseInt(input.value, 10)) && !input.disabled && !input.checked) {
          input.checked = true;
          input.closest('.reservation-space-item')?.classList.add('is-selected');
          changed = true;
        }
      });
      if (changed) syncResourceChoices();
    }

    function validateEquipmentSpaceSelection() {
      if (!resourceKindActive('equipo') || selectedSpaceScope() === 'unidad_completa') return true;
      const selectedSpaceIds = new Set(
        spaceInputs
          .filter((input) => input.checked && !input.disabled)
          .map((input) => Number.parseInt(input.value, 10))
          .filter(Number.isInteger)
      );
      for (const equipmentInput of form.querySelectorAll('.unidad-checkbox:checked')) {
        const locations = equipmentSpaceIds(equipmentInput);
        if (!locations.length || locations.some((spaceId) => selectedSpaceIds.has(spaceId))) continue;
        const equipmentName = equipmentInput.closest('tr')?.querySelector('.reservation-equipment-identity strong')?.textContent.trim()
          || 'el equipo seleccionado';
        const firstLocation = locations
          .map((spaceId) => spaceInputs.find((input) => Number.parseInt(input.value, 10) === spaceId))
          .find((input) => input && !input.disabled);
        return showValidationMessage(
          resourceValidationMessage,
          locations.length > 1
            ? `Selecciona el área donde utilizarás ${equipmentName}; este equipo puede operar en más de una ubicación.`
            : `La ubicación de ${equipmentName} debe quedar incluida en la reserva.`,
          firstLocation || equipmentInput
        );
      }
      return true;
    }

    function softwareEquipmentIds(input) {
      return (input.closest('.reservation-software-item')?.dataset.equipmentIds || '')
        .split(',')
        .map((value) => Number.parseInt(value, 10))
        .filter(Number.isInteger);
    }

    function syncSoftwareEquipmentCompatibility({ autoSelect = false } = {}) {
      const selectedLinkedSoftware = softwareInputs.filter((input) => (
        input.checked && !input.disabled && softwareEquipmentIds(input).length
      ));
      const compatibleIds = new Set(
        selectedLinkedSoftware.flatMap((input) => softwareEquipmentIds(input))
      );
      let changed = false;
      form.querySelectorAll('.unidad-checkbox').forEach((input) => {
        const equipmentId = Number.parseInt(input.value, 10);
        input.closest('[data-unit-row]')?.classList.toggle(
          'is-software-compatible',
          compatibleIds.has(equipmentId)
        );
      });
      if (autoSelect) {
        // El software incluido con el equipo no puede volver a marcarlo: si la
        // persona desmarco la tarjeta, tiene que quedarse desmarcada.
        selectedLinkedSoftware.filter((input) => input.dataset.rwRequired !== 'true').forEach((softwareInput) => {
          const candidates = softwareEquipmentIds(softwareInput)
            .map((equipmentId) => form.querySelector(`.unidad-checkbox[value="${equipmentId}"]`))
            .filter((input) => input && !input.disabled);
          if (candidates.length === 1 && !candidates[0].checked) {
            candidates[0].checked = true;
            changed = true;
          }
        });
      }
      if (changed && typeof window.actualizarSeleccionUnidades === 'function') {
        window.actualizarSeleccionUnidades();
      }
    }

    function validateSoftwareEquipmentSelection() {
      if (!resourceKindActive('software')) return true;
      const selectedSoftware = softwareInputs.filter((input) => input.checked && !input.disabled);
      const selectedEquipmentIds = new Set(
        Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
          .map((input) => Number.parseInt(input.value, 10))
          .filter(Number.isInteger)
      );
      for (const softwareInput of selectedSoftware) {
        const card = softwareInput.closest('.reservation-software-item');
        const softwareName = card?.querySelector('strong')?.textContent.trim() || 'el software seleccionado';
        const equipmentIds = softwareEquipmentIds(softwareInput);
        const installedLocally = card?.dataset.accessType === 'instalacion';
        if (installedLocally && !equipmentIds.length) {
          return showValidationMessage(
            resourceValidationMessage,
            `${softwareName} todavía no tiene configurado el equipo donde está instalado. Solicita al administrador que complete esta relación.`,
            softwareInput
          );
        }
        if (equipmentIds.length && !equipmentIds.some((equipmentId) => selectedEquipmentIds.has(equipmentId))) {
          const firstCompatible = equipmentIds
            .map((equipmentId) => form.querySelector(`.unidad-checkbox[value="${equipmentId}"]`))
            .find((input) => input && !input.disabled);
          return showValidationMessage(
            resourceValidationMessage,
            firstCompatible
              ? `Selecciona uno de los equipos donde está disponible ${softwareName}.`
              : `Los equipos vinculados a ${softwareName} no están disponibles en esta unidad.`,
            firstCompatible || softwareInput
          );
        }
      }
      return true;
    }

    function selectedTechnicalSpaceInputs() {
      const fullUnit = selectedSpaceScope() === 'unidad_completa';
      if (fullUnit) return [];
      return spaceInputs.filter((input) => {
        const card = input.closest('.reservation-space-item');
        return card?.dataset.requiresTechnicalResource === 'true'
          && input.checked && !input.disabled;
      });
    }

    function syncSpaceEquipmentCompatibility({ autoSelect = false } = {}) {
      const technicalSpaces = selectedTechnicalSpaceInputs();
      const compatibleIds = new Set(technicalSpaces.flatMap((input) => spaceEquipmentIds(input)));
      let changed = false;
      form.querySelectorAll('.unidad-checkbox').forEach((input) => {
        const equipmentId = Number.parseInt(input.value, 10);
        input.closest('[data-unit-row]')?.classList.toggle('is-space-compatible', compatibleIds.has(equipmentId));
      });
      if (autoSelect && selectedSpaceScope() !== 'unidad_completa') {
        technicalSpaces.forEach((spaceInput) => {
          const candidates = spaceEquipmentIds(spaceInput)
            .map((equipmentId) => form.querySelector(`.unidad-checkbox[value="${equipmentId}"]`))
            .filter((input) => input && !input.disabled);
          if (candidates.length === 1 && !candidates[0].checked) {
            candidates[0].checked = true;
            changed = true;
          }
        });
      }
      if (changed && typeof window.actualizarSeleccionUnidades === 'function') {
        window.actualizarSeleccionUnidades();
      }
    }

    // Trabajar solo en el espacio es legítimo: una mesa, una práctica sin
    // máquina o un ensayo con material propio. En vez de bloquear, la solicitud
    // declara su alcance y la persona lo confirma antes de continuar.
    function spaceOnlySelection() {
      if (state.type !== 'recursos') return false;
      if (form.querySelector('.unidad-checkbox:checked')) return false;
      if (softwareInputs.some((input) => input.checked && !input.disabled)) return false;
      return selectedSpaceScope() === 'unidad_completa' || cascadeSelectedSpaceIds().size > 0;
    }

    function selectedSpaceNames() {
      if (selectedSpaceScope() === 'unidad_completa') {
        return [gettext('Toda la unidad, con su mobiliario y sus áreas de trabajo')];
      }
      return spaceInputs
        .filter((input) => input.checked && !input.disabled)
        .map((input) => (
          input.closest('.reservation-space-item')?.querySelector('strong')?.textContent.trim()
          || 'Área de trabajo'
        ));
    }

    function selectedConsumableSummary() {
      return Array.from(form.querySelectorAll('.reservation-consumable:not(.is-mirror)'))
        .filter((card) => card.querySelector('.reservation-consumable__check')?.checked)
        .map((card) => {
          const campo = card.querySelector('.reservation-consumable__quantity');
          const total = card.querySelector('[data-quantity-total]')?.textContent || '';
          const nombre = campo?.dataset.consumibleNombre || 'Insumo';
          const cantidad = total.replace(/^Total:\s*/, '');
          return cantidad && !/escribe la cantidad/i.test(cantidad)
            ? `${nombre} · ${cantidad}`
            : nombre;
        });
    }

    function syncScopeNotice() {
      if (!scopeNotice) return;
      const activo = spaceOnlySelection();
      scopeNotice.hidden = !activo;
      if (!activo) return;
      const insumos = selectedConsumableSummary();
      const tecnicas = selectedTechnicalSpaceInputs().map((input) => (
        input.closest('.reservation-space-item')?.querySelector('strong')?.textContent.trim() || 'el área'
      ));
      const puntos = [
        `Espacio: ${selectedSpaceNames().join(' · ')}`,
        insumos.length
          ? `Insumos del laboratorio: ${insumos.join(' · ')}`
          : gettext('Sin insumos del laboratorio: traes tu propio material o no necesitas ninguno'),
        gettext('Sin equipos ni software: no se reserva ninguna máquina ni ningún programa'),
      ];
      const ayuda = tecnicas.length
        ? `${tecnicas.join(' y ')} está pensada para trabajar con un equipo. Si vas a encender alguno, márcalo arriba; si solo necesitas el puesto y su mobiliario, confírmalo aquí.`
        : gettext('Revisa que sea todo lo que necesitas. Puedes volver arriba y añadir equipos, software o insumos.');
      const firma = `${puntos.join('|')}|${ayuda}`;
      if (scopeNotice.dataset.firma === firma) return;
      scopeNotice.dataset.firma = firma;
      // Cambió lo que se solicita: la confirmación se vuelve a pedir.
      if (scopeConfirm) scopeConfirm.checked = false;
      const ayudaNodo = scopeNotice.querySelector('[data-scope-hint]');
      if (ayudaNodo) ayudaNodo.textContent = ayuda;
      const confirmacion = scopeNotice.querySelector('[data-scope-confirm-text]');
      if (confirmacion) {
        confirmacion.textContent = insumos.length
          ? gettext('Confirmo que solo necesito el espacio y los insumos indicados.')
          : gettext('Confirmo que solo necesito el espacio, sin equipos ni software.');
      }
      const lista = scopeNotice.querySelector('[data-scope-list]');
      if (lista) {
        lista.replaceChildren(...puntos.map((texto) => {
          const item = document.createElement('li');
          item.textContent = texto;
          return item;
        }));
      }
    }

    // ------------------------------------------------------------------
    // Software e insumos dentro de la tarjeta de su equipo. Se mueven los
    // nodos originales (con sus inputs, que el servidor ya conoce); antes de
    // que el modulo heredado vuelva a dibujar la lista se devuelven a su sitio.
    // ------------------------------------------------------------------
    const resourceHomes = new Map();

    // Cada equipo declara sus propias piezas y su detalle: una impresora de
    // resina y una FDM del mismo trabajo no producen lo mismo. Lo escrito
    // sobrevive a que la lista de equipos se vuelva a dibujar.
    const workUnitsByEquipment = new Map();

    function equipmentWorkMemory(id) {
      if (!workUnitsByEquipment.has(id)) workUnitsByEquipment.set(id, { piezas: '1', detalle: '' });
      return workUnitsByEquipment.get(id);
    }

    function syncEquipmentWorkUnits(groups) {
      const plantilla = element('plantillaTrabajoEquipo');
      if (!plantilla) return;
      equipmentGroups().forEach((group) => {
        const activo = groups.includes(group) && group.classList.contains('is-selected');
        const destino = group.querySelector('[data-equipment-resources]');
        let franja = group.querySelector('[data-equipment-work]');
        if (!activo) {
          franja?.remove();
          return;
        }
        if (!franja) {
          franja = plantilla.content.firstElementChild.cloneNode(true);
          const memoria = equipmentWorkMemory(group.dataset.equipoId);
          franja.querySelector('[data-equipment-pieces]').value = memoria.piezas;
          franja.querySelector('[data-equipment-detail]').value = memoria.detalle;
          destino.insertBefore(franja, destino.querySelector('[data-equipment-software]'));
        }
      });
    }

    // Piezas de la tarjeta donde vive el material; si esta en el catalogo
    // general, las que se declararon alli.
    function resourceWorkUnits(card) {
      const propio = card?.closest('[data-equipment-row]')?.querySelector('[data-equipment-pieces]');
      const valor = Number.parseInt((propio || workUnitsInput)?.value || '1', 10);
      return Number.isInteger(valor) && valor > 0 ? valor : 1;
    }

    // Al servidor va la cuenta completa de la sesion y el detalle de cada
    // equipo, que es lo que el laboratorio necesita para entender el encargo.
    function syncEquipmentWorkSummary() {
      const total = element('piezasPorSesionTotal');
      const detalle = element('detalleTrabajoRecursos');
      const franjas = Array.from(form.querySelectorAll('[data-equipment-work]'));
      franjas.forEach((franja) => {
        const memoria = equipmentWorkMemory(franja.closest('[data-equipment-row]')?.dataset.equipoId);
        memoria.piezas = franja.querySelector('[data-equipment-pieces]')?.value || '1';
        memoria.detalle = franja.querySelector('[data-equipment-detail]')?.value || '';
      });
      if (total) {
        const suma = franjas.reduce((acumulado, franja) => (
          acumulado + resourceWorkUnits(franja)
        ), 0);
        total.value = String(suma || resourceWorkUnits(null));
      }
      syncCatalogWorkUnits();
      if (detalle) {
        detalle.value = franjas.map((franja) => {
          const tarjeta = franja.closest('[data-equipment-row]');
          const nombre = tarjeta?.querySelector('.reservation-equipment__identity strong')?.textContent.trim() || 'Equipo';
          const piezas = resourceWorkUnits(franja);
          const texto = (franja.querySelector('[data-equipment-detail]')?.value || '').trim();
          return `${nombre} · ${contarTrabajo(piezas)}${texto ? `: ${texto}` : ''}`;
        }).join('\n').slice(0, 2000);
      }
    }

    // La cuenta del catalogo general solo tiene sentido si queda algun material
    // fuera de las tarjetas de equipo.
    function syncCatalogWorkUnits() {
      const campo = element('piezasPorSesionCampo');
      if (!campo) return;
      const sueltos = form.querySelector(
        '#catalogoConsumiblesOpciones .reservation-consumable:not(.is-integrated):not(.is-mirror)'
        + ':not(.is-filtered-out):not(.is-equipment-incompatible):not(.rw-cascade-hidden)'
      );
      campo.hidden = state.type !== 'recursos' || !sueltos;
    }

    function rememberResourceHome(node) {
      if (node && !resourceHomes.has(node)) resourceHomes.set(node, node.parentElement);
    }

    function parkIntegratedResources() {
      removeConsumableMirrors();
      resourceHomes.forEach((home, node) => {
        if (home && node.parentElement !== home) home.appendChild(node);
        node.classList.remove('is-integrated');
      });
    }

    // Un insumo compatible con varios equipos se ve en la tarjeta de cada uno:
    // la tarjeta original (con los controles que lee el servidor) vive en el
    // primero y las demas son espejos que reflejan y reenvian su estado.
    const consumableMirrors = new Map();
    const mirrorOrigins = new WeakMap();
    const MIRROR_CONTROLS = ['.reservation-consumable__check', '.reservation-consumable__quantity'];

    function removeConsumableMirrors() {
      consumableMirrors.forEach((mirrors) => mirrors.forEach((mirror) => mirror.remove()));
      consumableMirrors.clear();
    }

    function refreshConsumableMirror(mirror, card) {
      const collapsed = mirror.classList.contains('is-collapsed');
      mirror.className = card.className;
      mirror.classList.add('is-mirror');
      mirror.classList.toggle('is-collapsed', collapsed);
      mirror.setAttribute('aria-disabled', card.getAttribute('aria-disabled') || 'false');
      // El espejo se desbloquea con el equipo de su propia tarjeta.
      const mirrorUnlocked = Boolean(mirror.closest('[data-equipment-row]')?.classList.contains('is-selected'));
      const sourceCheck = card.querySelector('.reservation-consumable__check');
      MIRROR_CONTROLS.forEach((selector) => {
        const source = card.querySelector(selector);
        const target = mirror.querySelector(selector);
        if (!source || !target) return;
        if (source.type === 'checkbox') {
          if (target.checked !== source.checked) target.checked = source.checked;
          target.disabled = source.dataset.rwBaseEnabled !== 'true' || !mirrorUnlocked;
        } else {
          if (target.value !== source.value) target.value = source.value;
          target.disabled = !sourceCheck?.checked || !mirrorUnlocked;
        }
        target.required = false;
        if (source.max && target.max !== source.max) target.max = source.max;
      });
      // El espejo repite lo que el sistema calcula: etiqueta y total.
      [gettext('[data-quantity-label]'), gettext('[data-quantity-total]')].forEach((selector) => {
        const origen = card.querySelector(selector);
        const destino = mirror.querySelector(selector);
        if (origen && destino && destino.textContent !== origen.textContent) {
          destino.textContent = origen.textContent;
        }
      });
      const sourceNote = card.querySelector('[data-stock-note]');
      const targetNote = mirror.querySelector('[data-stock-note]');
      if (sourceNote && targetNote) {
        targetNote.hidden = sourceNote.hidden;
        if (targetNote.textContent !== sourceNote.textContent) targetNote.textContent = sourceNote.textContent;
      }
    }

    function refreshConsumableMirrors() {
      consumableMirrors.forEach((mirrors, card) => mirrors.forEach((mirror) => refreshConsumableMirror(mirror, card)));
    }

    function syncConsumableMirrors(card, groups) {
      const bodies = groups.map((group) => group.querySelector('[data-equipment-consumables-body]')).filter(Boolean);
      const mirrors = (consumableMirrors.get(card) || []).filter((mirror) => {
        const keep = bodies.includes(mirror.parentElement);
        if (!keep) mirror.remove();
        return keep;
      });
      bodies.forEach((body) => {
        if (mirrors.some((mirror) => mirror.parentElement === body)) return;
        const mirror = card.cloneNode(true);
        mirror.classList.add('is-mirror');
        mirror.querySelectorAll('input, select').forEach((control) => {
          control.removeAttribute('name');
          control.removeAttribute('id');
        });
        mirrorOrigins.set(mirror, card);
        body.appendChild(mirror);
        mirrors.push(mirror);
      });
      if (mirrors.length) consumableMirrors.set(card, mirrors); else consumableMirrors.delete(card);
      mirrors.forEach((mirror) => refreshConsumableMirror(mirror, card));
    }

    function relayMirrorEvent(event) {
      const mirror = event.target.closest?.('.reservation-consumable.is-mirror');
      const card = mirror ? mirrorOrigins.get(mirror) : null;
      if (!card) return;
      const selector = MIRROR_CONTROLS.find((item) => event.target.matches(item));
      const original = selector ? card.querySelector(selector) : null;
      if (!original) return;
      if (original.type === 'checkbox') original.checked = event.target.checked;
      else original.value = event.target.value;
      original.dispatchEvent(new Event(event.type, { bubbles: true }));
      refreshConsumableMirrors();
    }
    form.addEventListener('change', relayMirrorEvent);
    form.addEventListener('input', relayMirrorEvent);

    function equipmentGroups() {
      return Array.from(equipmentCatalog?.querySelectorAll('[data-equipment-row]') || []);
    }

    function groupUnitIds(group) {
      return Array.from(group.querySelectorAll('.unidad-checkbox'))
        .map((input) => Number.parseInt(input.value, 10))
        .filter(Number.isInteger);
    }

    function groupForUnitIds(unitIds) {
      if (!unitIds.length) return null;
      return equipmentGroups().find((group) => groupUnitIds(group).some((id) => unitIds.includes(id))) || null;
    }

    function groupForEquipmentId(equipmentId) {
      return equipmentGroups().find((group) => group.dataset.equipoId === String(equipmentId)) || null;
    }

    function consumableEquipmentIds(card) {
      return (card.dataset.compatibleEquipmentIds || '')
        .split(',')
        .map((value) => Number.parseInt(value, 10))
        .filter(Number.isInteger);
    }

    function syncEquipmentGroupState(group) {
      const selected = Array.from(group.querySelectorAll('.unidad-checkbox'))
        .some((input) => input.checked && !input.disabled);
      group.classList.toggle('is-selected', selected);
      // Software e insumos se ven siempre (con su cantidad); se habilitan al
      // marcar el equipo.
      const lock = group.querySelector('[data-equipment-lock]');
      if (lock) lock.hidden = selected;
    }

    // En un servicio los materiales llegan del catalogo tecnico del trabajo, no
    // del inventario: la tarjeta del equipo lo dice en vez de mostrar un cero.
    function describeEquipmentConsumables(section, count, eligeInsumos) {
      if (!section) return;
      const counter = section.querySelector('[data-count]');
      const guidance = section.querySelector('h5 small');
      const empty = section.querySelector('[data-equipment-empty]');
      if (counter) {
        counter.hidden = !eligeInsumos;
        if (eligeInsumos && counter.textContent !== String(count)) counter.textContent = String(count);
      }
      if (guidance) {
        guidance.textContent = eligeInsumos
          ? gettext('Marca los que necesitas e indica la cantidad.')
          : gettext('Se eligen arriba, en «Materiales para este trabajo», según el servicio solicitado.');
      }
      if (empty) {
        empty.hidden = eligeInsumos && count > 0;
        empty.textContent = eligeInsumos
          ? gettext('Sin insumos ligados a este equipo.')
          : gettext('Los materiales de este trabajo se eligen junto a las piezas, arriba.');
      }
      section.classList.toggle('is-empty', eligeInsumos && !count);
    }

    function integrateResourcesIntoEquipment() {
      if (!equipmentCatalog) return;
      const groups = equipmentGroups();
      // Con «diseño con asesoría» la persona trabaja en la unidad con equipos y
      // software reservados: su tarjeta se arma igual que en la reserva de
      // recursos, salvo los insumos, que vienen del servicio.
      const eligeInsumos = state.type === 'recursos';
      if ((!eligeInsumos && !isAssistedService()) || !groups.length) {
        parkIntegratedResources();
        return;
      }
      form.querySelectorAll('.reservation-consumable:not(.is-mirror)').forEach((card) => {
        rememberResourceHome(card);
        const ids = consumableEquipmentIds(card);
        // Cada insumo aparece en la tarjeta de todos sus equipos compatibles:
        // la original en el primero y un espejo en cada uno de los demas. Sin
        // equipo ligado, queda en el catalogo general.
        // El original, que es el que se edita y viaja al servidor, se queda en
        // un equipo marcado: de ahi salen las piezas con las que se multiplica.
        const candidates = (eligeInsumos
          ? groups.filter((item) => ids.includes(Number.parseInt(item.dataset.equipoId, 10)))
          : []
        ).sort((a, b) => (
          Number(b.classList.contains('is-selected')) - Number(a.classList.contains('is-selected'))
        ));
        const [group = null, ...others] = candidates;
        const target = group ? group.querySelector('[data-equipment-consumables-body]') : resourceHomes.get(card);
        if (target && card.parentElement !== target) target.appendChild(card);
        card.classList.toggle('is-integrated', Boolean(group));
        syncConsumableMirrors(card, others);
      });
      softwareInputs.forEach((input) => {
        const item = input.closest('.reservation-software-item');
        if (!item) return;
        rememberResourceHome(item);
        const group = groupForUnitIds(softwareEquipmentIds(input));
        item.classList.toggle('is-integrated', Boolean(group));
        if (group) {
          const target = group.querySelector('[data-equipment-software-grid]');
          if (target && item.parentElement !== target) target.appendChild(item);
        }
      });
      groups.forEach((group) => {
        const softwareCount = group.querySelectorAll('[data-equipment-software-grid] .reservation-software-item').length;
        const consumableCount = group.querySelectorAll('[data-equipment-consumables-body] .reservation-consumable').length;
        const softwareSection = group.querySelector('[data-equipment-software]');
        if (softwareSection) {
          const counter = softwareSection.querySelector('[data-count]');
          if (counter && counter.textContent !== String(softwareCount)) counter.textContent = String(softwareCount);
          const empty = softwareSection.querySelector('[data-equipment-empty]');
          if (empty) empty.hidden = softwareCount > 0;
          softwareSection.classList.toggle('is-empty', !softwareCount);
        }
        describeEquipmentConsumables(
          group.querySelector('[data-equipment-consumables]'),
          consumableCount,
          eligeInsumos,
        );
        const lock = group.querySelector('[data-equipment-lock]');
        if (lock) {
          lock.lastChild.textContent = eligeInsumos
            ? gettext(' Marca el equipo para elegir su software e insumos.')
            : gettext(' Marca el equipo para elegir su software.');
        }
        const extraSoftware = group.querySelector('[data-equipment-extra-software]');
        if (extraSoftware) extraSoftware.hidden = group.dataset.admiteSoftwareAdicional !== 'true';
        const extras = group.querySelector('[data-equipment-extras]');
        if (extras) {
          const parts = [];
          if (softwareCount) parts.push(`${softwareCount} software`);
          if (eligeInsumos && consumableCount) parts.push(`${consumableCount} insumo${consumableCount === 1 ? '' : 's'}`);
          extras.textContent = parts.join(' · ');
          extras.hidden = !parts.length;
        }
        syncEquipmentGroupState(group);
      });
      syncEquipmentWorkUnits(eligeInsumos ? groups : []);
      syncEquipmentWorkSummary();
      fillConsumableCompatibility();
      // Al marcar o desmarcar un equipo cambia que insumos pueden elegirse.
      updateConsumableGuidance();
    }

    window.reservationBeforeUnitsRender = parkIntegratedResources;
    window.reservationAfterUnitsRender = integrateResourcesIntoEquipment;

    // ------------------------------------------------------------------
    // Fichas: equipo, software e insumo en un dialogo con la informacion
    // completa; la tarjeta solo muestra lo necesario para elegir.
    // ------------------------------------------------------------------
    const resourceSheet = create('div', 'reservation-sheet');
    resourceSheet.id = 'fichaRecursoReserva';
    resourceSheet.hidden = true;
    resourceSheet.setAttribute('role', 'dialog');
    resourceSheet.setAttribute('aria-modal', 'true');
    resourceSheet.setAttribute('aria-labelledby', 'fichaRecursoReservaTitulo');
    resourceSheet.innerHTML = window.interfaz.html`
      <div class="reservation-sheet__dialog">
        <header><div><small data-sheet-kind></small><h3 id="fichaRecursoReservaTitulo" data-sheet-title></h3><p data-sheet-subtitle></p></div><button type="button" data-sheet-close aria-label="Cerrar ficha"><i class="fas fa-times"></i></button></header>
        <nav class="reservation-sheet__tabs" data-sheet-tabs role="tablist"></nav>
        <div class="reservation-sheet__body" data-sheet-body></div>
      </div>`;
    // Dentro de la raíz del modal: Bootstrap conserva el foco en sus diálogos hijos.
    modal.appendChild(resourceSheet);
    let resourceSheetTrigger = null;

    function closeResourceSheet() {
      resourceSheet.hidden = true;
      resourceSheet.querySelector('[data-sheet-body]').replaceChildren();
      delete resourceSheet.dataset.spaceId;
      document.body.classList.remove('reservation-sheet-open');
      resourceSheetTrigger?.focus?.({ preventScroll: true });
      resourceSheetTrigger = null;
    }

    function openResourceSheet({ kind, title, subtitle, tabs, mode = 'resource' }, trigger) {
      resourceSheetTrigger = trigger || null;
      resourceSheet.dataset.mode = mode;
      delete resourceSheet.dataset.spaceId;
      resourceSheet.querySelector('[data-sheet-kind]').textContent = kind || '';
      resourceSheet.querySelector('[data-sheet-title]').textContent = title || '';
      resourceSheet.querySelector('[data-sheet-subtitle]').textContent = subtitle || '';
      const nav = resourceSheet.querySelector('[data-sheet-tabs]');
      const body = resourceSheet.querySelector('[data-sheet-body]');
      const visibleTabs = tabs.filter((tab) => tab.html);
      nav.innerHTML = visibleTabs.map((tab, index) => (
        window.interfaz.html`<button type="button" role="tab" aria-selected="${index === 0}" data-sheet-tab="${index}">${escapeHtml(tab.label)}</button>`
      )).join('');
      nav.hidden = visibleTabs.length < 2;
      body.innerHTML = visibleTabs.map((tab, index) => (
        window.interfaz.html`<section data-sheet-panel="${index}"${index ? ' hidden' : ''}>${tab.html}</section>`
      )).join('') || window.interfaz.html`<p class="rw-empty-note">Sin información adicional publicada.</p>`;
      resourceSheet.hidden = false;
      document.body.classList.add('reservation-sheet-open');
      resourceSheet.scrollTop = 0;
      resourceSheet.querySelector('[data-sheet-close]')?.focus?.({ preventScroll: true });
      resourceSheet.querySelectorAll('iframe[data-src]').forEach((frame) => {
        frame.src = frame.dataset.src;
        frame.removeAttribute('data-src');
      });
    }

    resourceSheet.querySelector('[data-sheet-close]')?.addEventListener('click', closeResourceSheet);
    if (window.jQuery) window.jQuery(modal).on('hidden.bs.modal', closeResourceSheet);
    else modal.addEventListener('hidden.bs.modal', closeResourceSheet);
    resourceSheet.addEventListener('click', (event) => {
      if (event.target === resourceSheet) {
        closeResourceSheet();
        return;
      }
      const chooseSpace = event.target.closest('[data-sheet-space-toggle]');
      if (chooseSpace) {
        const input = spaceInputs.find((item) => item.value === chooseSpace.dataset.sheetSpaceToggle);
        if (!input || input.disabled) return;
        input.checked = !input.checked;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        closeResourceSheet();
        return;
      }
      const tab = event.target.closest('[data-sheet-tab]');
      if (!tab) return;
      resourceSheet.querySelectorAll('[data-sheet-tab]').forEach((other) => other.setAttribute('aria-selected', String(other === tab)));
      resourceSheet.querySelectorAll('[data-sheet-panel]').forEach((panel) => {
        panel.hidden = panel.dataset.sheetPanel !== tab.dataset.sheetTab;
      });
    });
    document.addEventListener('keydown', (event) => {
      if (resourceSheet.hidden) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeResourceSheet();
      } else if (event.key === 'Tab') {
        const focusable = Array.from(resourceSheet.querySelectorAll('button:not(:disabled), a[href], iframe, input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'))
          .filter((node) => !node.closest('[hidden]'));
        const target = event.shiftKey ? focusable[focusable.length - 1] : focusable[0];
        if (!resourceSheet.contains(document.activeElement)
            || (event.shiftKey && document.activeElement === focusable[0])
            || (!event.shiftKey && document.activeElement === focusable[focusable.length - 1])) {
          event.preventDefault();
          target?.focus?.();
        }
      }
    }, true);

    function sheetFacts(rows) {
      const items = rows.filter(([, value]) => value);
      if (!items.length) return '';
      return window.interfaz.html`<dl class="reservation-sheet__facts">${items.map(([label, value]) => window.interfaz.html`<div><dt>${escapeHtml(label)}</dt><dd>${value}</dd></div>`).join('')}</dl>`;
    }

    function sheetText(title, value) {
      if (!value) return '';
      return window.interfaz.html`<h4>${escapeHtml(title)}</h4><p>${escapeHtml(value).replace(/\n/g, window.interfaz.html`<br>`)}</p>`;
    }

    function currentUnits() {
      return Array.isArray(window.unidadesLaboratorioActuales) ? window.unidadesLaboratorioActuales : [];
    }

    function renderAreaEquipmentSummaries() {
      if (resourceSheet.hidden || !resourceSheet.dataset.spaceId) return;
      const units = new Map(Array.from(form.querySelectorAll('[data-equipment-unit]'), (source) => [
        source.dataset.equipmentUnit,
        { id: source.dataset.equipmentUnit, equipo_id: source.dataset.equipmentModelId,
          equipo_nombre: source.dataset.equipmentName }
      ]));
      // La API aporta las mismas categorías que usa el selector inferior.
      currentUnits().forEach((unit) => units.set(String(unit.id), unit));
      const input = spaceInputs.find((item) => item.value === resourceSheet.dataset.spaceId);
      const target = resourceSheet.querySelector('[data-space-equipment-summary]');
      if (!input || !target) return;
      const html = areaEquipmentSummaryHtml(summarizeAreaEquipment(spaceEquipmentIds(input), Array.from(units.values()), Number.MAX_SAFE_INTEGER));
      if (target.innerHTML !== html) target.innerHTML = html;
      target.hidden = !html;
    }

    function openSpaceSheet(trigger) {
      const card = trigger.closest('.reservation-space-item');
      const input = card?.querySelector('input[name="espacios_solicitados"]');
      const content = card?.querySelector('[data-space-detail-content]');
      if (!input || !content) return;
      const label = input.checked ? gettext('Quitar de la selección') : gettext('Seleccionar esta área');
      openResourceSheet({
        kind: gettext('Área de la unidad'),
        title: card.querySelector('.reservation-space-item__title').textContent.trim(),
        mode: 'area',
        tabs: [{ label: gettext('El área'), html: content.innerHTML + window.interfaz.html`<div class="reservation-area-detail__action"><button type="button" class="rw-button" data-sheet-space-toggle="${escapeHtml(input.value)}" ${input.disabled ? 'disabled' : ''}><i class="fas fa-check" aria-hidden="true"></i> ${label}</button></div>` }]
      }, trigger);
      resourceSheet.dataset.spaceId = input.value;
      renderAreaEquipmentSummaries();
    }

    spaceCatalog?.addEventListener('click', (event) => {
      const trigger = event.target.closest('[data-space-detail]');
      if (trigger) openSpaceSheet(trigger);
    });

    function openEquipmentSheet(equipmentId, trigger) {
      const units = currentUnits().filter((unit) => String(unit.equipo_id) === String(equipmentId));
      if (!units.length) return;
      const equipment = units[0];
      const available = units.filter((unit) => unit.disponible);
      const unitIds = units.map((unit) => Number(unit.id));
      const unitList = window.interfaz.html`<ul class="reservation-sheet__units">${units.map((unit) => (
        window.interfaz.html`<li><b>${escapeHtml(unit.codigo || 'Unidad')}</b><span>${escapeHtml(unit.ubicacion || 'Ubicación por confirmar')}</span><em class="${unit.disponible ? 'is-ok' : ''}">${unit.disponible ? gettext('Disponible') : escapeHtml(unit.estado || 'No disponible')}</em></li>`
      )).join('')}</ul>`;
      const software = softwareInputs
        .map((input) => input.closest('.reservation-software-item'))
        .filter((item) => item && softwareEquipmentIds(item.querySelector('input')).some((id) => unitIds.includes(id)))
        .map((item) => window.interfaz.html`<li><b>${escapeHtml(item.querySelector('strong')?.textContent.trim() || '')}</b><span>${escapeHtml(item.dataset.softwareAccess || '')}</span></li>`);
      const consumables = Array.from(form.querySelectorAll('.reservation-consumable:not(.is-mirror)'))
        .filter((card) => consumableEquipmentIds(card).includes(Number(equipmentId)))
        .map((card) => window.interfaz.html`<li><b>${escapeHtml(card.querySelector('.reservation-consumable__identity h4')?.textContent.trim() || '')}</b><span>${escapeHtml((card.querySelector('.reservation-consumable__stock')?.textContent || '').trim().replace(/\s+/g, ' '))}</span></li>`);
      const image = equipment.imagen_url
        ? window.interfaz.html`<figure class="reservation-sheet__figure"><img src="${escapeHtml(equipment.imagen_url)}" alt="${escapeHtml(equipment.equipo_nombre || '')}"></figure>`
        : '';
      const manualIsPdf = /\.pdf(?:[?#]|$)/i.test(equipment.manual_url || '');
      const files = [
        equipment.manual_url ? window.interfaz.html`<a href="${escapeHtml(equipment.manual_url)}" ${manualIsPdf ? window.interfaz.html`data-ver-pdf data-pdf-titulo="Manual de operación · ${escapeHtml(equipment.equipo_nombre || 'Equipo')}" data-pdf-descarga="${escapeHtml(equipment.manual_url)}"` : 'download'}><i class="fas fa-book-open"></i> ${manualIsPdf ? 'Manual de operación' : 'Descargar manual de operación'}</a>` : '',
        equipment.ficha_tecnica_url ? window.interfaz.html`<a href="${escapeHtml(equipment.ficha_tecnica_url)}" data-ver-pdf data-pdf-titulo="Ficha técnica · ${escapeHtml(equipment.nombre || equipment.name || 'Equipo')}" data-pdf-descarga="${escapeHtml(equipment.ficha_tecnica_url)}"><i class="fas fa-file-pdf"></i> Ficha técnica</a>` : '',
        equipment.video_url ? window.interfaz.html`<a href="${escapeHtml(equipment.video_url)}" target="_blank" rel="noopener"><i class="fas fa-video"></i> Video de montaje y cuidados</a>` : ''
      ].filter(Boolean);
      openResourceSheet({
        kind: equipment.categoria || 'Equipo',
        title: equipment.equipo_nombre || 'Equipo',
        subtitle: [equipment.equipo_codigo, [equipment.marca, equipment.modelo].filter(Boolean).join(' ')].filter(Boolean).join(' · '),
        tabs: [
          {
            label: gettext('Características'),
            html: window.interfaz.html`<div class="reservation-sheet__columns"><div>${sheetFacts([
              [gettext('Código'), escapeHtml(equipment.equipo_codigo || '')],
              [gettext('Marca'), escapeHtml(equipment.marca || '')],
              [gettext('Modelo'), escapeHtml(equipment.modelo || '')],
              [gettext('Categoría'), escapeHtml(equipment.categoria || '')],
              [gettext('Disponibilidad'), `${available.length} de ${units.length} unidad${units.length === 1 ? '' : 'es'}`],
              [gettext('Equipos auxiliares'), escapeHtml((equipment.auxiliares || []).join(', ') || 'Ninguno')],
              [gettext('Accesorios incluidos'), escapeHtml((equipment.accesorios || []).join(', ') || 'Ninguno')]
            ])}${sheetText('Características', equipment.caracteristicas_publicas)}${sheetText('Uso', equipment.uso_publico)}${sheetText('Cómo prepararse', equipment.instrucciones_publicas)}</div>${image}</div>`
          },
          { label: gettext('Unidades y ubicación'), html: unitList },
          {
            label: gettext('Software e insumos'),
            html: (software.length || consumables.length)
              ? `${software.length ? window.interfaz.html`<h4>Software instalado</h4><ul class="reservation-sheet__list">${software.join('')}</ul>` : ''}${consumables.length ? window.interfaz.html`<h4>Insumos compatibles</h4><ul class="reservation-sheet__list">${consumables.join('')}</ul>` : ''}`
              : ''
          },
          { label: gettext('Archivos'), html: files.length ? window.interfaz.html`<div class="reservation-sheet__files">${files.join('')}</div>` : '' }
        ]
      }, trigger);
    }

    // Detalles desplegables de software e insumos: uno abierto a la vez por lista.
    function toggleItemDetails(item, open) {
      const details = item.querySelector('[data-item-details]');
      const toggle = item.querySelector('[data-item-toggle]');
      const shouldOpen = open ?? item.classList.contains('is-collapsed');
      if (shouldOpen) {
        Array.from(item.parentElement?.children || []).forEach((sibling) => {
          if (sibling !== item && sibling.querySelector?.('[data-item-details]')) toggleItemDetails(sibling, false);
        });
      }
      item.classList.toggle('is-collapsed', !shouldOpen);
      if (details) details.hidden = !shouldOpen;
      if (toggle) {
        toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
        toggle.innerHTML = window.interfaz.html`<i class="fas fa-chevron-${shouldOpen ? 'up' : 'down'}" aria-hidden="true"></i> ${shouldOpen ? gettext('Ocultar') : gettext('Detalles')}`;
      }
    }
    form.addEventListener('click', (event) => {
      const toggle = event.target.closest('[data-item-toggle]');
      if (!toggle) return;
      // Dentro de un <label>: no debe marcar la casilla.
      event.preventDefault();
      const item = toggle.closest('.reservation-software-item, .reservation-consumable');
      if (item) toggleItemDetails(item);
    });
    form.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const toggle = event.target.closest?.('[data-item-toggle]');
      if (!toggle) return;
      event.preventDefault();
      const item = toggle.closest('.reservation-software-item, .reservation-consumable');
      if (item) toggleItemDetails(item);
    });

    // Nombres de los equipos compatibles de cada insumo, dentro de sus detalles.
    function fillConsumableCompatibility() {
      const units = currentUnits();
      form.querySelectorAll('.reservation-consumable').forEach((card) => {
        const target = card.querySelector('[data-consumable-compatible-names]');
        if (!target) return;
        const names = [...new Set(consumableEquipmentIds(card)
          .map((id) => units.find((unit) => Number(unit.equipo_id) === id)?.equipo_nombre)
          .filter(Boolean))];
        const text = names.length ? names.join(', ') : (consumableEquipmentIds(card).length ? gettext('Equipos indicados por la unidad') : gettext('Uso general en la unidad'));
        if (target.textContent !== text) target.textContent = text;
      });
    }

    document.addEventListener('click', (event) => {
      const equipmentTrigger = event.target.closest('[data-equipment-sheet]');
      if (equipmentTrigger && modal.contains(equipmentTrigger)) {
        openEquipmentSheet(equipmentTrigger.dataset.equipmentSheet, equipmentTrigger);
        return;
      }
    });

    if (equipmentCatalog && typeof MutationObserver !== 'undefined') {
      // La sincronizacion mueve nodos dentro del catalogo observado; sin esta
      // guarda el observador se vuelve a disparar con sus propios cambios.
      let syncingEquipment = false;
      const equipmentObserver = new MutationObserver(() => {
        if (syncingEquipment) return;
        syncingEquipment = true;
        try {
          syncEquipmentAvailability();
          renderAreaEquipmentSummaries();
        } finally {
          equipmentObserver.takeRecords();
          syncingEquipment = false;
        }
      });
      equipmentObserver.observe(equipmentCatalog, { childList: true, subtree: true });
    }

    resourceKindToggles.forEach((input) => input.addEventListener('change', () => {
      const kind = input.dataset.resourceKindToggle;
      if (kind === 'espacio') spaceSelectedExplicitly = input.checked;
      if (kind === 'equipo') equipmentSelectedExplicitly = input.checked;
      state.resources[kind] = input.checked;
      syncResourceChoices();
      updateTypeUI();
      intentionValidationMessage.hidden = true;
      resourceValidationMessage.hidden = true;
    }));
    spaceInputs.forEach((input) => input.addEventListener('change', () => {
      input.closest('.reservation-space-item')?.classList.toggle('is-selected', input.checked);
      syncResourceChoices();
      updateTypeUI();
      syncSpaceEquipmentCompatibility({ autoSelect: false });
      resourceValidationMessage.hidden = true;
      updateAutomaticTitle();
      syncScopeNotice();
    }));
    // El mismo diálogo amplio muestra plano, video o 360 sin abrir paneles en la grilla.
    const spaceOrientation = spaceCatalog?.querySelector('[data-space-orientation]');
    spaceOrientation?.querySelectorAll('[data-orientation-open]').forEach((button) => {
      button.addEventListener('click', () => {
        const content = spaceOrientation.querySelector(`#${button.dataset.orientationOpen}`);
        if (!content) return;
        openResourceSheet({ kind: gettext('Conoce la unidad'), title: button.textContent.trim(),
          mode: 'media', tabs: [{ label: button.textContent.trim(), html: content.innerHTML }] }, button);
      });
    });
    spaceScopeInputs.forEach((input) => input.addEventListener('change', () => {
      syncSpaceScope();
      syncResourceChoices();
      updateTypeUI();
      syncSpaceEquipmentCompatibility({ autoSelect: false });
      resourceValidationMessage.hidden = true;
      updateAutomaticTitle();
      if (typeof window.refreshCalendarAvailability === 'function') {
        window.refreshCalendarAvailability();
      }
    }));

    function selectedProvision() {
      return provisionInput?.value || 'ninguno';
    }

    function syncProvision() {
      if (!provisionInput) return;
      // Un original marcado desde el espejo de otra tarjeta puede quedar
      // bloqueado en la suya: cuenta lo marcado (updateConsumableGuidance ya
      // desmarca lo que no tiene un equipo compatible seleccionado).
      provisionInput.value = consumableChecks.some((check) => check.checked) ? 'unidad' : 'ninguno';
    }

    // Sesiones aproximadas de una programacion semanal (el servidor confirma
    // el numero exacto con el calendario academico).
    const sessionEstimateNote = form.querySelector('[data-session-estimate]');
    function estimatedSessions() {
      const frequency = selectedFrequency();
      const firstDate = (element('fechaInicio')?.value || '').slice(0, 10);
      if (frequency === 'unica' || !firstDate) return 1;
      let limit = '';
      if (frequency === 'semanal_rango') limit = frequencyRangeEnd?.value || '';
      else {
        const period = academicPeriods.find((item) => item.inicio <= firstDate && firstDate <= item.fin);
        limit = period?.fin_clases || period?.fin || '';
      }
      if (!limit) return 1;
      const start = new Date(`${firstDate}T12:00:00`);
      const end = new Date(`${limit}T12:00:00`);
      const weeks = Math.floor((end - start) / (7 * 24 * 3600 * 1000)) + 1;
      return Math.max(1, Math.min(26, weeks));
    }
    function renderResourceCost(selected = []) {
      if (!resourceCostResult) return;
      const provision = selectedProvision();
      if (state.type !== 'recursos') return;
      const counts = selectedResourceCounts();
      let duration = 0;
      try {
        const hours = JSON.parse(element('horasSeleccionadas')?.value || '[]');
        duration = new Set(hours.map(Number).filter(Number.isInteger)).size;
      } catch (_error) {
        duration = 0;
      }
      const sessions = estimatedSessions();
      if (sessionEstimateNote) {
        sessionEstimateNote.textContent = sessions > 1
          ? `Aproximadamente ${sessions} sesiones de ${duration || '—'} h; el número exacto lo confirma el calendario académico al enviar.`
          : '';
      }
      let materialTotal = 0;
      let supportTotal = 0;
      let pending = 0;
      const missingRates = [];
      const rows = provision === 'unidad' ? selected.map((item) => {
        const quantity = item.cantidad === null ? null : Number(item.cantidad || 0);
        const price = Number(item.precio_unitario || 0);
        // La cantidad escrita es la de una sesión; el total la multiplica.
        const totalQuantity = quantity === null ? null : quantity * sessions;
        const subtotal = totalQuantity === null ? 0 : totalQuantity * price;
        materialTotal += subtotal;
        if (quantity === null) pending += 1;
        const unit = escapeHtml(item.unidad_medida);
        const quantityText = quantity === null
          ? gettext('Por calcular en la revisión')
          : sessions > 1
            ? `${quantity} ${unit} × ${sessions} sesiones = ${redondear(totalQuantity)} ${unit}`
            : `${quantity} ${unit}`;
        return window.interfaz.html`<tr><td>${escapeHtml(item.nombre)}${item.detalle ? window.interfaz.html`<small>${escapeHtml(item.detalle)}</small>` : ''}</td><td>${quantityText}</td><td>${money(price)} por ${unit}</td><td>${money(subtotal)}</td><td>${money(0)}</td><td>${money(subtotal)}</td></tr>`;
      }) : [];
      const supportDefinitions = [
        ['espacio', gettext('Espacio y mobiliario'), counts.spaces],
        ['equipo', gettext('Equipos o instrumentos'), counts.equipment],
        ['software', gettext('Software o licencias'), counts.software],
        ['acompanamiento', gettext('Acompañamiento técnico'), Object.values(counts).some(Boolean) ? 1 : 0]
      ];
      supportDefinitions.forEach(([kind, label, quantity]) => {
        if (!quantity) return;
        const rate = resourceReferenceRates[kind];
        const subtotal = quantity * duration * sessions * rate;
        supportTotal += subtotal;
        if (!rate) missingRates.push(label);
        const contribution = subtotal * resourceReferenceRates.aporte / 100;
        // Sin horario todavia: se muestra lo que vale cada hora y cuanto asume la UPEC.
        const hourly = quantity * rate;
        const hourlyContribution = hourly * resourceReferenceRates.aporte / 100;
        const perHour = !duration;
        rows.push(window.interfaz.html`<tr><td>${label}${rate ? '' : window.interfaz.html`<small>Tarifa por configurar</small>`}</td><td>${perHour ? `${quantity} × cada hora` : `${quantity} × ${duration} h${sessions > 1 ? ` × ${sessions} sesiones` : ''}`}</td><td>${money(rate)} por hora</td><td>${perHour ? `${money(hourly)}/h` : money(subtotal)}</td><td>${perHour ? (hourlyContribution > 0 ? `−${money(hourlyContribution)}/h` : money(0)) : (contribution > 0 ? `−${money(contribution)}` : money(0))}</td><td>${perHour ? `${money(hourly - hourlyContribution)}/h` : money(subtotal - contribution)}</td></tr>`);
      });
      const contribution = supportTotal * resourceReferenceRates.aporte / 100;
      const userSubtotal = Math.round((materialTotal + Number.EPSILON) * 100) / 100;
      const tax = taxFor(userSubtotal);
      if (resourceReferenceRates.taxApplies && rows.length) {
        rows.push(window.interfaz.html`<tr class="is-tax"><td>IVA ${resourceReferenceRates.taxRate.toFixed(0)} %<small>Sobre lo que pagas</small></td><td>—</td><td>—</td><td>${money(tax)}</td><td>${money(0)}</td><td>${money(tax)}</td></tr>`);
      }
      const userTotal = userSubtotal + tax;
      const guidance = provision === 'unidad'
        ? ''
        : gettext('Sin insumos del laboratorio: marca los que necesites en la tarjeta de su equipo y se sumarán aquí.');
      const scheduleNotice = duration
        ? `${duration} hora(s) seleccionada(s).`
        : gettext('Selecciona el horario para conocer el aporte de la UPEC por los recursos y el personal.');
      resourceCostResult.innerHTML = window.interfaz.html`
        ${guidance ? window.interfaz.html`<p>${guidance}</p>` : ''}
        ${rows.length ? window.interfaz.html`<div class="reservation-quote__table"><table class="reservation-quote__resources"><thead><tr><th>Concepto</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th><th>Lo asume la UPEC</th><th>A tu cargo</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>` : ''}
        <div class="reservation-quote__total"><span>Insumos ${money(materialTotal)} (se cobran según consumo real) · apoyos ${money(supportTotal)}, de los que la UPEC asume ${money(contribution)} (${resourceReferenceRates.aporte.toFixed(0)} %)${resourceReferenceRates.taxApplies ? ` · IVA ${money(tax)}` : ''}</span><strong>Estimado a tu cargo: ${money(userTotal)} USD${sessions > 1 ? window.interfaz.html` <em>(${money(userTotal / sessions)} por sesión · ${sessions} sesiones)</em>` : ''}</strong><small>${scheduleNotice} ${pending ? `Falta${pending === 1 ? '' : 'n'} ${pending} cantidad(es): ese consumo no está incluido en el valor. ` : ''}${missingRates.length ? `Falta configurar: ${missingRates.join(', ')}. ` : ''}Es una simulación; el valor real se determina con el consumo y tiempo ejecutados. Los insumos se cobran según el consumo real y los recursos reservados deben utilizarse: el incumplimiento resta prioridad en futuras reservas y servicios.</small></div>`;
    }

    function syncConsumables() {
      if (!consumableSelection) return [];
      if (selectedProvision() !== 'unidad') {
        consumableSelection.value = '[]';
        return [];
      }
      const selected = consumableChecks
        .filter((check) => check.checked)
        .map((check) => {
          const card = check.closest('.reservation-consumable');
          const input = card?.querySelector('.reservation-consumable__quantity');
          const raw = (input?.value || '').trim();
          // Al servidor va lo que consume una sesión completa: la cantidad
          // escrita por pieza multiplicada por las piezas de la sesión.
          const porSesion = raw === ''
            ? null
            : Math.round(Number(raw) * resourceWorkUnits(card) * 1000) / 1000;
          return {
            id: Number(check.dataset.consumibleId),
            nombre: input?.dataset.consumibleNombre || '',
            detalle: input?.dataset.detalle || '',
            unidad_medida: input?.dataset.unidadMedida || 'unidades',
            precio_unitario: input?.dataset.precioUnitario || '',
            cantidad: porSesion,
            metodo_estimacion: raw === '' ? 'revision' : 'estimacion'
          };
        });
      consumableSelection.value = JSON.stringify(selected);
      renderResourceCost(selected);
      return selected;
    }

    function selectedServiceIds() {
      return serviceInputs.filter((input) => input.checked).map((input) => input.value);
    }

    function filterConsumablesByService() {
      const selectedIds = selectedServiceIds();
      const selectedEquipmentIds = new Set(
        Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
          .map((input) => String(input.dataset.equipoId || ''))
          .filter(Boolean)
      );
      let compatibleCount = 0;
      let availableCompatibleCount = 0;
      let controlledEquipment = false;
      // La cascada mueve el catalogo al paso 3: se consulta el catalogo, no el paso 4.
      const inventoryRoot = inventoryCatalog || requirementsGrid;
      form.querySelectorAll('.reservation-consumable:not(.is-mirror)').forEach((card) => {
        const related = (card.dataset.serviceIds || '').split(',').filter(Boolean);
        const serviceCompatible = state.type !== 'servicio'
          || !selectedIds.length
          || related.some((id) => selectedIds.includes(id));
        const compatibleEquipmentIds = (card.dataset.compatibleEquipmentIds || '')
          .split(',')
          .filter(Boolean);
        if (compatibleEquipmentIds.some((id) => selectedEquipmentIds.has(id))) {
          controlledEquipment = true;
        }
        const equipmentCompatible = !selectedEquipmentIds.size
          || !compatibleEquipmentIds.length
          || compatibleEquipmentIds.some((id) => selectedEquipmentIds.has(id));
        const visible = serviceCompatible;
        card.classList.toggle('is-filtered-out', !serviceCompatible);
        card.classList.toggle('is-equipment-incompatible', !equipmentCompatible);
        card.setAttribute('aria-disabled', String(!equipmentCompatible));
        if (visible && equipmentCompatible) {
          compatibleCount += 1;
          if (card.querySelector('.reservation-consumable__quantity')?.dataset.stockAvailable === 'true') {
            availableCompatibleCount += 1;
          }
        }
        if (!visible || !equipmentCompatible) {
          const check = card.querySelector('.reservation-consumable__check');
          if (check) check.checked = false;
        }
      });
      // El catalogo general solo muestra insumos transversales o de uso general;
      // los de un unico equipo viven en la tarjeta de ese equipo.
      const generalCompatible = Array.from(inventoryRoot.querySelectorAll('.reservation-consumable'))
        .filter((card) => !card.classList.contains('is-filtered-out') && !card.classList.contains('is-equipment-incompatible')).length;
      if (consumableCatalog) consumableCatalog.classList.toggle('is-empty', state.type === 'recursos' && !generalCompatible);
      inventoryRoot.querySelectorAll('.reservation-inventory-family').forEach((family) => {
        const hasVisibleItems = Array.from(family.querySelectorAll('.reservation-consumable'))
          .some((item) => !item.classList.contains('is-filtered-out') && !item.classList.contains('is-equipment-incompatible'));
        family.hidden = !hasVisibleItems;
      });
      inventoryRoot.querySelectorAll('.reservation-inventory-type').forEach((type) => {
        const hasVisibleFamilies = Array.from(type.querySelectorAll('.reservation-inventory-family'))
          .some((family) => !family.hidden);
        type.hidden = !hasVisibleFamilies;
      });
      if (consumableCompatibility) {
        consumableCompatibility.hidden = state.type === 'servicio' || !selectedEquipmentIds.size;
        consumableCompatibility.classList.toggle('is-warning', !availableCompatibleCount);
        consumableCompatibility.innerHTML = availableCompatibleCount
          ? window.interfaz.html`<i class="fas fa-check-circle"></i><div><strong>${availableCompatibleCount} opción(es) compatible(s) disponible(s)</strong><span>El resto del inventario permanece visible solo como referencia y no puede seleccionarse con los equipos actuales.${controlledEquipment ? gettext(' Para proteger los equipos solo se usan los materiales homologados del laboratorio.') : ''}</span></div>`
          : window.interfaz.html`<i class="fas fa-info-circle"></i><div><strong>Los equipos elegidos no requieren artículos compatibles del catálogo</strong><span>La reserva se registra sin insumos. El inventario sigue visible para explicar por qué no corresponde a esta reserva.</span></div>`;
      }
      return { compatibleCount, availableCompatibleCount, controlledEquipment };
    }

    function updateConsumableGuidance() {
      const anyEquipmentSelected = Boolean(form.querySelector('.unidad-checkbox:checked'));
      const spaceOnly = state.type === 'recursos' && resourceKindActive('espacio') && !resourceKindActive('equipo');
      consumableChecks.forEach((check) => {
        const card = check.closest('.reservation-consumable');
        const available = card?.querySelector('.reservation-consumable__quantity')?.dataset.stockAvailable === 'true';
        const baseEnabled = inventoryOffered && available
          && !card?.classList.contains('is-filtered-out')
          && !card?.classList.contains('is-equipment-incompatible');
        check.dataset.rwBaseEnabled = baseEnabled ? 'true' : 'false';
        // Un insumo solo se elige desde la tarjeta de un equipo ya marcado; los
        // de uso general esperan a que haya un equipo (o solo un espacio).
        const ownGroup = card?.closest('[data-equipment-row]');
        const unlocked = state.type !== 'recursos'
          || (ownGroup ? ownGroup.classList.contains('is-selected') : (anyEquipmentSelected || spaceOnly));
        check.disabled = !baseEnabled || !unlocked;
        const anyCompatibleSelected = ownGroup
          ? consumableEquipmentIds(card).some((id) => groupForEquipmentId(id)?.classList.contains('is-selected'))
          : unlocked;
        if (!baseEnabled || !anyCompatibleSelected) check.checked = false;
        // Lo que el proceso exige no se quita: queda marcado aunque falte existencia.
        if (check.dataset.processLocked === 'true') {
          check.disabled = false;
          check.checked = true;
        }
      });
      consumableInputs.forEach((input) => {
        const card = input.closest('.reservation-consumable');
        const check = card?.querySelector('.reservation-consumable__check');
        input.disabled = !check?.checked;
        input.required = false;
        checkConsumableStock(input);
      });
      syncScopeNotice();
      updateConsumableTotals();
      // La forma de provision se deduce de lo marcado.
      syncProvision();
      if (consumableCatalog) {
        consumableCatalog.classList.toggle('is-readonly', !consumableChecks.some((check) => !check.disabled));
      }
      syncConsumables();
      refreshConsumableMirrors();
    }

    consumableChecks.forEach((check) => check.addEventListener('change', () => {
      check.closest('.reservation-consumable')?.classList.toggle('is-selected', check.checked);
      updateConsumableGuidance();
      renderResourceCost(syncConsumables());
    }));
    // Aviso inmediato cuando la cantidad supera la existencia; bloquea el avance.
    // Piezas, muestras o ensayos de cada sesión: el insumo se indica por pieza
    // y el sistema calcula lo que consumirá la reserva completa.
    const workUnitsInput = element('piezasPorSesionReserva');
    const scopeNotice = element('avisoAlcanceRecursos');
    const scopeConfirm = element('confirmarAlcanceRecursos');

    // Cantidades legibles: sin ceros decimales inventados.
    function redondear(valor) {
      return Number.isFinite(valor) ? String(Math.round(valor * 1000) / 1000) : '';
    }

    // La existencia se compara con lo que consumirá toda la reserva: la
    // cantidad de una sesión repetida en cada una de sus sesiones.
    function checkConsumableStock(input) {
      const card = input.closest('.reservation-consumable');
      const note = card?.querySelector('[data-stock-note]');
      const check = card?.querySelector('.reservation-consumable__check');
      const stock = Number(input.max);
      const sessions = estimatedSessions();
      const value = Number(input.value || 0) * resourceWorkUnits(card) * sessions;
      const over = Boolean(check?.checked) && !input.disabled && Number.isFinite(stock) && value > stock
        && check?.dataset.processLocked !== 'true';
      const unidad = input.dataset.unidadMedida || 'unidades';
      card?.classList.toggle('is-over-stock', over);
      if (note) {
        note.hidden = !over;
        note.textContent = over
          ? `Solo hay ${input.max} ${unidad} disponibles y la reserva consumiría ${redondear(value)}${sessions > 1 ? ` (${sessions} sesiones)` : ''}. Reduce la cantidad, ${trabajoEsFemenino() ? 'las' : 'los'} ${palabraTrabajo(true)} o elige otro material.`
          : '';
      }
      input.setCustomValidity(over ? gettext('La cantidad supera la existencia disponible.') : '');
      return !over;
    }

    // Total de la reserva junto al campo: lo calcula el sistema y no se edita.
    function updateConsumableTotals() {
      const sessions = estimatedSessions();
      form.querySelectorAll('.reservation-consumable:not(.is-mirror)').forEach((card) => {
        const units = resourceWorkUnits(card);
        const salida = card.querySelector('[data-quantity-total]');
        const input = card.querySelector('.reservation-consumable__quantity');
        const etiqueta = card.querySelector('[data-quantity-label]');
        if (!salida || !input) return;
        const unidad = input.dataset.unidadMedida || 'unidades';
        if (etiqueta) {
          etiqueta.textContent = `${units > 1 ? `Cantidad por ${palabraTrabajo()}` : gettext('Cantidad')} (${unidad})`
            + (etiqueta.dataset.stock ? ` · disponible ${etiqueta.dataset.stock}` : '');
        }
        const valor = Number((input.value || '').trim());
        if (!(input.value || '').trim() || !Number.isFinite(valor) || valor <= 0) {
          salida.textContent = gettext('Total: escribe la cantidad');
          return;
        }
        const factores = [];
        if (units > 1) factores.push(contarTrabajo(units));
        if (sessions > 1) factores.push(`${sessions} sesiones`);
        salida.textContent = factores.length
          ? `Total: ${redondear(valor)} ${unidad} × ${factores.join(' × ')} = ${redondear(valor * units * sessions)} ${unidad}`
          : `Total: ${redondear(valor)} ${unidad}`;
      });
      refreshConsumableMirrors();
      syncScopeNotice();
    }
    function consumablesWithinStock() {
      return !form.querySelector('.reservation-consumable.is-over-stock:not(.is-mirror):not(.is-process-locked)');
    }
    // Primer insumo marcado sin cantidad: la cantidad se pide siempre.
    function consumableWithoutQuantity() {
      return Array.from(form.querySelectorAll('.reservation-consumable:not(.is-mirror)')).find((card) => (
        card.querySelector('.reservation-consumable__check')?.checked
        && !(card.querySelector('.reservation-consumable__quantity')?.value || '').trim()
      )) || null;
    }
    function refreshWorkUnits() {
      syncEquipmentWorkSummary();
      consumableInputs.forEach((input) => checkConsumableStock(input));
      updateConsumableTotals();
      renderResourceCost(syncConsumables());
    }
    workUnitsInput?.addEventListener('input', refreshWorkUnits);
    scopeConfirm?.addEventListener('change', () => {
      resourceValidationMessage.hidden = true;
    });
    // Las franjas de cada equipo se crean al vuelo: se escuchan desde el formulario.
    form.addEventListener('input', (event) => {
      if (event.target.matches('[data-equipment-pieces]')) refreshWorkUnits();
      else if (event.target.matches('[data-equipment-detail]')) syncEquipmentWorkSummary();
    });
    consumableInputs.forEach((input) => input.addEventListener('input', () => {
      checkConsumableStock(input);
      updateConsumableTotals();
      syncConsumables();
      refreshConsumableMirrors();
    }));

    function updateServiceModeAvailability() {
      const selected = selectedServiceInputs();
      const datasetKeys = {
        modelo_listo: 'allowsModelReady',
        diseno_asistido: 'allowsAssisted',
        diseno_completo: 'allowsComplete'
      };
      const palabras = palabrasServicio();
      syncServiceWording();
      const unavailableModes = [];
      let assistedUnavailableByFacility = false;
      serviceModes.forEach((input) => {
        const supportedByServices = selected.every((serviceInput) => (
          serviceInput.closest('.reservation-service')?.dataset[datasetKeys[input.value]] !== 'false'
        ));
        const supportedByFacility = input.value !== 'diseno_asistido' || resourceAvailability.espacio;
        const allowed = selected.length > 0 && supportedByServices && supportedByFacility;
        input.disabled = state.type !== 'servicio' || !allowed;
        input.required = state.type === 'servicio' && allowed;
        input.closest('[data-service-mode]')?.classList.toggle('is-disabled', !allowed);
        if (!allowed) input.checked = false;
        if (selected.length && !allowed) {
          if (input.value === 'diseno_asistido' && !supportedByFacility) assistedUnavailableByFacility = true;
          else unavailableModes.push(`«${(palabras[input.value] || [])[0]}»`);
        }
      });
      if (serviceModeGuidance) {
        const guidance = [];
        if (assistedUnavailableByFacility) {
          guidance.push(`La modalidad «${(palabras.diseno_asistido || [])[0]}» no está disponible porque esta unidad no permite reservar su espacio de trabajo.`);
        }
        if (unavailableModes.length) {
          guidance.push(`Los servicios seleccionados no admiten conjuntamente estas modalidades: ${unavailableModes.join(', ')}.`);
        }
        serviceModeGuidance.hidden = !guidance.length;
        serviceModeGuidance.textContent = guidance.length
          ? `${guidance.join(' ')} Elige una alternativa habilitada.`
          : '';
      }
      if (!isAssistedService() && state.type === 'servicio') clearComplementaryResources();
    }

    function updateTechnicalFileGuidance() {
      if (!technicalFileRequirement) return;
      const selected = selectedServiceInputs();
      const requiredServices = selected.filter((input) => input.closest('.reservation-service')?.dataset.requiresFiles === 'true');
      const formats = Array.from(new Set(requiredServices
        .flatMap((input) => (input.closest('.reservation-service')?.dataset.formats || '').split(',').map((value) => value.trim()))
        .filter(Boolean)));
      const mode = selectedServiceMode();
      const required = serviceRequiresPreparedFile();
      if (technicalFileInput) {
        technicalFileInput.required = required;
        technicalFileInput.setAttribute('aria-required', String(required));
      }
      technicalFiles?.classList.toggle('is-required', required);
      technicalFiles?.classList.toggle('is-optional', Boolean(mode) && !required);
      technicalFileRequirement.classList.toggle('is-required', required);
      if (technicalFileType) technicalFileType.textContent = required ? gettext('(obligatorio)') : gettext('(opcional)');
      if (technicalFileHelp) {
        technicalFileHelp.textContent = required
          ? gettext('Carga el modelo terminado que el laboratorio debe revisar y fabricar. Agrega para cada archivo la versión del software o cualquier instrucción necesaria.')
          : gettext('Si tienes bocetos, planos o referencias puedes adjuntarlos de forma opcional para orientar al equipo técnico.');
      }
      technicalFileRequirement.textContent = !selected.length
        ? gettext('Selecciona primero el servicio y luego la modalidad de trabajo.')
        : !mode
          ? gettext('Selecciona cómo participarás en el servicio para definir si debes cargar un archivo.')
          : required
            ? `Obligatorio solo porque elegiste “Entrego el modelo listo”.${formats.length ? ` Formatos admitidos por el servicio: ${formats.join(', ')}.` : ''}`
            : mode === 'diseno_asistido'
              ? gettext('Opcional: en “Diseño con asesoría” puedes adjuntar un boceto o referencia, pero no impide continuar.')
              : gettext('Opcional: en “Diseño completo del laboratorio” puedes adjuntar referencias, pero no impide continuar.');
    }

    serviceInputs.forEach((input) => input.addEventListener('change', () => {
      // Cada solicitud corresponde a un trabajo con un servicio: elegir uno
      // desmarca los demas y evita cotizar servicios que no se pidieron.
      if (input.checked) {
        serviceInputs.forEach((other) => {
          if (other !== input && other.checked) {
            other.checked = false;
            other.closest('.reservation-service')?.classList.remove('is-selected');
          }
        });
      }
      input.closest('.reservation-service')?.classList.toggle('is-selected', input.checked);
      updateServiceModeAvailability();
      filterConsumablesByService();
      updateConsumableGuidance();
      updateTechnicalFileGuidance();
      invalidateQuote();
      invalidateProposal();
      renderServiceWork();
      updateAutomaticTitle();
      intentionValidationMessage.hidden = true;
    }));
    window.seleccionarServicioReserva = (serviceId) => {
      const typeButton = types.querySelector('[data-type="servicio"]');
      const input = serviceInputs.find((item) => String(item.value) === String(serviceId));
      if (!typeButton || typeButton.disabled || !input) return false;
      typeButton.click();
      if (!input.checked) input.click();
      showStep(1, true);
      window.setTimeout(() => input.closest('.reservation-service')?.scrollIntoView({
        behavior: 'smooth', block: 'center'
      }), 250);
      return true;
    };
    form.addEventListener('reset', () => setTimeout(() => {
      state.type = initialType;
      state.resources.equipo = false;
      state.resources.espacio = false;
      state.resources.software = false;
      spaceSelectedExplicitly = false;
      equipmentSelectedExplicitly = false;
      requestType.value = initialType;
      types.querySelectorAll('[data-type]').forEach((button) => {
        button.setAttribute('aria-pressed', String(button.dataset.type === initialType));
        button.closest('[data-type-card]')?.classList.toggle('is-selected', button.dataset.type === initialType);
      });
      selectedParticipants.clear();
      syncParticipants();
      if (technicalFileNotes) technicalFileNotes.value = '[]';
      renderTechnicalFiles();
      closeTutorialViewer();
      updateTypeUI();
      updateConsumableGuidance();
      showStep(1, true);
    }, 0));
    updateConsumableGuidance();
    function fileIcon(fileName) {
      const extension = (fileName.split('.').pop() || '').toLowerCase();
      if (['png', 'jpg', 'jpeg', 'webp', 'svg'].includes(extension)) return 'fa-file-image';
      if (extension === 'pdf') return 'fa-file-pdf';
      if (extension === 'zip') return 'fa-file-archive';
      return 'fa-cube';
    }

    function syncTechnicalFileNotes() {
      if (!technicalFileNotes || !technicalFileInput) return;
      const files = Array.from(technicalFileInput.files || []);
      technicalFileNotes.value = JSON.stringify(files.map((file, index) => ({
        nombre: file.name,
        indicaciones: technicalFileList?.querySelector(`[data-file-index="${index}"] textarea`)?.value.trim()
          || technicalFileNoteCache.get(file.name)
          || ''
      })));
    }

    function replaceTechnicalFiles(files) {
      if (!technicalFileInput || typeof DataTransfer === 'undefined') return;
      const transfer = new DataTransfer();
      files.slice(0, 5).forEach((file) => transfer.items.add(file));
      technicalFileInput.files = transfer.files;
      technicalFileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function renderTechnicalFiles() {
      if (!technicalFileInput || !technicalFileList) return;
      const files = Array.from(technicalFileInput.files || []);
      technicalFileList.querySelectorAll('[data-file-name] textarea').forEach((textarea) => {
        technicalFileNoteCache.set(textarea.closest('[data-file-name]').dataset.fileName, textarea.value);
      });
      technicalFileList.innerHTML = '';
      if (technicalFileCount) technicalFileCount.textContent = String(files.length);
      if (technicalFileAttachments) technicalFileAttachments.hidden = files.length === 0;
      if (!files.length) {
        if (technicalFileNotes) technicalFileNotes.value = '[]';
        if (technicalFileStatus) {
          technicalFileStatus.dataset.state = 'empty';
          technicalFileStatus.hidden = true;
          technicalFileStatus.innerHTML = '';
        }
        if (technicalFileProgress) {
          technicalFileProgress.hidden = true;
          technicalFileProgress.dataset.state = 'empty';
        }
        if (technicalFileProgressBar) technicalFileProgressBar.style.width = '0%';
        if (technicalFileProgressText) technicalFileProgressText.textContent = gettext('Preparando archivos');
        if (technicalFileProgressValue) technicalFileProgressValue.textContent = '0%';
        return;
      }
      technicalFiles?.classList.remove('has-validation-error');
      resourceValidationMessage.hidden = true;
      if (technicalFileStatus) {
        technicalFileStatus.dataset.state = 'ready';
        technicalFileStatus.hidden = true;
        technicalFileStatus.innerHTML = '';
      }
      if (technicalFileProgress) {
        technicalFileProgress.hidden = false;
        technicalFileProgress.dataset.state = 'preparing';
      }
      if (technicalFileProgressBar) technicalFileProgressBar.style.width = '0%';
      if (technicalFileProgressText) technicalFileProgressText.textContent = gettext('Preparando archivos');
      if (technicalFileProgressValue) technicalFileProgressValue.textContent = '0%';
      window.requestAnimationFrame(() => {
        if (!technicalFileInput.files?.length) return;
        if (technicalFileProgress) technicalFileProgress.dataset.state = 'ready';
        if (technicalFileProgressBar) technicalFileProgressBar.style.width = '100%';
        if (technicalFileProgressText) technicalFileProgressText.textContent = gettext('Carga preparada y conservada');
        if (technicalFileProgressValue) technicalFileProgressValue.textContent = '100%';
      });
      files.forEach((file, index) => {
        const row = create('article', 'reservation-upload-file');
        row.dataset.fileIndex = String(index);
        row.dataset.fileName = file.name;
        row.innerHTML = window.interfaz.html`
          <span class="reservation-upload-file__icon"><i class="fas ${fileIcon(file.name)}" aria-hidden="true"></i></span>
          <span class="reservation-upload-file__identity"><strong></strong><small>${(file.size / 1048576).toFixed(2)} MB · listo para enviar</small></span>
          <span class="reservation-upload-file__actions">
            <button type="button" class="reservation-upload-file__download" aria-label="Descargar archivo seleccionado" title="Descargar"><i class="fas fa-download" aria-hidden="true"></i></button>
            <button type="button" class="reservation-upload-file__remove" aria-label="Eliminar archivo seleccionado" title="Eliminar"><i class="fas fa-trash-alt" aria-hidden="true"></i></button>
          </span>
          <details class="reservation-upload-file__notes"><summary>Indicaciones para abrir o visualizar (opcional)</summary><label><span>Versión, software o instrucciones</span><textarea rows="2" maxlength="1200" placeholder="Ej. Abrir con Blender 4.2; modelo en milímetros."></textarea></label></details>`;
        row.querySelector('.reservation-upload-file__identity strong').textContent = file.name;
        const notes = row.querySelector('textarea');
        notes.value = technicalFileNoteCache.get(file.name) || '';
        notes.addEventListener('input', () => {
          technicalFileNoteCache.set(file.name, notes.value);
          syncTechnicalFileNotes();
        });
        row.querySelector('.reservation-upload-file__download').addEventListener('click', () => {
          const objectUrl = URL.createObjectURL(file);
          const download = document.createElement('a');
          download.href = objectUrl;
          download.download = file.name;
          document.body.appendChild(download);
          download.click();
          download.remove();
          window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        });
        row.querySelector('.reservation-upload-file__remove').addEventListener('click', () => {
          technicalFileNoteCache.delete(file.name);
          replaceTechnicalFiles(files.filter((_item, fileIndex) => fileIndex !== index));
        });
        technicalFileList.appendChild(row);
      });
      syncTechnicalFileNotes();
    }

    if (technicalFileInput) technicalFileInput.addEventListener('change', renderTechnicalFiles);
    if (technicalFileDropZone) {
      ['dragenter', 'dragover'].forEach((eventName) => technicalFileDropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        technicalFileDropZone.classList.add('is-dragging');
      }));
      ['dragleave', 'drop'].forEach((eventName) => technicalFileDropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        technicalFileDropZone.classList.remove('is-dragging');
      }));
      technicalFileDropZone.addEventListener('drop', (event) => {
        const dropped = Array.from(event.dataTransfer?.files || []);
        if (dropped.length) replaceTechnicalFiles(dropped);
      });
      technicalFileDropZone.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          technicalFileInput?.click();
        }
      });
    }
    renderTechnicalFiles();

    const participantsContainer = element('participantesReserva');
    const participantSearch = element('buscarParticipanteReserva');
    const participantResults = element('resultadosParticipantesReserva');
    const participantSelected = element('seleccionParticipantesReserva');
    const participantCounter = element('contadorParticipantesReserva');
    const participantValue = element('participantesSeleccionados');
    const selectedParticipants = new Map();
    let participantTimer = null;

    function clearParticipantRequirement() {
      participantsContainer?.classList.remove('has-validation-error');
      participantsContainer?.querySelector('[data-participant-requirement-error]')?.remove();
    }

    function syncParticipants() {
      scheduleProcessRefresh();
      if (participantValue) participantValue.value = JSON.stringify(Array.from(selectedParticipants.keys()));
      const totalPeople = selectedParticipants.size + 1;
      const calendarParticipantCount = calendarParticipantSummary?.querySelector('[data-calendar-participant-count]');
      if (calendarParticipantCount) {
        calendarParticipantCount.textContent = selectedParticipants.size
          ? `${totalPeople} personas · solicitante y ${selectedParticipants.size} participante${selectedParticipants.size === 1 ? '' : 's'}`
          : gettext('1 persona · solo el solicitante');
      }
      if (participantCounter) {
        const count = selectedParticipants.size;
        participantCounter.textContent = `${count} participante${count === 1 ? '' : 's'} secundario${count === 1 ? '' : 's'}`;
      }
      if (document.getElementById('calendarViewToolbar')
        && typeof window.refreshCalendarAvailability === 'function') {
        window.refreshCalendarAvailability();
      }
      if (selectedParticipants.size) clearParticipantRequirement();
      if (!participantSelected) return;
      participantSelected.innerHTML = '';
      const scroll = create('div', 'reservation-participants__table-scroll');
      scroll.tabIndex = 0;
      scroll.setAttribute('role', 'region');
      scroll.setAttribute('aria-label', gettext('Datos de los participantes seleccionados'));
      const table = create('table', 'reservation-participants__table');
      const caption = create('caption', 'sr-only');
      caption.textContent = gettext('Participantes secundarios. Los datos se completan desde su perfil.');
      const head = create('thead');
      const heading = create('tr');
      ['#', 'Cédula / documento', 'Nombres completos', 'Rol', 'Datos institucionales', 'Celular', 'Correo', 'Acción'].forEach((label) => {
        const cell = create('th');
        cell.scope = 'col';
        cell.textContent = gettext(label);
        heading.appendChild(cell);
      });
      head.appendChild(heading);
      const rows = create('tbody');
      table.append(caption, head, rows);
      scroll.appendChild(table);
      participantSelected.appendChild(scroll);
      if (!selectedParticipants.size) {
        const row = create('tr');
        const empty = create('td');
        empty.colSpan = 8;
        empty.textContent = gettext('Solo asistirá el solicitante principal. Busca una persona para añadirla a la tabla.');
        row.appendChild(empty);
        rows.appendChild(row);
        return;
      }
      let index = 0;
      selectedParticipants.forEach((person) => {
        const item = create('tr');
        function cell(value) {
          const td = create('td');
          td.textContent = value || gettext('No registrado');
          item.appendChild(td);
          return td;
        }
        cell(String(++index));
        cell(person.documento);
        const content = cell('');
        content.textContent = '';
        const name = create('strong');
        name.textContent = person.nombre;
        const detail = create('small');
        detail.textContent = person.usuario || '';
        content.append(name, detail);
        cell(person.tipo);
        const institution = cell('');
        institution.textContent = '';
        [person.institucion, person.facultad, person.carrera, person.nivel].filter(Boolean).forEach((value) => {
          const line = create('small');
          line.textContent = value;
          institution.appendChild(line);
        });
        if (!institution.childNodes.length) institution.textContent = gettext('No registrado');
        cell(person.telefono);
        cell(person.correo);
        const remove = create('button');
        remove.type = 'button';
        remove.className = 'reservation-participants__remove';
        remove.dataset.removeParticipant = String(person.id);
        remove.setAttribute('aria-label', `Quitar a ${person.nombre}`);
        remove.title = gettext('Quitar participante');
        remove.innerHTML = window.interfaz.html`<i class="fas fa-times"></i>`;
        const action = cell('');
        action.textContent = '';
        action.appendChild(remove);
        rows.appendChild(item);
      });
    }

    function renderParticipantResults(users) {
      if (!participantResults) return;
      participantResults.innerHTML = '';
      participantResults.hidden = false;
      const available = users.filter((person) => !selectedParticipants.has(Number(person.id)));
      if (!available.length) {
        participantResults.innerHTML = window.interfaz.html`<p>No se encontraron usuarios disponibles.</p>`;
        return;
      }
      available.forEach((person) => {
        const button = create('button', 'reservation-participant-result');
        button.type = 'button';
        button.dataset.participantId = String(person.id);
        button._participant = person;
        button.disabled = person.habilitado === false;
        const name = create('strong');
        name.textContent = person.nombre;
        const detail = create('small');
        detail.textContent = person.habilitado === false
          ? `${person.tipo} · perfil incompleto: ${person.faltantes.join(', ')}`
          : `${person.tipo} · ${person.facultad} · ${person.carrera} · ${person.correo}`;
        button.append(name, detail);
        participantResults.appendChild(button);
      });
    }

    participantSearch?.addEventListener('input', () => {
      clearTimeout(participantTimer);
      const query = participantSearch.value.trim();
      if (query.length < 2) {
        if (participantResults) participantResults.hidden = true;
        return;
      }
      participantTimer = setTimeout(async () => {
        try {
          const url = new URL(modal.dataset.participantSearchUrl, window.location.origin);
          url.searchParams.set('q', query);
          const response = await fetch(url, { credentials: 'same-origin' });
          const data = await response.json();
          renderParticipantResults(data.success ? data.usuarios : []);
        } catch (_error) {
          renderParticipantResults([]);
        }
      }, 250);
    });
    participantResults?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-participant-id]');
      if (!button || !button._participant) return;
      selectedParticipants.set(Number(button.dataset.participantId), button._participant);
      participantSearch.value = '';
      participantResults.hidden = true;
      syncParticipants();
    });
    participantSelected?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-remove-participant]');
      if (!button) return;
      selectedParticipants.delete(Number(button.dataset.removeParticipant));
      syncParticipants();
    });
    syncParticipants();

    function selectedPurpose() {
      return form.querySelector('[name="proposito_codigo"]:checked')?.value || '';
    }

    const purposeLabels = {
      docencia_practica: 'Docencia y práctica curricular',
      investigacion_innovacion: 'Investigación, desarrollo e innovación',
      vinculacion: 'Vinculación con la sociedad',
      capacitacion: 'Capacitación y educación continua',
      servicio_cientifico_tecnologico: 'Servicio científico-tecnológico',
      titulacion: 'Trabajo de titulación',
      otro: 'Otro propósito institucional'
    };
    const subtypeOptions = {
      // Toda actividad docente exige guia; semillero y entrenamiento tecnico
      // viven en investigacion y capacitacion (mismo mapa que el servidor).
      docencia_practica: [
        ['practica_curricular', gettext('Práctica curricular de laboratorio')],
        ['simulacion_demostracion', gettext('Clase demostrativa o simulación académica')],
        ['practica_evaluativa', gettext('Práctica evaluativa o examen práctico')],
        ['proyecto_asignatura', gettext('Proyecto integrador de asignatura')],
        ['taller_docente', gettext('Taller práctico de asignatura')]
      ],
      investigacion_innovacion: [
        ['proyecto_investigacion', gettext('Proyecto de investigación')],
        ['desarrollo_experimental', gettext('Desarrollo experimental')],
        ['innovacion_prototipado', gettext('Innovación o prototipado')],
        ['proyecto_centro', gettext('Actividad de un centro o grupo de investigación')],
        ['investigacion_formativa', gettext('Investigación formativa o semillero')]
      ],
      vinculacion: [
        ['proyecto_vinculacion', gettext('Proyecto o programa de vinculación')],
        ['transferencia_conocimiento', gettext('Transferencia de conocimiento o tecnología')]
      ],
      capacitacion: [
        ['curso', gettext('Curso de educación continua')],
        ['taller', gettext('Taller o capacitación práctica')],
        ['induccion', gettext('Inducción o actualización técnica')],
        ['entrenamiento_tecnico', gettext('Entrenamiento técnico o desarrollo de competencias')]
      ],
      servicio_cientifico_tecnologico: [
        ['servicio_autorizado', gettext('Servicio técnico o científico autorizado')]
      ],
      titulacion: [['trabajo_titulacion', gettext('Trabajo de titulación registrado')]],
      otro: [['otro', gettext('Otro subtipo')]]
    };
    const referenceLabels = {
      docencia_practica: 'Nombre corto de la actividad o guía *',
      investigacion_innovacion: 'Proyecto, semillero o iniciativa vinculada *',
      vinculacion: 'Programa o proyecto de vinculación *',
      capacitacion: 'Curso, taller o actividad de capacitación *',
      servicio_cientifico_tecnologico: 'Ensayo, servicio o asistencia vinculada *',
      titulacion: 'Trabajo de titulación registrado *',
      otro: 'Nombre de la actividad *'
    };
    const purposeContext = element('contextoActividadReserva');
    const purposeContextGrid = purposeContext?.querySelector('.reservation-purpose-context__grid');
    if (purposeContextGrid && !element('vinculacionActividadCampo')) {
      const activityLinkFallback = create(
        'fieldset',
        'reservation-activity-link reservation-context-field--wide'
      );
      activityLinkFallback.id = 'vinculacionActividadCampo';
      activityLinkFallback.innerHTML = window.interfaz.html`
        <legend>¿Necesitas vincular una actividad o guía?</legend>
        <p>Elige una reserva puntual sin guía, una actividad publicada o el registro de una actividad nueva.</p>
        <div class="reservation-activity-link__options">
          <label data-activity-link="independiente"><input type="radio" name="vinculacion_actividad" value="independiente"><span><i class="fas fa-clock"></i><b>Reserva sin guía</b><small>Podrá ser una sesión o repetirse semanalmente sin adjuntar PDF.</small></span></label>
          <label data-activity-link="catalogo"><input type="radio" name="vinculacion_actividad" value="catalogo"><span><i class="fas fa-list-alt"></i><b>Actividad ya registrada</b><small>La buscaré en el catálogo institucional.</small></span></label>
          <label data-activity-link="clonada"><input type="radio" name="vinculacion_actividad" value="clonada"><span><i class="fas fa-copy"></i><b>Clonar y adaptar</b><small>Partiré de una guía aprobada y crearé un borrador propio.</small></span></label>
          <label data-activity-link="manual"><input type="radio" name="vinculacion_actividad" value="manual"><span><i class="fas fa-file-alt"></i><b>Crear una guía nueva</b><small>Completa, revisa y confirma aquí el formato institucional.</small></span></label>
        </div>
        <div class="reservation-activity-link__notice" id="vinculacionActividadAviso"><i class="fas fa-info-circle"></i><span>Esta respuesta evita referencias inventadas y mantiene correctos los indicadores.</span></div>`;
      purposeContextGrid.insertBefore(
        activityLinkFallback,
        element('actividadCatalogoCampo') || element('referenciaActividadCampo') || null
      );
    }
    const subtypeSelect = element('subtipoActividad');
    const activityCatalog = element('actividadCatalogo');
    const activityCatalogHelp = element('actividadCatalogoAyuda');
    const activityCatalogField = element('actividadCatalogoCampo');
    const activityLinkField = element('vinculacionActividadCampo');
    const activityLinkInputs = Array.from(form.querySelectorAll('[name="vinculacion_actividad"]'));
    const activityLinkNotice = element('vinculacionActividadAviso');
    const activityCatalogPreview = element('actividadCatalogoDetalle');
    const activityReferenceField = element('referenciaActividadCampo');
    const activityReferenceInput = element('referenciaActividad');
    const activityReferenceLabel = element('referenciaActividadEtiqueta');
    const activityReferenceHelp = element('referenciaActividadAyuda');
    const referenceCodeField = element('codigoReferenciaCampo');
    const academicPeriodField = element('periodoAcademicoCampo');
    const academicPeriodInput = form.querySelector('[name="periodo_academico"]');
    const academicPeriodIdInput = form.querySelector('[name="periodo_id"]');
    const calendarVersionInput = form.querySelector('[name="version_calendario_id"]');
    const academicPeriodHelp = element('periodoAcademicoAyuda');
    let academicPeriods = [];
    try {
      academicPeriods = JSON.parse(element('periodosAcademicosReservaData')?.textContent || '[]');
    } catch (error) {
      academicPeriods = [];
    }
    const activityResponsibleField = element('responsableActividadCampo');
    const activityGuidesField = element('guiasActividadCampo');
    const activityGuidesInput = element('guiasActividadInput');
    const activityGuidePermissionsInput = element('permisosDescargaGuias');
    const activityGuidesList = element('guiasActividadLista');
    const activityGuidesAction = element('guiasActividadAccion');
    const activityGuidePreview = element('guiaActividadPreview');
    const activityGuidePreviewFrame = element('guiaActividadPreviewFrame');
    const activityGuidePreviewName = element('guiaActividadPreviewNombre');
    const activityGuidePreviewClose = element('cerrarGuiaActividadPreview');
    const activityGuideRequirement = element('guiaActividadObligatoriedad');
    const activityGuideHelp = element('guiaActividadAyuda');
    const activityCatalogGuides = element('actividadCatalogoGuias');
    let clonableGuides = [];
    try {
      clonableGuides = JSON.parse(element('guiasClonablesReservaData')?.textContent || '[]');
    } catch (error) {
      clonableGuides = [];
    }
    let clonedGuideAppliedId = '';
    const frequencyInputs = Array.from(form.querySelectorAll('[name="frecuencia_reserva"]'));
    const frequencyHelp = element('frecuenciaReservaAyuda');
    const frequencyRangeField = element('rangoFrecuenciaReserva');
    const frequencyRangeEnd = element('fechaFinRecurrencia');
    const programmingOriginField = element('origenProgramacionCampo');
    const otherPurposeField = element('detalleOtroPropositoCampo');
    const finalActivityFields = finalActivityIdentity.querySelector('[data-final-activity-fields]');
    const finalActivitySuggestionBox = finalActivityIdentity.querySelector('[data-activity-suggestion-box]');
    const finalActivitySuggestionText = finalActivityIdentity.querySelector('[data-activity-suggestion-text]');
    const finalActivitySuggestionButton = finalActivityIdentity.querySelector('[data-use-activity-suggestion]');
    const finalActivityError = finalActivityIdentity.querySelector('[data-final-activity-error]');
    appendUnique(finalActivityFields, activityReferenceField);
    const activityNamingHelper = finalActivityIdentity.querySelector('[data-activity-naming]');
    if (activityNamingHelper) finalActivityFields.appendChild(activityNamingHelper);
    appendUnique(finalActivityFields, programmingOriginField);
    const beneficiaryCareerField = element('carreraBeneficiariaCampo');
    const beneficiaryEntityField = element('entidadBeneficiariaCampo');
    const beneficiaryEntityLabel = element('entidadBeneficiariaEtiqueta');
    let activityGuideFiles = [];
    const activityGuidePermissions = new Map();

    function activityGuideKey(file) {
      return `${file.name.toLowerCase()}::${file.size}::${file.lastModified}`;
    }

    function syncActivityGuidePermissions() {
      if (!activityGuidePermissionsInput) return;
      activityGuidePermissionsInput.value = JSON.stringify(
        activityGuideFiles.map((file) => activityGuidePermissions.get(activityGuideKey(file)) === true)
      );
    }

    function closeActivityGuidePreview() {
      if (activityGuidePreview) activityGuidePreview.hidden = true;
    }

    function previewActivityGuide(file) {
      if (!file) return;
      const url = URL.createObjectURL(file);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.dataset.pdfTitulo = file.name;
      if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) {
        window.visorPdfModal?.abrir(enlace, () => URL.revokeObjectURL(url));
      } else {
        enlace.download = file.name;
        enlace.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 60000);
      }
    }

    function selectedActivityLink() {
      return form.querySelector('[name="vinculacion_actividad"]:checked')?.value || '';
    }

    function guideContentAsText(value) {
      if (Array.isArray(value)) {
        return value.map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            return item.titulo && item.url ? `${item.titulo} | ${item.url}` : Object.values(item).join(' | ');
          }
          return '';
        }).filter(Boolean).join('\n');
      }
      return value && typeof value === 'object' ? Object.values(value).join(' | ') : String(value || '');
    }

    function applyClonedGuide() {
      if (selectedActivityLink() !== 'clonada' || !activityCatalog?.value) return;
      const source = clonableGuides.find((item) => String(item.actividad_id) === String(activityCatalog.value));
      if (!source || String(source.guia_id) === clonedGuideAppliedId) return;
      const editor = ensureGuideEditor();
      if (!editor) return;
      const content = source.contenido || {};
      Object.keys(GUIDE_FIELD_TYPES).forEach((field) => {
        const raw = guideContentAsText(content[field]);
        if (!raw) return;
        const html = content.formato_contenido === 'html' && typeof content[field] === 'string'
          ? content[field]
          : window.GuiaEditor.textoAHtml(raw, GUIDE_FIELD_TYPES[field]);
        editor.establecer(field, html);
      });
      ['bibliografia', 'materiales_complementarios'].forEach((field) => {
        const input = form.querySelector(`[name="guia_${field}"]`);
        if (input) input.value = guideContentAsText(content[field]);
      });
      if (guideSubjectInput && content.asignatura) guideSubjectInput.value = guideContentAsText(content.asignatura);
      clonedGuideAppliedId = String(source.guia_id);
      syncGuideFieldsFromEditor();
      invalidateGuidePreview();
      refreshGuideAutomaticSummary();
    }

    function selectedFrequency() {
      if (state.type === 'visita') return 'unica';
      return form.querySelector('[name="frecuencia_reserva"]:checked')?.value || 'unica';
    }

    function updateFrequencyContext() {
      if (state.type === 'visita') return;
      const activityMode = selectedActivityLink();
      const weeklyInputs = frequencyInputs.filter((input) => input.value !== 'unica');
      const singleInput = frequencyInputs.find((input) => input.value === 'unica');
      const weeklyAllowed = state.type !== 'servicio' && Boolean(activityMode);
      weeklyInputs.forEach((weeklyInput) => {
        weeklyInput.disabled = !weeklyAllowed;
        weeklyInput.closest('label')?.classList.toggle('is-disabled', !weeklyAllowed);
        if (!weeklyAllowed && weeklyInput.checked && singleInput) singleInput.checked = true;
      });
      frequencyInputs.forEach((input) => {
        input.closest('label')?.classList.toggle('is-selected', input.checked);
      });
      const usesRange = selectedFrequency() === 'semanal_rango' && weeklyAllowed;
      if (frequencyRangeField) frequencyRangeField.hidden = !usesRange;
      if (frequencyRangeEnd) {
        frequencyRangeEnd.required = usesRange;
        frequencyRangeEnd.disabled = !usesRange;
        const firstDate = (element('fechaInicio')?.value || '').slice(0, 10);
        const period = academicPeriods.find((item) => (
          firstDate && item.inicio <= firstDate && firstDate <= item.fin
        ));
        if (firstDate) {
          const minimum = new Date(`${firstDate}T12:00:00`);
          minimum.setDate(minimum.getDate() + 7);
          frequencyRangeEnd.min = minimum.toISOString().slice(0, 10);
        }
        frequencyRangeEnd.max = period?.fin || '';
        if (usesRange && frequencyRangeEnd.value
          && ((frequencyRangeEnd.min && frequencyRangeEnd.value < frequencyRangeEnd.min)
            || (frequencyRangeEnd.max && frequencyRangeEnd.value > frequencyRangeEnd.max))) {
          frequencyRangeEnd.value = '';
        }
      }
      if (frequencyHelp) {
        const frequency = selectedFrequency();
        frequencyHelp.innerHTML = frequency === 'semanal_rango'
          ? window.interfaz.html`<i class="fas fa-info-circle"></i> El sistema repetirá el día y los bloques seleccionados hasta la fecha indicada. ${activityMode === 'independiente' ? gettext('Cada fecha quedará como una sesión sin guía y se validará por separado.') : gettext('Cada sesión quedará vinculada a la actividad seleccionada.')}`
          : frequency === 'semanal_periodo'
            ? window.interfaz.html`<i class="fas fa-info-circle"></i> Se creará una sesión por cada semana habilitada del período. ${activityMode === 'independiente' ? 'No se solicitará guía; cada fecha conservará su propia reserva.' : gettext('Todas quedarán vinculadas a la actividad seleccionada.')}`
            : weeklyAllowed && selectedSpaceScope() === 'unidad_completa'
              ? window.interfaz.html`<i class="fas fa-info-circle"></i> Reservaste la unidad completa: en esas horas el laboratorio queda bloqueado para otros usuarios. Para una asignatura conviene repetirla semanalmente o por todo el período.`
            : weeklyAllowed
              ? window.interfaz.html`<i class="fas fa-info-circle"></i> Selecciona el primer día y sus horas. Puedes reservar una sola sesión o repetirla semanalmente, con o sin guía.`
              : window.interfaz.html`<i class="fas fa-info-circle"></i> Selecciona abajo el día y sus horas. Los servicios técnicos se programan como una sola solicitud.`;
      }
      refreshSchedulePlan();
    }

    function renderActivityGuides() {
      if (!activityGuidesList || !activityGuidesInput) return;
      const files = activityGuideFiles;
      activityGuidesList.hidden = !files.length;
      activityGuidesList.innerHTML = '';
      if (activityGuidesAction) {
        activityGuidesAction.textContent = files.length ? gettext('Agregar más guías') : gettext('Seleccionar guías');
      }
      if (files.length) {
        const summary = create('div', 'reservation-activity-guide-upload__summary');
        const remaining = Math.max(0, 10 - files.length);
        summary.innerHTML = window.interfaz.html`<strong>${files.length} ${files.length === 1 ? gettext('guía seleccionada') : gettext('guías seleccionadas')}</strong><small>${remaining ? `Puedes agregar ${remaining} archivo${remaining === 1 ? '' : 's'} más.` : gettext('Alcanzaste el máximo de 10 archivos.')}</small>`;
        activityGuidesList.appendChild(summary);
      }
      files.forEach((file, index) => {
        const item = create('div', 'reservation-activity-guide-upload__item');
        const size = file.size >= 1024 * 1024
          ? `${(file.size / (1024 * 1024)).toFixed(1)} MB`
          : `${Math.max(1, Math.round(file.size / 1024))} KB`;
        item.innerHTML = window.interfaz.html`<i class="fas fa-file-pdf" aria-hidden="true"></i>`;
        const detail = create('span');
        const name = create('strong');
        const meta = create('small');
        name.textContent = file.name;
        meta.textContent = `${size} \u00b7 listo para guardar con la actividad`;
        detail.append(name, meta);
        const actions = create('div', 'reservation-activity-guide-upload__actions');
        const downloadPolicy = create('label', 'reservation-activity-guide-upload__policy');
        const downloadToggle = document.createElement('input');
        downloadToggle.type = 'checkbox';
        downloadToggle.checked = activityGuidePermissions.get(activityGuideKey(file)) === true;
        const downloadPolicyText = create('span');
        const renderDownloadPolicy = () => {
          const enabled = downloadToggle.checked;
          downloadPolicy.classList.toggle('is-downloadable', enabled);
          downloadPolicyText.innerHTML = enabled
            ? window.interfaz.html`<strong><i class="fas fa-download"></i> Descarga permitida</strong><small>Los usuarios autorizados podrán guardar este PDF.</small>`
            : window.interfaz.html`<strong><i class="fas fa-eye"></i> Solo visualización</strong><small>No se mostrará la opción de descarga.</small>`;
        };
        downloadToggle.addEventListener('change', () => {
          activityGuidePermissions.set(activityGuideKey(file), downloadToggle.checked);
          syncActivityGuidePermissions();
          renderDownloadPolicy();
        });
        renderDownloadPolicy();
        downloadPolicy.append(downloadToggle, downloadPolicyText);
        const preview = create('button', 'reservation-activity-guide-upload__preview', window.interfaz.html`<i class="fas fa-eye"></i><span>Vista previa</span>`);
        preview.type = 'button';
        preview.addEventListener('click', () => previewActivityGuide(file));
        const remove = create('button', 'reservation-activity-guide-upload__remove', window.interfaz.html`<i class="fas fa-trash-alt"></i><span>Eliminar</span>`);
        remove.type = 'button';
        remove.addEventListener('click', () => {
          closeActivityGuidePreview();
          activityGuidePermissions.delete(activityGuideKey(file));
          activityGuideFiles = files.filter((_entry, position) => position !== index);
          syncActivityGuideInput();
          syncActivityGuidePermissions();
          renderActivityGuides();
        });
        actions.append(downloadPolicy, preview, remove);
        item.append(detail, actions);
        activityGuidesList.appendChild(item);
      });
    }

    function syncActivityGuideInput() {
      if (!activityGuidesInput) return;
      const transfer = new DataTransfer();
      activityGuideFiles.forEach((file) => transfer.items.add(file));
      activityGuidesInput.files = transfer.files;
      syncActivityGuidePermissions();
    }

    function acceptActivityGuides(files) {
      if (!activityGuidesInput) return;
      const incoming = Array.from(files || []).filter((file) => (
        file.name.toLowerCase().endsWith('.pdf')
        && file.size <= 20 * 1024 * 1024
      ));
      const known = new Set(activityGuideFiles.map((file) => (
        `${file.name.toLowerCase()}::${file.size}::${file.lastModified}`
      )));
      const added = [];
      incoming.forEach((file) => {
        const key = activityGuideKey(file);
        if (known.has(key) || activityGuideFiles.length + added.length >= 10) return;
        known.add(key);
        activityGuidePermissions.set(key, false);
        added.push(file);
      });
      activityGuideFiles = [...activityGuideFiles, ...added];
      syncActivityGuideInput();
      renderActivityGuides();
      if (added.length) {
        previewActivityGuide(added[0]);
      } else if (!activityGuideFiles.length) {
        closeActivityGuidePreview();
      }
    }

    function selectedPurposeLabel() {
      const code = selectedPurpose();
      return purposeLabels[code] || 'propósito por seleccionar';
    }

    function updateBeneficiaryContext() {
      const scope = form.querySelector('[name="alcance_beneficiario"]:checked')?.value || '';
      beneficiaryCareerField.hidden = scope !== 'otra_carrera';
      beneficiaryEntityField.hidden = !['dependencia_upec', 'proyecto_centro', 'externo'].includes(scope);
      const labels = {
        dependencia_upec: 'Dependencia UPEC beneficiaria *',
        proyecto_centro: 'Proyecto, grupo o centro beneficiario *',
        externo: 'Institución o comunidad externa beneficiaria *'
      };
      if (beneficiaryEntityLabel) beneficiaryEntityLabel.textContent = labels[scope] || 'Entidad beneficiaria *';
      form.querySelectorAll('[name="alcance_beneficiario"]').forEach((input) => {
        input.closest('label')?.classList.toggle('is-selected', input.checked);
      });
    }

    function setAcademicPeriod(period, { catalogLinked = false } = {}) {
      if (!academicPeriodInput) return;
      academicPeriodInput.value = period?.codigo || '';
      academicPeriodInput.readOnly = true;
      academicPeriodInput.dataset.catalogLinked = catalogLinked ? 'true' : 'false';
      if (academicPeriodIdInput) academicPeriodIdInput.value = period?.id || '';
      if (calendarVersionInput) calendarVersionInput.value = period?.version_id || '';
      if (academicPeriodHelp) {
        academicPeriodHelp.textContent = period
          ? `${period.nombre || period.codigo} · ${period.semanas || 16} semanas planificadas.`
          : gettext('El sistema lo identificará al elegir una fecha del calendario institucional.');
      }
      academicPeriodField?.classList.toggle('is-resolved', Boolean(period));
    }

    function syncAcademicPeriod(dateValue = '') {
      const option = activityCatalog?.selectedOptions?.[0];
      const catalogCode = option?.dataset.period || '';
      if (option?.value && catalogCode) {
        const linkedPeriod = academicPeriods.find((item) => (
          String(item.id) === String(option.dataset.periodId || '')
          || item.codigo === catalogCode
        ));
        setAcademicPeriod(linkedPeriod || { codigo: catalogCode, id: option.dataset.periodId }, { catalogLinked: true });
        return;
      }
      const selectedDate = (dateValue || element('fechaInicio')?.value || '').slice(0, 10);
      const matchingPeriod = academicPeriods.find((item) => (
        selectedDate && item.inicio <= selectedDate && selectedDate <= item.fin
      ));
      setAcademicPeriod(matchingPeriod || null);
    }

    function updateCatalogActivity() {
      const option = activityCatalog?.selectedOptions?.[0];
      const activityMode = selectedActivityLink();
      const cloning = activityMode === 'clonada';
      const linked = ['catalogo', 'clonada'].includes(activityMode) && Boolean(option?.value);
      const fields = [
        [activityReferenceInput, 'name'],
        [form.querySelector('[name="codigo_referencia_actividad"]'), 'code'],
        [form.querySelector('[name="periodo_academico"]'), 'period'],
        [form.querySelector('[name="responsable_actividad"]'), 'responsible']
      ];
      fields.forEach(([input, key]) => {
        if (!input) return;
        if (input === academicPeriodInput) return;
        if (linked) {
          if (input === activityReferenceInput && cloning) {
            if (input.dataset.cloneSource !== option.value) {
              input.value = `${option.dataset.name || 'Guía institucional'} adaptada`.slice(0, 120);
              input.dataset.cloneSource = option.value;
              delete input.dataset.userEdited;
            }
            input.readOnly = false;
          } else {
            input.value = option.dataset[key] || '';
            input.readOnly = true;
          }
          input.dataset.catalogLinked = 'true';
        } else {
          if (input.dataset.catalogLinked === 'true') input.value = '';
          input.readOnly = false;
          delete input.dataset.catalogLinked;
        }
      });
      if (linked && subtypeSelect && option.dataset.subtype) {
        subtypeSelect.value = option.dataset.subtype;
      }
      if (activityCatalogPreview) {
        activityCatalogPreview.hidden = !linked;
        const previewValues = {
          actividadCatalogoNombre: option?.dataset.name || '',
          actividadCatalogoTipo: option?.dataset.subtypeLabel || 'Por definir',
          actividadCatalogoCodigo: option?.dataset.code || 'Sin código',
          actividadCatalogoPeriodo: option?.dataset.period || 'Según fecha de la reserva',
          actividadCatalogoResponsable: option?.dataset.responsible || 'Por asignar',
          actividadCatalogoUnidad: option?.dataset.career || option?.dataset.faculty || 'Referencia institucional'
        };
        Object.entries(previewValues).forEach(([id, value]) => {
          const node = element(id);
          if (node) node.textContent = value;
        });
      }
      activityCatalogGuides?.querySelectorAll('[data-activity-guides]').forEach((group) => {
        group.hidden = !linked || group.dataset.activityGuides !== option?.value;
      });
      syncAcademicPeriod();
      purposeContext?.classList.toggle('has-catalog-activity', linked);
      if (cloning && linked) applyClonedGuide();
      updateFrequencyContext();
    }

    function prioritizePublishedGuides() {
      if (!activityCatalog) return;
      const selectedValue = activityCatalog.value;
      const family = processSelect?.selectedOptions?.[0]?.dataset.family || '';
      const subject = (guideSubjectInput?.value || '').trim().toLocaleLowerCase('es');
      const placeholder = activityCatalog.options[0];
      const options = Array.from(activityCatalog.options).slice(1);
      options.forEach((option, index) => {
        if (!option.dataset.originalOrder) option.dataset.originalOrder = String(index);
      });
      options.sort((left, right) => {
        const score = (option) => {
          let value = 0;
          if (family && option.dataset.family === family) value += 4;
          const optionSubject = (option.dataset.subject || '').toLocaleLowerCase('es');
          if (subject && optionSubject && (optionSubject.includes(subject) || subject.includes(optionSubject))) value += 2;
          return value;
        };
        return score(right) - score(left)
          || Number(left.dataset.originalOrder) - Number(right.dataset.originalOrder);
      });
      activityCatalog.replaceChildren(placeholder, ...options);
      activityCatalog.value = selectedValue;
    }

    function suggestedActivityName() {
      // Enfoque tecnico o metodologico: [tecnica o equipo] aplicada a [caso o asignatura].
      const selectedEquipment = Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
        .map((input) => input.dataset.equipoNombre
          || form.querySelector(`[data-equipment-unit="${input.value}"]`)?.dataset.equipmentName
          || '')
        .find(Boolean);
      const selectedSoftware = softwareInputs.filter((input) => input.checked)
        .map((input) => input.closest('.reservation-software-item')
          ?.querySelector('.reservation-software-item__content > strong')?.textContent?.trim())
        .find(Boolean);
      const subtypeLabel = subtypeSelect?.selectedOptions?.[0]?.textContent?.trim();
      const genericSubtype = !subtypeLabel || subtypeSelect?.selectedIndex === 0
        ? ''
        : subtypeLabel.replace(/\s+de laboratorio$/i, '');
      const focus = guideSubjectInput?.value.trim() || genericSubtype || 'la asignatura';
      const technique = selectedEquipment && selectedSoftware
        ? `${selectedEquipment} con ${selectedSoftware}`
        : (selectedEquipment || selectedSoftware);
      const raw = technique ? `Uso de ${technique} aplicado a ${focus}` : `Práctica de ${focus}`;
      if (raw.length <= 120) return raw;
      return raw.slice(0, 120).replace(/\s+\S*$/, '').trim();
    }

    function refreshFinalActivityIdentity({ autofill = false } = {}) {
      const purpose = selectedPurpose();
      const mode = selectedActivityLink();
      const directTeachingFlow = purpose === 'docencia_practica' && state.type !== 'servicio';
      const active = directTeachingFlow && Boolean(mode) && mode !== 'independiente';
      const manual = active && ['manual', 'clonada'].includes(mode);
      const heading = finalActivityIdentity.querySelector('.reservation-final-activity__header h3');
      const copy = finalActivityIdentity.querySelector('.reservation-final-activity__header p');
      finalActivityIdentity.hidden = !active;
      if (finalActivitySuggestionBox) finalActivitySuggestionBox.hidden = !manual;
      const subjectField = finalActivityIdentity.querySelector('[data-final-subject-field]');
      if (subjectField) subjectField.hidden = !manual;
      if (guideSubjectInput) {
        guideSubjectInput.disabled = !manual;
        guideSubjectInput.required = manual;
      }
      if (finalActivityError) finalActivityError.hidden = true;
      if (heading) heading.textContent = manual
        ? gettext('Confirma el nombre de la actividad')
        : gettext('Confirma la planificación de la guía vinculada');
      if (copy) copy.textContent = manual
        ? gettext('El sistema propone un nombre después de conocer el tipo de práctica y los recursos elegidos. Puedes corregirlo antes de generar la guía.')
        : 'La guía aprobada conserva su identificación institucional; solo indica si esta práctica estaba prevista en la planificación de la asignatura.';
      if (!manual) return;

      const suggestion = suggestedActivityName();
      if (finalActivitySuggestionText) finalActivitySuggestionText.textContent = suggestion;
      if (finalActivitySuggestionButton) finalActivitySuggestionButton.dataset.suggestion = suggestion;
      if (autofill && activityReferenceInput && !activityReferenceInput.value.trim()
        && activityReferenceInput.dataset.userEdited !== 'true') {
        activityReferenceInput.value = suggestion;
        activityReferenceInput.dataset.autoSuggested = 'true';
        updateAutomaticTitle();
      }
    }

    function updateActivityLinkContext({ reset = false } = {}) {
      const purpose = selectedPurpose();
      const needsReference = Object.prototype.hasOwnProperty.call(referenceLabels, purpose);
      if (reset) activityLinkInputs.forEach((input) => { input.checked = false; });

      const directTeachingFlow = (
        purpose === 'docencia_practica' && state.type !== 'servicio'
      );
      // Cualquier subtipo docente elegido exige guia; la pregunta aparece al elegirlo.
      const curricularPractice = directTeachingFlow && Boolean(subtypeSelect?.value);

      const independentInput = activityLinkInputs.find((input) => input.value === 'independiente');
      const catalogInput = activityLinkInputs.find((input) => input.value === 'catalogo');
      const cloneInput = activityLinkInputs.find((input) => input.value === 'clonada');
      const manualInput = activityLinkInputs.find((input) => input.value === 'manual');
      const independentAllowed = Boolean(purpose) && !curricularPractice;
      if (independentInput) {
        independentInput.disabled = !independentAllowed;
        independentInput.closest('label')?.classList.toggle('is-disabled', !independentAllowed);
        independentInput.closest('label')?.toggleAttribute('hidden', curricularPractice);
        if (!independentAllowed && independentInput.checked) independentInput.checked = false;
        if (independentAllowed && !directTeachingFlow) {
          activityLinkInputs.forEach((input) => {
            input.checked = input === independentInput;
          });
        }
      }
      if (catalogInput) {
        catalogInput.disabled = !directTeachingFlow;
        catalogInput.closest('label')?.classList.toggle('is-disabled', !directTeachingFlow);
      }
      if (manualInput) {
        const manualAllowed = directTeachingFlow && canAuthorGuides;
        manualInput.disabled = !manualAllowed;
        manualInput.closest('label')?.classList.toggle('is-disabled', !manualAllowed);
        manualInput.closest('label')?.classList.toggle('is-recommended', curricularPractice && manualAllowed);
        manualInput.closest('label')?.toggleAttribute('hidden', directTeachingFlow && !canAuthorGuides);
        if (!manualAllowed && manualInput.checked) manualInput.checked = false;
      }
      const hasApprovedGuide = Array.from(activityCatalog?.options || []).some((option, index) => (
        index > 0
        && option.dataset.purpose === purpose
        && option.dataset.hasGuides === 'true'
      ));
      if (catalogInput) {
        // Siempre visible: sin guias aprobadas queda deshabilitada y lo explica.
        catalogInput.disabled = !directTeachingFlow || !hasApprovedGuide;
        catalogInput.closest('label')?.classList.toggle('is-disabled', catalogInput.disabled);
        if (catalogInput.disabled && catalogInput.checked) catalogInput.checked = false;
      }
      if (cloneInput) {
        const cloneAllowed = directTeachingFlow && canAuthorGuides && hasApprovedGuide;
        cloneInput.disabled = !cloneAllowed;
        cloneInput.closest('label')?.classList.toggle('is-disabled', !cloneAllowed);
        cloneInput.closest('label')?.toggleAttribute('hidden', directTeachingFlow && !canAuthorGuides);
        if (!cloneAllowed && cloneInput.checked) cloneInput.checked = false;
      }
      if (reset && directTeachingFlow) {
        const preferred = curricularPractice
          ? (hasApprovedGuide ? catalogInput : (canAuthorGuides ? manualInput : null))
          : independentInput;
        if (preferred && !preferred.disabled) preferred.checked = true;
      }

      // Solo se muestra en practica curricular; el resto de docencia decide al
      // final con el interruptor "Generar guia".
      const activityLinkCopy = {
        legend: 'La actividad docente requiere guía. ¿Ya existe una aprobada?',
        description: canAuthorGuides
          ? gettext('Si ya existe una guía aprobada para esta práctica, vincúlala. Si no, se creará con los datos de esta reserva y la revisarás al final.')
          : gettext('Como estudiante solo puedes vincular una guía institucional ya aprobada por un docente. No puedes crear ni modificar guías.'),
        catalogo: [gettext('Sí, vincular una guía aprobada'), hasApprovedGuide
          ? 'Selecciona una versión institucional vigente; no se copia y no puede modificarse desde esta reserva.'
          : 'Aún no hay guías aprobadas para docencia en esta unidad; crea la guía con esta reserva.'],
        clonada: [gettext('Clonar y adaptar una aprobada'), gettext('Copia su contenido en un borrador propio para ajustarlo sin alterar la versión institucional.')],
        manual: [gettext('Crear desde cero'), 'Horario, equipos, software e insumos se copian solos; al final revisas el contenido académico ya propuesto.']
      };
      const activityLinkLegend = activityLinkField?.querySelector('legend');
      const activityLinkDescription = activityLinkField?.querySelector(':scope > p');
      if (activityLinkLegend) activityLinkLegend.textContent = activityLinkCopy.legend;
      if (activityLinkDescription) activityLinkDescription.textContent = activityLinkCopy.description;
      Object.entries(activityLinkCopy).forEach(([modeName, copy]) => {
        if (!Array.isArray(copy)) return;
        const option = activityLinkField?.querySelector(`[data-activity-link="${modeName}"]`);
        const title = option?.querySelector('b');
        const help = option?.querySelector('small');
        if (title) title.textContent = copy[0];
        if (help) help.textContent = copy[1];
      });

      const mode = selectedActivityLink();
      // Solo la practica curricular decide aqui (vincular una guia aprobada o
      // crearla con esta reserva). El resto de docencia elige al final si quiere
      // generar la guia; los demas propositos solo reciben el reporte de reserva.
      if (activityLinkField) activityLinkField.hidden = !(directTeachingFlow && curricularPractice);
      activityLinkInputs.forEach((input) => {
        input.closest('label')?.classList.toggle('is-selected', input.checked);
      });

      const usesCatalog = directTeachingFlow && needsReference && ['catalogo', 'clonada'].includes(mode);
      const usesManualReference = directTeachingFlow && needsReference && ['manual', 'clonada'].includes(mode);
      if (activityCatalog) {
        Array.from(activityCatalog.options).forEach((option, index) => {
          if (!index) return;
          const visible = option.dataset.purpose === purpose
            && (!curricularPractice || option.dataset.hasGuides === 'true');
          option.hidden = !visible;
          option.disabled = !visible || !usesCatalog;
        });
        const selected = activityCatalog.selectedOptions?.[0];
        if (selected?.value && (selected.hidden || selected.dataset.purpose !== purpose)) {
          activityCatalog.value = '';
        }
      }
      activityCatalogField.hidden = !usesCatalog;
      const catalogLabel = activityCatalogField?.querySelector(':scope > span');
      if (catalogLabel) catalogLabel.textContent = curricularPractice
        ? (mode === 'clonada' ? gettext('Selecciona la guía que vas a clonar *') : gettext('Selecciona la guía institucional aprobada *'))
        : gettext('Selecciona una actividad publicada *');
      if (activityCatalogHelp && usesCatalog && curricularPractice) {
        activityCatalogHelp.textContent = mode === 'clonada'
          ? gettext('El contenido aprobado se copiará a un borrador nuevo que podrás adaptar en el paso 4.')
          : gettext('Solo aparecen actividades con una guía aprobada y vigente. La versión se vincula sin crear una copia editable.');
      }
      activityReferenceField.hidden = !usesManualReference;
      if (referenceCodeField) referenceCodeField.hidden = !usesManualReference;
      if (activityResponsibleField) activityResponsibleField.hidden = !usesManualReference;
      const usesTeachingGuides = false;
      if (activityGuidesField) activityGuidesField.hidden = true;
      if (activityGuidesInput) activityGuidesInput.disabled = true;
      if (!usesTeachingGuides && activityGuideFiles.length) {
        closeActivityGuidePreview();
        activityGuideFiles = [];
        activityGuidePermissions.clear();
        syncActivityGuideInput();
        renderActivityGuides();
      }
      if (activityCatalogGuides) activityCatalogGuides.hidden = !directTeachingFlow || !usesCatalog;
      if (activityGuideRequirement) {
        activityGuideRequirement.textContent = gettext('(opcional)');
      }
      if (activityGuideHelp) {
        activityGuideHelp.textContent = directTeachingFlow && usesManualReference
          ? gettext('El sistema creará una guía estructurada editable. Adjunta un PDF solo si deseas conservar un documento previo como respaldo.')
          : gettext('Puedes adjuntar una o varias guías y definir para cada una si sus participantes podrán descargarla o solo visualizarla.');
      }
      if (activityCatalog) {
        activityCatalog.disabled = !usesCatalog;
        if (!usesCatalog && activityCatalog.value) activityCatalog.value = '';
      }
      [activityReferenceInput,
        form.querySelector('[name="codigo_referencia_actividad"]'),
        form.querySelector('[name="responsable_actividad"]')
      ].forEach((input) => {
        if (!input) return;
        input.disabled = !usesManualReference && !usesCatalog;
        if (!usesManualReference && !usesCatalog && input.dataset.catalogLinked !== 'true') {
          input.value = '';
        }
      });

      programmingOriginField.hidden = !(
        purpose === 'docencia_practica' && mode && mode !== 'independiente'
      );
      if (purpose === 'docencia_practica' && mode === 'independiente') {
        form.querySelectorAll('[name="origen_programacion"]').forEach((input) => {
          input.checked = false;
        });
      }
      if (activityLinkNotice) {
        activityLinkNotice.querySelector('span').textContent = curricularPractice && !canAuthorGuides && mode !== 'catalogo'
          ? gettext('Solicita al docente responsable que publique o asigne la guía antes de reservar esta práctica curricular.')
          : mode === 'independiente'
          ? 'No se creará ningún documento de guía. Podrás elegir una sola sesión, un rango semanal o todo el período; cada fecha se validará por separado.'
          : directTeachingFlow
            ? (mode === 'manual'
              ? gettext('Ahora solo declara que la actividad lleva guía. La completarás en el paso 4, con horario, equipos, software e insumos ya incorporados automáticamente.')
              : mode === 'clonada'
                ? gettext('La guía aprobada se copiará en un borrador propio. Revisa y adapta el contenido en el paso 4.')
              : gettext('La guía aprobada seleccionada quedará vinculada sin crear una copia editable. Podrás verla completa en HTML antes de enviar.'))
            : gettext('Este propósito no requiere guías. La referencia seleccionada se usará solamente para trazabilidad e indicadores.');
      }
      updateCatalogActivity();
      updateFrequencyContext();
      refreshFinalActivityIdentity({ autofill: state.step >= 4 });
      updateGuideBuilder();
    }

    form.addEventListener('reservation:date-changed', (event) => {
      if (state.type === 'visita') { visitFlow.updateSummary(); return; }
      if (guidePreviewSignature) invalidateGuidePreview();
      syncAcademicPeriod(event.detail?.date || '');
      updateFrequencyContext();
      renderResourceCost(syncConsumables());
    });

    function updatePurposeContext({ reset = false } = {}) {
      const purpose = selectedPurpose();
      if (!purposeContext || !subtypeSelect) return;
      purposeContext.hidden = !purpose;
      if (!purpose) return;

      const previousSubtype = reset ? '' : subtypeSelect.value;
      const options = subtypeOptions[purpose] || [];
      subtypeSelect.innerHTML = window.interfaz.html`<option value="">Selecciona una opción</option>`
        + options.map(([value, label]) => window.interfaz.html`<option value="${value}">${label}</option>`).join('');
      if (options.some(([value]) => value === previousSubtype)) subtypeSelect.value = previousSubtype;
      if (options.length === 1) subtypeSelect.value = options[0][0];
      placeIntentField();

      if (activityCatalog) {
        Array.from(activityCatalog.options).forEach((option, index) => {
          if (!index) return;
          const visible = option.dataset.purpose === purpose;
          option.hidden = !visible;
          option.disabled = !visible;
        });
        if (reset || activityCatalog.selectedOptions[0]?.dataset.purpose !== purpose) {
          activityCatalog.value = '';
        }
      }

      const needsReference = Object.prototype.hasOwnProperty.call(referenceLabels, purpose);
      academicPeriodField.hidden = false;
      otherPurposeField.hidden = purpose !== 'otro';
      if (activityReferenceLabel) {
        activityReferenceLabel.textContent = referenceLabels[purpose] || 'Referencia de la actividad';
      }
      if (activityReferenceInput) {
        activityReferenceInput.maxLength = purpose === 'docencia_practica' ? 120 : 140;
      }
      if (activityReferenceHelp) {
        activityReferenceHelp.textContent = purpose === 'docencia_practica'
          ? gettext('Hasta 120 caracteres. Será el nombre visible en Recursos y prácticas.')
          : gettext('Escribe el nombre oficial con el que se identificará la actividad.');
      }
      updateActivityLinkContext({ reset: reset || !needsReference });
      updateBeneficiaryContext();
      syncProcessField();
    }

    function selectedRequestedResourceName() {
      const names = [];
      if (resourceKindActive('espacio')) {
        const selectedSpaces = spaceInputs.filter((input) => input.checked)
          .map((input) => input.closest('.reservation-space-item')?.querySelector('.reservation-space-item__content strong')?.textContent?.trim())
          .filter(Boolean);
        names.push(selectedSpaceScope() === 'unidad_completa'
          ? `unidad completa · ${modal.querySelector('#modalTitle')?.textContent?.trim() || 'laboratorio'}`
          : selectedSpaces.length
          ? selectedSpaces.join(', ')
          : `espacio de ${modal.querySelector('#modalTitle')?.textContent?.trim() || 'la unidad'}`);
      }
      if (resourceKindActive('equipo')) {
        const equipment = Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
          .map((input) => input.dataset.equipoNombre || input.value)
          .filter(Boolean);
        names.push(equipment.length ? equipment.join(', ') : gettext('equipos por seleccionar'));
      }
      if (resourceKindActive('software')) {
        const software = softwareInputs.filter((input) => input.checked)
          .map((input) => input.closest('.reservation-software-item')?.querySelector('strong')?.textContent)
          .filter(Boolean);
        names.push(software.length ? software.join(', ') : gettext('software por seleccionar'));
      }
      return names.join(' + ') || 'recursos por seleccionar';
    }

    function selectedResourceName() {
      if (state.type === 'servicio') {
        const names = selectedServiceInputs()
          .map((input) => input.closest('.reservation-service')?.querySelector('strong')?.textContent)
          .filter(Boolean);
        return names.length === 1 ? names[0] : names.length ? names.join(', ') : gettext('servicio por seleccionar');
      }
      return selectedRequestedResourceName();
    }

    function updateAutomaticTitle() {
      const purpose = selectedPurposeLabel();
      const resourceName = selectedResourceName();
      const modeLabels = {
        modelo_listo: 'modelo listo para revisión y ejecución',
        diseno_asistido: 'diseño asistido en el laboratorio',
        diseno_completo: 'diseño completo a cargo del laboratorio'
      };
      const mode = selectedServiceMode();
      const title = state.type === 'servicio'
        ? `Solicitud de servicio: ${resourceName} · ${modeLabels[mode] || 'modalidad por seleccionar'} · ${purpose}`
        : `Solicitud de recursos: ${resourceName} · ${purpose}`;
      const description = state.type === 'servicio'
        ? `${title}. Modalidad: ${modeLabels[mode] || 'por seleccionar'}.${isAssistedService() && Object.values(state.resources).some(Boolean) ? ` Recursos complementarios: ${selectedRequestedResourceName()}.` : ''}`
        : `${title}. La persona solicitante utilizará los recursos seleccionados en la fecha y horario reservados.`;
      if (element('tituloSolicitud')) element('tituloSolicitud').value = title;
      if (element('tituloSolicitudVista')) element('tituloSolicitudVista').textContent = title;
      if (descriptionInput) descriptionInput.value = description;
    }

    let quoteTimer = null;
    function quoteReady() {
      return state.type === 'servicio' && selectedServiceInputs().length > 0 && Boolean(selectedServiceMode());
    }
    // Cada cambio recalcula el valor sin pedirlo: la persona ve cuanto cuesta
    // mientras elige piezas y materiales.
    function scheduleServiceQuote() {
      window.clearTimeout(quoteTimer);
      if (!quoteReady()) return;
      quoteTimer = window.setTimeout(() => { calculateServiceQuote(); }, 350);
    }
    function invalidateQuote() {
      currentQuote = null;
      if (quoteAcceptance) quoteAcceptance.checked = false;
      if (paymentMethod) paymentMethod.value = '';
      if (quotePayment) quotePayment.hidden = true;
      if (quoteResult) quoteResult.innerHTML = quoteReady()
        ? window.interfaz.html`<p>Actualizando el valor estimado…</p>`
        : window.interfaz.html`<p>Elige el servicio y la modalidad para ver el valor estimado.</p>`;
      if (quoteRecap) quoteRecap.innerHTML = window.interfaz.html`<p>El valor estimado se calcula en el paso anterior, junto a los materiales del trabajo.</p>`;
      scheduleServiceQuote();
    }

    // ------------------------------------------------------------------
    // Trabajo del servicio: piezas, equipo y materiales elegidos; propuesta
    // de fecha segun la cola de la unidad.
    // ------------------------------------------------------------------
    function selectedPieces() {
      const value = Number.parseInt(piecesInput?.value || '1', 10);
      return Number.isInteger(value) && value > 0 ? value : 1;
    }

    function selectedUrgency() {
      return urgencyInputs.find((input) => input.checked)?.value || 'normal';
    }

    function materialRows() {
      return Array.from(serviceMaterialsList?.querySelectorAll('.reservation-service-material') || []);
    }

    // Cantidad escrita por pieza y su total para el trabajo completo.
    function materialUnitQuantity(row) {
      const valor = Number((row.querySelector('.reservation-service-material__input')?.value || '').trim());
      return Number.isFinite(valor) && valor > 0 ? valor : null;
    }

    function materialTotalQuantity(row) {
      const unidad = materialUnitQuantity(row);
      return unidad === null ? null : Math.round(unidad * selectedPieces() * 1000) / 1000;
    }

    function syncUrgencyLabels() {
      urgencyInputs.forEach((input) => input.closest('[data-service-urgency]')?.classList.toggle('is-selected', input.checked));
    }

    function renderServiceWork() {
      if (!serviceMaterialsList) return;
      const selected = selectedServiceInputs();
      const previous = new Map(materialRows().map((row) => [row.dataset.materialId, row]));
      const seen = new Set();
      const equipment = new Map();
      const exclusive = new Set();
      serviceMaterialsList.innerHTML = '';
      selected.forEach((input) => {
        const template = input.closest('.reservation-service')?.querySelector('[data-service-material-template]');
        if (!template) return;
        Array.from(template.content.querySelectorAll('.reservation-service-material')).forEach((node) => {
          const id = node.dataset.materialId;
          if (seen.has(id)) return;
          seen.add(id);
          const row = previous.get(id) || node.cloneNode(true);
          serviceMaterialsList.appendChild(row);
          const names = (row.dataset.equipmentNames || '').split(' / ');
          const ids = (row.dataset.equipmentIds || '').split(',').filter(Boolean);
          if (ids.length === 1) exclusive.add(ids[0]);
          ids.forEach((equipmentId, index) => {
            if (!equipment.has(equipmentId)) equipment.set(equipmentId, { name: names[index] || `Equipo ${equipmentId}`, count: 0 });
            equipment.get(equipmentId).count += 1;
          });
        });
      });
      // Opciones de fabricacion: equipos con algun material propio (exclusivo).
      // Los que solo comparten insumos genericos (cinta, lija) no son opcion.
      if (exclusive.size) {
        Array.from(equipment.keys()).forEach((equipmentId) => {
          if (!exclusive.has(equipmentId)) equipment.delete(equipmentId);
        });
      }
      renderServiceEquipmentOptions(equipment);
      if (serviceMaterialsEmpty) {
        serviceMaterialsEmpty.hidden = seen.size > 0;
        serviceMaterialsEmpty.textContent = selected.length
          ? 'Este servicio no tiene materiales vinculados; el laboratorio los definirá en la revisión técnica.'
          : gettext('Selecciona un servicio para ver sus materiales.');
      }
      filterMaterialsByEquipment();
    }

    function renderServiceEquipmentOptions(equipment) {
      if (!serviceEquipmentOptions || !serviceEquipmentBox || !serviceEquipmentInput) return;
      const current = serviceEquipmentInput.value || '';
      const entries = Array.from(equipment.entries());
      if (entries.length === 1) serviceEquipmentInput.value = entries[0][0];
      else if (!entries.some(([id]) => id === current)) serviceEquipmentInput.value = '';
      serviceEquipmentOptions.innerHTML = entries.map(([id, item]) => window.interfaz.html`<label data-service-equipment-option="${escapeHtml(id)}"${serviceEquipmentInput.value === id ? ' class="is-selected"' : ''}><input type="radio" name="equipo_servicio_opcion" value="${escapeHtml(id)}"${serviceEquipmentInput.value === id ? ' checked' : ''}><span><i class="fas fa-cogs" aria-hidden="true"></i><strong>${escapeHtml(item.name)}</strong><small>${item.count} material${item.count === 1 ? '' : 'es'} compatible${item.count === 1 ? '' : 's'}</small></span></label>`).join('');
      serviceEquipmentBox.hidden = entries.length < 2;
    }

    function filterMaterialsByEquipment() {
      const chosen = serviceEquipmentInput?.value || '';
      materialRows().forEach((row) => {
        const ids = (row.dataset.equipmentIds || '').split(',').filter(Boolean);
        const compatible = !chosen || !ids.length || ids.includes(chosen);
        row.hidden = !compatible;
        if (!compatible) {
          const check = row.querySelector('.reservation-service-material__check');
          if (check && !check.disabled) check.checked = false;
        }
      });
      refreshMaterialQuantities();
      syncServiceMaterials();
    }

    // El total lo calcula el sistema con las piezas; la persona solo escribe
    // cuanto usa cada pieza, para que el valor no aparezca sin haberlo indicado.
    function refreshMaterialQuantities() {
      const pieces = selectedPieces();
      materialRows().forEach((row) => {
        const input = row.querySelector('.reservation-service-material__input');
        const check = row.querySelector('.reservation-service-material__check');
        const salida = row.querySelector('[data-quantity-total]');
        if (!input) return;
        input.disabled = !check?.checked;
        const total = materialTotalQuantity(row);
        if (salida) {
          salida.textContent = total === null
            ? gettext('Total: escribe la cantidad')
            : pieces > 1
              ? `Total: ${materialUnitQuantity(row)} ${row.dataset.unit || ''} × ${contarTrabajo(pieces)} = ${total} ${row.dataset.unit || ''}`
              : `Total: ${total} ${row.dataset.unit || ''}`;
        }
        checkServiceMaterialStock(row);
      });
    }

    function checkServiceMaterialStock(row) {
      const input = row.querySelector('.reservation-service-material__input');
      const note = row.querySelector('[data-material-note]');
      const check = row.querySelector('.reservation-service-material__check');
      const stock = Number(row.dataset.stock || 0);
      const value = materialTotalQuantity(row) || 0;
      const over = Boolean(check?.checked) && !row.hidden && value > stock;
      row.classList.toggle('is-over-stock', over);
      if (note) {
        note.hidden = !over;
        note.textContent = over
          ? `Solo hay ${row.dataset.stock} ${row.dataset.unit || 'unidades'} disponibles y el trabajo consumiría ${value}. Reduce la cantidad por ${palabraTrabajo()} o el número de ${palabraTrabajo(true)}.`
          : '';
      }
      input?.setCustomValidity(over ? gettext('La cantidad supera la existencia disponible.') : '');
      return !over;
    }

    function serviceMaterialsWithinStock() {
      return materialRows().every((row) => checkServiceMaterialStock(row));
    }
    // Primer material marcado sin cantidad: la cantidad se pide siempre.
    function serviceMaterialWithoutQuantity() {
      return materialRows().find((row) => (
        row.querySelector('.reservation-service-material__check')?.checked
        && !row.hidden
        && !(row.querySelector('.reservation-service-material__input')?.value || '').trim()
      )) || null;
    }

    function syncServiceMaterials() {
      const selectedIds = [];
      const quantities = {};
      materialRows().forEach((row) => {
        const check = row.querySelector('.reservation-service-material__check');
        const input = row.querySelector('.reservation-service-material__input');
        const active = Boolean(check?.checked) && !row.hidden;
        row.classList.toggle('is-selected', active);
        if (!active) return;
        selectedIds.push(Number(row.dataset.materialId));
        // Al servidor va el consumo del trabajo completo, no el de una pieza.
        const total = materialTotalQuantity(row);
        if (total !== null) quantities[row.dataset.materialId] = String(total);
      });
      if (serviceMaterialsInput) serviceMaterialsInput.value = JSON.stringify(selectedIds);
      serviceConsumablesInput.value = JSON.stringify(quantities);
      Object.keys(serviceQuantities).forEach((key) => delete serviceQuantities[key]);
      Object.assign(serviceQuantities, quantities);
      return { selectedIds, quantities };
    }

    function selectedMaterialsSummary() {
      return materialRows()
        .filter((row) => row.querySelector('.reservation-service-material__check')?.checked && !row.hidden)
        .map((row) => {
          const total = materialTotalQuantity(row);
          return `${row.dataset.name}: ${total === null ? gettext('cantidad por calcular') : `${total} ${row.dataset.unit || ''}`}`;
        })
        .join(' · ');
    }

    serviceMaterialsList?.addEventListener('change', (event) => {
      const row = event.target.closest?.('.reservation-service-material');
      if (!row) return;
      if (event.target.classList.contains('reservation-service-material__check')) {
        refreshMaterialQuantities();
      }
      syncServiceMaterials();
      invalidateQuote();
    });
    serviceMaterialsList?.addEventListener('input', (event) => {
      const row = event.target.closest?.('.reservation-service-material');
      if (!row || !event.target.classList.contains('reservation-service-material__input')) return;
      refreshMaterialQuantities();
      syncServiceMaterials();
      invalidateQuote();
    });
    serviceEquipmentOptions?.addEventListener('change', (event) => {
      const input = event.target.closest?.('input[type="radio"]');
      if (!input || !serviceEquipmentInput) return;
      serviceEquipmentInput.value = input.value;
      serviceEquipmentOptions.querySelectorAll('[data-service-equipment-option]').forEach((label) => {
        label.classList.toggle('is-selected', label.querySelector('input')?.checked);
      });
      filterMaterialsByEquipment();
      invalidateQuote();
    });
    piecesInput?.addEventListener('input', () => {
      refreshMaterialQuantities();
      syncServiceMaterials();
      invalidateQuote();
      invalidateProposal();
    });
    urgencyInputs.forEach((input) => input.addEventListener('change', () => {
      syncUrgencyLabels();
      invalidateQuote();
      invalidateProposal();
      if (selectedServiceInputs().length && selectedServiceMode()) requestDeliveryProposal();
    }));

    function invalidateProposal() {
      if (!proposalBox || proposalBox.dataset.applied !== 'true') return;
      proposalBox.dataset.applied = 'false';
      proposalBox.innerHTML = window.interfaz.html`<p>Cambiaste las piezas o la urgencia: vuelve a pedir una propuesta de fecha.</p>`;
      if (deliveryDateInput) deliveryDateInput.value = '';
    }

    async function requestDeliveryProposal() {
      const services = selectedServiceInputs().map((input) => input.value);
      const mode = selectedServiceMode();
      if (!services.length || !mode) {
        if (proposalBox) proposalBox.innerHTML = window.interfaz.html`<p class="is-error">Selecciona el servicio y la modalidad antes de pedir una fecha.</p>`;
        return null;
      }
      if (proposalBox) proposalBox.innerHTML = window.interfaz.html`<p>Buscando el primer espacio disponible en la cola de la unidad…</p>`;
      try {
        const url = new URL(modal.dataset.serviceScheduleUrl, window.location.origin);
        url.searchParams.set('unidad_id', element('proyectoId')?.value || '');
        url.searchParams.set('modalidad', mode);
        url.searchParams.set('urgencia', selectedUrgency());
        url.searchParams.set('piezas', String(selectedPieces()));
        url.searchParams.set('proposito', selectedPurpose() || '');
        services.forEach((id) => url.searchParams.append('servicios', id));
        const response = await fetch(url, { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'No fue posible proponer una fecha');
        proposalPending = data.propuesta;
        renderDeliveryProposal(data.propuesta);
        return data.propuesta;
      } catch (error) {
        if (proposalBox) proposalBox.innerHTML = window.interfaz.html`<p class="is-error">${escapeHtml(error.message)}</p>`;
        return null;
      }
    }

    function renderDeliveryProposal(proposal) {
      if (!proposalBox) return;
      const queue = proposal.cola || {};
      proposalBox.dataset.applied = 'false';
      proposalBox.innerHTML = window.interfaz.html`
        <div class="reservation-delivery">
          <div class="reservation-delivery__main"><span>Propuesta del sistema</span><strong>${escapeHtml(formatSchedule(proposal.fecha, JSON.stringify(proposal.horas_seleccionadas || [])))}</strong><small>Entrega prevista: ${escapeHtml(formatSchedule(proposal.fecha_entrega, '[]'))}</small></div>
          <ul class="reservation-delivery__facts">
            <li><b>${escapeHtml(String(proposal.horas_estimadas))} h</b> de máquina estimadas para ${contarTrabajo(proposal.piezas)}</li>
            <li><b>${queue.solicitudes || 0}</b> solicitud${queue.solicitudes === 1 ? '' : 'es'} por delante en la cola (${queue.horas || 0} h)</li>
            <li>Jornada de la unidad <b>${escapeHtml(proposal.jornada || '')}</b> · ${proposal.urgencia === 'urgente' ? gettext('atención urgente') : gettext('atención normal')}</li>
          </ul>
          ${(proposal.avisos || []).map((aviso) => window.interfaz.html`<p class="reservation-delivery__warning"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i> ${escapeHtml(aviso)}</p>`).join('')}
          <button type="button" class="reservation-button" data-apply-proposal><i class="fas fa-check" aria-hidden="true"></i> Usar esta fecha y hora</button>
        </div>`;
    }

    function applyDeliveryProposal(proposal) {
      if (!proposal) return;
      const legacyCalendar = window.calendarState;
      if (legacyCalendar) {
        legacyCalendar.selectedDate = proposal.fecha;
        legacyCalendar.selectedHours = [...(proposal.horas_seleccionadas || [])];
        const [year, month] = String(proposal.fecha).split('-').map(Number);
        if (Number.isInteger(year) && Number.isInteger(month)) legacyCalendar.date = new Date(year, month - 1, 1);
      }
      if (typeof window.updateFormFields === 'function') {
        window.updateFormFields();
      } else {
        if (element('fechaInicio')) element('fechaInicio').value = `${proposal.fecha}T${proposal.hora_inicio}`;
        if (element('fechaFin')) element('fechaFin').value = `${proposal.fecha}T${proposal.hora_fin}`;
        if (element('horasSeleccionadas')) element('horasSeleccionadas').value = JSON.stringify(proposal.horas_seleccionadas || []);
      }
      if (typeof window.renderCalendarSurface === 'function') window.renderCalendarSurface();
      if (deliveryDateInput) deliveryDateInput.value = proposal.fecha_entrega || '';
      const urgencyInput = urgencyInputs.find((input) => input.value === proposal.urgencia);
      if (urgencyInput && !urgencyInput.checked) {
        urgencyInput.checked = true;
        syncUrgencyLabels();
      }
      if (proposalBox) {
        proposalBox.dataset.applied = 'true';
        const applied = create('p', 'reservation-delivery__applied', window.interfaz.html`<i class="fas fa-check-circle" aria-hidden="true"></i> Fecha y hora aplicadas a tu solicitud. Puedes elegir otra en el calendario si lo prefieres.`);
        proposalBox.querySelector('[data-apply-proposal]')?.replaceWith(applied);
      }
      updateSummary();
    }

    proposalBox?.addEventListener('click', (event) => {
      if (event.target.closest?.('[data-apply-proposal]')) applyDeliveryProposal(proposalPending);
    });
    proposeButton?.addEventListener('click', requestDeliveryProposal);
    otherDateButton?.addEventListener('click', () => {
      showCalendarForService = !showCalendarForService;
      integratedCalendar.hidden = !showCalendarForService;
      otherDateButton.textContent = showCalendarForService ? gettext('Ocultar el calendario') : gettext('Elegir otra fecha en el calendario');
    });

    function quoteTable(quote) {
      const rows = [];
      quote.conceptos.forEach((item) => {
        rows.push(window.interfaz.html`<tr class="is-group"><td colspan="6"><strong>${escapeHtml(item.servicio)}</strong> · ${contarTrabajo(quote.piezas)} · ${escapeHtml(item.horas_equipo || '0')} h de máquina</td></tr>`);
        (item.componentes || []).forEach((component) => {
          const aporte = Number(component.aporte_institucional || 0);
          rows.push(window.interfaz.html`<tr class="${component.cobrado ? 'is-charged' : 'is-reference'}"><td>${escapeHtml(component.nombre)}<small>${component.cobrado ? `Se cobra${Number(component.descuento) > 0 ? ` · descuento ${escapeHtml(quote.segmento_display)} ${item.descuento_porcentaje} %` : ''}` : gettext('Referencial · lo asume la UPEC')}</small></td><td>${escapeHtml(component.cantidad || '')}</td><td>${escapeHtml(component.precio_unitario || '')}</td><td>$${component.valor}</td><td>${aporte > 0 ? `−$${component.aporte_institucional}` : '$0.00'}</td><td>$${component.valor_usuario}</td></tr>`);
        });
      });
      (quote.materiales_planificados || []).forEach((item) => {
        rows.push(window.interfaz.html`<tr class="is-charged"><td>${escapeHtml(item.nombre)}<small>${escapeHtml([item.variante, (item.servicios || []).join(', '), item.obligatorio ? 'necesario' : ''].filter(Boolean).join(' · '))} · se cobra según consumo real</small></td><td>${item.cantidad === null ? gettext('Por calcular') : `${escapeHtml(item.cantidad)} ${escapeHtml(item.unidad)}`}</td><td>$${item.precio_unitario} por ${escapeHtml(item.unidad)}</td><td>$${item.subtotal}</td><td>$0.00</td><td>$${item.valor_usuario || item.subtotal}</td></tr>`);
      });
      if (quote.iva?.aplica) {
        rows.push(window.interfaz.html`<tr class="is-tax"><td>IVA ${escapeHtml(quote.iva.porcentaje)} %<small>Sobre lo que pagas</small></td><td>—</td><td>—</td><td>$${quote.iva.monto}</td><td>$0.00</td><td>$${quote.iva.monto}</td></tr>`);
      }
      rows.push(window.interfaz.html`<tr class="is-total"><td>Total</td><td></td><td></td><td>$${quote.valor_referencial}</td><td>−$${quote.aporte_institucional}</td><td><strong>$${quote.valor_estimado_usuario}</strong></td></tr>`);
      return window.interfaz.html`
        <div class="reservation-quote__segment"><span>Tarifa aplicada</span><strong>${escapeHtml(quote.segmento_display)}</strong></div>
        <div class="reservation-quote__table"><table class="reservation-quote__resources reservation-quote__service-table"><thead><tr><th>Concepto</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th><th>Lo asume la UPEC</th><th>A tu cargo</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>
        <div class="reservation-quote__total"><span>Valor de referencia $${quote.valor_referencial} · la UPEC asume $${quote.aporte_institucional} (componentes referenciales $${quote.no_cobrado} y descuentos $${quote.descuentos_segmento})${quote.iva?.aplica ? ` · IVA $${quote.iva.monto}` : ''}</span><strong>Valor estimado a tu cargo: $${quote.valor_estimado_usuario} USD</strong><small>${escapeHtml(quote.advertencia)} El valor final se determina con el peso real de los materiales utilizados.</small></div>`;
    }

    function renderQuote(quote) {
      const table = quoteTable(quote);
      const pertenencia = quote.aviso_pertenencia
        ? window.interfaz.html`<p class="reservation-quote__pending" role="status">${escapeHtml(quote.aviso_pertenencia)}</p>`
        : '';
      const pendiente = pertenencia + (quote.aviso_estimacion
        ? window.interfaz.html`<p class="reservation-quote__pending"><i class="fas fa-exclamation-circle" aria-hidden="true"></i> ${escapeHtml(quote.aviso_estimacion)}</p>`
        : '');
      if (quoteResult) {
        quoteResult.innerHTML = window.interfaz.html`${table}${pendiente}<p class="reservation-quote__hint">Cambia materiales, piezas o urgencia arriba y el valor se actualiza solo.</p>`;
      }
      if (quoteRecap) quoteRecap.innerHTML = `${table}${pendiente}`;
      if (quotePayment) quotePayment.hidden = !quote.requiere_aceptacion;
      if (paymentMethod) {
        paymentMethod.required = Boolean(quote.requiere_aceptacion);
        paymentMethod.disabled = !quote.requiere_aceptacion;
      }
      if (quoteAcceptance) {
        quoteAcceptance.required = Boolean(quote.requiere_aceptacion);
        quoteAcceptance.disabled = !quote.requiere_aceptacion;
      }
    }

    async function calculateServiceQuote() {
      const services = selectedServiceInputs().map((input) => input.value);
      const mode = selectedServiceMode();
      if (!services.length || !mode) {
        if (quoteResult) quoteResult.innerHTML = window.interfaz.html`<p class="is-error">Selecciona un servicio y una modalidad.</p>`;
        return false;
      }
      if (!serviceMaterialsWithinStock()) {
        if (quoteResult) quoteResult.innerHTML = window.interfaz.html`<p class="is-error">Hay materiales con una cantidad mayor a la existencia. Ajusta las cantidades en el paso anterior.</p>`;
        return false;
      }
      const { selectedIds, quantities } = syncServiceMaterials();
      const params = {
        piezas: selectedPieces(),
        urgencia: selectedUrgency(),
        seleccion: selectedIds,
        cantidades: quantities,
        equipo: serviceEquipmentInput?.value || '',
        modalidad: mode
      };
      if (quoteResult) quoteResult.innerHTML = window.interfaz.html`<p>Calculando la simulación institucional…</p>`;
      try {
        const url = new URL(modal.dataset.serviceQuoteUrl, window.location.origin);
        url.searchParams.set('unidad_id', element('proyectoId')?.value || '');
        url.searchParams.set('modalidad', mode);
        url.searchParams.set('piezas', String(params.piezas));
        url.searchParams.set('urgencia', params.urgencia);
        url.searchParams.set('seleccion', JSON.stringify(selectedIds));
        if (Object.keys(quantities).length) url.searchParams.set('cantidades', JSON.stringify(quantities));
        services.forEach((id) => url.searchParams.append('servicios', id));
        const response = await fetch(url, { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'No fue posible calcular');
        currentQuote = data.cotizacion;
        renderQuote(currentQuote);
        return true;
      } catch (error) {
        if (quoteResult) quoteResult.innerHTML = window.interfaz.html`<p class="is-error">${escapeHtml(error.message)}</p>`;
        return false;
      }
    }

    function applyServiceModeSelection(input, revealUploader = false) {
      invalidateQuote();
      invalidateProposal();
      updateTypeUI();
      updateAutomaticTitle();
      resourceValidationMessage.hidden = true;
      technicalFiles?.classList.remove('has-validation-error');
      if (technicalFileStatus && !technicalFileInput?.files?.length) {
        technicalFileStatus.hidden = true;
        technicalFileStatus.innerHTML = '';
      }
      serviceModes.forEach((item) => item.closest('[data-service-mode]')?.classList.toggle('is-selected', item.checked));
      if (revealUploader && input?.checked && input.value === 'modelo_listo' && technicalFiles) {
        technicalFiles.hidden = false;
        technicalFiles.classList.add('is-newly-revealed');
        window.requestAnimationFrame(() => {
          technicalFiles.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' });
          window.setTimeout(() => technicalFiles.classList.remove('is-newly-revealed'), 500);
        });
      }
    }

    serviceModes.forEach((input) => {
      input.addEventListener('change', () => applyServiceModeSelection(input, true));
      input.closest('[data-service-mode]')?.addEventListener('click', () => {
        window.requestAnimationFrame(() => {
          if (input.checked && !input.disabled) applyServiceModeSelection(input, true);
        });
      });
    });
    spaceScopeInputs.forEach((input) => input.addEventListener('change', () => updateFrequencyContext()));
    softwareInputs.forEach((input) => input.addEventListener('change', () => {
      if (state.type !== 'recursos') return;
      syncSoftwareAdicional();
      syncResourceChoices();
      syncCascadeVisibility();
    }));
    form.querySelectorAll('[name="proposito_codigo"]').forEach((input) => input.addEventListener('change', () => {
      syncSpaceScope();
      syncResourceChoices();
    }));
    softwareInputs.forEach((input) => input.addEventListener('change', () => {
      input.closest('.reservation-software-item')?.classList.toggle('is-selected', input.checked);
      syncResourceChoices();
      updateTypeUI();
      syncSoftwareEquipmentCompatibility({ autoSelect: input.checked });
      updateAutomaticTitle();
    }));
    form.querySelectorAll('[name="proposito_codigo"]').forEach((input) => input.addEventListener('change', () => {
      input.closest('label')?.parentElement?.querySelectorAll('label').forEach((label) => {
        label.classList.toggle('is-selected', label.contains(form.querySelector('[name="proposito_codigo"]:checked')));
      });
      updatePurposeContext({ reset: true });
      updateAutomaticTitle();
    }));
    form.querySelectorAll('[name="alcance_beneficiario"]').forEach((input) => {
      input.addEventListener('change', updateBeneficiaryContext);
    });
    activityLinkInputs.forEach((input) => {
      input.addEventListener('change', () => {
        updateActivityLinkContext();
      });
    });
    finalActivitySuggestionButton?.addEventListener('click', () => {
      if (!activityReferenceInput) return;
      activityReferenceInput.value = finalActivitySuggestionButton.dataset.suggestion
        || suggestedActivityName();
      activityReferenceInput.dataset.autoSuggested = 'true';
      delete activityReferenceInput.dataset.userEdited;
      finalActivityError.hidden = true;
      updateAutomaticTitle();
      refreshGuideAutomaticSummary();
      activityReferenceInput.focus();
    });
    finalActivityIdentity.querySelectorAll('[data-naming-pattern]').forEach((button) => {
      button.addEventListener('click', () => {
        if (!activityReferenceInput) return;
        activityReferenceInput.value = button.dataset.namingPattern || '';
        activityReferenceInput.dataset.userEdited = 'true';
        delete activityReferenceInput.dataset.autoSuggested;
        finalActivityError.hidden = true;
        updateAutomaticTitle();
        refreshGuideAutomaticSummary();
        activityReferenceInput.focus();
        const opening = activityReferenceInput.value.indexOf('[');
        const closing = activityReferenceInput.value.indexOf(']');
        if (opening >= 0 && closing > opening) activityReferenceInput.setSelectionRange(opening, closing + 1);
      });
    });
    guideSubjectInput?.addEventListener('input', () => {
      prioritizePublishedGuides();
      refreshFinalActivityIdentity();
      refreshGuideAutomaticSummary();
    });
    activityReferenceInput?.addEventListener('input', (event) => {
      if (event.isTrusted) {
        activityReferenceInput.dataset.userEdited = 'true';
        delete activityReferenceInput.dataset.autoSuggested;
      }
      updateAutomaticTitle();
      refreshGuideAutomaticSummary();
    });
    frequencyInputs.forEach((input) => {
      input.addEventListener('change', () => {
        updateFrequencyContext();
        updateSummary();
      });
    });
    frequencyRangeEnd?.addEventListener('change', updateSummary);
    // La programacion semanal cambia el numero de sesiones y, con el, el costo.
    frequencyInputs.forEach((input) => input.addEventListener('change', () => renderResourceCost(syncConsumables())));
    frequencyRangeEnd?.addEventListener('change', () => renderResourceCost(syncConsumables()));
    activityGuidesInput?.addEventListener('change', () => {
      closeActivityGuidePreview();
      acceptActivityGuides(activityGuidesInput.files);
      updateSummary();
    });
    activityGuidePreviewClose?.addEventListener('click', closeActivityGuidePreview);
    const activityGuidesDrop = activityGuidesField?.querySelector('.reservation-activity-guide-upload__drop');
    ['dragenter', 'dragover'].forEach((eventName) => {
      activityGuidesDrop?.addEventListener(eventName, (event) => {
        event.preventDefault();
        activityGuidesDrop.classList.add('is-dragging');
      });
    });
    ['dragleave', 'drop'].forEach((eventName) => {
      activityGuidesDrop?.addEventListener(eventName, (event) => {
        event.preventDefault();
        activityGuidesDrop.classList.remove('is-dragging');
        if (eventName === 'drop') {
          acceptActivityGuides(event.dataTransfer?.files);
          updateSummary();
        }
      });
    });
    activityCatalog?.addEventListener('change', updateCatalogActivity);
    subtypeSelect?.addEventListener('change', () => {
      updateActivityLinkContext({ reset: true });
      updateAutomaticTitle();
      placeIntentField();
    });
    updatePurposeContext({ reset: true });
    form.addEventListener('change', (event) => {
      if (event.target.matches('.unidad-checkbox')) {
        equipmentGroups().forEach(syncEquipmentGroupState);
        // Las piezas y el detalle son de cada equipo: aparecen al marcarlo.
        syncEquipmentWorkUnits(state.type === 'recursos' ? equipmentGroups() : []);
        syncEquipmentWorkSummary();
        syncScopeNotice();
        syncSpacesFromSelectedEquipment();
        syncSpaceEquipmentCompatibility({ autoSelect: false });
        filterConsumablesByService();
        updateConsumableGuidance();
        renderResourceCost(syncConsumables());
        updateAutomaticTitle();
      }
    });

    function updateTypeUI() {
      if (state.type === 'visita') {
        visitFlow.activate();
        return;
      }
      visitFlow.deactivate();
      const isService = state.type === 'servicio';
      const isResourceRequest = state.type === 'recursos';
      syncProcessField();
      resourceGrid.classList.toggle('is-service-flow', isService);

      // Un servicio es un encargo concreto: sin clasificacion academica ni
      // participantes. El proposito institucional queda fijado para los
      // indicadores y el solicitante es la persona responsable.
      if (isService) {
        const servicePurposeInput = form.querySelector('[name="proposito_codigo"][value="servicio_cientifico_tecnologico"]');
        if (servicePurposeInput && !servicePurposeInput.checked) {
          servicePurposeInput.checked = true;
          servicePurposeInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (selectedParticipants.size) {
          selectedParticipants.clear();
          syncParticipants();
        }
      }
      if (purposeSection) purposeSection.hidden = isService;
      if (isService) clearProcessMode();
      if (participantsContainer) participantsContainer.hidden = isService;
      if (purposeContext && isService) purposeContext.hidden = true;
      if (servicePurpose) servicePurpose.hidden = !isService;
      placeIntentField();
      const dataHeading = dataCard.querySelector('.rw-panel__header h3');
      const dataCopy = dataCard.querySelector('.rw-panel__header p');
      if (dataHeading) dataHeading.textContent = isService ? gettext('Finalidad del servicio') : gettext('Contexto y participantes');
      if (dataCopy) dataCopy.textContent = isService
        ? gettext('Cuéntanos brevemente para qué necesitas el trabajo. Tú eres la persona responsable de la solicitud.')
        : gettext('Clasifica el uso, indica si llevará guía e identifica a las personas que asistirán. El nombre y el contenido se completan al final.');

      serviceInputs.forEach((input) => {
        input.disabled = !isService;
        if (!isService) input.checked = false;
        input.closest('.reservation-service')?.classList.toggle('is-selected', input.checked);
      });
      updateServiceModeAvailability();

      const assisted = isAssistedService();
      syncResourceChoices();
      syncSpaceScope();
      syncResourceChoices();
      const usesEquipment = resourceKindActive('equipo');
      const usesSpace = resourceKindActive('espacio');
      const usesSoftware = resourceKindActive('software');
      const inventoryApplies = isResourceRequest && (usesEquipment || usesSpace);
      updateFrequencyContext();

      primaryResourceChoices.hidden = true;
      if (serviceCatalog) serviceCatalog.hidden = !isService;
      complementaryChoices.hidden = !assisted;
      spaceSelection.hidden = !usesSpace || spaceInputs.length > 0;
      if (spaceCatalog) spaceCatalog.hidden = isResourceRequest ? !resourceAvailability.espacio : !usesSpace;
      if (resourcesTitle) {
        resourcesTitle.textContent = isService
          ? assisted ? gettext('1. Modalidad y recursos complementarios') : gettext('1. Modalidad y archivos del servicio')
          : gettext('Selección guiada: dónde, con qué y qué necesitas');
      }
      if (equipmentCatalog) equipmentCatalog.hidden = isResourceRequest ? !cascadeEquipmentStageOpen() : !usesEquipment;
      if (serviceScope) serviceScope.hidden = !isService;
      if (softwareCatalog) {
        softwareCatalog.hidden = isResourceRequest
          ? !(cascadeSoftwareStageOpen() && hayLicenciasSinEquipo())
          : !usesSoftware;
      }
      if (technicalFiles) {
        const modeSelected = Boolean(selectedServiceMode());
        technicalFiles.hidden = !isService;
        technicalFiles.dataset.visibleForMode = modeSelected ? selectedServiceMode() : '';
        serviceScope?.classList.toggle('has-selected-mode', isService && modeSelected);
      }
      if (inventoryCatalog && !isResourceRequest) inventoryCatalog.hidden = !inventoryApplies;
      if (resourceCost) resourceCost.hidden = !isResourceRequest;
      if (serviceQuote) serviceQuote.hidden = !isService;
      if (servicePayment) servicePayment.hidden = !isService;
      if (serviceWork) serviceWork.hidden = !isService;
      if (serviceSchedule) serviceSchedule.hidden = !isService;
      integratedCalendar.hidden = isService && !showCalendarForService;
      if (isService) renderServiceWork();
      if (commitmentNote) {
        commitmentNote.innerHTML = isService
          ? '<i class="fas fa-handshake" aria-hidden="true"></i> <strong>Condiciones del servicio.</strong> Solo se cobran materiales consumidos; la UPEC asume los recursos, el diseño y el personal. La fecha propuesta depende de la cola de trabajo y puede ajustarse en la revisión técnica.'
          : window.interfaz.html`<i class="fas fa-handshake" aria-hidden="true"></i> <strong>Compromiso de uso.</strong> Los espacios, equipos y software reservados deben utilizarse en el horario confirmado. Una reserva no utilizada sin cancelación previa se registra como incumplimiento y reduce tu prioridad en futuras reservas y servicios, incluida la atención urgente. Los insumos y materiales solicitados se cobran según el consumo real registrado en el cierre.`;
      }
      if (specialRequirementsField) specialRequirementsField.hidden = false;
      if (responsibleCatalog) responsibleCatalog.hidden = false;

      if (technicalFileInput) {
        technicalFileInput.disabled = !isService;
        if (!isService) {
          technicalFileInput.value = '';
          renderTechnicalFiles();
        }
      }
      updateTechnicalFileGuidance();
      syncSpaceScope();
      const softwareEnabled = isResourceRequest ? cascadeSoftwareStageOpen() : usesSoftware;
      softwareInputs.forEach((input) => {
        const unavailable = input.closest('.reservation-software-item')?.classList.contains('is-unavailable');
        input.disabled = !softwareEnabled || unavailable;
        // Deshabilitado solo porque la etapa aun no abre: la cascada lo
        // vuelve a habilitar al marcar un equipo.
        if (!softwareEnabled && !unavailable) input.dataset.rwStageDisabled = 'true';
        else delete input.dataset.rwStageDisabled;
        if (!softwareEnabled) input.checked = false;
      });
      syncEquipmentAvailability();

      if (paymentMethod) {
        paymentMethod.required = false;
        paymentMethod.disabled = true;
      }
      if (quoteAcceptance) {
        quoteAcceptance.required = false;
        quoteAcceptance.disabled = true;
      }
      if (!inventoryApplies) {
        consumableChecks.forEach((check) => {
          check.checked = false;
          check.closest('.reservation-consumable')?.classList.remove('is-selected');
        });
        syncProvision();
      }
      syncResourceChoices();

      const stepTwo = shell.querySelector('[data-rw-step="2"] .rw-step__text');
      const stepThree = shell.querySelector('[data-rw-step="3"] .rw-step__text');
      const stepFour = shell.querySelector('[data-rw-step="4"] .rw-step__text');
      if (stepTwo) stepTwo.innerHTML = isService
        ? window.interfaz.html`<strong>Finalidad</strong><small>Para qué necesitas el servicio</small>`
        : window.interfaz.html`<strong>Contexto y guía</strong><small>Solo define el tipo de actividad</small>`;
      if (stepThree) stepThree.innerHTML = isService
        ? window.interfaz.html`<strong>Alcance y calendario</strong><small>Modalidad, archivos, recursos opcionales y fecha</small>`
        : window.interfaz.html`<strong>Recursos y calendario</strong><small>Dónde, con qué, software, insumos y horario</small>`;
      if (stepFour) stepFour.innerHTML = isService
        ? window.interfaz.html`<strong>Cotización y pago</strong><small>Revisa y acepta el valor</small>`
        : guideIsRequired()
          ? window.interfaz.html`<strong>Revisión y condiciones</strong><small>Valida la guía completa y los insumos</small>`
        : inventoryApplies
          ? window.interfaz.html`<strong>Insumos y estimación</strong><small>Revisa valor, aporte UPEC y condiciones</small>`
          : window.interfaz.html`<strong>Estimación y condiciones</strong><small>Revisa valor, aporte UPEC y acceso</small>`;
      const calendarTitle = calendar.querySelector('h4');
      if (calendarTitle) calendarTitle.textContent = isService
        ? gettext('2. Urgencia, fecha propuesta y entrega')
        : gettext('5. Fecha y horario');
      invalidateQuote();
      updateActivityLinkContext();
      filterConsumablesByService();
      updateConsumableGuidance();
      renderResourceCost(syncConsumables());
      placeInventoryCatalog();
      syncCascadeVisibility();
      updateAutomaticTitle();
      updateGuideBuilder();
    }

    addActions(requirementsCard, 4);

    const confirmationCard = panelCard(panels[4], '✓', gettext('Tu solicitud está lista para revisión'), gettext('Comprueba el nombre, la ruta seleccionada y las condiciones antes de enviarla.'));
    // Compromiso de uso (recursos) o condiciones del servicio; el texto lo fija updateTypeUI.
    const commitmentNote = create('p', 'rw-confirmation-commitment');
    appendUnique(confirmationCard, automaticTitle);
    automaticTitle.classList.add('reservation-auto-title--confirmation');
    const summary = create('div', 'rw-summary');
    summary.innerHTML = window.interfaz.html`
      <div class="rw-summary__item"><strong>Tipo de solicitud</strong><span data-rw-summary="type">Reserva combinada de recursos</span></div>
      <div class="rw-summary__item"><strong>Solicitante</strong><span data-rw-summary="requester">Por completar</span></div>
      <div class="rw-summary__item"><strong>Participantes</strong><span data-rw-summary="participants">Solicitante principal</span></div>
      <div class="rw-summary__item"><strong>Actividad</strong><span data-rw-summary="activity">Por completar</span></div>
      <div class="rw-summary__item rw-summary__item--wide"><strong>Lo que pretendes realizar</strong><span data-rw-summary="intent">Por describir</span></div>
      <div class="rw-summary__item"><strong>Guía de práctica</strong><span data-rw-summary="guide">No requerida</span></div>
      <div class="rw-summary__item"><strong>Disponibilidad</strong><span data-rw-summary="schedule">Selecciona fecha y horario</span></div>
      <div class="rw-summary__item"><strong>Responsable de seguimiento</strong><span data-rw-summary="responsible">Asignación por la unidad</span></div>
      <div class="rw-summary__item rw-summary__item--wide"><strong>Recurso o servicio</strong><span data-rw-summary="services">Por seleccionar</span></div>
      <div class="rw-summary__item rw-summary__item--wide"><strong>Proceso de la planta</strong><span data-rw-summary="process">Sin proceso definido</span></div>
      <div class="rw-summary__item rw-summary__item--wide"><strong>Insumos y materiales</strong><span data-rw-summary="consumables">Por definir</span></div>
      <div class="rw-summary__item rw-summary__item--wide"><strong>Apoyo del laboratorio</strong><span data-rw-summary="requirements">Incluido en la prestación del servicio de la unidad</span></div>`;
    confirmationCard.appendChild(summary);
    // Lo que la unidad exige para entrar y en qué está quien solicita: se avisa antes de enviar.
    const accessData = (() => {
      try { return JSON.parse(document.getElementById('accesoReserva')?.textContent || 'null'); } catch (error) { return null; }
    })();
    if (accessData && accessData.controlado && Array.isArray(accessData.requisitos) && accessData.requisitos.length) {
      const access = create('div', 'rw-access');
      const pending = accessData.requisitos.filter((item) => item.obligatorio && item.estado === 'pendiente').length;
      access.innerHTML = window.interfaz.html`<strong><i class="fas fa-id-badge" aria-hidden="true"></i> Acceso a la unidad · ${escapeHtml(accessData.categoria_display)}</strong>
        <ul>${accessData.requisitos.map((item) => window.interfaz.html`<li class="is-${escapeHtml(item.estado)}"><span>${escapeHtml(item.nombre)}${item.obligatorio ? '' : window.interfaz.html` <small>(opcional)</small>`}</span><b>${escapeHtml(item.detalle)}</b></li>`).join('')}</ul>
        <p>${pending
          ? `Tienes ${pending} requisito${pending === 1 ? '' : 's'} pendiente${pending === 1 ? '' : 's'}: puedes enviar la solicitud y la unidad la aprobará cuando lo cumplas o programará tu inducción.`
          : 'Tus habilitaciones están al día; la protección y las restricciones se verifican al ingresar.'}</p>`;
      confirmationCard.appendChild(access);
    }
    const terms = element('aceptarTerminos');
    if (terms) {
      const termsField = create('div', 'rw-confirmation-terms');
      const label = create('label');
      label.htmlFor = terms.id;
      label.appendChild(terms);
      label.appendChild(document.createTextNode(' Acepto las condiciones de uso, seguridad y responsabilidad aplicables a la unidad y sus recursos.'));
      termsField.appendChild(label);
      termsField.insertAdjacentHTML('beforeend', '<p><i class="fas fa-info-circle" aria-hidden="true"></i> La disponibilidad mostrada no equivale a aprobación; el responsable asignado validará la solicitud.</p>');
      termsField.appendChild(commitmentNote);
      confirmationCard.appendChild(termsField);
    }
    addActions(confirmationCard, 5);
    const visitFlow = window.createVisitReservationFlow({
      form, shell, dataCard, dataGrid, requesterProfile, resourceCard, resourceGrid, resources,
      calendar, integratedCalendar, calendarParticipantSummary, requirementsCard, confirmationCard,
      formatSchedule, hasCalendarSelection, showCalendarSelectionError, showStep,
    });
    window.reservationVisitFlow = visitFlow;

    function selectedResourceCounts() {
      const equipment = resourceKindActive('equipo')
        ? form.querySelectorAll('.unidad-checkbox:checked').length
        : 0;
      const selectedSpaces = resourceKindActive('espacio')
        ? spaceInputs.filter((input) => input.checked).length
        : 0;
      const spaces = resourceKindActive('espacio')
        ? selectedSpaceScope() === 'unidad_completa' ? 1 : selectedSpaces
        : 0;
      const software = resourceKindActive('software')
        ? softwareInputs.filter((input) => input.checked).length
        : 0;
      return { equipment, spaces, software };
    }

    function softwareTypeLabel(count) {
      const selected = softwareInputs.filter((input) => input.checked);
      const kinds = new Set(selected.map((input) => (
        input.closest('.reservation-software-item')?.dataset.resourceKind || 'software'
      )));
      if (kinds.size > 1) return 'Reserva de software y licencias';
      if (kinds.has('licencia')) return `Reserva de licencia${count === 1 ? '' : 's'} de software`;
      return 'Reserva de software';
    }

    function typeLabel() {
      if (state.type === 'servicio') return 'Solicitud de servicio';
      const counts = selectedResourceCounts();
      const selectedKinds = Object.values(counts).filter((count) => count > 0).length;
      if (selectedKinds > 1) return 'Reserva combinada de recursos';
      if (counts.equipment) return `Reserva de equipo${counts.equipment === 1 ? '' : 's'}`;
      if (counts.spaces) return `Reserva de espacio${counts.spaces === 1 ? '' : 's'}`;
      if (counts.software) return softwareTypeLabel(counts.software);
      return 'Reserva de recursos';
    }

    function formatSelectedHours(hoursValue) {
      let parsedHours = [];
      try {
        parsedHours = JSON.parse(hoursValue || '[]');
      } catch (_error) {
        return '';
      }
      const hours = Array.from(new Set(parsedHours.map(Number)))
        .filter((hour) => Number.isInteger(hour) && hour >= 0 && hour <= 23)
        .sort((left, right) => left - right);
      if (!hours.length) return '';

      const ranges = [];
      let start = hours[0];
      let end = hours[0];
      hours.slice(1).forEach((hour) => {
        if (hour === end + 1) {
          end = hour;
          return;
        }
        ranges.push([start, end + 1]);
        start = hour;
        end = hour;
      });
      ranges.push([start, end + 1]);
      const formatHour = (hour) => `${String(hour).padStart(2, '0')}:00`;
      return ranges.map(([rangeStart, rangeEnd]) => (
        `${formatHour(rangeStart)} a ${formatHour(rangeEnd)}`
      )).join(' y ');
    }

    function formatSchedule(dateValue, hoursValue) {
      if (!dateValue) return 'Selecciona fecha y horario';
      const [year, month, day] = dateValue.split('T')[0].split('-').map(Number);
      if (![year, month, day].every(Number.isInteger)) return 'Selecciona fecha y horario';
      const localDate = new Date(year, month - 1, day);
      if (Number.isNaN(localDate.getTime())) return 'Selecciona fecha y horario';
      const formattedDate = new Intl.DateTimeFormat(window.regionalInstitucion?.idioma || document.documentElement.lang || 'es-EC', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      }).format(localDate);
      const readableDate = formattedDate.charAt(0).toUpperCase() + formattedDate.slice(1);
      const readableHours = formatSelectedHours(hoursValue);
      return readableHours ? `${readableDate} · ${readableHours}` : readableDate;
    }

    function updateSummary() {
      if (state.type === 'visita') { visitFlow.updateSummary(); return; }
      const set = (key, value) => {
        const node = shell.querySelector(`[data-rw-summary="${key}"]`);
        if (node) node.textContent = value || 'Por completar';
      };
      set('type', typeLabel());
      set('requester', element('solicitanteNombre')?.value || element('solicitanteEmail')?.value);
      set('participants', `${selectedParticipants.size + 1} usuario${selectedParticipants.size ? 's' : ''} registrado${selectedParticipants.size ? 's' : ''}`);
      set('activity', element('tituloSolicitud')?.value || element('descripcionProyecto')?.value);
      set('intent', (intentInput?.value || '').trim() || 'Por describir');
      set('guide', guideIsRequired()
        ? (guideConfirmation?.checked ? gettext('Completada y confirmada · se enviará a revisión') : gettext('Pendiente de revisar'))
        : selectedActivityLink() === 'catalogo'
          ? gettext('Guía publicada vinculada')
          : gettext('No requerida para esta actividad'));
      const date = element('fechaInicio')?.value;
      const hours = element('horasSeleccionadas')?.value;
      const schedule = formatSchedule(date, hours);
      const frequency = selectedFrequency();
      set('schedule', (frequency === 'semanal_periodo'
        ? `Cada semana hasta finalizar ${academicPeriodInput?.value || 'el período'} · primera sesión: ${schedule}`
        : frequency === 'semanal_rango'
          ? `Cada semana hasta ${frequencyRangeEnd?.value || 'definir fecha final'} · primera sesión: ${schedule}`
          : schedule) + scheduleSummarySuffix());
      set('responsible', 'Asignación por la unidad');
      const selectedServices = serviceInputs
        .filter((input) => input.checked)
        .map((input) => input.closest('.reservation-service')?.querySelector('strong')?.textContent)
        .filter(Boolean);
      const fileCount = technicalFileInput?.files?.length || 0;
      const selectedSoftware = softwareInputs.filter((input) => input.checked)
        .map((input) => input.closest('.reservation-software-item')?.querySelector('strong')?.textContent)
        .filter(Boolean);
      set('services', state.type === 'servicio'
        ? `${selectedServices.join(', ') || 'Servicio por seleccionar'} · ${selectedPieces()} pieza(s) · ${selectedUrgency() === 'urgente' ? 'urgente' : gettext('atención normal')}${deliveryDateInput?.value ? ` · entrega prevista ${formatSchedule(deliveryDateInput.value, '[]')}` : ''} · ${fileCount} archivo(s) · ${currentQuote ? `$${currentQuote.total} USD` : gettext('sin cotizar')}${isAssistedService() && Object.values(state.resources).some(Boolean) ? ` · Complementos: ${selectedRequestedResourceName()}` : ''}`
        : selectedResourceName());
      const selectedConsumables = syncConsumables();
      const inventoryApplies = state.type === 'recursos'
        && (resourceKindActive('equipo') || resourceKindActive('espacio'));
      const consumablesText = state.type === 'servicio'
        ? currentQuote?.materiales_planificados?.length
          ? currentQuote.materiales_planificados.map((item) => (
            `${item.nombre}: ${item.cantidad === null ? gettext('cantidad por validar') : `${item.cantidad} ${item.unidad}`}`
          )).join(' · ')
          : selectedMaterialsSummary() || 'Sin materiales elegidos; el laboratorio los definirá en la revisión técnica'
        : !inventoryApplies
          ? gettext('No aplica para una reserva exclusiva de software')
          : selectedProvision() === 'unidad'
        ? selectedConsumables.map((item) => item.cantidad === null
          ? `${item.nombre}: cantidad por calcular`
          : `${item.nombre}: ${item.cantidad} ${item.unidad_medida}`).join(' · ')
        : gettext('No requiere insumos ni materiales');
      set('consumables', consumablesText || 'Por definir');
      set('requirements', 'Incluido en la prestación del servicio de la unidad');
      set('process', processSummaryText());
    }

    function guideIsRequired() {
      return state.type === 'recursos'
        && selectedPurpose() === 'docencia_practica'
        && ['manual', 'clonada'].includes(selectedActivityLink());
    }

    function guideAutomaticValues() {
      const catalogOption = activityCatalog?.selectedOptions?.[0];
      const activity = activityReferenceInput?.value.trim()
        || catalogOption?.dataset.name
        || 'Actividad por identificar';
      const activityCode = form.querySelector('[name="codigo_referencia_actividad"]')?.value.trim();
      // La asignatura la escribe la persona; nunca se copia del nombre de la practica.
      const subject = guideSubjectInput?.value.trim() || 'Por completar en la identificación';
      const date = element('fechaInicio')?.value || '';
      const hours = element('horasSeleccionadas')?.value || '[]';
      const beneficiaryScope = form.querySelector('[name="alcance_beneficiario"]:checked');
      const beneficiary = beneficiaryScope?.closest('label')?.textContent.trim()
        || 'Según perfil del solicitante';
      const careerName = beneficiaryCareerField?.querySelector('select')?.selectedOptions?.[0]?.textContent.trim()
        || (beneficiaryScope?.value === 'perfil_solicitante' ? modal.dataset.requesterCareer : '')
        || beneficiary;
      const level = beneficiaryScope?.value === 'perfil_solicitante'
        ? (modal.dataset.requesterLevel || '')
        : '';
      const career = [careerName, level].filter(Boolean).join(' · ');
      let selectedHours = [];
      try {
        selectedHours = JSON.parse(hours);
      } catch (_error) {
        selectedHours = [];
      }
      const durationCount = new Set(
        (Array.isArray(selectedHours) ? selectedHours : []).map(Number).filter(Number.isInteger)
      ).size;
      const equipment = Array.from(form.querySelectorAll('.unidad-checkbox:checked'))
        .map((input) => input.dataset.equipoNombre
          || form.querySelector(`[data-equipment-unit="${input.value}"]`)?.dataset.equipmentName
          || input.value)
        .filter(Boolean);
      const software = softwareInputs.filter((input) => input.checked)
        .map((input) => input.closest('.reservation-software-item')
          ?.querySelector('.reservation-software-item__content > strong')?.textContent?.trim())
        .filter(Boolean);
      if (softwareAdicionalTextoInput.value) software.push(`Por instalar: ${softwareAdicionalTextoInput.value}`);
      const selectedMaterials = syncConsumables();
      const consumables = selectedProvision() === 'unidad'
        ? selectedMaterials.map((item) => item.cantidad === null
          ? `${item.nombre} · cantidad por validar`
          : `${item.nombre} · ${item.cantidad} ${item.unidad_medida}`)
        : [];
      const policyLines = (value) => String(value || '')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      const institutionalSafety = [
        ...policyLines(unitRegulation.seguridad),
        ...policyLines(unitRegulation.equipos_materiales)
      ];
      const safety = institutionalSafety.length
        ? institutionalSafety.join('\n')
        : gettext('Cumplir las normas vigentes de seguridad, inducción y uso de equipos de la unidad.');
      const waste = selectedProvision() === 'unidad' && selectedMaterials.length
        ? gettext('El laboratorio clasificará, registrará y dispondrá los remanentes según los insumos aprobados y su procedimiento interno.')
        : 'No se prevén residuos asociados a insumos; se mantienen las obligaciones de orden, limpieza y reporte de novedades.';
      return {
        title: `Guía de práctica: ${activity}`,
        code: activityCode ? (activityCode.toUpperCase().startsWith('GP-') ? activityCode : `GP-${activityCode}`) : gettext('Se genera al guardar'),
        activity,
        subject,
        laboratory: element('modalTitle')?.textContent.trim() || 'Unidad de laboratorio',
        schedule: formatSchedule(date, hours),
        duration: durationCount ? `${durationCount} hora${durationCount === 1 ? '' : 's'}` : gettext('Se calcula al elegir el horario'),
        participants: `${selectedParticipants.size + 1} persona${selectedParticipants.size ? 's' : ''}`,
        resources: selectedResourceName(),
        equipment: equipment.join(' · ') || (resourceKindActive('equipo')
          ? gettext('Se seleccionarán en el paso 3')
          : gettext('No aplica')),
        software: software.join(' · ') || (resourceKindActive('software')
          ? gettext('Se seleccionará en el paso 3')
          : gettext('No aplica')),
        consumables: consumables.join(' · ') || 'No aplica: no se solicitaron insumos',
        safety,
        waste,
        career,
        responsible: form.querySelector('[name="responsable_actividad"]')?.value.trim()
          || element('solicitanteNombre')?.value.trim()
          || 'Solicitante principal',
        purpose: purposeLabels[selectedPurpose()] || 'Docencia y práctica curricular'
      };
    }

    function guideFieldLabel(input) {
      return input?.dataset.guideLabel
        || input?.closest('label')?.querySelector(':scope > span')?.textContent.replace('*', '').trim()
        || 'campo requerido';
    }

    // Apartados obligatorios sin contenido (etiquetas), segun el editor.
    // Firmas: quien elabora siempre; revision y aprobacion cuando el autor las
    // incluye, y entonces el sistema pide nombre y cargo.
    const GUIDE_SIGNATURE_ROLES = { elaborado: 'Elaborado por', revisado: 'Revisado por', aprobado: 'Aprobado por' };

    function collectGuideSignatures() {
      const blocks = Array.from(guidePreview.querySelectorAll('[data-guide-signature]'));
      if (!blocks.length) return null;
      const firmas = {};
      blocks.forEach((block) => {
        const rol = block.dataset.guideSignature;
        const activo = rol === 'elaborado' || Boolean(block.querySelector('input[type="checkbox"]')?.checked);
        block.classList.toggle('is-off', !activo);
        firmas[rol] = {
          activo,
          nombre: block.querySelector(`[name="firma_${rol}_nombre"]`)?.value.trim() || '',
          cargo: block.querySelector(`[name="firma_${rol}_cargo"]`)?.value.trim() || '',
          fecha: block.querySelector(`[name="firma_${rol}_fecha"]`)?.value.trim() || ''
        };
      });
      if (guideSignaturesInput) guideSignaturesInput.value = JSON.stringify(firmas);
      return firmas;
    }

    function guideSignatureMissing() {
      const firmas = collectGuideSignatures() || {};
      const missing = [];
      Object.entries(firmas).forEach(([rol, firma]) => {
        if (rol === 'elaborado' || !firma.activo) return;
        if (!firma.nombre) missing.push(`firma «${GUIDE_SIGNATURE_ROLES[rol]}»: nombre`);
        if (!firma.cargo) missing.push(`firma «${GUIDE_SIGNATURE_ROLES[rol]}»: cargo`);
      });
      return missing;
    }

    guidePreview.addEventListener('input', (event) => {
      const block = event.target.closest?.('[data-guide-signature]');
      if (!block) return;
      if (event.target.name?.endsWith('_nombre')) event.target.dataset.userEdited = 'true';
      collectGuideSignatures();
      invalidateGuidePreview();
      updateGuidePreviewState();
    });
    guidePreview.addEventListener('change', (event) => {
      if (!event.target.closest?.('[data-guide-signature]') || event.target.type !== 'checkbox') return;
      collectGuideSignatures();
      invalidateGuidePreview();
      updateGuidePreviewState();
    });

    function guideMissingLabels() {
      if (guideEditor) return [...guideEditor.faltantes(), ...guideSignatureMissing()];
      return guideRequiredInputs.filter((input) => !input.value.trim()).map(guideFieldLabel);
    }

    function syncGuideFieldsFromEditor() {
      if (!guideEditor) return;
      collectGuideSignatures();
      const values = guideEditor.valores();
      guideFieldInputs.forEach((input) => {
        const value = values[input.dataset.guideField] ?? '';
        if (input.value !== value) input.value = value;
      });
      const completeness = guideBuilder.querySelector('[data-guide-completeness]');
      if (completeness) {
        const missing = guideMissingLabels();
        completeness.textContent = missing.length
          ? `Faltan: ${missing.map((label) => label.toLowerCase()).join(', ')}.`
          : gettext('Apartados obligatorios completos. Revisa la vista final y acepta el contenido.');
        completeness.classList.toggle('is-complete', !missing.length);
      }
    }

    function guideManualValues() {
      syncGuideFieldsFromEditor();
      const values = {};
      form.querySelectorAll('textarea[name^="guia_"], input[type="text"][name^="guia_"], input[type="hidden"][data-guide-field]').forEach((input) => {
        values[input.name.replace(/^guia_/, '')] = input.value.trim();
      });
      values.formato_procedimiento = guideBuilder.querySelector('[name="guia_formato_procedimiento"]')?.value || 'numerado';
      values.firmas = guideSignaturesInput?.value || '';
      return values;
    }

    // Frases iniciales de la descripcion de la reserva, para la guia.
    function intentSummary(maxSentences = 2) {
      const text = (intentInput?.value || '').trim().replace(/\s+/g, ' ');
      if (!text) return '';
      const sentences = text.match(/[^.!?]+[.!?]?/g) || [text];
      return sentences.slice(0, maxSentences).join(' ').trim();
    }

    function applyGuideSuggestions() {
      if (!guideIsRequired()) return;
      refreshFinalActivityIdentity({ autofill: true });
      const automatic = guideAutomaticValues();
      const intent = intentSummary(2);
      const intentContext = intentSummary(4);
      const activity = automatic.activity === 'Actividad por identificar'
        ? gettext('la práctica propuesta')
        : automatic.activity;
      const usableResources = [automatic.equipment, automatic.software]
        .filter((value) => value
          && value !== 'No aplica'
          && !/^Se seleccionar/i.test(value));
      const resourceText = usableResources.length
        ? usableResources.join(' y ')
        : gettext('los recursos seleccionados del laboratorio');
      const suggestions = {
        guia_resultado_aprendizaje: intent
          ? `Aplica un procedimiento técnico, seguro y documentado para desarrollar ${activity}, utilizando correctamente ${resourceText}. La práctica se orienta a lo descrito en la reserva: ${intent}`
          : `Aplica un procedimiento técnico, seguro y documentado para desarrollar ${activity}, utilizando correctamente ${resourceText}.`,
        guia_objetivos: [
          intent ? `Lograr lo planteado para ${activity}: ${intent}` : '',
          `Preparar ${resourceText} de acuerdo con las condiciones de la actividad.`,
          `Ejecutar ${activity} siguiendo el procedimiento y las medidas de seguridad definidas.`,
          gettext('Registrar las evidencias, resultados y novedades obtenidas durante la práctica.')
        ].filter(Boolean).join('\n'),
        guia_fundamento_teorico: intentContext
          ? `Contexto de la actividad. ${intentContext}\nDescribe a continuación los conceptos, leyes o modelos de ${automatic.subject && automatic.subject !== 'Por completar en la identificación' ? automatic.subject : gettext('la asignatura')} que sustentan ${activity} y cómo se relacionan con lo que se observará en el laboratorio.`
          : '',
        guia_procedimiento: [
          gettext('Confirmar el objetivo, los participantes, el horario y los recursos reservados.'),
          `Preparar ${resourceText} y verificar sus condiciones de operación.`,
          `Desarrollar ${activity} conforme a las indicaciones técnicas y de seguridad.`,
          gettext('Registrar parámetros, evidencias, consumos y novedades relevantes.'),
          gettext('Entregar el área y los recursos en condiciones seguras y reportar el resultado.')
        ].join('\n'),
        guia_resultados_esperados: [
          `Evidencia verificable de ${activity}.`,
          gettext('Registro de parámetros, observaciones y resultado obtenido.'),
          gettext('Recursos entregados y consumos reportados para la trazabilidad institucional.')
        ].join('\n'),
        guia_criterios_evaluacion: [
          gettext('Cumplimiento del procedimiento y de las medidas de seguridad.'),
          gettext('Uso correcto de los recursos y materiales seleccionados.'),
          gettext('Calidad y trazabilidad de la evidencia o producto obtenido.')
        ].join('\n')
      };
      // El proceso elegido sabe llenar su guía: procedimiento, seguridad y resultados.
      const processGuide = processState.seleccion?.guia || null;
      if (processGuide) {
        Object.entries(processGuide).forEach(([name, html]) => { if (html) suggestions[name] = html; });
      }
      ensureGuideEditor();
      let completed = 0;
      Object.entries(suggestions).forEach(([name, value]) => {
        const field = name.replace(/^guia_/, '');
        if (!value || !guideEditor || !guideEditor.vacio(field)) return;
        const fromProcess = Boolean(processGuide && processGuide[name]);
        guideEditor.establecer(field, fromProcess ? value : window.GuiaEditor.textoAHtml(value, GUIDE_FIELD_TYPES[field] || 'rico'));
        completed += 1;
      });
      syncGuideFieldsFromEditor();
      invalidateGuidePreview();
      refreshGuideAutomaticSummary();
      if (guideSuggestionStatus) {
        guideSuggestionStatus.textContent = completed
          ? `Se completaron ${completed} apartados vacíos. Ábrelos con «Revisar y completar guía» y ajusta la propuesta.`
          : 'Los apartados ya tenían contenido; no se reemplazó ninguna respuesta.';
      }
    }

    const GUIDE_FIELD_TYPES = {
      resultado_aprendizaje: 'texto', objetivos: 'texto', fundamento_teorico: 'rico',
      medidas_seguridad: 'texto', procedimiento: 'pasos', resultados_esperados: 'tablas',
      criterios_evaluacion: 'tablas',
    };

    const GUIDE_SIGNATURE_LABELS = {
      schedule: 'la fecha u horario', duration: 'la duración', participants: 'los participantes',
      equipment: 'los equipos', software: 'el software', consumables: 'los insumos',
      activity: 'el nombre de la práctica', title: gettext('el título'), subject: 'la asignatura',
      career: 'la carrera', responsible: 'el responsable', purpose: 'el propósito',
      safety: 'la política de seguridad', waste: 'el manejo de residuos', resources: 'los recursos',
      code: 'el código', laboratory: 'el laboratorio'
    };

    function guideSignatureChanges(previous, current) {
      let before;
      let after;
      try {
        before = JSON.parse(previous || '{}');
        after = JSON.parse(current || '{}');
      } catch (_error) {
        return [];
      }
      const changed = [];
      ['automatic', 'manual'].forEach((group) => {
        const keys = new Set([...Object.keys(before[group] || {}), ...Object.keys(after[group] || {})]);
        keys.forEach((key) => {
          if ((before[group] || {})[key] === (after[group] || {})[key]) return;
          const label = GUIDE_SIGNATURE_LABELS[key]
            || guideFieldLabel(guideBuilder.querySelector(`[name="guia_${key}"]`)).toLowerCase();
          if (!changed.includes(label)) changed.push(label);
        });
      });
      return changed;
    }

    function currentGuideSignature() {
      return JSON.stringify({
        automatic: guideAutomaticValues(),
        manual: guideManualValues()
      });
    }

    function invalidateGuidePreview() {
      guidePreviewSignature = '';
      if (guideConfirmation) {
        guideConfirmation.checked = false;
        guideConfirmation.disabled = true;
      }
      guideBuilder.classList.remove('is-reviewed');
      guideFinalReview.classList.remove('is-reviewed');
      if (guideFinalError) guideFinalError.hidden = true;
    }

    function refreshGuideAutomaticSummary() {
      const values = guideAutomaticValues();
      Object.entries({
        title: values.title,
        code: values.code,
        activity: values.activity,
        subject: values.subject,
        schedule: values.schedule,
        duration: values.duration,
        participants: values.participants,
        career: values.career,
        responsible: values.responsible,
        laboratory: values.laboratory,
        purpose: values.purpose,
        equipment: values.equipment,
        software: values.software,
        consumables: values.consumables,
        safety: values.safety,
        waste: values.waste
      }).forEach(([key, value]) => {
        [guideBuilder, guideFinalReview].forEach((root) => {
          const target = root.querySelector(`[data-guide-auto="${key}"]`);
          if (target) target.textContent = value;
        });
      });
      refreshGuideDocumentAutomatic(values);
    }

    // Datos protegidos del documento (encabezado, generales, recursos, politicas, firma).
    function refreshGuideDocumentAutomatic(values) {
      const doc = guidePreview.querySelector('[data-guide-document]');
      if (!doc) return;
      const author = element('solicitanteNombre')?.value || 'Usuario autenticado';
      Object.entries({ ...values, author }).forEach(([key, value]) => {
        doc.querySelectorAll(`[data-guide-auto="${key}"]`).forEach((target) => {
          if (key === 'version') return;
          const text = Array.isArray(value) ? value.join(' · ') : String(value ?? '');
          if (target.tagName === 'INPUT') {
            // El nombre de quien elabora se propone; si la persona lo edita, se respeta.
            if (target.dataset.userEdited !== 'true' && target.value !== text) target.value = text;
            return;
          }
          if (target.textContent !== text) target.textContent = text;
        });
      });
      const safetyList = doc.querySelector('[data-guide-auto-list="safety"]');
      if (safetyList) {
        const html = guideLines(values.safety).map((line) => window.interfaz.html`<li>${escapeHtml(line)}</li>`).join('') || window.interfaz.html`<li>Se aplicarán las normas vigentes de la unidad.</li>`;
        if (safetyList.innerHTML !== html) safetyList.innerHTML = html;
      }
      const manual = guideManualValuesRaw();
      const formatted = guideReferences(manual.bibliografia, manual.materiales_complementarios);
      [[gettext('[data-guide-references]'), formatted.references], [gettext('[data-guide-materials]'), formatted.materials]].forEach(([selector, html]) => {
        const node = doc.querySelector(selector);
        if (node && node.innerHTML !== html) node.innerHTML = html;
      });
    }

    // Bibliografia y materiales tal como estan escritos (sin tocar el editor).
    function guideManualValuesRaw() {
      return {
        bibliografia: form.querySelector('[name="guia_bibliografia"]')?.value || '',
        materiales_complementarios: form.querySelector('[name="guia_materiales_complementarios"]')?.value || ''
      };
    }

    function updateGuideBuilder() {
      if (state.type === 'visita') return;
      const active = guideIsRequired();
      refreshFinalActivityIdentity({ autofill: state.step >= 4 });
      guideBuilder.hidden = !active;
      guideFinalReview.hidden = !active;
      guideInputs.forEach((input) => {
        input.disabled = !active;
        if (input.matches('[data-guide-required]')) input.required = active;
      });
      if (guideConfirmation) {
        guideConfirmation.required = active;
        guideConfirmation.disabled = !active || !guidePreviewSignature;
        if (!active) guideConfirmation.checked = false;
      }
      const heading = requirementsCard.querySelector('.rw-panel__header h3');
      const copy = requirementsCard.querySelector('.rw-panel__header p');
      const stepFour = shell.querySelector('[data-rw-step="4"] .rw-step__text');
      if (active) {
        if (heading) heading.textContent = gettext('Identificación, guía y condiciones');
        if (copy) copy.textContent = gettext('Confirma el nombre sugerido y completa la guía con los datos definitivos de recursos, insumos y horario.');
        if (stepFour) stepFour.innerHTML = window.interfaz.html`<strong>Identificación y guía</strong><small>Confirma el nombre y revisa el documento</small>`;
        refreshGuideAutomaticSummary();
      } else {
        if (heading) heading.textContent = state.type === 'servicio'
          ? gettext('Cotización y condiciones del servicio')
          : gettext('Requisitos de la solicitud');
        if (copy) copy.textContent = state.type === 'servicio'
          ? gettext('Revisa el valor estimado, la forma de pago y las condiciones de atención.')
          : gettext('Revisa inventario, costo referencial y condiciones aplicables a la reserva.');
        if (stepFour) {
          const inventoryApplies = state.type === 'recursos'
            && (resourceKindActive('equipo') || resourceKindActive('espacio'));
          stepFour.innerHTML = state.type === 'servicio'
            ? window.interfaz.html`<strong>Cotización y pago</strong><small>Revisa y acepta el valor</small>`
            : inventoryApplies
              ? window.interfaz.html`<strong>Insumos y estimación</strong><small>Revisa valor, aporte UPEC y condiciones</small>`
              : window.interfaz.html`<strong>Estimación y condiciones</strong><small>Revisa valor, aporte UPEC y acceso</small>`;
        }
      }
    }

    function showGuideError(message, input, { final = false } = {}) {
      const target = final ? guideFinalError : guideError;
      if (target) {
        target.textContent = message;
        target.hidden = false;
        target.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      }
      input?.focus?.();
      return false;
    }

    function validateEmbeddedGuide({ requireAcceptance = true } = {}) {
      if (!guideIsRequired()) return true;
      if (guideError) guideError.hidden = true;
      if (guideFinalError) guideFinalError.hidden = true;
      const missing = guideMissingLabels();
      if (missing.length) {
        return showGuideError(
          `Completa en la guía: ${missing.join(', ')}. Ábrela con «Revisar y completar guía».`,
          guideBuilder.querySelector('[data-guide-open]')
        );
      }
      if (guideEditor && guideEditor.pendientes() > 0) {
        return showGuideError('Espera a que terminen de cargarse las imágenes de la guía.', guideBuilder.querySelector('[data-guide-open]'));
      }
      if (!requireAcceptance) return true;
      if (!guidePreviewSignature || guidePreviewSignature !== currentGuideSignature()) {
        const changed = guideSignatureChanges(guidePreviewSignature, currentGuideSignature());
        invalidateGuidePreview();
        return showGuideError(
          changed.length
            ? `Abre la vista previa y pulsa «Contenido revisado»: cambió ${changed.join(', ')} desde la última revisión.`
            : gettext('Abre la vista previa y pulsa «Contenido revisado» para habilitar la firma.'),
          guideBuilder.querySelector('[data-guide-open]'),
          { final: true }
        );
      }
      if (!guideConfirmation?.checked) {
        return showGuideError(
          'Confirma que revisaste la vista previa de la guía antes de continuar.',
          guideConfirmation,
          { final: true }
        );
      }
      return true;
    }

    function guideLines(value) {
      return String(value || '')
        .split(/\r?\n/)
        .map((line) => line.replace(/^\s*(?:\d+[.)]|[-*•])\s*/, '').trim())
        .filter(Boolean);
    }

    // El documento nace de la misma plantilla que la vista HTML del servidor
    // (includes/documento.html, modo asistente) y se construye una sola vez.
    function ensureGuideEditor() {
      if (guideEditor || typeof window.GuiaEditor === 'undefined') return guideEditor;
      const template = document.getElementById('guiaDocumentoPlantilla');
      const target = guidePreview.querySelector('[data-guide-preview-document]');
      if (!template || !target) return null;
      target.appendChild(template.content.cloneNode(true));
      const doc = target.querySelector('[data-guide-document]');
      // Materiales (10) y bibliografia (11) se redactan en su apartado del
      // documento, con la misma jerarquia que el resto.
      doc.querySelectorAll('[data-guide-source]').forEach((zone) => {
        const field = form.querySelector(`[name="guia_${zone.dataset.guideSource}"]`)?.closest('.reservation-guide-field');
        if (!field) return;
        zone.appendChild(field);
        zone.hidden = false;
      });
      guideEditor = window.GuiaEditor.crear(doc, {
        urlSubida: modal.dataset.figureUploadUrl || '',
        csrf: form.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        borrador: guideTokenInput?.value || '',
        figuras: [],
        modo: 'edicion',
        sugerencias: (campo) => (GUIDE_SNIPPETS[`guia_${campo}`] || []).map((option) => {
          const context = guideSnippetContext();
          const text = option.text.replace(/\{(practica|asignatura|recursos|laboratorio|intencion)\}/g, (_match, key) => context[key] || '');
          return {
            label: option.label,
            resumen: text.split('\n')[0].replace(/^##\s+/, '').slice(0, 96),
            html: window.GuiaEditor.textoAHtml(text, GUIDE_FIELD_TYPES[campo] || 'rico')
          };
        })
      });
      guideEditor.on('cambio', () => {
        syncGuideFieldsFromEditor();
        invalidateGuidePreview();
        updateGuidePreviewState();
      });
      guideEditor.on('subidas', (pending) => {
        const node = guidePreview.querySelector('[data-guide-pending]');
        if (node) node.hidden = !pending;
        updateGuidePreviewState();
      });
      // La presentacion del procedimiento se elige en la barra del editor.
      const formatInput = guideBuilder.querySelector('[name="guia_formato_procedimiento"]');
      guideEditor.on('formato', (formato) => { if (formatInput) formatInput.value = formato; });
      if (formatInput?.value && formatInput.value !== 'numerado') guideEditor.formatoPasos(formatInput.value);
      syncGuideFieldsFromEditor();
      return guideEditor;
    }

    function setGuidePreviewMode(mode) {
      if (!guideEditor) return;
      guideEditor.modo(mode);
      guidePreview.querySelectorAll('[data-guide-mode]').forEach((button) => {
        const on = button.dataset.guideMode === mode;
        button.classList.toggle('is-on', on);
        button.setAttribute('aria-selected', on ? 'true' : 'false');
      });
    }
    guidePreview.querySelectorAll('[data-guide-mode]').forEach((button) => {
      button.addEventListener('click', () => setGuidePreviewMode(button.dataset.guideMode));
    });
    guideBuilder.querySelector('[data-guide-open]')?.addEventListener('click', (event) => openGuidePreview(event.currentTarget));

    function updateGuidePreviewState() {
      const missing = guideMissingLabels();
      const pending = guideEditor ? guideEditor.pendientes() : 0;
      if (guidePreviewStatus) {
        guidePreviewStatus.hidden = false;
        guidePreviewStatus.classList.toggle('is-complete', !missing.length);
        guidePreviewStatus.innerHTML = missing.length
          ? window.interfaz.html`<i class="fas fa-exclamation-triangle"></i><div><strong>Apartados obligatorios por completar</strong><span>Escribe en la guía: ${missing.map(escapeHtml).join(', ')}. Los demás apartados son opcionales.</span></div>`
          : window.interfaz.html`<i class="fas fa-check-circle"></i><div><strong>Documento completo para revisión</strong><span>Comprueba la vista final y pulsa “Contenido revisado” para habilitar la firma electrónica.</span></div>`;
      }
      if (guidePreviewAccept) guidePreviewAccept.disabled = Boolean(missing.length) || pending > 0;
      const footnote = guidePreview.querySelector('[data-guide-preview-footnote]');
      if (footnote) {
        footnote.textContent = missing.length
          ? `Para aceptar, completa: ${missing.join(', ')}.`
          : pending > 0 ? gettext('Esperando que terminen las cargas de imágenes.') : gettext('Al aceptar se habilita la firma electrónica en el paso 4.');
        footnote.classList.toggle('is-error', Boolean(missing.length));
      }
    }

    function renderGuidePreview() {
      ensureGuideEditor();
      refreshGuideAutomaticSummary();
      updateGuidePreviewState();
    }

    function closeGuidePreview() {
      guidePreview.hidden = true;
      document.body.classList.remove('reservation-guide-preview-open');
      syncGuideFieldsFromEditor();
      guidePreviewTrigger?.focus?.();
    }

    function openGuidePreview(trigger) {
      guidePreviewTrigger = trigger;
      if (!ensureGuideEditor()) return;
      requestBibliographyFormat();
      renderGuidePreview();
      const missing = guideMissingLabels();
      setGuidePreviewMode(missing.length ? 'edicion' : 'final');
      if (missing.length && guideError) {
        guideError.textContent = `Completa en la guía: ${missing.join(', ')}.`;
        guideError.hidden = false;
      }
      guidePreview.hidden = false;
      document.body.classList.add('reservation-guide-preview-open');
      // El documento se lee desde el inicio; el foco va al cierre para no
      // desplazar el dialogo hasta el pie.
      guidePreview.scrollTop = 0;
      guidePreview.querySelector('[data-guide-preview-close]')?.focus?.({ preventScroll: true });
    }

    // Las referencias se formatean en el servidor (mismo codigo que el guardado).
    const bibliographyFormat = { source: null, items: [], materials: [] };

    function bibliographyKey() {
      const references = form.querySelector('[name="guia_bibliografia"]')?.value || '';
      const materials = form.querySelector('[name="guia_materiales_complementarios"]')?.value || '';
      return `${references}\u0000${materials}`;
    }

    function requestBibliographyFormat() {
      const key = bibliographyKey();
      const url = modal.dataset.bibliographyFormatUrl;
      if (!url || bibliographyFormat.source === key) return;
      const [texto, materiales] = key.split('\u0000');
      fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        },
        body: JSON.stringify({ texto, materiales })
      })
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => {
          if (!data?.success) return;
          bibliographyFormat.source = key;
          bibliographyFormat.items = Array.isArray(data.referencias) ? data.referencias : [];
          bibliographyFormat.materials = Array.isArray(data.materiales) ? data.materiales : [];
          if (!guidePreview.hidden) refreshGuideAutomaticSummary();
        })
        .catch(() => {});
    }

    function guideReferences(rawReferences, rawMaterials) {
      const formatted = bibliographyFormat.source === `${rawReferences || ''}\u0000${rawMaterials || ''}`;
      const references = formatted
        ? bibliographyFormat.items
        : guideLines(rawReferences).map((line) => line.replace(/^\[\d+\]\s*/, ''));
      const referencesHtml = [window.interfaz.html`<ol class="guide-references">${references.length
        ? references.map((item) => window.interfaz.html`<li>${escapeHtml(item)}</li>`).join('')
        : window.interfaz.html`<li class="is-empty">No registrada</li>`}</ol>`];
      if (!formatted && /@\w+\s*\{/.test(rawReferences || '')) {
        referencesHtml.push('<p class="guide-document__source">Las entradas BibTeX se mostrarán en estilo IEEE en cuanto termine el formateo.</p>');
      }
      const materials = formatted
        ? bibliographyFormat.materials
        : guideLines(rawMaterials).map((line) => {
          const [title, url] = line.split('|').map((part) => part.trim());
          const link = /^https?:\/\//i.test(url || '') ? url : (/^https?:\/\//i.test(title) ? title : '');
          return { titulo: title && title !== link ? title : link, url: link };
        });
      const materialsHtml = window.interfaz.html`<ul class="guide-materials">${materials.length
        ? materials.map((item) => (item.url
          ? window.interfaz.html`<li><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.titulo)}</a> <small>${escapeHtml(item.url)}</small></li>`
          : window.interfaz.html`<li>${escapeHtml(item.titulo)}</li>`)).join('')
        : window.interfaz.html`<li class="is-empty">No registrados</li>`}</ul>`;
      return { references: referencesHtml.join(''), materials: materialsHtml };
    }

    guideSuggestionButton?.addEventListener('click', applyGuideSuggestions);
    guideBuilder.querySelector('[data-material-template]')?.addEventListener('click', () => {
      const input = form.querySelector('[name="guia_materiales_complementarios"]');
      if (!input || input.disabled) return;
      const template = 'Título del recurso | https://';
      const separator = input.value.trim() ? '\n' : '';
      input.value = `${input.value.replace(/\s+$/, '')}${separator}${template}`;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      input.setSelectionRange(input.value.length - template.length, input.value.length - ' | https://'.length);
    });
    let bibliographyTimer = null;
    ['guia_bibliografia', 'guia_materiales_complementarios'].forEach((name) => {
      guideBuilder.querySelector(`[name="${name}"]`)?.addEventListener('input', () => {
        window.clearTimeout(bibliographyTimer);
        bibliographyTimer = window.setTimeout(requestBibliographyFormat, 500);
        // El apartado formateado se actualiza mientras se escribe.
        if (!guidePreview.hidden) refreshGuideAutomaticSummary();
      });
    });
    // Vista previa del borrador en el visor compartido, sin abandonar la guía.
    guidePreview.querySelector('[data-guide-pdf-preview]')?.addEventListener('click', async (event) => {
      const url = modal.dataset.guidePdfPreviewUrl;
      if (!url) return;
      const boton = event.currentTarget;
      if (boton.disabled) return;
      if (!window.visorPdfModal) {
        showGuideError('El visualizador no está disponible. Recarga la página e inténtalo de nuevo.', boton);
        return;
      }
      syncGuideFieldsFromEditor();
      const datos = new FormData();
      datos.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
      datos.append('unidad_id', element('proyectoId')?.value || '');
      form.querySelectorAll('[name^="guia_"]').forEach((input) => {
        if (input.type === 'file') return;
        if (input.type === 'checkbox' || input.type === 'radio') {
          if (input.checked) datos.append(input.name, input.value);
          return;
        }
        datos.append(input.name, input.value ?? '');
      });
      datos.append('automaticos', JSON.stringify(guideAutomaticValues()));
      boton.disabled = true;
      let documentoUrl = '';
      try {
        const respuesta = await fetch(url, {method: 'POST', credentials: 'same-origin', body: datos});
        if (!respuesta.ok || !respuesta.headers.get('content-type')?.toLowerCase().includes('application/pdf')) {
          throw new Error('No se pudo preparar el documento. Revisa tu sesión e inténtalo nuevamente.');
        }
        documentoUrl = URL.createObjectURL(await respuesta.blob());
        const liberar = () => URL.revokeObjectURL(documentoUrl);
        const abierto = window.visorPdfModal.abrirUrl(documentoUrl, {
          titulo: 'Borrador de la guía de práctica', descarga: documentoUrl, alCerrar: liberar,
        });
        if (!abierto) {
          liberar();
          showGuideError('No se pudo abrir el visualizador. Inténtalo nuevamente.', boton);
        }
      } catch (error) {
        if (documentoUrl) URL.revokeObjectURL(documentoUrl);
        showGuideError(error.message || 'No se pudo preparar el documento. Inténtalo nuevamente.', boton);
      } finally {
        boton.disabled = false;
      }
    });
    guidePreview.querySelector('[data-guide-preview-accept]')?.addEventListener('click', () => {
      if (guidePreviewAccept?.disabled) return;
      // La revision cuenta solo cuando la persona vio el documento y lo acepto.
      syncGuideFieldsFromEditor();
      guidePreviewSignature = currentGuideSignature();
      if (guideConfirmation) {
        guideConfirmation.disabled = false;
        guideConfirmation.checked = true;
      }
      guideBuilder.classList.add('is-reviewed');
      guideFinalReview.classList.add('is-reviewed');
      if (guideError) guideError.hidden = true;
      if (guideFinalError) guideFinalError.hidden = true;
      closeGuidePreview();
    });
    // Contenido listo para incluir: opciones detalladas que la persona decide
    // agregar o no. {practica}, {asignatura}, {recursos} y {laboratorio} se
    // reemplazan con los datos de la solicitud al insertar.
    const GUIDE_SNIPPETS = {
      guia_resultado_aprendizaje: [
        { label: gettext('Según tu descripción'), text: 'Al finalizar {practica} el estudiante alcanza lo planteado en la reserva: {intencion}' },
        { label: gettext('Procedimental'), text: 'Ejecuta {practica} aplicando el procedimiento establecido, las normas de seguridad y el uso correcto de {recursos}, registrando los datos con rigor y trazabilidad.' },
        { label: gettext('Analítico'), text: 'Analiza e interpreta los resultados obtenidos en {practica}, contrastándolos con el fundamento teórico de {asignatura} y argumentando las desviaciones observadas.' },
        { label: gettext('Actitudinal'), text: 'Trabaja en equipo con responsabilidad, puntualidad y cuidado del laboratorio, comunicando novedades y respetando los protocolos de la unidad.' }
      ],
      guia_objetivos: [
        { label: gettext('Según tu descripción'), text: 'Lograr lo planteado para {practica}: {intencion}' },
        { label: gettext('Objetivo general'), text: 'Desarrollar {practica} en el laboratorio para relacionar los conceptos de {asignatura} con la operación real de {recursos}.' },
        { label: gettext('Específicos · operación'), text: 'Identificar las partes, parámetros y condiciones de operación de {recursos}.\nConfigurar y verificar {recursos} antes de iniciar la práctica.' },
        { label: gettext('Específicos · datos'), text: 'Registrar mediciones u observaciones en tablas de datos con sus unidades.\nComparar los resultados con los valores esperados y explicar las diferencias.' },
        { label: gettext('Específicos · informe'), text: 'Elaborar el informe de práctica con evidencias, cálculos, conclusiones y referencias.' }
      ],
      guia_fundamento_teorico: [
        { label: gettext('Marco conceptual'), text: '## Marco conceptual\nDescribe los conceptos, leyes o modelos de {asignatura} que sustentan {practica} y cómo se relacionan con lo que se observará en el laboratorio.' },
        { label: gettext('Principio de funcionamiento'), text: '## Principio de funcionamiento del equipo\nExplica cómo opera {recursos}: variables que controla, rangos de trabajo, precisión y limitaciones que deben considerarse al interpretar los resultados.' },
        { label: gettext('Variables y parámetros (tabla)'), text: '## Variables y parámetros\n| Variable | Símbolo | Unidad | Rango de trabajo |\n| Variable independiente | x | — | — |\n| Variable dependiente | y | — | — |' },
        { label: gettext('Normativa aplicable'), text: '## Normativa y referencias técnicas\nIndica las normas técnicas, fichas de seguridad o manuales del fabricante que aplican a esta práctica (por ejemplo, normas INEN, ISO o instructivos internos de la unidad).' }
      ],
      guia_medidas_seguridad: [
        { label: gettext('Equipo de protección'), text: 'Usar el equipo de protección personal requerido para esta práctica (bata, gafas, guantes o calzado cerrado) durante toda la sesión.' },
        { label: gettext('Riesgo eléctrico o mecánico'), text: 'Verificar conexiones, guardas y paradas de emergencia de {recursos} antes de energizar; no intervenir partes móviles o energizadas sin autorización del laboratorista.' },
        { label: gettext('Sustancias y materiales'), text: 'Revisar la ficha de seguridad de cada sustancia o material, manipularlos con las herramientas indicadas y rotular los recipientes; nunca pipetear con la boca ni consumir alimentos en el área.' },
        { label: gettext('Emergencias'), text: 'Ubicar el extintor, el botiquín, la ducha o lavaojos y la salida de emergencia; ante cualquier incidente, detener la actividad y avisar de inmediato al responsable de la unidad.' }
      ],
      guia_procedimiento: [
        { label: gettext('Preparación previa'), text: 'Revisar la guía, el fundamento teórico y las medidas de seguridad antes de ingresar al laboratorio.\nVerificar que el área, los materiales y {recursos} estén disponibles y en condiciones de uso.' },
        { label: gettext('Calibración y verificación'), text: 'Encender {recursos} y esperar su estabilización según el manual.\nCalibrar o verificar el equipo con el patrón o procedimiento indicado y registrar el resultado.' },
        { label: gettext('Ejecución y registro'), text: 'Ejecutar la actividad siguiendo el orden indicado y registrar cada medición u observación en la tabla de datos.\nRepetir las mediciones críticas al menos tres veces y anotar las condiciones ambientales relevantes.' },
        { label: gettext('Tabla de registro de datos'), text: '| N.º | Condición o muestra | Medición 1 | Medición 2 | Medición 3 | Promedio | Observaciones |\n| 1 | | | | | | |\n| 2 | | | | | | |\n| 3 | | | | | | |' },
        { label: gettext('Cierre y limpieza'), text: 'Apagar y limpiar {recursos}, ordenar el área y disponer los residuos según la política de la unidad.\nEntregar el área al responsable, reportar novedades y registrar la salida.' }
      ],
      guia_resultados_esperados: [
        { label: gettext('Informe de práctica'), text: 'Informe de práctica con datos registrados, cálculos, gráficas, análisis de resultados, conclusiones y referencias en formato IEEE.' },
        { label: gettext('Tabla de datos y gráficas'), text: 'Tabla de datos completa con unidades y promedios, y gráficas de las variables medidas con su interpretación.' },
        { label: gettext('Producto o archivo'), text: 'Producto físico o archivo digital resultante de {practica} (pieza, muestra, modelo o código), identificado y entregado al responsable.' },
        { label: gettext('Evidencias'), text: 'Fotografías o capturas del montaje, del proceso y del resultado, con fecha y responsable.' }
      ],
      guia_criterios_evaluacion: [
        { label: gettext('Rúbrica base (100 %)'), text: 'Preparación y conocimiento previo de la práctica: 10 %.\nCumplimiento del procedimiento y de las medidas de seguridad: 30 %.\nCalidad y trazabilidad de los datos registrados: 20 %.\nAnálisis de resultados y conclusiones: 30 %.\nOrden, limpieza y entrega del área y los recursos: 10 %.' },
        { label: gettext('Trabajo en equipo'), text: 'Participación equitativa, comunicación efectiva y cumplimiento de roles dentro del equipo.' },
        { label: gettext('Informe'), text: 'Estructura completa del informe, coherencia entre datos y conclusiones, y uso correcto de referencias.' }
      ]
    };

    function guideSnippetContext() {
      const automatic = guideAutomaticValues();
      const resources = [automatic.equipment, automatic.software]
        .filter((value) => value && value !== 'No aplica' && !/^Se seleccionar/i.test(value))
        .join(' y ');
      return {
        practica: automatic.activity === 'Actividad por identificar' ? gettext('la práctica') : automatic.activity,
        asignatura: guideSubjectInput?.value.trim() || 'la asignatura',
        recursos: resources || 'los equipos del laboratorio',
        laboratorio: automatic.laboratory,
        intencion: intentSummary()
      };
    }

    form.addEventListener('input', (event) => {
      if (guidePreviewSignature
        && event.target !== guideConfirmation
        && event.target.id !== 'aceptarTerminos') invalidateGuidePreview();
    });
    form.addEventListener('change', (event) => {
      if (guidePreviewSignature
        && event.target !== guideConfirmation
        && event.target.id !== 'aceptarTerminos') invalidateGuidePreview();
    });

    function showValidationMessage(container, message, focusTarget) {
      if (container) {
        container.textContent = message;
        container.hidden = false;
        container.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      }
      if (focusTarget && !focusTarget.disabled && focusTarget.type !== 'hidden') focusTarget.focus?.();
      return false;
    }

    function showTechnicalFileError(message) {
      if (technicalFiles) {
        technicalFiles.hidden = false;
        technicalFiles.classList.add('is-required', 'has-validation-error');
      }
      if (serviceScope) serviceScope.classList.add('has-selected-mode');
      if (technicalFileRequirement) technicalFileRequirement.textContent = message;
      if (technicalFileStatus && !technicalFileInput?.files?.length) {
        technicalFileStatus.hidden = false;
        technicalFileStatus.dataset.state = 'error';
        technicalFileStatus.innerHTML = window.interfaz.html`<i class="fas fa-exclamation-circle" aria-hidden="true"></i><span><strong>Falta cargar el archivo del modelo</strong><small>Selecciona o arrastra el archivo en el recuadro anterior para continuar.</small></span>`;
      }
      if (resourceValidationMessage) resourceValidationMessage.hidden = true;
      technicalFiles?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      technicalFileDropZone?.focus?.({ preventScroll: true });
      return false;
    }

    function showCalendarSelectionError() {
      if (state.type === 'servicio' && proposalBox) {
        proposalBox.innerHTML = window.interfaz.html`<p class="is-error"><i class="fas fa-exclamation-circle" aria-hidden="true"></i> Pide una propuesta de fecha y acéptala, o elige una fecha y un bloque horario en el calendario.</p>`;
        proposalBox.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      }
      // El resumen vive en la barra de la agenda semanal; el panel antiguo
               // estaba oculto y el aviso no llegaba a verse.
      const selectionSummary = form.querySelector('[data-calendar-selection-summary]');
      selectionSummary?.classList.add('has-validation-error');
      return showValidationMessage(
        resourceValidationMessage,
        'Selecciona una fecha y al menos un bloque horario disponible para continuar.',
        null,
      );
    }

    function hasCalendarSelection() {
      let hours = [];
      try {
        hours = JSON.parse(element('horasSeleccionadas')?.value || '[]');
      } catch (_error) {
        hours = [];
      }
      return Boolean(element('fechaInicio')?.value
        && element('fechaFin')?.value
        && Array.isArray(hours)
        && hours.length);
    }

    function showParticipantRequirement() {
      resourceValidationMessage.hidden = true;
      showStep(2, true);
      participantsContainer?.classList.add('has-validation-error');
      let message = participantsContainer?.querySelector('[data-participant-requirement-error]');
      if (!message && participantsContainer) {
        message = create('div', 'reservation-participants__error');
        message.dataset.participantRequirementError = 'true';
        message.setAttribute('role', 'alert');
        message.innerHTML = window.interfaz.html`<i class="fas fa-exclamation-circle" aria-hidden="true"></i><span><strong>Agrega al menos un estudiante o participante</strong><small>Para programar una actividad docente semanal o durante todo el período, busca aquí una persona registrada, selecciónala y luego vuelve a “Recursos y calendario”.</small></span>`;
        participantsContainer.insertBefore(message, participantSearch?.closest('label') || null);
      }
      window.requestAnimationFrame(() => {
        participantsContainer?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
        participantSearch?.focus?.({ preventScroll: true });
      });
      return false;
    }

    // ------------------------------------------------------------------
    // El cronograma por sesión. La primera sesión toma el proceso del
    // contexto; en las demás la persona dice la práctica, el proceso y la
    // materia prima. Cada sesión nace con lo que su proceso exige y se
    // completa después desde «Mis sesiones programadas».
    function scheduleApplies() {
      return Boolean(schedulePlan) && state.type !== 'servicio' && selectedFrequency() !== 'unica';
    }
    function scheduleTopics() {
      const topics = [];
      (Array.isArray(subjectCatalog) ? subjectCatalog : []).forEach((subject) => {
        (Array.isArray(subject.temas) ? subject.temas : []).forEach((topic) => {
          topics.push({ id: topic.id, nombre: String(topic.nombre || ''), orden: topic.orden, asignatura: subject.nombre });
        });
      });
      return topics;
    }
    function scheduleProcessOptions() {
      return processSelect
        ? Array.from(processSelect.options).filter((option) => option.dataset.recipeId)
        : [];
    }
    function scheduleRowValues(fecha) {
      return scheduleState.filas.get(fecha) || { tema: '', receta_id: '', cantidad: '' };
    }
    function scheduleContextRow() {
      const option = selectedProcessOption();
      return {
        receta_id: option ? option.dataset.recipeId : '',
        cantidad: option ? String(processScaleInput?.value || option.dataset.base || '') : '',
        unidad: option ? String(option.dataset.unidadBase || '') : '',
        nombre: option ? option.textContent.trim() : gettext('Sin proceso definido'),
      };
    }
    function scheduleSlotHours() {
      try { return JSON.parse(element('horasSeleccionadas')?.value || '[]').length; } catch (error) { return 0; }
    }
    function syncScheduleInput() {
      if (!scheduleInput) return;
      if (!scheduleApplies() || !scheduleState.fechas.length) { scheduleInput.value = ''; return; }
      const topics = scheduleTopics();
      const contexto = scheduleContextRow();
      scheduleInput.value = JSON.stringify(scheduleState.fechas.map((sesion, index) => {
        const values = scheduleRowValues(sesion.fecha);
        const tema = String(values.tema || '').trim();
        const topic = topics.find((item) => item.nombre.trim().toLowerCase() === tema.toLowerCase());
        return {
          fecha: sesion.fecha,
          tema,
          tema_id: topic ? topic.id : null,
          receta_id: index === 0 ? (contexto.receta_id || null) : (values.receta_id || null),
          cantidad: index === 0 ? contexto.cantidad : String(values.cantidad || ''),
        };
      }));
    }
    function scheduleSummarySuffix() {
      if (!scheduleApplies() || !scheduleState.fechas.length) return '';
      const contexto = scheduleContextRow();
      const conProceso = scheduleState.fechas.filter((sesion, index) => (
        index === 0 ? Boolean(contexto.receta_id) : Boolean(scheduleRowValues(sesion.fecha).receta_id)
      )).length;
      return ` · ${scheduleState.fechas.length} sesiones en el cronograma, ${conProceso} con proceso definido`;
    }
    function renderScheduleRows() {
      if (!schedulePlan || !scheduleRows) return;
      const applies = scheduleApplies();
      schedulePlan.hidden = !applies;
      if (!applies || !scheduleState.fechas.length) {
        scheduleRows.innerHTML = '';
        if (scheduleInput) scheduleInput.value = '';
        return;
      }
      const topics = scheduleTopics();
      const listId = topics.length ? 'temasCronogramaReserva' : '';
      const datalist = topics.length
        ? window.interfaz.html`<datalist id="${listId}">${topics.map((topic) => window.interfaz.html`<option value="${escapeHtml(topic.nombre)}">${escapeHtml(`${topic.asignatura} · semana ${topic.orden}`)}</option>`).join('')}</datalist>`
        : '';
      const options = scheduleProcessOptions();
      const contexto = scheduleContextRow();
      const required = processRequired();
      scheduleRows.innerHTML = datalist + scheduleState.fechas.map((sesion, index) => {
        const values = scheduleRowValues(sesion.fecha);
        const selected = index === 0 ? null : options.find((option) => option.dataset.recipeId === String(values.receta_id || ''));
        const hasProcess = index === 0 ? Boolean(contexto.receta_id) : Boolean(selected);
        const unidad = index === 0 ? contexto.unidad : (selected ? String(selected.dataset.unidadBase || '') : '');
        const processCell = index === 0
          ? window.interfaz.html`<strong class="reservation-schedule-plan__fixed">${escapeHtml(contexto.nombre)}</strong><small>Se define en el paso anterior.</small>`
          : window.interfaz.html`<select class="form-control" data-schedule-field="receta_id"><option value="">Sin proceso definido</option>${options.map((option) => window.interfaz.html`<option value="${escapeHtml(option.dataset.recipeId)}"${selected === option ? ' selected' : ''}>${escapeHtml(option.textContent.trim())}</option>`).join('')}</select>`;
        const quantityCell = index === 0
          ? window.interfaz.html`<strong class="reservation-schedule-plan__fixed">${escapeHtml(contexto.cantidad)}</strong>`
          : window.interfaz.html`<input type="number" class="form-control" data-schedule-field="cantidad" min="0.001" step="0.001" value="${escapeHtml(String(values.cantidad || ''))}">`;
        return window.interfaz.html`<div class="reservation-schedule-plan__row${index === 0 ? ' is-context' : ''}" data-schedule-row="${escapeHtml(sesion.fecha)}">
            <div class="reservation-schedule-plan__when"><strong>Sesión ${sesion.numero}</strong><small>${escapeHtml(sesion.fecha_texto || sesion.fecha)}${sesion.semana ? ` · semana ${sesion.semana}` : ''}</small></div>
            <label><span>Práctica${required ? ' *' : ''}</span><input type="text" class="form-control" data-schedule-field="tema"${listId ? ` list="${listId}"` : ''} maxlength="240" placeholder="Qué se hará en esta sesión" value="${escapeHtml(String(values.tema || ''))}"></label>
            <label><span>Proceso</span>${processCell}</label>
            <label${hasProcess ? '' : ' hidden'}><span>Materia prima${unidad ? ` (${escapeHtml(unidad)})` : ''}</span>${quantityCell}</label>
            <small class="reservation-schedule-plan__note" data-schedule-note></small>
          </div>`;
      }).join('');
      syncScheduleInput();
      scheduleState.fechas.forEach((sesion, index) => { if (index > 0) describeScheduleRow(sesion.fecha); });
    }
    async function describeScheduleRow(fecha) {
      const row = scheduleRows?.querySelector(`[data-schedule-row="${fecha}"]`);
      const note = row?.querySelector('[data-schedule-note]');
      if (!row || !note) return;
      const values = scheduleRowValues(fecha);
      const option = scheduleProcessOptions().find((item) => item.dataset.recipeId === String(values.receta_id || ''));
      note.classList.remove('is-warning');
      if (!option) {
        note.textContent = gettext('Sin proceso, la sesión conserva las áreas, los equipos y los insumos pedidos en el paso de recursos.');
        return;
      }
      const base = Number(option.dataset.base) || 1;
      const cantidad = Number(values.cantidad) || base;
      const factor = Math.max(0.001, Math.round((cantidad / base) * 1000) / 1000);
      const personas = selectedParticipants.size + 1;
      const key = `${option.dataset.recipeId}:${factor}:${personas}`;
      if (!scheduleDescriptions.has(key)) {
        const template = processField?.dataset.selectionUrlTemplate || '';
        if (!template) return;
        const url = new URL(template.replace('/0/', `/${option.dataset.recipeId}/`), window.location.href);
        url.searchParams.set('factor', String(factor));
        url.searchParams.set('personas', String(personas));
        let data = null;
        try {
          const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
          data = await response.json().catch(() => null);
          if (!response.ok) data = null;
        } catch (error) {
          data = null;
        }
        scheduleDescriptions.set(key, data);
      }
      const data = scheduleDescriptions.get(key);
      if (!data || !data.success || scheduleRowValues(fecha).receta_id !== option.dataset.recipeId) { note.textContent = ''; return; }
      const horas = ((data.sesion || {}).horas || []).length;
      const slot = scheduleSlotHours();
      note.textContent = `${data.escala} → ${data.producto_esperado} · ${data.espacios.length} áreas, ${data.equipos.length} equipos, ${data.insumos.length} insumos · corrida de ${horas} h`;
      if (slot && horas > slot) {
        note.classList.add('is-warning');
        note.textContent += ` (la sesión tiene ${slot} h: elige una hora de inicio que cubra la corrida o ajusta la materia prima)`;
      }
    }
    function refreshSchedulePlan() {
      if (!schedulePlan) return;
      if (!scheduleApplies()) {
        scheduleState.fechas = [];
        scheduleState.key = '';
        renderScheduleRows();
        return;
      }
      const fecha = (element('fechaInicio')?.value || '').slice(0, 10);
      const frequency = selectedFrequency();
      const fin = frequency === 'semanal_rango' ? (frequencyRangeEnd?.value || '') : '';
      if (!fecha || (frequency === 'semanal_rango' && !fin)) {
        scheduleState.fechas = [];
        scheduleState.key = '';
        renderScheduleRows();
        schedulePlan.hidden = false;
        if (scheduleStatus) {
          scheduleStatus.textContent = fecha
            ? gettext('Indica la fecha final de la serie para ver las sesiones.')
            : gettext('Elige el primer día en la agenda para ver las sesiones.');
        }
        return;
      }
      const key = `${fecha}|${frequency}|${fin}`;
      if (scheduleState.key === key) { schedulePlan.hidden = false; return; }
      scheduleState.key = key;
      window.clearTimeout(scheduleState.timer);
      scheduleState.timer = window.setTimeout(() => fetchSchedulePlan(fecha, frequency, fin), 150);
    }
    async function fetchSchedulePlan(fecha, frequency, fin) {
      const sequence = scheduleState.sequence + 1;
      scheduleState.sequence = sequence;
      const url = new URL(schedulePlan.dataset.fechasUrl || '', window.location.href);
      url.searchParams.set('unidad', schedulePlan.dataset.unidad || '');
      url.searchParams.set('fecha', fecha);
      url.searchParams.set('frecuencia', frequency);
      if (fin) url.searchParams.set('fin', fin);
      schedulePlan.hidden = false;
      if (scheduleStatus) scheduleStatus.textContent = gettext('Calculando las sesiones del período…');
      let data = null;
      try {
        const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        data = await response.json().catch(() => null);
      } catch (error) {
        data = null;
      }
      if (sequence !== scheduleState.sequence) return;
      if (!data || !data.success) {
        scheduleState.fechas = [];
        scheduleState.key = '';
        renderScheduleRows();
        schedulePlan.hidden = !scheduleApplies();
        if (scheduleStatus) scheduleStatus.textContent = (data && data.error) || 'No fue posible calcular las sesiones. Intenta de nuevo.';
        return;
      }
      scheduleState.fechas = Array.isArray(data.sesiones) ? data.sesiones : [];
      scheduleState.periodo = data.periodo || '';
      scheduleState.omitidas = Array.isArray(data.omitidas) ? data.omitidas : [];
      if (scheduleStatus) {
        const omitidas = scheduleState.omitidas.length;
        scheduleStatus.textContent = `${scheduleState.fechas.length} sesiones${scheduleState.periodo ? ` en ${scheduleState.periodo}` : ''}${omitidas ? ` · ${omitidas} semana${omitidas === 1 ? '' : 's'} sin reservas omitida${omitidas === 1 ? '' : 's'}` : ''}.`;
      }
      renderScheduleRows();
      updateSummary();
    }
    function onScheduleEdit(event) {
      const field = event.target?.closest?.('[data-schedule-field]');
      const row = event.target?.closest?.('[data-schedule-row]');
      if (!field || !row) return;
      const fecha = row.dataset.scheduleRow;
      const values = { ...scheduleRowValues(fecha) };
      values[field.dataset.scheduleField] = field.value;
      if (field.dataset.scheduleField === 'receta_id') {
        const option = scheduleProcessOptions().find((item) => item.dataset.recipeId === field.value);
        values.cantidad = option ? String(option.dataset.base || '') : '';
        scheduleState.filas.set(fecha, values);
        renderScheduleRows();
        updateSummary();
        return;
      }
      scheduleState.filas.set(fecha, values);
      syncScheduleInput();
      if (field.dataset.scheduleField === 'cantidad' && event.type === 'change') describeScheduleRow(fecha);
      updateSummary();
    }
    function validateSchedulePlan() {
      if (!scheduleApplies()) return true;
      if (!scheduleState.fechas.length) {
        return showValidationMessage(
          resourceValidationMessage,
          'La unidad aún no calculó las sesiones de la programación: revisa la primera fecha y la modalidad semanal.',
          frequencyRangeEnd && !frequencyRangeEnd.disabled ? frequencyRangeEnd : null
        );
      }
      const required = processRequired();
      for (let index = 0; index < scheduleState.fechas.length; index += 1) {
        const sesion = scheduleState.fechas[index];
        const values = scheduleRowValues(sesion.fecha);
        const row = scheduleRows?.querySelector(`[data-schedule-row="${sesion.fecha}"]`);
        if (required && !String(values.tema || '').trim()) {
          return showValidationMessage(
            resourceValidationMessage,
            `Indica qué práctica harás en la sesión ${sesion.numero} (${sesion.fecha_texto || sesion.fecha}).`,
            row?.querySelector('[data-schedule-field="tema"]')
          );
        }
        if (index > 0 && values.receta_id && !(Number(values.cantidad) > 0)) {
          return showValidationMessage(
            resourceValidationMessage,
            `Indica la materia prima de la sesión ${sesion.numero} (${sesion.fecha_texto || sesion.fecha}).`,
            row?.querySelector('[data-schedule-field="cantidad"]')
          );
        }
      }
      return true;
    }
    if (scheduleRows) {
      scheduleRows.addEventListener('input', onScheduleEdit);
      scheduleRows.addEventListener('change', onScheduleEdit);
    }
    processSelect?.addEventListener('change', () => { renderScheduleRows(); updateSummary(); });
    processScaleInput?.addEventListener('input', () => renderScheduleRows());
    frequencyRangeEnd?.addEventListener('change', refreshSchedulePlan);

    function validateStep(step) {
      if (state.type !== 'visita' && element('btnEnviarReserva')?.dataset.authenticated === 'false') {
        return showValidationMessage(intentionValidationMessage, gettext('Inicia sesión para reservar recursos o solicitar servicios.'));
      }
      if (state.type === 'visita') return visitFlow.validate(step);
      if (step >= 3 && !consumablesWithinStock()) {
        return showValidationMessage(
          resourceValidationMessage,
          'Hay insumos con una cantidad mayor a la existencia disponible. Ajusta la cantidad antes de continuar.',
          form.querySelector('.reservation-consumable.is-over-stock .reservation-consumable__quantity')
        );
      }
      if (step >= 3) {
        const insumoSinCantidad = consumableWithoutQuantity();
        if (insumoSinCantidad) {
          const campo = insumoSinCantidad.querySelector('.reservation-consumable__quantity');
          return showValidationMessage(
            resourceValidationMessage,
            `Indica cuánto vas a usar de ${campo?.dataset.consumibleNombre || 'cada insumo'}: sin la cantidad, el valor estimado queda incompleto.`,
            campo
          );
        }
      }
      if (step === 1) {
        intentionValidationMessage.hidden = true;
        if (!['recursos', 'servicio', 'visita'].includes(state.type)) {
          return showValidationMessage(
            intentionValidationMessage,
            'Elige quién realizará el trabajo para continuar por la ruta correcta.',
            types.querySelector('[data-type]')
          );
        }
      }

      if (step === 2) {
        dataValidationMessage.hidden = true;
        // Servicio: solo la descripcion del trabajo; sin clasificacion ni participantes.
        if (state.type === 'servicio') return validateIntent();
        if (form.querySelector('[name="proposito_codigo"]') && !selectedPurpose()) {
          return showValidationMessage(
            dataValidationMessage,
            'Selecciona el propósito de la solicitud antes de continuar.',
            form.querySelector('[name="proposito_codigo"]')
          );
        }
        if (subtypeSelect && !subtypeSelect.value) {
          return showValidationMessage(
            dataValidationMessage,
            'Selecciona el tipo concreto de actividad que se realizará.',
            subtypeSelect
          );
        }
        if (processRequired() && !processSelect.value) {
          return showValidationMessage(
            dataValidationMessage,
            'Indica qué producto vas a realizar o elige «Uso de recursos sin un producto definido».',
            processSelect
          );
        }
        if (selectedProcessOption() && !(Number(processScaleInput?.value) > 0)) {
          return showValidationMessage(
            dataValidationMessage,
            'Indica la materia prima que procesarás; la planta calcula el resto desde el proceso.',
            processScaleInput
          );
        }
        const beneficiaryScope = form.querySelector('[name="alcance_beneficiario"]:checked')?.value;
        if (!beneficiaryScope) {
          return showValidationMessage(
            dataValidationMessage,
            'Indica para quién se realizará la actividad.',
            form.querySelector('[name="alcance_beneficiario"]')
          );
        }
        const beneficiaryCareer = form.querySelector('[name="carrera_beneficiaria"]');
        if (beneficiaryScope === 'otra_carrera' && !beneficiaryCareer?.value) {
          return showValidationMessage(
            dataValidationMessage,
            'Selecciona la carrera UPEC beneficiaria de la actividad.',
            beneficiaryCareer
          );
        }
        const beneficiaryEntity = form.querySelector('[name="entidad_beneficiaria"]');
        if (['dependencia_upec', 'proyecto_centro', 'externo'].includes(beneficiaryScope)
          && !beneficiaryEntity?.value.trim()) {
          return showValidationMessage(
            dataValidationMessage,
            'Identifica la dependencia, proyecto, centro, institución o comunidad beneficiaria.',
            beneficiaryEntity
          );
        }
        const purpose = selectedPurpose();
        const needsReference = state.type !== 'servicio'
          && Object.prototype.hasOwnProperty.call(referenceLabels, purpose);
        const activityLink = selectedActivityLink();
        const curricularPractice = purpose === 'docencia_practica' && state.type !== 'servicio';
        if (needsReference && !activityLink) {
          return showValidationMessage(
            dataValidationMessage,
            curricularPractice && reservationUserType === 'estudiante'
              ? gettext('Esta actividad docente requiere una guía aprobada. Solicita al docente responsable que la publique o asigne antes de reservar.')
              : gettext('Indica si la actividad utilizará una guía de práctica.'),
            activityLinkInputs[0]
          );
        }
        if (curricularPractice && activityLink === 'independiente') {
          return showValidationMessage(
            dataValidationMessage,
            'Toda actividad docente debe vincular una guía aprobada o crear una guía nueva al final de la solicitud.',
            activityLinkInputs.find((input) => input.value === 'catalogo')
          );
        }
        if (!validateIntent()) return false;
        if (activityLink === 'manual' && !canAuthorGuides) {
          return showValidationMessage(
            dataValidationMessage,
            'Tu perfil no puede crear guías. Los estudiantes deben seleccionar una guía institucional aprobada.',
            activityLinkInputs.find((input) => input.value === 'catalogo')
          );
        }
        if (needsReference && activityLink === 'catalogo' && !activityCatalog?.value) {
          return showValidationMessage(
            dataValidationMessage,
            'Selecciona una actividad publicada en el catálogo institucional.',
            activityCatalog
          );
        }
        if (curricularPractice && activityLink === 'catalogo'
          && activityCatalog?.selectedOptions?.[0]?.dataset.hasGuides !== 'true') {
          return showValidationMessage(
            dataValidationMessage,
            'La actividad seleccionada no tiene una guía institucional aprobada y vigente.',
            activityCatalog
          );
        }
        const otherPurpose = form.querySelector('[name="detalle_otro_proposito"]');
        if (purpose === 'otro' && (otherPurpose?.value.trim().length || 0) < 10) {
          return showValidationMessage(
            dataValidationMessage,
            'Explica brevemente el propósito institucional de la solicitud.',
            otherPurpose
          );
        }
        updateAutomaticTitle();
      }

      if (step === 3 && element('fechaInicio')?.value && !validateSchedulePlan()) return false;
      if (step === 3) {
        resourceValidationMessage.hidden = true;
        if (state.type === 'recursos' && !cascadeHasAnyResource()) {
          return showValidationMessage(
            resourceValidationMessage,
            resourceAvailability.espacio
              ? gettext('Selecciona dónde vas a trabajar para continuar.')
              : gettext('Selecciona al menos un equipo o software para continuar.'),
            spaceInputs.find((input) => !input.disabled) || form.querySelector('.unidad-checkbox:not(:disabled)')
          );
        }
        if (selectedFrequency() === 'semanal_rango' && !frequencyRangeEnd?.value) {
          return showValidationMessage(
            resourceValidationMessage,
            'Selecciona la fecha hasta la que se repetirá la reserva semanal.',
            frequencyRangeEnd
          );
        }
        if (selectedFrequency() !== 'unica'
          && selectedPurpose() === 'docencia_practica'
          && !selectedParticipants.size) {
          return showParticipantRequirement();
        }
        if (state.type === 'servicio') {
          const selectedServices = selectedServiceInputs();
          if (!selectedServices.length) {
            return showValidationMessage(
              resourceValidationMessage,
              serviceInputs.length
                ? gettext('Selecciona el servicio técnico que necesitas.')
                : gettext('Este laboratorio todavía no ha publicado servicios que puedan solicitarse.'),
              serviceInputs[0]
            );
          }
          const selectedMode = serviceModes.find((input) => input.checked && !input.disabled);
          if (!selectedMode) {
            return showValidationMessage(resourceValidationMessage, 'Selecciona una modalidad compatible para definir cómo se realizará el servicio.', serviceModes.find((input) => !input.disabled));
          }
          const requiresFiles = selectedMode.value === 'modelo_listo' && selectedServices.some((input) => (
            input.closest('.reservation-service')?.dataset.requiresFiles === 'true'
          ));
          if (requiresFiles && !technicalFileInput?.files?.length) {
            const formats = selectedServices
              .map((input) => input.closest('.reservation-service')?.dataset.formats)
              .filter(Boolean)
              .join(' · ');
            return showTechnicalFileError(`Para “Entrego el modelo listo” debes cargar al menos un archivo técnico${formats ? ` (${formats})` : ''}. Las otras modalidades permiten continuar sin adjuntos.`);
          }
          if (piecesInput && !(Number.parseInt(piecesInput.value, 10) > 0)) {
            return showValidationMessage(resourceValidationMessage, `Indica ${trabajoEsFemenino() ? gettext('cuántas') : gettext('cuántos')} ${palabraTrabajo(true)} necesitas (al menos ${trabajoEsFemenino() ? 'una' : 'uno'}).`, piecesInput);
          }
          if (!serviceMaterialsWithinStock()) {
            return showValidationMessage(
              resourceValidationMessage,
              'Hay materiales con una cantidad mayor a la existencia disponible. Ajusta la cantidad antes de continuar.',
              serviceMaterialsList?.querySelector('.is-over-stock .reservation-service-material__input')
            );
          }
          const sinCantidad = serviceMaterialWithoutQuantity();
          if (sinCantidad) {
            return showValidationMessage(
              resourceValidationMessage,
              `Indica cuánto vas a usar de ${sinCantidad.dataset.name || 'cada material'}: sin la cantidad, el valor estimado queda incompleto.`,
              sinCantidad.querySelector('.reservation-service-material__input')
            );
          }
        }

        const usesEquipment = resourceKindActive('equipo');
        const usesSpace = resourceKindActive('espacio');
        const usesSoftware = resourceKindActive('software');
        if (usesSpace && selectedSpaceScope() === 'areas'
          && spaceInputs.length && !spaceInputs.some((input) => input.checked && !input.disabled)) {
          const firstSpace = spaceInputs.find((input) => !input.disabled);
          const hasTechnicalOnlySpaces = spaceInputs.some((input) => (
            input.closest('.reservation-space-item')?.classList.contains('is-plan-incompatible')
          ));
          return showValidationMessage(
            resourceValidationMessage,
            firstSpace
              ? gettext('Selecciona al menos un área o estación de trabajo.')
              : hasTechnicalOnlySpaces
                ? gettext('Esta unidad solo tiene áreas técnicas para esta selección. Regresa al inicio y marca también Equipos o Software según lo que realmente utilizarás.')
                : gettext('No hay áreas o estaciones disponibles para reservar.'),
            firstSpace || primaryResourceChoices.querySelector('[data-resource-option="equipo"] input')
          );
        }
        if (usesEquipment && !form.querySelector('.unidad-checkbox:checked')) {
          const firstEquipment = form.querySelector('.unidad-checkbox:not(:disabled)');
          return showValidationMessage(
            resourceValidationMessage,
            firstEquipment ? gettext('Selecciona al menos un equipo concreto del catálogo.') : gettext('No hay equipos disponibles para el horario o la unidad seleccionada.'),
            firstEquipment
          );
        }
        if (usesSoftware && !softwareInputs.some((input) => input.checked && !input.disabled)) {
          const firstSoftware = softwareInputs.find((input) => !input.disabled);
          return showValidationMessage(
            resourceValidationMessage,
            firstSoftware ? gettext('Selecciona al menos un software o una licencia del catálogo.') : gettext('No hay software ni licencias disponibles para reservar.'),
            firstSoftware
          );
        }
        if (usesSoftware && !validateSoftwareEquipmentSelection()) return false;
        if (usesEquipment && !validateEquipmentSpaceSelection()) return false;
        syncScopeNotice();
        if (spaceOnlySelection() && scopeConfirm && !scopeConfirm.checked) {
          return showValidationMessage(
            resourceValidationMessage,
            'Revisa lo que vas a solicitar y confirma que solo necesitas el espacio.',
            scopeConfirm
          );
        }
        if (!hasCalendarSelection()) {
          return showCalendarSelectionError();
        }
      }

      if (step === 4) {
        if (finalActivityError) finalActivityError.hidden = true;
        const purpose = selectedPurpose();
        const activityLink = selectedActivityLink();
        if (activityLink === 'manual' && !activityReferenceInput?.value.trim()) {
          return showValidationMessage(
            finalActivityError,
            'Confirma el nombre sugerido o escribe el nombre de la práctica.',
            activityReferenceInput
          );
        }
        if (activityLink === 'manual' && /\[[^\]]*\]/.test(activityReferenceInput?.value || '')) {
          return showValidationMessage(
            finalActivityError,
            'Reemplaza los corchetes del patrón por el contenido real de tu práctica.',
            activityReferenceInput
          );
        }
        if (guideIsRequired() && !guideSubjectInput?.value.trim()) {
          return showValidationMessage(
            finalActivityError,
            'Escribe la asignatura o módulo al que pertenece la práctica.',
            guideSubjectInput
          );
        }
        if (purpose === 'docencia_practica' && activityLink === 'manual'
          && activityReferenceInput?.value.trim().length > 120) {
          return showValidationMessage(
            finalActivityError,
            'El nombre corto de la actividad o guía admite hasta 120 caracteres.',
            activityReferenceInput
          );
        }
        const programmingOrigin = form.querySelector('[name="origen_programacion"]:checked');
        if (purpose === 'docencia_practica' && activityLink !== 'independiente' && !programmingOrigin) {
          return showValidationMessage(
            finalActivityError,
            'Indica si la práctica ya estaba prevista en la planificación de la asignatura o si se agregó después.',
            form.querySelector('[name="origen_programacion"]')
          );
        }
        if (!validateEmbeddedGuide()) return false;
        if (state.type === 'servicio') {
          if (!currentQuote) {
            if (quoteRecap) quoteRecap.innerHTML = '<p class="is-error">El valor estimado aún no está disponible; espera un momento o revisa los materiales en el paso anterior.</p>';
            scheduleServiceQuote();
            return false;
          }
          if (currentQuote.requiere_aceptacion && !paymentMethod?.value) {
            paymentMethod?.focus();
            paymentMethod?.reportValidity?.();
            return false;
          }
          if (currentQuote.requiere_aceptacion && !quoteAcceptance?.checked) {
            quoteAcceptance?.focus();
            quoteAcceptance?.reportValidity?.();
            return false;
          }
          return true;
        }
        const inventoryApplies = state.type === 'recursos'
          && (resourceKindActive('equipo') || resourceKindActive('espacio'));
        if (!inventoryApplies) return true;
        const invalidQuantity = consumableInputs.find((input) => {
          const card = input.closest('.reservation-consumable');
          const selected = card?.querySelector('.reservation-consumable__check')?.checked;
          // Vacia: la calcula el laboratorio en la revision.
          if (!selected || input.value.trim() === '') return false;
          const value = Number(input.value || 0);
          const maximum = Number(input.max || 0);
          return value <= 0 || (maximum > 0 && value > maximum);
        });
        if (invalidQuantity) {
          invalidQuantity.focus();
          invalidQuantity.reportValidity?.();
          return false;
        }
        syncConsumables();
      }
      if (step === 5 && element('aceptarTerminos') && !element('aceptarTerminos').checked) {
        element('aceptarTerminos').focus();
        element('aceptarTerminos').reportValidity?.();
        return false;
      }
      return true;
    }

    function showStep(nextStep, force) {
      const target = Math.max(1, Math.min(TOTAL_STEPS, Number(nextStep) || 1));
      if (!force && target > state.step && !validateStep(state.step)) return;
      state.step = target;
      panels.forEach((panel) => panel.classList.toggle('is-active', Number(panel.dataset.rwPanel) === target));
      shell.querySelectorAll('[data-rw-step]').forEach((button) => {
        const step = Number(button.dataset.rwStep);
        const isFutureStep = step > target + 1;
        button.disabled = isFutureStep;
        button.setAttribute('aria-disabled', String(isFutureStep));
        button.classList.toggle('is-active', step === target);
        button.classList.toggle('is-complete', step < target);
        button.querySelector('.rw-step__number').textContent = step < target ? '✓' : String(step);
      });
      if (target === 3 && state.type === 'visita') window.refreshCalendarAvailability?.();
      if (target === 3 && state.type !== 'visita' && processActive()) applyProcessMode();
      if (target === 4 && state.type !== 'visita') {
        if (state.type === 'servicio' && !currentQuote && quoteReady()) calculateServiceQuote();
        updateGuideBuilder();
        // La guia nace de la reserva: al llegar aqui ya viene propuesta y solo
        // se revisa. Nunca se sobrescribe lo que la persona escribio.
        if (guideIsRequired()) {
          ensureGuideEditor();
          if (guideMissingLabels().length) applyGuideSuggestions();
        }
      }
      if (target === 5) updateSummary();
      modal.querySelector('.modal-body')?.scrollTo({ top: 0, behavior: 'smooth' });
      if (target === 1) scheduleRouteFit();
    }

    types.addEventListener('click', (event) => {
      const button = event.target.closest('[data-type]');
      if (!button || button.disabled) return;
      state.type = button.dataset.type;
      requestType.value = state.type;
      types.querySelectorAll('[data-type]').forEach((item) => {
        item.setAttribute('aria-pressed', String(item === button));
        item.closest('[data-type-card]')?.classList.toggle('is-selected', item === button);
      });
      intentionValidationMessage.hidden = true;
      resourceValidationMessage.hidden = true;
      updateTypeUI();
      window.refreshCalendarAvailability?.();
    });

    shell.addEventListener('click', (event) => {
      const stepButton = event.target.closest('[data-rw-step]');
      if (stepButton) {
        const requested = Number(stepButton.dataset.rwStep);
        if (requested > state.step + 1) return;
        showStep(requested, requested < state.step);
        return;
      }
      const action = event.target.closest('[data-rw-action]')?.dataset.rwAction;
      if (action === 'previous') showStep(state.step - 1, true);
      if (action === 'next') showStep(state.step + 1);
      if (action === 'submit') {
        const externalGuestVisit = state.type === 'visita'
          && element('visitaDatosReserva')?.dataset.authenticated === 'false'
          && form.elements.visita_categoria?.value === 'externa';
        if (profileStatusKnown && !profileComplete && !externalGuestVisit) {
          profileMessage.hidden = false;
          requesterProfile?.classList.add('is-attention');
          showStep(2, true);
          requesterProfile?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return;
        }
        if (!validateStep(5)) return;
        updateSummary();
        const legacySubmit = element('btnEnviarReserva') || element('btnConfirmarEnvioReserva');
        if (legacySubmit) legacySubmit.click();
        else if (form.requestSubmit) form.requestSubmit();
      }
    });

    modal.addEventListener('shown.bs.modal', () => {
      updateTypeUI();
      renderAreaEquipmentSummaries();
      showStep(1, true);
    });
    modal.addEventListener('hidden.bs.modal', () => {
      closeActivityGuidePreview();
      closeGuidePreview();
    });
    renderAreaEquipmentSummaries();
    updateTypeUI();
    showStep(1, true);
    if (currentUrl.searchParams.get('reserva') === 'visita' && visitAvailable) {
      window.abrirModalEquipos?.();
      types.querySelector('[data-type="visita"]')?.click();
    }
  }

  ready(init);
})();
(function mountReservationModalsAtDocumentRoot() {
    const mountModals = () => {
        ["equiposReservaModal"].forEach((modalId) => {
            const modal = document.getElementById(modalId);
            if (modal && modal.parentElement !== document.body) {
                document.body.appendChild(modal);
            }
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mountModals, { once: true });
    } else {
        mountModals();
    }
})();
