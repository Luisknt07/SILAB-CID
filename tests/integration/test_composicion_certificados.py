"""Composición PDF sin acceso a datos: límites, identidad congelada y render histórico."""
import base64
from datetime import date, datetime, timezone as utc
from decimal import Decimal
from importlib.util import find_spec
from io import BytesIO
from itertools import product
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from PIL import Image

from apps.formacion.presentation.certificados_diseno import DISENOS_CERTIFICADO, _cajas_logos, crear_diseno, dibujar_certificado


class ComposicionCertificadoTests(SimpleTestCase):
    def imagen(self):
        salida = BytesIO()
        Image.new('RGBA', (300, 100), (20, 70, 50, 150)).save(salida, format='PNG')
        return base64.b64encode(salida.getvalue()).decode()

    def certificado(self):
        return SimpleNamespace(
            codigo='CERT-DEMO-2026', tipo='aprobacion', nombre='María Fernanda Espinoza Guerrero',
            documento='DOCUMENTO-PRIVADO', curso_nombre='Aplicaciones logísticas con IA',
            horas=Decimal('40.50'), edicion='Octubre 2026', unidad_nombre='Laboratorio docente',
            clasificacion='Curso corto', emitido_en=timezone.now(), fecha_inicio=date(2026, 10, 12),
            fecha_fin=date(2026, 10, 23), categoria_evento='evento_cientifico', nota_final=Decimal('92.5'),
            firma_nombre='Firmante original', firma_cargo='Coordinación académica', anulado=False,
            diseno_certificado={},
        )

    def diseno(self, modelo='clasico', logos=1, firmas=2):
        return dict(version=3, diseno=modelo, titulo='CERTIFICADO DE APROBACIÓN',
                    alineacion_contenido='izquierda' if modelo=='sobrio' else 'centro',
                    texto='Aprobó el curso de aplicaciones de inteligencia artificial para la logística, con una duración de 40,5 horas, del 12 al 23 de octubre de 2026.',
                    primario='#1E5A3D', acento='#D5AC40', institucion='Universidad de muestra', siglas='UM',
                    logos=[dict(imagen=self.imagen(),posicion='auto',fondo='claro') for _ in range(logos)],
                    firmantes=[dict(nombre='Gabriela Montenegro',cargo='Coordinación académica',imagen=self.imagen()) for _ in range(firmas)],
                    mostrar_nota=True, fecha='9 de octubre de 2026', fecha_emision='9 de octubre de 2026', fecha_inicio='12 de octubre de 2026', fecha_fin='23 de octubre de 2026',
                    emisor='Laboratorio docente',entradilla='Otorga el presente certificado a',
                    horas='40,5', categoria_evento='Curso', rol='participante',
                    verificacion_url='https://example.org/certificados/CERT-DEMO-2026/')

    def test_todas_las_alineaciones_de_uno_a_cuatro_logos_caben_sin_solaparse(self):
        from reportlab.lib.units import mm
        posiciones = ('auto', 'izquierda', 'centro', 'derecha')
        for cantidad in range(1, 5):
            for disposicion in (*posiciones, 'entre_extremos'):
                for elegidas in product(posiciones, repeat=cantidad):
                    logos = [{'posicion': p} for p in elegidas]
                    cajas = _cajas_logos(logos, 23*mm, 195*mm, 251*mm, 22*mm, disposicion)
                    self.assertEqual(len(cajas), cantidad)
                    limite = 23*mm
                    for _, izquierda, _, ancho, _ in sorted(cajas, key=lambda c: c[1]):
                        self.assertGreaterEqual(izquierda + .001, limite)
                        self.assertLessEqual(izquierda + ancho, 274*mm + .001)
                        limite = izquierda + ancho + 6*mm
        for posicion, esperado in (('izquierda', 23), ('derecha', 218), ('centro', 120.5)):
            caja = _cajas_logos([{'posicion': posicion}],23*mm,195*mm,251*mm,22*mm,'auto')[0]
            self.assertAlmostEqual(caja[1] / mm, esperado)

    def test_snapshot_nuevo_congela_roles_evento_fechas_y_no_la_nota(self):
        identidad = SimpleNamespace(nombre='Universidad de muestra', siglas='UM', paleta={})
        cert = self.certificado()
        config = SimpleNamespace(tercera_firma_nombre='Tercer firmante', tercera_firma_cargo='Dirección',
                                 mostrar_nota=True, texto_aprobacion='{categoria_evento}: {fecha_inicio} a {fecha_fin}; {horas} horas; {rol}.')
        with patch('apps.core.presentation.identidad.identidad_actual', return_value=(None,identidad)), \
             patch('apps.core.presentation.identidad.logo_institucional', return_value=None):
            diseno = crear_diseno(cert, config)
        self.assertEqual(diseno['version'], 12)
        self.assertEqual(diseno['alineacion_contenido'], 'centro')
        self.assertFalse(diseno['mostrar_nota'])
        self.assertEqual(diseno['horas'], '40,5')
        self.assertEqual(diseno['categoria_evento'], 'Evento científico')
        self.assertIn('12 de octubre de 2026 a 23 de octubre de 2026', diseno['texto'])
        self.assertEqual(len(diseno['firmantes']), 2)
        for tipo in ('asistencia','ponente','organizador'):
            cert.tipo = tipo
            with patch('apps.core.presentation.identidad.identidad_actual', return_value=(None,identidad)), \
                 patch('apps.core.presentation.identidad.logo_institucional', return_value=None):
                rol = crear_diseno(cert)
            self.assertIn({'asistencia':'Asistió', 'ponente':'ponente', 'organizador':'organización'}[tipo], rol['texto'])

    @skipUnless(find_spec('pymupdf'), 'Extracción y geometría disponibles en desarrollo con PyMuPDF.')
    def test_seis_modelos_con_cuatro_logos_tres_firmas_y_texto_extenso(self):
        import pymupdf
        for modelo in DISENOS_CERTIFICADO:
            with self.subTest(diseno=modelo):
                cert = self.certificado()
                cert.nombre = ('María Fernanda Participante de nombre y apellidos compuestos ' * 4)[:200]
                cert.diseno_certificado = self.diseno(modelo, 4, 3)
                cert.diseno_certificado['texto'] = ('Participó en el encuentro de actualización profesional sobre aplicaciones de inteligencia artificial para logística, transporte y cadena de suministro; desarrolló actividades guiadas de análisis, simulación, diseño de soluciones y validación de resultados. ' * 3)[:700]+' La actividad se desarrolló del 12 al 23 de octubre de 2026, con una duración de 40,5 horas.'
                for firma in cert.diseno_certificado['firmantes']:
                    firma['nombre'] = ('Gabriela Alejandra Nombre compuesto de firmante de muestra ' * 3)[:160]
                    firma['cargo'] = ('Coordinación académica institucional de formación continua y transferencia del conocimiento ' * 3)[:200]
                with patch('apps.core.presentation.identidad.identidad_actual', side_effect=AssertionError('Snapshot congelado')):
                    pdf = dibujar_certificado(cert)
                documento = pymupdf.open(stream=pdf, filetype='pdf')
                self.assertEqual(len(documento), 1)
                pagina = documento[0]
                texto = pagina.get_text()
                for dato in ('12 al 23 de octubre de 2026', '9 de octubre de 2026', '40,5 horas', 'CERT-DEMO-2026'):
                    self.assertIn(dato, texto)
                self.assertNotIn('Calificación', texto)
                self.assertNotIn('9,25/10', texto)
                self.assertEqual([link.get('uri') for link in pagina.get_links()],
                                 [cert.diseno_certificado['verificacion_url']])
                for bloque in pagina.get_text('dict')['blocks']:
                    for linea in bloque.get('lines', []):
                        for span in linea['spans']:
                            self.assertTrue(pagina.rect.contains(pymupdf.Rect(span['bbox'])), span['text'])
                            # Incluso los cargos máximos quedan por encima del filete de 12 mm.
                            self.assertLess(span['bbox'][3], pagina.rect.height - 12*72/25.4, span['text'])
                publico = pymupdf.open(stream=dibujar_certificado(cert, False), filetype='pdf')
                self.assertNotIn('DOCUMENTO-PRIVADO', publico[0].get_text())
                imagen = pagina.get_pixmap(matrix=pymupdf.Matrix(.5,.5),alpha=False)
                self.assertGreater(len(set(imagen.samples)), 30)

    @skipUnless(find_spec('pymupdf'), 'La regresión de texto histórico requiere PyMuPDF.')
    def test_snapshot_version_uno_conserva_calificacion_y_composicion_original(self):
        import pymupdf
        cert = self.certificado()
        cert.diseno_certificado = self.diseno('sobrio')
        cert.diseno_certificado.update(version=1, logo='', firmantes=[], mostrar_nota=True)
        antiguo = pymupdf.open(stream=dibujar_certificado(cert), filetype='pdf')
        self.assertIn('Calificación final: 9,25/10', antiguo[0].get_text())
        del cert.diseno_certificado['version']
        sin_version = pymupdf.open(stream=dibujar_certificado(cert), filetype='pdf')
        self.assertEqual(sin_version[0].get_text(), antiguo[0].get_text())


    @skipUnless(find_spec('pymupdf'), 'La regresión histórica requiere extracción PDF.')
    def test_certificado_historico_sin_snapshot_ignora_defaults_nuevos_y_horas_decimal(self):
        import pymupdf
        identidad = SimpleNamespace(nombre='Universidad de muestra', siglas='UM', paleta={})
        for tipo, verbo in (('aprobacion', 'Aprobó'), ('participacion', 'Participó y completó')):
            cert = self.certificado()
            cert.tipo = tipo
            cert.horas = Decimal('40.00')
            with patch('apps.core.presentation.identidad.identidad_actual', return_value=(None,identidad)), \
                 patch('apps.core.presentation.identidad.logo_institucional', return_value=None), \
                 patch('apps.formacion.presentation.certificados_diseno.TEXTO_APROBACION', 'Nuevo texto'), \
                 patch('apps.formacion.presentation.certificados_diseno.TEXTO_PARTICIPACION', 'Otro texto'):
                pdf = dibujar_certificado(cert)
            texto = pymupdf.open(stream=pdf,filetype='pdf')[0].get_text()
            self.assertIn(verbo, texto)
            self.assertIn('40 horas', texto)
            self.assertNotIn('40.00', texto)
            self.assertNotIn('Nuevo texto', texto)
            self.assertNotIn('Otro texto', texto)
            self.assertIn('Calificación final: 9,25/10', texto)


    def test_factory_v5_historica_logo_institucional_permanece_con_aliados_y_primer_upload_lo_reemplaza(self):
        from apps.formacion.presentation.certificados_diseno import _crear_diseno_base_v5
        from pathlib import Path
        from django.core.files.base import ContentFile
        from django.conf import settings
        identidad = SimpleNamespace(nombre='Universidad de muestra', siglas='UM', paleta={})
        institucional = Path(settings.BASE_DIR) / 'apps/portal/static/img/logo_upec.png'
        config = SimpleNamespace(logo_2_imagen=ContentFile(base64.b64decode(self.imagen()), name='aliado.png'))
        with patch('apps.core.presentation.identidad.identidad_actual', return_value=(None,identidad)), \
             patch('apps.core.presentation.identidad.logo_institucional', return_value=institucional) as origen:
            diseno = _crear_diseno_base_v5(self.certificado(), config)
        self.assertEqual(origen.call_args_list, [__import__('unittest').mock.call(fondo='claro'), __import__('unittest').mock.call(fondo='oscuro')])
        self.assertEqual(len(diseno['logos']), 2)
        self.assertEqual(diseno['logos'][0]['imagen'], diseno['logo'])
        self.assertIn(diseno['logos'][0]['fondo'], ('claro','oscuro'))
        self.assertNotEqual(diseno['logos'][0]['imagen'], diseno['logos'][1]['imagen'])
        for indice in (1,3,4):
            setattr(config, f'logo_{indice}_imagen', ContentFile(base64.b64decode(self.imagen()), name=f'logo{indice}.png'))
        with patch('apps.core.presentation.identidad.identidad_actual', return_value=(None,identidad)), \
             patch('apps.core.presentation.identidad.logo_institucional', side_effect=AssertionError('Primer logo explícito')):
            reemplazado = _crear_diseno_base_v5(self.certificado(), config)
        self.assertEqual(len(reemplazado['logos']), 4)
        self.assertEqual(reemplazado['logo'], '')
        self.assertNotEqual(reemplazado['logos'][0]['imagen'], diseno['logo'])


    def test_texto_personalizado_conserva_periodo_y_horas_en_el_mismo_parrafo_sin_duplicarlos(self):
        identidad = SimpleNamespace(nombre='Universidad de muestra', siglas='UM', paleta={})
        for plantilla in ('Completó «{curso}».', 'Actividad iniciada el {fecha_inicio}.',
                          'Completó {horas} horas {periodo}.'):
            with self.subTest(plantilla=plantilla), \
                 patch('django.utils.timezone.now', return_value=datetime(2026, 10, 23, 17, tzinfo=utc.utc)), \
                 patch('apps.core.presentation.identidad.identidad_actual', return_value=(None, identidad)), \
                 patch('apps.core.presentation.identidad.logo_institucional', return_value=None):
                diseno = crear_diseno(self.certificado(), SimpleNamespace(texto_aprobacion=plantilla))
            self.assertIn('del 12 al 23 de octubre de 2026', diseno['texto'])
            self.assertEqual(diseno['texto'].count('40,5 horas'), 1)
            self.assertEqual(diseno['texto'].count('del 12 al 23 de octubre de 2026'), 1)
            self.assertEqual(diseno['emisor'], 'Laboratorio docente')
            self.assertIn('octubre de', diseno['fecha_emision'])


    def test_normalizacion_cierra_solo_el_archivo_que_abre_el_helper(self):
        from django.core.files.base import ContentFile
        from apps.formacion.presentation.certificados_diseno import imagen_png
        contenido = base64.b64decode(self.imagen())
        abierto = ContentFile(contenido, name='logo.png')
        self.assertTrue(imagen_png(abierto))
        self.assertFalse(abierto.closed)
        self.assertEqual(abierto.tell(), 0)

        class ArchivoCerrado:
            def __init__(self):
                self.closed = True
                self.stream = None
            def open(self, mode):
                self.stream = BytesIO(contenido)
                self.closed = False
            def read(self, *args):
                return self.stream.read(*args)
            def seek(self, *args):
                return self.stream.seek(*args)
            def tell(self):
                return self.stream.tell()
            def close(self):
                self.stream.close()
                self.closed = True
        cerrado = ArchivoCerrado()
        self.assertTrue(imagen_png(cerrado))
        self.assertTrue(cerrado.closed)


    def test_fieldfile_real_cerrado_se_puede_reemplazar_despues_de_normalizar(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.core.files.storage import FileSystemStorage
        from django.db.models.fields.files import FieldFile
        from apps.formacion.presentation.certificados_diseno import imagen_png
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'firma.png'
            archivo.write_bytes(base64.b64decode(self.imagen()))
            storage = FileSystemStorage(location=carpeta)
            fieldfile = FieldFile(SimpleNamespace(), SimpleNamespace(storage=storage), 'firma.png')
            self.assertTrue(fieldfile.closed)
            self.assertTrue(imagen_png(fieldfile))
            self.assertTrue(fieldfile.closed)
            # Windows rechaza unlink si el descriptor que abrió el helper sigue abierto.
            archivo.unlink()
            self.assertFalse(archivo.exists())


    @skipUnless(find_spec('pymupdf'), 'La alineación y límites del PDF requieren PyMuPDF.')
    def test_geometrico_centra_el_contenido_con_uno_a_cuatro_logos_y_tres_firmas(self):
        import pymupdf
        from reportlab.lib.units import mm
        for logos in range(1, 5):
            for firmas in range(1, 4):
                with self.subTest(logos=logos, firmas=firmas):
                    cert = self.certificado()
                    cert.nombre = ('María Fernanda Participante de nombre y apellidos compuestos ' * 4)[:200]
                    cert.diseno_certificado = self.diseno('geometrico', logos, firmas)
                    cert.diseno_certificado['texto'] = (
                        'Participó en el encuentro de actualización profesional sobre aplicaciones de inteligencia artificial para logística, transporte y cadena de suministro; desarrolló actividades guiadas de análisis, simulación, diseño de soluciones y validación de resultados. ' * 3
                    )[:700] + ' La actividad se desarrolló del 12 al 23 de octubre de 2026, con una duración de 40,5 horas.'
                    for firma in cert.diseno_certificado['firmantes']:
                        firma['nombre'] = ('Gabriela Alejandra Nombre compuesto de firmante de muestra ' * 3)[:160]
                        firma['cargo'] = ('Coordinación académica institucional de formación continua y transferencia del conocimiento ' * 3)[:200]
                    doc = pymupdf.open(stream=dibujar_certificado(cert), filetype='pdf')
                    self.assertEqual(len(doc), 1)
                    pagina = doc[0]
                    qr = pagina.get_links()[0]['from']
                    centradas = []
                    for bloque in pagina.get_text('dict')['blocks']:
                        for linea in bloque.get('lines', []):
                            caja = pymupdf.Rect(linea['bbox'])
                            self.assertTrue(pagina.rect.contains(caja))
                            self.assertFalse(caja.intersects(qr))
                            if 90 <= caja.y0 and caja.y1 < 435:
                                centradas.append(linea)
                                self.assertAlmostEqual((caja.x0 + caja.x1) / 2, pagina.rect.width / 2, delta=.75)
                                self.assertGreaterEqual(caja.x0, 24*mm - .75)
                                self.assertLessEqual(caja.x1, pagina.rect.width - 24*mm + .75)
                    self.assertGreaterEqual(len(centradas), 10)
                    texto = pagina.get_text()
                    for dato in ('12 al 23 de octubre de 2026', '40,5 horas', 'Emitido el 9 de octubre de 2026'):
                        self.assertIn(dato, texto)


    def test_nuevas_previas_congelan_alineacion_geometrica_y_sobria(self):
        identidad = SimpleNamespace(nombre='Universidad de muestra', siglas='UM', paleta={})
        for modelo, esperado in (('geometrico', 'centro'), ('sobrio', 'centro')):
            with self.subTest(modelo=modelo), \
                 patch('apps.core.presentation.identidad.identidad_actual', return_value=(None, identidad)), \
                 patch('apps.core.presentation.identidad.logo_institucional', return_value=None):
                diseno = crear_diseno(self.certificado(), SimpleNamespace(diseno=modelo))
            self.assertEqual(diseno['alineacion_contenido'], esperado)


    @skipUnless(find_spec('pymupdf'), 'La regresión del snapshot V3 requiere PyMuPDF.')
    def test_geometrico_v3_sin_alineacion_conserva_la_composicion_izquierda(self):
        import pymupdf
        from reportlab.lib.units import mm
        cert = self.certificado()
        cert.diseno_certificado = self.diseno('geometrico')
        del cert.diseno_certificado['alineacion_contenido']
        anterior = pymupdf.open(stream=dibujar_certificado(cert), filetype='pdf')[0]
        cabecera = anterior.search_for('UNIVERSIDAD DE MUESTRA')[0]
        self.assertAlmostEqual(cabecera.x0, 24*mm, delta=.75)
        cert.diseno_certificado['alineacion_contenido'] = 'izquierda'
        explicita = pymupdf.open(stream=dibujar_certificado(cert), filetype='pdf')[0]
        self.assertEqual(anterior.get_text(), explicita.get_text())
        self.assertEqual(anterior.get_pixmap().samples, explicita.get_pixmap().samples)
