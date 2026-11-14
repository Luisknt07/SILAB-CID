(function(){
  'use strict';
  function initialize(){document.querySelectorAll('.catalogo-editor').forEach(function(editor){
    const payload=editor.querySelector('textarea');
    const panel=editor.querySelector('.catalogo-editor-guiado');
    let initial;
    try{initial=JSON.parse(payload.value);}catch(error){return;}
    const groups=['facultades','carreras','carreras_historicas'];
    if(!initial||typeof initial!=='object'||Object.keys(initial).some(k=>!groups.includes(k)&&k!=='tipos_con_carrera')||groups.some(g=>!Array.isArray(initial[g]||[])||(initial[g]||[]).some(row=>!Array.isArray(row)||row.length!==(g==='carreras'?3:2)||row.some(v=>typeof v!=='string')))||!Array.isArray(initial.tipos_con_carrera||[]))return;
    let sequence=0;
    const rows=g=>Array.from(panel.querySelector('[data-group="'+g+'"] .catalogo-filas').children);
    const values=g=>rows(g).map(row=>Array.from(row.querySelectorAll('input[type=text],select')).map(field=>field.value));
    function flush(){
      payload.value=JSON.stringify({facultades:values('facultades'),carreras:values('carreras'),carreras_historicas:values('carreras_historicas'),tipos_con_carrera:Array.from(panel.querySelectorAll('[data-tipo]:checked')).map(field=>field.dataset.tipo)});
      groups.forEach(g=>{const section=panel.querySelector('[data-group="'+g+'"]');section.querySelector('[data-add]').disabled=rows(g).length>=Number(section.dataset.max);});
    }
    function options(){
      const faculties=values('facultades').filter(f=>f[0]&&f[0]!=='externo');
      rows('carreras').forEach(row=>{
        const select=row.querySelector('select'), selected=select.value;
        select.replaceChildren(new Option(editor.dataset.chooseLabel,''));
        faculties.forEach(f=>select.add(new Option(f[1]+' ('+f[0]+')',f[0])));
        if(selected&&!faculties.some(f=>f[0]===selected))select.add(new Option(selected,selected));
        select.value=selected;
      });
    }
    function add(group, data){
      const section=panel.querySelector('[data-group="'+group+'"]');
      if(rows(group).length>=Number(section.dataset.max))return;
      const row=document.createElement('div');row.className='catalogo-fila';
      const fields=[editor.dataset.codeLabel,editor.dataset.nameLabel];
      if(group==='carreras')fields.push(editor.dataset.facultyLabel);
      fields.forEach((caption,index)=>{
        const container=document.createElement('div'),label=document.createElement('label');
        const field=document.createElement(index===2?'select':'input');
        if(index!==2){field.type='text';field.maxLength=index===0?50:250;}
        field.id=payload.id+'-fila-'+(++sequence);label.htmlFor=field.id;label.textContent=caption;
        if(index===2){field.add(new Option(editor.dataset.chooseLabel,''));if(data[index])field.add(new Option(data[index],data[index]));}
        field.value=data[index]||'';
        field.addEventListener('input',()=>{if(group==='facultades')options();flush();});
        container.append(label,field);row.append(container);
      });
      const actions=document.createElement('div');actions.className='catalogo-fila-acciones';
      const remove=document.createElement('button');remove.type='button';remove.dataset.remove='';remove.textContent=editor.dataset.removeLabel;
      remove.addEventListener('click',()=>{row.remove();if(group==='facultades')options();flush();});actions.append(remove);
      if(group==='carreras'){
        const retire=document.createElement('button');retire.type='button';retire.textContent=editor.dataset.retireLabel;
        retire.addEventListener('click',()=>{
          if(rows('carreras_historicas').length>=2000)return;
          const data=Array.from(row.querySelectorAll('input[type=text]')).map(f=>f.value);row.remove();add('carreras_historicas',data);flush();
        });actions.append(retire);
      }
      row.append(actions);section.querySelector('.catalogo-filas').append(row);
    }
    groups.forEach(group=>{
      (initial[group]||[]).forEach(data=>add(group,data));
      panel.querySelector('[data-add="'+group+'"]').addEventListener('click',()=>{add(group,[]);options();flush();rows(group).at(-1)?.querySelector('input').focus();});
    });
    panel.querySelectorAll('[data-tipo]').forEach(field=>{field.checked=(initial.tipos_con_carrera||[]).includes(field.dataset.tipo);field.addEventListener('change',flush);});
    options();flush();payload.hidden=true;panel.hidden=false;
    editor.closest('form').addEventListener('submit',flush);
  });}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize);else initialize();
})();
