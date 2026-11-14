"""Confianza del contenido nativo y persistencia del último control automático."""
from hashlib import sha256
from io import BytesIO
from datetime import date
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, RectangleObject, TextStringObject
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.confianza_documental import (
    AUDITORIA_PROCEDENCIA, comparar_pdf_nativo, comprobar_procedencia, registrar_procedencia_nativa,
)
from apps.documentos.presentation.expediente_archivos import codificar_metadatos, identidad_documental
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.models.recursos import Recurso


def pdf_prueba(asunto='', texto='Contenido nativo de prueba, con unidad y período identificables.'):
    salida = BytesIO()
    canvas = Canvas(salida)
    canvas.setSubject(asunto)
    canvas.drawString(40, 780, texto)
    canvas.save()
    return salida.getvalue()


def reescribir(datos, cambio=None):
    lector = PdfReader(BytesIO(datos))
    escritor = PdfWriter(clone_from=lector)
    if cambio:
        cambio(escritor)
    salida = BytesIO()
    escritor.write(salida)
    return salida.getvalue()


def widget_firma(escritor, rect):
    widget = DictionaryObject({NameObject('/Type'): NameObject('/Annot'),
        NameObject('/Subtype'): NameObject('/Widget'), NameObject('/FT'): NameObject('/Sig'),
        NameObject('/Rect'): ArrayObject([NumberObject(v) for v in rect])})
    referencia = escritor._add_object(widget)
    escritor.pages[0][NameObject('/Annots')] = ArrayObject([
        *escritor.pages[0].get('/Annots', []), referencia])
    escritor._root_object[NameObject('/AcroForm')] = DictionaryObject({
        NameObject('/Fields'): ArrayObject([referencia])})


def pdf_con_enlace(uri):
    salida = BytesIO()
    canvas = Canvas(salida)
    canvas.drawString(40, 780, 'Fuente del respaldo documental nativo.')
    canvas.linkURL(uri, (40, 750, 220, 770), relative=0, thickness=0)
    canvas.save()
    return salida.getvalue()


def pdf_con_indice():
    salida = BytesIO()
    canvas = Canvas(salida)
    canvas.bookmarkPage('inicio')
    canvas.addOutlineEntry('Inicio', 'inicio')
    canvas.drawString(40, 780, 'Índice del documento nativo')
    canvas.linkRect('', 'detalle', (40, 730, 240, 750), relative=0, thickness=0)
    canvas.showPage()
    canvas.bookmarkPage('detalle')
    canvas.addOutlineEntry('Detalle', 'detalle')
    canvas.drawString(40, 780, 'Detalle del documento nativo')
    canvas.save()
    return salida.getvalue()


class ComparacionNativaPdfTests(SimpleTestCase):
    def test_indice_y_enlaces_locales_nativos_se_conservan_al_firmar(self):
        original = pdf_con_indice()
        self.assertTrue(comparar_pdf_nativo(original, reescribir(
            original, lambda w: widget_firma(w, [0, 0, 0, 0]))))

    def test_cambiar_destino_del_indice_o_titulo_del_marcador_no_pasa(self):
        original = pdf_con_indice()
        def cambiar_destino(w):
            w.pages[0]['/Annots'][0].get_object()['/Dest'][0] = w.pages[0].indirect_reference
        def cambiar_marcador(w):
            w._root_object['/Outlines']['/First'][NameObject('/Title')] = TextStringObject('Otro contenido')
        for cambio in (cambiar_destino, cambiar_marcador):
            with self.subTest(cambio=cambio.__name__), self.assertRaises(ValidationError):
                comparar_pdf_nativo(original, reescribir(original, cambio))

    def test_un_enlace_interno_agregado_no_pasa(self):
        original = pdf_con_indice()
        def agregar(w):
            w.pages[0]['/Annots'].append(w.pages[0]['/Annots'][0])
        with self.assertRaises(ValidationError):
            comparar_pdf_nativo(original, reescribir(original, agregar))

    def test_referencias_y_compresion_distintas_conservan_contenido_real(self):
        original = pdf_prueba()
        nuevo = reescribir(original, lambda w: w.pages[0].compress_content_streams())
        self.assertNotEqual(original, nuevo)
        self.assertTrue(comparar_pdf_nativo(original, nuevo))

    def test_cambiar_recurso_de_fuente_no_pasa_aunque_el_texto_extraido_coincida(self):
        original = pdf_prueba()
        def cambiar(w):
            fuente = w.pages[0]['/Resources']['/Font']['/F1']
            fuente[NameObject('/BaseFont')] = NameObject('/Courier')
        alterado = reescribir(original, cambiar)
        self.assertEqual(PdfReader(BytesIO(original)).pages[0].extract_text(),
                         PdfReader(BytesIO(alterado)).pages[0].extract_text())
        with self.assertRaisesMessage(ValidationError, 'recursos no coinciden'):
            comparar_pdf_nativo(original, alterado)

    def test_cambiar_contenido_o_recortar_hoja_no_pasa(self):
        original = pdf_prueba()
        with self.assertRaises(ValidationError):
            comparar_pdf_nativo(original, pdf_prueba(texto='Otra información ajena al original.'))
        with self.assertRaises(ValidationError):
            comparar_pdf_nativo(original, reescribir(original, lambda w: setattr(w.pages[0], 'cropbox', RectangleObject([0, 0, 100, 100]))))

    def test_javascript_y_archivos_adjuntos_quedan_fuera(self):
        original = pdf_prueba()
        for cambio in (lambda w: w.add_js('app.alert("cambio");'),
                       lambda w: w.add_attachment('adjunto.txt', b'contenido externo')):
            with self.subTest(cambio=cambio), self.assertRaises(ValidationError):
                comparar_pdf_nativo(original, reescribir(original, cambio))

    def test_firma_visible_sin_campo_reservado_necesita_revision(self):
        original = pdf_prueba()
        firmado = reescribir(original, lambda w: widget_firma(w, [20, 20, 200, 80]))
        with self.assertRaisesMessage(ValidationError, 'firma visible'):
            comparar_pdf_nativo(original, firmado)

    def test_firma_invisible_y_campo_de_firma_preexistente_no_cambian_paginas(self):
        original = pdf_prueba()
        self.assertTrue(comparar_pdf_nativo(original, reescribir(original, lambda w: widget_firma(w, [0, 0, 0, 0]))))
        reservado = reescribir(original, lambda w: widget_firma(w, [20, 20, 200, 80]))
        self.assertTrue(comparar_pdf_nativo(reservado, reescribir(reservado)))

    def test_anotacion_no_firma_no_se_ignora(self):
        original = pdf_prueba()
        def anotar(w):
            anotacion = DictionaryObject({NameObject('/Subtype'): NameObject('/Text'),
                NameObject('/Rect'): ArrayObject([NumberObject(v) for v in [20, 20, 200, 80]])})
            w.pages[0][NameObject('/Annots')] = ArrayObject([w._add_object(anotacion)])
        with self.assertRaisesMessage(ValidationError, 'anotaciones ajenas'):
            comparar_pdf_nativo(original, reescribir(original, anotar))

    def test_enlace_web_nativo_identico_se_conserva_al_reescribir_y_firmar(self):
        for uri in ('http://127.0.0.1:8000/recursos-unidad/12/',
                    'https://institucion.example/recursos-unidad/12/'):
            with self.subTest(uri=uri):
                original = pdf_con_enlace(uri)
                def firmar(w):
                    w.pages[0].compress_content_streams()
                    # La referencia inversa no es contenido del enlace.
                    w.pages[0]['/Annots'][0].get_object()[NameObject('/P')] = w.pages[0].indirect_reference
                    widget_firma(w, [0, 0, 0, 0])
                firmado = reescribir(original, firmar)
                self.assertNotEqual(original, firmado)
                self.assertTrue(comparar_pdf_nativo(original, firmado))

    def test_agregar_enlace_web_a_un_documento_nativo_no_pasa(self):
        original = pdf_prueba()
        def agregar(w):
            enlace = DictionaryObject({NameObject('/Type'): NameObject('/Annot'),
                NameObject('/Subtype'): NameObject('/Link'),
                NameObject('/A'): DictionaryObject({NameObject('/S'): NameObject('/URI'),
                    NameObject('/URI'): TextStringObject('https://institucion.example/agregado/')}),
                NameObject('/Rect'): RectangleObject([40, 750, 220, 770])})
            w.pages[0][NameObject('/Annots')] = ArrayObject([w._add_object(enlace)])
        with self.assertRaisesMessage(ValidationError, 'recursos no coinciden'):
            comparar_pdf_nativo(original, reescribir(original, agregar))

    def test_eliminar_enlace_web_nativo_no_pasa(self):
        original = pdf_con_enlace('http://127.0.0.1:8000/recursos-unidad/12/')
        def eliminar(w):
            del w.pages[0]['/Annots']
        with self.assertRaisesMessage(ValidationError, 'recursos no coinciden'):
            comparar_pdf_nativo(original, reescribir(original, eliminar))

    def test_cambiar_destino_area_estilo_o_accion_de_enlace_nativo_no_pasa(self):
        original = pdf_con_enlace('http://127.0.0.1:8000/recursos-unidad/12/')
        def destino(w):
            w.pages[0]['/Annots'][0].get_object()['/A'][NameObject('/URI')] = TextStringObject(
                'https://institucion.example/otro-respaldo/')
        def area(w):
            w.pages[0]['/Annots'][0].get_object()[NameObject('/Rect')] = RectangleObject([0, 0, 500, 500])
        def borde(w):
            w.pages[0]['/Annots'][0].get_object()[NameObject('/Border')] = ArrayObject([
                NumberObject(0), NumberObject(0), NumberObject(5)])
        def javascript(w):
            w.pages[0]['/Annots'][0].get_object()['/A'][NameObject('/URI')] = TextStringObject('javascript:alert(1)')
        def accion_encadenada(w):
            w.pages[0]['/Annots'][0].get_object()['/A'][NameObject('/Next')] = DictionaryObject({
                NameObject('/S'): NameObject('/URI'), NameObject('/URI'): TextStringObject('https://otro.example/')})
        for cambio in (destino, area, borde, javascript, accion_encadenada):
            with self.subTest(cambio=cambio.__name__), self.assertRaises(ValidationError):
                comparar_pdf_nativo(original, reescribir(original, cambio))


class ProcedenciaYControlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='qa-confianza-documental')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de confianza QA', slug='qa-confianza-documental',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2025, 1, 1))
        cls.exigido = DocumentoExigido.objects.create(codigo='QA-CONFIANZA', nombre='Documento nativo QA',
            carpeta='ejecucion', origen='sistema', fuente_reporte='reservas')

    def setUp(self):
        temporal = tempfile.TemporaryDirectory(prefix='citt-qa-confianza-')
        self.addCleanup(temporal.cleanup)
        medios = override_settings(MEDIA_ROOT=temporal.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.doc = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigido,
            anio=2026, corte='B', estado='generado')

    def recurso(self, datos, version=1, anterior=None):
        recurso = Recurso(unidad=self.unidad, nombre='PDF QA confianza', version=version,
            reemplaza_a=anterior, visibilidad='interna')
        recurso.archivo.save('confianza-qa.pdf', ContentFile(datos), save=False)
        recurso.save()
        return recurso

    def preparado(self, *, anclar=True, comandar=True):
        metadatos = dict(identidad_documental(self.doc), esquema=1, contexto_sha256='c' * 64, borrador=False)
        datos = pdf_prueba(codificar_metadatos(metadatos))
        recurso = self.recurso(datos)
        self.doc.recurso, self.doc.version = recurso, 1
        self.doc.save()
        if anclar:
            registrar_procedencia_nativa(self.doc, self.actor)
        if comandar:
            self.comando_generar()
        return datos, recurso

    def comando_generar(self):
        registrar_auditoria(unidad=self.unidad, usuario=self.actor, accion='actualizar', objeto=self.doc,
            descripcion='_generar: QA-CONFIANZA (Período 2026-B, v1)', nuevos=dict(estado='generado',
                recurso_id=self.doc.recurso_id, version=self.doc.version, unidad_id=self.unidad.pk,
                exigido_id=self.exigido.pk))

    def firmado(self, datos):
        origen = self.doc.recurso
        # Sólo se simula la detección estructural que hoy ofrece el sistema.
        firmado = datos + b'\n% /Type /Sig /ByteRange [0 1 2 3]\n'
        self.doc.recurso = self.recurso(firmado, version=2, anterior=origen)
        self.doc.version, self.doc.estado, self.doc.firma_verificada = 2, 'cargado', True
        self.doc.save()
        registrar_auditoria(unidad=self.unidad, usuario=self.actor, accion='actualizar', objeto=self.doc,
            descripcion='cargar_documento: QA-CONFIANZA (Período 2026-B, v2)', nuevos=dict(estado='cargado',
                recurso_id=self.doc.recurso_id, version=2, unidad_id=self.unidad.pk, exigido_id=self.exigido.pk))
        return firmado

    def test_metadatos_sin_generacion_auditada_no_demuestran_procedencia(self):
        self.preparado(anclar=False)
        lectura = comprobar_procedencia(self.doc)
        self.assertFalse(lectura['confiable'])
        self.assertIn('metadatos solos', str(lectura['motivos']))

    def test_ancla_sin_comando_de_generacion_no_demuestra_procedencia(self):
        self.preparado(comandar=False)
        lectura = comprobar_procedencia(self.doc)
        self.assertFalse(lectura['confiable'])
        self.assertIn('comando nativo', str(lectura['motivos']))

    def test_nativo_sin_firma_exige_bytes_exactos_y_no_escribe_notas(self):
        _, origen = self.preparado()
        cantidad = RegistroAuditoriaUnidad.objects.count()
        lectura = comprobar_procedencia(self.doc)
        self.assertTrue(lectura['confiable'], lectura['motivos'])
        self.assertEqual(lectura['origen_recurso'], origen.pk)
        self.assertEqual(lectura['firma_criptografica']['estado'], 'no_requerida')
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), cantidad)
        self.doc.refresh_from_db()
        self.assertIsNone(self.doc.evaluacion)

    def test_ancla_registra_identidad_version_y_huella_sin_aprobar_entrega(self):
        _, origen = self.preparado()
        evento = RegistroAuditoriaUnidad.objects.get(objeto_id=str(self.doc.pk), descripcion=AUDITORIA_PROCEDENCIA)
        self.assertEqual(evento.datos_nuevos['recurso_id'], origen.pk)
        self.assertEqual(evento.datos_nuevos['version'], 1)
        self.assertEqual(evento.datos_nuevos['sha256'], origen.hash_sha256)
        self.assertFalse(evento.datos_nuevos.get('director_revisado', False))
        self.assertEqual(self.doc.estado, 'generado')

    def test_estructura_de_firma_no_se_presenta_como_certificado_autentico(self):
        original, _ = self.preparado()
        self.doc.exigido.requiere_firma = True
        self.doc.exigido.save()
        firmado = self.firmado(original)
        with patch('apps.documentos.presentation.confianza_documental.comparar_pdf_nativo',
                   wraps=comparar_pdf_nativo) as comparar:
            lectura = comprobar_procedencia(self.doc)
        comparar.assert_called_once_with(original, firmado)
        self.assertTrue(lectura['contenido_equivalente'], lectura['motivos'])
        self.assertTrue(lectura['firma_estructural'])
        self.assertEqual(lectura['firma_criptografica']['estado'], 'no_comprobada')

    def test_manipular_bytes_y_hash_del_recurso_no_cambia_huella_auditada(self):
        original, origen = self.preparado()
        alterado = original + b'\n% alteracion posterior\n'
        origen.archivo.save('origen-alterado.pdf', ContentFile(alterado), save=True)
        self.doc.refresh_from_db()
        lectura = comprobar_procedencia(self.doc)
        self.assertFalse(lectura['confiable'])
        self.assertIn('huella registrada', str(lectura['motivos']))

    def test_cambiar_version_o_cadena_del_origen_requiere_revision(self):
        original, _ = self.preparado()
        self.doc.exigido.requiere_firma = True
        self.doc.exigido.save()
        self.firmado(original)
        Recurso.objects.filter(pk=self.doc.recurso_id).update(reemplaza_a=None)
        self.doc.refresh_from_db()
        self.assertIn('cadena de versiones', str(comprobar_procedencia(self.doc)['motivos']))
        self.doc.version = 9
        self.assertFalse(comprobar_procedencia(self.doc)['confiable'])

    def test_archivo_perdido_no_acredita_procedencia(self):
        self.preparado()
        self.doc.recurso.archivo.storage.delete(self.doc.recurso.archivo.name)
        lectura = comprobar_procedencia(self.doc)
        self.assertFalse(lectura['confiable'])
        self.assertFalse(lectura['archivo_integro'])

    def test_control_unico_por_documento_y_snapshot_sin_editar_nota_manual(self):
        self.preparado()
        self.doc.evaluacion, self.doc.evaluacion_version, self.doc.evaluado_por = 81, 1, self.actor
        self.doc.save()
        control = ControlAutomaticoDocumento.objects.create(documento=self.doc, metodo='qa-1',
            version_documento=1, recurso=self.doc.recurso, sha256=self.doc.recurso.hash_sha256,
            estado='automatico', hallazgos=[], resumen={'contenido': 'comprobado'},
            fuentes_sha256=sha256(b'fuentes qa').hexdigest(), nota='90.00', politica={'minimo': 70})
        self.assertEqual(self.doc.control_automatico.pk, control.pk)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            ControlAutomaticoDocumento.objects.create(documento=self.doc, metodo='duplicado')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.evaluacion, 81)

    def test_modelo_y_migracion_conservan_todos_los_campos_del_control(self):
        tabla = ControlAutomaticoDocumento._meta.db_table
        with connection.cursor() as cursor:
            campos = {col.name for col in connection.introspection.get_table_description(cursor, tabla)}
        self.assertTrue({'documento_id', 'metodo', 'version_documento', 'recurso_id', 'sha256', 'estado',
            'hallazgos', 'resumen', 'fuentes_sha256', 'comprobado_en', 'aplicado', 'nota', 'politica'} <= campos)
        control = ControlAutomaticoDocumento(documento=self.doc, metodo='qa-1', nota='101', hallazgos={})
        with self.assertRaises(ValidationError) as error:
            control.full_clean()
        self.assertIn('nota', error.exception.message_dict)
        self.assertIn('hallazgos', error.exception.message_dict)
