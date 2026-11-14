"""«Conoce la unidad»: la presentación que la planta escribe sobre sí misma.

Qué es, qué hace, historia con hitos, misión, visión, objetivos, líneas de
acción, beneficiarios, resultados y el video en el que la presenta su
responsable. El público la ve publicada; el personal también el borrador. Las
cifras salen de lo registrado en la plataforma, no se escriben a mano.
"""
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.gestion_unidades.presentation.conoce import cifras_de_la_unidad, equipos_de_la_unidad
from apps.gestion_unidades.models.presentacion import HitoUnidad, LineaAccionUnidad, PresentacionUnidad
from apps.gestion_unidades.models.interior import MedioInterior
from tests.integration.test_produccion_planta import BasePlantaProduce


class ConoceLaUnidadTests(BasePlantaProduce):
    def pagina(self, usuario=None):
        if usuario is not None:
            self.client.force_login(usuario)
        return self.client.get(reverse('conoce_unidad', args=[self.unidad.slug]))

    def presentar(self, **datos):
        datos.setdefault('lema', 'De la leche cruda al producto terminado')
        datos.setdefault('mision', 'Formar profesionales en procesamiento lácteo seguro.')
        datos.setdefault('objetivos', 'Formar en buenas prácticas\n\nValidar nuevos productos\n')
        datos.setdefault('video_url', 'https://youtu.be/IJxxIxTuMb8')
        datos.setdefault('video_presenta', 'Ing. Patricia Chamorro, coordinadora')
        return PresentacionUnidad.objects.create(unidad=self.unidad, **datos)

    def test_el_video_debe_ser_de_youtube_y_las_listas_van_una_por_linea(self):
        with self.assertRaises(ValidationError) as error:
            PresentacionUnidad(unidad=self.unidad, video_url='https://vimeo.com/1').clean()
        self.assertIn('video_url', error.exception.message_dict)
        presentacion = PresentacionUnidad(unidad=self.unidad, objetivos='Uno\n\n  Dos  \n')
        self.assertEqual(presentacion.lista('objetivos'), ['Uno', 'Dos'])

    def test_sin_presentacion_el_personal_ve_como_escribirla(self):
        self.assertContains(self.pagina(), 'La unidad todavía no publica su presentación.')
        self.assertNotContains(self.pagina(), 'Escribir la presentación')
        self.assertContains(self.pagina(self.coordinacion), 'Escribir la presentación')

    def test_el_borrador_solo_lo_ve_el_personal(self):
        self.presentar(publicada=False)
        self.assertNotContains(self.pagina(), 'De la leche cruda al producto terminado')
        pagina = self.pagina(self.coordinacion)
        self.assertContains(pagina, 'De la leche cruda al producto terminado')
        self.assertContains(pagina, 'Borrador: el público todavía no ve esta presentación.')

    def test_publicada_cuenta_la_unidad_completa(self):
        self.presentar(publicada=True)
        LineaAccionUnidad.objects.create(unidad=self.unidad, titulo='Docencia práctica', icono='fa-graduation-cap')
        HitoUnidad.objects.create(unidad=self.unidad, anio=2021, titulo='Primera corrida de yogur')
        HitoUnidad.objects.create(unidad=self.unidad, anio=2019, titulo='Creación de la planta')
        pagina = self.pagina()
        self.assertEqual(pagina['X-Frame-Options'], 'SAMEORIGIN')
        for texto in ('Formar profesionales en procesamiento lácteo seguro.', '>Formar en buenas prácticas</li>',
                      '>Validar nuevos productos</li>', 'fas fa-graduation-cap', 'i.ytimg.com/vi/IJxxIxTuMb8',
                      'Ing. Patricia Chamorro, coordinadora', reverse('ubicacion_unidad', args=[self.unidad.slug])):
            self.assertContains(pagina, texto)
        contenido = pagina.content.decode()
        self.assertLess(contenido.index('Creación de la planta'), contenido.index('Primera corrida de yogur'))
        self.assertNotContains(pagina, 'Borrador')

    def test_quienes_somos_va_en_pestanas_y_el_indice_lleva_a_lo_que_hay(self):
        self.presentar(publicada=True, que_es='Planta de la UPEC.\nTrabaja por lotes.', capacidades='Molienda y empaque.')
        pagina = self.pagina()
        # Solo los temas escritos, uno visible a la vez.
        self.assertEqual([pestana['clave'] for pestana in pagina.context['pestanas']], ['que_es', 'capacidades'])
        self.assertContains(pagina, 'id="panel-capacidades" aria-labelledby="pestana-capacidades" hidden')
        self.assertEqual([ancla for ancla, _ in pagina.context['indice']], ['quienes', 'video', 'rumbo'])
        self.assertContains(pagina, 'href="#quienes" data-indice="quienes"')

    def test_el_mosaico_invita_a_la_galeria(self):
        self.presentar(publicada=True, que_es='Planta de la UPEC.')
        self.assertNotContains(self.pagina(), 'data-accion="galeria"')
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            contenido = BytesIO()
            Image.new('RGB', (200, 120), (40, 120, 80)).save(contenido, 'PNG')
            MedioInterior.objects.create(unidad=self.unidad, titulo='Línea', imagen=SimpleUploadedFile('linea.png', contenido.getvalue()))
            MedioInterior.objects.create(unidad=self.unidad, titulo='Video', tipo='video', youtube_url='https://youtu.be/IJxxIxTuMb8')
            pagina = self.pagina()
            self.assertEqual(len(pagina.context['fotos_interior']), 1)
            self.assertEqual(pagina.context['total_medios'], 2)
            self.assertContains(pagina, 'data-accion="galeria"')

    def test_las_cifras_salen_de_lo_registrado(self):
        _, equipos = equipos_de_la_unidad(self.unidad)
        cifras = {cifra['etiqueta']: cifra['valor'] for cifra in cifras_de_la_unidad(self.unidad)}
        self.assertEqual(cifras['Equipos especializados'], equipos.count())
        self.assertGreater(cifras['Áreas y espacios'], 0)
        # La ficha cuenta los equipos con la misma consulta.
        self.assertEqual(self.client.get(self.unidad.get_absolute_url()).context['total_equipos'], equipos.count())

    def test_la_ficha_la_ofrece_publicada_y_al_personal_siempre(self):
        url = reverse('conoce_unidad', args=[self.unidad.slug])
        self.assertNotContains(self.client.get(self.unidad.get_absolute_url()), 'data-id="conoce-unidad"')
        self.client.force_login(self.coordinacion)
        self.assertContains(self.client.get(self.unidad.get_absolute_url()), f'data-ui-arg0="{url}"')
        self.client.logout()
        self.presentar(publicada=True)
        self.assertContains(self.client.get(self.unidad.get_absolute_url()), 'data-id="conoce-unidad"')

    def test_el_editor_de_la_planta_la_escribe(self):
        self.client.force_login(self.coordinacion)
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]))
        for fragmento in ('Conoce la unidad: presentación', 'name="presentacion-TOTAL_FORMS"',
                          'name="lineas_accion-TOTAL_FORMS"', 'name="hitos-TOTAL_FORMS"'):
            self.assertContains(editor, fragmento)
