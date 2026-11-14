"""Contratos ES/EN: navegación, aislamiento, protección CSRF y datos originales."""

import gettext as gettext_stdlib
import gzip
import json
from pathlib import Path
import subprocess
import sys

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import translation
from django.utils import timezone

from apps.core.presentation.regional import regional_publica
from apps.core.presentation.traducciones import traducir_campos
from apps.directorio_unidades.models.core import Unidad


class PreferenciaIdiomaTests(TestCase):
    def setUp(self):
        # LocaleMiddleware activa el idioma de cada petición. El siguiente
        # caso del worker debe recuperar el idioma previo, no la última cookie.
        self.enterContext(translation.override(settings.LANGUAGE_CODE))

    def cambiar(self, cliente, idioma, destino='/'):
        return cliente.post(reverse('set_language'), {'language': idioma, 'next': destino})

    def test_selector_es_en_en_portal_y_preferencia_independiente(self):
        otro = Client()
        destino = reverse('noticias') + '?pagina=2#contenido'
        respuesta = self.cambiar(self.client, 'en', destino)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, destino)
        ingles = self.client.get(reverse('home'))
        self.assertContains(ingles, 'data-language-switch')
        self.assertContains(ingles, '>Home<')
        self.assertContains(ingles, '>News<')
        self.assertEqual(ingles.wsgi_request.LANGUAGE_CODE, 'en')
        self.assertContains(otro.get(reverse('home')), '>Inicio<')
        self.cambiar(self.client, 'es')
        self.assertContains(self.client.get(reverse('home')), '>Inicio<')

    def test_cookie_segura_y_sin_cambiar_sesion_de_usuario(self):
        usuario = get_user_model().objects.create_user('idiomas', password='clave-prueba-123')
        self.client.force_login(usuario)
        with override_settings(LANGUAGE_COOKIE_SECURE=True):
            respuesta = self.cambiar(self.client, 'en')
        cookie = respuesta.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(self.client.session['_auth_user_id'], str(usuario.pk))

    def test_csrf_obligatorio_para_cambiar_idioma(self):
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(self.cambiar(cliente, 'en').status_code, 403)
        cliente.get(reverse('home'))
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        respuesta = cliente.post(reverse('set_language'), {
            'language': 'en', 'csrfmiddlewaretoken': token, 'next': '/',
        })
        self.assertEqual(respuesta.status_code, 302)

    def test_no_admite_idiomas_no_configurados_ni_cambio_por_get(self):
        self.assertEqual(self.client.get(reverse('set_language')).status_code, 405)
        self.assertEqual(self.cambiar(self.client, 'fr').status_code, 400)
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, self.client.cookies)

    def test_destinos_externos_y_downgrade_https_rechazados(self):
        self.assertEqual(self.cambiar(self.client, 'en', 'https://externo.example/').url, '/')
        respuesta = self.client.post(reverse('set_language'), {
            'language': 'en', 'next': 'http://testserver/inseguro/',
        }, secure=True)
        self.assertEqual(respuesta.url, '/')

    def test_catalogos_js_separados_y_cache_privada(self):
        url = reverse('javascript_catalog')
        ingles = self.client.get(url, {'language': 'en'})
        espanol = self.client.get(url, {'language': 'es'})
        self.assertEqual(ingles.status_code, 200)
        self.assertContains(ingles, 'Process datasheet')
        self.assertNotEqual(ingles.content, espanol.content)
        self.assertIn('private', ingles['Cache-Control'])
        self.assertIn('Cookie', ingles['Vary'])
        comprimido = self.client.get(url, {'language': 'en'}, HTTP_ACCEPT_ENCODING='gzip')
        self.assertEqual(comprimido['Content-Encoding'], 'gzip')
        self.assertIn(b'Process datasheet', gzip.decompress(comprimido.content))
        self.assertLess(len(comprimido.content), len(ingles.content))
        self.assertIn('Accept-Encoding', comprimido['Vary'])
        self.assertEqual(self.client.get(url, {'language': 'fr'}).status_code, 400)

    def test_paginas_principales_ingles_sin_cambiar_rutas(self):
        self.cambiar(self.client, 'en')
        for nombre in ('home', 'quienes_somos', 'centros_id', 'laboratorios_unidades',
                       'servicios_portal', 'normativa', 'noticias', 'account_login'):
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.wsgi_request.LANGUAGE_CODE, 'en')
                self.assertContains(respuesta, 'data-language-switch')
                self.assertIn('Cookie', respuesta.get('Vary', ''))

    def test_admin_en_conserva_permisos_datos_y_campos(self):
        usuario = get_user_model().objects.create_superuser('admin-idiomas', password='clave-123')
        self.client.force_login(usuario)
        unidad = Unidad.objects.create(nombre='Laboratorio propio', slug='idioma-propio', fecha_inicio=timezone.now())
        self.cambiar(self.client, 'en')
        respuesta = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-language-switch')
        self.assertContains(respuesta, 'Laboratorio propio')
        formulario = admin.site._registry[Unidad].get_form(respuesta.wsgi_request, unidad)
        self.assertEqual(formulario().fields['nombre'].label, 'Name')
        self.assertEqual(formulario().fields['nombre'].widget.input_type, 'text')
        unidad.refresh_from_db()
        self.assertEqual(unidad.nombre, 'Laboratorio propio')
        anonimo = Client()
        self.assertEqual(anonimo.get(reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk])).status_code, 302)

    def test_cuatro_tipos_de_unidad_conservan_modulos_y_datos_al_cambiar(self):
        self.cambiar(self.client, 'en')
        for dependencia in ('laboratorios', 'observatorios', 'centro_experimental', 'plantas_piloto'):
            with self.subTest(tipo=dependencia):
                unidad = Unidad.objects.create(nombre=f'Unidad propia {dependencia}',
                                               slug=f'idioma-{dependencia}',
                                               dependencia=dependencia, fecha_inicio=timezone.now())
                antes = list(unidad.modulos_contenido.values_list('pk', 'clave', 'nombre', 'activo'))
                respuesta = self.client.get(unidad.get_absolute_url())
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, unidad.nombre)
                self.assertContains(respuesta, 'data-language-switch')
                self.assertContains(respuesta, 'General information')
                self.assertEqual(antes, list(unidad.modulos_contenido.values_list('pk', 'clave', 'nombre', 'activo')))


class ContratosTraduccionTests(SimpleTestCase):
    def test_idioma_personal_no_cambia_zona_institucional(self):
        with translation.override('en'):
            contexto = regional_publica(None)
        self.assertEqual(contexto['idioma_actual'], 'en')
        self.assertEqual(contexto['regional_institucion']['zona_horaria'], settings.TIME_ZONE)
        self.assertEqual(settings.LANGUAGE_CODE, 'es-ec')

    def test_formulario_traduce_etiquetas_y_grupos_sin_cambiar_valores(self):
        class Formulario(forms.Form):
            nombre = forms.CharField(label='Nombre')
            opcion = forms.ChoiceField(choices=[('laboratorios', [('equipo', 'Equipos')])])

        with translation.override('en'):
            formulario = traducir_campos(Formulario({'nombre': 'Mi equipo', 'opcion': 'equipo'}))
            self.assertEqual(formulario.fields['nombre'].label, 'Name')
            self.assertEqual(list(formulario.fields['opcion'].choices)[0], ('laboratorios', [('equipo', 'Equipment')]))
            self.assertTrue(formulario.is_valid())
            self.assertEqual(formulario.cleaned_data, {'nombre': 'Mi equipo', 'opcion': 'equipo'})

    def test_catalogos_compilados_actualizados_y_compatibles_gettext(self):
        root = Path(settings.BASE_DIR)
        resultado = subprocess.run([sys.executable,
                                    str(root / 'scripts/compilar_idiomas.py'), '--check'],
                                   capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        for idioma, palabra in [('es', 'Inicio'), ('en', 'Home')]:
            with (root / f'locale/{idioma}/LC_MESSAGES/django.mo').open('rb') as stream:
                catalogo = gettext_stdlib.GNUTranslations(stream)
            self.assertEqual(catalogo.gettext('Inicio'), palabra)
            self.assertEqual(catalogo.gettext('UPEC'), 'UPEC')

    def test_errores_de_reservas_localizados_con_mismo_contrato(self):
        from apps.reservas.presentation.views import _respuesta_error
        with translation.override('en'):
            respuesta = _respuesta_error('Usuario no autenticado', status=401)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(json.loads(respuesta.content), {
            'success': False, 'error': 'User not authenticated',
        })

    def test_html_js_traduce_textos_sin_traducir_datos_ni_identificadores(self):
        source = Path(settings.BASE_DIR, 'apps', 'core', 'static', 'portal', 'js', 'components', 'idiomas.js').read_text(encoding='utf-8')
        programa = '''
const vm=require('vm');
let submit;
const contexto={window:{gettext:s=>({'Equipos':'Equipment','Continuar':'Continue'})[s]||s},
 URL,document:{addEventListener:(kind,fn)=>{if(kind==='submit')submit=fn;}}};
vm.createContext(contexto);vm.runInContext(SOURCE,contexto);
const dato='Equipo propio 12.50';
const html=contexto.window.interfaz.html`<button id="equipo" data-value="equipos" title="Continuar">Equipos</button><span>${dato}</span>`;
if(!html.includes('Equipment')||!html.includes('title="Continue"')||!html.includes('id="equipo"')||!html.includes('data-value="equipos"')||!html.includes(dato))throw Error(html);
const original=contexto.window.gettext;
contexto.window.gettext=s=>s.includes('name=')||s.includes('value=')?'CORRUPT':original(s);
const atributos=contexto.window.interfaz.html`<input type="${'number'}" name="${'equipo_id'}" value="${12.5}" title="Continuar"><span>Equipos</span>`;
if(!atributos.includes('name="equipo_id"')||!atributos.includes('value="12.5"')||!atributos.includes('type="number"')||!atributos.includes('title="Continue"')||!atributos.includes('Equipment')||atributos.includes('CORRUPT'))throw Error(atributos);
const dinamico=contexto.window.interfaz.html`<${'button'} name="${'equipo_id'}">Equipos</${'button'}>`;
if(dinamico!=='<button name="equipo_id">Equipment</button>')throw Error(dinamico);
contexto.window.gettext=()=>'<img onerror="alert(1)">';
const seguro=contexto.window.interfaz.html`<span>Equipos</span>`;
if(seguro.includes('<img'))throw Error(seguro);
contexto.window.location={href:'https://testserver/planta/?pagina=2#informacion-general'};
contexto.document.querySelector=s=>s.includes('nav-link')?{dataset:{modulo:'procesos-protocolos'}}:{dataset:{id:'receta-25'}};
const form={elements:{next:{value:''}}};
submit({target:{closest:()=>form}});
const destino=new URL(form.elements.next.value,'https://testserver');
if(destino.searchParams.get('recurso')!=='receta-25'||destino.hash!=='#procesos-protocolos'||destino.searchParams.get('pagina')!=='2')throw Error(destino);
contexto.document.querySelector=()=>null;
submit({target:{closest:()=>form}});
if(form.elements.next.value!=='/planta/?pagina=2#informacion-general')throw Error(form.elements.next.value);
'''.replace('SOURCE', json.dumps(source))
        resultado = subprocess.run(['node', '-e', programa], capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
