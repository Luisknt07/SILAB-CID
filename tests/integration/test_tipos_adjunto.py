from io import BytesIO
from zipfile import ZipFile

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.recursos.admin.contenido import RecursoInline
from apps.recursos.presentation.tipos_adjunto import inferir, opciones_agrupadas
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests


def zip_con(archivos):
    salida = BytesIO()
    with ZipFile(salida, 'w') as z:
        for nombre, contenido in archivos.items():
            z.writestr(nombre, contenido)
    return SimpleUploadedFile('paquete.zip', salida.getvalue())


class TiposAdjuntoTests(EditorRecursosUnidadTests):
    def test_deduce_el_tipo_del_archivo_o_del_enlace(self):
        casos = {
            'microproyecto_django': zip_con({'wms/manage.py': '# django', 'wms/requirements.txt': 'Django'}),
            'multimedia': zip_con({'index.html': '<html></html>'}),
        }
        for esperado, archivo in casos.items():
            self.assertEqual(inferir(archivo), esperado)
        for nombre, esperado in (('tour.html', 'multimedia'), ('video.mp4', 'multimedia'), ('datos.xlsx', 'dataset'),
                                 ('pieza.stl', 'plano'), ('guia.pdf', 'informe')):
            self.assertEqual(inferir(SimpleUploadedFile(nombre, b'x')), esperado, nombre)
        self.assertEqual(inferir(None, 'https://www.labxchange.org/'), 'publicacion')

    def test_selector_agrupado_con_automatico_primero(self):
        opciones = opciones_agrupadas()
        self.assertEqual(opciones[0], ('', 'Automático (según el archivo)'))
        claves = [clave for _, grupo in opciones[1:] for clave, _ in grupo]
        self.assertCountEqual(claves, [clave for clave, _ in Recurso._meta.get_field('tipo_adjunto').choices])

    def formset(self, archivo=None, **campos):
        FormSet = RecursoInline(Unidad, admin.site).get_formset(self.request, self.unidad)
        p = FormSet.get_default_prefix()
        datos = {f'{p}-TOTAL_FORMS': '1', f'{p}-INITIAL_FORMS': '0', f'{p}-0-nombre': 'Contenido',
                 f'{p}-0-descripcion': 'Prueba', f'{p}-0-carpeta': str(self.carpeta.pk), f'{p}-0-version': '1',
                 f'{p}-0-estado': 'vigente', f'{p}-0-orden': '0', f'{p}-0-visibilidad': 'interna',
                 f'{p}-0-fuente': 'interna', f'{p}-0-licencia_uso': 'interna', f'{p}-0-tipo_adjunto': ''}
        datos.update({f'{p}-0-{k}': v for k, v in campos.items()})
        return FormSet(datos, {f'{p}-0-archivo': archivo} if archivo else {}, instance=self.unidad)

    def test_en_automatico_no_hace_falta_elegir(self):
        formset = self.formset(zip_con({'wms/manage.py': '# django', 'wms/requirements.txt': 'Django'}))
        self.assertTrue(formset.is_valid(), formset.errors)
        recurso = formset.save()[0]
        recurso.archivo.close()
        self.assertEqual(recurso.tipo_adjunto, 'microproyecto_django')
        enlace = self.formset(url='https://www.labxchange.org/')
        self.assertTrue(enlace.is_valid(), enlace.errors)
        self.assertEqual(enlace.save()[0].tipo_adjunto, 'publicacion')

    def test_una_eleccion_explicita_se_respeta(self):
        formset = self.formset(SimpleUploadedFile('guia.pdf', b'%PDF-1.4'), tipo_adjunto='manual')
        self.assertTrue(formset.is_valid(), formset.errors)
        recurso = formset.save()[0]
        recurso.archivo.close()
        self.assertEqual(recurso.tipo_adjunto, 'manual')

    def test_un_recurso_existente_muestra_su_tipo_y_uno_nuevo_automatico(self):
        FormSet = RecursoInline(Unidad, admin.site).get_formset(self.request, self.unidad)
        self.assertEqual(FormSet(instance=self.unidad).empty_form.initial.get('tipo_adjunto'), '')
        existente = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta, nombre='Guía', tipo_adjunto='norma',
                                           archivo=SimpleUploadedFile('guia.pdf', b'%PDF'))
        existente.archivo.close()
        formulario = FormSet(instance=self.unidad).forms[0]
        self.assertEqual(formulario.initial['tipo_adjunto'], 'norma')
        self.assertIn('No es obligatorio', formulario.fields['tipo_adjunto'].help_text)
