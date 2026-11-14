"""Portada de Logística: relaciones explícitas, lectura acotada y publicación."""
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.laboratorios.operacion.presentation.logistica_presentacion import logistica_identidad_view
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.asignaturas import Asignatura
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.presentacion import PresentacionUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class LogisticaPresentacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            slug=SLUG, nombre='Laboratorio de Logística, Transporte y Cadena de Suministro',
            dependencia='laboratorios', descripcion='Operaciones logísticas', fecha_inicio=date(2026, 1, 1),
        )
        cls.otra = Unidad.objects.create(
            slug='logistica-otra', nombre='Información de otra unidad', dependencia='laboratorios',
            descripcion='Otra unidad', fecha_inicio=date(2026, 1, 1),
        )
        cls.gestor = get_user_model().objects.create_superuser('logistica-presentacion-admin', 'admin@example.org', 'clave')
        cls.areas = {}
        for orden, (codigo, datos) in enumerate(AREAS.items()):
            area = EspacioReservable.objects.create(
                unidad=cls.unidad, codigo=codigo, nombre=datos['nombre'], orden=orden,
                descripcion_publica='Aplicaciones docentes del área ' + codigo,
            )
            cls.areas[codigo] = area
        cls.almacen = cls.areas['LOG-ALMACEN']
        cls.area_inactiva = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='LOG-AREA-ANTERIOR', nombre='Área retirada confidencial', activo=False,
        )
        FichaArea.objects.create(espacio=cls.almacen, publicada=True, que_es='Recepción y almacenamiento con trazabilidad.',
                                 aplicaciones='Competencia: Explicar el flujo de recepción.\nIndicador: Exactitud del inventario.\nPráctica: Recepción con trazabilidad.')
        FichaArea.objects.create(
            espacio=cls.areas['LOG-AREA-ERP'], publicada=False, que_es='BORRADOR_PRIVADO_DE_FICHA',
        )
        PresentacionUnidad.objects.create(unidad=cls.unidad, publicada=False, lema='BORRADOR_PRIVADO_DE_PRESENTACION')
        cls.rutas = Asignatura.objects.create(
            unidad=cls.unidad, codigo='LOGT-DISENO-DE-RUTAS', nombre='Diseño de rutas', carrera='Logística y Transporte',
            semestre='Semestre 6', descripcion='Se practica en el área «Transporte, distribución y movilidad». Fuente: malla.',
        )
        cls.legada = Asignatura.objects.create(
            unidad=cls.unidad, codigo='LOG-LEGADA', nombre='Inventarios con denominación anterior', carrera='Comercio Exterior',
            descripcion='Se practica en el área «Almacenamiento e inventarios inteligentes». Fuente: malla.',
        )
        cls.sin_area = Asignatura.objects.create(
            unidad=cls.unidad, codigo='LOG-SIN-AREA', nombre='Taller libre de transporte', carrera='Administración de Empresas',
            descripcion='Esta actividad no declara asociación de área.',
        )
        Asignatura.objects.bulk_create([
            Asignatura(unidad=cls.unidad, codigo=f'LOG-ESCALA-{n:03}', nombre=f'Práctica de inventarios {n:03}',
                       carrera='Logística y Transporte', descripcion=f'Se practica en el área «{cls.almacen.nombre}».')
            for n in range(24)
        ])
        Asignatura.objects.create(unidad=cls.unidad, codigo='LOG-PRIVADA', nombre='Asignatura inactiva confidencial', activa=False)
        Asignatura.objects.create(unidad=cls.otra, codigo='LOG-AJENA', nombre='Asignatura ajena confidencial')
        base = EquiposServicios.objects.create(codigo='LOG-PRES-LECTOR', nombre='Lector para pruebas')
        cls.verificado = UnidadEquipo.objects.create(
            laboratorio=cls.unidad, equipo=base, codigo_unidad='LOG-PRES-01', existencia_verificada=True,
            numero_serie='SERIE_PATRIMONIAL_PRIVADA', custodio='CUSTODIO_PRIVADO',
        )
        cls.verificado.laboratorios.add(cls.unidad)
        UnidadEquipo.objects.create(laboratorio=cls.unidad, equipo=base, codigo_unidad='LOG-PRES-02', existencia_verificada=False)
        UnidadEquipo.objects.create(laboratorio=cls.otra, equipo=base, codigo_unidad='LOG-PRES-AJENO', existencia_verificada=True)
        programa = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Software registrado', activo=True)
        programa.equipos_instalados.add(cls.verificado)
        SoftwareDisponible.objects.create(unidad=cls.otra, nombre='Software ajeno confidencial', activo=True)

    @property
    def url(self):
        return reverse('logistica_identidad', args=[SLUG])

    def solicitud(self, parametros=None):
        request = RequestFactory().get(self.url, parametros or {})
        request.user = AnonymousUser()
        return request

    def test_portada_muestra_seis_areas_tres_carreras_y_matriz_paginada(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(len(respuesta.context['areas_logistica']), 6)
        self.assertEqual(respuesta.context['total_asignaturas'], 27)
        self.assertEqual(len(respuesta.context['carreras_logistica']), 3)
        self.assertEqual(len(respuesta.context['matriz_logistica']), 12)
        self.assertEqual(respuesta.context['pagina_matriz'].paginator.num_pages, 3)
        self.assertContains(respuesta, reverse('logistica_juego_cerveza', args=[SLUG]))
        self.assertContains(respuesta, 'Evidencia que desarrollas')

    def test_asociacion_academica_solo_sale_del_registro_explicito(self):
        respuesta = self.client.get(self.url, {'q': self.sin_area.nombre})
        fila = respuesta.context['matriz_logistica'][0]
        self.assertIsNone(fila['area'])
        self.assertContains(respuesta, 'Sin área vinculada en el registro')
        self.assertNotContains(respuesta, reverse('area_unidad', args=[SLUG, 'LOG-AREA-TMS']) + '">Transporte')

    def test_denominacion_historica_apunta_al_area_vigente_sin_alterar_datos(self):
        respuesta = self.client.get(self.url, {'q': self.legada.nombre, 'area': self.almacen.codigo})
        fila = respuesta.context['matriz_logistica'][0]
        self.assertEqual(fila['area'].pk, self.almacen.pk)
        self.legada.refresh_from_db()
        self.assertIn('Almacenamiento e inventarios inteligentes', self.legada.descripcion)

    def test_filtros_combinados_usan_carrera_area_y_nombre(self):
        respuesta = self.client.get(self.url, {'carrera': 'Logística y Transporte', 'area': 'LOG-AREA-TMS', 'q': 'rutas'})
        self.assertEqual([fila['asignatura'].pk for fila in respuesta.context['matriz_logistica']], [self.rutas.pk])
        self.assertEqual(respuesta.context['pagina_matriz'].paginator.count, 1)
        self.assertTrue(respuesta.context['matriz_logistica'][0]['orientacion'].get('evidencia'))

    def test_paginacion_conserva_filtros_y_no_repite_registros(self):
        ids = []
        for numero in range(1, 4):
            respuesta = self.client.get(self.url, {'area': self.almacen.codigo, 'pagina': numero})
            ids.extend(fila['asignatura'].pk for fila in respuesta.context['matriz_logistica'])
            self.assertIn('area=LOG-ALMACEN', respuesta.context['consulta_matriz'])
        self.assertEqual(len(ids), 25)
        self.assertEqual(len(set(ids)), 25)

    def test_filtros_invalidos_y_paginas_extremas_no_producen_error(self):
        for pagina in ('x', '-1', '9' * 500, '١٢', '999999'):
            with self.subTest(pagina=pagina):
                respuesta = self.client.get(self.url, {'pagina': pagina, 'area': 'AJENA', 'carrera': 'AJENA'})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['filtros_logistica']['area'], '')
                self.assertEqual(respuesta.context['filtros_logistica']['carrera'], '')
        respuesta = self.client.get(self.url, {'q': 'a' * 300 + '\x00'})
        self.assertEqual(len(respuesta.context['filtros_logistica']['q']), 120)

    def test_filtros_se_escapan_en_la_plantilla(self):
        respuesta = self.client.get(self.url, {'q': '<script>alert(1)</script>'})
        self.assertNotContains(respuesta, '<script>alert(1)</script>')
        self.assertContains(respuesta, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_no_expone_borradores_areas_retiradas_ni_datos_patrimoniales(self):
        respuesta = self.client.get(self.url)
        for texto in ('BORRADOR_PRIVADO_DE_FICHA', 'BORRADOR_PRIVADO_DE_PRESENTACION',
                      'Área retirada confidencial', 'Asignatura inactiva confidencial', 'Asignatura ajena confidencial',
                      'Software ajeno confidencial', 'SERIE_PATRIMONIAL_PRIVADA', 'CUSTODIO_PRIVADO'):
            self.assertNotContains(respuesta, texto)
        equipos = respuesta.context['equipos_logistica']
        self.assertEqual((equipos['registrados'], equipos['verificados'], equipos['operativos_verificados']), (2, 1, 1))
        self.assertEqual(respuesta.context['software_logistica']['registrados'], 1)
        self.assertContains(respuesta, 'La asociación no acredita instalación vigente')

    def test_url_directa_respeta_modulo_desactivado_y_permiso_de_revision(self):
        self.unidad.modulos_contenido.filter(clave='informacion-general').update(activo=False)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_url_directa_respeta_seccion_oculta(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='1.3', oculta=True)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_unidad_inactiva_no_es_publica(self):
        self.unidad.activo = False
        self.unidad.save(update_fields=['activo'])
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_otra_unidad_no_abre_la_portada_ni_hace_consultas(self):
        with self.assertNumQueries(0):
            with self.assertRaises(Http404):
                logistica_identidad_view(self.solicitud(), self.otra.slug)

    def test_get_no_escribe_ni_carga_el_panel_o_reservas(self):
        with CaptureQueriesContext(connection) as consultas:
            respuesta = logistica_identidad_view(self.solicitud(), SLUG)
        self.assertEqual(respuesta.status_code, 200)
        for consulta in consultas:
            sql = consulta['sql'].lstrip().upper()
            self.assertFalse(sql.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER')))
            self.assertNotIn('FROM "WEBCITT_RESERVA"', sql)
            self.assertNotIn('FROM "WEBCITT_CURSO"', sql)
        self.assertLessEqual(len(consultas), 16)

    def test_consultas_no_crecen_con_el_numero_de_asignaturas(self):
        logistica_identidad_view(self.solicitud(), SLUG)
        with CaptureQueriesContext(connection) as antes:
            logistica_identidad_view(self.solicitud(), SLUG)
        Asignatura.objects.bulk_create([
            Asignatura(unidad=self.unidad, codigo=f'LOG-MAS-{n}', nombre=f'Escenario ampliado {n}') for n in range(80)
        ])
        with CaptureQueriesContext(connection) as despues:
            respuesta = logistica_identidad_view(self.solicitud(), SLUG)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(antes), len(despues))
        self.assertLessEqual(len(despues), 16)

    def test_post_no_admite_mutaciones(self):
        self.assertEqual(self.client.post(self.url, {'activo': 'false'}).status_code, 405)
        self.unidad.refresh_from_db()
        self.assertTrue(self.unidad.activo)

    def test_editar_ficha_publicada_actualiza_competencias_sin_actualizar_codigo(self):
        FichaArea.objects.filter(espacio=self.almacen).update(
            aplicaciones='Competencia: Contenido docente editado.\nIndicador: Indicador editado.\nPráctica: Experimento editado.',
        )
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'Contenido docente editado.')
        self.assertContains(respuesta, 'Indicador editado.')
        self.assertContains(respuesta, 'Experimento editado.')
        self.assertNotContains(respuesta, 'Explicar el flujo de recepción.')

    def test_ficha_manual_sin_prefijos_no_recibe_competencias_inventadas(self):
        FichaArea.objects.filter(espacio=self.almacen).update(aplicaciones='Aplicación propia de la unidad.')
        respuesta = self.client.get(self.url)
        almacen = next(item for item in respuesta.context['areas_logistica'] if item['espacio'].pk == self.almacen.pk)
        self.assertEqual(almacen['competencias'], [])
        self.assertEqual(almacen['indicadores'], [])
        self.assertEqual(almacen['practicas'], [])

    def test_portada_no_enlaza_simulador_con_modulo_docente_desactivado(self):
        self.unidad.modulos_contenido.filter(clave='docencia-capacitacion').update(activo=False)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['juego_cerveza_url'], '')
        self.assertNotContains(respuesta, reverse('logistica_juego_cerveza', args=[SLUG]))
        self.assertNotContains(respuesta, 'Abrir el simulador')

    def test_portada_no_enlaza_simulador_con_seccion_de_aprendizaje_oculta(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='4.4', oculta=True)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['juego_cerveza_url'], '')
        self.assertNotContains(respuesta, reverse('logistica_juego_cerveza', args=[SLUG]))
        self.client.force_login(self.gestor)
        self.assertNotContains(self.client.get(self.url), 'Abrir el simulador')

    def test_ocultar_matriz_evita_consultas_datos_filtros_y_metricas_academicas(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='4.2', oculta=True)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url, {'q': 'rutas'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['matriz_logistica'], [])
        self.assertEqual(respuesta.context['carreras_logistica'], [])
        self.assertIsNone(respuesta.context['total_asignaturas'])
        self.assertIsNone(respuesta.context['pagina_matriz'])
        self.assertFalse(any('webcitt_asignatura' in item['sql'].lower() for item in consultas))
        self.assertNotContains(respuesta, 'id="matriz"')
        self.assertNotContains(respuesta, 'asignaturas vinculadas')
        self.assertNotContains(respuesta, 'Ver sus asignaturas')
        self.assertNotContains(respuesta, self.rutas.codigo)
        self.client.force_login(self.gestor)
        self.assertNotContains(self.client.get(self.url), 'id="matriz"')

    def test_ocultar_areas_evita_consultas_a_areas_fichas_y_enlaces_de_matriz(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='2.1', oculta=True)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url, {'area': self.almacen.codigo})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['areas_logistica'], [])
        self.assertEqual(respuesta.context['filtros_logistica']['area'], '')
        for tabla in ('webcitt_espacioreservable', 'webcitt_fichaarea'):
            self.assertFalse(any(tabla in item['sql'].lower() for item in consultas))
        for texto in ('id="areas"', 'id="sistema"', 'id="logistica-area"', 'Área vinculada', 'áreas activas'):
            self.assertNotContains(respuesta, texto)
        self.assertEqual(len(respuesta.context['matriz_logistica']), 12)
        self.assertTrue(all(fila['area'] is None for fila in respuesta.context['matriz_logistica']))
        self.assertNotContains(respuesta, reverse('area_unidad', args=[SLUG, self.almacen.codigo]))

    def test_ocultar_equipos_evita_consultas_y_conteos_del_inventario(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='2.2', oculta=True)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url)
        self.assertIsNone(respuesta.context['equipos_logistica'])
        self.assertFalse(any('from "webcitt_unidadequipo"' in item['sql'].lower() for item in consultas))
        self.assertNotContains(respuesta, 'Equipamiento activo registrado')
        self.assertNotContains(respuesta, 'id="logistica-verificacion"')

    def test_ocultar_software_evita_consultas_y_conteos_de_plataformas(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='2.3', oculta=True)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url)
        self.assertIsNone(respuesta.context['software_logistica'])
        self.assertFalse(any('webcitt_softwaredisponible' in item['sql'].lower() for item in consultas))
        self.assertNotContains(respuesta, 'Software activo registrado')
        self.assertNotContains(respuesta, reverse('software_unidad', args=[SLUG]))

    def test_modulos_ocultos_impiden_carga_de_tablas_dependientes_incluso_para_gestor(self):
        self.unidad.modulos_contenido.filter(clave__in=['areas-equipos', 'docencia-capacitacion']).update(activo=False)
        for usuario in (None, self.gestor):
            with self.subTest(gestor=bool(usuario)):
                if usuario:
                    self.client.force_login(usuario)
                with CaptureQueriesContext(connection) as consultas:
                    respuesta = self.client.get(self.url)
                self.assertEqual(respuesta.status_code, 200)
                for tabla in ('webcitt_espacioreservable', 'webcitt_fichaarea', 'webcitt_unidadequipo',
                              'webcitt_softwaredisponible', 'webcitt_asignatura'):
                    self.assertFalse(any(tabla in item['sql'].lower() for item in consultas), tabla)
                for texto in ('id="areas"', 'id="matriz"', 'id="capacidad"', 'Abrir el simulador'):
                    self.assertNotContains(respuesta, texto)

    def test_repositorio_oculto_no_recibe_enlaces_desde_la_portada(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='1.5', oculta=True)
        for usuario in (None, self.gestor):
            if usuario:
                self.client.force_login(usuario)
            self.assertNotContains(self.client.get(self.url), reverse('repositorio_unidad', args=[SLUG]))

    def test_presentacion_oculta_no_se_consulta_ni_muestra_en_portada(self):
        PresentacionUnidad.objects.filter(unidad=self.unidad).update(publicada=True, lema='LEMA_OCULTO_PROPIO')
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='1.1', oculta=True)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url)
        self.assertIsNone(respuesta.context['presentacion_logistica'])
        self.assertFalse(any('webcitt_presentacionunidad' in item['sql'].lower() for item in consultas))
        self.assertNotContains(respuesta, 'LEMA_OCULTO_PROPIO')
