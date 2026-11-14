"""Tres tipos de usuario, y lo que cada uno alcanza.

El superusuario administra toda la plataforma. El personal de una unidad la
gestiona y solo a ella. El resto de usuarios ve y gestiona únicamente sus
propias reservas. Quien no inicia sesión lee la ficha pública y puede explorar
la disponibilidad, pero no envía nada ni entra a ninguna superficie privada.
"""

import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integraciones import modelos as modelos
from apps.gestion_unidades.presentation.permisos import MODULOS_OPERATIVOS, permisos_operativos_unidad, puede_administrar_personal_unidad, puede_gestionar_unidad, unidades_gestionables
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar, verificar_pertenencia


def _dia_habil(referencia):
    fecha = referencia
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha


class TiposDeUsuarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.superusuario = Usuario.objects.create_superuser(
            username='superadmin', email='superadmin@upec.edu.ec', password='Clave-Super-2026'
        )
        cls.principal = Usuario.objects.create_user(
            username='principal.ia', email='principal.ia@upec.edu.ec', password='Clave-2026'
        )
        cls.laboratorista = Usuario.objects.create_user(
            username='laboratorista.ia', email='laboratorista.ia@upec.edu.ec', password='Clave-2026'
        )
        cls.personal_ajeno = Usuario.objects.create_user(
            username='personal.otra', email='personal.otra@upec.edu.ec', password='Clave-2026'
        )
        cls.docente = Usuario.objects.create_user(
            username='docente.comun', email='docente.comun@upec.edu.ec', password='Clave-2026'
        )
        cls.estudiante = Usuario.objects.create_user(
            username='estudiante.comun', email='estudiante.comun@upec.edu.ec', password='Clave-2026'
        )
        identificar(cls.docente, tipo_usuario='docente')
        verificar_pertenencia(cls.docente)
        identificar(cls.estudiante, tipo_usuario='estudiante')
        # El personal también usa la plataforma con sus datos al día: la
        # compuerta de perfil no distingue por quién se pregunta.
        for persona in (cls.principal, cls.laboratorista, cls.personal_ajeno):
            identificar(persona, tipo_usuario='administrativo')

        # Una unidad completa, cargada como la usaría la Universidad.
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio IA y Ciencia de Datos',
            descripcion='Unidad de prueba.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-inteligencia-artificial-ciencia-datos',
            administrador=cls.principal,
        )
        call_command('cargar_laboratorios_institucionales', laboratorio='ia')
        cls.otra = Unidad.objects.create(
            nombre='Laboratorio Vecino',
            descripcion='Otra unidad, con su propio personal.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-vecino',
        )
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.laboratorista, nombre='Laboratorista IA',
            rol='laboratorista', email='laboratorista.ia@upec.edu.ec', recibe_reservas=True,
        )
        ResponsableUnidad.objects.create(
            unidad=cls.otra, usuario=cls.personal_ajeno, nombre='Coordinación vecina',
            rol='coordinacion', email='personal.otra@upec.edu.ec', recibe_reservas=True,
        )

    def _reservar_sala(self, usuario):
        """Una reserva real de solo espacio, enviada por el asistente."""
        self.client.force_login(usuario)
        sala = EspacioReservable.objects.get(codigo='IA-SALA-ANALITICA')
        fecha = _dia_habil(timezone.localdate() + timedelta(days=3))
        respuesta = self.client.post(reverse('crear_reserva'), {
            'unidad_id': self.unidad.pk,
            'fecha_inicio': f'{fecha.isoformat()}T09:00',
            'fecha_fin': f'{fecha.isoformat()}T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito': 'Investigación',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'proyecto_investigacion',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Prueba de tipos de usuario',
            'descripcion_proyecto': 'Reserva de una sala para comprobar quién la ve.',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'tipo_solicitud': 'recursos',
            'provision_consumibles': 'ninguno',
            'unidades_seleccionadas': '[]',
            'espacios_solicitados': [str(sala.pk)],
            'incluye_espacio': '1',
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.client.logout()
        return Reserva.objects.get(pk=respuesta.json()['reserva_id'])

    # ------------------------------------------------------------ superusuario
    def test_el_superusuario_gestiona_todas_las_unidades(self):
        self.assertEqual(
            unidades_gestionables(self.superusuario).count(), Unidad.objects.count()
        )
        self.assertTrue(all(permisos_operativos_unidad(self.superusuario, self.otra).values()))
        self.client.force_login(self.superusuario)
        for unidad in (self.unidad, self.otra):
            with self.subTest(unidad=unidad.slug):
                respuesta = self.client.get(reverse('gestion_unidad', args=[unidad.slug]))
                self.assertEqual(respuesta.status_code, 200)

    # ------------------------------------------------------ personal de unidad
    def test_el_personal_solo_gestiona_su_unidad(self):
        self.client.force_login(self.laboratorista)
        propia = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]))
        ajena = self.client.get(reverse('gestion_unidad', args=[self.otra.slug]))
        self.assertEqual(propia.status_code, 200)
        self.assertEqual(ajena.status_code, 403)
        # La ficha pública ofrece «Gestionar» solo en la unidad que atiende.
        self.assertContains(self.client.get(self.unidad.get_absolute_url()), 'gestionLaboratorioModal')
        self.assertNotContains(self.client.get(self.otra.get_absolute_url()), 'gestionLaboratorioModal')
        # Y el administrador de Django no es una puerta para el personal.
        administrador = self.client.get('/admin/')
        self.assertEqual(administrador.status_code, 302)
        self.assertIn('/admin/login/', administrador['Location'])

    def test_el_administrador_principal_es_quien_cambia_al_personal(self):
        self.assertTrue(puede_administrar_personal_unidad(self.principal, self.unidad))
        self.assertTrue(all(permisos_operativos_unidad(self.principal, self.unidad).values()))
        # Un laboratorista atiende con su matriz, pero no cambia al personal.
        self.assertTrue(puede_gestionar_unidad(self.laboratorista, self.unidad))
        self.assertFalse(puede_administrar_personal_unidad(self.laboratorista, self.unidad))
        self.assertFalse(puede_gestionar_unidad(self.principal, self.otra))

    # --------------------------------------------------------------- usuarios
    def test_un_usuario_solo_ve_sus_propias_reservas(self):
        reserva = self._reservar_sala(self.docente)

        self.client.force_login(self.docente)
        propias = self.client.get(reverse('obtener_reservas_usuario')).json()
        self.assertEqual([r['id'] for r in propias['reservas']], [reserva.pk])
        self.assertEqual(
            self.client.get(reverse('comprobante_reserva', args=[reserva.pk])).status_code, 200
        )

        self.client.force_login(self.estudiante)
        ajenas = self.client.get(reverse('obtener_reservas_usuario')).json()
        self.assertEqual(ajenas['reservas'], [])
        self.assertEqual(
            self.client.get(reverse('comprobante_reserva', args=[reserva.pk])).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse('gestion_unidad', args=[self.unidad.slug])).status_code, 403
        )

    def test_el_comprobante_lo_abre_su_titular_o_el_personal_de_esa_unidad(self):
        reserva = self._reservar_sala(self.docente)
        for usuario, esperado in (
            (self.laboratorista, 200),
            (self.principal, 200),
            (self.superusuario, 200),
            (self.personal_ajeno, 403),
        ):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
                self.assertEqual(respuesta.status_code, esperado)

    # ---------------------------------------------------- sin iniciar sesión
    def test_sin_sesion_lee_ficha_pero_no_reserva_recursos_o_servicios(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Recursos, servicios y visitas internas requieren iniciar sesión')
        self.assertContains(pagina, 'Las visitas externas pueden solicitarse sin cuenta')
        self.assertNotContains(pagina, 'gestionLaboratorioModal')

        envio = self.client.post(reverse('crear_reserva'), {'unidad_id': self.unidad.pk})
        self.assertEqual(envio.status_code, 401)
        for tipo in ('recursos', 'servicio'):
            with self.subTest(tipo=tipo):
                envio = self.client.post(reverse('crear_reserva'), {
                    'unidad_id': self.unidad.pk, 'tipo_solicitud': tipo,
                })
                self.assertEqual(envio.status_code, 401)

        for nombre, argumentos in (
            ('gestion_unidad', [self.unidad.slug]),
            ('lista_guias_practica', [self.unidad.slug]),
            ('comprobante_reserva', [1]),
        ):
            with self.subTest(ruta=nombre):
                respuesta = self.client.get(reverse(nombre, args=argumentos))
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn('/accounts/login/', respuesta['Location'])
        administrador = self.client.get('/admin/')
        self.assertIn('/admin/login/', administrador['Location'])

    def test_sin_sesion_el_catalogo_no_muestra_existencias_ni_precios(self):
        """Las cifras del inventario son internas; el catálogo sí es público."""
        anonimo = self.client.get(self.unidad.get_absolute_url()).content.decode()
        self.assertIn('Marcador para pizarra blanca', anonimo)
        self.assertIn('Disponible', anonimo)
        self.assertNotIn('data-stock="48"', anonimo)
        self.assertNotIn('disponible 48', anonimo)
        self.assertNotIn('$0.90 por unidad', anonimo)

        self.client.force_login(self.estudiante)
        con_sesion = self.client.get(self.unidad.get_absolute_url()).content.decode()
        self.assertIn('data-stock="48"', con_sesion)
        self.assertIn('disponible 48', con_sesion)

    def test_la_agenda_publica_no_revela_quien_reservo(self):
        reserva = self._reservar_sala(self.docente)
        agenda = self.client.get(
            reverse('obtener_ocupacion_laboratorio', args=[self.unidad.pk]),
            {'desde': reserva.fecha.isoformat(), 'hasta': reserva.fecha.isoformat()},
        )
        self.assertEqual(agenda.status_code, 200)
        eventos = [e for e in agenda.json()['eventos'] if e['evento_id'] == f'reserva-{reserva.pk}']
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]['reservado_por'], 'Docente UPEC')
        self.assertNotIn(self.docente.get_full_name() or self.docente.username, json.dumps(eventos))

    # ------------------------------------------------- no hay otros caminos
    def test_no_quedan_otros_caminos_para_gestionar_una_unidad(self):
        for nombre in ('Mentor', 'Integrante', 'CarpetaSubmodulo'):
            with self.subTest(modelo=nombre):
                self.assertFalse(hasattr(modelos, nombre))
        self.assertFalse(hasattr(Unidad, 'mentor'))
        permisos = permisos_operativos_unidad(self.estudiante, self.unidad)
        self.assertEqual(set(permisos), set(MODULOS_OPERATIVOS))
        self.assertFalse(any(permisos.values()))
        self.assertFalse(puede_gestionar_unidad(self.estudiante, self.unidad))
