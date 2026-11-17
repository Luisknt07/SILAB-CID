"""Emisión real del protocolo adaptable y compatibilidad del catálogo anterior."""
from io import BytesIO

from django.contrib.auth import get_user_model
from pypdf import PdfReader

from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido
from apps.documentos.presentation.aprobacion_en_linea import (
    admite_aprobacion_en_linea, decidir_documento_qr, enviar_documento_qr, estado_constancia,
)
from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
from apps.documentos.presentation.expediente import generar_documento, tramo_del_documento
from apps.documentos.presentation.expediente_archivos import identidad_documental
from apps.documentos.presentation.expediente_redaccion import obtener_redaccion, secciones_de
from apps.documentos.presentation.validacion_pdf import copia_aprobada
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.test_protocolo_seguridad import protocolo_completo
from tests.integration.utiles import abrir_entrega, contenido_plan_completo
from tests.integration.test_seguimiento_gobernanza import designar


class RevisionFlujoTipologiasTests(BaseDeRedaccion):
    def texto_pdf(self, contenido):
        return '\n'.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages)

    def contenido_simple(self, documento):
        contenido = dict(obtener_redaccion(documento).contenido)
        for seccion in secciones_de(documento.exigido.fuente_reporte, documento.unidad):
            for campo in seccion.campos:
                if not campo.requerido:
                    continue
                contenido[campo.clave] = ([campo.opciones[0][0]] if campo.tipo == 'marcas' else
                    campo.opciones[0][0] if campo.tipo == 'opcion' else
                    '<p>Actividades, recursos y responsables verificados para esta prueba aislada.</p>')
        contenido.update(firma_nombre=self.coordinador.get_full_name(), firma_cargo='Responsable de la unidad')
        if documento.exigido.fuente_reporte == 'compras':
            contenido['sin_compras_justificacion'] = '<p>Los recursos registrados cubren las actividades; no se solicitan compras.</p>'
        return contenido

    def test_protocolo_observatorio_emite_envia_y_aprueba_con_mismo_qr_y_dos_identidades(self):
        self.unidad.dependencia = 'observatorios'
        self.unidad.nombre = 'Observatorio de información territorial QA'
        self.unidad.save(update_fields=['dependencia', 'nombre'])
        protocolo = self.documento('PROTOCOLO-BIOSEGURIDAD', corte='')
        director = get_user_model().objects.create_superuser('direccion-flujo-observatorio', password=None,
            first_name='Elena', last_name='Directora')
        designar(director)
        for usuario, cedula in ((self.coordinador, '0400000001'), (director, '0400000002')):
            usuario.profile.cedula = cedula
            usuario.profile.save(update_fields=['cedula'])
        contenido = protocolo_completo(protocolo)
        self.assertIn('análisis de información', contenido['alcance_protocolo'])
        self.assertTrue(admite_aprobacion_en_linea(protocolo))
        DocumentoElaborado.objects.create(documento=protocolo, contenido=contenido, version=1)

        generar_documento(protocolo, self.coordinador)
        enviar_documento_qr(protocolo, self.coordinador,
            token=protocolo.verificacion_qr, version=protocolo.version)
        constancia = ConstanciaDocumento.objects.select_related('documento', 'recurso').get(token=protocolo.verificacion_qr)
        ancla = (constancia.token, constancia.recurso_id, constancia.version, constancia.sha256)
        self.assertEqual(estado_constancia(constancia), 'PENDIENTE DE APROBACIÓN')
        self.assertEqual(constancia.enviado_por_id, self.coordinador.pk)
        with constancia.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        self.assertIn('0400000001', self.texto_pdf(original))

        decidir_documento_qr(protocolo, director, token=constancia.token,
            version=constancia.version, decision='aprobar')
        protocolo.refresh_from_db()
        constancia.refresh_from_db()
        self.assertEqual((constancia.token, constancia.recurso_id, constancia.version, constancia.sha256), ancla)
        self.assertEqual(protocolo.verificacion_qr, constancia.token)
        self.assertEqual((constancia.emisor_nombre, constancia.aprobador_nombre),
                         ('Ana Coordinadora', 'Elena Directora'))
        self.assertEqual((constancia.emisor_cedula, constancia.aprobador_cedula), ('0400000001', '0400000002'))
        self.assertEqual(estado_constancia(constancia), 'VIGENTE')
        self.assertTrue(aprobacion_vigente(protocolo, inspeccionar=True))
        aprobado = copia_aprobada(original, constancia)
        texto = self.texto_pdf(aprobado).upper()
        for dato in ('ANA COORDINADORA', 'ELENA DIRECTORA', '0400000001', '0400000002'):
            self.assertIn(dato, texto)
        pdf = PdfReader(BytesIO(aprobado))
        enlaces = str([anotacion.get_object() for pagina in pdf.pages for anotacion in pagina.get('/Annots', [])])
        self.assertIn(str(constancia.token), enlaces)
        self.assertEqual(ConstanciaDocumento.objects.filter(documento=protocolo).count(), 1)

    def test_tres_nombres_historicos_se_preparan_y_emiten_con_identidad_estable(self):
        anteriores = {
            'PLANIFICACION': 'Planificación semestral de la unidad (firmada)',
            'INFORME-SEMESTRAL': 'Informe semestral de actividades (firmado)',
            'PLAN-COMPRAS-ANUAL': 'Plan anual de compras y presupuesto del año siguiente (firmado)',
        }
        for codigo, nombre in anteriores.items():
            DocumentoExigido.objects.filter(codigo=codigo).update(nombre=nombre)
        for codigo, nombre_anterior in anteriores.items():
            with self.subTest(codigo=codigo):
                documento = abrir_entrega(self.documento(codigo, corte='' if codigo == 'PLAN-COMPRAS-ANUAL' else 'A'))
                identidad = identidad_documental(documento)
                nombre_presentado = documento.nombre_documental
                self.assertEqual(documento.exigido.nombre, nombre_anterior)
                self.assertNotIn('(firmad', nombre_presentado)
                self.assertTrue(admite_aprobacion_en_linea(documento))
                contenido = (contenido_plan_completo(documento, self.coordinador)
                    if codigo == 'PLANIFICACION' else self.contenido_simple(documento))
                DocumentoElaborado.objects.create(documento=documento, contenido=contenido, version=1)
                tramo = tramo_del_documento(documento)

                generar_documento(documento, self.coordinador)
                documento.refresh_from_db()
                constancia = ConstanciaDocumento.objects.get(token=documento.verificacion_qr)
                self.assertEqual(identidad_documental(documento), identidad)
                self.assertEqual(tramo_del_documento(documento), tramo)
                self.assertEqual((constancia.documento_id, constancia.recurso_id), (documento.pk, documento.recurso_id))
                self.assertEqual(constancia.titulo, nombre_presentado)
                self.assertEqual((documento.estado, constancia.enviado_en), ('generado', None))
                self.assertEqual(documento.exigido.nombre, nombre_anterior)
                with documento.recurso.archivo.open('rb') as archivo:
                    texto = self.texto_pdf(archivo.read())
                titulo_pdf = 'Plan anual de compras' if codigo == 'PLAN-COMPRAS-ANUAL' else nombre_presentado
                self.assertIn(' '.join(titulo_pdf.upper().split()), ' '.join(texto.upper().split()))
                self.assertNotIn('(FIRMAD', texto.upper())
