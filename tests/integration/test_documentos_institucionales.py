"""Un solo formato para toda la documentación, y una sola ruta para entregarla.

La guía de práctica, la planificación, el informe y los reportes del Centro
comparten el mismo marco: caja con el logo, nombre del formato, código y
metadatos a la derecha, y al pie «Página: n de N». El Centro de reportes
consulta; lo que la unidad entrega y se audita vive en el expediente, y cada
categoría dice a qué documento del expediente alimenta.
"""

import tempfile
from datetime import date, time
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm

from apps.documentos.presentation.expediente import construir_expediente, generar_documento
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente_redaccion import obtener_redaccion
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, documentos_del_expediente, render_unit_report_pdf
from apps.core.presentation.pdf_institucional import encabezado_en_flujo, marco_institucional
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva
from apps.documentos.models.expediente import DocumentoExpediente
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import abrir_entrega, identificar

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix='citt-documentos-')


class MarcoInstitucionalTests(TestCase):
    def test_las_medidas_son_las_mismas_en_vertical_y_en_apaisado(self):
        _dibujar, _lienzo, vertical = marco_institucional(formato='FORMATO GUÍA DE PRÁCTICA')
        _dibujar2, _lienzo2, apaisado = marco_institucional(formato='REPORTE INSTITUCIONAL', apaisado=True)

        self.assertEqual(vertical['pagesize'], A4)
        self.assertEqual(apaisado['pagesize'], landscape(A4))
        # El contenido empieza bajo el encabezado en ambos: 10 mm de aire + 21 de caja + 3 de respiro.
        self.assertEqual(vertical['margen_superior'], apaisado['margen_superior'])
        self.assertAlmostEqual(vertical['margen_superior'], 34 * mm, places=3)
        self.assertAlmostEqual(vertical['ancho_util'], 210 * mm - 28 * mm, places=3)
        self.assertAlmostEqual(apaisado['ancho_util'], 297 * mm - 26 * mm, places=3)
        self.assertEqual(set(vertical['colores']), set(apaisado['colores']))

    def test_el_encabezado_escribe_el_formato_los_metadatos_y_el_pie(self):
        dibujar, CanvasNumerado, medidas = marco_institucional(
            formato='FORMATO PLANIFICACIÓN SEMESTRAL',
            metadatos=('Código: AP-P-LAP-GO', 'Revisión: 01', 'Período: Período 2026-A', 'Versión: 2'),
            pie='Expediente de calidad',
        )
        memoria = BytesIO()
        lienzo = CanvasNumerado(memoria, pagesize=medidas['pagesize'], pageCompression=0)

        dibujar(lienzo, None)
        lienzo.showPage()
        dibujar(lienzo, None)
        lienzo.showPage()
        lienzo.save()

        contenido = memoria.getvalue()
        self.assertTrue(contenido.startswith(b'%PDF'))
        texto = contenido.decode('latin-1')
        self.assertIn('FORMATO PLANIFICACI', texto)
        self.assertIn('Revisi', texto)
        self.assertIn('AP-P-LAP-GO', texto)
        self.assertIn('Expediente de calidad', texto)
        # El total solo se conoce al cerrar: las dos páginas dicen «de 2».
        self.assertEqual(texto.count('de 2'), 2)

    def test_nunca_pinta_mas_metadatos_de_los_que_caben(self):
        dibujar, CanvasNumerado, medidas = marco_institucional(
            formato='FORMATO', metadatos=[f'Línea {n}' for n in range(9)])
        memoria = BytesIO()
        lienzo = CanvasNumerado(memoria, pagesize=medidas['pagesize'], pageCompression=0)

        dibujar(lienzo, None)
        lienzo.showPage()
        lienzo.save()

        texto = memoria.getvalue().decode('latin-1')
        self.assertIn('nea 3', texto)
        self.assertNotIn('nea 4', texto)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class MismoFormatoEnTodoDocumentoTests(TestCase):
    """Los tres generadores declaran su formato en el mismo marco."""

    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-documentos', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de documentos', slug='laboratorio-documentos', dependencia='laboratorios',
            descripcion='Laboratorio de prueba.', fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)
        periodo = PeriodoAcademico.objects.create(
            codigo='2026-A', nombre='Período 2026-A', anio_referencia=2026, ciclo='A', tipo='ordinario',
            ambito='carreras_centros', semanas_planificadas=16, estado='publicado')
        VersionCalendarioAcademico.objects.create(
            periodo=periodo, numero=1, nombre='Calendario', fecha_inicio_clases=date(2026, 3, 9),
            fecha_fin_clases=date(2026, 7, 10), fecha_fin_periodo=date(2026, 7, 17), vigente=True)

    def test_la_guia_declara_su_formato_en_el_marco_comun(self):
        from apps.reservas.presentation import guias

        actividad = CatalogoActividadReserva.objects.create(
            nombre='Práctica de documentos', unidad=self.unidad, creado_por=self.coordinador,
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular')
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía de documentos', es_estructurada=True, contenido={})

        with patch.object(guias, 'marco_institucional', wraps=marco_institucional) as marco:
            contenido = guias.construir_pdf_guia(guia)

        self.assertTrue(contenido.startswith(b'%PDF'))
        argumentos = marco.call_args.kwargs
        self.assertEqual(argumentos['formato'], 'Guía de práctica')
        self.assertIn('Código: UPEC-P10-S01-FT04', argumentos['metadatos'])
        self.assertEqual(argumentos['pie'], 'Guías de práctica')

    def test_la_planificacion_declara_su_formato_en_el_marco_comun(self):
        from apps.documentos.presentation import expediente_pdf

        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        plan = DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='PLANIFICACION', anio=2026, corte='A')
        obtener_redaccion(plan)

        self.client.force_login(self.coordinador)
        with patch.object(expediente_pdf, 'marco_institucional', wraps=marco_institucional) as marco:
            pdf = self.client.get(
                reverse('pdf_borrador_documento_expediente', args=[self.unidad.slug, plan.pk]))

        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        argumentos = marco.call_args.kwargs
        self.assertEqual(argumentos['formato'], 'Formato Planificación semestral de actividades de la unidad')
        self.assertEqual(argumentos['pie'], 'Expediente de calidad')
        self.assertIn('Período: 2026-A', argumentos['metadatos'])
        self.assertIn('Revisión: 01', argumentos['metadatos'])

    def test_el_reporte_del_centro_usa_el_mismo_marco_apaisado(self):
        peticion = RequestFactory().get('/', {'categoria_reporte': 'planificaciones'})
        peticion.user = self.coordinador
        reporte = build_unit_report(peticion, self.unidad)

        with patch('apps.core.presentation.pdf_institucional.marco_institucional', wraps=marco_institucional) as marco:
            contenido = render_unit_report_pdf(reporte)

        self.assertTrue(contenido.startswith(b'%PDF'))
        argumentos = marco.call_args.kwargs
        self.assertTrue(argumentos['apaisado'])
        # Un formato institucional se anuncia por su nombre; una consulta, como reporte.
        self.assertEqual(argumentos['formato'], 'PLANIFICACIÓN DE USO DE LABORATORIOS')
        self.assertIn('Código: UPEC-P10-S01-FT02', argumentos['metadatos'])
        self.assertEqual(argumentos['pie'], 'Centro de reportes')

        peticion = RequestFactory().get('/', {'categoria_reporte': 'auditoria'})
        peticion.user = self.coordinador
        with patch('apps.core.presentation.pdf_institucional.marco_institucional', wraps=marco_institucional) as marco:
            render_unit_report_pdf(build_unit_report(peticion, self.unidad))
        self.assertEqual(marco.call_args.kwargs['formato'], 'Auditoría y trazabilidad')

    def test_los_formatos_de_practica_abren_cada_uno_con_su_encabezado(self):
        from apps.formacion.presentation import practicas

        actividad = CatalogoActividadReserva.objects.create(
            nombre='Práctica de manufactura', unidad=self.unidad, creado_por=self.coordinador,
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular')
        plan = PlanificacionPractica.objects.create(
            codigo='PL-DOC-0001', unidad=self.unidad, actividad=actividad, fecha=date(2026, 4, 8),
            hora_inicio=time(9, 0), hora_fin=time(11, 0), asignatura='Manufactura', docente_tutor='Ana',
            tema='Impresión 3D', resultado_aprendizaje='Imprime una pieza', estado='aprobada',
            creado_por=self.coordinador)

        with patch.object(practicas, 'encabezado_en_flujo', wraps=encabezado_en_flujo) as encabezado:
            contenido = practicas._render_practice_pdf(plan, None)

        self.assertTrue(contenido.startswith(b'%PDF'))
        formatos = [llamada.kwargs['formato'] for llamada in encabezado.call_args_list]
        self.assertEqual(formatos, ['PLANIFICACIÓN DE USO DE LABORATORIOS'])
        self.assertIn('Código: UPEC-P10-S01-FT02', encabezado.call_args.kwargs['metadatos'])

        ejecucion = EjecucionPractica.objects.create(
            planificacion=plan, fecha_ejecucion=date(2026, 4, 8), estado='validada', resultado='ejecutada',
            estudiantes_asistentes=12, creado_por=self.coordinador)
        with patch.object(practicas, 'encabezado_en_flujo', wraps=encabezado_en_flujo) as encabezado:
            practicas._render_practice_pdf(plan, ejecucion)
        # Dos formatos en el mismo archivo: cada uno se anuncia con su código.
        self.assertEqual([llamada.kwargs['formato'] for llamada in encabezado.call_args_list],
                         ['PLANIFICACIÓN DE USO DE LABORATORIOS',
                          'REGISTRO DE EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS'])

    def test_el_documento_generado_al_expediente_sigue_saliendo_en_pdf(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        informe = DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='INFORME-SEMESTRAL', anio=2026, corte='A')

        generar_documento(abrir_entrega(informe), self.coordinador)

        guias = DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='GUIAS', anio=2026, corte='A')
        self.assertTrue(guias.recurso.archivo.read().startswith(b'%PDF'))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RutaDelCentroDeReportesTests(TestCase):
    """El centro consulta; el expediente recibe. Cada categoría dice dónde cuenta."""

    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-ruta', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de ruta', slug='laboratorio-ruta', dependencia='laboratorios',
            descripcion='Laboratorio de prueba.', fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)

    def test_las_categorias_que_alimentan_el_expediente_estan_identificadas(self):
        exigidos = documentos_del_expediente(self.unidad)

        self.assertEqual(exigidos['guias'].codigo, 'GUIAS')
        self.assertEqual(exigidos['reservas'].codigo, 'REGISTRO-USO')
        self.assertEqual(exigidos['recursos'].codigo, 'INVENTARIO-CORTE')
        # Una consulta de apoyo no es un documento exigido.
        self.assertNotIn('auditoria', exigidos)
        self.assertNotIn('aula', exigidos)

    def test_lo_que_carga_la_unidad_se_distingue_de_lo_que_produce_el_sistema(self):
        """Quién pone cada documento: la unidad lo carga o el sistema lo produce."""
        from apps.documentos.models.expediente import DocumentoExigido

        codigos = [
            exigido.codigo
            for exigido in DocumentoExigido.objects.filter(activo=True, origen__in=('unidad', 'ambos'))
            if exigido.aplica_a(self.unidad.dependencia)
        ]

        self.assertIn('PLANIFICACION', codigos)
        self.assertIn('INFORME-SEMESTRAL', codigos)
        self.assertIn('RESOLUCION-CREACION', codigos)
        # Lo que produce el sistema no se le pide cargado a la unidad.
        self.assertNotIn('REGISTRO-USO', codigos)
        self.assertNotIn('ACCIONES-MEJORA', codigos)

    def test_el_reporte_dice_a_que_documento_del_expediente_alimenta(self):
        peticion = RequestFactory().get('/', {'categoria_reporte': 'guias'})
        peticion.user = self.coordinador

        reporte = build_unit_report(peticion, self.unidad)

        ruta = reporte['expediente']
        self.assertEqual(ruta['carpeta'], 'Ejecución')
        self.assertTrue(ruta['lo_genera_el_sistema'])
        self.assertIn('Registro de guías de práctica', ruta['nombre'])
        self.assertEqual(ruta['url'], reverse('gestion_expediente_unidad', args=[self.unidad.slug]))
        self.assertIn('guias', reporte['choices']['expediente'])

        peticion = RequestFactory().get('/', {'categoria_reporte': 'auditoria'})
        peticion.user = self.coordinador
        self.assertIsNone(build_unit_report(peticion, self.unidad)['expediente'])

    def test_el_centro_de_reportes_es_el_expediente_dentro_de_la_consola(self):
        """Abrir la pestaña trae el expediente entero junto al menú de la consola."""
        self.client.force_login(self.coordinador)

        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'reportes'})

        self.assertIsNotNone(panel.context['expediente_consola'])
        self.assertContains(panel, 'data-management-target="reportes"')
        self.assertContains(panel, 'class="entregas__tabla entregas__tabla--simple"')
        self.assertContains(panel, 'expediente-en-consola')
        # La misma interfaz de la página, sin repetir su portada ni ofrecerla aparte.
        self.assertNotContains(panel, 'Pantalla completa')
        self.assertNotContains(panel, 'LO QUE LA UNIDAD ENTREGA')
        # Los enlaces del período se quedan en la consola.
        self.assertContains(panel, '?view=reportes&amp;anio=')
        # Sin informe elegido no se suelta ninguno ni sus filtros.
        self.assertNotContains(panel, 'unit-console__report-filters')
    def test_el_consolidado_de_todas_las_unidades_se_anuncia_como_lo_que_es(self):
        self.client.force_login(self.coordinador)

        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'reportes'})

        self.assertContains(panel, reverse('reporte_institucional'))
        self.assertContains(panel, 'Reporte institucional')

    def test_al_abrir_un_informe_se_ve_entero_y_se_vuelve_al_expediente(self):
        self.client.force_login(self.coordinador)

        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
                                {'view': 'reportes', 'categoria_reporte': 'guias'})

        self.assertContains(panel, 'unit-console__report-filters')
        self.assertContains(panel, 'unit-console__report-preview')
        self.assertContains(panel, 'Volver a las entregas del período')
        self.assertContains(panel, 'CONSULTA Y ANÁLISIS')
        # Las guías son un anexo del informe: el Centro lo dice, y dice que aquí solo se consulta.
        self.assertContains(panel, 'anexo del informe de cierre')
        self.assertContains(panel, 'el sistema lo adjunta con las fechas del período')
        # El expediente no se repite debajo del informe.
        self.assertNotContains(panel, 'class="entregas__tabla"')
