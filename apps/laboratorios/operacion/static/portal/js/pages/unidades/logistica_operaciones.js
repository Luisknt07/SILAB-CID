/* Simuladores UPEC: WebGL nativo y cliente de decisiones autoritativas. Sin CDN. */
(function (global) {
  'use strict';
  var TAU = Math.PI * 2;
  var clamp = function (n, a, b) { return Math.max(a, Math.min(b, n)); };
  var finite = function (n, fallback) { var value = Number(n); return Number.isFinite(value) ? value : fallback; };
  var vector = function (v) {
    if (Array.isArray(v) && v.length >= 3) return v.slice(0, 3).map(function (n) { return finite(n, 0); });
    if (v && typeof v === 'object') return [finite(v.x, 0), finite(v.y, 0), finite(v.z, 0)];
    return null;
  };
  var sub = function (a, b) { return a.map(function (n, i) { return n - b[i]; }); };
  var dot = function (a, b) { return a.reduce(function (n, v, i) { return n + v * b[i]; }, 0); };
  var cross = function (a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; };
  var unit = function (v) { var length = Math.hypot.apply(Math, v) || 1; return v.map(function (n) { return n / length; }); };
  var identity = function () { return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; };
  function multiply(a, b) {
    var out = new Array(16).fill(0);
    for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) for (var k = 0; k < 4; k++) out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
    return out;
  }
  function transform(m, v) {
    var a = v.length === 4 ? v : v.concat(1);
    return [0, 1, 2, 3].map(function (r) { return m[r] * a[0] + m[4 + r] * a[1] + m[8 + r] * a[2] + m[12 + r] * a[3]; });
  }
  function inverse(m) {
    var rows = [0, 1, 2, 3].map(function (r) { return [m[r], m[4 + r], m[8 + r], m[12 + r], r === 0 ? 1 : 0, r === 1 ? 1 : 0, r === 2 ? 1 : 0, r === 3 ? 1 : 0]; });
    for (var c = 0; c < 4; c++) {
      var pivot = c;
      for (var r = c + 1; r < 4; r++) if (Math.abs(rows[r][c]) > Math.abs(rows[pivot][c])) pivot = r;
      if (Math.abs(rows[pivot][c]) < 1e-10) return null;
      var swap = rows[c]; rows[c] = rows[pivot]; rows[pivot] = swap;
      var divisor = rows[c][c]; rows[c] = rows[c].map(function (n) { return n / divisor; });
      for (var rr = 0; rr < 4; rr++) if (rr !== c) { var scale = rows[rr][c]; rows[rr] = rows[rr].map(function (n, j) { return n - scale * rows[c][j]; }); }
    }
    var out = new Array(16);
    for (var cc = 0; cc < 4; cc++) for (var row = 0; row < 4; row++) out[cc * 4 + row] = rows[row][cc + 4];
    return out;
  }
  function model(position, scale, angle) {
    var c = Math.cos(angle || 0), s = Math.sin(angle || 0);
    return [c * scale[0], 0, -s * scale[0], 0, 0, scale[1], 0, 0, s * scale[2], 0, c * scale[2], 0, position[0], position[1], position[2], 1];
  }
  function perspective(aspect) {
    var f = 1 / Math.tan(Math.PI / 8), near = .15, far = 250;
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, (2 * far * near) / (near - far), 0];
  }
  function lookAt(eye, target) {
    var z = unit(sub(eye, target)), x = unit(cross([0, 1, 0], z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
  }
  function project(vp, point, width, height) {
    var p = transform(vp, point);
    if (p[3] <= 0) return null;
    var ndc = p.map(function (n) { return n / p[3]; });
    if (ndc[2] < -1 || ndc[2] > 1) return null;
    return { x: (ndc[0] + 1) * width / 2, y: (1 - ndc[1]) * height / 2, depth: ndc[2] };
  }
  function screenRay(vp, x, y) {
    var inv = inverse(vp); if (!inv) return null;
    var a = transform(inv, [x, y, -1, 1]), b = transform(inv, [x, y, 1, 1]);
    a = a.slice(0, 3).map(function (n) { return n / transform(inv, [x, y, -1, 1])[3]; });
    b = b.slice(0, 3).map(function (n) { return n / transform(inv, [x, y, 1, 1])[3]; });
    return { origin: a, direction: unit(sub(b, a)) };
  }
  function intersectBox(ray, bounds) {
    if (!ray || !bounds) return null;
    var low = -Infinity, high = Infinity;
    for (var i = 0; i < 3; i++) {
      if (Math.abs(ray.direction[i]) < 1e-9) { if (ray.origin[i] < bounds.min[i] || ray.origin[i] > bounds.max[i]) return null; }
      else {
        var a = (bounds.min[i] - ray.origin[i]) / ray.direction[i], b = (bounds.max[i] - ray.origin[i]) / ray.direction[i];
        low = Math.max(low, Math.min(a, b)); high = Math.min(high, Math.max(a, b));
      }
    }
    if (high < Math.max(0, low)) return null;
    return Math.max(0, low);
  }
  function normalizeObjects(raw) {
    var values = Array.isArray(raw) ? raw : raw && typeof raw === 'object' ? Object.keys(raw).map(function (id) { return Object.assign({id: id}, raw[id]); }) : [];
    var ids = new Set();
    return values.slice(0, 80).filter(function (o) { return o && o.id !== undefined && String(o.id).length < 180; }).map(function (o) {
      var copy = Object.assign({}, o, {id: String(o.id)});
      copy.nombre = String(o.nombre || o.titulo || o.id);
      copy.acciones = Array.isArray(o.acciones) ? o.acciones.map(function (a) { return String(a && typeof a === 'object' ? a.id : a); }) : [];
      return copy;
    }).filter(function (o) { if (ids.has(o.id)) return false; ids.add(o.id); return true; });
  }
  // Geometrías modulares: un mismo objeto del servidor conserva su ID al moverse.
  var COLORS = {green: [0.02, .39, .23], pale: [.73, .85, .77], yellow: [.98, .78, .18], navy: [.09, .2, .24], blue: [.24, .52, .62], grey: [.58, .67, .64], white: [.93, .97, .94], steel: [.24, .36, .35], orange: [.87, .4, .16], sea: [.37, .64, .72]};
  var REFERENCES = {
    almacen: [
      {id:'recepcion',nombre:'Recepción',tipo:'recepcion',posicion:[-12,0,-6],descripcion:'Comprueba la identidad de la carga y registra su entrada antes de ubicarla.'},
      {id:'calidad',nombre:'Control de calidad',tipo:'calidad',posicion:[-5,0,-6],descripcion:'Identifica condiciones, discrepancias y trazabilidad antes de liberar el material.'},
      {id:'racks',nombre:'Almacenamiento',tipo:'racks',posicion:[4,0,-5],descripcion:'Relaciona ubicación, capacidad y trazabilidad de los productos.'},
      {id:'picking',nombre:'Preparación de pedidos',tipo:'picking',posicion:[6,0,5],descripcion:'Agrupa las referencias del pedido y contrasta cantidades y recorridos.'},
      {id:'empaque',nombre:'Empaque',tipo:'empaque',posicion:[-2,0,6],descripcion:'Consolida y protege la carga, conservando identificación y documentación.'},
      {id:'despacho',nombre:'Despacho',tipo:'despacho',posicion:[-12,0,6],descripcion:'Comprueba el pedido y la autorización de salida antes de despachar.'}
    ],
    puerto: [
      {id:'buque',nombre:'Buque',tipo:'buque',posicion:[-3,0,-7],descripcion:'La secuencia de descarga debe mantener coordinación con el muelle y el patio.'},
      {id:'muelle',nombre:'Muelle',tipo:'muelle',posicion:[-6,0,-1],descripcion:'Interfaz entre el transporte marítimo y la transferencia terrestre.'},
      {id:'grua',nombre:'Grúa de muelle',tipo:'grua',posicion:[1,0,-2],descripcion:'Transfiere contenedores atendiendo seguridad, disponibilidad y secuencia.'},
      {id:'patio',nombre:'Patio de contenedores',tipo:'patio',posicion:[7,0,5],descripcion:'La ubicación influye en las remociones y el tiempo de permanencia.'},
      {id:'puerta',nombre:'Puerta de acceso',tipo:'puerta',posicion:[-11,0,8],descripcion:'Verifica autorización, documentación y sincronización con el transporte terrestre.'}
    ],
    fabrica: [
      {id:'estacion-1',nombre:'Preparación',tipo:'estacion',posicion:[-11,0,-2],descripcion:'Prepara materiales para alimentar el proceso y evitar faltantes.'},
      {id:'estacion-2',nombre:'Transformación',tipo:'estacion',posicion:[-2,0,-2],descripcion:'Compara capacidad, ciclo y acumulación de trabajo en proceso.'},
      {id:'robot',nombre:'Celda robotizada',tipo:'robot',posicion:[7,0,-3],descripcion:'Coordina manipulación, zona de seguridad y transferencia entre estaciones.'},
      {id:'cinta',nombre:'Transferencia',tipo:'cinta',posicion:[-2,0,5],descripcion:'Conecta las estaciones; no elimina un cuello de botella por sí sola.'},
      {id:'estacion-3',nombre:'Control y salida',tipo:'calidad',posicion:[10,0,5],descripcion:'Contrasta producción conforme, errores y disponibilidad para despacho.'}
    ],
    transporte: [
      {id:'hub',nombre:'Centro de distribución',tipo:'hub',posicion:[-11,0,-4],descripcion:'Consolida pedidos y coordina capacidad de los recursos de distribución.'},
      {id:'camion-1',nombre:'Vehículo de reparto',tipo:'camion',posicion:[-1,0,4],descripcion:'Relaciona capacidad, recorridos y restricciones para cumplir una entrega.'},
      {id:'destino-1',nombre:'Punto de entrega',tipo:'destino',posicion:[11,0,-4],descripcion:'La entrega exige comprobar el destino y la evidencia de recepción.'},
      {id:'dron-1',nombre:'Dron conceptual',tipo:'dron',posicion:[8,5,7],descripcion:'Referencia visual de un recurso aéreo. Su operación depende de las reglas del caso y la normativa aplicable.'}
    ],
    tecnologia: [
      {id:'sensor',nombre:'Estación de datos',tipo:'sensor',posicion:[-10,0,-4],descripcion:'La calidad de la lectura y su identificación condicionan la trazabilidad.'},
      {id:'robotica',nombre:'Celda de robótica',tipo:'robot',posicion:[1,0,-3],descripcion:'Observa transferencia, zona de trabajo y restricciones de la misión.'},
      {id:'pronostico',nombre:'Análisis de demanda',tipo:'pronostico',posicion:[9,0,5],descripcion:'Contrasta un pronóstico con los datos observados y el error. La representación no implica un modelo de IA conectado.'}
    ]
  };
  function part(group, type, position, size, color, angle, shadow) {
    group.parts.push({type:type || 'box',position:position,scale:size,color:COLORS[color] || color || COLORS.green,angle:angle || 0,shadow:shadow !== false});
  }
  function box(g, x,y,z, sx,sy,sz,color,angle,shadow) { part(g,'box',[x,y,z],[sx,sy,sz],color,angle,shadow); }
  function cylinder(g,x,y,z,sx,sy,sz,color,angle) { part(g,'cylinder',[x,y,z],[sx,sy,sz],color,angle); }
  function pallet(g,x,z) {
    box(g,x,.18,z,2.2,.25,1.7,'steel');
    for (var j=0;j<3;j++) box(g,x-.67+j*.67,.36,z,.5,.15,1.7,'pale');
    box(g,x,1,z,1.8,1.15,1.4,'yellow');box(g,x,1.6,z,.16,.06,1.42,'white');
  }
  function conveyor(g, length) {
    box(g,0,1.2,0,length,.3,2,'steel');box(g,0,1.39,0,length,.08,1.6,'navy');
    for(var x=-length/2+.3;x<length/2;x+=.65) box(g,x,1.48,0,.09,.12,1.7,'grey');
    [-1,1].forEach(function(s){box(g,s*(length/2-.5),.6,0,.25,1.2,1.6,'steel');});
  }
  function truck(g) {
    box(g,0,1.25,0,5.2,1.9,2.4,'white');box(g,3.4,.95,0,1.8,1.8,2.3,'green');
    box(g,3.45,1.45,0,1.9,.6,2.34,'blue');box(g,3.5,.7,1.18,1.5,.2,.07,'yellow');
    [-1,1].forEach(function(s){[-1.6,1.6,3.5].forEach(function(x){box(g,x,.4,s*1.2,.8,.85,.34,'navy');});});
    box(g,0,.6,0,6.8,.25,1.9,'steel');
  }
  function robot(g) {
    box(g,0,.2,0,4,.3,4,'pale');cylinder(g,0,.7,0,1.3,1.2,1.3,'steel');
    box(g,0,1.5,0,1.15,1,1.15,'yellow');cylinder(g,0,2.15,0,1.3,.45,1.3,'orange');
    box(g,.9,2.7,0,2.2,.5,.7,'yellow',-.28);box(g,1.85,2.4,0,.5,1.3,.65,'orange');
    box(g,2.2,1.9,0,.9,.25,.7,'steel');box(g,2.5,1.65,-.36,.2,.5,.15,'navy');box(g,2.5,1.65,.36,.2,.5,.15,'navy');
    box(g,-1.8,.9,-1.8,.1,1.5,3.6,'green');box(g,0,.9,-1.8,3.6,1.5,.1,'green');
  }
  function rack(g) {
    [-2.4,0,2.4].forEach(function(x){[-1,1].forEach(function(z){box(g,x,2.6,z,.13,5.2,.13,'steel');});});
    [1,2.8,4.6].forEach(function(y){box(g,0,y,0,5.3,.16,2.1,'orange');[-1.2,1.2].forEach(function(x){box(g,x,y+.58,0,1.8,1,1.7,'yellow');box(g,x,y+.6,-.87,.5,.3,.03,'white');});});
  }
  function inferKind(object, scene, state) {
    if(state&&isDistributionCase(state.caso)){if(object.id==='montacargas')return 'montacargas';if(object.tipo==='pedido')return 'pedido';if(object.tipo==='racks')return String(object.id).startsWith('ubicacion-')?'ubicacion':'almacen-control';}
    var exact={pallet:'pallet',contenedor:'contenedor',cliente:'destino',maquina:'estacion',servidor:'pronostico'};
    if(exact[object.tipo])return exact[object.tipo];
    if(state&&state.caso==='robotica-mision'){if(object.tipo==='robot')return 'amr';if(String(object.id).startsWith('inspeccion-'))return 'baliza';}
    var term = [object.tipo,object.zona,object.id,object.nombre].join(' ').toLowerCase();
    var kinds = [['dron',/dron|drone/],['camion',/camion|camión|vehiculo|vehículo|truck/],['grua',/grua|grúa|crane/],['buque',/buque|barco|ship/],['racks',/rack|estanter|ubicacion|ubicación|almacenamiento/],['robot',/robot|brazo|celda/],['recepcion',/recep|ingreso/],['despacho',/despacho|expedici/],['calidad',/calidad|inspec/],['picking',/picking|pedido/],['empaque',/empaque|embal/],['muelle',/muelle|berth/],['patio',/patio|container|contenedor/],['puerta',/puerta|gate/],['cinta',/cinta|banda|transfer|conveyor/],['pronostico',/pronost|forecast|demanda|modelo|datos/],['sensor',/sensor|lect|rfid/],['destino',/destino|cliente|entrega/],['hub',/hub|centro|deposit|depósito/],['estacion',/estaci|station|produc/]];
    for(var i=0;i<kinds.length;i++) if(kinds[i][1].test(term)) return kinds[i][0];
    return scene==='puerto'?'patio':scene==='fabrica'?'estacion':scene==='transporte'?'destino':'pallet';
  }
  function geometryFor(g,kind,state) {
    if(kind==='montacargas'){var broken=g.object.estado==='averiado';box(g,0,.5,0,2.1,.8,2.7,broken?'orange':'green');box(g,0,1.15,-.5,1.7,.5,1.3,'navy');[-.85,.85].forEach(function(x){box(g,x,.26,-.8,.42,.5,.65,'steel');box(g,x,.26,.8,.42,.5,.65,'steel');box(g,x,1.7,-.75,.12,2.4,.12,'steel');box(g,x,1.7,.65,.12,2.4,.12,'steel');box(g,x,1.4,1.2,.12,2.6,.2,'steel');box(g,x,.21,2,.18,.15,1.6,'yellow');});box(g,0,2.9,0,2,.15,1.9,'yellow');}
    else if(kind==='ubicacion'){var location=distributionData(state).ubicaciones.find(function(l){return l.id===g.id;})||{},color=location.clase==='A'?'green':location.clase==='B'?'blue':'orange';[-1.7,1.7].forEach(function(x){[-1.05,1.05].forEach(function(z){box(g,x,1.7,z,.15,3.4,.15,'steel');});});[.3,1.6,3.2].forEach(function(y){box(g,0,y,0,3.6,.12,2.3,'grey');});box(g,0,3.48,0,3.7,.3,2.4,color);var ratio=clamp(finite(location.ocupadas,0)/Math.max(1,finite(location.capacidad,1)),0,1);box(g,-1.9,1.6,0,.16,2.8,.35,'pale');if(ratio>0)box(g,-1.91,.2+ratio*1.4,.01,.2,ratio*2.8,.38,color);}
    else if(kind==='almacen-control'){box(g,0,1.1,0,3.7,2.2,1.5,'green');box(g,0,1.3,.78,3.3,1.5,.06,'white');[-.95,0,.95].forEach(function(x,i){box(g,x,1.2,.83,.55,.8,.06,['green','blue','orange'][i]);});box(g,0,2.35,0,4,.25,1.7,'yellow');}
    else if(kind==='pallet'&&state&&isDistributionCase(state.caso)){var lot=distributionData(state).lotes.find(function(l){return l.id===g.id;})||{},quantity=finite(lot.recibidas,0)>0?finite(lot.saldo,0):Math.max(0,finite(lot.cantidad,0)-finite(lot.rechazadas,0)),ratio=clamp(quantity/Math.max(1,finite(lot.cantidad,1)),0,1);box(g,0,.18,0,2.2,.25,1.7,'steel');for(var slat=0;slat<3;slat++)box(g,-.67+slat*.67,.36,0,.5,.15,1.7,'pale');if(quantity>0){var h=.25+.9*ratio;box(g,0,.44+h/2,0,1.8,h,1.4,'yellow');box(g,0,.44+h+.03,0,.16,.06,1.42,'white');}}
    else if(kind==='pedido'){var order=distributionData(state).pedidos.find(function(p){return p.id===g.id;})||{},prepared=(order.lineas||[]).reduce(function(sum,line){return sum+finite(line.preparadas,0);},0);box(g,0,.22,0,2.5,.35,2.1,'steel');box(g,0,.52,0,2.3,.3,1.9,order.estado==='despachado'?'green':'pale');[-1.1,1.1].forEach(function(x){box(g,x,.85,0,.12,.8,1.9,'steel');});box(g,0,.85,-.9,2.3,.8,.12,'steel');if(prepared>0&&order.estado!=='despachado')box(g,0,.95,0,1.7,.65,1.3,order.embalado?'yellow':'blue');box(g,0,1.65,-.9,.13,1.4,.13,'steel');box(g,0,2.15,-.85,1.5,.7,.08,'white');}
    else if(kind==='baliza'){box(g,0,.1,0,1,.2,1,'pale');cylinder(g,0,.65,0,.1,1.1,.1,'steel');box(g,0,1.3,0,.7,.35,.7,'green');box(g,0,1.53,0,.3,.12,.3,'yellow');}
    else if(kind==='amr'){box(g,0,.55,0,1.3,.7,1.1,'green');box(g,0,.98,0,1.1,.18,.9,'yellow');[-.55,.55].forEach(function(x){box(g,x,.25,-.55,.35,.5,.17,'navy');box(g,x,.25,.55,.35,.5,.17,'navy');});cylinder(g,0,1.2,0,.25,.3,.25,'blue');}
    else if(kind==='contenedor'){box(g,0,.8,0,2.8,1.6,2,'green');for(var r=-1.1;r<1.2;r+=.35)box(g,r,.8,1.02,.04,1.4,.04,'pale');box(g,0,1.65,0,2.9,.08,2.1,'yellow');}
    else if(kind==='racks') rack(g);
    else if(kind==='robot') robot(g);
    else if(kind==='camion') truck(g);
    else if(kind==='cinta') conveyor(g,9);
    else if(kind==='dron') {box(g,0,0,0,1.6,.6,1.2,'green');box(g,0,0,0,5,.13,.22,'steel');box(g,0,0,0,.22,.13,5,'steel');[[2.2,0],[-2.2,0],[0,2.2],[0,-2.2]].forEach(function(p){cylinder(g,p[0],.12,p[1],1.6,.08,1.6,'navy');cylinder(g,p[0],.16,p[1],.35,.18,.35,'yellow');});box(g,0,-.55,0,1.2,.15,.8,'steel');}
    else if(kind==='buque') {box(g,0,.35,0,14,.6,4.7,'navy');box(g,0,.95,0,13,1,4.4,'green');box(g,5.2,2,0,1.8,2.1,3.3,'white');box(g,5.2,2.6,-.02,1.9,.45,3.35,'blue');}
    else if(kind==='grua') {[-2,2].forEach(function(x){box(g,x,4,0,.45,8,.55,'steel');box(g,x,.35,0,2,.5,2.4,'navy');});box(g,0,8,0,5,.55,.9,'yellow');box(g,0,8,-3,.6,.5,8,'yellow');box(g,0,5.8,-4,.08,4,.08,'steel');box(g,0,3.6,-4,2.4,.2,1.4,'orange');box(g,-2.5,5.3,0,1.2,1.2,1.1,'green');}
    else if(kind==='patio') {[-2,1].forEach(function(x,i){[-1.2,1.2].forEach(function(z){[.75,2.25].forEach(function(y,j){box(g,x,y,z,2.8,1.4,2.1,(i+j)%2?'blue':'green');for(var k=-1;k<2;k+=.5) box(g,x+k,y,z+1.06,.04,1.15,.025,'pale');});});});}
    else if(kind==='puerta') {[-2.5,2.5].forEach(function(x){box(g,x,2.2,0,.4,4.4,.6,'steel');});box(g,0,4.4,0,5.5,.6,.7,'green');box(g,-3.8,.9,0,1.8,1.8,2,'white');box(g,-3.8,1.3,-1.01,1.4,.55,.04,'blue');box(g,.3,1.3,0,4.5,.13,.13,'yellow');}
    else if(kind==='muelle') {box(g,0,.24,0,6,.4,3,'grey');box(g,0,.48,-1.4,6,.08,.15,'yellow');[-2,0,2].forEach(function(x){cylinder(g,x,.55,-1.1,.3,.25,.3,'navy');});}
    else if(kind==='recepcion'||kind==='despacho') {box(g,0,.15,0,5,.25,4,'pale');[-2.4,2.4].forEach(function(x){box(g,x,2.4,-1.6,.3,4.8,.3,'green');});box(g,0,4.8,-1.6,5.1,.3,.35,'green');box(g,0,2.4,-1.7,4.4,4.4,.15,'grey');box(g,0,2,-1.8,3.4,3.5,.15,'navy');pallet(g,0,.1);box(g,0,.34,1.8,5,.12,.16,'yellow');}
    else if(kind==='calidad') {box(g,0,1,0,3.7,.25,2.4,'white');[-1.5,1.5].forEach(function(x){box(g,x,.5,0,.18,1,2,'steel');});box(g,-1.1,1.6,0,.65,1.1,.7,'blue');box(g,1,1.5,0,1.2,.75,1,'yellow');box(g,-1.1,2.2,0,.8,.12,.9,'green');}
    else if(kind==='picking'||kind==='empaque') {conveyor(g,5);box(g,0,2.03,0,1.6,1,1.3,kind==='empaque'?'yellow':'pale');box(g,2.6,2.2,-1.6,.15,2.2,.15,'steel');box(g,2.6,3.2,-1.6,1.5,.7,.2,'green');}
    else if(kind==='estacion') {box(g,0,1.3,0,4.2,2.6,3,'green');box(g,0,2.8,0,4.5,.4,3.3,'pale');box(g,-.7,1.7,-1.53,1.2,1.4,.1,'blue');box(g,1,2,-1.55,.7,.4,.12,'navy');cylinder(g,1.35,2.55,-1.6,.18,.2,.18,'yellow');box(g,0,.2,0,4.5,.2,3.5,'steel');}
    else if(kind==='hub'||kind==='destino') {box(g,0,1.65,0,5,3.3,4,'white');box(g,0,3.45,0,5.6,.3,4.6,'green');box(g,0,1.4,2.04,2.5,2.7,.1,'navy');box(g,-1.9,2.2,2.06,.5,.8,.12,'blue');box(g,1.9,2.2,2.06,.5,.8,.12,'blue');box(g,0,3.7,0,1.4,.2,1.4,'yellow');}
    else if(kind==='sensor') {box(g,0,.35,0,3.5,.5,3,'pale');box(g,0,1.9,0,1.4,2.8,1.2,'navy');box(g,0,2.4,.62,1.2,1.5,.04,'blue');box(g,0,1.2,.64,.8,.2,.05,'yellow');box(g,0,3.4,0,.18,1,.18,'steel');cylinder(g,0,3.95,0,.4,.18,.4,'green');}
    else if(kind==='pronostico') {box(g,0,.3,0,6,.5,4,'pale');box(g,0,2.5,-.7,5.8,3.7,.3,'navy');box(g,0,2.5,-.48,5.4,3.3,.08,'white');var observed=state&&state.datos&&Array.isArray(state.datos.serie)?state.datos.serie.slice(-5):null;var bars=observed&&observed.length===5?observed.map(function(v){return Math.max(.12,finite(v,0)/Math.max.apply(Math,[1].concat(observed.map(function(n){return finite(n,0);} )))*2.5);}):[.7,1.4,1.8,1.2,2.5];bars.forEach(function(h,i){box(g,-1.9+i*.95,.9+h/2,-.35,.6,h,.15,i===4?'yellow':'green');});box(g,0,.6,1,5.7,.25,2,'steel');}
    else pallet(g,0,0);
  }
  function boundsFor(g) {
    var min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
    g.parts.forEach(function(p){var c=Math.abs(Math.cos(p.angle)),s=Math.abs(Math.sin(p.angle));var e=[(c*p.scale[0]+s*p.scale[2])/2,p.scale[1]/2,(s*p.scale[0]+c*p.scale[2])/2];for(var i=0;i<3;i++){min[i]=Math.min(min[i],g.position[i]+p.position[i]-e[i]);max[i]=Math.max(max[i],g.position[i]+p.position[i]+e[i]);}});
    return {min:min,max:max};
  }
  function buildScene(sceneName, rawObjects, state) {
    var scene=Object.prototype.hasOwnProperty.call(REFERENCES,sceneName)?sceneName:'almacen';
    var objects=normalizeObjects(rawObjects);if(!objects.length) objects=normalizeObjects(REFERENCES[scene]).map(function(o){return Object.assign(o,{referencia:true,estado:'Referencia visual'});});
    var decor={id:'',parts:[],position:[0,0,0]},groups=[];
    box(decor,0,-.22,0,39,.4,28,'white',0,false);
    for(var x=-18;x<=18;x+=3) box(decor,x,.005,0,.025,.015,26,'pale',0,false);
    for(var z=-12;z<=12;z+=3) box(decor,0,.005,z,37,.015,.025,'pale',0,false);
    if(scene==='puerto') {box(decor,0,.02,-8.2,38,.08,10,'sea',0,false);box(decor,0,.09,-2.9,38,.1,.3,'yellow',0,false);}
    if(scene==='transporte') {var hub=objects.find(function(o){return o.tipo==='hub';}),hp=hub&&vector(hub.posicion)||[0,0,0];objects.filter(function(o){return o.tipo==='cliente'||o.tipo==='destino';}).forEach(function(o){var dp=vector(o.posicion);if(!dp)return;var dx=(dp[0]-hp[0])*1.6,dz=(dp[2]-hp[2])*1.6;box(decor,(dp[0]+hp[0])*.8,.015,(dp[2]+hp[2])*.8,Math.hypot(dx,dz),.05,1.6,'steel',-Math.atan2(dz,dx),false);});}
    else {box(decor,0,.018,0,35,.03,1,'blue',0,false);for(var fx=-15;fx<16;fx+=4){box(decor,fx,.04,0,1.2,.02,.12,'yellow',0,false);}}
    if(state&&isDistributionCase(state.caso)){['recepcion','calidad','racks','picking','empaque','despacho'].slice(1).forEach(function(id,index){var from=objects.find(function(o){return o.id===['recepcion','calidad','racks','picking','empaque'][index];}),to=objects.find(function(o){return o.id===id;}),a=from&&vector(from.posicion),b=to&&vector(to.posicion);if(!a||!b)return;var ax=a[0]*1.6,bx=b[0]*1.6,z=(a[2]+b[2])*.8+3;box(decor,(ax+bx)/2,.09,z,Math.max(.2,Math.abs(bx-ax)),.08,.16,'blue',0,false);box(decor,bx-.5,.1,z-.22,.8,.08,.12,'blue',-.6,false);box(decor,bx-.5,.1,z+.22,.8,.08,.12,'blue',.6,false);});}
    objects.forEach(function(o,i){var ref=REFERENCES[scene].find(function(r){return r.id===o.id||r.tipo===o.tipo;});var pos=vector(o.posicion)||ref&&ref.posicion.slice()||[-13+(i%5)*6,0,-7+Math.floor(i/5)*6];pos=pos.map(function(v,j){return clamp(v,j===1?0:-60,j===1?20:60);});var kind=inferKind(o,scene,state);if(!o.referencia)pos=[pos[0]*1.6,pos[1],pos[2]*1.6];
      // Las coordenadas del motor identifican nodos lógicos, no medidas físicas.
      // Aparcamiento y cubierta evitan ocultar la carga dentro de edificios o cascos.
      if(!o.referencia&&kind==='camion')pos[2]+=4;
      if(!o.referencia&&kind==='contenedor'&&o.estado==='buque'){var ship=objects.find(function(item){return item.tipo==='buque';});var shipPos=ship&&vector(ship.posicion);if(shipPos){var n=objects.filter(function(item){return item.tipo==='contenedor';}).findIndex(function(item){return item.id===o.id;});pos=[shipPos[0]*1.6-3+(n%2)*3.1,1.55,shipPos[2]*1.6+(Math.floor(n/2)-.5)*2];}}
      if(state&&state.caso==='robotica-mision'&&o.id==='sensor')pos[0]-=2.5;var g={id:o.id,title:o.nombre,position:pos,kind:kind,object:o,parts:[]};
      if(!['pallet','contenedor','amr','camion','dron','baliza','pedido','montacargas'].includes(kind))box(g,0,.025,0,kind==='buque'?15:5.5,.04,kind==='buque'?5.2:4.6,'pale',0,false);
      geometryFor(g,kind,state);if(kind==='pallet'&&state&&isDistributionCase(state.caso)){var lot=distributionData(state).lotes.find(function(l){return l.id===g.id;}),product=lot&&distributionData(state).productos.find(function(p){return p.sku===lot.sku;}),tint=product&&product.clase==='B'?COLORS.blue:product&&product.clase==='C'?COLORS.orange:COLORS.green;g.parts.forEach(function(p){if(p.color===COLORS.yellow)p.color=tint;});}var small=kind==='pallet'?.65:kind==='contenedor'?.8:kind==='amr'?.8:1; if(small!==1)g.parts.forEach(function(p){p.position=p.position.map(function(v){return v*small;});p.scale=p.scale.map(function(v){return v*small;});});g.bounds=boundsFor(g);groups.push(g);
    });
    if(state&&state.caso==='robotica-mision'&&state.datos){var d=state.datos;for(var gx=0;gx<8;gx++)for(var gz=0;gz<6;gz++){box(decor,(gx*1.4-7)*1.6,.07,(gz*1.4-3.5)*1.6,2.15,.06,2.15,'pale',0,false);}if(Array.isArray(d.obstaculos))d.obstaculos.slice(0,48).forEach(function(p){box(decor,(p[0]*1.4-7)*1.6,.6,(p[1]*1.4-3.5)*1.6,1.7,1.1,1.7,'orange');});if(Array.isArray(d.ruta))d.ruta.slice(0,48).forEach(function(p){box(decor,(p[0]*1.4-7)*1.6,.14,(p[1]*1.4-3.5)*1.6,.65,.15,.65,'yellow',0,false);});if(Array.isArray(d.meta)){var mx=(d.meta[0]*1.4-7)*1.6,mz=(d.meta[1]*1.4-3.5)*1.6;box(decor,mx,.17,mz,1.7,.1,1.7,'green',0,false);box(decor,mx,.8,mz,.1,1.4,.1,'steel');box(decor,mx+.4,1.3,mz,.8,.5,.08,'yellow');}}
    return {name:scene,caso:state&&state.caso,decor:decor,groups:groups,objects:objects};
  }
  function cubeMesh() {
    var points=[],normals=[];
    var faces=[[[0,0,1],[[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]]],[[0,0,-1],[[.5,-.5,-.5],[-.5,-.5,-.5],[-.5,.5,-.5],[.5,.5,-.5]]],[[1,0,0],[[.5,-.5,.5],[.5,-.5,-.5],[.5,.5,-.5],[.5,.5,.5]]],[[-1,0,0],[[-.5,-.5,-.5],[-.5,-.5,.5],[-.5,.5,.5],[-.5,.5,-.5]]],[[0,1,0],[[-.5,.5,.5],[.5,.5,.5],[.5,.5,-.5],[-.5,.5,-.5]]],[[0,-1,0],[[-.5,-.5,-.5],[.5,-.5,-.5],[.5,-.5,.5],[-.5,-.5,.5]]]];
    faces.forEach(function(face){[0,1,2,0,2,3].forEach(function(i){points.push.apply(points,face[1][i]);normals.push.apply(normals,face[0]);});});return {points:points,normals:normals};
  }
  function cylinderMesh() {
    var points=[],normals=[];
    function vertex(x,y,z,n){points.push(x,y,z);normals.push.apply(normals,n);}
    for(var i=0;i<16;i++){var a=i*TAU/16,b=(i+1)*TAU/16;var x=Math.cos(a)*.5,z=Math.sin(a)*.5,xx=Math.cos(b)*.5,zz=Math.sin(b)*.5;
      [[x,-.5,z],[xx,-.5,zz],[xx,.5,zz],[x,-.5,z],[xx,.5,zz],[x,.5,z]].forEach(function(v){vertex(v[0],v[1],v[2],unit([v[0],0,v[2]]));});
      vertex(0,.5,0,[0,1,0]);vertex(x,.5,z,[0,1,0]);vertex(xx,.5,zz,[0,1,0]);vertex(0,-.5,0,[0,-1,0]);vertex(xx,-.5,zz,[0,-1,0]);vertex(x,-.5,z,[0,-1,0]);
    }return {points:points,normals:normals};
  }

  // Renderer aislado: buffers compartidos, cámara orbital y render bajo demanda.
  function layoutLabels(entries,width,height){
    var placed=[],result=[];entries.slice().sort(function(a,b){return Number(Boolean(b.selected))-Number(Boolean(a.selected))||a.depth-b.depth;}).forEach(function(entry){var w=Math.min(entry.width||100,width-16),h=entry.height||26,best=null;for(var step=0;step<12&&!best;step++){var dy=step===0?0:(step%2?-1:1)*Math.ceil(step/2)*(h+5);for(var candidateX of (width<600?[w/2+8,width-w/2-8]:[entry.x,entry.x-w-6,entry.x+w+6])){var x=clamp(candidateX,w/2+8,width-w/2-8),y=clamp(entry.y+dy,h+8,height-8),rect={left:x-w/2,right:x+w/2,top:y-h,bottom:y};if(!placed.some(function(p){return rect.left<p.right+4&&rect.right>p.left-4&&rect.top<p.bottom+4&&rect.bottom>p.top-4;})){best={id:entry.id,x:x,y:y,rect:rect,anchorX:entry.x,anchorY:entry.y};break;}}}if(!best){var grid=[];for(var gy=h+8;gy<=height-8;gy+=h+6){[w/2+8,width-w/2-8].forEach(function(gx){grid.push({x:gx,y:gy});});}grid.sort(function(a,b){return Math.hypot(a.x-entry.x,a.y-entry.y)-Math.hypot(b.x-entry.x,b.y-entry.y);});for(var candidate of grid){var rectangle={left:candidate.x-w/2,right:candidate.x+w/2,top:candidate.y-h,bottom:candidate.y};if(!placed.some(function(p){return rectangle.left<p.right+4&&rectangle.right>p.left-4&&rectangle.top<p.bottom+4&&rectangle.bottom>p.top-4;})){best={id:entry.id,x:candidate.x,y:candidate.y,rect:rectangle,anchorX:entry.x,anchorY:entry.y};break;}}}if(best){placed.push(best.rect);result.push(best);}});return result;
  }
  function Renderer(canvas, labelRoot, options) {
    this.canvas=canvas;this.labels=labelRoot;this.options=options||{};this.gl=null;this.scene=null;this.selected='';this.frame=0;this.visible=true;this.lost=false;this.reduced=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.camera={yaw:.78,pitch:.66,distance:45,target:[0,1.3,0]};this.vp=identity();this.labelNodes=new Map();this.labelLines=new Map();this.pointer=new Map();this.drag=null;this.transition=null;
    try {this.gl=canvas.getContext('webgl',{alpha:false,antialias:true,stencil:true,preserveDrawingBuffer:false,powerPreference:'low-power'});if(!this.gl) throw new Error('WebGL no disponible');this.setup();this.bind();this.resize();}
    catch(error){this.gl=null;if(this.options.onAvailability) this.options.onAvailability(false);}
  }
  Renderer.prototype.setup=function(){
    var gl=this.gl;
    function shader(type,source){var s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){gl.deleteShader(s);throw new Error('No se pudo compilar la escena');}return s;}
    var vertex=shader(gl.VERTEX_SHADER,'attribute vec3 aPosition;attribute vec3 aNormal;uniform mat4 uModel;uniform mat4 uVP;uniform mat3 uNormal;varying vec3 vNormal;varying vec3 vWorld;void main(){vec4 p=uModel*vec4(aPosition,1.0);vWorld=p.xyz;vNormal=normalize(uNormal*aNormal);gl_Position=uVP*p;}');
    var fragment=shader(gl.FRAGMENT_SHADER,'precision mediump float;varying vec3 vNormal;varying vec3 vWorld;uniform vec4 uColor;uniform float uFlat;uniform vec3 uEye;void main(){vec3 n=normalize(vNormal);vec3 light=normalize(vec3(-0.55,1.0,0.4));float diffuse=max(dot(n,light),0.0);vec3 eye=normalize(uEye-vWorld);float spec=pow(max(dot(n,normalize(light+eye)),0.0),32.0)*0.08;vec3 color=uColor.rgb*(0.58+0.42*diffuse)+spec;float fog=clamp((distance(uEye,vWorld)-45.0)/140.0,0.0,0.20);color=mix(color,vec3(0.83,0.90,0.86),fog);gl_FragColor=vec4(mix(color,uColor.rgb,uFlat),uColor.a);}');
    var program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);gl.deleteShader(vertex);gl.deleteShader(fragment);if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error('No se pudo inicializar la escena');
    this.program=program;this.locations={position:gl.getAttribLocation(program,'aPosition'),normal:gl.getAttribLocation(program,'aNormal'),model:gl.getUniformLocation(program,'uModel'),vp:gl.getUniformLocation(program,'uVP'),norm:gl.getUniformLocation(program,'uNormal'),color:gl.getUniformLocation(program,'uColor'),flat:gl.getUniformLocation(program,'uFlat'),eye:gl.getUniformLocation(program,'uEye')};
    function mesh(data,mode){var p=gl.createBuffer(),n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,p);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data.points),gl.STATIC_DRAW);gl.bindBuffer(gl.ARRAY_BUFFER,n);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data.normals),gl.STATIC_DRAW);return {p:p,n:n,count:data.points.length/3,mode:mode||gl.TRIANGLES};}
    this.meshes={box:mesh(cubeMesh()),cylinder:mesh(cylinderMesh())};
    var corners=[[-.5,-.5,-.5],[.5,-.5,-.5],[.5,-.5,.5],[-.5,-.5,.5],[-.5,.5,-.5],[.5,.5,-.5],[.5,.5,.5],[-.5,.5,.5]],lines=[];
    [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]].forEach(function(edge){lines.push.apply(lines,corners[edge[0]]);lines.push.apply(lines,corners[edge[1]]);});
    this.meshes.outline=mesh({points:lines,normals:lines.map(function(){return 1;})},gl.LINES);
    gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);gl.clearColor(.83,.90,.86,1);if(this.options.onAvailability)this.options.onAvailability(true);
  };
  Renderer.prototype.resize=function(){if(!this.gl)return;var rect=this.canvas.getBoundingClientRect();var ratio=Math.min(global.devicePixelRatio||1,1.5,1600/Math.max(rect.width,1),1000/Math.max(rect.height,1));this.canvas.width=Math.max(1,Math.round(rect.width*ratio));this.canvas.height=Math.max(1,Math.round(rect.height*ratio));if(!this.initialDistance){this.initialDistance=clamp(45/Math.min(1,rect.width/Math.max(1,rect.height)/1.35),45,75);this.camera.distance=this.initialDistance;}this.request();};
  Renderer.prototype.request=function(){var self=this;if(!this.gl||this.lost||!this.visible||this.frame||typeof document!=='undefined'&&document.hidden)return;this.frame=requestAnimationFrame(function(time){self.frame=0;self.render(time);});};
  Renderer.prototype.load=function(name,objects,animate,state){
    var next=buildScene(name,objects,state),before=this.scene;this.transition=null;
    if(animate&&!this.reduced&&before&&before.name===next.name){var from={};before.groups.forEach(function(g){from[g.id]=g.position.slice();});this.transition={from:from,started:0,duration:650};}
    this.scene=next;this.syncLabels();this.request();return next;
  };
  Renderer.prototype.syncLabels=function(){var self=this;this.labels.replaceChildren();this.labelNodes.clear();this.labelLines.clear();if(!this.scene||!this.gl)return;var leaders=document.createElementNS('http://www.w3.org/2000/svg','svg');leaders.classList.add('lo-leaders');leaders.setAttribute('aria-hidden','true');this.labels.appendChild(leaders);this.scene.groups.slice(0,isDistributionCase(this.scene.caso)?32:18).forEach(function(g){var b=document.createElement('button'),line=document.createElementNS('http://www.w3.org/2000/svg','line');b.type='button';b.className='lo-etiqueta-3d';b.textContent=g.title;b.setAttribute('aria-pressed',String(g.id===self.selected));b.addEventListener('click',function(){if(self.options.onSelect)self.options.onSelect(g.id);});leaders.appendChild(line);self.labels.appendChild(b);self.labelNodes.set(g.id,b);self.labelLines.set(g.id,line);});};
  Renderer.prototype.select=function(id){this.selected=id;this.labelNodes.forEach(function(node,key){node.setAttribute('aria-pressed',String(key===id));});this.request();};
  Renderer.prototype.control=function(action){var c=this.camera;if(action==='reiniciar'){c.yaw=.78;c.pitch=.66;c.distance=this.initialDistance||45;c.target=[0,1.3,0];}if(action==='planta'){c.pitch=1.47;c.yaw=0;c.distance=44;}if(action==='acercar')c.distance=clamp(c.distance*.85,12,100);if(action==='alejar')c.distance=clamp(c.distance/ .85,12,100);this.request();};
  Renderer.prototype.drawPart=function(p,offset,shadow){
    var gl=this.gl,l=this.locations,mesh=this.meshes[p.type]||this.meshes.box;
    var pos=p.position.map(function(v,i){return v+offset[i];}),m=model(pos,p.scale,p.angle),c=Math.cos(p.angle),s=Math.sin(p.angle);
    if(shadow)m=multiply([1,0,0,0,.55,0,-.4,0,0,0,1,0,0,.075,0,1],m);
    gl.bindBuffer(gl.ARRAY_BUFFER,mesh.p);gl.vertexAttribPointer(l.position,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(l.position);gl.bindBuffer(gl.ARRAY_BUFFER,mesh.n);gl.vertexAttribPointer(l.normal,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(l.normal);
    gl.uniformMatrix4fv(l.model,false,m);gl.uniformMatrix3fv(l.norm,false,[c/p.scale[0],0,-s/p.scale[0],0,1/p.scale[1],0,s/p.scale[2],0,c/p.scale[2]]);gl.uniform4fv(l.color,shadow?[.06,.16,.11,.16]:p.color.concat(1));gl.uniform1f(l.flat,shadow?1:0);gl.drawArrays(mesh.mode,0,mesh.count);
  };
  Renderer.prototype.render=function(time){
    if(!this.gl||this.lost||!this.scene)return;var gl=this.gl,l=this.locations,c=this.camera,eye=[c.target[0]+Math.sin(c.yaw)*Math.cos(c.pitch)*c.distance,c.target[1]+Math.sin(c.pitch)*c.distance,c.target[2]+Math.cos(c.yaw)*Math.cos(c.pitch)*c.distance];
    this.vp=multiply(perspective(this.canvas.width/this.canvas.height),lookAt(eye,c.target));gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT|gl.STENCIL_BUFFER_BIT);gl.useProgram(this.program);gl.uniformMatrix4fv(l.vp,false,this.vp);gl.uniform3fv(l.eye,eye);
    var self=this,positions={},fraction=1;
    if(this.transition){if(!this.transition.started)this.transition.started=time;fraction=clamp((time-this.transition.started)/this.transition.duration,0,1);fraction=fraction*fraction*(3-2*fraction);}
    this.scene.groups.forEach(function(g){var start=self.transition&&self.transition.from[g.id];positions[g.id]=start?g.position.map(function(v,i){return start[i]+(v-start[i])*fraction;}):g.position;});
    this.scene.decor.parts.forEach(function(p){self.drawPart(p,[0,0,0],false);});
    this.scene.groups.forEach(function(g){g.parts.forEach(function(p){self.drawPart(p,positions[g.id],false);});});
    gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);
    var stencil=gl.getContextAttributes().stencil;if(stencil){gl.enable(gl.STENCIL_TEST);gl.stencilFunc(gl.EQUAL,0,255);gl.stencilOp(gl.KEEP,gl.KEEP,gl.INCR);}
    this.scene.groups.forEach(function(g){g.parts.forEach(function(p){if(p.shadow)self.drawPart(p,positions[g.id],true);});});
    if(stencil)gl.disable(gl.STENCIL_TEST);gl.disable(gl.BLEND);gl.depthMask(true);
    var selected=this.scene.groups.find(function(g){return g.id===self.selected;});
    if(selected){var b=selected.bounds,delta=sub(positions[selected.id],selected.position),center=b.min.map(function(v,i){return(v+b.max[i])/2+delta[i];}),size=b.min.map(function(v,i){return Math.max(.15,b.max[i]-v+.13);});this.drawPart({type:'outline',position:center,scale:size,angle:0,color:COLORS.yellow},[0,0,0],false);}
    var rect=this.canvas.getBoundingClientRect(),candidates=[];this.labelNodes.forEach(function(node,id){var g=self.scene.groups.find(function(item){return item.id===id;}),base=positions[id];var anchor=[base[0],g.bounds.max[1]+base[1]-g.position[1]+.5,base[2]];var p=project(self.vp,anchor,rect.width,rect.height);node.hidden=true;if(self.labelLines.has(id))self.labelLines.get(id).style.display='none';if(p&&p.x>10&&p.x<rect.width-10&&p.y>20&&p.y<rect.height-10)candidates.push({id:id,x:p.x,y:p.y,depth:p.depth,selected:id===self.selected,width:145,height:26});});layoutLabels(candidates,rect.width,rect.height).forEach(function(p){var n=self.labelNodes.get(p.id);n.hidden=false;n.style.left=p.x+'px';n.style.top=p.y+'px';n.style.zIndex=p.id===self.selected?'120':'90';var line=self.labelLines.get(p.id);if(line){line.style.display='';line.setAttribute('x1',p.anchorX);line.setAttribute('y1',p.anchorY);line.setAttribute('x2',p.x);line.setAttribute('y2',p.y-13);}});
    if(this.transition){if(fraction>=1)this.transition=null;else this.request();}
  };
  Renderer.prototype.pick=function(x,y){var rect=this.canvas.getBoundingClientRect(),ray=screenRay(this.vp,(x-rect.left)/rect.width*2-1,1-(y-rect.top)/rect.height*2),best=null,distance=Infinity;this.scene.groups.forEach(function(g){var t=intersectBox(ray,g.bounds);if(t!==null&&t<distance){best=g.id;distance=t;}});if(best&&this.options.onSelect)this.options.onSelect(best);};
  Renderer.prototype.bind=function(){var self=this,canvas=this.canvas;
    canvas.addEventListener('webglcontextlost',function(event){event.preventDefault();self.lost=true;if(self.frame)cancelAnimationFrame(self.frame);self.frame=0;self.labels.hidden=true;if(self.options.onAvailability)self.options.onAvailability(false);});
    canvas.addEventListener('webglcontextrestored',function(){try{self.setup();self.lost=false;self.labels.hidden=false;self.syncLabels();self.resize();}catch(error){self.gl=null;if(self.options.onAvailability)self.options.onAvailability(false);}});
    canvas.addEventListener('pointerdown',function(event){if(event.button!==0)return;self.pointer.set(event.pointerId,{x:event.clientX,y:event.clientY});canvas.setPointerCapture(event.pointerId);self.drag={x:event.clientX,y:event.clientY,moved:false,pinch:0};canvas.classList.add('is-dragging');});
    canvas.addEventListener('pointermove',function(event){if(!self.pointer.has(event.pointerId))return;var previous=self.pointer.get(event.pointerId);self.pointer.set(event.pointerId,{x:event.clientX,y:event.clientY});if(self.pointer.size===2){var p=Array.from(self.pointer.values()),length=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);if(self.drag.pinch)self.camera.distance=clamp(self.camera.distance*self.drag.pinch/Math.max(length,1),12,100);self.drag.pinch=length;self.drag.moved=true;}else{var dx=event.clientX-previous.x,dy=event.clientY-previous.y;self.camera.yaw-=dx*.008;self.camera.pitch=clamp(self.camera.pitch+dy*.006,.12,1.48);if(Math.hypot(event.clientX-self.drag.x,event.clientY-self.drag.y)>5)self.drag.moved=true;}self.request();});
    function release(event){var pick=self.drag&&!self.drag.moved&&self.pointer.size===1;self.pointer.delete(event.pointerId);if(!self.pointer.size){canvas.classList.remove('is-dragging');self.drag=null;}if(pick&&self.scene)self.pick(event.clientX,event.clientY);}
    canvas.addEventListener('pointerup',release);canvas.addEventListener('pointercancel',function(){self.pointer.clear();self.drag=null;canvas.classList.remove('is-dragging');});
    canvas.addEventListener('wheel',function(event){if(!canvas.matches(':focus')&&!event.ctrlKey)return;event.preventDefault();self.camera.distance=clamp(self.camera.distance*Math.exp(clamp(event.deltaY,-120,120)*.003),12,100);self.request();},{passive:false});
    canvas.addEventListener('keydown',function(event){var key=event.key.toLowerCase(),c=self.camera,used=true,step=.9;var right=[Math.cos(c.yaw),0,-Math.sin(c.yaw)],forward=[Math.sin(c.yaw),0,Math.cos(c.yaw)];if(key==='arrowleft')c.yaw+=.1;else if(key==='arrowright')c.yaw-=.1;else if(key==='arrowup')c.pitch=clamp(c.pitch+.08,.12,1.48);else if(key==='arrowdown')c.pitch=clamp(c.pitch-.08,.12,1.48);else if(key==='+'||key==='=')self.control('acercar');else if(key==='-')self.control('alejar');else if(key==='home')self.control('reiniciar');else if('wasd'.includes(key)&&key.length===1){var direction=(key==='a'||key==='d')?right:forward;var sign=(key==='a'||key==='w')?-1:1;c.target=c.target.map(function(n,i){return i===1?n:clamp(n+direction[i]*sign*step,-30,30);});}else used=false;if(used){event.preventDefault();self.request();}});
    if(typeof ResizeObserver==='function'){this.resizeObserver=new ResizeObserver(function(){self.resize();});this.resizeObserver.observe(canvas);}else global.addEventListener('resize',function(){self.resize();});
    if(typeof IntersectionObserver==='function'){this.intersectionObserver=new IntersectionObserver(function(entries){self.visible=entries[0].isIntersecting;if(self.visible)self.request();});this.intersectionObserver.observe(canvas);}
    document.addEventListener('visibilitychange',function(){if(!document.hidden)self.request();});
  };
  // Frontera HTTP: nunca calcula decisiones, resultados o evaluaciones del motor.
  function safeURL(value, base, sameOrigin) {
    try{var url=new URL(String(value),base);var current=new URL(base);if(!/^https?:$/.test(url.protocol)||url.username||url.password||sameOrigin&&url.origin!==current.origin)return null;return url;}catch(error){return null;}
  }
  function createTransport(apiURL,csrf,fetcher,base) {
    var url=safeURL(apiURL,base,true);if(!url)throw new Error('Dirección de API no válida');
    return async function(method,params){var target=new URL(url.href),options={method:method,credentials:'same-origin',headers:{Accept:'application/json'}};
      if(method==='GET'){Object.keys(params||{}).forEach(function(key){if(params[key]!==undefined&&params[key]!==null)target.searchParams.set(key,String(params[key]));});}
      else{options.headers['Content-Type']='application/json';options.headers['X-CSRFToken']=csrf||'';options.body=JSON.stringify(params);}
      var response=await fetcher(target.href,options),data;try{data=await response.json();}catch(error){var malformed=new Error('El servidor no devolvió una respuesta válida. Intenta cargar la práctica otra vez.');malformed.status=response.status;throw malformed;}
      if(!response.ok){var message=data.error||data.detalle||'No se pudo completar la operación.';if(typeof message!=='string')message='No se pudo completar la operación.';var failed=new Error(message);failed.status=response.status;failed.data=data;throw failed;}
      return data;
    };
  }
  function sessionFrom(data){return data&&data.sesion&&typeof data.sesion==='object'?data.sesion:data&&data.estado&&data.id?data:null;}
  function actionChoices(object,caso){var allowed=new Set(object&&object.acciones||[]);return (caso&&Array.isArray(caso.acciones)?caso.acciones:[]).filter(function(a){return a&&allowed.has(String(a.id));});}
  function chartPoints(raw){return (Array.isArray(raw)?raw:[]).slice(-120).filter(function(p){return p&&typeof p==='object';}).map(function(p,i){var rawX=p.paso!==undefined?p.paso:p.x!==undefined?p.x:i,rawY=p.valor!==undefined?p.valor:p.y;var x=rawX===null||rawX===''?NaN:Number(rawX),y=rawY===null||rawY===''?NaN:Number(rawY);return {x:x,y:y};}).filter(function(p){return Number.isFinite(p.x)&&Number.isFinite(p.y);});}

  function parseSeed(value) {
    if(typeof value!=='string'||!/^\d{1,10}$/.test(value))return null;
    var seed=Number(value);return Number.isInteger(seed)&&seed>=0&&seed<=2147483647?seed:null;
  }
  function scenarioURL(base,caseId,seed){
    var url=safeURL(base,base,true);if(!url||typeof caseId!=='string'||!/^[a-z][a-z0-9-]{1,100}$/.test(caseId)||!Number.isInteger(seed)||seed<0||seed>2147483647)return null;
    url.search='';url.hash='';url.searchParams.set('caso',caseId);url.searchParams.set('semilla',String(seed));return url.href;
  }
  function sessionID(value){return typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)?value:null;}
  function isDistributionCase(value){return /^cd-(normal|pico|falla)$/.test(String(value||''));}
  function distributionData(state){
    var d=state&&state.datos||{},result={};
    ['productos','lotes','ubicaciones','pedidos','recursos','eventos','balances','etapas'].forEach(function(key){result[key]=Array.isArray(d[key])?(key==='eventos'?d[key].slice(-120):d[key].slice(0,100)).filter(function(row){return row&&typeof row==='object';}):[];});
    result.resumen=d.resumen&&typeof d.resumen==='object'?d.resumen:{};return result;
  }
  function distributionURL(value,base,caseId,seed,dataset,comparison){
    var url=safeURL(value,base,true);if(!url||!isDistributionCase(caseId))return null;
    if(dataset&&!['productos','ubicaciones','pedidos','recursos'].includes(dataset))return null;
    url.search='';url.searchParams.set('caso',caseId);if(Number.isInteger(seed)&&seed>=0&&seed<=2147483647)url.searchParams.set('semilla',String(seed));
    if(dataset){url.searchParams.set('dataset',dataset);url.hash='';}else if(comparison)url.hash='comparador';
    return url.href;
  }
  function compatibleVersion(session,motorVersion,caseVersion){return !session||session.solo_lectura!==true&&(!motorVersion||session.version_motor===motorVersion)&&(!caseVersion||session.version_caso===caseVersion);}
  function verificationMessage(result){var v=result&&result.verificacion||result||{};return v.verificada===true?'La reproducción en el servidor coincide con la evidencia registrada.':v.verificada===false?'La reproducción no coincide con la evidencia registrada. Conserva el archivo y consulta al administrador.':'El servidor no confirmó coincidencia. Conserva la evidencia y consulta al administrador.';}
  var exported={scenarioURL:scenarioURL,parseSeed:parseSeed,sessionID:sessionID,isDistributionCase:isDistributionCase,distributionData:distributionData,distributionURL:distributionURL,multiply:multiply,transform:transform,inverse:inverse,model:model,perspective:perspective,lookAt:lookAt,project:project,screenRay:screenRay,intersectBox:intersectBox,normalizeObjects:normalizeObjects,buildScene:buildScene,cubeMesh:cubeMesh,cylinderMesh:cylinderMesh,safeURL:safeURL,createTransport:createTransport,sessionFrom:sessionFrom,actionChoices:actionChoices,chartPoints:chartPoints,Renderer:Renderer,layoutLabels:layoutLabels,verificationMessage:verificationMessage,compatibleVersion:compatibleVersion};
  if(typeof module!=='undefined'&&module.exports)module.exports=exported;
  global.UPECLogistica3D=exported;

  // Controlador de interfaz. Los datos originales se presentan sin modificarlos.
  function bootstrap(){
    var main=document.getElementById('operaciones');if(!main)return;
    var $=function(id){return document.getElementById(id);};
    var node=function(tag,text,cls){var n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
    function json(id,fallback){try{return JSON.parse($(id).textContent);}catch(error){return fallback;}}
    var catalog=json('logistica-catalogo',[]);if(!Array.isArray(catalog)||!catalog.length)return;
    var initial=json('logistica-datos-iniciales',{}),initialCase=json('logistica-caso-inicial','');
    var caseId=typeof initialCase==='string'?initialCase:initialCase&&initialCase.id;
    var caso=catalog.find(function(c){return c.id===caseId||c.id===initial.caso;})||catalog[0];
    var live=null,view=initial.estado&&initial.caso===caso.id?initial.estado:{caso:caso.id,objetos:[],kpis:[],series:[],historial:[]},selected='',objects=[],busy=false,page=1,nextPage=null,previousPage=null,chartChoice='';
    var cdTableChoice='lotes',querySeed=parseSeed(new URL(global.location.href).searchParams.get('semilla'));
    if(querySeed!==null)$('lo-semilla').value=String(querySeed);else if(Number.isInteger(view.semilla))$('lo-semilla').value=String(view.semilla);
    var originalSeed=parseSeed($('lo-semilla').value);
    var transport=null;
    try{transport=createTransport(main.dataset.api,$('operaciones').querySelector('[name=csrfmiddlewaretoken]')?.value||'',global.fetch.bind(global),global.location.href);}catch(error){message(error.message,true);}
    var renderer=new Renderer($('lo-canvas'),$('lo-etiquetas'),{onSelect:selectObject,onAvailability:function(available){$('lo-fallback').hidden=available;$('lo-canvas').hidden=!available;$('lo-render-estado').textContent=available?'WebGL · profundidad y luz':'Alternativa accesible · lista de objetos';}});
    function message(text,error,success){var area=$('lo-mensaje');area.textContent=text;area.className='lo-mensaje'+(error?' is-error':success?' is-exito':'');}
    function number(value){if(typeof value==='number'&&Number.isFinite(value))return new Intl.NumberFormat('es-EC',{maximumFractionDigits:3}).format(value);return value===null||value===undefined?'—':String(value);}
    function updateBusy(value){busy=value;main.setAttribute('aria-busy',String(value));['lo-iniciar','lo-exportar','lo-verificar','lo-partidas-abrir','lo-partidas-anterior','lo-partidas-siguiente','lo-objeto','lo-semilla'].forEach(function(id){if($(id))$(id).disabled=value;});if(!value){$('lo-partidas-anterior').disabled=!previousPage;$('lo-partidas-siguiente').disabled=!nextPage;}renderActions();}
    async function failure(error,refreshConflict){
      if(error.status===409&&live&&refreshConflict){try{var latest=await transport('GET',{sesion:live.id});apply(latest);message(compatible()?'La práctica cambió en otra ventana. Se cargó su última revisión; revisa el estado antes de decidir de nuevo.':error.message,true);return;}catch(refreshError){message(refreshError.message,true);return;}}
      message(error.message||'No se pudo comunicar con el servidor.',true);
      if(error.status===401){var link=node('a',' Acceder de nuevo');link.href=main.dataset.login;link.target='_top';$('lo-mensaje').appendChild(link);}
    }
    async function perform(work,refreshConflict){if(busy||!transport)return;updateBusy(true);try{await work();}catch(error){await failure(error,refreshConflict);}finally{updateBusy(false);}}
    function compatible(){return compatibleVersion(live,caso.version_motor||initial.estado&&initial.estado.version_motor,caso.version);}
    function renderCase(){
      $('lo-area').textContent=caso.area||'Escenario logístico';$('lo-caso-titulo').textContent=caso.titulo;$('lo-objetivo').textContent=caso.objetivo||caso.resumen||'';
      document.querySelectorAll('[data-caso]').forEach(function(link){if(link.dataset.caso===caso.id)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');});
      $('lo-reglas').replaceChildren();(caso.reglas||[]).forEach(function(rule){$('lo-reglas').appendChild(node('li',rule));});
      $('lo-fuentes').replaceChildren();(caso.fuentes||[]).forEach(function(source){var url=safeURL(source.url,global.location.href,false);if(!url)return;var li=node('li'),a=node('a',source.titulo||url.hostname);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';li.appendChild(a);$('lo-fuentes').appendChild(li);});
      if(caso.id==='robotica-mision')$('lo-escena-leyenda').lastElementChild.textContent='Cuadrícula del motor: bloques naranjas = obstáculos; marcas amarillas = ruta A*; bandera = meta. Esquema educativo, sin control de equipos.';
      else if(isDistributionCase(caso.id))$('lo-escena-leyenda').lastElementChild.textContent='Flujo: recepción → calidad → ubicación ABC → preparación → empaque → despacho. A verde, B azul, C naranja. Geometría esquemática; cantidades, distancias y acciones calculadas por el motor.';
      else $('lo-escena-leyenda').lastElementChild.textContent='Esquema 3D educativo; no representa el plano ni el inventario del laboratorio.';
    }
    function apply(data){
      var session=sessionFrom(data);if(!session||!session.estado||!session.id)throw new Error('La respuesta no contiene una práctica válida.');
      var actual=catalog.find(function(c){return c.id===session.caso||c.id===session.estado.caso;});if(!actual)throw new Error('La práctica corresponde a un caso no disponible.');
      var switched=caso.id!==actual.id,changedSession=!live||live.id!==session.id;if(changedSession)selected='';caso=actual;live=session;view=session.estado;renderCase();renderState(!switched);if(switched)renderer.control('reiniciar');
      var url=new URL(global.location.href);url.searchParams.set('caso',caso.id);if(sessionID(String(session.id)))url.searchParams.set('sesion',session.id);var actualSeed=Number.isInteger(session.semilla)?session.semilla:view.semilla;if(Number.isInteger(actualSeed))url.searchParams.set('semilla',String(actualSeed));try{global.history.replaceState(null,'',url.href);}catch(error){/* Un iframe puede limitar la navegación del historial. */}
      var seed=Number.isInteger(session.semilla)?session.semilla:view.semilla;if(Number.isInteger(seed))$('lo-semilla').value=String(seed);renderDistributionLinks();
      message(view.mensaje||'Práctica actualizada.',false,Boolean(view.terminada));
    }
    function renderState(animate){
      var scene=renderer.load(caso.escena,view.objetos,Boolean(animate),view);objects=scene.objects;
      $('lo-objeto').replaceChildren();objects.forEach(function(o){var option=node('option',o.nombre+(o.acciones.length?' · '+o.acciones.length+' decisiones':''));option.value=o.id;$('lo-objeto').appendChild(option);});
      if(!objects.some(function(o){return o.id===selected;}))selected=(objects.find(function(o){return live&&o.acciones.length;})||objects[0]||{}).id||'';
      selectObject(selected);$('lo-modo').textContent=live?(!compatible()?'Práctica histórica':view.terminada?'Práctica finalizada':'Práctica guardada'):'Exploración';$('lo-revision').textContent=live?'Revisión '+number(live.revision)+' · paso '+number(view.paso||0):'Vista inicial · sin decisiones';
      $('lo-datos-origen').textContent=live?'Estado validado por el servidor':'Vista inicial · datos sintéticos';if($('lo-iniciar'))$('lo-iniciar').textContent=live?'Iniciar otra práctica':'Iniciar práctica guardada';
      $('lo-evidencia').hidden=!(live&&view.terminada);$('lo-verificacion').textContent='';renderKPIs();renderTable();renderCharts();renderHistory();renderDistribution();
    }
    function selectObject(id){selected=id;var object=objects.find(function(o){return o.id===id;});if(!object)return;renderer.select(id);$('lo-objeto').value=id;$('lo-objeto-nombre').textContent=object.nombre;$('lo-objeto-estado').textContent=object.estado||'Disponible';$('lo-objeto-descripcion').textContent=object.descripcion||'Consulta las reglas del escenario antes de decidir.';
      var fields=[['Zona',object.zona],['Tipo',object.tipo]],d=view.datos||{};
      if(isDistributionCase(caso.id)){var cd=distributionData(view),lot=cd.lotes.find(function(l){return l.id===id;}),order=cd.pedidos.find(function(p){return p.id===id;}),location=cd.ubicaciones.find(function(l){return l.id===id;}),resource=cd.recursos.find(function(r){return r.id===id;});
        if(lot){fields.push(['SKU',lot.sku],['Lote',lot.lote],['Cantidad',lot.cantidad],['Saldo disponible',lot.saldo],['Ubicación',lot.ubicacion||'Por ubicar']);if(lot.inspeccionado&&Object.prototype.hasOwnProperty.call(lot,'defectuosas'))fields.push(['Unidades no conformes',lot.defectuosas]);else fields.push(['Calidad','Sin inspeccionar']);}
        if(order)fields.push(['Prioridad',order.prioridad],['Promesa',number(order.prometido_min)+' min'],['Preparación',(order.lineas||[]).map(function(l){return l.sku+': '+number(l.preparadas)+' / '+number(l.cantidad);}).join(' · ')],['Empaque',order.embalado?'Completo':'Pendiente'],['OTIF',order.otif===null||order.otif===undefined?'Pendiente':order.otif?'Cumple':'No cumple']);
        if(location)fields.push(['Clase ABC',location.clase],['Capacidad',location.capacidad],['Ocupación',location.ocupadas]);
        if(resource)fields.push(['Disponibilidad',resource.estado],['Recuperación',resource.recuperacion_en===null?'—':number(resource.recuperacion_en)+' min']);
      }
      if(d.pallets){var p=d.pallets.find(function(pallet){return pallet.id===id;});if(p){fields.push(['Lote FIFO',p.lote]);if(Object.prototype.hasOwnProperty.call(p,'dano'))fields.push(['Inspección',p.dano?'Daño detectado':'Conforme']);}}
      if(d.contenedores){var c=d.contenedores.find(function(container){return container.id===id;});if(c)fields.push(['Carga',c.frio?'Refrigerada':'Seca'],['Documentación',c.documentos?'Validada':'Por validar']);}
      if(d.clientes){var client=d.clientes.find(function(c){return c.id===id;});if(client)fields.push(['Demanda',number(client.demanda)+' unidades'],['Ventana',client.ventana.map(number).join('–')+' min']);}
      $('lo-objeto-datos').replaceChildren();fields.forEach(function(field){if(field[1]!==null&&field[1]!==undefined&&field[1]!==''){$('lo-objeto-datos').appendChild(node('dt',field[0]));$('lo-objeto-datos').appendChild(node('dd',number(field[1])));}});renderActions();
    }

    function renderScenarioLinks(){
      var seed=parseSeed($('lo-semilla').value),shown=Number.isInteger(view.semilla)?view.semilla:originalSeed,preserved=seed===null?shown:seed;
      document.querySelectorAll('[data-caso]').forEach(function(link){var href=scenarioURL(global.location.href,link.dataset.caso,preserved);if(href)link.href=href;});
      var help=$('lo-semilla-ayuda');if(help)help.textContent=seed===null?'Introduce una semilla entera entre 0 y 2147483647. Los datos visibles conservan su semilla actual.':seed!==shown?'Los datos visibles conservan la semilla '+number(shown)+'. La semilla '+number(seed)+' se aplicará al iniciar '+(live?'otra práctica':'la práctica')+' o abrir otro escenario.':'Semilla '+number(seed)+' de los datos visibles. Consérvala para comparar estrategias.';
    }
    function renderDistributionLinks(){
      renderScenarioLinks();
      // Los archivos documentan la escena visible, no una semilla todavía pendiente.
      var seed=Number.isInteger(view.semilla)?view.semilla:originalSeed,base=global.location.href,guide=$('lo-guia-distribucion'),compare=$('lo-comparar');
      [guide,compare].forEach(function(link){if(!link)return;if(!link.dataset.originalHref)link.dataset.originalHref=link.href;var href=distributionURL(link.dataset.originalHref,base,caso.id,seed,null,link===compare);if(href)link.href=href;});
      var downloads=$('lo-cd-descargas');if(!downloads)return;downloads.replaceChildren();if(!guide||!isDistributionCase(caso.id))return;
      [['productos','Productos'],['ubicaciones','Ubicaciones'],['pedidos','Pedidos'],['recursos','Recursos']].forEach(function(item){var href=distributionURL(guide.dataset.originalHref,base,caso.id,seed,item[0]);if(!href)return;var a=node('a',item[1]+' · CSV','lo-boton is-pequeno');a.href=href;downloads.appendChild(a);});
    }
    function renderDistribution(){
      var panel=$('lo-cd-panel');renderDistributionLinks();if(!panel)return;panel.hidden=!isDistributionCase(caso.id);if(panel.hidden)return;
      var d=distributionData(view),summary=d.resumen;$('lo-cd-progreso').textContent=number(summary.completados)+' / '+number(summary.total_pedidos)+' pedidos despachados · '+number(summary.unidades_despachadas)+' / '+number(summary.unidades_solicitadas)+' cajas despachadas';
      $('lo-cd-reloj').textContent=number(view.minutos||0)+' min de operación';var stages=$('lo-cd-etapas');stages.replaceChildren();
      d.etapas.forEach(function(stage,index){var li=node('li'),station=objects.find(function(o){return o.id===({control:'calidad',ubicacion:'racks',embalaje:'empaque'}[stage.id]||stage.id);}),a=node(station?'button':'div');if(station){a.type='button';a.addEventListener('click',function(){selectObject(station.id);$('lo-objeto').focus();});}a.appendChild(node('small','0'+(index+1)));a.appendChild(node('strong',stage.titulo));a.appendChild(node('span',stage.estado+(Number.isFinite(stage.completados)&&Number.isFinite(stage.total)?' · '+number(stage.completados)+' / '+number(stage.total):'')));li.appendChild(a);stages.appendChild(li);});
      var occupancy=$('lo-cd-ocupacion');occupancy.replaceChildren();d.ubicaciones.forEach(function(location){var occupied=finite(location.ocupadas,0),capacity=finite(location.capacidad,0),button=node('button',undefined,'lo-cd-ubicacion');button.type='button';button.appendChild(node('strong',location.codigo||location.id));button.appendChild(node('small','Clase '+String(location.clase||'—')+' · '+number(occupied)+' / '+number(capacity)));var meter=node('meter');meter.min=0;meter.max=Math.max(1,capacity);meter.value=clamp(occupied,0,Math.max(1,capacity));meter.setAttribute('aria-label','Ocupación de '+String(location.codigo||location.id));button.appendChild(meter);button.setAttribute('aria-label',String(location.codigo||location.id)+': '+number(occupied)+' de '+number(capacity)+' cajas ocupadas');button.addEventListener('click',function(){var station=objects.find(function(o){return o.id===location.id;})||objects.find(function(o){return o.id==='racks';});if(station){selectObject(station.id);$('lo-objeto').focus();}});occupancy.appendChild(button);});
    }
    function renderActions(){
      $('lo-acciones').replaceChildren();var object=objects.find(function(o){return o.id===selected;});var choices=actionChoices(object,caso);
      if(live&&!view.terminada&&compatible()){choices.forEach(function(action){var button=node('button',action.titulo);button.type='button';button.disabled=busy;var confirmClose=false;button.addEventListener('click',function(){if(isDistributionCase(caso.id)&&action.id==='cerrar'&&!confirmClose){confirmClose=true;button.textContent='Confirmar cierre con resultados parciales';$('lo-acciones-ayuda').textContent='Esta decisión finaliza la práctica y conserva los faltantes en el resultado. Pulsa otra vez para confirmar o selecciona otro objeto para continuar.';return;}var decision={accion:String(action.id),objeto:String(object.id)};perform(async function(){var response=await transport('POST',{accion:'actuar',sesion:live.id,revision:live.revision,decision:decision});apply(response);},true);});$('lo-acciones').appendChild(button);});}
      $('lo-acciones-ayuda').textContent=!live?'Inicia una práctica para habilitar las decisiones del motor.':!compatible()?'Práctica de una versión anterior: consulta sus datos y conserva la evidencia. Inicia otra para usar el motor actual.':view.terminada?'Caso concluido. Consulta la evidencia o inicia otra práctica con la misma semilla.':choices.length?'Cada decisión actualiza el estado, el tiempo y los indicadores.':'Este objeto no tiene decisiones disponibles en su estado actual. Selecciona otro objeto.';
    }
    function renderKPIs(){
      $('lo-kpis').replaceChildren();var kpis=Array.isArray(view.kpis)?view.kpis:[];
      kpis.slice(0,16).forEach(function(kpi){var card=node('article',undefined,'lo-kpi');card.appendChild(node('h3',kpi.titulo||kpi.id));var value=node('strong',number(kpi.valor));card.appendChild(value);card.appendChild(node('small',kpi.unidad||''));$('lo-kpis').appendChild(card);});
      if(live&&view.terminada&&typeof view.puntaje==='number'){var score=node('article',undefined,'lo-kpi is-puntaje');score.appendChild(node('h3','Puntaje didáctico'));score.appendChild(node('strong',number(view.puntaje)));score.appendChild(node('small','/100 · calculado por el servidor'));$('lo-kpis').appendChild(score);}
    }
    function table(title,headers,rows,caption,maxRows){var limit=Math.min(120,Math.max(1,Number.isInteger(maxRows)?maxRows:100)),root=node('section');root.appendChild(node('h3',title));var wrap=node('div',undefined,'lo-tabla-scroll'),t=node('table');if(caption)t.appendChild(node('caption',caption));var head=node('thead'),hr=node('tr');headers.forEach(function(h){var th=node('th',h);th.scope='col';hr.appendChild(th);});head.appendChild(hr);t.appendChild(head);var body=node('tbody');rows.slice(0,limit).forEach(function(row){var tr=node('tr');if(row.highlight)tr.className='is-elegido';row.cells.forEach(function(cell){var td=node('td');if(cell&&typeof cell==='object'&&cell.object){var b=node('button',cell.text);b.type='button';b.addEventListener('click',function(){selectObject(cell.object);$('lo-objeto').focus();});td.appendChild(b);}else td.textContent=number(cell);tr.appendChild(td);});body.appendChild(tr);});t.appendChild(body);wrap.appendChild(t);root.appendChild(wrap);return root;}

    function renderDistributionTables(target){
      var d=distributionData(view),tabs=[['lotes','Lotes e inventario'],['pedidos','Pedidos'],['ubicaciones','Ubicaciones ABC'],['productos','Productos'],['recursos','Recursos'],['eventos','Eventos'],['balances','Balance por SKU']],nav=node('div',undefined,'lo-cd-tablas-nav');nav.setAttribute('aria-label','Seleccionar datos operativos');
      var active=node('section',undefined,'lo-cd-tabla-activa');active.id='lo-cd-tabla-activa';
      function content(){active.replaceChildren();var rows=[],headers=[],caption='',title=(tabs.find(function(tab){return tab[0]===cdTableChoice;})||tabs[0])[1];
        if(cdTableChoice==='lotes'){headers=['Lote','SKU','Cantidad (cajas)','Estado','Calidad','Saldo (cajas)','Ubicación'];rows=d.lotes.map(function(l){return {cells:[{text:l.id,object:l.id},l.sku,l.cantidad,l.estado,l.inspeccionado?(Object.prototype.hasOwnProperty.call(l,'defectuosas')?number(l.defectuosas)+' no conformes':'Inspeccionado'):'Sin inspeccionar',l.saldo,l.ubicacion||'—']};});caption='La condición de calidad se revela al inspeccionar. El saldo y la ubicación proceden del registro del servidor.';}
        if(cdTableChoice==='pedidos'){headers=['Pedido','Prioridad','Promesa (min)','SKU / preparado de solicitado','Estado','Salida (min)','OTIF'];rows=d.pedidos.map(function(p){return {cells:[{text:p.id,object:p.id},p.prioridad,p.prometido_min,(Array.isArray(p.lineas)?p.lineas:[]).map(function(l){return l.sku+': '+number(l.preparadas)+' / '+number(l.cantidad);}).join(' · '),p.estado,p.despachado_en,p.otif===null||p.otif===undefined?'Pendiente':p.otif?'Cumple':'No cumple']};});caption='Cada preparación retira una unidad con la regla FIFO del motor. OTIF se determina al despachar.';}
        if(cdTableChoice==='ubicaciones'){headers=['Ubicación','Zona','Clase ABC','Capacidad (cajas)','Ocupación (cajas)','Disponible (cajas)'];rows=d.ubicaciones.map(function(l){return {cells:[{text:l.codigo||l.id,object:l.id},l.zona,l.clase,l.capacidad,l.ocupadas,Math.max(0,finite(l.capacidad,0)-finite(l.ocupadas,0))]};});caption='Capacidad en cajas normalizadas de 30 × 20 × 15 cm. El pallet representa un lote agrupado; no implica una posición de carga certificada.';}
        if(cdTableChoice==='productos'){headers=['SKU','Producto','Clase ABC','Unidad','Peso (kg)','Dimensiones (cm)'];rows=d.productos.map(function(p){return {cells:[p.sku,p.nombre,p.clase,p.unidad,p.peso_kg,Array.isArray(p.dimensiones_cm)?p.dimensiones_cm.join(' × '):p.dimensiones_cm]};});caption='Catálogo sintético del caso. No representa existencias reales de la universidad.';}
        if(cdTableChoice==='recursos'){headers=['Recurso','Estado','Fallo (min)','Recuperación (min)'];rows=d.recursos.map(function(r){return {cells:[{text:r.nombre||r.id,object:r.id},r.estado,r.fallo_en,r.recuperacion_en]};});caption='Comprueba disponibilidad y horarios planificados de contingencia. Los eventos registrados y las acciones permitidas proceden del servidor.';}
        if(cdTableChoice==='eventos'){headers=['Evento','Minuto','Objeto','Descripción'];rows=d.eventos.map(function(e){return {cells:[e.tipo,e.minuto,e.objeto,e.descripcion]};});caption='Eventos registrados hasta el reloj actual. La contingencia planificada se explica en las reglas y en los recursos.';var totalEvents=Array.isArray(view.datos&&view.datos.eventos)?view.datos.eventos.length:0;if(totalEvents>d.eventos.length)caption+=' Se muestran los últimos '+number(d.eventos.length)+' de '+number(totalEvents)+' eventos. La evidencia JSON conserva el registro completo.';}
        if(cdTableChoice==='balances'){headers=['SKU','Entrada','Pendiente','Rechazo inspección','Disponible','Preparado','Despachado','Rechazado','Diferencia'];rows=d.balances.map(function(b){return {cells:[b.sku,b.entrada,b.pendiente,b.inspeccion_rechazo,b.disponible,b.preparado,b.despachado,b.rechazado,b.diferencia]};});caption='Contrasta el balance de conservación por SKU. Una diferencia distinta de cero requiere revisar la evidencia.';}
        if(rows.length)active.appendChild(table(title,headers,rows,caption,cdTableChoice==='eventos'?120:100));else{active.appendChild(node('h3',title));active.appendChild(node('p',cdTableChoice==='eventos'?'Todavía no hay eventos revelados.':'No hay registros disponibles en esta versión de la práctica.','lo-vacio'));}
      }
      tabs.forEach(function(tab){var button=node('button',tab[1]);button.type='button';button.setAttribute('aria-pressed',String(tab[0]===cdTableChoice));button.setAttribute('aria-controls','lo-cd-tabla-activa');button.addEventListener('click',function(){cdTableChoice=tab[0];Array.from(nav.children).forEach(function(other){other.setAttribute('aria-pressed',String(other===button));});content();});nav.appendChild(button);});target.appendChild(nav);target.appendChild(active);content();
    }
    function renderTable(){var d=view.datos||{},target=$('lo-tabla-operativa');target.replaceChildren();
      if(isDistributionCase(caso.id)){renderDistributionTables(target);return;}
      if(Array.isArray(d.pallets)){target.appendChild(table('Trazabilidad por lote',['Objeto','Lote','Estado','Inspección'],d.pallets.map(function(p){return {cells:[{text:p.id,object:p.id},p.lote,p.estado,Object.prototype.hasOwnProperty.call(p,'dano')?(p.dano?'Daño detectado':'Conforme'):'Sin inspeccionar']};}),'Selecciona un pallet para intervenir. La condición de calidad se revela al inspeccionar.'));}
      else if(Array.isArray(d.contenedores)){target.appendChild(table('Flujo de contenedores',['Objeto','Carga','Estado','Documentos','Salida (min)'],d.contenedores.map(function(c){return {cells:[{text:c.id,object:c.id},c.frio?'Refrigerada':'Seca',c.estado,c.documentos?'Validados':'Por validar',c.salida]};}),'Datos sintéticos de la terminal. El estado documental no constituye autorización aduanera.'));}
      else if(Array.isArray(d.buffers)){target.appendChild(table('Balance de la línea',['Estación','En proceso (unid.)','Capacidad (unid./5 min)'],d.buffers.map(function(b,i){return {cells:[{text:'Estación '+(i+1),object:'estacion-'+(i+1)},b,d.capacidades&&d.capacidades[i]]};}),'Una unidad avanza como máximo una estación por intervalo; comprueba acumulación y capacidad.'));}
      else if(Array.isArray(d.clientes)){target.appendChild(table('Pedidos y ventanas de entrega',['Cliente','Pedido (unid.)','Ventana (min)','Estado','Llegada (min)'],d.clientes.map(function(c){return {cells:[{text:c.id,object:c.id},c.demanda,c.ventana.map(number).join('–'),c.entregado?(c.tardia?'Entregado tarde':'Entregado'):'Pendiente',c.llegada]};}),'Red sintética. Las distancias del motor son euclidianas; la escena no es un mapa geográfico.'));}
      else if(Array.isArray(d.modelos)){var names={ultimo:'Último valor',media4:'Media móvil de 4 semanas',regresion:'Regresión con tendencia y estacionalidad'};if(d.modelos.length)target.appendChild(table('Comparación temporal de candidatos',['Modelo','MAE de validación','Selección'],d.modelos.map(function(m){return {highlight:m.id===d.seleccionado,cells:[names[m.id]||m.id,m.mae_validacion,m.id===d.seleccionado?'Seleccionado':'—']};}),'El MAE de validación selecciona el modelo; la prueba reservada se consulta una única vez al evaluar.'));
        var note=node('p',d.evaluado?'Prueba revelada al finalizar. MAE del modelo: '+number(d.mae_prueba)+'; referencia de último valor: '+number(d.mae_referencia)+'.':'Partición temporal: entrenamiento 1–36, validación 37–48; prueba 49–60 reservada. Los datos de prueba no se muestran antes de evaluar.');target.appendChild(note);
      }
    }
    function svgNode(tag,attributes,text){var el=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attributes||{}).forEach(function(k){el.setAttribute(k,String(attributes[k]));});if(text!==undefined)el.textContent=String(text);return el;}
    function drawChart(title,unitLabel,series,xLabel){
      var valid=series.map(function(s){return {titulo:s.titulo,puntos:chartPoints(s.puntos),color:s.color||'#00673c'};}).filter(function(s){return s.puntos.length;});if(!valid.length)return node('p','No hay puntos registrados para esta serie.','lo-vacio');
      var all=valid.reduce(function(a,s){return a.concat(s.puntos);},[]),xmin=Math.min.apply(Math,all.map(function(p){return p.x;})),xmax=Math.max.apply(Math,all.map(function(p){return p.x;})),ymin=Math.min(0,Math.min.apply(Math,all.map(function(p){return p.y;}))),ymax=Math.max.apply(Math,all.map(function(p){return p.y;}));if(xmin===xmax){xmin-=1;xmax+=1;}if(ymin===ymax)ymax=ymin+1;var pad=(ymax-ymin)*.07;ymax+=pad;
      var sx=function(x){return 56+(x-xmin)/(xmax-xmin)*450;},sy=function(y){return 190-(y-ymin)/(ymax-ymin)*158;};
      var figure=node('figure'),svg=svgNode('svg',{viewBox:'0 0 540 230',role:'img','aria-label':title+'. '+unitLabel+'. Datos del servidor; tabla disponible debajo.'});
      for(var i=0;i<5;i++){var y=ymin+(ymax-ymin)*i/4,yy=sy(y);svg.appendChild(svgNode('line',{x1:56,y1:yy,x2:506,y2:yy,stroke:'#e4ece6','stroke-width':1}));svg.appendChild(svgNode('text',{x:48,y:yy+3,'text-anchor':'end',fill:'#536e60','font-size':9},number(y)));}
      [xmin,(xmin+xmax)/2,xmax].forEach(function(x){svg.appendChild(svgNode('text',{x:sx(x),y:207,'text-anchor':'middle',fill:'#536e60','font-size':9},number(x)));});svg.appendChild(svgNode('text',{x:281,y:224,'text-anchor':'middle',fill:'#536e60','font-size':9},xLabel||'Paso de decisión'));
      valid.forEach(function(s){svg.appendChild(svgNode('polyline',{points:s.puntos.map(function(p){return sx(p.x)+','+sy(p.y);}).join(' '),fill:'none',stroke:s.color,'stroke-width':2.3,'stroke-linejoin':'round'}));s.puntos.forEach(function(p){var circle=svgNode('circle',{cx:sx(p.x),cy:sy(p.y),r:s.puntos.length>60?1.5:2.5,fill:s.color});circle.appendChild(svgNode('title',null,s.titulo+': '+number(p.y)+' '+unitLabel+' · '+(xLabel||'paso')+' '+number(p.x)));svg.appendChild(circle);});});figure.appendChild(svg);figure.appendChild(node('figcaption',unitLabel+' · '+all.length+' observaciones disponibles. Cada serie conserva su unidad.'));
      if(valid.length>1){var legend=node('div',undefined,'lo-serie-leyenda');valid.forEach(function(s,i){legend.appendChild(node('span',s.titulo,i?'is-prediccion':''));});figure.appendChild(legend);}
      var details=node('details'),summary=node('summary','Ver los datos de la gráfica');details.appendChild(summary);var rows=[];valid.forEach(function(s){s.puntos.forEach(function(p){rows.push({cells:[s.titulo,p.x,p.y]});});});details.appendChild(table('Observaciones',['Serie',xLabel||'Paso','Valor ('+unitLabel+')'],rows,null,120));figure.appendChild(details);return figure;
    }
    function renderCharts(){
      var target=$('lo-graficos');target.replaceChildren();var series=Array.isArray(view.series)?view.series.filter(function(s){return chartPoints(s.puntos).length;}):[];
      if(series.length){var section=node('section',undefined,'lo-grafico'),label=node('label','Indicador a analizar'),select=node('select');select.setAttribute('aria-label','Seleccionar serie del indicador');series.forEach(function(s){var option=node('option',s.titulo+' · '+s.unidad);option.value=s.id;select.appendChild(option);});if(!series.some(function(s){return s.id===chartChoice;}))chartChoice=series[0].id;select.value=chartChoice;label.appendChild(select);section.appendChild(label);var graph=node('div');section.appendChild(graph);
        function display(){var s=series.find(function(item){return item.id===select.value;})||series[0];chartChoice=s.id;graph.replaceChildren(drawChart(s.titulo,s.unidad,[s]));}select.addEventListener('change',display);display();target.appendChild(section);
      }
      var d=view.datos||{};if(caso.id==='ia-pronostico'&&Array.isArray(d.serie)){var demand=node('section',undefined,'lo-grafico');demand.appendChild(node('h3','Demanda observada y prueba temporal'));var ds=[{titulo:'Demanda observada',puntos:d.serie.map(function(v,i){return {paso:i+1,valor:v};})}];if(d.evaluado&&Array.isArray(d.predicciones))ds.push({titulo:'Pronóstico en prueba',color:'#a66d00',puntos:d.predicciones.map(function(v,i){return {paso:49+i,valor:v};})});demand.appendChild(drawChart('Demanda semanal','unidades',ds,'Semana'));target.appendChild(demand);}
      if(!target.childElementCount)target.appendChild(node('p','Las series aparecerán a medida que avances en una práctica.','lo-vacio'));
    }
    function renderHistory(){var list=$('lo-historial');list.replaceChildren();var history=Array.isArray(view.historial)?view.historial:[];if(!history.length){list.appendChild(node('li','Todavía no hay decisiones registradas.','lo-vacio'));return;}
      if(history.length>120)list.appendChild(node('li','Se muestran las últimas 120 de '+number(history.length)+' decisiones. La evidencia JSON conserva la partida completa.','lo-vacio'));
      history.slice(-120).reverse().forEach(function(h){var li=node('li'),action=(caso.acciones||[]).find(function(a){return a.id===h.accion;}),object=objects.find(function(o){return o.id===h.objeto;});li.appendChild(node('small','Paso '+number(h.paso)+' · '+number(h.minutos)+' min acumulados'));li.appendChild(node('strong',(action?action.titulo:h.accion)+' · '+(object?object.nombre:h.objeto)));li.appendChild(node('span',h.mensaje));if(h.efecto!==undefined)li.appendChild(node('small','Efecto de la decisión: +'+number(h.efecto)+' min'));list.appendChild(li);});
    }
    async function loadSessions(requested){var result=await transport('GET',{accion:'listar',pagina:requested});var list=$('lo-partidas-lista');list.replaceChildren();page=finite(result.pagina,requested);nextPage=result.siguiente?typeof result.siguiente==='number'?result.siguiente:page+1:null;previousPage=result.anterior?typeof result.anterior==='number'?result.anterior:Math.max(1,page-1):null;$('lo-partidas-pagina').textContent='Página '+page;
      (Array.isArray(result.sesiones)?result.sesiones:[]).slice(0,20).forEach(function(saved){var li=node('li'),button=node('button'),left=node('span'),right=node('small',saved.fase||'Guardada');button.type='button';var c=catalog.find(function(c){return c.id===saved.caso;});left.appendChild(node('strong',saved.nombre||c&&c.titulo||saved.caso));left.appendChild(node('small','Revisión '+number(saved.revision)+(saved.actualizada_en?' · '+new Date(saved.actualizada_en).toLocaleString('es-EC'):'')));button.append(left,right);button.addEventListener('click',function(){perform(async function(){apply(await transport('GET',{sesion:saved.id}));$('lo-partidas').hidden=true;$('lo-partidas-abrir').setAttribute('aria-expanded','false');});});li.appendChild(button);list.appendChild(li);});if(!list.childElementCount)list.appendChild(node('li','Aún no hay prácticas guardadas. Inicia una desde este escenario.'));}
    if($('lo-iniciar'))$('lo-iniciar').addEventListener('click',function(){var seed=parseSeed($('lo-semilla').value);if(seed===null){message('La semilla debe ser un entero entre 0 y 2147483647.',true);$('lo-semilla').focus();return;}perform(async function(){apply(await transport('POST',{accion:'crear',caso:caso.id,semilla:seed}));});});
    $('lo-semilla').addEventListener('change',renderDistributionLinks);$('lo-semilla').addEventListener('input',renderDistributionLinks);
    $('lo-objeto').addEventListener('change',function(){selectObject(this.value);});
    document.querySelectorAll('[data-camara]').forEach(function(button){button.addEventListener('click',function(){renderer.control(button.dataset.camara);});});
    var screen=$('lo-pantalla'),viewer=document.querySelector('.lo-visor');if(document.fullscreenEnabled&&viewer.requestFullscreen){screen.hidden=false;screen.addEventListener('click',async function(){try{if(document.fullscreenElement)await document.exitFullscreen();else await viewer.requestFullscreen();}catch(error){message('El navegador no permitió abrir la pantalla completa.',true);}});document.addEventListener('fullscreenchange',function(){screen.textContent=document.fullscreenElement?'Salir de pantalla completa':'Pantalla completa';renderer.resize();});}
    if($('lo-partidas-abrir'))$('lo-partidas-abrir').addEventListener('click',function(){var panel=$('lo-partidas');panel.hidden=!panel.hidden;this.setAttribute('aria-expanded',String(!panel.hidden));if(!panel.hidden)perform(async function(){await loadSessions(1);});});
    $('lo-partidas-cerrar').addEventListener('click',function(){$('lo-partidas').hidden=true;if($('lo-partidas-abrir')){$('lo-partidas-abrir').setAttribute('aria-expanded','false');$('lo-partidas-abrir').focus();}});
    $('lo-partidas-anterior').addEventListener('click',function(){if(previousPage)perform(async function(){await loadSessions(previousPage);});});$('lo-partidas-siguiente').addEventListener('click',function(){if(nextPage)perform(async function(){await loadSessions(nextPage);});});
    $('lo-exportar').addEventListener('click',function(){if(!live||!view.terminada)return;perform(async function(){var evidence=await transport('GET',{sesion:live.id,exportar:1}),blob=new Blob([JSON.stringify(evidence,null,2)],{type:'application/json;charset=utf-8'}),href=URL.createObjectURL(blob),a=node('a');a.href=href;a.download='upec-logistica-'+String(live.id).replace(/[^a-zA-Z0-9_-]/g,'')+'.json';document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(href);},1000);message('Evidencia descargada desde el registro del servidor.',false,true);});});
    $('lo-verificar').addEventListener('click',function(){if(!live||!view.terminada)return;perform(async function(){var result=await transport('GET',{sesion:live.id,verificar:1});$('lo-verificacion').textContent=verificationMessage(result);});});
    renderCase();renderState(false);
    var requestedSession=new URL(global.location.href).searchParams.get('sesion');if(requestedSession!==null){if(!sessionID(requestedSession))message('El identificador de la práctica no es válido. Puedes explorar el caso o iniciar otra práctica.',true);else if(main.dataset.auth==='1')perform(async function(){apply(await transport('GET',{sesion:requestedSession}));});else message('Accede a tu cuenta para reabrir la práctica guardada. La vista inicial sigue disponible.',false);}
    if(!global.isSecureContext)$('lo-xr').textContent='Navegación 3D en pantalla. WebXR requiere un contexto seguro y un dispositivo compatible; este entorno no activa sesiones inmersivas.';else if(global.navigator&&global.navigator.xr)$('lo-xr').textContent='El navegador ofrece la API WebXR. Este entorno utiliza navegación 3D en pantalla y no inicia sesiones inmersivas ni solicita permisos de dispositivo.';
  }
  if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bootstrap,{once:true});else bootstrap();}
})(typeof globalThis!=='undefined'?globalThis:this);
