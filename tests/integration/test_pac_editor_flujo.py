"""GET, autoguardado y emisión estricta del plan anual con necesidades PAC."""
from copy import deepcopy
from io import BytesIO
import json
from uuid import UUID

from django.http import QueryDict
from pypdf import PdfReader

from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.expediente import tramo_del_documento
from apps.documentos.presentation.expediente_redaccion import pdf_del_documento
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.utiles import abrir_entrega


class AutoguardadoPacIntegradoTests(BaseDeRedaccion):
    def guardar(self, documento, contenido, version):
        post = QueryDict(mutable=True)
        post.update(accion='guardar', version_base=str(version), centro_costo=contenido['centro_costo'],
            capacidad=contenido.get('capacidad', ''), firma_nombre=contenido['firma_nombre'],
            firma_cargo=contenido['firma_cargo'],
            justificacion_uso_existente=contenido.get('justificacion_uso_existente', ''))
        for clave in ('accion', 'responsable', 'plazo', 'resultado'):
            post.setlist('acciones_cumplimiento__' + clave,
                [str(f.get(clave, '')) for f in contenido.get('acciones_cumplimiento', [])])
        # Una fila vacía al final representa la plantilla del editor. No se
        # mandan las clasificaciones internas antiguas: el motor las conserva
        # sólo en las filas que ya las tenían, identificadas por su UUID.
        for clave in ('id_necesidad', 'item', 'cantidad', 'costo_unitario', 'justificacion',
                      'area_id', 'tipo_necesidad', 'mes_compra', 'clase_bien',
                      'cpc', 'partida', 'clasificacion_pac', 'fuente_pac', 'observaciones'):
            post.setlist('compras__' + clave, [str(f.get(clave, '')) for f in contenido['compras']] + [''])
        post.setlist('compras__equipos_referencia', [json.dumps(f.get('equipos_referencia', [])) for f in contenido['compras']] + ['[]'])
        respuesta = self.client.post(self.ruta_editor(documento), post.urlencode(),
            content_type='application/x-www-form-urlencoded', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        resultado = respuesta.json()
        self.assertTrue(resultado['success'])
        self.assertEqual(resultado['pac_identidades'][-1], '')
        return resultado

    def test_legacy_get_y_tres_autoguardados_conservan_identidad_y_emiten_pac_completo(self):
        documento = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        legado = dict(centro_costo='Centro agrupador confirmado',
            capacidad='<p>Los espacios, el personal y los servicios registrados sostienen estas necesidades.</p>',
            justificacion_uso_existente='<p>La unidad publicará el plan de utilización de los recursos existentes y el material solicitado.</p>',
            acciones_cumplimiento=[dict(accion='Programar las actividades del área y ejecutar sus prácticas',
                responsable='Coordinación de la unidad', plazo='2027-03-31',
                resultado='Publicar metas, responsables y meses; registrar las prácticas realizadas y sus asistentes.')],
            firma_nombre=self.coordinador.get_full_name(), firma_cargo='Responsable de la unidad',
            compras=[dict(item='Material heredado del plan anual', cantidad='2', costo_unitario='12.50',
                justificacion='Atender las actividades previstas de la unidad.', categoria='insumos',
                prioridad='alta', fuente='proyecto', trimestre='2', cpc='00012345', partida='00530404',
                clasificacion_pac='pac', fuente_pac='001')])
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido=deepcopy(legado))
        self.client.force_login(self.coordinador)

        pagina = self.client.get(self.ruta_editor(documento))
        self.assertEqual(pagina.status_code, 200)
        visto = deepcopy(pagina.context['redaccion'].contenido)
        identificador_legacy = visto['compras'][0]['id_necesidad']
        self.assertEqual(str(UUID(identificador_legacy)), identificador_legacy)
        self.assertContains(pagina, f'name="compras__id_necesidad" value="{identificador_legacy}"')
        self.assertContains(pagina, 'name="centro_costo" value="Centro agrupador confirmado"')
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido, legado)  # El GET no persiste una migración.
        # El archivo histórico conserva su CPC original hasta editarlo. Al
        # guardar un borrador en el formato nuevo, la unidad corrige el código
        # de ocho dígitos usando una referencia completa del catálogo.
        visto['compras'][0].update(area_id='unidad', tipo_necesidad='insumos', mes_compra='2',
                                   clase_bien='insumos', cpc='369400115')

        primero = self.guardar(documento, visto, redaccion.version)
        self.assertEqual(primero['pac_identidades'], [identificador_legacy, ''])
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido['pac_version'], 2)
        self.assertEqual(redaccion.contenido['compras'][0]['id_necesidad'], identificador_legacy)

        con_nueva = deepcopy(redaccion.contenido)
        con_nueva['compras'].append(dict(id_necesidad='', item='Servicio nuevo sin clasificaciones internas',
            cantidad='5', costo_unitario='2.00', justificacion='Servicio necesario para ejecutar las actividades.',
            area_id='unidad', tipo_necesidad='mantenimiento', mes_compra='7', clase_bien='servicios', equipos_referencia=[],
            cpc='841600111', partida='00530405', clasificacion_pac='no_pac', fuente_pac='Fuente 1'))
        segundo = self.guardar(documento, con_nueva, primero['version'])
        identificador_nuevo = segundo['pac_identidades'][1]
        self.assertEqual(str(UUID(identificador_nuevo)), identificador_nuevo)
        self.assertNotEqual(identificador_nuevo, identificador_legacy)
        self.assertEqual(segundo['pac_identidades'], [identificador_legacy, identificador_nuevo, ''])
        redaccion.refresh_from_db()
        self.assertTrue(all(not redaccion.contenido['compras'][1].get(clave)
            for clave in ('categoria', 'prioridad', 'fuente', 'trimestre')))

        final = deepcopy(redaccion.contenido)
        final['compras'].reverse()
        final['compras'][0]['item'] = 'Servicio nuevo renombrado sin duplicación'
        tercero = self.guardar(documento, final, segundo['version'])
        self.assertEqual(tercero['pac_identidades'], [identificador_nuevo, identificador_legacy, ''])
        self.assertEqual(tercero['porcentaje'], 100)
        self.assertEqual(tercero['faltantes'], [])
        redaccion.refresh_from_db()
        self.assertEqual(len(redaccion.contenido['compras']), 2)
        self.assertEqual([f['id_necesidad'] for f in redaccion.contenido['compras']],
                         [identificador_nuevo, identificador_legacy])
        self.assertEqual(redaccion.contenido['compras'][1]['fuente'], 'proyecto')
        self.assertEqual(redaccion.contenido['compras'][1]['partida'], '00530404')

        contenido_pdf = pdf_del_documento(documento, redaccion, *tramo_del_documento(documento), estricto=True)
        pdf = PdfReader(BytesIO(contenido_pdf))
        texto = '\n'.join(pagina.extract_text() or '' for pagina in pdf.pages)
        self.assertIn('Servicio nuevo renombrado sin duplicación', texto)
        self.assertIn('369400115', texto)
        self.assertIn('841600111', texto)
        self.assertIn('Resumen de compras por clase', texto)
        self.assertIn('Total de compras solicitadas', ' '.join(texto.split()))
        self.assertIn('Insumos', texto)
        self.assertIn('Servicios de soporte', texto)
        self.assertNotIn('00530404', texto)
        self.assertNotIn('00530405', texto)
        self.assertNotIn('Fuente 1', texto)
