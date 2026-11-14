"""El sílabo y las guías pendientes no consultan por cada asignatura o sesión."""

from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.formacion.presentation import asignaturas
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ProgramacionReserva, Reserva
from apps.formacion.models.practicas import PlanificacionPractica
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad


class AsignaturasSinConsultasPorFilaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username='qa-syllabus-consultas')
        cls.unidad = Unidad.objects.create(nombre='Unidad QA syllabus', slug='qa-syllabus-consultas',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1), administrador=cls.usuario)
        cls.otra = Unidad.objects.create(nombre='Unidad ajena QA', slug='qa-syllabus-ajena',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.hoy = date(2026, 10, 11)
        producto = Producto.objects.create(unidad=cls.unidad, codigo='QA-SIL-PROD', nombre='Producto QA', unidad_medida='kg')
        cls.receta = Receta.objects.create(unidad=cls.unidad, producto=producto, codigo='QA-SIL-PROC', nombre='Proceso QA',
            cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        cls.software = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Simulador QA')
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Prácticas QA',
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular')
        cls.general = GuiaActividadReserva.objects.create(actividad=cls.actividad, titulo='Guía general QA', alcance='periodo')
        cls.guia = GuiaActividadReserva.objects.create(actividad=cls.actividad, titulo='Sesión QA', guia_general=cls.general)
        cls.programa = ProgramacionReserva.objects.create(laboratorio=cls.unidad, solicitante=cls.usuario,
            actividad=cls.actividad, fecha_inicio=cls.hoy, fecha_fin=cls.hoy + timedelta(days=30),
            dia_semana=0, hora_inicio=time(9), hora_fin=time(11))

    def crear_asignaturas(self, inicio, cantidad):
        materias = Asignatura.objects.bulk_create([
            Asignatura(unidad=self.unidad, codigo=f'QA-SIL-{i:03}', nombre=f'Asignatura QA {i:03}',
                docente=self.usuario, activa=i % 2 == 0)
            for i in range(inicio, inicio + cantidad)
        ])
        temas = TemaAsignatura.objects.bulk_create([
            TemaAsignatura(asignatura=materia, nombre=f'Tema {orden}', orden=orden,
                receta=self.receta if orden == 2 else None)
            for materia in materias for orden in (2, 1)
        ])
        TemaAsignatura.software.through.objects.bulk_create([
            TemaAsignatura.software.through(temaasignatura_id=tema.pk, softwaredisponible_id=self.software.pk)
            for tema in temas
        ])
        ProgramacionReserva.objects.bulk_create([
            ProgramacionReserva(laboratorio=self.unidad, solicitante=self.usuario, asignatura=materia,
                fecha_inicio=self.hoy, fecha_fin=self.hoy + timedelta(days=30), dia_semana=0,
                hora_inicio=time(9), hora_fin=time(11), estado=estado)
            for materia in materias for estado in ('activa', 'cancelada')
        ])
        return materias

    def crear_sesiones(self, inicio, cantidad, **cambios):
        datos = dict(laboratorio=self.unidad, usuario=self.usuario, programacion=self.programa,
            fecha=self.hoy + timedelta(days=3), hora_inicio=time(9), hora_fin=time(11), estado='confirmada')
        datos.update(cambios)
        reservas = Reserva.objects.bulk_create([
            Reserva(**datos, codigo_reserva=f'QA-SIL-SES-{i:03}') for i in range(inicio, inicio + cantidad)
        ])
        PlanificacionPractica.objects.bulk_create([
            PlanificacionPractica(unidad=datos['laboratorio'], reserva=reserva, actividad=self.actividad,
                guia=self.guia, codigo=f'QA-SIL-PLAN-{inicio + i:03}', fecha=reserva.fecha,
                hora_inicio=reserva.hora_inicio, hora_fin=reserva.hora_fin, creado_por=self.usuario)
            for i, reserva in enumerate(reservas)
        ])
        return reservas

    def contexto_materializado(self, permisos=None):
        unidad = Unidad.objects.get(pk=self.unidad.pk)
        with CaptureQueriesContext(connection) as consultas:
            contexto = asignaturas.contexto_asignaturas(unidad, permisos or {}, self.hoy)
            datos = [(materia.codigo, materia.activa, materia.docente.username, materia.total_programaciones,
                [(tema.orden, tema.nombre, tema.receta.nombre if tema.receta else None,
                    tema.software_ids_csv, [programa.nombre for programa in tema.software.all()])
                 for tema in materia.lista_temas]) for materia in contexto['asignaturas_unidad']]
            for clave in ('recetas_para_temas', 'software_para_temas', 'periodos_para_asignaturas'):
                list(contexto[clave])
        return contexto, datos, list(consultas)

    def test_crecer_uno_a_ciento_veintiuno_no_consulta_temas_por_asignatura(self):
        self.crear_asignaturas(0, 1)
        _contexto, primero, consultas_antes = self.contexto_materializado()
        self.crear_asignaturas(1, 120)
        contexto, datos, consultas_despues = self.contexto_materializado({'practicas': True})
        self.assertEqual(len(primero), 1)
        self.assertEqual(len(datos), 121)
        self.assertTrue(contexto['puede_operar_asignaturas'])
        self.assertEqual(len(consultas_antes), len(consultas_despues))
        self.assertLessEqual(len(consultas_despues), 9)
        for _codigo, _activa, docente, programaciones, temas in datos:
            self.assertEqual(docente, self.usuario.username)
            self.assertEqual(programaciones, 2)  # Incluye programaciones canceladas, como antes.
            self.assertEqual([tema[0] for tema in temas], [1, 2])
            self.assertEqual([tema[2] for tema in temas], [None, self.receta.nombre])
            self.assertTrue(all(tema[3] == str(self.software.pk) and tema[4] == ['Simulador QA'] for tema in temas))
        self.assertEqual([dato[1] for dato in datos], sorted([dato[1] for dato in datos], reverse=True))

    def test_crecer_uno_a_ciento_veintiuno_no_busca_plan_por_sesion(self):
        reservas = self.crear_sesiones(0, 1)
        asignaturas.antelacion_de(self.unidad)
        with CaptureQueriesContext(connection) as antes:
            primero = asignaturas.sesiones_sin_guia(self.unidad, self.hoy)
        reservas += self.crear_sesiones(1, 120)
        with CaptureQueriesContext(connection) as despues:
            filas = asignaturas.sesiones_sin_guia(self.unidad, self.hoy)
        self.assertEqual(len(primero), 1)
        self.assertEqual([fila['reserva'].pk for fila in filas], [reserva.pk for reserva in reservas])
        self.assertEqual(len(antes), len(despues))
        self.assertLessEqual(len(despues), 2)
        for fila in filas:
            self.assertEqual(fila['programa'], self.actividad.nombre)
            self.assertEqual(fila['guia'].pk, self.guia.pk)
            self.assertEqual(fila['margen'], asignaturas.dias_habiles_hasta(self.hoy, fila['reserva'].fecha) - 2)

    def test_sesiones_conservan_alcance_estado_y_plan_eliminado(self):
        reservas = self.crear_sesiones(0, 8)
        aprobada = GuiaActividadReserva.objects.create(actividad=self.actividad, titulo='Aprobada',
            guia_general=self.general, estado_publicacion='publicada', activo=True)
        inactiva = GuiaActividadReserva.objects.create(actividad=self.actividad, titulo='Inactiva',
            guia_general=self.general, estado_publicacion='publicada', activo=False)
        PlanificacionPractica.objects.filter(reserva=reservas[1]).update(guia=aprobada)
        PlanificacionPractica.objects.filter(reserva=reservas[2]).update(guia=inactiva)
        PlanificacionPractica.objects.filter(reserva=reservas[3]).update(eliminado_en=timezone.now())
        Reserva.objects.filter(pk=reservas[4].pk).update(fecha=self.hoy - timedelta(days=1))
        Reserva.objects.filter(pk=reservas[5].pk).update(estado='cancelada')
        Reserva.objects.filter(pk=reservas[6].pk).update(laboratorio=self.otra)
        Reserva.objects.filter(pk=reservas[7].pk).update(programacion=None)
        filas = asignaturas.sesiones_sin_guia(self.unidad, self.hoy)
        self.assertEqual([fila['reserva'].pk for fila in filas], [reservas[i].pk for i in (0, 2, 3)])
        self.assertIsNone(filas[-1]['guia'])
        self.assertEqual(filas[-1]['estado_guia'], 'Sin guía')
        self.assertEqual(filas[-1]['url_guia'], '')

    def test_plan_precargado_y_fallback_tienen_el_mismo_contrato(self):
        reserva = Reserva.objects.get(pk=self.crear_sesiones(0, 1)[0].pk)
        with self.assertNumQueries(1):
            esperado = asignaturas._plan_de(reserva)
        cargada = Reserva.objects.select_related('planificacion_practica__guia',
            'planificacion_practica__tema_asignatura__receta').get(pk=reserva.pk)
        with self.assertNumQueries(0):
            obtenido = asignaturas._plan_de(cargada)
            self.assertEqual(obtenido.pk, esperado.pk)
            self.assertEqual(obtenido.guia.pk, self.guia.pk)
            self.assertIsNone(obtenido.tema_asignatura)
        PlanificacionPractica.objects.filter(pk=esperado.pk).update(eliminado_en=timezone.now())
        cargada = Reserva.objects.select_related('planificacion_practica').get(pk=reserva.pk)
        with self.assertNumQueries(0):
            self.assertIsNone(asignaturas._plan_de(cargada))
        with self.assertNumQueries(1):
            self.assertIsNone(asignaturas._plan_de(reserva))

    def test_temas_sin_prefetch_conservan_fallback_y_orden(self):
        materia = self.crear_asignaturas(0, 1)[0]
        with self.assertNumQueries(2):
            temas = asignaturas._temas_de_asignatura(materia)
        self.assertEqual([tema.orden for tema in temas], [1, 2])
        with self.assertNumQueries(0):
            self.assertEqual(temas[1].receta.pk, self.receta.pk)
            self.assertEqual([programa.pk for programa in temas[0].software.all()], [self.software.pk])

    def test_cache_vacia_no_se_confunde_con_relacion_sin_precargar(self):
        materia = Asignatura.objects.create(unidad=self.unidad, codigo='QA-SIN-TEMAS', nombre='Sin temas')
        materia = Asignatura.objects.prefetch_related('temas').get(pk=materia.pk)
        reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.usuario,
            fecha=self.hoy, hora_inicio=time(9), hora_fin=time(11))
        reserva = Reserva.objects.select_related('planificacion_practica').get(pk=reserva.pk)
        with self.assertNumQueries(0):
            self.assertEqual(asignaturas._temas_de_asignatura(materia), [])
            self.assertIsNone(asignaturas._plan_de(reserva))

    def test_permiso_de_edicion_no_modifica_catalogo_ni_contadores(self):
        self.crear_asignaturas(0, 3)
        solo_lectura, datos_lectura, _ = self.contexto_materializado()
        editable, datos_edicion, _ = self.contexto_materializado({'practicas': True})
        self.assertFalse(solo_lectura['puede_operar_asignaturas'])
        self.assertTrue(editable['puede_operar_asignaturas'])
        self.assertEqual(datos_lectura, datos_edicion)
