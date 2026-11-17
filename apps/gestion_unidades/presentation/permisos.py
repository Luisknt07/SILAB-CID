"""Reglas de acceso para la operación interna de cada unidad.

Hay tres tipos de usuario y nada más:

* el superusuario, que administra toda la plataforma;
* el personal de una unidad, que la gestiona y solo a ella: su administrador
  principal, con todos los permisos, y las personas registradas como
  responsables con cuenta, cada una con la matriz de módulos que la unidad
  les asigne;
* el resto de usuarios, que solo ven y gestionan sus propias reservas.
"""
from apps.core.gobernanza import es_revisor_institucional

from django.db.models import Q

from apps.core.presentation.roles import roles_actuales
from apps.core.roles import MODULOS_OPERATIVOS, ROLES_OPERATIVOS, resolver_delegacion

from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


def _cuenta_activa(usuario):
    return bool(usuario and usuario.is_authenticated and usuario.is_active and usuario.pk is not None)


def permisos_operativos_unidad(usuario, unidad):
    """Devuelve la matriz efectiva de permisos para la unidad solicitada."""
    permisos = {modulo: False for modulo in MODULOS_OPERATIVOS}
    if not _cuenta_activa(usuario):
        return permisos
    if usuario.is_superuser or unidad.administrador_id == usuario.pk:
        return {modulo: True for modulo in MODULOS_OPERATIVOS}

    # La coordinación es administración local, no una delegación parcial.
    # Se calcula desde la asignación vigente: también cubre cuentas existentes.
    if ResponsableUnidad.objects.filter(
        unidad=unidad, usuario=usuario, activo=True, rol='coordinacion'
    ).exists():
        return dict.fromkeys(MODULOS_OPERATIVOS, True)

    responsabilidades = ResponsableUnidad.objects.filter(
        unidad=unidad,
        usuario=usuario,
        activo=True,
    )
    for responsable in responsabilidades:
        efectivos = resolver_delegacion(
            responsable.rol, responsable.recibe_reservas,
            responsable.permisos_operativos, roles_actuales(),
        )
        for modulo in MODULOS_OPERATIVOS:
            permisos[modulo] = permisos[modulo] or efectivos[modulo]
    return permisos


def permisos_operativos_responsable(responsable):
    """Previsualiza la delegacion para editarla; no autoriza una operacion.

    Conservar la matriz al desactivar permite revisar o reactivar sin perderla.
    La autorizacion efectiva usa permisos_operativos_unidad y exige cuenta activa.
    """
    if not responsable.usuario_id:
        return dict.fromkeys(MODULOS_OPERATIVOS, False)
    return resolver_delegacion(
        responsable.rol, responsable.recibe_reservas,
        responsable.permisos_operativos, roles_actuales(),
    )


def puede_operar_modulo_unidad(usuario, unidad, modulo):
    if modulo not in MODULOS_OPERATIVOS:
        return False
    return permisos_operativos_unidad(usuario, unidad)[modulo]


def puede_crear_guias_unidad(usuario, unidad):
    """Autoría nueva: docente verificado o delegación explícita en prácticas."""
    from apps.core.usuarios.pertenencia import es_docente_verificado

    return bool(
        _cuenta_activa(usuario)
        and (puede_operar_modulo_unidad(usuario, unidad, 'practicas')
             or es_docente_verificado(usuario))
    )


def unidades_gestionables(usuario):
    """Devuelve únicamente las unidades que el usuario puede administrar."""
    if not _cuenta_activa(usuario):
        return Unidad.objects.none()
    if usuario.is_superuser:
        return Unidad.objects.all()
    return Unidad.objects.filter(
        Q(administrador=usuario)
        | Q(
            responsables_unidad__usuario=usuario,
            responsables_unidad__activo=True,
            responsables_unidad__rol__in=ROLES_OPERATIVOS,
        )
    ).distinct()


def puede_gestionar_unidad(usuario, unidad):
    """Permite gestionar solo a personal institucional vinculado a la unidad."""
    if not _cuenta_activa(usuario):
        return False
    return unidades_gestionables(usuario).filter(pk=unidad.pk).exists()


def puede_administrar_personal_unidad(usuario, unidad):
    """La coordinación también puede asignar personal operativo de su unidad."""
    if not _cuenta_activa(usuario):
        return False
    return (usuario.is_superuser or unidad.administrador_id == usuario.pk
            or ResponsableUnidad.objects.filter(
                unidad=unidad, usuario=usuario, activo=True, rol='coordinacion').exists())


def _personal_editable_para_administracion(usuario, unidad, responsable):
    if responsable.unidad_id != unidad.pk:
        return False
    if usuario.is_superuser or unidad.administrador_id == usuario.pk:
        return True
    return (responsable.rol != 'coordinacion'
            and (not responsable.usuario_id or responsable.usuario_id not in (usuario.pk, unidad.administrador_id))
            and not (responsable.usuario_id and responsable.usuario.is_superuser))


def puede_editar_personal_unidad(usuario, unidad, responsable):
    return (puede_administrar_personal_unidad(usuario, unidad)
            and _personal_editable_para_administracion(usuario, unidad, responsable))


def permisos_edicion_personal_unidad(usuario, unidad, responsables):
    """Resuelve una autorización local y aplica la misma política a cada fila.

    El llamador debe cargar la cuenta relacionada para no consultar por fila.
    Una asignación de otra unidad nunca se vuelve editable por este cálculo.
    """
    autorizado = puede_administrar_personal_unidad(usuario, unidad)
    return {
        responsable.pk: autorizado and _personal_editable_para_administracion(
            usuario, unidad, responsable
        )
        for responsable in responsables
    }


def puede_operar_reservas_unidad(usuario, unidad):
    """Restringe las decisiones operativas a quienes atienden la agenda."""
    return puede_operar_modulo_unidad(usuario, unidad, "reservas")


def puede_corregir_reservas_cerradas_unidad(usuario, unidad):
    """Autoriza correcciones excepcionales sin perder la trazabilidad original."""
    return puede_operar_modulo_unidad(usuario, unidad, "corregir_cerradas")


def es_receptor_de(usuario, unidad):
    """Lectura del expediente adscrito a una dependencia activa."""
    if not _cuenta_activa(usuario):
        return False
    return usuario.is_superuser or bool(
        unidad.adscrita_a_id and unidad.adscrita_a.recibe_informe(usuario))


def puede_leer_expediente(usuario, unidad):
    return (es_revisor_institucional(usuario) or puede_operar_modulo_unidad(usuario, unidad, 'reportes')
            or es_receptor_de(usuario, unidad))


def unidades_del_expediente(usuario):
    """El mismo alcance para consola, reportes y administradores de modelos proxy."""
    if not _cuenta_activa(usuario):
        return Unidad.objects.none()
    if usuario.is_superuser or es_revisor_institucional(usuario):
        return Unidad.objects.all()
    operativas = [unidad.pk for unidad in unidades_gestionables(usuario)
                  if puede_operar_modulo_unidad(usuario, unidad, 'reportes')]
    return Unidad.objects.filter(
        Q(pk__in=operativas) | Q(adscrita_a__activa=True, adscrita_a__receptores=usuario)
    ).distinct()


def puede_cargar_guia_firmada(usuario, guia):
    """Una carga firmada corresponde a la autoría o al personal de prácticas."""
    return usuario.is_authenticated and usuario.is_active and (
        guia.actividad.creado_por_id == usuario.pk
        or puede_operar_modulo_unidad(usuario, guia.actividad.unidad, 'practicas')
    )
