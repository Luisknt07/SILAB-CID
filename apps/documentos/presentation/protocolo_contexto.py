"""Datos institucionales y propuestas de seguridad ligadas a los registros de la unidad."""
import hashlib
import json
import unicodedata
from copy import deepcopy

from django.db.models import Q
from django.utils.html import escape

# Insumos que son sustancias con lote, vencimiento y ficha de seguridad: su manejo se propone como riesgo químico.
CLASES_DE_SUSTANCIAS = ('reactivo', 'agroquimico', 'veterinario')


def _texto(valor):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(valor or '').lower())
                   if not unicodedata.combining(c))


def contexto_de(documento):
    if hasattr(documento, '_contexto_protocolo'):
        return documento._contexto_protocolo
    from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
    from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.recursos.models.consumibles import Consumible
    from apps.recursos.models.software import SoftwareDisponible
    from apps.reservas.models.seguridad import RequisitoAcceso
    from .perfil_unidades import base_de

    u = documento.unidad
    personal, espacios, equipos, insumos, requisitos, jornadas, software = [], [], [], [], [], [], []
    admin = u.administrador
    nombre = (admin.get_full_name() or admin.get_username()) if admin else ''
    contacto = ' · '.join(filter(None, (u.telefono, u.celular, u.contacto_email or (admin.email if admin else ''))))
    if admin:
        personal.append(dict(nombre=nombre, rol='Responsable de la unidad', contacto=contacto,
            funcion='Coordinar la aplicación, comunicación y actualización del protocolo.'))
    if u.pk:
        for r in ResponsableUnidad.objects.filter(unidad=u, activo=True).select_related('usuario', 'usuario__profile'):
            if admin and r.usuario_id == admin.pk:
                continue
            personal.append(dict(nombre=r.nombre_publico, rol=r.get_rol_display(),
                contacto=' · '.join(filter(None, (r.telefono_publico, r.email_publico))) or 'Contacto pendiente en la ficha de personal',
                funcion=r.descripcion_publica or f'Cumplir las funciones de {r.get_rol_display().lower()} en la operación de la unidad.'))
        espacios = list(EspacioReservable.objects.filter(unidad=u, activo=True).order_by('orden', 'pk').values(
            'id', 'codigo', 'nombre', 'tipo', 'ubicacion', 'instrucciones_uso'))
        equipos = list(UnidadEquipo.objects.filter(Q(laboratorio=u) | Q(laboratorios=u),
            activa=True, fecha_baja__isnull=True).distinct().order_by('codigo_unidad').values(
                'id', 'codigo_unidad', 'equipo__nombre', 'equipo__instrucciones_publicas'))
        insumos = list(Consumible.objects.filter(unidad=u, activo=True).order_by('codigo').values('id', 'codigo', 'nombre', 'clasificacion'))
        requisitos = list(RequisitoAcceso.objects.filter(unidad=u, activo=True).order_by('orden', 'pk').values(
            'id', 'nombre', 'tipo', 'descripcion'))
        jornadas = list(HorarioOperacionUnidad.objects.filter(unidad=u, activo=True, periodo__isnull=True).order_by(
            'dia_semana', 'hora_inicio').values('dia_semana', 'hora_inicio', 'hora_fin'))
        software = list(SoftwareDisponible.objects.filter(unidad=u, activo=True).values_list('nombre', flat=True))
    dias = dict(HorarioOperacionUnidad.DIA_CHOICES)
    horario = u.horario_atencion or '; '.join(
        f"{dias[j['dia_semana']]} {j['hora_inicio']:%H:%M}-{j['hora_fin']:%H:%M}" for j in jornadas)
    identidad = dict(unidad_nombre=u.nombre, unidad_tipo=u.nombre_tipologia or base_de(u).replace('_', ' ').title(),
        ubicacion_protocolo=u.ubicacion or u.direccion or 'Ubicación pendiente en la ficha de la unidad',
        horario_protocolo=horario or 'Horario pendiente en la configuración de la unidad',
        contacto_protocolo=contacto or 'Contacto pendiente en la ficha de la unidad')
    resultado = dict(identidad=identidad, personal=personal, responsable=nombre or 'Responsable de la unidad',
        espacios=espacios, equipos=equipos, insumos=insumos, requisitos=requisitos, software=software, base=base_de(u))
    resultado['huella'] = hashlib.sha256(json.dumps(resultado, sort_keys=True, default=str).encode()).hexdigest()
    documento._contexto_protocolo = resultado
    return resultado


def propuestas_de(documento):
    c = contexto_de(documento)
    responsable = c['responsable']
    registros = [(e['nombre'], e['tipo']) for e in c['espacios']]
    registros += [(e['equipo__nombre'], 'equipo') for e in c['equipos']]
    registros += [(e['nombre'], e['clasificacion']) for e in c['insumos']]
    def coincidencias(*claves):
        return list(dict.fromkeys(nombre for nombre, tipo in registros
            if any(clave in _texto(nombre + ' ' + tipo) for clave in claves)))
    quimicos = list(dict.fromkeys([i['nombre'] for i in c['insumos'] if i['clasificacion'] in CLASES_DE_SUSTANCIAS]
        + coincidencias('resina', 'alcohol', 'solvente', 'pintura', 'fundente', 'sanitizante')))
    grupos = [
        ('Máquinas y fabricación', coincidencias('cnc', 'fresad', 'cortadora', 'laser', 'torno', 'prensa', 'impresora 3d', 'manufactura'),
         'Contacto con partes móviles, superficies calientes o proyección de material.',
         'Aplicar las instrucciones del equipo y los controles definidos para la actividad; comprobar autorización, supervisión y protecciones antes del uso.'),
        ('Sustancias químicas', quimicos, 'Exposición o contacto durante el manejo de sustancias y materiales.',
         'Consultar las fichas de seguridad y definir el manejo, almacenamiento, protección y respuesta específicos antes de utilizar cada sustancia.'),
        ('Trabajo con electricidad y electrónica', coincidencias('electri', 'electro', 'soldad', 'bateria', 'fuente de alimentacion'),
         'Contacto eléctrico, calentamiento o daño durante conexiones y pruebas.',
         'Seguir las instrucciones del fabricante; permitir las intervenciones únicamente al personal autorizado y comprobar las condiciones antes de las pruebas.'),
        ('Agentes biológicos', coincidencias('biolog', 'microbi', 'cultivo', 'muestra biolog', 'establo', 'animal'),
         'Exposición asociada a material biológico o actividades con animales.',
         'Determinar el material y la exposición; aplicar el procedimiento específico y las medidas de contención, higiene y manejo de residuos que correspondan.'),
        ('Actividades de campo', coincidencias('parcela', 'invernadero', 'establo', 'campo', 'riego'),
         'Caídas, condiciones ambientales o exposición durante recorridos y trabajo de campo.',
         'Revisar el lugar, las condiciones y los recursos antes de cada salida; definir comunicación, acompañamiento y suspensión cuando las condiciones no sean seguras.'),
        ('Trabajo con información y equipos informáticos', coincidencias('comput', 'cad', 'software', 'datos', 'servidor', 'diseno'),
         'Fatiga postural o visual; pérdida o acceso indebido a información.',
         'Organizar el puesto y las pausas según la actividad; limitar el acceso a la información y conservar los respaldos autorizados.'),
    ]
    if c['software'] and not grupos[-1][1]:
        grupos[-1][1].extend(c['software'][:3])
    if c['base'] == 'observatorios' and not grupos[-1][1]:
        grupos[-1][1].append('Perfil de observatorio: análisis y gestión de información')
    if c['base'] == 'centro_experimental' and not grupos[4][1]:
        grupos[4][1].append('Perfil de centro experimental: revisar las actividades de campo de la unidad')
    riesgos = []
    for actividad, fuentes, peligro, control in grupos:
        if fuentes:
            riesgos.append(dict(actividad=actividad, peligro=peligro, control=control, responsable=responsable,
                verificacion='Antes de cada actividad: revisión del responsable y registro de novedades.', aplica='si',
                origen='Registros: ' + '; '.join(fuentes[:4])))
    riesgos.insert(0, dict(actividad='Ingreso y circulación en las instalaciones',
        peligro='Obstáculos, caídas o acceso a zonas de trabajo sin autorización.',
        control='Revisar las condiciones del espacio y mantener libres las circulaciones; comunicar restricciones y controlar el ingreso.',
        responsable=responsable, verificacion='Al inicio de la atención y ante cambios en el espacio.', aplica='si',
        origen='Instalaciones de ' + documento.unidad.nombre))
    if c['base'] == 'plantas_piloto':
        riesgos.append(dict(actividad='Preparación, operación y cierre de procesos de la planta piloto',
            peligro='Exposición a peligros propios de las etapas y de los materiales utilizados en cada proceso.',
            control='Revisar el procedimiento de cada proceso, sus condiciones de operación y las medidas preventivas antes de programar su ejecución.',
            responsable=responsable, verificacion='Revisión del proceso y de los controles antes de cada ejecución.', aplica='si',
            origen='Perfil de planta piloto: completar según los procesos y líneas de trabajo de la unidad'))
    medidas = []
    for indice, ambito in ((3, 'Agentes biológicos'), (1, 'Sustancias químicas'), (0, 'Equipos, máquinas y energía'),
                          (4, 'Actividades de campo'), (5, 'Información y datos')):
        grupo = grupos[indice]
        fuentes = grupo[1] or ([e['equipo__nombre'] for e in c['equipos'][:3]] if indice == 0 else [])
        medidas.append(dict(ambito=ambito, aplica='si' if fuentes else 'no',
            medidas=grupo[3] if fuentes else f'No se incluyen actividades de {ambito.lower()} entre los registros consultados para este protocolo.',
            origen='Registros: ' + '; '.join(fuentes[:4]) if fuentes else 'Sin registros asociados: revisar la propuesta de no aplicación'))
    recursos = [nombre for nombre, _tipo in registros if any(k in _texto(nombre)
        for k in ('extintor', 'botiquin', 'alarma', 'lavaojos', 'kit de derrame'))]
    emergencias = [dict(situacion='Alarma, humo o situación que impida continuar con seguridad',
        respuesta='Suspender la actividad, avisar al responsable y seguir las indicaciones del plan de emergencia aplicable a la instalación.',
        responsable=responsable, recursos='; '.join(recursos) or 'Medios de aviso y respuesta que se identifiquen en el plan de emergencia de la instalación.',
        aplica='si', origen='Propuesta para las instalaciones de la unidad; confirmar el plan aplicable'),
        dict(situacion='Incidente, lesión o condición insegura durante una actividad',
        respuesta='Suspender el trabajo afectado, comunicar el incidente y solicitar la asistencia correspondiente por los canales definidos en la instalación.',
        responsable=responsable, recursos='Contactos y canales de atención confirmados para la instalación.', aplica='si',
        origen='Propuesta común: completar los canales reales de aviso y atención')]
    controles = [dict(control='Verificación de ingreso e inducción', frecuencia='Antes de cada actividad',
        responsable=responsable, registro='Registro de ingreso o inducción y novedades de la actividad.'),
        dict(control='Revisión de espacios y recursos utilizados', frecuencia='Antes de cada actividad',
        responsable=responsable, registro='Inspección o registro de novedades y acciones de corrección.'),
        dict(control='Revisión del protocolo', frecuencia='Ante cambios o incidentes', responsable=responsable,
        registro='Protocolo actualizado y comunicación de los cambios a los usuarios.')]
    return dict(riesgos_protocolo=riesgos, medidas_protocolo=medidas,
                emergencias_protocolo=emergencias, controles_protocolo=controles)


def completar_contenido(documento, contenido, *, proponer=False):
    """Corrige sólo fuentes automáticas; conserva lo redactado y las decisiones guardadas."""
    c = contexto_de(documento)
    resultado = deepcopy(contenido or {})
    if resultado.get('_protocolo_fuentes') and resultado['_protocolo_fuentes'] != c['huella']:
        resultado['revision_propuestas'] = ''
    if proponer and not resultado.get('_protocolo_guiado'):
        anteriores = resultado.get('responsables_protocolo') or []
        funciones_actuales = {p['funcion'] for p in c['personal']}
        propias = [f"{p.get('rol', 'Función')}: {p['funcion']}" for p in anteriores
                   if isinstance(p, dict) and p.get('funcion') and p['funcion'] not in funciones_actuales]
        if propias and not resultado.get('responsabilidades_adicionales'):
            resultado['responsabilidades_adicionales'] = '<ul>' + ''.join(
                f'<li>{escape(texto)}</li>' for texto in propias) + '</ul>'
            resultado['_responsables_redaccion_anterior'] = deepcopy(anteriores)
        for clave, filas in propuestas_de(documento).items():
            if not resultado.get(clave):
                resultado[clave] = filas
        resultado.setdefault('revision_propuestas', '')
        resultado['_protocolo_guiado'] = 1
    resultado.update(c['identidad'])
    resultado['responsables_protocolo'] = deepcopy(c['personal'])
    resultado['firma_nombre'] = c['responsable']
    resultado['firma_cargo'] = 'Responsable de la unidad'
    # La ausencia de horario o teléfono se muestra como un dato pendiente en su fuente.
    resultado['_protocolo_fuentes'] = c['huella']
    return resultado


def bloques_automaticos(documento, contenido=None):
    c = contexto_de(documento)
    etiquetas = ('Nombre de la unidad', 'Tipo de unidad', 'Instalaciones y ubicación', 'Horario de atención', 'Contacto')
    valores = list(c['identidad'].values())
    resultado = dict(protocolo_general=[dict(tipo='pares', titulo='Ficha de la unidad', pares=list(zip(etiquetas, valores)))],
        protocolo_responsables=[dict(tipo='tabla', titulo='Personal registrado',
            cabecera=['Rol', 'Nombre', 'Responsabilidad', 'Contacto'],
            filas=[[p[k] for k in ('rol', 'nombre', 'funcion', 'contacto')] for p in c['personal']])],
        protocolo_contactos=[dict(tipo='tabla', titulo='Contactos registrados para aviso interno',
            cabecera=['Persona o función', 'Contacto'],
            filas=[[p['nombre'] + ' · ' + p['rol'], p['contacto'] or 'Contacto pendiente en la ficha de la unidad'] for p in c['personal']])])
    if c['requisitos']:
        resultado['protocolo_acceso'] = [dict(tipo='lista', titulo='Requisitos de acceso registrados',
            items=[r['nombre'] + (': ' + r['descripcion'] if r['descripcion'] else '') for r in c['requisitos']])]
    referencias = [f"{e['nombre']}: {e['instrucciones_uso']}" for e in c['espacios'] if e['instrucciones_uso']]
    if referencias:
        resultado['protocolo_instrucciones'] = [dict(tipo='lista', titulo='Indicaciones registradas por área', items=referencias)]
    return resultado


EJEMPLOS = {
    'evacuacion_protocolo': 'Ejemplo para completar: «Desde [área], seguir la ruta [referencia] hasta [punto de encuentro]. '
        'El aviso se comunica por [canal] y coordina [responsable]. Referencia: [plan o señalización de la instalación]».',
    'referencias_protocolo': 'Puedes incluir el nombre o enlace del plan de emergencia, los manuales de los equipos y las fichas de seguridad que utilice tu unidad.',
    'responsabilidades_adicionales': 'Si hace falta, indica una función complementaria del personal que aparece arriba. Los nombres y contactos se actualizan en Personal de la unidad.',
}


def opciones_editor(documento, campo, valor):
    c = contexto_de(documento)
    return dict(responsables=[p['nombre'] for p in c['personal']], ejemplo=EJEMPLOS.get(campo.clave, ''),
        ejemplos=dict(actividad='Ejemplo: preparación y operación del equipo registrado',
            peligro='Ejemplo: contacto con una superficie caliente durante la actividad',
            control='Indica las medidas de la actividad o explica por qué no aplica',
            verificacion='Ejemplo: lista de comprobación antes de iniciar',
            situacion='Ejemplo: falla de equipo durante la actividad',
            respuesta='Indica cómo se suspende, a quién se avisa y qué procedimiento se sigue',
            recursos='Ejemplo: canal de aviso y medios de respuesta identificados en la instalación',
            medidas='Ajusta la propuesta a las actividades reales de la unidad',
            servicio='Ejemplo: servicio institucional de atención de emergencias',
            telefono='Número o canal real de atención', ubicacion='Ubicación o medio alterno de contacto',
            registro='Ejemplo: registro de inducción o lista de inspección'),
        propuestas=propuestas_de(documento).get(campo.clave, []),
        frecuencias=['Antes de cada actividad', 'Al finalizar la actividad', 'Según programación de la unidad',
                     'Ante cambios o incidentes'])


def leer_contenido(documento, contenido, anterior, post):
    from django.core.exceptions import ValidationError
    documento.__dict__.pop('_contexto_protocolo', None)
    c = contexto_de(documento)
    if post.get('protocolo_fuentes') != c['huella']:
        raise ValidationError('Cambiaron los datos de la unidad. Actualiza el editor y revisa las propuestas antes de guardar.')
    permitidos = {p['nombre'] for p in c['personal']}
    for clave in ('riesgos_protocolo', 'emergencias_protocolo', 'controles_protocolo'):
        for fila in contenido.get(clave, []):
            if fila.get('responsable') and fila['responsable'] not in permitidos:
                raise ValidationError('Selecciona un responsable del personal registrado en esta unidad.')
    resultado = dict(anterior or {}, **contenido, _protocolo_fuentes=c['huella'], _protocolo_guiado=1)
    return completar_contenido(documento, resultado)
