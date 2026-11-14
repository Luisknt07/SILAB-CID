"""Guía FT04 editada sobre su propio formato (contenido HTML acotado).

Cubre: saneado por lista blanca, numeración de figuras y tablas en HTML y
PDF, conversión del formato anterior, carga de figuras en borrador, guardado
por apartado con control de versión y permisos, y el flujo del asistente.
"""

from tests.integration.utiles import verificar_pertenencia

import json
import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.reservas.presentation.guia_html import DocumentoHtml, esta_vacio, html_desde_legado, sanear, texto_a_html
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ImagenGuiaActividad, Reserva
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

WORD = (
    '<html><body><p class=MsoNormal style="margin:0"><span style="font-size:14pt">Hola '
    '<b>mundo</b> <script>alert(1)</script><span style="color:red">rojo</span></span></p>'
    '<h2>Título</h2><table border=1><tr><th>A</th><th>B</th></tr><tr><td><p>1</p><p>2</p></td><td>3</td></tr></table>'
    '<img src="file:///C:/x.png"><ul><li>uno<ul><li>sub</li></ul></li><li><p>dos</p></li></ul>'
    '<div onclick="x()">suelto <a href="javascript:alert(1)">mal</a> <a href="https://ok.org">ok</a></div></body></html>'
)


def imagen_png(nombre='figura.png'):
    buffer = BytesIO()
    Image.new('RGB', (40, 30), (30, 90, 60)).save(buffer, format='PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class SaneadoTests(SimpleTestCase):
    def test_lista_blanca_conserva_estructura_y_descarta_lo_ajeno(self):
        html, avisos = sanear(WORD, 'rico')
        self.assertEqual(
            html,
            '<p>Hola <strong>mundo</strong> rojo</p><h4>Título</h4>'
            '<figure class="guide-table" data-titulo="" data-cabecera="1"><table>'
            '<tr><td>A</td><td>B</td></tr><tr><td>1<br>2</td><td>3</td></tr></table></figure>'
            '<ul><li>uno<ul><li>sub</li></ul></li><li>dos</li></ul>'
            '<p>suelto mal <a href="https://ok.org" target="_blank" rel="noopener">ok</a></p>',
        )
        self.assertEqual(avisos, ['imagen_no_recuperable'])
        # Un apartado de texto no admite titulos ni tablas: se degradan a parrafos.
        texto, _ = sanear(WORD, 'texto')
        self.assertNotIn('<h4>', texto)
        self.assertNotIn('<table', texto)
        self.assertIn('<p>Título</p>', texto)

    def test_figuras_solo_las_autorizadas_y_pasos_con_bloques(self):
        html, avisos = sanear(
            '<figure data-figura="7" data-tamano="ancha" data-titulo="Montaje"><img src="/m.png"></figure>'
            '<figure data-figura="9"></figure>', 'rico', figuras_permitidas=[7],
        )
        self.assertEqual(html, '<figure class="guide-figure" data-figura="7" data-titulo="Montaje" data-fuente="" data-tamano="ancha"></figure>')
        self.assertEqual(avisos, ['figura_no_autorizada'])
        pasos, _ = sanear(
            '<ol><li>Preparar<table><tr><th>a</th></tr></table></li><li><p>Medir</p></li></ol><p>Suelto</p>', 'pasos', [7],
        )
        self.assertEqual(
            pasos,
            '<ol class="guide-steps"><li><p>Preparar</p><figure class="guide-table" data-titulo="" data-cabecera="1">'
            '<table><tr><td>a</td></tr></table></figure></li><li><p>Medir</p></li><li><p>Suelto</p></li></ol>',
        )
        self.assertTrue(esta_vacio('<p></p><ul><li> </li></ul>'))
        self.assertFalse(esta_vacio('<p>a</p>'))

    def test_numeracion_por_orden_de_aparicion_en_html_y_bloques_pdf(self):
        figuras = [{'pk': 7, 'url': '/media/a.png', 'ruta': None, 'titulo': 'A'}, {'pk': 8, 'url': '/media/b.png', 'ruta': None, 'titulo': 'B'}]
        contenido = {
            'fundamento_teorico': '<p>x</p><figure class="guide-figure" data-figura="8" data-titulo="Segunda cargada" data-fuente="" data-tamano="mediana"></figure>'
                                  '<figure class="guide-table" data-titulo="Datos" data-cabecera="1"><table><tr><td>a</td></tr></table></figure>',
            'procedimiento': '<ol class="guide-steps"><li><p>Paso</p><figure class="guide-figure" data-figura="7" data-titulo="Primera cargada" data-fuente="Autor" data-tamano="pequena"></figure></li></ol>',
        }
        documento = DocumentoHtml(contenido, figuras)
        fundamento = documento.html('fundamento_teorico')
        procedimiento = documento.html('procedimiento')
        # La figura cargada en segundo lugar aparece primero en el documento: es la Figura 1.
        self.assertIn('<figcaption>Figura 1. Segunda cargada</figcaption>', fundamento)
        self.assertIn('<figcaption>Tabla 1. Datos</figcaption>', fundamento)
        self.assertIn('<img src="/media/b.png" alt="Segunda cargada">', fundamento)
        self.assertIn('<figcaption>Figura 2. Primera cargada Fuente: Autor</figcaption>', procedimiento)
        self.assertIn('<th>a</th>', fundamento)
        bloques = documento.bloques('procedimiento')
        self.assertEqual(bloques[0]['tipo'], 'paso')
        self.assertEqual(bloques[0]['bloques'][1]['titulo'], 'Figura 2. Primera cargada Fuente: Autor')
        self.assertIn('Tabla 1. Datos', [b['titulo'] for b in documento.bloques('fundamento_teorico') if b['tipo'] == 'tabla'])
        self.assertEqual(DocumentoHtml(contenido, figuras, formato_procedimiento='vinetas').html('procedimiento')[:24], '<ul class="guide-steps">')

    def test_conversion_del_formato_anterior(self):
        convertido = html_desde_legado({
            'objetivos': 'Uno\nDos',
            'resultado_aprendizaje': 'Solo uno',
            'fundamento_teorico': '## Montaje\nConecta.\n| A | B |\n|---|---|\n| 1 | 2 |\n![Figura 1: Esquema](figura:1)\n![Externa](https://ejemplo.org/a.png)',
            'procedimiento': ['Preparar', '| P | V |', 'Medir'],
            'formato_procedimiento': 'numerado',
        }, [{'n': 1, 'pk': 9, 'titulo': 'Esquema', 'url': '/u', 'ruta': None}])
        self.assertEqual(convertido['objetivos'], '<ul><li>Uno</li><li>Dos</li></ul>')
        self.assertEqual(convertido['resultado_aprendizaje'], '<p>Solo uno</p>')
        self.assertIn('<h4>Montaje</h4><p>Conecta.</p><figure class="guide-table"', convertido['fundamento_teorico'])
        self.assertIn('data-figura="9" data-titulo="Esquema"', convertido['fundamento_teorico'])
        # Las imagenes externas no se descargan: queda el enlace.
        self.assertIn('<a href="https://ejemplo.org/a.png"', convertido['fundamento_teorico'])
        self.assertTrue(convertido['procedimiento'].startswith('<ol class="guide-steps"><li><p>Preparar</p><figure class="guide-table"'))
        self.assertEqual(texto_a_html('a\nb', 'texto'), '<ul><li>a</li><li>b</li></ul>')
        self.assertEqual(texto_a_html('1. a\n2. b', 'pasos'), '<ol class="guide-steps"><li><p>a</p></li><li><p>b</p></li></ol>')


class EditorVisualTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-editor', password='clave-segura', email='editor@upec.edu.ec',
            first_name='Docente', last_name='Editor',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.ajeno = User.objects.create_user('ajeno-editor', password='clave-segura')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio del editor', descripcion='Unidad para validar el editor visual.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios', slug='laboratorio-editor',
        )
        catalogo = EquiposServicios.objects.create(codigo='EQ-EDIT-001', nombre='Impresora 3D')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-EDIT-001', equipo=catalogo, laboratorio=cls.unidad,
            estado_unidad='disponible', activa=True,
        )
        cls.area = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='AREA-EDIT', nombre='Área de impresión', tipo='area',
            politica_reserva='tecnico', capacidad=8, reservable=True, activo=True,
        )
        cls.area.equipos_asociados.add(cls.equipo)

    def setUp(self):
        self.client.force_login(self.docente)
        self._media = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._override = override_settings(MEDIA_ROOT=self._media.name)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(self._media.cleanup)

    def _payload(self, **overrides):
        payload = {
            'unidad_id': self.unidad.pk, 'tipo_solicitud': 'recursos',
            'fecha_inicio': '2026-11-19T09:00', 'fecha_fin': '2026-11-19T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'practica_curricular',
            'alcance_beneficiario': 'perfil_solicitante', 'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Impresión 3D de una pieza de prueba', 'origen_programacion': 'adicional',
            'participantes_seleccionados': '[]', 'aceptar_terminos': 'on',
            'incluye_espacio': 'true', 'solicito_espacio': 'true', 'solicito_equipo': 'true',
            'alcance_espacio': 'areas', 'espacios_solicitados': [str(self.area.pk)],
            'unidades_seleccionadas': json.dumps([{'id': self.equipo.pk}]), 'provision_consumibles': 'ninguno',
            'guia_confirmada_solicitante': '1', 'guia_asignatura': 'Fabricación digital',
            'guia_formato_contenido': 'html',
            'guia_medidas_seguridad': '<p>Usar gafas al retirar la pieza.</p>',
            'guia_resultado_aprendizaje': '<p>Imprime una pieza <b>funcional</b>.</p>',
            'guia_objetivos': '<ul><li>Laminar</li><li>Imprimir</li></ul>',
            'guia_formato_procedimiento': 'numerado',
            'guia_procedimiento': '<ol><li>Laminar<table><tr><th>Parámetro</th><th>Valor</th></tr><tr><td>Capa</td><td>0,2 mm</td></tr></table></li><li>Imprimir</li></ol>',
        }
        payload.update(overrides)
        return payload

    def _subir_figura(self, token, nombre='montaje.png'):
        respuesta = self.client.post(reverse('subir_figura_guia'), {
            'imagen': imagen_png(nombre), 'titulo': 'Montaje', 'borrador': token,
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()['figura']

    def test_el_asistente_crea_la_guia_en_html_con_figuras_del_borrador(self):
        token = 'abcdef1234567890abcdef1234567890'
        figura = self._subir_figura(token)
        self.assertIsNone(ImagenGuiaActividad.objects.get(pk=figura['id']).guia_id)
        vacio = self.client.post(reverse('crear_reserva'), self._payload(guia_procedimiento='<ol><li><p></p></li></ol>'))
        self.assertEqual(vacio.status_code, 400, vacio.content)
        self.assertIn('Procedimiento', vacio.json()['error'])

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            guia_imagenes_token=token,
            guia_fundamento_teorico=(
                f'<h2>Marco</h2><p style="color:red">Texto</p><figure data-figura="{figura["id"]}" data-titulo="Montaje" data-tamano="ancha"><img src="x"></figure>'
                '<figure data-figura="999999"></figure><script>alert(1)</script>'
            ),
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        self.assertEqual(guia.contenido['formato_contenido'], 'html')
        self.assertEqual(guia.contenido['resultado_aprendizaje'], '<p>Imprime una pieza <strong>funcional</strong>.</p>')
        self.assertEqual(guia.contenido['objetivos'], '<ul><li>Laminar</li><li>Imprimir</li></ul>')
        self.assertEqual(
            guia.contenido['fundamento_teorico'],
            f'<h4>Marco</h4><p>Texto</p><figure class="guide-figure" data-figura="{figura["id"]}" data-titulo="Montaje" data-fuente="" data-tamano="ancha"></figure>',
        )
        self.assertTrue(guia.contenido['procedimiento'].startswith('<ol class="guide-steps"><li><p>Laminar</p><figure class="guide-table"'))
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.assertEqual(ImagenGuiaActividad.objects.get(pk=figura['id']).guia_id, guia.pk)
        # La politica de la unidad queda aparte del texto del autor.
        self.assertIsInstance(guia.contenido['seguridad_institucional'], list)
        self.assertTrue(guia.contenido['seguridad_institucional'])
        # La politica de la unidad no se duplica dentro de la zona del autor.
        self.assertEqual(guia.contenido['medidas_seguridad'], '<p>Usar gafas al retirar la pieza.</p>')
        self.assertEqual(guia.secciones_faltantes(), [])

        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertEqual(vista.status_code, 200)
        self.assertContains(vista, '<figcaption>Figura 1. Montaje</figcaption>')
        self.assertContains(vista, '<figcaption>Tabla 1.</figcaption>')
        self.assertContains(vista, 'class="guide-figure is-ancha"')
        self.assertContains(vista, '<ol class="guide-steps"><li><p>Laminar</p>')
        # El <script>alert(1)</script> que pegó el autor se descarta; la página conserva sus scripts propios.
        self.assertNotContains(vista, 'alert(1)')
        pdf = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertGreater(len(pdf.content), 3000)

    def test_el_editor_abre_una_guia_anterior_convertida_y_guarda_por_apartado(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            nombre='Práctica anterior', codigo='ANT-01', unidad=self.unidad, creado_por=self.docente,
            estado_publicacion='borrador', visibilidad='privada', activo=True,
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía anterior', numero_version=1, es_estructurada=True,
            estado_publicacion='borrador', visibilidad='participantes', subido_por=self.docente,
            contenido={
                'asignatura': 'Materia', 'carrera_semestre': 'C', 'docente_responsable': 'D',
                'laboratorio': 'L', 'categoria_uso': 'Docencia', 'duracion': '2 h', 'maximo_estudiantes': 10,
                'resultado_aprendizaje': 'Resultado', 'objetivos': 'Uno\nDos',
                'fundamento_teorico': '## Montaje\n| A | B |\n| 1 | 2 |\n![Figura 1: Esquema](figura:1)',
                'medidas_seguridad': ['Usar gafas'], 'formato_procedimiento': 'numerado',
                'procedimiento': ['Preparar', 'Medir'], 'bibliografia': ['Ref'],
                'firma_elaborador': {'tipo': 'aceptacion_electronica_interna', 'huella_sha256': 'x'},
            },
        )
        imagen = ImagenGuiaActividad.objects.create(guia=guia, imagen=imagen_png('esquema.png'), titulo='Esquema', orden=1, tamano=10)

        editor = self.client.get(reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]))
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, 'data-guide-document')
        self.assertContains(editor, f'data-figura="{imagen.pk}"')
        self.assertContains(editor, '<figcaption>Figura 1. Esquema</figcaption>')
        self.assertContains(editor, 'data-guia-campo="procedimiento" data-guia-tipo="pasos"')
        self.assertContains(editor, 'name="formato_contenido" value="html"')
        self.assertContains(editor, 'guia_editor.js')
        # El registro no cambia por abrirlo.
        guia.refresh_from_db()
        self.assertNotIn('formato_contenido', guia.contenido)

        url = reverse('guardar_contenido_guia', args=[guia.pk])
        version = guia.actualizado_en.isoformat()
        guardado = self.client.post(url, json.dumps({
            'campos': {
                'fundamento_teorico': '<p>Nuevo fundamento</p><figure data-figura="%d" data-titulo="Esquema"></figure>' % imagen.pk,
                'asignatura': 'No se puede tocar desde aquí',
                'equipos': ['Otro equipo'],
            },
            'formato_procedimiento': 'vinetas',
            'version_base': version,
        }), content_type='application/json')
        self.assertEqual(guardado.status_code, 200, guardado.content)
        datos = guardado.json()
        self.assertTrue(datos['success'])
        self.assertIn('<figcaption>Figura 1. Esquema</figcaption>', datos['zonas']['fundamento_teorico'])
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['formato_contenido'], 'html')
        self.assertEqual(guia.contenido['fundamento_teorico'], '<p>Nuevo fundamento</p><figure class="guide-figure" data-figura="%d" data-titulo="Esquema" data-fuente="" data-tamano="mediana"></figure>' % imagen.pk)
        # El resto se convirtio con la misma regla del editor; los datos protegidos no cambian.
        self.assertEqual(guia.contenido['objetivos'], '<ul><li>Uno</li><li>Dos</li></ul>')
        self.assertEqual(guia.contenido['asignatura'], 'Materia')
        self.assertNotEqual(guia.contenido.get('equipos'), ['Otro equipo'])
        self.assertEqual(guia.contenido['formato_procedimiento'], 'vinetas')
        self.assertEqual(guia.contenido['origen_campos']['fundamento_teorico'], 'manual')
        # Cualquier cambio invalida la aceptacion anterior.
        self.assertNotIn('firma_elaborador', guia.contenido)

        # Una version mas reciente no se sobrescribe en silencio.
        conflicto = self.client.post(url, json.dumps({'campos': {'objetivos': '<p>x</p>'}, 'version_base': version}), content_type='application/json')
        self.assertEqual(conflicto.status_code, 409)
        self.assertTrue(conflicto.json()['conflicto'])
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['objetivos'], '<ul><li>Uno</li><li>Dos</li></ul>')

        # Solo quien puede editar la guia guarda o carga figuras.
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(url, json.dumps({'campos': {}}), content_type='application/json').status_code, 403)
        self.assertEqual(self.client.post(reverse('subir_figura_guia'), {'imagen': imagen_png(), 'guia_id': guia.pk}).status_code, 403)
        self.assertEqual(self.client.post(reverse('subir_figura_guia'), {'imagen': imagen_png(), 'borrador': 'x'}).status_code, 400)
        self.assertEqual(self.client.post(reverse('subir_figura_guia'), {'imagen': SimpleUploadedFile('n.txt', b'no', content_type='text/plain'), 'borrador': 'abcdefgh12345678'}).status_code, 400)

        # Guardar el formulario completo con una version base antigua tampoco sobrescribe.
        self.client.force_login(self.docente)
        formulario = self.client.post(reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]), {
            'actividad_existente': str(actividad.pk), 'titulo': 'Guía anterior', 'asignatura': 'Materia',
            'formato_contenido': 'html', 'formato_procedimiento': 'numerado', 'version_base': version,
            'resultado_aprendizaje': '<p>R</p>', 'objetivos': '<p>O</p>', 'procedimiento': '<ol><li>P</li></ol>',
            'accion': 'guardar',
        })
        self.assertEqual(formulario.status_code, 200)
        self.assertContains(formulario, 'cambió después de que abriste el editor')
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['objetivos'], '<ul><li>Uno</li><li>Dos</li></ul>')

    def test_una_guia_publicada_no_se_edita_desde_el_endpoint(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            nombre='Publicada', codigo='PUB-01', unidad=self.unidad, creado_por=self.docente,
            estado_publicacion='publicado', visibilidad='unidad', activo=True,
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Publicada', numero_version=1, es_estructurada=True, es_vigente=True,
            estado_publicacion='publicada', visibilidad='unidad', subido_por=self.docente,
            contenido={'formato_contenido': 'html', 'objetivos': '<p>O</p>', 'asignatura': 'M'},
        )
        respuesta = self.client.post(reverse('guardar_contenido_guia', args=[guia.pk]), json.dumps({'campos': {'objetivos': '<p>X</p>'}}), content_type='application/json')
        self.assertEqual(respuesta.status_code, 403)
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['objetivos'], '<p>O</p>')

    def test_el_asistente_publica_la_plantilla_del_documento_y_el_editor(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, '<template id="guiaDocumentoPlantilla">')
        self.assertContains(pagina, 'data-guide-mode="asistente"')
        self.assertContains(pagina, 'guia_editor.js')
        self.assertContains(pagina, 'data-figure-upload-url=')
        self.assertContains(pagina, 'guias_practica.css')
