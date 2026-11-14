"""Préstamo de equipos: quién lo retira, con qué plazo y en qué estado vuelve.

Hasta ahora un préstamo era la marca «prestado» en el activo, sin traza. El
expediente exigía el registro y había que cargarlo a mano. Estas pruebas
cubren lo que ese registro tiene que garantizar: que el equipo salga de las
reservas mientras está afuera, que vuelva solo al devolverlo, que la salida
externa no se acepte sin respaldo y que el reporte sustente el documento.
"""

import io
import tempfile
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class BaseDePrestamos(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-prestamos', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de préstamos', slug='laboratorio-prestamos', dependencia='laboratorios',
            descripcion='Laboratorio de prueba.', fecha_inicio=date(2024, 1, 1),
            administrador=cls.coordinador)
        servicio = EquiposServicios.objects.create(codigo='PRE-SCAN', nombre='Escáner 3D')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='PRE-SCAN-01', equipo=servicio, laboratorio=cls.unidad,
            estado_unidad='disponible')

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix='citt-qa-prestamos-')
        self.addCleanup(self.temporal.cleanup)
        medios = override_settings(MEDIA_ROOT=self.temporal.name)
        medios.enable()
        self.addCleanup(medios.disable)

    def acta(self):
        salida = io.BytesIO()
        canvas = Canvas(salida)
        canvas.drawString(36, 780, 'Acta QA: entrega externa autorizada de equipo y responsabilidad de custodia.')
        canvas.save()
        return SimpleUploadedFile('acta-qa.pdf', salida.getvalue(), 'application/pdf')

    def prestar(self, **extra):
        datos = dict(
            equipo=self.equipo, tipo='interno', estado='entregado',
            nombre_solicitante='Docente de Diseño', proposito='Taller en otra aula.',
            fecha_salida=timezone.make_aware(datetime(2026, 10, 5, 9, 0)),
            fecha_retorno_previsto=timezone.make_aware(datetime(2026, 10, 9, 17, 0)))
        datos.update(extra)
        if datos['tipo'] == 'externo':
            datos.setdefault('acta', self.acta())
            datos.setdefault('entregado_por', self.coordinador)
        return PrestamoEquipo.objects.create(**datos)


class CustodiaDelEquipoTests(BaseDePrestamos):
    """Mientras está afuera, el equipo no se ofrece ni se reserva."""

    def test_al_entregarlo_el_equipo_queda_prestado_y_recuerda_su_estado(self):
        prestamo = self.prestar()

        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'prestado')
        self.assertEqual(prestamo.estado_equipo_previo, 'disponible')
        self.assertFalse(self.equipo.disponible_para_reserva)

    def test_al_devolverlo_vuelve_al_estado_que_tenia(self):
        # Un préstamo ya entregado: el retorno se registra sobre una salida real.
        prestamo = self.prestar(
            fecha_salida=timezone.now() - timedelta(days=6),
            fecha_retorno_previsto=timezone.now() - timedelta(days=1))

        prestamo.estado = 'devuelto'
        prestamo.condicion_retorno = 'bueno'
        prestamo.recibido_por = self.coordinador
        prestamo.save()

        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'disponible')
        self.assertIsNotNone(prestamo.fecha_retorno_real)

    def test_el_calendario_lo_muestra_afuera_todo_el_plazo(self):
        prestamo = self.prestar()

        bloqueo = BloqueoAgendaUnidad.objects.get(prestamo=prestamo)
        self.assertEqual(bloqueo.tipo, 'prestamo')
        self.assertEqual(bloqueo.alcance, 'equipos')
        self.assertTrue(bloqueo.dia_completo)
        self.assertEqual((bloqueo.fecha_inicio, bloqueo.fecha_fin),
                         (date(2026, 10, 5), date(2026, 10, 9)))
        self.assertEqual(list(bloqueo.equipos.all()), [self.equipo])

    def test_al_devolverlo_la_agenda_queda_libre(self):
        prestamo = self.prestar(
            fecha_salida=timezone.now() - timedelta(days=6),
            fecha_retorno_previsto=timezone.now() - timedelta(days=1))

        prestamo.estado = 'devuelto'
        prestamo.condicion_retorno = 'bueno'
        prestamo.recibido_por = self.coordinador
        prestamo.save()

        self.assertFalse(BloqueoAgendaUnidad.objects.filter(prestamo=prestamo).exists())

    def test_el_cierre_impide_reservar_ese_equipo_esos_dias(self):
        from apps.reservas.presentation.conflictos import validar_conflictos_recursos

        prestamo = self.prestar()

        with self.assertRaises(ValueError) as fallo:
            validar_conflictos_recursos(
                self.unidad, date(2026, 10, 7), time(10, 0), time(11, 0),
                [{'id': self.equipo.pk, 'nombre': self.equipo.equipo.nombre}], [], [],
                incluye_espacio=False, alcance_espacio='', tipo_solicitud='equipos',
                modalidad_servicio='', proposito_codigo='docencia_practica', numero_participantes=1)

        self.assertIn(prestamo.codigo, str(fallo.exception))

    def test_un_prestamo_vencido_se_reconoce_solo(self):
        prestamo = self.prestar(
            fecha_salida=timezone.now() - timedelta(days=20),
            fecha_retorno_previsto=timezone.now() - timedelta(days=3))

        self.assertTrue(prestamo.vencido)
        self.assertGreaterEqual(prestamo.dias_fuera, 20)


class SalidaExternaTests(BaseDePrestamos):
    """El activo que sale de la Universidad exige respaldo."""

    def test_sin_institucion_ni_autorizacion_no_se_acepta(self):
        with self.assertRaises(ValidationError) as fallo:
            self.prestar(tipo='externo')

        errores = fallo.exception.message_dict
        self.assertIn('institucion', errores)
        self.assertIn('autorizado_por', errores)

    def test_con_institucion_y_autorizacion_se_registra(self):
        prestamo = self.prestar(
            tipo='externo', institucion='Colegio Técnico Bolívar',
            autorizado_por='Dirección de Vinculación')

        self.assertEqual(prestamo.get_tipo_display(), 'Externo: sale de la Universidad')
        self.assertTrue(prestamo.esta_afuera)

    def test_el_interno_no_pide_institucion(self):
        prestamo = self.prestar(tipo='interno')

        self.assertEqual(prestamo.institucion, '')

    def test_hay_que_decir_quien_retira(self):
        with self.assertRaises(ValidationError) as fallo:
            self.prestar(nombre_solicitante='')

        self.assertIn('nombre_solicitante', fallo.exception.message_dict)

    def test_devolver_exige_decir_en_que_condicion_volvio(self):
        prestamo = self.prestar()

        prestamo.estado = 'devuelto'
        with self.assertRaises(ValidationError) as fallo:
            prestamo.save()

        self.assertIn('condicion_retorno', fallo.exception.message_dict)

    def test_el_retorno_no_puede_preceder_a_la_salida(self):
        with self.assertRaises(ValidationError) as fallo:
            self.prestar(fecha_retorno_previsto=timezone.make_aware(datetime(2026, 10, 1, 9, 0)))

        self.assertIn('fecha_retorno_previsto', fallo.exception.message_dict)


class ReporteDePrestamosTests(BaseDePrestamos):
    """El registro que el expediente exigía cargado a mano ahora sale del sistema."""

    def test_el_reporte_sustenta_el_documento_del_expediente(self):
        # El informe conserva una salida histórica incompleta, aunque las
        # nuevas transiciones ya no permiten entregar sin acta.
        PrestamoEquipo.objects.bulk_create([PrestamoEquipo(equipo=self.equipo, unidad=self.unidad,
            tipo='externo', estado='entregado', nombre_solicitante='Docente de Diseño', proposito='Préstamo histórico QA',
            institucion='Colegio Técnico Bolívar', autorizado_por='Dirección de Vinculación',
            fecha_salida=timezone.now() - timedelta(days=2),
            fecha_retorno_previsto=timezone.now() + timedelta(days=3))])
        peticion = RequestFactory().get('/', {'categoria_reporte': 'prestamos'})
        peticion.user = self.coordinador

        reporte = build_unit_report(peticion, self.unidad)

        datos = reporte['dataset']
        columna = {nombre: indice for indice, nombre in enumerate(datos['headers'])}
        fila = datos['rows'][0]
        self.assertEqual(fila[columna['Tipo']], 'Externo')
        self.assertEqual(fila[columna['Institución o área']], 'Colegio Técnico Bolívar')
        self.assertEqual(fila[columna['Acta']], 'No')
        tarjetas = {tarjeta[0]: tarjeta[1] for tarjeta in datos['cards']}
        self.assertEqual(tarjetas['Equipos fuera ahora'], 1)
        self.assertEqual(tarjetas['Externos sin acta'], 1)
        self.assertEqual(reporte['expediente']['nombre'], 'Registro de préstamos y devoluciones de equipos')

    def test_la_consola_ofrece_registrar_el_prestamo(self):
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'recursos'})

        contenido = pagina.content.decode()
        self.assertIn('data-agenda-operation-form="prestamo"', contenido)
        self.assertIn('data-agenda-operation-open="prestamo"', contenido)
        self.assertIn('Salidas y devoluciones', contenido)

    def test_se_registra_desde_la_consola_y_el_equipo_sale_de_reservas(self):
        self.client.force_login(self.coordinador)

        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'prestamo',
                'equipo_id': self.equipo.pk,
                'tipo': 'externo',
                'estado': 'entregado',
                'nombre_solicitante': 'Sra. Patricia Yépez',
                'institucion': 'Junta Parroquial',
                'autorizado_por': 'Dirección de Vinculación',
                'proposito': 'Señalética del centro comunitario.',
                'fecha_salida': '2026-11-02T08:00',
                'fecha_retorno_previsto': '2026-11-12T17:00',
                'condicion_salida': 'bueno',
                'bloquea_agenda': 'true',
                'acta': self.acta(),
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        prestamo = PrestamoEquipo.objects.get(pk=respuesta.json()['registro']['id'])
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'prestado')
        self.assertEqual(prestamo.entregado_por, self.coordinador)
        self.assertTrue(BloqueoAgendaUnidad.objects.filter(prestamo=prestamo).exists())


class NavegadorDeInformesTests(BaseDePrestamos):
    """Los ocho informes se ven y se abren sin desplegar un menú."""

    def test_la_consola_lista_las_familias_y_marca_cuales_son_evidencia(self):
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'reportes', 'categoria_reporte': 'reservas'})

        contenido = pagina.content.decode()
        self.assertIn('unit-console__report-nav', contenido)
        self.assertIn('1 · Planificación y registros de uso de laboratorios', contenido)
        self.assertIn('8 · Transferencia de conocimiento, tecnología y servicios especializados a la sociedad', contenido)
        # Los préstamos son un anexo del informe de cierre: el navegador lo dice.
        self.assertIn('anexo del informe de cierre', contenido)
        self.assertIn('categoria_reporte=prestamos', contenido)
        # El menú desplegable de veinte categorías ya no hace falta.
        self.assertNotIn('<select name="categoria_reporte"', contenido)

    def test_el_informe_abierto_despliega_su_grupo(self):
        peticion = RequestFactory().get('/', {'categoria_reporte': 'prestamos'})
        peticion.user = self.coordinador

        reporte = build_unit_report(peticion, self.unidad)

        self.assertEqual(reporte['choices']['familia_activa'],
                         '3 · Inventario de equipamiento, reactivos e insumos')
