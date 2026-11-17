"""Filtros, alcance y consultas del centro de reportes (auditoría A08)."""

from datetime import date, time, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.configuracion_institucional.tipologias.models import TipologiaUnidad
from apps.documentos.presentation.cumplimiento import cumplimiento_por_periodo, unidades_auditadas
from apps.documentos.presentation.expediente import leer_expedientes
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.gestion_unidades.presentation.reportes_consolidados import evidencias_por_unidad
from apps.gestion_unidades.presentation.reportes_evidencias import disponibilidad_de_unidades, reporte_guias
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte, anio_pedido
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_reportes_evidencias import BaseDeReportes


class PeriodoTests(SimpleTestCase):
    def test_rechaza_fechas_imposibles_y_anios_fuera_del_calendario(self):
        for valor in ('2026-02-31', 'texto', '20260301', '9999-12-31'):
            with self.subTest(valor=valor), self.assertRaises(BadRequest):
                PeriodoReporte.pedido({'desde': valor})
        for valor in ('-1', '10000', 'texto'):
            with self.subTest(valor=valor), self.assertRaises(BadRequest):
                anio_pedido(valor, 2026)

    def test_normaliza_y_propaga_el_mismo_tramo(self):
        tramo = PeriodoReporte.pedido({'desde': '2026-03-10', 'hasta': '2020-01-01'}, maximo_dias=730)
        self.assertEqual(tramo.desde, date(2026, 3, 10) - timedelta(days=730))
        self.assertEqual(parse_qs(tramo.query()), {k: [v] for k, v in tramo.parametros().items()})


class FiltrosIntegradosTests(BaseDeReportes):
    def test_fecha_imposible_es_400_en_las_tres_salidas(self):
        for formato in ('', 'pdf', 'xlsx'):
            with self.subTest(formato=formato):
                self.assertEqual(self.reporte('reservas', formato, desde='2026-02-31').status_code, 400)

    def test_consolidado_abre_la_categoria_con_el_periodo_original(self):
        filas, _ = evidencias_por_unidad(['laboratorios'], self.desde, self.hasta, self.coordinador)
        for enlace in [filas[0]['url'], *filas[0]['informes'].values()]:
            consulta = parse_qs(urlsplit(enlace).query)
            self.assertEqual(consulta['desde'], ['2026-03-01'])
            self.assertEqual(consulta['hasta'], ['2026-03-10'])
            if enlace != filas[0]['url']:
                self.assertIn('categoria_reporte', consulta)
        direccion = get_user_model().objects.create_superuser('direccion-filtros', 'd@example.test', 'clave')
        self.client.force_login(direccion)
        pagina = self.client.get(filas[0]['informes']['guias'])
        self.assertEqual(pagina.status_code, 200)
        self.assertTrue(pagina.content.startswith(b'%PDF'))
        self.assertIn('2026-03-01', pagina['Content-Disposition'])
        self.assertIn('2026-03-10', pagina['Content-Disposition'])

    def test_guias_vigentes_y_actualizadas_coinciden_en_detalle_y_consolidado(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Práctica')
        for vigente, numero in ((False, 1), (True, 2)):
            guia = GuiaActividadReserva.objects.create(actividad=actividad, titulo=f'Guía {numero}',
                numero_version=numero, es_vigente=vigente, estado_publicacion='publicada')
            GuiaActividadReserva.objects.filter(pk=guia.pk).update(actualizado_en='2025-01-01T12:00:00Z')
        _, totales = evidencias_por_unidad(['laboratorios'], self.desde, self.hasta, self.coordinador)
        _, filas, _, _ = reporte_guias(self.unidad, self.desde, self.hasta, state='publicada')
        self.assertEqual(totales['guias_publicadas'], 1)
        self.assertEqual(len(filas), 1)

    def test_varias_evidencias_no_multiplican_las_ejecuciones(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Práctica')
        plan = PlanificacionPractica.objects.create(unidad=self.unidad, actividad=actividad,
            fecha=self.desde, hora_inicio=time(9), hora_fin=time(11), creado_por=self.coordinador)
        ejecucion = EjecucionPractica.objects.create(planificacion=plan, fecha_ejecucion=self.desde,
            hora_inicio_real=time(9), hora_fin_real=time(11), creado_por=self.coordinador)
        for indice in range(3):
            EvidenciaPractica.objects.create(ejecucion=ejecucion, tipo='foto',
                archivo=f'pruebas/{indice}.png', nombre_original=f'{indice}.png', descripcion='Registro')
        _, totales = evidencias_por_unidad(['laboratorios'], self.desde, self.hasta, self.coordinador)
        self.assertEqual(totales['ejecuciones'], 1)
        self.assertEqual(totales['ejecuciones_con_evidencia'], 1)


class AlcanceEstadisticasTests(BaseDeReportes):
    def test_enlaces_reales_de_los_tres_reportes_abren_la_unidad(self):
        from html import unescape
        import re

        asegurar_catalogo()
        destino = reverse('admin:reportes-cumplimiento-expediente')
        for nombre in ('reportes-institucional', 'reportes-evidencias-por-tipo', 'reportes-expediente-por-tipo'):
            pagina = self.client.get(reverse('admin:' + nombre), {'anio': 2026}, follow=True)
            self.assertEqual(pagina.status_code, 200)
            enlaces = [unescape(url) for url in re.findall(r'href="([^"]+)"', pagina.content.decode())
                       if url.startswith(destino + '?')]
            if pagina.redirect_chain and pagina.redirect_chain[-1][0].startswith(destino):
                # Este acceso anterior lleva al propio tablero, cuyos vínculos a la unidad son relativos.
                # Los vínculos absolutos venían de los soportes de la planificación, que ya no hay (documentos.0024).
                self.assertIn(self.unidad.slug, [f['unidad'].slug for f in pagina.context['filas']])
                continue
            self.assertTrue(enlaces, nombre)
            for enlace in enlaces:
                with self.subTest(origen=nombre, enlace=enlace):
                    respuesta = self.client.get(enlace)
                    self.assertEqual(respuesta.status_code, 200)
                    slug = parse_qs(urlsplit(enlace).query)['unidad'][0]
                    self.assertEqual(respuesta.context['unidad'], slug)
                    self.assertEqual([f['unidad'].slug for f in respuesta.context['filas']], [slug])

    def test_identificador_numerico_se_normaliza_sin_ampliar_el_alcance(self):
        from django.contrib.auth.models import Permission

        asegurar_catalogo()
        url = reverse('admin:reportes-cumplimiento-expediente')
        for valor in (self.unidad.pk, self.unidad.slug):
            respuesta = self.client.get(url, {'unidad': valor, 'anio': 2026})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.context['unidad'], self.unidad.slug)
        self.coordinador.is_staff = True
        self.coordinador.save(update_fields=['is_staff'])
        self.coordinador.user_permissions.add(Permission.objects.get(
            content_type__app_label='documentos', codename='view_documentoexpediente'))
        ajena = Unidad.objects.create(nombre='Fuera de alcance', slug='fuera-alcance', dependencia='laboratorios',
                                      fecha_inicio=self.desde, administrador=self.direccion)
        self.client.force_login(self.coordinador)
        for valor in (ajena.pk, ajena.slug, 99999999):
            self.assertEqual(self.client.get(url, {'unidad': valor}).status_code, 400)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.direccion = get_user_model().objects.create_superuser('direccion-reportes', 'reportes@example.org', 'clave')
        cls.planta = Unidad.objects.create(nombre='Planta de prueba', slug='planta-reporte',
            dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1), administrador=cls.coordinador)

    def setUp(self):
        self.client.force_login(self.direccion)

    def test_html_y_pdf_comparten_anio_agrupacion_y_alcance_del_proxy(self):
        self.reserva(laboratorio=self.planta)
        self.reserva(laboratorio=self.planta, fecha=date(2025, 3, 4))
        self.reserva()
        parametros = {'year': '2026', 'por_laboratorio': '1'}
        pagina = self.client.get(reverse('admin:plantas_piloto-reservas-estadisticas'), parametros)
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context['filas'], [('Planta de prueba', 1, 0, 100.0)])
        self.assertIn('year=2026', pagina.context['url_pdf'])
        with patch('apps.reservas.admin.reservas.render_unit_report_pdf', return_value=b'%PDF-test') as render:
            pdf = self.client.get(pagina.context['url_pdf'])
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(render.call_args.args[0]['dataset']['rows'], pagina.context['filas'])
        self.assertIn(('Registros', 1), render.call_args.args[0]['filter_summary'])

    def test_enlaces_del_listado_permanecen_en_su_seccion(self):
        pagina = self.client.get(reverse('admin:plantas_piloto_reserva_changelist'), {'todas': '1'})
        for nombre in ('reporte-uso', 'reporte-listado', 'estadisticas'):
            self.assertContains(pagina, reverse('admin:plantas_piloto-reservas-' + nombre))

    def test_estadisticas_semanales_y_pdf_real_respetan_el_anio(self):
        self.reserva()
        self.reserva(fecha=date(2025, 3, 4))
        pagina = self.client.get(reverse('admin:reservas-estadisticas'), {'year': '2026'})
        self.assertEqual(pagina.context['filas'], [('02/03/2026', 1, 0, 100.0)])
        pdf = self.client.get(pagina.context['url_pdf'])
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_entradas_invalidas_no_amplian_el_reporte(self):
        casos = [('reportes-cumplimiento-expediente', {'anio': '10000'}),
                 ('reportes-cumplimiento-expediente', {'unidad': 'inexistente'}),
                 ('reportes-evidencias-por-tipo', {'desde': '2026-02-31'}),
                 ('reservas-estadisticas', {'year': 'texto'}),
                 ('reservas-reporte-uso', {'unidad': 'texto'}),
                 ('plantas_piloto-reservas-reporte-uso', {'unidad': self.unidad.pk})]
        for nombre, parametros in casos:
            with self.subTest(nombre=nombre, parametros=parametros):
                self.assertEqual(self.client.get(reverse('admin:' + nombre), parametros).status_code, 400)

    def test_ser_staff_no_otorga_acceso_a_estadisticas_y_exportaciones(self):
        ajeno = get_user_model().objects.create_user('sin-permiso-reportes', is_staff=True)
        self.client.force_login(ajeno)
        for nombre in ('reservas-estadisticas', 'reservas-descargar-pdf', 'reservas-reporte-uso', 'reservas-reporte-listado'):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse('admin:' + nombre)).status_code, 403)


class SubtiposYRendimientoTests(BaseDeReportes):
    def test_subtipo_hereda_obligaciones_y_aparece_en_el_filtro_base(self):
        TipologiaUnidad.objects.create(codigo='invernaderos', nombre='Invernadero', nombre_plural='Invernaderos',
            nombre_en='Greenhouse', nombre_plural_en='Greenhouses', icono='iconsminds-plant', orden=5)
        self.unidad.dependencia = 'invernaderos'
        self.unidad.save(update_fields=['dependencia'])
        asegurar_catalogo()
        exigido = DocumentoExigido.objects.filter(activo=True).first()
        exigido.tipos_unidad = ['laboratorios']
        exigido.save(update_fields=['tipos_unidad'])
        for tipos in (None, ('laboratorios',), ('invernaderos',)):
            self.assertIn(self.unidad, unidades_auditadas(self.coordinador, tipos))
        documentos = leer_expedientes([self.unidad], 2026)[self.unidad.pk]
        self.assertTrue(any(d.exigido_id == exigido.pk for d in documentos))

    def test_treinta_unidades_con_documentos_y_equipos_mantienen_presupuesto(self):
        asegurar_catalogo()
        unidades = [self.unidad]
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model.objects.create(codigo='EQ-CARGA', nombre='Equipo')
        for indice in range(29):
            unidades.append(Unidad.objects.create(nombre=f'Unidad {indice}', slug=f'carga-{indice}',
                dependencia='laboratorios', fecha_inicio=self.desde, administrador=self.coordinador))
        for indice, unidad in enumerate(unidades):
            UnidadEquipo.objects.create(laboratorio=unidad, equipo=catalogo, codigo_unidad=f'CARGA-{indice}')
        proyecciones = leer_expedientes(unidades, 2026, hoy=self.hasta)
        DocumentoExpediente.objects.bulk_create([d for documentos in proyecciones.values() for d in documentos])
        with CaptureQueriesContext(connection) as consultas:
            filas, _ = cumplimiento_por_periodo(2026, usuario=self.coordinador, hoy=self.hasta)
        self.assertEqual(len(filas), 30)
        self.assertLessEqual(len(consultas), 18)
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))
        with CaptureQueriesContext(connection) as consultas:
            filas, _ = evidencias_por_unidad(['laboratorios'], self.desde, self.hasta, self.coordinador)
        self.assertEqual(len(filas), 30)
        # Catorce fijas aunque sean treinta unidades: una resuelve el alcance por permisos de reportes y
        # dos comprueban, sin caché, la cuenta activa y la designación de seguimiento de quien consulta.
        self.assertLessEqual(len(consultas), 14)
        activo = UnidadEquipo.objects.filter(laboratorio=unidades[0]).first()
        activo.laboratorios.add(unidades[1])
        with self.assertNumQueries(3):
            disponibilidad = disponibilidad_de_unidades(unidades, self.desde, self.hasta)
        self.assertEqual(disponibilidad[unidades[0].pk][activo.pk], disponibilidad[unidades[1].pk][activo.pk])
