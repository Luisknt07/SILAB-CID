"""Identidad conservada, fallos aislados, recuperacion acotada y carreras reales."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from io import StringIO
import json
from threading import Barrier
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.reservas.models.reservas import asignar_codigo_reserva
from apps.reservas.services.codigos_reserva import EVENTO_ASIGNACION_FALLIDA, EVENTO_RECUPERACION_FALLIDA, ReservaFueraDeAlcance, asegurar_codigo_reserva


def unidad(sufijo):
    return Unidad.objects.create(nombre='Unidad de codigos ' + sufijo, slug='codigos-' + sufijo,
                                 fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')


def reserva(unidad):
    return Reserva.objects.create(laboratorio=unidad, fecha=date(2026, 10, 5),
                                  hora_inicio=time(9), hora_fin=time(10), detalle_trabajo='Prueba de codigo')


class CodigosSinDatosTests(SimpleTestCase):
    def test_raw_no_ejecuta_asignacion(self):
        with patch('apps.reservas.services.codigos_reserva.asegurar_codigo_reserva') as asegurar:
            asignar_codigo_reserva(Reserva, Reserva(pk=1, laboratorio_id=1), True, raw=True)
        asegurar.assert_not_called()

    def test_asignacion_propaga_alias_recibido(self):
        instancia = Reserva(pk=1, laboratorio_id=1)
        with patch('apps.reservas.services.codigos_reserva.asegurar_codigo_reserva') as asegurar:
            asignar_codigo_reserva(Reserva, instancia, True, using='alias_confirmado')
        asegurar.assert_called_once_with(instancia, using='alias_confirmado')

    def test_servicio_rechaza_no_persistida(self):
        with self.assertRaisesMessage(ValueError, 'persistida'):
            asegurar_codigo_reserva(Reserva(laboratorio_id=1))

    def test_comando_rechaza_escritura_sin_unidad_o_unidad_invalida(self):
        for opciones in ({'aplicar': True}, {'unidad': 0}, {'unidad': -1, 'aplicar': True}):
            with self.subTest(opciones=opciones), self.assertRaises(CommandError):
                call_command('recuperar_codigos_reservas', stdout=StringIO(), **opciones)


class CodigosReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = unidad('a'), unidad('b')

    def faltante(self, unidad=None, valor=None):
        instancia = reserva(unidad or self.a)
        Reserva.objects.filter(pk=instancia.pk).update(codigo_reserva=valor)
        instancia.refresh_from_db()
        return instancia

    def comando(self, **opciones):
        salida = StringIO()
        call_command('recuperar_codigos_reservas', stdout=salida, **opciones)
        return json.loads(salida.getvalue())

    def test_creacion_sincroniza_codigo_canonico_en_memoria(self):
        instancia = reserva(self.a)
        esperado = f'RL{self.a.pk:03d}-{instancia.pk:06d}'
        self.assertEqual(instancia.codigo_reserva, esperado)
        self.assertEqual(Reserva.objects.get(pk=instancia.pk).codigo_reserva, esperado)

    def test_constructor_no_consulta_relacion(self):
        instancia = reserva(self.a)
        instancia = Reserva.objects.only('pk', 'laboratorio_id').get(pk=instancia.pk)
        with self.assertNumQueries(0):
            self.assertEqual(instancia.construir_codigo_reserva(), f'RL{self.a.pk:03d}-{instancia.pk:06d}')

    def test_servicio_preserva_existente_aunque_instancia_este_obsoleta(self):
        instancia = self.faltante()
        Reserva.objects.filter(pk=instancia.pk).update(codigo_reserva='HISTORICO-CONSERVADO')
        resultado = asegurar_codigo_reserva(instancia)
        self.assertFalse(resultado.asignado)
        self.assertEqual(instancia.codigo_reserva, 'HISTORICO-CONSERVADO')
        instancia.refresh_from_db()
        self.assertEqual(instancia.codigo_reserva, resultado.codigo)

    def test_asignacion_null_o_vacio_converge_sin_reemplazar(self):
        for valor in (None, ''):
            with self.subTest(valor=valor):
                instancia = self.faltante(valor=valor)
                primera = asegurar_codigo_reserva(instancia)
                segunda = asegurar_codigo_reserva(instancia)
                self.assertTrue(primera.asignado)
                self.assertFalse(segunda.asignado)
                self.assertEqual(primera.codigo, segunda.codigo)

    def test_unidad_fresca_distinta_no_se_repara_fuera_del_alcance(self):
        instancia = self.faltante()
        Reserva.objects.filter(pk=instancia.pk).update(laboratorio=self.b)
        with self.assertRaises(ReservaFueraDeAlcance):
            asegurar_codigo_reserva(instancia, unidad_esperada=self.a.pk)
        instancia.refresh_from_db()
        self.assertIsNone(instancia.codigo_reserva)

    def test_integrity_error_no_invalida_transaccion_llamadora_o_memoria(self):
        existente = reserva(self.a)
        instancia = self.faltante()
        with patch.object(Reserva, 'construir_codigo_reserva', return_value=existente.codigo_reserva):
            with self.assertRaises(IntegrityError):
                asegurar_codigo_reserva(instancia)
        self.assertIsNone(instancia.codigo_reserva)
        self.assertTrue(Reserva.objects.filter(pk=instancia.pk).exists())
        self.assertFalse(connection.needs_rollback)

    def test_signal_con_error_sql_real_registra_sin_datos_y_permite_continuar(self):
        existente = reserva(self.a)
        with patch.object(Reserva, 'construir_codigo_reserva', return_value=existente.codigo_reserva), self.assertLogs(
                'apps.reservas.services.codigos_reserva', level='WARNING') as registros, transaction.atomic():
            instancia = reserva(self.b)
            self.assertTrue(Reserva.objects.filter(pk=instancia.pk).exists())
        self.assertIsNone(instancia.codigo_reserva)
        self.assertEqual(len(registros.records), 1)
        registro = registros.records[0]
        self.assertEqual(registro.getMessage(), EVENTO_ASIGNACION_FALLIDA)
        self.assertFalse(registro.args)
        self.assertIsNone(registro.exc_info)
        self.assertIsNone(registro.stack_info)
        self.assertNotIn(existente.codigo_reserva, str(registros.output))

    def test_update_del_codigo_no_reentra_en_signal(self):
        llamadas = []

        def observar(sender, instance, **kwargs):
            llamadas.append(instance.pk)

        post_save.connect(observar, sender=Reserva, weak=False, dispatch_uid='prueba_codigo_sin_reentrada')
        try:
            instancia = reserva(self.a)
        finally:
            post_save.disconnect(sender=Reserva, dispatch_uid='prueba_codigo_sin_reentrada')
        self.assertEqual(llamadas, [instancia.pk])

    def test_auditoria_predeterminada_solo_select_y_no_muestra_codigos(self):
        instancia = self.faltante()
        with CaptureQueriesContext(connection) as consultas:
            resumen = self.comando()
        self.assertEqual(resumen['modo'], 'auditoria')
        self.assertEqual(resumen['pendientes_observados'], 1)
        self.assertTrue(all(c['sql'].lstrip().upper().startswith('SELECT') for c in consultas.captured_queries))
        instancia.refresh_from_db()
        self.assertIsNone(instancia.codigo_reserva)
        self.assertNotIn('codigo_reserva', resumen)

    def test_recuperacion_por_unidad_conserva_otra_y_repeticion_no_cambia(self):
        a, b = self.faltante(self.a), self.faltante(self.b)
        primera = self.comando(aplicar=True, unidad=self.a.pk)
        self.assertEqual(primera['asignados'], 1)
        a.refresh_from_db()
        codigo = a.codigo_reserva
        b.refresh_from_db()
        self.assertIsNone(b.codigo_reserva)
        self.assertEqual(self.comando(aplicar=True, unidad=self.a.pk)['asignados'], 0)
        a.refresh_from_db()
        self.assertEqual(a.codigo_reserva, codigo)

    def test_reconciliacion_parcial_con_fallo_sql_real_es_reintentable(self):
        existente = reserva(self.a)
        mala, buena = self.faltante(), self.faltante()
        original = Reserva.construir_codigo_reserva

        def construir(instancia):
            return existente.codigo_reserva if instancia.pk == mala.pk else original(instancia)

        salida = StringIO()
        with patch.object(Reserva, 'construir_codigo_reserva', autospec=True, side_effect=construir), self.assertLogs(
                'apps.reservas.services.codigos_reserva', level='WARNING') as registro:
            with self.assertRaises(CommandError):
                call_command('recuperar_codigos_reservas', aplicar=True, unidad=self.a.pk, stdout=salida)
        resumen = json.loads(salida.getvalue())
        self.assertEqual((resumen['asignados'], resumen['fallidos']), (1, 1))
        self.assertEqual(registro.records[0].getMessage(), EVENTO_RECUPERACION_FALLIDA)
        self.assertNotIn(existente.codigo_reserva, str(registro.output))
        buena.refresh_from_db()
        codigo_bueno = buena.codigo_reserva
        self.assertEqual(self.comando(aplicar=True, unidad=self.a.pk)['asignados'], 1)
        buena.refresh_from_db()
        self.assertEqual(buena.codigo_reserva, codigo_bueno)

    def test_comando_detecta_cambio_de_unidad_despues_de_seleccionar(self):
        instancia = self.faltante()
        original = asegurar_codigo_reserva

        def mover(objeto, **opciones):
            Reserva.objects.filter(pk=objeto.pk).update(laboratorio=self.b)
            return original(objeto, **opciones)

        salida = StringIO()
        with patch('apps.reservas.management.commands.recuperar_codigos_reservas.asegurar_codigo_reserva', mover):
            with self.assertRaises(CommandError):
                call_command('recuperar_codigos_reservas', aplicar=True, unidad=self.a.pk, stdout=salida)
        resumen = json.loads(salida.getvalue())
        self.assertEqual((resumen['asignados'], resumen['fuera_de_alcance']), (0, 1))
        instancia.refresh_from_db()
        self.assertIsNone(instancia.codigo_reserva)


class CarreraCodigosReservaTests(TransactionTestCase):
    def test_dos_conexiones_solo_asignan_una_vez(self):
        instancia = reserva(unidad('carrera'))
        Reserva.objects.filter(pk=instancia.pk).update(codigo_reserva=None)
        barrera = Barrier(2)

        def asignar():
            close_old_connections()
            try:
                objeto = Reserva.objects.get(pk=instancia.pk)
                barrera.wait(timeout=10)
                return asegurar_codigo_reserva(objeto)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            trabajos = [ejecutor.submit(asignar) for _ in range(2)]
            resultados = [t.result(timeout=20) for t in trabajos]
        self.assertEqual(sum(r.asignado for r in resultados), 1)
        self.assertEqual(resultados[0].codigo, resultados[1].codigo)
        instancia.refresh_from_db()
        self.assertEqual(instancia.codigo_reserva, resultados[0].codigo)
