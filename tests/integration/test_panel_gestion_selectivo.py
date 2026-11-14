"""El panel carga solo el módulo solicitado y conserva el alcance de la unidad."""
import re
from datetime import date, time, timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.reservas.models.reservas import Reserva
from tests.integration import test_panel_gestion_unidad as fixtures


class CargaSelectivaGestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PanelGestionUnidadTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.coordinador)

    def test_cursos_no_construye_otros_modulos_ni_sus_formularios(self):
        with patch('apps.gestion_unidades.presentation.gestion._datos_reservas_panel', side_effect=AssertionError('reservas cerradas')), \
             patch('apps.gestion_unidades.presentation.gestion._datos_recursos_panel', side_effect=AssertionError('recursos cerrados')), \
             patch('apps.gestion_unidades.presentation.gestion.contexto_seguridad', side_effect=AssertionError('seguridad cerrada')), \
             patch('apps.gestion_unidades.presentation.gestion.contexto_del_expediente', side_effect=AssertionError('reportes cerrados')):
            response = self.client.get(self.url, {'view': 'cursos', 'fragment': '1', 'modal': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-management-view="cursos"')
        self.assertContains(response, 'data-management-target="reservas"')
        self.assertNotContains(response, 'data-management-view="reservas"')
        self.assertNotContains(response, 'id="reservationManagementDrawer"')
        self.assertNotContains(response, 'data-agenda-operation-form="finanzas"')
        self.assertNotContains(response, 'data-agenda-operation-form="conteo_inventario"')
        self.assertNotIn('reporte_gestion', response.context)
        self.assertNotIn('equipos', response.context)

    def test_get_de_unidad_sin_configuracion_no_escribe_defaults(self):
        ConfiguracionOperativaUnidad.objects.filter(unidad=self.unidad).delete()
        response = self.client.get(self.url, {'view': 'cursos', 'fragment': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['configuracion_operativa'].pk)
        self.assertFalse(ConfiguracionOperativaUnidad.objects.filter(unidad=self.unidad).exists())

    def test_cursos_tiene_costo_constante_al_crecer_reservas_ajenas_y_propias(self):
        self.client.get(self.url, {'view': 'cursos', 'fragment': '1'})
        with CaptureQueriesContext(connection) as antes:
            response = self.client.get(self.url, {'view': 'cursos', 'fragment': '1'})
        Reserva.objects.bulk_create([
            Reserva(laboratorio=self.unidad if indice % 2 else self.otra_unidad,
                usuario=self.usuario_ajeno, fecha=timezone.localdate(),
                hora_inicio=time(8), hora_fin=time(9), estado='pendiente',
                titulo_solicitud=f'Reserva de escala {indice}')
            for indice in range(300)
        ])
        with CaptureQueriesContext(connection) as despues:
            ampliada = self.client.get(self.url, {'view': 'cursos', 'fragment': '1'})
        self.assertEqual(len(antes), len(despues))
        self.assertEqual(len(response.content), len(ampliada.content))
        sql = ' '.join(item['sql'].lower() for item in despues)
        for tabla in ('webcitt_reserva', 'webcitt_entrada_inventario', 'webcitt_movimientofinancierounidad', 'webcitt_mantenimientoequipo'):
            self.assertNotIn('"' + tabla + '"', sql)
        self.assertNotContains(ampliada, 'Reserva de escala')

    def test_enlaces_anteriores_y_modulos_respetan_seleccion_aislada(self):
        for parametros, vista, modo in (
            ({'view': 'agenda'}, 'reservas', 'agenda'),
            ({'view': 'inventario'}, 'recursos', 'inventario'),
            ({'view': 'finanzas'}, 'recursos', 'finanzas'),
        ):
            with self.subTest(parametros=parametros):
                response = self.client.get(self.url, {**parametros, 'fragment': '1'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['vista_gestion'], vista)
                self.assertContains(response, f'data-management-view="{vista}"')
                self.assertNotContains(response, 'data-management-view="indicadores"')
                self.assertNotContains(response, 'Reserva que no debe aparecer')
                self.assertEqual(response.context['modo_reservas' if vista == 'reservas' else 'modo_recursos'], modo)

    def test_no_puede_forzar_pestana_ni_otra_unidad(self):
        self.client.force_login(self.usuario_ajeno)
        for vista in ('cursos', 'recursos', 'configuracion'):
            self.assertEqual(self.client.get(self.url, {'view': vista, 'fragment': '1'}).status_code, 403)
        self.client.force_login(self.coordinador)
        otra_url = reverse('gestion_unidad', args=[self.otra_unidad.slug])
        self.assertEqual(self.client.get(otra_url, {'view': 'cursos', 'fragment': '1'}).status_code, 403)

    def test_activos_no_carga_analisis_financiero_ni_movimientos_historicos(self):
        with patch('apps.gestion_unidades.presentation.gestion._datos_finanzas_panel', side_effect=AssertionError('finanzas cerradas')), \
             patch('apps.gestion_unidades.presentation.gestion._preparar_trazabilidad_lotes', side_effect=AssertionError('historial cerrado')):
            response = self.client.get(self.url, {'view': 'recursos', 'modo_recursos': 'activos', 'fragment': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-resources-pane="activos"')
        self.assertNotContains(response, 'data-resources-pane="finanzas"')
        self.assertNotContains(response, 'data-resources-pane="inventario"')
        self.assertNotIn('analitica_financiera', response.context)

    def test_indicadores_no_materializa_historial_ni_auditoria_de_reservas(self):
        parametros = {'view': 'indicadores', 'fragment': '1'}
        self.client.get(self.url, parametros)
        with CaptureQueriesContext(connection) as antes:
            response = self.client.get(self.url, parametros)
        Reserva.objects.bulk_create([
            Reserva(laboratorio=self.unidad, usuario=self.usuario_ajeno,
                fecha=timezone.localdate() - timedelta(days=365),
                hora_inicio=time(8), hora_fin=time(9), estado='completada',
                resultado_cierre='atendida', detalle_ejecucion={'registrada_en': '2025-10-10T09:00:00Z'},
                titulo_solicitud=f'Historia cerrada {indice}')
            for indice in range(300)
        ])
        with CaptureQueriesContext(connection) as despues:
            ampliada = self.client.get(self.url, parametros)
        self.assertEqual(response.context['resumen_reservas']['cierres_total'], ampliada.context['resumen_reservas']['cierres_total'])
        self.assertEqual(len(antes), len(despues))
        self.assertEqual(len(response.content), len(ampliada.content))
        self.assertNotIn('reservas_bandeja_pagina', ampliada.context)
        self.assertNotIn('trazabilidad_reservas', ampliada.context)
        self.assertNotContains(ampliada, 'Historia cerrada')
        self.assertNotIn('"django_admin_log"', ' '.join(item['sql'].lower() for item in despues))

    def test_conteo_sql_de_cierres_conserva_semantica_de_json_heredado(self):
        from apps.gestion_unidades.presentation.gestion import _reservas_por_cerrar
        ahora = timezone.now()
        pruebas = []
        for estado in ('completada', 'confirmada', 'en_proceso', 'cancelada'):
            for resultado in ('atendida', ''):
                for registro in (None, '', False, 0, [], {}, '2026-10-10T09:00:00Z', ['registro'], {'valor': 1}):
                    pruebas.append(Reserva(laboratorio=self.unidad, usuario=self.usuario_ajeno,
                        fecha=timezone.localdate() - timedelta(days=2), hora_inicio=time(8), hora_fin=time(9),
                        estado=estado, resultado_cierre=resultado,
                        detalle_ejecucion={'registrada_en': registro}))
        pruebas.append(Reserva(laboratorio=self.unidad, usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=2), hora_inicio=time(8), hora_fin=time(9),
            estado='completada', resultado_cierre='atendida', detalle_ejecucion={}))
        Reserva.objects.bulk_create(pruebas)
        consulta = Reserva.objects.filter(pk__in=[reserva.pk for reserva in pruebas])
        esperados = {reserva.pk for reserva in consulta if reserva.requiere_cierre_operativo or reserva.requiere_regularizacion_operativa}
        self.assertSetEqual(set(_reservas_por_cerrar(consulta, ahora).values_list('pk', flat=True)), esperados)

    def test_cada_operacion_visible_tiene_su_formulario_del_modulo(self):
        for vista, modo in (('reservas', ''), ('configuracion', ''), ('mantenimiento', ''),
                ('recursos', 'activos'), ('recursos', 'espacios'), ('recursos', 'software'),
                ('recursos', 'insumos'), ('recursos', 'inventario'), ('recursos', 'finanzas')):
            with self.subTest(vista=vista, modo=modo):
                response = self.client.get(self.url, {'view': vista, 'modo_recursos': modo, 'fragment': '1'})
                self.assertEqual(response.status_code, 200)
                import re
                html = response.content.decode()
                botones = set(re.findall(r'data-agenda-operation-open="([^"]+)"', html))
                formularios = set(re.findall(r'data-agenda-operation-form="([^"]+)"', html))
                self.assertFalse(botones - formularios, botones - formularios)

    def test_el_tablero_no_reconstruye_la_ficha_publica_al_abrir(self):
        from apps.gestion_unidades.admin.tablero_unidad import estado_de_la_ficha
        from apps.recursos.models.recursos import ModuloUnidad
        ModuloUnidad.objects.update_or_create(unidad=self.unidad, clave='informacion-general', defaults={'nombre': 'Información', 'activo': False})
        with patch('apps.formacion.presentation.aula.contexto_aula', side_effect=AssertionError('revisión no solicitada')):
            with CaptureQueriesContext(connection) as consultas:
                estado = estado_de_la_ficha(self.unidad, revisar_pendientes=False)
        self.assertEqual(len(consultas), 1)
        self.assertEqual(estado['desactivados'], ['Información'])
        self.assertFalse(estado['revisado'])
        with patch('apps.formacion.presentation.aula.contexto_aula', return_value={'aula': {'carpetas': [
                {'numero': '2.1', 'titulo': 'Procesos', 'pendiente': True},
                {'numero': '2.2', 'titulo': 'Publicado', 'pendiente': False}]}}) as revision:
            estado = estado_de_la_ficha(self.unidad, revisar_pendientes=True)
        revision.assert_called_once()
        self.assertEqual(estado['pendientes'], ['2.1 Procesos'])
        self.assertTrue(estado['revisado'])

    def test_configuracion_no_ofrece_usuarios_globales_sin_busqueda(self):
        response = self.client.get(self.url, {'view': 'configuracion', 'fragment': '1'})
        ids = {usuario.pk for usuario in response.context['usuarios_responsables_disponibles']}
        self.assertSetEqual(ids, {self.coordinador.pk, self.responsable.pk})
        self.assertNotIn(self.usuario_ajeno.pk, ids)
        self.assertNotContains(response, 'data-management-view="reservas"')

    def test_scan_y_formacion_de_planta_conservan_destino(self):
        scan = self.client.get(self.url, {'scan': 'LOTE-01', 'fragment': '1'})
        self.assertEqual(scan.context['vista_gestion'], 'recursos')
        self.assertEqual(scan.context['modo_recursos'], 'inventario')
        ConfiguracionOperativaUnidad.objects.update_or_create(unidad=self.unidad, defaults={'registra_produccion': True})
        cursos = self.client.get(self.url, {'view': 'cursos', 'fragment': '1'})
        self.assertEqual(cursos.context['vista_gestion'], 'cursos')
        self.assertContains(cursos, 'data-management-target="cursos"')
        self.assertContains(cursos, 'data-management-view="cursos"')
        claves = [seccion['clave'] for seccion in cursos.context['secciones_navegacion']]
        self.assertEqual(len(claves), len(set(claves)))
        self.assertEqual(claves.count('cursos'), 1)
        menu = re.search(r'<aside\b[^>]*>(.*?)</aside>', cursos.content.decode(), re.S)
        self.assertIsNotNone(menu)
        claves_html = re.findall(r'data-management-target="([^"]+)"', menu.group(1))
        self.assertEqual(len(claves_html), len(set(claves_html)))
        self.assertEqual(claves_html.count('cursos'), 1)

    def test_catalogos_y_reservas_no_armar_historial_de_inventario(self):
        for parametros in ({'view': 'recursos', 'modo_recursos': 'insumos'},
                {'view': 'recursos', 'modo_recursos': 'espacios'},
                {'view': 'recursos', 'modo_recursos': 'software'}, {'view': 'reservas'}):
            with self.subTest(parametros=parametros), \
                 patch('apps.gestion_unidades.presentation.gestion._preparar_trazabilidad_lotes', side_effect=AssertionError('historial cerrado')), \
                 patch('apps.gestion_unidades.presentation.gestion.inventario_por_area', side_effect=AssertionError('inventario de activos cerrado')):
                response = self.client.get(self.url, {**parametros, 'fragment': '1'})
            self.assertEqual(response.status_code, 200)

    def test_semana_invalida_recupera_fecha_actual_sin_abrir_otro_modulo(self):
        hoy = timezone.localdate()
        for semana in ('2026-99-99', '2026-02-30', '0001-01-01', '9999-12-31'):
            with self.subTest(semana=semana):
                response = self.client.get(self.url, {'view': 'cursos', 'semana': semana, 'fragment': '1'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['fecha_seleccionada'], hoy)
                self.assertEqual(response.context['vista_gestion'], 'cursos')
                self.assertNotContains(response, 'data-management-view="reservas"')
                self.assertNotContains(response, 'data-agenda-operation-form="conteo_inventario"')

    def test_semana_valida_conserva_fecha_y_enlaces_del_calendario(self):
        response = self.client.get(self.url, {'view': 'cursos', 'semana': '2026-10-21', 'fragment': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['fecha_seleccionada'], date(2026, 10, 21))
        self.assertEqual(response.context['inicio_semana'], date(2026, 10, 19))
        self.assertEqual(response.context['fin_semana'], date(2026, 10, 25))
        self.assertEqual(response.context['semana_anterior'], '2026-10-12')
        self.assertEqual(response.context['semana_siguiente'], '2026-10-26')
