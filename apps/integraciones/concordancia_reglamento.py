"""Diagnóstico de configuración entre Laboratorios y Centros sin alterar datos.

No es una certificación de conformidad normativa. Revisa las dos bases y
distingue capacidades propias y articuladas. Nunca determina adscripciones.
"""

from contextlib import ExitStack
from django.utils import timezone
from django.db import connections, transaction
from django.db.models import Count, Q, Exists, OuterRef
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExpediente
from django.contrib.auth import get_user_model


def diagnosticar():
    from apps.centros_id.models import CentroID, Componente, EquipoCentro, Proyecto, Resultado
    auditadas = set()
    with ExitStack() as stack:
        for alias in ("default", CentroID.objects.db):
            if alias in auditadas:
                continue
            stack.enter_context(transaction.atomic(using=alias))
            with connections[alias].cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
            auditadas.add(alias)
        active = Unidad.objects.filter(activo=True)
        components = Componente.objects.exclude(unidad_slug="")
        centers = CentroID.objects.filter(activo=True)
        rows = {
            "fecha": str(timezone.localdate()),
            "bases_separadas": CentroID.objects.db != "default",
            "unidades_activas": active.count(),
            "unidades_por_tipo": list(
                active.values("dependencia")
                .annotate(total=Count("pk"))
                .order_by("dependencia")
            ),
            "sin_adscripcion": active.filter(adscrita_a__isnull=True).count(),
            "adscripcion_sin_receptor": active.filter(adscrita_a__isnull=False)
            .filter(
                Q(adscrita_a__activa=False) | Q(adscrita_a__receptores__isnull=True)
            )
            .distinct()
            .count(),
            "sin_coordinacion_con_cuenta": active.annotate(
                coordinacion_activa=Exists(ResponsableUnidad.objects.filter(
                    unidad_id=OuterRef('pk'), activo=True, usuario__is_active=True, rol='coordinacion'))
            ).filter(coordinacion_activa=False).exclude(administrador__is_active=True).count(),
            "centros_activos": centers.count(),
            "centros_por_estado": list(
                centers.values("estado").annotate(total=Count("pk")).order_by("estado")
            ),
            "centros_sin_responsable": centers.filter(responsable__isnull=True).count(),
            "areas_con_laboratorio_propio": components.count(),
            "laboratorios_propios_repetidos": list(
                components.values("unidad_slug")
                .annotate(total=Count("pk"))
                .filter(total__gt=1)
                .order_by("unidad_slug")
            ),
            "areas_propio_y_compartido_a_la_vez": [
                {
                    "centro_id": c.centro_id,
                    "area_id": c.pk,
                    "laboratorio": c.unidad_slug,
                }
                for c in components
                if c.unidad_slug in c.lista_unidades
            ],
            "equipos_centros_individuales": EquipoCentro.objects.filter(
                es_activo_individual=True
            ).count(),
            "codigos_individuales_repetidos": list(
                EquipoCentro.objects.filter(es_activo_individual=True)
                .exclude(codigo="")
                .values("codigo")
                .annotate(total=Count("pk"))
                .filter(total__gt=1)
            ),
            "proyectos_centros": Proyecto.objects.count(),
            "resultados_centros": Resultado.objects.count(),
            "documentos_expediente": DocumentoExpediente.objects.count(),
            "cuentas_superusuario_activas": get_user_model()
            .objects.filter(is_active=True, is_superuser=True)
            .count(),
            "caso_xr": list(
                active.filter(
                    Q(nombre__icontains="extendida")
                    | Q(nombre__icontains="virtual")
                    | Q(nombre__icontains=" XR")
                    | Q(codigo__icontains="xr")
                ).values(
                    "id",
                    "nombre",
                    "clasificacion_funcional",
                    "adscrita_a__nombre",
                    "resolucion_numero",
                )
            ),
            "areas_xr": list(
                Componente.objects.filter(
                    Q(nombre__icontains="extendida")
                    | Q(nombre__icontains="virtual")
                    | Q(nombre__icontains=" XR")
                    | Q(codigo__icontains="xr")
                ).values(
                    "id", "centro_id", "nombre", "unidad_slug", "unidades_articuladas"
                )
            ),
        }
        missing = []
        slugs = set(active.values_list("slug", flat=True))
        for component in components:
            if component.unidad_slug not in slugs:
                missing.append(
                    {"area_id": component.pk, "laboratorio": component.unidad_slug}
                )
        rows["laboratorios_propios_no_resueltos"] = missing
        from apps.core.models.gobernanza import AsignacionGobernanza
        from apps.recursos.models.unidades import UnidadEquipo
        hoy = timezone.localdate()
        asignaciones = AsignacionGobernanza.objects.filter(activa=True, usuario__is_active=True,
            desde__lte=hoy).filter(Q(hasta__isnull=True) | Q(hasta__gte=hoy))
        rows['sin_designacion_institucional'] = not asignaciones.filter(rol='seguimiento', referencia='').exists()
        deps = set(str(x) for x in active.exclude(adscrita_a__isnull=True).values_list('adscrita_a_id', flat=True))
        validadas = set(asignaciones.filter(rol='adscripcion').values_list('referencia', flat=True))
        rows['adscripciones_sin_validador_designado'] = len(deps - validadas)
        designados = set(asignaciones.filter(rol='centro').values_list('referencia', 'usuario_id'))
        rows['centros_sin_designacion_concordante'] = sum(
            (c.slug, c.responsable_id) not in designados for c in centers)
        patrimonio = {}
        for ident, codigo in UnidadEquipo.objects.exclude(codigo_bien__isnull=True).exclude(codigo_bien='').values_list('pk', 'codigo_bien'):
            patrimonio.setdefault(codigo.strip().upper(), []).append(ident)
        coincidencias = []
        for equipo in EquipoCentro.objects.filter(es_activo_individual=True).exclude(codigo=''):
            if equipo.codigo.strip().upper() in patrimonio:
                coincidencias.append({'codigo': equipo.codigo.strip().upper(), 'equipo_centro': equipo.pk,
                    'equipos_directorio': patrimonio[equipo.codigo.strip().upper()]})
        rows['codigos_coincidentes_entre_inventarios'] = coincidencias
        rows['nota_codigos_coincidentes'] = 'Requieren cotejo patrimonial; no se fusionan automáticamente por una coincidencia de código.'
        rows['capacidades_compartidas_no_resueltas'] = [
            {'area_id': c.pk, 'laboratorio': slug} for c in Componente.objects.all()
            for slug in c.lista_unidades if slug not in slugs]
        return rows
