"""Alertas de equipos sin uso y traspasos entre unidades.

Un equipo ocioso abre una alerta (una sola, aunque se revise otra vez); si la unidad lo justifica no se vuelve a
alertar. El traspaso lo aprueba la Dirección y, al ejecutarlo, el equipo pasa a la otra unidad con el código de
laboratorio de su área nueva, conserva el de bodega, deja el anterior como alias y el acta lo documenta.
"""
from datetime import date, time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation.traspasos import (detectar_equipos_sin_uso, ejecutar_traspaso, resolver_traspaso,
                                                 responder_traspaso, solicitar_traspaso)
from apps.recursos.models.redistribucion import AlertaUsoEquipo, PoliticaUsoEquipo, TraspasoEquipo
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class TraspasosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        PoliticaUsoEquipo.objects.create(dias_sin_uso=180, horas_minimas_anuales=12, dias_atencion=30)
        usuarios = get_user_model().objects
        cls.direccion = usuarios.create_user('direccion-traspasos', password='clave')
        cls.direccion.user_permissions.add(Permission.objects.get(codename='aprobar_traspasoequipo'))
        cls.gestor = usuarios.create_user('gestor-traspasos', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.gestor.user_permissions.add(Permission.objects.get(codename='add_traspasoequipo'))
        cls.receptor = usuarios.create_user('receptor-traspasos', password='clave')
        identificar(cls.receptor, tipo_usuario='administrativo', carrera='')
        cls.origen = Unidad.objects.create(nombre='Laboratorio que presta', slug='lab-presta', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.destino = Unidad.objects.create(nombre='Laboratorio que necesita', slug='lab-necesita', dependencia='laboratorios',
                                            descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.receptor)
        EspacioReservable.objects.create(unidad=cls.origen, codigo='PRE-AREA-VR', nombre='Realidad virtual', capacidad=4)
        cls.area_destino = EspacioReservable.objects.create(unidad=cls.destino, codigo='NEC-AREA-SIM', nombre='Simulación', capacidad=4)
        cls.tipo = EquiposServicios.objects.create(codigo='PRE-VR-01', nombre='Visor de realidad virtual')
        hace_un_anio = timezone.localdate() - timedelta(days=400)
        cls.ocioso = UnidadEquipo.objects.create(codigo_unidad='PRE-VR-01-01', equipo=cls.tipo, laboratorio=cls.origen,
                                                 codigo_bien='40530999', custodio='Custodio que entrega',
                                                 fecha_ingreso_bodega=hace_un_anio)
        cls.usado = UnidadEquipo.objects.create(codigo_unidad='PRE-VR-01-02', equipo=cls.tipo, laboratorio=cls.origen,
                                                fecha_ingreso_bodega=hace_un_anio)
        Reserva.objects.create(
            laboratorio=cls.origen, usuario=cls.gestor, equipo_nombre='Visor', unidades_seleccionadas='[{"codigo": "PRE-VR-01-02"}]',
            fecha=timezone.localdate() - timedelta(days=10), hora_inicio=time(8, 0), hora_fin=time(20, 0), estado='completada',
            resultado_cierre='atendida', detalle_ejecucion={
                'registrada_en': timezone.now().isoformat(), 'horario_real': {'inicio': '08:00', 'fin': '20:00'},
                'asistentes_total': 10, 'equipos': [{'id': str(cls.usado.pk), 'codigo': cls.usado.codigo_unidad}]},
            proposito_codigo='docencia_practica', titulo_solicitud='Práctica', numero_participantes=10)

    def test_la_deteccion_abre_una_alerta_por_equipo_ocioso_y_respeta_la_justificacion(self):
        salida = StringIO()
        call_command('detectar_equipos_sin_uso', '--simular', stdout=salida)
        self.assertIn('Simulación', salida.getvalue())
        self.assertFalse(AlertaUsoEquipo.objects.exists())
        detectar_equipos_sin_uso()
        detectar_equipos_sin_uso()
        alerta = AlertaUsoEquipo.objects.get()
        self.assertEqual((alerta.equipo, alerta.motivo, alerta.unidad), (self.ocioso, 'sin_registros', self.origen))
        alerta.estado, alerta.justificacion = 'justificada', 'Se usa en el semestre de simulación clínica.'
        alerta.save()
        detectar_equipos_sin_uso()
        self.assertEqual(AlertaUsoEquipo.objects.count(), 1, 'Lo justificado no se vuelve a alertar.')

    def test_el_traspaso_aprobado_recodifica_conserva_bodega_y_cierra_la_alerta(self):
        detectar_equipos_sin_uso()
        alerta = AlertaUsoEquipo.objects.get()
        traspaso = solicitar_traspaso(self.gestor, [self.ocioso], self.destino, 'Lo necesitan para simulación.',
                                      motivo='subutilizado', area=self.area_destino, alerta=alerta)
        self.assertRegex(traspaso.codigo, r'^TRP-\d{4}-0001$')
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, 'reasignacion')
        # Solo la Dirección aprueba y ejecuta; sin aprobar no se ejecuta.
        with self.assertRaises(PermissionDenied):
            resolver_traspaso(traspaso, self.gestor, True)
        with self.assertRaises(ValidationError):
            ejecutar_traspaso(traspaso, self.direccion, entrega='Quien entrega', recibe='Quien recibe')
        # Sin la aceptación de la unidad que recibe, la Dirección todavía no aprueba.
        with self.assertRaises(ValidationError):
            resolver_traspaso(traspaso, self.direccion, True)
        responder_traspaso(traspaso, self.receptor, True)
        resolver_traspaso(traspaso, self.direccion, True, 'Aprobado: evita una compra.')
        with self.assertRaises(ValidationError):
            ejecutar_traspaso(traspaso, self.direccion)
        ejecutar_traspaso(traspaso, self.direccion, entrega='Quien entrega', recibe='Quien recibe',
                          bodega='Guardalmacén', custodio='Custodio que recibe')
        self.ocioso.refresh_from_db()
        self.assertEqual(self.ocioso.laboratorio, self.destino)
        self.assertEqual(self.ocioso.codigo_unidad, 'NEC-SIM-01-01')
        self.assertEqual(self.ocioso.codigo_bien, '40530999')
        self.assertEqual(self.ocioso.custodio, 'Custodio que recibe')
        self.assertEqual(list(self.ocioso.espacios_asociados.all()), [self.area_destino])
        self.assertTrue(AliasCodigoUnidadEquipo.objects.filter(codigo='PRE-VR-01-01', unidad_equipo=self.ocioso).exists())
        evento = EventoCicloVidaEquipo.objects.get(equipo=self.ocioso, tipo='transferencia')
        self.assertIn(traspaso.codigo, evento.descripcion)
        item = traspaso.equipos.get()
        self.assertEqual((item.codigo_anterior, item.codigo_nuevo, item.codigo_bien), ('PRE-VR-01-01', 'NEC-SIM-01-01', '40530999'))
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, 'cerrada')
        self.assertEqual(TraspasoEquipo.objects.get().estado, 'ejecutado')

    def test_el_acta_la_ven_la_direccion_y_las_unidades_y_la_ficha_avisa(self):
        detectar_equipos_sin_uso()
        ficha = reverse('ficha_equipo_publica', args=[self.origen.slug, self.ocioso.codigo_unidad])
        self.client.force_login(self.gestor)
        pagina = self.client.get(ficha).content.decode('utf-8')
        self.assertIn('Alerta de uso:', pagina)
        self.assertIn('Solicitar traslado', pagina)
        self.assertIn(f'equipo={self.ocioso.pk}', pagina)
        traspaso = solicitar_traspaso(self.gestor, [self.ocioso], self.destino, 'Para simulación.')
        pagina = self.client.get(ficha).content.decode('utf-8')
        self.assertIn(traspaso.codigo, pagina)
        self.assertNotIn('Solicitar traslado', pagina.split('data-registro="PRE-VR-01-02"')[0].split(f'data-registro="{self.ocioso.codigo_unidad}"')[1])
        acta = reverse('acta_traspaso_equipos', args=[traspaso.codigo])
        self.assertContains(self.client.get(acta), 'Acta de traspaso de equipos entre unidades')
        self.client.force_login(self.direccion)
        self.assertEqual(self.client.get(acta, {'formato': 'pdf'})['Content-Type'], 'application/pdf')
        extrano = get_user_model().objects.create_user('ajeno-traspasos', password='clave')
        identificar(extrano, tipo_usuario='estudiante')
        self.client.force_login(extrano)
        self.assertEqual(self.client.get(acta).status_code, 403)
        # El público no ve avisos ni el botón.
        self.client.logout()
        publica = self.client.get(ficha).content.decode('utf-8')
        self.assertNotIn('Alerta de uso:', publica)
        self.assertNotIn('Solicitar traslado', publica)
