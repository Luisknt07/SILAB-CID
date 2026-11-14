"""Transferencia de necesidades: receptor, evaluación y captura inmutable."""
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.necesidades_decanato import lectura_necesidades, render_necesidades_pdf, render_necesidades_xlsx
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso


class NecesidadesDecanatoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.director = usuarios.objects.create_superuser('director-necesidades', password=None)
        cls.receptor = usuarios.objects.create_user('receptor-necesidades', is_staff=True)
        cls.operador = usuarios.objects.create_user('operador-necesidades', is_staff=True)
        cls.dep = DependenciaAcademica.objects.create(nombre='Decanato de prueba', centro_costo='Agrupador confirmado')
        cls.dep.receptores.add(cls.receptor)
        cls.dep_ajena = DependenciaAcademica.objects.create(nombre='Otro centro de costo')
        cls.exigido, _ = DocumentoExigido.objects.get_or_create(codigo='PLAN-COMPRAS-ANUAL', defaults=dict(nombre='Necesidades anuales',
            carpeta='planeacion', periodicidad='anual', origen='ambos', fuente_reporte='compras', requiere_firma=True))

    def unidad(self, sufijo, dependencia=None, tipo='laboratorios'):
        return Unidad.objects.create(nombre='Unidad ' + sufijo, slug='unidad-necesidades-' + sufijo,
            dependencia=tipo, adscrita_a=dependencia or self.dep, administrador=self.operador, fecha_inicio=date(2020, 1, 1))

    def captura(self, unidad, item='Equipo documentado', mes='2', sin_compras=False):
        return dict(pac_version=2, clases_bien_version=1, centro_costo='Centro archivado ' + unidad.nombre,
            compras=[] if sin_compras else [dict(id_necesidad=str(uuid4()), area_id='unidad', area_nombre='Área documentada',
                tipo_necesidad='dotacion', clase_bien='equipos', item=item, cantidad='2', costo_unitario='4.50',
                justificacion='Brecha de capacidad documentada.', equipos_referencia=[], equipo_referencia='',
                mes_compra=mes, clasificacion_pac='pac', cpc='000123', partida='00530404', fuente_pac='001')],
            sin_compras_justificacion='Los recursos actuales cubren las actividades previstas.' if sin_compras else '',
            diagnostico_compras_fuentes=dict(version=1, unidad=unidad.pk, anio=2026, areas=[]))

    def emitido(self, unidad, contenido=None, aprobado=True):
        recurso = Recurso(nombre='Documento nativo', unidad=unidad, archivo='prueba-necesidades.pdf',
            version=1, activo=True, estado='vigente', hash_sha256='a' * 64)
        Recurso.objects.bulk_create([recurso])
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=self.exigido, anio=2026,
            estado='validado', recurso=recurso, version=1, verificacion_qr=uuid4())
        constancia = ConstanciaDocumento.objects.create(token=documento.verificacion_qr, documento=documento,
            recurso=recurso, version=1, sha256=recurso.hash_sha256, titulo='Necesidades', unidad_nombre=unidad.nombre,
            periodo='Año 2026', emitido_por=self.operador, emisor_nombre='Responsable', enviado_en=timezone.now(),
            aprobado_en=timezone.now() if aprobado else None, aprobado_por=self.director if aprobado else None,
            aprobador_nombre='Dirección de prueba' if aprobado else '', contenido_emitido={'pac_datos': contenido} if contenido is not None else {})
        return documento, constancia

    def test_falta_declaracion_no_equivale_a_sin_compras_y_no_consulta_redaccion(self):
        unidad = self.unidad('pendiente')
        d = DocumentoExpediente.objects.create(unidad=unidad, exigido=self.exigido, anio=2026)
        DocumentoElaborado.objects.create(documento=d, contenido=self.captura(unidad), version=1)
        lectura = lectura_necesidades(2026, self.receptor, self.dep)
        u = lectura['unidades'][0]
        self.assertEqual((u['estado'], u['declaracion'], u['transferible'], u['necesidades'], u['pac_datos']),
            ('sin_declaracion', 'pendiente', False, [], None))
        self.assertEqual(lectura['resumen']['sin_compras'], 0)

    def test_validado_por_la_unidad_no_transfiere_antes_de_direccion(self):
        unidad = self.unidad('sin-direccion')
        self.emitido(unidad, self.captura(unidad, item='Texto aún no evaluado'), aprobado=False)
        lectura = lectura_necesidades('2026', self.receptor)
        u = lectura['unidades'][0]
        self.assertEqual(u['estado'], 'pendiente_evaluacion')
        self.assertFalse(u['evaluado'])
        self.assertFalse(u['transferible'])
        self.assertNotIn('Texto aún no evaluado', json.dumps(lectura))

    def test_sin_compras_requiere_declaracion_explicita_evaluada(self):
        unidad = self.unidad('no-requiere')
        self.emitido(unidad, self.captura(unidad, sin_compras=True))
        lectura = lectura_necesidades(2026, self.receptor)
        u = lectura['unidades'][0]
        self.assertEqual((u['estado'], u['transferible'], u['total']), ('sin_compras', True, '0'))
        self.assertIn('cubren las actividades', u['sin_compras_justificacion'])
        self.assertEqual(lectura['resumen']['sin_compras'], 1)
        otra = self.unidad('declaracion-vacia')
        datos = self.captura(otra, sin_compras=True)
        datos['sin_compras_justificacion'] = '<p> </p>'
        self.emitido(otra, datos)
        u = next(u for u in lectura_necesidades(2026, self.receptor)['unidades'] if u['id'] == otra.pk)
        self.assertEqual(u['estado'], 'incompleto')
        self.assertFalse(u['transferible'])

    def test_archivado_sin_matriz_no_se_presenta_sin_compras(self):
        unidad = self.unidad('legada')
        self.emitido(unidad)
        u = lectura_necesidades(2026, self.receptor)['unidades'][0]
        self.assertEqual((u['evaluado'], u['estado'], u['declaracion']), (True, 'sin_matriz', 'sin_matriz'))
        self.assertFalse(u['transferible'])

    def test_lee_captura_inmutable_y_no_sustituye_centro_con_dato_actual(self):
        unidad = self.unidad('congelada')
        contenido = self.captura(unidad)
        documento, constancia = self.emitido(unidad, contenido)
        DocumentoElaborado.objects.create(documento=documento, contenido=dict(compras=[dict(item='Mutable prohibido')]), version=1)
        Unidad.objects.filter(pk=unidad.pk).update(nombre='Unidad renombrada')
        DependenciaAcademica.objects.filter(pk=self.dep.pk).update(centro_costo='Centro actual distinto')
        lectura = lectura_necesidades(2026, self.receptor)
        u = lectura['unidades'][0]
        self.assertEqual((u['nombre'], u['centro_costo']), (unidad.nombre, contenido['centro_costo']))
        self.assertEqual(u['necesidades'][0]['item'], 'Equipo documentado')
        self.assertEqual(u['fuente']['token'], str(constancia.token))
        self.assertEqual(u['fuente']['sha256'], 'a' * 64)
        self.assertEqual(json.loads(json.dumps(lectura)), lectura)
        self.assertEqual(lectura_necesidades(2026, self.receptor), lectura)

    def test_token_recurso_version_y_hash_distintos_no_usan_captura(self):
        for campo, valor in [('verificacion_qr', uuid4()), ('version', 2)]:
            unidad = self.unidad('alterada-' + campo)
            documento, _ = self.emitido(unidad, self.captura(unidad))
            DocumentoExpediente.objects.filter(pk=documento.pk).update(**{campo: valor})
            u = next(u for u in lectura_necesidades(2026, self.director)['unidades'] if u['id'] == unidad.pk)
            self.assertFalse(u['transferible'])
            self.assertIsNone(u['pac_datos'])
        unidad = self.unidad('hash-distinto')
        documento, _ = self.emitido(unidad, self.captura(unidad))
        Recurso.objects.filter(pk=documento.recurso_id).update(hash_sha256='b' * 64)
        u = next(u for u in lectura_necesidades(2026, self.director)['unidades'] if u['id'] == unidad.pk)
        self.assertFalse(u['transferible'])

    def test_fuentes_de_otra_unidad_o_anio_y_recurso_retirado_no_transfieren(self):
        otra = self.unidad('otra-captura')
        for clave, valor in [('unidad', otra.pk), ('anio', 2025)]:
            unidad = self.unidad('fuente-' + clave)
            datos = self.captura(unidad)
            datos['diagnostico_compras_fuentes'][clave] = valor
            self.emitido(unidad, datos)
            u = next(u for u in lectura_necesidades(2026, self.receptor)['unidades'] if u['id'] == unidad.pk)
            self.assertFalse(u['transferible'])
        unidad = self.unidad('recurso-retirado')
        documento, _ = self.emitido(unidad, self.captura(unidad))
        Recurso.objects.filter(pk=documento.recurso_id).update(activo=False)
        u = next(u for u in lectura_necesidades(2026, self.receptor)['unidades'] if u['id'] == unidad.pk)
        self.assertFalse(u['evaluado'])
        self.assertFalse(u['transferible'])

    def test_matriz_legada_con_datos_y_matriz_incompleta_no_inventan_no_compra(self):
        unidad = self.unidad('matriz-v1')
        datos = dict(pac_version=1, centro_costo='Centro legado', compras=[dict(item='Necesidad antigua',
            cantidad='1', costo_unitario='8', justificacion='Necesidad registrada.', clasificacion_pac='por_definir')])
        self.emitido(unidad, datos)
        u = next(u for u in lectura_necesidades(2026, self.receptor)['unidades'] if u['id'] == unidad.pk)
        self.assertTrue(u['transferible'])
        self.assertEqual(u['necesidades'][0]['mes'], 'Por confirmar')
        self.assertIsNone(u['necesidades'][0]['semestre'])
        otra = self.unidad('matriz-incompleta')
        datos = self.captura(otra)
        datos['compras'][0]['cantidad'] = 'NaN'
        self.emitido(otra, datos)
        u = next(u for u in lectura_necesidades(2026, self.receptor)['unidades'] if u['id'] == otra.pk)
        self.assertEqual(u['estado'], 'incompleto')
        self.assertFalse(u['transferible'])
        self.assertIsNone(u['pac_datos'])

    def test_permisos_receptor_solo_dependencia_activa_no_operador(self):
        propia = self.unidad('propia')
        self.unidad('ajena', self.dep_ajena)
        self.assertEqual([u['id'] for u in lectura_necesidades(2026, self.receptor)['unidades']], [propia.pk])
        with self.assertRaises(PermissionDenied):
            lectura_necesidades(2026, self.receptor, self.dep_ajena)
        with self.assertRaises(PermissionDenied):
            lectura_necesidades(2026, self.operador)
        DependenciaAcademica.objects.filter(pk=self.dep.pk).update(activa=False)
        with self.assertRaises(PermissionDenied):
            lectura_necesidades(2026, self.receptor)
        self.assertEqual(len(lectura_necesidades(2026, self.director)['unidades']), 2)

    def test_receptor_sin_unidades_tiene_consulta_vacia_y_excluye_otras_tipologias(self):
        self.unidad('otro-ciclo', tipo='no-auditable')
        lectura = lectura_necesidades(2026, self.receptor, self.dep)
        self.assertEqual(lectura['unidades'], [])
        self.assertEqual(lectura['grupos'][0]['id'], self.dep.pk)
        self.assertEqual(lectura['resumen']['pendientes'], 0)

    def test_validacion_no_admite_anios_ni_dependencias_invalidos(self):
        for anio in (True, 'hoy', 1999, 9999):
            with self.assertRaises(ValidationError):
                lectura_necesidades(anio, self.director)
        with self.assertRaises(ValidationError):
            lectura_necesidades(2026, self.director, 'no-entero')

    def test_matriz_detalle_conserva_clase_nombre_especificaciones_y_columnas_oficiales(self):
        unidad = self.unidad('matriz-detalle')
        datos = self.captura(unidad, item='Licencia CAD', mes='8')
        datos['matriz_detalle_version'] = 1
        datos['compras'][0].update(clase_bien='software', especificaciones='Vigencia anual; 12 usuarios.',
            unidad_medida='usuario/año', cpc='001234567', partida='530702', cantidad='12', costo_unitario='90')
        self.emitido(unidad, datos)
        lectura = lectura_necesidades(2026, self.receptor)
        necesidad = lectura['unidades'][0]['necesidades'][0]
        self.assertEqual((necesidad['clase'], necesidad['item'], necesidad['especificaciones']),
            ('Software y licencias', 'Licencia CAD', 'Vigencia anual; 12 usuarios.'))
        self.assertEqual(necesidad['cpc'], '001234567')
        self.assertEqual(necesidad['total'], '1080')
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertEqual((libro['CONSOLIDADO'].max_column, libro['PAC'].max_column, libro['NO PAC'].max_column), (13, 12, 12))
        self.assertEqual(libro['CONSOLIDADO']['D5'].value, 'Licencia CAD')
        self.assertEqual(libro['CONSOLIDADO']['H5'].value, '001234567')
        self.assertEqual(libro['CONSOLIDADO']['H5'].data_type, 's')
        self.assertIn('Especificaciones: Vigencia anual', libro['CONSOLIDADO']['M5'].value)
        hoja = libro['DETALLE POR CLASE']
        fila = dict(zip([c.value for c in hoja[1]], [c.value for c in hoja[2]]))
        self.assertEqual((fila['CLASE'], fila['NOMBRE DEL BIEN O SERVICIO'], fila['CPC']),
            ('Software y licencias', 'Licencia CAD', '001234567'))
        self.assertEqual(fila['ESPECIFICACIONES'], 'Vigencia anual; 12 usuarios.')
        self.assertEqual((fila['SEMESTRE'], fila['MES']), ('2', 'Agosto'))
        self.assertEqual(fila['GRUPO'], '53')

    def test_nuevo_resumen_redondea_por_necesidad_y_concuerda_lectura_presupuesto_excel_y_pdf(self):
        from copy import deepcopy
        from apps.documentos.presentation.presupuesto_documental import analizar_presupuesto
        unidad = self.unidad('centavos-nuevos')
        datos = self.captura(unidad, item='Necesidad primera')
        datos.update(compras_resumen_version=1, matriz_detalle_version=1)
        primera = datos['compras'][0]
        primera.update(cantidad='1', costo_unitario='0.005', cpc='011200011')
        segunda = deepcopy(primera)
        segunda.update(id_necesidad=str(uuid4()), item='Necesidad segunda', clase_bien='software', mes_compra='8')
        datos['compras'].append(segunda)
        self.emitido(unidad, datos)
        lectura = lectura_necesidades(2026, self.receptor)
        recibida = lectura['unidades'][0]
        self.assertEqual([Decimal(n['total']) for n in recibida['necesidades']], [Decimal('.01'), Decimal('.01')])
        self.assertTrue(all(n.get('compras_resumen_version') == 1 for n in recibida['necesidades']))
        self.assertEqual(Decimal(recibida['total']), Decimal('.02'))
        self.assertEqual(Decimal(lectura['resumen']['total']), Decimal('.02'))
        self.assertEqual(analizar_presupuesto('compras', datos)['total'], Decimal('.02'))
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertEqual(libro['Equipos']['H6'].value, .01)
        self.assertEqual(libro['Software']['H6'].value, .01)
        self.assertEqual((libro['Resumen']['C9'].value, libro['Resumen']['D9'].value,
                          libro['Resumen']['F9'].value), (.01, .01, .02))
        texto = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(render_necesidades_pdf(lectura))).pages)
        self.assertIn('0.02', texto)
        self.assertGreaterEqual(texto.count('0.01'), 2)

    def test_captura_anterior_conserva_productos_sin_redondeo_nuevo(self):
        from copy import deepcopy
        from apps.documentos.presentation.presupuesto_documental import analizar_presupuesto
        unidad = self.unidad('centavos-anteriores')
        datos = self.captura(unidad, item='Necesidad antigua primera')
        primera = datos['compras'][0]
        primera.update(cantidad='1', costo_unitario='0.005')
        segunda = deepcopy(primera)
        segunda.update(id_necesidad=str(uuid4()), item='Necesidad antigua segunda')
        datos['compras'].append(segunda)
        self.emitido(unidad, datos)
        lectura = lectura_necesidades(2026, self.receptor)
        self.assertEqual([Decimal(n['total']) for n in lectura['unidades'][0]['necesidades']],
                         [Decimal('.005'), Decimal('.005')])
        self.assertEqual(Decimal(lectura['resumen']['total']), Decimal('.010'))
        self.assertEqual(analizar_presupuesto('compras', datos)['total'], Decimal('.010'))
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertIn('CONSOLIDADO', libro.sheetnames)
        self.assertEqual(libro['CONSOLIDADO']['G5'].value, '=E5*F5')

    def test_excel_y_pdf_consolidan_tras_evaluacion_sin_perder_unidad_o_mes(self):
        una, dos = self.unidad('uno'), self.unidad('dos')
        self.emitido(una, self.captura(una, item='Equipo primer semestre', mes='2'))
        otra = self.captura(dos, item='=texto de software', mes='9')
        otra['compras'][0]['clase_bien'] = 'software'
        otra['compras'][0]['clasificacion_pac'] = 'no_pac'
        self.emitido(dos, otra)
        pendiente = self.unidad('pendiente-exportacion')
        self.emitido(pendiente, self.captura(pendiente, item='No exportar pendiente'), aprobado=False)
        sin = self.unidad('sin-compras-exportacion')
        self.emitido(sin, self.captura(sin, sin_compras=True))
        lectura = lectura_necesidades(2026, self.receptor)
        with self.assertNumQueries(0):
            contenido = render_necesidades_xlsx(lectura)
        libro = load_workbook(BytesIO(contenido), data_only=False)
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertEqual(hoja.max_column, 13)
        self.assertEqual((hoja['B5'].value, hoja['C5'].value), (dos.nombre, otra['centro_costo']))
        self.assertEqual(hoja['D5'].value, '=texto de software')
        self.assertEqual(hoja['D5'].data_type, 's')
        self.assertEqual(hoja['G6'].value, '=E6*F6')
        self.assertEqual(hoja['I6'].value, '=IF(J6="","",LEFT(J6,2))')
        self.assertEqual(libro['PAC'].max_column, 12)
        self.assertEqual(libro['NO PAC'].max_column, 12)
        self.assertEqual(libro['PAC']['B5'].value, una.nombre)
        self.assertEqual(libro['NO PAC']['B5'].value, dos.nombre)
        self.assertEqual(libro['PROGRAMACION']['K2'].value, '2')
        self.assertEqual(libro['PROGRAMACION']['L2'].value, 'Septiembre')
        self.assertNotIn('No exportar pendiente', str(list(hoja.values)))
        self.assertIn('Sin compras', str(list(libro['UNIDADES'].values)))
        pdf = PdfReader(BytesIO(render_necesidades_pdf(lectura)))
        self.assertLess(float(pdf.pages[0].mediabox.width), float(pdf.pages[0].mediabox.height))
        texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertIn('Software', texto)
        self.assertIn('Septiembre', texto)
        self.assertIn('cubren las actividades', texto)
        self.assertNotIn('No exportar pendiente', texto)

    def test_conformidad_humana_legada_sin_matriz_no_es_no_compra(self):
        unidad = self.unidad('humana-legada')
        documento, _ = self.emitido(unidad, self.captura(unidad))
        DocumentoExpediente.objects.filter(pk=documento.pk).update(verificacion_qr=None, firma_verificada=True)
        RegistroAuditoriaUnidad.objects.create(unidad=unidad, usuario=self.director, entidad=documento._meta.label,
            objeto_id=str(documento.pk), accion='actualizar', descripcion='conformidad_documental:confirmar',
            datos_nuevos=dict(version=1, recurso_id=documento.recurso_id, sha256='a' * 64, alcance='documental'))
        u = lectura_necesidades(2026, self.receptor)['unidades'][0]
        self.assertTrue(u['evaluado'])
        self.assertEqual(u['estado'], 'sin_matriz')
        self.assertFalse(u['transferible'])
