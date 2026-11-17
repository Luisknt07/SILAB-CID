"""Identidad, revisión y vigencia del contenido sin modificar archivos históricos."""
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.expediente import cargar_documento, recibir_documento, validar_documento
from apps.documentos.presentation.expediente_archivos import (
    codificar_metadatos, completar_integridad_documental, estado_integridad_documental,
    identidad_documental, versiones_del_documento,
)
from apps.recursos.models.recursos import Recurso
from tests.integration.utiles import abrir_entrega
from tests.integration.test_seguimiento_gobernanza import designar


class CorrespondenciaDocumentalLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='correspondencia-responsable')
        cls.director = get_user_model().objects.create_superuser(username='correspondencia-director')
        designar(cls.director)
        from tests.integration.utiles import identificar
        identificar(cls.actor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio documental QA', slug='documental-qa',
            dependencia='laboratorios', descripcion='Unidad de pruebas aisladas',
            fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Otro laboratorio documental QA', slug='otro-documental-qa',
            dependencia='laboratorios', descripcion='Otra unidad de pruebas', fecha_inicio=date(2026, 1, 1))
        cls.exigido = DocumentoExigido.objects.create(codigo='ACTO-QA', nombre='Acto institucional QA',
            carpeta='planeacion', origen='unidad', periodicidad='anual', plazo_regla='ninguno')

    def documento(self, *, redactable=False):
        exigido = self.exigido
        if redactable:
            exigido = DocumentoExigido.objects.create(codigo='PLAN-QA', nombre='Plan de prueba QA',
                carpeta='planeacion', origen='ambos', periodicidad='semestral', fuente_reporte='planificacion')
        return abrir_entrega(DocumentoExpediente.objects.create(unidad=self.unidad,
            exigido=exigido, anio=2026, corte='B' if redactable else ''))

    @staticmethod
    def pdf(metadatos=None):
        salida = BytesIO()
        canvas = Canvas(salida)
        if metadatos is not None:
            canvas.setSubject(codificar_metadatos(metadatos))
        canvas.drawString(40, 800, 'Documento de prueba: contenido legible para comprobar su correspondencia.')
        canvas.showPage()
        canvas.save()
        return salida.getvalue()

    def declaracion(self, documento):
        return dict(identidad_documental(documento), revisado=True, version=documento.version)

    def cargar(self, documento, metadatos=None):
        cargar_documento(documento, SimpleUploadedFile('documento-qa.pdf', self.pdf(metadatos)), self.actor,
            declaracion_correspondencia=self.declaracion(documento))
        documento.refresh_from_db()

    def test_carga_requiere_confirmacion_de_correspondencia_sin_crear_archivos(self):
        d = self.documento()
        cantidad = Recurso.objects.count()
        with self.assertRaisesMessage(ValidationError, 'Confirma que abriste'):
            cargar_documento(d, SimpleUploadedFile('documento-qa.pdf', self.pdf()), self.actor)
        self.assertEqual(Recurso.objects.count(), cantidad)
        self.assertFalse(d.recurso_id)

    def test_pdf_propio_de_otra_unidad_o_periodo_se_rechaza(self):
        d = self.documento()
        for cambio in ({'unidad_id': self.otra.pk}, {'anio': 2025}, {'codigo': 'OTRO-QA'}):
            datos = dict(identidad_documental(d), esquema=1, contexto_sha256='a' * 64, borrador=False)
            datos.update(cambio)
            with self.assertRaisesMessage(ValidationError, 'otro documento, unidad o período'):
                self.cargar(d, datos)
        self.assertFalse(d.recurso_id)

    def test_borrador_no_se_puede_presentar_como_documento_para_firma(self):
        d = self.documento()
        datos = dict(identidad_documental(d), esquema=1, contexto_sha256='a' * 64, borrador=True)
        with self.assertRaisesMessage(ValidationError, 'vista previa es un borrador'):
            self.cargar(d, datos)

    def test_externo_declarado_no_se_aprueba_y_requiere_revision_director(self):
        d = self.documento()
        self.cargar(d)
        self.assertEqual(d.estado, 'cargado')
        self.assertFalse(estado_integridad_documental(d)['correspondencia_verificada'])
        validar_documento(d, self.actor)
        self.assertEqual(d.estado, 'validado')
        self.assertIsNone(d.recibido_en)
        with self.assertRaisesMessage(ValidationError, 'Dirección debe abrir'):
            recibir_documento(d, self.director)
        recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        self.assertIsNotNone(d.recibido_en)
        self.assertTrue(estado_integridad_documental(d)['correspondencia_verificada'])
        self.assertIsNone(d.evaluacion)

    def test_documento_propietario_correcto_se_conserva_despues_de_enviado(self):
        d = self.documento(redactable=True)
        datos = dict(identidad_documental(d), esquema=1, contexto_sha256='a' * 64, borrador=False)
        with patch('apps.documentos.presentation.expediente_archivos._contexto_actual', return_value='a' * 64):
            self.cargar(d, datos)
            validar_documento(d, self.actor)
        self.unidad.nombre = 'Nombre institucional actualizado después del envío'
        self.unidad.save(update_fields=['nombre'])
        with patch('apps.documentos.presentation.expediente_archivos._contexto_actual', return_value='b' * 64):
            recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        self.assertTrue(estado_integridad_documental(d)['correspondencia_verificada'])

    def test_cambiar_datos_antes_de_enviar_exige_regenerar(self):
        d = self.documento(redactable=True)
        datos = dict(identidad_documental(d), esquema=1, contexto_sha256='a' * 64, borrador=False)
        with patch('apps.documentos.presentation.expediente_archivos._contexto_actual', return_value='a' * 64):
            self.cargar(d, datos)
        with patch('apps.documentos.presentation.expediente_archivos._contexto_actual', return_value='b' * 64):
            with self.assertRaisesMessage(ValidationError, 'desactualizado'):
                validar_documento(d, self.actor)
        self.assertEqual(d.estado, 'cargado')

    def test_cambiar_bytes_o_propietario_no_puede_reusar_la_revision(self):
        d = self.documento()
        self.cargar(d)
        with d.recurso.archivo.open('ab') as archivo:
            archivo.write(b'\nContenido modificado fuera del expediente')
        with self.assertRaisesMessage(ValidationError, 'huella registrada'):
            validar_documento(d, self.actor)
        Recurso.objects.filter(pk=d.recurso_id).update(unidad=self.otra)
        d.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, 'otra unidad'):
            validar_documento(d, self.actor)

    def test_revision_sobre_version_anterior_no_reemplaza_archivo_vigente(self):
        d = self.documento()
        anterior = self.declaracion(d)
        self.cargar(d)
        recurso = d.recurso_id
        with self.assertRaisesMessage(ValidationError, 'versión cambió'):
            cargar_documento(d, SimpleUploadedFile('otro-qa.pdf', self.pdf()), self.actor,
                             declaracion_correspondencia=anterior)
        self.assertEqual(d.recurso_id, recurso)
        self.assertEqual(len(versiones_del_documento(d)), 1)

    def test_listado_no_abre_pdfs_y_archivo_historico_se_conserva(self):
        d = self.documento()
        self.cargar(d)
        with patch('apps.documentos.presentation.expediente_archivos._leer_archivo') as leer:
            completar_integridad_documental([d])
        leer.assert_not_called()
        ruta = d.recurso.archivo.name
        Recurso.objects.filter(pk=d.recurso_id).update(estado='obsoleto')
        d.refresh_from_db()
        self.assertTrue(estado_integridad_documental(d)['bloqueado'])
        self.assertTrue(d.recurso.archivo.storage.exists(ruta))

    def test_pdf_generado_conserva_identidad_interna_sin_afirmar_aprobacion(self):
        from pypdf import PdfReader
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        d = self.documento()
        institucion = SimpleNamespace(nombre='Institución de pruebas', siglas='QA', paleta={})
        identidad = (SimpleNamespace(codigo='QA'), institucion)
        compuesto = dict(documento=d, tipo='planificacion', titulo='Documento de prueba', codigo_formato='INTERNO-QA',
            codigo_etiqueta='Referencia interna', unidad=self.unidad, periodo=d.etiqueta_corte,
            tramo=(date(2026, 1, 1), date(2026, 12, 31)), firmas=[], secciones=[])
        with patch('apps.core.presentation.pdf_institucional.identidad_actual', return_value=identidad), \
                patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None), \
                patch('apps.documentos.presentation.expediente_pdf.identidad_actual', return_value=identidad):
            datos = render_documento_pdf(compuesto)
        pdf = PdfReader(BytesIO(datos))
        self.assertTrue(pdf.metadata.subject.startswith('SLCID-DOC-1:'))
        texto = '\n'.join(pagina.extract_text() or '' for pagina in pdf.pages)
        # La planificación es un documento principal: la referencia interna se declara como código de referencia,
        # sin la revisión del formato de los anexos.
        self.assertIn('Código de referencia: INTERNO-QA', texto)
        self.assertNotIn('Revisión: 01', texto)
        self.assertIn('la versión firmada electrónicamente es', texto)
        self.assertNotIn('Documento aprobado', texto)

    def test_acto_permanente_conserva_revision_y_huella_al_heredarse(self):
        self.exigido.periodicidad = 'unica'
        self.exigido.save(update_fields=['periodicidad'])
        d = self.documento()
        datos = dict(identidad_documental(d), esquema=1, contexto_sha256='a' * 64, borrador=False)
        self.cargar(d, datos)
        validar_documento(d, self.actor)
        recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        heredado = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigido,
            anio=2027, recurso=d.recurso, version=d.version, estado='validado',
            firma_verificada=d.firma_verificada)
        estado = estado_integridad_documental(heredado, inspeccionar=True)
        self.assertFalse(estado['bloqueado'])
        self.assertTrue(estado['correspondencia_verificada'])
        self.assertEqual(heredado.recurso.hash_sha256, d.recurso.hash_sha256)
        virtual = DocumentoExpediente(unidad=self.unidad, exigido=self.exigido, anio=2028,
            recurso=d.recurso, version=d.version, estado='validado')
        self.assertTrue(estado_integridad_documental(virtual)['correspondencia_verificada'])

    def test_huella_contexto_no_cambia_por_instante_de_calculo(self):
        from apps.documentos.presentation.expediente_archivos import huella_contexto_pdf
        a = dict(tipo='informe', tramo=('2026-01-01', '2026-12-31'), firmas=[],
                 secciones=[dict(calculado_en='2026-10-17T10:00:00', pares=[('Fecha de elaboración', '17/10/2026')],
                     registrado=3)])
        b = dict(a, secciones=[dict(calculado_en='2026-10-17T10:00:10',
            pares=[('Fecha de elaboración', '18/10/2026')], registrado=3)])
        self.assertEqual(huella_contexto_pdf(a), huella_contexto_pdf(b))
        b['secciones'][0]['registrado'] = 4
        self.assertNotEqual(huella_contexto_pdf(a), huella_contexto_pdf(b))

    def test_componer_firmar_cargar_enviar_mantiene_contexto_sin_mocks_de_huella(self):
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.presentation.expediente import tramo_del_documento
        from apps.documentos.presentation.expediente_redaccion import componer
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        for tipo in ('planificacion', 'informe'):
            exigido = DocumentoExigido.objects.create(codigo='FLUJO-' + tipo.upper(),
                nombre='Documento de flujo QA', carpeta='planeacion', origen='ambos',
                periodicidad='semestral', fuente_reporte=tipo, requiere_firma=True)
            d = abrir_entrega(DocumentoExpediente.objects.create(unidad=self.unidad,
                exigido=exigido, anio=2026, corte='B'))
            DocumentoElaborado.objects.create(documento=d, contenido={})
            compuesto = componer(d, {}, *tramo_del_documento(d))
            datos = render_documento_pdf(compuesto)
            datos += b'\n% /Type /Sig /ByteRange [0 100 200 300] /Contents <00>\n'
            cargar_documento(d, SimpleUploadedFile('firmado-qa.pdf', datos), self.actor,
                declaracion_correspondencia=self.declaracion(d))
            validar_documento(d, self.actor)
            self.assertEqual(d.estado, 'validado')
            self.assertTrue(d.firma_verificada)
            self.assertFalse(estado_integridad_documental(d)['correspondencia_verificada'])

    def test_http_cargar_y_enviar_conserva_confirmacion_en_la_version_creada(self):
        from tests.integration.utiles import datos_correspondencia_revisada
        d = self.documento()
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
            dict(anio=2026, documento=d.pk, accion='cargar', enviar='1',
                archivo=SimpleUploadedFile('externo-qa.pdf', self.pdf()),
                **datos_correspondencia_revisada(d)))
        self.assertEqual(respuesta.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.estado, 'validado')
        self.assertEqual(d.version, 1)
        self.assertFalse(estado_integridad_documental(d)['correspondencia_verificada'])

    def test_nota_legada_de_un_documento_obligatorio_se_conserva_sin_contar(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado, _matriz
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        d = self.documento()
        self.cargar(d)
        validar_documento(d, self.actor)
        # Simula una calificación histórica anterior al control de correspondencia.
        d.evaluacion, d.evaluacion_version = 90, d.version
        d.save(update_fields=['evaluacion', 'evaluacion_version'])
        previo = progreso_general([d])
        nivel = _nivel_evaluado([d], date(2026, 10, 17))
        self.assertEqual((previo['porcentaje'], previo['calificadas'], previo['total']), (0, 0, 0))
        lectura = acreditacion_actual(d)
        self.assertEqual((lectura['nota_registrada'], lectura['nota_acreditable']), (None, None))
        self.assertEqual((nivel['total'], nivel['total_registrado'],
                          nivel['pendientes_correspondencia']), (None, None, 0))
        self.assertIsNone(nivel['cumple'])
        self.assertIsNone(_matriz([d], date(2026, 10, 17))[0]['cumple'])
        # Enviado pero no recibido: la nota antigua no lo da por cumplido.
        self.assertIsNone(d.cumple)
        recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        confirmado = progreso_general([d])
        self.assertEqual((confirmado['porcentaje'], confirmado['pendientes_correspondencia']), (0, 0))
        self.assertIsNone(acreditacion_actual(d)['nota_acreditable'])
        self.assertEqual(confirmado['sin_ponderacion'][0]['aporte'], 0)
        self.assertIsNone(_nivel_evaluado([d], date(2026, 10, 17))['cumple'])
        fila = _matriz([d], date(2026, 10, 17))[0]
        self.assertTrue(fila['documento'].resumen_interfaz['integridad']['correspondencia_verificada'])
        d.refresh_from_db()
        self.assertEqual((d.nota, d.evaluacion, d.cumple), (None, 90, True))

    def test_nota_historica_de_archivo_ajeno_no_suma_ni_se_borra(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        d = self.documento()
        self.cargar(d)
        validar_documento(d, self.actor)
        d.evaluacion, d.evaluacion_version = 90, d.version
        d.save(update_fields=['evaluacion', 'evaluacion_version'])
        Recurso.objects.filter(pk=d.recurso_id).update(unidad=self.otra)
        d.refresh_from_db()
        estado = progreso_general([d])
        lectura = acreditacion_actual(d)
        self.assertEqual((estado['porcentaje'], lectura['nota'], lectura['nota_acreditable']), (0, None, None))
        self.assertTrue(lectura['integridad']['bloqueado'])
        self.assertIsNone(_nivel_evaluado([d], date(2026, 10, 17))['cumple'])
        with self.assertRaisesMessage(ValidationError, 'otra unidad'):
            recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        d.refresh_from_db()
        self.assertEqual((d.nota, d.evaluacion, d.cumple), (None, 90, None))

    def test_aporte_carga_en_lote_y_reutiliza_lectura_sin_abrir_pdfs(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        d = self.documento()
        self.cargar(d)
        validar_documento(d, self.actor)
        DocumentoExpediente.objects.filter(pk=d.pk).update(evaluacion=90, evaluacion_version=d.version)
        otro = DocumentoExpediente.objects.create(unidad=self.otra, exigido=self.exigido,
            anio=2026, recurso=d.recurso, estado='validado', version=d.version,
            evaluacion=90, evaluacion_version=d.version)
        documentos = list(DocumentoExpediente.objects.filter(pk__in=[d.pk, otro.pk])
                          .select_related('unidad', 'exigido', 'recurso'))
        with patch('apps.documentos.presentation.expediente_archivos._leer_archivo') as leer, \
                patch('apps.documentos.presentation.cumplimiento.minimo_vigente', return_value=70):
            with self.assertNumQueries(2):
                progreso = progreso_general(documentos)
                nivel = _nivel_evaluado(documentos, date(2026, 10, 17))
            with self.assertNumQueries(0):
                progreso_general(documentos)
                _nivel_evaluado(documentos, date(2026, 10, 17))
                acreditaciones = [acreditacion_actual(d) for d in documentos]
        leer.assert_not_called()
        self.assertEqual((progreso['total'], progreso['porcentaje'], nivel['total_registrado']), (0, 0, None))
        self.assertEqual(len(progreso['sin_ponderacion']), 2)
        self.assertTrue(all(a['nota_registrada'] is None and a['nota_acreditable'] is None for a in acreditaciones))

    def test_tipologia_fuera_de_las_cuatro_conserva_acreditacion_sin_puntuar_el_acto_administrativo(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        self.unidad.dependencia = 'centros_id'
        # El catálogo de tipologías tiene su propia lectura inicial; el
        # control documental no añade ninguna consulta para otros tipos.
        self.unidad.codigo_base
        d = DocumentoExpediente(unidad=self.unidad, exigido=self.exigido, anio=2026,
            estado='validado', evaluacion=90, version=1, evaluacion_version=1)
        with patch('apps.documentos.presentation.cumplimiento.minimo_vigente', return_value=70):
            with self.assertNumQueries(0):
                progreso = progreso_general([d])
                nivel = _nivel_evaluado([d], date(2026, 10, 17))
                acreditacion = acreditacion_actual(d)
        self.assertEqual((progreso['porcentaje'], progreso['pendientes_correspondencia']), (0, 0))
        self.assertIsNone(acreditacion['nota_acreditable'])
        self.assertTrue(acreditacion['acreditable'])
        self.assertIsNone(nivel['cumple'])

    def test_mejora_actual_separa_nota_registrada_de_correspondencia_pendiente(self):
        from apps.documentos.presentation.cumplimiento import cumplimiento_de_unidad, totales_de
        from apps.documentos.presentation.mejora_continua import cumplimiento_del_periodo
        from apps.documentos.presentation.progreso_general import acreditacion_actual
        d = self.documento()
        self.cargar(d)
        validar_documento(d, self.actor)
        d.evaluacion, d.evaluacion_version = 90, d.version
        d.save(update_fields=['evaluacion', 'evaluacion_version'])
        with patch('apps.documentos.presentation.expediente_archivos._leer_archivo') as leer:
            nivel = cumplimiento_del_periodo(self.unidad, 2026, 'B', hoy=date(2026, 10, 17))
            fila = cumplimiento_de_unidad(self.unidad, 2026, 'B', hoy=date(2026, 10, 17))
        leer.assert_not_called()
        documento = next(f for f in nivel['filas'] if f['documento'].pk == d.pk)
        self.assertEqual((documento['nota'], documento['nota_acreditable']), (None, None))
        self.assertIsNone(documento['nota_registrada'])
        self.assertTrue(documento['correspondencia_pendiente'])
        self.assertIsNone(acreditacion_actual(documento['documento'])['nota_acreditable'])
        self.assertIsNone(nivel['total'])
        totales = totales_de([fila])
        self.assertEqual((totales['evaluadas'], totales['cumplen_minimo'],
                          totales['pendientes_correspondencia'], totales['bajo_minimo']), (0, 0, 0, 0))
        recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        nivel = cumplimiento_del_periodo(self.unidad, 2026, 'B', hoy=date(2026, 10, 17))
        documento = next(f for f in nivel['filas'] if f['documento'].pk == d.pk)
        self.assertEqual((documento['nota'], documento['nota_acreditable']), (None, None))
        self.assertIsNone(acreditacion_actual(documento['documento'])['nota_acreditable'])
        self.assertIsNone(nivel['total'])
        self.assertFalse(nivel['pendientes_correspondencia'])

    def test_revision_anterior_del_mismo_recurso_no_acredita_otra_version(self):
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        d = self.documento()
        self.cargar(d)
        recibir_documento(d, self.director, declaracion_correspondencia=self.declaracion(d))
        self.assertTrue(estado_integridad_documental(d)['correspondencia_verificada'])
        d.version += 1
        d.evaluacion, d.evaluacion_version = 90, d.version
        d.save(update_fields=['version', 'evaluacion', 'evaluacion_version'])
        self.assertFalse(estado_integridad_documental(d)['correspondencia_verificada'])
        self.assertEqual(progreso_general([d])['porcentaje'], 0)
        self.assertIsNone(acreditacion_actual(d)['nota_acreditable'])
        d = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=d.pk)
        self.assertFalse(estado_integridad_documental(d)['correspondencia_verificada'])
        self.assertEqual(progreso_general([d])['porcentaje'], 0)
        self.assertIsNone(acreditacion_actual(d)['nota_acreditable'])

    def test_cero_por_no_entrega_es_antecedente_sin_inventar_desempeno_de_la_unidad(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado
        from apps.documentos.presentation.progreso_general import acreditacion_actual, progreso_general
        d = DocumentoExpediente(unidad=self.unidad, exigido=self.exigido, anio=2026,
            estado='pendiente', evaluacion=0, evaluacion_version=0, version=0)
        with patch('apps.documentos.presentation.cumplimiento.minimo_vigente', return_value=70):
            datos = progreso_general([d])
            nivel = _nivel_evaluado([d], date(2026, 10, 17))
        self.assertEqual((datos['porcentaje'], datos['pendientes_correspondencia']), (0, 0))
        self.assertEqual((nivel['total'], nivel['pendientes_correspondencia']), (None, 0))
        self.assertIsNone(acreditacion_actual(d)['nota_registrada'])
        self.assertIsNone(nivel['cumple'])

    def test_siguiente_paso_usa_correspondencia_precargada_sin_consultas(self):
        from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
        # Recibido antes del control de correspondencia: queda aceptado, pero la comprobación sigue pendiente.
        d = DocumentoExpediente(unidad=self.unidad, exigido=self.exigido, anio=2026,
            estado='validado', recibido_en=timezone.now(), version=1)
        d.integridad_documental = dict(aplica=True, correspondencia_verificada=False)
        with self.assertNumQueries(0):
            pendiente = resumen_de_entrega(d)
        # Las ramas existentes pueden leer la política institucional; la rama
        # nueva con correspondencia precargada no la consulta ni añade lecturas.
        d.integridad_documental['correspondencia_verificada'] = True
        verificada = resumen_de_entrega(d)
        d.integridad_documental = dict(aplica=False, correspondencia_verificada=False)
        fuera_del_alcance = resumen_de_entrega(d)
        self.assertEqual(pendiente['siguiente_paso'], 'Dirección: comprobar correspondencia del documento')
        self.assertEqual(pendiente['paso_unidad'], 'Esperar comprobación de correspondencia por Dirección')
        self.assertEqual(verificada['siguiente_paso'], 'Entrega aceptada')
        self.assertEqual(verificada['paso_unidad'], 'Consultar la respuesta de Dirección')
        self.assertEqual(fuera_del_alcance['siguiente_paso'], verificada['siguiente_paso'])
        self.assertEqual((pendiente['nota'], verificada['nota'], d.nota), (None, None, None))
