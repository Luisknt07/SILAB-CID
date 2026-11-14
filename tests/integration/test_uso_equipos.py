"""El uso de cada equipo y su situación, y lo que la ficha muestra de él y de las otras unidades.

Seis meses sin reservas atendidas, o menos de doce horas al año, es un equipo ocioso; lo recién llegado no se
juzga. El público ve en qué otras unidades está el mismo modelo y cuántos hay disponibles; las horas, la
situación y el patrimonio solo los ve quien gestiona.
"""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation.uso_equipos import situacion, situaciones, uso_de_equipos
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.models.redistribucion import PoliticaUsoEquipo
from tests.integration.utiles import identificar


class UsoDeEquiposTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        PoliticaUsoEquipo.objects.create(dias_sin_uso=180, horas_minimas_anuales=12, dias_atencion=30)
        cls.gestor = get_user_model().objects.create_user('gestor-uso', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.aqui = Unidad.objects.create(nombre='Laboratorio con visores', slug='lab-visores', dependencia='laboratorios',
                                         descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.otra = Unidad.objects.create(nombre='Laboratorio vecino', slug='lab-vecino', dependencia='laboratorios',
                                         descripcion='.', fecha_inicio=date(2020, 1, 1))
        familia = FamiliaEquipo.objects.create(nombre='Visores de prueba', slug='visores-de-prueba', grupo='Realidad extendida')
        cls.tipo = EquiposServicios.objects.create(codigo='USO-VR-01', nombre='Visor de prueba', familia=familia,
                                                   marca='Meta', modelo='Quest 3')
        equivalente = EquiposServicios.objects.create(codigo='USO-VR-02', nombre='Visor profesional', familia=familia)
        hace_un_anio = timezone.localdate() - timedelta(days=400)
        cls.usado = UnidadEquipo.objects.create(codigo_unidad='USO-VR-01-01', equipo=cls.tipo, laboratorio=cls.aqui,
                                                fecha_ingreso_bodega=hace_un_anio, custodio='Custodio de prueba')
        cls.ocioso = UnidadEquipo.objects.create(codigo_unidad='USO-VR-01-02', equipo=cls.tipo, laboratorio=cls.aqui,
                                                 fecha_ingreso_bodega=hace_un_anio)
        cls.ajeno = UnidadEquipo.objects.create(codigo_unidad='VEC-VR-01-01', equipo=cls.tipo, laboratorio=cls.otra,
                                                fecha_ingreso_bodega=hace_un_anio)
        UnidadEquipo.objects.create(codigo_unidad='VEC-VR-02-01', equipo=equivalente, laboratorio=cls.otra)
        for dia in (5, 12, 30):
            Reserva.objects.create(
                laboratorio=cls.aqui, usuario=cls.gestor, equipo_nombre='Visor',
                unidades_seleccionadas='[{"codigo": "USO-VR-01-01"}]', fecha=timezone.localdate() - timedelta(days=dia),
                hora_inicio=time(8, 0), hora_fin=time(12, 0), estado='completada',
                resultado_cierre='atendida', detalle_ejecucion={
                    'registrada_en': timezone.now().isoformat(), 'horario_real': {'inicio': '08:00', 'fin': '12:00'},
                    'asistentes_total': 10, 'equipos': [{'id': str(cls.usado.pk), 'codigo': cls.usado.codigo_unidad}]},
                proposito_codigo='docencia_practica', titulo_solicitud='Práctica', numero_participantes=10)

    def test_el_uso_y_la_situacion_de_cada_equipo(self):
        hoy = timezone.localdate()
        uso = uso_de_equipos(hoy - timedelta(days=365), {'USO-VR-01-01', 'USO-VR-01-02'})
        self.assertEqual(uso['USO-VR-01-01']['horas'], 12.0)
        self.assertEqual(uso['USO-VR-01-01']['sesiones'], 3)
        self.assertEqual(uso['USO-VR-01-01']['ultimo'], hoy - timedelta(days=5))
        self.assertNotIn('USO-VR-01-02', uso)
        por_equipo = situaciones([self.usado, self.ocioso])
        self.assertEqual(por_equipo[self.usado.pk]['clave'], 'en_uso')
        self.assertEqual(por_equipo[self.ocioso.pk]['clave'], 'sin_registros')
        self.assertTrue(por_equipo[self.ocioso.pk]['alerta'])
        # Lo que llegó hace poco no se juzga; lo que está fuera de servicio tampoco.
        self.assertEqual(situacion(self.ocioso, None, hoy - timedelta(days=30), hoy)['clave'], 'nuevo')
        self.ocioso.estado_unidad = 'mantenimiento'
        self.assertEqual(situacion(self.ocioso, None, hoy - timedelta(days=400), hoy)['clave'], 'fuera')
        # Usado hace poco pero menos de doce horas en el año: poco uso.
        poco = {'horas': 3.0, 'sesiones': 1, 'ultimo': hoy - timedelta(days=20)}
        self.assertEqual(situacion(self.usado, poco, hoy - timedelta(days=400), hoy)['clave'], 'poco_uso')

    def test_la_ficha_muestra_otras_unidades_al_publico_y_el_uso_solo_a_gestion(self):
        url = reverse('ficha_equipo_publica', args=[self.aqui.slug, self.usado.codigo_unidad])
        publica = self.client.get(url).content.decode('utf-8')
        self.assertIn('Este modelo en otras unidades', publica)
        self.assertIn('Laboratorio vecino', publica)
        self.assertIn('Equipos equivalentes', publica)
        self.assertIn('Visor profesional', publica)
        self.assertNotIn('Uso en 12 meses', publica)
        self.assertNotIn('Sin uso acreditado', publica)
        self.assertNotIn('Custodio de prueba', publica)
        self.client.force_login(self.gestor)
        gestion = self.client.get(url).content.decode('utf-8')
        self.assertIn('Uso en 12 meses', gestion)
        self.assertRegex(gestion, r'12[,.]0 h · 3 sesiones')
        self.assertIn('Sin uso acreditado', gestion)
        self.assertIn('Patrimonio · solo gestión', gestion)
        self.assertIn('Custodio de prueba', gestion)
