from io import BytesIO, StringIO
import hashlib
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from apps.recursos.admin.contenido import RecursoInline, SolicitudMicroproyectoAdminMixin
from apps.recursos.presentation import despliegue_microproyectos as dm
from apps.recursos.models.recursos import DespliegueMicroproyecto, Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests

MANAGE = "import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')\n"


def paquete(manage=MANAGE):
    salida = BytesIO()
    with ZipFile(salida, 'w') as z:
        z.writestr('wms/manage.py', manage)
        z.writestr('wms/requirements.txt', 'Django==5.2.17'.encode('utf-16'))
        z.writestr('wms/db.sqlite3', 'datos')
    return SimpleUploadedFile('wms.zip', salida.getvalue())


class DockerSimulado:
    """Registra las órdenes y responde como un Docker sin contenedores previos."""

    def __init__(self, falla_en=None):
        self.ordenes, self.falla_en = [], falla_en

    def __call__(self, *args, capturar=False, timeout=None):
        args = [str(a) for a in args]
        self.ordenes.append(args)
        if self.falla_en and args[0] == self.falla_en:
            raise subprocess.CalledProcessError(1, ['docker', *args])
        if args[:2] == ['inspect', '--format'] and 'Running' in args[2]:
            return 'true'
        if args[0] == 'build':
            self.contexto = Path(args[-1])
            self.configuracion = (self.contexto / 'app' / 'citt_runtime_settings.py').read_text(encoding='utf-8')
            self.requisitos = (self.contexto / 'app' / 'requirements.txt').read_text(encoding='utf-8')
        return ''

    def orden(self, inicio):
        return next(o for o in self.ordenes if o[:len(inicio)] == inicio)


class DespliegueMicroproyectosTests(EditorRecursosUnidadTests):
    def setUp(self):
        super().setUp()
        directorio = TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.enterContext(override_settings(MICROPROYECTOS_DIRECTORIO=directorio.name,
                                            MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=True,
                                            MICROPROYECTOS_DOMINIO='localhost', MICROPROYECTOS_ESQUEMA='http',
                                            MICROPROYECTOS_PUERTO_PASARELA=19000, MICROPROYECTOS_PUERTO_PUBLICO='19000'))
        self.directorio = Path(directorio.name)

    def recurso(self, **extra):
        datos = {'unidad': self.unidad, 'carpeta': self.carpeta, 'nombre': 'WMS', 'descripcion': 'Almacén',
                 'archivo': paquete(), 'tipo_adjunto': 'microproyecto_django', **extra}
        recurso = Recurso.objects.create(**datos)
        recurso.archivo.close()  # Windows no borra el directorio temporal con el ZIP abierto.
        return recurso

    def test_guardar_un_zip_nuevo_lo_pone_en_cola_solo_con_permiso(self):
        inline = RecursoInline(Unidad, admin.site)
        FormSet = inline.get_formset(self.request, self.unidad)
        p = FormSet.get_default_prefix()
        datos = {f'{p}-TOTAL_FORMS': '1', f'{p}-INITIAL_FORMS': '0', f'{p}-0-nombre': 'WMS',
                 f'{p}-0-descripcion': 'Almacén', f'{p}-0-carpeta': str(self.carpeta.pk),
                 f'{p}-0-tipo_adjunto': 'microproyecto_django', f'{p}-0-version': '1', f'{p}-0-estado': 'vigente',
                 f'{p}-0-orden': '0', f'{p}-0-visibilidad': 'publica', f'{p}-0-activo': 'on',
                 f'{p}-0-fuente': 'interna', f'{p}-0-licencia_uso': 'interna',
                 f'{p}-0-microproyecto_dependencias': 'django-unfold==0.91.0'}
        formset = FormSet(datos, {f'{p}-0-archivo': paquete()}, instance=self.unidad)
        self.assertTrue(formset.is_valid(), formset.errors)
        recurso = formset.save()[0]
        self.assertTrue(dm.solicitar_si_corresponde(recurso, self.usuario))
        self.assertIsNone(dm.solicitar_si_corresponde(recurso, self.usuario))
        despliegue = recurso.despliegues.get()
        self.assertEqual((despliegue.estado, despliegue.origen, despliegue.solicitado_por), ('pendiente', 'automatico', self.usuario))
        # Un fallo de esa misma versión se reintenta con el botón, no en cada guardado.
        despliegue.estado = 'error'
        despliegue.save()
        self.assertIsNone(dm.solicitar_si_corresponde(recurso, self.usuario))
        sin_permiso = get_user_model().objects.create_user('coordinacion', password='clave', is_staff=True)
        self.assertIsNone(dm.solicitar_si_corresponde(self.recurso(nombre='Otro'), sin_permiso))
        sin_permiso.user_permissions.add(Permission.objects.get(codename='solicitar_despliegue_microproyecto'))
        sin_permiso = get_user_model().objects.get(pk=sin_permiso.pk)
        self.assertTrue(dm.solicitar_si_corresponde(Recurso.objects.get(nombre='Otro'), sin_permiso))

    def test_el_mixin_del_admin_solicita_tras_guardar(self):
        class Base:
            def save_model(self, request, obj, form, change):
                obj.save()

        class Admin(SolicitudMicroproyectoAdminMixin, Base):
            pass

        from django.contrib.messages.storage.fallback import FallbackStorage
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)
        recurso = self.recurso()
        Admin().save_model(self.request, recurso, None, False)
        recurso.archivo.close()
        self.assertEqual(recurso.despliegues.get().origen, 'automatico')

    def test_no_se_solicita_si_no_es_publico_o_falta_el_dominio(self):
        privado = self.recurso(visibilidad='restringida', seguridad_verificada=True)
        with self.assertRaisesMessage(ValidationError, 'recursos públicos'):
            dm.solicitar(privado, self.usuario, 'manual')
        with override_settings(MICROPROYECTOS_DOMINIO=''):
            self.assertIn('MICROPROYECTOS_DOMINIO', dm.motivo_no_desplegable(self.recurso(nombre='Sin dominio')))

    def test_boton_del_admin_registra_la_solicitud_y_consulta_el_estado(self):
        recurso = self.recurso()
        url = reverse('admin:recursos_recurso_microproyecto', args=[recurso.pk])
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).json()['estado'], 'sin_solicitud')
        respuesta = self.client.post(url)
        self.assertEqual(respuesta.json()['estado'], 'pendiente')
        self.client.post(url)
        self.assertEqual(recurso.despliegues.get().origen, 'manual')
        pagina = self.client.get(reverse('admin:recursos_recurso_change', args=[recurso.pk]))
        self.assertContains(pagina, f'data-microproyecto-url="{url}"')
        self.assertContains(pagina, 'En cola para ponerse en marcha.')
        self.assertContains(pagina, 'microproyecto_dependencias')
        personal = get_user_model().objects.create_user('personal', password='clave', is_staff=True)
        personal.user_permissions.add(Permission.objects.get(codename='view_recurso'))
        self.client.force_login(personal)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(recurso.despliegues.count(), 1)

    def test_el_servicio_construye_aislado_y_publica_por_la_pasarela(self):
        recurso = self.recurso(microproyecto_dependencias='django-unfold==0.91.0')
        dm.solicitar(recurso, self.usuario, 'manual')
        docker = DockerSimulado()
        despliegue = dm.atender_siguiente(docker)
        self.assertEqual(despliegue.estado, 'completado', despliegue.detalle)
        recurso.refresh_from_db()
        self.assertEqual(recurso.microproyecto_url, f'http://microproyecto-{recurso.pk}.localhost:19000/')
        self.assertEqual(recurso.microproyecto_hash, recurso.hash_sha256)
        self.assertIn('from config.settings.local import *', docker.configuracion)
        self.assertIn(f"ALLOWED_HOSTS = ['microproyecto-{recurso.pk}.localhost']", docker.configuracion)
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', docker.configuracion)
        self.assertIn('Django==5.2.17', docker.requisitos)
        self.assertIn('django-unfold==0.91.0', docker.requisitos)
        self.assertFalse(docker.contexto.exists())
        nombre = dm.nombre_contenedor(recurso)
        identificador = f'citt-microproyecto-{recurso.pk}'
        self.assertEqual(docker.orden(['network', 'create'])[-2:], ['--internal', identificador + '-red'])
        aplicacion = docker.orden(['run', '-d', '--name', nombre])
        for bandera in ('--read-only', '--cap-drop', 'no-new-privileges', f'citt.microproyecto={recurso.pk}'):
            self.assertIn(bandera, aplicacion)
        self.assertNotIn('-p', aplicacion)
        self.assertEqual(aplicacion[aplicacion.index('--network-alias') + 1], identificador)
        self.assertIn(f'type=volume,source={identificador}-datos,target=/data', aplicacion)
        pasarela = docker.orden(['run', '-d', '--name', dm.PASARELA])
        self.assertIn('127.0.0.1:19000:8080', pasarela)
        self.assertIn(['network', 'connect', identificador + '-red', dm.PASARELA], docker.ordenes)
        self.assertIn(f'Host: microproyecto-{recurso.pk}.localhost', docker.orden(['exec', dm.PASARELA]))
        self.assertTrue((self.directorio / str(recurso.pk) / 'runtime.env').exists())
        self.assertEqual(dm.estado_visible(recurso)['estado'], 'activo')
        # La dirección directa se comparte solo desde el admin; el portal la muestra en el visor.
        publica = self.client.get(recurso.get_url_compartir())
        self.assertContains(publica, f'<iframe src="{recurso.microproyecto_url}"')
        self.assertNotContains(publica, 'Abrir proyecto')

    def test_https_en_produccion_confia_en_el_proxy(self):
        recurso = self.recurso()
        with override_settings(MICROPROYECTOS_DOMINIO='apps.upec.edu.ec', MICROPROYECTOS_ESQUEMA='https',
                               MICROPROYECTOS_PUERTO_PUBLICO=''):
            self.assertEqual(dm.url_publica(recurso), f'https://microproyecto-{recurso.pk}.apps.upec.edu.ec/')
            configuracion = dm.configuracion_runtime(recurso, 'config.settings')
        self.assertIn("SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')", configuracion)
        self.assertIn(f"CSRF_TRUSTED_ORIGINS = ['https://microproyecto-{recurso.pk}.apps.upec.edu.ec']", configuracion)

    def test_los_fallos_quedan_registrados_con_un_mensaje_util(self):
        recurso = self.recurso()
        dm.solicitar(recurso, self.usuario, 'manual')
        despliegue = dm.atender_siguiente(DockerSimulado(falla_en='build'))
        self.assertEqual(despliegue.estado, 'error')
        self.assertIn('Dependencias adicionales', despliegue.detalle)
        self.assertEqual(dm.estado_visible(recurso)['estado'], 'error')
        sin_modulo = self.recurso(nombre='Sin módulo', archivo=paquete(manage='print(1)'))
        dm.solicitar(sin_modulo, self.usuario, 'manual')
        self.assertIn('DJANGO_SETTINGS_MODULE', dm.atender_siguiente(DockerSimulado()).detalle)
        self.assertIsNone(dm.atender_siguiente(DockerSimulado()))

    def test_una_version_reemplazada_no_se_publica_como_la_nueva(self):
        recurso = self.recurso()
        dm.solicitar(recurso, self.usuario, 'manual')
        Recurso.objects.filter(pk=recurso.pk).update(hash_sha256='otra-version')
        self.assertIn('cambió', dm.atender_siguiente(DockerSimulado()).detalle)

    def test_retira_contenedores_de_recursos_eliminados_u_ocultos(self):
        oculto = self.recurso()
        Recurso.objects.filter(pk=oculto.pk).update(activo=False, microproyecto_url='http://x/')
        vigente = self.recurso(nombre='Vigente')

        def docker(*args, capturar=False, timeout=None):
            docker.ordenes.append([str(a) for a in args])
            nombres = [f'citt-microproyecto-{oculto.pk}', f'citt-microproyecto-{vigente.pk}',
                       f'citt-microproyecto-{vigente.pk}-visor', 'citt-microproyecto-99999', dm.PASARELA]
            return '\n'.join(nombres) if args[0] == 'ps' else ''
        docker.ordenes = []
        # «-visor» es la pasarela por puerto de la versión anterior: se retira siempre.
        self.assertEqual(dm.retirar_huerfanos(docker), [
            f'citt-microproyecto-{oculto.pk}', f'citt-microproyecto-{vigente.pk}-visor', 'citt-microproyecto-99999'])
        self.assertIn(['rm', '-f', f'citt-microproyecto-{oculto.pk}'], docker.ordenes)
        self.assertNotIn(['rm', '-f', f'citt-microproyecto-{vigente.pk}'], docker.ordenes)
        self.assertEqual(vigente.despliegues.get().origen, 'automatico')
        self.assertEqual(Recurso.objects.get(pk=oculto.pk).microproyecto_url, '')

    def test_visor_informa_mientras_se_pone_en_marcha(self):
        recurso = self.recurso()
        dm.solicitar(recurso, self.usuario, 'automatico')
        respuesta = self.client.get(recurso.get_url_compartir())
        self.assertContains(respuesta, 'Poniéndose en marcha')
        self.assertContains(respuesta, 'http-equiv="refresh"')

    def test_reedicion_del_titulo_reemplaza_la_aplicacion_etiquetada_y_conserva_datos(self):
        recurso = self.recurso(nombre='Almacén anterior')
        anterior = dm.nombre_contenedor(recurso)
        recurso.nombre = 'WMS actualizado'
        recurso.save()

        class DockerAnterior(DockerSimulado):
            def __call__(self, *args, **kwargs):
                resultado = super().__call__(*args, **kwargs)
                if args[0] == 'ps' and (f'label={dm.ETIQUETA}={recurso.pk}' in args
                                       or f'name=^/{anterior}$' in args):
                    return anterior
                return resultado

        docker = DockerAnterior()
        dm.desplegar(recurso, docker)
        self.assertIn(['rm', '-f', anterior], docker.ordenes)
        arranque = docker.orden(['run', '-d', '--name', dm.nombre_contenedor(recurso)])
        self.assertIn(f'type=volume,source=citt-microproyecto-{recurso.pk}-datos,target=/data', arranque)
        self.assertFalse(any(o[0] == 'volume' for o in docker.ordenes))

    def test_retiro_por_etiqueta_reconoce_nombres_legibles_y_no_retira_aplicaciones_vigentes(self):
        oculto = self.recurso(nombre='WMS privado', activo=False)
        vigente = self.recurso(nombre='WMS vigente')
        nombres = {dm.nombre_contenedor(r): str(r.pk) for r in (oculto, vigente)}
        ordenes = []

        def docker(*args, **kwargs):
            ordenes.append(list(args))
            if args[0] == 'ps' and f'label={dm.ETIQUETA}' in args:
                return '\n'.join(nombres)
            if args[0] == 'inspect':
                return nombres.get(args[-1], '')
            return ''

        self.assertEqual(dm.retirar_huerfanos(docker), [dm.nombre_contenedor(oculto)])
        self.assertNotIn(['rm', '-f', dm.nombre_contenedor(vigente)], ordenes)

    def test_dependencias_adicionales_rechazan_opciones_de_pip(self):
        recurso = self.recurso(microproyecto_dependencias='--index-url=http://malo paquete')
        with self.assertRaises(ValidationError) as error:
            recurso.full_clean()
        recurso.archivo.close()
        self.assertIn('microproyecto_dependencias', error.exception.message_dict)

    def test_comando_de_consola_deja_constancia(self):
        recurso = self.recurso()
        with self.assertRaises(CommandError):
            call_command('desplegar_microproyecto', recurso.pk, '--project-settings', 'mal;modulo', stdout=StringIO())
        with patch.object(dm, 'docker', DockerSimulado(falla_en='build')), self.assertRaises(CommandError):
            call_command('desplegar_microproyecto', recurso.pk, stdout=StringIO())
        self.assertEqual(DespliegueMicroproyecto.objects.get(recurso=recurso).origen, 'consola')


class PoliticaDespliegueTests(SimpleTestCase):
    @override_settings(MICROPROYECTOS_DOMINIO='localhost')
    def test_una_carpeta_desactivada_impide_poner_en_marcha_y_mostrar_enlace(self):
        carpeta = SimpleNamespace(pk=1, activa=False, visibilidad='publica', carpeta_padre=None)
        recurso = SimpleNamespace(es_microproyecto=True, archivo=True, activo=True,
                                  visibilidad='publica', carpeta_id=1, carpeta=carpeta)
        self.assertTrue(dm.motivo_no_desplegable(recurso))
        self.assertEqual(dm.estado_visible(recurso)['estado'], 'bloqueado')

    @override_settings(MICROPROYECTOS_DOMINIO='localhost')
    def test_una_carpeta_superior_desactivada_tambien_impide_el_despliegue(self):
        superior = SimpleNamespace(pk=1, activa=False, visibilidad='publica', carpeta_padre=None)
        carpeta = SimpleNamespace(pk=2, activa=True, visibilidad='publica', carpeta_padre=superior)
        recurso = SimpleNamespace(es_microproyecto=True, archivo=True, activo=True,
                                  visibilidad='publica', carpeta_id=2, carpeta=carpeta)
        self.assertTrue(dm.motivo_no_desplegable(recurso))

    @override_settings(MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=False)
    def test_guardar_no_encola_ni_consulta_datos_si_la_automatizacion_esta_apagada(self):
        with patch.object(dm, 'solicitar') as solicitar:
            self.assertIsNone(dm.solicitar_si_corresponde(object(), object()))
        solicitar.assert_not_called()

    @override_settings(MICROPROYECTOS_DOMINIO='localhost')
    def test_recurso_retirado_no_muestra_enlace_activo_ni_cola_historica(self):
        recurso = SimpleNamespace(es_microproyecto=True, archivo=True, activo=False,
                                  microproyecto_url='http://microproyecto-88.localhost:19000/',
                                  microproyecto_hash='hash', hash_sha256='hash')
        # Una URL guardada y un despliegue anterior no autorizan su publicación.
        with patch.object(dm, 'ultimo') as ultimo:
            estado = dm.estado_visible(recurso)
        self.assertEqual(estado['estado'], 'bloqueado')
        self.assertEqual(estado['url'], '')
        ultimo.assert_not_called()

    @override_settings(MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=False)
    def test_la_solicitud_manual_sigue_disponible_con_automatizacion_apagada(self):
        from unittest.mock import Mock
        recurso = Mock(hash_sha256='version')
        recurso.despliegues.filter.return_value.first.return_value = None
        usuario = object()
        with patch.object(dm, 'motivo_no_desplegable', return_value=''), \
                patch.object(DespliegueMicroproyecto.objects, 'create', return_value='solicitud') as crear:
            self.assertEqual(dm.solicitar(recurso, usuario, 'manual'), 'solicitud')
        crear.assert_called_once_with(recurso=recurso, hash_sha256='version',
                                      solicitado_por=usuario, origen='manual')


class NombresContenedoresTests(SimpleTestCase):
    def test_nombre_identifica_contenido_y_laboratorio_sin_terminos_tecnicos_redundantes(self):
        recurso = SimpleNamespace(pk=90, nombre='WMS - microproyecto Django', unidad=SimpleNamespace(
            nombre='Laboratorio de Logística, Transporte y Cadena de Suministro'))
        self.assertEqual(dm.nombre_contenedor(recurso), 'slcid-wms-logistica-transporte-cadena-suministro-90')

    def test_nombre_seguro_acotado_y_unico_por_identificador(self):
        recurso = SimpleNamespace(pk=7, nombre='Álmacén; $(archivo) / WMS ' * 30,
                                  unidad=SimpleNamespace(nombre='Laboratorio de Transporte ' * 30))
        nombre = dm.nombre_contenedor(recurso)
        self.assertRegex(nombre, r'^slcid-[a-z0-9-]+-7$')
        self.assertLessEqual(len(nombre), 100)
        recurso.pk = 8
        self.assertNotEqual(nombre, dm.nombre_contenedor(recurso))

    def test_adopta_pasarela_anterior_sin_recrearla_cuando_configuracion_coincide(self):
        nombres = {dm.PASARELA_ANTERIOR}
        ordenes = []

        def docker(*args, **kwargs):
            ordenes.append(list(args))
            if args[0] == 'rename':
                nombres.remove(args[1])
                nombres.add(args[2])
            if args[0] == 'inspect':
                return hashlib.sha256(dm.NGINX.encode()).hexdigest()[:12]
            return ''

        with patch.object(dm, '_existe', side_effect=lambda ejecutar, tipo, nombre: nombre in nombres):
            dm.asegurar_pasarela(docker)
        self.assertIn(['rename', dm.PASARELA_ANTERIOR, dm.PASARELA], ordenes)
        self.assertIn(['start', dm.PASARELA], ordenes)
        self.assertFalse(any(o[0] in {'rm', 'run'} for o in ordenes))

    def test_no_retira_contenedores_sin_identidad_valida(self):
        def docker(*args, **kwargs):
            if args[0] == 'ps':
                return 'slcid-contenedor-ajeno'
            if args[0] == 'inspect':
                return 'sin-identificador'
            raise AssertionError('No debe modificar contenedores sin identidad')

        self.assertEqual(dm.retirar_huerfanos(docker), [])
