"""Perfiles propios, catálogo explícito e historia conservada."""
from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, leer_expediente
from apps.documentos.presentation.expediente_catalogo import (
    CATALOGO, CATALOGO_PERFILES, NOMBRES_ESTANDAR_ANTERIORES, TIPOS_CATALOGO_PERFILES,
    asegurar_catalogo,
)
from apps.documentos.presentation.perfil_unidades import (
    aplica_documento, base_de, documento_visible, es_unidad_auditable,
    familias_de_perfil, nombre_para, requisitos_para,
)


class PerfilesDocumentalesPurosTests(SimpleTestCase):
    def exigido(self, codigo, **cambios):
        fila = next(f for f in CATALOGO if f[0] == codigo)
        return SimpleNamespace(**(dict(codigo=codigo, nombre=fila[1], fuente_reporte=fila[9], tipos_unidad=[]) | cambios))

    def unidad(self, base):
        return SimpleNamespace(dependencia=base, codigo_base=base)

    def test_el_observatorio_no_hereda_formatos_de_practicas_ni_controles_biologicos(self):
        # Tampoco el registro de uso: el observatorio no tiene meta de sesiones que respaldar.
        for codigo in ('REGISTRO-USO', 'PRACTICAS-FT02', 'PRACTICAS-FT03',
                       'GUIAS', 'INDUCCION-SEGURIDAD', 'DESECHOS'):
            with self.subTest(codigo=codigo):
                self.assertFalse(aplica_documento(self.exigido(codigo), 'observatorios'))
                self.assertTrue(aplica_documento(self.exigido(codigo), 'laboratorios'))

    def test_protocolo_general_disponible_para_todos_los_perfiles_sin_forzar_bioseguridad(self):
        exigido = self.exigido('PROTOCOLO-BIOSEGURIDAD')
        for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(base=base):
                self.assertTrue(aplica_documento(exigido, base))
                requisitos = requisitos_para(SimpleNamespace(unidad=self.unidad(base), exigido=exigido))
                self.assertTrue(requisitos)
        observatorio = SimpleNamespace(unidad=self.unidad('observatorios'), exigido=exigido)
        self.assertIn('información', ' '.join(requisitos_para(observatorio)))
        self.assertFalse(aplica_documento(self.exigido('DESECHOS'), 'observatorios'))

    def test_nombres_anteriores_solo_se_actualizan_en_presentacion_si_la_fuente_sigue_estandar(self):
        for codigo, nombres in NOMBRES_ESTANDAR_ANTERIORES.items():
            for nombre in nombres:
                exigido = self.exigido(codigo, nombre=nombre)
                with self.subTest(codigo=codigo, nombre=nombre):
                    for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
                        self.assertNotIn('(firmad', nombre_para(exigido, self.unidad(base)))
                    self.assertEqual(exigido.nombre, nombre)
                    exigido.fuente_reporte = 'fuente-personalizada'
                    self.assertEqual(nombre_para(exigido, self.unidad('laboratorios')), nombre)

    def test_todos_los_documentos_estandar_aplicables_tienen_contenido_orientado_por_perfil(self):
        for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            for fila in (*CATALOGO, *CATALOGO_PERFILES):
                exigido = SimpleNamespace(codigo=fila[0], nombre=fila[1], fuente_reporte=fila[9],
                    tipos_unidad=TIPOS_CATALOGO_PERFILES.get(fila[0], []))
                if not aplica_documento(exigido, base):
                    continue
                documento = SimpleNamespace(unidad=self.unidad(base), exigido=exigido)
                with self.subTest(base=base, codigo=exigido.codigo):
                    self.assertTrue(requisitos_para(documento))

    def test_las_practicas_de_planta_y_campo_siguen_disponibles(self):
        for tipo in ('plantas_piloto', 'centro_experimental'):
            for codigo in ('REGISTRO-USO', 'PRACTICAS-FT02', 'PRACTICAS-FT03', 'GUIAS'):
                with self.subTest(tipo=tipo, codigo=codigo):
                    self.assertTrue(aplica_documento(self.exigido(codigo), tipo))

    def test_una_asignacion_institucional_explicita_tiene_prioridad(self):
        exigido = self.exigido('PRACTICAS-FT02', tipos_unidad=['observatorios'])
        self.assertTrue(aplica_documento(exigido, 'observatorios'))
        self.assertFalse(aplica_documento(exigido, 'laboratorios'))
        self.assertTrue(aplica_documento(exigido, 'observatorio_economico', base='observatorios'))

    def test_un_documento_personalizado_no_se_oculta_ni_se_renombra(self):
        exigido = self.exigido('PRACTICAS-FT02', nombre='Registro institucional adaptado de proyectos')
        self.assertTrue(aplica_documento(exigido, 'observatorios'))
        self.assertEqual(nombre_para(exigido, self.unidad('observatorios')), exigido.nombre)
        custom = SimpleNamespace(codigo='PROPIO', nombre='Informe propio', fuente_reporte='', tipos_unidad=[])
        self.assertTrue(aplica_documento(custom, 'tipo_nuevo_sin_proveedor'))

    def test_perfil_derivado_reutiliza_la_implementacion_y_no_se_convierte_en_laboratorio(self):
        observatorio = SimpleNamespace(dependencia='observatorio_economico', codigo_base='observatorios')
        self.assertEqual(base_de(observatorio), 'observatorios')
        self.assertTrue(es_unidad_auditable(observatorio))
        self.assertFalse(es_unidad_auditable(self.unidad('centros_id')))
        from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
        self.assertFalse(es_laboratorio(observatorio))

    def test_historia_enviada_o_evaluada_no_desaparece_al_cambiar_el_perfil(self):
        base = dict(exigido=self.exigido('PRACTICAS-FT03'), unidad=self.unidad('observatorios'),
                    estado='pendiente', entregado_en=None, validado_en=None,
                    recibido_en=None, evaluado_en=None, evaluacion=None)
        self.assertFalse(documento_visible(SimpleNamespace(**base)))
        self.assertFalse(documento_visible(SimpleNamespace(**(base | dict(estado='generado', recurso_id=3)))))
        for cambio in (dict(estado='validado'), dict(entregado_en=timezone.now()), dict(evaluacion=0)):
            self.assertTrue(documento_visible(SimpleNamespace(**(base | cambio))))

    def test_cada_tipo_explica_sus_resultados_propio_sin_duplicar_un_formato_de_laboratorio(self):
        for tipo, codigo, palabra in (('observatorios', 'OBS-DATOS', 'Ficha del indicador'),
                                     ('plantas_piloto', 'PP-CALIDAD', 'Parámetros'),
                                     ('centro_experimental', 'CE-ENSAYOS', 'diseño del ensayo')):
            documento = SimpleNamespace(unidad=self.unidad(tipo), exigido=SimpleNamespace(codigo=codigo))
            with self.subTest(tipo=tipo):
                self.assertIn(palabra, ' '.join(requisitos_para(documento)))

    def test_familias_del_observatorio_ofrecen_datos_publicaciones_y_vinculacion(self):
        familias = (('1 · Uso de laboratorios', (('reservas', 'Uso'), ('planificaciones', 'FT02'))),
                    ('3 · Reactivos', (('recursos', 'Recursos'), ('inventario', 'Reactivos'))),
                    ('Bioseguridad', (('seguridad', 'Seguridad'), ('desechos', 'Desechos'))))
        seleccion = familias_de_perfil(self.unidad('observatorios'), familias)
        categorias = {codigo for _, filas in seleccion for codigo, _ in filas}
        self.assertEqual(categorias, {'datos-observatorio', 'boletines', 'eventos', 'reservas', 'recursos'})
        self.assertFalse(any('laboratorio' in nombre.lower() or 'reactivo' in nombre.lower() for nombre, _ in seleccion))

    def test_familias_de_planta_y_campo_muestran_sus_evidencias(self):
        for tipo, codigo in (('plantas_piloto', 'control-calidad'), ('centro_experimental', 'ensayos')):
            categorias = {c for _, filas in familias_de_perfil(self.unidad(tipo), ()) for c, _ in filas}
            self.assertIn(codigo, categorias)

    def test_el_selector_conserva_la_categoria_con_asignacion_explicita(self):
        familias = (('Formatos de prácticas', (('planificaciones', 'FT02'),)),)
        exigido = self.exigido('PRACTICAS-FT02', tipos_unidad=['observatorios'], nombre='Actividad especial')
        seleccion = familias_de_perfil(self.unidad('observatorios'), familias, catalogo=[exigido])
        self.assertIn(('planificaciones', 'Actividad especial'), [f for _, filas in seleccion for f in filas])

    def test_categoria_nativa_con_nombre_personalizado_conserva_su_denominacion(self):
        exigido = SimpleNamespace(codigo='OBS-BOLETINES', nombre='Publicaciones del observatorio regional',
            fuente_reporte='boletines', tipos_unidad=['observatorios'])
        seleccion = familias_de_perfil(self.unidad('observatorios'), (), catalogo=[exigido])
        self.assertIn(('boletines', exigido.nombre), [fila for _, filas in seleccion for fila in filas])

    def test_fuente_de_produccion_aparece_una_vez_con_catalogo_estandar_o_personalizado(self):
        familias = (('Producción genérica', (('produccion', 'Producción genérica'),
                     ('procesos', 'Procesos genéricos'), ('finanzas', 'Consulta financiera'))),)
        catalogo = [SimpleNamespace(codigo=f[0], nombre=f[1], fuente_reporte=f[9],
                    tipos_unidad=TIPOS_CATALOGO_PERFILES[f[0]]) for f in CATALOGO_PERFILES]
        propia = SimpleNamespace(codigo='PRODUCCION-PROPIA', nombre='Producción institucional adaptada',
                                  fuente_reporte='produccion', tipos_unidad=['plantas_piloto'])
        for registros, nombre in ((catalogo, catalogo[0].nombre), (catalogo + [propia], propia.nombre)):
            with self.subTest(nombre=nombre):
                seleccion = familias_de_perfil(self.unidad('plantas_piloto'), familias, catalogo=registros)
                opciones = [fila for _, filas in seleccion for fila in filas]
                self.assertEqual([f for f in opciones if f[0] == 'produccion'], [('produccion', nombre)])
                self.assertIn(('produccion', nombre), seleccion[0][1])
                self.assertIn(('finanzas', 'Consulta financiera'), opciones)
                self.assertEqual(len(opciones), len({f[0] for f in opciones}))

    def test_cada_anexo_nativo_muestra_su_indicador_del_cierre(self):
        from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS, detalle_anexo
        asociaciones = {'PP-PRODUCCION': 'PRODUCCION', 'PP-CALIDAD': 'CONTROL-CALIDAD',
                        'CE-ENSAYOS': 'ENSAYOS', 'OBS-DATOS': 'DATOS-ACTUALIZADOS',
                        'OBS-BOLETINES': 'BOLETINES', 'OBS-EVENTOS': 'EVENTOS'}
        cierre = {'catalogo': [dict(codigo=codigo, nombre=codigo, porcentaje=50, registrado=1,
                                    exigencia='Comprometido en el período') for codigo in asociaciones.values()]}
        for anexo, codigo in asociaciones.items():
            with self.subTest(anexo=anexo):
                self.assertEqual(ANEXOS_METAS[anexo], (codigo,))
                detalle = detalle_anexo(anexo, cierre)
                self.assertEqual([(f['codigo'], f['porcentaje']) for f in detalle], [(codigo, 50)])


class PerfilesDocumentalesPersistidosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad de prueba ' + tipo,
            slug='prueba-perfil-' + tipo, dependencia=tipo, fecha_inicio=date(2025, 1, 1)) for tipo in
            ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')}

    def test_materializar_cada_tipo_con_sus_anexos_y_sin_los_de_otro_perfil(self):
        for tipo, unidad in self.unidades.items():
            codigos = {d.exigido.codigo for d in construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))}
            propios = {'laboratorios': {'PRACTICAS-FT02', 'PRACTICAS-FT03', 'GUIAS'},
                       'plantas_piloto': {'PP-PRODUCCION', 'PP-CALIDAD'},
                       'centro_experimental': {'CE-ENSAYOS'},
                       'observatorios': {'OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS'}}[tipo]
            with self.subTest(tipo=tipo):
                self.assertTrue(propios <= codigos)
                if tipo == 'observatorios':
                    self.assertTrue({'PRACTICAS-FT02', 'PRACTICAS-FT03', 'GUIAS', 'DESECHOS'}.isdisjoint(codigos))
                    self.assertIn('PROTOCOLO-BIOSEGURIDAD', codigos)
                if tipo == 'laboratorios':
                    self.assertFalse(any(c.startswith(('OBS-', 'PP-', 'CE-')) for c in codigos))

    def test_selector_de_planta_lee_catalogo_sin_duplicar_fuentes_ni_escribir(self):
        from apps.gestion_unidades.presentation.gestion_reportes import familias_para
        with CaptureQueriesContext(connection) as consultas:
            familias = familias_para(self.unidades['plantas_piloto'])
        opciones = [fila for _, filas in familias for fila in filas]
        self.assertEqual(sum(codigo == 'produccion' for codigo, _ in opciones), 1)
        self.assertEqual(len(opciones), len({f[0] for f in opciones}))
        escrituras = [q['sql'] for q in consultas if q['sql'].lstrip().split(' ', 1)[0].upper() in
                      ('INSERT', 'UPDATE', 'DELETE')]
        self.assertEqual(escrituras, [])

    def test_lectura_no_escribe_y_no_trae_pendientes_inapropiados_ya_creados(self):
        unidad = self.unidades['observatorios']
        ft = DocumentoExigido.objects.get(codigo='PRACTICAS-FT02')
        viejo = DocumentoExpediente.objects.create(unidad=unidad, exigido=ft, anio=2026, corte='B')
        cantidad = DocumentoExpediente.objects.count()
        documentos = leer_expediente(unidad, 2026, hoy=date(2026, 10, 17))
        self.assertNotIn(viejo.pk, [d.pk for d in documentos])
        self.assertEqual(DocumentoExpediente.objects.count(), cantidad)
        self.assertTrue(DocumentoExpediente.objects.filter(pk=viejo.pk).exists())

    def test_lectura_y_anexos_conservan_el_documento_historico_evaluado(self):
        unidad = self.unidades['observatorios']
        padre = DocumentoExigido.objects.get(codigo='INFORME-SEMESTRAL')
        informe = DocumentoExpediente.objects.create(unidad=unidad, exigido=padre, anio=2026, corte='B')
        ft = DocumentoExigido.objects.get(codigo='PRACTICAS-FT02')
        historico = DocumentoExpediente.objects.create(unidad=unidad, exigido=ft, anio=2026, corte='B',
                                                       estado='observado', evaluacion=0, evaluado_en=timezone.now())
        self.assertIn(historico.pk, [d.pk for d in leer_expediente(unidad, 2026, hoy=date(2026, 10, 17))])
        self.assertIn(historico.pk, [d.pk for d in anexos_del(informe)])

    def test_el_catalogo_explicitamente_personalizado_se_materializa(self):
        ft = DocumentoExigido.objects.get(codigo='PRACTICAS-FT02')
        ft.tipos_unidad = ['observatorios']
        ft.nombre = 'Seguimiento institucional especial'
        ft.save(update_fields=['tipos_unidad', 'nombre'])
        documentos = construir_expediente(self.unidades['observatorios'], 2026, hoy=date(2026, 10, 17))
        self.assertTrue(any(d.exigido_id == ft.pk and d.nombre_documental == ft.nombre for d in documentos))
