"""Integridad entre unidades, kardex, conteos y el expediente de una visita."""
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone, translation

from apps.core.tipologias import TIPOLOGIAS_BASE, Tipologia
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.gestion import _datos_anteriores_operacion, _decimal_opcional, _operar_inventario
from apps.integraciones.management.commands.cargar_laboratorios_institucionales import Command as CargarUnidades
from apps.laboratorios.operacion.models.fablab import (
    FablabService, FablabServiceConsumible, SolicitudConsumible, SolicitudFabricacion,
)
from apps.recursos.models.almacen import ConteoInventario, LineaConteo
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.presentation.almacen import cerrar_conteo, registrar_linea
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.visitas import SolicitudVisita
from apps.reservas.presentation.ejecucion import _decimal
from apps.plantas_piloto.operacion.models.produccion import _decimal as decimal_produccion


class NombresGestionTests(SimpleTestCase):
    def test_etiqueta_respeta_los_cuatro_tipos_y_el_catalogo_institucional(self):
        for tipo in (*TIPOLOGIAS_BASE, Tipologia('invernaderos', 'Invernadero', 'Invernaderos', 'centro_experimental')):
            with self.subTest(tipo=tipo.codigo), translation.override('es'), patch(
                'apps.directorio_unidades.models.core.tipologia_por_codigo', return_value=tipo,
            ), patch('apps.directorio_unidades.models.core.nombre_tipologia', return_value=tipo.nombre):
                unidad = Unidad(dependencia=tipo.codigo)
                self.assertEqual(unidad.etiqueta_gestion, 'Gestionar ' + tipo.nombre.lower())


class CantidadesCierreTests(SimpleTestCase):
    def test_un_monto_no_finito_es_error_de_validacion(self):
        for texto in ('NaN', 'sNaN', 'Infinity', '-Infinity'):
            with self.subTest(texto=texto), self.assertRaisesMessage(ValueError, 'finito'):
                _decimal(texto, 'El monto')
        self.assertEqual(_decimal('0.60', 'El monto'), Decimal('0.60'))

    def test_gestion_y_produccion_rechazan_numeros_no_finitos(self):
        for texto in ('NaN', 'sNaN', 'Infinity', '-Infinity'):
            with self.subTest(texto=texto), self.assertRaisesMessage(ValueError, 'finito'):
                _decimal_opcional(texto, 'La cantidad')
            with self.subTest(texto=texto), self.assertRaisesMessage(ValidationError, 'finito'):
                decimal_produccion(texto)


class IntegridadGestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Unidad QA', slug='integridad-qa', descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra QA', slug='integridad-otra', descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.material = Consumible.objects.create(unidad=cls.unidad, codigo='QA-INTEGRIDAD-PROPIO', nombre='Material propio', stock_total=10, precio_unitario=1)
        cls.ajeno = Consumible.objects.create(unidad=cls.otra, codigo='QA-INTEGRIDAD-AJENO', nombre='Material ajeno', stock_total=10, precio_unitario=1)
        cls.lote = LoteConsumible.objects.create(consumible=cls.material, codigo='QA-01', cantidad_inicial=10, cantidad_actual=10, bodega='Bodega QA')
        cls.conteo = ConteoInventario.objects.create(unidad=cls.unidad, nombre='Conteo QA')
        cls.linea = LineaConteo.objects.create(conteo=cls.conteo, consumible=cls.material, lote=cls.lote, cantidad_sistema=10)

    def test_los_materiales_de_servicio_no_cruzan_unidades_ni_admiten_negativos(self):
        servicio = FablabService.objects.create(unidad=self.unidad, code='QA', nombre='Servicio QA')
        solicitud = SolicitudFabricacion.objects.create(unidad=self.unidad)
        for fila, campo in (
            (FablabServiceConsumible(service=servicio, consumible=self.ajeno), 'consumible'),
            (SolicitudConsumible(solicitud=solicitud, consumible=self.ajeno), 'consumible'),
            (FablabServiceConsumible(service=servicio, consumible=self.material, cantidad_sugerida=-1), 'cantidad_sugerida'),
            (SolicitudConsumible(solicitud=solicitud, consumible=self.material, cantidad=-1), 'cantidad'),
        ):
            with self.subTest(fila=type(fila).__name__, campo=campo), self.assertRaises(ValidationError) as error:
                fila.save()
            self.assertIn(campo, error.exception.message_dict)

    def test_el_conteo_valida_la_unidad_y_el_lote(self):
        self.linea.consumible = self.ajeno
        with self.assertRaises(ValidationError) as error:
            self.linea.full_clean()
        self.assertIn('consumible', error.exception.message_dict)
        self.assertIn('lote', error.exception.message_dict)

    def test_el_kardex_rechaza_un_saldo_no_finito_sin_crear_movimiento(self):
        for valor in ('NaN', 'Infinity', '-Infinity'):
            request = RequestFactory().post('/', {'consumible_id': self.material.pk, 'tipo': 'ajuste', 'cantidad': valor})
            with self.subTest(valor=valor), self.assertRaisesMessage(ValidationError, 'finita'):
                _operar_inventario(request, self.unidad)
        self.assertFalse(EntradaInventario.objects.exists())

    def test_la_captura_de_auditoria_no_invierte_los_bloqueos_del_caso_de_uso(self):
        for modelo, objeto, tabla_padre, tabla_hija in (
            (LineaConteo, self.linea, 'webcitt_conteoinventario', 'webcitt_lineaconteo'),
            (LoteConsumible, self.lote, 'webcitt_consumible', 'webcitt_loteconsumible'),
        ):
            with self.subTest(modelo=modelo.__name__), CaptureQueriesContext(connection) as queries:
                request = RequestFactory().post('/', {'registro_id': objeto.pk})
                _datos_anteriores_operacion(request, self.unidad, modelo)
            bloqueos = [q['sql'] for q in queries if 'FOR UPDATE' in q['sql']]
            self.assertGreaterEqual(len(bloqueos), 2)
            self.assertIn('FROM "' + tabla_padre + '"', bloqueos[0])
            self.assertIn('FROM "' + tabla_hija + '"', bloqueos[1])

    def test_rechaza_cantidades_no_finitas_sin_alterar_el_conteo(self):
        for cantidad in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(cantidad=cantidad), self.assertRaisesMessage(ValidationError, 'finito'):
                registrar_linea(self.linea, cantidad)
        self.linea.refresh_from_db()
        self.assertIsNone(self.linea.cantidad_contada)

    def test_un_movimiento_posterior_impide_ajustar_un_conteo_desactualizado(self):
        registrar_linea(self.linea, '8')
        EntradaInventario.objects.create(unidad=self.unidad, consumible=self.material, lote_inventario=self.lote, tipo='salida', cantidad=1)
        with self.assertRaisesMessage(ValidationError, 'saldo de un lote cambió'):
            cerrar_conteo(self.conteo, None)
        self.lote.refresh_from_db()
        self.conteo.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('9'))
        self.assertEqual(self.conteo.estado, 'abierto')
        self.assertFalse(EntradaInventario.objects.filter(referencia=self.conteo.codigo).exists())

    def test_un_objeto_antiguo_no_permite_reabrir_ni_cerrar_dos_veces(self):
        registrar_linea(self.linea, '8')
        cerrar_conteo(self.conteo, None)
        with self.assertRaisesMessage(ValidationError, 'ya está cerrado'):
            registrar_linea(self.linea, '6')
        with self.assertRaisesMessage(ValidationError, 'ya está cerrado'):
            cerrar_conteo(self.conteo, None)
        self.assertEqual(EntradaInventario.objects.filter(referencia=self.conteo.codigo).count(), 1)

    def test_el_importe_de_visita_se_sincroniza_al_cambiar_el_expediente(self):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, fecha=timezone.localdate() + timedelta(days=3), hora_inicio=time(10), hora_fin=time(11),
            nombre_solicitante='Solicitante QA', correo_solicitante='qa@example.invalid', costo_estimado=Decimal('1.00'),
        )
        visita = SolicitudVisita.objects.create(unidad=self.unidad, reserva=reserva, institucion='Grupo QA', personas=1, costo_estimado=Decimal('1.00'))
        reserva.costo_estimado = Decimal('2.50')
        reserva.save(update_fields=['costo_estimado'])
        visita.refresh_from_db()
        self.assertEqual(visita.costo_estimado, Decimal('2.50'))
        self.assertEqual(visita.valor_estimado_vigente, Decimal('2.50'))
        # Un guardado parcial de otro campo no debe publicar un importe local obsoleto.
        reserva.costo_estimado = Decimal('99')
        reserva.descripcion_proyecto = 'Nota QA'
        reserva.save(update_fields=['descripcion_proyecto'])
        visita.refresh_from_db()
        self.assertEqual(visita.costo_estimado, Decimal('2.50'))

    def test_recargar_el_catalogo_conserva_los_saldos_y_vencimientos_operativos(self):
        datos = {
            'codigo': 'QA-INS-RECARGA', 'nombre': 'Material de referencia', 'clasificacion': 'material',
            'cantidad_por_presentacion': Decimal('1'), 'unidad_medida': 'unidad', 'descripcion': '.',
            'stock_total': Decimal('10'), 'minimo': Decimal('2'), 'precio_unitario': Decimal('1'),
            'ubicacion': 'Bodega QA', 'lotes': [{'codigo': 'QA-RECARGA', 'cantidad': Decimal('10'), 'estado': 'bodega'}],
        }
        comando = CargarUnidades()
        definicion = {'consumibles': [datos]}
        material = comando._consumibles(self.unidad, definicion, {}, {})[datos['codigo']]
        lote = material.lotes_inventario.get()
        vencimiento = timezone.localdate() + timedelta(days=7)
        lote.fecha_vencimiento = vencimiento
        lote.save(update_fields=['fecha_vencimiento'])
        EntradaInventario.objects.create(unidad=self.unidad, consumible=material, lote_inventario=lote, tipo='salida', cantidad=2)
        comando._consumibles(self.unidad, definicion, {}, {})
        material.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(material.stock_total, Decimal('8'))
        self.assertEqual(lote.cantidad_actual, Decimal('8'))
        self.assertEqual(lote.fecha_vencimiento, vencimiento)
        self.assertEqual(material.lotes_inventario.count(), 1)
