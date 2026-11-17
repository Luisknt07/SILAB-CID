from tests.integration.test_seguimiento_gobernanza import designar
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from django.core.exceptions import ValidationError
from apps.documentos.presentation.independencia_revision import (
    conflicto_directo,
    exigir_revision_independiente,
)


class IndependenciaRevisionTests(SimpleTestCase):
    def test_superusuario_no_evalua_su_unidad(self):
        usuario = SimpleNamespace(pk=7, is_superuser=True)
        with self.assertRaisesMessage(ValidationError, "superadministración"):
            exigir_revision_independiente(
                SimpleNamespace(), usuario, SimpleNamespace(pk=2, administrador_id=7)
            )

    def test_carga_y_validacion_local_exigen_otro_revisor(self):
        for datos in (
            {"cargado_por_id": 7},
            {"validado_por_id": 7, "recibido_por_id": None},
        ):
            with self.subTest(datos=datos):
                self.assertTrue(
                    conflicto_directo(
                        SimpleNamespace(**datos),
                        SimpleNamespace(pk=7),
                        SimpleNamespace(),
                    )
                )

    def test_recepcion_administrativa_no_se_confunde_con_autoria(self):
        self.assertEqual(
            "",
            conflicto_directo(
                SimpleNamespace(cargado_por_id=3, validado_por_id=7, recibido_por_id=7),
                SimpleNamespace(pk=7),
                SimpleNamespace(administrador_id=3),
            ),
        )

    def test_coordinacion_formal_tambien_bloquea(self):
        with patch(
            "apps.gestion_unidades.models.espacios.ResponsableUnidad.objects.filter"
        ) as query:
            query.return_value.exists.return_value = True
            with self.assertRaisesMessage(ValidationError, "coordina"):
                exigir_revision_independiente(
                    SimpleNamespace(), SimpleNamespace(pk=7), SimpleNamespace(pk=2)
                )
            query.assert_called_once_with(
                unidad_id=2, usuario_id=7, activo=True, rol="coordinacion"
            )

    def test_revisor_ajeno_sigue_el_circuito_original(self):
        with patch(
            "apps.gestion_unidades.models.espacios.ResponsableUnidad.objects.filter"
        ) as query:
            query.return_value.exists.return_value = False
            exigir_revision_independiente(
                SimpleNamespace(cargado_por_id=3),
                SimpleNamespace(pk=7),
                SimpleNamespace(pk=2),
            )


class ComandosRevisionIndependienteTests(TestCase):
    def test_comando_bloquea_autoevaluacion_sin_cambiar_el_expediente(self):
        from django.contrib.auth import get_user_model
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.models.expediente import DocumentoExpediente, DocumentoExigido
        from apps.documentos.presentation.expediente import evaluar_documento
        actor = get_user_model().objects.create_superuser('revisor-autor', password=None)
        designar(actor)
        from datetime import date
        unidad = Unidad.objects.create(nombre='Laboratorio de ensayo', slug='revision-independiente', dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        exigido = DocumentoExigido.objects.create(codigo='ENSAYO-INDEPENDENCIA', nombre='Entrega de ensayo')
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=exigido, anio=2026, cargado_por=actor)
        with self.assertRaisesMessage(ValidationError, 'cargó el documento'):
            evaluar_documento(documento, actor, 100)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluado_en)
        self.assertIsNone(documento.evaluacion)

    def test_emision_y_redaccion_nativas_tambien_requieren_independencia(self):
        from unittest.mock import patch
        for redactor, emisor in ((True, False), (False, True)):
            with self.subTest(redactor=redactor, emisor=emisor), patch(
                'apps.gestion_unidades.models.espacios.ResponsableUnidad.objects.filter'
            ) as coordinacion, patch('apps.documentos.models.expediente.DocumentoElaborado.objects.filter') as redaccion, patch(
                'apps.documentos.models.constancias.ConstanciaDocumento.objects.filter'
            ) as constancia:
                coordinacion.return_value.exists.return_value = False
                redaccion.return_value.exists.return_value = redactor
                constancia.return_value.exists.return_value = emisor
                with self.assertRaisesMessage(ValidationError, 'otra persona autorizada'):
                    exigir_revision_independiente(SimpleNamespace(pk=5, version=2), SimpleNamespace(pk=7), SimpleNamespace(pk=2))
