(() => {
  'use strict';
  const form = document.querySelector('[data-certificado-editor]');
  if (!form) return;
  const save = form.querySelector('[data-guardar-diseno]');
  const token = form.querySelector('[data-previa-token]');
  const frame = document.querySelector('[data-previa-pdf]');
  const empty = document.querySelector('[data-previa-vacio]');
  const status = document.querySelector('[data-previa-estado]');
  const errors = document.querySelector('[data-previa-errores]');
  const errorText = document.querySelector('[data-previa-error-texto]');
  const retry = document.querySelector('[data-reintentar-previa]');
  const tools = document.querySelector('[data-previa-herramientas]');
  const link = document.querySelector('[data-descargar-previa]');
  const type = document.querySelector('[data-tipo-muestra]');
  const role = document.querySelector('[data-texto-rol]');
  const suggested = document.querySelector('[data-texto-sugerido]');
  const textModel = document.querySelector('[data-modelo-texto]');
  const design = form.elements.namedItem('diseno');
  const models = [...document.querySelectorAll('[data-diseno]')];
  const localImages = new Map();
  const selectedFiles = new WeakMap();
  let defaults = {};
  try { defaults = JSON.parse(document.getElementById('certificadoModelosTexto')?.textContent || '{}') || {}; } catch (_) { /* Custom texts remain editable. */ }
  let academicCatalog = {facultades: [], carreras: []};
  let institutionalPalette = {primario: '#006633', acento: '#ffce00'};
  try { academicCatalog = JSON.parse(document.getElementById('certificadoCatalogoAcademico')?.textContent || '{}') || academicCatalog; } catch (_) { /* Existing text fields remain available. */ }
  try { institutionalPalette = {...institutionalPalette, ...JSON.parse(document.getElementById('certificadoPaletaInstitucional')?.textContent || '{}')}; } catch (_) { /* Server validates the persisted hexadecimal values. */ }
  let revision = 0;
  let objectUrl = null;
  let visor = null;
  let active = true;
  let busy = false;
  let previewTimer = null;
  let previewSequence = 0;
  let previewJob = null;
  let acceptedRevision = -1;
  let acceptedStamp = '';
  let saving = false;
  let galleryEpoch = 0;
  let galleryJob = null;
  let galleryTimer = null;
  const visibleModels = new Set();
  const fileIds = new WeakMap();
  let fileSequence = 0;
  window.courseEditorDirty = false;
  window.courseEditorBusy = false;
  const stamp = () => JSON.stringify({
    fields: [...new FormData(form)].filter(([name]) => !['csrfmiddlewaretoken', 'vista_previa_token', '_panel'].includes(name)).map(([name, value]) =>
      [name, value instanceof File ? (value.name ? [value.name, value.size, value.type, value.lastModified] : null) : value]),
    files: [...form.querySelectorAll('input[type=file]')].map(input => [input.name, [...input.files].map(file => {
      if (!fileIds.has(file)) fileIds.set(file, ++fileSequence);
      return fileIds.get(file);
    })]),
    type: type.value
  });
  const downloadReady = ready => {
    tools.hidden = false;
    link.hidden = false;
    link.setAttribute('aria-disabled', String(!ready));
    link.tabIndex = ready ? 0 : -1;
    if (!ready) link.removeAttribute('href');
  };
  const discardJob = job => {
    if (!job) return;
    window.clearTimeout(job.timeout);
    job.controller.abort();
    if (job.stage) {
      window.VisorPdf?.desmontar(job.stage);
      job.stage.remove();
      job.stage = null;
    }
    job.mounted?.destruir();
    job.mounted = null;
    if (job.url) { URL.revokeObjectURL(job.url); job.url = null; }
  };
  const stopPendingPreview = () => {
    window.clearTimeout(previewTimer);
    previewTimer = null;
    const previous = previewJob;
    previewJob = null;
    discardJob(previous);
    busy = false;
    form.removeAttribute('aria-busy');
  };
  const destroyPreview = () => {
    visor?.destruir();
    visor = null;
    frame.replaceChildren();
    if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = null; }
    downloadReady(false);
  };
  const invalidate = event => {
    if (event?.target?.matches('[data-texto-rol], [data-modelo-texto]')) return;
    pauseGallery();
    if (event?.target !== design) resetGallery();
    revision += 1;
    previewSequence += 1;
    stopPendingPreview();
    if (event?.target && form.contains(event.target)) window.courseEditorDirty = true;
    acceptedRevision = -1;
    acceptedStamp = '';
    token.value = '';
    save.disabled = true;
    downloadReady(false);
    errors.hidden = true;
    if (event?.target) clearFieldError(event.target);
    status.textContent = 'Actualizando la vista previa…';
    schedulePreview(event?.type === 'input' ? 500 : event?.target === design ? 0 : 150);
  };
  const syncDesign = () => {
    models.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.diseno === design?.value)));
    const currentModel = document.querySelector('[data-modelo-actual]');
    const selectedModel = models.find(button => button.dataset.diseno === design?.value);
    if (currentModel) currentModel.textContent = models.length + ' modelos · ' + (selectedModel?.title || selectedModel?.querySelector('strong')?.textContent.trim() || 'Elige un diseño');
    const primary = form.elements.namedItem('color_primario')?.value || institutionalPalette.primario;
    const accent = form.elements.namedItem('color_acento')?.value || institutionalPalette.acento;
    document.querySelectorAll('.cert-editor__miniatura').forEach(item => {
      if (/^#[0-9a-f]{6}$/i.test(primary || '')) item.style.setProperty('--modelo-primario', primary);
      else item.style.removeProperty('--modelo-primario');
      if (/^#[0-9a-f]{6}$/i.test(accent || '')) item.style.setProperty('--modelo-acento', accent);
      else item.style.removeProperty('--modelo-acento');
      item.dataset.modo = 'claro';
    });
  };
  if (design && models.length) {
    models.forEach(button => {
      const label = button.querySelector('strong');
      if (!label) return;
      const fullLabel = button.title || label.textContent.trim();
      button.setAttribute('aria-label', fullLabel);
      label.textContent = button.dataset.diseno === 'clasico' ? 'Clásico' : fullLabel.split('·')[0].trim();
    });
    const native = document.querySelector('[data-diseno-nativo]');
    if (native) native.hidden = !native.querySelector('.errorlist');
    models.forEach(button => button.addEventListener('click', () => {
      if (design.value === button.dataset.diseno) { schedulePreview(0); return; }
      design.value = button.dataset.diseno;
      design.dispatchEvent(new Event('change', {bubbles: true}));
    }));
    design.addEventListener('change', syncDesign);
    syncDesign();
  }
  const hexColor = value => /^#[0-9a-f]{6}$/i.test(value || '');
  const syncColors = () => {
    const effective = {};
    [['color_primario', 'primario'], ['color_acento', 'acento'], ['color_texto', 'texto'], ['color_titulos', 'titulos']].forEach(([name, key]) => {
      const input = form.elements.namedItem(name);
      const value = input?.value || (key === 'texto' ? '#263d33' : key === 'titulos' ? (form.elements.namedItem('color_primario')?.value || institutionalPalette.primario) : institutionalPalette[key]);
      const picker = form.querySelector('[data-color-picker="' + name + '"]');
      if (picker && hexColor(value)) picker.value = value;
      effective[key] = value.toLowerCase();
    });
    form.querySelectorAll('[data-paleta]').forEach(button => button.setAttribute('aria-pressed', String(
      effective.primario === button.dataset.primario.toLowerCase() && effective.acento === button.dataset.acento.toLowerCase())));
    syncDesign();
  };
  ['color_primario', 'color_acento', 'color_texto', 'color_titulos'].forEach(name => {
    const input = form.elements.namedItem(name), picker = form.querySelector('[data-color-picker="' + name + '"]');
    input?.addEventListener('input', syncColors);
    input?.addEventListener('change', syncColors);
    picker?.addEventListener('input', () => {
      if (!input) return;
      input.value = picker.value;
      input.dispatchEvent(new Event('input', {bubbles: true}));
    });
  });
  const applyPalette = palette => {
    [['color_primario', 'primario'], ['color_acento', 'acento']].forEach(([name, key]) => {
      const input = form.elements.namedItem(name);
      if (!input) return;
      input.value = palette?.[key] || '';
      input.dispatchEvent(new Event('input', {bubbles: true}));
    });
  };
  form.querySelectorAll('[data-paleta]').forEach(button => button.addEventListener('click', () => applyPalette(button.dataset)));
  form.querySelector('[data-paleta-auto]')?.addEventListener('click', () => applyPalette(null));
  form.querySelector('[data-texto-colores-auto]')?.addEventListener('click', () => {
    ['color_texto', 'color_titulos'].forEach(name => {
      const input = form.elements.namedItem(name);
      if (input) { input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true})); }
    });
  });
  const syncFooter = () => {
    const active = form.elements.namedItem('mostrar_pie_tecnologico')?.checked;
    const style = form.elements.namedItem('estilo_pie_tecnologico');
    if (style) style.closest('.cert-editor__campo').hidden = !active;
  };
  form.elements.namedItem('mostrar_pie_tecnologico')?.addEventListener('change', syncFooter);
  syncFooter();

  design?.addEventListener('change', syncColors);
  syncColors();
  const textPresets = {
    academico: {
      aprobacion: 'Aprobó satisfactoriamente {curso}. La actividad académica se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      participacion: 'Participó en {curso}. La actividad académica se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      asistencia: 'Asistió a {curso}. La actividad académica se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      ponente: 'Intervino como ponente en {curso}. La actividad académica se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      organizador: 'Participó en la organización de {curso}. La actividad académica se desarrolló {periodo}, con una duración de {horas} horas, bajo la responsabilidad de {emisor}.'
    },
    tecnico: {
      aprobacion: 'Aprobó {curso}, una actividad de formación técnica aplicada al entorno profesional. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      participacion: 'Participó en {curso}, una actividad de formación técnica aplicada al entorno profesional. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      asistencia: 'Asistió a {curso}, una actividad de formación técnica aplicada al entorno profesional. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      ponente: 'Intervino como ponente en {curso}, compartiendo conocimientos para la formación técnica y profesional. La actividad se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      organizador: 'Participó en la organización de {curso}, una actividad de formación técnica aplicada al entorno profesional. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la responsabilidad de {emisor}.'
    },
    cientifico: {
      aprobacion: 'Aprobó {curso}, una actividad de formación y actualización científica. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      participacion: 'Participó en {curso}, un espacio de intercambio de conocimientos y experiencias científicas. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      asistencia: 'Asistió a {curso}, un espacio de intercambio de conocimientos y experiencias científicas. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      ponente: 'Intervino como ponente en {curso}, contribuyendo al intercambio de conocimientos y experiencias científicas. La actividad se desarrolló {periodo}, con una duración de {horas} horas, bajo la organización de {emisor}.',
      organizador: 'Participó en la organización de {curso}, un espacio de intercambio de conocimientos y experiencias científicas. Se desarrolló {periodo}, con una duración de {horas} horas, bajo la responsabilidad de {emisor}.'
    }
  };
  Object.values(textPresets).forEach(preset => Object.keys(preset).forEach(key => {
    preset[key] = preset[key].replaceAll('{emisor}', '{organizadores}');
  }));
  const syncRole = () => {
    document.querySelectorAll('[data-texto-campo]').forEach(item => {
      item.hidden = !item.dataset.textoCampo.endsWith('_' + role.value);
    });
    suggested.hidden = !defaults[role.value];
  };
  role.addEventListener('change', () => { syncRole(); type.value = role.value; invalidate(); });
  suggested.addEventListener('click', () => {
    const baseModel = defaults[role.value];
    const preset = textPresets[textModel?.value]?.[role.value];
    const model = preset ? {...baseModel, texto: preset} : baseModel;
    if (!model) return;
    ['titulo', 'texto'].forEach(name => {
      const input = form.elements.namedItem(name + '_' + role.value);
      if (input && typeof model[name] === 'string') {
        input.value = model[name];
        input.dispatchEvent(new Event('input', {bubbles: true}));
      }
    });
  });
  syncRole();
  form.querySelectorAll('input[type=file]').forEach(input => {
    const remove = form.elements.namedItem('quitar_' + input.name);
    remove?.addEventListener('change', () => {
      if (remove.checked && input.files?.length) {
        input.value = '';
        input.dispatchEvent(new Event('change', {bubbles: true}));
      }
    });
    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (file && file !== selectedFiles.get(input)) {
        if (remove) { remove.checked = false; clearFieldError(remove); }
      }
      if (file) selectedFiles.set(input, file);
      else selectedFiles.delete(input);
      const image = input.closest('[data-cert-campo]')?.querySelector('[data-imagen-local]');
      const previous = localImages.get(input);
      if (previous) URL.revokeObjectURL(previous);
      localImages.delete(input);
      if (!image) return;
      image.hidden = true;
      image.removeAttribute('src');
      if (file && ['image/png', 'image/jpeg'].includes(file.type) && file.size <= 2 * 1024 * 1024) {
        const url = URL.createObjectURL(file);
        localImages.set(input, url);
        image.src = url;
        image.hidden = false;
      }
    });
  });
  const format = form.elements.namedItem('formato_contenido');
  const syncContent = () => {
    const competencies = document.querySelector('[data-contenido-competencias]');
    if (competencies) {
      competencies.hidden = format?.value !== 'competencias';
      const input = competencies.querySelector('textarea');
      if (input) input.required = format?.value === 'competencias';
    }
    const help = document.querySelector('[data-formato-ayuda]');
    const descriptions = {
      breve: 'Una descripción directa de la actividad y su duración.',
      institucional: 'Presentación formal con entidad emisora, actividad, período y duración.',
      competencias: 'Incluye las competencias o resultados de aprendizaje que deseas acreditar.'
    };
    if (help) help.textContent = descriptions[format?.value] || '';
  };
  const competenciesInput = form.elements.namedItem('competencias');
  const syncCompetenciesCount = () => {
    const counter = document.querySelector('[data-competencias-contador]');
    if (!counter || !competenciesInput) return;
    const lines = competenciesInput.value.split(/\r?\n/).filter(line => line.trim()).length;
    const maximum = competenciesInput.maxLength;
    counter.textContent = competenciesInput.value.length + (maximum > 0 ? '/' + maximum : '') + ' caracteres · ' + lines + '/6 competencias';
    counter.classList.toggle('is-limite', lines > 6 || (maximum > 0 && competenciesInput.value.length > maximum));
    competenciesInput.setCustomValidity(lines > 6 ? 'Incluye como máximo seis competencias o logros.' : '');
  };
  competenciesInput?.addEventListener('input', syncCompetenciesCount);
  syncCompetenciesCount();
  format?.addEventListener('change', syncContent);
  syncContent();
  const photo = form.elements.namedItem('foto_alusiva');
  const useUnitPhoto = form.elements.namedItem('usar_foto_unidad');
  const removePhoto = form.elements.namedItem('quitar_foto_alusiva');
  const syncPhoto = () => {
    const removed = removePhoto?.checked;
    const local = !removed && localImages.get(photo);
    const saved = !removed && form.dataset.fotoGuardada;
    const source = local || saved || (useUnitPhoto?.checked && form.dataset.fotoUnidad) || '';
    document.querySelectorAll('[data-miniatura-foto]').forEach(image => {
      image.hidden = !source;
      if (source) image.src = source;
      else image.removeAttribute('src');
    });
    const figure = document.querySelector('[data-foto-resumen]');
    const image = document.querySelector('[data-foto-elegida]');
    const caption = document.querySelector('[data-foto-origen]');
    if (figure) figure.hidden = !source;
    if (image) { if (source) image.src = source; else image.removeAttribute('src'); }
    if (caption) caption.textContent = local ? 'Fotografía seleccionada en este equipo' : saved ? 'Fotografía guardada para este certificado' : source ? 'Fotografía del laboratorio' : '';
  };
  [photo, useUnitPhoto, removePhoto].filter(Boolean).forEach(input => input.addEventListener('change', syncPhoto));
  syncPhoto();
  const institutionCards = [...document.querySelectorAll('[data-institucion]')];
  const addInstitution = document.querySelector('[data-agregar-institucion]');
  const institutionFields = card => {
    const number = card.dataset.institucion;
    return Object.fromEntries(['nombre', 'imagen', 'posicion', 'contraste'].map(key => [key, form.elements.namedItem('logo_' + number + '_' + key)]).concat([['quitar', form.elements.namedItem('quitar_logo_' + number + '_imagen')]]));
  };
  const syncInstitutions = () => {
    institutionCards.forEach(card => {
      const fields = institutionFields(card), selected = fields.imagen?.files?.length;
      const removed = fields.quitar?.checked;
      const source = !removed && (localImages.get(fields.imagen) || card.dataset.logoGuardado) || '';
      const used = !!(fields.nombre?.value.trim() || source || selected || card.querySelector('.errorlist,[data-validacion-editor]'));
      if (used) card.dataset.activa = 'true';
      card.hidden = card.dataset.activa !== 'true';
      card.querySelector('[data-institucion-titulo]').textContent = fields.nombre?.value.trim() || 'Entidad colaboradora ' + card.dataset.institucion;
      fields.nombre.required = !!selected && !removed;
      const figure = card.querySelector('[data-logo-resumen]'), image = card.querySelector('[data-logo-elegido]');
      figure.hidden = !source;
      card.querySelector('.cert-editor__retirar-logo').hidden = !selected && !card.dataset.logoGuardado;
      if (source) image.src = source;
      else image.removeAttribute('src');
    });
    if (addInstitution) addInstitution.hidden = institutionCards.every(card => !card.hidden);
  };
  institutionCards.forEach(card => {
    const fields = institutionFields(card);
    Object.values(fields).filter(Boolean).forEach(input => {
      input.addEventListener('input', syncInstitutions);
      input.addEventListener('change', syncInstitutions);
    });
    card.querySelector('[data-retirar-institucion]')?.addEventListener('click', () => {
      fields.nombre.value = '';
      fields.imagen.value = '';
      fields.posicion.value = 'auto';
      fields.contraste.value = 'auto';
      fields.quitar.checked = !!card.dataset.logoGuardado;
      Object.values(fields).filter(Boolean).forEach(clearFieldError);
      card.querySelectorAll('.errorlist').forEach(error => error.remove());
      fields.imagen.dispatchEvent(new Event('change', {bubbles:true}));
      delete card.dataset.activa;
      syncInstitutions();
      addInstitution?.focus();
    });
  });
  addInstitution?.addEventListener('click', () => {
    const card = institutionCards.find(item => item.hidden);
    if (!card) return;
    card.dataset.activa = 'true';
    syncInstitutions();
    institutionFields(card).nombre.focus();
  });
  syncInstitutions();
  const facultySelect = form.elements.namedItem('facultad_catalogo');
  const careerSelect = form.elements.namedItem('carrera_catalogo');
  const facultyName = form.elements.namedItem('facultad_nombre');
  const careerName = form.elements.namedItem('carrera_nombre');
  const showFaculty = form.elements.namedItem('mostrar_facultad');
  const showCareer = form.elements.namedItem('mostrar_carrera');
  const careersByCode = new Map((academicCatalog.carreras || []).map(item => [item.codigo, item]));
  const CUSTOM_ACADEMIC = '__personalizado__';
  const syncAcademics = resetCareer => {
    if (!facultySelect || !careerSelect || !facultyName || !careerName) return;
    const selectedCareer = careersByCode.get(careerSelect.value);
    if (resetCareer && selectedCareer && selectedCareer.facultad !== facultySelect.value) {
      careerSelect.value = '';
      careerName.value = '';
    }
    [...careerSelect.options].forEach(option => {
      const career = careersByCode.get(option.value);
      const visible = !career || career.facultad === facultySelect.value || (!resetCareer && option.selected);
      option.hidden = !visible;
      option.disabled = !visible;
    });
    [['facultad', facultySelect, facultyName, showFaculty], ['carrera', careerSelect, careerName, showCareer]].forEach(([key, select, input, checkbox]) => {
      const needed = checkbox?.checked || (key === 'facultad' && showCareer?.checked);
      const custom = select.value === CUSTOM_ACADEMIC;
      select.closest('[data-cert-campo]').hidden = !needed;
      select.required = Boolean(needed && !(key === 'facultad' && !showFaculty?.checked && careerSelect.value === CUSTOM_ACADEMIC));
      if (!custom) input.value = select.value ? select.selectedOptions[0]?.textContent.trim() || '' : '';
      input.closest('[data-cert-campo]').hidden = !needed || !custom;
      input.required = Boolean(checkbox?.checked && custom);
      const summary = document.querySelector('[data-principal-' + key + ']');
      const name = summary?.querySelector('[data-principal-nombre]');
      if (name) name.textContent = input.value.trim();
      if (summary) summary.hidden = !checkbox?.checked || !input.value.trim();
    });
  };
  facultySelect?.addEventListener('change', () => syncAcademics(true));
  careerSelect?.addEventListener('change', () => syncAcademics(false));
  [showFaculty, showCareer, facultyName, careerName].filter(Boolean).forEach(input => {
    input.addEventListener('input', () => syncAcademics(false));
    input.addEventListener('change', () => syncAcademics(false));
  });
  syncAcademics(false);
  const revealErrors = () => {
    form.querySelectorAll('.errorlist').forEach(item => {
      const academic = item.closest('[data-cert-campo]');
      if (academic && /^(facultad|carrera)_/.test(academic.dataset.certCampo || '')) academic.hidden = false;
      const details = item.closest('details');
      if (details) details.open = true;
      const competencies = item.closest('[data-contenido-competencias]');
      if (competencies) competencies.hidden = false;
      const text = item.closest('[data-texto-campo]');
      if (text) {
        const key = ['aprobacion', 'participacion', 'asistencia', 'ponente', 'organizador'].find(value => text.dataset.textoCampo.endsWith('_' + value));
        if (key) role.value = key;
      }
    });
    syncRole();
  };
  revealErrors();
  const clearFieldError = input => {
    if (!input?.name) return;
    const box = input.closest('[data-cert-campo]');
    box?.querySelector('[data-validacion-editor]')?.remove();
    if (input.dataset.editorInvalid) {
      input.removeAttribute('aria-invalid');
      const id = 'cert-error-' + input.name;
      const description = (input.getAttribute('aria-describedby') || '').split(/\s+/).filter(value => value && value !== id).join(' ');
      if (description) input.setAttribute('aria-describedby', description);
      else input.removeAttribute('aria-describedby');
      delete input.dataset.editorInvalid;
    }
    const details = box?.closest('details');
    if (details && !details.querySelector('[data-validacion-editor],.errorlist')) details.classList.remove('has-error');
  };
  const fieldError = (input, message) => {
    if (!input) return;
    clearFieldError(input);
    const box = input.closest('[data-cert-campo]');
    if (!box) return;
    const hint = document.createElement('small');
    hint.className = 'cert-editor__validacion';
    hint.dataset.validacionEditor = 'true';
    hint.id = 'cert-error-' + input.name;
    hint.textContent = message;
    box.append(hint);
    input.setAttribute('aria-invalid', 'true');
    input.dataset.editorInvalid = 'true';
    input.setAttribute('aria-describedby', [(input.getAttribute('aria-describedby') || ''), hint.id].filter(Boolean).join(' '));
    box.closest('details')?.classList.add('has-error');
  };
  const revealField = input => {
    const academic = input?.closest('[data-cert-campo]');
    if (academic && /^(facultad|carrera)_/.test(academic.dataset.certCampo || '')) academic.hidden = false;
    const institution = input?.closest('[data-institucion]');
    if (institution) { institution.dataset.activa = 'true'; institution.hidden = false; }
    const details = input?.closest('details');
    if (details) details.open = true;
    const competencies = input?.closest('[data-contenido-competencias]');
    if (competencies) competencies.hidden = false;
    const text = input?.closest('[data-texto-campo]');
    if (text) {
      const key = ['aprobacion', 'participacion', 'asistencia', 'ponente', 'organizador'].find(value => text.dataset.textoCampo.endsWith('_' + value));
      if (key) { role.value = key; type.value = key; syncRole(); }
    }
  };
  const validateForm = interactive => {
    const input = form.querySelector(':invalid');
    if (!input) return true;
    fieldError(input, input.validationMessage || 'Completa este dato.');
    status.textContent = 'Vista previa detenida · Completa los campos señalados.';
    if (interactive) { revealField(input); input.reportValidity(); }
    return false;
  };
  const serverErrors = (payload, interactive = false) => {
    let first = null;
    const messages = Object.entries(payload.errores || {}).flatMap(([name, items]) => {
      const input = form.elements.namedItem(name);
      const message = items.map(item => item.message || String(item)).join(' ');
      if (input) { fieldError(input, message); first ||= input; }
      const label = input?.labels?.[0]?.textContent.trim();
      return (label ? label + ': ' : '') + message;
    });
    if (interactive && first) { revealField(first); first.focus(); }
    return messages.join(' ') || 'Revisa los campos del formulario.';
  };
  // Las tarjetas se renderizan con el mismo endpoint y PDF.js que la vista grande.
  // Sólo se solicitan las visibles, en serie, después de terminar la vista principal.
  const cancelGalleryJob = job => {
    if (!job) return;
    job.controller.abort();
    job.render?.cancel();
    if (job.task) Promise.resolve(job.task.destroy()).catch(() => {});
  };
  const pauseGallery = () => {
    window.clearTimeout(galleryTimer);
    cancelGalleryJob(galleryJob);
  };
  const resetGallery = () => {
    galleryEpoch += 1;
    models.forEach(button => {
      button.querySelector('[data-miniatura-pdf]')?.remove();
      const hint = button.querySelector('[data-miniatura-estado]');
      if (hint) { hint.hidden = false; hint.textContent = 'Cargando modelo…'; }
      delete button.dataset.miniaturaError;
    });
  };
  const paintThumbnail = (button, page) => {
    if (!button || !page?.width || !page?.height) return;
    const miniature = button.querySelector('.cert-editor__miniatura');
    const small = document.createElement('canvas');
    small.width = 320; small.height = Math.round(320 * page.height / page.width);
    small.getContext('2d').drawImage(page, 0, 0, small.width, small.height);
    let image = miniature.querySelector('[data-miniatura-pdf]');
    if (!image) { image = document.createElement('img'); image.dataset.miniaturaPdf = ''; image.alt = ''; miniature.append(image); }
    image.src = small.toDataURL('image/png');
    miniature.querySelector('[data-miniatura-estado]').hidden = true;
    delete button.dataset.miniaturaError;
  };
  const runGallery = async () => {
    if (!active || busy || galleryJob || !token.value || !window.VisorPdf) return;
    const button = models.find(item => visibleModels.has(item) && !item.querySelector('[data-miniatura-pdf]') && !item.dataset.miniaturaError);
    if (!button) return;
    const job = {epoch:galleryEpoch, controller:new AbortController(), render:null};
    galleryJob = job;
    let pdf, task;
    const valid = () => active && job.epoch === galleryEpoch && !job.controller.signal.aborted;
    const timeout = window.setTimeout(() => { job.timedOut = true; cancelGalleryJob(job); }, 45000);
    try {
      const data = new FormData(form);
      data.set('diseno', button.dataset.diseno);
      data.set('tipo_muestra', type.value);
      const response = await fetch(form.dataset.previaUrl, {method:'POST', body:data, credentials:'same-origin', signal:job.controller.signal});
      if (!valid()) return;
      if (!response.ok || !(response.headers.get('Content-Type') || '').includes('application/pdf')) throw new Error('Modelo no disponible');
      const blob = await response.blob();
      const library = await window.VisorPdf.cargarBiblioteca();
      if (!valid()) return;
      task = library.getDocument({data:new Uint8Array(await blob.arrayBuffer()), useWasm:false, isEvalSupported:false});
      job.task = task;
      pdf = await task.promise;
      if (!valid()) return;
      const page = await pdf.getPage(1);
      const initial = page.getViewport({scale:1});
      const viewport = page.getViewport({scale:320 / initial.width});
      const canvas = document.createElement('canvas');
      canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
      job.render = page.render({canvasContext:canvas.getContext('2d'), viewport});
      await job.render.promise;
      if (valid()) paintThumbnail(button, canvas);
    } catch (_) {
      if (active && job.epoch === galleryEpoch && (!job.controller.signal.aborted || job.timedOut)) {
        button.dataset.miniaturaError = 'true';
        button.querySelector('[data-miniatura-estado]').textContent = 'Selecciona para revisar';
      }
    } finally {
      window.clearTimeout(timeout);
      try { if (pdf) await pdf.destroy(); else if (task) await task.destroy(); } catch (_) { /* Tarea cancelada. */ }
      if (galleryJob === job) galleryJob = null;
      scheduleGallery();
    }
  };
  const scheduleGallery = () => {
    window.clearTimeout(galleryTimer);
    if (active) galleryTimer = window.setTimeout(runGallery, 200);
  };
  const galleryObserver = window.IntersectionObserver ? new IntersectionObserver(entries => {
    entries.forEach(entry => entry.isIntersecting ? visibleModels.add(entry.target) : visibleModels.delete(entry.target));
    scheduleGallery();
  }, {root:form.querySelector('.cert-editor__controles'), rootMargin:'80px'}) : null;
  if (galleryObserver) models.forEach(button => galleryObserver.observe(button));
  else models.forEach(button => visibleModels.add(button));

  const current = job => active && previewJob === job && job.sequence === previewSequence && job.revision === revision && job.stamp === stamp();
  const waitForPaint = async job => {
    const until = Date.now() + 15000;
    while (current(job) && Date.now() < until) {
      if (job.stage?.querySelector('.pdf-viewer-canvas[data-renderizado="true"]')) return true;
      await new Promise(resolve => window.setTimeout(resolve, 25));
    }
    return false;
  };
  const runPreview = async job => {
    busy = true;
    form.setAttribute('aria-busy', 'true');
    save.disabled = true;
    token.value = '';
    downloadReady(false);
    errors.hidden = true;
    errorText.textContent = '';
    status.textContent = 'Actualizando la vista previa…';
    const data = new FormData(form);
    data.set('tipo_muestra', type.value);
    try {
      job.timeout = window.setTimeout(() => { job.timedOut = true; job.controller.abort(); }, 45000);
      const response = await fetch(form.dataset.previaUrl, {method:'POST',body:data,credentials:'same-origin',signal:job.controller.signal});
      if (!current(job)) return false;
      if (!response.ok) {
        if ((response.headers.get('Content-Type') || '').includes('application/json')) {
          const payload = await response.json();
          if (!current(job)) return false;
          throw new Error(serverErrors(payload));
        }
        throw new Error('No se pudo actualizar la vista previa. Revisa tu conexión y vuelve a intentarlo.');
      }
      const previewToken = response.headers.get('X-Certificado-Vista-Previa');
      const blob = await response.blob();
      window.clearTimeout(job.timeout);
      if (!current(job)) return false;
      if (!previewToken || blob.type !== 'application/pdf') throw new Error('No se recibió una vista previa válida.');
      if (!window.VisorPdf) throw new Error('El visor no está disponible. Recarga la página.');
      job.url = URL.createObjectURL(blob);
      job.stage = document.createElement('div');
      job.stage.className = 'cert-editor__pdf-stage is-preparing';
      job.stage.setAttribute('aria-hidden', 'true');
      frame.hidden = false;
      empty.hidden = true;
      frame.append(job.stage);
      job.mounted = await window.VisorPdf.montar(job.stage, job.url, {ajuste:'ancho',miniaturas:false,densidadMinima:2});
      if (!current(job)) return false;
      job.stage.querySelectorAll('.pdf-viewer-toolbar,.pdf-viewer-sidebar').forEach(element => {
        element.hidden = true;
        element.setAttribute('aria-hidden', 'true');
      });
      if (!job.mounted.listo || !await waitForPaint(job)) {
        if (!current(job)) return false;
        throw new Error('No se pudo mostrar el documento. Vuelve a intentarlo.');
      }
      if (!current(job)) return false;
      const previousViewer = visor, previousUrl = objectUrl, stage = job.stage;
      visor = job.mounted;
      objectUrl = job.url;
      job.mounted = null; job.url = null; job.stage = null;
      previousViewer?.destruir();
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      stage.classList.remove('is-preparing');
      stage.removeAttribute('aria-hidden');
      frame.replaceChildren(stage);
      paintThumbnail(models.find(button => button.dataset.diseno === design.value),
        stage.querySelector('.pdf-viewer-canvas[data-renderizado="true"]'));
      token.value = previewToken;
      acceptedRevision = revision;
      acceptedStamp = job.stamp;
      link.href = objectUrl;
      downloadReady(true);
      save.disabled = saving;
      status.textContent = 'Hoja completa · Vista previa actualizada.';
      scheduleGallery();
      fitLayout();
      return true;
    } catch (error) {
      if (!current(job)) return false;
      token.value = '';
      acceptedRevision = -1;
      save.disabled = true;
      downloadReady(false);
      if (!visor) { frame.hidden = true; empty.hidden = false; }
      errorText.textContent = job.timedOut ? 'La vista previa tardó demasiado. Vuelve a intentarlo; tus cambios se conservan.' : error.name === 'AbortError' ? 'La vista previa se interrumpió. Puedes volver a intentarlo sin perder tus cambios.' : error.message;
      errors.hidden = false;
      status.textContent = 'Vista previa detenida · Revisa los campos señalados.';
      fitLayout();
      return false;
    } finally {
      discardJob(job);
      if (previewJob === job) {
        previewJob = null;
        busy = false;
        form.removeAttribute('aria-busy');
      }
    }
  };
  const startPreview = () => {
    if (!active || !validateForm(false)) return Promise.resolve(false);
    const signature = stamp();
    if (token.value && acceptedRevision === revision && acceptedStamp === signature) return Promise.resolve(true);
    if (previewJob?.revision === revision && previewJob.stamp === signature) return previewJob.promise;
    stopPendingPreview();
    const job = {sequence:++previewSequence, revision, stamp:signature, controller:new AbortController(), stage:null, mounted:null, url:null};
    previewJob = job;
    job.promise = runPreview(job);
    return job.promise;
  };
  const schedulePreview = (delay = 500) => {
    window.clearTimeout(previewTimer);
    if (active) previewTimer = window.setTimeout(() => { previewTimer = null; startPreview(); }, delay);
  };
  const ensureLatestPreview = async () => {
    while (active) {
      if (!validateForm(true)) return false;
      window.clearTimeout(previewTimer); previewTimer = null;
      const requestedRevision = revision, requestedStamp = stamp();
      const ready = await startPreview();
      if (requestedRevision !== revision || requestedStamp !== stamp()) continue;
      return ready && token.value && acceptedRevision === revision && acceptedStamp === requestedStamp;
    }
    return false;
  };
  form.noValidate = true;
  form.addEventListener('input', invalidate);
  form.addEventListener('change', invalidate);
  type.addEventListener('change', () => { role.value = type.value; syncRole(); invalidate(); });
  retry.addEventListener('click', () => schedulePreview(0));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    save.disabled = true;
    window.courseEditorBusy = true;
    try {
      if (!await ensureLatestPreview()) return;
      const savedRevision = revision, savedStamp = stamp();
      const data = new FormData(form);
      data.set('tipo_muestra', type.value);
      status.textContent = 'Guardando el diseño…';
      const response = await fetch(form.action || location.href, {method:'POST',body:data,credentials:'same-origin',headers:{'X-Requested-With':'XMLHttpRequest'}});
      const payload = (response.headers.get('Content-Type') || '').includes('application/json') ? await response.json() : null;
      if (!response.ok || !payload?.ok) {
        token.value = ''; acceptedRevision = -1; downloadReady(false);
        errorText.textContent = payload ? serverErrors(payload, true) : 'No se pudo guardar el diseño. Revisa tu sesión y vuelve a intentarlo.';
        errors.hidden = false;
        status.textContent = 'El diseño no se guardó. Tus cambios e imágenes siguen en el editor.';
        return;
      }
      const unchanged = revision === savedRevision && stamp() === savedStamp;
      let notice = document.querySelector('.cert-editor__guardado');
      if (!notice) { notice = document.createElement('div'); notice.className = 'cert-editor__guardado'; notice.setAttribute('role','status'); columns.before(notice); }
      notice.textContent = unchanged ? 'Diseño guardado. Se aplicará a los nuevos certificados.' : 'Diseño guardado. Hay cambios posteriores que todavía no se han guardado.';
      if (unchanged) {
        window.courseEditorDirty = false;
        document.dispatchEvent(new CustomEvent('panel-task:saved', {bubbles:true}));
        status.textContent = 'Diseño guardado.';
        if (payload.url) {
          const destination = new URL(payload.url, location.href);
          if (destination.origin === location.origin && /^https?:$/.test(destination.protocol)) location.assign(destination.href);
        }
      }
      fitLayout();
    } catch (error) {
      errorText.textContent = 'No se pudo guardar el diseño. Tus cambios e imágenes siguen en el editor. ' + error.message;
      errors.hidden = false;
      status.textContent = 'El diseño no se guardó.';
    } finally {
      saving = false;
      window.courseEditorBusy = false;
      save.disabled = !token.value || acceptedRevision !== revision || acceptedStamp !== stamp();
    }
  });
  const columns = document.querySelector('.cert-editor__columnas');
  const previewPanel = document.querySelector('.cert-editor__previa');
  const previewHeader = previewPanel.querySelector('header');
  let layoutFrame = 0;
  const putSize = (name, value) => {
    const size = Math.round(value) + 'px';
    if (columns.style.getPropertyValue(name) !== size) columns.style.setProperty(name, size);
  };
  const fitLayout = () => {
    cancelAnimationFrame(layoutFrame);
    layoutFrame = requestAnimationFrame(() => {
      const availableHeight = Math.max(360, Math.floor(window.innerHeight - columns.getBoundingClientRect().top - 12));
      putSize('--cert-editor-height', availableHeight);
      // The full landscape page fits both dimensions without internal scrolling.
      const previewWidth = previewPanel.getBoundingClientRect().width;
      const surface = frame.querySelector('.pdf-viewer-main');
      const gutter = surface ? surface.offsetWidth - surface.clientWidth : (window.innerWidth <= 620 ? 0 : 15);
      putSize('--cert-preview-frame-height', Math.ceil(Math.max(1, previewWidth - 16 - gutter) * 210 / 297 + 16));
      columns.style.removeProperty('--cert-preview-width');
    });
  };
  window.addEventListener('resize', fitLayout);
  const classObserver = new MutationObserver(fitLayout);
  classObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
  const layoutObserver = new ResizeObserver(fitLayout);
  [previewHeader, status, tools, errors].forEach(element => layoutObserver.observe(element));
  fitLayout();
  document.fonts?.ready.then(fitLayout);
  window.addEventListener('pagehide', () => {
    active = false;
    pauseGallery();
    previewSequence += 1;
    stopPendingPreview();
    revision += 1;
    token.value = '';
    save.disabled = true;
    destroyPreview();
    localImages.forEach(url => URL.revokeObjectURL(url));
    localImages.clear();
    syncPhoto();
    document.querySelectorAll('[data-imagen-local]').forEach(image => { image.hidden = true; image.removeAttribute('src'); });
    window.courseEditorBusy = false;
    cancelAnimationFrame(layoutFrame);
  });
  window.addEventListener('pageshow', event => {
    active = true;
    form.querySelectorAll('input[type=file]').forEach(input => {
      if (input.files?.length) input.dispatchEvent(new Event('change', {bubbles: true}));
    });
    syncPhoto();
    fitLayout();
    if (event.persisted) schedulePreview(0);
  });
  const begin = () => schedulePreview(0);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', begin, {once:true});
  else begin();
})();
