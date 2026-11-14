(function () {
  'use strict';
  let root, dirty = false, busy = false;
  let currentTab = 'datos';
  let opener;
  const tabs = ['datos', 'programa', 'evaluaciones', 'participantes', 'certificado'];
  window.courseEditorPage = true;
  window.courseEditorDirty = false;
  window.courseEditorBusy = false;
  window.panelTaskBeforeClose = () => !busy;
  window.courseEditorSaved = false;
  function announce(text, error) {
    const el = root.querySelector('[data-course-feedback]');
    el.hidden = !text; el.textContent = text;
    el.classList.toggle('is-error', Boolean(error));
  }
  function setDirty(value) { dirty = value; window.courseEditorDirty = value; }
  function setBusy(value) {
    busy = value; window.courseEditorBusy = value;
    if (value) root.setAttribute('aria-busy', 'true'); else root.removeAttribute('aria-busy');
  }
  function discarded() {
    setDirty(false);
    document.dispatchEvent(new CustomEvent('panel-task:discarded'));
  }
  function canDiscard() {
    if (busy) return false;
    if (dirty && !window.confirm('Hay cambios sin guardar. ¿Quieres descartarlos?')) return false;
    if (dirty) discarded();
    return true;
  }
  function activate(tab, updateHash) {
    currentTab = tabs.includes(tab) ? tab : 'datos';
    root.querySelectorAll('[data-course-pane]').forEach(el => { el.hidden = el.dataset.coursePane !== currentTab; });
    root.querySelectorAll('[data-course-tab]').forEach(el => {
      const selected = el.dataset.courseTab === currentTab;
      el.classList.toggle('is-active', selected);
      if (selected) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
    });
    if (updateHash) history.replaceState(null, '', '#' + currentTab);
  }
  function returnToBrowser() {
    if (!canDiscard()) return;
    root.querySelector('[data-course-form-region]').hidden = true;
    root.querySelector('[data-course-browser]').hidden = false;
    root.querySelector('[data-course-form-content]').replaceChildren();
    if (opener?.isConnected) opener.focus({preventScroll:true});
    else root.querySelector('[data-course-tab="' + currentTab + '"]').focus({preventScroll:true});
  }
  function conditionalFields(form) {
    const type = form.querySelector('[name="registro-tipo"]');
    if (!type) return;
    let visible;
    if (form.querySelector('[name="registro-video_url"]')) {
      const common = ['orden','titulo','tipo','contenido','duracion_min','obligatoria','publicada','eliminar'];
      const byType = {texto:[],video:['video_url','archivo'],material:['archivo','enlace'],
        en_vivo:['sala','enlace','reunion_url','fecha_hora','lugar','grabacion_url'],
        evaluacion:['nota_minima','intentos','fecha_limite'],deber:['nota_minima','fecha_limite']};
      visible = new Set(common.concat(byType[type.value] || []));
    } else if (form.querySelector('[name="registro-respuestas_aceptadas"]')) {
      visible = new Set(['orden','enunciado','tipo','puntos','explicacion','eliminar',
        type.value === 'corta' ? 'respuestas_aceptadas' : 'opciones']);
    } else return;
    form.querySelectorAll('.editor__campo').forEach(field => {
      const control = field.querySelector('[name^="registro-"]');
      const name = control?.name.slice(9).replace(/-clear$/, '');
      field.hidden = Boolean(name && !visible.has(name));
      if (field.querySelector('.editor__mensaje')) field.hidden = false;
    });
  }
  function displayForm(html) {
    const parsed = new DOMParser().parseFromString(html, 'text/html');
    const form = parsed.querySelector('form[data-editor-ficha]');
    if (!form) throw Error('Formulario no disponible. Revisa tu sesión y vuelve a intentarlo.');
    if (!form.querySelector('[name=fragmento]')) {
      const hidden = document.createElement('input'); hidden.type='hidden';hidden.name='fragmento';hidden.value='1';form.appendChild(hidden);
    }
    form.querySelectorAll('textarea').forEach(el => { el.rows = el.name.endsWith('-contenido') ? 18 : 6; });
    const content = root.querySelector('[data-course-form-content]');
    content.replaceChildren(form);
    conditionalFields(form);
    root.querySelector('[data-course-browser]').hidden = true;
    root.querySelector('[data-course-form-region]').hidden = false;
  }
  async function edit(link) {
    if (!canDiscard()) return;
    opener = link;
    setBusy(true);announce('Cargando formulario…');
    try {
      const url = new URL(link.href, location.href);
      if (url.origin !== location.origin) throw Error('El editor debe pertenecer a este sitio.');
      url.searchParams.set('fragmento','1');
      const response = await fetch(url,{credentials:'same-origin'});
      if (!response.ok) throw Error('No se pudo abrir esta parte del curso. Revisa tu sesión y permisos.');
      displayForm(await response.text());
      root.querySelector('[data-course-form-title]').textContent = link.dataset.editTitle || 'Editar contenido';
      announce('');setDirty(false);
      root.querySelector('[data-course-form-title]').focus({preventScroll:true});
      root.querySelector('[data-course-form-region]').scrollIntoView({block:'start',behavior:'auto'});
    } catch (error) { announce(error.message,true); }
    finally { setBusy(false); }
  }
  async function refresh() {
    const opened = Array.from(root.querySelectorAll('details[open][data-course-module]')).map(el=>el.dataset.courseModule);
    const response = await fetch(root.dataset.editorUrl,{credentials:'same-origin'});
    if (!response.ok) throw Error('Los cambios se guardaron. Actualiza el editor para verlos.');
    const parsed = new DOMParser().parseFromString(await response.text(),'text/html');
    const replacement = parsed.querySelector('[data-course-editor]');
    if (!replacement) throw Error('Los cambios se guardaron. Vuelve a abrir el editor.');
    root.replaceWith(replacement);root=replacement;wire();activate(currentTab,false);
    root.querySelectorAll('details[data-course-module]').forEach(el => {el.open=opened.includes(el.dataset.courseModule);});
  }
  async function save(form) {
    if (busy) return;
    setBusy(true);announce('Guardando cambios…');
    try {
      const url = new URL(form.action,location.href);
      if (url.origin !== location.origin) throw Error('No se pudo guardar el formulario.');
      const data = new FormData(form);data.set('fragmento','1');
      const response = await fetch(url,{method:'POST',body:data,credentials:'same-origin',headers:{'X-Requested-With':'fetch'}});
      if (response.ok && (response.headers.get('Content-Type')||'').includes('application/json')) {
        const result=await response.json();
        if (!result.ok) throw Error('No se confirmó el guardado. Revisa los datos.');
        setDirty(false);window.courseEditorSaved=true;
        document.dispatchEvent(new CustomEvent('panel-task:saved'));
        if (result.redirigir) {
          const destination = new URL(result.redirigir, location.href);
          if (destination.origin !== location.origin) throw Error('Destino de retorno no válido.');
          try {
            if (parent !== window && parent.document.querySelector('.gestion-curso-modal iframe')?.contentWindow === window) {
              parent.location.assign(destination.href);return;
            }
          } catch (_) { /* Conserva el retorno dentro del editor. */ }
          location.replace(destination.href);return;
        }
        await refresh();announce('Cambios guardados correctamente.');
        root.querySelector('[data-course-feedback]').scrollIntoView({block:'nearest'});
        root.querySelector('[data-course-tab="'+currentTab+'"]').focus({preventScroll:true});
      } else {
        if (!response.ok && response.status !== 400) throw Error('No se pudo guardar. Revisa tu sesión y vuelve a intentarlo.');
        displayForm(await response.text());announce('Revisa los campos marcados: no se guardaron los cambios.',true);
        const error=root.querySelector('.editor__error,.editor__mensaje');
        error?.scrollIntoView({block:'center'});
      }
    } catch(error) { announce(error.message,true); }
    finally {setBusy(false);}
  }
  function wire() {
    root.addEventListener('click',event=>{
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const editLink=event.target.closest('[data-course-edit]');
      if(editLink){event.preventDefault();edit(editLink);return;}
      if(event.target.closest('[data-course-cancel],[data-cerrar-edicion],.editor__pie>a')){event.preventDefault();returnToBrowser();return;}
      const tab=event.target.closest('[data-course-tab],[data-course-go]');
      if(tab){event.preventDefault();activate(tab.dataset.courseTab||tab.dataset.courseGo,true);return;}
      const link=event.target.closest('a[href]');
      if(link && dirty && !canDiscard()){event.preventDefault();event.stopImmediatePropagation();}
    });
    root.addEventListener('input',event=>{if(event.target.closest('form[data-editor-ficha]'))setDirty(true);});
    root.addEventListener('change',event=>{const form=event.target.closest('form[data-editor-ficha]');if(form){setDirty(true);conditionalFields(form);}});
    root.addEventListener('submit',event=>{const form=event.target.closest('form[data-editor-ficha]');if(form){event.preventDefault();save(form);}});
  }
  root=document.querySelector('[data-course-editor]');if(!root)return;
  wire();activate(location.hash.slice(1),false);
  addEventListener('hashchange',()=>{if(!root.querySelector('[data-course-browser]').hidden)activate(location.hash.slice(1),false);});
  addEventListener('beforeunload',event=>{if(dirty && parent===window){event.preventDefault();event.returnValue='';}});
}());
