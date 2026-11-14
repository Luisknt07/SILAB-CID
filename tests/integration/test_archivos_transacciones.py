"""Los borrados de medios se confirman junto a sus filas y nunca al simular."""
from datetime import date, timedelta
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.reservas.presentation.guia_contenido import guardar_imagenes_guia
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ImagenGuiaActividad
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad


class ArchivosTransaccionesTests(TestCase):
    def setUp(self):
        medios = TemporaryDirectory()
        self.addCleanup(medios.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=medios.name))
        self.persona = get_user_model().objects.create_user('archivos-transacciones-qa')
        self.unidad = Unidad.objects.create(nombre='Archivos QA', slug='archivos-qa',
            dependencia='laboratorios', fecha_inicio=date.today(), administrador=self.persona)
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, creado_por=self.persona,
            nombre='Práctica QA', codigo='ARCH-QA', proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular', estado_publicacion='borrador', visibilidad='privada')
        self.guia = GuiaActividadReserva.objects.create(actividad=actividad, titulo='Guía QA',
            es_estructurada=True, estado_publicacion='borrador', subido_por=self.persona)
        buffer = BytesIO()
        Image.new('RGB', (20, 20), (0, 80, 40)).save(buffer, format='PNG')
        self.datos = buffer.getvalue()

    def figura(self, *, borrador=False):
        figura = ImagenGuiaActividad.objects.create(guia=None if borrador else self.guia,
            subido_por=self.persona, borrador_token='qa' if borrador else '',
            imagen=SimpleUploadedFile('figura.png', self.datos, content_type='image/png'))
        if borrador:
            ImagenGuiaActividad.objects.filter(pk=figura.pk).update(creado_en=timezone.now() - timedelta(days=3))
        return figura

    def medio(self):
        nombre = default_storage.save(f'unidades/interior/u{self.unidad.pk}/referencia.png', ContentFile(self.datos))
        return MedioInterior.objects.create(unidad=self.unidad, tipo='foto', titulo='Referencia QA',
            descripcion='Imagen referencial del área · QA', imagen=nombre)

    def assert_archivo_intacto(self, almacen, nombre):
        self.assertTrue(almacen.exists(nombre))
        with almacen.open(nombre, 'rb') as archivo:
            self.assertEqual(archivo.read(), self.datos)

    def test_figura_retirada_se_conserva_si_la_operacion_exterior_revierte(self):
        figura = self.figura()
        identificador, nombre, almacen = figura.pk, figura.imagen.name, figura.imagen.storage
        with self.assertRaisesMessage(RuntimeError, 'Revertir QA'):
            with transaction.atomic():
                guardar_imagenes_guia(self.guia, [], eliminar=[identificador])
                raise RuntimeError('Revertir QA')
        self.assertTrue(self.guia.imagenes.filter(pk=identificador).exists())
        self.assert_archivo_intacto(almacen, nombre)

    def test_figura_retirada_se_borra_solo_tras_commit(self):
        figura = self.figura()
        identificador, nombre, almacen = figura.pk, figura.imagen.name, figura.imagen.storage
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            guardar_imagenes_guia(self.guia, [], eliminar=[identificador])
            self.assertFalse(self.guia.imagenes.filter(pk=identificador).exists())
            self.assert_archivo_intacto(almacen, nombre)
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(almacen.exists(nombre))

    def test_imagen_nueva_invalida_no_retira_la_figura_anterior(self):
        figura = self.figura()
        identificador, nombre, almacen = figura.pk, figura.imagen.name, figura.imagen.storage
        invalida = SimpleUploadedFile('invalida.png', b'no es imagen', content_type='image/png')
        with self.assertRaises(ValueError):
            guardar_imagenes_guia(self.guia, [invalida], eliminar=[identificador])
        self.assertTrue(self.guia.imagenes.filter(pk=identificador).exists())
        self.assert_archivo_intacto(almacen, nombre)

    def test_limpieza_de_borrador_se_revierte_sin_perder_el_archivo(self):
        figura = self.figura(borrador=True)
        identificador, nombre, almacen = figura.pk, figura.imagen.name, figura.imagen.storage
        with self.assertRaisesMessage(RuntimeError, 'Revertir QA'):
            with transaction.atomic():
                call_command('limpiar_figuras_guia_huerfanas', stdout=StringIO())
                raise RuntimeError('Revertir QA')
        self.assertTrue(ImagenGuiaActividad.objects.filter(pk=identificador).exists())
        self.assert_archivo_intacto(almacen, nombre)

    def test_limpieza_de_borrador_confirma_antes_de_borrar_archivo_y_respeta_figuras_asociadas(self):
        asociada = self.figura()
        figura = self.figura(borrador=True)
        identificador, nombre, almacen = figura.pk, figura.imagen.name, figura.imagen.storage
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            call_command('limpiar_figuras_guia_huerfanas', stdout=StringIO())
            self.assertFalse(ImagenGuiaActividad.objects.filter(pk=identificador).exists())
            self.assert_archivo_intacto(almacen, nombre)
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(almacen.exists(nombre))
        self.assertTrue(ImagenGuiaActividad.objects.filter(pk=asociada.pk).exists())
        self.assert_archivo_intacto(asociada.imagen.storage, asociada.imagen.name)

    def test_simular_retirada_de_interior_conserva_fila_y_archivo(self):
        medio = self.medio()
        identificador, nombre = medio.pk, medio.imagen.name
        call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, '--eliminar', '--simular', stdout=StringIO())
        self.assertTrue(MedioInterior.objects.filter(pk=identificador).exists())
        self.assert_archivo_intacto(default_storage, nombre)

    def test_retirada_de_interior_se_revierte_sin_perder_archivo(self):
        medio = self.medio()
        identificador, nombre = medio.pk, medio.imagen.name
        with self.assertRaisesMessage(RuntimeError, 'Revertir QA'):
            with transaction.atomic():
                call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, '--eliminar', stdout=StringIO())
                raise RuntimeError('Revertir QA')
        self.assertTrue(MedioInterior.objects.filter(pk=identificador).exists())
        self.assert_archivo_intacto(default_storage, nombre)

    def test_retirada_de_interior_borra_archivo_solo_tras_commit(self):
        medio = self.medio()
        identificador, nombre = medio.pk, medio.imagen.name
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, '--eliminar', stdout=StringIO())
            self.assertFalse(MedioInterior.objects.filter(pk=identificador).exists())
            self.assert_archivo_intacto(default_storage, nombre)
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(default_storage.exists(nombre))
