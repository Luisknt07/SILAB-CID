"""Un anexo por cada documento que pide la universidad (documentos.0027).

Fija la estructura acordada el 16 de noviembre de 2026 (docs/estructura-anexos-por-tipo-de-unidad.md):
- los anexos del informe responden uno a uno a las exigencias de la universidad y llevan su nombre;
- cada tipo de unidad lleva sus anexos, en el mismo orden: comunes, propios y condicionales;
- desechos, investigación y transferencia se presentan solo cuando aplican; si no, conservan su número
  y quedan «No aplica» con su motivo;
- cada meta de la planificación tiene un solo anexo;
- todos usan el formato de registro: datos generales y tablas numeradas «n.m».

El contenido de cada anexo, tabla por tabla, lo fijan las pruebas test_anexos_*.py.
"""
import tempfile
from contextlib import ExitStack
from datetime import date, time
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps as registro
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.anexos_evidencia import (
    ANEXOS, ANEXOS_PERFIL, COLUMNAS_MAXIMAS, CONDICIONALES, CONSTRUCTORES, EXIGENCIAS, MOTIVOS_NO_APLICA, ORDEN,
    Grupo, Par, Registro, anexo_de_cada_meta, anexos_numerados, aplica_el_anexo, componer_anexo, constructor_de,
    es_anexo_de_evidencia, lectura_de_metas, par, pdf_del_anexo,
)
from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS
from apps.documentos.presentation.expediente import (
    anexos_del, construir_expediente, generar_anexos, tramo_del_documento,
)
from apps.documentos.presentation.expediente_catalogo import (
    CATALOGO, CATALOGO_PERFILES, NOMBRES_ESTANDAR_ANTERIORES, RETIRADOS, TIPOS_CATALOGO_PERFILES, asegurar_catalogo,
)
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN
from apps.documentos.presentation.perfil_laboratorios import NOMBRES, SUFIJOS_DE_REFERENCIA, referencia_interna

MIGRACION = import_module('apps.documentos.migrations.0027_anexos_por_exigencia')
DE_LA_UNIVERSIDAD = import_module('apps.documentos.migrations.0028_nombres_de_la_universidad')
IDENTIDAD = (SimpleNamespace(codigo='PRUEBA'), SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={}))
COMUNES = ['REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS', 'PRACTICAS-FT02', 'GUIAS',
           'PRACTICAS-FT03', 'INDUCCION-SEGURIDAD']
CONDICIONALES_EN_ORDEN = ['DESECHOS', 'INVESTIGACION', 'TRANSFERENCIA']
# Los anexos de cada tipo de unidad, en el orden en que se numeran.
ANEXOS_POR_TIPO = {
    'laboratorios': [*COMUNES, *CONDICIONALES_EN_ORDEN],
    'plantas_piloto': [*COMUNES, 'PP-PRODUCCION', 'PP-CALIDAD', *CONDICIONALES_EN_ORDEN],
    'centro_experimental': [*COMUNES, 'CE-ENSAYOS', 'CE-PRODUCCION', *CONDICIONALES_EN_ORDEN],
    # El inventario del observatorio es anual: viaja con el informe B.
    'observatorios': ['EQUIPAMIENTO', 'INVENTARIO-CORTE', 'OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS',
                      'INVESTIGACION', 'TRANSFERENCIA'],
}


def _sin_identidad_real(pila):
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional',
                   'apps.documentos.presentation.expediente_pdf'):
        pila.enter_context(patch(modulo + '.identidad_actual', return_value=IDENTIDAD))
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional'):
        pila.enter_context(patch(modulo + '.logo_institucional', return_value=None))


class CatalogoPorExigenciaTests(SimpleTestCase):
    def setUp(self):
        self.catalogo = {f[0]: f for f in (*CATALOGO, *CATALOGO_PERFILES)}
        self.anexos = {c: f for c, f in self.catalogo.items() if f[-1] == 'INFORME-SEMESTRAL'}

    def test_el_catalogo_el_motor_y_el_orden_nombran_los_mismos_anexos(self):
        codigos = set(self.anexos)
        self.assertEqual(set(ANEXOS) | set(ANEXOS_PERFIL), codigos)
        self.assertEqual(set(CONSTRUCTORES), codigos)
        self.assertEqual(set(ORDEN), codigos)
        self.assertEqual(set(EXIGENCIAS), set(ANEXOS))
        self.assertEqual(set(SUFIJOS_DE_REFERENCIA) & codigos, codigos)
        self.assertEqual(set(TIPOS_CATALOGO_PERFILES), set(ANEXOS_PERFIL))
        self.assertFalse(codigos & set(RETIRADOS))
        self.assertIn('ACCIONES-MEJORA', RETIRADOS)
        self.assertEqual(CONDICIONALES, frozenset(CONDICIONALES_EN_ORDEN))
        self.assertEqual(set(MOTIVOS_NO_APLICA), set(CONDICIONALES))

    def test_el_orden_del_catalogo_es_el_de_la_numeracion(self):
        # Comunes, propios y condicionales al final: el número de un anexo fijo no cambia.
        for tipo, esperados in ANEXOS_POR_TIPO.items():
            with self.subTest(tipo=tipo):
                ordenados = sorted(esperados, key=lambda c: (self.anexos[c][10], c))
                self.assertEqual(ordenados, esperados)
                self.assertEqual(sorted(esperados, key=ORDEN.index), esperados)

    def test_cada_anexo_comun_lleva_el_nombre_de_la_exigencia(self):
        self.assertEqual(self.anexos['EQUIPAMIENTO'][1],
                         'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad')
        self.assertEqual(self.anexos['INVENTARIO-CORTE'][1], 'Inventario de equipamiento, reactivos e insumos')
        self.assertEqual(self.anexos['DESECHOS'][1], 'Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable')
        self.assertEqual(NOMBRES['REGISTRO-USO'], 'Registros de uso del laboratorio')
        self.assertEqual(NOMBRES['GUIAS'], 'Guías de prácticas de laboratorio aprobadas y vinculadas con los contenidos del syllabus')
        for codigo, (titulo, _metas) in ANEXOS.items():
            with self.subTest(codigo=codigo):
                self.assertEqual(titulo, self.anexos[codigo][1])
        for codigo, (titulo, _metas) in ANEXOS_PERFIL.items():
            with self.subTest(codigo=codigo):
                self.assertEqual(titulo, self.anexos[codigo][1])
                self.assertFalse(titulo.startswith('Informe'))

    def test_ningun_documento_ni_meta_se_llama_ft02_o_ft03(self):
        from apps.gestion_unidades.presentation.gestion_reportes import PRACTICE_REPORT_META, REPORT_CATEGORIES
        nombres = [f[1] for f in self.catalogo.values()] + [a.nombre for a in ACTIVIDADES_PLAN]
        nombres += list(NOMBRES.values()) + [etiqueta for _c, etiqueta in REPORT_CATEGORIES]
        nombres += [m['title'] + ' ' + m['code'] for m in PRACTICE_REPORT_META.values()]
        for nombre in nombres:
            with self.subTest(nombre=nombre):
                self.assertNotIn('FT02', nombre)
                self.assertNotIn('FT03', nombre)
                self.assertNotIn('UPEC-P10', nombre)

    def test_cada_meta_tiene_un_solo_anexo(self):
        vistas = {}
        for codigo in self.anexos:
            for meta in ANEXOS_METAS[codigo]:
                self.assertNotIn(meta, vistas, f'{meta} está en {vistas.get(meta)} y en {codigo}')
                vistas[meta] = codigo
        for codigo, (_titulo, metas) in (*ANEXOS.items(), *ANEXOS_PERFIL.items()):
            with self.subTest(codigo=codigo):
                self.assertTrue(set(metas) - {'USO-EFECTIVO'} <= set(ANEXOS_METAS[codigo]))

    def test_la_migracion_escribe_lo_mismo_que_el_catalogo(self):
        # documentos.0028 lleva los nombres recortados de 0027 a la redacción de la universidad.
        for codigo, (_anterior, nombre) in MIGRACION.NOMBRES.items():
            vigente = DE_LA_UNIVERSIDAD.NOMBRES.get(codigo, (nombre, nombre))
            self.assertEqual(vigente[0], nombre, codigo)
            self.assertEqual(vigente[1], self.anexos[codigo][1], codigo)
        for codigo, (recortado, _nuevo) in DE_LA_UNIVERSIDAD.NOMBRES.items():
            self.assertIn(recortado, NOMBRES_ESTANDAR_ANTERIORES[codigo], codigo)
        self.assertEqual(DE_LA_UNIVERSIDAD.NOMBRES['FICHAS-TECNICAS'],
                         (MIGRACION.NUEVOS['FICHAS-TECNICAS']['nombre'], self.anexos['FICHAS-TECNICAS'][1]))
        for codigo, (_anterior, descripcion) in MIGRACION.DESCRIPCIONES.items():
            self.assertEqual(descripcion, self.anexos[codigo][11], codigo)
        for codigo, (_anterior, orden) in MIGRACION.ORDENES.items():
            self.assertEqual(orden, self.anexos[codigo][10], codigo)
        for codigo, datos in MIGRACION.NUEVOS.items():
            fila = self.anexos[codigo]
            nombre = DE_LA_UNIVERSIDAD.NOMBRES.get(codigo, (None, datos['nombre']))[1]
            self.assertEqual((nombre, datos['fuente_reporte'], datos['orden'], datos['descripcion']),
                             (fila[1], fila[9], fila[10], fila[11]), codigo)
            self.assertEqual(datos['tipos_unidad'], TIPOS_CATALOGO_PERFILES.get(codigo, []))
        # Lo que no cambió de nombre o de orden ya coincide con el catálogo anterior.
        self.assertEqual(set(MIGRACION.REACTIVADOS),
                         {'PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA'})

    def test_el_codigo_de_referencia_distingue_el_tipo_de_unidad_y_el_anexo(self):
        referencias = set()
        for tipo, prefijo in (('laboratorios', 'LAB'), ('plantas_piloto', 'PP'), ('centro_experimental', 'CE'),
                              ('observatorios', 'OBS')):
            for codigo in ('PROTOCOLO-BIOSEGURIDAD', *ANEXOS_POR_TIPO[tipo]):
                documento = SimpleNamespace(exigido=SimpleNamespace(codigo=codigo),
                                            unidad=SimpleNamespace(dependencia=tipo, codigo_base=tipo))
                referencia = referencia_interna(documento)
                self.assertTrue(referencia.startswith(f'SLCID-{prefijo}-'), referencia)
                self.assertNotIn(referencia, referencias)
                referencias.add(referencia)

    def test_investigacion_aplica_solo_si_el_plan_la_compromete(self):
        no = {'filas': {'INVESTIGACION': ({'aplica': False}, {})}}
        si = {'filas': {'INVESTIGACION': ({'aplica': True}, {})}}
        self.assertFalse(aplica_el_anexo('INVESTIGACION', no))
        self.assertFalse(aplica_el_anexo('INVESTIGACION', {'filas': {}}))
        self.assertTrue(aplica_el_anexo('INVESTIGACION', si))
        self.assertTrue(aplica_el_anexo('PRACTICAS-FT02', {'filas': {}}))
        self.assertTrue(aplica_el_anexo('TRANSFERENCIA', {'filas': {'SERVICIOS': ({'aplica': True}, {})}}))
        self.assertTrue(aplica_el_anexo('DESECHOS', {'filas': {'DESECHOS': ({'aplica': True}, {})}}))

    def test_cada_anexo_tiene_quien_lo_arme(self):
        for codigo in self.anexos:
            with self.subTest(codigo=codigo):
                self.assertTrue(callable(constructor_de(codigo)))
                self.assertTrue(es_anexo_de_evidencia(SimpleNamespace(codigo=codigo)))

    def test_una_celda_de_dos_lineas_degrada_a_una_si_falta_la_segunda(self):
        self.assertEqual(par('01/09/2026', ''), '01/09/2026')
        self.assertEqual(par('01/09/2026', '—'), '01/09/2026')
        self.assertEqual(par('01/09/2026', 'previsto 09:00–11:00'), Par('01/09/2026', 'previsto 09:00–11:00'))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='anexos-por-exigencia-'))
class AnexosPorTipoDeUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coordinador = get_user_model().objects.create_user('coordinador-exigencia', password='clave-segura',
                                                               first_name='Coordinadora', last_name='De Prueba')
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad exigencia ' + tipo, slug='exigencia-' + tipo,
            dependencia=tipo, fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)
            for tipo in ANEXOS_POR_TIPO}

    def informe(self, tipo, corte='B'):
        documentos = construir_expediente(self.unidades[tipo], 2026, hoy=date(2026, 10, 17))
        return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == corte)

    def test_cada_tipo_de_unidad_lleva_sus_anexos_en_orden(self):
        for tipo, esperados in ANEXOS_POR_TIPO.items():
            with self.subTest(tipo=tipo):
                anexos = anexos_del(self.informe(tipo), incluir_no_aplica=True)
                self.assertEqual([a.exigido.codigo for a in anexos], esperados)
        # En el informe A el observatorio no lleva inventario; los demás tipos, sí.
        codigos_a = [a.exigido.codigo for a in anexos_del(self.informe('observatorios', 'A'), incluir_no_aplica=True)]
        self.assertEqual(codigos_a, [c for c in ANEXOS_POR_TIPO['observatorios'] if c != 'INVENTARIO-CORTE'])
        self.assertIn('INVENTARIO-CORTE', [a.exigido.codigo for a in anexos_del(self.informe('laboratorios', 'A'))])

    def test_cada_anexo_es_un_registro_con_datos_generales_y_tablas_numeradas(self):
        for tipo in ANEXOS_POR_TIPO:
            informe = self.informe(tipo)
            for numero, anexo in anexos_numerados(informe):
                codigo = anexo.exigido.codigo
                with self.subTest(tipo=tipo, anexo=codigo):
                    inicio, fin = tramo_del_documento(anexo)
                    compuesto = componer_anexo(anexo, inicio, fin)
                    claves = [clave for clave, _valor in compuesto['datos']]
                    self.assertEqual(claves[:6], ['Unidad', 'Tipo de unidad', 'Período', 'Datos al', 'Acompaña a',
                                                  'Responsable'])
                    self.assertEqual('Exigencia que responde' in claves, codigo in ANEXOS)
                    self.assertEqual(claves[-2:], ['Metas que respalda', 'Fuente'])
                    self.assertEqual(dict(compuesto['datos'])['Responsable'], 'Coordinadora De Prueba')
                    self.assertEqual(compuesto['numero'], numero)
                    registros = compuesto['registros']
                    self.assertTrue(registros)
                    for registro_ in registros:
                        self.assertIsInstance(registro_, Registro)
                        self.assertLessEqual(len(registro_.cabecera), COLUMNAS_MAXIMAS, registro_.titulo)
                        self.assertNotRegex(registro_.titulo, r'^\d', 'el motor numera las tablas')
                        for fila in registro_.filas:
                            if not isinstance(fila, Grupo):
                                self.assertEqual(len(fila), len(registro_.cabecera), registro_.titulo)
                    with ExitStack() as pila:
                        _sin_identidad_real(pila)
                        pdf = pdf_del_anexo(anexo, inicio, fin, codigo_documento=referencia_interna(anexo), version=1)
                    texto = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages)
                    self.assertIn('Código: ' + referencia_interna(anexo), texto)
                    self.assertIn(f'Anexo {numero}', texto)
                    self.assertIn(f'{numero}.1 {registros[0].titulo.upper()}', ' '.join(texto.split()))
                    for de_informe in ('QUÉ RESPALDA', 'QUÉ FALTA', 'Son las cifras del informe'):
                        self.assertNotIn(de_informe, texto)

    def test_una_unidad_sin_actividad_no_presenta_los_condicionales(self):
        informe = self.informe('laboratorios')
        with ExitStack() as pila:
            _sin_identidad_real(pila)
            generar_anexos(informe, self.coordinador)
        estados = {a.exigido.codigo: a for a in DocumentoExpediente.objects.filter(
            pk__in=[a.pk for a in anexos_del(informe, incluir_no_aplica=True)]).select_related('exigido')}
        for codigo in CONDICIONALES:
            self.assertEqual((estados[codigo].estado, estados[codigo].observacion),
                             ('no_aplica', MOTIVOS_NO_APLICA[codigo]), codigo)
            self.assertIsNone(estados[codigo].recurso_id)
        for codigo in COMUNES:
            self.assertIsNotNone(estados[codigo].recurso_id, codigo)
        # El que no aplica conserva su número y no se cita desde ninguna meta.
        numerados = {d.exigido.codigo: n for n, d in anexos_numerados(informe)}
        self.assertEqual(numerados, {codigo: n for n, codigo in enumerate(ANEXOS_POR_TIPO['laboratorios'], 1)})
        por_meta = anexo_de_cada_meta(informe)
        self.assertEqual(por_meta['GUIAS'], f"Anexo {numerados['GUIAS']}")
        self.assertEqual(por_meta['PRACTICAS'], f"Anexo {numerados['PRACTICAS-FT03']}")
        self.assertEqual(por_meta['INVENTARIO'], f"Anexo {numerados['INVENTARIO-CORTE']}")
        self.assertNotIn('DESECHOS', por_meta)
        self.assertNotIn('INVESTIGACION', por_meta)

    def test_desechos_aplica_si_hay_registros_o_reactivos_y_transferencia_si_hubo_servicios(self):
        from apps.recursos.models.consumibles import Consumible
        from apps.recursos.models.desechos import RegistroDesecho
        from apps.reservas.models.reservas import Reserva
        unidad = self.unidades['laboratorios']
        informe = self.informe('laboratorios')
        anexo = next(a for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.codigo == 'DESECHOS')
        tramo = tramo_del_documento(anexo)
        self.assertFalse(aplica_el_anexo('DESECHOS', lectura_de_metas(anexo, *tramo)))
        self.assertFalse(aplica_el_anexo('TRANSFERENCIA', lectura_de_metas(anexo, *tramo)))
        reactivo = Consumible.objects.create(unidad=unidad, codigo='REACTIVO-EXIGENCIA', nombre='Etanol',
                                             clasificacion='reactivo', unidad_medida='l')
        self.assertTrue(aplica_el_anexo('DESECHOS', lectura_de_metas(anexo, *tramo)))
        reactivo.delete()
        RegistroDesecho.objects.create(unidad=unidad, fecha_generacion=date(2026, 9, 10), clase='especial',
                                       nombre='Residuo de prueba', cantidad=1, registrado_por=self.coordinador)
        self.assertTrue(aplica_el_anexo('DESECHOS', lectura_de_metas(anexo, *tramo)))
        Reserva.objects.create(laboratorio=unidad, usuario=self.coordinador, fecha=date(2026, 9, 12),
                               hora_inicio=time(8), hora_fin=time(10), tipo_solicitud='servicio', estado='completada')
        self.assertTrue(aplica_el_anexo('TRANSFERENCIA', lectura_de_metas(anexo, *tramo)))
        self.assertFalse(aplica_el_anexo('INVESTIGACION', lectura_de_metas(anexo, *tramo)))


class MigracionPorExigenciaTests(TestCase):
    """La migración 0027 sobre el catálogo en el estado de 0026."""

    def setUp(self):
        asegurar_catalogo()
        self.editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        # El catálogo se siembra con los nombres de 0028; estas pruebas parten del estado que dejó 0027.
        self.con_nombres_de_la_universidad = {
            e.codigo: e.nombre for e in DocumentoExigido.objects.filter(codigo__in=DE_LA_UNIVERSIDAD.NOMBRES)}
        DE_LA_UNIVERSIDAD.con_los_nombres_recortados(registro, self.editor)

    def test_los_nombres_de_la_universidad_se_aplican_se_revierten_y_respetan_lo_editado(self):
        recortados = {e.codigo: e.nombre for e in
                      DocumentoExigido.objects.filter(codigo__in=DE_LA_UNIVERSIDAD.NOMBRES)}
        self.assertEqual(recortados, {c: n[0] for c, n in DE_LA_UNIVERSIDAD.NOMBRES.items()})
        DocumentoExigido.objects.filter(codigo='GUIAS').update(nombre='Guías revisadas por la institución')
        for _vez in range(2):
            DE_LA_UNIVERSIDAD.con_la_redaccion_de_la_universidad(registro, self.editor)
        vigentes = {e.codigo: e.nombre for e in
                    DocumentoExigido.objects.filter(codigo__in=DE_LA_UNIVERSIDAD.NOMBRES)}
        self.assertEqual(vigentes.pop('GUIAS'), 'Guías revisadas por la institución')
        esperados = dict(self.con_nombres_de_la_universidad)
        esperados.pop('GUIAS')
        self.assertEqual(vigentes, esperados)

    def estado(self):
        return {e.codigo: (e.nombre, e.descripcion, e.activo, e.orden)
                for e in DocumentoExigido.objects.filter(anexo_de__codigo='INFORME-SEMESTRAL')}

    def test_vuelve_al_estado_anterior_y_se_reaplica_sin_efecto(self):
        vigente = self.estado()
        self.assertEqual({c for c, e in vigente.items() if e[2]},
                         set(ANEXOS) | set(ANEXOS_PERFIL))
        MIGRACION.fusionar_de_nuevo(registro, self.editor)
        anterior = self.estado()
        for codigo in MIGRACION.REACTIVADOS:
            self.assertEqual(anterior[codigo][1:3], (MIGRACION.NOTA_RETIRO, False), codigo)
        for codigo in MIGRACION.NUEVOS:
            self.assertNotIn(codigo, anterior)
        for codigo, (nombre, _nuevo) in MIGRACION.NOMBRES.items():
            self.assertEqual(anterior[codigo][0], nombre, codigo)
        MIGRACION.separar_por_exigencia(registro, self.editor)
        self.assertEqual(self.estado(), vigente)
        MIGRACION.separar_por_exigencia(registro, self.editor)
        self.assertEqual(self.estado(), vigente)

    def test_conserva_lo_editado_por_la_institucion_y_la_historia(self):
        MIGRACION.fusionar_de_nuevo(registro, self.editor)
        DocumentoExigido.objects.filter(codigo='REGISTRO-USO').update(nombre='Nombre propio de la institución')
        DocumentoExigido.objects.filter(codigo='GUIAS').update(descripcion='Desactivado por la institución.')
        unidad = Unidad.objects.create(nombre='Unidad migración 27', slug='unidad-migracion-27',
                                       dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        historia = DocumentoExpediente.objects.create(
            unidad=unidad, exigido=DocumentoExigido.objects.get(codigo='DESECHOS'), anio=2026, corte='A',
            estado='validado')
        MIGRACION.separar_por_exigencia(registro, self.editor)
        estado = self.estado()
        self.assertEqual(estado['REGISTRO-USO'][0], 'Nombre propio de la institución')
        # Sin la nota de retiro de 0025, las guías no se reactivan: las desactivó la institución.
        self.assertEqual(estado['GUIAS'][1:3], ('Desactivado por la institución.', False))
        self.assertTrue(estado['DESECHOS'][2])
        self.assertTrue(DocumentoExpediente.objects.filter(pk=historia.pk, estado='validado').exists())
        # Al revertir, un anexo creado aquí que ya tiene documentos queda inactivo en lugar de borrarse.
        fichas = DocumentoExigido.objects.get(codigo='FICHAS-TECNICAS')
        DocumentoExpediente.objects.create(unidad=unidad, exigido=fichas, anio=2026, corte='B')
        MIGRACION.fusionar_de_nuevo(registro, self.editor)
        self.assertFalse(DocumentoExigido.objects.get(codigo='FICHAS-TECNICAS').activo)
        self.assertFalse(DocumentoExigido.objects.filter(codigo='CE-PRODUCCION').exists())
