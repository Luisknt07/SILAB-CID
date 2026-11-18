"""Ningún documento suelto en la tabla del Centro de reportes.

Lo que el Centro de reportes genera de los registros (respaldo para auditoría y consultas de gestión) se lee en
la categoría temática del anexo con el que se relaciona, o en «Personal, formación y difusión» y «Seguimiento y
mejora». Cada fila dice su etiqueta, lo registrado y su estado, con un conteo como máximo.
"""
from datetime import date
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from apps.documentos.presentation.expediente import consultas_de_la_unidad
from apps.documentos.templatetags.reportes_estilo import (
    CATEGORIA_DE_CONSULTA, CATEGORIA_PERSONAL, CATEGORIA_SEGUIMIENTO, CATEGORIA_SIN_ASIGNAR, CATEGORIAS_DE_ANEXOS,
    ORDEN_DE_CATEGORIAS, consultas_por_categoria, exigencias_de_consultas, filas_de_la_tabla,
)
from apps.gestion_unidades.presentation.gestion_reportes import REPORT_CATEGORIES
from apps.gestion_unidades.presentation.reportes_conteo import CONTEOS, SIN_CONTEO, lo_registrado
from apps.gestion_unidades.presentation.reportes_perfiles import CATEGORIAS_PERFIL
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes

USO, PRACTICAS, SEGURIDAD = (titulo for titulo, _codigos in CATEGORIAS_DE_ANEXOS[:3])
SEGUN_ACTIVIDAD = CATEGORIAS_DE_ANEXOS[-1][0]
SIN_ANEXO = 'Actividades sin anexo específico'


def _bloque(numero, categoria):
    return dict(numero_item=numero, categoria=categoria, nombre=f'Anexo ficticio {numero}')


def _consulta(codigo, respaldo=False, **extra):
    return dict(codigo=codigo, nombre=f'Consulta ficticia {codigo}', respaldo=respaldo, **extra)


def _secuencia(filas):
    """[(categoría, [número de anexo o código de consulta, …]), …] en el orden de la tabla."""
    temas = []
    for fila in filas:
        if not temas or temas[-1][0] != fila['categoria']:
            temas.append((fila['categoria'], []))
        temas[-1][1].append(fila['bloque']['numero_item'] if 'bloque' in fila else fila['consulta']['codigo'])
    return temas


class AsignacionDeCategoriasTests(SimpleTestCase):
    def test_cada_consulta_del_centro_de_reportes_tiene_su_categoria_tematica(self):
        # Una consulta nueva sin asignar caería en «Otros»: esta prueba la detecta. El reglamento pasa a
        # documento principal (encargo I1) y por eso no se asigna.
        codigos = {codigo for codigo, _nombre in REPORT_CATEGORIES} | set(CATEGORIAS_PERFIL)
        sin_asignar = codigos - set(CATEGORIA_DE_CONSULTA) - {'reglamento'}
        self.assertEqual(sin_asignar, set())
        self.assertTrue(set(CATEGORIA_DE_CONSULTA.values()) <= set(ORDEN_DE_CATEGORIAS))
        self.assertNotIn(CATEGORIA_SIN_ASIGNAR, CATEGORIA_DE_CONSULTA.values())
        self.assertEqual(ORDEN_DE_CATEGORIAS[-1], CATEGORIA_SEGUIMIENTO)

    def test_asignacion_minima_del_encargo(self):
        esperadas = {
            USO: ('uso-capacidad', 'calibracion', 'sustancias', 'satisfaccion', 'prestamos', 'visitas', 'inventario'),
            PRACTICAS: ('asignaturas', 'planificaciones', 'ejecuciones', 'aula'),
            SEGURIDAD: ('simulacros', 'desechos'),
            CATEGORIA_PERSONAL: ('personal', 'capacitacion', 'cursos'),
            CATEGORIA_SEGUIMIENTO: ('mejora', 'auditoria'),
            SEGUN_ACTIVIDAD: ('investigacion', 'transferencia', 'finanzas'),
        }
        for categoria, codigos in esperadas.items():
            for codigo in codigos:
                with self.subTest(codigo=codigo):
                    self.assertEqual(CATEGORIA_DE_CONSULTA[codigo], categoria)

    def test_los_documentos_generados_van_al_final_de_su_categoria_y_las_nuevas_en_su_lugar(self):
        grupos = [dict(elementos=[_bloque(1, USO), _bloque(2, USO), _bloque(3, SEGURIDAD),
                                  _bloque(4, SEGUN_ACTIVIDAD), _bloque(5, SIN_ANEXO)])]
        consultas = [_consulta('uso-capacidad'), _consulta('calibracion', True), _consulta('simulacros', True),
                     _consulta('personal', True), _consulta('capacitacion', True), _consulta('mejora'),
                     _consulta('auditoria'), _consulta('reglamento', True), _consulta('consulta-nueva-ficticia')]
        filas = filas_de_la_tabla(grupos, consultas)
        self.assertEqual(_secuencia(filas), [
            (USO, [1, 2, 'uso-capacidad', 'calibracion']),
            (SEGURIDAD, [3, 'simulacros']),
            (CATEGORIA_PERSONAL, ['personal', 'capacitacion']),
            (SEGUN_ACTIVIDAD, [4]),
            (CATEGORIA_SIN_ASIGNAR, ['reglamento', 'consulta-nueva-ficticia']),
            (SIN_ANEXO, [5]),
            (CATEGORIA_SEGUIMIENTO, ['mejora', 'auditoria']),
        ])
        # El identificador de la sección va en un solo documento generado: el primero.
        self.assertEqual([f['consulta']['codigo'] for f in filas if f.get('primera_consulta')], ['uso-capacidad'])
        # Sin consultas, la tabla es la de siempre.
        self.assertEqual(_secuencia(filas_de_la_tabla(grupos)),
                         [(USO, [1, 2]), (SEGURIDAD, [3]), (SEGUN_ACTIVIDAD, [4]), (SIN_ANEXO, [5])])

    def test_una_categoria_sin_anexos_entra_antes_de_la_siguiente_con_anexos(self):
        grupos = [dict(elementos=[_bloque(1, 'Respaldos de la planificación'), _bloque(2, SEGURIDAD)])]
        filas = filas_de_la_tabla(grupos, [_consulta('calibracion', True), _consulta('auditoria')])
        self.assertEqual(_secuencia(filas), [('Respaldos de la planificación', [1]), (USO, ['calibracion']),
                                             (SEGURIDAD, [2]), (CATEGORIA_SEGUIMIENTO, ['auditoria'])])

    def test_cada_fila_trae_etiqueta_registrado_y_estado(self):
        consultas = [_consulta('personal', True, registrado='4 personas', con_registros=True),
                     _consulta('simulacros', True, registrado='0 simulacros', con_registros=False),
                     _consulta('uso-capacidad', registrado=SIN_CONTEO, con_registros=None),
                     # Una consulta armada a mano, sin conteo ni código, no rompe la fila.
                     dict(nombre='Consulta ficticia sin código', url='/ficticia/')]
        lecturas = {c['nombre']: c for grupo in consultas_por_categoria(consultas) for c in grupo['consultas']}
        personal = lecturas['Consulta ficticia personal']
        self.assertEqual((personal['etiqueta'], personal['registrado'], personal['estado']),
                         ('Respaldo para auditoría', '4 personas', 'Con registros'))
        simulacros = lecturas['Consulta ficticia simulacros']
        self.assertEqual((simulacros['registrado'], simulacros['estado']), ('0 simulacros', 'Sin registros en el período'))
        capacidad = lecturas['Consulta ficticia uso-capacidad']
        self.assertEqual((capacidad['etiqueta'], capacidad['registrado'], capacidad['estado']),
                         ('Consulta de gestión', SIN_CONTEO, 'Disponible'))
        self.assertEqual(lecturas['Consulta ficticia sin código']['categoria'], CATEGORIA_SIN_ASIGNAR)
        self.assertEqual(exigencias_de_consultas(consultas),
                         [('respaldo', 'Respaldo para auditoría'), ('gestion', 'Consulta de gestión')])
        self.assertEqual(exigencias_de_consultas(consultas[2:3]), [('gestion', 'Consulta de gestión')])


class CategoriasPorTipoDeUnidadTests(BaseAlcanceReportes):
    desde, hasta = date(2026, 7, 1), date(2026, 12, 31)

    def test_laboratorio_planta_y_observatorio_no_dejan_documentos_sueltos(self):
        for tipo in ('laboratorios', 'plantas_piloto', 'observatorios'):
            with self.subTest(tipo=tipo):
                consultas = consultas_de_la_unidad(self.unidades[tipo], self.desde, self.hasta)
                self.assertTrue(consultas)
                for consulta in consultas:
                    if consulta['codigo'] != 'reglamento':
                        self.assertNotEqual(CATEGORIA_DE_CONSULTA.get(consulta['codigo'], CATEGORIA_SIN_ASIGNAR),
                                            CATEGORIA_SIN_ASIGNAR, consulta['codigo'])
                    self.assertTrue(consulta['registrado'])
                    self.assertEqual(consulta['registrado'] == SIN_CONTEO, consulta['codigo'] not in CONTEOS)
                temas = [g['categoria'] for g in consultas_por_categoria(consultas)]
                self.assertEqual(len(temas), len(set(temas)))
                self.assertIn(CATEGORIA_PERSONAL, temas)
                self.assertEqual(temas[-1], CATEGORIA_SEGUIMIENTO)

    def test_cada_fila_cuesta_una_consulta_como_maximo_y_ninguna_sin_conteo_sencillo(self):
        unidad = self.unidades['laboratorios']
        for codigo in {codigo for codigo, _nombre in REPORT_CATEGORIES}:
            with self.subTest(codigo=codigo), CaptureQueriesContext(connection) as sql:
                lo_registrado(codigo, unidad, self.desde, self.hasta)
            self.assertEqual(len(sql), 1 if codigo in CONTEOS else 0, codigo)
        # La página suma, como mucho, un conteo por documento generado con conteo.
        with CaptureQueriesContext(connection) as sin_conteos, patch(
                'apps.gestion_unidades.presentation.reportes_conteo.lo_registrado', return_value=(SIN_CONTEO, None)):
            consultas = consultas_de_la_unidad(unidad, self.desde, self.hasta)
        with CaptureQueriesContext(connection) as con_conteos:
            consultas_de_la_unidad(unidad, self.desde, self.hasta)
        contadas = sum(c['codigo'] in CONTEOS for c in consultas)
        self.assertEqual(len(con_conteos) - len(sin_conteos), contadas)
        self.assertLessEqual(contadas, len(CONTEOS))
