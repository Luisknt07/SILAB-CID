from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.practicas_integracion import estado_documental_reserva, guias_vencidas_sin_enviar, validar_compuerta_documental
from apps.reservas.presentation.guia_automatizacion import asegurar_borrador_guia_desde_reserva
from apps.reservas.presentation.reservas_publicas import agenda_publica
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


class PasoCincoReservasServiciosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planta = Unidad.objects.create(
            nombre='Planta piloto paso cinco',
            descripcion='Unidad para probar reservas y servicios.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='plantas_piloto',
            slug='planta-paso-cinco',
        )
        cls.laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin migración de árbol',
            descripcion='Unidad que conserva su navegación actual.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-paso-cinco',
        )
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=cls.planta)
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=cls.laboratorio)
        cls.gestor = get_user_model().objects.create_user(
            username='gestor.paso5', password='paso-cinco', is_staff=True,
        )
        cls.solicitante = get_user_model().objects.create_user(
            username='persona.privada.paso5',
            email='privado-paso5@example.com',
            password='paso-cinco',
        )
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.planta,
            usuario=cls.gestor,
            nombre='Responsable de servicios',
            rol='coordinacion',
            publico=True,
            activo=True,
            recibe_reservas=True,
        )
        cls.servicio = FablabService.objects.create(
            code='P5-SRV-ANALISIS',
            nombre='Análisis de muestra',
            descripcion='Caracterización de una muestra alimentaria.',
            unidad=cls.planta,
            tipo_servicio='analisis',
            familia='Análisis',
            resultado_entregado='Informe con resultados y observaciones.',
            requisitos_usuario='Entregar una muestra rotulada.',
            tiempo_estimado_texto='Tres días laborables',
            unidad_cobro='Por muestra',
            responsable=cls.responsable,
            tarifa_base=Decimal('10'),
            horas_equipo_estimadas=Decimal('2'),
            costo_hora_equipo=Decimal('5'),
            horas_mano_obra_estimadas=Decimal('1'),
            costo_hora_mano_obra=Decimal('10'),
            descuento_personal=Decimal('25'),
            descuento_externo=Decimal('0'),
            activo=True,
            publico=True,
        )
        HorarioOperacionUnidad.objects.filter(unidad=cls.planta).delete()
        HorarioOperacionUnidad.objects.create(
            unidad=cls.planta,
            nombre='Lunes de atención',
            dia_semana=0,
            hora_inicio=time(8),
            hora_fin=time(12),
            permite_recursos=True,
            permite_servicios=True,
        )

    def _contenido_modulo(self, response, clave):
        html = response.content.decode()
        desde = html.rindex(f'data-modulo="{clave}"')
        hasta = html.find('class="modulo-carpeta-list', desde)
        return html[desde:hasta if hasta > 0 else None]

    def test_el_arbol_de_la_planta_publica_6_1_a_6_6_y_reserva_6_7_al_gestor(self):
        respuesta = self.client.get(self.planta.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        contenido = self._contenido_modulo(respuesta, 'reservas-servicios')
        for numero in (f'6.{indice}' for indice in range(1, 7)):
            self.assertIn(f'data-seccion="{numero}"', contenido)
        self.assertNotIn('data-seccion="6.7"', contenido)
        self.assertNotIn('data-id="gestionar-laboratorio"', contenido)
        self.assertIn('Abrir sistema de reservas', contenido)
        self.assertIn('Mis reservas', contenido)
        self.assertIn(reverse('catalogo_servicios_unidad', args=[self.planta.slug]), contenido)
        self.assertIn(reverse('agenda_disponibilidad_unidad', args=[self.planta.slug]), contenido)

        self.client.force_login(self.gestor)
        contenido_gestor = self._contenido_modulo(
            self.client.get(self.planta.get_absolute_url()), 'reservas-servicios'
        )
        self.assertIn('data-seccion="6.7"', contenido_gestor)
        self.assertNotIn('data-id="gestionar-laboratorio"', contenido_gestor)

    def test_un_laboratorio_publica_su_propio_arbol_de_reservas_5_1_a_5_7(self):
        respuesta = self.client.get(self.laboratorio.get_absolute_url())
        clave = self.laboratorio.modulos_contenido.get(
            mostrar_herramientas_reserva=True,
        ).clave
        contenido = self._contenido_modulo(respuesta, clave)
        self.assertIn('Reservar el laboratorio', contenido)
        self.assertIn('data-seccion="5.1"', contenido)
        self.assertIn('Catálogo de servicios y tarifas', contenido)
        self.assertNotIn('data-seccion="6.1"', contenido)

    def test_catalogo_usa_los_datos_administrables_y_el_mismo_asistente(self):
        respuesta = self.client.get(
            reverse('catalogo_servicios_unidad', args=[self.planta.slug])
        )
        self.assertEqual(respuesta.status_code, 200)
        for texto in (
            'P5-SRV-ANALISIS',
            'Análisis de muestra',
            'Informe con resultados y observaciones.',
            'Entregar una muestra rotulada.',
            'Tres días laborables',
            'Por muestra',
            'Responsable de servicios',
            '$22.50',
            '$30.00',
        ):
            self.assertContains(respuesta, texto)
        self.assertContains(
            respuesta,
            f'{self.planta.get_absolute_url()}?servicio={self.servicio.pk}#reservas-servicios',
        )
        # El laboratorio también tiene su catálogo: es su sección 5.2.
        self.assertEqual(
            self.client.get(
                reverse('catalogo_servicios_unidad', args=[self.laboratorio.slug])
            ).status_code,
            200,
        )

    def test_agenda_publica_solo_informa_disponible_o_comprometido(self):
        fecha = date(2026, 9, 14)
        Reserva.objects.create(
            laboratorio=self.planta,
            usuario=self.solicitante,
            fecha=fecha,
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='P5-EQ-PRIVADO',
            equipo_nombre='Equipo reservado de forma privada',
            nombre_solicitante='Nombre que no debe publicarse',
            correo_solicitante='secreto@example.com',
            proposito='Proyecto reservado',
            descripcion_proyecto='Información confidencial',
            titulo_solicitud='Título privado',
            estado='confirmada',
        )
        BloqueoAgendaUnidad.objects.create(
            unidad=self.planta,
            tipo='mantenimiento',
            titulo='Motivo técnico privado',
            motivo='Detalle interno que no debe publicarse',
            fecha_inicio=fecha,
            fecha_fin=fecha,
            hora_inicio=time(11),
            hora_fin=time(12),
            alcance='unidad_completa',
            activo=True,
        )
        slots = agenda_publica(self.planta, desde=fecha, dias=1)[0]['slots']
        self.assertEqual(
            [(slot['inicio'].hour, slot['estado']) for slot in slots],
            [(8, 'disponible'), (9, 'comprometido'), (10, 'comprometido'), (11, 'comprometido')],
        )

        respuesta = self.client.get(
            reverse('agenda_disponibilidad_unidad', args=[self.planta.slug]),
            {'desde': fecha.isoformat()},
        )
        serializado = respuesta.content.decode()
        self.assertContains(respuesta, 'Consulta anónima')
        self.assertContains(respuesta, 'comprometido')
        for privado in (
            'Nombre que no debe publicarse',
            'secreto@example.com',
            'Proyecto reservado',
            'Información confidencial',
            'Título privado',
            'Motivo técnico privado',
            'Detalle interno que no debe publicarse',
        ):
            self.assertNotIn(privado, serializado)

    def test_un_servicio_no_acepta_un_responsable_de_otra_unidad(self):
        responsable_ajeno = ResponsableUnidad.objects.create(
            unidad=self.laboratorio,
            nombre='Responsable ajeno',
            email='ajeno@example.com',
        )
        self.servicio.responsable = responsable_ajeno
        with self.assertRaises(ValidationError):
            self.servicio.full_clean()

    @staticmethod
    def _contenido_guia_completo():
        return {
            'asignatura': 'Tecnología de alimentos',
            'carrera_semestre': 'Alimentos · quinto semestre',
            'docente_responsable': 'Docente paso cinco',
            'laboratorio': 'Planta piloto paso cinco',
            'categoria_uso': 'Docencia y práctica curricular',
            'duracion': '2 horas',
            'maximo_estudiantes': '20',
            'resultado_aprendizaje': 'Controla las variables del proceso.',
            'objetivos': 'Ejecutar y documentar el proceso.',
            'procedimiento': ['Preparar', 'Procesar', 'Registrar datos'],
            'resultados_esperados': 'Tabla de datos y observaciones.',
        }

    def test_compuertas_documentales_y_deuda_vencida_siguen_la_especificacion(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica anterior pendiente',
            unidad=self.planta,
            creado_por=self.solicitante,
            estado_publicacion='borrador',
            visibilidad='privada',
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Guía anterior sin enviar',
            es_estructurada=True,
            estado_publicacion='borrador',
            contenido=self._contenido_guia_completo(),
            subido_por=self.solicitante,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.planta,
            usuario=self.solicitante,
            actividad_catalogo=actividad,
            vinculacion_actividad='manual',
            proposito_codigo='docencia_practica',
            proposito='Docencia y práctica curricular',
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo='P5-GUIA',
            equipo_nombre='Práctica con guía',
            nombre_solicitante='Docente paso cinco',
            estado='confirmada',
        )

        estado = estado_documental_reserva(reserva)
        self.assertTrue(estado['lista_para_aprobar'])
        self.assertFalse(estado['lista'])
        validar_compuerta_documental(reserva, 'aprobar')
        with self.assertRaises(ValueError):
            validar_compuerta_documental(reserva, 'completar')
        self.assertEqual(list(guias_vencidas_sin_enviar(self.solicitante)), [guia])

        guia.estado_publicacion = 'revision'
        guia.save(update_fields=['estado_publicacion', 'actualizado_en'])
        with self.assertRaises(ValueError):
            validar_compuerta_documental(reserva, 'completar')
        self.assertFalse(guias_vencidas_sin_enviar(self.solicitante).exists())
        guia.estado_publicacion = 'publicada'
        guia.save(update_fields=['estado_publicacion', 'actualizado_en'])
        validar_compuerta_documental(reserva, 'completar')

    def test_una_guia_publicada_puede_usarse_clonarse_o_crearse_desde_cero(self):
        fuente = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica institucional reutilizable',
            unidad=self.planta,
            creado_por=self.gestor,
            estado_publicacion='publicado',
            visibilidad='unidad',
        )
        publicada = GuiaActividadReserva.objects.create(
            actividad=fuente,
            titulo='Guía institucional reutilizable',
            es_estructurada=True,
            estado_publicacion='publicada',
            es_vigente=True,
            contenido=self._contenido_guia_completo(),
            subido_por=self.gestor,
        )
        adaptacion = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Adaptación propia',
            unidad=self.planta,
            creado_por=self.solicitante,
            estado_publicacion='borrador',
            visibilidad='privada',
        )
        reserva = Reserva.objects.create(
            laboratorio=self.planta,
            usuario=self.solicitante,
            actividad_catalogo=adaptacion,
            vinculacion_actividad='clonada',
            proposito_codigo='docencia_practica',
            proposito='Docencia y práctica curricular',
            fecha=timezone.localdate() + timedelta(days=2),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo='P5-CLON',
            equipo_nombre='Práctica adaptada',
            nombre_solicitante='Docente paso cinco',
            estado='pendiente',
        )

        clon, creada = asegurar_borrador_guia_desde_reserva(
            reserva,
            usuario=self.solicitante,
            guia_origen=publicada,
        )
        self.assertTrue(creada)
        self.assertEqual(clon.guia_origen, publicada)
        self.assertEqual(clon.contenido['objetivos'], publicada.contenido['objetivos'])

        respuesta = self.client.get(self.planta.get_absolute_url())
        html = respuesta.content.decode()
        usar = html.index('value="catalogo"')
        clonar = html.index('value="clonada"')
        crear = html.index('value="manual"')
        self.assertLess(usar, clonar)
        self.assertLess(clonar, crear)
        self.assertContains(respuesta, 'guiasClonablesReservaData')
