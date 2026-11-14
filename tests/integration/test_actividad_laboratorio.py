"""Lo que el laboratorio registra se publica solo: proyectos, colaboración, vinculación, cursos y áreas.

Las secciones 6.1, 6.2 y 6.4 se arman con las reservas aprobadas o realizadas, agrupadas por
actividad, sin publicar lo que escribió el solicitante; la 4.3 con los cursos publicados del
catálogo; la 4.4 agrupa los recursos por área; y cada área dice quién la coordina, cómo se
reserva, su software y sus recursos en línea.
"""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.admin.sites import site
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.admin.configuracion import EspacioReservableInline
from apps.laboratorios.operacion.presentation.actividad_laboratorio import actividades_de, completar_cursos_de, consulta_cursos_de, cursos_de, grupo_de
from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


class ActividadDelLaboratorioTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = Unidad.objects.create(
            nombre='Laboratorio con actividad', descripcion='.', fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-con-actividad', dependencia='laboratorios')
        cls.otro = Unidad.objects.create(nombre='Otro laboratorio', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                         slug='otro-laboratorio', dependencia='laboratorios')
        cls.usuario = get_user_model().objects.create_user('solicitante.actividad', 's@example.org', 'clave')
        cls.semillero = cls.actividad('Semillero de robótica', 'investigacion_innovacion', 'investigacion_formativa',
                                      visibilidad='unidad', responsable='MSc. Ana Pérez')
        cls.proyecto_privado = cls.actividad('Proyecto reservado del centro', 'investigacion_innovacion',
                                             'proyecto_centro', visibilidad='privada', responsable='Dr. Privado')
        cls.curso = cls.actividad('Inducción a impresión 3D', 'capacitacion', 'induccion', visibilidad='institucional',
                                  estado='publicado', responsable='Técnico del FabLab')
        cls.borrador = cls.actividad('Curso en preparación', 'capacitacion', 'curso', visibilidad='institucional',
                                     estado='borrador')

    @classmethod
    def actividad(cls, nombre, proposito, subtipo, visibilidad='unidad', estado='publicado', responsable=''):
        return CatalogoActividadReserva.objects.create(
            nombre=nombre, proposito_codigo=proposito, subtipo_actividad=subtipo, unidad=cls.laboratorio,
            creado_por=cls.usuario, visibilidad=visibilidad, estado_publicacion=estado, responsable=responsable)

    def reserva(self, proposito, subtipo, estado='confirmada', actividad=None, dias=0, horas=(9, 11), unidad=None):
        return Reserva.objects.create(
            laboratorio=unidad or self.laboratorio, usuario=self.usuario,
            fecha=timezone.localdate() + timedelta(days=dias), hora_inicio=time(horas[0]), hora_fin=time(horas[1]),
            equipo_codigo='EQ-1', equipo_nombre='Equipo', nombre_solicitante='Nombre privado',
            correo_solicitante='privado@example.org', proposito='Texto privado del solicitante',
            proposito_codigo=proposito, subtipo_actividad=subtipo, actividad_catalogo=actividad, estado=estado)

    def test_cada_reserva_cae_en_su_seccion(self):
        casos = {
            ('investigacion_innovacion', 'proyecto_centro'): 'colaboracion_centros',
            ('investigacion_innovacion', 'proyecto_investigacion'): 'colaboracion_centros',
            ('vinculacion', 'proyecto_vinculacion'): 'vinculacion',
            ('titulacion', 'trabajo_titulacion'): 'proyectos_formativos',
            ('investigacion_innovacion', 'investigacion_formativa'): 'proyectos_formativos',
            ('docencia_practica', 'proyecto_asignatura'): 'proyectos_formativos',
            ('docencia_practica', 'practica_curricular'): '',
            ('capacitacion', 'curso'): '',
        }
        for (proposito, subtipo), esperado in casos.items():
            with self.subTest(subtipo=subtipo):
                self.assertEqual(grupo_de(Reserva(proposito_codigo=proposito, subtipo_actividad=subtipo)), esperado)

    def test_agrupa_por_actividad_cuenta_horas_y_no_publica_lo_privado(self):
        self.reserva('investigacion_innovacion', 'investigacion_formativa', actividad=self.semillero, dias=-10)
        self.reserva('investigacion_innovacion', 'investigacion_formativa', estado='completada',
                     actividad=self.semillero, dias=-3, horas=(14, 17))
        self.reserva('investigacion_innovacion', 'investigacion_formativa', estado='rechazada', actividad=self.semillero)
        self.reserva('investigacion_innovacion', 'proyecto_centro', actividad=self.proyecto_privado, dias=5)
        self.reserva('docencia_practica', 'practica_curricular')
        self.reserva('investigacion_innovacion', 'proyecto_centro', unidad=self.otro)

        actividades = actividades_de(self.laboratorio)
        [semillero] = actividades['proyectos_formativos']
        self.assertEqual((semillero['nombre'], semillero['responsable'], semillero['sesiones'], semillero['horas']),
                         ('Semillero de robótica', 'MSc. Ana Pérez', 2, 5.0))
        self.assertFalse(semillero['en_curso'])
        # Una actividad privada se publica por su tipo, sin nombre ni responsable.
        [centro] = actividades['colaboracion_centros']
        self.assertEqual((centro['nombre'], centro['responsable']), ('Actividad de un centro o grupo de investigación', ''))
        self.assertTrue(centro['en_curso'])
        self.assertEqual(actividades['vinculacion'], [])

        pagina = self.client.get(reverse('proyectos_unidad', args=[self.laboratorio.slug, 'colaboracion_centros']))
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context['seccion'], '6.2')
        for privado in ('Proyecto reservado del centro', 'Dr. Privado', 'Texto privado del solicitante', 'Nombre privado'):
            self.assertNotContains(pagina, privado)
        self.assertEqual(self.client.get(
            reverse('proyectos_unidad', args=[self.laboratorio.slug, 'docencia'])).status_code, 404)

    def test_la_ficha_ofrece_las_secciones_que_tienen_actividad_y_cursos(self):
        self.reserva('investigacion_innovacion', 'investigacion_formativa', actividad=self.semillero)
        self.reserva('capacitacion', 'induccion', actividad=self.curso, dias=7)
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(ficha, reverse('proyectos_unidad', args=[self.laboratorio.slug, 'proyectos_formativos']))
        self.assertContains(ficha, 'Proyectos formativos (1)')
        self.assertContains(ficha, 'Actividades con reserva (1)')
        self.assertNotContains(ficha, reverse('proyectos_unidad', args=[self.laboratorio.slug, 'vinculacion']))
        visibles = [modulo.clave for modulo in ficha.context['modulos']]
        self.assertIn('investigacion-formativa', visibles)
        self.assertIn('docencia-capacitacion', visibles)

        [curso] = cursos_de(self.laboratorio)
        self.assertEqual((curso.nombre, curso.proxima_sesion.fecha), ('Inducción a impresión 3D',
                                                                     timezone.localdate() + timedelta(days=7)))
        cursos = self.client.get(reverse('cursos_unidad', args=[self.laboratorio.slug]))
        self.assertContains(cursos, 'Técnico del FabLab')
        self.assertNotContains(cursos, 'Curso en preparación')
        self.assertEqual(cursos.context['seccion'], '4.3')


    def test_catalogo_con_muchas_actividades_limita_seis_en_sql_y_pagina_sin_omitirlas(self):
        for numero in range(8):
            self.actividad(f'Capacitación paginada {numero:02d}', 'capacitacion', 'curso')
        url = reverse('cursos_unidad', args=[self.laboratorio.slug])
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['catalogo']), 6)
        self.assertEqual(respuesta.context['catalogo_total'], 9)
        self.assertEqual(respuesta.context['catalogo_pagina'].paginator.per_page, 6)
        self.assertEqual(respuesta.context['catalogo_pagina'].paginator.num_pages, 2)
        tabla = CatalogoActividadReserva._meta.db_table.upper()
        seleccion = [consulta['sql'].upper() for consulta in consultas.captured_queries
                     if consulta['sql'].upper().startswith(f'SELECT "{tabla}"."ID"')]
        self.assertTrue(seleccion)
        self.assertTrue(any('LIMIT 6' in sql for sql in seleccion))
        self.assertTrue(all('LIMIT' in sql for sql in seleccion), 'No materializar todas las actividades para paginar.')
        pagina_dos = self.client.get(url, {'pagina_reservas': '2'})
        self.assertEqual(len(pagina_dos.context['catalogo']), 3)
        ids = [curso.pk for curso in respuesta.context['catalogo'] + pagina_dos.context['catalogo']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(consulta_cursos_de(self.laboratorio).values_list('pk', flat=True)))

    def test_resumen_de_seis_actividades_usa_dos_consultas_y_una_proxima_sesion_aprobada(self):
        cursos = [self.actividad(f'Actividad de resumen {numero}', 'capacitacion', 'taller') for numero in range(6)]
        esperadas = {}
        for numero, curso in enumerate(cursos):
            self.reserva('capacitacion', 'taller', estado='rechazada', actividad=curso, dias=1, horas=(8, 9))
            self.reserva('capacitacion', 'taller', estado='pendiente', actividad=curso, dias=1, horas=(9, 10))
            self.reserva('capacitacion', 'taller', estado='cancelada', actividad=curso, dias=1, horas=(10, 11))
            self.reserva('capacitacion', 'taller', estado='completada', actividad=curso, dias=-2)
            self.reserva('capacitacion', 'taller', estado='confirmada', actividad=curso, dias=-1)
            if numero < 5:
                primera = self.reserva('capacitacion', 'taller', actividad=curso, dias=2, horas=(9, 10))
                self.reserva('capacitacion', 'taller', actividad=curso, dias=2, horas=(9, 10))
                self.reserva('capacitacion', 'taller', estado='en_proceso', actividad=curso, dias=2, horas=(11, 12))
                self.reserva('capacitacion', 'taller', actividad=curso, dias=3)
                esperadas[curso.pk] = primera.pk
            else:
                esperadas[curso.pk] = None
        with self.assertNumQueries(2):
            resumidas = completar_cursos_de(cursos)
        with self.assertNumQueries(0):
            self.assertEqual(len(resumidas), 6)
            for curso in resumidas:
                with self.subTest(actividad=curso.nombre):
                    self.assertEqual(curso.proxima_sesion.pk if curso.proxima_sesion else None, esperadas[curso.pk])
                    self.assertEqual(curso.sesiones_realizadas, 1)
        with self.assertNumQueries(0):
            self.assertEqual(completar_cursos_de([]), [])

    def test_catalogo_de_reservas_excluye_revision_rechazadas_privadas_inactivas_y_otras_unidades(self):
        ocultas = [
            self.actividad('Actividad pendiente de revisión', 'capacitacion', 'curso', estado='revision'),
            self.actividad('Actividad rechazada', 'capacitacion', 'curso', estado='rechazada'),
            self.actividad('Actividad privada', 'capacitacion', 'curso', visibilidad='privada'),
            self.actividad('Actividad desactivada', 'capacitacion', 'curso'),
        ]
        ocultas[-1].activo = False
        ocultas[-1].save(update_fields=['activo'])
        ajena = CatalogoActividadReserva.objects.create(
            nombre='Actividad de otra unidad', unidad=self.otro, creado_por=self.usuario,
            proposito_codigo='capacitacion', subtipo_actividad='curso',
            estado_publicacion='publicado', visibilidad='institucional',
        )
        self.assertEqual(list(consulta_cursos_de(self.laboratorio)), [self.curso])
        respuesta = self.client.get(reverse('cursos_unidad', args=[self.laboratorio.slug]))
        self.assertEqual(respuesta.context['catalogo_total'], 1)
        for actividad in [self.borrador, *ocultas, ajena]:
            with self.subTest(actividad=actividad.nombre):
                self.assertNotContains(respuesta, actividad.nombre)


class AreasDelLaboratorioTests(TestCase):
    databases = {'default', 'centros'}

    def setUp(self):
        self.laboratorio = Unidad.objects.create(nombre='Laboratorio de áreas', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                                 slug='laboratorio-de-areas', dependencia='laboratorios')
        self.otro = Unidad.objects.create(nombre='Ajeno', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                          slug='ajeno', dependencia='laboratorios')
        self.tecnica = ResponsableUnidad.objects.create(unidad=self.laboratorio, nombre='Ing. Laura Ruiz', rol='tecnico',
                                                        horario_atencion='Lunes a viernes 8:00–16:00')
        self.area = EspacioReservable.objects.create(
            unidad=self.laboratorio, codigo='LAB-RV', nombre='Realidad virtual', capacidad=8, politica_reserva='tecnico',
            instrucciones_uso='Inducción previa obligatoria.', responsable=self.tecnica)

    def test_cada_area_tiene_su_pagina_con_responsable_y_reserva(self):
        url = reverse('area_unidad', args=[self.laboratorio.slug, self.area.codigo])
        pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Realidad virtual')
        self.assertContains(pagina, 'Ing. Laura Ruiz')
        self.assertContains(pagina, 'Lunes a viernes 8:00–16:00')
        self.assertContains(pagina, 'Inducción previa obligatoria.')
        self.assertContains(pagina, 'Uso técnico')
        self.assertNotContains(pagina, '<table')
        # El menú de la ficha ofrece el área como un botón propio, y la página general la enlaza.
        self.assertContains(self.client.get(self.laboratorio.get_absolute_url()), url)
        self.assertContains(self.client.get(reverse('areas_equipos', args=[self.laboratorio.slug])), url)
        # Un área inactiva o un código ajeno no tienen página.
        self.assertEqual(self.client.get(reverse('area_unidad', args=[self.otro.slug, self.area.codigo])).status_code, 404)
        self.area.activo = False
        self.area.save(update_fields=['activo'])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_un_responsable_no_publico_no_aparece_en_el_area(self):
        self.tecnica.publico = False
        self.tecnica.save(update_fields=['publico'])
        pagina = self.client.get(reverse('area_unidad', args=[self.laboratorio.slug, self.area.codigo]))
        self.assertNotContains(pagina, 'Ing. Laura Ruiz')

    def test_el_responsable_debe_ser_de_la_misma_unidad(self):
        ajeno = ResponsableUnidad.objects.create(unidad=self.otro, nombre='Ajeno', rol='tecnico')
        self.area.responsable = ajeno
        with self.assertRaises(ValidationError):
            self.area.clean()

    def test_el_administrador_solo_ofrece_responsables_activos_de_la_unidad(self):
        ResponsableUnidad.objects.create(unidad=self.otro, nombre='De otra unidad', rol='tecnico')
        ResponsableUnidad.objects.create(unidad=self.laboratorio, nombre='Retirado', rol='tecnico', activo=False)
        solicitud = RequestFactory().get(f'/admin/directorio_unidades/unidad/{self.laboratorio.pk}/change/')
        bloque = EspacioReservableInline(Unidad, site)
        campo = bloque.formfield_for_foreignkey(EspacioReservable._meta.get_field('responsable'), solicitud)
        self.assertEqual(list(campo.queryset), [self.tecnica])
