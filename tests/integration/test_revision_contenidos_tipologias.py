"""Contenido propio del perfil y trazabilidad de los anexos, en una base aislada."""
from datetime import date, datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.automatizacion_documental import huella
from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
from apps.documentos.presentation.expediente_redaccion import _pares_uso_informe, secciones_de
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.presentation.reportes_perfiles import _texto, dataset_perfil
from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, RegistroProduccion
from apps.plantas_piloto.operacion.models.calidad import AccionCorrectiva, ControlCalidad, NoConformidad, PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Producto, Receta


class ResumenesDePerfilTests(SimpleTestCase):
    def test_tablas_complementarias_conservan_palabras_completas_en_la_cabecera(self):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from apps.gestion_unidades.presentation.gestion_reportes import _anchos_por_contenido
        cabecera = ['Referencia', 'Fecha', 'Actividad', 'Objetivo', 'Método', 'Resultado', 'Revisión', 'Respaldo']
        filas = [['A', '01/09/2026', 'Actividad', 'Objetivo ' * 40, 'Método ' * 40,
                  'Resultado ' * 40, 'Revisión ' * 20, 'Enlace ' * 20]]
        estilo = ParagraphStyle('CabeceraQA', fontName='Helvetica-Bold', fontSize=9)
        anchos = _anchos_por_contenido(cabecera, filas, minimo=12, maximo=80, estilo_cabecera=estilo)
        self.assertAlmostEqual(sum(anchos), 264)
        for titulo, ancho in zip(cabecera, anchos):
            self.assertGreaterEqual(ancho * mm + .01, stringWidth(titulo, estilo.fontName, estilo.fontSize) + 12)

    def setUp(self):
        self.registros = dict(sesiones=5, atendidas=3, horas=4.5, usuarios=2,
            practicas_planificadas=7, practicas=2, guias=1, habilitaciones=2, servicios=1,
            desechos=0, mantenimientos=1, mantenimientos_programados=2, incidencias=0,
            gestion_boletines=2, gestion_datos_actualizados=3, gestion_eventos=1,
            gestion_produccion=4, gestion_control_calidad=5, gestion_ensayos=6)

    def resumen(self, base):
        return dict(_pares_uso_informe(SimpleNamespace(dependencia=base), self.registros))

    def test_observatorio_informa_sus_productos_y_no_formatos_de_practicas(self):
        pares = self.resumen('observatorios')
        self.assertEqual(pares['Publicaciones con revisión técnica'], '2')
        self.assertEqual(pares['Actualizaciones de series con revisión técnica'], '3')
        self.assertEqual(pares['Socializaciones con revisión técnica'], '1')
        self.assertNotIn('FT02', str(pares))
        self.assertNotIn('FT03', str(pares))
        self.assertNotIn('Registros de desechos', pares)

    def test_planta_y_centro_muestran_solo_sus_contadores_propios(self):
        planta, centro = self.resumen('plantas_piloto'), self.resumen('centro_experimental')
        self.assertEqual(planta['Órdenes de producción con revisión técnica'], '4')
        self.assertEqual(planta['Controles de calidad con revisión técnica'], '5')
        self.assertEqual(centro['Ciclos o ensayos con seguimiento y revisión técnica'], '6')
        self.assertNotIn('Publicaciones con revisión técnica', planta)
        self.assertNotIn('Órdenes de producción con revisión técnica', centro)

    def test_medicion_no_disponible_no_se_presenta_como_cero_verificado(self):
        self.registros.pop('gestion_ensayos')
        self.assertEqual(self.resumen('centro_experimental')[
            'Ciclos o ensayos con seguimiento y revisión técnica'], 'Sin medición disponible')

    def test_lectura_parcial_conserva_cifras_disponibles_sin_inventar_las_ausentes(self):
        pares = dict(_pares_uso_informe(SimpleNamespace(dependencia='observatorios'),
                                      dict(sesiones=2, horas=1.5)))
        self.assertEqual(pares['Sesiones registradas'], '2')
        self.assertEqual(pares['Horas de uso efectivas'], '1.5')
        self.assertEqual(pares['Incidencias reportadas'], 'Sin medición disponible')

    def test_ningun_perfil_declara_sustituido_el_manual_de_funciones(self):
        for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(base=base):
                secciones = secciones_de('planificacion', SimpleNamespace(dependencia=base))
                identidad = next(s for s in secciones if s.codigo == 'identidad')
                self.assertIn('Vincula el organigrama', identidad.descripcion)
                self.assertNotIn('reemplaza', identidad.descripcion)
                self.assertNotIn('sustitu', identidad.descripcion)

    @override_settings(TIME_ZONE='America/Guayaquil')
    def test_fecha_del_anexo_coincide_con_el_dia_local_de_la_actividad(self):
        instante = datetime(2026, 9, 11, 1, tzinfo=dt_timezone.utc)
        self.assertEqual(_texto(instante), '10/09/2026')


@override_settings(MEDICION_METAS_HABILITADA=False)
class AnexosDePerfilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('contenido-perfiles-qa', first_name='Ana', last_name='Técnica')
        cls.planta = Unidad.objects.create(nombre='Planta contenido QA', slug='planta-contenido-qa',
            dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))
        cls.centro = Unidad.objects.create(nombre='Centro contenido QA', slug='centro-contenido-qa',
            dependencia='centro_experimental', fecha_inicio=date(2026, 1, 1))
        cls.producto = Producto.objects.create(unidad=cls.planta, codigo='CONT-PROD-QA', nombre='Producto QA',
            unidad_medida='kg')
        cls.receta = Receta.objects.create(unidad=cls.planta, producto=cls.producto, codigo='CONT-REC-QA',
            nombre='Proceso QA', cantidad_base=10, unidad_base='kg', rendimiento_esperado=10)
        cls.orden = OrdenProduccion.objects.create(unidad=cls.planta, receta=cls.receta,
            fecha_inicio=date(2026, 9, 10), fecha_fin=date(2026, 9, 10), cantidad_obtenida=8)
        cls.plan = PlanCalidad.objects.create(unidad=cls.planta, codigo='CONT-CAL-QA', nombre='Calidad QA')
        cls.control = ControlCalidad.objects.create(unidad=cls.planta, plan=cls.plan, orden=cls.orden,
            fecha=datetime(2026, 9, 10, 18, tzinfo=dt_timezone.utc), registrado_por=cls.actor, resultado='no_conforme')
        cls.hallazgo = NoConformidad.objects.create(unidad=cls.planta, control=cls.control,
            descripcion='Desviación real de temperatura QA', causa='Ajuste del equipo QA',
            detectada_en=datetime(2026, 9, 10, 18, tzinfo=dt_timezone.utc))
        AccionCorrectiva.objects.create(no_conformidad=cls.hallazgo, descripcion='Calibrar sensor QA',
            responsable=cls.actor, fecha_compromiso=date(2026, 9, 20), estado='pendiente')
        parcela = EspacioReservable.objects.create(unidad=cls.centro, nombre='Parcela QA', tipo='parcela')
        eje = EjeProductivo.objects.create(unidad=cls.centro, codigo='cont-eje-qa', titulo='Eje QA',
            resumen='Seguimiento de cultivo QA', que_produce='Producto QA')
        cls.ciclo = CicloProductivo.objects.create(eje=eje, lugar=parcela, nombre='Ciclo plurianual QA',
            tipo='cultivo', rubro='Papa QA', inicio=date(2026, 8, 1), fin_previsto=date(2027, 2, 1),
            superficie_ha=2, animales=0, meta=120, unidad_medida='kg', referencia='Plan experimental QA', estado='en_curso')
        RegistroProduccion.objects.create(ciclo=cls.ciclo, fecha=date(2026, 9, 11), tipo='pesaje',
            cantidad=0, unidad_medida='kg', detalle='Medición inicial QA', registrado_por=cls.actor)

    def reporte(self, categoria, unidad, **kwargs):
        return dataset_perfil(categoria, unidad, date(2026, 8, 17), date(2026, 10, 1), **kwargs)

    def test_calidad_incluye_hallazgo_accion_y_responsable_sin_presumir_cierre(self):
        reporte = self.reporte('control-calidad', self.planta)
        tablas = {t['titulo']: t for t in reporte['tablas']}
        hallazgos = tablas['No conformidades del período y pendientes anteriores']['rows']
        acciones = tablas['Acciones correctivas y verificación de cierre']['rows']
        self.assertIn('Desviación real de temperatura QA', str(hallazgos))
        self.assertIn('Ajuste del equipo QA', str(hallazgos))
        self.assertIn('Abierta', str(hallazgos))
        self.assertIn('Calibrar sensor QA', str(acciones))
        self.assertIn('Ana Técnica', str(acciones))
        self.assertIn('Pendiente', str(acciones))
        self.assertNotIn('Verificada', str(acciones))

    def test_busqueda_aplica_tambien_a_no_conformidades_y_acciones(self):
        vacio = self.reporte('control-calidad', self.planta, buscar='NO-EXISTE-QA')
        self.assertTrue(all(not t['rows'] for t in vacio['tablas']))
        encontrada = self.reporte('control-calidad', self.planta, buscar=self.hallazgo.codigo)
        self.assertTrue(any(self.hallazgo.codigo in str(t['rows']) for t in encontrada['tablas']))

    def test_no_conformidad_demostrativa_no_se_incluye(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(demostrativa=True)
        reporte = self.reporte('control-calidad', self.planta)
        self.assertEqual(reporte['rows'], [])
        self.assertTrue(all(not t['rows'] for t in reporte['tablas']))

    def test_ensayo_distingue_alcance_meta_unidad_y_seguimiento_del_semestre(self):
        reporte = self.reporte('ensayos', self.centro)
        tablas = {t['titulo']: t for t in reporte['tablas']}
        contexto = tablas['Alcance y metas de los ciclos o ensayos']
        self.assertIn('Meta del ciclo', contexto['headers'])
        self.assertIn('Unidad', contexto['headers'])
        self.assertIn('Papa QA', str(contexto['rows']))
        self.assertIn('Plan experimental QA', str(contexto['rows']))
        self.assertIn('kilogramos', str(contexto['rows']))
        self.assertEqual(contexto['rows'][0][3], '0')
        seguimiento = tablas['Seguimiento, mediciones y observaciones del semestre']['rows']
        self.assertEqual(seguimiento[0][3], '0.00')
        self.assertIn('ciclo completo', ' '.join(reporte['notes']))

    def test_cantidad_producida_identifica_su_unidad_de_medida(self):
        reporte = self.reporte('produccion', self.planta)
        self.assertEqual(reporte['rows'][0][5], '8.000 kg')

    def test_editar_hallazgo_o_accion_invalida_la_huella_de_fuentes_del_anexo(self):
        def fuentes():
            return ContextoCalidad(self.planta, date(2026, 8, 17), date(2026, 10, 1)).analizar('PP-CALIDAD')['fuentes']

        originales = fuentes()
        captura = next(c for c in originales['datos']['nativos'] if c.get('modelo') == 'no_conformidad')
        self.assertEqual(captura['causa'], 'Ajuste del equipo QA')
        self.assertEqual(captura['acciones'][0]['descripcion'], 'Calibrar sensor QA')
        firma_original = huella(originales)
        NoConformidad.objects.filter(pk=self.hallazgo.pk).update(causa='Causa revisada QA', disposicion='reproceso')
        firma_hallazgo = huella(fuentes())
        self.assertNotEqual(firma_hallazgo, firma_original)
        AccionCorrectiva.objects.filter(no_conformidad=self.hallazgo).update(
            descripcion='Sustituir sensor QA', verificacion='Resultado de comprobación QA')
        self.assertNotEqual(huella(fuentes()), firma_hallazgo)

    def test_limite_de_acciones_se_informa_y_conserva_todas_las_fuentes(self):
        AccionCorrectiva.objects.bulk_create([AccionCorrectiva(no_conformidad=self.hallazgo,
            descripcion=f'Acción adicional QA {i}') for i in range(500)])
        reporte = self.reporte('control-calidad', self.planta)
        tabla = next(t for t in reporte['tablas'] if t['titulo'] == 'Acciones correctivas y verificación de cierre')
        self.assertEqual(len(tabla['rows']), 500)
        self.assertEqual(tabla['total'], 501)
        self.assertTrue(tabla['truncated'])
        self.assertTrue(reporte['truncated'])
        captura = next(c for c in reporte['fuentes_nativas'] if c.get('modelo') == 'no_conformidad')
        self.assertEqual(len(captura['acciones']), 501)
