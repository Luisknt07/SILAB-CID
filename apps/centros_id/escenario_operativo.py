"""Construcción idempotente del escenario local CIDT solicitado para revisar contenido y recorridos."""
from datetime import time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import router, transaction
from django.utils import timezone
from django.utils.text import slugify

from .carga import Cargador
from .contenido import cidt, cidt_muestra
from .contenido.cidt_operativo import CURSOS, LINEAS, PROYECTOS, SERVICIOS
from .models import Convocatoria, DocumentoCentro, EquipoCentro, Grupo, HitoProyecto, HorarioRecurso, Zona

FUENTE = 'Escenario operativo de desarrollo CIDT v1; contenido representativo solicitado para diseño.'


def completar(objeto, valores):
    """Completa vacíos sin reemplazar lo que ya editó el centro."""
    campos = []
    for campo, valor in valores.items():
        if getattr(objeto, campo) in ('', None) and valor not in ('', None):
            setattr(objeto, campo, valor)
            campos.append(campo)
    if campos:
        objeto.full_clean()
        objeto.save(update_fields=campos)
    return objeto


def archivo(objeto, nombre, texto):
    if objeto.es_muestra and not objeto.archivo:
        contenido = f'# {objeto.titulo}\n\n{FUENTE}\n\n{texto}\n'
        objeto.archivo.save(nombre, ContentFile(contenido.encode('utf-8')))


def construir_escenario(centro):
    with transaction.atomic(using=router.db_for_write(type(centro))):
        return _construir_escenario(centro)


def _construir_escenario(centro):
    if not settings.DEBUG or centro.slug != 'cidt-upec':
        raise ValidationError('El escenario CIDT se construye únicamente en desarrollo local.')
    hoy = timezone.localdate()
    areas = {a.codigo: a for a in centro.componentes.all()}
    if set(SERVICIOS) - areas.keys():
        raise ValidationError('Cargue primero la estructura de las nueve áreas del CIDT.')
    cargador = Cargador(cidt)
    cargador._muestra(centro, areas, cidt_muestra)
    fuente = {'fuente_validacion': FUENTE}
    completar(centro, {
        'mision': 'Investigar, desarrollar y validar soluciones tecnológicas con equipos interdisciplinarios, integrando datos, automatización, fabricación digital y plataformas experimentales para atender necesidades del territorio.',
        'vision': 'Ser un referente regional de investigación aplicada y transferencia tecnológica, con soluciones reproducibles, talento especializado y colaboración sostenida con el sector productivo y la sociedad.',
        'adscripcion': 'Universidad Politécnica Estatal del Carchi',
        'horario_atencion': 'Lunes a viernes, 08:00 a 17:00. Las prácticas se programan con el área responsable.',
    })
    personas = list(centro.integrantes.filter(es_muestra=True))
    for persona in personas:
        completar(persona, fuente)
    for linea in centro.lineas.all():
        datos = LINEAS.get(linea.nombre)
        if datos:
            problema, pregunta, metodo = datos
            responsable = next((p for p in personas if p.rol == 'investigador' and linea in p.lineas.all()), None)
            completar(linea, {'problema': problema, 'preguntas': pregunta, 'metodologia': metodo,
                'objetivos': linea.resultados, 'ambito': 'Carchi y zona de integración fronteriza', 'responsable': responsable})
    for servicio in centro.servicios.select_related('componente'):
        if not servicio.componente or servicio.componente.codigo not in SERVICIOS:
            continue
        entradas, metodo, aceptacion, plazo, exclusiones = SERVICIOS[servicio.componente.codigo]
        completar(servicio, {'alcance': f'{servicio.descripcion} El alcance se concreta mediante diagnóstico, hitos y entregables acordados para cada solicitud.',
            'entradas': entradas, 'metodo': metodo, 'aceptacion': f'{servicio.entregable}. {aceptacion}',
            'plazo': plazo, 'exclusiones': exclusiones,
            'requisitos': 'Persona responsable de la solicitud, objetivo definido y autorización para usar los materiales o datos. La evaluación técnica determina los requisitos específicos.',
            'formato_entrega': 'Entregable técnico y memoria de ejecución en formato digital; material físico cuando corresponde.',
            'condiciones': 'Se acuerdan confidencialidad, permisos de uso, custodia y devolución de materiales antes de iniciar. Las condiciones económicas se comunican tras evaluar el caso.'})
    for proyecto in centro.proyectos.filter(es_muestra=True):
        datos = PROYECTOS.get(proyecto.codigo)
        if not datos:
            continue
        problema, objetivos, metodo, sector, categoria = datos
        completar(proyecto, {**fuente, 'problema': problema, 'objetivos': objetivos, 'metodologia': metodo,
            'sector': sector, 'avance_metodo': 'Seguimiento de entregables del plan de trabajo del escenario.',
            'avance_fecha': min(hoy, proyecto.fin or hoy), 'avance_evidencia': FUENTE})
        # La categoría inicial proviene del guion de este proyecto, solo en registros de muestra.
        if proyecto.categoria == 'investigacion' and categoria != 'investigacion':
            proyecto.categoria = categoria
            proyecto.save(update_fields=['categoria'])
        titulos = ('Diagnóstico y requisitos', 'Diseño y protocolo de pruebas', 'Desarrollo y experimentación', 'Validación y entrega técnica')
        terminados = 4 if not proyecto.activo else (0 if proyecto.estado == 'formulacion' else 2)
        inicio = proyecto.inicio or hoy - timedelta(days=180)
        fin = proyecto.fin or hoy + timedelta(days=90)
        for indice, titulo in enumerate(titulos):
            fecha = inicio + (fin - inicio) * (indice + 1) / 4
            cumplido = indice < terminados
            HitoProyecto.objects.get_or_create(proyecto=proyecto, titulo=titulo, defaults={
                'fecha_prevista': fecha, 'estado': 'cumplido' if cumplido else 'pendiente',
                'fecha_cumplida': min(fecha, hoy) if cumplido else None,
                'evidencia': FUENTE if cumplido else '', 'publico': True})
    grupos = (
        ('Sistemas inteligentes y datos', ('IA y analítica', 'Automatización e IoT'), 'Modelos de IA, integración de sistemas y dispositivos conectados.'),
        ('Producción y logística digital', ('Manufactura inteligente', 'Logística y cadena de suministro'), 'Procesos productivos, trazabilidad y operación de cadenas de suministro.'),
        ('Diseño y experiencias tecnológicas', ('Prototipado', 'XR y gemelos digitales'), 'Prototipos funcionales, simulación y experiencias inmersivas.'),
        ('Energía y aprendizaje aplicado', ('Energía y sostenibilidad', 'Innovación educativa'), 'Uso eficiente de recursos y aprendizaje mediante práctica tecnológica.'),
    )
    for orden, (nombre, nombres, descripcion) in enumerate(grupos, 1):
        grupo = cargador._guardar_muestra(Grupo, 'grupos', {'centro': centro, 'nombre': nombre},
            {**fuente, 'descripcion': descripcion, 'orden': orden})
        lineas = list(centro.lineas.filter(nombre__in=nombres))
        cargador._enlazar(grupo.lineas, lineas)
        if grupo.es_muestra:
            for persona in personas:
                if not persona.grupo_id and any(linea in persona.lineas.all() for linea in lineas):
                    completar(persona, {'grupo': grupo})
    for resultado in centro.resultados.filter(es_muestra=True).select_related('proyecto', 'componente'):
        completar(resultado, {**fuente, 'version': '1.0', 'sector': resultado.proyecto.sector if resultado.proyecto else 'Diseño y validación',
            'tecnologia': resultado.componente.nombre_corto if resultado.componente else 'Tecnologías digitales',
            'usuarios_previstos': 'Equipos de investigación, técnicos y organizaciones que necesitan evaluar y adaptar esta solución a su proceso.',
            'colaboracion': 'Diagnóstico conjunto, prueba supervisada y adaptación mediante un proyecto o servicio acordado con el centro.',
            'restricciones': 'La ficha técnica delimita el alcance de uso, los requisitos de adaptación y los elementos que necesitan validación adicional.'})
        if resultado.trl:
            completar(resultado, {'trl_fecha': min(hoy, resultado.proyecto.fin or hoy) if resultado.proyecto else hoy,
                'trl_evaluador': 'Equipo técnico del escenario CIDT', 'trl_alcance': 'Valoración representativa para recorrer la ficha de un desarrollo tecnológico.', 'trl_evidencia': FUENTE})
        if resultado.estado_pi:
            completar(resultado, {'pi_modalidad': 'Software', 'pi_titular': 'Titular del escenario, por determinar en el expediente real',
                'pi_identificador': 'EXP-ESCENARIO-CIDT-01', 'pi_fecha': hoy, 'pi_evidencia': FUENTE})
        texto = f'## Descripción\n{resultado.descripcion}\n\n## Procedencia técnica\nProyecto: {resultado.proyecto or "Protocolo transversal de validación"}.\nÁrea: {resultado.componente or "CIDT"}.\nVersión: {resultado.version}.\n\n## Uso y revisión\n1. Revisar los requisitos y el contexto del proceso.\n2. Preparar los datos y materiales autorizados.\n3. Ejecutar las pruebas acordadas y registrar incidencias.\n4. Comparar los resultados con los criterios de aceptación.\n5. Documentar los límites y las adaptaciones necesarias.\n\n## Límites\nEste archivo describe el resultado del escenario de diseño. No contiene una publicación, titulación o registro oficial ni acredita ensayos realizados.\n'
        archivo(resultado, f'{slugify(resultado.titulo)[:100]}-ficha.md', texto)
    for caso in centro.casos.filter(es_muestra=True).select_related('proyecto'):
        desarrollo = centro.resultados.filter(es_muestra=True, proyecto=caso.proyecto, tipo__in=('prototipo', 'software')).first()
        completar(caso, {**fuente, 'contexto': 'Aplicación piloto y acompañamiento a usuarios en el escenario operativo.',
            'aporte_centro': caso.solucion, 'receptor': caso.beneficiario,
            'mecanismo': 'Entrega técnica, formación de usuarios y acompañamiento de la adopción',
            'fecha_transferencia': min(hoy, caso.proyecto.fin or hoy) if caso.proyecto else hoy,
            'evidencia': FUENTE, 'autorizacion_publicacion': 'Divulgación de actores genéricos del escenario de desarrollo.',
            'desarrollo': desarrollo, 'limites': 'El caso describe una aplicación representativa; las mediciones de impacto requieren una línea base, período y método propios.'})
    responsable = next((p for p in personas if p.rol in ('director', 'investigador')), None)
    for aliado in centro.aliados.filter(es_muestra=True):
        completar(aliado, {**fuente, 'convenio': 'Programa de colaboración del escenario operativo CIDT',
            'vigencia_desde': hoy - timedelta(days=180), 'vigencia_hasta': hoy + timedelta(days=180),
            'actividades': aliado.aporte, 'responsable': responsable})
    for curso in CURSOS:
        cargador._guardar_muestra(Convocatoria, 'cursos', {'centro': centro, 'titulo': 'Curso: ' + curso['nombre']}, {
            **fuente, 'tipo': 'otro', 'descripcion': curso['dirigido'] + ' ' + curso['entregable'],
            'componente': areas[curso['area']], 'cierre': hoy + timedelta(days=curso['dias'] - 3)})
    for convocatoria in centro.convocatorias.filter(es_muestra=True):
        completar(convocatoria, fuente)
    for novedad in centro.novedades.filter(es_muestra=True):
        completar(novedad, fuente)
    _recursos(centro, areas, cargador)
    _documentos(centro, cargador, hoy)
    return cargador.resumen()


def _recursos(centro, areas, cargador):
    filas = (
        ('fablab', 'CIDT-FAB-PR01', 'Estación de impresión 3D', 'Preparación y fabricación de prototipos con filamento autorizado.', 'Mesa de preparación de prototipos', 6),
        ('xr-mediatech', 'CIDT-XR-PR01', 'Estación de práctica XR', 'Interacción con entornos inmersivos y revisión de escenarios de simulación.', 'Sala de práctica inmersiva', 8),
        ('ia-datos', 'CIDT-IA-PR01', 'Estación de análisis de datos', 'Análisis de conjuntos de práctica, programación y visualización.', 'Sala de trabajo con datos', 10),
    )
    for indice, (codigo, etiqueta, nombre, funcion, sala, aforo) in enumerate(filas, 1):
        area = areas[codigo]
        equipo = cargador._guardar_muestra(EquipoCentro, 'activos de práctica', {'componente': area, 'codigo': etiqueta}, {
            'nombre': nombre, 'categoria': 'Estación de práctica', 'funcion': funcion, 'detalle': 'Unidad individual para práctica supervisada.',
            'es_activo_individual': True, 'reservable': True, 'estado': 'operativo', 'margen_minutos': 15,
            'requisitos': 'Presentar actividad y archivos de trabajo; revisión por el técnico responsable y operación supervisada.',
            'fuente_validacion': FUENTE})
        zona = cargador._guardar_muestra(Zona, 'espacios de práctica', {'centro': centro, 'codigo': f'PRACTICA-{indice}'}, {
            'nombre': sala, 'nivel': area.nivel, 'area_m2': 0, 'componente': area, 'reservable': True,
            'estado_acceso': 'disponible', 'aforo': aforo, 'margen_minutos': 15, 'fuente_validacion': FUENTE,
            'requisitos': 'Reunión de proyecto o práctica guiada. Informar actividad, participantes y materiales; respetar aforo y protocolo del área.',
            'accesibilidad': 'Coordinar necesidades de acceso y apoyo antes de la sesión.'})
        for objeto, campo in ((equipo, 'equipo'), (zona, 'zona')):
            if not objeto.es_muestra:
                continue
            for dia in range(5):
                if not objeto.horarios.filter(dia=dia).exists():
                    horario = HorarioRecurso(centro=centro, **{campo: objeto}, dia=dia, abre=time(8), cierra=time(17))
                    horario.full_clean()
                    horario.save()


def _documentos(centro, cargador, hoy):
    filas = (
        ('plan_desarrollo', 'Plan de trabajo del centro', 'Agenda, responsabilidades y seguimiento de proyectos y capacidades.',
         'Priorizar retos con las líneas de investigación. Revisar trimestralmente entregables, riesgos y necesidades de recursos. Cada proyecto registra responsable, método, hitos y resultados; el comité revisa coherencia científica y oportunidades de transferencia.'),
        ('otro', 'Guía de servicios y atención', 'Cómo solicitar diagnóstico, servicio técnico o acompañamiento.',
         'Registrar necesidad y entregable esperado. El área evalúa entradas, requisitos, plazo y condiciones económicas. Acordar alcance y aceptación antes de ejecutar. Entregar memoria y resultados; registrar observaciones y cierre desde el expediente de atención.'),
        ('seguridad', 'Acceso seguro a equipos y espacios', 'Preparación, supervisión y cierre de prácticas.',
         'Solicitar fecha, horario, participantes y actividad. Revisar materiales y riesgos con el técnico. La solicitud no confirma una reserva. Operar según las instrucciones, registrar incidencias y dejar el recurso en condiciones seguras. Una inducción o calibración exigida debe estar vigente.'),
        ('politica_datos', 'Guía de datos y confidencialidad', 'Permisos, minimización y conservación de información.',
         'Identificar fuente, autorización y responsable de cada conjunto. Separar datos personales y material reservado. Aplicar permisos por función, respaldos y plazos de conservación. Publicar únicamente versiones autorizadas y registrar licencia, versión y restricciones.'),
        ('propiedad_intelectual', 'Ruta de protección y transferencia', 'Decisiones sobre uso, derechos y adopción de resultados.',
         'Documentar autores, aportes, titularidad y obligaciones de terceros. Evaluar protección antes de divulgar. Elegir licencia, servicio, formación o acuerdo de transferencia según la solución. Registrar receptor, mecanismo y evidencia de aceptación; medir impacto con referencia y método.'),
    )
    for orden, (tipo, titulo, resumen, texto) in enumerate(filas, 20):
        documento = cargador._guardar_muestra(DocumentoCentro, 'documentos de operación', {'centro': centro, 'titulo': titulo}, {
            'tipo': tipo, 'resumen': resumen, 'version': '1.0', 'periodo': str(hoy.year), 'fecha': hoy,
            'estado_documental': 'informativo', 'fuente_validacion': FUENTE, 'orden': orden})
        archivo(documento, f'{slugify(titulo)}.md', texto)
