"""Catálogos grandes: páginas acotadas, filtros públicos y exportación completa."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import connections, router
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import CasoExito, CentroID, Proyecto, Resultado
from apps.centros_id.presentation.secciones import seccion_view, exportar_resultados_view
from apps.centros_id.selectors_cientificos import filtrar_proyectos, opciones_proyectos


class PaginacionCientificaTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Centro paginado', slug='centro-paginado', proposito='Investigar')
        cls.otro = CentroID.objects.create(nombre='Otro centro', slug='otro-paginado', proposito='Investigar')
        cls.hoy = timezone.localdate()
        Proyecto.objects.bulk_create([Proyecto(centro=cls.centro, titulo='Fabricación Ñ', codigo=f'P{i:03}',
            resumen='Ensayo técnico', inicio=cls.hoy, estado='ejecucion', monto=Decimal('10'), monto_publico=i % 2 == 0)
            for i in range(63)])
        cls.proyecto = cls.centro.proyectos.order_by('pk').first()
        Resultado.objects.bulk_create([Resultado(centro=cls.centro, titulo='Producción Ñ', tipo='dato',
            anio=cls.hoy.year, proyecto=cls.proyecto, sector='Agro', tecnologia='IoT') for _ in range(63)])
        for extras in ({'confidencial': True}, {'publicado': False}, {'es_muestra': True}):
            Resultado.objects.create(centro=cls.centro, titulo='Oculto', tipo='dato', anio=cls.hoy.year, **extras)
        Resultado.objects.create(centro=cls.otro, titulo='Otro centro', tipo='dato', anio=cls.hoy.year)

    def request(self, nombre, parametros=None):
        request = RequestFactory().get(reverse(nombre, args=[self.centro.slug]), parametros or {})
        request.user = AnonymousUser()
        return request

    def seccion(self, clave, **parametros):
        request = RequestFactory().get(reverse('seccion_centro_id', args=[self.centro.slug, clave]), parametros)
        request.user = AnonymousUser()
        with patch('apps.centros_id.presentation.secciones.render', side_effect=lambda r, t, c: c):
            return seccion_view(request, self.centro.slug, clave)

    def test_proyectos_paginas_estables_y_filtros_antes_del_limite(self):
        paginas = [self.seccion('proyectos', pagina=n, estado='ejecucion', q='fabricación ñ') for n in (1, 2, 3)]
        ids = [[p.pk for p in c['proyectos']] for c in paginas]
        self.assertEqual([len(p) for p in ids], [25, 25, 13])
        self.assertEqual(len(set(sum(ids, []))), 63)
        self.assertEqual(sum(ids, []), list(self.centro.proyectos.order_by('pk').values_list('pk', flat=True)))
        self.assertEqual(paginas[1]['coincidencias'], 63)
        self.assertEqual(paginas[1]['financiado'], Decimal('320'))
        self.assertIn('estado=ejecucion', paginas[1]['paginacion']['siguiente_url'])
        self.assertIn('pagina=3', paginas[1]['paginacion']['siguiente_url'])

    def test_produccion_no_materializa_colecciones_completas_y_sql_tiene_limite(self):
        def prohibido(_):
            raise AssertionError('No materializar colecciones completas para servir una página')
        with patch.object(Contenidos, 'resultados', property(prohibido)), \
                patch.object(Contenidos, 'proyectos', property(prohibido)):
            with CaptureQueriesContext(connections[router.db_for_read(CentroID)]) as consultas:
                contexto = self.seccion('produccion', pagina=2)
        self.assertEqual(len(contexto['filtrados']), 25)
        self.assertEqual(contexto['total'], 63)
        self.assertEqual(contexto['c'].resumen_produccion['total'], 63)
        sql = [q['sql'].lower() for q in consultas]
        paginas = [q for q in sql if 'centros_id_resultado' in q and 'limit 25 offset 25' in q]
        self.assertEqual(len(paginas), 1)
        self.assertLess(len(consultas), 22)
        for nombre in ('areas', 'integrantes', 'proyectos', 'resultados'):
            self.assertNotIn(nombre, contexto['c'].__dict__)

    def test_plantilla_real_no_carga_colecciones_completas(self):
        def prohibido(_):
            raise AssertionError('La plantilla no debe cargar el catálogo completo')
        with patch.object(Contenidos, 'resultados', property(prohibido)), \
                patch.object(Contenidos, 'proyectos', property(prohibido)):
            respuesta = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'produccion']), {'pagina': 2})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Página 2 de 3')
        self.assertNotContains(respuesta, 'Oculto')

    def test_exportacion_completa_ignora_pagina_y_conserva_filtros_y_privacidad(self):
        request = self.request('exportar_resultados_centro_id', {'pagina': 2, 'q': 'producción ñ', 'sector': 'Agro'})
        respuesta = exportar_resultados_view(request, self.centro.slug)
        import json
        datos = json.loads(respuesta.content)
        self.assertEqual(datos['total'], 63)
        self.assertEqual(len(datos['resultados']), 63)
        request.GET = request.GET.copy()
        request.GET['formato'] = 'ris'
        respuesta = exportar_resultados_view(request, self.centro.slug)
        self.assertEqual(respuesta.content.decode().count('TY  - '), 63)
        self.assertNotIn('Oculto', respuesta.content.decode())

    def test_filtros_invalidos_no_eliminan_restricciones_ni_generan_errores(self):
        for campo in ('linea', 'proyecto', 'anio', 'trl'):
            for valor in ('abc', '9' * 200, '-1', '١'):
                with self.subTest(campo=campo, valor=valor):
                    self.assertEqual(self.seccion('produccion', **{campo: valor})['total'], 0)
        for valor in ('10000', '9' * 200, '-1'):
            self.assertEqual(self.seccion('proyectos', anio=valor)['coincidencias'], 0)
        self.assertEqual(len(self.seccion('produccion', pagina='incorrecta')['filtrados']), 25)

    def test_busqueda_orm_conserva_acentos_y_continuidad_entre_columnas(self):
        consulta = filtrar_proyectos(self.centro.proyectos.all(), {'q': 'ñ p000 ensayo'})
        self.assertEqual(list(consulta.values_list('pk', flat=True)), [self.proyecto.pk])

    def test_cifras_exigen_evidencia_no_blanca_y_fecha_vigente(self):
        transferencia = Proyecto.objects.create(centro=self.centro, titulo='Transferencia', resumen='Aplicada', estado='transferido')
        caso = CasoExito.objects.create(centro=self.centro, proyecto=transferencia, titulo='Caso', beneficiario='Entidad',
            reto='Necesidad', solucion='Solución', resultado='Adopción', anio=self.hoy.year, receptor='Entidad',
            mecanismo='Convenio', evidencia='Acta', autorizacion_publicacion='Autorización', fecha_transferencia=self.hoy)
        c = Contenidos(self.centro)
        self.assertEqual(c.resumen_proyectos['concluidos'], 1)
        caso.evidencia = ' \t\n'
        caso.save()
        self.assertEqual(Contenidos(self.centro).resumen_proyectos['concluidos'], 0)
        datos = dict(centro=self.centro, titulo='Prototipo', tipo='prototipo', anio=self.hoy.year, trl=7,
                     trl_fecha=self.hoy, trl_evaluador='Comité', trl_alcance='Prueba', trl_evidencia='Acta')
        resultado = Resultado.objects.create(**datos)
        Resultado.objects.create(centro=self.centro, titulo='PI respaldada', tipo='propiedad_intelectual', anio=self.hoy.year,
            estado_pi='solicitada', pi_modalidad='Patente', pi_titular='UPEC', pi_evidencia='Solicitud', pi_fecha=self.hoy)
        Resultado.objects.create(centro=self.centro, titulo='PI futura', tipo='propiedad_intelectual', anio=self.hoy.year,
            estado_pi='concedida', pi_modalidad='Patente', pi_titular='UPEC', pi_evidencia='Acta', pi_fecha=self.hoy + timedelta(days=1))
        c = Contenidos(self.centro)
        self.assertEqual(c.resumen_desarrollos, {'prototipos': 1, 'propiedad': 1, 'trl': 7})
        self.assertEqual(self.seccion('desarrollos', trl='7')['total'], 1)
        resultado.trl_alcance = '\n\t'
        resultado.save()
        self.assertIsNone(Contenidos(self.centro).resumen_desarrollos['trl'])
        self.assertEqual(self.seccion('desarrollos', trl='7')['total'], 0)

    def test_resultado_no_filtra_por_referencia_oculta(self):
        self.proyecto.publicado = False
        self.proyecto.save()
        self.assertEqual(self.seccion('produccion', proyecto=str(self.proyecto.pk))['total'], 0)
        self.assertEqual(self.seccion('produccion')['total'], 63)

    def test_opciones_de_proyectos_acotadas_busqueda_y_seleccion_fuera_de_lista(self):
        Proyecto.objects.bulk_create([Proyecto(centro=self.centro, titulo=f'Agenda {i:03}', resumen='Investigación')
                                     for i in range(210)])
        consulta = self.centro.proyectos.all()
        opciones = opciones_proyectos(consulta, seleccionado=str(self.proyecto.pk))
        self.assertTrue(opciones['hay_mas'])
        self.assertEqual(len(opciones['opciones']), 201)
        self.assertIn(self.proyecto.pk, [o['pk'] for o in opciones['opciones']])
        opciones = opciones_proyectos(consulta, texto='Agenda 209')
        self.assertFalse(opciones['hay_mas'])
        self.assertEqual([o['titulo'] for o in opciones['opciones']], ['Agenda 209'])
        respuesta = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'produccion']))
        self.assertContains(respuesta, 'Buscar proyecto por título')
