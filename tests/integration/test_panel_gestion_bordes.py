"""Consultas constantes al crecer las relaciones de la pestaña seleccionada."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration import test_panel_gestion_unidad as fixtures


class CatalogosRelacionadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PanelGestionUnidadTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.coordinador)

    def agregar_recursos(self, desde, cantidad):
        for indice in range(desde, desde + cantidad):
            catalogo = EquiposServicios.objects.create(
                codigo=f'BORDE-{indice}', nombre=f'Equipo borde {indice}',
            )
            equipo = UnidadEquipo.objects.create(
                equipo=catalogo, laboratorio=self.unidad, codigo_unidad=f'FISICO-{indice}',
            )
            espacio = EspacioReservable.objects.create(
                unidad=self.unidad, codigo=f'ESP-{indice}', nombre=f'Espacio borde {indice}', capacidad=4,
            )
            programa = SoftwareDisponible.objects.create(
                unidad=self.unidad, nombre=f'Programa borde {indice}',
                licencias_totales=2, licencias_disponibles=2,
            )
            espacio.equipos_asociados.add(equipo)
            programa.equipos_instalados.add(equipo)

    def test_espacios_no_consulta_por_cada_equipo_y_programa_asociado(self):
        self.comprobar_crecimiento('espacios')

    def test_software_no_consulta_por_cada_equipo_instalado(self):
        self.comprobar_crecimiento('software')

    def comprobar_crecimiento(self, modo):
        self.agregar_recursos(0, 1)
        parametros = {'view': 'recursos', 'modo_recursos': modo, 'fragment': '1'}
        self.client.get(self.url, parametros)
        with CaptureQueriesContext(connection) as antes:
            response = self.client.get(self.url, parametros)
        self.agregar_recursos(1, 18)
        with CaptureQueriesContext(connection) as despues:
            ampliada = self.client.get(self.url, parametros)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ampliada.status_code, 200)
        self.assertEqual(len(despues), len(antes), (modo, len(antes), len(despues)))
        self.assertContains(ampliada, 'Equipo borde 18')
        self.assertContains(ampliada, 'Programa borde 18' if modo == 'software' else 'Espacio borde 18')
        self.assertContains(ampliada, f'data-agenda-operation-form="{"espacio" if modo == "espacios" else "software"}"')
        self.assertNotContains(ampliada, 'data-agenda-operation-form="equipo"')

    def test_configuracion_no_consulta_autorizacion_por_cada_responsable(self):
        self.responsable_unidad.rol = 'coordinacion'
        self.responsable_unidad.save(update_fields=['rol'])
        self.client.force_login(self.responsable)
        parametros = {'view': 'configuracion', 'fragment': '1'}
        self.client.get(self.url, parametros)
        with CaptureQueriesContext(connection) as antes:
            response = self.client.get(self.url, parametros)
        cuentas = get_user_model().objects.bulk_create([
            get_user_model()(username=f'responsable-borde-{indice}', first_name=f'Persona borde {indice}')
            for indice in range(40)
        ])
        ResponsableUnidad.objects.bulk_create([
            ResponsableUnidad(unidad=self.unidad, usuario=cuenta, rol='tecnico') for cuenta in cuentas
        ])
        with CaptureQueriesContext(connection) as despues:
            ampliada = self.client.get(self.url, parametros)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ampliada.status_code, 200)
        self.assertEqual(len(despues), len(antes), (len(antes), len(despues)))
        self.assertContains(ampliada, 'Persona borde 39')
        self.assertTrue(all(
            registro.puede_editar_personal
            for registro in ampliada.context['responsables'] if registro.usuario_id in {u.pk for u in cuentas}
        ))


class InstantaneaOperativaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PanelGestionUnidadTests.setUpTestData.__func__(cls)

    def setUp(self):
        from django.urls import reverse
        self.client.force_login(self.coordinador)
        self.operacion_url = reverse('gestion_operacion_accion', args=[self.unidad.slug])

    def test_id_invalido_devuelve_error_controlado_sin_escrituras(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        for valor in ('no-numero', '1.5', '-1', '0', '9' * 100):
            with self.subTest(registro_id=valor):
                response = self.client.post(self.operacion_url, {
                    'modulo': 'recursos', 'entidad': 'espacio', 'registro_id': valor,
                })
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()['success'])
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertFalse(EspacioReservable.objects.exists())

    def test_editar_espacio_audita_su_estado_previo_y_no_equipo_ajeno_con_mismo_id(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad, codigo='ESP-PROPIO', nombre='Área original', capacidad=4,
        )
        catalogo = EquiposServicios.objects.create(codigo='AJENO-AUD', nombre='Equipo ajeno')
        equipo_ajeno = UnidadEquipo.objects.create(
            pk=espacio.pk, laboratorio=self.otra_unidad, equipo=catalogo,
            codigo_unidad='CONFIDENCIAL-AJENO', custodio='Custodio de otra unidad',
        )
        response = self.client.post(self.operacion_url, {
            'modulo': ' recursos ', 'entidad': 'espacio', 'registro_id': espacio.pk,
            'nombre': 'Área actualizada', 'capacidad': 5, 'activo': 'on', 'reservable': 'on',
        })
        self.assertEqual(response.status_code, 200, response.content)
        evento = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad)
        self.assertEqual(evento.datos_anteriores['nombre'], 'Área original')
        self.assertEqual(evento.datos_anteriores['codigo'], 'ESP-PROPIO')
        self.assertNotIn('custodio', evento.datos_anteriores)
        self.assertNotIn('CONFIDENCIAL-AJENO', str(evento.datos_anteriores))
        equipo_ajeno.refresh_from_db()
        self.assertEqual(equipo_ajeno.codigo_unidad, 'CONFIDENCIAL-AJENO')

    def test_intentar_editar_registro_de_otra_unidad_no_genera_auditoria(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        espacio = EspacioReservable.objects.create(
            unidad=self.otra_unidad, codigo='ESP-AJENO', nombre='Área ajena', capacidad=4,
        )
        response = self.client.post(self.operacion_url, {
            'modulo': 'recursos', 'entidad': 'espacio', 'registro_id': espacio.pk,
            'nombre': 'Intrusión', 'capacidad': 5, 'activo': 'on',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        espacio.refresh_from_db()
        self.assertEqual(espacio.nombre, 'Área ajena')


class EdicionPersonalPorLoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PanelGestionUnidadTests.setUpTestData.__func__(cls)
        cls.responsable_unidad.rol = 'coordinacion'
        cls.responsable_unidad.save(update_fields=['rol'])
        cls.superusuario = get_user_model().objects.create_user(
            username='supervisor-borde', is_superuser=True, is_staff=True,
        )
        cls.tecnico = get_user_model().objects.create_user(username='tecnico-borde')
        cls.objetivos = [
            ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.coordinador, rol='coordinacion'),
            cls.responsable_unidad,
            ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.superusuario, rol='tecnico'),
            ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.tecnico, rol='tecnico'),
            ResponsableUnidad.objects.create(unidad=cls.unidad, nombre='Contacto sin cuenta'),
            ResponsableUnidad.objects.create(unidad=cls.unidad, nombre='Contacto inactivo', activo=False),
            ResponsableUnidad.objects.create(unidad=cls.otra_unidad, nombre='Contacto ajeno'),
        ]

    def test_lote_y_operacion_individual_conservan_politica_y_alcance(self):
        from copy import copy
        from django.contrib.auth.models import AnonymousUser
        from apps.gestion_unidades.presentation.permisos import puede_editar_personal_unidad, permisos_edicion_personal_unidad
        inactivo = copy(self.coordinador)
        inactivo.is_active = False
        for actor, esperado in (
            (self.coordinador, [True, True, True, True, True, True, False]),
            (self.superusuario, [True, True, True, True, True, True, False]),
            (self.responsable, [False, False, False, True, True, True, False]),
            (self.tecnico, [False] * 7),
            (self.usuario_ajeno, [False] * 7),
            (inactivo, [False] * 7),
            (AnonymousUser(), [False] * 7),
        ):
            with self.subTest(actor=actor):
                permisos = permisos_edicion_personal_unidad(actor, self.unidad, self.objetivos)
                self.assertEqual([permisos[r.pk] for r in self.objetivos], esperado)
                self.assertEqual([
                    puede_editar_personal_unidad(actor, self.unidad, r) for r in self.objetivos
                ], esperado)

    def test_lote_con_cuarenta_contactos_consulta_autorizacion_una_vez(self):
        from apps.gestion_unidades.presentation.permisos import permisos_edicion_personal_unidad
        ResponsableUnidad.objects.bulk_create([
            ResponsableUnidad(unidad=self.unidad, nombre=f'Contacto escala {i}') for i in range(40)
        ])
        responsables = list(ResponsableUnidad.objects.filter(unidad=self.unidad).select_related('usuario'))
        with self.assertNumQueries(1):
            permisos = permisos_edicion_personal_unidad(self.responsable, self.unidad, responsables)
        self.assertEqual(len(permisos), len(responsables))
        self.assertFalse(permisos[self.responsable_unidad.pk])

    def test_coordinacion_de_otra_unidad_no_autoriza_lote(self):
        from apps.gestion_unidades.presentation.permisos import permisos_edicion_personal_unidad
        propio = self.objetivos[-1]
        self.assertEqual(
            permisos_edicion_personal_unidad(self.responsable, self.otra_unidad, [propio]),
            {propio.pk: False},
        )
