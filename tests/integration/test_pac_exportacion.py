"""Descarga por unidad y conservación de los requerimientos ya enviados."""
from copy import deepcopy
from io import BytesIO

from django.contrib.auth import get_user_model
from django.urls import reverse
from openpyxl import load_workbook

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.aprobacion_en_linea import generar_y_enviar_qr
from apps.documentos.presentation.expediente import generar_documento
from apps.documentos.presentation.pac_universitario import preparar_pac
from apps.recursos.models.recursos import Recurso
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.utiles import abrir_entrega


class DescargaPacPorUnidadTests(BaseDeRedaccion):
    def preparar(self):
        documento = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        contenido = preparar_pac(dict(centro_costo='Centro agrupador confirmado', compras=[dict(
            item='Necesidad congelada de prueba', cantidad='3', costo_unitario='4.50',
            justificacion='Sostener las actividades registradas con una necesidad documentada.',
            area_id='unidad', area_nombre='Toda la unidad', tipo_necesidad='dotacion', clase_bien='equipos', mes_compra='1', equipos_referencia=[],
            cpc='011200011', partida='00530404', clasificacion_pac='pac', fuente_pac='001')],
            capacidad='<p>Los espacios y el personal registrados permiten operar el bien solicitado.</p>',
            justificacion_uso_existente='El inventario operativo y la necesidad se incluirán en la programación verificable del área.',
            acciones_cumplimiento=[dict(accion='Publicar el plan de actividades y ejecutar las prácticas del área',
                responsable='Coordinación de la unidad', plazo='2027-03-31',
                resultado='Identificar metas y responsables; registrar horario real y asistentes de las prácticas.')],
            firma_nombre=self.coordinador.get_full_name(), firma_cargo='Responsable de la unidad'))
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido=contenido)
        return documento, redaccion

    def ruta(self, documento, unidad=None):
        return reverse('exportar_pac_unidad', args=[(unidad or self.unidad).slug, documento.pk])

    def libro(self, respuesta):
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        libro = load_workbook(BytesIO(respuesta.content), data_only=False)
        self.addCleanup(libro.close)
        return libro

    def test_borrador_exporta_datos_actuales_para_anio_siguiente_sin_cerrar_documento(self):
        documento, redaccion = self.preparar()
        self.client.force_login(self.coordinador)
        antes = (documento.estado, documento.version, documento.recurso_id, Recurso.objects.count())
        libro = self.libro(self.client.get(self.ruta(documento)))
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        self.assertIn('2027', libro['Resumen']['A2'].value)
        self.assertIn('BORRADOR', libro['Resumen']['A3'].value)
        self.assertEqual(libro['Equipos']['B6'].value, redaccion.contenido['compras'][0]['item'])
        self.assertEqual(libro['Equipos']['H6'].value, 13.5)
        self.assertEqual(libro['Equipos']['H6'].data_type, 'n')
        self.assertEqual(libro['Resumen']['F9'].value, 13.5)
        documento.refresh_from_db()
        self.assertEqual((documento.estado, documento.version, documento.recurso_id, Recurso.objects.count()), antes)

    def test_emision_preparada_no_tapa_ediciones_mas_recientes_del_borrador(self):
        documento, redaccion = self.preparar()
        generar_documento(documento, self.coordinador)
        contenido = deepcopy(redaccion.contenido)
        contenido['compras'][0]['item'] = 'Borrador actualizado después de preparar'
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(contenido=contenido)
        self.client.force_login(self.coordinador)
        libro = self.libro(self.client.get(self.ruta(documento)))
        self.assertEqual(libro['Equipos']['B6'].value, contenido['compras'][0]['item'])
        self.assertIn('BORRADOR', libro['Resumen']['A3'].value)

    def test_borrador_legacy_descarga_misma_proyeccion_del_editor_sin_guardar_ni_emitir(self):
        documento, redaccion = self.preparar()
        legado = deepcopy(redaccion.contenido)
        legado.pop('compras_resumen_version')
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(contenido=legado)
        redaccion.refresh_from_db()
        antes = (deepcopy(redaccion.contenido), redaccion.version, redaccion.generado_version,
                 documento.estado, documento.version, documento.recurso_id,
                 Recurso.objects.count(), ConstanciaDocumento.objects.count())
        self.client.force_login(self.coordinador)
        libro = self.libro(self.client.get(self.ruta(documento)))
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        self.assertEqual(libro['Equipos']['B6'].value, legado['compras'][0]['item'])
        self.assertEqual(libro['Resumen']['F9'].value, 13.5)
        redaccion.refresh_from_db()
        documento.refresh_from_db()
        self.assertEqual((redaccion.contenido, redaccion.version, redaccion.generado_version,
            documento.estado, documento.version, documento.recurso_id,
            Recurso.objects.count(), ConstanciaDocumento.objects.count()), antes)

    def test_entrega_cargada_o_validada_sin_captura_exportable_no_se_proyecta_como_borrador_vivo(self):
        documento, redaccion = self.preparar()
        legado = deepcopy(redaccion.contenido)
        legado.pop('compras_resumen_version')
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(contenido=legado)
        self.client.force_login(self.coordinador)
        for estado in ('cargado', 'validado'):
            with self.subTest(estado=estado):
                documento.estado = estado
                documento.save(update_fields=['estado'])
                libro = self.libro(self.client.get(self.ruta(documento)))
                self.assertIn('CONSOLIDADO', libro.sheetnames)
                self.assertNotIn('Resumen', libro.sheetnames)
                self.assertIn('BORRADOR', libro['CONSOLIDADO']['A3'].value)
                redaccion.refresh_from_db()
                self.assertEqual(redaccion.contenido, legado)

    def test_envio_usa_snapshot_aunque_cambien_redaccion_y_nombre_actual(self):
        documento, redaccion = self.preparar()
        nombre_emitido = self.unidad.nombre
        generar_y_enviar_qr(documento, self.coordinador)
        self.assertEqual(documento.estado, 'validado')
        constancia = ConstanciaDocumento.objects.get(token=documento.verificacion_qr)
        self.assertIn('pac_datos', constancia.contenido_emitido)
        alterado = deepcopy(redaccion.contenido)
        alterado['centro_costo'] = 'Agrupador alterado'
        alterado['compras'][0].update(item='NO DEBE EXPORTARSE', cpc='99999', cantidad='99')
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(contenido=alterado)
        Unidad.objects.filter(pk=self.unidad.pk).update(nombre='Nombre actual diferente')
        self.client.force_login(self.coordinador)
        libro = self.libro(self.client.get(self.ruta(documento)))
        hoja = libro['Equipos']
        self.assertIn(nombre_emitido, hoja['A3'].value)
        self.assertNotIn('Nombre actual diferente', hoja['A3'].value)
        self.assertEqual(hoja['B6'].value, 'Necesidad congelada de prueba')
        self.assertEqual((hoja['F6'].value, hoja['I6'].value), (3, '011200011'))
        self.assertEqual(hoja['I6'].data_type, 's')
        self.assertIn('REQUERIMIENTOS REGISTRADOS', hoja['A3'].value)
        self.assertIn('no autoriza gasto', libro['Resumen']['A3'].comment.text)

    def test_captura_emitida_sin_nuevo_formato_conserva_matriz_anterior(self):
        documento, _redaccion = self.preparar()
        generar_y_enviar_qr(documento, self.coordinador)
        constancia = ConstanciaDocumento.objects.get(token=documento.verificacion_qr)
        captura = deepcopy(constancia.contenido_emitido)
        captura['pac_datos'].pop('compras_resumen_version')
        ConstanciaDocumento.objects.filter(pk=constancia.pk).update(contenido_emitido=captura)
        self.client.force_login(self.coordinador)
        libro = self.libro(self.client.get(self.ruta(documento)))
        self.assertIn('CONSOLIDADO', libro.sheetnames)
        self.assertIn('PAC', libro.sheetnames)
        self.assertNotIn('Resumen', libro.sheetnames)
        self.assertEqual(libro['CONSOLIDADO']['D5'].value, 'Necesidad congelada de prueba')
        self.assertEqual(libro['CONSOLIDADO']['H5'].value, '011200011')

    def test_permiso_no_se_reutiliza_para_descargar_otra_unidad(self):
        documento, _redaccion = self.preparar()
        otra = Unidad.objects.create(nombre='Unidad sin permiso PAC', slug='unidad-sin-permiso-pac',
            dependencia='observatorios', fecha_inicio=self.unidad.fecha_inicio)
        ajeno = documento.__class__.objects.create(unidad=otra, exigido=documento.exigido, anio=2026)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.client.get(self.ruta(ajeno, otra)).status_code, 403)
        self.assertEqual(self.client.get(self.ruta(ajeno)).status_code, 404)
        sin_unidades = get_user_model().objects.create_user(username='lector-sin-unidades-pac')
        self.client.force_login(sin_unidades)
        self.assertEqual(self.client.get(self.ruta(documento)).status_code, 403)

    def test_descarga_requiere_autenticacion_get_y_documento_anual(self):
        documento, _redaccion = self.preparar()
        self.assertEqual(self.client.get(self.ruta(documento)).status_code, 302)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.client.post(self.ruta(documento), {}).status_code, 405)
        plan = self.documento('PLANIFICACION')
        self.assertEqual(self.client.get(self.ruta(plan)).status_code, 404)

    def test_busqueda_cpc_reutiliza_alcance_real_de_unidad_y_documento(self):
        documento, _redaccion = self.preparar()
        ruta = reverse('buscar_cpc_necesidad', args=[self.unidad.slug, documento.pk])
        self.assertEqual(self.client.get(ruta, {'q': 'computador'}).status_code, 302)
        self.client.force_login(self.coordinador)
        recursos_antes = Recurso.objects.count()
        respuesta = self.client.get(ruta, {'q': '4522000111'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['resultados'][0]['codigo'], '4522000111')
        self.assertEqual(respuesta.json()['resultados'][0]['estado'], 'por_validar')
        self.assertEqual(Recurso.objects.count(), recursos_antes)
        self.assertEqual(self.client.post(ruta, {'q': 'computador'}).status_code, 405)
        otra = Unidad.objects.create(nombre='Unidad CPC ajena', slug='unidad-cpc-ajena',
            dependencia='observatorios', fecha_inicio=self.unidad.fecha_inicio)
        ajeno = documento.__class__.objects.create(unidad=otra, exigido=documento.exigido, anio=2026)
        self.assertEqual(self.client.get(reverse('buscar_cpc_necesidad', args=[otra.slug, ajeno.pk]),
            {'q': 'computador'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('buscar_cpc_necesidad', args=[self.unidad.slug, ajeno.pk]),
            {'q': 'computador'}).status_code, 404)
        plan = self.documento('PLANIFICACION')
        self.assertEqual(self.client.get(reverse('buscar_cpc_necesidad', args=[self.unidad.slug, plan.pk]),
            {'q': 'computador'}).status_code, 404)
