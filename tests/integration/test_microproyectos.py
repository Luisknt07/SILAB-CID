from io import BytesIO
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.recursos.presentation.microproyectos import inspeccionar_paquete
from apps.recursos.models.recursos import Recurso
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests


def paquete(**extras):
    salida = BytesIO()
    with ZipFile(salida, 'w') as z:
        for nombre, contenido in {'manage.py': '# proyecto', 'requirements.txt': 'Django==5.2.17', **extras}.items():
            z.writestr(nombre, contenido)
    return SimpleUploadedFile('proyecto.zip', salida.getvalue())


class MicroproyectosTests(EditorRecursosUnidadTests):
    def test_inspeccion_excluye_entornos_y_secretos_sin_ejecutar(self):
        archivo = paquete(**{'.env': 'SECRET_KEY=privada', '.venv/lib.py': 'raise RuntimeError()',
                             'config/__pycache__/a.pyc': 'cache', 'db.sqlite3': 'datos'})
        nombres = inspeccionar_paquete(archivo)
        self.assertEqual(set(nombres), {'manage.py', 'requirements.txt', 'db.sqlite3'})
        self.assertEqual(archivo.tell(), 0)

    def test_rechaza_escape_del_zip(self):
        with self.assertRaises(ValidationError):
            inspeccionar_paquete(paquete(**{'../escape.py': 'no'}))

    def test_microproyecto_no_se_extrae_como_sitio_estatico(self):
        recurso = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta,
            nombre='Proyecto aislado', archivo=paquete(), tipo_adjunto='microproyecto_django')
        self.assertFalse(recurso.es_zip)
        self.assertFalse(recurso.directorio_extraido.exists())
        self.assertEqual(recurso.nombre_visualizador, 'microproyecto.html')
        url = recurso.get_url_compartir()
        self.assertContains(self.client.get(url), 'Pendiente de puesta en marcha')
        self.assertEqual(self.client.get(url + 'manage.py').status_code, 404)
        self.assertEqual(self.client.get(url + '?download=1').status_code, 404)
        Recurso.objects.filter(pk=recurso.pk).update(
            microproyecto_url='http://microproyecto-1.localhost:19001/admin/', microproyecto_hash=recurso.hash_sha256)
        self.assertContains(self.client.get(url), 'http://microproyecto-1.localhost:19001/admin/')
        Recurso.objects.filter(pk=recurso.pk).update(hash_sha256='nueva-version')
        self.assertNotContains(self.client.get(url), 'http://microproyecto-1.localhost:19001/admin/')

    def test_tipo_microproyecto_rechaza_html_suelto(self):
        recurso = Recurso(unidad=self.unidad, nombre='Incorrecto', descripcion='Prueba',
            tipo_adjunto='microproyecto_django', archivo=SimpleUploadedFile('index.html', b'html'), activo=False)
        with self.assertRaises(ValidationError) as error:
            recurso.clean()
        self.assertIn('archivo', error.exception.message_dict)

    def test_no_publica_un_django_como_zip_estatico(self):
        recurso = Recurso(unidad=self.unidad, nombre='ZIP Python', descripcion='Prueba',
                          archivo=paquete(), activo=False)
        with self.assertRaises(ValidationError):
            recurso.save()
