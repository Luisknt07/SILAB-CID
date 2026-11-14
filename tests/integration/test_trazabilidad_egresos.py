"""La fuente del fondo no reemplaza el expediente de compra ni la trazabilidad técnica."""
from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import MantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class TrazabilidadEgresosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('gestor-egresos-trazables')
        identificar(cls.actor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Unidad de reparaciones trazables',
            slug='egresos-trazables', dependencia='laboratorios', fecha_inicio=date(2025, 1, 1),
            administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Unidad ajena de reparaciones',
            slug='egresos-trazables-ajena', dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        modelo = EquiposServicios.objects.create(codigo='MODELO-TRAZA-EGRESO', nombre='Equipo de ensayo')
        cls.equipo = UnidadEquipo.objects.create(equipo=modelo, laboratorio=cls.unidad, codigo_unidad='TRAZA-EG-1')
        cls.ajeno = UnidadEquipo.objects.create(equipo=modelo, laboratorio=cls.otra, codigo_unidad='TRAZA-EG-2')
        cls.orden = MantenimientoEquipo.objects.create(equipo=cls.equipo, unidad=cls.unidad,
            tipo='correctivo', titulo='Reparación registrada', fecha_programada=timezone.now(), bloquea_agenda=False)

    def setUp(self):
        medios = TemporaryDirectory()
        self.addCleanup(medios.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=medios.name))

    def datos(self, **cambios):
        valores = dict(unidad=self.unidad, tipo='egreso', categoria='mantenimiento',
            fuente_fondos='autogestion', estado='pendiente', monto=Decimal('15'),
            descripcion='Reparación de accesorio', creado_por=self.actor, actualizado_por=self.actor)
        valores.update(cambios)
        return valores

    def respaldo(self):
        return dict(referencia='Factura 001-000045',
            comprobante=SimpleUploadedFile('factura.pdf', b'%PDF-1.4\nComprobante de prueba', content_type='application/pdf'),
            procedimiento_solicitado='infima', procedimiento_verificado=True,
            referencia_autorizacion='Oficio 041 autorizado por delegado de compras',
            certificacion_presupuestaria='Certificación CP-011')

    def confirmado(self, **cambios):
        return MovimientoFinancieroUnidad.objects.create(**self.datos(
            **dict(self.respaldo(), estado='confirmado', **cambios)))

    def test_autogestion_y_monto_pequeno_no_eximen_respaldo(self):
        with self.assertRaises(ValidationError) as error:
            MovimientoFinancieroUnidad.objects.create(**self.datos(estado='confirmado', monto=Decimal('0.50')))
        self.assertTrue({'referencia', 'comprobante', 'procedimiento_solicitado',
            'referencia_autorizacion', 'certificacion_presupuestaria'}.issubset(error.exception.message_dict))
        self.assertEqual(MovimientoFinancieroUnidad.objects.count(), 0)

    def test_pendiente_se_guarda_y_confirmacion_conserva_respaldo_y_orden(self):
        movimiento = MovimientoFinancieroUnidad.objects.create(**self.datos(mantenimiento=self.orden))
        self.assertEqual(movimiento.equipo_id, self.equipo.pk)
        for campo, valor in self.respaldo().items():
            setattr(movimiento, campo, valor)
        movimiento.estado = 'confirmado'
        movimiento.save(update_fields=['estado'])
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.trazabilidad_version, 1)
        self.assertEqual(movimiento.procedimiento_solicitado, 'infima')
        self.assertEqual(movimiento.referencia, 'Factura 001-000045')
        self.assertTrue(movimiento.comprobante)
        self.assertEqual(self.orden.movimientos_financieros.get().pk, movimiento.pk)

    def test_orden_y_equipo_no_pueden_contradecirse(self):
        with self.assertRaisesMessage(ValidationError, 'otro equipo'):
            MovimientoFinancieroUnidad.objects.create(**self.datos(mantenimiento=self.orden, equipo=self.ajeno))
        with self.assertRaisesMessage(ValidationError, 'asignado a esta unidad'):
            MovimientoFinancieroUnidad.objects.create(**self.datos(equipo=self.ajeno))
        with self.assertRaisesMessage(ValidationError, 'orden de mantenimiento debe pertenecer'):
            MovimientoFinancieroUnidad.objects.create(**self.datos(unidad=self.otra, mantenimiento=self.orden))

    def test_equipo_compartido_si_puede_vincularse_a_su_unidad(self):
        self.ajeno.laboratorios.add(self.unidad)
        movimiento = MovimientoFinancieroUnidad.objects.create(**self.datos(equipo=self.ajeno))
        self.assertEqual(movimiento.equipo_id, self.ajeno.pk)

    def test_borrador_recarga_asignacion_aunque_el_equipo_estuviera_en_memoria(self):
        movimiento = MovimientoFinancieroUnidad(**self.datos(equipo=self.equipo))
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(laboratorio=self.otra)
        with self.assertRaisesMessage(ValidationError, 'asignado a esta unidad'):
            movimiento.save()

    def test_caja_chica_exige_fundamento_y_revision_existente(self):
        valores = self.datos(**dict(self.respaldo(), estado='confirmado'))
        valores['procedimiento_solicitado'] = 'caja_chica'
        with self.assertRaisesMessage(ValidationError, 'fundamento vigente'):
            MovimientoFinancieroUnidad.objects.create(**valores)
        valores['fundamento_procedimiento'] = 'Fondo y norma institucional revisados por Finanzas, referencia FC-02'
        valores['procedimiento_verificado'] = False
        with self.assertRaisesMessage(ValidationError, 'revisión ya emitida'):
            MovimientoFinancieroUnidad.objects.create(**valores)
        valores['procedimiento_verificado'] = True
        movimiento = MovimientoFinancieroUnidad.objects.create(**valores)
        self.assertEqual(movimiento.fuente_fondos, 'autogestion')

    def test_ingreso_no_pide_expediente_de_adquisicion(self):
        ingreso = MovimientoFinancieroUnidad.objects.create(**self.datos(
            tipo='ingreso', categoria='producto', estado='confirmado'))
        self.assertEqual(ingreso.estado, 'confirmado')
        with self.assertRaisesMessage(ValidationError, 'corresponden a un egreso'):
            MovimientoFinancieroUnidad.objects.create(**self.datos(
                tipo='ingreso', categoria='producto', equipo=self.equipo))

    def test_confirmado_no_permite_reemplazar_respaldo_ni_equipo(self):
        movimiento = self.confirmado(equipo=self.equipo)
        for campo, valor in (('referencia_autorizacion', 'Otro oficio'), ('equipo', self.ajeno),
                             ('procedimiento_verificado', False), ('comprobante', 'finanzas/comprobantes/otro.pdf')):
            movimiento.refresh_from_db()
            setattr(movimiento, campo, valor)
            with self.subTest(campo=campo), self.assertRaisesMessage(ValidationError, 'no se edita'):
                movimiento.save()

    def test_traspaso_posterior_no_reescribe_ni_impide_anular_el_asiento(self):
        movimiento = self.confirmado(equipo=self.equipo, mantenimiento=self.orden)
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(laboratorio=self.otra)
        movimiento.refresh_from_db()
        movimiento.estado = 'anulado'
        movimiento.motivo_anulacion = 'Corrección documentada del valor'
        movimiento.anulado_por = self.actor
        movimiento.save()
        self.assertEqual(movimiento.unidad_id, self.unidad.pk)
        self.assertEqual(movimiento.equipo_id, self.equipo.pk)

    def test_migracion_legacy_confirmado_no_exige_recrear_respaldos(self):
        movimiento = MovimientoFinancieroUnidad.objects.create(**self.datos())
        # Simula el estado preservado por la migración, sin modificarlo en un sistema real.
        MovimientoFinancieroUnidad.objects.filter(pk=movimiento.pk).update(estado='confirmado', trazabilidad_version=0)
        movimiento.refresh_from_db()
        movimiento.estado = 'anulado'
        movimiento.motivo_anulacion = 'Anulación de asiento histórico'
        movimiento.save()
        self.assertEqual(movimiento.trazabilidad_version, 0)

    def test_borrador_legacy_y_marker_falso_no_omiten_validacion_nueva(self):
        movimiento = MovimientoFinancieroUnidad.objects.create(**self.datos())
        MovimientoFinancieroUnidad.objects.filter(pk=movimiento.pk).update(trazabilidad_version=0)
        movimiento.refresh_from_db()
        movimiento.estado = 'confirmado'
        with self.assertRaisesMessage(ValidationError, 'Adjunta el comprobante'):
            movimiento.save()
        with self.assertRaisesMessage(ValidationError, 'Adjunta el comprobante'):
            MovimientoFinancieroUnidad.objects.create(**self.datos(estado='confirmado', trazabilidad_version=0))

    def test_endpoint_enlaza_orden_y_rechaza_equipo_ajeno(self):
        self.client.force_login(self.actor)
        url = reverse('gestion_operacion_accion', args=[self.unidad.slug])
        datos = dict(modulo='finanzas', tipo='egreso', categoria='mantenimiento',
            fuente_fondos='autogestion', estado='confirmado', fecha_movimiento=date.today().isoformat(),
            monto='15', descripcion='Reparación con respaldo', mantenimiento_financiero_id=self.orden.pk,
            **self.respaldo())
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        movimiento = MovimientoFinancieroUnidad.objects.get()
        self.assertEqual(movimiento.equipo_id, self.equipo.pk)
        self.assertEqual(movimiento.mantenimiento_id, self.orden.pk)
        datos = dict(datos, estado='pendiente', equipo_financiero_id=self.ajeno.pk)
        datos.pop('comprobante')
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(MovimientoFinancieroUnidad.objects.count(), 1)

    def test_endpoint_no_acepta_egreso_confirmado_incompleto_y_formulario_es_guiado(self):
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            dict(modulo='finanzas', tipo='egreso', categoria='mantenimiento', fuente_fondos='autogestion',
                estado='confirmado', fecha_movimiento=date.today().isoformat(), monto='15', descripcion='Incompleto'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(MovimientoFinancieroUnidad.objects.exists())
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
            dict(view='recursos', modo_recursos='finanzas'))
        self.assertContains(panel, 'data-financial-egreso')
        self.assertContains(panel, 'Saldo registrado de autogestión')
        self.assertContains(panel, 'Este formulario no autoriza compras')
        self.assertNotContains(panel, 'Presupuesto institucional / compra pública')
