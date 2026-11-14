from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.recursos.admin.contenido import RecursoAdmin, RecursoInline
from apps.documentos.presentation.expediente import carpeta_del_expediente
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests


class ContenidosSinExpedienteTests(EditorRecursosUnidadTests):
    """Los contenidos de la unidad no se mezclan con los documentos que genera el expediente."""

    def setUp(self):
        super().setUp()
        self.planeacion = carpeta_del_expediente(self.unidad, 2026, 'planeacion')
        self.informe = Recurso.objects.create(
            unidad=self.unidad, carpeta=self.planeacion, nombre='Plan semestral de prácticas · v1',
            descripcion='Generado por el sistema', visibilidad='interna',
            archivo=SimpleUploadedFile('plan.pdf', b'%PDF-1.4'))
        self.informe.archivo.close()
        self.contenido = Recurso.objects.create(
            unidad=self.unidad, carpeta=self.carpeta, nombre='Simulador XR', descripcion='Práctica',
            archivo=SimpleUploadedFile('simulador.html', b'<html>XR</html>'))
        self.contenido.archivo.close()

    def test_el_expediente_marca_sus_carpetas(self):
        self.assertTrue(self.planeacion.del_expediente)
        self.assertTrue(self.planeacion.carpeta_padre.del_expediente)
        self.assertEqual(self.planeacion.carpeta_padre.nombre, 'Expediente de calidad 2026')
        self.assertFalse(CarpetaRecurso.objects.get(pk=self.carpeta.pk).del_expediente)

    def test_una_carpeta_manual_con_el_mismo_nombre_pasa_al_expediente(self):
        manual = CarpetaRecurso.objects.create(unidad=self.unidad, nombre='Expediente de calidad 2027')
        self.assertEqual(carpeta_del_expediente(self.unidad, 2027, 'ejecucion').carpeta_padre, manual)
        manual.refresh_from_db()
        self.assertTrue(manual.del_expediente)

    def test_la_ficha_de_la_unidad_solo_muestra_contenidos(self):
        self.client.force_login(self.usuario)
        pagina = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]))
        self.assertContains(pagina, 'Simulador XR')
        self.assertNotContains(pagina, 'Plan semestral de prácticas')
        self.assertNotContains(pagina, 'Expediente de calidad 2026')
        recursos = RecursoInline(Unidad, admin.site)
        self.assertEqual(list(recursos.get_queryset(self.request)), [self.contenido])
        self.assertNotIn(self.informe, recursos.get_formset(self.request, self.unidad).form.base_fields["reemplaza_a"].queryset)
        # El organizador de la ficha tampoco los lista.
        organizador = self.client.get(reverse('admin:directorio_unidades_unidad_contenidos', args=[self.unidad.pk]))
        self.assertContains(organizador, 'Simulador XR')
        self.assertNotContains(organizador, 'Expediente de calidad 2026')
        self.assertNotContains(organizador, 'Plan semestral de prácticas')

    def test_no_se_ofrecen_como_destino_de_un_contenido(self):
        formulario = RecursoInline(Unidad, admin.site).get_formset(self.request, self.unidad).form
        self.assertNotIn(self.planeacion, formulario.base_fields['carpeta'].queryset)
        self.assertIn(self.carpeta, formulario.base_fields['carpeta'].queryset)
        # Ni el organizador los ofrece para llevar un archivo suelto.
        self.client.force_login(self.usuario)
        organizador = self.client.get(reverse('admin:directorio_unidades_unidad_contenidos', args=[self.unidad.pk]))
        self.assertEqual([carpeta for carpeta, _ruta in organizador.context['carpetas_con_ruta']], [self.carpeta.pk])

    def test_la_lista_general_de_recursos_tampoco_los_mezcla(self):
        consulta = RecursoAdmin(Recurso, admin.site).get_queryset(self.request)
        self.assertIn(self.contenido, consulta)
        self.assertNotIn(self.informe, consulta)

    def test_el_visor_nunca_los_publica(self):
        # Aunque alguien les asigne un módulo, siguen fuera del visor.
        CarpetaRecurso.objects.filter(del_expediente=True).update(modulo_config=self.modulo)
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(self.unidad.get_absolute_url()), 'Plan semestral de prácticas')
