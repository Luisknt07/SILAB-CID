"""La custodia exige respaldo al entregar, sin convertir solicitudes en salidas."""
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.reportes_condiciones import reporte_prestamos
from apps.recursos.models.prestamos import PrestamoEquipo
from tests.integration.test_prestamos_equipos import BaseDePrestamos


class RespaldoPrestamosLaboratoriosTests(BaseDePrestamos):
    def solicitud(self, **extra):
        return self.prestar(tipo='externo', estado='solicitado', acta='', institucion='', autorizado_por='', **extra)

    def preparar_salida(self, prestamo):
        prestamo.estado = 'entregado'
        prestamo.institucion = 'Institución receptora QA'
        prestamo.autorizado_por = 'Dirección de unidad QA'
        prestamo.entregado_por = self.coordinador

    def test_solicitud_externa_se_guarda_sin_acta_y_sin_autorizacion(self):
        prestamo = self.solicitud()
        self.equipo.refresh_from_db()
        self.assertEqual(prestamo.estado, 'solicitado')
        self.assertEqual(self.equipo.estado_unidad, 'disponible')

    def test_no_se_puede_crear_una_salida_externa_ya_entregada_sin_acta(self):
        with self.assertRaises(ValidationError) as error:
            self.prestar(tipo='externo', estado='entregado', institucion='Destinatario QA',
                autorizado_por='Dirección QA', acta='')
        self.assertIn('acta', error.exception.message_dict)
        self.assertFalse(PrestamoEquipo.objects.exists())
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'disponible')

    def test_transicion_entregado_exige_acta_legible_y_no_cierra_el_archivo_nuevo(self):
        prestamo = self.solicitud()
        self.preparar_salida(prestamo)
        with self.assertRaises(ValidationError) as error:
            prestamo.save()
        self.assertIn('acta', error.exception.message_dict)
        prestamo.acta = SimpleUploadedFile('falso.pdf', b'archivo vacio sin un PDF real', 'application/pdf')
        with self.assertRaises(ValidationError):
            prestamo.save()
        prestamo.acta = self.acta()
        prestamo.full_clean()
        prestamo.save()
        prestamo.refresh_from_db()
        self.assertTrue(prestamo.acta.storage.exists(prestamo.acta.name))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'prestado')

    def test_entrega_externa_necesita_responsable_de_entrega_real(self):
        prestamo = self.solicitud()
        self.preparar_salida(prestamo)
        prestamo.acta = self.acta()
        prestamo.entregado_por = None
        with self.assertRaises(ValidationError) as error:
            prestamo.save()
        self.assertIn('entregado_por', error.exception.message_dict)

    def test_regreso_de_un_prestamo_historico_no_obliga_inventar_un_acta_de_salida(self):
        prestamo = self.solicitud()
        PrestamoEquipo.objects.filter(pk=prestamo.pk).update(estado='entregado')
        prestamo.refresh_from_db()
        prestamo.estado = 'devuelto'
        prestamo.condicion_retorno = 'bueno'
        with self.assertRaises(ValidationError) as error:
            prestamo.save()
        self.assertIn('recibido_por', error.exception.message_dict)
        prestamo.recibido_por = self.coordinador
        prestamo.save()
        self.assertEqual(prestamo.estado, 'devuelto')
        self.assertFalse(prestamo.acta)
        encabezados, filas, _, _ = reporte_prestamos(self.unidad,
            prestamo.fecha_salida.date(), prestamo.fecha_retorno_previsto.date())
        self.assertIn('acta legible', filas[0][encabezados.index('Pendientes de respaldo')])

    def test_la_transicion_desde_consola_registra_al_usuario_que_entrega(self):
        prestamo = self.solicitud()
        PrestamoEquipo.objects.filter(pk=prestamo.pk).update(entregado_por=None)
        self.client.force_login(self.coordinador)
        datos = dict(modulo='prestamo', registro_id=prestamo.pk, equipo_id=self.equipo.pk,
            tipo='externo', estado='entregado', nombre_solicitante='Receptor QA',
            institucion='Institución QA', autorizado_por='Dirección QA', proposito='Uso autorizado QA',
            fecha_salida='2026-10-05T09:00', fecha_retorno_previsto='2026-10-09T17:00',
            condicion_salida='bueno', acta=self.acta())
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.entregado_por_id, self.coordinador.pk)
        self.assertEqual(prestamo.estado, 'entregado')

    def test_otros_tipos_de_unidad_conservan_la_regla_anterior_sin_acta_obligatoria(self):
        observatorio = Unidad.objects.create(nombre='Observatorio de préstamos QA', slug='observatorio-prestamos-qa',
            dependencia='observatorios', administrador=self.coordinador, fecha_inicio=self.unidad.fecha_inicio)
        self.equipo.laboratorio = observatorio
        self.equipo.save()
        prestamo = self.prestar(tipo='externo', estado='entregado', acta='',
            institucion='Receptor QA', autorizado_por='Dirección QA')
        self.assertFalse(prestamo.acta)
        prestamo.estado = 'devuelto'
        prestamo.condicion_retorno = 'bueno'
        prestamo.save()
        self.assertIsNone(prestamo.recibido_por)
