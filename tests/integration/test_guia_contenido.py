"""Tablas e imágenes en el fundamento y el procedimiento de la guía FT04."""

from tests.integration.utiles import verificar_pertenencia

import json
import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.reservas.presentation.guia_contenido import bloques_enriquecidos, html_bloques, html_procedimiento, parrafos_procedimiento, pasos_procedimiento, texto_procedimiento_parrafos
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

TEXTO = (
    '## Montaje\n'
    'Conecta la fuente y el sensor.\n'
    '| Parámetro | Valor |\n'
    '|---|---|\n'
    '| Voltaje | 5 V |\n'
    '| Corriente | 20 mA |\n'
    '![Figura 1: Esquema del montaje](figura:1)\n'
    '- Verifica la polaridad\n'
    '- Registra la lectura\n'
)


def imagen_png(nombre='figura.png', color=(30, 90, 60)):
    buffer = BytesIO()
    Image.new('RGB', (48, 32), color).save(buffer, format='PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class ContenidoEnriquecidoTests(TestCase):
    def test_bloques_y_html_de_fundamento(self):
        bloques = bloques_enriquecidos(TEXTO)
        self.assertEqual([bloque['tipo'] for bloque in bloques], ['subtitulo', 'parrafo', 'tabla', 'imagen', 'lista'])
        self.assertEqual(bloques[2]['filas'], [['Parámetro', 'Valor'], ['Voltaje', '5 V'], ['Corriente', '20 mA']])

        figuras = [{'n': 1, 'titulo': 'Esquema', 'url': '/media/f1.png', 'ruta': None}]
        html = html_bloques(bloques, figuras)
        self.assertIn('<h4>Montaje</h4>', html)
        self.assertIn('<table class="guide-table"><thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>', html)
        self.assertIn('<td>Corriente</td><td>20 mA</td>', html)
        self.assertIn('<figure class="guide-figure"><img src="/media/f1.png" alt="Figura 1: Esquema del montaje">', html)
        self.assertIn('<ul><li>Verifica la polaridad</li>', html)
        # Sin figura cargada ni URL, se avisa en lugar de romper el documento.
        self.assertIn('imagen no disponible', html_bloques(bloques, []))
        self.assertIn('<img src="https://ejemplo.org/a.png"', html_bloques(bloques_enriquecidos('![Externa](https://ejemplo.org/a.png)')))
        # Nada del usuario se interpreta como HTML.
        self.assertIn('&lt;script&gt;', html_bloques(bloques_enriquecidos('| <script> |')))

    def test_procedimiento_con_adjuntos_por_paso_y_parrafos(self):
        items = ['Preparar', '| Reactivo | Cantidad |', '| NaOH | 10 mL |', 'Medir', '![Figura 1: Bureta](figura:1)']
        pasos = pasos_procedimiento(items, 'numerado')
        self.assertEqual([paso['texto'] for paso in pasos], ['Preparar', 'Medir'])
        self.assertEqual(pasos[0]['adjuntos'][0]['tipo'], 'tabla')
        self.assertEqual(pasos[1]['adjuntos'][0]['tipo'], 'imagen')
        html = html_procedimiento(items, 'numerado', [{'n': 1, 'titulo': '', 'url': '/media/b.png', 'ruta': None}])
        self.assertIn('<ol><li>Preparar<div class="guide-table-wrap">', html)
        self.assertIn('<li>Medir<figure class="guide-figure">', html)
        self.assertIn('<ul><li>Preparar', html_procedimiento(['Preparar'], 'vinetas'))

        texto = 'Primer párrafo\ncontinúa aquí.\n\n| A | B |\n| 1 | 2 |\n\nSegundo párrafo.'
        parrafos = parrafos_procedimiento(texto)
        self.assertEqual(parrafos, ['Primer párrafo continúa aquí.', '| A | B |', '| 1 | 2 |', 'Segundo párrafo.'])
        self.assertEqual(texto_procedimiento_parrafos(parrafos), 'Primer párrafo continúa aquí.\n\n| A | B |\n| 1 | 2 |\n\nSegundo párrafo.')
        self.assertIn('<p>Primer párrafo continúa aquí.</p><div class="guide-table-wrap">', html_procedimiento(parrafos, 'parrafos'))


class FigurasEnLaGuiaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-figuras', password='clave-segura',
            email='figuras@upec.edu.ec', first_name='Docente', last_name='Figuras',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de figuras',
            descripcion='Unidad para validar figuras y tablas en la guía.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-figuras',
        )
        catalogo = EquiposServicios.objects.create(codigo='EQ-FIG-001', nombre='Fuente de poder')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-FIG-001', equipo=catalogo, laboratorio=cls.unidad,
            estado_unidad='disponible', activa=True,
        )
        cls.area = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='AREA-FIG', nombre='Área de electrónica',
            tipo='area', politica_reserva='tecnico', capacidad=8, reservable=True, activo=True,
        )
        cls.area.equipos_asociados.add(cls.equipo)

    def setUp(self):
        self.client.force_login(self.docente)
        self._media = tempfile.TemporaryDirectory()
        self._override = override_settings(MEDIA_ROOT=self._media.name)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(self._media.cleanup)

    def _payload(self, **overrides):
        payload = {
            'unidad_id': self.unidad.pk,
            'tipo_solicitud': 'recursos',
            'fecha_inicio': '2026-11-19T09:00',
            'fecha_fin': '2026-11-19T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Caracterización de una fuente de poder regulada',
            'origen_programacion': 'adicional',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'incluye_espacio': 'true',
            'solicito_espacio': 'true',
            'solicito_equipo': 'true',
            'alcance_espacio': 'areas',
            'espacios_solicitados': [str(self.area.pk)],
            'unidades_seleccionadas': json.dumps([{'id': self.equipo.pk}]),
            'provision_consumibles': 'ninguno',
            'guia_confirmada_solicitante': '1',
            'guia_asignatura': 'Electrónica analógica',
            'guia_resultado_aprendizaje': 'Mide y registra parámetros eléctricos con seguridad.',
            'guia_objetivos': 'Configurar la fuente.\nMedir voltaje y corriente.',
            'guia_fundamento_teorico': TEXTO,
            'guia_formato_procedimiento': 'numerado',
            'guia_procedimiento': (
                'Preparar el montaje\n'
                '| Parámetro | Valor esperado |\n'
                '| Voltaje | 5 V |\n'
                '![Figura 2: Conexión de la carga](figura:2)\n'
                'Registrar las lecturas'
            ),
        }
        payload.update(overrides)
        return payload

    def test_las_figuras_se_guardan_y_se_muestran_en_html_y_pdf(self):
        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            guia_imagenes=[imagen_png('esquema.png'), imagen_png('carga.png', (120, 40, 40))],
            guia_imagenes_titulos=['Esquema del montaje', 'Conexión de la carga'],
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        figuras = list(guia.imagenes.all())
        self.assertEqual([(figura.orden, figura.titulo) for figura in figuras], [(1, 'Esquema del montaje'), (2, 'Conexión de la carga')])
        self.assertEqual(guia.contenido['procedimiento'], [
            'Preparar el montaje', '| Parámetro | Valor esperado |', '| Voltaje | 5 V |',
            '![Figura 2: Conexión de la carga](figura:2)', 'Registrar las lecturas',
        ])

        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertEqual(vista.status_code, 200)
        self.assertContains(vista, '<table class="guide-table">', count=2)
        self.assertContains(vista, '<figure class="guide-figure"><img src="/media/', count=2)
        self.assertContains(vista, 'Figura 2: Conexión de la carga')
        self.assertContains(vista, '<li>Preparar el montaje<div class="guide-table-wrap">')

        pdf = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_un_archivo_que_no_es_imagen_se_rechaza_antes_de_crear_la_reserva(self):
        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            guia_imagenes=[SimpleUploadedFile('notas.txt', b'no soy una imagen', content_type='text/plain')],
        ))
        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        self.assertIn('JPG, PNG, GIF o WebP', respuesta.json()['error'])
        self.assertFalse(Reserva.objects.exists())

        falsa = self.client.post(reverse('crear_reserva'), self._payload(
            guia_imagenes=[SimpleUploadedFile('falsa.png', b'no soy png', content_type='image/png')],
        ))
        self.assertEqual(falsa.status_code, 400, falsa.content)
        self.assertIn('no es una imagen válida', falsa.json()['error'])

    def test_el_editor_agrega_y_elimina_figuras(self):
        url = reverse('nueva_guia_practica', args=[self.unidad.slug])
        datos = {
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'nombre_actividad': 'Caracterización de fuentes reguladas',
            'codigo_actividad': 'ACT-FIG-01',
            'descripcion_actividad': 'Práctica de electrónica.',
            'titulo': 'Guía de caracterización de fuentes',
            'codigo_guia': 'GUIA-FIG-01',
            'asignatura': 'Electrónica analógica',
            'carrera_semestre': 'Computación · cuarto semestre',
            'docente_responsable': 'Docente Figuras',
            'categoria_uso': 'Docencia y práctica curricular',
            'duracion': '2 horas',
            'maximo_estudiantes': '20',
            'resultado_aprendizaje': 'Mide parámetros eléctricos.',
            'objetivos': 'Configurar la fuente.',
            'fundamento_teorico': '![Figura 1: Esquema](figura:1)',
            'equipos': 'Fuente de poder',
            'materiales': 'Cables',
            'medidas_seguridad': 'Verificar el aislamiento.',
            'formato_procedimiento': 'numerado',
            'procedimiento': 'Preparar\nMedir',
            'resultados_esperados': 'Tabla de lecturas.',
            'criterios_evaluacion': 'Precisión.',
            'manejo_residuos': 'No aplica.',
            'accion': 'guardar',
            'guia_imagenes': [imagen_png('esquema.png')],
            'guia_imagenes_titulos_texto': 'Esquema',
        }
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b'')[:800])
        guia = GuiaActividadReserva.objects.get(titulo='Guía de caracterización de fuentes')
        figura = guia.imagenes.get()
        self.assertEqual((figura.orden, figura.titulo), (1, 'Esquema'))

        editor = self.client.get(reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]))
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, 'enctype="multipart/form-data"')
        self.assertContains(editor, 'name="eliminar_imagenes"')
        # El editor visual muestra la figura convertida, citada por su identificador estable.
        self.assertContains(editor, f'data-figura="{figura.pk}"')
        self.assertContains(editor, '<figcaption>Figura 1. Esquema</figcaption>')

        datos.pop('guia_imagenes')
        datos['eliminar_imagenes'] = [str(figura.pk)]
        eliminada = self.client.post(reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]), datos)
        self.assertEqual(eliminada.status_code, 302, getattr(eliminada, 'content', b'')[:800])
        self.assertEqual(guia.imagenes.count(), 0)

        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertContains(vista, 'imagen no disponible')
