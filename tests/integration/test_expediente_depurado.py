"""Expediente depurado: lo mínimo para cumplir, sin anexos repetidos ni metas que no se miden.

Fija la depuración de ``documentos.0024`` con el catálogo que dejó ``documentos.0027``:
- la planificación viaja sola y el informe lleva un anexo por documento que pide la universidad, más los
  propios de cada tipo;
- el mantenimiento tiene anexo en los dos períodos, en el plan de mantenimiento y equipamiento;
- el inventario es semestral, salvo en los observatorios, que lo presentan una vez al año con el informe B;
- el reporte del inventario trae los movimientos de insumos;
- las consultas de gestión solo se ofrecen cuando la unidad tiene registros del módulo;
- los anexos retirados quedan inactivos sin borrar su historia.
"""
import tempfile
from datetime import date
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps as registro
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS, detalle_anexo
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, consultas_de_la_unidad
from apps.documentos.presentation.expediente_catalogo import (
    CATALOGO, CATALOGO_PERFILES, NOMBRES_ESTANDAR_ANTERIORES, RETIRADOS, asegurar_catalogo,
)
from apps.documentos.presentation.metas_plan import ANEXOS_AUTOMATICOS
from apps.documentos.templatetags.reportes_estilo import evidencias_cierre
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.recursos.models.consumibles import Consumible, EntradaInventario

DEPURADOS = ('INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE')
MIGRACION = import_module('apps.documentos.migrations.0024_expediente_depurado')
# Las migraciones siguientes parten de lo que 0024 escribió: 0025 renombra o retira parte de lo que 0024
# dejó y 0027 separa de nuevo un anexo por cada documento que pide la universidad.
SIGUIENTE = import_module('apps.documentos.migrations.0025_anexos_del_informe')
POR_EXIGENCIA = import_module('apps.documentos.migrations.0027_anexos_por_exigencia')
DE_LA_UNIVERSIDAD = import_module('apps.documentos.migrations.0028_nombres_de_la_universidad')


class _FilasDelCatalogo(list):
    def first(self):
        return self[0] if self else None


class _CatalogoEnMemoria:
    """Lo que usan las migraciones de datos del catálogo, sobre filas en memoria, sin base de datos."""

    def __init__(self, filas):
        self.filas, self.objects = filas, self

    def using(self, _alias):
        return self

    def filter(self, codigo=None, codigo__in=()):
        codigos = {codigo} if codigo else set(codigo__in)
        return _FilasDelCatalogo(f for f in self.filas if f.codigo in codigos)


def _fila_del_catalogo(codigo, nombre, descripcion):
    return SimpleNamespace(codigo=codigo, nombre=nombre, descripcion=descripcion, activo=True, orden=None,
                           save=lambda update_fields=None: None)


class CatalogoDepuradoTests(SimpleTestCase):
    def test_lo_retirado_no_vuelve_a_sembrarse(self):
        codigos = {f[0] for f in (*CATALOGO, *CATALOGO_PERFILES)}
        self.assertTrue(set(DEPURADOS) <= set(RETIRADOS))
        self.assertFalse(codigos & set(RETIRADOS))
        self.assertEqual(set(MIGRACION.RETIRADOS), set(DEPURADOS))

    def test_ningun_anexo_promete_una_meta_que_no_cuenta(self):
        for fila in (*CATALOGO, *CATALOGO_PERFILES):
            with self.subTest(codigo=fila[0]):
                self.assertNotIn('meta opcional', fila[11])
                self.assertNotIn('cuenta en la nota solo si', fila[11])

    def test_la_migracion_escribe_los_mismos_textos_que_el_catalogo(self):
        # Lo que 0024 escribió pasa por 0025, 0027 y 0028 tal como ellas lo aplican: al final es el catálogo
        # vigente.
        filas = {codigo: _fila_del_catalogo(codigo, MIGRACION.NOMBRES.get(codigo, ('', ''))[1],
                                            MIGRACION.DESCRIPCIONES.get(codigo, ''))
                 for codigo in set(MIGRACION.NOMBRES) | set(MIGRACION.DESCRIPCIONES)}
        catalogo = _CatalogoEnMemoria(list(filas.values()))
        apps = SimpleNamespace(get_model=lambda *_modelo: catalogo)
        editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        SIGUIENTE.fusionar(apps, editor)
        POR_EXIGENCIA.separar_por_exigencia(apps, editor)
        DE_LA_UNIVERSIDAD.con_la_redaccion_de_la_universidad(apps, editor)
        por_codigo = {f[0]: f for f in CATALOGO}
        for codigo, fila in filas.items():
            with self.subTest(codigo=codigo):
                if codigo in RETIRADOS:
                    # Lo que 0024 escribió es exactamente lo que 0025 reconoce para dejar solo la nota de retiro.
                    self.assertNotIn(codigo, por_codigo)
                    self.assertEqual((fila.descripcion, fila.activo), (SIGUIENTE.NOTA_RETIRO, False))
                    continue
                self.assertTrue(fila.activo)
                self.assertEqual(fila.descripcion, por_codigo[codigo][11])
                if codigo in MIGRACION.NOMBRES:
                    self.assertEqual(fila.nombre, por_codigo[codigo][1])
                    # Un catálogo que conserva el nombre de 0024 se sigue presentando con el nombre vigente.
                    self.assertIn(MIGRACION.NOMBRES[codigo][1], NOMBRES_ESTANDAR_ANTERIORES[codigo])

    def test_cada_anexo_respalda_una_meta_o_es_registro_sin_meta(self):
        descripciones = {f[0]: f[11] for f in (*CATALOGO, *CATALOGO_PERFILES)}
        for codigo, metas in ANEXOS_METAS.items():
            with self.subTest(codigo=codigo):
                # Un anexo sin meta lo declara en su descripción: es registro del período.
                self.assertTrue(metas or 'sin meta propia' in descripciones.get(codigo, ''))
        self.assertEqual((ANEXOS_METAS['FICHAS-TECNICAS'], ANEXOS_METAS['CE-PRODUCCION']), ((), ()))
        # Un anexo por cada documento que pide la universidad (documentos.0027): cada meta tiene un solo anexo.
        metas = [meta for respaldadas in ANEXOS_METAS.values() for meta in respaldadas]
        self.assertEqual(len(metas), len(set(metas)))
        # El equipamiento respalda el mantenimiento y el inventario la revisión física; la disponibilidad y los
        # insumos son registros sin meta. Las acciones de mejora van en el informe, como registro sin meta.
        self.assertEqual(ANEXOS_METAS['EQUIPAMIENTO'], ('MANTENIMIENTO', 'EQUIPAMIENTO'))
        self.assertEqual(ANEXOS_METAS['INVENTARIO-CORTE'], ('INVENTARIO', 'INSUMOS'))
        self.assertTrue({'EQUIPAMIENTO', 'INSUMOS', 'MEJORA'} <= ANEXOS_AUTOMATICOS)
        self.assertFalse({'INVENTARIO', 'MANTENIMIENTO'} & ANEXOS_AUTOMATICOS)
        # El anexo retirado conserva su lectura solo para los cierres anteriores que aún lo traen.
        self.assertEqual(ANEXOS_METAS['ACCIONES-MEJORA'], ('MEJORA',))
        self.assertIn('ACCIONES-MEJORA', RETIRADOS)
        self.assertNotIn('INVENTARIO-CORTE', RETIRADOS)

    def test_la_meta_de_mantenimiento_tiene_anexo_y_no_queda_suelta_en_el_cierre(self):
        mantenimiento = dict(codigo='MANTENIMIENTO', nombre='Mantenimiento', indicador='Mantenimientos completados',
            meta='≥ 80 %', registrado=1, porcentaje=50, pendiente=False, aplica=True, obligatoria=True,
            exigible=True, definida=True, exigencia='Obligatorio institucional', estado='No cumple')
        inventario = dict(codigo='INVENTARIO', nombre='Revisión física del inventario', indicador='Acta verificada',
            meta='1', registrado=1, porcentaje=100, pendiente=False, aplica=True, obligatoria=True,
            exigible=True, definida=True, exigencia='Obligatorio institucional', estado='Cumple')
        disponibilidad = dict(codigo='EQUIPAMIENTO', nombre='Disponibilidad', indicador='Equipos disponibles',
            registrado=3, porcentaje=None, pendiente=False, aplica=False, exigible=False,
            exigencia='Registro del período', estado='Anexo automático')
        cierre = dict(politica_metas=3, catalogo=[mantenimiento, inventario, disponibilidad],
                      filas=[mantenimiento, inventario])
        # El mantenimiento y la disponibilidad van en el equipamiento; la revisión física, en el inventario.
        detalle = detalle_anexo('EQUIPAMIENTO', cierre)
        self.assertEqual([f['codigo'] for f in detalle], ['MANTENIMIENTO', 'EQUIPAMIENTO'])
        acta = detalle_anexo('INVENTARIO-CORTE', cierre)
        self.assertEqual([f['codigo'] for f in acta], ['INVENTARIO'])
        anexos = [
            SimpleNamespace(nombre_documental='Plan de mantenimiento de equipos e informe de equipamiento, '
                            'disponibilidad y funcionalidad', exigido=SimpleNamespace(nombre='EQUIPAMIENTO'),
                            recurso_id=None, indicadores_cierre=detalle),
            SimpleNamespace(nombre_documental='Inventario de equipamiento, reactivos e insumos',
                            exigido=SimpleNamespace(nombre='INVENTARIO-CORTE'), recurso_id=None,
                            indicadores_cierre=acta),
        ]
        # Cada meta obligatoria viaja en su anexo: ninguna queda suelta en el cierre.
        bloques = [b for grupo in evidencias_cierre(cierre, anexos) for b in grupo['elementos']]
        self.assertEqual(len(bloques), 2)
        self.assertFalse(any(b['sin_anexo'] for b in bloques))
        self.assertEqual(next(g for g in evidencias_cierre(cierre, anexos))['codigo'], 'obligatorio')

    def test_el_inventario_del_observatorio_no_inventa_un_registro_de_insumos(self):
        inventario = dict(codigo='INVENTARIO', nombre='Inventario', exigible=True, porcentaje=100, aplica=True,
                          exigencia='Obligatorio institucional', estado='Cumple')
        mantenimiento = dict(codigo='MANTENIMIENTO', nombre='Mantenimiento', exigible=True, porcentaje=100,
                             aplica=True, exigencia='Obligatorio institucional', estado='Cumple')
        # El plan del observatorio no lleva la actividad de insumos: el anexo muestra solo las metas que respalda.
        detalle = detalle_anexo('INVENTARIO-CORTE', dict(politica_metas=3, catalogo=[inventario, mantenimiento]))
        self.assertEqual([f['codigo'] for f in detalle], ['INVENTARIO'])


MEDIA = tempfile.mkdtemp(prefix='citt-expediente-depurado-')


@override_settings(MEDIA_ROOT=MEDIA)
class ExpedienteDepuradoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user('coordinador-depurado', password='clave-segura')
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad depurada ' + tipo, slug='depurada-' + tipo,
            dependencia=tipo, fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)
            for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')}

    def expediente(self, tipo):
        return construir_expediente(self.unidades[tipo], 2026, hoy=date(2026, 10, 17))

    def test_documentos_por_semestre_de_cada_tipo_de_unidad(self):
        # Planificación + informe con un anexo por documento que pide la universidad (once, documentos.0027) y
        # los propios de cada tipo; el observatorio no lleva uso, fichas, prácticas, guías, seguridad ni
        # desechos, y presenta su inventario una vez al año, con el informe B.
        esperados = {'laboratorios': (13, 13), 'plantas_piloto': (15, 15),
                     'centro_experimental': (15, 15), 'observatorios': (8, 9)}
        for tipo, (en_a, en_b) in esperados.items():
            with self.subTest(tipo=tipo):
                documentos = self.expediente(tipo)
                por_corte = {corte: [d for d in documentos if d.corte == corte and d.mes is None] for corte in 'AB'}
                self.assertEqual((len(por_corte['A']), len(por_corte['B'])), (en_a, en_b))
                # Lo de una vez y el plan de compras no cambian.
                self.assertEqual({d.exigido.codigo for d in documentos if not d.corte},
                                 {'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'REGLAMENTO-USO',
                                  'PLAN-COMPRAS-ANUAL'})
                self.assertFalse(set(RETIRADOS) & {d.exigido.codigo for d in documentos})
                for corte, filas in por_corte.items():
                    plan = next(d for d in filas if d.exigido.codigo == 'PLANIFICACION')
                    self.assertEqual(anexos_del(plan), [])

    def test_el_mantenimiento_tiene_anexo_en_los_dos_periodos_de_cada_tipo(self):
        for tipo in self.unidades:
            documentos = self.expediente(tipo)
            for corte in 'AB':
                with self.subTest(tipo=tipo, corte=corte):
                    informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == corte)
                    self.assertIn('EQUIPAMIENTO', {a.exigido.codigo for a in anexos_del(informe)})

    def test_equipamiento_semestral_e_inventario_semestral_salvo_en_el_observatorio(self):
        # El inventario vuelve como anexo propio (documentos.0027): semestral donde se mueven insumos y anual,
        # con el informe B, en el observatorio. El equipamiento es semestral en todos los tipos.
        for tipo in self.unidades:
            with self.subTest(tipo=tipo):
                documentos = self.expediente(tipo)
                self.assertEqual(sorted(d.corte for d in documentos if d.exigido.codigo == 'EQUIPAMIENTO'), ['A', 'B'])
                inventario = [d for d in documentos if d.exigido.codigo == 'INVENTARIO-CORTE']
                self.assertEqual(sorted(d.corte for d in inventario),
                                 ['B'] if tipo == 'observatorios' else ['A', 'B'])
                informes = {d.corte: d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL'}
                for d in inventario:
                    self.assertIn(d, anexos_del(informes[d.corte]))

    def test_el_observatorio_no_recibe_registro_de_uso(self):
        self.assertNotIn('REGISTRO-USO', {d.exigido.codigo for d in self.expediente('observatorios')})
        self.assertIn('REGISTRO-USO', {d.exigido.codigo for d in self.expediente('laboratorios')})

    def reporte(self, unidad, categoria):
        peticion = RequestFactory().get('/', {'categoria_reporte': categoria, 'desde': '2026-07-01',
                                              'hasta': '2026-12-31'})
        peticion.user = self.coordinador
        return build_unit_report(peticion, unidad)

    def test_el_inventario_trae_los_movimientos_de_insumos_del_periodo(self):
        for tipo in ('laboratorios', 'plantas_piloto'):
            with self.subTest(tipo=tipo):
                unidad = self.unidades[tipo]
                insumo = Consumible.objects.create(unidad=unidad, codigo='INS-DEP-' + tipo[:3].upper(),
                    nombre='Insumo de prueba', unidad_medida='kg', ubicacion='Bodega')
                EntradaInventario.objects.create(unidad=unidad, consumible=insumo, tipo='ingreso',
                    cantidad=Decimal('2'), usuario=self.coordinador, referencia='ACTA-PRUEBA')
                datos = self.reporte(unidad, 'recursos')['dataset']
                tablas = {t['titulo']: t for t in datos['tablas']}
                movimientos = tablas['Movimientos de reactivos e insumos del período']
                self.assertEqual(len(movimientos['rows']), 1)
                self.assertEqual(movimientos['rows'][0][2], insumo.codigo)
                self.assertIn('Existencias actuales de reactivos e insumos', tablas)
                tarjetas = {c[0]: c[1] for c in datos['cards']}
                self.assertEqual(tarjetas['Movimientos de insumos del período'], 1)
        observatorio = self.reporte(self.unidades['observatorios'], 'recursos')['dataset']
        self.assertFalse(any('insumos' in t['titulo'] for t in observatorio['tablas']))

    def test_el_equipamiento_reune_mantenimiento_y_funcionalidad_sin_repetir_el_inventario(self):
        reporte = self.reporte(self.unidades['laboratorios'], 'equipamiento')
        titulos = [t['titulo'] for t in reporte['dataset']['tablas']]
        self.assertIn('Órdenes de mantenimiento y respaldo de su ejecución', titulos)
        self.assertIn('Medición del programa anual crítico al corte efectivo', titulos)
        self.assertIn('Pruebas funcionales documentadas en el período', titulos)
        self.assertNotIn('Identificación y verificación física del equipamiento', titulos)
        tarjetas = {c[0] for c in reporte['dataset']['cards']}
        self.assertTrue({'Mantenimientos del período', 'Meta de mantenimiento crítico (80 %)'} <= tarjetas)
        # La consulta alimenta el anexo del plan de mantenimiento y el equipamiento (documentos.0027).
        self.assertEqual(reporte['expediente']['nombre'],
                         'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad')
        self.assertEqual(reporte['expediente']['periodicidad'], 'Una vez por período académico')

    def test_una_consulta_de_gestion_sin_registros_no_se_muestra(self):
        unidad = self.unidades['laboratorios']
        codigos = {c['codigo'] for c in consultas_de_la_unidad(unidad, date(2026, 7, 1), date(2026, 12, 31))}
        self.assertTrue({'auditoria', 'uso-capacidad'} <= codigos)
        self.assertFalse({'aula', 'visitas', 'cursos', 'finanzas', 'retiros', 'prestamos', 'inventario',
                          'mantenimiento', 'asignaturas'} & codigos)
        # Ninguna consulta repite la fuente de un anexo del informe (documentos.0027).
        self.assertFalse({'reservas', 'equipamiento', 'recursos', 'planificaciones', 'guias', 'ejecuciones',
                          'seguridad', 'desechos', 'investigacion', 'transferencia'} & codigos)
        Consumible.objects.create(unidad=unidad, codigo='INS-CONSULTA', nombre='Insumo con registro')
        codigos = {c['codigo'] for c in consultas_de_la_unidad(unidad, date(2026, 7, 1), date(2026, 12, 31))}
        # El inventario de insumos ya está en el anexo de inventario: la consulta no lo repite.
        self.assertNotIn('inventario', codigos)

    def test_la_consulta_de_atenciones_del_observatorio_aparece_solo_con_registros(self):
        unidad = self.unidades['observatorios']
        codigos = {c['codigo'] for c in consultas_de_la_unidad(unidad, date(2026, 7, 1), date(2026, 12, 31))}
        self.assertNotIn('reservas', codigos)
        self.assertIn('auditoria', codigos)
        self.assertNotIn('uso-capacidad', codigos)  # El observatorio no la tiene en su Centro de reportes.


class MigracionDepuradaTests(TestCase):
    """La migración 0024 sobre un catálogo en el estado de 0023."""

    def setUp(self):
        self.editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        # La base de pruebas ya tiene el catálogo de las migraciones; se lleva cada fila al estado de 0023.
        self.informe, _ = DocumentoExigido.objects.get_or_create(codigo='INFORME-SEMESTRAL', defaults=dict(
            nombre='Informe', carpeta='evaluacion', periodicidad='semestral'))
        self.plan, _ = DocumentoExigido.objects.get_or_create(codigo='PLANIFICACION', defaults=dict(
            nombre='Plan', carpeta='planeacion', periodicidad='semestral'))
        frase_prestamos = MIGRACION.FRASES_FALSAS[0]
        filas = {
            # La frase falsa agregada por 0023 a un texto distribuido: queda solo la nota de retiro.
            'PRESTAMOS-EQUIPOS': ('Registro de préstamos de equipos',
                                  MIGRACION.ANTERIORES['PRESTAMOS-EQUIPOS'][0] + ' ' + frase_prestamos, self.informe),
            # Un texto propio de la institución se conserva y recibe la nota.
            'INSUMOS-CORTE': ('Reactivos e insumos: existencias y movimientos del período',
                              'Texto propio de insumos. ' + MIGRACION.FRASES_FALSAS[2], self.informe),
            'INDICADORES-PLAN': ('Plan semestral de prácticas por asignatura', '', self.plan),
            'PLAN-MANTENIMIENTO': ('Plan anual de mantenimiento preventivo y correctivo',
                                   MIGRACION.ANTERIORES['PLAN-MANTENIMIENTO'][0], self.plan),
            'EQUIPAMIENTO': (MIGRACION.NOMBRES['EQUIPAMIENTO'][0], MIGRACION.ANTERIORES['EQUIPAMIENTO'][0],
                             self.informe),
            'INVENTARIO-CORTE': (MIGRACION.NOMBRES['INVENTARIO-CORTE'][0],
                                 MIGRACION.ANTERIORES['INVENTARIO-CORTE'][0], self.informe),
            'ACCIONES-MEJORA': ('Seguimiento de acciones de mejora',
                                'Texto propio de la institución. ' + MIGRACION.FRASES_FALSAS[3], self.informe),
        }
        for codigo, (nombre, descripcion, padre) in filas.items():
            DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(
                nombre=nombre, descripcion=descripcion, carpeta='evaluacion',
                periodicidad='anual' if codigo in ('INVENTARIO-CORTE', 'PLAN-MANTENIMIENTO') else 'semestral',
                origen='sistema', anexo_de=padre, activo=True))
        self.unidad = Unidad.objects.create(nombre='Unidad migración', slug='unidad-migracion',
            dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        self.historia = DocumentoExpediente.objects.create(unidad=self.unidad,
            exigido=DocumentoExigido.objects.get(codigo='INSUMOS-CORTE'), anio=2026, corte='A', estado='validado')

    def estado(self):
        return {e.codigo: (e.nombre, e.descripcion, e.activo, e.periodicidad)
                for e in DocumentoExigido.objects.order_by('codigo')}

    def test_retira_sin_borrar_historia_corrige_textos_y_se_repite_sin_efecto(self):
        MIGRACION.depurar(registro, self.editor)
        estado = self.estado()
        for codigo in DEPURADOS:
            self.assertFalse(estado[codigo][2], codigo)
            self.assertIn(MIGRACION.NOTAS_RETIRO[codigo], estado[codigo][1])
            self.assertNotIn('meta opcional', estado[codigo][1])
        for codigo in ('PRESTAMOS-EQUIPOS', 'INDICADORES-PLAN', 'PLAN-MANTENIMIENTO'):
            self.assertEqual(estado[codigo][1], MIGRACION.NOTAS_RETIRO[codigo])
        self.assertTrue(estado['INSUMOS-CORTE'][1].startswith('Texto propio de insumos.'))
        self.assertTrue(DocumentoExpediente.objects.filter(pk=self.historia.pk, estado='validado').exists())
        self.assertEqual(estado['EQUIPAMIENTO'][:3], (MIGRACION.NOMBRES['EQUIPAMIENTO'][1],
                                                      MIGRACION.DESCRIPCIONES['EQUIPAMIENTO'], True))
        self.assertEqual(estado['INVENTARIO-CORTE'], (MIGRACION.NOMBRES['INVENTARIO-CORTE'][1],
                                                      MIGRACION.DESCRIPCIONES['INVENTARIO-CORTE'], True, 'anual'))
        # Un texto editado por la institución se conserva, sin la promesa falsa.
        self.assertEqual(estado['ACCIONES-MEJORA'][1], 'Texto propio de la institución.')
        MIGRACION.depurar(registro, self.editor)
        self.assertEqual(self.estado(), estado)

    def test_la_reversa_reactiva_lo_retirado_y_devuelve_los_nombres(self):
        MIGRACION.depurar(registro, self.editor)
        MIGRACION.restaurar(registro, self.editor)
        estado = self.estado()
        for codigo in DEPURADOS:
            self.assertTrue(estado[codigo][2], codigo)
            self.assertNotIn(MIGRACION.NOTAS_RETIRO[codigo], estado[codigo][1])
        self.assertEqual(estado['PLAN-MANTENIMIENTO'][1], MIGRACION.ANTERIORES['PLAN-MANTENIMIENTO'][0])
        self.assertEqual(estado['EQUIPAMIENTO'][1], MIGRACION._sin_frases_falsas(MIGRACION.ANTERIORES['EQUIPAMIENTO'][0]))
        self.assertEqual(estado['EQUIPAMIENTO'][0], MIGRACION.NOMBRES['EQUIPAMIENTO'][0])
        self.assertEqual(estado['INVENTARIO-CORTE'][0], MIGRACION.NOMBRES['INVENTARIO-CORTE'][0])
        self.assertTrue(DocumentoExpediente.objects.filter(pk=self.historia.pk).exists())
