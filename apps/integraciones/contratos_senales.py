"""Revision manual v1 de efectos heredados; no importa Django ni registra señales.

Responsable de revision es el destino del contrato, no una transferencia de
tablas o autoridad. El propietario de ejecución corresponde al módulo actual.
"""
from dataclasses import dataclass
import re
from types import MappingProxyType
from .propiedad_modelos import PAQUETES_PROPIETARIOS, PROPIETARIOS_MODELOS


@dataclass(frozen=True, slots=True)
class ContratoSenal:
    funcion: str
    modulo: str
    senal: str
    sender: str
    modelo_sender: str
    responsable_revision: str
    lecturas: tuple[str, ...]
    escrituras: tuple[str, ...]
    condicion: str
    repeticion: str
    encadenamientos: tuple[str, ...] = ()
    fallo: str = 'propaga'
    propietario_actual: str = 'integraciones'
    atomicidad: str = 'sin_transaccion_completa_propia'
    alias: str = 'no_propaga_using_explicito'
    autoridad: str = 'en_llamador_no_concedida_por_signal'

    def __post_init__(self):
        if (not isinstance(self.funcion, str) or not re.fullmatch(r'[a-zA-Z_]\w*', self.funcion)
                or not isinstance(self.modulo, str) or not re.fullmatch(r'apps(?:\.[a-zA-Z_]\w*)+', self.modulo)
                or self.senal not in ('pre_save', 'post_save', 'post_delete', 'm2m_changed',
                                      'email_confirmed', 'user_logged_in')
                or self.responsable_revision not in ('core', 'directorio_unidades', 'plantas_piloto', 'integraciones')
                or self.fallo not in ('propaga', 'descarta_excepcion', 'registra_fallo_no_bloqueante')
                or self.propietario_actual not in set(PAQUETES_PROPIETARIOS) | {'integraciones'}
                or self.atomicidad not in ('sin_transaccion_completa_propia', 'savepoint_para_codigo')
                or self.alias not in ('no_propaga_using_explicito', 'propaga_using_en_lectura', 'propaga_using_servicio')
                or self.autoridad != 'en_llamador_no_concedida_por_signal'
                or not self.sender or not self.modelo_sender or not self.condicion or not self.repeticion
                or ((self.sender == '*' or self.modelo_sender == '*') and
                    (self.sender != '*' or self.modelo_sender != '*' or
                     self.senal not in ('email_confirmed', 'user_logged_in')))):
            raise ValueError('Contrato de señal invalido.')
        for valores in (self.lecturas, self.escrituras, self.encadenamientos):
            if type(valores) is not tuple or any(not isinstance(v, str) or not v for v in valores):
                raise ValueError('Los efectos del contrato deben ser tuplas de referencias.')

    @property
    def clave(self):
        return (self.modulo.replace('.', '/') + '.py', self.funcion, self.senal, self.sender)


def _contrato(funcion, sender, responsable, lecturas, escrituras, condicion, repeticion,
              *, modulo='apps.integraciones.senales_unidades', senal='post_save', modelo=None,
              encadenamientos=(), fallo='propaga', alias='no_propaga_using_explicito',
              atomicidad='sin_transaccion_completa_propia'):
    if funcion in {'create_user_profile', 'save_user_profile'}:
        modulo = 'apps.core.models.usuarios_base'
    propietario = next((label for label, paquete in sorted(PAQUETES_PROPIETARIOS.items(),
                        key=lambda item: len(item[1]), reverse=True) if modulo.startswith(paquete + '.')), 'integraciones')
    base = sender.split('.', 1)[0]
    modelo_actual = PROPIETARIOS_MODELOS.get(base, 'auth') + '.' + sender
    return ContratoSenal(funcion, modulo, senal, sender, modelo or modelo_actual,
                         responsable, lecturas, escrituras, condicion, repeticion,
                         encadenamientos, fallo, alias=alias, atomicidad=atomicidad,
                         propietario_actual=propietario)


CONTRATOS = (
    *(_contrato('revisar_uso_tras_actividad', 'Reserva', 'integraciones',
               ('Reserva.laboratorio_id', 'UnidadEquipo', 'PoliticaUsoEquipo', 'AlertaUsoEquipo'),
               ('AlertaUsoEquipo',),
               'omite raw y actualizacion exclusiva del codigo; agenda revision tras commit del alias recibido',
               'recalcula alertas vigentes por unidad; rollback descarta la tarea; no envia mensajes',
               modulo='apps.recursos.signals_uso', senal=senal, modelo='reservas.Reserva',
               fallo='registra_fallo_no_bloqueante')
      for senal in ('post_save', 'post_delete')),
    _contrato('crear_configuracion_operativa_unidad', 'Unidad', 'directorio_unidades',
              ('ConfiguracionOperativaUnidad',), ('ConfiguracionOperativaUnidad', 'HorarioOperacionUnidad'),
              'created=True; cinco jornadas ordinarias', 'repetir created=True duplica horarios'),
    _contrato('crear_perfil_especializado_unidad', 'Unidad', 'directorio_unidades',
              ('Unidad.clasificacion_funcional', 'PERFIL_POR_CLASIFICACION'), ('PerfilEspecializadoPorClasificacion',),
              'clasificacion reconocida', 'get_or_create; conserva perfiles anteriores'),
    _contrato('conservar_estado_anterior_equipo', 'UnidadEquipo', 'directorio_unidades',
              ('UnidadEquipo.estado_unidad', 'UnidadEquipo.laboratorio_id', 'UnidadEquipo.fecha_baja',
               'UnidadEquipo.codigo_unidad', 'UnidadEquipo.codigo_bien', 'UnidadEquipo.custodio',
               'UnidadEquipo.motivo_baja', 'UnidadEquipo.observacion_baja', 'UnidadEquipo.reemplazado_por_id'),
              ('instance._estado_ciclo_anterior',),
              'si tiene pk lee estado previo', 'reemplaza memoria; no escribe filas', senal='pre_save'),
    _contrato('registrar_ciclo_vida_equipo', 'UnidadEquipo', 'directorio_unidades',
              ('instance._estado_ciclo_anterior', 'Unidad.nombre', 'instance._usuario_ciclo_vida',
               'instance._evidencia_ciclo_vida', 'instance._justificacion_ciclo_vida', 'UnidadEquipo.reemplazado_por'),
              ('EventoCicloVidaEquipo', 'EventoCicloVidaEquipo.evidencia', 'AliasCodigoUnidadEquipo',
               'instance._archivo_ciclo_vida_creado'),
              'creacion, transferencia, cambio de estado, codigo, custodio, retiro o rectificacion documentada',
              'repetir evento puede duplicar trazabilidad; el alias usa get_or_create'),
    _contrato('registrar_cambio_de_area', 'EspacioReservable.equipos_asociados.through', 'directorio_unidades',
              ('EspacioReservable', 'UnidadEquipo'), ('EventoCicloVidaEquipo',),
              'post_add o post_remove con pk_set, directo o inverso; otras acciones retornan',
              'cada alta o baja de area agrega un evento', senal='m2m_changed',
              modelo='gestion_unidades.EspacioReservable.equipos_asociados.through'),
    _contrato('conservar_estado_del_prestamo', 'PrestamoEquipo', 'directorio_unidades',
              ('PrestamoEquipo.estado',), ('instance._estado_prestamo_anterior',),
              'si tiene pk lee el estado previo', 'reemplaza memoria; no escribe filas', senal='pre_save'),
    _contrato('registrar_prestamo_en_la_historia', 'PrestamoEquipo', 'directorio_unidades',
              ('instance._estado_prestamo_anterior', 'PrestamoEquipo'), ('EventoCicloVidaEquipo',),
              'el estado cambia a entregado o vuelve de entregado', 'un evento por cambio de estado'),
    _contrato('registrar_ficha_producto', 'Producto', 'plantas_piloto',
              ('Producto', 'ContentType', 'FichaContenido'), ('FichaContenido',),
              'unidad.dependencia=plantas_piloto', 'actualiza indice; respeta decision editorial vigente'),
    _contrato('registrar_ficha_proceso', 'Receta', 'plantas_piloto',
              ('Receta', 'ContentType', 'FichaContenido', 'ArtefactoExterno'),
              ('FichaContenido', 'FichaContenido.relacionadas', 'ArtefactoExterno'),
              'ficha solo plantas; invalida artefactos sincronizados al actualizar receta',
              'converge indice/relacion; invalida sin ejecutar artefacto'),
    _contrato('registrar_ficha_pcc', 'EtapaReceta', 'plantas_piloto',
              ('EtapaReceta', 'Receta', 'ContentType', 'FichaContenido', 'ArtefactoExterno'),
              ('FichaContenido', 'FichaContenido.relacionadas', 'ArtefactoExterno'),
              'PCC crea ficha de plantas; sin PCC archiva; actualizacion invalida artefactos',
              'converge indice/relacion/archivo; no ejecuta artefacto'),
    _contrato('registrar_ficha_especificacion', 'PlanCalidad', 'plantas_piloto',
              ('PlanCalidad', 'ContentType', 'FichaContenido'), ('FichaContenido',),
              'unidad.dependencia=plantas_piloto', 'actualiza indice conservando decision editorial'),
    _contrato('registrar_ficha_guia', 'GuiaActividadReserva', 'plantas_piloto',
              ('GuiaActividadReserva', 'CatalogoActividadReserva', 'ContentType', 'FichaContenido'), ('FichaContenido',),
              'unidad de actividad es planta; visibilidad depende de estado, visibilidad y activo',
              'actualiza indice conservando decision editorial'),
    _contrato('registrar_ficha_equipo', 'UnidadEquipo', 'plantas_piloto',
              ('UnidadEquipo', 'EquiposServicios', 'ContentType', 'FichaContenido', 'ArtefactoExterno'),
              ('FichaContenido', 'ArtefactoExterno'),
              'ficha solo plantas; actualizar equipo invalida artefactos sincronizados',
              'indice en revision inicial; no publica automaticamente'),
    _contrato('marcar_artefactos_por_equipo_base', 'EquiposServicios', 'integraciones',
              ('ArtefactoExterno', 'UnidadEquipo', 'EtapaReceta'), ('ArtefactoExterno',),
              'created=False; artefactos nivel 1/2 sincronizados', 'solo marca desactualizacion'),
    _contrato('insumo_compatible_registrado', 'ConsumiblePorEquipo', 'directorio_unidades',
              ('ConsumiblePorEquipo', 'Consumible', 'UnidadEquipo'),
              ('UnidadEquipo.requiere_insumos', 'UnidadEquipo.insumos_necesarios'),
              'activos de la ficha en la unidad del insumo', 'recalculo idempotente desde la relacion'),
    _contrato('insumo_compatible_retirado', 'ConsumiblePorEquipo', 'directorio_unidades',
              ('ConsumiblePorEquipo', 'Consumible', 'UnidadEquipo'),
              ('UnidadEquipo.requiere_insumos', 'UnidadEquipo.insumos_necesarios'),
              'activos de la ficha en la unidad del insumo', 'recalculo idempotente desde la relacion',
              senal='post_delete'),
    _contrato('validar_archivos_del_artefacto', 'ArtefactoExterno.archivos.through', 'integraciones',
              ('Recurso.unidad_id', 'ArtefactoExterno.unidad_id'), (),
              'pre_add directo o inverso con pk_set; otras acciones o vacio retornan', 'valida; no agrega archivos',
              senal='m2m_changed', modelo='gestion_unidades.ArtefactoExterno.archivos.through', alias='propaga_using_en_lectura'),
    _contrato('retirar_ficha_producto', 'Producto', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('retirar_ficha_proceso', 'Receta', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('retirar_ficha_pcc', 'EtapaReceta', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('retirar_ficha_especificacion', 'PlanCalidad', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('retirar_ficha_guia', 'GuiaActividadReserva', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('retirar_ficha_equipo', 'UnidadEquipo', 'plantas_piloto',
              ('ContentType', 'FichaContenido'), ('FichaContenido.codigo', 'FichaContenido.estado', 'FichaContenido.visibilidad'),
              'borrado del objeto con ficha editorial', 'archiva la ficha; repetir no la reactiva', senal='post_delete'),
    _contrato('create_user_profile', 'User', 'core', (), ('UserProfile',),
              'created=True', 'no repetir creacion: perfil OneToOne',
              modulo='apps.directorio_unidades.models.core', modelo='auth.User'),
    _contrato('save_user_profile', 'User', 'core', ('UserProfile',), ('UserProfile',),
              'guarda perfil existente o crea el faltante', 'actualiza derivado; no concede permisos',
              modulo='apps.directorio_unidades.models.core', modelo='auth.User'),
    _contrato('calcular_duracion_reserva', 'Reserva', 'directorio_unidades',
              ('instance.hora_inicio', 'instance.hora_fin', 'Reserva.calcular_duracion'), ('instance.duracion',),
              'ambas horas presentes', 'calculo en memoria; no guarda reserva',
              modulo='apps.reservas.models.reservas', senal='pre_save'),
    _contrato('asignar_codigo_reserva', 'Reserva', 'directorio_unidades',
              ('Reserva persistida bajo bloqueo', 'Reserva.construir_codigo_reserva'),
              ('Reserva.codigo_reserva', 'instance.codigo_reserva'),
              'codigo ausente y raw=False', 'conserva existente; update evita reentrada; fallo registra evento fijo',
              modulo='apps.reservas.models.reservas', fallo='registra_fallo_no_bloqueante',
              alias='propaga_using_servicio', atomicidad='savepoint_para_codigo'),
    _contrato('initialize_project_modules', 'Unidad', 'directorio_unidades',
              ('ModuloUnidad', 'DEFAULT_MODULES_BY_DEPENDENCIA'), ('ModuloUnidad',),
              'created=True y sin modulos', 'no completa una inicializacion parcial si ya hay modulos',
              modulo='apps.recursos.models.recursos'),
    _contrato('initialize_project_public_content', 'Unidad', 'directorio_unidades',
              ('Unidad.contacto_email', 'ReglamentoUnidad'), ('ReglamentoUnidad',),
              'created=True', 'get_or_create; conserva contenido existente', modulo='apps.recursos.models.recursos'),
    _contrato('configurar_usuario_decanato', 'Decanato', 'core',
              ('User', 'Group', 'Permission'), ('User.is_staff', 'Group', 'Group.permissions', 'User.groups'),
              'activa staff si falta; agrega grupo/permisos de SolicitudFabricacion',
              'adiciones convergentes; eliminar Decanato no revoca estas concesiones',
              modulo='apps.core.models.usuarios', encadenamientos=('create_user_profile', 'save_user_profile')),
    _contrato('habilitar_receptor', 'DependenciaAcademica.receptores.through', 'core',
              ('User', 'Group', 'Permission'), ('User.is_staff', 'Group', 'Group.permissions', 'User.groups'),
              'post_add con pk_set; otras acciones retornan',
              'adiciones convergentes; quitar el receptor no revoca estas concesiones',
              senal='m2m_changed', modulo='apps.directorio_unidades.models.core',
              modelo='directorio_unidades.DependenciaAcademica.receptores.through'),
    *tuple(_contrato(funcion, '*', 'directorio_unidades',
              ('EmailAddress.verified', 'User.is_active', 'UserProfile.cedula',
               'Curso.activo', 'Curso.origen', 'InvitacionCurso', 'EdicionCurso',
               'ParticipanteEvento', 'InscripcionCurso', 'PagoInscripcion'),
              ('InscripcionCurso', 'PagoInscripcion', 'InvitacionCurso.inscripcion'),
              'correo verificado y univoco; invitacion activa sin vinculo; curso nativo y activo; '
              'edicion activa, no finalizada y con cupo; identidad compatible; '
              'bloquea curso, edicion e invitacion en ese orden y revalida estado en transaccion por invitacion',
              'converge invitacion ya vinculada; conserva identidad de cuenta y de matricula; '
              'conflictos de identidad se omiten; los demas fallos se propagan',
              modulo='apps.formacion.presentation.matriculas_signals', senal=senal, modelo='*')
           for funcion, senal in (('vincular_correo_confirmado', 'email_confirmed'),
                                 ('vincular_al_ingresar', 'user_logged_in'))),
)


HUELLAS_REVISION = MappingProxyType({
    'apps/recursos/signals_uso.py': 'da63c6e5ae838d327b0ebcc229edc7bd89a06a75d3dfc0fb65e4614251e25f7c',
    'apps/core/models/usuarios_base.py': 'a3608622ba381996124c06c1c744913aa39b98c71bf31352fd0422eeccc10777',
    'apps/integraciones/senales_unidades.py': '41c7af5c8eab2ce488bc531e389b656751666022872309bfe3a3c64ec25bdf2c',
    'apps/formacion/presentation/matriculas_signals.py': '20151ed8988c962f8b50162b7fe56af3b99ba80f04b44362ca8da2befcd80b67',
    'apps/formacion/presentation/matriculas_cursos.py': 'b9f7b04091e65260000fac7468c1c36366fd84f2b673b26aed6cf06df46ffe45',
    'apps/directorio_unidades/models/core.py': '82cdd0c03fa7902b0b2b94760c96ea8ea3748a0acc886f95c245702e42f71c6c',
    'apps/reservas/models/reservas.py': '58f72a9dec58b971aa5b9481f86636be8f9c43f630e59938ca7fa6863d68963b',
    'apps/reservas/services/codigos_reserva.py': 'd4aa106653494d054b400235c19667e60b030ef4f63f1687aac5ffe96cdc65b2',
    'apps/recursos/models/recursos.py': 'f67b53cbff63af8312ce69382196f95bf9004048f16426c3aa7034545cbcc7fa',
    'apps/core/models/usuarios.py': 'd6b47498796dac94bf594e6e7f8e481eae5dc9489ee4cad6c9ea23b52dd7d9f3',
})


def registro_contratos(contratos=CONTRATOS):
    resultado = {}
    for contrato in contratos:
        if not isinstance(contrato, ContratoSenal) or contrato.clave in resultado:
            raise ValueError('Contrato ausente, invalido o duplicado.')
        resultado[contrato.clave] = contrato
    if not resultado:
        raise ValueError('El registro requiere contratos.')
    funciones = {c.funcion for c in resultado.values()}
    if any(set(c.encadenamientos) - funciones for c in resultado.values()):
        raise ValueError('Encadenamiento sin contrato de destino.')
    return MappingProxyType(resultado)
