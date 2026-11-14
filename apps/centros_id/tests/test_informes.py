"""Reportes científicos: autorización canónica, dos bases y exportación coherente."""
from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connections, router
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.centros_id.informes import CATEGORIAS, construir_reporte_centros, puede_reportar_centros
from apps.centros_id.models import (
    Aliado, CarpetaCentro, CasoExito, CentroID, Componente, DocumentoCentro,
    EquipoCentro, Fase, HitoProyecto, Indicador, Integrante, LineaInvestigacion,
    PartidaPresupuesto, Proyecto, RecursoCentro, Resultado, Servicio,
    SesionAcompanamiento, SolicitudCentro,
)
from apps.centros_id.presentation.informes import informes_view


class InformesCentrosTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.admin = Usuario.objects.create_user('administracion-reportes', is_superuser=True, is_staff=True)
        cls.gestor = Usuario.objects.create_user('gestor-reportes', is_staff=True)
        cls.ajeno = Usuario.objects.create_user('staff-ajeno-reportes', is_staff=True)
        cls.solicitante = Usuario.objects.create_user('PERSONA_RESERVADA', first_name='NOMBRE_RESERVADO')
        cls.centro = CentroID.objects.create(nombre='Centro autorizado A', sigla='CA', slug='reportes-a',
                                             proposito='Investigar', responsable=cls.gestor)
        cls.centro.gestores.add(cls.gestor)  # Una doble asignación no duplica filas.
        cls.segundo = CentroID.objects.create(nombre='Centro autorizado B', sigla='CB', slug='reportes-b', proposito='Investigar')
        cls.segundo.gestores.add(cls.gestor)
        cls.otro = CentroID.objects.create(nombre='CENTRO_NO_AUTORIZADO', slug='reportes-privado', proposito='Investigar')
        cls.inactivo = CentroID.objects.create(nombre='Centro archivado', slug='reportes-inactivo', proposito='Investigar', activo=False)
        cls.hoy = timezone.localdate()
        cls.anio = cls.hoy.year
        cls.proyecto = Proyecto.objects.create(centro=cls.centro, titulo='Proyecto autorizado', resumen='Ciencia',
            inicio=date(cls.anio - 1, 5, 1), fin=date(cls.anio, 5, 1), estado='ejecucion')
        Proyecto.objects.create(centro=cls.segundo, titulo='Otro proyecto autorizado', resumen='Ciencia')
        Proyecto.objects.create(centro=cls.otro, titulo='PROYECTO_NO_AUTORIZADO', resumen='Reservado', inicio=cls.hoy)
        Proyecto.objects.create(centro=cls.centro, titulo='PROYECTO_DEMOSTRATIVO', resumen='Ejemplo', es_muestra=True)
        Resultado.objects.create(centro=cls.centro, titulo='Resultado autorizado', tipo='publicacion', anio=cls.anio)
        Resultado.objects.create(centro=cls.centro, titulo='Resultado anterior', tipo='dato', anio=cls.anio - 1)
        Resultado.objects.create(centro=cls.centro, titulo='RESULTADO_CONFIDENCIAL', anio=cls.anio, confidencial=True)
        Resultado.objects.create(centro=cls.centro, titulo='RESULTADO_DEMOSTRATIVO', anio=cls.anio, es_muestra=True)
        Resultado.objects.create(centro=cls.otro, titulo='RESULTADO_NO_AUTORIZADO', anio=cls.anio)
        cls.solicitud = SolicitudCentro.objects.create(centro=cls.centro, usuario=cls.solicitante,
            tipo='capacitacion', titulo='Capacitación autorizada', problema='DIAGNOSTICO_RESERVADO',
            resultado_esperado='ENTREGABLE_RESERVADO', participantes=6, notas_internas='NOTAS_RESERVADAS')
        cls.solicitud_b = SolicitudCentro.objects.create(centro=cls.segundo, usuario=cls.solicitante,
            tipo='servicio', titulo='Servicio autorizado', problema='Necesidad', resultado_esperado='Entrega')
        SolicitudCentro.objects.create(centro=cls.otro, usuario=cls.solicitante,
            titulo='SOLICITUD_NO_AUTORIZADA', problema='Privado', resultado_esperado='Privado', participantes=99)
        cls.integrante = Integrante.objects.create(centro=cls.centro, nombre='PERSONA_CIENTIFICA_RESERVADA', rol='investigador')

    def reporte(self, categoria='resumen', usuario=None, **filtros):
        return construir_reporte_centros(usuario or self.gestor, {'categoria': categoria, **filtros})

    def metrica(self, reporte, clave):
        return next(m['valor'] for m in reporte['metrics'] if m['clave'] == clave)

    def peticion(self, parametros=None, usuario=None, metodo='get'):
        request = getattr(RequestFactory(), metodo)(reverse('reportes_centros_id'), parametros or {})
        request.user = usuario if usuario is not None else self.gestor
        return request

    def test_scope_canonico_global_y_asignaciones_sin_duplicacion(self):
        informe = self.reporte()
        self.assertEqual(self.metrica(informe, 'centros'), 2)
        self.assertEqual([f[0] for f in informe['sections'][0]['rows']], [self.centro.nombre, self.segundo.nombre])
        self.assertFalse(informe['macro'])
        macro = self.reporte(usuario=self.admin)
        self.assertEqual(self.metrica(macro, 'centros'), 4)
        self.assertTrue(macro['macro'])
        self.assertIn('Centro archivado', str(macro['sections']))

    def test_staff_modelpermission_y_proyeccion_no_otorgan_acceso(self):
        for persona in (AnonymousUser(), self.ajeno, self.centro.responsable,
                        SimpleNamespace(is_authenticated=True, pk=self.admin.pk, is_superuser=True)):
            with self.subTest(tipo=type(persona).__name__):
                self.assertFalse(puede_reportar_centros(persona))
                with self.assertRaises(PermissionDenied):
                    construir_reporte_centros(persona)

    def test_baja_y_revocacion_se_aplican_a_objeto_y_sesion_anteriores(self):
        get_user_model().objects.filter(pk=self.gestor.pk).update(is_active=False)
        self.assertFalse(puede_reportar_centros(self.gestor))
        with self.assertRaises(PermissionDenied):
            self.reporte()

    def test_superuser_revocado_no_conserva_alcance_macro(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_superuser=False)
        with self.assertRaises(PermissionDenied):
            self.reporte(usuario=self.admin)

    def test_gestor_sin_staff_puede_reportar_y_quitar_asignaciones_revoca_acceso(self):
        get_user_model().objects.filter(pk=self.gestor.pk).update(is_staff=False)
        self.gestor.refresh_from_db()
        self.assertTrue(puede_reportar_centros(self.gestor))
        self.assertEqual(self.reporte()['pagination']['count'], 2)
        CentroID.objects.filter(pk=self.centro.pk).update(responsable_id=None)
        self.centro.gestores.remove(self.gestor)
        self.segundo.gestores.remove(self.gestor)
        self.assertFalse(puede_reportar_centros(self.gestor))

    def test_filtros_invalidos_o_centro_ajeno_fallan_sin_ampliar_scope(self):
        for filtros in ({'centro': str(self.otro.pk)}, {'centro': '9' * 200}, {'anio': '-1'},
                        {'anio': '10000'}, {'anio': 'texto'}, {'categoria': 'desconocida'}, {'q': 'x' * 201}):
            with self.subTest(filtros=filtros), self.assertRaises(ValidationError):
                construir_reporte_centros(self.gestor, filtros)

    def test_anio_respeta_fecha_proyectos_y_precision_anual_resultados(self):
        proyectos = self.reporte('proyectos', anio=str(self.anio))
        self.assertEqual(self.metrica(proyectos, 'proyectos'), 1)
        self.assertEqual(proyectos['sections'][0]['rows'][0][2], 'Proyecto autorizado')
        resultados = self.reporte('produccion', anio=str(self.anio))
        self.assertEqual(self.metrica(resultados, 'resultados'), 1)
        self.assertEqual(resultados['sections'][0]['rows'][0][1], 'Resultado autorizado')
        with self.settings(DEBUG=True, CENTROS_ID_ESCENARIOS_OPERATIVOS=(self.centro.slug,)):
            self.assertEqual(self.metrica(self.reporte('produccion', anio=str(self.anio)), 'resultados'), 1)

    def test_busqueda_vacia_en_centro_elegido_conserva_scope_y_exporta_sin_filas(self):
        filtros = {'categoria': 'resumen', 'centro': str(self.centro.pk), 'q': 'SIN_COINCIDENCIAS_QA'}
        for usuario in (self.gestor, self.admin):
            with self.subTest(usuario=usuario.username):
                informe = construir_reporte_centros(usuario, filtros)
                exportado = construir_reporte_centros(usuario, filtros, exportar=True)
                self.assertEqual(informe['scope'], self.centro.nombre)
                self.assertEqual(informe['pagination']['count'], 0)
                self.assertEqual(informe['sections'][0]['rows'], [])
                self.assertEqual(exportado['scope'], informe['scope'])
                self.assertEqual(exportado['sections'], informe['sections'])
                self.assertEqual(self.metrica(informe, 'proyectos'), 0)
                self.assertEqual(informes_view(self.peticion(filtros, usuario=usuario)).status_code, 200)
                for formato in ('pdf', 'docx', 'xlsx'):
                    respuesta = informes_view(self.peticion({**filtros, 'formato': formato}, usuario=usuario))
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertIn('no-store', respuesta['Cache-Control'])

    def test_transferencia_y_pi_trl_requieren_evidencia_y_fecha_no_futura(self):
        base = dict(centro=self.centro, titulo='Transferencia', beneficiario='Entidad', reto='Reto', solucion='Solución',
            resultado='Adopción', anio=self.anio, receptor='Entidad', mecanismo='Convenio', evidencia='Acta',
            autorizacion_publicacion='Autorización', fecha_transferencia=self.hoy)
        CasoExito.objects.create(**base)
        CasoExito.objects.create(**{**base, 'evidencia': ' \t\n'})
        CasoExito.objects.create(**{**base, 'fecha_transferencia': self.hoy + timedelta(days=1)})
        self.assertEqual(self.metrica(self.reporte('transferencias'), 'transferencias'), 1)
        self.assertEqual(self.metrica(self.reporte('transferencias'), 'impacto'), 0)
        Resultado.objects.create(centro=self.centro, titulo='Prototipo documentado', tipo='prototipo', anio=self.anio,
            trl=6, trl_fecha=self.hoy, trl_evaluador='Comité', trl_alcance='Prueba', trl_evidencia='Acta')
        Resultado.objects.create(centro=self.centro, titulo='Patente futura', tipo='propiedad_intelectual', anio=self.anio,
            estado_pi='concedida', pi_modalidad='Patente', pi_titular='UPEC', pi_evidencia='Acta', pi_fecha=self.hoy + timedelta(days=1))
        produccion = self.reporte('produccion')
        self.assertEqual(self.metrica(produccion, 'trl'), 1)
        self.assertEqual(self.metrica(produccion, 'pi'), 0)

    def test_formacion_no_confunde_solicitudes_con_cursos_aprobados(self):
        informe = self.reporte('formacion')
        self.assertEqual(self.metrica(informe, 'solicitudes'), 1)
        self.assertEqual(self.metrica(informe, 'participantes'), 6)
        self.assertEqual(self.metrica(informe, 'entregadas'), 0)
        self.assertIn('no acreditan asistencia, aprobación', ' '.join(informe['notes']))
        self.assertNotIn('PERSONA_RESERVADA', str(informe))

    def test_consulta_minima_no_lee_notas_expediente_ni_otras_categorias(self):
        alias = router.db_for_read(CentroID)
        with CaptureQueriesContext(connections[alias]) as consultas:
            informe = self.reporte('servicios', q='Servicio autorizado')
        self.assertEqual(self.metrica(informe, 'solicitudes'), 1)
        sql = '\n'.join(c['sql'].lower() for c in consultas)
        for campo in ('"notas_internas"', '"diagnostico"', '"problema"', '"resultado_esperado"'):
            self.assertNotIn(campo, sql)
        self.assertNotIn('centros_id_resultado', sql)
        self.assertNotIn('centros_id_proyecto', sql)
        for reservado in ('NOMBRE_RESERVADO', 'NOTAS_RESERVADAS', 'DIAGNOSTICO_RESERVADO', 'ENTREGABLE_RESERVADO'):
            self.assertNotIn(reservado, str(informe))

    def test_paginacion_sql_exportacion_completa_y_limite_explicito(self):
        Proyecto.objects.bulk_create([Proyecto(centro=self.centro, titulo=f'Paginado {i:03}', resumen='Investigación') for i in range(63)])
        alias = router.db_for_read(CentroID)
        with CaptureQueriesContext(connections[alias]) as consultas:
            pagina = self.reporte('proyectos', q='Paginado', pagina='2')
        self.assertEqual(len(pagina['sections'][0]['rows']), 25)
        self.assertEqual(pagina['pagination']['count'], 63)
        self.assertTrue(any('LIMIT 25 OFFSET 25' in c['sql'] for c in consultas))
        self.assertLess(len(consultas), 13)
        completo = construir_reporte_centros(self.gestor, {'categoria': 'proyectos', 'q': 'Paginado', 'pagina': 2}, exportar=True)
        self.assertEqual(len(completo['sections'][0]['rows']), 63)
        with patch('apps.centros_id.informes.MAX_EXPORTACION', 20), self.assertRaises(ValidationError):
            construir_reporte_centros(self.gestor, {'categoria': 'proyectos', 'q': 'Paginado'}, exportar=True)

    def test_catalogos_todos_rinden_con_scope_y_celdas_consistentes(self):
        for categoria, _ in CATEGORIAS:
            with self.subTest(categoria=categoria):
                informe = self.reporte(categoria)
                self.assertNotIn('CENTRO_NO_AUTORIZADO', str(informe))
                for seccion in informe['sections']:
                    self.assertTrue(all(len(f) == len(seccion['headers']) for f in seccion['rows']))
                self.assertTrue(all('periodo' in m and 'scope' in m for m in informe['metrics']))

    def test_centros_homonimos_no_se_fusionan_en_agregados_y_exportaciones(self):
        CentroID.objects.filter(pk=self.segundo.pk).update(nombre=self.centro.nombre)
        Integrante.objects.create(centro=self.segundo, nombre='Otra persona', rol=self.integrante.rol,
                                  vigente=self.integrante.vigente)
        for categoria in ('equipo', 'seguridad'):
            with self.subTest(categoria=categoria):
                parametros = {'categoria': categoria}
                informe = construir_reporte_centros(self.gestor, parametros)
                exportado = construir_reporte_centros(self.gestor, parametros, exportar=True)
                filas = informe['sections'][0]['rows']
                self.assertEqual(informe['pagination']['count'], 2)
                self.assertEqual(filas, exportado['sections'][0]['rows'])
                self.assertEqual({fila[1] for fila in filas}, {self.centro.pk, self.segundo.pk})
                self.assertEqual([fila[0] for fila in filas], [self.centro.nombre] * 2)
                self.assertEqual([fila[-1] for fila in filas], [1, 1])

    def test_catalogos_poblados_renderizan_datos_y_resumenes_sin_contenido_reservado(self):
        HitoProyecto.objects.create(proyecto=self.proyecto, titulo='Hito técnico', fecha_prevista=self.hoy)
        Componente.objects.create(centro=self.centro, codigo='capacidad', nombre='Capacidad técnica', tipo='division', resumen='Ciencia')
        Aliado.objects.create(centro=self.centro, nombre='Entidad colaboradora', tipo='Empresa', pais='Ecuador')
        DocumentoCentro.objects.create(centro=self.centro, titulo='Documento interno QA', tipo='informe',
                                      fecha=self.hoy, publico=False)
        carpeta = CarpetaCentro.objects.create(centro=self.centro, nombre='Carpeta interna QA', visibilidad='interna')
        RecursoCentro.objects.create(carpeta=carpeta, titulo='Recurso interno QA', texto='CONTENIDO_INTERNO_RESERVADO')
        Fase.objects.create(centro=self.centro, numero=1, nombre='Fase técnica', horizonte='Plan actual')
        PartidaPresupuesto.objects.create(centro=self.centro, concepto='Inversión referencial', monto=10)
        Indicador.objects.create(centro=self.centro, categoria='Ciencia', nombre='Valor registrado QA', medicion='Conteo', valor=3)
        Servicio.objects.create(centro=self.centro, nombre='Servicio de medición', linea='Metrología',
                                descripcion='Medición', entregable='Informe')
        muestras = {'hitos': 'Hito técnico', 'capacidades': 'Capacidad técnica',
                    'colaboracion': 'Entidad colaboradora', 'repositorio': 'Documento interno QA',
                    'planificacion': 'Fase técnica', 'indicadores': 'Valor registrado QA',
                    'portafolio': 'Servicio de medición'}
        for categoria, esperado in muestras.items():
            with self.subTest(categoria=categoria):
                informe = self.reporte(categoria)
                self.assertIn(esperado, str(informe['sections']))
                self.assertNotIn('CONTENIDO_INTERNO_RESERVADO', str(informe))
                respuesta = informes_view(self.peticion({'categoria': categoria}))
                self.assertContains(respuesta, esperado)
        self.assertEqual(self.metrica(self.reporte('planificacion'), 'monto'), 10)
        self.assertEqual(self.metrica(self.reporte('repositorio'), 'recursos'), 1)

    def test_filtros_de_estado_y_tipo_coinciden_en_metricas_y_exportacion(self):
        tipo = {'categoria': 'produccion', 'tipo_resultado': 'publicacion'}
        informe = construir_reporte_centros(self.gestor, tipo)
        self.assertEqual(self.metrica(informe, 'resultados'), 1)
        self.assertEqual(len(informe['sections'][0]['rows']), 1)
        self.assertIn(('Tipo de resultado', 'Publicación'), informe['filter_summary'])
        libro = load_workbook(BytesIO(informes_view(self.peticion({**tipo, 'formato': 'xlsx'})).content))
        self.assertEqual(len(list(libro.worksheets[-1].values)), 2)
        self.assertEqual(self.reporte('proyectos', estado='ejecucion')['pagination']['count'], 1)
        self.assertEqual(self.reporte('servicios', estado='recibida')['pagination']['count'], 2)
        with self.assertRaises(ValidationError):
            self.reporte('proyectos', estado='operativo')

    def test_inventario_no_convierte_cantidad_en_activos_individuales(self):
        componente = Componente.objects.create(centro=self.centro, codigo='inventario', nombre='Área', tipo='division', resumen='Capacidades')
        EquipoCentro.objects.create(componente=componente, nombre='Equipos agrupados', categoria='Medición', cantidad=7)
        EquipoCentro.objects.create(componente=componente, nombre='Ejemplo', categoria='Medición', cantidad=90, es_muestra=True)
        informe = self.reporte('equipamiento', anio=str(self.anio - 10))
        self.assertEqual(self.metrica(informe, 'equipos'), 1)
        self.assertEqual(self.metrica(informe, 'unidades'), 7)
        self.assertIn('no se filtra por año', ' '.join(informe['notes']))

    def test_referencia_inconsistente_no_revela_linea_de_otro_centro(self):
        linea = LineaInvestigacion.objects.create(centro=self.otro, nombre='LINEA_NO_AUTORIZADA', resultados='Reservado')
        Proyecto.objects.filter(pk=self.proyecto.pk).update(linea=linea)
        self.assertNotIn('LINEA_NO_AUTORIZADA', str(self.reporte('proyectos')))

    def test_agenda_no_exporta_nombres_acuerdos_o_notas(self):
        SesionAcompanamiento.objects.bulk_create([SesionAcompanamiento(solicitud=self.solicitud,
            responsable=self.integrante, inicio=timezone.now(), fin=timezone.now() + timedelta(hours=1),
            modalidad='Presencial', estado='realizada', acuerdos='ACUERDOS_RESERVADOS', notas_internas='NOTAS_RESERVADAS')])
        informe = self.reporte('agenda')
        self.assertEqual(self.metrica(informe, 'realizadas'), 1)
        for texto in ('PERSONA_CIENTIFICA_RESERVADA', 'ACUERDOS_RESERVADOS', 'NOTAS_RESERVADAS'):
            self.assertNotIn(texto, str(informe))
        self.assertRegex(informe['sections'][0]['rows'][0][2], r'\d{2}:\d{2}')

    def test_endpoint_autenticacion_metodos_y_errores_no_amplian_filtros(self):
        self.assertEqual(informes_view(self.peticion(usuario=AnonymousUser())).status_code, 302)
        self.assertEqual(informes_view(self.peticion(metodo='post')).status_code, 405)
        self.assertEqual(informes_view(self.peticion({'formato': 'desconocido'})).status_code, 400)
        self.assertEqual(informes_view(self.peticion({'centro': self.otro.pk})).status_code, 400)
        with self.assertRaises(PermissionDenied):
            informes_view(self.peticion({'formato': 'xlsx'}, usuario=self.ajeno))

    def test_exportaciones_mismo_scope_totales_y_texto_literal(self):
        Proyecto.objects.create(centro=self.centro, titulo='=SUM(1,2)', resumen='Texto editable')
        parametros = {'categoria': 'proyectos', 'centro': self.centro.pk}
        html = self.reporte('proyectos', centro=str(self.centro.pk))
        xlsx = informes_view(self.peticion({**parametros, 'formato': 'xlsx'}))
        self.assertIn('private', xlsx['Cache-Control'])
        self.assertIn('no-store', xlsx['Cache-Control'])
        libro = load_workbook(BytesIO(xlsx.content), data_only=False)
        filas = list(libro.worksheets[-1].values)
        self.assertEqual(len(filas) - 1, html['pagination']['count'])
        self.assertNotIn('PROYECTO_NO_AUTORIZADO', str(filas))
        literal = next(c for fila in libro.worksheets[-1] for c in fila if c.value == '=SUM(1,2)')
        self.assertEqual(literal.data_type, 's')
        docx = informes_view(self.peticion({**parametros, 'formato': 'docx'}))
        with ZipFile(BytesIO(docx.content)) as archivo:
            texto = archivo.read('word/document.xml').decode()
        self.assertIn('Proyecto autorizado', texto)
        self.assertNotIn('PROYECTO_NO_AUTORIZADO', texto)
        pdf = informes_view(self.peticion({**parametros, 'formato': 'pdf', 'descargar': '0'}))
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertTrue(pdf['Content-Disposition'].startswith('inline;'))

    def test_plantilla_real_y_enlaces_estan_disponibles_sin_privilegios_globales(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.get(reverse('reportes_centros_id'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Descargar Excel')
        self.assertContains(respuesta, 'Centro autorizado A')
        self.assertNotContains(respuesta, 'CENTRO_NO_AUTORIZADO')
        self.assertIn('no-cache', respuesta['Cache-Control'])
        cabecera = self.client.head(reverse('reportes_centros_id'))
        self.assertEqual(cabecera.status_code, 200)
        self.assertEqual(cabecera.content, b'')

    def test_multibase_consulta_centros_en_su_alias_y_auth_en_canonico(self):
        alias = router.db_for_read(CentroID)
        if alias == 'default':
            self.assertEqual(self.reporte('proyectos')['pagination']['count'], 2)
            return
        with CaptureQueriesContext(connections['default']) as central, CaptureQueriesContext(connections[alias]) as local:
            informe = self.reporte('produccion')
        self.assertEqual(self.metrica(informe, 'resultados'), 2)
        self.assertFalse(any('centros_id_' in q['sql'].lower() for q in central))
        self.assertFalse(any('auth_user' in q['sql'].lower() or 'webcitt_' in q['sql'].lower() for q in local))
        self.assertTrue(any('centros_id_resultado' in q['sql'].lower() for q in local))
        self.assertTrue(any('auth_user' in q['sql'].lower() for q in central))
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in [*central, *local]))
