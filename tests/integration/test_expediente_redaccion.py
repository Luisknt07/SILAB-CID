"""Editor guiado de la planificación y del informe semestral.

La unidad redacta por apartados, el sistema aporta lo que ya sabe, el avance y
los faltantes se calculan solos, el PDF se genera cuando no falta nada y queda
en el expediente como «generado», listo para firmar y cargar.
"""

import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.documentos.presentation.anexos_evidencia import anexos_numerados
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente import construir_expediente, generar_documento
from apps.documentos.presentation.expediente_redaccion import actividades_para, avance, componer, leer_formulario, meses_del_tramo, obtener_redaccion, registros_del_periodo
from apps.documentos.presentation.expediente_sugerencias import POLITICA_POR_CAMPO, sugerencias_para
from apps.recursos.models.consumibles import Consumible
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import abrir_entrega, identificar

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix='citt-redaccion-')

PLAN_COMPLETO = {
    'descripcion': '<p>Laboratorio de docencia e investigación en redes.</p>',
    'mision': '<p>Formar con práctica real.</p>', 'vision': '<p>Referente regional en redes.</p>',
    'estructura': '<h4>Estructura</h4><p>Coordinación, responsable técnico y laboratorista.</p>',
    'objetivo_general': '<p>Sostener la práctica curricular del período.</p>',
    'objetivos_especificos': '<ul><li>Ejecutar 8 prácticas</li><li>Actualizar 2 guías</li></ul>',
    'sectores': ['docencia', 'tecnologia'],
    'estado_operativo': 'B', 'diagnostico': '<p>Faltan dos switches.</p>',
    'necesidades': '<ul><li>Dos switches gestionables</li></ul>',
    'actividades': {'catalogo': {'PRACTICAS': {'aplica': True, 'meta': '8', 'meses': [3, 4, 5], 'responsable': 'Ana'},
                                 'USO': {'aplica': True, 'meta': '100 %', 'meses': [3, 4, 5, 6, 7], 'responsable': ''},
                                 'GUIAS': {'aplica': True, 'obligatoria': True, 'meta': '1', 'meses': [3], 'responsable': 'Ana'},
                                 'PRACTICAS-PLAN': {'aplica': True, 'meta': '6'},
                                 'CAPACITACION': {'aplica': True, 'meta': '1'},
                                 'DIFUSION': {'aplica': True, 'meta': '1'},
                                 'INVESTIGACION': {'aplica': True, 'meta': '1'},
                                 'TRANSFERENCIA': {'aplica': True, 'meta': '1'},
                                 'MANTENIMIENTO': {'aplica': True, 'meta': '80 %'},
                                 'INVENTARIO': {'aplica': True, 'meta': '1'},
                                 'SEGURIDAD': {'aplica': True, 'meta': '100 %'},
                                 'INSPECCIONES': {'aplica': True, 'meta': '100 %'},
                                 'DESECHOS': {'aplica': True, 'meta': '100 %'}},
                    'otras': [{'nombre': 'Jornada de puertas abiertas', 'indicador': 'Evento', 'meta': '1',
                               'meses': [6], 'responsable': 'Ana'}]},
    'inversion': [{'categoria': 'equipos', 'item': 'Switch gestionable', 'cantidad': '2', 'justificacion': 'Topologías',
                   'prioridad': 'alta', 'costo_unitario': '450', 'fuente': 'institucional'}],
    'presupuesto_uso': {'horas_por_mes': {str(m): '4' for m in range(1, 7)},
                       'horas_comprometidas': '24',
                       'justificacion': 'Jornadas de prácticas y actividades previstas para el semestre.'},
    'firma_nombre': 'Ana Coordinadora', 'firma_cargo': 'Responsable de la unidad',
}

# Una planificación apta para firma identifica quién ejecuta cada compromiso.
PLAN_COMPLETO['actividades']['minimos_catalogo'] = 2
for actividad_completa in PLAN_COMPLETO['actividades']['catalogo'].values():
    actividad_completa['responsable'] = 'Ana Coordinadora'
    actividad_completa.setdefault('meses', [3, 4, 5, 6, 7])


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseDeRedaccion(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            username='coordinador-redaccion', password='clave-segura', first_name='Ana', last_name='Coordinadora',
            email='ana@upec.edu.ec')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de redes', slug='laboratorio-redes-redaccion', dependencia='laboratorios',
            descripcion='Laboratorio de docencia e investigación en redes.', fecha_inicio=date(2025, 1, 1),
            administrador=cls.coordinador, facultad='Industrias', carreras='Computación')
        ResponsableUnidad.objects.create(unidad=cls.unidad, nombre='Luis Técnico', rol='responsable_tecnico')
        EspacioReservable.objects.create(unidad=cls.unidad, codigo='RED-A1', nombre='Área de racks', tipo='area',
                                         capacidad=12)
        equipo = EquiposServicios.objects.create(codigo='SW-CORE', nombre='Switch de núcleo', marca='Cisco')
        cls.unidad_equipo = UnidadEquipo.objects.create(
            codigo_unidad='RED-SW-01', equipo=equipo, laboratorio=cls.unidad, estado_unidad='disponible',
            fecha_adquisicion=date(2024, 5, 2), valor_referencial=1200)
        PlanMantenimientoEquipo.objects.create(
            equipo=cls.unidad_equipo, nombre='Limpieza y firmware', tipo='preventivo', frecuencia_dias=60,
            fecha_inicio=date(2026, 1, 10), proxima_ejecucion=date(2026, 1, 10))
        SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Packet Tracer', codigo='PT', version='8.2',
                                          licencias_totales=30, licencias_disponibles=30)
        Consumible.objects.create(unidad=cls.unidad, codigo='CAB-UTP', nombre='Cable UTP cat. 6',
                                  clasificacion='material', unidad_medida='m', stock_total=300, minimo=50)
        periodo = PeriodoAcademico.objects.create(
            codigo='2026-A', nombre='Período 2026-A', anio_referencia=2026, ciclo='A', tipo='ordinario',
            ambito='carreras_centros', semanas_planificadas=16, estado='publicado')
        VersionCalendarioAcademico.objects.create(
            periodo=periodo, numero=1, nombre='Calendario', fecha_inicio_clases=date(2026, 3, 9),
            fecha_fin_clases=date(2026, 7, 10), fecha_fin_periodo=date(2026, 7, 17), vigente=True)

    def documento(self, codigo, corte='A'):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        return DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo=codigo, anio=2026, corte=corte)

    def ruta_editor(self, documento):
        return reverse('redactar_documento_expediente', args=[self.unidad.slug, documento.pk])


class ApartadosYAvanceTests(BaseDeRedaccion):
    def test_el_editor_propone_lo_que_sabe_y_calcula_el_avance(self):
        plan = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(plan)
        self.assertEqual(redaccion.contenido['descripcion'], '<p>Laboratorio de docencia e investigación en redes.</p>')
        self.assertEqual(redaccion.contenido['firma_nombre'], 'Ana Coordinadora')
        # Las redacciones base del tipo vienen puestas; lo que solo la unidad decide, no.
        self.assertIn('Sostener la formación práctica', redaccion.contenido['mision'])
        self.assertIn('Coordinación de la unidad', redaccion.contenido['estructura'])
        progreso = avance('planificacion', redaccion.contenido)
        self.assertLess(progreso['porcentaje'], 100)
        etiquetas = [c.etiqueta for _s, c in progreso['faltantes']]
        self.assertIn('Sectores de aplicación', etiquetas)
        self.assertIn('Estado operativo de la unidad', etiquetas)
        self.assertNotIn('Misión', etiquetas)
        completo = avance('planificacion', PLAN_COMPLETO)
        self.assertEqual((completo['porcentaje'], completo['faltantes']), (100, []))

    def test_el_plan_viene_con_lo_obligatorio_marcado_y_su_cronograma(self):
        from apps.documentos.presentation.expediente_redaccion import filas_del_plan, plan_inicial

        plan = self.documento('PLANIFICACION')
        inicial = plan_inicial(plan, date(2026, 3, 9), date(2026, 7, 17))
        uso = inicial['catalogo']['USO']
        self.assertEqual((uso['aplica'], uso['meta'], uso['meses']), (True, '100 %', [3, 4, 5, 6, 7]))
        self.assertEqual(inicial['catalogo']['INVENTARIO']['meses'], [7])
        # La ventana general queda después de clases; las frecuencias por equipo se conservan aparte.
        self.assertEqual(inicial['catalogo']['MANTENIMIENTO'], {
            'aplica': True, 'meta': '80 %', 'meses': [7],
            'responsable': ''})
        self.assertEqual(inicial['cronograma_auto']['mantenimiento_meses_por_equipo'], [3, 5, 7])
        self.assertTrue(inicial['catalogo']['PRACTICAS']['aplica'])
        self.assertTrue(inicial['catalogo']['GUIAS']['aplica'])
        # Aunque la unidad intente desmarcarla, una obligatoria sigue aplicando.
        from django.http import QueryDict
        post = QueryDict(mutable=True)
        post.update({'act__GUIAS__aplica': '1'})
        contenido = leer_formulario('planificacion', post, self.unidad)
        self.assertTrue(contenido['actividades']['catalogo']['USO']['aplica'])
        filas = {f['codigo']: f for f in filas_del_plan(self.unidad, contenido, date(2026, 3, 9), date(2026, 7, 17))}
        self.assertTrue(filas['USO']['obligatoria'] and filas['USO']['aplica'])
        self.assertTrue(filas['GUIAS']['obligatoria'])
        self.assertFalse(filas['GUIAS']['institucional'])
        # La redacción nueva ya trae el plan y, mientras nadie la guarde, se completa con lo propuesto.
        redaccion = obtener_redaccion(plan)
        self.assertTrue(redaccion.contenido['actividades']['catalogo']['SEGURIDAD']['aplica'])
        redaccion.contenido = {'mision': '<p>Propia</p>'}
        redaccion.save()
        redaccion = obtener_redaccion(plan)
        self.assertEqual(redaccion.contenido['mision'], '<p>Propia</p>')
        self.assertIn('vision', redaccion.contenido)

    def test_una_obligatoria_guardada_sin_meses_recupera_el_cronograma_previsto(self):
        from apps.documentos.presentation.expediente_redaccion import filas_del_plan

        # Un plan guardado antes de que el sistema propusiera meses: las obligatorias
        # aplican pero no tienen cronograma escrito.
        contenido = {'actividades': {'catalogo': {
            'USO': {'aplica': True, 'meta': '100 %', 'meses': [], 'responsable': ''},
            'MANTENIMIENTO': {'aplica': True, 'meta': '', 'meses': [], 'responsable': ''},
            'INVENTARIO': {'aplica': True, 'meta': '', 'meses': [], 'responsable': ''},
            'GUIAS': {'aplica': True, 'meta': '2', 'meses': [], 'responsable': ''},
        }, 'otras': []}}

        filas = {f['codigo']: f for f in filas_del_plan(self.unidad, contenido, date(2026, 3, 9), date(2026, 7, 17))}

        self.assertEqual(filas['USO']['meses'], [3, 4, 5, 6, 7])
        self.assertEqual(filas['INVENTARIO']['meses'], [7])
        # El plan del equipo (cada 60 días desde el 10/01) fija los meses del mantenimiento.
        self.assertEqual(filas['MANTENIMIENTO']['meses'], [3, 5, 7])
        # Lo que la unidad decide se respeta tal cual: sin meses marcados, sin meses.
        self.assertEqual(filas['GUIAS']['meses'], [])

    def test_sin_planes_el_mantenimiento_conserva_al_menos_un_mes_en_el_cronograma(self):
        from apps.documentos.presentation.expediente_redaccion import _bloque_cronograma

        PlanMantenimientoEquipo.objects.all().delete()
        contenido = {'actividades': {'catalogo': {
            'MANTENIMIENTO': {'aplica': True, 'meta': '', 'meses': [], 'responsable': ''}}, 'otras': []}}

        bloque = _bloque_cronograma(self.unidad, contenido, date(2026, 3, 9), date(2026, 7, 17))

        marcas = dict(bloque['filas'])['Mantenimiento preventivo y correctivo de equipos']
        self.assertEqual(sum(1 for marca in marcas if marca), 1)

    def test_las_actividades_del_catalogo_dependen_del_tipo_de_unidad(self):
        codigos = {a.codigo for a in actividades_para(self.unidad)}
        self.assertIn('PRACTICAS', codigos)
        self.assertNotIn('BOLETINES', codigos)
        observatorio = Unidad(nombre='Obs', slug='obs', dependencia='observatorios', fecha_inicio=date(2025, 1, 1))
        codigos_obs = {a.codigo for a in actividades_para(observatorio)}
        self.assertIn('BOLETINES', codigos_obs)
        self.assertNotIn('PRACTICAS', codigos_obs)
        self.assertIn('DATOS-ACTUALIZADOS', codigos_obs)
        self.assertNotIn('USO', codigos_obs)

    def test_el_formulario_se_lee_al_diccionario_de_contenido(self):
        from django.http import QueryDict

        post = QueryDict(mutable=True)
        post.update({'mision': '<p>Formar <script>alert(1)</script><b>bien</b></p>', 'estado_operativo': 'Z',
                     'act__PRACTICAS__aplica': '1', 'act__PRACTICAS__meta': '8',
                     'objetivos_especificos': '<ul><li>Uno</li><li style="color:red">Dos</li></ul>'})
        post.setlist('sectores', ['docencia', 'inventado'])
        post.setlist('act__PRACTICAS__meses', ['3', '4', '13', 'x'])
        post.setlist('otra__nombre', ['', 'Puertas abiertas'])
        post.setlist('otra__indicador', ['', 'Evento'])
        post.setlist('otra__meta', ['', '1'])
        post.setlist('otra__responsable', ['', ''])
        post.setlist('otra__meses__1', ['6'])
        post.setlist('inversion__categoria', ['equipos', ''])
        post.setlist('inversion__item', ['Switch', ''])
        post.setlist('inversion__cantidad', ['2', ''])
        post.setlist('inversion__justificacion', ['Topologías', ''])
        post.setlist('inversion__prioridad', ['alta', ''])
        post.setlist('inversion__costo_unitario', ['450', ''])
        post['cobertura_recursos'] = '<p>Recursos existentes para las prácticas.</p>'
        post['revision_recursos'] = 'revisado'

        contenido = leer_formulario('planificacion', post, self.unidad)

        # El HTML se sanea por lista blanca, igual que en las guías: sin scripts ni estilos.
        self.assertEqual(contenido['mision'], '<p>Formar <strong>bien</strong></p>')
        self.assertEqual(contenido['estado_operativo'], '')
        self.assertEqual(contenido['objetivos_especificos'], '<ul><li>Uno</li><li>Dos</li></ul>')
        self.assertEqual(contenido['sectores'], ['docencia'])
        self.assertEqual(contenido['actividades']['catalogo']['PRACTICAS']['meses'], [3, 4])
        self.assertEqual(contenido['actividades']['otras'],
                         [{'nombre': 'Puertas abiertas', 'indicador': 'Evento', 'meta': '1', 'responsable': '',
                           'meses': [6]}])
        self.assertNotIn('inversion', contenido)  # Una tabla antigua enviada por POST no crea otra solicitud.
        self.assertEqual(contenido['revision_recursos'], 'revisado')
        self.assertEqual(contenido['recursos_periodo_version'], 1)
        self.assertIn('Recursos existentes', contenido['cobertura_recursos'])

    def test_las_sugerencias_se_escriben_para_la_unidad_y_su_tipo(self):
        plan = self.documento('PLANIFICACION')
        sugerencias = sugerencias_para(plan, POLITICA_POR_CAMPO)
        etiquetas = [s['label'] for s in sugerencias['mision']]
        self.assertEqual(etiquetas[0], 'Laboratorio académico')
        self.assertIn('Computación', sugerencias['mision'][0]['html'])
        # El apartado ya se titula solo: la sugerencia entra directo al contenido.
        self.assertTrue(sugerencias['estructura'][0]['html'].startswith('<p>'))
        self.assertIn('Laboratorio de redes', sugerencias['objetivo_general'][0]['html'])
        self.assertEqual(sugerencias['descripcion'][0]['html'],
                         '<p>Laboratorio de docencia e investigación en redes.</p>')
        observatorio = Unidad.objects.create(nombre='Observatorio Territorial', slug='obs-redaccion',
                                             dependencia='observatorios', fecha_inicio=date(2025, 1, 1))
        construir_expediente(observatorio, 2026, hoy=date(2026, 9, 22))
        plan_obs = DocumentoExpediente.objects.get(unidad=observatorio, exigido__codigo='PLANIFICACION', corte='A')
        self.assertEqual(sugerencias_para(plan_obs, POLITICA_POR_CAMPO)['mision'][0]['label'], 'Observatorio')

    def test_lo_escrito_antes_como_texto_o_lista_se_convierte_a_html(self):
        plan = self.documento('PLANIFICACION')
        contenido = {**PLAN_COMPLETO, 'mision': 'Formar con práctica real.',
                     'objetivos_especificos': ['Ejecutar 8 prácticas', 'Actualizar 2 guías']}
        compuesto = componer(plan, contenido, date(2026, 3, 9), date(2026, 7, 17))
        identidad = next(s for s in compuesto['secciones'] if s['codigo'] == 'identidad')
        mision = next(b for b in identidad['bloques'] if b.get('titulo') == 'Misión')
        self.assertEqual(mision['html'], '<p>Formar con práctica real.</p>')
        objetivos = next(s for s in compuesto['secciones'] if s['codigo'] == 'objetivos')
        especificos = next(b for b in objetivos['bloques'] if b.get('titulo') == 'Objetivos específicos')
        self.assertEqual(especificos['bloques'][0]['tipo'], 'lista')
        self.assertEqual(avance('planificacion', contenido)['porcentaje'], 100)

    def test_los_meses_del_tramo_siguen_al_calendario(self):
        self.assertEqual([n for _m, n in meses_del_tramo(date(2026, 3, 9), date(2026, 7, 17))],
                         ['Mar', 'Abr', 'May', 'Jun', 'Jul'])


class ComponerYGenerarTests(BaseDeRedaccion):
    def test_plan_nuevo_propone_una_ventana_fuera_de_clases_sin_inventar_ordenes(self):
        from apps.documentos.presentation.expediente_redaccion import plan_inicial

        PlanMantenimientoEquipo.objects.all().delete()
        plan = self.documento('PLANIFICACION')
        inicial = plan_inicial(plan, date(2026, 3, 9), date(2026, 7, 17))
        self.assertEqual(inicial['catalogo']['MANTENIMIENTO']['meses'], [7])
        self.assertTrue(inicial['cronograma_auto']['mantenimiento_exigible'])
        self.assertEqual(inicial['cronograma_auto']['mantenimiento_ventana'], '2026-07-13')
        self.assertEqual(inicial['cronograma_auto']['mantenimiento_meses_por_equipo'], [])

    def test_el_inventario_resume_equipos_software_e_insumos_y_los_mantenimientos_previstos(self):
        plan = self.documento('PLANIFICACION')
        compuesto = componer(plan, PLAN_COMPLETO, date(2026, 3, 9), date(2026, 7, 17))
        inventario = next(s for s in compuesto['secciones'] if s['codigo'] == 'inventario')
        # La planificación trae el resumen y los equipos por categoría; las listas completas de equipos, software
        # e insumos se consultan en el Centro de reportes (documentos.0025).
        self.assertEqual([(b['tipo'], b.get('titulo')) for b in inventario['bloques']],
                         [('pares', 'Resumen del inventario'), ('tabla', 'Equipos por categoría'), ('parrafo', None)])
        resumen = dict(inventario['bloques'][0]['pares'])
        self.assertEqual(resumen['Equipos registrados'], '1')
        self.assertEqual(resumen['Valor referencial total (USD)'], '1,200.00')
        self.assertEqual(resumen['Software y licencias'], '1 programas · 30 licencias')
        self.assertEqual(resumen['Insumos y materiales en catálogo'], '1')
        self.assertEqual(inventario['bloques'][1]['filas'], [['Sin categoría', '1']])
        self.assertIn('Centro de reportes', inventario['bloques'][2]['texto'])
        titulos = [b.get('titulo') for b in inventario['bloques']]
        self.assertFalse({'Equipos registrados', 'Software y licencias', 'Insumos, reactivos y materiales'}
                         & set(titulos))
        cronograma = next(s for s in compuesto['secciones'] if s['codigo'] == 'cronograma')
        mantenimientos = cronograma['bloques'][1]
        self.assertEqual(mantenimientos['titulo'], 'Mantenimientos previstos por los planes de los equipos')
        self.assertEqual(mantenimientos['filas'][0],
                         ['RED-SW-01 - Switch de núcleo', 'Limpieza y firmware · Preventivo', 'cada 60 días',
                          '11/03, 10/05, 09/07'])

    def test_el_documento_compuesto_trae_lo_automatico_el_cronograma_y_la_inversion_totalizada(self):
        plan = self.documento('PLANIFICACION')
        compuesto = componer(plan, PLAN_COMPLETO, date(2026, 3, 9), date(2026, 7, 17))
        titulos = [s['titulo'] for s in compuesto['secciones']]
        self.assertEqual(len(titulos), 12)  # incluye el compromiso de capacidad y uso efectivo
        self.assertIn('Capacidad y compromiso de uso efectivo', titulos)
        general = compuesto['secciones'][0]['bloques'][0]
        self.assertIn(('Nombre', 'Laboratorio de redes'), general['pares'])
        alcance = next(s for s in compuesto['secciones'] if s['codigo'] == 'alcance')
        self.assertIn('Área de racks · Área de trabajo · capacidad 12', alcance['bloques'][0]['items'])
        identidad = next(s for s in compuesto['secciones'] if s['codigo'] == 'identidad')
        estructura = next(b for b in identidad['bloques'] if b.get('titulo') == 'Estructura orgánica-funcional')
        self.assertEqual([b['tipo'] for b in estructura['bloques']], ['subtitulo', 'parrafo'])
        cronograma = next(s for s in compuesto['secciones'] if s['codigo'] == 'cronograma')['bloques'][0]
        self.assertEqual(cronograma['meses'], ['Mar', 'Abr', 'May', 'Jun', 'Jul'])
        self.assertIn(('Jornada de puertas abiertas', [False, False, False, True, False]), cronograma['filas'])
        bloques = next(s for s in compuesto['secciones'] if s['codigo'] == 'inversion')['bloques']
        # Primero lo que el sistema sugiere; después el presupuesto que la unidad escribió.
        self.assertEqual(bloques[0]['titulo'], 'Lo que el sistema sugiere')
        inversion = next(b for b in bloques if b.get('titulo') == 'Presupuesto del período')
        self.assertEqual(inversion['filas'][-1][-1], '900.00')

    def test_no_se_genera_con_faltantes_y_si_se_genera_completo_queda_listo_para_firma(self):
        plan = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(plan)
        with self.assertRaises(ValidationError) as contexto:
            generar_documento(abrir_entrega(plan), self.coordinador)
        self.assertIn('Faltan apartados obligatorios', ' '.join(contexto.exception.messages))

        redaccion.contenido = dict(PLAN_COMPLETO, recursos_periodo_version=1,
            cobertura_recursos='<p>El inventario disponible cubre las actividades previstas.</p>',
            revision_recursos='revisado')
        redaccion.save()
        generar_documento(abrir_entrega(plan), self.coordinador)
        plan.refresh_from_db()
        redaccion.refresh_from_db()
        self.assertEqual((plan.estado, plan.version), ('generado', 1))
        self.assertTrue(plan.recurso.archivo.read().startswith(b'%PDF'))
        self.assertEqual(plan.recurso.carpeta.nombre, 'Planeación')
        self.assertIn('aprobación en la plataforma', plan.recurso.descripcion)
        self.assertIsNotNone(redaccion.generado_en)

    def test_el_informe_compara_el_plan_con_lo_registrado_y_consolida_las_acciones_de_mejora(self):
        plan = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(plan)
        redaccion.contenido = PLAN_COMPLETO
        redaccion.save()
        informe = self.documento('INFORME-SEMESTRAL')
        contenido = {
            'resumen_ejecutivo': '<p>Semestre con 7 prácticas.</p>', 'logros': '<ul><li>Red renovada</li></ul>',
            'cumplimiento': {'PRACTICAS': {'realizado': '7', 'observacion': 'Una práctica se movió a B.'}},
            'acciones': [{'hallazgo': 'Sin registro de préstamos', 'accion': 'Habilitar bitácora', 'responsable': 'Luis',
                          'plazo': '2026-08', 'estado': 'en_curso'}],
            'firma_nombre': 'Ana Coordinadora', 'firma_cargo': 'Responsable',
        }
        compuesto = componer(informe, contenido, date(2026, 3, 9), date(2026, 7, 17))
        bloques = next(s for s in compuesto['secciones'] if s['codigo'] == 'cumplimiento')['bloques']
        # 3.1 cómo se lee; 3.2 la tabla con el veredicto por meta y su anexo; 3.3 lo que falta.
        self.assertEqual((bloques[0]['tipo'], bloques[0]['titulo']), ('parrafo', 'Cómo se lee el cumplimiento'))
        self.assertIn('metas obligatorias', bloques[0]['texto'])
        self.assertIn('«Con respaldo»', bloques[0]['texto'])
        cumplimiento = bloques[1]
        self.assertEqual((cumplimiento['tipo'], cumplimiento['titulo']), ('tabla', 'Planificado frente a realizado'))
        self.assertEqual(cumplimiento['cabecera'],
                         ['Meta', 'Comprometido', 'Registrado', 'Con respaldo', 'Avance', 'Estado', 'Anexo'])
        numero = {d.exigido.codigo: n for n, d in anexos_numerados(informe)}
        fila = next(f for f in cumplimiento['filas']
                    if f[0] == 'Prácticas académicas ejecutadas con asistencia y evidencias')
        self.assertEqual(fila[1:], ['8', '0', '0', '0 %', 'No cumple', f"Anexo {numero['PRACTICAS-FT03']}"])
        propia = next(f for f in cumplimiento['filas'] if f[0] == 'Jornada de puertas abiertas')
        self.assertEqual(propia[2], '—')
        # Solo lo que no se cumple, con lo que reporta la unidad y el anexo que trae el detalle.
        faltas = bloques[2]
        self.assertEqual((faltas['titulo'], faltas['cabecera']), ('Qué falta para cumplir', ['Meta', 'Qué falta']))
        estados = {f[0]: f[5] for f in cumplimiento['filas']}
        self.assertTrue(all(estados[nombre] != 'Cumple' for nombre, _detalle in faltas['filas']))
        detalle = dict(faltas['filas'])['Prácticas académicas ejecutadas con asistencia y evidencias']
        self.assertIn('La unidad reporta 7.', detalle)
        self.assertIn('Observación de la unidad: Una práctica se movió a B.', detalle)
        self.assertIn(f"Detalle en el anexo {numero['PRACTICAS-FT03']}.", detalle)
        self.assertEqual(registros_del_periodo(self.unidad, date(2026, 3, 9), date(2026, 7, 17))['sesiones'], 0)

        redaccion_informe = obtener_redaccion(informe)
        redaccion_informe.contenido = contenido
        redaccion_informe.save()
        generar_documento(abrir_entrega(informe), self.coordinador)
        # La planificación compromete investigación y transferencia: el anexo condicional se presenta.
        investigacion = self.documento('INVESTIGACION')
        self.assertEqual(investigacion.estado, 'generado')
        self.assertTrue(investigacion.recurso.archivo.read().startswith(b'%PDF'))
        # Las acciones de mejora ya no son un anexo (documentos.0025): el apartado de mejora del informe trae las
        # de la unidad y los incumplimientos del expediente del período.
        self.assertFalse(DocumentoExpediente.objects.filter(unidad=self.unidad,
                                                            exigido__codigo='ACCIONES-MEJORA').exists())
        compuesto = componer(informe, contenido, date(2026, 3, 9), date(2026, 7, 17))
        mejora = next(s for s in compuesto['secciones'] if s['codigo'] == 'mejora')['bloques']
        self.assertIn('Entregas del expediente fuera de plazo u observadas', [b.get('titulo') for b in mejora])
        self.assertIn('Habilitar bitácora', str([b.get('filas') for b in mejora]))


class EditorEnLaConsolaTests(BaseDeRedaccion):
    def test_la_pagina_del_editor_muestra_los_apartados_lo_automatico_y_la_ayuda_final(self):
        self.client.force_login(self.coordinador)
        plan = self.documento('PLANIFICACION')

        pagina = self.client.get(self.ruta_editor(plan))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Planificación semestral del laboratorio · Período 2026-A')
        self.assertContains(pagina, 'Lo que el sistema ya sabe')
        self.assertRegex(pagina.content.decode(),
            r'<td>\s*Luis Técnico\s*</td>\s*<td>\s*Responsable técnico\s*</td>')
        self.assertContains(pagina, 'Área de racks')
        self.assertContains(pagina, 'Prácticas académicas ejecutadas con asistencia y evidencias')
        self.assertContains(pagina, 'Prácticas académicas planificadas y aprobadas')
        self.assertContains(pagina, 'Para finalizar')
        self.assertContains(pagina, 'Todavía falta:')
        self.assertContains(pagina, 'Generar y enviar')
        self.assertContains(pagina, 'expediente_editor.js')
        # Mismo editor y visor que las guías: zonas enriquecidas, sugerencias y PDF en modal.
        self.assertContains(pagina, 'guia_editor.js')
        self.assertContains(pagina, 'data-guia-campo="mision"')
        self.assertContains(pagina, 'redaccionSugerencias')
        self.assertContains(pagina, 'Laboratorio académico')
        self.assertContains(pagina, 'Obligatoria institucional')
        self.assertContains(pagina, 'font-awesome')
        self.assertContains(pagina, 'data-aula-pdf-modal')
        self.assertContains(pagina, reverse('pdf_borrador_documento_expediente', args=[self.unidad.slug, plan.pk]))

    def test_el_pdf_de_borrador_sale_aunque_falten_apartados_y_no_se_archiva(self):
        self.client.force_login(self.coordinador)
        plan = self.documento('PLANIFICACION')
        respuesta = self.client.get(reverse('pdf_borrador_documento_expediente', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('inline', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        plan.refresh_from_db()
        self.assertEqual((plan.estado, plan.recurso), ('pendiente', None))

    def test_guardar_por_ajax_devuelve_avance_y_respeta_la_version(self):
        self.client.force_login(self.coordinador)
        plan = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(plan)

        respuesta = self.client.post(self.ruta_editor(plan), {
            'version_base': str(redaccion.version), 'mision': '<p>Formar con práctica real.</p>',
            'firma_nombre': 'Ana', 'firma_cargo': 'Responsable',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['success'])
        self.assertEqual(datos['version'], redaccion.version + 1)
        self.assertGreater(datos['porcentaje'], 0)
        self.assertIn('Sectores, áreas de trabajo, servicios y productos → Sectores de aplicación', datos['faltantes'])
        redaccion = DocumentoElaborado.objects.get(documento=plan)
        self.assertEqual(redaccion.contenido['mision'], '<p>Formar con práctica real.</p>')
        self.assertEqual(redaccion.actualizado_por, self.coordinador)

        conflicto = self.client.post(self.ruta_editor(plan), {'version_base': '0', 'mision': 'otra'},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(conflicto.status_code, 409)
        self.assertTrue(conflicto.json()['conflicto'])

    def test_generar_desde_el_editor_archiva_y_vuelve_al_expediente(self):
        self.client.force_login(self.coordinador)
        plan = abrir_entrega(self.documento('PLANIFICACION'))
        redaccion = obtener_redaccion(plan)
        redaccion.contenido = PLAN_COMPLETO
        redaccion.save()

        datos = {'version_base': str(redaccion.version), 'accion': 'generar', **{
            k: v for k, v in PLAN_COMPLETO.items() if isinstance(v, str)}}
        datos['sectores'] = PLAN_COMPLETO['sectores']
        datos['act__PRACTICAS__aplica'] = '1'
        datos['act__PRACTICAS__meta'] = '8'
        datos['act__PRACTICAS__meses'] = ['3', '4']
        for codigo, actividad in PLAN_COMPLETO['actividades']['catalogo'].items():
            datos[f'act__{codigo}__responsable'] = actividad['responsable']
        datos['sin_inversion_justificacion'] = '<p>El inventario cubre el período.</p>'
        datos['cobertura_recursos'] = '<p>El inventario cubre el período; se revisó su disponibilidad.</p>'
        datos['revision_recursos'] = 'revisado'
        respuesta = self.client.post(self.ruta_editor(plan), datos)

        self.assertRedirects(respuesta, reverse('gestion_expediente_unidad', args=[self.unidad.slug]) + '?anio=2026&corte=A',
                             fetch_redirect_response=False)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'generado')
        expediente = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
                                {'anio': 2026, 'corte': 'A'})
        self.assertNotContains(expediente, '<th scope="col">Borrador</th>')
        self.assertContains(expediente, 'data-entrega-editor')
        self.assertContains(expediente, 'data-ver-pdf')
        self.assertContains(expediente, 'data-aula-pdf-modal')
        gestion = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
                                 dict(anio=2026, corte='A', gestionar=plan.pk, fragment='1'))
        self.assertContains(gestion, 'Enviar a Dirección')
        self.assertNotContains(gestion, 'type="file"')

    def test_la_vista_previa_muestra_el_documento_compuesto(self):
        self.client.force_login(self.coordinador)
        plan = self.documento('PLANIFICACION')
        pagina = self.client.get(reverse('vista_previa_documento_expediente', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Vista previa')
        self.assertContains(pagina, 'INFORMACIÓN GENERAL DE LA UNIDAD')
        self.assertContains(pagina, 'Seguir editando')

    def test_solo_los_redactables_abren_el_editor_y_solo_quien_gestiona(self):
        self.client.force_login(self.coordinador)
        practicas = self.documento('PRACTICAS-FT02')
        self.assertEqual(self.client.get(self.ruta_editor(practicas)).status_code, 404)
        ajeno = get_user_model().objects.create_user('ajeno-redaccion', password='clave-segura')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(self.ruta_editor(self.documento('PLANIFICACION'))).status_code, 403)

    def test_el_expediente_enlaza_el_editor_y_muestra_el_avance(self):
        self.client.force_login(self.coordinador)
        plan = self.documento('PLANIFICACION')
        pagina = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
                                {'anio': 2026, 'corte': 'A'})
        self.assertContains(pagina, self.ruta_editor(plan))
        self.assertContains(pagina, 'data-entrega-editor')
        self.assertContains(pagina, 'data-editor-dialogo')
        self.assertEqual(DocumentoElaborado.objects.filter(documento=plan).count(), 0)
