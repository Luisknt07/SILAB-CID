"""Sólo recursos reales acreditan uso; las alertas dan oportunidad de revisión."""
import json
from unittest.mock import patch
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from io import StringIO
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.redistribucion import AlertaUsoEquipo, PoliticaUsoEquipo
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.presentation.traspasos import candidatura_reasignacion, detectar_equipos_sin_uso, transparencia_equipos
from apps.recursos.presentation.uso_equipos import equipos_reales_reserva, leer_uso_equipos, situaciones
from apps.reservas.models.reservas import Reserva
from tests.integration.utiles import identificar


class TransparenciaEquiposTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        PoliticaUsoEquipo.objects.create(dias_sin_uso=180, horas_minimas_anuales=12, dias_atencion=30)
        cls.hoy = timezone.localdate()
        cls.gestor = get_user_model().objects.create_user('gestor-transparencia', password='clave', is_staff=True)
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.director = get_user_model().objects.create_user('direccion-transparencia', password='clave', is_staff=True, is_superuser=True)
        cls.unidad = Unidad.objects.create(nombre='Unidad visible', slug='transparencia-visible', dependencia='laboratorios',
            descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.ajena = Unidad.objects.create(nombre='Unidad ajena', slug='transparencia-ajena', dependencia='laboratorios',
            descripcion='.', fecha_inicio=date(2020, 1, 1))
        tipo = EquiposServicios.objects.create(codigo='TRA-CPU', nombre='Computador trazable')
        cls.a, cls.b, cls.c = [UnidadEquipo.objects.create(codigo_unidad=f'TRA-{n}', equipo=tipo,
            laboratorio=cls.unidad if n != 3 else cls.ajena, fecha_ingreso_bodega=cls.hoy - timedelta(days=400))
            for n in (1, 2, 3)]

    def reserva(self, *, reales=None, fecha=None, inicio='08:00', fin='10:00', completa=True, **kwargs):
        detalle = dict(registrada_en=timezone.now().isoformat(), horario_real=dict(inicio=inicio, fin=fin),
                       asistentes_total=2, equipos=reales if reales is not None else [{'id': str(self.a.pk)}])
        if not completa:
            detalle = {}
        valores = dict(laboratorio=self.unidad, usuario=self.gestor, equipo_nombre='Equipo trazable',
            unidades_seleccionadas=json.dumps([{'id': str(self.b.pk), 'codigo': self.b.codigo_unidad}]),
            fecha=fecha or self.hoy - timedelta(days=1), hora_inicio=time(7), hora_fin=time(19),
            estado='completada', resultado_cierre='atendida', detalle_ejecucion=detalle,
            proposito_codigo='docencia_practica', titulo_solicitud='Actividad', numero_participantes=2)
        valores.update(kwargs)
        return Reserva.objects.create(**valores)

    def test_el_cierre_real_y_no_la_seleccion_solicitada_acredita_el_activo(self):
        reserva = self.reserva()
        lectura = leer_uso_equipos(self.hoy - timedelta(days=365))['equipos']
        self.assertEqual(lectura[self.a.codigo_unidad]['horas'], 2)
        self.assertNotIn(self.b.codigo_unidad, lectura)
        self.assertEqual(equipos_reales_reserva(reserva)['ids'], [self.a.pk])
        self.assertEqual(lectura[self.a.codigo_unidad]['fuentes'][0]['reserva_id'], reserva.pk)

    def test_ids_alias_y_franjas_simultaneas_no_duplican_horas(self):
        AliasCodigoUnidadEquipo.objects.create(codigo='TRA-ANTERIOR', unidad_equipo=self.a)
        self.reserva(reales=[{'codigo': 'TRA-ANTERIOR'}, {'id': str(self.a.pk)}], inicio='08:00', fin='10:00')
        self.reserva(inicio='09:00', fin='11:00')
        lectura = leer_uso_equipos(self.hoy - timedelta(days=365), [self.a.codigo_unidad])['equipos'][self.a.codigo_unidad]
        self.assertEqual((lectura['horas'], lectura['sesiones']), (3, 2))
        self.assertTrue(lectura['solapamientos'])
        self.assertEqual(lectura['por_mes'][0]['horas'], 3)
        self.assertEqual(lectura['por_finalidad'][0]['horas'], 3)

    def test_cierre_incompleto_y_fecha_futura_no_acreditan_uso(self):
        incompleta = self.reserva(completa=False)
        self.reserva(fecha=self.hoy + timedelta(days=1))
        estados = situaciones([self.a, self.b], self.hoy)
        self.assertEqual(estados[self.a.pk]['horas'], 0)
        self.assertEqual(estados[self.b.pk]['clave'], 'pendiente')
        self.assertIn(incompleta.pk, estados[self.b.pk]['pendientes'])

    def test_cierre_sin_asistencia_o_registrado_despues_del_corte_no_acredita(self):
        reserva = self.reserva()
        reserva.detalle_ejecucion['asistentes_total'] = 0
        reserva.save()
        self.assertEqual(situaciones([self.a], self.hoy)[self.a.pk]['horas'], 0)
        reserva.detalle_ejecucion['asistentes_total'] = 2
        reserva.detalle_ejecucion['registrada_en'] = (timezone.now() + timedelta(days=1)).isoformat()
        reserva.save()
        self.assertEqual(situaciones([self.a], self.hoy)[self.a.pk]['horas'], 0)

    def test_captura_vacia_no_imputa_los_equipos_solicitados(self):
        self.reserva(reales=[])
        lectura = situaciones([self.a, self.b], self.hoy)
        self.assertEqual(lectura[self.b.pk]['clave'], 'sin_registros')
        self.assertFalse(lectura[self.b.pk]['pendientes'])

    def test_id_invalido_no_se_rescata_con_otro_codigo(self):
        reserva = self.reserva(reales=[{'id': 'invalido', 'codigo': self.a.codigo_unidad}])
        self.assertEqual(equipos_reales_reserva(reserva)['ids'], [])
        self.assertTrue(equipos_reales_reserva(reserva)['pendientes'])
        self.assertEqual(situaciones([self.a], self.hoy)[self.a.pk]['horas'], 0)

    def test_filtro_de_un_activo_no_invalida_capturas_de_otro(self):
        self.reserva(reales=[{'id': str(self.b.pk)}])
        lectura = situaciones([self.a], self.hoy)[self.a.pk]
        self.assertEqual(lectura['clave'], 'sin_registros')
        self.assertFalse(lectura['pendientes'])

    def test_transparencia_cuenta_m2m_una_vez_y_no_escribe(self):
        self.a.laboratorios.add(self.unidad)
        self.b.laboratorio = None
        self.b.save()
        self.b.laboratorios.add(self.unidad)
        with CaptureQueriesContext(connection) as consultas:
            lectura = transparencia_equipos(self.unidad, self.hoy)
        self.assertEqual(lectura['resumen']['total'], 2)
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))

    def test_oportunidad_de_correccion_no_traspasa_ni_habilita_sin_plazo(self):
        detectar_equipos_sin_uso(self.hoy, unidad=self.unidad)
        alerta = AlertaUsoEquipo.objects.get(equipo=self.a)
        lectura = situaciones([self.a], self.hoy)[self.a.pk]
        self.assertFalse(candidatura_reasignacion(alerta, lectura, self.hoy)['candidata'])
        alerta.plan_uso = 'Responsable: coordinación. Ejecutar prácticas y cerrar sus evidencias.'
        alerta.notificada_en = self.hoy - timedelta(days=20)
        alerta.revisar_desde = self.hoy + timedelta(days=1)
        alerta.full_clean()
        alerta.save()
        self.assertEqual(candidatura_reasignacion(alerta, lectura, self.hoy)['estado'], 'en_correccion')
        alerta.revisar_desde = self.hoy
        alerta.save()
        self.assertTrue(candidatura_reasignacion(alerta, lectura, self.hoy)['candidata'])
        self.reserva()
        lectura = situaciones([self.a], self.hoy)[self.a.pk]
        self.assertFalse(candidatura_reasignacion(alerta, lectura, self.hoy)['candidata'])
        self.a.refresh_from_db()
        self.assertEqual(self.a.laboratorio_id, self.unidad.pk)

    def test_no_habilita_redistribucion_con_cierres_pendientes_o_fuera_de_servicio(self):
        alerta = AlertaUsoEquipo.objects.create(equipo=self.b, unidad=self.unidad, motivo='sin_registros',
            plan_uso='Ejecutar las actividades acordadas.', notificada_en=self.hoy - timedelta(days=30), revisar_desde=self.hoy)
        self.reserva(completa=False)
        lectura = situaciones([self.b], self.hoy)[self.b.pk]
        self.assertFalse(candidatura_reasignacion(alerta, lectura, self.hoy)['candidata'])
        self.b.estado_unidad = 'mantenimiento'
        self.b.save()
        lectura = situaciones([self.b], self.hoy)[self.b.pk]
        self.assertFalse(candidatura_reasignacion(alerta, lectura, self.hoy)['candidata'])

    def test_el_plazo_requiere_comunicacion_y_plan(self):
        alerta = AlertaUsoEquipo(equipo=self.a, unidad=self.unidad, motivo='sin_registros', revisar_desde=self.hoy)
        with self.assertRaises(ValidationError):
            alerta.full_clean()

    def test_sin_politica_no_inventa_umbrales_ni_crea_alertas_institucionales(self):
        PoliticaUsoEquipo.objects.all().delete()
        lectura = transparencia_equipos(self.unidad, self.hoy)
        self.assertFalse(lectura['politica']['configurada'])
        self.assertTrue(detectar_equipos_sin_uso(self.hoy)['politica_pendiente'])
        self.assertFalse(AlertaUsoEquipo.objects.exists())
        self.assertFalse(any(f['redistribucion']['candidata'] for f in lectura['filas']))

    def test_cambiar_la_politica_cambia_la_lectura_sin_regenerar_fuentes(self):
        self.reserva(fecha=self.hoy - timedelta(days=40))
        politica = PoliticaUsoEquipo.objects.get()
        politica.dias_sin_uso, politica.horas_minimas_anuales = 30, None
        politica.save()
        self.assertEqual(situaciones([self.a], self.hoy)[self.a.pk]['clave'], 'sin_uso')
        politica.dias_sin_uso = 90
        politica.save()
        self.assertEqual(situaciones([self.a], self.hoy)[self.a.pk]['clave'], 'en_uso')

    @patch('apps.recursos.management.commands.vigilar_uso_equipos.close_old_connections')
    def test_monitor_una_vez_usa_la_misma_politica_y_no_traspasa(self, _cerrar):
        salida = StringIO()
        call_command('vigilar_uso_equipos', '--una-vez', stdout=salida)
        self.assertIn('equipos revisados', salida.getvalue())
        self.a.refresh_from_db()
        self.assertEqual(self.a.laboratorio_id, self.unidad.pk)

    def test_cambios_de_actividad_programan_revision_solo_tras_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.reserva()
        self.assertTrue(callbacks)
        self.assertTrue(AlertaUsoEquipo.objects.filter(equipo=self.b).exists())
        self.assertFalse(AlertaUsoEquipo.objects.filter(equipo=self.a, motivo='sin_registros').exists())

    @patch('apps.recursos.presentation.transparencia.admin.site.each_context', return_value={})
    def test_vista_global_csv_y_alcance_de_la_unidad_sin_writes_get(self, _contexto):
        url = reverse('admin:recursos_unidadequipo_transparencia')
        self.client.force_login(self.director)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(url)
        self.assertContains(respuesta, self.c.codigo_unidad)
        self.assertContains(respuesta, 'El uso se comprueba')
        self.assertFalse(any('webcitt_alertausoequipo' in q['sql'] and q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))
        self.client.force_login(self.gestor)
        self.assertNotContains(self.client.get(url), self.c.codigo_unidad)
        self.assertEqual(self.client.get(url, {'unidad': self.ajena.pk}).status_code, 403)
        csv = self.client.get(url, {'formato': 'csv'})
        self.assertEqual(csv['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Horas acreditadas', csv.content.decode('utf-8'))
        self.assertNotIn(self.c.codigo_unidad, csv.content.decode('utf-8'))

    @patch('apps.recursos.presentation.transparencia.admin.site.each_context', return_value={})
    def test_html_pagina_activos_y_actividades_sin_recortar_la_descarga(self, _contexto):
        UnidadEquipo.objects.bulk_create([UnidadEquipo(codigo_unidad=f'PAG-{n:03d}', equipo=self.a.equipo,
            laboratorio=self.unidad) for n in range(51)])
        for n in range(26):
            self.reserva(fecha=self.hoy - timedelta(days=n + 1))
        url = reverse('admin:recursos_unidadequipo_transparencia')
        self.client.force_login(self.director)
        respuesta = self.client.get(url)
        self.assertEqual(len(respuesta.context['filas']), 50)
        self.assertEqual(respuesta.context['pagina'].paginator.count, 54)
        pagina2 = self.client.get(url, {'pagina': 2})
        self.assertEqual(len(pagina2.context['filas']), 4)
        self.assertIn('PAG-050', self.client.get(url, {'formato': 'csv'}).content.decode('utf-8'))
        detalle = self.client.get(url, {'equipo_id': self.a.pk})
        self.assertEqual(len(detalle.context['filas'][0]['fuentes_vista']), 25)
        self.assertEqual(detalle.context['filas'][0]['total_fuentes'], 26)
        mas = self.client.get(url, {'equipo_id': self.a.pk, 'actividad_pagina': 2})
        self.assertEqual(len(mas.context['filas'][0]['fuentes_vista']), 1)
