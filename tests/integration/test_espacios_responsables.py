from datetime import date, time, timedelta
from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.gestion_unidades.admin.configuracion import EspacioReservableInline, ResponsableUnidadInline
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad


class EspaciosYResponsablesUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de espacios',
            descripcion='Unidad para probar áreas y responsables.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-espacios-prueba',
        )
        cls.usuario = get_user_model().objects.create_user(
            username='responsable.prueba',
            email='responsable@upec.edu.ec',
            first_name='María',
            last_name='Técnica',
        )

    def test_espacio_tiene_codigo_unico_por_unidad_y_datos_publicos(self):
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad,
            codigo='AREA-IMP3D',
            nombre='Área de impresión 3D',
            tipo='area',
            descripcion_publica='Fabricación aditiva supervisada.',
            ubicacion='Zona norte',
            capacidad=4,
            caracteristicas='Dos puestos de impresión.',
            instrucciones_uso='Requiere inducción.',
        )

        self.assertEqual(str(espacio), f'Área de impresión 3D · {self.unidad.nombre}')
        self.assertTrue(espacio.activo)
        self.assertTrue(espacio.reservable)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EspacioReservable.objects.create(
                unidad=self.unidad,
                codigo='AREA-IMP3D',
                nombre='Código repetido',
            )

    def test_responsable_admite_usuario_o_contacto_institucional(self):
        vinculado = ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=self.usuario,
            rol='responsable_tecnico',
            foto_referencial='img/ott/perfil_3.png',
        )
        self.assertEqual(vinculado.nombre_publico, 'María Técnica')
        self.assertEqual(vinculado.email_publico, 'responsable@upec.edu.ec')
        self.assertEqual(vinculado.iniciales, 'MT')
        self.assertIn('/static/img/ott/perfil_3.png', vinculado.foto_publica_url)

        self.usuario.profile.telefono = '06 2980302 ext. 2800'
        self.usuario.profile.save(update_fields=['telefono'])
        self.assertEqual(vinculado.telefono_publico, '06 2980302 ext. 2800')

        institucional = ResponsableUnidad(
            unidad=self.unidad,
            nombre='Coordinación del laboratorio',
            rol='coordinacion',
            email='laboratorio@upec.edu.ec',
        )
        institucional.full_clean()
        self.assertFalse(institucional.recibe_reservas)

        institucional.recibe_reservas = True
        with self.assertRaises(ValidationError):
            institucional.full_clean()

        incompleto = ResponsableUnidad(unidad=self.unidad, rol='soporte')
        with self.assertRaises(ValidationError):
            incompleto.full_clean()

    def test_una_cuenta_no_se_duplica_en_el_mismo_laboratorio(self):
        ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=self.usuario,
            rol='laboratorista',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ResponsableUnidad.objects.create(
                unidad=self.unidad,
                usuario=self.usuario,
                rol='soporte',
            )

    def test_reserva_relaciona_espacios_y_responsable(self):
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad,
            codigo='EST-01',
            nombre='Estación 1',
            tipo='estacion',
        )
        responsable = ResponsableUnidad.objects.create(
            unidad=self.unidad,
            nombre='Técnico de turno',
            rol='tecnico',
            email='turno@upec.edu.ec',
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario,
            responsable_asignado=responsable,
            fecha=date.today() + timedelta(days=3),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            equipo_codigo='ESPACIO',
            equipo_nombre='Estación 1',
        )
        reserva.espacios_solicitados.add(espacio)

        self.assertEqual(reserva.responsable_asignado, responsable)
        self.assertEqual(list(reserva.espacios_solicitados.all()), [espacio])

    def test_administracion_expone_espacios_responsables_y_tutoriales(self):
        self.assertIn(EspacioReservable, admin.site._registry)
        self.assertIn(ResponsableUnidad, admin.site._registry)

        unidad_admin = admin.site._registry[Unidad]
        modelos_inline = {inline.model for inline in unidad_admin.inlines}
        self.assertIn(EspacioReservableInline.model, modelos_inline)
        self.assertIn(ResponsableUnidadInline.model, modelos_inline)

        configuracion_inline = unidad_admin.inlines[0]
        campos_configuracion = {
            campo
            for _titulo, opciones in configuracion_inline.fieldsets
            for campo in opciones['fields']
        }
        self.assertTrue({
            'tutorial_recursos_url', 'tutorial_servicios_url',
        }.issubset(campos_configuracion))

        reserva_admin = admin.site._registry[Reserva]
        self.assertIn('espacios_solicitados', reserva_admin.filter_horizontal)
        self.assertIn('responsable_asignado', reserva_admin.raw_id_fields)


@override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
class DatosPruebaFablabEspaciosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Manufactura Digital y Prototipado',
            descripcion='FabLab de prueba.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-fabricacion-digital-prototipado',
        )

    def test_comando_carga_areas_responsables_y_catalogo_publico_idempotente(self):
        salida = StringIO()
        opciones = {
            'unidad': self.unidad.slug,
            'confirmar_datos_demo': True,
            'stdout': salida,
        }
        call_command('cargar_pruebas_fablab', **opciones)
        call_command('cargar_pruebas_fablab', **opciones)

        espacios = EspacioReservable.objects.filter(unidad=self.unidad)
        responsables = ResponsableUnidad.objects.filter(unidad=self.unidad)
        self.assertEqual(espacios.count(), 7)
        self.assertEqual(responsables.count(), 2)
        self.assertTrue(all(espacio.descripcion_publica for espacio in espacios))
        self.assertTrue(all(espacio.mobiliario_incluido for espacio in espacios))
        self.assertEqual(
            espacios.filter(politica_reserva='tecnico').count(),
            6,
        )
        self.assertEqual(
            espacios.filter(
                politica_reserva='general',
                equipos_asociados__isnull=True,
            ).distinct().count(),
            1,
        )
        self.assertTrue(all(espacio.caracteristicas for espacio in espacios))
        self.assertTrue(all(espacio.instrucciones_uso for espacio in espacios))
        self.assertTrue(all(not responsable.recibe_reservas for responsable in responsables))
        self.assertTrue(all(responsable.usuario_id is None for responsable in responsables))

        equipos = EquiposServicios.objects.filter(codigo__startswith='FAB-EQ-')
        # Ocho equipos principales mas dos auxiliares: el secador de filamento y
        # la estacion de lavado y curado.
        self.assertEqual(equipos.count(), 10)
        self.assertEqual(equipos.filter(rol='auxiliar').count(), 2)
        self.assertTrue(all(equipo.caracteristicas_publicas for equipo in equipos))
        self.assertTrue(all(equipo.uso_publico for equipo in equipos))
        self.assertTrue(all(equipo.instrucciones_publicas for equipo in equipos))

        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        self.assertEqual(configuracion.tutorial_recursos_url, '')
        self.assertEqual(configuracion.tutorial_servicios_url, '')


@override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
class UsuariosPruebaGestionLaboratorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.principal = User.objects.create_user(
            username='principal.existente',
            password='clave-principal',
            first_name='Principal',
            last_name='Existente',
        )
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de roles de prueba',
            descripcion='Valida perfiles operativos.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-roles-prueba',
            administrador=cls.principal,
        )

    def test_comando_crea_roles_sin_reemplazar_al_principal_y_es_idempotente(self):
        salida = StringIO()
        for _ in range(2):
            call_command(
                'crear_usuarios_prueba_gestion',
                unidad=self.unidad.slug,
                password='PruebaCITT2026!',
                stdout=salida,
            )

        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.administrador, self.principal)
        User = get_user_model()
        coordinador = User.objects.get(username='demo.coordinador.fablab')
        laboratorista = User.objects.get(username='demo.laboratorista.fablab')
        solicitante = User.objects.get(username='demo.solicitante.fablab')
        self.assertTrue(coordinador.check_password('PruebaCITT2026!'))
        self.assertTrue(laboratorista.check_password('PruebaCITT2026!'))
        self.assertTrue(solicitante.check_password('PruebaCITT2026!'))
        self.assertEqual(
            ResponsableUnidad.objects.filter(
                unidad=self.unidad,
                usuario__in=[self.principal, coordinador, laboratorista],
            ).count(),
            3,
        )
        self.assertEqual(
            sum(
                responsable.es_administrador_principal
                for responsable in ResponsableUnidad.objects.filter(unidad=self.unidad)
            ),
            1,
        )

        permisos_principal = permisos_operativos_unidad(self.principal, self.unidad)
        permisos_coordinador = permisos_operativos_unidad(coordinador, self.unidad)
        permisos_laboratorista = permisos_operativos_unidad(laboratorista, self.unidad)
        permisos_solicitante = permisos_operativos_unidad(solicitante, self.unidad)
        self.assertTrue(all(permisos_principal.values()))
        # La coordinación administra su unidad completa: no es una delegación parcial. Lo que no puede es nombrar
        # otra coordinación (test_acceso_admin_unidades.test_coordinacion_asigna_operadores_solo_en_su_unidad).
        self.assertTrue(all(permisos_coordinador.values()))
        self.assertTrue(permisos_laboratorista['reservas'])
        self.assertTrue(permisos_laboratorista['reportes'])
        self.assertFalse(permisos_laboratorista['finanzas'])
        self.assertFalse(permisos_laboratorista['agenda'])
        self.assertFalse(permisos_laboratorista['configuracion'])
        self.assertFalse(any(permisos_solicitante.values()))
