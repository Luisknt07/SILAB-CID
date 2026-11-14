from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.recursos.admin.contenido import CarpetaRecursoAdmin, RecursoInline
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.directorio_unidades.models.core import Unidad


class EditorRecursosUnidadTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        self.usuario = get_user_model().objects.create_superuser('editor', 'editor@example.org', 'clave')
        self.unidad = Unidad.objects.create(nombre='Laboratorio XR', slug='xr-editor',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1), administrador=self.usuario)
        self.modulo = ModuloUnidad.objects.filter(unidad=self.unidad).first()
        self.carpeta = CarpetaRecurso.objects.create(unidad=self.unidad, nombre='Simuladores XR',
                                                    modulo_config=self.modulo, seccion_planta='1.5')
        self.request = RequestFactory().get(reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]))
        self.request.user = self.usuario

    def test_seccion_numerada_solo_para_unidades_con_mapa(self):
        panel = CarpetaRecursoAdmin(CarpetaRecurso, admin.site)
        for tipo in ('laboratorios', 'plantas_piloto', 'centros_experimentales', 'observatorios'):
            self.carpeta.unidad.dependencia = tipo
            formulario = panel.get_form(self.request, self.carpeta)
            self.assertEqual('seccion_planta' in formulario.base_fields, tipo in ('plantas_piloto', 'laboratorios', 'observatorios'))

    def test_archivo_visible_y_enlazado_desde_carpeta(self):
        recurso = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta,
            nombre='Simulador XR', archivo=SimpleUploadedFile('simulador.html', b'<html>XR</html>'),
            descripcion='Simulador del laboratorio.', seguridad_verificada=True)
        self.client.force_login(self.usuario)
        respuesta = self.client.get(self.request.path)
        self.assertEqual(respuesta.status_code, 200)
        # Cada archivo dice dónde se ve; las carpetas se ordenan en «Contenidos de la ficha», no aquí.
        self.assertContains(respuesta, f'id="recurso-editor-{recurso.pk}"')
        self.assertContains(respuesta, f'Se ve en: {self.modulo.nombre} › 1.5 Repositorio y descargas › Simuladores XR')
        self.assertNotContains(respuesta, 'carpetas-TOTAL_FORMS')
        self.assertContains(respuesta, reverse('admin:directorio_unidades_unidad_contenidos', args=[self.unidad.pk]))
        self.assertContains(respuesta, 'name="recursos-0-archivo"')
        self.assertContains(respuesta, recurso.archivo.name)
        enlace = recurso.get_url_compartir()
        self.assertIn('-simulador-xr/', enlace)
        self.assertContains(respuesta, f'data-url-recurso="{enlace}"')
        self.assertContains(respuesta, 'Copiar enlace')
        self.assertContains(respuesta, 'admin/js/enlace_recurso.js')
        self.client.logout()
        sitio = self.client.get(enlace)
        self.assertEqual(sitio.status_code, 200)
        self.assertEqual(b''.join(sitio.streaming_content), b'<html>XR</html>')
        recurso.nombre = 'Nuevo título del simulador'
        recurso.save(update_fields=['nombre'])
        for anterior in (enlace, reverse('recurso_unidad', args=[recurso.pk])):
            sitio = self.client.get(anterior)
            self.assertEqual(sitio.status_code, 200)
            self.assertEqual(b''.join(sitio.streaming_content), b'<html>XR</html>')
        recurso.archivo.close()
        self.assertIn('-nuevo-titulo-del-simulador/', recurso.get_url_compartir())
        inline = next(item for item in respuesta.context['inline_admin_formsets'] if item.formset.model is Recurso)
        # El grupo abre; cada archivo queda plegado (valor de Grappelli) hasta abrirlo.
        self.assertIn('grp-open', inline.opts.classes)
        self.assertFalse(getattr(inline.opts, 'inline_classes', None))

    def test_cargar_reemplazar_y_eliminar_archivo_en_formset(self):
        inline = RecursoInline(Unidad, admin.site)
        FormSet = inline.get_formset(self.request, self.unidad)
        prefix = FormSet.get_default_prefix()
        datos = {f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-0-nombre': 'Simulador', f'{prefix}-0-descripcion': 'Práctica interactiva',
            f'{prefix}-0-carpeta': str(self.carpeta.pk), f'{prefix}-0-tipo_adjunto': 'multimedia',
            f'{prefix}-0-version': '1', f'{prefix}-0-estado': 'vigente',
            f'{prefix}-0-orden': '0', f'{prefix}-0-visibilidad': 'publica',
            f'{prefix}-0-fuente': 'interna', f'{prefix}-0-licencia_uso': 'interna',
            f'{prefix}-0-seguridad_verificada': 'on'}
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            for numero in (1, 2):
                archivo = SimpleUploadedFile(f'simulador{numero}.html', f'<html>{numero}</html>'.encode())
                formset = FormSet(datos, {f'{prefix}-0-archivo': archivo}, instance=self.unidad)
                self.assertTrue(formset.is_valid(), formset.errors)
                recurso = formset.save()[0]
                self.assertEqual(recurso.archivo.read(), f'<html>{numero}</html>'.encode())
                recurso.archivo.close()
                datos.update({f'{prefix}-INITIAL_FORMS': '1', f'{prefix}-0-id': str(recurso.pk)})
            datos[f'{prefix}-0-DELETE'] = 'on'
            formset = FormSet(datos, instance=self.unidad)
            self.assertTrue(formset.is_valid(), formset.errors)
            formset.save()
            for form in formset.forms:
                form.instance.archivo.close()
            self.assertFalse(Recurso.objects.filter(pk=recurso.pk).exists())

    def test_url_con_nombre_sirve_zip_y_respeta_visibilidad(self):
        contenido = BytesIO()
        with ZipFile(contenido, 'w') as paquete:
            paquete.writestr('index.html', '<script src="js/app.js"></script>')
            paquete.writestr('js/app.js', 'window.simulador = true;')
        recurso = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta,
            nombre='Simulación XR', archivo=SimpleUploadedFile('sitio.zip', contenido.getvalue()),
            descripcion='Sitio interactivo.', seguridad_verificada=True)
        enlace = recurso.get_url_compartir()
        for ruta, esperado in (('', b'<script src="js/app.js"></script>'),
                               ('js/app.js', b'window.simulador = true;')):
            respuesta = self.client.get(enlace + ruta)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(b''.join(respuesta.streaming_content), esperado)
        Recurso.objects.filter(pk=recurso.pk).update(visibilidad='restringida')
        self.assertEqual(self.client.get(enlace).status_code, 302)
        self.assertEqual(self.client.get(enlace + 'js/app.js').status_code, 302)

    def test_un_archivo_duplicado_indica_donde_esta_el_original(self):
        from django.core.exceptions import ValidationError
        original = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta, nombre='WMS',
                                          archivo=SimpleUploadedFile('wms.html', b'<html>WMS</html>'))
        original.archivo.close()
        copia = Recurso(unidad=self.unidad, carpeta=self.carpeta, nombre='Simulador wms', descripcion='Copia',
                        activo=False, archivo=SimpleUploadedFile('copia.html', b'<html>WMS</html>'))
        with self.assertRaises(ValidationError) as error:
            copia.full_clean()
        self.assertEqual(error.exception.message_dict['archivo'], [
            'El archivo ya existe como «WMS» (unidad «Laboratorio XR», carpeta «Simuladores XR»). '
            'Edite ese recurso o comparta su enlace en lugar de duplicarlo.'])
