"""Editor, aplicabilidad y aprobación permanente del protocolo adaptable."""
from copy import deepcopy
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import QueryDict
from pypdf import PdfReader

from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.aprobacion_en_linea import (
    decidir_documento_qr, enviar_documento_qr, estado_constancia,
)
from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
from apps.documentos.presentation.expediente import construir_expediente, generar_documento
from apps.documentos.presentation.expediente_redaccion import (
    avance, componer, leer_formulario, obtener_redaccion, pdf_del_documento, secciones_de,
)
from apps.documentos.presentation.perfil_unidades import aplica_documento
from apps.documentos.presentation.protocolo_seguridad import NOMBRE, NOMBRE_ANTERIOR
from tests.integration.test_expediente_redaccion import BaseDeRedaccion


def protocolo_completo(documento):
    contenido = deepcopy(obtener_redaccion(documento).contenido)
    for seccion in secciones_de('protocolo'):
        for campo in seccion.campos:
            if campo.tipo == 'tabla':
                filas = contenido.get(campo.clave) or [{}]
                for fila in filas:
                    for clave, _etiqueta, tipo, opciones in campo.columnas:
                        if not fila.get(clave):
                            fila[clave] = opciones[0][0] if tipo == 'opcion' else 'Dato verificado de prueba'
                contenido[campo.clave] = filas
            elif campo.requerido and not contenido.get(campo.clave):
                contenido[campo.clave] = (campo.opciones[0][0] if campo.tipo == 'opcion' else
                    '<p>Dato verificado de prueba.</p>' if campo.tipo == 'rico' else 'Dato de prueba')
    return contenido


def formulario_protocolo(contenido, **otros):
    post = QueryDict(mutable=True)
    post['protocolo_fuentes'] = contenido.get('_protocolo_fuentes', '')
    for seccion in secciones_de('protocolo'):
        for campo in seccion.campos:
            valor = contenido.get(campo.clave, '')
            if campo.tipo == 'tabla':
                for clave, *_ in campo.columnas:
                    post.setlist(f'{campo.clave}__{clave}', [str(fila.get(clave, '')) for fila in valor or []])
            else:
                post[campo.clave] = valor
    post.update(otros)
    return post


class ProtocoloSeguridadTests(BaseDeRedaccion):
    def setUp(self):
        self.protocolo = self.documento('PROTOCOLO-BIOSEGURIDAD', corte='')
        self.director = get_user_model().objects.create_superuser('direccion-protocolo', password=None,
            first_name='Directora', last_name='de prueba')
        self.coordinador.profile.cedula = '0400000001'
        self.coordinador.profile.save(update_fields=['cedula'])
        self.director.profile.cedula = '0400000002'
        self.director.profile.save(update_fields=['cedula'])

    def emitir_y_enviar(self):
        DocumentoElaborado.objects.create(documento=self.protocolo, version=1,
            contenido=protocolo_completo(self.protocolo))
        generar_documento(self.protocolo, self.coordinador)
        enviar_documento_qr(self.protocolo, self.coordinador,
            token=self.protocolo.verificacion_qr, version=self.protocolo.version)
        return ConstanciaDocumento.objects.get(token=self.protocolo.verificacion_qr)

    def aprobar(self, constancia):
        decidir_documento_qr(self.protocolo, self.director, token=constancia.token,
            version=constancia.version, decision='aprobar')
        constancia.refresh_from_db()

    def test_catalogo_editor_y_aplicabilidad_por_tipo(self):
        e = self.protocolo.exigido
        self.assertEqual(e.nombre, NOMBRE)
        self.assertTrue(e.generable and e.redactable and e.cargable)
        self.assertEqual((e.periodicidad, e.anexo_de_id), ('unica', None))
        for base in ('laboratorios', 'plantas_piloto', 'centro_experimental'):
            self.assertTrue(aplica_documento(e, base, base=base))
        self.assertTrue(aplica_documento(e, 'observatorios', base='observatorios'))
        e.tipos_unidad = ['observatorios']
        self.assertTrue(aplica_documento(e, 'observatorios', base='observatorios'))

    def test_ficha_automatica_y_propuestas_sin_inventar_contactos_o_rutas(self):
        redaccion = obtener_redaccion(self.protocolo)
        self.assertEqual(redaccion.contenido['unidad_nombre'], self.unidad.nombre)
        self.assertTrue(redaccion.contenido['riesgos_protocolo'])
        self.assertNotIn('contactos_emergencia', redaccion.contenido)
        self.assertNotIn('evacuacion_protocolo', redaccion.contenido)
        self.assertTrue(all(fila['aplica'] in ('si', 'no') for fila in redaccion.contenido['medidas_protocolo']))
        self.assertLess(avance('protocolo', redaccion.contenido)['porcentaje'], 100)
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(self.ruta_editor(self.protocolo))
        self.assertContains(respuesta, NOMBRE)
        self.assertContains(respuesta, 'data-redaccion-tipo="protocolo"')
        self.assertContains(respuesta, 'name="medidas_protocolo__medidas"')
        self.assertContains(respuesta, 'textarea')
        self.assertTrue(respuesta.context['secciones'][0]['seccion'].automatico)
        self.assertNotContains(respuesta, 'name="unidad_nombre"')
        self.assertNotContains(respuesta, 'name="unidad_tipo"')
        self.assertNotContains(respuesta, 'name="responsables_protocolo__nombre"')
        self.assertContains(respuesta, 'name="riesgos_protocolo__responsable"')
        self.assertContains(respuesta, 'Cómo completarlo')
        self.assertNotContains(respuesta, 'fírmalo electrónicamente y cárgalo')

    def test_conserva_textos_editados_y_no_admite_suplantar_los_datos_automaticos(self):
        contenido = protocolo_completo(self.protocolo)
        contenido['alcance_protocolo'] = '<p>Alcance específico del documento.</p><script>alert(1)</script>'
        contenido['riesgos_protocolo'][0]['control'] = 'Control detallado\nSegunda indicación'
        post = formulario_protocolo(contenido, version_base='0', accion='guardar')
        post.update(unidad_nombre='Otra unidad', unidad_tipo='Otro tipo', ubicacion_protocolo='Ubicación inventada')
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(self.ruta_editor(self.protocolo), post.urlencode(),
            content_type='application/x-www-form-urlencoded', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200)
        guardado = DocumentoElaborado.objects.get(documento=self.protocolo)
        self.assertNotIn('<script', guardado.contenido['alcance_protocolo'])
        self.assertEqual([f['control'] for f in guardado.contenido['riesgos_protocolo']],
                         [f['control'] for f in contenido['riesgos_protocolo']])
        self.assertEqual(guardado.contenido['unidad_nombre'], self.unidad.nombre)
        self.assertNotEqual(guardado.contenido['ubicacion_protocolo'], 'Ubicación inventada')
        self.unidad.ubicacion = 'Una ubicación nueva de la ficha'
        self.unidad.save(update_fields=['ubicacion'])
        actual = DocumentoExpediente.objects.select_related('unidad', 'exigido').get(pk=self.protocolo.pk)
        self.assertEqual(obtener_redaccion(actual).contenido['ubicacion_protocolo'], self.unidad.ubicacion)
        self.assertIn('Alcance específico', obtener_redaccion(actual).contenido['alcance_protocolo'])
        post['protocolo_fuentes'] = obtener_redaccion(actual).contenido['_protocolo_fuentes']
        obsoleta = self.client.post(self.ruta_editor(self.protocolo), post.urlencode(),
            content_type='application/x-www-form-urlencoded', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(obsoleta.status_code, 409)

    def test_las_propuestas_usan_recursos_activos_de_su_unidad_y_piden_revision(self):
        from apps.recursos.models.consumibles import Consumible
        from apps.gestion_unidades.models.espacios import EspacioReservable
        Consumible.objects.create(unidad=self.unidad, codigo='RESINA-PROTOCOLO', nombre='Resina de ensayo', clasificacion='insumo')
        EspacioReservable.objects.create(unidad=self.unidad, codigo='CNC-PROTOCOLO', nombre='Área de fresado CNC', tipo='area')
        otra = self.unidad.__class__.objects.create(nombre='Unidad ajena', slug='unidad-ajena-protocolo',
            dependencia='laboratorios', fecha_inicio=self.unidad.fecha_inicio)
        Consumible.objects.create(unidad=otra, codigo='BIO-AJENO-PROTOCOLO', nombre='Cultivo biológico ajeno', clasificacion='reactivo')
        Consumible.objects.create(unidad=self.unidad, codigo='BIO-INACTIVO-PROTOCOLO', nombre='Cultivo biológico inactivo',
            clasificacion='reactivo', activo=False)
        contenido = obtener_redaccion(self.protocolo).contenido
        medidas = {f['ambito']: f for f in contenido['medidas_protocolo']}
        self.assertEqual(medidas['Sustancias químicas']['aplica'], 'si')
        self.assertEqual(medidas['Agentes biológicos']['aplica'], 'no')
        self.assertIn('Resina de ensayo', medidas['Sustancias químicas']['origen'])
        self.assertNotIn('ajeno', str(contenido))
        self.assertNotIn('inactivo', str(contenido))
        self.assertEqual(contenido['revision_propuestas'], '')
        self.assertIn('revision_propuestas', [c.clave for s,c in avance('protocolo', contenido)['faltantes']])

    def test_no_permite_asignar_responsables_ajenos_ni_confirmar_fuentes_que_cambiaron(self):
        contenido = protocolo_completo(self.protocolo)
        post = formulario_protocolo(contenido)
        post.setlist('riesgos_protocolo__responsable', ['Persona ajena'] * len(contenido['riesgos_protocolo']))
        with self.assertRaisesMessage(ValidationError, 'personal registrado'):
            leer_formulario('protocolo', post, self.unidad, documento=self.protocolo)
        post = formulario_protocolo(contenido)
        post['protocolo_fuentes'] = 'huella-obsoleta'
        with self.assertRaisesMessage(ValidationError, 'Cambiaron los datos'):
            leer_formulario('protocolo', post, self.unidad, documento=self.protocolo)

    def test_actualizar_borrador_anterior_no_borra_lo_redactado(self):
        contenido = {'alcance_protocolo': '<p>Alcance redactado previamente.</p>',
                     'medidas_protocolo': [dict(ambito='Actividad propia', aplica='no', medidas='No corresponde al alcance.')],
                     'responsables_protocolo': [dict(rol='Coordinación', nombre='Ana Coordinadora', funcion='Función propia previamente redactada.')],
                     'evacuacion_protocolo': '<p>Ruta comprobada por la unidad.</p>'}
        DocumentoElaborado.objects.create(documento=self.protocolo, version=3, contenido=contenido)
        actual = obtener_redaccion(self.protocolo)
        self.assertEqual(actual.contenido['medidas_protocolo'], contenido['medidas_protocolo'])
        self.assertEqual(actual.contenido['evacuacion_protocolo'], contenido['evacuacion_protocolo'])
        self.assertTrue(actual.contenido['riesgos_protocolo'])
        self.assertIn('Función propia previamente redactada', actual.contenido['responsabilidades_adicionales'])
        self.assertEqual(DocumentoElaborado.objects.get(documento=self.protocolo).contenido, contenido)

    def test_toma_horarios_y_personal_de_sus_registros_y_no_confirma_si_cambian(self):
        from datetime import time
        from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
        HorarioOperacionUnidad.objects.create(unidad=self.unidad, dia_semana=0,
            hora_inicio=time(8), hora_fin=time(12), activo=True)
        contenido = protocolo_completo(self.protocolo)
        self.assertIn('Lunes 08:00-12:00', contenido['horario_protocolo'])
        self.assertTrue(any(p['nombre'] == 'Luis Técnico' for p in contenido['responsables_protocolo']))
        DocumentoElaborado.objects.create(documento=self.protocolo, version=1, contenido=contenido)
        self.unidad.__class__.objects.filter(pk=self.unidad.pk).update(nombre='Nombre institucional actualizado')
        actual = DocumentoExpediente.objects.select_related('unidad', 'exigido').get(pk=self.protocolo.pk)
        actualizado = obtener_redaccion(actual).contenido
        self.assertEqual(actualizado['unidad_nombre'], 'Nombre institucional actualizado')
        self.assertEqual(actualizado['revision_propuestas'], '')
        with self.assertRaisesMessage(ValidationError, 'Revisión del contenido propuesto'):
            pdf_del_documento(actual, DocumentoElaborado(documento=actual, contenido=contenido), *self.tramo())

    def test_propuestas_de_planta_campo_y_observatorio_se_adaptan_al_perfil(self):
        for base, texto in (('plantas_piloto', 'procesos de la planta piloto'),
                            ('centro_experimental', 'Actividades de campo'),
                            ('observatorios', 'información y equipos informáticos')):
            unidad = self.unidad.__class__(nombre='Unidad de prueba', dependencia=base, administrador=self.coordinador)
            documento = DocumentoExpediente(unidad=unidad, exigido=self.protocolo.exigido, anio=2026)
            with self.subTest(base=base):
                contenido = obtener_redaccion(documento).contenido
                self.assertTrue(any(texto in f['actividad'] for f in contenido['riesgos_protocolo']))
                self.assertEqual(contenido['revision_propuestas'], '')

    def test_no_se_emite_una_tabla_incompleta_o_no_aplicacion_sin_justificar(self):
        contenido = protocolo_completo(self.protocolo)
        self.assertEqual(avance('protocolo', contenido)['porcentaje'], 100)
        for tabla, celda, valor in (('riesgos_protocolo', 'control', ''),
                                    ('medidas_protocolo', 'aplica', 'invalido'),
                                    ('medidas_protocolo', 'medidas', '')):
            copia = deepcopy(contenido)
            copia[tabla][0][celda] = valor
            redaccion = DocumentoElaborado(documento=self.protocolo, contenido=copia)
            with self.subTest(tabla=tabla, celda=celda), self.assertRaises(ValidationError):
                pdf_del_documento(self.protocolo, redaccion, *self.tramo())

    def tramo(self):
        from apps.documentos.presentation.expediente import tramo_del_documento
        return tramo_del_documento(self.protocolo)

    def test_pdf_tiene_estructura_institucional_y_cobertura_permanente(self):
        contenido = protocolo_completo(self.protocolo)
        compuesto = componer(self.protocolo, contenido, *self.tramo())
        self.assertEqual(compuesto['periodo'], 'Documento permanente')
        self.assertEqual(len(compuesto['secciones']), 9)
        pdf = PdfReader(BytesIO(pdf_del_documento(self.protocolo,
            DocumentoElaborado(documento=self.protocolo, contenido=contenido), *self.tramo())))
        paginas = [p.extract_text() or '' for p in pdf.pages]
        texto = '\n'.join(paginas)
        self.assertTrue(pdf.outline)
        # Documento principal: portada, contenido con su índice y el encabezado del informe institucional, con el
        # código de referencia y la cobertura en una línea (sin revisión ni versión del formato de los anexos).
        self.assertIn('Código de referencia: SLCID-LAB-SEGURIDAD', paginas[0])
        self.assertIn('CONTENIDO', paginas[1])
        self.assertIn('Código de referencia: SLCID-LAB-SEGURIDAD · Cobertura: Documento permanente', texto)
        self.assertNotIn('Revisión: 01', texto)
        self.assertNotIn('Versión:', texto)
        self.assertTrue(any(a.get_object().get('/Dest') for pagina in pdf.pages
                            for a in pagina.get('/Annots', [])))
        self.assertIn('EMERGENCIAS Y COMUNICACIÓN', texto)

    def test_borrador_muestra_responsables_al_inicio_sin_firma_manual_ni_duplicados(self):
        from apps.documentos.presentation.aprobacion_en_linea import admite_aprobacion_en_linea
        from apps.documentos.presentation.validacion_pdf import _formulario
        self.assertTrue(admite_aprobacion_en_linea(self.protocolo))
        pdf = PdfReader(BytesIO(pdf_del_documento(self.protocolo,
            obtener_redaccion(self.protocolo), *self.tramo(), estricto=False)))
        # Tras la portada, los responsables abren la segunda página, antes del contenido.
        pagina_responsables = pdf.pages[1].extract_text()
        texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertLess(pagina_responsables.index('RESPONSABLES DEL DOCUMENTO'),
                        pagina_responsables.index('CONTENIDO'))
        self.assertIn('Pendiente de envío a Dirección', pagina_responsables)
        self.assertEqual(texto.count('RESPONSABLES DEL DOCUMENTO'), 1)
        self.assertNotIn('9. RESPONSABLES', texto)
        self.assertNotIn('versión firmada electrónicamente', texto)
        self.assertNotIn('__________________________________', texto)
        self.assertFalse(any(_formulario(p) for p in pdf.pages))
        self.assertFalse(ConstanciaDocumento.objects.filter(documento=self.protocolo).exists())

    def test_qr_aprueba_sin_firma_manual_y_se_conserva_el_mismo_archivo_al_heredar(self):
        c = self.emitir_y_enviar()
        ancla = (c.token, c.recurso_id, c.sha256, c.version)
        self.assertEqual(c.emitido_por_id, self.coordinador.pk)
        self.assertIsNotNone(c.enviado_en)
        with c.recurso.archivo.open('rb') as archivo:
            emitido = PdfReader(BytesIO(archivo.read()))
        # Tras la portada, el cuadro de aprobación abre la segunda página, antes del contenido.
        inicio = emitido.pages[1].extract_text()
        self.assertIn('RESPONSABILIDAD Y APROBACIÓN', inicio)
        self.assertLess(inicio.index('DOCUMENTO EMITIDO PARA REVISIÓN'), inicio.index('CONTENIDO'))
        self.assertIn('0400000001', inicio)
        self.assertIn('PENDIENTE DE APROBACIÓN', inicio)
        self.assertFalse(aprobacion_vigente(self.protocolo))
        self.aprobar(c)
        self.assertEqual(estado_constancia(c), 'VIGENTE')
        self.assertTrue(aprobacion_vigente(self.protocolo, inspeccionar=True))
        self.assertFalse(self.protocolo.firma_verificada)
        self.assertEqual((c.token, c.recurso_id, c.sha256, c.version), ancla)
        self.assertEqual((c.emisor_cedula, c.aprobador_cedula), ('0400000001', '0400000002'))
        from apps.documentos.presentation.validacion_pdf import copia_aprobada
        with c.recurso.archivo.open('rb') as archivo:
            copia = copia_aprobada(archivo.read(), c)
        aprobado = PdfReader(BytesIO(copia))
        texto = '\n'.join(p.extract_text() or '' for p in aprobado.pages)
        inicio_aprobado = aprobado.pages[1].extract_text()
        self.assertLess(inicio_aprobado.index('DOCUMENTO APROBADO POR DIRECCIÓN'), inicio_aprobado.index('CONTENIDO'))
        self.assertIn('RESPONSABILIDAD Y APROBACIÓN', inicio_aprobado)
        self.assertNotIn('9. RESPONSABLES', texto)
        self.assertNotIn('versión firmada electrónicamente', texto)
        self.assertIn('0400000001', texto)
        self.assertIn('0400000002', texto)
        heredado = next(d for d in construir_expediente(self.unidad, 2027)
            if d.exigido.codigo == 'PROTOCOLO-BIOSEGURIDAD')
        self.assertEqual(heredado.recurso_id, c.recurso_id)
        self.assertTrue(aprobacion_vigente(heredado))
        self.assertEqual(ConstanciaDocumento.objects.filter(recurso_id=c.recurso_id).count(), 1)

    def test_devolucion_revoca_vigencia_y_permite_corregir_con_nuevo_qr(self):
        c = self.emitir_y_enviar()
        self.aprobar(c)
        decidir_documento_qr(self.protocolo, self.director, token=c.token, version=c.version,
            decision='observar', observacion='Precisar las rutas de evacuación.')
        self.assertFalse(aprobacion_vigente(self.protocolo))
        self.protocolo.refresh_from_db()
        self.assertEqual(self.protocolo.estado, 'observado')
        generar_documento(self.protocolo, self.coordinador)
        self.assertNotEqual(self.protocolo.verificacion_qr, c.token)
        c.refresh_from_db()
        c.documento.refresh_from_db()
        self.assertEqual(estado_constancia(c), 'SUSTITUIDO')

    def test_aprobaciones_qr_se_consultan_por_lote_sin_abrir_archivos(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
        c = self.emitir_y_enviar()
        self.aprobar(c)
        copias = [DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.protocolo.exigido,
            anio=anio, recurso=c.recurso, version=c.version, estado='validado') for anio in (2027, 2028)]
        documentos = list(DocumentoExpediente.objects.filter(pk__in=[d.pk for d in copias]).select_related(
            'unidad', 'exigido', 'recurso'))
        with CaptureQueriesContext(connection) as consultas:
            completar_aprobaciones(documentos)
            self.assertTrue(all(aprobacion_vigente(d) for d in documentos))
        tabla = ConstanciaDocumento._meta.db_table
        self.assertEqual(sum(tabla in q['sql'] for q in consultas), 1)

    def test_solo_responsables_editan_y_la_unidad_no_aprueba(self):
        ajeno = get_user_model().objects.create_user('ajeno-protocolo')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(self.ruta_editor(self.protocolo)).status_code, 403)
        c = self.emitir_y_enviar()
        with self.assertRaises(ValidationError):
            decidir_documento_qr(self.protocolo, self.coordinador, token=c.token,
                version=c.version, decision='aprobar')
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(self.ruta_editor(self.protocolo),
            formulario_protocolo(protocolo_completo(self.protocolo), version_base='1'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 409)

    def test_migracion_conserva_registros_archivos_y_catalogo_personalizado(self):
        from django.db import connection
        migracion = import_module('apps.documentos.migrations.0019_editor_protocolo_seguridad')
        e = self.protocolo.exigido
        DocumentoExigido.objects.filter(pk=e.pk).update(nombre=NOMBRE_ANTERIOR, origen='unidad', fuente_reporte='')
        identidad = (self.protocolo.pk, self.protocolo.estado, self.protocolo.recurso_id, self.protocolo.version)
        migracion.habilitar(apps, SimpleNamespace(connection=connection))
        e.refresh_from_db()
        self.protocolo.refresh_from_db()
        self.assertEqual((e.nombre, e.origen, e.fuente_reporte), (NOMBRE, 'ambos', 'protocolo'))
        self.assertEqual((self.protocolo.pk, self.protocolo.estado, self.protocolo.recurso_id, self.protocolo.version), identidad)
        DocumentoExigido.objects.filter(pk=e.pk).update(nombre='Protocolo institucional particular', fuente_reporte='')
        migracion.habilitar(apps, SimpleNamespace(connection=connection))
        e.refresh_from_db()
        self.assertEqual(e.nombre, 'Protocolo institucional particular')
        self.assertEqual(e.fuente_reporte, '')
