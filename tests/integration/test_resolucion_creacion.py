"""La resolución de creación de la unidad en su «Ficha de la unidad».

Sale del expediente: se carga una vez y se hereda cada año. Validada la ve
cualquiera, y su archivo se abre cuando pasó la verificación de seguridad;
cargada y sin validar, solo la ve el personal de la unidad. Sin cargar, el
personal ve cómo cargarla y el público no ve un hueco.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.formacion.presentation.recursos_publicos import _acceso_recurso, resolucion_de_creacion
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.recursos.models.recursos import Recurso
from tests.integration.test_produccion_planta import BasePlantaProduce


class LaResolucionDeCreacionTests(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        asegurar_catalogo()
        cls.recurso = Recurso.objects.create(
            unidad=cls.unidad, nombre='Resolución HCU-2019-045 de creación de la planta',
            url='https://upec.edu.ec/resoluciones/hcu-2019-045.pdf', visibilidad='interna',
        )
        cls.documento = DocumentoExpediente.objects.create(
            unidad=cls.unidad, exigido=DocumentoExigido.objects.get(codigo='RESOLUCION-CREACION'), anio=2026,
            estado='cargado', recurso=cls.recurso, cargado_en=timezone.now(),
        )

    def ficha(self, usuario=None):
        if usuario is not None:
            self.client.force_login(usuario)
        return self.client.get(reverse('ficha_unidad', args=[self.unidad.slug]))

    def test_cargada_sin_validar_solo_la_ve_el_personal(self):
        self.assertIsNone(resolucion_de_creacion(self.unidad, AnonymousUser(), False))
        interna = resolucion_de_creacion(self.unidad, self.coordinacion, True)
        self.assertFalse(interna['validada'])
        self.assertContains(self.ficha(self.coordinacion), 'Resolución HCU-2019-045 de creación de la planta')
        self.client.logout()
        publica = self.ficha()
        self.assertNotContains(publica, 'Resolución HCU-2019-045')
        self.assertContains(publica, 'La unidad todavía no publica su resolución de creación.')
        self.assertEqual(_acceso_recurso(self.recurso, AnonymousUser()), 'denegado')

    def test_validada_la_ve_cualquiera_y_su_archivo_se_abre_verificado(self):
        DocumentoExpediente.objects.filter(pk=self.documento.pk).update(estado='validado', validado_en=timezone.now())
        publica = resolucion_de_creacion(self.unidad, AnonymousUser(), False)
        self.assertTrue(publica['validada'])
        # Sin la verificación de seguridad, el archivo no se entrega al público.
        self.assertEqual(publica['url'], '')
        self.assertContains(self.ficha(), 'El archivo se publica cuando termina su verificación de seguridad.')
        Recurso.objects.filter(pk=self.recurso.pk).update(seguridad_verificada=True)
        self.recurso.refresh_from_db()
        self.assertEqual(_acceso_recurso(self.recurso, AnonymousUser()), 'permitido')
        self.assertTrue(resolucion_de_creacion(self.unidad, AnonymousUser(), False)['url'])
        self.assertContains(self.ficha(), 'data-accion="documento"')
        # Se ve en el visor; la ficha no ofrece descargarla aunque el archivo lo permita.
        Recurso.objects.filter(pk=self.recurso.pk).update(descargar=True)
        self.assertNotContains(self.ficha(), 'download')

    def test_otro_documento_del_expediente_sigue_siendo_interno(self):
        otro = Recurso.objects.create(unidad=self.unidad, nombre='Informe del período', url='https://upec.edu.ec/i.pdf',
                                      visibilidad='interna', seguridad_verificada=True)
        DocumentoExpediente.objects.create(
            unidad=self.unidad, exigido=DocumentoExigido.objects.exclude(codigo='RESOLUCION-CREACION').first(),
            anio=2026, estado='validado', recurso=otro,
        )
        self.assertEqual(_acceso_recurso(otro, AnonymousUser()), 'denegado')

    def test_sin_cargar_el_personal_ve_como_cargarla(self):
        DocumentoExpediente.objects.filter(pk=self.documento.pk).delete()
        ficha = self.ficha(self.coordinacion)
        self.assertContains(ficha, 'Cargarla en el expediente')
        visitante = get_user_model().objects.create_user('visitante.resolucion', 'vr@upec.edu.ec', 'Clave-segura-2026')
        self.assertNotContains(self.ficha(visitante), 'Cargarla en el expediente')
