"""El estándar de códigos UNIDAD-ÁREA-MODELO-N.º: se asigna solo, se aplica a lo existente sin romper nada.

Los códigos anteriores quedan como alias (las etiquetas impresas siguen abriendo el equipo), las reservas pasan al
código nuevo y el uso del equipo las sigue contando; los cargadores no duplican lo que se estandarizó.
"""
import json
from datetime import date, time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation.codigos_equipo import buscar_equipo
from apps.core.presentation.codigos_sistema import actualizar_o_crear, modelo_vigente, sigla_de_area, siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.recursos.presentation.ficha_equipo import reservas_del_equipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class CodigosEstandarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-estandar', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio estándar', slug='laboratorio-estandar', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.impresion = EspacioReservable.objects.create(unidad=cls.unidad, codigo='EST-AREA-IMP3D', nombre='Impresión 3D',
                                                         capacidad=4, orden=1)
        cls.sala = EspacioReservable.objects.create(unidad=cls.unidad, codigo='EST-SALA-CAP', nombre='Sala de capacitación',
                                                    capacidad=20, orden=2)
        cls.fdm = EquiposServicios.objects.create(codigo='EST-A1-05', nombre='Impresora 3D FDM')
        cls.visor = EquiposServicios.objects.create(codigo='EST-EQ-VISOR', nombre='Visor de realidad virtual')
        cls.fdm_1 = UnidadEquipo.objects.create(codigo_unidad='EST-A1-05-01', equipo=cls.fdm, laboratorio=cls.unidad)
        cls.fdm_2 = UnidadEquipo.objects.create(codigo_unidad='EST-A1-05-02', equipo=cls.fdm, laboratorio=cls.unidad)
        cls.visor_1 = UnidadEquipo.objects.create(codigo_unidad='BIEN-777', codigo_bien='777', equipo=cls.visor,
                                                  laboratorio=cls.unidad)
        cls.impresion.equipos_asociados.add(cls.fdm_1, cls.fdm_2)
        cls.sala.equipos_asociados.add(cls.visor_1)

    def test_siglas_y_siguientes_codigos(self):
        self.assertEqual(sigla_de_area(self.impresion), 'IMP3D')
        self.assertEqual(sigla_de_area(self.sala), 'CAP')
        self.assertEqual(sigla_de_area(None), 'GEN')
        self.assertEqual(siguiente_codigo_modelo(self.unidad, self.impresion), 'EST-IMP3D-01')
        self.assertEqual(siguiente_codigo_unidad(self.unidad, None, self.visor), 'EST-GEN-01-01')

    def test_la_orden_estandariza_deja_alias_actualiza_reservas_y_no_cambia_al_repetirse(self):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.gestor, equipo_nombre='Impresora', equipo_codigo='EST-A1-05-02',
            unidades_seleccionadas=json.dumps([{'id': self.fdm_2.pk, 'codigo': 'EST-A1-05-02'}]),
            fecha=timezone.localdate() - timedelta(days=3), hora_inicio=time(8), hora_fin=time(10), estado='completada',
            proposito_codigo='docencia_practica', titulo_solicitud='Práctica', numero_participantes=4)
        call_command('estandarizar_codigos_equipo', stdout=StringIO())
        for equipo in (self.fdm_1, self.fdm_2, self.visor_1):
            equipo.refresh_from_db()
        self.assertEqual([self.fdm_1.codigo_unidad, self.fdm_2.codigo_unidad], ['EST-IMP3D-01-01', 'EST-IMP3D-01-02'])
        self.assertEqual(self.visor_1.codigo_unidad, 'EST-CAP-01-01')
        self.fdm.refresh_from_db()
        self.assertEqual(self.fdm.codigo, 'EST-IMP3D-01')
        # Las etiquetas y documentos con el código anterior siguen llevando al mismo equipo y modelo.
        self.assertEqual(buscar_equipo('EST-A1-05-02'), self.fdm_2)
        self.assertEqual(buscar_equipo('BIEN-777'), self.visor_1)
        self.assertEqual(modelo_vigente('EST-A1-05'), self.fdm)
        self.assertTrue(EventoCicloVidaEquipo.objects.filter(equipo=self.fdm_2, tipo='cambio_codigo',
                                                             descripcion__contains='EST-IMP3D-01-02').exists())
        reserva.refresh_from_db()
        self.assertEqual(reserva.equipo_codigo, 'EST-IMP3D-01-02')
        self.assertIn('EST-IMP3D-01-02', reserva.unidades_seleccionadas)
        self.assertEqual(list(reservas_del_equipo(self.fdm_2)), [reserva])
        salida = StringIO()
        call_command('estandarizar_codigos_equipo', stdout=salida)
        self.assertIn('todo ya estaba en el estándar', salida.getvalue())

    def test_el_uso_cuenta_las_reservas_con_un_codigo_anterior(self):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.gestor, equipo_nombre='Impresora', equipo_codigo='VIEJO-01',
            unidades_seleccionadas=json.dumps([{'codigo': 'VIEJO-01'}]), fecha=timezone.localdate(),
            hora_inicio=time(8), hora_fin=time(9), estado='completada', proposito_codigo='docencia_practica',
            titulo_solicitud='Práctica', numero_participantes=2)
        self.fdm_1.codigo_unidad = 'EST-IMP3D-09-01'
        self.fdm_1.save()
        self.assertEqual(list(reservas_del_equipo(self.fdm_1)), [])
        self.fdm_1.codigos_anteriores.create(codigo='VIEJO-01')
        self.assertEqual(list(reservas_del_equipo(self.fdm_1)), [reserva])

    def test_la_consola_asigna_el_codigo_estandar_si_se_deja_vacio(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {
            'modulo': 'recursos', 'entidad': 'equipo', 'nombre_catalogo': 'Escáner 3D de mano', 'codigo_catalogo': '',
            'codigo_unidad': '', 'estado_unidad': 'disponible', 'espacios_asociados': [self.impresion.pk], 'activa': 'on'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        nuevo = UnidadEquipo.objects.get(equipo__nombre='Escáner 3D de mano')
        self.assertEqual((nuevo.equipo.codigo, nuevo.codigo_unidad), ('EST-IMP3D-01', 'EST-IMP3D-01-01'))
        otra = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {
            'modulo': 'recursos', 'entidad': 'equipo', 'equipo_catalogo_id': nuevo.equipo.pk, 'codigo_unidad': '',
            'estado_unidad': 'disponible', 'espacios_asociados': [self.impresion.pk], 'activa': 'on'})
        self.assertEqual(otra.status_code, 200, otra.content)
        self.assertTrue(UnidadEquipo.objects.filter(codigo_unidad='EST-IMP3D-01-02').exists())

    def test_un_cargador_no_duplica_lo_que_se_estandarizo(self):
        call_command('estandarizar_codigos_equipo', stdout=StringIO())
        modelo, creado = actualizar_o_crear(modelo_vigente, EquiposServicios, 'codigo', 'EST-A1-05',
                                            {'nombre': 'Impresora 3D FDM (cargador)'})
        self.assertFalse(creado)
        self.assertEqual((modelo.pk, modelo.codigo, modelo.nombre), (self.fdm.pk, 'EST-IMP3D-01', 'Impresora 3D FDM (cargador)'))
        self.assertEqual(EquiposServicios.objects.filter(nombre__startswith='Impresora 3D FDM').count(), 1)
