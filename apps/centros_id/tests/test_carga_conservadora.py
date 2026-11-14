"""Una actualización del catálogo puede crear faltantes sin restaurar ediciones vacías."""
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import ciab
from apps.centros_id.models import DocumentoCentro, Proyecto


class CargaConservadoraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(ciab).cargar()

    def test_preserva_vacios_intencionales_y_estados_desactivados(self):
        centro = self.centro
        centro.presentacion = ''
        centro.credito_imagen = ''
        centro.activo = False
        centro.save()
        servicio = centro.servicios.first()
        servicio.alcance = ''
        servicio.activo = False
        servicio.save()
        linea = centro.lineas.first()
        linea.metodologia = ''
        linea.save()
        antes = (centro.servicios.count(), centro.lineas.count(), centro.documentos.count())

        call_command('cargar_centros_id', centro=centro.slug,
                     conservar_existentes=True, stdout=StringIO())

        centro.refresh_from_db()
        servicio.refresh_from_db()
        linea.refresh_from_db()
        self.assertEqual(centro.presentacion, '')
        self.assertEqual(centro.credito_imagen, '')
        self.assertFalse(centro.activo)
        self.assertEqual(servicio.alcance, '')
        self.assertFalse(servicio.activo)
        self.assertEqual(linea.metodologia, '')
        self.assertEqual(antes, (centro.servicios.count(), centro.lineas.count(), centro.documentos.count()))

    def test_crea_faltantes_con_sus_detalles_en_la_misma_carga(self):
        servicio = self.centro.servicios.first()
        nombre = servicio.nombre
        servicio.delete()
        cargador = Cargador(ciab, conservar_existentes=True)

        centro = cargador.cargar()

        nuevo = centro.servicios.get(nombre=nombre)
        self.assertTrue(nuevo.alcance)
        self.assertTrue(nuevo.metodo)
        nuevo.alcance = ''
        nuevo.save()
        # Reutilizar el cargador inicia otra carga: el registro ya tiene propietario editorial.
        cargador.cargar()
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.alcance, '')

    def test_con_medios_no_restaura_portada_que_el_gestor_retiro(self):
        self.assertFalse(self.centro.imagen)
        self.assertEqual(self.centro.credito_imagen, '')
        Cargador(ciab, medios=True, conservar_existentes=True).cargar()
        self.centro.refresh_from_db()
        self.assertFalse(self.centro.imagen)
        self.assertEqual(self.centro.credito_imagen, '')
        self.assertTrue(self.centro.imagenes.exists())

    def test_no_regenera_documento_existente_ni_repone_relacion_vaciada(self):
        tipo, titulo = 'otro', 'Documento revisado por el gestor'
        contenido = SimpleNamespace(DOCUMENTOS_GENERADOS=[(tipo, titulo, 'servicios', 'Resumen')])
        documento = DocumentoCentro.objects.create(
            centro=self.centro, titulo=titulo, tipo=tipo,
            estado_documental='borrador', publico=False)
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto revisado', es_muestra=True)
        cargador = Cargador(contenido, conservar_existentes=True)
        with patch('apps.centros_id.documentos.pdf') as pdf:
            cargador._documentos_generados(self.centro)
        pdf.assert_not_called()
        documento.refresh_from_db()
        self.assertFalse(documento.archivo)
        cargador._enlazar(proyecto.componentes, [self.centro.componentes.first()])
        self.assertFalse(proyecto.componentes.exists())

    def test_rechaza_modificaciones_contradictorias(self):
        with self.assertRaises(ValueError):
            Cargador(ciab, reescribir=True, conservar_existentes=True)
        with self.assertRaises(CommandError):
            call_command('cargar_centros_id', reescribir=True, conservar_existentes=True,
                         stdout=StringIO())
