"""Secciones y campos explícitos del panel propio de Centros I+D."""

PANELES = (
    ('resumen', 'Indicadores del centro', 'fas fa-chart-line'),
    ('solicitudes', 'Solicitudes y atención', 'fas fa-inbox'),
    ('agenda', 'Reservas y acompañamiento', 'fas fa-calendar-alt'),
    ('recursos', 'Equipos, espacios y horarios', 'fas fa-cubes'),
    ('investigacion', 'Investigación y transferencia', 'fas fa-flask'),
    ('servicios', 'Servicios y formación', 'fas fa-handshake'),
    ('equipo', 'Equipo y gobierno', 'fas fa-users'),
    ('contenidos', 'Contenidos y documentos', 'fas fa-folder-open'),
    ('configuracion', 'Configuración del centro', 'fas fa-cog'),
)

# clave: panel, modelo, título, ruta al centro, campos editables. Sin permisos,
# procedencia ni sellos de validación: no se alteran al editar una ficha.
REGISTROS = {
    'solicitudes': ('solicitudes', 'SolicitudCentro', 'Solicitudes', 'centro',
        'estado prioridad zona equipo participantes inicio_reservado fin_reservado requisitos_validados '
        'evidencia_requisitos supervisor responsable_atencion respuesta diagnostico plan entregable '
        'evaluacion_cierre notas_internas'),
    'sesiones': ('agenda', 'SesionAcompanamiento', 'Sesiones de acompañamiento', 'solicitud__centro',
        'solicitud responsable inicio fin modalidad estado acuerdos notas_internas'),
    'tareas': ('agenda', 'TareaSolicitud', 'Compromisos de atención', 'solicitud__centro',
        'solicitud titulo a_cargo plazo completada evidencia'),
    'equipos': ('recursos', 'EquipoCentro', 'Equipos', 'componente__centro',
        'componente categoria nombre detalle funcion especificaciones cantidad codigo estado es_activo_individual '
        'reservable requisitos requiere_induccion requiere_supervision calibracion_requerida calibracion_hasta '
        'calibracion_evidencia margen_minutos imagen orden'),
    'espacios': ('recursos', 'Zona', 'Espacios', 'centro',
        'codigo nombre nivel dimensiones area_m2 componente reservable estado_acceso aforo requisitos '
        'accesibilidad margen_minutos plano_x plano_y orden'),
    'horarios': ('recursos', 'HorarioRecurso', 'Horarios de recursos', 'centro', 'zona equipo dia abre cierra'),
    'bloqueos': ('recursos', 'BloqueoRecurso', 'Bloqueos de disponibilidad', 'centro', 'zona equipo inicio fin motivo'),
    'habilitaciones': ('recursos', 'HabilitacionEquipo', 'Habilitaciones de uso', 'equipo__componente__centro',
        'equipo usuario desde hasta evidencia revocada'),
    'herramientas': ('recursos', 'HerramientaCentro', 'Herramientas y simulaciones', 'centro',
        'nombre tipo objetivo entradas metodo salidas supuestos limites version enlace publicado'),
    'areas': ('recursos', 'Componente', 'Áreas y capacidades', 'centro',
        'tipo integrado_en codigo nombre nombre_corto resumen descripcion estado funciones capacidades resultados flujo '
        'equipamiento software organizacion_operativa insumos_materiales usos_academicos seguridad area_m2 nivel unidad_slug unidades_articuladas videos recorrido_360_url '
        'icono color publicado orden'),
    'lineas': ('investigacion', 'LineaInvestigacion', 'Líneas de investigación', 'centro',
        'nombre problema objetivos preguntas metodologia ambito responsable componente resultados retos orden'),
    'proyectos': ('investigacion', 'Proyecto', 'Proyectos', 'centro',
        'codigo titulo resumen linea categoria sector problema objetivos metodologia estado etapa avance '
        'avance_metodo avance_fecha avance_evidencia responsable equipo componentes aliados investigadores '
        'financiador monto monto_publico inicio fin hitos enlace imagen destacado publicado'),
    'hitos': ('investigacion', 'HitoProyecto', 'Hitos de proyectos', 'proyecto__centro',
        'proyecto titulo fecha_prevista estado fecha_cumplida evidencia publico'),
    'resultados': ('investigacion', 'Resultado', 'Resultados y desarrollos', 'centro',
        'tipo titulo descripcion anio revista cuartil proyecto componente autores autores_texto doi version '
        'enlace archivo acceso embargo_hasta confidencial licencia sector tecnologia usuarios_previstos '
        'colaboracion trl trl_fecha trl_evaluador trl_alcance trl_evidencia estado_pi pi_modalidad pi_titular '
        'pi_identificador pi_fecha pi_evidencia restricciones publicado'),
    'casos': ('investigacion', 'CasoExito', 'Casos de transferencia', 'centro',
        'titulo beneficiario sector reto contexto aporte_centro solucion resultado receptor mecanismo '
        'fecha_transferencia evidencia referencia unidad_medida periodo_medicion metodo_medicion limites '
        'autorizacion_publicacion desarrollo componente proyecto aliado anio imagen enlace publicado orden'),
    'aliados': ('investigacion', 'Aliado', 'Alianzas y colaboración', 'centro',
        'nombre tipo pais aporte convenio rol_colaboracion vigencia_desde vigencia_hasta actividades responsable '
        'enlace logo activo orden'),
    'servicios': ('servicios', 'Servicio', 'Servicios del portafolio', 'centro',
        'linea componente nombre descripcion entregable usuarios alcance exclusiones entradas requisitos metodo '
        'formato_entrega plazo aceptacion condiciones contacto modalidad estado_oferta tarifa_fuente tarifa_fecha '
        'tarifa_hasta tarifa activo orden'),
    'convocatorias': ('servicios', 'Convocatoria', 'Cursos y oportunidades', 'centro',
        'tipo titulo descripcion componente cierre enlace activa orden'),
    'modalidades': ('servicios', 'Modalidad', 'Modalidades de colaboración', 'centro',
        'nombre proposito usuarios icono orden'),
    'personas': ('equipo', 'Integrante', 'Personas del centro', 'centro',
        'nombre rol cargo componente grupo facultad perfil orcid scholar foto lineas vigente orden'),
    'grupos': ('equipo', 'Grupo', 'Grupos de investigación', 'centro',
        'nombre sigla descripcion facultad enlace lineas activo orden'),
    'gobierno': ('equipo', 'OrganoGobierno', 'Gobierno y responsabilidades', 'centro',
        'nombre rol responsabilidad funciones icono orden'),
    'novedades': ('contenidos', 'Novedad', 'Noticias y eventos', 'centro',
        'tipo titulo resumen fecha fecha_fin lugar enlace imagen publicada'),
    'documentos': ('contenidos', 'DocumentoCentro', 'Documentos', 'centro',
        'tipo titulo periodo resumen archivo enlace estado_documental emisor version publico fecha orden'),
    'carpetas': ('contenidos', 'CarpetaCentro', 'Carpetas de contenidos', 'centro',
        'pestana seccion nombre descripcion icono visibilidad orden activa'),
    'archivos': ('contenidos', 'RecursoCentro', 'Recursos de carpetas', 'carpeta__centro',
        'carpeta tipo titulo descripcion archivo url texto orden activo'),
    'secciones': ('contenidos', 'AjusteSeccion', 'Títulos y visibilidad', 'centro', 'clave titulo oculta'),
    'ruta': ('contenidos', 'EtapaOperativa', 'Ruta de atención', 'centro',
        'numero nombre proposito responsable resultado'),
    'imagenes': ('contenidos', 'ImagenCentro', 'Imágenes del centro', 'centro',
        'componente imagen titulo credito fuente es_plano orden'),
}

CAMPOS_CENTRO = ('nombre sigla area estado lema proposito presentacion adscripcion mision vision sectores_retos '
    'fuente_identidad fuente_estado objetivo_general objetivos_especificos cadena cifras ubicacion direccion '
    'latitud longitud como_llegar horario_atencion contacto_email imagen credito_imagen videos '
    'recorrido_360_url visitas_texto fuente').split()


def url_edicion(centro, nombre='centroid', pk=None, **extras):
    from urllib.parse import urlencode
    from django.urls import reverse

    tipo = next((k for k, s in REGISTROS.items() if s[1].lower() == nombre.lower()), '')
    parametros = {'panel': REGISTROS[tipo][0], 'tipo': tipo} if tipo else {'panel': 'configuracion'}
    if pk is not None:
        parametros['editar'] = pk
    parametros.update(extras)
    return reverse('gestion_centro_id', args=[centro.slug]) + '?' + urlencode(parametros)
