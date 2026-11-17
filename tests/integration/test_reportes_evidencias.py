"""Fase 1 de reportes: lo que la unidad ya registra sale como evidencia.

Familias en el selector, tres categorías nuevas (guías, seguridad,
transferencia), disponibilidad de equipos en el período, clasificación en
inventario, escenario en la planificación y el tema del syllabus al planificar.
"""

from datetime import date, datetime, time
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.practicas_forms import PlanificacionPracticaForm
from apps.gestion_unidades.presentation.reportes_evidencias import disponibilidad_por_equipo, reporte_equipamiento
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.formacion.models.practicas import PlanificacionPractica
from apps.reservas.models.seguridad import RegistroIngreso
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class BaseDeReportes(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coordinador = get_user_model().objects.create_user(
            username='coordinador-evidencias', password='clave-segura',
            first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de evidencias', slug='laboratorio-evidencias',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1),
            administrador=cls.coordinador)
        cls.desde, cls.hasta = date(2026, 3, 1), date(2026, 3, 10)

    def setUp(self):
        self.client.force_login(self.coordinador)

    def reporte(self, categoria, formato='', **extra):
        nombre = {'': 'gestion_reporte_unidad', 'pdf': 'gestion_reporte_unidad_pdf',
                  'xlsx': 'gestion_reporte_unidad_xlsx'}[formato]
        parametros = {'categoria_reporte': categoria, 'desde': self.desde.isoformat(),
                      'hasta': self.hasta.isoformat(), **extra}
        return self.client.get(reverse(nombre, args=[self.unidad.slug]), parametros)

    def reserva(self, **campos):
        datos = dict(laboratorio=self.unidad, usuario=self.coordinador, fecha=date(2026, 3, 4),
                     hora_inicio=time(9, 0), hora_fin=time(11, 0), titulo_solicitud='Sesión',
                     estado='confirmada')
        datos.update(campos)
        return Reserva.objects.create(**datos)


class SelectorPorFamiliasTests(BaseDeReportes):
    def test_reportes_de_unidad_abren_el_visor_compartido_con_sus_filtros(self):
        from html.parser import HTMLParser

        class Enlaces(HTMLParser):
            def __init__(self):
                super().__init__()
                self.enlaces = []

            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.enlaces.append(dict(attrs))

        pagina = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
                                {'view': 'reportes', 'categoria_reporte': 'reservas',
                                 'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()})
        parser = Enlaces()
        parser.feed(pagina.content.decode())
        rutas = (reverse('gestion_reporte_unidad_pdf', args=[self.unidad.slug]), reverse('reporte_institucional'))
        vistas = [a for a in parser.enlaces if 'data-ver-pdf' in a and a.get('href', '').startswith(rutas)]
        self.assertGreaterEqual(len(vistas), 2)
        for enlace in vistas:
            self.assertNotIn('target', enlace)
            self.assertNotIn('data-pdf-directo', enlace)
            self.assertTrue(enlace.get('data-pdf-titulo'))
            if enlace['href'].startswith(rutas[0]):
                self.assertIn('categoria_reporte=reservas', enlace['href'])
                self.assertIn('desde=2026-03-01', enlace['href'])
                self.assertIn('hasta=2026-03-10', enlace['href'])
            respuesta = self.client.get(enlace['href'])
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertContains(pagina, 'class="aula-pdf-modal"', count=1)

    def test_la_entrada_anterior_abre_cumplimiento_y_conserva_el_expediente_propio_para_operadores(self):
        direccion = get_user_model().objects.create_superuser('direccion-evidencias', 'd@example.test', 'clave')
        self.client.force_login(direccion)
        parametros = {'tipo': 'laboratorios', 'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()}
        ruta = reverse('admin:reportes-evidencias-por-tipo')
        pagina = self.client.get(ruta, parametros, follow=True)
        self.assertEqual([estado for _url, estado in pagina.redirect_chain], [302])
        destino = urlsplit(pagina.redirect_chain[0][0])
        self.assertEqual(destino.path, reverse('admin:reportes-cumplimiento-expediente'))
        self.assertEqual(parse_qs(destino.query)['tipo'], ['laboratorios'])
        self.assertEqual(parse_qs(destino.query)['desde'], [self.desde.isoformat()])
        self.assertEqual(parse_qs(destino.query)['hasta'], [self.hasta.isoformat()])
        self.assertTemplateUsed(pagina, 'admin/gestion_unidades/reporteoperativounidad/cumplimiento.html')
        self.assertNotContains(pagina, 'data-directorio-unidades')
        self.assertContains(pagina, 'class="citt-tipo__cabecera"')
        self.assertNotContains(pagina, 'data-pdf-directo')
        self.assertNotContains(pagina, 'target="_blank"')
        self.assertNotContains(pagina, '?view=reportes')
        fila = next(f for f in pagina.context['filas'] if f['unidad'].pk == self.unidad.pk)
        self.assertIn('matriz', fila)
        self.assertIn('progreso_general', fila)
        self.assertNotIn('informes', fila)
        detalle = self.client.get(ruta, dict(parametros, unidad=self.unidad.slug), follow=True)
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual([estado for _url, estado in detalle.redirect_chain], [302])
        self.assertEqual(detalle.context['unidad'], self.unidad.slug)
        self.assertEqual([f['unidad'].pk for f in detalle.context['filas']], [self.unidad.pk])
        self.coordinador.is_staff = True
        self.coordinador.save(update_fields=['is_staff'])
        self.client.force_login(self.coordinador)
        ajena = Unidad.objects.create(nombre='Ajena', slug='ajena-evidencias', dependencia='laboratorios',
                                      fecha_inicio=self.desde, administrador=direccion)
        self.assertEqual(self.client.get(reverse('admin:reportes-documento-evidencia', args=[ajena.slug])).status_code, 403)
        from django.contrib import admin
        with patch.object(admin.site, 'each_context', return_value={
                'site_title': 'Administración', 'site_header': 'Administración',
                'has_permission': True, 'available_apps': [], 'is_popup': False}):
            propia = self.client.get(reverse('admin:reportes-evidencias-por-tipo'))
        self.assertNotContains(propia, ajena.nombre)
        self.assertEqual([f['unidad'].pk for f in propia.context['filas']], [self.unidad.pk])
        self.assertEqual(urlsplit(propia.context['filas'][0]['url']).path,
                         reverse('gestion_expediente_unidad', args=[self.unidad.slug]))

    def test_el_selector_agrupa_las_categorias_en_familias_de_evidencia(self):
        # El navegador de familias acompaña al informe abierto; la portada es el expediente.
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
                                {'view': 'reportes', 'categoria_reporte': 'reservas'})

        self.assertEqual(panel.status_code, 200)
        for familia in ('1 · Planificación y registros de uso de laboratorios',
                        '2 · Mantenimiento, disponibilidad y funcionalidad del equipamiento',
                        '3 · Inventario de equipamiento, reactivos e insumos',
                        '4 · Guías de prácticas de laboratorio',
                        '5 · Bioseguridad, seguridad y condiciones de operación',
                        '6 · Gestión de desechos peligrosos y especiales',
                        '7 · Investigación aplicada y desarrollo tecnológico',
                        '8 · Transferencia de conocimiento, tecnología y servicios especializados a la sociedad'):
            with self.subTest(familia=familia):
                # El menú desplegable se volvió un navegador a la vista; las
                # ocho familias siguen siendo las mismas.
                self.assertContains(panel, familia)
        self.assertContains(panel, 'Planificación semestral de prácticas por asignatura')
        # Las consultas de prácticas llevan el nombre del anexo al que alimentan (documentos.0027).
        self.assertContains(panel, 'Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable')
        self.assertContains(panel, 'Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados')
        # Un laboratorio que no produce no ofrece producción, pero sí transferencia.
        self.assertNotContains(panel, 'categoria_reporte=produccion')
        self.assertNotContains(panel, 'Producción (plantas piloto)')
        self.assertContains(panel, 'categoria_reporte=transferencia')
        self.assertContains(panel, 'categoria_reporte=investigacion')
        self.assertContains(panel, 'categoria_reporte=equipamiento')

    def test_cada_categoria_nueva_sale_en_html_pdf_y_hoja_de_calculo(self):
        for categoria in ('guias', 'seguridad', 'transferencia', 'equipamiento', 'investigacion', 'desechos'):
            for formato in ('', 'pdf', 'xlsx'):
                with self.subTest(categoria=categoria, formato=formato):
                    respuesta = self.reporte(categoria, formato)
                    self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self.reporte('guias', 'pdf').content.startswith(b'%PDF'))


class GuiasTests(BaseDeReportes):
    def test_lista_las_guias_con_su_vinculo_al_syllabus(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Impresión FDM')
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía FDM', codigo_guia='G-FDM-01', numero_version=2,
            es_vigente=True, estado_publicacion='publicada', activo=True)
        asignatura = Asignatura.objects.create(unidad=self.unidad, codigo='MAN-301', nombre='Manufactura digital')
        tema = TemaAsignatura.objects.create(asignatura=asignatura, nombre='Impresión 3D', orden=1)
        PlanificacionPractica.objects.create(
            codigo='PL-0001', unidad=self.unidad, actividad=actividad, guia=guia, tema_asignatura=tema,
            fecha=date(2026, 3, 4), hora_inicio=time(9, 0), hora_fin=time(11, 0),
            asignatura='Manufactura digital', docente_tutor='Ana', tema='Impresión 3D',
            resultado_aprendizaje='Imprime una pieza', creado_por=self.coordinador)

        pagina = self.reporte('guias')

        self.assertContains(pagina, 'G-FDM-01')
        self.assertContains(pagina, 'v2 (vigente)')
        self.assertContains(pagina, 'Manufactura digital · Impresión 3D')
        self.assertContains(pagina, 'Vinculadas al syllabus')


class SeguridadTests(BaseDeReportes):
    def test_lista_ingresos_y_rechazos_con_proteccion_verificada(self):
        reserva = self.reserva(codigo_reserva='RES-SEG-1')
        RegistroIngreso.objects.create(reserva=reserva, nombre='Estudiante Uno', categoria='estudiante',
                                       ingresa=True, proteccion_verificada=True)
        RegistroIngreso.objects.create(reserva=reserva, nombre='Visitante Dos', categoria='visitante',
                                       ingresa=False, motivo='Sin inducción vigente')

        todos = self.reporte('seguridad')
        rechazos = self.reporte('seguridad', estado='rechazo')

        self.assertContains(todos, 'Estudiante Uno')
        self.assertContains(todos, 'Sin inducción vigente')
        self.assertContains(todos, 'Habilitaciones vigentes')
        self.assertContains(rechazos, 'Visitante Dos')
        self.assertNotContains(rechazos, 'Estudiante Uno')


class TransferenciaTests(BaseDeReportes):
    def test_reune_servicios_y_reservas_de_vinculacion(self):
        SolicitudFabricacion.objects.create(
            unidad=self.unidad, solicitante=self.coordinador, nombre_proyecto='Pieza para cooperativa',
            tipo_trabajo='servicio_institucional', estado='completada', tiempo_estimado_horas=Decimal('3.5'),
            fecha_solicitud=date(2026, 3, 3))
        self.reserva(codigo_reserva='RES-VIN-1', proposito_codigo='vinculacion', institucion='Cooperativa Carchi',
                     tipo_usuario_solicitante='externo', nombre_solicitante='Rosa Externa')
        self.reserva(codigo_reserva='RES-DOC-1', proposito_codigo='docencia_practica', fecha=date(2026, 3, 5))

        pagina = self.reporte('transferencia')

        self.assertContains(pagina, 'Pieza para cooperativa')
        self.assertContains(pagina, 'Cooperativa Carchi')
        self.assertNotContains(pagina, 'RES-DOC-1')
        self.assertContains(pagina, 'Beneficiarios externos')
        # Las solicitudes siguen como contexto; ninguna acredita una transferencia aceptada.
        datos = pagina.context['reporte_gestion']['dataset']
        self.assertEqual(datos['rows'], [])
        self.assertEqual(datos['cards'][1][1], 0)
        self.assertContains(pagina, 'Solicitudes de servicio y actividades de vinculación')


class DisponibilidadTests(BaseDeReportes):
    def activo(self, codigo='UE-01'):
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        ficha = catalogo.objects.create(codigo=f'EQ-{codigo}', nombre='Centrífuga')
        return UnidadEquipo.objects.create(laboratorio=self.unidad, equipo=ficha, codigo_unidad=codigo,
                                           estado_unidad='disponible', activa=True)

    def momento(self, dia):
        return timezone.make_aware(datetime.combine(dia, time.min), timezone.get_current_timezone())

    def test_los_cambios_de_estado_dan_el_porcentaje_del_periodo(self):
        activo = self.activo()
        EventoCicloVidaEquipo.objects.create(
            equipo=activo, unidad=self.unidad, tipo='cambio_estado', descripcion='Falla',
            fecha=self.momento(date(2026, 3, 3)), estado_anterior='disponible', estado_nuevo='mantenimiento')
        EventoCicloVidaEquipo.objects.create(
            equipo=activo, unidad=self.unidad, tipo='cambio_estado', descripcion='Reparada',
            fecha=self.momento(date(2026, 3, 5)), estado_anterior='mantenimiento', estado_nuevo='disponible')

        resultado = disponibilidad_por_equipo(self.unidad, self.desde, self.hasta)

        # Diez días de período, dos fuera de servicio.
        self.assertEqual(resultado[activo.pk], (80.0, 2.0))
        pagina = self.reporte('equipamiento')
        self.assertContains(pagina, 'Disponible en el período')
        self.assertContains(pagina, '80.0 %')
        self.assertContains(pagina, 'Disponibilidad media')
        # La ficha de inventario no repite la disponibilidad: cada evidencia en su sitio.
        ficha = self.reporte('recursos')
        self.assertContains(ficha, 'Marca / modelo / versión')
        self.assertNotContains(ficha, 'Disponible en el período')

    def test_un_equipo_en_mantenimiento_sin_cambios_cuenta_todo_el_periodo(self):
        activo = self.activo('UE-02')
        UnidadEquipo.objects.filter(pk=activo.pk).update(estado_unidad='mantenimiento')

        resultado = disponibilidad_por_equipo(self.unidad, self.desde, self.hasta)

        self.assertEqual(resultado[activo.pk], (0.0, 10.0))
        _headers, _rows, tarjetas, _estados = reporte_equipamiento(self.unidad, self.desde, self.hasta)
        self.assertEqual(tarjetas[1][1], '0.0 %')

    def test_un_equipo_obsoleto_o_no_localizado_no_se_informa_como_disponible(self):
        for estado in ('obsoleto', 'no_localizado'):
            with self.subTest(estado=estado):
                activo = self.activo('UE-' + estado)
                UnidadEquipo.objects.filter(pk=activo.pk).update(estado_unidad=estado)
                resultado = disponibilidad_por_equipo(self.unidad, self.desde, self.hasta)
                self.assertEqual(resultado[activo.pk], (0.0, 10.0))
        _headers, filas, tarjetas, _estados = reporte_equipamiento(self.unidad, self.desde, self.hasta)
        self.assertEqual(tarjetas[1][1], '0.0 %')
        self.assertEqual(tarjetas[2][1], 2)
        self.assertTrue(all(fila[4] == '0.0 %' for fila in filas))

    def test_un_inventario_vacio_no_inventa_cien_por_ciento_de_disponibilidad(self):
        _headers, filas, tarjetas, _estados = reporte_equipamiento(self.unidad, self.desde, self.hasta)
        self.assertEqual(filas, [])
        self.assertEqual(tarjetas[0][1], 0)
        self.assertEqual(tarjetas[1][1], 'Sin medición')
        self.assertEqual(tarjetas[1][2], 'sin equipos en la selección')


class InventarioPorClasificacionTests(BaseDeReportes):
    def test_los_movimientos_muestran_la_clasificacion_y_cuentan_reactivos(self):
        reactivo = Consumible.objects.create(unidad=self.unidad, codigo='REA-1', nombre='Ácido acético',
                                             clasificacion='reactivo')
        EntradaInventario.objects.create(
            consumible=reactivo, unidad=self.unidad, tipo='ingreso', cantidad=Decimal('2'),
            fecha=timezone.make_aware(datetime(2026, 3, 2, 10, 0)), saldo_resultante=Decimal('2'))

        pagina = self.reporte('inventario')

        self.assertContains(pagina, 'Clasificación')
        self.assertContains(pagina, 'Reactivo')
        self.assertContains(pagina, 'Ácido acético')
        self.assertContains(pagina, 'Reactivos')


class EscenarioEnPlanificacionTests(BaseDeReportes):
    def test_el_formato_ft02_muestra_el_escenario_de_la_reserva(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Análisis de suelos')
        espacio = EspacioReservable.objects.create(unidad=self.unidad, codigo='ESP-1', nombre='Mesa de análisis')
        reserva = self.reserva(actividad_catalogo=actividad)
        reserva.espacios_solicitados.add(espacio)
        PlanificacionPractica.objects.create(
            codigo='PL-0002', unidad=self.unidad, actividad=actividad, reserva=reserva,
            fecha=date(2026, 3, 4), hora_inicio=time(9, 0), hora_fin=time(11, 0),
            asignatura='Edafología', docente_tutor='Ana', tema='Textura', resultado_aprendizaje='Clasifica',
            creado_por=self.coordinador)

        pagina = self.reporte('planificaciones')

        self.assertContains(pagina, 'Escenario')
        self.assertContains(pagina, 'Mesa de análisis')


class TemaDelSyllabusAlPlanificarTests(BaseDeReportes):
    def datos(self, actividad, **extra):
        base = {'actividad': actividad.pk, 'fecha': '2026-03-04', 'hora_inicio': '09:00', 'hora_fin': '11:00',
                'carrera': 'Agroindustria', 'semestre': '5', 'asignatura': 'Manufactura', 'docente_tutor': 'Ana',
                'tema': '', 'resultado_aprendizaje': '', 'estudiantes_planificados': 20,
                'categoria_uso': 'docencia', 'observaciones': ''}
        base.update(extra)
        return base

    def test_sin_asignaturas_el_tema_no_es_obligatorio(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Práctica libre')
        formulario = PlanificacionPracticaForm(
            unidad=self.unidad, actividades=CatalogoActividadReserva.objects.filter(unidad=self.unidad))

        self.assertFalse(formulario.fields['tema_asignatura'].required)
        self.assertEqual(list(formulario.fields['tema_asignatura'].queryset), [])
        del actividad

    def test_con_asignaturas_el_tema_es_obligatorio_y_rellena_la_practica(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Impresión FDM')
        asignatura = Asignatura.objects.create(unidad=self.unidad, codigo='MAN-301', nombre='Manufactura digital',
                                               carrera='Ingeniería en Producción', semestre='Quinto')
        tema = TemaAsignatura.objects.create(asignatura=asignatura, nombre='Impresión 3D', orden=1,
                                             resultado_aprendizaje='Imprime una pieza funcional')
        actividades = CatalogoActividadReserva.objects.filter(unidad=self.unidad)

        sin_tema = PlanificacionPracticaForm(self.datos(actividad), unidad=self.unidad, actividades=actividades)
        self.assertFalse(sin_tema.is_valid())
        self.assertIn('tema_asignatura', sin_tema.errors)

        con_tema = PlanificacionPracticaForm(
            self.datos(actividad, tema_asignatura=tema.pk, asignatura='', carrera='', semestre=''),
            unidad=self.unidad, actividades=actividades)
        self.assertTrue(con_tema.is_valid(), con_tema.errors)
        self.assertEqual(con_tema.cleaned_data['tema'], 'Impresión 3D')
        self.assertEqual(con_tema.cleaned_data['resultado_aprendizaje'], 'Imprime una pieza funcional')
        # La asignatura, la carrera y el semestre vienen del syllabus: el FT02 no queda con casillas vacías.
        self.assertEqual(con_tema.cleaned_data['asignatura'], 'Manufactura digital')
        self.assertEqual(con_tema.cleaned_data['carrera'], 'Ingeniería en Producción')
        self.assertEqual(con_tema.cleaned_data['semestre'], 'Quinto')
        self.assertEqual(list(con_tema.fields['tema_asignatura'].queryset), [tema])


class SemestrePorDefectoTests(BaseDeReportes):
    def test_sin_fechas_los_informes_cubren_el_semestre_de_gestion_aunque_varie_el_calendario(self):
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico

        hoy = timezone.localdate()
        periodo = PeriodoAcademico.objects.create(
            codigo='2026-X', nombre='Período de prueba', anio_referencia=hoy.year, ciclo='A',
            tipo='ordinario', ambito='carreras_centros', semanas_planificadas=16, estado='publicado')
        VersionCalendarioAcademico.objects.create(
            periodo=periodo, numero=1, nombre='Calendario', fecha_inicio_clases=hoy.replace(day=1),
            fecha_fin_clases=hoy, fecha_fin_periodo=hoy, vigente=True)

        semestral = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
                                    {'categoria_reporte': 'planificaciones'})
        treinta_dias = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
                                       {'categoria_reporte': 'reservas'})

        inicio = date(hoy.year, 1 if hoy.month <= 6 else 7, 1)
        fin = date(hoy.year, 6, 30) if hoy.month <= 6 else date(hoy.year, 12, 31)
        self.assertEqual(semestral.context['reporte_gestion']['start_date'], inicio)
        self.assertEqual(semestral.context['reporte_gestion']['end_date'], fin)
        # También cuentan mantenimiento, visitas y servicios fuera de clases.
        self.assertEqual(treinta_dias.context['reporte_gestion']['start_date'], inicio)
        self.assertEqual(treinta_dias.context['reporte_gestion']['end_date'], fin)
        # Con fechas explícitas, manda lo que pidió la persona.
        explicito = self.reporte('planificaciones')
        self.assertEqual(explicito.context['reporte_gestion']['start_date'], self.desde)


class InvestigacionTests(BaseDeReportes):
    def test_reune_reservas_de_investigacion_y_titulacion_y_deja_fuera_la_docencia(self):
        self.reserva(codigo_reserva='RES-INV-1', proposito_codigo='investigacion_innovacion',
                     nombre_solicitante='Investigadora Uno', carrera_solicitante='Agroindustria')
        self.reserva(codigo_reserva='RES-TIT-1', proposito_codigo='titulacion', fecha=date(2026, 3, 6))
        self.reserva(codigo_reserva='RES-DOC-2', proposito_codigo='docencia_practica', fecha=date(2026, 3, 7))

        pagina = self.reporte('investigacion')

        self.assertContains(pagina, 'RES-INV-1')
        self.assertContains(pagina, 'RES-TIT-1')
        self.assertNotContains(pagina, 'RES-DOC-2')
        self.assertContains(pagina, 'Reservas de titulación')
