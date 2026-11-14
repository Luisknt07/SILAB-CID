from copy import deepcopy

from django.http import QueryDict

from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.pac_universitario import leer_pac, preparar_pac
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.utiles import abrir_entrega


class CentroCostoNecesidadesTests(BaseDeRedaccion):
    def adscribir(self):
        dependencia = DependenciaAcademica.objects.create(nombre='Decanato de prueba de compras',
            centro_costo='Centro agrupador institucional confirmado')
        self.unidad.adscrita_a = dependencia
        self.unidad.save(update_fields=['adscrita_a'])
        return dependencia

    def test_el_centro_confirmado_de_la_dependencia_prevalece_sobre_el_post(self):
        self.adscribir()
        original = dict(centro_costo='Otro centro de un borrador anterior', compras=[])
        anterior = deepcopy(original)
        preparado = preparar_pac(original, unidad=self.unidad)
        self.assertEqual(original, anterior)
        self.assertEqual(preparado['centro_costo'], 'Centro agrupador institucional confirmado')
        post = QueryDict('centro_costo=Texto+alterado', mutable=True)
        leido = leer_pac(post, preparado, unidad=self.unidad)
        self.assertEqual(leido['centro_costo'], preparado['centro_costo'])

    def test_el_editor_muestra_el_centro_automatico_sin_reescribir_el_borrador(self):
        self.adscribir()
        documento = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        contenido = dict(compras=[], centro_costo='Centro anterior', firma_nombre='Responsable registrado',
                         firma_cargo='Responsable de la unidad')
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido=contenido)
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(self.ruta_editor(documento))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'name="centro_costo" value="Centro agrupador institucional confirmado" maxlength="300" readonly')
        self.assertContains(respuesta, 'Decanato de prueba de compras')
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido, contenido)
