from datetime import date, time

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Categoria, Unidad
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario
from apps.laboratorios.operacion.models.fablab import FablabService, SolicitudFabricacion
from apps.reservas.models.reservas import GuiaActividadReserva, ProgramacionReserva, Reserva, RegistroParticipanteReserva
from apps.formacion.models.practicas import PlanificacionPractica
from apps.recursos.models.recursos import Recurso
from apps.recursos.models.unidades import UnidadEquipo


class RecursoAdminFormTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-recursos',
            email='recursos@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.usuario)
        self.unidad = Unidad.objects.create(
            nombre='Unidad para recursos del administrador',
            slug='unidad-recursos-admin',
            dependencia='plantas_piloto',
            descripcion='Unidad para validar altas y cambios de archivos.',
            fecha_inicio=date(2026, 1, 1),
        )
        self.datos = {
            'unidad': str(self.unidad.pk),
            'nombre': 'Manual de operación',
            'descripcion': 'Explica la operación segura del proceso y su secuencia.',
            'carpeta': '',
            'ficha': '',
            'archivo': '',
            'url': 'https://example.test/manual.pdf',
            'tipo_adjunto': 'informe',
            'autor': 'Unidad responsable',
            'fecha_documento': '',
            'fuente': 'interna',
            'licencia_uso': 'interna',
            'version': '1',
            'reemplaza_a': '',
            'estado': 'vigente',
            'palabras_clave': 'operación, seguridad',
            'orden': '1',
            'activo': True,
            'visibilidad': 'publica',
            'descargar': False,
            'seguridad_verificada': True,
            'autorizacion_tamano': False,
        }

    def test_los_errores_de_gobierno_se_muestran_en_sus_campos(self):
        datos = {**self.datos, 'descripcion': '', 'seguridad_verificada': False}

        respuesta = self.client.post(reverse('admin:recursos_recurso_add'), datos)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Describe el contenido')
        self.assertContains(respuesta, 'La revisión de seguridad es obligatoria')
        self.assertFalse(Recurso.objects.exists())

    def test_el_formulario_permite_crear_y_editar_un_recurso(self):
        respuesta = self.client.post(reverse('admin:recursos_recurso_add'), self.datos)
        self.assertEqual(respuesta.status_code, 302)
        recurso = Recurso.objects.get()
        self.assertEqual(recurso.unidad, self.unidad)

        datos_editados = {**self.datos, 'nombre': 'Manual de operación actualizado'}
        respuesta = self.client.post(
            reverse('admin:recursos_recurso_change', args=[recurso.pk]),
            datos_editados,
        )
        self.assertEqual(respuesta.status_code, 302)
        recurso.refresh_from_db()
        self.assertEqual(recurso.nombre, 'Manual de operación actualizado')

    def test_el_inline_de_unidad_muestra_los_campos_obligatorios(self):
        Recurso.objects.create(
            unidad=self.unidad,
            nombre='Procedimiento visible en el inline',
            descripcion='Documento revisado para administrar desde la unidad.',
            url='https://example.test/procedimiento.pdf',
            seguridad_verificada=True,
        )

        respuesta = self.client.get(
            reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'id_recursos-0-descripcion')
        self.assertContains(respuesta, 'id_recursos-0-seguridad_verificada')


class EquiposAdminTests(SimpleTestCase):
    def test_equipos_fisicos_usan_su_modulo_de_administracion(self):
        for modelo in (CategoriaEquipo, EquiposServicios, UnidadEquipo):
            with self.subTest(modelo=modelo.__name__):
                registro = admin.site._registry[modelo]
                self.assertEqual(
                    registro.__class__.__module__,
                    'apps.recursos.admin.equipos',
                )


class UnidadAdminProtegidaTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-unidad-protegida',
            email='unidad-protegida@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.usuario)
        self.unidad = Unidad.objects.create(
            nombre='Laboratorio que conserva su historial',
            slug='laboratorio-historial-protegido',
            dependencia='laboratorios',
            descripcion='Unidad que debe desactivarse en lugar de eliminarse.',
            fecha_inicio=date(2026, 1, 1),
        )

    def test_ni_un_superusuario_puede_eliminar_la_unidad_desde_el_admin(self):
        respuesta = self.client.get(
            reverse('admin:directorio_unidades_unidad_delete', args=[self.unidad.pk]),
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Unidad.objects.filter(pk=self.unidad.pk).exists())

    def test_el_admin_no_publica_la_accion_de_eliminacion_masiva(self):
        respuesta = self.client.get(reverse('admin:directorio_unidades_unidad_changelist'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'delete_selected')


class LimiteCategoriasUnidadTests(TestCase):
    """El maximo institucional se aplica sobre la seleccion enviada.

    `Unidad.clean` solo alcanza las categorias ya guardadas, de modo que al
    crear no comprobaba nada y al editar comprobaba la seleccion anterior.
    """

    def formulario(self, datos):
        peticion = RequestFactory().get('/')
        peticion.user = get_user_model().objects.create_superuser(
            username='admin-categorias',
            email='categorias@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        registro = admin.site._registry[Unidad]
        return registro.get_form(peticion)(data=datos)

    def datos_base(self, categorias):
        return {
            'nombre': 'Laboratorio con clasificacion',
            'slug': 'laboratorio-con-clasificacion',
            'descripcion': 'Unidad para comprobar el limite de categorias.',
            'fecha_inicio': '2026-01-01',
            'dependencia': 'laboratorios',
            'estado_catalogo': 'disponible',
            'contacto_email': 'clasificacion@upec.edu.ec',
            'visitas': 0,
            'likes': 0,
            'categorias': [categoria.pk for categoria in categorias],
        }

    def test_el_maximo_se_rechaza_al_crear_desde_el_admin(self):
        excedidas = [
            Categoria.objects.create(nombre=f'Subárea {indice}')
            for indice in range(Unidad.MAXIMO_CATEGORIAS + 1)
        ]

        formulario = self.formulario(self.datos_base(excedidas))

        self.assertFalse(formulario.is_valid())
        self.assertIn('categorias', formulario.errors)
        self.assertFalse(Unidad.objects.filter(slug='laboratorio-con-clasificacion').exists())

    def test_el_maximo_exacto_sigue_siendo_valido(self):
        permitidas = [
            Categoria.objects.create(nombre=f'Subárea {indice}')
            for indice in range(Unidad.MAXIMO_CATEGORIAS)
        ]

        formulario = self.formulario(self.datos_base(permitidas))

        self.assertTrue(formulario.is_valid(), formulario.errors)
        unidad = formulario.save()
        self.assertEqual(unidad.categorias.count(), Unidad.MAXIMO_CATEGORIAS)


class FabricacionAdminTests(SimpleTestCase):
    def test_modelos_de_fabricacion_usan_su_modulo_de_administracion(self):
        modelos = (
            FablabService,
            SolicitudFabricacion,
        )

        for modelo in modelos:
            with self.subTest(modelo=modelo.__name__):
                registro = admin.site._registry[modelo]
                self.assertEqual(
                    registro.__class__.__module__,
                    'apps.laboratorios.operacion.admin.fabricacion',
                )


class InventarioAdminTests(SimpleTestCase):
    def test_consumibles_usan_su_modulo_de_administracion(self):
        for modelo in (Consumible, ConsumiblePorEquipo, EntradaInventario):
            with self.subTest(modelo=modelo.__name__):
                registro = admin.site._registry[modelo]
                self.assertEqual(
                    registro.__class__.__module__,
                    'apps.recursos.admin.inventario',
                )


class ReservasAdminTests(SimpleTestCase):
    def test_reservas_y_reportes_usan_su_modulo_de_administracion(self):
        registro = admin.site._registry[Reserva]
        self.assertEqual(
            registro.__class__.__module__,
            'apps.reservas.admin.reservas',
        )

    def test_rutas_de_estadisticas_y_pdf_conservan_sus_nombres(self):
        self.assertEqual(
            reverse('admin:reservas-estadisticas'),
            '/admin/reservas/reserva/estadisticas/',
        )
        self.assertEqual(
            reverse('admin:reservas-descargar-pdf'),
            '/admin/reservas/reserva/descargar_pdf/',
        )


class MovimientoInventarioAdminTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-inventario',
            email='inventario@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.consumible = Consumible.objects.create(
            codigo='INS-PRUEBA',
            nombre='Insumo de prueba',
            stock_total=0,
        )

    def test_registro_rapido_crea_movimiento_y_actualiza_stock(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse('admin:recursos_consumible_changelist'),
            {
                'registrar_movimiento': '1',
                'consumible': self.consumible.pk,
                'tipo': 'ingreso',
                'cantidad': 5,
                'nota': 'Entrada de prueba',
            },
        )

        self.assertRedirects(
            response,
            reverse('admin:recursos_consumible_changelist'),
        )
        self.consumible.refresh_from_db()
        self.assertEqual(self.consumible.stock_total, 5)
        movimiento = EntradaInventario.objects.get(consumible=self.consumible)
        self.assertEqual(movimiento.usuario, self.usuario)


class ExpedienteReservaSoloLecturaTests(TestCase):
    """El administrador consulta; la operacion vive en Gestionar laboratorio.

    Cambiar estado, horario, recursos o cotizacion desde el admin se saltaba la
    maquina de estados, la compuerta documental, las revisiones, el FT02, las
    notificaciones y la auditoria. Estas pruebas fijan que ya no sea posible.
    """

    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(
            username='admin-expediente',
            email='expediente@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.staff)
        self.unidad = Unidad.objects.create(
            nombre='Laboratorio expediente',
            slug='laboratorio-expediente',
            dependencia='laboratorios',
            descripcion='Unidad para validar el admin de consulta.',
            fecha_inicio=date(2026, 1, 1),
        )
        self.reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.staff,
            fecha=date(2026, 11, 3),
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='EQ-EXP',
            equipo_nombre='Equipo expediente',
            estado='pendiente',
        )

    def test_el_estado_y_los_datos_operativos_son_solo_lectura(self):
        registro = admin.site._registry[Reserva]
        solo_lectura = set(registro.get_readonly_fields(None, self.reserva))

        self.assertLessEqual(
            {
                'estado', 'fecha', 'hora_inicio', 'hora_fin', 'responsable_asignado',
                'software_solicitado', 'espacios_solicitados', 'servicios_solicitados',
                'participantes', 'costo_estimado', 'desglose_cotizacion',
            },
            solo_lectura,
        )
        self.assertFalse(registro.has_add_permission(None))
        self.assertFalse(registro.has_delete_permission(None, self.reserva))

    def test_las_acciones_masivas_sin_reglas_ya_no_existen(self):
        registro = admin.site._registry[Reserva]
        respuesta = self.client.get(reverse('admin:reservas_reserva_changelist'))

        self.assertEqual(respuesta.status_code, 200)
        acciones = registro.get_actions(respuesta.wsgi_request)
        self.assertNotIn('confirmar_reservas', acciones)
        self.assertNotIn('cancelar_reservas', acciones)

    def test_un_post_al_formulario_no_altera_el_estado(self):
        url = reverse('admin:reservas_reserva_change', args=[self.reserva.pk])
        pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Abrir en Gestionar laboratorio')

        respuesta = self.client.post(url, {'estado': 'confirmada', '_save': '1'})

        self.reserva.refresh_from_db()
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.reserva.estado, 'pendiente')

    def test_el_ciclo_documental_de_la_guia_no_se_edita_desde_el_admin(self):
        registro = admin.site._registry[GuiaActividadReserva]
        solo_lectura = set(registro.get_readonly_fields(None))

        self.assertLessEqual(
            {'estado_publicacion', 'es_vigente', 'numero_version', 'contenido'},
            solo_lectura,
        )
        self.assertFalse(registro.has_add_permission(None))

    def test_la_planificacion_ft02_no_se_edita_desde_el_admin(self):
        registro = admin.site._registry[PlanificacionPractica]
        solo_lectura = set(registro.get_readonly_fields(None))

        self.assertLessEqual(
            {'estado', 'es_version_vigente', 'reserva', 'guia'},
            solo_lectura,
        )
        self.assertFalse(registro.has_add_permission(None))

    def test_programacion_y_participantes_no_se_editan_desde_el_admin(self):
        for modelo in (ProgramacionReserva, RegistroParticipanteReserva):
            with self.subTest(modelo=modelo.__name__):
                registro = admin.site._registry[modelo]
                campos = {field.name for field in modelo._meta.fields}
                solo_lectura = set(registro.get_readonly_fields(None))

                self.assertLessEqual(campos, solo_lectura)
                self.assertFalse(registro.has_add_permission(None))
                self.assertFalse(registro.has_delete_permission(None))
