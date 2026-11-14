"""2.6 Guías de práctica: una guía FT04 de referencia por proceso de referencia de la planta.

La guía se arma desde el proceso (objetivos, fundamento, equipos, materiales,
procedimiento con sus controles, residuos y evaluación), se publica en 2.6 y el
docente la adapta: una nueva carga no pisa lo que haya editado.
"""
from django.core.management import call_command
from django.test import TestCase

from apps.reservas.models.reservas import GuiaActividadReserva
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.directorio_unidades.models.core import Unidad


class GuiasDeReferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        cls.unidad = Unidad.objects.get(slug='planta-piloto-lacteos')

    def test_cada_proceso_de_referencia_tiene_su_guia_publicada(self):
        recetas = Receta.objects.filter(unidad=self.unidad, origen='referencia')
        guias = GuiaActividadReserva.objects.filter(actividad__unidad=self.unidad, es_estructurada=True)
        self.assertEqual(guias.count(), recetas.count())
        queso = guias.get(codigo_guia='LAC-GUI-QUESO-100')
        self.assertEqual(queso.estado_publicacion, 'publicada')
        self.assertEqual(queso.visibilidad, 'publica')
        self.assertTrue(queso.es_vigente)
        self.assertEqual(queso.familia.nombre, 'Quesos')
        contenido = queso.contenido
        for clave in ('asignatura', 'resultado_aprendizaje', 'objetivos', 'procedimiento'):
            self.assertTrue(contenido[clave], clave)
        self.assertEqual(len(contenido['procedimiento']), Receta.objects.get(codigo='LAC-REC-QUESO-100').etapas.count())
        self.assertTrue(any('PCC (inocuidad)' in paso for paso in contenido['procedimiento']))
        self.assertTrue(contenido['fundamento_teorico'])

    def test_se_publican_en_la_seccion_2_6(self):
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'Guía de práctica: Queso fresco')

    def test_la_carga_no_pisa_la_guia_que_el_docente_adapto(self):
        guia = GuiaActividadReserva.objects.get(codigo_guia='LAC-GUI-QUESO-100')
        guia.contenido = {**guia.contenido, 'asignatura': 'Lácteos II'}
        guia.save(update_fields=['contenido'])
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['asignatura'], 'Lácteos II')
        self.assertEqual(GuiaActividadReserva.objects.filter(codigo_guia='LAC-GUI-QUESO-100').count(), 1)

    def test_una_guia_quitada_vuelve_a_crearse_sin_chocar_con_su_ficha(self):
        GuiaActividadReserva.objects.get(codigo_guia='LAC-GUI-YOGUR-100').delete()
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        self.assertTrue(GuiaActividadReserva.objects.filter(codigo_guia='LAC-GUI-YOGUR-100').exists())
