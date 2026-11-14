"""Carga casos ideales y críticos para evaluar la consola de un FabLab."""

import json
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.gestion_unidades.management.datos_demo import ComandoDatosDemostrativosMixin
from apps.reservas.presentation.capacidad import comando_reservas
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class Command(ComandoDatosDemostrativosMixin, BaseCommand):
    help = (
        "Carga escenarios demostrativos ideales y críticos, sin duplicarlos, "
        "para comprobar reservas, activos, inventario, mantenimiento y finanzas."
    )

    PREFIX = "[EVAL"

    def add_arguments(self, parser):
        self.agregar_argumentos_datos_demo(parser)

    @staticmethod
    def _fecha_hora(fecha, valor_hora):
        return timezone.make_aware(
            datetime.combine(fecha, valor_hora),
            timezone.get_current_timezone(),
        )

    @staticmethod
    def _registrar_auditoria(unidad, usuario, objeto, descripcion):
        entidad = f"{objeto._meta.app_label}.{objeto.__class__.__name__}"
        if RegistroAuditoriaUnidad.objects.filter(
            unidad=unidad,
            entidad=entidad,
            objeto_id=str(objeto.pk),
            descripcion=descripcion,
        ).exists():
            return
        RegistroAuditoriaUnidad.objects.create(
            unidad=unidad,
            usuario=usuario,
            accion="crear",
            entidad=entidad,
            objeto_id=str(objeto.pk),
            descripcion=descripcion,
            datos_nuevos={"origen": "escenarios_evaluacion_fablab"},
        )

    def _reserva(self, unidad, usuario, responsable, titulo, **datos):
        reserva = Reserva.objects.filter(
            laboratorio=unidad,
            titulo_solicitud=titulo,
        ).order_by("pk").first()
        creada = reserva is None
        if creada:
            equipo = datos.pop("equipo")
            fecha = datos.pop("fecha")
            hora_inicio = datos.pop("hora_inicio", time(9, 0))
            hora_fin = datos.pop("hora_fin", time(11, 0))
            estado = datos.pop("estado", "pendiente")
            resultado_cierre = datos.pop("resultado_cierre", "")
            reserva = Reserva.objects.create(
                laboratorio=unidad,
                usuario=usuario,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                horas_seleccionadas=json.dumps(
                    list(range(hora_inicio.hour, hora_fin.hour))
                ),
                equipo_codigo=equipo.codigo_unidad,
                equipo_nombre=equipo.equipo.nombre,
                unidades_seleccionadas=json.dumps(
                    [{"id": equipo.pk, "codigo": equipo.codigo_unidad}]
                ),
                nombre_solicitante=usuario.get_full_name() or usuario.get_username(),
                correo_solicitante=usuario.email,
                telefono_solicitante="099 000 2026",
                institucion="Universidad Politécnica Estatal del Carchi",
                tipo_usuario_solicitante="docente",
                facultad_solicitante="agropecuarias_ambientales",
                carrera_solicitante="computacion",
                nivel_academico_solicitante="docente",
                tipo_uso="practica",
                proposito=datos.pop(
                    "proposito",
                    "Evaluar el flujo integral de atención y trazabilidad del laboratorio.",
                ),
                proposito_codigo=datos.pop("proposito_codigo", "docencia_practica"),
                subtipo_actividad=datos.pop("subtipo_actividad", "practica_curricular"),
                alcance_beneficiario=datos.pop("alcance_beneficiario", "perfil_solicitante"),
                vinculacion_actividad=datos.pop("vinculacion_actividad", "manual"),
                referencia_actividad=datos.pop(
                    "referencia_actividad", "Escenario controlado de evaluación"
                ),
                responsable_actividad=usuario.get_full_name() or usuario.get_username(),
                origen_programacion=datos.pop("origen_programacion", "adicional"),
                descripcion_proyecto=datos.pop(
                    "descripcion_proyecto",
                    "Caso demostrativo con datos completos para validar la consola.",
                ),
                requisitos_especiales=datos.pop(
                    "requisitos_especiales",
                    "Verificar inducción, archivo técnico, material y disponibilidad.",
                ),
                titulo_solicitud=titulo,
                numero_participantes=datos.pop("numero_participantes", 4),
                estado=estado,
                resultado_cierre=resultado_cierre,
                responsable_asignado=responsable,
                validada_por=unidad.administrador,
                fecha_validacion=timezone.now(),
                observaciones_validacion=datos.pop(
                    "observaciones_validacion",
                    "Registro preparado para evaluación funcional.",
                ),
                **datos,
            )
        RegistroParticipanteReserva.objects.update_or_create(
            reserva=reserva,
            usuario=usuario,
            defaults={
                "rol": "solicitante",
                "nombre": usuario.get_full_name() or usuario.get_username(),
                "correo": usuario.email,
                "tipo_usuario": "docente",
                "institucion": "UPEC",
            },
        )
        return reserva, creada

    @staticmethod
    def _lote_con_ingreso(
        unidad,
        usuario,
        consumible,
        codigo,
        cantidad,
        *,
        estado="bodega",
        equipo=None,
        bodega="Bodega principal FabLab",
        estanteria="Estantería de evaluación",
        posicion="Nivel 1 · Posición A",
        vencimiento=None,
        costo=None,
    ):
        lote = LoteConsumible.objects.filter(
            consumible=consumible,
            codigo=codigo,
        ).first()
        creado = lote is None
        if creado:
            lote = LoteConsumible.objects.create(
                consumible=consumible,
                codigo=codigo,
                cantidad_inicial=cantidad,
                cantidad_actual=Decimal("0"),
                estado=estado,
                equipo_en_uso=equipo if estado == "en_uso" else None,
                bodega=bodega,
                estanteria=estanteria,
                posicion=posicion,
                fecha_apertura=timezone.localdate() if estado == "en_uso" else None,
                fecha_vencimiento=vencimiento,
                costo_unitario=costo if costo is not None else consumible.precio_unitario,
                documento_recepcion=f"ACTA-{codigo}",
                observaciones="Lote demostrativo para validar ubicación y trazabilidad.",
                creado_por=usuario,
                actualizado_por=usuario,
            )
            EntradaInventario.objects.create(
                consumible=consumible,
                unidad=unidad,
                tipo="ingreso",
                motivo="recepcion",
                cantidad=cantidad,
                lote_inventario=lote,
                equipo=equipo if estado == "en_uso" else None,
                costo_unitario=lote.costo_unitario,
                responsable_costo=(
                    "institucional"
                    if consumible.origen_abastecimiento == "compra_publica"
                    else "laboratorio"
                ),
                usuario=usuario,
                referencia=f"REC-{codigo}",
                nota="Recepción física demostrativa con ubicación documentada.",
            )
        return lote, creado

    @staticmethod
    def _movimiento(unidad, usuario, referencia, **datos):
        movimiento = EntradaInventario.objects.filter(
            unidad=unidad,
            referencia=referencia,
        ).first()
        if movimiento:
            return movimiento, False
        return EntradaInventario.objects.create(
            unidad=unidad,
            usuario=usuario,
            referencia=referencia,
            **datos,
        ), True

    @transaction.atomic
    @comando_reservas
    def handle(self, *args, **options):
        slug = self.validar_opciones_datos_demo(options)
        try:
            unidad = Unidad.objects.select_for_update().get(slug=slug)
        except Unidad.DoesNotExist as exc:
            raise CommandError(f'No existe una unidad con slug "{slug}".') from exc

        usuario = unidad.administrador or get_user_model().objects.filter(
            is_superuser=True
        ).order_by("pk").first()
        if usuario is None:
            usuario = get_user_model().objects.filter(is_staff=True).order_by("pk").first()
        if usuario is None:
            raise CommandError("El laboratorio necesita un administrador para crear la trazabilidad.")

        solicitante = get_user_model().objects.filter(
            username="docente.demo.fablab"
        ).first() or usuario
        responsable = ResponsableUnidad.objects.filter(
            unidad=unidad,
            usuario__isnull=False,
            activo=True,
        ).order_by("orden", "pk").first()
        if responsable is None:
            responsable = ResponsableUnidad.objects.filter(
                unidad=unidad,
                activo=True,
            ).order_by("orden", "pk").first()

        # Un equipo puede tener varias unidades fisicas; los escenarios usan
        # siempre la primera por codigo (FAB-UNIT-...-01).
        equipos = {}
        for item in UnidadEquipo.objects.filter(
            laboratorio=unidad,
            activa=True,
            equipo__codigo__in={
                "FAB-EQ-FDM", "FAB-EQ-SLA", "FAB-EQ-LASER",
                "FAB-EQ-CNC", "FAB-EQ-SCAN", "FAB-EQ-CAD",
            },
        ).select_related("equipo").order_by("codigo_unidad"):
            equipos.setdefault(item.equipo.codigo, item)
        consumibles = {
            item.codigo: item
            for item in Consumible.objects.filter(
                unidad=unidad,
                activo=True,
            )
        }
        faltantes = {
            "equipos": sorted({"FAB-EQ-FDM", "FAB-EQ-SLA", "FAB-EQ-LASER", "FAB-EQ-CNC", "FAB-EQ-SCAN"} - equipos.keys()),
            "insumos": sorted({"FAB-MAT-PLA", "FAB-MAT-PLA-ROJ", "FAB-MAT-RESINA", "FAB-CON-CINTA"} - consumibles.keys()),
        }
        if any(faltantes.values()):
            raise CommandError(
                "Faltan datos base. Ejecuta primero cargar_pruebas_fablab. "
                f"Detalle: {faltantes}"
            )

        hoy = timezone.localdate()
        sabado = hoy + timedelta(days=(5 - hoy.weekday()) % 7 or 7)
        fdm = equipos["FAB-EQ-FDM"]
        sla = equipos["FAB-EQ-SLA"]
        laser = equipos["FAB-EQ-LASER"]
        cnc = equipos["FAB-EQ-CNC"]
        scanner = equipos["FAB-EQ-SCAN"]

        reservas = {}
        escenarios_reserva = (
            (
                "ideal",
                "[EVAL IDEAL] Servicio FDM atendido y cerrado",
                {
                    "equipo": fdm,
                    "fecha": hoy - timedelta(days=1),
                    "tipo_solicitud": "servicio",
                    "provision_consumibles": "unidad",
                    "solicito_equipo": True,
                    "incluye_espacio": True,
                    "solicito_espacio": True,
                    "alcance_espacio": "areas",
                    "modalidad_servicio": "modelo_listo",
                    "desglose_cotizacion": {"material": 9.0, "equipo": 12.0, "mano_obra": 8.0},
                    "costo_estimado": Decimal("29.00"),
                    "cotizacion_aceptada": True,
                    "metodo_pago": "transferencia",
                    "estado": "completada",
                    "resultado_cierre": "atendida",
                    "fecha_inicio_atencion": self._fecha_hora(hoy - timedelta(days=1), time(9, 2)),
                    "fecha_cierre": self._fecha_hora(hoy - timedelta(days=1), time(10, 48)),
                    "detalle_cierre": "Pieza entregada, consumo real registrado y área liberada.",
                },
            ),
            (
                "no_presentado",
                "[EVAL CRÍTICO] Usuario no se presentó",
                {
                    "equipo": scanner,
                    "fecha": hoy - timedelta(days=2),
                    "tipo_solicitud": "recursos",
                    "provision_consumibles": "ninguno",
                    "solicito_equipo": True,
                    "estado": "no_presentado",
                    "resultado_cierre": "no_presentado",
                    "fecha_cierre": self._fecha_hora(hoy - timedelta(days=2), time(11, 15)),
                    "detalle_cierre": "Se esperaron 15 minutos y se registró la inasistencia.",
                },
            ),
            (
                "no_atendida",
                "[EVAL CRÍTICO] Solicitud no atendida por falla operativa",
                {
                    "equipo": sla,
                    "fecha": hoy - timedelta(days=3),
                    "tipo_solicitud": "recursos",
                    "provision_consumibles": "unidad",
                    "solicito_equipo": True,
                    "estado": "no_atendida",
                    "resultado_cierre": "no_atendida",
                    "fecha_cierre": self._fecha_hora(hoy - timedelta(days=3), time(15, 0)),
                    "detalle_cierre": "No hubo responsable disponible; requiere acción correctiva.",
                },
            ),
            (
                "pendiente",
                "[EVAL PENDIENTE] Servicio con cotización por revisar",
                {
                    "equipo": laser,
                    "fecha": hoy + timedelta(days=2),
                    "tipo_solicitud": "servicio",
                    "provision_consumibles": "revision",
                    "solicito_equipo": True,
                    "incluye_espacio": True,
                    "solicito_espacio": True,
                    "alcance_espacio": "areas",
                    "modalidad_servicio": "diseno_asistido",
                    "desglose_cotizacion": {"material": 18.0, "equipo": 15.0, "diseño": 8.0},
                    "costo_estimado": Decimal("41.00"),
                    "metodo_pago": "por_definir",
                    "estado": "pendiente",
                    "observaciones_validacion": "Pendiente confirmar material, archivo vectorial y pago.",
                },
            ),
            (
                "fin_semana",
                "[EVAL EXCEPCIÓN] Práctica autorizada en sábado",
                {
                    "equipo": cnc,
                    "fecha": sabado,
                    "hora_inicio": time(9, 0),
                    "hora_fin": time(12, 0),
                    "tipo_solicitud": "recursos",
                    "provision_consumibles": "propios",
                    "solicito_equipo": True,
                    "estado": "confirmada",
                    "observaciones_validacion": "Excepción de fin de semana aprobada por administración.",
                },
            ),
        )
        for clave, titulo, datos in escenarios_reserva:
            reserva, _ = self._reserva(
                unidad, solicitante, responsable, titulo, **datos
            )
            reservas[clave] = reserva
            self._registrar_auditoria(
                unidad, usuario, reserva, "Escenario de evaluación de reserva creado"
            )

        participantes_demo = list(
            get_user_model().objects.filter(
                username__startswith="estudiante.demo.fablab"
            ).select_related("profile").order_by("username")[:3]
        )
        composicion_reservas = {
            "ideal": (4, "asistio"),
            "no_presentado": (1, "no_asistio"),
            "no_atendida": (4, "asistio"),
            "pendiente": (1, "prevista"),
            "fin_semana": (4, "prevista"),
        }
        for clave, (cantidad, asistencia_solicitante) in composicion_reservas.items():
            reserva = reservas[clave]
            if reserva.numero_participantes != cantidad:
                reserva.numero_participantes = cantidad
                reserva.save(update_fields=["numero_participantes"])
            RegistroParticipanteReserva.objects.filter(
                reserva=reserva,
                usuario=solicitante,
            ).update(asistencia=asistencia_solicitante)
            if clave not in {"ideal", "no_atendida", "fin_semana"}:
                reserva.participantes.clear()
                RegistroParticipanteReserva.objects.filter(
                    reserva=reserva,
                    rol="participante",
                ).delete()
                continue
            reserva.participantes.set(participantes_demo)
            for participante in participantes_demo:
                perfil = getattr(participante, "profile", None)
                RegistroParticipanteReserva.objects.update_or_create(
                    reserva=reserva,
                    usuario=participante,
                    defaults={
                        "rol": "participante",
                        "nombre": participante.get_full_name() or participante.get_username(),
                        "correo": participante.email,
                        "tipo_usuario": getattr(perfil, "tipo_usuario", "estudiante"),
                        "facultad": getattr(perfil, "facultad", "agropecuarias_ambientales"),
                        "carrera": getattr(perfil, "carrera", "computacion"),
                        "nivel_academico": getattr(perfil, "nivel_academico", "sexto_semestre"),
                        "institucion": getattr(perfil, "institucion", "UPEC"),
                        "asistencia": (
                            "asistio" if clave in {"ideal", "no_atendida"} else "prevista"
                        ),
                    },
                )

        activos_demostrativos = {
            "UNIT-TEST-004-01": (
                "donacion", "ACTA-DONACION-DEMO-2024-004", Decimal("900.00")
            ),
            "UNIT-TEST-004-02": (
                "donacion", "ACTA-DONACION-DEMO-2024-005", Decimal("900.00")
            ),
            "FAB-EQ-FDM": (
                "asignacion_institucional", "ACTA-UPEC-FAB-2024-001", Decimal("1800.00")
            ),
            "FAB-EQ-SLA": (
                "proyecto", "PROY-IMPRESION-3D-2024-017", Decimal("2200.00")
            ),
            "FAB-EQ-LASER": (
                "compra_publica", "ORDEN-COMPRA-UPEC-2023-084", Decimal("8500.00")
            ),
            "FAB-EQ-CNC": (
                "compra_publica", "ORDEN-COMPRA-UPEC-2023-085", Decimal("12000.00")
            ),
            "FAB-EQ-SCAN": (
                "proyecto", "PROY-DIGITALIZACION-2025-006", Decimal("4500.00")
            ),
            "FAB-EQ-CAD": (
                "asignacion_institucional", "ACTA-UPEC-TIC-2025-022", Decimal("2800.00")
            ),
        }
        for codigo, (origen, documento, valor) in activos_demostrativos.items():
            activo = equipos.get(codigo) or UnidadEquipo.objects.filter(
                laboratorio=unidad,
                codigo_unidad=codigo,
                activa=True,
            ).first()
            if activo is None:
                continue
            if not activo.numero_serie:
                activo.numero_serie = f"DEMO-{activo.codigo_unidad}"
            activo.origen_adquisicion = origen
            activo.fecha_adquisicion = hoy - timedelta(days=730)
            activo.documento_adquisicion = documento
            activo.valor_referencial = valor
            activo.save(update_fields=[
                "numero_serie",
                "origen_adquisicion",
                "fecha_adquisicion",
                "documento_adquisicion",
                "valor_referencial",
            ])

        servicios = {
            servicio.code: servicio
            for servicio in FablabService.objects.filter(unidad=unidad, activo=True)
        }
        espacios = list(unidad.espacios_reservables.filter(activo=True))
        software = list(SoftwareDisponible.objects.filter(unidad=unidad, activo=True))
        if servicios.get("FAB-SRV-FDM"):
            reservas["ideal"].servicios_solicitados.set([servicios["FAB-SRV-FDM"]])
        if servicios.get("FAB-SRV-LASER"):
            reservas["pendiente"].servicios_solicitados.set([servicios["FAB-SRV-LASER"]])
        reservas["ideal"].software_solicitado.set(
            [item for item in software if "Cura" in item.nombre]
        )
        if espacios:
            for reserva in reservas.values():
                relacionados = [
                    espacio for espacio in espacios
                    if espacio.equipos_asociados.filter(
                        pk__in=[item["id"] for item in reserva.get_unidades_seleccionadas_list()]
                    ).exists()
                ]
                if relacionados:
                    reserva.espacios_solicitados.set(relacionados[:1])

        pla = consumibles["FAB-MAT-PLA"]
        pla_rojo = consumibles["FAB-MAT-PLA-ROJ"]
        resina = consumibles["FAB-MAT-RESINA"]
        cinta = consumibles["FAB-CON-CINTA"]
        for insumo in consumibles.values():
            contenido = (
                Decimal("1000")
                if insumo.unidad_medida in {"g", "mL"}
                else Decimal("1")
            )
            if insumo.cantidad_por_presentacion != contenido:
                insumo.cantidad_por_presentacion = contenido
                insumo.save(update_fields=["cantidad_por_presentacion"])
        pla.minimo = Decimal("1000")
        pla.stock_seguridad = Decimal("500")
        pla.stock_objetivo = Decimal("5000")
        pla.plazo_reposicion_dias = 30
        pla.especificacion_tecnica = "PLA 1,75 mm ±0,03 mm, temperatura 190–220 °C, bobina sellada y seca."
        pla.save()
        pla_rojo.minimo = Decimal("2200")
        pla_rojo.stock_seguridad = Decimal("1800")
        pla_rojo.stock_objetivo = Decimal("5000")
        pla_rojo.plazo_reposicion_dias = 45
        pla_rojo.especificacion_tecnica = "PLA rojo 1,75 mm homologado para extrusor FDM."
        pla_rojo.save()

        fichas_abastecimiento = {
            "EQ00234": (
                "Filamento PLA demostrativo",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA 1,75 mm de uso general; bobina sellada y protegida de humedad.",
            ),
            "FAB-MAT-PLA": (
                "Filamento técnico homologado",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA 1,75 mm ±0,03 mm; bobina sellada, seca y con trazabilidad de lote.",
            ),
            "FAB-MAT-PLA-AZU": (
                "Filamento técnico homologado",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA azul 1,75 mm ±0,03 mm homologado para extrusor FDM.",
            ),
            "FAB-MAT-PLA-GRI": (
                "Filamento técnico homologado",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA gris 1,75 mm ±0,03 mm homologado para extrusor FDM.",
            ),
            "FAB-MAT-PLA-NEG": (
                "Filamento técnico homologado",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA negro 1,75 mm ±0,03 mm homologado para extrusor FDM.",
            ),
            "FAB-MAT-PLA-ROJ": (
                "Filamento técnico homologado",
                "Proveedor demostrativo de fabricación aditiva",
                "PLA rojo 1,75 mm homologado para extrusor FDM.",
            ),
            "FAB-MAT-RESINA": (
                "Resina técnica estándar",
                "Proveedor demostrativo de fotopolímeros",
                "Resina 405 nm para impresión SLA; conservar cerrada, ventilada y sin luz directa.",
            ),
            "FAB-CON-CINTA": (
                "Consumible auxiliar homologado",
                "Bodega institucional UPEC",
                "Cinta de enmascarar de adhesión media, sin residuos sobre superficies de trabajo.",
            ),
            "FAB-MAT-MDF3": (
                "Tablero técnico estándar",
                "Proveedor demostrativo de materiales planos",
                "MDF de 3 mm, superficie uniforme, seco y compatible con corte láser/CNC.",
            ),
            "FAB-MAT-ACR3": (
                "Acrílico técnico estándar",
                "Proveedor demostrativo de materiales planos",
                "PMMA de 3 mm, espesor uniforme y película protectora para corte láser.",
            ),
        }
        for codigo, (marca, proveedor, especificacion) in fichas_abastecimiento.items():
            insumo = consumibles.get(codigo)
            if insumo is None:
                continue
            insumo.marca = marca
            insumo.proveedor_referencia = proveedor
            insumo.especificacion_tecnica = especificacion
            insumo.save(update_fields=[
                "marca", "proveedor_referencia", "especificacion_tecnica",
            ])

        lote_uso, lote_uso_creado = self._lote_con_ingreso(
            unidad,
            usuario,
            pla,
            "EVAL-PLA-USO-001",
            Decimal("1000"),
            estado="en_uso",
            equipo=fdm,
            bodega="Área de impresión 3D",
            estanteria="Soporte de bobina",
            posicion="Impresora FDM · Alimentador 1",
            vencimiento=hoy + timedelta(days=540),
            costo=Decimal("0.0250"),
        )
        lote_bodega, lote_bodega_creado = self._lote_con_ingreso(
            unidad,
            usuario,
            pla,
            "EVAL-PLA-BOD-001",
            Decimal("1000"),
            bodega="Bodega FabLab",
            estanteria="Estantería FDM",
            posicion="Nivel 2 · Caja blanca",
            vencimiento=hoy + timedelta(days=720),
            costo=Decimal("0.0250"),
        )
        lote_vencido, lote_vencido_creado = self._lote_con_ingreso(
            unidad,
            usuario,
            resina,
            "EVAL-RES-VENC-001",
            Decimal("300"),
            bodega="Gabinete ventilado de resinas",
            estanteria="Estante inferior",
            posicion="Bandeja de cuarentena",
            vencimiento=hoy - timedelta(days=5),
            costo=Decimal("0.0600"),
        )
        lote_proximo, lote_proximo_creado = self._lote_con_ingreso(
            unidad,
            usuario,
            resina,
            "EVAL-RES-PROX-001",
            Decimal("500"),
            bodega="Gabinete ventilado de resinas",
            estanteria="Estante superior",
            posicion="Fila A · Posición 2",
            vencimiento=hoy + timedelta(days=12),
            costo=Decimal("0.0600"),
        )
        lote_perdido, lote_perdido_creado = self._lote_con_ingreso(
            unidad,
            usuario,
            cinta,
            "EVAL-CINTA-EXT-001",
            Decimal("1"),
            bodega="Gabinete de herramientas",
            estanteria="Cajón de consumibles auxiliares",
            posicion="Compartimento C-04",
            costo=Decimal("1.5000"),
        )

        # Muestras completas para distinguir unidades cerradas de una
        # presentación abierta. Los códigos DEMO hacen la carga idempotente y
        # permiten conservar cualquier lote real creado por el usuario.
        lotes_demostrativos = []
        especificaciones_lote = (
            (
                "FAB-MAT-PLA-AZU", "DEMO-PLA-AZU-BOD-001", Decimal("2000"),
                "bodega", None, "Bodega FabLab", "Estantería FDM", "Nivel 1 · Azul",
            ),
            (
                "FAB-MAT-PLA-AZU", "DEMO-PLA-AZU-USO-001", Decimal("1000"),
                "en_uso", fdm, "Área de impresión 3D", "Soporte de bobina", "Impresora FDM · Azul",
            ),
            (
                "FAB-MAT-PLA-GRI", "DEMO-PLA-GRI-BOD-001", Decimal("2000"),
                "bodega", None, "Bodega FabLab", "Estantería FDM", "Nivel 1 · Gris",
            ),
            (
                "FAB-MAT-PLA-NEG", "DEMO-PLA-NEG-USO-001", Decimal("1000"),
                "en_uso", fdm, "Área de impresión 3D", "Soporte de bobina", "Impresora FDM · Negro",
            ),
            (
                "FAB-MAT-RESINA", "DEMO-RES-USO-001", Decimal("1000"),
                "en_uso", sla, "Área de impresión 3D", "Gabinete de proceso", "Impresora SLA · Tanque 1",
            ),
            (
                "FAB-MAT-MDF3", "DEMO-MDF-BOD-001", Decimal("8"),
                "bodega", None, "Bodega de materiales planos", "Rack vertical", "MDF · Posición 03",
            ),
            (
                "FAB-MAT-ACR3", "DEMO-ACR-BOD-001", Decimal("6"),
                "bodega", None, "Bodega de materiales planos", "Rack vertical", "Acrílico · Posición 05",
            ),
        )
        for (
            codigo_insumo, codigo_lote, cantidad_lote, estado_lote,
            equipo_lote, bodega_lote, estanteria_lote, posicion_lote,
        ) in especificaciones_lote:
            insumo_lote = consumibles.get(codigo_insumo)
            if insumo_lote is None:
                continue
            lote_demo, creado_demo = self._lote_con_ingreso(
                unidad,
                usuario,
                insumo_lote,
                codigo_lote,
                cantidad_lote,
                estado=estado_lote,
                equipo=equipo_lote,
                bodega=bodega_lote,
                estanteria=estanteria_lote,
                posicion=posicion_lote,
                vencimiento=hoy + timedelta(days=540),
                costo=insumo_lote.precio_unitario,
            )
            lotes_demostrativos.append((lote_demo, creado_demo))

        lotes_por_codigo = {lote.codigo: lote for lote, _creado in lotes_demostrativos}
        consumos_demostrativos = (
            (
                "DEMO-CONSUMO-PLA-AZU-001", "DEMO-PLA-AZU-USO-001",
                Decimal("350"), "consumo_practica", fdm,
                "Uso parcial en práctica: quedan 650 g visibles en la bobina abierta.",
            ),
            (
                "DEMO-CONSUMO-PLA-NEG-001", "DEMO-PLA-NEG-USO-001",
                Decimal("625"), "consumo_produccion", fdm,
                "Fabricación de prototipo: quedan 375 g visibles en la bobina abierta.",
            ),
            (
                "DEMO-CONSUMO-RESINA-001", "DEMO-RES-USO-001",
                Decimal("420"), "consumo_produccion", sla,
                "Impresión SLA: quedan 580 mL visibles en el envase abierto.",
            ),
        )
        movimientos_demostrativos = []
        for referencia, codigo_lote, cantidad_salida, motivo, equipo_salida, nota in consumos_demostrativos:
            lote_demo = lotes_por_codigo.get(codigo_lote)
            if lote_demo is None:
                continue
            movimiento_demo, _ = self._movimiento(
                unidad,
                usuario,
                referencia,
                consumible=lote_demo.consumible,
                tipo="salida",
                motivo=motivo,
                cantidad=cantidad_salida,
                lote_inventario=lote_demo,
                equipo=equipo_salida,
                costo_unitario=lote_demo.costo_unitario,
                responsable_costo="institucional",
                nota=nota,
            )
            movimientos_demostrativos.append(movimiento_demo)

        incidencia = IncidenciaEquipo.objects.filter(
            equipo=fdm,
            titulo="[EVAL CRÍTICO] Atasco de extrusor con pieza incompleta",
        ).first()
        if incidencia is None:
            incidencia = IncidenciaEquipo.objects.create(
                equipo=fdm,
                unidad=unidad,
                titulo="[EVAL CRÍTICO] Atasco de extrusor con pieza incompleta",
                tipo="falla",
                prioridad="critica",
                estado="evaluacion",
                descripcion=(
                    "La fabricación se detuvo a los 80 g; la pieza incompleta se clasifica "
                    "como desperdicio asumido por el laboratorio."
                ),
                detiene_operacion=True,
                reportada_por=usuario,
                asignada_a=responsable.usuario if responsable and responsable.usuario_id else usuario,
            )
        self._registrar_auditoria(
            unidad, usuario, incidencia, "Escenario crítico de incidencia creado"
        )
        incidencia_media = IncidenciaEquipo.objects.filter(
            equipo=scanner,
            titulo="[EVAL AVISO] Marcadores de calibración incompletos",
        ).first()
        if incidencia_media is None:
            incidencia_media = IncidenciaEquipo.objects.create(
                equipo=scanner,
                unidad=unidad,
                titulo="[EVAL AVISO] Marcadores de calibración incompletos",
                tipo="accesorio",
                prioridad="media",
                estado="abierta",
                descripcion="Faltan dos marcadores; el equipo funciona con limitaciones.",
                detiene_operacion=False,
                reportada_por=usuario,
            )

        ReservaConsumible.objects.update_or_create(
            reserva=reservas["ideal"],
            consumible=pla,
            defaults={
                "cantidad_solicitada": Decimal("150"),
                "cantidad_aprobada": Decimal("150"),
                "cantidad_consumida": Decimal("120"),
                "metodo_estimacion": "simulacion",
            },
        )
        consumo, _ = self._movimiento(
            unidad,
            usuario,
            "EVAL-CONSUMO-FDM-001",
            consumible=pla,
            tipo="salida",
            motivo="consumo_produccion",
            cantidad=Decimal("120"),
            lote_inventario=lote_uso,
            equipo=fdm,
            reserva=reservas["ideal"],
            costo_unitario=Decimal("0.0250"),
            responsable_costo="usuario",
            nota="Consumo efectivo de la pieza terminada y entregada.",
        )
        desperdicio, _ = self._movimiento(
            unidad,
            usuario,
            "EVAL-DESPERDICIO-FDM-001",
            consumible=pla,
            tipo="salida",
            motivo="desperdicio_equipo",
            cantidad=Decimal("80"),
            lote_inventario=lote_uso,
            equipo=fdm,
            incidencia=incidencia,
            costo_unitario=Decimal("0.0250"),
            responsable_costo="laboratorio",
            nota="Material de pieza incompleta por falla; no se factura al usuario.",
        )
        perdida, _ = self._movimiento(
            unidad,
            usuario,
            "EVAL-EXTRAVIO-CINTA-001",
            consumible=cinta,
            tipo="salida",
            motivo="extravio",
            cantidad=Decimal("1"),
            lote_inventario=lote_perdido,
            costo_unitario=Decimal("1.5000"),
            responsable_costo="laboratorio",
            nota="Diferencia detectada durante el conteo físico de bodega.",
        )
        for lote, creado in (
            (lote_uso, lote_uso_creado),
            (lote_bodega, lote_bodega_creado),
            (lote_vencido, lote_vencido_creado),
            (lote_proximo, lote_proximo_creado),
            (lote_perdido, lote_perdido_creado),
            *lotes_demostrativos,
        ):
            if creado:
                self._registrar_auditoria(
                    unidad, usuario, lote, "Lote físico de evaluación recibido"
                )
        for movimiento in (consumo, desperdicio, perdida, *movimientos_demostrativos):
            self._registrar_auditoria(
                unidad, usuario, movimiento, "Movimiento trazable de evaluación creado"
            )

        # Historial equilibrado para evaluar gráficas semanales, mensuales y ABC
        # sin alterar la existencia final demostrativa.
        for indice, dias_atras in enumerate((155, 125, 95, 65, 35, 12), start=1):
            fecha_hist = hoy - timedelta(days=dias_atras)
            for insumo, equipo_hist, cantidad, costo in (
                (pla, fdm, Decimal(180 + indice * 20), Decimal("0.0250")),
                (resina, sla, Decimal(80 + indice * 10), Decimal("0.0600")),
            ):
                codigo = insumo.codigo.replace("FAB-MAT-", "")
                ingreso_hist, _ = self._movimiento(
                    unidad,
                    usuario,
                    f"HIST-DEMO-{codigo}-{indice:02d}-IN",
                    consumible=insumo,
                    tipo="ingreso",
                    motivo="recepcion",
                    cantidad=cantidad,
                    equipo=equipo_hist,
                    costo_unitario=costo,
                    responsable_costo="institucional",
                    fecha=self._fecha_hora(fecha_hist, time(8, 0)),
                    nota="Ingreso histórico equilibrado para evaluar analítica de inventario.",
                )
                salida_hist, _ = self._movimiento(
                    unidad,
                    usuario,
                    f"HIST-DEMO-{codigo}-{indice:02d}-OUT",
                    consumible=insumo,
                    tipo="salida",
                    motivo="consumo_practica",
                    cantidad=cantidad,
                    equipo=equipo_hist,
                    costo_unitario=costo,
                    responsable_costo="institucional",
                    fecha=self._fecha_hora(fecha_hist + timedelta(days=4), time(15, 0)),
                    nota="Consumo histórico equilibrado para evaluar demanda y clasificación ABC.",
                )
                for movimiento_hist in (ingreso_hist, salida_hist):
                    self._registrar_auditoria(
                        unidad,
                        usuario,
                        movimiento_hist,
                        "Movimiento histórico demostrativo creado",
                    )

        # Serie amplia y variable: todos los insumos principales participan en
        # seis meses. Las entradas y salidas se equilibran en el período para
        # poblar gráficas sin alterar el saldo final de cada ficha.
        factores_ingreso = (Decimal("3"), Decimal("1"), Decimal("2"), Decimal("1"), Decimal("3"), Decimal("2"))
        factores_salida = (Decimal("1"), Decimal("2"), Decimal("1"), Decimal("3"), Decimal("2"), Decimal("3"))
        perfiles_historicos = (
            ("FAB-MAT-PLA", Decimal("0.0250")),
            ("FAB-MAT-PLA-AZU", Decimal("0.0300")),
            ("FAB-MAT-PLA-GRI", Decimal("0.0290")),
            ("FAB-MAT-PLA-NEG", Decimal("0.0310")),
            ("FAB-MAT-PLA-ROJ", Decimal("0.0320")),
            ("FAB-MAT-RESINA", Decimal("0.0600")),
            ("FAB-CON-CINTA", Decimal("1.5000")),
            ("FAB-MAT-MDF3", Decimal("3.8000")),
            ("FAB-MAT-ACR3", Decimal("6.5000")),
        )
        for perfil_indice, (codigo_insumo, costo_hist) in enumerate(perfiles_historicos):
            insumo_hist = consumibles.get(codigo_insumo)
            if insumo_hist is None:
                continue
            contenido = Decimal(insumo_hist.cantidad_por_presentacion or 1)
            codigo_corto = codigo_insumo.replace("FAB-", "")
            for indice, dias_atras in enumerate((155, 125, 95, 65, 35, 12), start=1):
                fecha_hist = hoy - timedelta(days=dias_atras)
                cantidad_entrada = contenido * factores_ingreso[indice - 1]
                cantidad_salida = contenido * factores_salida[indice - 1]
                ingreso_grafica, _ = self._movimiento(
                    unidad,
                    usuario,
                    f"HIST-GRAF-{codigo_corto}-{indice:02d}-IN",
                    consumible=insumo_hist,
                    tipo="ingreso",
                    motivo="recepcion",
                    cantidad=cantidad_entrada,
                    costo_unitario=costo_hist,
                    responsable_costo="institucional",
                    fecha=self._fecha_hora(fecha_hist, time(8, 0)),
                    nota="Ingreso histórico importado para evaluar demanda y abastecimiento.",
                )
                motivo_salida = (
                    "desperdicio_calidad"
                    if (perfil_indice + indice) % 5 == 0
                    else ("consumo_practica" if indice % 2 else "consumo_produccion")
                )
                salida_grafica, _ = self._movimiento(
                    unidad,
                    usuario,
                    f"HIST-GRAF-{codigo_corto}-{indice:02d}-OUT",
                    consumible=insumo_hist,
                    tipo="salida",
                    motivo=motivo_salida,
                    cantidad=cantidad_salida,
                    costo_unitario=costo_hist,
                    responsable_costo=(
                        "laboratorio" if motivo_salida == "desperdicio_calidad"
                        else "institucional"
                    ),
                    fecha=self._fecha_hora(fecha_hist + timedelta(days=4), time(15, 0)),
                    nota=(
                        "Merma histórica por calidad registrada para evaluar pérdidas."
                        if motivo_salida == "desperdicio_calidad"
                        else "Consumo histórico importado para evaluar tendencias y clasificación ABC."
                    ),
                )
                for movimiento_grafica in (ingreso_grafica, salida_grafica):
                    self._registrar_auditoria(
                        unidad,
                        usuario,
                        movimiento_grafica,
                        "Movimiento para gráfica demostrativa creado",
                    )

        plan_mantenimiento, _ = PlanMantenimientoEquipo.objects.update_or_create(
            equipo=scanner,
            nombre="[EVAL] Calibración trimestral del escáner",
            defaults={
                "tipo": "calibracion",
                "frecuencia_dias": 90,
                "fecha_inicio": hoy - timedelta(days=180),
                "proxima_ejecucion": hoy - timedelta(days=5),
                "anticipacion_dias": 15,
                "responsable": responsable.usuario if responsable and responsable.usuario_id else usuario,
                "instrucciones": "Verificar marcadores, distancia, iluminación y desviación dimensional.",
                "activo": True,
            },
        )
        mantenimiento_activo = MantenimientoEquipo.objects.filter(
            equipo=laser,
            titulo="[EVAL EN CURSO] Limpieza de óptica y extracción",
        ).first()
        if mantenimiento_activo is None:
            mantenimiento_activo = MantenimientoEquipo.objects.create(
                equipo=laser,
                unidad=unidad,
                tipo="preventivo",
                estado="en_proceso",
                titulo="[EVAL EN CURSO] Limpieza de óptica y extracción",
                descripcion="Limpieza de lente, espejos, mesa y conductos de extracción.",
                fecha_programada=timezone.now() - timedelta(hours=1),
                responsable=responsable.usuario if responsable and responsable.usuario_id else usuario,
                proveedor="Personal técnico interno",
            )
        mantenimiento_completo = MantenimientoEquipo.objects.filter(
            equipo=cnc,
            titulo="[EVAL IDEAL] Mantenimiento preventivo CNC completado",
        ).first()
        if mantenimiento_completo is None:
            mantenimiento_completo = MantenimientoEquipo.objects.create(
                equipo=cnc,
                unidad=unidad,
                tipo="preventivo",
                estado="completado",
                titulo="[EVAL IDEAL] Mantenimiento preventivo CNC completado",
                descripcion="Limpieza, lubricación y verificación de herramienta.",
                fecha_programada=timezone.now() - timedelta(days=10, hours=1),
                fecha_inicio=timezone.now() - timedelta(days=10),
                fecha_fin=timezone.now() - timedelta(days=10) + timedelta(hours=2),
                responsable=responsable.usuario if responsable and responsable.usuario_id else usuario,
                proveedor="Personal técnico interno",
                costo=Decimal("35.00"),
                resultado="Equipo probado, sin holguras y disponible para operación.",
                proximo_mantenimiento=hoy + timedelta(days=170),
            )
        for objeto, descripcion in (
            (plan_mantenimiento, "Plan vencido de evaluación creado"),
            (mantenimiento_activo, "Mantenimiento en curso de evaluación creado"),
            (mantenimiento_completo, "Mantenimiento completado de evaluación creado"),
        ):
            self._registrar_auditoria(unidad, usuario, objeto, descripcion)

        ingreso_financiero, _ = MovimientoFinancieroUnidad.objects.get_or_create(
            unidad=unidad,
            referencia="EVAL-DEP-SERV-001",
            defaults={
                "tipo": "ingreso",
                "categoria": "servicio",
                "fuente_fondos": "autogestion",
                "estado": "confirmado",
                "fecha_movimiento": hoy - timedelta(days=1),
                "monto": Decimal("29.00"),
                "metodo": "transferencia",
                "descripcion": "Cobro confirmado del servicio FDM de evaluación.",
                "reserva": reservas["ideal"],
                "observaciones": "Ingreso de evaluación registrado; no representa disponibilidad presupuestaria certificada.",
                "creado_por": usuario,
                "actualizado_por": usuario,
            },
        )
        recepcion_lote = EntradaInventario.objects.get(
            lote_inventario=lote_bodega,
            motivo="recepcion",
        )
        egreso_financiero, _ = MovimientoFinancieroUnidad.objects.get_or_create(
            unidad=unidad,
            referencia="EVAL-OC-PLA-001",
            defaults={
                "tipo": "egreso",
                "categoria": "reposicion_insumos",
                "fuente_fondos": "presupuesto_institucional",
                "estado": "pendiente",
                "fecha_movimiento": hoy - timedelta(days=4),
                "monto": Decimal("25.00"),
                "metodo": "asignacion",
                "descripcion": "Compra institucional de una bobina PLA de evaluación.",
                "movimiento_inventario": recepcion_lote,
                "observaciones": "Ejemplo pendiente de revisión administrativa y comprobante; separado de los fondos autogenerados.",
                "creado_por": usuario,
                "actualizado_por": usuario,
            },
        )
        pendiente_financiero, _ = MovimientoFinancieroUnidad.objects.get_or_create(
            unidad=unidad,
            referencia="EVAL-COT-PEND-001",
            defaults={
                "tipo": "ingreso",
                "categoria": "servicio",
                "fuente_fondos": "autogestion",
                "estado": "pendiente",
                "fecha_movimiento": hoy,
                "monto": Decimal("41.00"),
                "metodo": "no_aplica",
                "descripcion": "Cotización pendiente: todavía no constituye un ingreso efectivo.",
                "reserva": reservas["pendiente"],
                "creado_por": usuario,
                "actualizado_por": usuario,
            },
        )
        for objeto in (ingreso_financiero, egreso_financiero, pendiente_financiero):
            self._registrar_auditoria(
                unidad, usuario, objeto, "Movimiento financiero de evaluación creado"
            )

        actividad, _ = CatalogoActividadReserva.objects.update_or_create(
            unidad=unidad,
            codigo="EVAL-PRACTICA-FDM",
            defaults={
                "proposito_codigo": "docencia_practica",
                "subtipo_actividad": "practica_curricular",
                "nombre": "Práctica evaluativa de diseño e impresión 3D",
                "responsable": solicitante.get_full_name() or solicitante.get_username(),
                "descripcion": "Actividad completa usada para validar guía, planificación y ejecución.",
                "creado_por": usuario,
                "estado_publicacion": "publicado",
                "visibilidad": "unidad",
                "activo": True,
            },
        )
        guia = GuiaActividadReserva.objects.filter(
            actividad=actividad,
            codigo_guia="GUIA-EVAL-FDM-001",
        ).first()
        if guia is None:
            version = (actividad.guias.aggregate(maximo=Max("numero_version"))["maximo"] or 0) + 1
            actividad.guias.filter(es_estructurada=True, es_vigente=True).update(es_vigente=False)
            guia = GuiaActividadReserva.objects.create(
                actividad=actividad,
                titulo="Guía de práctica: preparación e impresión FDM",
                descripcion="Ejemplo institucional completamente diligenciado.",
                codigo_guia="GUIA-EVAL-FDM-001",
                numero_version=version,
                es_estructurada=True,
                es_vigente=True,
                contenido={
                    "asignatura": "Diseño y fabricación digital",
                    "carrera_semestre": "Computación · Sexto semestre",
                    "docente_responsable": solicitante.get_full_name() or solicitante.get_username(),
                    "laboratorio": unidad.nombre,
                    "duracion": "2 horas",
                    "maximo_estudiantes": "12",
                    "categoria_uso": "Docencia",
                    "resultado_aprendizaje": "Prepara y fabrica un prototipo aplicando parámetros seguros.",
                    "objetivos": "Configurar el laminado, verificar la máquina y documentar el resultado.",
                    "fundamento_teorico": "Fabricación aditiva FDM, orientación, soportes y adhesión entre capas.",
                    "equipos": "Impresora 3D FDM y estación CAD/CAM.",
                    "materiales": "Filamento PLA 1,75 mm, espátula y elementos de limpieza.",
                    "reactivos": "No aplica.",
                    "medidas_seguridad": "Inducción previa; no tocar boquilla ni cama caliente; usar herramientas autorizadas.",
                    "procedimiento": [
                        "Validar el archivo STL y sus dimensiones.",
                        "Laminar y registrar tiempo y gramos estimados.",
                        "Inspeccionar equipo, cargar el lote y ejecutar la fabricación.",
                        "Registrar consumo real, resultado e incidencias.",
                    ],
                    "resultados_esperados": "Pieza terminada y registro técnico trazable.",
                    "criterios_evaluacion": "Preparación 30 %, operación segura 30 %, pieza 25 %, registro 15 %.",
                    "manejo_residuos": "Separar soportes y piezas fallidas; registrar su peso como desperdicio.",
                    "bibliografia": "Manual del fabricante y procedimiento operativo del FabLab UPEC.",
                },
                visibilidad="unidad",
                estado_publicacion="publicada",
                permite_descarga=True,
                solicita_publicacion=True,
                activo=True,
                subido_por=usuario,
                revisado_por=usuario,
                revisado_en=timezone.now(),
                aprobado_por=usuario,
                aprobado_en=timezone.now(),
            )
        plan_ideal = PlanificacionPractica.objects.filter(
            unidad=unidad,
            tema="[EVAL IDEAL] Preparación e impresión segura de un prototipo",
        ).first()
        if plan_ideal is None:
            plan_ideal = PlanificacionPractica.objects.create(
                actividad=actividad,
                guia=guia,
                unidad=unidad,
                reserva=reservas["ideal"],
                fecha=reservas["ideal"].fecha,
                hora_inicio=reservas["ideal"].hora_inicio,
                hora_fin=reservas["ideal"].hora_fin,
                carrera="Computación",
                semestre="Sexto",
                asignatura="Diseño y fabricación digital",
                docente_tutor=solicitante.get_full_name() or solicitante.get_username(),
                tema="[EVAL IDEAL] Preparación e impresión segura de un prototipo",
                resultado_aprendizaje="Fabricar un prototipo y documentar parámetros y consumo.",
                estudiantes_planificados=4,
                categoria_uso="docencia",
                responsable_tecnico=responsable,
                observaciones="Planificación completa vinculada a guía, reserva y recursos.",
                estado="aprobada",
                revisado_por=usuario,
                revisado_en=timezone.now(),
                creado_por=usuario,
            )
        EjecucionPractica.objects.update_or_create(
            planificacion=plan_ideal,
            defaults={
                "fecha_ejecucion": reservas["ideal"].fecha,
                "hora_inicio_real": time(9, 2),
                "hora_fin_real": time(10, 48),
                "resultado": "ejecutada",
                "estudiantes_asistentes": 4,
                "recursos_utilizados": "Impresora FDM, Cura y 120 g de PLA.",
                "detalle_operativo": {
                    "equipo": fdm.codigo_unidad,
                    "lote": lote_uso.codigo,
                    "consumo": "120 g",
                    "desperdicio": "0 g en esta atención",
                },
                "tuvo_incidente": False,
                "observaciones_docente": "Resultado obtenido dentro del tiempo previsto.",
                "cumplimiento_resultado": "si",
                "responsable_tecnico": responsable,
                "estado": "validada",
                "creado_por": usuario,
                "validado_por": usuario,
                "validado_en": timezone.now(),
            },
        )

        resumen = {
            "reservas_evaluacion": Reserva.objects.filter(
                laboratorio=unidad, titulo_solicitud__startswith=self.PREFIX
            ).count(),
            "lotes_evaluacion": LoteConsumible.objects.filter(
                consumible__unidad=unidad, codigo__startswith="EVAL-"
            ).count(),
            "incidencias_abiertas": IncidenciaEquipo.objects.filter(
                unidad=unidad
            ).exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).count(),
            "mantenimientos_evaluacion": MantenimientoEquipo.objects.filter(
                unidad=unidad, titulo__startswith="[EVAL"
            ).count(),
            "movimientos_financieros": MovimientoFinancieroUnidad.objects.filter(
                unidad=unidad, referencia__startswith="EVAL-"
            ).count(),
            "practicas_evaluacion": PlanificacionPractica.objects.filter(
                unidad=unidad, tema__startswith="[EVAL"
            ).count(),
        }
        self.finalizar_simulacion_datos_demo(options)
        prefijo = self.prefijo_simulacion_datos_demo(options)
        self.stdout.write(self.style.SUCCESS(
            f'{prefijo}Escenarios de evaluación listos en "{unidad.nombre}": {resumen}'
        ))
