"""Recorrido autenticado, trazabilidad de versiones y verificación sin subir archivos."""
from tests.integration.test_seguimiento_gobernanza import designar
from copy import deepcopy
from io import BytesIO
import re
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from pypdf import PdfReader

from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.aprobacion_en_linea import (
    comprobar_emision, decidir_documento_qr, enviar_documento_qr, estado_constancia,
    completar_constancias, lectura_aprobacion_qr,
)
from apps.documentos.presentation.expediente import generar_documento
from apps.documentos.presentation.expediente_redaccion import secciones_de
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.utiles import abrir_entrega


class AprobacionDocumentalQrTests(BaseDeRedaccion):
    def setUp(self):
        self.documento_qr = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        self.director = get_user_model().objects.create_superuser('direccion-aprobacion-qr', password=None,
            first_name='Dirección', last_name='de prueba')
        designar(self.director)
        self.coordinador.profile.cedula = '0400000001'
        self.coordinador.profile.save(update_fields=['cedula'])
        self.director.profile.cedula = '0400000002'
        self.director.profile.save(update_fields=['cedula'])
        contenido = {}
        for seccion in secciones_de('compras', self.unidad):
            for campo in seccion.campos:
                if campo.requerido:
                    contenido[campo.clave] = ([campo.opciones[0][0]] if campo.tipo == 'marcas' else
                        campo.opciones[0][0] if campo.tipo == 'opcion' else
                        '<p>Necesidades y recursos identificados para la gestión de la unidad.</p>')
        contenido['sin_compras_justificacion'] = '<p>La dotación actual cubre las necesidades; no se solicitan compras.</p>'
        DocumentoElaborado.objects.create(documento=self.documento_qr, contenido=contenido)

    def emitir(self):
        generar_documento(self.documento_qr, self.coordinador)
        self.documento_qr.refresh_from_db()
        return ConstanciaDocumento.objects.select_related('documento', 'recurso').get(documento=self.documento_qr,
            version=self.documento_qr.version)

    def enviar(self):
        c = self.emitir()
        enviar_documento_qr(self.documento_qr, self.coordinador, token=c.token, version=c.version)
        c.refresh_from_db()
        return c

    def aprobar(self, c, actor=None, **cambios):
        datos = dict(token=c.token, version=c.version, decision='aprobar')
        datos.update(cambios)
        decidir_documento_qr(self.documento_qr, actor or self.director, **datos)
        c.refresh_from_db()

    def test_generacion_emite_qr_y_envia_sin_descargar_firmar_o_cargar(self):
        c = self.enviar()
        self.documento_qr.refresh_from_db()
        self.assertEqual(self.documento_qr.estado, 'validado')
        self.assertFalse(self.documento_qr.firma_verificada)
        self.assertFalse(self.documento_qr.firma_pendiente)
        self.assertEqual(c.enviado_por_id, self.coordinador.pk)
        self.assertEqual(c.sha256, self.documento_qr.recurso.hash_sha256)
        with c.recurso.archivo.open('rb') as archivo:
            pdf = PdfReader(BytesIO(archivo.read()))
            texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertIn('RESPONSABILIDAD Y APROBACIÓN', texto)
        self.assertIn('ELABORADO POR', texto)
        self.assertIn('APROBADO POR', texto)
        self.assertNotIn('BORRADOR', texto)
        self.assertFalse(any(v.get('/FT') == '/Sig' for v in (pdf.get_fields() or {}).values()))
        self.assertEqual(estado_constancia(c), 'PENDIENTE DE APROBACIÓN')

    def test_director_aprueba_y_no_cambia_archivo_version_o_puntos(self):
        c = self.enviar()
        anterior = (c.sha256, c.version, c.recurso_id)
        self.aprobar(c)
        c.documento.refresh_from_db()
        self.assertEqual(estado_constancia(c), 'VIGENTE')
        self.assertEqual(c.aprobador_nombre, 'Dirección de prueba')
        self.assertEqual(c.aprobado_por_id, self.director.pk)
        self.assertEqual((c.sha256, c.version, c.recurso_id), anterior)
        from apps.documentos.presentation.progreso_general import progreso_general
        progreso = progreso_general([c.documento])
        self.assertIsNone(progreso['resultado_porcentaje'])
        self.assertEqual(progreso['sin_ponderacion'][0]['aporte'], 0)
        self.assertFalse(progreso['sin_ponderacion'][0]['puntua'])

    def test_copia_aprobada_conserva_qr_y_original_con_ambos_responsables(self):
        from apps.documentos.presentation.validacion_pdf import copia_aprobada
        import hashlib
        c = self.enviar()
        self.aprobar(c)
        with c.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        aprobado = copia_aprobada(original, c)
        self.assertEqual(aprobado, copia_aprobada(original, c))
        self.assertTrue(c.archivo_aprobado)
        self.assertEqual(hashlib.sha256(aprobado).hexdigest(), c.sha256_aprobado)
        with patch('apps.documentos.presentation.validacion_pdf._representar_aprobada',
                   side_effect=AssertionError('Una copia conservada no debe regenerarse.')):
            self.assertEqual(copia_aprobada(original, c), aprobado)
        pdf = PdfReader(BytesIO(aprobado))
        self.assertTrue(pdf.outline)
        texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertIn('ANA COORDINADORA', texto)
        self.assertIn('DIRECCIÓN DE PRUEBA', texto)
        self.assertIn('Cédula:', texto)
        self.assertIn('0400000001', texto)
        self.assertIn('0400000002', texto)
        self.assertIn('DOCUMENTO APROBADO POR DIRECCIÓN', texto)
        self.assertNotIn('Pendiente de aprobación', texto)
        self.assertEqual(len(pdf.pages), len(PdfReader(BytesIO(original)).pages))
        self.assertIn(str(c.token), str([a.get_object() for p in pdf.pages for a in p.get('/Annots', [])]))
        self.client.force_login(self.director)
        r = self.client.get(reverse('recurso_unidad', args=[c.recurso_id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), aprobado)
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, hashlib.sha256(aprobado).hexdigest())
        self.assertContains(r, c.sha256)
        with c.recurso.archivo.open('rb') as archivo:
            self.assertEqual(hashlib.sha256(archivo.read()).hexdigest(), c.sha256)

    def test_la_copia_aprobada_no_admite_cambiar_huella_y_detecta_alteracion(self):
        c = self.enviar()
        self.aprobar(c)
        c.sha256_aprobado = 'f' * 64
        with self.assertRaisesMessage(ValidationError, 'conserva sin modificaciones'):
            c.save()
        c.refresh_from_db()
        with c.archivo_aprobado.open('ab') as archivo:
            archivo.write(b'\n% copia alterada\n')
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, 'NO VERIFICABLE')

    def test_cedulas_se_conservan_con_la_emision_y_aprobacion(self):
        c = self.enviar()
        self.coordinador.profile.cedula = '0400000010'
        self.coordinador.profile.save(update_fields=['cedula'])
        self.aprobar(c)
        self.director.profile.cedula = '0400000020'
        self.director.profile.save(update_fields=['cedula'])
        c.refresh_from_db()
        self.assertEqual(c.emisor_cedula, '0400000001')
        self.assertEqual(c.aprobador_cedula, '0400000002')
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, '0400000001')
        self.assertContains(r, '0400000002')
        self.assertNotContains(r, '0400000010')
        c.emisor_cedula = '0000000000'
        with self.assertRaisesMessage(ValidationError, 'identidad'):
            c.save()

    def test_presentacion_usa_el_contenido_emitido_y_no_recalcula_datos_actuales(self):
        from apps.documentos.presentation.validacion_pdf import _representar_aprobada
        c = self.enviar()
        self.aprobar(c)
        self.assertTrue(c.contenido_emitido)
        with c.recurso.archivo.open('rb') as archivo:
            original=archivo.read()
        nombre=c.unidad_nombre
        self.unidad.nombre='Nombre cambiado después de la aprobación'
        self.unidad.save(update_fields=['nombre'])
        with patch('apps.documentos.presentation.expediente_redaccion.componer',side_effect=AssertionError('No se consulta el contenido actual.')):
            copia=_representar_aprobada(original,c)
        texto=' '.join(p.extract_text() or '' for p in PdfReader(BytesIO(copia)).pages)
        self.assertIn(nombre,texto)
        self.assertNotIn('Nombre cambiado después',texto)
        c.contenido_emitido={}
        with self.assertRaisesMessage(ValidationError,'identidad'):
            c.save()

    def test_emision_pendiente_y_aprobacion_conservan_sus_descargas_con_el_mismo_qr(self):
        import hashlib
        from apps.documentos.presentation.validacion_pdf import copia_aprobada, copia_preparada
        c=self.enviar()
        with c.recurso.archivo.open('rb') as archivo:
            original=archivo.read()
        pendiente=copia_preparada(original,c)
        self.assertEqual(pendiente,copia_preparada(original,c))
        texto=' '.join(p.extract_text() or '' for p in PdfReader(BytesIO(pendiente)).pages)
        self.assertIn('DOCUMENTO EMITIDO PARA REVISIÓN',texto)
        self.assertNotIn('DOCUMENTO APROBADO POR DIRECCIÓN',texto)
        self.aprobar(c)
        aprobada=copia_aprobada(original,c)
        self.assertNotEqual(pendiente,aprobada)
        r=self.client.get(reverse('verificar_documento_qr',args=[c.token]))
        self.assertContains(r,hashlib.sha256(pendiente).hexdigest())
        self.assertContains(r,hashlib.sha256(aprobada).hexdigest())
        self.assertTrue(c.presentaciones.filter(aprobada=False).exists())

    def test_pdf_anterior_recupera_tablas_y_ceros_sin_usar_fuentes_actuales(self):
        import hashlib
        from apps.documentos.presentation.contenido_emitido import recuperar_del_pdf, restaurar_compuesto
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        c=self.enviar()
        compuesto=restaurar_compuesto(c.contenido_emitido,c)
        filas=[[f'EQUIPO-REGISTRO-PATRIMONIAL-{i:03d}',str(i),'17'] for i in range(65)]
        compuesto['secciones']=[
            dict(numero=1,codigo='inventario',titulo='INVENTARIO CONSERVADO',bloques=[
                dict(tipo='tabla',titulo='Recursos',cabecera=['Equipo','Cantidad','Meta'],filas=filas)]),
            dict(numero=2,codigo='firmas',titulo='VALIDACIÓN DOCUMENTAL',bloques=[])]
        original=render_documento_pdf(compuesto)
        c.sha256=hashlib.sha256(original).hexdigest()
        with patch('apps.documentos.presentation.expediente_redaccion.componer',side_effect=AssertionError):
            recuperado=recuperar_del_pdf(original,c)
        tablas=[b for s in recuperado['secciones'] for b in s['bloques'] if b['tipo']=='tabla']
        recuperadas=[fila for t in tablas for fila in t['filas']]
        self.assertEqual(recuperadas,filas)
        self.assertIn(str(c.token),recuperado['url_verificacion'])

    def test_formato_actual_no_sustituye_la_copia_anterior_y_ambas_son_verificables(self):
        import hashlib
        from pypdf import PdfWriter
        from apps.documentos.presentation.validacion_pdf import copia_aprobada
        c = self.enviar()
        self.aprobar(c)
        with c.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        anterior = PdfWriter()
        with c.archivo_aprobado.open('rb') as archivo:
            anterior.clone_document_from_reader(PdfReader(BytesIO(archivo.read())))
        from reportlab.pdfgen.canvas import Canvas
        sello_anterior = BytesIO()
        lienzo = Canvas(sello_anterior)
        lienzo.drawString(40, 40, 'Versión: 4')
        lienzo.save()
        anterior.pages[0].merge_page(PdfReader(BytesIO(sello_anterior.getvalue())).pages[0])
        anterior.add_metadata({'/SLCIDFormatoValidacion': '3'})
        salida = BytesIO()
        anterior.write(salida)
        contenido_anterior = salida.getvalue()
        huella_anterior = hashlib.sha256(contenido_anterior).hexdigest()
        with c.archivo_aprobado.open('wb') as archivo:
            archivo.write(contenido_anterior)
        ConstanciaDocumento.objects.filter(pk=c.pk).update(sha256_aprobado=huella_anterior)
        c.refresh_from_db()
        nueva = copia_aprobada(original, c)
        self.assertNotEqual(nueva, contenido_anterior)
        texto_nuevo = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(nueva)).pages)
        # El plan de compras es un documento principal: su encabezado lleva código de referencia y cobertura, sin
        # la versión del formato de los anexos; el sello «Versión: 4» de la copia anterior no se arrastra.
        self.assertNotIn('Versión:', texto_nuevo)
        self.assertNotIn('Versión del documento:', texto_nuevo)
        self.assertIn('ELABORADO POR', texto_nuevo)
        self.assertIn('APROBADO POR', texto_nuevo)
        self.assertEqual(c.presentaciones.count(), 1)
        with c.archivo_aprobado.open('rb') as archivo:
            self.assertEqual(archivo.read(), contenido_anterior)
        self.assertEqual(c.sha256_aprobado, huella_anterior)
        with patch('apps.documentos.presentation.validacion_pdf._representar_aprobada', side_effect=AssertionError):
            self.assertEqual(copia_aprobada(original, c), nueva)
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, huella_anterior)
        self.assertContains(r, hashlib.sha256(nueva).hexdigest())
        presentacion = c.presentaciones.get()
        self.assertEqual(self.client.get(presentacion.archivo.url).status_code, 404)
        with presentacion.archivo.open('ab') as archivo:
            archivo.write(b'alteracion')
        self.assertContains(self.client.get(reverse('verificar_documento_qr', args=[c.token])), 'NO VERIFICABLE')

    def test_fallo_final_de_auditoria_revierte_aprobacion_y_copia(self):
        from pathlib import Path
        from django.conf import settings
        from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
        c = self.enviar()
        archivos = {p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
        def auditar(*args, **kwargs):
            if kwargs.get('descripcion') == 'aprobacion_en_plataforma':
                raise RuntimeError('Fallo al registrar la decisión.')
            return registrar_auditoria(*args, **kwargs)
        with patch('apps.gestion_unidades.presentation.auditoria.registrar_auditoria', side_effect=auditar):
            with self.assertRaises(RuntimeError):
                self.aprobar(c)
        c.refresh_from_db()
        self.assertIsNone(c.aprobado_en)
        self.assertFalse(c.archivo_aprobado)
        self.assertEqual({p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}, archivos)
        completar_constancias([self.documento_qr])
        self.assertEqual(lectura_aprobacion_qr(self.documento_qr)['estado'], 'pendiente')

    def test_unidad_no_puede_aprobar_su_documento_ni_suplantar_version(self):
        c = self.enviar()
        with self.assertRaisesMessage(ValidationError, 'No tienes permiso'):
            self.aprobar(c, self.coordinador)
        for cambios in (dict(token=uuid4()), dict(version=c.version + 1)):
            with self.assertRaisesMessage(ValidationError, 'versión cambió'):
                self.aprobar(c, **cambios)
        self.assertIsNone(c.aprobado_por_id)

    def test_no_se_aprueba_una_version_que_la_unidad_no_envio(self):
        c = self.emitir()
        with self.assertRaisesMessage(ValidationError, 'debe enviar'):
            self.aprobar(c)

    def test_observar_y_reemitir_conserva_constancia_y_renueva_el_qr(self):
        c = self.enviar()
        self.aprobar(c)
        self.aprobar(c, decision='observar', observacion='Aclarar las necesidades del siguiente año.')
        self.documento_qr.refresh_from_db()
        c.documento.refresh_from_db()
        self.assertEqual(estado_constancia(c), 'OBSERVADO')
        self.assertTrue(self.documento_qr.correccion_abierta)
        nuevo = self.emitir()
        c.documento.refresh_from_db()
        self.assertNotEqual(c.token, nuevo.token)
        self.assertEqual(estado_constancia(c), 'SUSTITUIDO')
        self.assertEqual(ConstanciaDocumento.objects.filter(documento=self.documento_qr).count(), 2)

    def test_modificar_archivo_impide_envio_aprobacion_y_vigencia_publica(self):
        c = self.emitir()
        with c.recurso.archivo.open('ab') as archivo:
            archivo.write(b'\n% archivo modificado\n')
        with self.assertRaisesMessage(ValidationError, 'modificado'):
            comprobar_emision(self.documento_qr)
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, 'NO VERIFICABLE')

    def test_verificacion_publica_solo_metadatos_y_hash_local(self):
        c = self.enviar()
        self.aprobar(c)
        self.client.logout()
        r = self.client.get(reverse('verificar_documento_qr', args=[c.token]))
        self.assertContains(r, 'Documento aprobado')
        self.assertContains(r, 'Dirección de prueba')
        self.assertContains(r, c.sha256)
        self.assertContains(r, 'el archivo no se sube al servidor')
        self.assertNotContains(r, 'data-ver-pdf data-pdf-titulo')
        self.assertEqual(r['Cache-Control'], 'no-store')
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(self.client.get(c.archivo_aprobado.url).status_code, 404)
        self.assertEqual(self.client.post(reverse('verificar_documento_qr', args=[c.token])).status_code, 405)
        self.assertEqual(self.client.get(reverse('verificar_documento_qr', args=[uuid4()])).status_code, 404)

    def test_archivo_desaparecido_da_un_error_claro_sin_confirmar_la_entrega(self):
        c = self.emitir()
        c.recurso.archivo.storage.delete(c.recurso.archivo.name)
        with self.assertRaisesMessage(ValidationError, 'no está disponible'):
            enviar_documento_qr(self.documento_qr, self.coordinador, token=c.token, version=c.version)
        self.documento_qr.refresh_from_db()
        self.assertNotEqual(self.documento_qr.estado, 'validado')

    def test_otra_unidad_no_envia_esta_version_y_constancia_no_admite_cambiar_huella(self):
        c = self.emitir()
        otro = get_user_model().objects.create_user('otro-administrador-qr')
        with self.assertRaises(ValidationError):
            enviar_documento_qr(self.documento_qr, otro, token=c.token, version=c.version)
        c.sha256 = '0' * 64
        with self.assertRaisesMessage(ValidationError, 'identidad'):
            c.save()

    def test_editor_ofrece_enviar_y_director_revision_sin_rubrica_duplicada(self):
        self.client.force_login(self.coordinador)
        r = self.client.get(self.ruta_editor(self.documento_qr))
        self.assertContains(r, 'Generar y enviar')
        self.assertNotContains(r, 'Firmar y cargar')
        self.enviar()
        self.client.force_login(self.director)
        url = reverse('admin:reportes-cumplimiento-expediente')
        r = self.client.get(url, dict(anio=2026, corte='', unidad=self.unidad.slug, revisar=self.documento_qr.pk))
        self.assertContains(r, 'data-decision-qr')
        self.assertContains(r, '>Aprobar</button>')
        self.assertContains(r, '>Rechazar</a>')
        self.assertNotContains(r, 'data-rubrica')

    def filas_de_revision(self):
        self.client.force_login(self.director)
        director = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
            dict(anio=2026, corte='', unidad=self.unidad.slug))
        self.assertEqual(director.status_code, 200)
        fila_director = re.search(r'<tr data-avance-documento="' + str(self.documento_qr.pk)
            + r'".*?</tr>', director.content.decode(), re.S)[0]
        self.client.force_login(self.coordinador)
        unidad = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]),
            dict(anio=2026, corte='A'))
        self.assertEqual(unidad.status_code, 200)
        fila_unidad = re.search(r'<tr[^>]+id="entrega-' + str(self.documento_qr.pk)
            + r'".*?</tr>', unidad.content.decode(), re.S)[0]
        return fila_director, fila_unidad

    def test_ambos_listados_muestran_aprobado_verde_y_acciones_sin_duplicados(self):
        c = self.enviar()
        self.aprobar(c)
        director, unidad = self.filas_de_revision()
        for fila in (director, unidad):
            self.assertIn('is-verde" data-estado-aprobacion="aprobado">Aprobado</strong>', fila)
            self.assertNotIn('Enviado a Dirección', fila)
            self.assertNotIn('Aprobación y vigencia', fila)
            self.assertEqual(fila.count('data-ver-pdf'), 1)
        self.assertIn('is-aprobar" disabled>Aprobar</button>', director)
        self.assertIn('decision=rechazar', director)
        self.assertNotIn('Revisar aprobación', director)

    def test_rechazo_rojo_es_visible_para_la_unidad_y_el_director(self):
        c = self.enviar()
        self.aprobar(c, decision='observar', observacion='Precisar la necesidad y el respaldo.')
        director, unidad = self.filas_de_revision()
        for fila in (director, unidad):
            self.assertIn('is-rojo" data-estado-aprobacion="rechazado">Rechazado</strong>', fila)
            self.assertNotIn('Precisar la necesidad', fila)
            self.assertIn('Observaciones', fila)
        self.assertIn('is-aprobar" disabled>Aprobar</button>', director)
        self.assertIn('Editar', unidad)

    def test_aprobacion_desde_fila_y_rechazo_desde_modal_regresan_al_mismo_listado(self):
        c = self.enviar()
        self.client.force_login(self.director)
        url = reverse('admin:reportes-cumplimiento-expediente')
        filtros = f'anio=2026&corte=&unidad={self.unidad.slug}'
        datos = dict(documento=self.documento_qr.pk, version=c.version, token=c.token, query=filtros)
        r = self.client.post(url, dict(datos, accion='aprobar_qr'), follow=True)
        self.assertContains(r, 'Documento aprobado.')
        self.assertContains(r, 'data-estado-aprobacion="aprobado"')
        r = self.client.get(url, dict(anio=2026, corte='', unidad=self.unidad.slug,
            revisar=self.documento_qr.pk, decision='rechazar'))
        self.assertNotRegex(r.content.decode(), r'data-rechazo-qr\s+hidden')
        self.assertContains(r, 'name="observacion" required')
        r = self.client.post(url, dict(datos, accion='observar_qr', observacion='Completar el respaldo.'), follow=True)
        self.assertContains(r, 'Documento rechazado.')
        self.assertContains(r, 'data-estado-aprobacion="rechazado"')
        c.refresh_from_db()
        self.assertIsNotNone(c.observado_en)

    def test_carga_qr_en_lote_y_lectura_sin_consultas_ni_aprobaciones_de_otra_version(self):
        c = self.enviar()
        self.aprobar(c)
        documentos = list(type(self.documento_qr).objects.filter(pk=self.documento_qr.pk)
            .select_related('recurso', 'unidad', 'exigido'))
        with self.assertNumQueries(1):
            completar_constancias(documentos)
        with self.assertNumQueries(0):
            self.assertTrue(lectura_aprobacion_qr(documentos[0])['aprobado'])
            completar_constancias(documentos)
            documentos[0].version += 1
            self.assertFalse(lectura_aprobacion_qr(documentos[0])['aprobado'])

    def test_cache_del_mismo_objeto_refleja_envio_y_decision(self):
        self.enviar()
        self.assertEqual(lectura_aprobacion_qr(self.documento_qr)['estado'], 'pendiente')
        c = comprobar_emision(self.documento_qr)
        self.aprobar(c)
        self.assertEqual(lectura_aprobacion_qr(self.documento_qr)['estado'], 'aprobado')

    def test_editor_genera_y_envia_en_una_operacion_y_rechaza_doble_envio_atrasado(self):
        self.client.force_login(self.coordinador)
        pagina = self.client.get(self.ruta_editor(self.documento_qr))
        datos = dict(accion='generar_enviar_guardado', version_base=pagina.context['redaccion'].version)
        r = self.client.post(self.ruta_editor(self.documento_qr), datos,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()['enviado'])
        self.documento_qr.refresh_from_db()
        identidad = (self.documento_qr.recurso_id, self.documento_qr.version)
        r = self.client.post(self.ruta_editor(self.documento_qr), datos,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 409)
        self.documento_qr.refresh_from_db()
        self.assertEqual((self.documento_qr.recurso_id, self.documento_qr.version), identidad)

    def test_fallo_de_envio_revierte_emision_recurso_y_constancia(self):
        from apps.documentos.presentation.aprobacion_en_linea import generar_y_enviar_qr
        from apps.recursos.models import Recurso
        recursos = Recurso.objects.count()
        with patch('apps.documentos.presentation.aprobacion_en_linea.enviar_documento_qr',
                   side_effect=ValidationError('Entrega no disponible')):
            with self.assertRaises(ValidationError):
                generar_y_enviar_qr(self.documento_qr, self.coordinador)
        self.documento_qr.refresh_from_db()
        self.assertIsNone(self.documento_qr.recurso_id)
        self.assertIsNone(self.documento_qr.verificacion_qr)
        self.assertEqual(Recurso.objects.count(), recursos)
        self.assertFalse(ConstanciaDocumento.objects.filter(documento=self.documento_qr).exists())

    def test_director_revocado_no_aprueba_con_privilegio_cacheado(self):
        c = self.enviar()
        from apps.core.models.gobernanza import AsignacionGobernanza
        AsignacionGobernanza.objects.filter(usuario=self.director).update(activa=False)
        with self.assertRaisesMessage(ValidationError, 'No tienes permiso'):
            self.aprobar(c)
        c.refresh_from_db()
        self.assertIsNone(c.aprobado_en)

    def test_carga_anterior_conserva_su_ruta_de_firma(self):
        self.documento_qr.estado = 'cargado'
        self.documento_qr.save(update_fields=['estado'])
        self.assertFalse(self.documento_qr.aprobacion_en_linea_disponible)

    def test_cierre_con_qr_confirma_el_calculo_conservado_sin_otorgar_cien_por_aprobar(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO
        from apps.documentos.presentation.aprobacion_en_linea import generar_y_enviar_qr
        plan = abrir_entrega(self.documento('PLANIFICACION'))
        contenido_plan = deepcopy(PLAN_COMPLETO)
        contenido_plan.update(recursos_periodo_version=1, revision_recursos='revisado',
            cobertura_recursos='<p>Los recursos disponibles cubren las actividades del semestre.</p>')
        from apps.documentos.presentation.expediente_redaccion import FUENTES_FINANCIAMIENTO
        contenido_plan['inversion'][0]['fuente'] = FUENTES_FINANCIAMIENTO[0][0]
        contenido_plan['presupuesto_uso'] = dict(horas_por_mes={str(m): '4' for m in range(1, 7)},
            horas_comprometidas='24', justificacion='Jornadas de prácticas y actividades del semestre.')
        DocumentoElaborado.objects.create(documento=plan, contenido=contenido_plan)
        generar_y_enviar_qr(plan, self.coordinador)
        decidir_documento_qr(plan, self.director, token=plan.verificacion_qr, version=plan.version, decision='aprobar')
        self.documento_qr = abrir_entrega(self.documento('INFORME-SEMESTRAL'))
        contenido = {c.clave: '<p>Resultados y evidencias del semestre para revisión.</p>'
            for s in secciones_de('informe', self.unidad) for c in s.campos if c.requerido}
        DocumentoElaborado.objects.create(documento=self.documento_qr, contenido=contenido)
        c = self.enviar()
        from apps.documentos.presentation.evaluacion_cierre import cierre_archivado
        calculado = cierre_archivado(self.documento_qr)
        self.assertTrue(calculado['plan_aprobado'])
        self.assertEqual(calculado['nota'], 0)
        self.aprobar(c)
        self.documento_qr.refresh_from_db()
        self.assertEqual(self.documento_qr.evaluacion, 0)
        self.assertEqual(self.documento_qr.evaluado_por_id, self.director.pk)
        self.assertEqual(estado_constancia(c), 'VIGENTE')

    def test_cierre_sin_planificacion_conforme_no_se_envia(self):
        self.documento_qr = abrir_entrega(self.documento('INFORME-SEMESTRAL'))
        contenido = {c.clave: '<p>Resultados del semestre pendientes de contrastar con el plan.</p>'
            for s in secciones_de('informe', self.unidad) for c in s.campos if c.requerido}
        DocumentoElaborado.objects.create(documento=self.documento_qr, contenido=contenido)
        c = self.emitir()
        with self.assertRaisesMessage(ValidationError, 'planificación del mismo semestre'):
            enviar_documento_qr(self.documento_qr, self.coordinador, token=c.token, version=c.version)
        c.refresh_from_db()
        self.assertIsNone(c.enviado_en)
        self.assertIsNone(c.aprobado_en)

    def test_no_se_emite_ni_envia_presupuesto_incompleto_aunque_haya_justificacion(self):
        redaccion = DocumentoElaborado.objects.get(documento=self.documento_qr)
        redaccion.contenido['compras'] = [dict(categoria='equipos', item='Equipo para las actividades')]
        redaccion.save()
        original = (self.documento_qr.estado, self.documento_qr.version, self.documento_qr.recurso_id)
        with self.assertRaisesMessage(ValidationError, 'Compras del año, ítem 1'):
            self.enviar()
        self.documento_qr.refresh_from_db()
        self.assertEqual((self.documento_qr.estado, self.documento_qr.version,
            self.documento_qr.recurso_id), original)
        self.assertFalse(ConstanciaDocumento.objects.filter(documento=self.documento_qr).exists())

    def test_presupuesto_incompleto_heredado_no_se_aprueba_ni_altera_su_archivo(self):
        redaccion = DocumentoElaborado.objects.get(documento=self.documento_qr)
        redaccion.contenido.update(compras=[dict(categoria='equipos')], sin_compras_justificacion='')
        redaccion.save()
        # Reproduce una emisión anterior que contaba cualquier fila como completa.
        with patch('apps.documentos.presentation.preparacion_documental.exigir_preparacion'):
            c = self.enviar()
        original = (c.sha256, c.version, c.recurso_id, c.enviado_en)
        with c.recurso.archivo.open('rb') as archivo:
            contenido_original = archivo.read()
        with self.assertRaisesMessage(ValidationError, 'justifica por qué la unidad no requiere compras'):
            self.aprobar(c)
        c.refresh_from_db()
        self.documento_qr.refresh_from_db()
        self.assertEqual((c.sha256, c.version, c.recurso_id, c.enviado_en), original)
        self.assertIsNone(c.aprobado_en)
        self.assertFalse(c.archivo_aprobado)
        self.assertEqual(self.documento_qr.estado, 'validado')
        with c.recurso.archivo.open('rb') as archivo:
            self.assertEqual(archivo.read(), contenido_original)

    def test_documento_preparado_antes_del_ajuste_no_envia_un_presupuesto_incompleto(self):
        redaccion = DocumentoElaborado.objects.get(documento=self.documento_qr)
        redaccion.contenido.update(compras=[dict(categoria='equipos')], sin_compras_justificacion='')
        redaccion.save()
        with patch('apps.documentos.presentation.preparacion_documental.exigir_preparacion'):
            c = self.emitir()
        with self.assertRaisesMessage(ValidationError, 'justifica por qué la unidad no requiere compras'):
            enviar_documento_qr(self.documento_qr, self.coordinador, token=c.token, version=c.version)
        c.refresh_from_db()
        self.documento_qr.refresh_from_db()
        self.assertIsNone(c.enviado_en)
        self.assertEqual(self.documento_qr.estado, 'generado')

    def test_campo_obligatorio_vacio_despues_de_preparar_impide_envio(self):
        c = self.emitir()
        redaccion = DocumentoElaborado.objects.get(documento=self.documento_qr)
        redaccion.contenido['firma_nombre'] = ''
        redaccion.save()
        with self.assertRaisesMessage(ValidationError, 'Elaborado por'):
            enviar_documento_qr(self.documento_qr, self.coordinador, token=c.token, version=c.version)
        c.refresh_from_db()
        self.assertIsNone(c.enviado_en)

    def test_direccion_no_recibe_un_qr_que_la_unidad_no_envio(self):
        from apps.documentos.presentation.expediente import recibir_documento
        c = self.emitir()
        with self.assertRaisesMessage(ValidationError, 'debe enviar esta versión'):
            recibir_documento(self.documento_qr, self.director)
        c.refresh_from_db()
        self.documento_qr.refresh_from_db()
        self.assertIsNone(c.enviado_en)
        self.assertIsNone(self.documento_qr.recibido_en)
        self.assertEqual(self.documento_qr.estado, 'generado')
