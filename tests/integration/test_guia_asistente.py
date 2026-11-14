"""Paso final del asistente: la guia FT04 que nace de la reserva.

Verificado a mano con las capturas del usuario: la vista previa se abria
detras del modal (y aun asi registraba su firma), habia dos botones de vista
previa, la asignatura se copiaba del nombre de la practica y el nombre
estaba limitado a 30 caracteres.
"""

from tests.integration.utiles import verificar_pertenencia

import json
import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class GuiaDesdeElAsistenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-guia-asistente', password='clave-segura',
            email='guia-asistente@upec.edu.ec', first_name='Docente', last_name='Guía',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de guías',
            descripcion='Unidad para validar la guía integrada.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-guias',
        )
        catalogo = EquiposServicios.objects.create(codigo='EQ-GUIA-001', nombre='Microscopio óptico')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-GUIA-001', equipo=catalogo, laboratorio=cls.unidad,
            estado_unidad='disponible', activa=True,
        )
        cls.area = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='AREA-GUIA', nombre='Área de microscopía',
            tipo='area', politica_reserva='tecnico', capacidad=8, reservable=True, activo=True,
        )
        cls.area.equipos_asociados.add(cls.equipo)

    def setUp(self):
        self.client.force_login(self.docente)

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
            'referencia_actividad': 'Uso del microscopio óptico y tinción de Gram',
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
            'guia_asignatura': 'Microbiología general',
            'guia_resultado_aprendizaje': 'Identifica bacterias Gram positivas y negativas.',
            'guia_objetivos': 'Preparar el frotis.\nAplicar la tinción.\nObservar al microscopio.',
            'guia_formato_procedimiento': 'numerado',
            'guia_procedimiento': 'Preparar el frotis\nFijar la muestra\nTeñir\nObservar a 100x',
        }
        payload.update(overrides)
        return payload

    def test_la_asignatura_es_obligatoria_y_no_se_copia_del_nombre_de_la_practica(self):
        sin_asignatura = self.client.post(reverse('crear_reserva'), self._payload(guia_asignatura=''))
        self.assertEqual(sin_asignatura.status_code, 400, sin_asignatura.content)
        self.assertIn('Asignatura', sin_asignatura.json()['error'])

        creada = self.client.post(reverse('crear_reserva'), self._payload())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva = Reserva.objects.get(pk=creada.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        self.assertEqual(guia.contenido['asignatura'], 'Microbiología general')
        self.assertEqual(reserva.referencia_actividad, 'Uso del microscopio óptico y tinción de Gram')
        self.assertNotEqual(guia.contenido['asignatura'], reserva.referencia_actividad)

    def test_el_nombre_de_la_practica_admite_hasta_120_caracteres_sin_patrones(self):
        largo = (
            'Control de calidad en la industria alimentaria: '
            'Análisis de acidez en leche comercial mediante titulación'
        )
        self.assertLessEqual(len(largo), 120)
        aceptada = self.client.post(reverse('crear_reserva'), self._payload(referencia_actividad=largo))
        self.assertEqual(aceptada.status_code, 200, aceptada.content)
        self.assertEqual(Reserva.objects.get(pk=aceptada.json()['reserva_id']).referencia_actividad, largo)

        excesivo = self.client.post(
            reverse('crear_reserva'),
            self._payload(referencia_actividad='A' * 121, fecha_inicio='2026-11-20T09:00', fecha_fin='2026-11-20T11:00'),
        )
        self.assertEqual(excesivo.status_code, 400, excesivo.content)
        self.assertIn('hasta 120 caracteres', excesivo.json()['error'])

        patron = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                referencia_actividad='[Problema real]: [Técnica académica]',
                fecha_inicio='2026-11-21T09:00', fecha_fin='2026-11-21T11:00',
            ),
        )
        self.assertEqual(patron.status_code, 400, patron.content)
        self.assertIn('corchetes', patron.json()['error'])

    def test_los_participantes_descargan_solo_la_guia_aprobada(self):
        creada = self.client.post(reverse('crear_reserva'), self._payload())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva = Reserva.objects.get(pk=creada.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        url = reverse('ver_guia_actividad', args=[guia.pk]) + '?download=1'
        # La persona autora descarga su version en revision.
        self.assertEqual(self.client.get(url).status_code, 200)

        participante = get_user_model().objects.create_user('participante-guia', password='clave-segura')
        reserva.actividad_catalogo.participantes_autorizados.add(participante)
        self.client.force_login(participante)
        self.assertEqual(self.client.get(url).status_code, 403)
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(estado_publicacion='publicada', permite_descarga=True)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_el_asistente_publica_una_sola_vista_previa_visible_sobre_el_modal(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)

        with open(os.path.join(settings.BASE_DIR, 'apps', 'reservas', 'static', 'portal', 'js', 'pages', 'unidades', 'reservas', 'reservation_wizard.js'), encoding='utf-8') as archivo:
            js = archivo.read()
        from django.contrib.staticfiles import finders
        with open(finders.find('portal/css/pages/unidades/reservation_wizard.css'), encoding='utf-8') as archivo:
            css = archivo.read()

        # Un solo acceso al dialogo "Revisar y completar guia"; la revision final solo firma.
        self.assertEqual(js.count('Revisar y completar guía</button>'), 1)
        self.assertNotIn('data-guide-final-preview', js)
        # El dialogo vive dentro del formulario (foco y envio de los campos que se
        # trasladan al documento) y ofrece la vista previa en PDF del borrador.
        self.assertIn('form.appendChild(guidePreview);', js)
        self.assertIn('data-guide-pdf-preview', js)
        self.assertIn("doc.querySelectorAll('[data-guide-source]')", js)
        self.assertContains(pagina, 'data-guide-source="materiales_complementarios"')
        self.assertContains(pagina, 'data-guide-source="bibliografia"')
        self.assertContains(pagina, '<span>11</span> Bibliografía / referencias')
        self.assertNotContains(pagina, 'Plantilla institucional FT04: una sola fuente')
        self.assertNotIn('Visualizar guía completa en HTML', js)
        # La firma de la revision se registra al aceptar, no al abrir el dialogo.
        self.assertIn('guidePreviewSignature = currentGuideSignature();\n      if (guideConfirmation) {', js)
        self.assertNotIn("guidePreviewSignature = missing.length ? '' : currentGuideSignature();", js)
        self.assertIn('data-naming-pattern="[Problema real]: [Técnica académica]"', js)
        self.assertIn('name="guia_asignatura"', js)
        self.assertNotIn('guideSubjectInput.value = activity;', js)
        # Contenido listo para incluir en cada apartado academico.
        for campo in ('guia_resultado_aprendizaje', 'guia_objetivos', 'guia_fundamento_teorico',
                      'guia_medidas_seguridad', 'guia_procedimiento', 'guia_resultados_esperados',
                      'guia_criterios_evaluacion'):
            self.assertIn(f'      {campo}: [', js)
        # Los fragmentos se insertan desde la barra del editor visual, no desde <details>.
        self.assertNotIn('data-guide-snippet=', js)
        self.assertIn('function ensureGuideEditor()', js)
        self.assertIn('name="guia_formato_contenido" value="html"', js)
        # Insumos: el filtro consulta el catalogo (la cascada lo mueve al paso 3).
        self.assertIn('const inventoryRoot = inventoryCatalog || requirementsGrid;', js)
        self.assertNotIn("requirementsGrid.querySelectorAll('.reservation-consumable')", js)
        # Vista previa desde el inicio, con el motivo junto al boton y aviso de plantilla anterior.
        self.assertIn('data-guide-preview-footnote', js)
        self.assertIn('guidePreview.scrollTop = 0;', js)
        self.assertIn('rw-stale-notice', js)
        self.assertIn('function guideSignatureChanges(previous, current)', js)
        self.assertIn('Tabla de registro de datos', js)
        self.assertRegex(css, r'\.reservation-guide-preview \{\n\s+position: fixed;\n[^}]*z-index: 100700 !important;')

    def test_la_vista_previa_pdf_del_borrador_usa_el_mismo_generador(self):
        respuesta = self.client.post(reverse('vista_previa_pdf_guia'), {
            'unidad_id': self.unidad.pk,
            'guia_formato_contenido': 'html',
            'guia_asignatura': 'Manufactura digital',
            'guia_resultado_aprendizaje': '<p>Configura una impresión 3D con trazabilidad.</p>',
            'guia_objetivos': '<ul><li>Preparar el modelo.</li></ul>',
            'guia_procedimiento': '<ol class="guide-steps"><li><p>Verificar el equipo.</p></li></ol>',
            'guia_bibliografia': '@book{prusa2024, author = {Prusa, Josef}, title = {Impresión 3D}, publisher = {Prusa Research}, year = {2024}}',
            'guia_materiales_complementarios': 'Guía de laminado | https://ejemplo.org/laminado',
            'automaticos': json.dumps({
                'title': 'Guía de práctica: Impresión de una pieza',
                'activity': 'Impresión de una pieza de prueba',
                'subject': 'Manufactura digital',
                'career': 'Computación · Quinto semestre',
                'responsible': 'Docente de prueba',
                'purpose': 'Docencia y práctica curricular',
                'duration': '2 horas',
                'participants': '3 personas',
                'equipment': ['Impresora 3D FDM'],
                'software': ['PrusaSlicer 2.9'],
                'consumables': 'Filamento PLA rojo 1,75 mm · 120 g',
                'safety': 'Usar guantes\nVerificar el estado del equipo',
                'waste': 'Separar residuos plásticos',
            }),
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.content[:200])
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertIn('vista-previa', respuesta['Content-Disposition'])

        sin_unidad = self.client.post(reverse('vista_previa_pdf_guia'), {'unidad_id': '999999'})
        self.assertEqual(sin_unidad.status_code, 404)

    def test_las_firmas_se_configuran_y_exigen_nombre_y_cargo_de_los_roles_incluidos(self):
        incompleta = self.client.post(reverse('crear_reserva'), self._payload(
            guia_firmas=json.dumps({
                'elaborado': {'activo': True, 'nombre': '', 'cargo': 'Docente responsable'},
                'revisado': {'activo': True, 'nombre': '', 'cargo': ''},
                'aprobado': {'activo': False},
            }),
        ))
        self.assertEqual(incompleta.status_code, 400, incompleta.content)
        self.assertIn('Revisado por: nombre', incompleta.json()['error'])

        creada = self.client.post(reverse('crear_reserva'), self._payload(
            guia_firmas=json.dumps({
                'elaborado': {'activo': True, 'nombre': 'Docente Autor', 'cargo': 'Docente responsable'},
                'revisado': {'activo': True, 'nombre': 'Coordinadora de Carrera', 'cargo': 'Coordinación académica'},
                'aprobado': {'activo': False},
            }),
        ))
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva = Reserva.objects.get(pk=creada.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        firmas = guia.contenido['firmas']
        self.assertTrue(firmas['elaborado']['activo'])
        self.assertEqual(firmas['revisado']['nombre'], 'Coordinadora de Carrera')
        self.assertFalse(firmas['aprobado']['activo'])
        self.assertEqual(guia.secciones_faltantes(), [])

        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertContains(vista, 'Coordinadora de Carrera')
        self.assertContains(vista, 'Coordinación académica')
        self.assertContains(vista, 'REVISADO POR')
        self.assertNotContains(vista, 'APROBADO POR')
        pdf = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_una_guia_sin_configuracion_de_firmas_conserva_las_tres_columnas(self):
        creada = self.client.post(reverse('crear_reserva'), self._payload())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva = Reserva.objects.get(pk=creada.json()['reserva_id'])
        guia = GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)
        # Sin firmas indicadas, solo firma quien elabora.
        self.assertFalse(guia.contenido['firmas']['revisado']['activo'])
        del guia.contenido['firmas']
        guia.save(update_fields=['contenido'])
        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertContains(vista, 'REVISADO POR')
        self.assertContains(vista, 'APROBADO POR')
