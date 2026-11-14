"""Derivación explicable del control, sin aprobar archivos ni cambiar resultados.

La unidad corrige faltantes objetivos. Dirección recibe las decisiones que no
puede tomar una regla, las anomalías y los resultados inferiores al mínimo.
"""
from decimal import Decimal, InvalidOperation


# Sólo los faltantes conocidos se devuelven directamente a la unidad. Una
# regla nueva o desconocida conserva la revisión humana hasta clasificarla.
FALTANTES_UNIDAD = frozenset({
    'archivo_ausente', 'apartados_incompletos', 'documento_no_enviado',
    'estructura_invalida', 'cronograma_invalido', 'plan_sin_estructura_vigente',
    'capacidad_por_confirmar', 'actividad_incompleta', 'sin_metas', 'meta_invalida',
    'cronograma_fuera_periodo', 'presupuesto_invalido', 'compra_incompleta',
    'clasificacion_compra_invalida', 'importe_invalido', 'trimestre_invalido',
    'necesidad_critica_sin_respuesta', 'redaccion_sin_ancla', 'fuentes_sin_congelar',
    'uso_sin_programacion', 'uso_programacion_invalida', 'uso_sin_fundamento',
    'uso_supera_capacidad',
    'fuentes_modificadas', 'cierre_no_enviado', 'cierre_incompleto',
    'anexos_incompletos', 'medicion_incompleta', 'periodo_en_curso', 'firma_ausente',
    'RESPALDO_PRACTICA_INCOMPLETO', 'FT02_APROBACION_SIN_RESPONSABLE',
    'SESION_SIN_FT02', 'SESION_ATENDIDA_SIN_FT03', 'ANEXO_VACIO_CON_ACTIVIDAD',
    'INSUMO_SIN_DATOS', 'EXISTENCIA_SIN_LOTE', 'REACTIVO_SIN_FICHA',
    'FALTA_ACTA_INTEGRAL', 'ACTA_SOLO_ENLACE', 'EQUIPO_SIN_IDENTIFICACION',
    'MANTENIMIENTO_SIN_UNIVERSO', 'INFRA_SIN_COBERTURA',
    'INFRA_EJECUCION_PENDIENTE', 'ORDENES_SIN_RESPALDO',
    'EQUIPO_SIN_PRUEBA_FUNCIONAL', 'PRESTAMO_SIN_RECEPTOR',
    'PRESTAMO_SIN_PROPOSITO', 'PRESTAMO_SIN_CONDICION_SALIDA',
    'PRESTAMO_SIN_RESPONSABLE', 'PRESTAMO_EXTERNO_SIN_ACTA',
    'DEVOLUCION_INCOMPLETA', 'CONTROL_MENSUAL_FALTANTE', 'INDUCCION_INCOMPLETA',
    'PROTOCOLO_SIN_VALIDAR', 'DESECHO_INCOMPLETO', 'RESULTADOS_SIN_DECLARACION',
    'UNIVERSO_SIN_CONCILIAR',
})

# Estas reglas piden precisamente una decisión sobre el contenido del mismo
# archivo. Una revisión actual puede resolverlas; una regla desconocida, una
# alteración o un resultado bajo siguen en seguimiento hasta atender su causa.
CRITERIOS_RESOLUBLES_POR_REVISION = frozenset({
    'criterio_humano', 'criterios_no_automatizables', 'catalogo_personalizado',
    'procedencia_no_comprobada', 'correccion_por_revisar',
})


def excepcion_resuelta_por_revision(documento, control=None):
    """Lee la resolución atribuida del mismo archivo sin consultar ni recalificar."""
    from .expediente_interfaz import evaluacion_humana_vigente

    control = control if control is not None else getattr(documento, 'automatizacion', {}) or {}
    if not control.get('vigente') or getattr(documento, 'estado', '') != 'validado':
        return False
    resumen = control.get('resumen') or {}
    decision = resumen.get('decision_automatica') or {}
    if decision.get('version') != 1 or decision.get('destino') != 'direccion':
        return False
    if decision.get('indicadores_bajo_minimo'):
        return False
    motivos = decision.get('motivos') or []
    if not motivos or any(m.get('regla') not in CRITERIOS_RESOLUBLES_POR_REVISION for m in motivos):
        return False
    if any(h.get('severidad') in ('critico', 'crítico', 'bloqueo_critico', 'bloqueo')
           and h.get('regla') not in FALTANTES_UNIDAD for h in control.get('hallazgos', [])):
        return False
    if (resumen.get('procedencia') or {}).get('archivo_integro') is False:
        return False
    lectura = getattr(documento, 'resumen_interfaz', {}) or {}
    integridad = lectura.get('integridad', getattr(documento, 'integridad_documental', {})) or {}
    if integridad.get('aplica') and not integridad.get('correspondencia_verificada'):
        return False
    codigo = getattr(documento.exigido, 'codigo', '')
    if codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
        from .conformidad_lectura import lectura_conformidad
        conformidad = lectura_conformidad(documento, integridad=integridad, control=control)
        return bool(conformidad and conformidad.get('estado') == 'conforme'
                    and conformidad.get('fuente') == 'Dirección')
    from .conformidad_permanente import es_permanente
    if es_permanente(documento):
        aprobacion = lectura.get('aprobacion') or getattr(documento, 'aprobacion_permanente', {}) or {}
        return bool(aprobacion.get('vigente') and aprobacion.get('actor_id'))
    if codigo != 'INFORME-SEMESTRAL':
        return False
    minimo = _porcentaje(decision.get('minimo_cumplimiento'))
    nota = _porcentaje(lectura['nota'] if 'nota' in lectura else getattr(documento, 'nota', None))
    return bool(minimo is not None and nota is not None and nota >= minimo
                and getattr(documento, 'recurso_id', None)
                and integridad.get('correspondencia_verificada') and evaluacion_humana_vigente(documento))


def _porcentaje(valor):
    try:
        numero = Decimal(str(valor))
        return numero if numero.is_finite() and 0 <= numero <= 100 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def decidir_atencion(documento, *, estado, hallazgos, resumen, nota, minimo, aplicado):
    """Proyección pura y auditable; no transforma un resultado bajo en aprobado."""
    minimo = _porcentaje(minimo)
    motivos, faltantes = [], []
    for hallazgo in hallazgos:
        if hallazgo.get('severidad') == 'informacion':
            continue
        lectura = {k: hallazgo.get(k, '') for k in ('regla', 'mensaje')}
        (faltantes if lectura['regla'] in FALTANTES_UNIDAD else motivos).append(lectura)

    codigo = documento.exigido.codigo
    resultado = _porcentaje(nota)
    indicadores_bajos = []
    if codigo == 'INFORME-SEMESTRAL':
        if minimo is None:
            motivos.append(dict(regla='minimo_no_verificable',
                mensaje='No se pudo comprobar el mínimo institucional aplicable.'))
        else:
            if resultado is not None and resultado < minimo:
                motivos.append(dict(regla='resultado_bajo_minimo',
                    mensaje=f'El resultado acreditado es {resultado} %, inferior al mínimo de {minimo} %.'))
            for fila in resumen.get('indicadores_exigibles', []):
                valor = _porcentaje(fila.get('porcentaje'))
                if valor is not None and valor < minimo:
                    indicadores_bajos.append(dict(codigo=fila.get('codigo', ''),
                        porcentaje=str(valor), nombre=fila.get('nombre', '')))
            if indicadores_bajos:
                motivos.append(dict(regla='indicadores_bajo_minimo',
                    mensaje=f'{len(indicadores_bajos)} indicador(es) obligatorio(s) están por debajo de {minimo} %.'))

    # El plan puede ser conforme mientras la solicitud de fondos requiere un
    # sustento excepcional. No se detiene ni se recalifica la conformidad.
    inversion = (resumen.get('conformidad_documental') or {}).get('priorizacion_inversion') or {}
    if (codigo == 'PLAN-COMPRAS-ANUAL' and estado == 'automatico'
            and inversion.get('aplica') and inversion.get('requiere_revision')):
        motivos.append(dict(regla='sustento_inversion', mensaje=inversion.get('explicacion') or
            'La propuesta es conforme; su priorización necesita comprobar el sustento de inversión.'))

    destino = 'direccion' if motivos else 'unidad' if faltantes else 'automatico'
    if estado != 'automatico' and destino == 'automatico':
        destino = 'unidad' if documento.estado != 'validado' else 'direccion'
        motivos.append(dict(regla='control_sin_conclusion',
            mensaje='El control aún no permite acreditar una conformidad automática.'))
    return dict(version=1, destino=destino, requiere_director=destino == 'direccion',
        motivos=motivos if destino == 'direccion' else faltantes,
        faltantes_unidad=faltantes, indicadores_bajo_minimo=indicadores_bajos,
        minimo_cumplimiento=str(minimo) if minimo is not None else None,
        resultado_conservado=bool(aplicado), autorizacion_financiera=False)
