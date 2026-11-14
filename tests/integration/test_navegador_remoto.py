from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation import navegador_remoto as nr
from apps.recursos.presentation import sitios_externos
from apps.recursos.models.recursos import Recurso, SesionNavegador
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests


class DockerSimulado:
    def __init__(self, contenedores=''):
        self.ordenes, self.contenedores, self.politica = [], contenedores, None

    def __call__(self, *args, capturar=False, timeout=None):
        args = [str(a) for a in args]
        self.ordenes.append(args)
        if args[0] == 'cp':
            self.politica = json.loads((Path(args[1]) / 'managed' / 'citt.json').read_text(encoding='utf-8'))
        if args[0] == 'ps':
            return self.contenedores
        return ''

    def orden(self, inicio):
        return next(o for o in self.ordenes if o[:len(inicio)] == inicio)


@override_settings(MICROPROYECTOS_DOMINIO='localhost', MICROPROYECTOS_ESQUEMA='http',
                   MICROPROYECTOS_PUERTO_PUBLICO='19000', NAVEGADOR_REMOTO_MAX_SESIONES=2)
class NavegadorRemotoTests(EditorRecursosUnidadTests):
    def setUp(self):
        super().setUp()
        self.recurso = Recurso.objects.create(
            unidad=self.unidad, carpeta=self.carpeta, nombre='LabXchange', descripcion='Laboratorio virtual',
            url='https://www.labxchange.org/library/', seguridad_verificada=True, navegador_remoto=True)
        self.url = reverse('recurso_unidad_navegador', args=[self.recurso.pk])
        crear = get_user_model().objects.create_user
        self.ana, self.luis, self.eva = (crear(n, password='clave') for n in ('ana', 'luis', 'eva'))

    def test_cupo_limitado_y_una_sesion_por_persona(self):
        primera = nr.abrir_sesion(self.recurso, self.ana)
        self.assertEqual(nr.abrir_sesion(self.recurso, self.ana), primera)
        nr.abrir_sesion(self.recurso, self.luis)
        with self.assertRaises(nr.LimiteAlcanzado):
            nr.abrir_sesion(self.recurso, self.eva)
        # Abrir otro sitio libera la sesión anterior de la misma persona.
        otro = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta, nombre='Otro', descripcion='x',
                                      url='https://otro.org/', seguridad_verificada=True, navegador_remoto=True)
        self.assertNotEqual(nr.abrir_sesion(otro, self.ana), primera)
        primera.refresh_from_db()
        self.assertLessEqual(primera.expira, timezone.now())

    def test_solo_con_la_opcion_activa_y_el_dominio_configurado(self):
        self.assertTrue(nr.disponible(self.recurso))
        Recurso.objects.filter(pk=self.recurso.pk).update(navegador_remoto=False)
        self.assertFalse(nr.disponible(Recurso.objects.get(pk=self.recurso.pk)))
        with override_settings(MICROPROYECTOS_DOMINIO=''):
            self.assertFalse(nr.disponible(self.recurso))

    def test_ruta_exige_sesion_y_gestiona_el_ciclo(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)
        self.client.force_login(self.ana)
        abierta = self.client.post(self.url, {'accion': 'abrir'}).json()
        self.assertEqual(abierta['estado'], 'pendiente')
        sesion = SesionNavegador.objects.get(token=abierta['token'])
        SesionNavegador.objects.filter(pk=sesion.pk).update(estado='activa')
        activa = self.client.post(self.url, {'accion': 'actividad', 'token': sesion.token}).json()
        self.assertEqual(activa['url'], f'http://navegador-{sesion.token}.localhost:19000/')
        # El token de otra persona no sirve.
        self.client.force_login(self.luis)
        self.assertEqual(self.client.post(self.url, {'accion': 'cerrar', 'token': sesion.token}).status_code, 404)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.post(self.url, {'accion': 'cerrar', 'token': sesion.token}).json()['estado'], 'terminada')
        nr.abrir_sesion(self.recurso, self.luis)
        nr.abrir_sesion(self.recurso, self.eva)
        self.assertEqual(self.client.post(self.url, {'accion': 'abrir'}).status_code, 429)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_visor_ofrece_el_navegador_solo_si_el_sitio_lo_prohibe(self):
        visor = reverse('recurso_unidad', args=[self.recurso.pk]) + '?visor=1'
        self.client.force_login(self.ana)
        with patch.object(sitios_externos, 'permite_incrustar', return_value=False):
            pagina = self.client.get(visor)
        self.assertContains(pagina, f'data-url="{self.url}"')
        self.assertContains(pagina, 'navegador_remoto.js')
        self.assertContains(pagina, 'Abrir sitio en una pestaña nueva')
        with patch.object(sitios_externos, 'permite_incrustar', return_value=True):
            self.assertNotContains(self.client.get(visor), 'navegadorRemoto')
        self.client.logout()
        with patch.object(sitios_externos, 'permite_incrustar', return_value=False):
            self.assertContains(self.client.get(visor), 'Inicie sesión en la plataforma')

    def test_el_servicio_abre_chromium_restringido_al_dominio(self):
        sesion = nr.abrir_sesion(self.recurso, self.ana)
        docker = DockerSimulado()
        self.assertEqual([s.estado for s in nr.atender_sesiones(docker)], ['activa'])
        nombre = f'citt-navegador-{sesion.token}'
        creado = docker.orden(['create', '--name', nombre])
        self.assertIn('CHROME_CLI=--app=https://www.labxchange.org/library/', creado)
        self.assertIn('--memory', creado)
        self.assertNotIn('-p', creado)
        self.assertEqual(docker.orden(['cp'])[-1], f'{nombre}:/etc/chromium/')
        self.assertEqual(docker.politica['URLBlocklist'], ['*'])
        self.assertIn('labxchange.org', docker.politica['URLAllowlist'])
        self.assertEqual(docker.politica['DeveloperToolsAvailability'], 2)
        self.assertLess(docker.ordenes.index(docker.orden(['cp'])), docker.ordenes.index(['start', nombre]))
        self.assertIn(f'Host: navegador-{sesion.token}.localhost', docker.orden(['exec']))

    def test_cierra_vencidas_abandonadas_y_huerfanas(self):
        vencida = nr.abrir_sesion(self.recurso, self.ana)
        abandonada = nr.abrir_sesion(self.recurso, self.luis)
        SesionNavegador.objects.filter(pk=vencida.pk).update(estado='activa', expira=timezone.now())
        SesionNavegador.objects.filter(pk=abandonada.pk).update(
            estado='activa', ultima_actividad=timezone.now() - timedelta(minutes=10))
        docker = DockerSimulado(contenedores='citt-navegador-perdido\ncitt-microproyecto-7')
        nr.atender_sesiones(docker)
        for sesion in (vencida, abandonada):
            sesion.refresh_from_db()
            self.assertEqual(sesion.estado, 'terminada')
            self.assertIn(['rm', '-f', f'citt-navegador-{sesion.token}'], docker.ordenes)
        self.assertIn(['rm', '-f', 'citt-navegador-perdido'], docker.ordenes)
        self.assertNotIn(['rm', '-f', 'citt-microproyecto-7'], docker.ordenes)

    def test_un_fallo_libera_la_sesion_y_lo_registra(self):
        sesion = nr.abrir_sesion(self.recurso, self.ana)

        def falla(*args, **kwargs):
            if args[0] == 'create':
                raise RuntimeError('sin memoria')
            return ''
        nr.atender_sesiones(falla)
        sesion.refresh_from_db()
        self.assertEqual((sesion.estado, sesion.detalle), ('error', 'sin memoria'))
        self.assertEqual(nr.estado(sesion)['estado'], 'error')
