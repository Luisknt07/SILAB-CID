"""La limpieza borra lo que las unidades registran al operar y conserva catálogos, biblioteca y cuentas reales."""
from datetime import date
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.expediente import construir_expediente
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.integraciones.management.commands.limpiar_movimientos import FRASE, MOVIMIENTOS
from apps.recursos.models.recursos import Recurso
from tests.integration.utiles import pdf_legible_prueba


class LimpiarMovimientosTests(TestCase):
    def setUp(self):
        medios = TemporaryDirectory(prefix='citt-limpieza-')
        self.addCleanup(medios.cleanup)
        ajustes = override_settings(MEDIA_ROOT=medios.name)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        asegurar_catalogo()
        usuarios = get_user_model().objects
        self.real = usuarios.create_user('admin.unidad-limpieza', password=None)
        self.demo = usuarios.create_user('demo.coordinador.limpieza', password=None)
        self.unidad = Unidad.objects.create(nombre='Laboratorio de limpieza', slug='laboratorio-limpieza',
                                            dependencia='laboratorios', administrador=self.real,
                                            fecha_inicio=date(2025, 1, 1))
        construir_expediente(self.unidad, 2026)
        self.documento = DocumentoExpediente.objects.filter(unidad=self.unidad).first()
        self.del_expediente = self.recurso('Informe generado · v1', palabras_clave='expediente, cierre, 2026')
        self.documento.recurso = self.del_expediente
        self.documento.save(update_fields=['recurso'])
        self.de_biblioteca = self.recurso('Manual de la impresora')
        RegistroAuditoriaUnidad.objects.create(unidad=self.unidad, usuario=self.real, descripcion='prueba:limpieza')

    def recurso(self, nombre, **campos):
        return Recurso.objects.create(unidad=self.unidad, nombre=nombre, **campos,
                                      archivo=ContentFile(pdf_legible_prueba(), name='archivo.pdf'))

    def limpiar(self, *opciones):
        salida = StringIO()
        call_command('limpiar_movimientos', *opciones, stdout=salida)
        return salida.getvalue()

    def aplicar(self, *opciones):
        return self.limpiar('--aplicar', '--confirmar', FRASE, '--base', connection.settings_dict['NAME'], *opciones)

    def test_la_lista_de_movimientos_no_incluye_catalogos_ni_configuracion(self):
        conservados = {'directorio_unidades.Unidad', 'gestion_unidades.EspacioReservable', 'recursos.UnidadEquipo',
                       'recursos.Consumible', 'recursos.LoteConsumible', 'recursos.EntradaInventario',
                       'recursos.SoftwareDisponible', 'recursos.Recurso', 'formacion.Asignatura', 'formacion.Curso',
                       'reservas.GuiaActividadReserva', 'reservas.CatalogoActividadReserva',
                       'documentos.DocumentoExigido', 'core.AsignacionGobernanza', 'auth.User'}
        self.assertFalse(conservados & set(MOVIMIENTOS))
        self.assertEqual(len(MOVIMIENTOS), len(set(MOVIMIENTOS)))

    def test_el_ensayo_informa_y_no_cambia_nada(self):
        documentos = DocumentoExpediente.objects.count()
        salida = self.limpiar()
        self.assertIn('ensayo', salida)
        self.assertIn('no se cambió nada', salida)
        self.assertEqual(DocumentoExpediente.objects.count(), documentos)
        self.assertTrue(get_user_model().objects.filter(pk=self.demo.pk).exists())
        self.assertTrue(Recurso.objects.filter(pk=self.del_expediente.pk).exists())

    def test_aplicar_exige_la_frase_y_el_nombre_de_la_base(self):
        with self.assertRaises(CommandError):
            self.limpiar('--aplicar')
        with self.assertRaises(CommandError):
            self.limpiar('--aplicar', '--confirmar', FRASE, '--base', 'otra_base')
        self.assertTrue(DocumentoExpediente.objects.exists())

    def test_aplicar_borra_los_movimientos_y_conserva_catalogos_biblioteca_y_cuentas_reales(self):
        exigidos = DocumentoExigido.objects.count()
        archivo = self.del_expediente.archivo.name
        salida = self.aplicar('--listar-archivos')
        self.assertIn('Limpieza aplicada', salida)
        self.assertFalse(DocumentoExpediente.objects.exists())
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertFalse(Recurso.objects.filter(pk=self.del_expediente.pk).exists())
        self.assertIn(f'ARCHIVO {archivo}', salida)
        # Lo que describe a la institución sigue ahí.
        self.assertTrue(Unidad.objects.filter(pk=self.unidad.pk).exists())
        self.assertTrue(Recurso.objects.filter(pk=self.de_biblioteca.pk).exists())
        self.assertNotIn(f'ARCHIVO {self.de_biblioteca.archivo.name}', salida)
        self.assertEqual(DocumentoExigido.objects.count(), exigidos)
        self.assertTrue(get_user_model().objects.filter(pk=self.real.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.demo.pk).exists())
        # Sobre una base ya limpia no hay nada que hacer y no falla.
        self.assertIn('Limpieza aplicada', self.aplicar())

    def test_la_valoracion_de_una_reserva_se_borra_con_ella(self):
        from datetime import time

        from apps.reservas.models.reservas import Reserva
        from apps.reservas.models.valoraciones import ValoracionReserva
        self.assertLess(MOVIMIENTOS.index('reservas.ValoracionReserva'), MOVIMIENTOS.index('reservas.Reserva'))
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.real, fecha=date(2026, 3, 10), hora_inicio=time(9),
            hora_fin=time(10), equipo_codigo='EQ-LIMPIEZA', equipo_nombre='Equipo ficticio',
            estado='completada', resultado_cierre='atendida')
        ValoracionReserva.objects.create(reserva=reserva, general=4, comentario='Comentario ficticio de prueba.')
        salida = self.aplicar()
        self.assertIn('Limpieza aplicada', salida)
        self.assertFalse(ValoracionReserva.objects.exists())
        self.assertFalse(Reserva.objects.exists())

    def test_una_cuenta_demo_ligada_a_lo_que_se_conserva_se_desactiva_en_vez_de_borrarse(self):
        from apps.core.models.gobernanza import AsignacionGobernanza
        AsignacionGobernanza.objects.create(
            usuario=self.demo, rol='seguimiento', referencia='', acto='Acto ficticio exclusivamente de prueba',
            dedicacion='Cobertura de prueba', desde=date(2026, 1, 1), registrado_por=self.real)
        salida = self.aplicar()
        self.assertIn('desactivada', salida)
        self.demo.refresh_from_db()
        self.assertFalse(self.demo.is_active)
        self.assertTrue(AsignacionGobernanza.objects.filter(usuario=self.demo).exists())

    def test_una_cuenta_demo_que_administra_una_unidad_se_borra_y_la_unidad_queda_sin_administrador(self):
        self.unidad.administrador = self.demo
        self.unidad.save(update_fields=['administrador'])
        salida = self.aplicar()
        self.assertIn('directorio_unidades.Unidad.administrador: 1', salida)
        self.unidad.refresh_from_db()
        self.assertIsNone(self.unidad.administrador_id)

    def test_las_existencias_solo_se_borran_si_se_pide_y_el_insumo_queda_en_el_catalogo_con_saldo_cero(self):
        from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='INS-LIMPIEZA', nombre='Filamento de prueba',
                                           unidad_medida='kg', minimo=2)
        EntradaInventario.objects.create(unidad=self.unidad, consumible=insumo, tipo='ingreso', motivo='recepcion',
                                         cantidad=5, usuario=self.real, nota='Recepción de prueba.')
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_total, 5)
        self.aplicar()
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_total, 5)
        self.assertTrue(EntradaInventario.objects.exists())
        salida = self.aplicar('--existencias')
        self.assertIn('insumos que quedan con saldo 0: 1', salida)
        self.assertFalse(EntradaInventario.objects.exists())
        self.assertFalse(LoteConsumible.objects.exists())
        insumo.refresh_from_db()
        self.assertEqual((insumo.stock_total, insumo.minimo), (0, 2))

    def test_los_archivos_de_lo_borrado_se_mueven_a_la_carpeta_indicada(self):
        ruta = self.del_expediente.archivo.path
        conservado = self.de_biblioteca.archivo.path
        with TemporaryDirectory(prefix='citt-retirados-') as destino:
            self.aplicar('--retirar-archivos-a', destino)
            from pathlib import Path
            self.assertFalse(Path(ruta).exists())
            self.assertTrue((Path(destino) / self.del_expediente.archivo.name).is_file())
            self.assertTrue(Path(conservado).is_file())
