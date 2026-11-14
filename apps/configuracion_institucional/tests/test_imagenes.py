"""Cuatro configuraciones de marca, archivos adversos e historial privado."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
from importlib import import_module

from PIL import Image, PngImagePlugin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.presentation.identidad import fuentes_logo, identidad_actual, logo_institucional
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional
from ..admin import PresentacionForm
from ..imagenes import CAMPOS_IMAGENES, MAX_BYTES, almacen_logos, preparar_imagen
from ..models import RevisionPresentacion
from ..services import guardar_borrador, publicar_revision
from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf


def imagen(formato='PNG', size=(600, 180), color=(20, 70, 100, 100)):
    salida = BytesIO()
    objeto = Image.new('RGBA', size, color)
    if formato == 'JPEG':
        objeto = objeto.convert('RGB')
    meta = PngImagePlugin.PngInfo()
    meta.add_text('comentario', 'Dato privado que no debe publicarse')
    objeto.save(salida, format=formato, **({'pnginfo': meta} if formato == 'PNG' else {}))
    return SimpleUploadedFile('nombre-no-confiable.' + formato.lower(), salida.getvalue(), content_type='text/html')


class ImagenInstitucionalTests(TestCase):
    def setUp(self):
        (Path(settings.BASE_DIR) / 'var' / 'tmp').mkdir(parents=True, exist_ok=True)
        self.directorio = TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'var' / 'tmp')
        self.addCleanup(self.directorio.cleanup)
        configuracion = override_settings(INSTITUTION_LOGO_ROOT=self.directorio.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.autor = get_user_model().objects.create_superuser('imagenes.qa')
        self.datos = dict(nombre_producto='Sistema de ensayo', nombre_corto_producto='Ensayo',
                          nombre_institucion='Institución de ensayo', logo='', logo_secundario='')

    def borrador(self, **campos):
        return guardar_borrador(RevisionPresentacion(**self.datos, **campos), self.autor)

    def test_caso_1_estaticos_sin_archivos_conservan_marca(self):
        revision = publicar_revision(self.borrador().pk, self.autor, base_esperada=None)
        with con_presentacion_institucional():
            self.assertEqual(identidad_actual()[1].imagenes, ())
            self.assertEqual(fuentes_logo(identidad_actual()[1]), {'escritorio': '', 'movil': ''})
        self.assertEqual(list(Path(self.directorio.name).iterdir()), [])
        self.assertEqual(revision.logo_claro.name, '')

    def test_caso_2_un_logo_hereda_ambas_superficies_y_movil(self):
        revision = publicar_revision(self.borrador(logo_claro=imagen()).pk, self.autor, base_esperada=None)
        with con_presentacion_institucional():
            institucion = identidad_actual()[1]
            self.assertEqual(fuentes_logo(institucion), fuentes_logo(institucion, fondo='oscuro'))
            self.assertEqual(fuentes_logo(institucion)['escritorio'], revision.logo_claro.url)
            self.assertEqual(logo_institucional(), Path(revision.logo_claro.path))

    def test_caso_3_variantes_claro_oscuro_seleccionan_por_superficie(self):
        revision = publicar_revision(self.borrador(logo_claro=imagen(), logo_oscuro=imagen('WEBP')).pk,
                                      self.autor, base_esperada=None)
        portal = self.client.get('/').content.decode()
        self.assertIn(revision.logo_oscuro.url, portal)
        # El portal va sobre fondo oscuro; el logo claro sirve a los documentos sobre blanco (logo_institucional).
        for nombre in ('quienes_somos', 'centros_id', 'servicios_portal', 'normativa', 'noticias'):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn(revision.logo_oscuro.url, respuesta.content.decode())
        with con_presentacion_institucional():
            self.assertEqual(logo_institucional(), Path(revision.logo_claro.path))
            self.assertEqual(logo_institucional(fondo='oscuro'), Path(revision.logo_oscuro.path))

    def test_caso_4_moviles_y_marca_secundaria_independientes(self):
        revision = publicar_revision(self.borrador(**{c: imagen(size=(256, 256)) for c in CAMPOS_IMAGENES}).pk,
                                      self.autor, base_esperada=None)
        with con_presentacion_institucional():
            institucion = identidad_actual()[1]
            self.assertEqual(fuentes_logo(institucion, fondo='oscuro')['movil'], revision.logo_movil_oscuro.url)
            self.assertEqual(fuentes_logo(institucion)['movil'], revision.logo_movil_claro.url)
            self.assertEqual(logo_institucional(secundario=True), Path(revision.logo_secundario_subido.path))
        contenido = self.client.get('/').content.decode()
        self.assertIn('(max-width: 575.98px)', contenido)
        self.assertIn(revision.logo_movil_oscuro.url, contenido)

    def test_borrador_privado_publicado_publico_y_cache_diferente(self):
        borrador = self.borrador(logo_claro=imagen())
        self.assertEqual(self.client.get(borrador.logo_claro.url).status_code, 404)
        self.client.force_login(self.autor)
        respuesta = self.client.get(borrador.logo_claro.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        respuesta._resource_closers[0]()
        publicar_revision(borrador.pk, self.autor, base_esperada=None)
        self.client.logout()
        respuesta = self.client.get(borrador.logo_claro.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'image/png')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        respuesta._resource_closers[0]()

    def test_validacion_quita_metadatos_preserva_alpha_y_normaliza_formatos(self):
        for formato in ('PNG', 'JPEG', 'WEBP'):
            with self.subTest(formato=formato):
                archivo = preparar_imagen(imagen(formato))
                with Image.open(archivo) as decodificada:
                    self.assertEqual(decodificada.format, 'PNG')
                    self.assertEqual(decodificada.size, (600, 180))
                    self.assertNotIn('comentario', decodificada.info)
                    self.assertNotIn('exif', decodificada.info)
                    if formato == 'PNG':
                        self.assertEqual(decodificada.getpixel((0, 0))[3], 100)

    def test_rechaza_disfrazados_animados_demasiado_peso_y_dimensiones(self):
        animacion = BytesIO()
        Image.new('RGB', (10, 10)).save(animacion, format='GIF')
        adversos = [SimpleUploadedFile('test.png', b'<svg><script>evil()</script></svg>'),
                    SimpleUploadedFile('test.png', b'x' * (MAX_BYTES + 1)),
                    SimpleUploadedFile('test.png', animacion.getvalue()),
                    imagen(size=(4097, 1)), imagen(size=(2100, 2100))]
        corrupto = bytearray(imagen().read())
        corrupto[29] ^= 1
        adversos.append(SimpleUploadedFile('corrupto.png', bytes(corrupto)))
        for archivo in adversos:
            with self.subTest(nombre=archivo.name), self.assertRaises(ValidationError):
                self.borrador(logo_claro=archivo)
        self.assertEqual(RevisionPresentacion.objects.count(), 0)
        self.assertEqual(list(Path(self.directorio.name).iterdir()), [])

    def test_editor_archivos_multipart_y_errores_sin_pagina_500(self):
        form = PresentacionForm(self.datos, files={'logo_oscuro': imagen()})
        self.assertTrue(form.is_valid(), list(form.errors))
        revision = guardar_borrador(form.save(commit=False), self.autor)
        self.assertTrue(almacen_logos.exists(revision.logo_oscuro.name))
        self.client.force_login(self.autor)
        url = reverse('admin:configuracion_institucional_revisionpresentacion_add')
        contenido = self.client.get(url).content.decode()
        self.assertIn('multipart/form-data', contenido)
        self.assertEqual(contenido.count('type="file"'), 5)
        invalido = self.client.post(url, {**self.datos, 'logo_claro': SimpleUploadedFile('a.png', b'error')})
        self.assertEqual(invalido.status_code, 200)
        self.assertEqual(RevisionPresentacion.objects.count(), 1)

    def test_historial_restauracion_no_sobrescribe_imagenes_y_editor_hereda(self):
        primera = publicar_revision(self.borrador(logo_claro=imagen()).pk, self.autor, base_esperada=None)
        segunda = publicar_revision(self.borrador(logo_claro=imagen('JPEG')).pk, self.autor, base_esperada=primera.pk)
        restaurada = publicar_revision(primera.pk, self.autor, base_esperada=segunda.pk)
        self.assertEqual(restaurada.logo_claro.name, primera.logo_claro.name)
        self.assertEqual(len(list(Path(self.directorio.name).iterdir())), 2)
        self.client.force_login(self.autor)
        url = reverse('admin:configuracion_institucional_revisionpresentacion_add')
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url + f'?fuente={primera.pk}').status_code, 200)
        historica = reverse('admin:configuracion_institucional_revisionpresentacion_change', args=[primera.pk])
        self.assertEqual(self.client.get(historica).status_code, 200)
        self.assertEqual(self.client.post(url, {**self.datos, 'fuente_imagenes': restaurada.pk}).status_code, 302)
        self.assertEqual(RevisionPresentacion.objects.first().logo_claro.name, primera.logo_claro.name)
        invalido = PresentacionForm({**self.datos, 'fuente_imagenes': 9223372036854775808})
        self.assertFalse(invalido.is_valid())
        self.assertIn('fuente_imagenes', invalido.errors)
        nueva_identidad = {**settings.INSTITUTION_IDENTITY, 'siglas': 'INSTITUCION-NUEVA-QA'}
        with override_settings(INSTITUTION_IDENTITY=nueva_identidad):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIsNone(respuesta.context['adminform'].form.initial['fuente_imagenes'])

    def test_referencia_inventada_y_traversal_no_publicables(self):
        with self.assertRaises(ValidationError):
            self.borrador(logo_claro='a' * 32 + '.png')
        for ruta in ('../secreto.png', 'otro.png', 'a' * 32 + '.svg'):
            self.assertEqual(self.client.get('/marca/imagenes/' + ruta).status_code, 404)

    def test_previsualizacion_autorizada_muestra_ambos_fondos(self):
        borrador = self.borrador(logo_claro=imagen())
        self.client.force_login(self.autor)
        url = reverse('admin:configuracion_institucional_revisionpresentacion_publicar', args=[borrador.pk])
        contenido = self.client.get(url).content.decode()
        self.assertIn(borrador.logo_claro.url, contenido)
        self.assertIn('background:#071525', contenido)
        self.assertIn('background:#fff', contenido)

    def test_poliglota_se_reescribe_sin_html_adjunta(self):
        original = imagen()
        poliglota = SimpleUploadedFile('logo.png', original.read() + b'<script>secreto()</script>')
        normalizada = preparar_imagen(poliglota)
        self.assertNotIn(b'<script>', normalizada.read())

    def test_visor_de_borrador_revoca_acceso_con_autoridad_fresca(self):
        borrador = self.borrador(logo_claro=imagen())
        self.client.force_login(self.autor)
        get_user_model().objects.filter(pk=self.autor.pk).update(is_staff=False)
        self.assertEqual(self.client.get(borrador.logo_claro.url).status_code, 404)

    def test_pdf_incrusta_imagen_publicada_y_reversa_no_pierde_historial(self):
        publicar_revision(self.borrador(logo_claro=imagen()).pk, self.autor, base_esperada=None)
        reporte = {'scope_label': 'QA', 'category_label': 'Recursos',
                   'filter_summary': [], 'is_generic': True,
                   'generated_at': datetime(2026, 9, 17, tzinfo=timezone.utc),
                   'start_date': datetime(2026, 9, 1), 'end_date': datetime(2026, 9, 30),
                   'dataset': {'headers': ['Equipo'], 'rows': [['QA']], 'cards': []}}
        with con_presentacion_institucional():
            pdf = render_unit_report_pdf(reporte)
        self.assertIn(b'/Subtype /Image', pdf)
        from django.apps import apps
        from django.db import connection
        modulo = import_module('apps.configuracion_institucional.migrations.0006_revisionpresentacion_logo_claro_and_more')
        with connection.schema_editor(atomic=False) as editor, self.assertRaises(RuntimeError):
            modulo.proteger_reversa(apps, editor)

    def test_configuracion_impide_exponer_borradores_en_media_publica(self):
        from ..checks import almacenamiento_marca_privado
        self.assertEqual(almacenamiento_marca_privado(), [])
        with override_settings(INSTITUTION_LOGO_ROOT=Path(settings.MEDIA_ROOT) / 'brand'):
            self.assertEqual(almacenamiento_marca_privado()[0].id, 'configuracion_institucional.E001')

    def test_un_logo_compacto_solo_tambien_funciona_como_respaldo(self):
        publicada = publicar_revision(self.borrador(logo_movil_claro=imagen(size=(256, 256))).pk,
                                       self.autor, base_esperada=None)
        with con_presentacion_institucional():
            self.assertEqual(fuentes_logo(identidad_actual()[1], fondo='oscuro')['escritorio'], publicada.logo_movil_claro.url)
            self.assertEqual(logo_institucional(), Path(publicada.logo_movil_claro.path))
