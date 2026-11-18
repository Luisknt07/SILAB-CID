import json
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.admin.models import LogEntry
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, CapacidadOperativaUnidad, ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva, ReservaAdjunto, ReservaConsumible, RegistroParticipanteReserva
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.core.models.usuarios_base import UserProfile
from tests.integration.utiles import identificar


class PanelGestionUnidadTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.coordinador = User.objects.create_user(
            username="coordinador-panel",
            password="clave-segura",
            first_name="Ana",
            last_name="Coordinadora",
        )
        cls.responsable = User.objects.create_user(
            username="responsable-panel",
            password="clave-segura",
            first_name="Luis",
            last_name="Técnico",
        )
        cls.usuario_ajeno = User.objects.create_user(
            username="usuario-ajeno-panel",
            password="clave-segura",
        )
        # Personal y solicitantes con sus datos institucionales al día, como
        # exige la plataforma para usar sus funciones.
        for persona in (cls.coordinador, cls.responsable):
            identificar(persona, tipo_usuario="administrativo", carrera="")
        identificar(cls.usuario_ajeno, tipo_usuario="estudiante")
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio con panel operativo",
            descripcion="Unidad usada para comprobar el panel.",
            fecha_inicio=date(2026, 1, 1),
            slug="laboratorio-panel-operativo",
            dependencia="laboratorios",
            administrador=cls.coordinador,
        )
        cls.otra_unidad = Unidad.objects.create(
            nombre="Laboratorio ajeno",
            descripcion="No debe mezclarse en el panel.",
            fecha_inicio=date(2026, 1, 1),
            slug="laboratorio-ajeno-panel",
            dependencia="laboratorios",
        )
        cls.responsable_unidad = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.responsable,
            rol="responsable_tecnico",
            recibe_reservas=True,
            activo=True,
        )
        cls.reserva = Reserva.objects.create(
            laboratorio=cls.unidad,
            usuario=cls.usuario_ajeno,
            fecha=timezone.localdate(),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            equipo_codigo="EQ-PANEL",
            equipo_nombre="Equipo del panel",
            titulo_solicitud="Reserva visible en la agenda",
            estado="pendiente",
        )
        Reserva.objects.create(
            laboratorio=cls.otra_unidad,
            usuario=cls.usuario_ajeno,
            fecha=timezone.localdate(),
            hora_inicio=time(11, 0),
            hora_fin=time(12, 0),
            equipo_codigo="EQ-AJENO",
            equipo_nombre="Equipo ajeno",
            titulo_solicitud="Reserva que no debe aparecer",
            estado="pendiente",
        )
        cls.url = reverse("gestion_unidad", args=[cls.unidad.slug])

    def test_panel_requiere_autenticacion(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_usuario_sin_vinculo_no_puede_gestionar(self):
        self.client.force_login(self.usuario_ajeno)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_coordinador_visualiza_panel_y_datos_solo_de_su_unidad(self):
        self.client.force_login(self.coordinador)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestionar unidad")
        self.assertContains(response, "Reserva visible en la agenda")
        self.assertNotContains(response, "Reserva que no debe aparecer")
        self.assertEqual(response.context["reservas_pendientes"], 1)
        self.assertEqual(response.context["reservas_hoy"], 1)
        activos = self.client.get(self.url, {"view": "recursos", "modo_recursos": "activos"})
        finanzas = self.client.get(self.url, {"view": "recursos", "modo_recursos": "finanzas"})
        self.assertIn("analitica_activos", activos.context)
        self.assertIn("analitica_financiera", finanzas.context)

    def test_responsable_activo_tambien_accede_al_panel(self):
        self.client.force_login(self.responsable)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responsable técnico")

    def test_operaciones_se_abren_dentro_del_visualizador_sin_ir_al_admin(self):
        self.client.force_login(self.coordinador)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for texto in ('Indicadores de la unidad', 'Equipos más utilizados', 'Carga y atenciones del personal', 'Centro de reportes', 'Reservas y agenda', 'Recursos e inventario'):
            self.assertContains(response, texto)
        for clave in ('indicadores', 'reservas', 'recursos', 'reportes'):
            self.assertContains(response, f'data-management-target="{clave}"')
        self.assertContains(response, 'data-management-view="indicadores"')
        self.assertContains(response, 'data-initial-view="indicadores"')
        self.assertNotContains(response, 'data-management-view="reservas"')
        self.assertRegex(response.content.decode(), r'<script\b[^>]*\bsrc="[^"]*/portal/js/pages/unidades/panel_gestion[.]js[?]v=[A-Za-z0-9_-]+"[^>]*></script>')
        self.assertIn('indicadores_utilizacion', response.context)
        self.assertIn('indicadores_portada', response.context)
        self.assertNotIn('reporte_gestion', response.context)
        self.assertNotIn('agenda_semana', response.context)

        reservas = self.client.get(self.url, {'view': 'reservas'})
        for atributo in ('data-reservations-pane="solicitudes"', 'data-reservations-pane="agenda"',
                'data-initial-reservations-mode="agenda"', 'class="unit-console__reservation-command"',
                'class="unit-console__agenda-settings ', 'class="unit-console__secondary-details ',
                'id="reservationManagementDrawer"', 'class="unit-console-drawer__panel"',
                'id="managementAdvancedDecision"',
                'data-reservation-drawer-tab="recursos"', 'data-reservation-drawer-tab="decision"',
                'data-reservation-drawer-pane="decision"', 'id="managementReservationPurposeField"',
                'id="managementEquipmentList"', 'id="managementParticipantList"',
                'data-reservation-action="solicitar_info"', 'data-can-edit-closed-reservations="true"',
                'data-open-reservation-editor', 'id="managementChangeReason"',
                'id="managementOriginalComparison"', 'data-reservation-action="aprobar"',
                'data-reservation-action="actualizar"', 'id="agendaManagementDrawer"',
                'data-agenda-operation-open="horario"', 'data-agenda-operation-open="bloqueo"',
                'class="unit-console__calendar"'):
            self.assertContains(reservas, atributo)
        for texto in ('Agenda visual', 'Bandeja de solicitudes', 'Edición autorizada para la administración de la unidad'):
            self.assertContains(reservas, texto)
        self.assertContains(reservas, reverse('gestion_reserva_detalle', args=[self.unidad.slug, self.reserva.pk]))
        self.assertContains(reservas, 'role="dialog" aria-modal="true" aria-labelledby="reservationManagementTitle"')
        self.assertContains(reservas, 'role="dialog" aria-modal="true" aria-labelledby="agendaManagementTitle"')
        self.assertNotContains(reservas, '<details class="unit-console-drawer__advanced"')
        self.assertIn('agenda_semana', reservas.context)
        self.assertIn('agenda_grid', reservas.context)

        for modo, marcadores in (
            ('activos', ('data-resources-pane="activos"', 'Equipos, espacios y software', 'data-assets-chart="semanal"')),
            ('inventario', ('data-resources-pane="inventario"',)),
            ('finanzas', ('data-resources-pane="finanzas"', 'Ingresos frente a costos', 'data-finance-chart="mensual"')),
        ):
            recursos = self.client.get(self.url, {'view': 'recursos', 'modo_recursos': modo})
            self.assertContains(recursos, 'data-management-view="recursos"')
            for marcador in marcadores:
                self.assertContains(recursos, marcador)
            for destino in ('activos', 'inventario', 'finanzas'):
                self.assertContains(recursos, f'data-resources-mode-target="{destino}"')
                if destino != modo:
                    self.assertNotContains(recursos, f'data-resources-pane="{destino}"')

        reportes = self.client.get(self.url, {'view': 'reportes'})
        self.assertContains(reportes, 'data-management-view="reportes"')
        self.assertContains(reportes, 'id="entregas-documentos"')
        self.assertContains(reportes, 'id="reportes-anexos"')
        for pagina in (response, reservas, recursos, reportes):
            for clave in ('resumen', 'agenda', 'inventario', 'academico'):
                self.assertNotContains(pagina, f'data-management-target="{clave}"')
                self.assertNotContains(pagina, f'data-management-view="{clave}"')
            self.assertNotContains(pagina, 'data-agenda-operation-open="silabo"')
            contenido = pagina.content.decode()
            self.assertEqual(contenido.count('href="/admin/'), contenido.count(f'href="{reverse("admin:directorio_unidades_unidad_change", args=[self.unidad.pk])}"'))

    def test_contador_y_paginacion_incluyen_todas_las_solicitudes_pendientes(self):
        for indice in range(25):
            Reserva.objects.create(
                laboratorio=self.unidad,
                usuario=self.usuario_ajeno,
                fecha=timezone.localdate() + timedelta(days=indice + 1),
                hora_inicio=time(9, 0),
                hora_fin=time(10, 0),
                equipo_codigo=f"EQ-PEND-{indice:02d}",
                equipo_nombre=f"Equipo pendiente {indice:02d}",
                titulo_solicitud=f"Solicitud pendiente {indice:02d}",
                estado="pendiente",
            )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            f"{self.url}?view=reservas&modo_reservas=solicitudes"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reservas_pendientes"], 26)
        self.assertEqual(response.context["reservas_bandeja_pagina"].paginator.count, 26)
        self.assertEqual(len(response.context["reservas_pendientes_lista"]), 10)
        self.assertContains(response, "26 pendientes")
        self.assertContains(response, "Página 1 de 3")
        self.assertContains(response, "Siguiente")

    def test_estado_integral_incluye_vencidas_cierres_y_sin_responsable(self):
        ayer = timezone.localdate() - timedelta(days=1)
        Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=ayer,
            hora_inicio=time(8, 0),
            hora_fin=time(9, 0),
            equipo_codigo="EQ-VENCIDA",
            equipo_nombre="Equipo vencido",
            titulo_solicitud="Solicitud vencida sin decisión",
            estado="pendiente",
        )
        Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=ayer,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            equipo_codigo="EQ-CIERRE",
            equipo_nombre="Equipo pendiente de cierre",
            titulo_solicitud="Atención pendiente de cierre",
            estado="confirmada",
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(self.url)

        resumen = response.context["resumen_reservas"]
        tipos_alerta = {item["tipo"] for item in response.context["alertas_operativas"]}
        esperadas = 1 + int(
            bool(
                self.reserva.fecha_hora_fin
                and self.reserva.fecha_hora_fin < timezone.now()
            )
        )
        self.assertEqual(resumen["pendientes_vencidas"], esperadas)
        self.assertEqual(resumen["cierres_total"], 1)
        self.assertEqual(resumen["sin_asignar_total"], 3)
        self.assertIn("solicitudes_vencidas", tipos_alerta)
        self.assertIn("reservas_sin_cierre", tipos_alerta)
        self.assertIn("reservas_sin_responsable", tipos_alerta)
        self.assertEqual(response.context["tablero"]["estado"]["tono"], "critico")
        self.assertContains(response, "Control operativo de la unidad")
        self.assertContains(response, "Vencidas sin decisión")

    def test_filtro_de_cierre_abre_la_reserva_que_requiere_resultado(self):
        reserva_cierre = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            equipo_codigo="EQ-FILTRO-CIERRE",
            equipo_nombre="Equipo para cerrar",
            titulo_solicitud="Reserva visible al filtrar cierres",
            estado="confirmada",
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            f"{self.url}?view=reservas&modo_reservas=solicitudes&filtro_reservas=cierre"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filtro_reservas"], "cierre")
        self.assertEqual(response.context["reservas_bandeja_pagina"].paginator.count, 1)
        self.assertEqual(response.context["reservas_pendientes_lista"], [reserva_cierre])
        self.assertContains(response, "Cierres operativos por validar")
        self.assertContains(response, "Reserva visible al filtrar cierres")

    def test_filtro_de_riesgo_muestra_motivo_y_accion_directa(self):
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-CAT-RIESGO-PANEL",
            nombre="Impresora detenida",
        )
        equipo = UnidadEquipo.objects.create(
            codigo_unidad="EQ-UNIT-RIESGO-PANEL",
            equipo=catalogo,
            laboratorio=self.unidad,
            estado_unidad="mantenimiento",
        )
        reserva_riesgo = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() + timedelta(days=1),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            equipo_codigo=catalogo.codigo,
            equipo_nombre=catalogo.nombre,
            titulo_solicitud="Reserva afectada por mantenimiento",
            unidades_seleccionadas=json.dumps([{"id": equipo.pk}]),
            estado="confirmada",
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            f"{self.url}?view=reservas&modo_reservas=solicitudes&filtro_reservas=riesgo"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filtro_reservas"], "riesgo")
        self.assertEqual(response.context["resumen_reservas"]["riesgos_total"], 1)
        self.assertEqual(
            response.context["reservas_pendientes_lista"],
            [reserva_riesgo],
        )
        self.assertContains(response, "Reservas con riesgo operativo")
        self.assertContains(response, "está en mantenimiento")
        self.assertContains(response, 'data-reservation-id="')

    def test_ranking_desglosa_las_unidades_fisicas_de_una_reserva_multiple(self):
        self.reserva.estado = "completada"
        self.reserva.resultado_cierre = "atendida"
        self.reserva.detalle_ejecucion = {
            "registrada_en": timezone.now().isoformat(),
        }
        self.reserva.equipo_codigo = "MULTI"
        self.reserva.equipo_nombre = "Múltiples equipos"
        self.reserva.unidades_seleccionadas = json.dumps(
            [
                {"codigo": "EQ-FDM-01", "equipo_nombre": "Impresora FDM"},
                {"codigo": "EQ-SCAN-01", "equipo_nombre": "Escáner 3D"},
            ]
        )
        self.reserva.save()
        self.client.force_login(self.coordinador)

        response = self.client.get(self.url)

        nombres = {
            item["nombre"]
            for item in response.context["indicadores_portada"]["equipos_mas_usados"]
        }
        self.assertEqual(nombres, {"Impresora FDM", "Escáner 3D"})
        self.assertNotIn("Múltiples equipos", nombres)

    def test_reporte_html_respeta_filtros_y_pdf_comparte_la_misma_ruta(self):
        self.client.force_login(self.coordinador)
        query = "?desde=2026-01-01&hasta=2026-12-31&agrupar=estado"

        html = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug]) + query
        )
        pdf = self.client.get(
            reverse("gestion_reporte_unidad_pdf", args=[self.unidad.slug]) + query
        )

        self.assertEqual(html.status_code, 200)
        self.assertContains(html, "Reporte operativo")
        self.assertContains(html, "Reserva visible en la agenda")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_centro_reportes_filtra_busqueda_responsable_y_efectividad(self):
        self.reserva.responsable_asignado = self.responsable_unidad
        self.reserva.estado = "completada"
        self.reserva.resultado_cierre = "atendida"
        self.reserva.detalle_ejecucion = {
            "registrada_en": timezone.now().isoformat(),
        }
        self.reserva.tipo_usuario_solicitante = "estudiante"
        self.reserva.save()
        self.client.force_login(self.coordinador)
        query = (
            f"?desde={self.reserva.fecha:%Y-%m-%d}"
            f"&hasta={self.reserva.fecha:%Y-%m-%d}"
            "&buscar=Reserva+visible"
            f"&responsable={self.responsable_unidad.pk}"
            "&efectividad=efectivas&agrupar=responsable"
        )

        html = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug]) + query
        )
        pdf = self.client.get(
            reverse("gestion_reporte_unidad_pdf", args=[self.unidad.slug]) + query
        )

        self.assertEqual(html.status_code, 200)
        self.assertContains(html, "CRITERIOS APLICADOS")
        self.assertContains(html, "Solo atenciones efectivas")
        self.assertContains(html, "Luis Técnico")
        self.assertContains(html, "Reserva visible en la agenda")
        self.assertEqual(html.context["reporte_gestion"]["metrics"]["confirmed"], 1)
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_boton_gestionar_solo_aparece_a_personal_autorizado(self):
        self.client.force_login(self.coordinador)
        response_autorizada = self.client.get(self.unidad.get_absolute_url())

        self.client.force_login(self.usuario_ajeno)
        response_ajena = self.client.get(self.unidad.get_absolute_url())

        self.assertContains(response_autorizada, "Gestionar laboratorio")
        self.assertContains(response_autorizada, "20261008-seguridad-v1")
        # El gestor entra por el botón de la cabecera; el árbol numerado de la ficha es público.
        self.assertContains(response_autorizada, 'unit-action--management')
        self.assertNotContains(response_autorizada, 'data-id="gestionar-laboratorio"')
        self.assertNotContains(response_ajena, 'unit-action--management')
        self.assertContains(response_autorizada, 'id="gestionLaboratorioModal"')
        self.assertContains(response_autorizada, 'id="gestionLaboratorioContent"')
        self.assertNotContains(response_autorizada, 'id="gestionLaboratorioFrame"')
        self.assertContains(response_autorizada, 'data-ui-click="abrirGestionLaboratorio"')
        self.assertNotContains(response_ajena, "Gestionar laboratorio")

    def test_panel_embebido_usa_el_espacio_del_modal_sin_encabezado_duplicado(self):
        self.client.force_login(self.coordinador)

        response = self.client.get(f"{self.url}?modal=1&fragment=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="unit-console is-embedded"')
        self.assertContains(response, 'data-management-url=')
        self.assertNotContains(response, 'class="unit-console__titlebar"')
        self.assertNotContains(response, "<html")

    def test_enlace_anterior_de_inventario_abre_la_pestana_unificada(self):
        self.client.force_login(self.coordinador)

        response = self.client.get(f"{self.url}?view=inventario")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["vista_gestion"], "recursos")
        self.assertEqual(response.context["modo_recursos"], "inventario")
        self.assertContains(response, 'data-initial-view="recursos"')
        self.assertContains(response, 'data-initial-resources-mode="inventario"')
        self.assertContains(
            response,
            'data-resources-pane="inventario">',
        )
        self.assertNotContains(response, 'data-management-view="inventario"')

    def test_agenda_integra_selector_mensual_y_fecha_controla_la_semana(self):
        self.client.force_login(self.coordinador)
        fecha = self.reserva.fecha.isoformat()

        response = self.client.get(
            f"{self.url}?modal=1&fragment=1&view=agenda&semana={fecha}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unit-console__month")
        self.assertContains(response, "BUSCAR FECHA")
        self.assertContains(response, 'data-management-load')
        self.assertContains(response, 'aria-current="date"')
        self.assertContains(response, "is-selected-day")
        self.assertEqual(response.context["fecha_seleccionada"], self.reserva.fecha)
        self.assertEqual(response.context["vista_gestion"], "reservas")
        self.assertEqual(response.context["modo_reservas"], "agenda")
        self.assertEqual(len(response.context["calendario_mensual"]["dias_semana"]), 7)
        self.assertTrue(
            any(
                dia["es_seleccionada"] and dia["reservas"] == 1
                for semana in response.context["calendario_mensual"]["semanas"]
                for dia in semana
            )
        )

    def test_agenda_apila_reservas_simultaneas_en_la_misma_hora(self):
        Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.coordinador,
            fecha=self.reserva.fecha,
            hora_inicio=self.reserva.hora_inicio,
            hora_fin=self.reserva.hora_fin,
            equipo_codigo="EQ-PANEL-02",
            equipo_nombre="Segundo equipo simultáneo",
            titulo_solicitud="Reserva simultánea visible",
            estado="confirmada",
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            f"{self.url}?view=agenda&semana={self.reserva.fecha.isoformat()}"
        )

        # Cada reserva es una franja continua; las simultáneas comparten el
        # día en carriles distintos en vez de repetirse hora por hora.
        dia = next(
            dia
            for dia in response.context["agenda_grid"]["dias"]
            if dia["fecha"] == self.reserva.fecha
        )
        self.assertEqual(len(dia["eventos"]), 2)
        self.assertEqual({evento["carril"] for evento in dia["eventos"]}, {0, 1})
        self.assertEqual({evento["carriles"] for evento in dia["eventos"]}, {2})
        self.assertEqual({evento["filas"] for evento in dia["eventos"]}, {1})
        self.assertContains(response, "Reserva visible en la agenda")
        self.assertContains(response, "Reserva simultánea visible")

    def test_agenda_se_recorta_a_la_atencion_aunque_exista_un_evento_de_dia_completo(self):
        configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(
            unidad=self.unidad,
        )
        configuracion.hora_apertura_atencion = time(7, 0)
        configuracion.hora_cierre_atencion = time(17, 0)
        configuracion.save(update_fields=[
            'hora_apertura_atencion', 'hora_cierre_atencion',
        ])
        Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.coordinador,
            fecha=self.reserva.fecha,
            hora_inicio=time(0, 0),
            hora_fin=time(23, 59),
            equipo_codigo='UNIDAD-COMPLETA',
            equipo_nombre='Unidad completa',
            titulo_solicitud='Actividad administrativa de día completo',
            estado='confirmada',
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            f"{self.url}?view=reservas&modo_reservas=agenda&semana={self.reserva.fecha.isoformat()}"
        )

        self.assertEqual(
            response.context['agenda_grid']['horas'],
            [f'{hora:02d}:00' for hora in range(7, 17)],
        )
        self.assertNotContains(response, '<span>00:00</span>', html=True)

    def test_fin_de_semana_solo_aparece_con_activacion_o_excepcion(self):
        lunes = self.reserva.fecha - timedelta(days=self.reserva.fecha.weekday())
        sabado = lunes + timedelta(days=5)
        # Igual que en la prueba del periodo: si hoy cae en fin de semana, las
        # reservas del fixture harian visible ese dia sin jornada activada.
        Reserva.objects.filter(
            laboratorio=self.unidad, fecha__week_day__in=[1, 7],
        ).update(fecha=lunes)
        self.client.force_login(self.coordinador)

        ordinaria = self.client.get(
            f"{self.url}?view=agenda&semana={lunes.isoformat()}"
        )
        self.assertEqual(len(ordinaria.context["agenda_semana"]), 5)

        BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            tipo="mantenimiento",
            titulo="Excepción administrativa del sábado",
            fecha_inicio=sabado,
            fecha_fin=sabado,
            dia_completo=True,
            alcance="unidad_completa",
            creado_por=self.coordinador,
        )
        con_sabado = self.client.get(
            f"{self.url}?view=agenda&semana={lunes.isoformat()}"
        )
        self.assertEqual(len(con_sabado.context["agenda_semana"]), 6)
        self.assertEqual(con_sabado.context["agenda_semana"][-1]["dia_semana"], 5)

        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            nombre="Apertura excepcional dominical",
            dia_semana=6,
            hora_inicio=time(9, 0),
            hora_fin=time(12, 0),
        )
        fin_semana_completo = self.client.get(
            f"{self.url}?view=agenda&semana={lunes.isoformat()}"
        )
        self.assertEqual(len(fin_semana_completo.context["agenda_semana"]), 7)
        self.assertEqual(
            fin_semana_completo.context["agenda_semana"][-1]["dia_semana"],
            6,
        )

    def test_jornada_de_fin_de_semana_respeta_el_periodo_de_su_calendario(self):
        lunes_actual = self.reserva.fecha - timedelta(
            days=self.reserva.fecha.weekday()
        )
        # El fixture crea reservas en la fecha de hoy. Si hoy cae en fin de
        # semana, la agenda muestra ese dia por tener una reserva y la prueba
        # dejaria de medir jornadas. Se mueven a lunes para aislar el horario.
        Reserva.objects.filter(
            laboratorio=self.unidad, fecha__week_day__in=[1, 7],
        ).update(fecha=lunes_actual)
        lunes_periodo = lunes_actual + timedelta(days=28)
        periodo = PeriodoAcademico.objects.create(
            codigo=f"{lunes_periodo.year}-E-PANEL",
            nombre="Período excepcional del panel",
            anio_referencia=lunes_periodo.year,
            ciclo="E",
            tipo="extraordinario",
            ambito="institucional",
            semanas_planificadas=3,
            estado="publicado",
        )
        VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            fecha_inicio_clases=lunes_periodo,
            fecha_fin_clases=lunes_periodo + timedelta(days=13),
            fecha_fin_periodo=lunes_periodo + timedelta(days=20),
            vigente=True,
        )
        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            periodo=periodo,
            nombre="Sábado del período excepcional",
            dia_semana=5,
            hora_inicio=time(9, 0),
            hora_fin=time(12, 0),
        )
        self.client.force_login(self.coordinador)

        fuera_del_periodo = self.client.get(
            f"{self.url}?view=agenda&semana={lunes_actual.isoformat()}"
        )
        dentro_del_periodo = self.client.get(
            f"{self.url}?view=agenda&semana={lunes_periodo.isoformat()}"
        )

        self.assertEqual(len(fuera_del_periodo.context["agenda_semana"]), 5)
        self.assertEqual(len(dentro_del_periodo.context["agenda_semana"]), 6)
        self.assertEqual(
            dentro_del_periodo.context["agenda_semana"][-1]["dia_semana"],
            5,
        )

    def test_coordinador_edita_y_reprograma_una_reserva_desde_el_panel(self):
        self.reserva.motivo = "Necesidad original del usuario"
        self.reserva.descripcion_proyecto = "Descripción original"
        self.reserva.requisitos_especiales = "Requisito original"
        self.reserva.save()
        nueva_fecha = self.reserva.fecha + timedelta(days=1)
        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            dia_semana=nueva_fecha.weekday(),
            hora_inicio=time(8, 0),
            hora_fin=time(17, 0),
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "actualizar",
                "fecha": nueva_fecha.isoformat(),
                "hora_inicio": "12:00",
                "hora_fin": "14:00",
                "titulo_solicitud": "Reserva reprogramada desde el panel",
                "numero_participantes": "3",
                "motivo": "Necesidad corregida por coordinación",
                "descripcion_proyecto": "Descripción corregida",
                "requisitos_especiales": "Requisito corregido",
                "justificacion_cambio": "Cambio coordinado con el solicitante.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.fecha, nueva_fecha)
        self.assertEqual(self.reserva.hora_inicio, time(12, 0))
        self.assertEqual(self.reserva.hora_fin, time(14, 0))
        self.assertEqual(self.reserva.duracion, 2)
        self.assertEqual(self.reserva.numero_participantes, 3)
        self.assertEqual(
            self.reserva.titulo_solicitud,
            "Reserva reprogramada desde el panel",
        )
        self.assertEqual(self.reserva.motivo, "Necesidad corregida por coordinación")
        auditoria = RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad,
            entidad=self.reserva._meta.label,
            objeto_id=str(self.reserva.pk),
            accion="actualizar",
        ).latest("creado_en")
        self.assertEqual(auditoria.usuario, self.coordinador)
        self.assertEqual(auditoria.datos_anteriores["titulo"], "Reserva visible en la agenda")
        self.assertEqual(
            auditoria.datos_nuevos["titulo"],
            "Reserva reprogramada desde el panel",
        )
        self.assertEqual(auditoria.datos_anteriores["motivo"], "Necesidad original del usuario")
        detalle = self.client.get(
            reverse(
                "gestion_reserva_detalle",
                args=[self.unidad.slug, self.reserva.pk],
            )
        ).json()["reserva"]
        cambios = detalle["seguimiento"]["notas"][0]["cambios"]
        cambios_desde_original = detalle["seguimiento"]["comparacion_original"]
        self.assertTrue(
            any(
                cambio["campo"] == "Título"
                and cambio["anterior"] == "Reserva visible en la agenda"
                and cambio["nuevo"] == "Reserva reprogramada desde el panel"
                for cambio in cambios
            )
        )
        self.assertTrue(
            any(
                cambio["campo"] == "Título"
                and cambio["anterior"] == "Reserva visible en la agenda"
                and cambio["nuevo"] == "Reserva reprogramada desde el panel"
                for cambio in cambios_desde_original
            )
        )
        self.assertTrue(
            LogEntry.objects.filter(
                object_id=str(self.reserva.pk),
                change_message__contains="Reserva actualizada",
            ).exists()
        )

    def test_edicion_integral_sincroniza_participantes_insumos_archivos_y_trazabilidad(self):
        participante = get_user_model().objects.create_user(
            username="participante-integral",
            email="participante.integral@upec.edu.ec",
            first_name="Elena",
            last_name="Participante",
        )
        participante.profile.tipo_usuario = "administrativo"
        participante.profile.facultad = "administracion_central"
        participante.profile.save()
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-INTEGRAL",
            nombre="Material para edición integral",
            unidad_medida="g",
            stock_total="500.000",
            precio_unitario=Decimal("0.03"),
        )
        nueva_fecha = self.reserva.fecha + timedelta(days=2)
        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            dia_semana=nueva_fecha.weekday(),
            hora_inicio=time(8, 0),
            hora_fin=time(17, 0),
            permite_recursos=True,
            permite_servicios=True,
        )
        self.reserva.tipo_solicitud = "servicio"
        self.reserva.modalidad_servicio = "modelo_listo"
        self.reserva.save(update_fields=["tipo_solicitud", "modalidad_servicio"])
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "actualizar",
                "fecha": nueva_fecha.isoformat(),
                "hora_inicio": "13:00",
                "hora_fin": "15:00",
                "titulo_solicitud": "Solicitud integral corregida",
                "motivo": "Corrección validada con el usuario",
                "descripcion_proyecto": "Expediente técnico completo.",
                "requisitos_especiales": "Utilizar elementos de protección.",
                "proposito_codigo": "docencia_practica",
                "justificacion_cambio": "Se completó la información operativa.",
                "participantes_seleccionados": json.dumps(
                    [{"id": participante.pk, "asistencia": "asistio"}]
                ),
                "asistencia_solicitante": "asistio",
                "provision_consumibles": "unidad",
                "alcance_beneficiario": "dependencia_upec",
                "entidad_beneficiaria": "Dirección de innovación",
                "modalidad_servicio": "diseno_completo",
                "costo_estimado": "125.50",
                "descuento_aplicado": "10",
                "metodo_pago": "transferencia",
                "cotizacion_aceptada": "on",
                "consumibles_json": json.dumps(
                    [
                        {
                            "id": consumible.pk,
                            "solicitada": "120.000",
                            "aprobada": "110.000",
                            "consumida": "25.000",
                            "metodo": "estimacion",
                        }
                    ]
                ),
                "archivos_tecnicos": SimpleUploadedFile(
                    "modelo-prueba.pdf",
                    b"%PDF-1.4\n% archivo de prueba",
                    content_type="application/pdf",
                ),
                "indicaciones_archivos_nuevos": "Abrir con un visor PDF.",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.numero_participantes, 2)
        self.assertEqual(list(self.reserva.participantes.all()), [participante])
        self.assertEqual(self.reserva.provision_consumibles, "unidad")
        self.assertEqual(self.reserva.modalidad_servicio, "diseno_completo")
        self.assertEqual(str(self.reserva.costo_estimado), "3.30")
        self.assertEqual(str(self.reserva.descuento_aplicado), "0.00")
        self.assertTrue(self.reserva.cotizacion_aceptada)
        asistencias = dict(
            self.reserva.registros_participantes.values_list(
                "usuario_id", "asistencia"
            )
        )
        self.assertEqual(asistencias[self.reserva.usuario_id], "asistio")
        self.assertEqual(asistencias[participante.pk], "asistio")
        fila_consumible = ReservaConsumible.objects.get(
            reserva=self.reserva,
            consumible=consumible,
        )
        self.assertEqual(str(fila_consumible.cantidad_solicitada), "120.000")
        self.assertEqual(str(fila_consumible.cantidad_consumida), "25.000")
        self.assertTrue(
            ReservaAdjunto.objects.filter(
                reserva=self.reserva,
                nombre_original="modelo-prueba.pdf",
            ).exists()
        )
        auditoria = RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad,
            objeto_id=str(self.reserva.pk),
            accion="actualizar",
        ).latest("creado_en")
        self.assertIn("Elena Participante", auditoria.datos_nuevos["participantes_identificados"])
        self.assertTrue(
            any("Material para edición integral" in item for item in auditoria.datos_nuevos["consumibles"])
        )
        self.assertIn("modelo-prueba.pdf", auditoria.datos_nuevos["archivos"])

    def test_permisos_granulares_separan_agenda_de_reservas_y_otros_modulos(self):
        self.responsable_unidad.permisos_operativos = {
            "reservas": False,
            "agenda": True,
            "recursos": False,
            "mantenimiento": False,
            "inventario": False,
            "practicas": False,
            "reportes": False,
            "configuracion": False,
            "corregir_cerradas": False,
        }
        self.responsable_unidad.save(update_fields=["permisos_operativos"])
        self.client.force_login(self.responsable)

        panel = self.client.get(self.url)
        reserva = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {"accion": "aprobar"},
        )
        agenda = self.client.post(
            reverse("gestion_agenda_accion", args=[self.unidad.slug]),
            {
                "entidad": "horario",
                "accion": "guardar",
                "nombre": "Jornada gestionada por permiso específico",
                "dia_semana": "3",
                "hora_inicio": "08:00",
                "hora_fin": "12:00",
                "permite_recursos": "on",
                "activo": "on",
            },
        )
        inventario = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {"modulo": "inventario"},
        )
        reporte = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
        )
        detalle_reserva = self.client.get(
            reverse(
                "gestion_reserva_detalle",
                args=[self.unidad.slug, self.reserva.pk],
            )
        )

        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context["vista_gestion"], "reservas")
        secciones = {
            item["clave"]: item["habilitada"]
            for item in panel.context["secciones_gestion"]
        }
        self.assertTrue(secciones["reservas"])
        self.assertFalse(secciones["indicadores"])
        self.assertFalse(secciones["practicas"])
        self.assertFalse(secciones["configuracion"])
        self.assertContains(panel, 'data-agenda-operation-open="bloqueo"')
        self.assertNotContains(panel, "Revisar y gestionar")
        self.assertEqual(reserva.status_code, 403)
        self.assertEqual(agenda.status_code, 200)
        self.assertEqual(inventario.status_code, 403)
        self.assertEqual(reporte.status_code, 403)
        self.assertEqual(detalle_reserva.status_code, 403)

    def test_permiso_de_configuracion_no_convierte_en_administrador_principal(self):
        self.responsable_unidad.permisos_operativos = {
            "configuracion": True,
        }
        self.responsable_unidad.save(update_fields=["permisos_operativos"])
        self.client.force_login(self.responsable)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "responsable",
                "nombre": "Persona que no debe crearse",
                "rol": "laboratorista",
                "email": "no-creado@citt.test",
                "activo": "on",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            ResponsableUnidad.objects.filter(
                unidad=self.unidad,
                email="no-creado@citt.test",
            ).exists()
        )

    def test_administrador_corrige_reserva_cerrada_y_conserva_estado(self):
        nueva_fecha = self.reserva.fecha + timedelta(days=2)
        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            dia_semana=nueva_fecha.weekday(),
            hora_inicio=time(8, 0),
            hora_fin=time(17, 0),
        )
        self.reserva.estado = "completada"
        self.reserva.resultado_cierre = "atendida"
        self.reserva.save()
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "actualizar",
                "fecha": nueva_fecha.isoformat(),
                "hora_inicio": "13:00",
                "hora_fin": "15:00",
                "titulo_solicitud": "Corrección posterior al cierre",
                "numero_participantes": "2",
                "proposito_codigo": "docencia_practica",
                "motivo": "Corrección administrativa",
                "descripcion_proyecto": "Dato corregido después de verificar el acta.",
                "requisitos_especiales": "",
                "justificacion_cambio": "Se contrastó con el registro físico del laboratorio.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "completada")
        self.assertEqual(self.reserva.titulo_solicitud, "Corrección posterior al cierre")
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                usuario=self.coordinador,
                objeto_id=str(self.reserva.pk),
                descripcion__contains="registro físico",
            ).exists()
        )

    def test_administrador_regulariza_cierre_antiguo_antes_de_reportarlo(self):
        self.reserva.fecha = timezone.localdate() - timedelta(days=1)
        self.reserva.estado = "completada"
        self.reserva.resultado_cierre = ""
        self.reserva.detalle_ejecucion = {}
        self.reserva.save()
        self.assertFalse(self.reserva.es_efectiva)
        self.assertTrue(self.reserva.requiere_regularizacion_operativa)
        self.client.force_login(self.coordinador)

        bandeja = self.client.get(
            f"{self.url}?view=reservas&modo_reservas=solicitudes&filtro_reservas=cierre"
        )
        respuesta = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "10:00",
                "ejecucion_hora_fin": "11:00",
                "ejecucion_asistentes_total": "1",
                "ejecucion_cumplimiento": "si",
                "ejecucion_consumibles_json": "[]",
                "ejecucion_observaciones": "Cierre regularizado desde el acta física.",
            },
        )

        self.assertEqual(bandeja.status_code, 200)
        self.assertContains(bandeja, "Reserva visible en la agenda")
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.reserva.refresh_from_db()
        self.assertTrue(self.reserva.es_efectiva)
        self.assertFalse(self.reserva.requiere_regularizacion_operativa)
        self.assertEqual(self.reserva.detalle_ejecucion["asistentes_total"], 1)

    def test_responsable_no_puede_corregir_una_reserva_cerrada(self):
        self.reserva.estado = "completada"
        self.reserva.save(update_fields=["estado"])
        self.client.force_login(self.responsable)

        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "actualizar",
                "fecha": self.reserva.fecha.isoformat(),
                "hora_inicio": "10:00",
                "hora_fin": "11:00",
                "titulo_solicitud": "Cambio no autorizado",
                "numero_participantes": "1",
                "proposito_codigo": "docencia_practica",
                "justificacion_cambio": "Intento fuera de permisos.",
            },
        )

        self.assertEqual(response.status_code, 409)

    def test_coordinador_crea_edita_y_desactiva_jornada_desde_el_panel(self):
        self.client.force_login(self.coordinador)
        url = reverse("gestion_agenda_accion", args=[self.unidad.slug])

        creada = self.client.post(
            url,
            {
                "entidad": "horario",
                "accion": "guardar",
                "nombre": "Apertura administrativa sabatina",
                "dia_semana": "5",
                "hora_inicio": "09:00",
                "hora_fin": "13:00",
                "permite_recursos": "on",
                "permite_servicios": "on",
                "activo": "on",
            },
        )

        self.assertEqual(creada.status_code, 200)
        horario = HorarioOperacionUnidad.objects.get(
            pk=creada.json()["registro"]["id"]
        )
        self.assertEqual(horario.dia_semana, 5)
        self.assertTrue(horario.activo)

        editada = self.client.post(
            url,
            {
                "entidad": "horario",
                "accion": "guardar",
                "registro_id": horario.pk,
                "nombre": "Apertura sabatina actualizada",
                "dia_semana": "5",
                "hora_inicio": "10:00",
                "hora_fin": "14:00",
                "permite_recursos": "on",
                "activo": "on",
            },
        )
        self.assertEqual(editada.status_code, 200)
        horario.refresh_from_db()
        self.assertEqual(horario.nombre, "Apertura sabatina actualizada")
        self.assertFalse(horario.permite_servicios)

        desactivada = self.client.post(
            url,
            {
                "entidad": "horario",
                "accion": "desactivar",
                "registro_id": horario.pk,
            },
        )
        self.assertEqual(desactivada.status_code, 200)
        horario.refresh_from_db()
        self.assertFalse(horario.activo)

    def test_coordinador_registra_bloqueo_desde_el_panel(self):
        self.client.force_login(self.coordinador)
        fecha = self.reserva.fecha + timedelta(days=2)

        response = self.client.post(
            reverse("gestion_agenda_accion", args=[self.unidad.slug]),
            {
                "entidad": "bloqueo",
                "accion": "guardar",
                "tipo": "mantenimiento",
                "titulo": "Mantenimiento eléctrico programado",
                "motivo": "Revisión preventiva de la instalación.",
                "fecha_inicio": fecha.isoformat(),
                "fecha_fin": fecha.isoformat(),
                "dia_completo": "on",
                "alcance": "unidad_completa",
                "bloquea_recursos": "on",
                "bloquea_servicios": "on",
                "visible_en_agenda": "on",
                "activo": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        bloqueo = BloqueoAgendaUnidad.objects.get(
            pk=response.json()["registro"]["id"]
        )
        self.assertEqual(bloqueo.unidad, self.unidad)
        self.assertTrue(bloqueo.dia_completo)
        self.assertEqual(bloqueo.creado_por, self.coordinador)

    def test_el_expediente_del_panel_trae_recorrido_y_documentos(self):
        self.client.force_login(self.coordinador)

        detalle = self.client.get(
            reverse("gestion_reserva_detalle", args=[self.unidad.slug, self.reserva.pk])
        ).json()["reserva"]

        linea = detalle["linea_tiempo"]
        self.assertEqual(linea["etapa_actual"], "revision")
        self.assertEqual(
            [paso["codigo"] for paso in linea["pasos"]],
            ["solicitud", "revision", "confirmada", "ejecucion", "cierre"],
        )
        documentos = detalle["documentos"]
        self.assertIn("fragmento=1", documentos["comprobante_url"])
        self.assertIn("inline=1", documentos["comprobante_pdf_url"])

        panel = self.client.get(self.url, {"view": "reservas"})
        self.assertContains(panel, 'id="managementTimeline"')
        self.assertContains(panel, 'data-management-document="comprobante"')
        self.assertContains(panel, 'id="managementDocumentViewer"')

    def test_la_tarjeta_de_agenda_resume_recurso_persona_categoria_y_estado(self):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate(),
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            equipo_codigo="EQ-TARJETA",
            equipo_nombre="Impresora 3D FDM",
            titulo_solicitud=(
                "Solicitud de recursos: Impresora 3D FDM + PrusaSlicer + "
                "Área de impresión 3D · Investigación, desarrollo e innovación"
            ),
            tipo_usuario_solicitante="docente",
            proposito_codigo="investigacion_innovacion",
            proposito="Investigación",
            estado="confirmada",
        )

        # El nombre corto deja solo el recurso; prefijo y propósito se muestran aparte.
        self.assertEqual(reserva.resumen_solicitud, "Impresora 3D FDM + PrusaSlicer +1")
        self.assertEqual(reserva.tipo_usuario_solicitante_corto, "Docente")
        self.assertEqual(reserva.proposito_corto, "Investigación")

        self.client.force_login(self.coordinador)
        panel = self.client.get(
            self.url,
            {"view": "reservas", "modo_reservas": "agenda"},
        )

        self.assertContains(panel, "Impresora 3D FDM + PrusaSlicer +1")
        self.assertContains(panel, "unit-console__calendar-event-who")
        self.assertContains(panel, "unit-console__calendar-event-meta")
        self.assertContains(
            panel,
            self.usuario_ajeno.get_full_name() or self.usuario_ajeno.username,
        )
        self.assertContains(panel, "<em>Docente</em>", html=False)
        self.assertContains(panel, "<span>Investigación</span>", html=False)
        self.assertContains(panel, "<b>Confirmada</b>", html=False)

    def test_un_titulo_escrito_a_mano_se_conserva_en_la_tarjeta(self):
        self.assertEqual(
            self.reserva.resumen_solicitud,
            "Reserva visible en la agenda",
        )
        self.assertEqual(
            self.reserva.tipo_usuario_solicitante_corto,
            "Usuario registrado",
        )
        # Sin código de propósito se conserva el texto guardado en la reserva.
        self.assertEqual(self.reserva.proposito_corto, self.reserva.proposito)

    def test_bloqueo_desde_el_calendario_solo_pide_tipo_y_motivo(self):
        self.client.force_login(self.coordinador)
        fecha = self.reserva.fecha + timedelta(days=3)

        response = self.client.post(
            reverse("gestion_agenda_accion", args=[self.unidad.slug]),
            {
                "entidad": "bloqueo",
                "accion": "guardar",
                "tipo": "limpieza",
                "motivo": "Limpieza de la cabina de resina.",
                "fecha_inicio": fecha.isoformat(),
                "fecha_fin": fecha.isoformat(),
                "hora_inicio": "10:00",
                "hora_fin": "12:00",
                "alcance": "unidad_completa",
                "bloquea_recursos": "on",
                "bloquea_servicios": "on",
                "visible_en_agenda": "on",
                "activo": "on",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        bloqueo = BloqueoAgendaUnidad.objects.get(pk=response.json()["registro"]["id"])
        self.assertEqual(bloqueo.titulo, f"{bloqueo.get_tipo_display()} · {fecha:%d/%m/%Y}")
        self.assertEqual(bloqueo.tipo, "limpieza")
        self.assertEqual(bloqueo.motivo, "Limpieza de la cabina de resina.")
        self.assertFalse(bloqueo.dia_completo)

        panel = self.client.get(
            reverse("gestion_unidad", args=[self.unidad.slug]),
            {"view": "reservas", "modo_reservas": "agenda"},
        )
        self.assertContains(panel, "data-block-selection-bar")
        self.assertContains(panel, "data-block-slot")
        self.assertContains(panel, "data-block-advanced")
        self.assertContains(panel, "¿Para qué se bloquea?")

    def test_cancelar_desde_el_panel_conserva_la_reserva_con_su_motivo(self):
        self.client.force_login(self.coordinador)
        self.reserva.estado = "pendiente"
        self.reserva.save(update_fields=["estado"])

        response = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, self.reserva.pk]),
            {"accion": "cancelar", "observacion": "Equipo en reparación imprevista."},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "cancelada")
        self.assertEqual(self.reserva.origen_cancelacion, "laboratorio")
        self.assertEqual(self.reserva.cancelada_por, self.coordinador)
        self.assertEqual(self.reserva.motivo_cancelacion, "Equipo en reparación imprevista.")
        self.assertIn("Reserva cancelada por el laboratorio: Equipo", self.reserva.observaciones_validacion)

    def test_usuario_ajeno_no_puede_mutar_la_agenda(self):
        self.client.force_login(self.usuario_ajeno)

        response = self.client.post(
            reverse("gestion_agenda_accion", args=[self.unidad.slug]),
            {"entidad": "horario", "accion": "guardar"},
        )

        self.assertEqual(response.status_code, 403)

    def _crear_equipo_operativo(self):
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-CAT-PANEL",
            nombre="Equipo operativo del panel",
        )
        return UnidadEquipo.objects.create(
            codigo_unidad="EQ-UNIT-PANEL",
            equipo=catalogo,
            laboratorio=self.unidad,
        )

    def test_panel_actualiza_equipo_espacio_y_software(self):
        equipo = self._crear_equipo_operativo()
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad,
            codigo="ESP-PANEL",
            nombre="Espacio del panel",
            capacidad=4,
        )
        software = SoftwareDisponible.objects.create(
            unidad=self.unidad,
            nombre="Software del panel",
            licencias_totales=5,
            licencias_disponibles=5,
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        equipo_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "equipo",
                "registro_id": equipo.pk,
                "estado_unidad": "mantenimiento",
                "ubicacion_especifica": "Mesa técnica 4",
                "observaciones": "Revisión preventiva.",
                "activa": "on",
            },
        )
        espacio_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "espacio",
                "registro_id": espacio.pk,
                "capacidad": "8",
                "ubicacion": "Bloque B",
                "descripcion_publica": "Área actualizada desde el panel.",
                "activo": "on",
            },
        )
        software_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "software",
                "registro_id": software.pk,
                "licencias_totales": "10",
                "licencias_disponibles": "7",
                "instrucciones_acceso": "Solicitar credenciales al responsable.",
                "requiere_reserva": "on",
                "activo": "on",
            },
        )

        self.assertEqual(equipo_response.status_code, 200)
        self.assertEqual(espacio_response.status_code, 200)
        self.assertEqual(software_response.status_code, 200)
        equipo.refresh_from_db()
        espacio.refresh_from_db()
        software.refresh_from_db()
        self.assertEqual(equipo.estado_unidad, "mantenimiento")
        self.assertEqual(equipo.ubicacion_especifica, "Mesa técnica 4")
        self.assertEqual(espacio.capacidad, 8)
        self.assertFalse(espacio.reservable)
        self.assertEqual(software.licencias_disponibles, 7)

    def test_panel_crea_vincula_y_archiva_espacios_software_y_equipos(self):
        equipo = self._crear_equipo_operativo()
        equipo.equipo.imagen_catalogo = (
            "img/catalogo/fablab/equipos/impresora-3d-fdm.png"
        )
        equipo.equipo.save(update_fields=["imagen_catalogo"])
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PLA-REL-PANEL",
            nombre="PLA vinculado",
            familia="Filamentos",
            cantidad_por_presentacion="1000",
            unidad_medida="g",
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        espacio_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "espacio",
                "codigo": "ESP-REL-PANEL",
                "nombre": "Estación FDM vinculada",
                "tipo": "estacion",
                "politica_reserva": "tecnico",
                "capacidad": "3",
                "ubicacion": "Bloque B · Mesa 2",
                "equipos_asociados": [str(equipo.pk)],
                "reservable": "on",
                "activo": "on",
            },
        )
        self.assertEqual(espacio_response.status_code, 200, espacio_response.content)
        espacio = EspacioReservable.objects.get(codigo="ESP-REL-PANEL")
        self.assertEqual(list(espacio.equipos_asociados.all()), [equipo])

        software_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "software",
                "codigo": "SW-REL-PANEL",
                "nombre": "Laminador vinculado",
                "version": "2026",
                "tipo_recurso": "software",
                "tipo_acceso": "instalacion",
                "licencias_totales": "5",
                "licencias_disponibles": "5",
                "equipos_instalados": [str(equipo.pk)],
                "requiere_reserva": "on",
                "activo": "on",
            },
        )
        self.assertEqual(software_response.status_code, 200, software_response.content)
        software = SoftwareDisponible.objects.get(codigo="SW-REL-PANEL")
        self.assertEqual(list(software.equipos_instalados.all()), [equipo])

        equipo_response = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "equipo",
                "registro_id": equipo.pk,
                "estado_unidad": "disponible",
                "espacios_asociados": [str(espacio.pk)],
                "software_asociado": [str(software.pk)],
                "consumibles_compatibles": [str(consumible.pk)],
                "activa": "on",
            },
        )
        self.assertEqual(equipo_response.status_code, 200, equipo_response.content)
        equipo.refresh_from_db()
        self.assertEqual(list(equipo.espacios_asociados.all()), [espacio])
        self.assertEqual(list(equipo.software_instalado.all()), [software])
        self.assertEqual(list(consumible.equipos_compatibles.all()), [equipo.equipo])

        panel = self.client.get(f"{self.url}?view=recursos&modo_recursos=activos")
        self.assertContains(panel, "img/catalogo/fablab/equipos/impresora-3d-fdm.png")
        self.assertContains(panel, f'data-field-software_asociado="{software.pk}"')
        opciones = self.client.get(reverse("gestion_recursos_buscar", args=[self.unidad.slug]), {"tipo": "software", "ids": software.pk})
        self.assertEqual(opciones.json()["items"][0]["text"], "Laminador vinculado · SW-REL-PANEL")
        self.assertContains(panel, f'data-field-consumibles_compatibles="{consumible.pk}"')
        insumos = self.client.get(reverse("gestion_recursos_buscar", args=[self.unidad.slug]), {"tipo": "insumos", "ids": consumible.pk})
        self.assertIn("PLA vinculado", insumos.json()["items"][0]["text"])
        self.assertContains(panel, "Equipos, espacios y software")
        self.assertContains(panel, 'data-assets-chart="semanal"')
        self.assertContains(panel, "unit-console__availability-card")
        self.assertIn("analitica_activos", panel.context)

        archived_space = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "espacio",
                "registro_id": espacio.pk,
                "accion": "desactivar",
            },
        )
        archived_software = self.client.post(
            url,
            {
                "modulo": "recursos",
                "entidad": "software",
                "registro_id": software.pk,
                "accion": "desactivar",
            },
        )
        self.assertEqual(archived_space.status_code, 200)
        self.assertEqual(archived_software.status_code, 200)
        espacio.refresh_from_db()
        software.refresh_from_db()
        self.assertFalse(espacio.activo)
        self.assertFalse(software.activo)

    def test_panel_incorpora_unidad_fisica_de_modelo_existente(self):
        catalogo = EquiposServicios.objects.create(
            codigo="CAT-IMP-TEST",
            nombre="Impresora de prueba",
            marca="UPEC Lab",
            modelo="FDM 01",
        )
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad,
            codigo="ESP-IMP-TEST",
            nombre="Área de impresión",
            capacidad=3,
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "recursos",
                "entidad": "equipo",
                "equipo_catalogo_id": catalogo.pk,
                "codigo_unidad": "UNIT-IMP-TEST-01",
                "numero_serie": "SERIE-001",
                "estado_unidad": "disponible",
                "ubicacion_especifica": "Mesa FDM 1",
                "origen_adquisicion": "compra_publica",
                "fecha_adquisicion": "2026-08-20",
                "documento_adquisicion": "ORDEN-UPEC-2026-001",
                "valor_referencial": "2850.75",
                "espacios_asociados": [str(espacio.pk)],
                "requiere_insumos": "on",
                "insumos_necesarios": "Filamento de 1,75 mm homologado.",
                "observaciones": "Activo incorporado desde el panel.",
                "activa": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        equipo = UnidadEquipo.objects.get(codigo_unidad="UNIT-IMP-TEST-01")
        self.assertEqual(equipo.equipo, catalogo)
        self.assertEqual(equipo.laboratorio, self.unidad)
        self.assertEqual(equipo.origen_adquisicion, "compra_publica")
        self.assertEqual(equipo.documento_adquisicion, "ORDEN-UPEC-2026-001")
        self.assertEqual(str(equipo.valor_referencial), "2850.75")
        self.assertEqual(list(equipo.espacios_asociados.all()), [espacio])
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                usuario=self.coordinador,
                accion="crear",
                entidad="recursos.UnidadEquipo",
                objeto_id=str(equipo.pk),
            ).exists()
        )

    def test_panel_crea_modelo_tecnico_y_unidad_fisica_con_auditoria(self):
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "recursos",
                "entidad": "equipo",
                "codigo_catalogo": "CAT-CNC-TEST",
                "nombre_catalogo": "Fresadora CNC de prueba",
                "marca": "UPEC Lab",
                "modelo": "CNC-2026",
                "descripcion_catalogo": "Equipo para mecanizado de precisión.",
                "caracteristicas_publicas": "Tres ejes y control numérico.",
                "uso_publico": "Prototipado y prácticas de manufactura.",
                "instrucciones_publicas": "Requiere inducción previa.",
                "software_requerido": "Software CAM compatible.",
                "codigo_unidad": "UNIT-CNC-TEST-01",
                "estado_unidad": "disponible",
                "origen_adquisicion": "proyecto",
                "documento_adquisicion": "PROYECTO-I+D-26",
                "activa": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        catalogo = EquiposServicios.objects.get(codigo="CAT-CNC-TEST")
        equipo = UnidadEquipo.objects.get(codigo_unidad="UNIT-CNC-TEST-01")
        self.assertEqual(equipo.equipo, catalogo)
        self.assertEqual(equipo.laboratorio, self.unidad)
        self.assertEqual(catalogo.marca, "UPEC Lab")
        self.assertEqual(catalogo.modelo, "CNC-2026")
        self.assertEqual(equipo.origen_adquisicion, "proyecto")
        entidades = set(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                usuario=self.coordinador,
                accion="crear",
                objeto_id__in=[str(catalogo.pk), str(equipo.pk)],
            ).values_list("entidad", flat=True)
        )
        self.assertIn("recursos.EquiposServicios", entidades)
        self.assertIn("recursos.UnidadEquipo", entidades)

    def test_panel_rechaza_espacio_ajeno_al_incorporar_equipo(self):
        catalogo = EquiposServicios.objects.create(
            codigo="CAT-AJENO-TEST",
            nombre="Equipo para validar alcance",
        )
        espacio_ajeno = EspacioReservable.objects.create(
            unidad=self.otra_unidad,
            codigo="ESP-AJENO-TEST",
            nombre="Espacio ajeno",
            capacidad=2,
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "recursos",
                "entidad": "equipo",
                "equipo_catalogo_id": catalogo.pk,
                "codigo_unidad": "UNIT-AJENA-TEST-01",
                "estado_unidad": "disponible",
                "origen_adquisicion": "asignacion_institucional",
                "espacios_asociados": [str(espacio_ajeno.pk)],
                "activa": "on",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("únicamente espacios de esta unidad", response.json()["error"])
        self.assertFalse(
            UnidadEquipo.objects.filter(codigo_unidad="UNIT-AJENA-TEST-01").exists()
        )

    def test_panel_registra_asigna_y_cierra_incidencia_y_mantenimiento(self):
        equipo = self._crear_equipo_operativo()
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        creada = self.client.post(
            url,
            {
                "modulo": "incidencia",
                "equipo_id": equipo.pk,
                "titulo": "Desviación detectada",
                "tipo": "calibracion",
                "prioridad": "alta",
                "estado": "evaluacion",
                "descripcion": "La medición supera la tolerancia.",
                "detiene_operacion": "on",
                "asignada_a": self.responsable.pk,
            },
        )
        self.assertEqual(creada.status_code, 200)
        incidencia = IncidenciaEquipo.objects.get(
            pk=creada.json()["registro"]["id"]
        )
        self.assertEqual(incidencia.asignada_a, self.responsable)
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado_unidad, "dañado")

        cerrada = self.client.post(
            url,
            {
                "modulo": "incidencia",
                "registro_id": incidencia.pk,
                "titulo": incidencia.titulo,
                "tipo": incidencia.tipo,
                "prioridad": incidencia.prioridad,
                "estado": "cerrada",
                "descripcion": incidencia.descripcion,
                "asignada_a": self.responsable.pk,
                "solucion": "Equipo recalibrado y verificado.",
            },
        )
        self.assertEqual(cerrada.status_code, 200)
        incidencia.refresh_from_db()
        self.assertEqual(incidencia.estado, "cerrada")
        self.assertIsNotNone(incidencia.fecha_resolucion)

        mantenimiento = self.client.post(
            url,
            {
                "modulo": "mantenimiento",
                "equipo_id": equipo.pk,
                "titulo": "Mantenimiento posterior a calibración",
                "tipo": "calibracion",
                "estado": "completado",
                "fecha_programada": "2026-09-01T10:00",
                "responsable": self.responsable.pk,
                "resultado": "Calibración completada correctamente.",
                "proximo_mantenimiento": "2027-03-01",
            },
        )
        self.assertEqual(mantenimiento.status_code, 200)
        registro = MantenimientoEquipo.objects.get(
            pk=mantenimiento.json()["registro"]["id"]
        )
        self.assertEqual(registro.estado, "completado")

    def test_los_escuchas_de_la_consola_toleran_grupos_de_opciones(self):
        """Un campo de varias opciones no puede tumbar la carga del panel.

        `form.elements.namedItem` devuelve la lista cuando el campo es un grupo
        de botones de opcion, y la lista no tiene `addEventListener`: hacerlo
        directo rompia la consola entera en cuanto un formulario cambiaba un
        menu por opciones. El guion pasa por `escucharCampo`, que resuelve los
        dos casos; esta prueba existe porque las pruebas no ejecutan JavaScript
        y el fallo solo aparecia en el navegador.
        """
        from django.contrib.staticfiles import finders

        guion = Path(finders.find('portal/js/pages/unidades/panel_gestion.js')).read_text(
            encoding='utf-8')

        self.assertIn('function escucharCampo(', guion)
        directos = [
            linea.strip() for linea in guion.splitlines()
            if 'namedItem(' in linea and 'addEventListener' in linea
        ]
        self.assertEqual(directos, [], 'Usa escucharCampo en lugar de namedItem().addEventListener')

    def test_panel_registra_ingreso_salida_y_ajuste_de_inventario(self):
        equipo = self._crear_equipo_operativo()
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-PANEL",
            nombre="Material del panel",
            unidad_medida="kg",
            stock_total="10.000",
        )
        lote_en_uso = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="MAT-PANEL-USO",
            cantidad_inicial="10.000",
            cantidad_actual="10.000",
            estado="en_uso",
            equipo_en_uso=equipo,
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        ingreso = self.client.post(
            url,
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "ingreso",
                "cantidad": "2.500",
                "referencia": "FAC-001",
                "nota": "Compra institucional.",
            },
        )
        salida = self.client.post(
            url,
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "salida",
                "cantidad": "1.000",
                "lote_inventario_id": lote_en_uso.pk,
                "referencia": "OT-001",
                "nota": "Consumo de práctica.",
            },
        )
        ajuste = self.client.post(
            url,
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "ajuste",
                "cantidad": "15.000",
                "referencia": "ACTA-001",
                "nota": "Conteo físico.",
            },
        )

        self.assertEqual(ingreso.status_code, 200)
        self.assertEqual(salida.status_code, 200)
        self.assertEqual(ajuste.status_code, 200)
        consumible.refresh_from_db()
        self.assertEqual(str(consumible.stock_total), "15.000")
        self.assertEqual(
            EntradaInventario.objects.filter(consumible=consumible).count(),
            3,
        )

    def test_lote_fisico_controla_ubicacion_consumo_desperdicio_y_costo(self):
        equipo = self._crear_equipo_operativo()
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PLA-LOTE-PANEL",
            nombre="Filamento PLA real",
            familia="Filamentos para impresión 3D",
            variante="PLA 1,75 mm",
            presentacion="Bobina de 1 kg",
            cantidad_por_presentacion="1000",
            unidad_medida="g",
            precio_unitario="0.0300",
            stock_seguridad="200",
            minimo="300",
            stock_objetivo="2000",
            imagen_catalogo="img/catalogo/fablab/filamentos-pla-colores.png",
        )
        ConsumiblePorEquipo.objects.create(
            consumible=consumible,
            equipo=equipo.equipo,
        )
        incidencia = IncidenciaEquipo.objects.create(
            equipo=equipo,
            unidad=self.unidad,
            titulo="Atasco durante fabricación",
            descripcion="La pieza se detuvo después de consumir material.",
            prioridad="alta",
            reportada_por=self.coordinador,
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        recibido = self.client.post(
            url,
            {
                "modulo": "lote_consumible",
                "consumible_id": consumible.pk,
                "codigo": "PLA-AZ-2026-001",
                "cantidad_inicial": "1000",
                "estado": "en_uso",
                "equipo_en_uso_id": equipo.pk,
                "bodega": "Bodega FabLab",
                "estanteria": "Estantería FDM",
                "posicion": "Nivel 2 · Caja azul",
                "fecha_ingreso": "2026-09-02",
                "fecha_apertura": "2026-09-02",
                "fecha_vencimiento": "2028-09-02",
                "costo_unitario": "0.0300",
                "documento_recepcion": "ACTA-PLA-001",
            },
        )
        self.assertEqual(recibido.status_code, 200, recibido.content)
        lote = LoteConsumible.objects.get(codigo="PLA-AZ-2026-001")
        consumible.refresh_from_db()
        self.assertEqual(lote.estado, "en_uso")
        self.assertEqual(lote.equipo_en_uso, equipo)
        self.assertEqual(lote.cantidad_actual, Decimal("1000.000"))
        self.assertEqual(consumible.stock_total, Decimal("1000.000"))

        desperdicio = self.client.post(
            url,
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "salida",
                "motivo": "desperdicio_equipo",
                "cantidad": "80",
                "lote_inventario_id": lote.pk,
                "equipo_id": equipo.pk,
                "incidencia_id": incidencia.pk,
                "responsable_costo": "laboratorio",
                "nota": "Pieza incompleta por atasco del extrusor.",
            },
        )
        self.assertEqual(desperdicio.status_code, 200, desperdicio.content)
        movimiento = EntradaInventario.objects.get(
            pk=desperdicio.json()["registro"]["id"]
        )
        lote.refresh_from_db()
        consumible.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("920.000"))
        self.assertEqual(consumible.stock_total, Decimal("920.000"))
        self.assertEqual(movimiento.costo_total, Decimal("2.4000000"))
        self.assertEqual(movimiento.incidencia, incidencia)
        self.assertEqual(movimiento.responsable_costo, "laboratorio")

        panel = self.client.get(f"{self.url}?view=recursos&modo_recursos=inventario")
        self.assertContains(panel, "img/catalogo/fablab/filamentos-pla-colores.png")
        self.assertContains(panel, "PLA-AZ-2026-001")
        self.assertContains(panel, "1 abierta")
        self.assertContains(panel, "920 g disponibles · 80 g utilizados")
        self.assertContains(panel, "$2,40")
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                entidad="recursos.EntradaInventario",
                objeto_id=str(movimiento.pk),
            ).exists()
        )

    def test_baja_por_extravio_exige_retirar_el_lote_completo(self):
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-LOST-PANEL",
            nombre="Material localizable",
            unidad_medida="unidad",
            stock_total="5",
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="LOT-LOST-01",
            cantidad_inicial="5",
            cantidad_actual="5",
            bodega="Bodega principal",
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "salida",
                "motivo": "extravio",
                "cantidad": "2",
                "lote_inventario_id": lote.pk,
                "nota": "Diferencia detectada en conteo.",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("todo el saldo", response.json()["error"])
        lote.refresh_from_db()
        consumible.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("5.000"))
        self.assertEqual(consumible.stock_total, Decimal("5.000"))

    def test_consumo_solo_descuenta_una_presentacion_abierta_en_uso(self):
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PLA-CERRADO-PANEL",
            nombre="Filamento cerrado",
            presentacion="Bobina de 1 kg",
            cantidad_por_presentacion="1000",
            unidad_medida="g",
            stock_total="1000",
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="PLA-CERRADO-001",
            cantidad_inicial="1000",
            cantidad_actual="1000",
            estado="bodega",
            bodega="Bodega principal",
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "inventario",
                "consumible_id": consumible.pk,
                "tipo": "salida",
                "motivo": "consumo_produccion",
                "cantidad": "100",
                "lote_inventario_id": lote.pk,
                "nota": "Intento de consumo desde una bobina cerrada.",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("sigue cerrada en bodega", response.json()["error"])
        self.assertIn("Poner en uso", response.json()["error"])
        lote.refresh_from_db()
        consumible.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("1000.000"))
        self.assertEqual(consumible.stock_total, Decimal("1000.000"))

    def test_recepcion_convierte_presentaciones_enteras_a_cantidad_base(self):
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PLA-RECEPCION-PANEL",
            nombre="Filamento recibido",
            presentacion="Bobina de 1 kg",
            cantidad_por_presentacion="1000",
            unidad_medida="g",
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "lote_consumible",
                "consumible_id": consumible.pk,
                "codigo": "PLA-RECEPCION-001",
                "numero_presentaciones": "3",
                "cantidad_inicial": "999999",
                "estado": "bodega",
                "bodega": "Bodega principal",
                "nota": "Tres bobinas cerradas.",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        lotes = list(
            LoteConsumible.objects.filter(
                consumible=consumible,
                codigo__startswith="PLA-RECEPCION-001",
            ).order_by("codigo")
        )
        consumible.refresh_from_db()
        self.assertEqual(len(lotes), 3)
        self.assertEqual(
            [lote.codigo for lote in lotes],
            ["PLA-RECEPCION-001", "PLA-RECEPCION-001-02", "PLA-RECEPCION-001-03"],
        )
        self.assertTrue(
            all(lote.cantidad_inicial == Decimal("1000.000") for lote in lotes)
        )
        self.assertTrue(
            all(lote.cantidad_actual == Decimal("1000.000") for lote in lotes)
        )
        self.assertEqual(consumible.stock_total, Decimal("3000.000"))

    def test_panel_crea_ficha_de_abastecimiento_y_compatibilidad_trazable(self):
        equipo = self._crear_equipo_operativo()
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "consumible",
                "codigo": "PLA-AZUL-PANEL",
                "nombre": "Filamento PLA azul",
                "clasificacion": "insumo",
                "familia": "Filamentos",
                "variante": "PLA 1,75 mm",
                "color": "Azul",
                "marca": "Marca homologada",
                "presentacion": "Bobina de 1 kg",
                "cantidad_por_presentacion": "1000",
                "unidad_medida": "g",
                "descripcion": "Material para fabricación aditiva.",
                "especificacion_tecnica": "Diámetro 1,75 mm ± 0,03 mm.",
                "instrucciones_solicitud": "Registrar gramos calculados por el laminador.",
                "minimo": "1500",
                "stock_seguridad": "500",
                "stock_objetivo": "5000",
                "plazo_reposicion_dias": "30",
                "precio_unitario": "0.03",
                "origen_abastecimiento": "recursos_autogestion",
                "proveedor_referencia": "Proveedor homologado",
                "ubicacion": "Estante FDM",
                "lote": "PLA-2026-09",
                "fecha_vencimiento": "2028-09-01",
                "equipos_compatibles": [str(equipo.equipo_id)],
                "visible_en_reservas": "on",
                "activo": "on",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        consumible = Consumible.objects.get(codigo="PLA-AZUL-PANEL")
        self.assertEqual(str(consumible.cantidad_por_presentacion), "1000.000")
        self.assertEqual(str(consumible.stock_seguridad), "500.000")
        self.assertEqual(str(consumible.stock_objetivo), "5000.000")
        self.assertEqual(consumible.origen_abastecimiento, "recursos_autogestion")
        self.assertEqual(
            list(consumible.equipos_compatibles.values_list("pk", flat=True)),
            [equipo.equipo_id],
        )
        auditoria = RegistroAuditoriaUnidad.objects.get(
            unidad=self.unidad,
            entidad="recursos.Consumible",
            objeto_id=str(consumible.pk),
        )
        self.assertEqual(auditoria.datos_nuevos["equipos_compatibles"], [equipo.equipo_id])

    def test_panel_registra_cobro_y_egreso_sin_mezclar_fuentes(self):
        self.reserva.tipo_solicitud = "servicio"
        self.reserva.costo_estimado = "80.00"
        self.reserva.save(update_fields=["tipo_solicitud", "costo_estimado"])
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="FIN-MAT-001",
            nombre="Material financiado",
            unidad_medida="unidad",
        )
        inventario = EntradaInventario.objects.create(
            consumible=consumible,
            unidad=self.unidad,
            tipo="ingreso",
            cantidad="10.000",
            usuario=self.coordinador,
            referencia="FAC-FIN-001",
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        ingreso = self.client.post(
            url,
            {
                "modulo": "finanzas",
                "tipo": "ingreso",
                "categoria": "servicio",
                "fuente_fondos": "autogestion",
                "estado": "confirmado",
                "fecha_movimiento": timezone.localdate().isoformat(),
                "monto": "75.00",
                "metodo": "transferencia",
                "referencia": "DEP-001",
                "descripcion": "Cobro real del servicio",
                "reserva_id": self.reserva.pk,
            },
        )
        egreso = self.client.post(
            url,
            {
                "modulo": "finanzas",
                "tipo": "egreso",
                "categoria": "reposicion_insumos",
                "fuente_fondos": "presupuesto_institucional",
                "estado": "confirmado",
                "fecha_movimiento": timezone.localdate().isoformat(),
                "monto": "30.00",
                "metodo": "asignacion",
                "referencia": "OC-001",
                "descripcion": "Compra pública de material",
                "movimiento_inventario_id": inventario.pk,
                "comprobante": SimpleUploadedFile('comprobante-egreso.pdf', b'%PDF-1.4\nPrueba', content_type='application/pdf'),
                "procedimiento_solicitado": "publico",
                "procedimiento_verificado": "on",
                "referencia_autorizacion": "OC-001 autorizada por delegado de compras",
                "certificacion_presupuestaria": "Certificación de prueba CP-001",
            },
        )

        self.assertEqual(ingreso.status_code, 200, ingreso.content)
        self.assertEqual(egreso.status_code, 200, egreso.content)
        panel = self.client.get(self.url, {"view": "recursos", "modo_recursos": "finanzas"})
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context["resumen_financiero"]["ingresos"], 75)
        self.assertEqual(panel.context["resumen_financiero"]["egresos"], 30)
        self.assertEqual(panel.context["resumen_financiero"]["saldo_autogestion"], 75)
        self.assertContains(panel, "Cobro real del servicio")
        self.assertContains(panel, "Compra pública de material")
        self.assertContains(panel, "Ingresos frente a costos")
        self.assertContains(panel, 'data-finance-chart="mensual"')
        self.assertContains(panel, 'class="unit-console__flow-line is-income"')
        grafica_mensual = panel.context["analitica_financiera"]["graficas"]["mensual"]
        self.assertTrue(grafica_mensual["tiene_datos"])
        self.assertEqual(grafica_mensual["puntos"][-1]["ingresos"], 75)
        self.assertEqual(grafica_mensual["puntos"][-1]["egresos"], 30)
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                entidad="finanzas.MovimientoFinancieroUnidad",
            ).count(),
            2,
        )
        fecha = timezone.localdate().isoformat()
        query = f"?categoria_reporte=finanzas&desde={fecha}&hasta={fecha}"
        reporte_html = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug]) + query
        )
        reporte_pdf = self.client.get(
            reverse("gestion_reporte_unidad_pdf", args=[self.unidad.slug]) + query
        )
        self.assertEqual(reporte_html.status_code, 200)
        self.assertEqual(reporte_html.context["reporte_gestion"]["category"], "finanzas")
        self.assertEqual(len(reporte_html.context["reporte_gestion"]["dataset"]["rows"]), 2)
        self.assertContains(
            reporte_html, "Informe financiero de servicios: ingresos, egresos y costos"
        )
        self.assertContains(reporte_html, "Recursos generados por servicios y ventas")
        self.assertContains(reporte_html, "Presupuesto institucional")
        self.assertEqual(reporte_pdf.status_code, 200)
        self.assertEqual(reporte_pdf["Content-Type"], "application/pdf")
        self.assertTrue(reporte_pdf.content.startswith(b"%PDF"))

    def test_movimiento_confirmado_no_se_edita_y_se_anula_con_trazabilidad(self):
        movimiento = MovimientoFinancieroUnidad.objects.create(
            unidad=self.unidad,
            tipo="ingreso",
            categoria="producto",
            fuente_fondos="autogestion",
            estado="confirmado",
            fecha_movimiento=timezone.localdate(),
            monto="25.00",
            descripcion="Venta de pieza",
            creado_por=self.coordinador,
            actualizado_por=self.coordinador,
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])

        editar = self.client.post(
            url,
            {
                "modulo": "finanzas",
                "registro_id": movimiento.pk,
                "tipo": "ingreso",
                "categoria": "producto",
                "fuente_fondos": "autogestion",
                "estado": "confirmado",
                "fecha_movimiento": timezone.localdate().isoformat(),
                "monto": "30.00",
                "metodo": "no_aplica",
                "descripcion": "Venta alterada",
            },
        )
        anular = self.client.post(
            url,
            {
                "modulo": "finanzas",
                "registro_id": movimiento.pk,
                "accion": "anular",
                "motivo_anulacion": "El comprobante tenía un valor incorrecto.",
            },
        )

        self.assertEqual(editar.status_code, 400)
        self.assertIn("no se edita", editar.json()["error"])
        self.assertEqual(anular.status_code, 200, anular.content)
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, "anulado")
        self.assertEqual(movimiento.anulado_por, self.coordinador)
        self.assertIsNotNone(movimiento.anulado_en)
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                entidad="finanzas.MovimientoFinancieroUnidad",
                datos_nuevos__estado="anulado",
            ).exists()
        )

    def test_responsable_sin_permiso_financiero_no_registra_movimientos(self):
        self.client.force_login(self.responsable)
        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "finanzas",
                "tipo": "ingreso",
                "categoria": "producto",
                "fuente_fondos": "autogestion",
                "estado": "confirmado",
                "fecha_movimiento": timezone.localdate().isoformat(),
                "monto": "10.00",
                "descripcion": "Movimiento no autorizado",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MovimientoFinancieroUnidad.objects.exists())

    def test_panel_rechaza_compatibilidad_con_equipo_ajeno(self):
        catalogo_ajeno = EquiposServicios.objects.create(
            codigo="CAT-COMP-AJENO",
            nombre="Modelo ajeno para compatibilidad",
        )
        UnidadEquipo.objects.create(
            codigo_unidad="UNIT-COMP-AJENA",
            equipo=catalogo_ajeno,
            laboratorio=self.otra_unidad,
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "consumible",
                "codigo": "MAT-COMP-AJENO",
                "nombre": "Material incompatible",
                "clasificacion": "insumo",
                "cantidad_por_presentacion": "1",
                "unidad_medida": "unidad",
                "equipos_compatibles": [str(catalogo_ajeno.pk)],
                "visible_en_reservas": "on",
                "activo": "on",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("disponibles en este laboratorio", response.json()["error"])
        self.assertFalse(Consumible.objects.filter(codigo="MAT-COMP-AJENO").exists())

    def test_panel_configura_responsable_capacidad_y_modulos(self):
        self.client.force_login(self.coordinador)
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])
        cuenta_tecnica = get_user_model().objects.create_user(
            username="tecnica-apoyo-panel",
            email="tecnica@upec.edu.ec",
        )

        responsable = self.client.post(
            url,
            {
                "modulo": "responsable",
                "usuario_id": str(cuenta_tecnica.pk),
                "nombre": "Técnica de apoyo",
                "rol": "tecnico",
                "email": "tecnica@upec.edu.ec",
                "telefono": "Ext. 123",
                "descripcion": "Apoyo de fabricación.",
                "horario_atencion": "Lunes a viernes",
                "publico": "on",
                "recibe_reservas": "on",
                "activo": "on",
            },
        )
        capacidad = self.client.post(
            url,
            {
                "modulo": "capacidad",
                "vigente_desde": "2026-09-01",
                "aforo_seguridad": "20",
                "puestos_mobiliario": "16",
                "puestos_equipados": "12",
                "capacidad_personal": "10",
                "fuente": "Inspección operativa",
            },
        )
        configuracion = self.client.post(
            url,
            {
                "modulo": "configuracion",
                "solicitudes_servicio": "on",
                "reservas_equipos": "on",
                "inventario_equipos": "on",
                "mantenimiento_equipos": "on",
                "incidencias_equipos": "on",
                "consumibles": "on",
                "cotizacion_costos": "on",
                "ordenes_trabajo": "on",
                "indicadores_reportes": "on",
                "seguimiento": "on",
                "tarifa_referencial_hora_espacio": "6.50",
                "tarifa_referencial_hora_equipo": "12.00",
                "tarifa_referencial_hora_software": "3.25",
                "tarifa_referencial_hora_acompanamiento": "8.00",
                "aporte_institucional_recursos_pct": "75.00",
            },
        )

        self.assertEqual(responsable.status_code, 200)
        self.assertEqual(capacidad.status_code, 200)
        self.assertEqual(configuracion.status_code, 200)
        self.assertTrue(
            ResponsableUnidad.objects.filter(
                unidad=self.unidad,
                nombre="Técnica de apoyo",
                usuario=cuenta_tecnica,
                recibe_reservas=True,
            ).exists()
        )
        capacidad_obj = CapacidadOperativaUnidad.objects.get(
            pk=capacidad.json()["registro"]["id"]
        )
        self.assertEqual(capacidad_obj.capacidad_efectiva, 10)
        configuracion_obj = ConfiguracionOperativaUnidad.objects.get(
            unidad=self.unidad
        )
        self.assertFalse(configuracion_obj.reservas_espacios)
        self.assertEqual(
            configuracion_obj.tarifa_referencial_hora_equipo,
            Decimal("12.00"),
        )
        self.assertEqual(
            configuracion_obj.aporte_institucional_recursos_pct,
            Decimal("100.00"),
        )

    def test_coordinador_aprueba_y_asigna_desde_el_panel_con_trazabilidad(self):
        self.client.force_login(self.coordinador)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        response = self.client.post(
            url,
            {
                "accion": "aprobar",
                "responsable_id": self.responsable_unidad.pk,
                "observacion": "Equipo revisado y jornada confirmada.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "confirmada")
        self.assertEqual(
            self.reserva.responsable_asignado_id,
            self.responsable_unidad.pk,
        )
        self.assertEqual(self.reserva.validada_por_id, self.coordinador.pk)
        self.assertIn("Equipo revisado", self.reserva.observaciones_validacion)
        self.assertTrue(
            LogEntry.objects.filter(
                object_id=str(self.reserva.pk),
                user=self.coordinador,
                change_message__contains="Reserva aprobada",
            ).exists()
        )

    def test_expediente_operativo_incluye_recursos_participantes_e_incidencias(self):
        equipo = self._crear_equipo_operativo()
        self.reserva.unidades_seleccionadas = json.dumps(
            [{"id": equipo.pk, "codigo": equipo.codigo_unidad}]
        )
        self.reserva.numero_participantes = 2
        self.reserva.descripcion_proyecto = "Fabricación y validación de un prototipo."
        self.reserva.save()
        software = SoftwareDisponible.objects.create(
            unidad=self.unidad,
            codigo="CAD-PANEL",
            nombre="CAD del panel",
            version="2026",
        )
        self.reserva.software_solicitado.add(software)
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-DETALLE",
            nombre="Filamento técnico",
            unidad_medida="g",
            stock_total="1000.000",
        )
        ReservaConsumible.objects.create(
            reserva=self.reserva,
            consumible=consumible,
            cantidad_solicitada="120.000",
        )
        RegistroParticipanteReserva.objects.create(
            reserva=self.reserva,
            usuario=self.usuario_ajeno,
            rol="solicitante",
            nombre="Persona solicitante",
            correo="persona@upec.edu.ec",
        )
        RegistroParticipanteReserva.objects.create(
            reserva=self.reserva,
            rol="participante",
            nombre="Participante invitado",
            correo="invitado@upec.edu.ec",
        )
        IncidenciaEquipo.objects.create(
            equipo=equipo,
            titulo="Falla de calibración",
            tipo="calibracion",
            prioridad="alta",
            descripcion="Requiere revisión antes de operar.",
            detiene_operacion=True,
            reportada_por=self.coordinador,
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            reverse(
                "gestion_reserva_detalle",
                args=[self.unidad.slug, self.reserva.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        detalle = response.json()["reserva"]
        self.assertEqual(detalle["recursos"]["equipos"][0]["nombre"], equipo.equipo.nombre)
        self.assertEqual(detalle["recursos"]["software"][0]["nombre"], software.nombre)
        self.assertEqual(detalle["recursos"]["consumibles"][0]["nombre"], consumible.nombre)
        self.assertEqual(detalle["participantes"]["identificados"], 2)
        self.assertEqual(
            detalle["recursos"]["equipos"][0]["incidencias"][0]["titulo"],
            "Falla de calibración",
        )

    def test_laboratorista_anota_y_solicita_informacion_sin_cambiar_estado(self):
        self.client.force_login(self.coordinador)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        nota = self.client.post(
            url,
            {"accion": "anotar", "observacion": "Verificar accesorio de seguridad."},
        )
        solicitud = self.client.post(
            url,
            {
                "accion": "solicitar_info",
                "observacion": "Completar la lista nominal de asistentes.",
            },
        )

        self.assertEqual(nota.status_code, 200)
        self.assertEqual(solicitud.status_code, 200)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "pendiente")
        self.assertIn("Verificar accesorio", self.reserva.observaciones_validacion)
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                objeto_id=str(self.reserva.pk),
                accion="observar",
                descripcion__contains="lista nominal",
            ).exists()
        )
        self.client.force_login(self.usuario_ajeno)
        vista_usuario = self.client.get(
            reverse("obtener_reservas_usuario"),
            {"laboratorio_id": self.unidad.pk},
        )
        reserva_usuario = vista_usuario.json()["reservas"][0]
        self.assertTrue(reserva_usuario["informacion_adicional_solicitada"])
        self.assertTrue(
            any(
                "lista nominal" in observacion
                for observacion in reserva_usuario["observaciones_seguimiento"]
            )
        )

    def test_aprobacion_asigna_responsable_automaticamente_sin_escribir_campos(self):
        self.client.force_login(self.coordinador)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        response = self.client.post(url, {"accion": "aprobar"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("asignada a", response.json()["message"])
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "confirmada")
        self.assertEqual(
            self.reserva.responsable_asignado_id,
            self.responsable_unidad.pk,
        )
        self.assertEqual(self.reserva.validada_por_id, self.coordinador.pk)

    def test_guia_obligatoria_bloquea_aprobacion_hasta_publicarse(self):
        actividad = CatalogoActividadReserva.objects.create(
            unidad=self.unidad,
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica con control documental",
            estado_publicacion="revision",
            visibilidad="privada",
            creado_por=self.usuario_ajeno,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            actividad_catalogo=actividad,
            fecha=timezone.localdate() + timedelta(days=7),
            hora_inicio=time(14, 0),
            hora_fin=time(15, 0),
            equipo_codigo="EQ-GUIA",
            equipo_nombre="Equipo para práctica",
            titulo_solicitud="Reserva que exige guía",
            proposito_codigo="docencia_practica",
            vinculacion_actividad="manual",
            referencia_actividad=actividad.nombre,
            estado="pendiente",
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía en elaboración",
            es_estructurada=True,
            contenido={"reserva_fuente_id": reserva.pk},
            estado_publicacion="borrador",
            subido_por=self.usuario_ajeno,
        )
        self.client.force_login(self.coordinador)
        accion_url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, reserva.pk],
        )

        bloqueada = self.client.post(accion_url, {"accion": "aprobar"})

        self.assertEqual(bloqueada.status_code, 409)
        self.assertEqual(bloqueada.json()["code"], "documentacion_pendiente")
        self.assertEqual(bloqueada.json()["documentacion"]["estado"], "borrador")
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "pendiente")
        detalle = self.client.get(
            reverse(
                "gestion_reserva_detalle",
                args=[self.unidad.slug, reserva.pk],
            )
        ).json()["reserva"]
        self.assertFalse(detalle["documentacion"]["lista"])
        self.assertIn(
            reverse(
                "editar_guia_practica",
                args=[self.unidad.slug, guia.pk],
            ),
            detalle["documentacion"]["url"],
        )

        guia.estado_publicacion = "publicada"
        guia.es_vigente = True
        guia.save(update_fields=["estado_publicacion", "es_vigente"])
        aprobada = self.client.post(accion_url, {"accion": "aprobar"})

        self.assertEqual(aprobada.status_code, 200, aprobada.content)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")

    def test_rechazo_exige_motivo_y_se_distingue_de_cancelacion(self):
        self.client.force_login(self.coordinador)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        response_sin_motivo = self.client.post(url, {"accion": "rechazar"})
        response = self.client.post(
            url,
            {"accion": "rechazar", "observacion": "No cumple requisitos técnicos."},
        )

        self.assertEqual(response_sin_motivo.status_code, 400)
        self.assertEqual(response.status_code, 200)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "rechazada")

    def test_usuario_sin_funcion_operativa_no_puede_cambiar_estados(self):
        self.client.force_login(self.usuario_ajeno)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        response = self.client.post(url, {"accion": "aprobar"})

        self.assertEqual(response.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "pendiente")

    def test_aprobacion_revalida_bloqueos_administrativos(self):
        BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            tipo="mantenimiento",
            titulo="Mantenimiento integral",
            fecha_inicio=self.reserva.fecha,
            fecha_fin=self.reserva.fecha,
            dia_completo=True,
            alcance="unidad_completa",
            creado_por=self.coordinador,
        )
        self.client.force_login(self.coordinador)
        url = reverse(
            "gestion_reserva_accion",
            args=[self.unidad.slug, self.reserva.pk],
        )

        response = self.client.post(
            url,
            {
                "accion": "aprobar",
                "responsable_id": self.responsable_unidad.pk,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Mantenimiento integral", response.json()["error"])
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "pendiente")

    def test_inventario_visual_muestra_unidades_abc_graficas_y_trazabilidad(self):
        equipo = self._crear_equipo_operativo()
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PLA-VISUAL",
            nombre="Filamento visual",
            presentacion="Bobina de 1 kg",
            cantidad_por_presentacion=Decimal("1000"),
            unidad_medida="g",
            stock_total=Decimal("3000"),
            minimo=Decimal("300"),
            stock_seguridad=Decimal("150"),
            stock_objetivo=Decimal("2000"),
            precio_unitario=Decimal("0.025"),
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="PLA-VISUAL-001",
            cantidad_inicial=Decimal("1000"),
            cantidad_actual=Decimal("1000"),
            estado="en_uso",
            bodega="Bodega FabLab",
            estanteria="FDM-02",
            posicion="Nivel 1",
            equipo_en_uso=equipo,
            creado_por=self.coordinador,
        )
        LoteConsumible.objects.create(
            consumible=consumible,
            codigo="PLA-VISUAL-BODEGA",
            cantidad_inicial=Decimal("2000"),
            cantidad_actual=Decimal("2000"),
            estado="bodega",
            bodega="Bodega FabLab",
            estanteria="FDM-02",
            posicion="Nivel 2",
            creado_por=self.coordinador,
        )
        EntradaInventario.objects.create(
            unidad=self.unidad,
            consumible=consumible,
            tipo="salida",
            motivo="consumo_practica",
            cantidad=Decimal("100"),
            lote_inventario=lote,
            costo_unitario=Decimal("0.025"),
            usuario=self.coordinador,
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(
            self.url,
            {"view": "recursos", "modo_recursos": "inventario"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entradas frente a consumo")
        self.assertContains(response, 'data-inventory-chart="semanal"', count=1)
        self.assertContains(response, 'data-inventory-chart="mensual"', count=1)
        self.assertContains(response, 'data-inventory-chart="periodo"', count=1)
        self.assertContains(response, 'class="unit-console__flow-line is-exit"')
        self.assertContains(response, "Se calcula automáticamente desde el kardex")
        self.assertContains(response, "ANÁLISIS ABC")
        self.assertContains(response, "Lectura rápida de lote")
        self.assertContains(response, 'data-lot-code="pla-visual-001"')
        self.assertContains(response, "900 g")
        self.assertContains(response, "100 g utilizados")
        self.assertContains(response, "Presentaciones abiertas / en uso")
        self.assertContains(response, "Unidades cerradas en bodega")
        self.assertContains(response, "2 bobinas cerradas")
        self.assertContains(response, "Bodega FabLab")
        self.assertContains(response, "Recorrido del lote")
        grafica = response.context["analitica_inventario"]["graficas"]["semanal"]
        self.assertTrue(grafica["tiene_datos"])
        self.assertTrue(grafica["linea_salidas"])
        self.assertNotIn(",", grafica["puntos"][-1]["y_salidas_svg"])
        self.assertEqual(response.context["analitica_inventario"]["abc"][0]["clase"], "A")

    def test_identificador_qr_y_code128_del_lote_son_svg_protegidos(self):
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="QR-INSUMO",
            nombre="Insumo identificable",
            unidad_medida="unidad",
            stock_total=Decimal("1"),
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="QR-LOTE-001",
            cantidad_inicial=Decimal("1"),
            cantidad_actual=Decimal("1"),
            estado="bodega",
            bodega="Bodega principal",
        )
        url = reverse("gestion_lote_identificador", args=[self.unidad.slug, lote.pk])

        anonimo = self.client.get(url)
        self.assertEqual(anonimo.status_code, 302)

        self.client.force_login(self.coordinador)
        qr = self.client.get(url)
        barras = self.client.get(url, {"tipo": "barra"})
        qr_descargable = self.client.get(url, {"tipo": "qr", "descargar": "1"})

        self.assertEqual(qr.status_code, 200)
        self.assertEqual(barras.status_code, 200)
        self.assertEqual(qr["Content-Type"], "image/svg+xml")
        self.assertTrue(qr_descargable["Content-Disposition"].startswith("attachment;"))
        self.assertIn(b"<svg", qr.content)
        self.assertIn(b"<svg", barras.content)

    def test_hoja_a4_de_etiquetas_es_pdf_descargable_y_admite_copias(self):
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="PDF-INSUMO",
            nombre="Filamento etiquetable",
            presentacion="Bobina de 1 kg",
            cantidad_por_presentacion=Decimal("1000"),
            unidad_medida="g",
            stock_total=Decimal("1000"),
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="PDF-LOTE-001",
            cantidad_inicial=Decimal("1000"),
            cantidad_actual=Decimal("1000"),
            estado="bodega",
            bodega="Bodega principal",
            estanteria="A-02",
            posicion="Nivel 3",
        )
        url = reverse("gestion_etiquetas_inventario_pdf", args=[self.unidad.slug])

        anonimo = self.client.get(url, {"lote": lote.pk})
        self.assertEqual(anonimo.status_code, 302)
        self.client.force_login(self.coordinador)
        response = self.client.get(url, {"lote": lote.pk, "copias": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertGreater(len(response.content), 3000)

    def test_cierre_operativo_concilia_asistencia_inventario_incidencia_y_cobro(self):
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-CIERRE-CAT",
            nombre="Impresora de cierre",
        )
        equipo = UnidadEquipo.objects.create(
            codigo_unidad="EQ-CIERRE-01",
            equipo=catalogo,
            laboratorio=self.unidad,
        )
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-CIERRE",
            nombre="Filamento para cierre",
            unidad_medida="g",
            stock_total=Decimal("1000"),
            precio_unitario=Decimal("0.0300"),
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="LOTE-CIERRE-001",
            cantidad_inicial=Decimal("1000"),
            cantidad_actual=Decimal("1000"),
            estado="en_uso",
            equipo_en_uso=equipo,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            equipo_codigo=equipo.codigo_unidad,
            equipo_nombre=catalogo.nombre,
            titulo_solicitud="Servicio con cierre integral",
            tipo_solicitud="servicio",
            proposito_codigo="docencia_practica",
            metodo_pago="transferencia",
            estado="confirmada",
            responsable_asignado=self.responsable_unidad,
            unidades_seleccionadas=json.dumps(
                [{"id": equipo.pk, "codigo": equipo.codigo_unidad, "nombre": catalogo.nombre}]
            ),
        )
        reserva_consumible = ReservaConsumible.objects.create(
            reserva=reserva,
            consumible=consumible,
            cantidad_solicitada=Decimal("200"),
            cantidad_aprobada=Decimal("200"),
        )
        self.client.force_login(self.coordinador)
        url = reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk])
        datos = {
            "accion": "completar",
            "ejecucion_registrada": "1",
            "participantes_seleccionados": "[]",
            "asistencia_solicitante": "asistio",
            "ejecucion_hora_inicio": "09:05",
            "ejecucion_hora_fin": "10:48",
            "ejecucion_asistentes_total": "3",
            "ejecucion_cumplimiento": "parcial",
            "ejecucion_equipos_ids": [str(equipo.pk)],
            "ejecucion_consumibles_json": json.dumps(
                [
                    {
                        "reserva_consumible_id": reserva_consumible.pk,
                        "consumida": "100",
                        "desperdiciada": "20",
                        "lote_id": lote.pk,
                        "equipo_id": equipo.pk,
                        "motivo_desperdicio": "desperdicio_equipo",
                    }
                ]
            ),
            "ejecucion_tuvo_incidencia": "1",
            "ejecucion_incidencia_equipo_id": str(equipo.pk),
            "ejecucion_incidencia_tipo": "falla",
            "ejecucion_incidencia_prioridad": "alta",
            "ejecucion_incidencia_titulo": "Atasco durante la impresión",
            "ejecucion_incidencia_descripcion": "La boquilla se obstruyó durante la fabricación.",
            "ejecucion_incidencia_detiene": "1",
            "ejecucion_monto_cobrado": "2.00",
            "ejecucion_justificacion_ajuste": "Valor autorizado por alcance adicional documentado.",
            "ejecucion_referencia_pago": "TRX-PRUEBA-001",
            "ejecucion_pago_confirmado": "1",
            "ejecucion_observaciones": "Se entregó el resultado parcial y se informó la novedad.",
        }

        response = self.client.post(url, datos)

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        reserva_consumible.refresh_from_db()
        consumible.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(reserva.estado, "completada")
        self.assertEqual(reserva.resultado_cierre, "atendida")
        self.assertEqual(reserva.detalle_ejecucion["asistentes_total"], 3)
        self.assertEqual(reserva.detalle_ejecucion["version"], 2)
        self.assertEqual(reserva.detalle_ejecucion["equipos"][0]["id"], str(equipo.pk))
        self.assertEqual(reserva.costo_real, Decimal("3.60"))
        self.assertEqual(reserva.aporte_institucional_real, Decimal("0.00"))
        self.assertEqual(reserva.valor_final_usuario, Decimal("3.00"))
        self.assertEqual(
            reserva.desglose_liquidacion["costo_desperdicio_laboratorio"],
            "0.60",
        )
        self.assertEqual(
            reserva.detalle_ejecucion["ingreso"]["conciliacion"]["ajuste"],
            "-1.00",
        )
        self.assertEqual(reserva_consumible.cantidad_consumida, Decimal("100"))
        self.assertEqual(reserva_consumible.cantidad_desperdiciada, Decimal("20"))
        self.assertEqual(consumible.stock_total, Decimal("880"))
        self.assertEqual(lote.cantidad_actual, Decimal("880"))
        self.assertEqual(
            EntradaInventario.objects.filter(reserva=reserva, tipo="salida").count(),
            2,
        )
        incidencia = IncidenciaEquipo.objects.get(reserva=reserva)
        self.assertEqual(incidencia.equipo, equipo)
        self.assertTrue(incidencia.detiene_operacion)
        ingreso = MovimientoFinancieroUnidad.objects.get(reserva=reserva)
        self.assertEqual(ingreso.monto, Decimal("2.00"))
        self.assertEqual(ingreso.estado, "confirmado")

        report = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
            + f"?desde={reserva.fecha:%Y-%m-%d}&hasta={reserva.fecha:%Y-%m-%d}"
            + "&efectividad=efectivas"
        )
        self.assertEqual(report.status_code, 200)
        metrics = report.context["reporte_gestion"]["metrics"]
        self.assertEqual(metrics["participants"], 3)
        self.assertEqual(metrics["hours"], 1.7)

        reporte_financiero = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
            + f"?desde={timezone.localdate():%Y-%m-%d}&hasta={timezone.localdate():%Y-%m-%d}"
            + "&categoria_reporte=finanzas"
        )
        self.assertEqual(reporte_financiero.status_code, 200)
        tarjetas = dict(reporte_financiero.context["reporte_gestion"]["dataset"]["cards"])
        self.assertEqual(tarjetas["Ingresos confirmados"], "$2.00")
        self.assertEqual(tarjetas["Costo operativo liquidado"], "$3.60")
        self.assertEqual(tarjetas["Valor final de usuarios"], "$3.00")
        self.assertEqual(tarjetas["Desperdicio asumido"], "$0.60")

        comprobante = self.client.get(
            reverse("comprobante_reserva", args=[reserva.pk])
        )
        self.assertEqual(comprobante.status_code, 200)
        self.assertContains(comprobante, "Soporte final de atención")
        self.assertContains(comprobante, "Ejecución real y trazabilidad del cierre")
        self.assertContains(comprobante, "Consumos reales")
        self.assertContains(comprobante, "Liquidación del cierre")
        self.assertContains(comprobante, "TRX-PRUEBA-001")
        comprobante_pdf = self.client.get(
            reverse("comprobante_reserva_pdf", args=[reserva.pk])
        )
        self.assertEqual(comprobante_pdf.status_code, 200)
        self.assertEqual(comprobante_pdf["Content-Type"], "application/pdf")
        self.assertTrue(comprobante_pdf.content.startswith(b"%PDF"))

        repetida = self.client.post(url, datos)
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(EntradaInventario.objects.filter(reserva=reserva).count(), 2)
        self.assertEqual(MovimientoFinancieroUnidad.objects.filter(reserva=reserva).count(), 1)

    def test_panel_muestra_captura_separada_de_ejecucion_real(self):
        # Con un insumo en el catalogo la fila de consumo real se dibuja entera.
        Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-VISTA",
            nombre="Filamento de vitrina",
            unidad_medida="g",
            stock_total=Decimal("100"),
            precio_unitario=Decimal("0.0200"),
        )
        self.client.force_login(self.coordinador)

        response = self.client.get(self.url, {"view": "reservas"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-reservation-drawer-tab="ejecucion"')
        self.assertContains(response, "Lo que realmente ocurrió")
        self.assertContains(response, 'id="managementExecutionConsumables"')
        self.assertContains(response, "Pago verificado")
        self.assertContains(response, "Estimado frente a ejecución real")
        self.assertContains(response, 'id="managementLiquidationUser"')
        self.assertContains(response, "Automático al cerrar")
        self.assertContains(response, 'id="managementExecutionPieces"')
        self.assertContains(response, "Uso útil total")
        # La unidad nombra su trabajo: esta usa el valor de partida, «piezas».
        self.assertContains(response, "Piezas iguales")
        self.assertContains(response, "Cada pieza usó una cantidad distinta")
        self.assertContains(response, 'data-trabajo-plural="piezas"')

    def test_cierre_servicio_genera_ingreso_desde_liquidacion_automatica(self):
        # Ni siquiera las banderas antiguas permiten trasladar patrimonio o personal.
        ConfiguracionOperativaUnidad.objects.update_or_create(
            unidad=self.unidad,
            defaults={
                "cobrar_tarifa_base": True,
                "cobrar_uso_equipo": True,
                "cobrar_mano_obra": True,
            },
        )
        servicio = FablabService.objects.create(
            unidad=self.unidad,
            code="SRV-LIQ-AUTO",
            nombre="Fabricación con liquidación automática",
            tarifa_base=Decimal("10.00"),
            costo_hora_equipo=Decimal("5.00"),
            costo_hora_mano_obra=Decimal("2.00"),
            descuento_externo=Decimal("0.00"),
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            equipo_codigo="SERVICIO",
            equipo_nombre=servicio.nombre,
            titulo_solicitud="Servicio liquidado automáticamente",
            tipo_solicitud="servicio",
            # El segmento externo también tiene cobertura completa de recursos.
            tipo_usuario_solicitante="externo",
            proposito_codigo="servicio_cientifico_tecnologico",
            metodo_pago="transferencia",
            estado="confirmada",
            responsable_asignado=self.responsable_unidad,
            costo_estimado=Decimal("25.00"),
            desglose_cotizacion={
                "valor_referencial": "25.00",
                "aporte_institucional": "0.00",
                "valor_estimado_usuario": "25.00",
            },
        )
        reserva.servicios_solicitados.add(servicio)
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "09:15",
                "ejecucion_hora_fin": "10:45",
                "ejecucion_asistentes_total": "1",
                "ejecucion_cumplimiento": "si",
                "ejecucion_servicios_ids": [str(servicio.pk)],
                "ejecucion_consumibles_json": "[]",
                "ejecucion_referencia_pago": "TRX-AUTOMATICA-001",
                "ejecucion_pago_confirmado": "1",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=reserva).exists())
        self.assertEqual(reserva.costo_real, Decimal("20.50"))
        self.assertEqual(reserva.valor_final_usuario, Decimal("0.00"))
        self.assertEqual(reserva.aporte_institucional_real, Decimal("20.50"))
        self.assertEqual(
            reserva.desglose_liquidacion["variacion"]["valor_usuario"],
            "-25.00",
        )
        self.assertIsNone(reserva.detalle_ejecucion["ingreso"])

    def test_cierre_recursos_calcula_aporte_sin_registrar_ingreso_directo(self):
        UserProfile.objects.update_or_create(
            user=self.coordinador,
            defaults={"tipo_usuario": "docente", "institucion": "UPEC"},
        )
        ConfiguracionOperativaUnidad.objects.update_or_create(
            unidad=self.unidad,
            defaults={
                "tarifa_referencial_hora_equipo": Decimal("10.00"),
                "tarifa_referencial_hora_acompanamiento": Decimal("5.00"),
                "aporte_institucional_recursos_pct": Decimal("50.00"),
            },
        )
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-LIQ-RECURSO",
            nombre="Equipo de liquidación de recursos",
        )
        equipo = UnidadEquipo.objects.create(
            codigo_unidad="UNIT-LIQ-RECURSO",
            equipo=catalogo,
            laboratorio=self.unidad,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.coordinador,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
            equipo_codigo=equipo.codigo_unidad,
            equipo_nombre=catalogo.nombre,
            titulo_solicitud="Uso institucional liquidado",
            tipo_solicitud="equipo",
            tipo_usuario_solicitante="docente",
            proposito_codigo="investigacion_innovacion",
            estado="confirmada",
            responsable_asignado=self.responsable_unidad,
            unidades_seleccionadas=json.dumps(
                [{"id": equipo.pk, "codigo": equipo.codigo_unidad, "nombre": catalogo.nombre}]
            ),
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "08:00",
                "ejecucion_hora_fin": "10:00",
                "ejecucion_asistentes_total": "1",
                "ejecucion_cumplimiento": "si",
                "ejecucion_equipos_ids": [str(equipo.pk)],
                "ejecucion_consumibles_json": "[]",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        self.assertEqual(reserva.costo_real, Decimal("30.00"))
        self.assertEqual(reserva.aporte_institucional_real, Decimal("30.00"))
        self.assertEqual(reserva.valor_final_usuario, Decimal("0.00"))
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=reserva).exists())

    def _reserva_de_piezas(self):
        """Trabajo de tres piezas con su material y su lote listo para el cierre."""
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-PIEZAS-CAT",
            nombre="Impresora de piezas",
        )
        equipo = UnidadEquipo.objects.create(
            codigo_unidad="EQ-PIEZAS-01",
            equipo=catalogo,
            laboratorio=self.unidad,
        )
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="MAT-PIEZAS",
            nombre="Filamento por piezas",
            unidad_medida="g",
            stock_total=Decimal("500"),
            precio_unitario=Decimal("0.0200"),
        )
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo="LOTE-PIEZAS-001",
            cantidad_inicial=Decimal("500"),
            cantidad_actual=Decimal("500"),
            estado="en_uso",
            equipo_en_uso=equipo,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            equipo_codigo=equipo.codigo_unidad,
            equipo_nombre=catalogo.nombre,
            titulo_solicitud="Tres piezas del prototipo",
            tipo_solicitud="servicio",
            proposito_codigo="servicio_cientifico_tecnologico",
            cantidad_piezas=3,
            estado="confirmada",
            responsable_asignado=self.responsable_unidad,
            unidades_seleccionadas=json.dumps(
                [{"id": equipo.pk, "codigo": equipo.codigo_unidad, "nombre": catalogo.nombre}]
            ),
        )
        reserva_consumible = ReservaConsumible.objects.create(
            reserva=reserva,
            consumible=consumible,
            cantidad_solicitada=Decimal("120"),
        )
        return reserva, reserva_consumible, equipo, lote

    def _cierre_de_piezas(self, reserva, fila, piezas="3"):
        return self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "09:00",
                "ejecucion_hora_fin": "11:00",
                "ejecucion_asistentes_total": "1",
                "ejecucion_piezas": piezas,
                "ejecucion_cumplimiento": "si",
                "ejecucion_equipos_ids": [str(fila["equipo_id"])],
                "ejecucion_consumibles_json": json.dumps([fila]),
            },
        )

    def test_cierre_registra_las_piezas_obtenidas_y_su_reparto_de_material(self):
        reserva, reserva_consumible, equipo, lote = self._reserva_de_piezas()
        self.client.force_login(self.coordinador)

        response = self._cierre_de_piezas(
            reserva,
            {
                "reserva_consumible_id": reserva_consumible.pk,
                "consumida": "100",
                "desperdiciada": "0",
                "lote_id": lote.pk,
                "equipo_id": equipo.pk,
                "piezas": 3,
                "modo_cantidad": "distintas",
                "detalle_piezas": ["40", "30", "30"],
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        detalle = reserva.detalle_ejecucion
        self.assertEqual(detalle["piezas_solicitadas"], 3)
        self.assertEqual(detalle["piezas_producidas"], 3)
        consumo = detalle["consumibles"][0]
        self.assertEqual(consumo["piezas"], 3)
        self.assertEqual(consumo["detalle_piezas"], ["40.000", "30.000", "30.000"])
        self.assertEqual(consumo["por_pieza"], "")
        self.assertEqual(consumo["consumida"], "100")

    def test_cierre_con_piezas_iguales_deja_el_promedio_por_pieza(self):
        reserva, reserva_consumible, equipo, lote = self._reserva_de_piezas()
        self.client.force_login(self.coordinador)

        response = self._cierre_de_piezas(
            reserva,
            {
                "reserva_consumible_id": reserva_consumible.pk,
                "consumida": "90",
                "desperdiciada": "0",
                "lote_id": lote.pk,
                "equipo_id": equipo.pk,
                "piezas": 3,
                "modo_cantidad": "iguales",
                "detalle_piezas": [],
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        consumo = reserva.detalle_ejecucion["consumibles"][0]
        self.assertEqual(consumo["por_pieza"], "30.000")
        self.assertEqual(consumo["detalle_piezas"], [])

    def test_cierre_rechaza_un_reparto_por_pieza_que_no_cuadra(self):
        reserva, reserva_consumible, equipo, lote = self._reserva_de_piezas()
        self.client.force_login(self.coordinador)

        response = self._cierre_de_piezas(
            reserva,
            {
                "reserva_consumible_id": reserva_consumible.pk,
                "consumida": "100",
                "desperdiciada": "0",
                "lote_id": lote.pk,
                "equipo_id": equipo.pk,
                "piezas": 3,
                "modo_cantidad": "distintas",
                "detalle_piezas": ["40", "30"],
            },
            piezas="3",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("las 3 piezas obtenidas", response.json()["error"])
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertFalse(reserva.detalle_ejecucion)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("500"))

    def test_cierre_rechaza_ajuste_manual_sin_justificacion(self):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.usuario_ajeno,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            equipo_codigo="SERVICIO",
            equipo_nombre="Servicio sin conceptos",
            titulo_solicitud="Ajuste manual no sustentado",
            tipo_solicitud="servicio",
            proposito_codigo="servicio_cientifico_tecnologico",
            estado="confirmada",
            responsable_asignado=self.responsable_unidad,
        )
        self.client.force_login(self.coordinador)

        response = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "09:00",
                "ejecucion_hora_fin": "10:00",
                "ejecucion_asistentes_total": "1",
                "ejecucion_cumplimiento": "si",
                "ejecucion_consumibles_json": "[]",
                "ejecucion_monto_cobrado": "10.00",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Explica el ajuste", response.json()["error"])
        # Una justificación tampoco autoriza cobrar recursos o personal.
        datos_justificados = response.wsgi_request.POST.copy()
        datos_justificados["ejecucion_justificacion_ajuste"] = "Cargo por acompañamiento del personal."
        justificada = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            datos_justificados,
        )
        self.assertEqual(justificada.status_code, 400)
        self.assertIn("El cobro no puede superar", justificada.json()["error"])
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertFalse(reserva.detalle_ejecucion)
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=reserva).exists())


class AdminAgrupadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superusuario = get_user_model().objects.create_superuser(
            username="super-admin-agrupado",
            email="admin@upec.edu.ec",
            password="clave-segura",
        )

    def test_indice_admin_organiza_modelos_por_categorias(self):
        self.client.force_login(self.superusuario)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centro de administración")
        self.assertContains(response, "Usuarios, responsables y acceso")
        categorias = {app["name"] for app in response.context["app_list"]}
        # Un area por tipo de unidad; lo que pertenece a una unidad vive dentro.
        for tipo in ("Laboratorios", "Plantas piloto", "Centros experimentales", "Observatorios"):
            self.assertIn(tipo, categorias)
        for mezclada in ("Gestión y reservas", "Inventario e insumos", "Producción",
                         "Indicadores y reportes", "Laboratorios y unidades"):
            self.assertNotIn(mezclada, categorias)
        # Los equipos van con su tipo; solo el catalogo de categorias es compartido.
        self.assertNotIn("Equipos y recursos tecnológicos", categorias)
        # Los Centros I+D tienen datos y operación propios: área aparte.
        self.assertIn("Centros de Investigación y Desarrollo", categorias)
        centros = next(app for app in response.context["app_list"] if app["slug"] == "centros_id")
        self.assertTrue({"Zona", "HerramientaCentro", "HorarioRecurso", "BloqueoRecurso",
                         "HabilitacionEquipo", "LineaInvestigacion"}
                        <= {modelo["object_name"] for modelo in centros["models"]})
        # Los módulos pueden aportar registros auxiliares: conservan su acceso
        # en la sección complementaria sin desplazar los dominios anteriores.
        complementaria = next((app for app in response.context['app_list']
            if app['slug'] == 'configuracion'), None)
        if complementaria:
            self.assertEqual(complementaria['name'], 'Configuración complementaria')
            self.assertTrue(complementaria['models'])
            self.assertTrue(all(modelo.get('admin_url') for modelo in complementaria['models']))

    def test_indice_admin_usa_menu_lateral_y_visualizador_por_categoria(self):
        self.client.force_login(self.superusuario)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="cittAdminConsole"')
        self.assertContains(response, 'data-admin-target="resumen"')
        self.assertContains(response, 'data-admin-target="plantas_piloto"')
        self.assertContains(response, 'data-admin-view="plantas_piloto"')
        self.assertContains(response, 'data-open-admin-view="plantas_piloto"')
        self.assertContains(response, "20260921-por-unidad-v219")
        self.assertContains(response, 'class="citt-admin-area-card"')
        self.assertContains(response, 'class="citt-admin-category__icon is-building"')
        self.assertContains(response, 'id="cittAdminViewerTitle"')
        self.assertNotContains(response, 'id="reservas"')
        self.assertNotContains(response, 'id="unidades"')

    def test_estilos_administrativos_tambien_cargan_en_listados_y_formularios(self):
        self.client.force_login(self.superusuario)

        listado = self.client.get(reverse("admin:directorio_unidades_unidad_changelist"))
        formulario = self.client.get(reverse("admin:directorio_unidades_unidad_add"))

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(formulario.status_code, 200)
        self.assertContains(listado, "20260921-por-unidad-v219")
        self.assertContains(formulario, "20260921-por-unidad-v219")
        self.assertContains(listado, "Unidades")
        self.assertContains(formulario, "Añadir Unidad")
