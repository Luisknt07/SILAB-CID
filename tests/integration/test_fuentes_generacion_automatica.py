"""La conformidad de un anexo se liga a las fuentes presentes al generarlo."""
from pathlib import Path
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.automatizacion_documental import huella
from apps.documentos.presentation.confianza_documental import AUDITORIA_PROCEDENCIA, comprobar_procedencia
from apps.documentos.presentation.expediente import _generar, construir_expediente
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class FuentesGeneracionAutomaticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='qa-fuentes-generacion')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio fuentes QA', slug='qa-fuentes-generacion',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2025, 1, 1))
        documentos = construir_expediente(cls.unidad, 2025)
        cls.anexo_id = next(d.pk for d in documentos if d.exigido.codigo == 'PRESTAMOS-EQUIPOS' and d.corte == 'B')

    def setUp(self):
        self.temporal = TemporaryDirectory(prefix='citt-qa-fuentes-generacion-')
        self.addCleanup(self.temporal.cleanup)
        medios = override_settings(MEDIA_ROOT=self.temporal.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.anexo = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=self.anexo_id)

    def contexto(self, fuentes):
        contexto = Mock()
        contexto.analizar.return_value = {'fuentes': fuentes}
        return contexto

    def test_dos_lecturas_nuevas_congelan_huella_de_fuentes_en_el_ancla(self):
        fuentes = {'unidad': self.unidad.pk, 'prestamos': [{'codigo': 'PRE-QA', 'responsable': self.actor.pk}]}
        contextos = [self.contexto(fuentes), self.contexto(fuentes)]
        with patch('apps.documentos.presentation.calidad_automatica_laboratorios.ContextoCalidad',
                   side_effect=contextos) as constructor:
            _generar(self.anexo, self.actor)
        self.assertEqual(constructor.call_count, 2)
        for contexto in contextos:
            contexto.analizar.assert_called_once_with('PRESTAMOS-EQUIPOS')
        evento = RegistroAuditoriaUnidad.objects.get(objeto_id=str(self.anexo.pk), descripcion=AUDITORIA_PROCEDENCIA)
        self.assertEqual(evento.datos_nuevos['fuentes_sha256'], huella(fuentes))
        from apps.documentos.presentation.calidad_automatica_laboratorios import VERSION_REGLAS
        self.assertEqual(evento.datos_nuevos['metodo_fuentes'], f'calidad-laboratorios-{VERSION_REGLAS}')
        confianza = comprobar_procedencia(self.anexo)
        self.assertTrue(confianza['confiable'], confianza['motivos'])
        self.assertEqual(confianza['fuentes_sha256'], huella(fuentes))
        self.assertFalse(hasattr(self.anexo, '_fuentes_control_generacion'))

    def test_cambio_entre_lecturas_revierte_documento_recurso_archivo_y_auditoria(self):
        contextos = [self.contexto({'prestamos': [{'responsable': None}]}),
                     self.contexto({'prestamos': [{'responsable': self.actor.pk}]})]
        recursos, auditorias = Recurso.objects.count(), RegistroAuditoriaUnidad.objects.count()
        with patch('apps.documentos.presentation.calidad_automatica_laboratorios.ContextoCalidad', side_effect=contextos):
            with self.assertRaisesMessage(ValidationError, 'fuentes cambiaron'):
                _generar(self.anexo, self.actor)
        self.anexo.refresh_from_db()
        self.assertEqual(self.anexo.version, 0)
        self.assertIsNone(self.anexo.recurso)
        self.assertEqual(Recurso.objects.count(), recursos)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)
        self.assertEqual(list(Path(self.temporal.name).rglob('*.pdf')), [])
