"""Catálogos y controles operativos del reporte privado de Centros I+D.

Los modelos auxiliares se resumen, sin convertir identidades, expedientes o
evidencias reservadas en archivos descargables. Ninguna consulta cruza bases.
"""
from django.db.models import Count, Q, Sum
from django.utils import timezone

from . import models

CATALOGOS = (
    ('hitos', 'Hitos de proyectos'), ('equipamiento', 'Equipamiento'),
    ('capacidades', 'Capacidades e infraestructura'), ('equipo', 'Equipo, grupos y líneas'),
    ('colaboracion', 'Aliados y articulación'), ('repositorio', 'Repositorio y contenidos'),
    ('planificacion', 'Gobierno y planificación'), ('indicadores', 'Indicadores configurados'),
    ('seguridad', 'Acceso, habilitaciones y seguimiento'),
    ('portafolio', 'Portafolio de servicios tecnológicos'),
)


def construir_catalogo(categoria, centros, filtros, exportar):
    # Importación diferida para mantener el proveedor principal y los catálogos
    # independientes al importar el módulo de autorización desde el hub.
    from .informes import _busqueda, _fecha, _pagina, _por_anio, _registrados

    anio, texto = filtros['anio'], filtros['q']
    periodo = str(anio) if anio else 'Todos los años registrados'
    metricas, notas = [], []

    def consulta(nombre, relacion='centro', contenido=False):
        return _registrados(getattr(models, nombre), centros, relacion=relacion, contenido=contenido)

    def metrica(clave, nombre, valor, unidad='registros', temporal='Situación actual, sin filtro de año'):
        metricas.append((clave, nombre, valor, unidad, temporal))

    def tabla(qs, campos, columnas, fila, orden):
        objetos, paginacion = _pagina(qs.only(*campos).order_by(*orden), filtros['pagina'], exportar)
        return columnas, [fila(o) for o in objetos], paginacion

    def estado(qs, campo='estado'):
        return qs.filter(**{campo: filtros['estado']}) if filtros['estado'] else qs

    if categoria == 'hitos':
        qs = consulta('HitoProyecto', 'proyecto__centro').filter(proyecto__es_muestra=False)
        qs = estado(_busqueda(_por_anio(qs, 'fecha_prevista', anio), texto, ('titulo', 'proyecto__titulo')))
        documentados = Q(estado='cumplido', fecha_cumplida__lte=timezone.localdate(), evidencia__regex=r'\S')
        cifras = qs.aggregate(total=Count('pk'), documentados=Count('pk', filter=documentados),
                              vencidos=Count('pk', filter=Q(estado='pendiente', fecha_prevista__lt=timezone.localdate())))
        for clave, nombre in [('total', 'Hitos planificados'), ('documentados', 'Cumplimientos documentados'), ('vencidos', 'Hitos pendientes vencidos')]:
            metrica(clave, nombre, cifras[clave], temporal=periodo)
        resultado = tabla(qs.select_related('proyecto__centro'),
            ('pk', 'proyecto__titulo', 'proyecto__centro__nombre', 'titulo', 'fecha_prevista', 'estado', 'fecha_cumplida', 'evidencia'),
            ['Centro', 'Proyecto', 'Hito', 'Fecha prevista', 'Estado', 'Cumplimiento documentado'],
            lambda h: [h.proyecto.centro.nombre, h.proyecto.titulo, h.titulo, _fecha(h.fecha_prevista),
                       str(h.get_estado_display()), 'Sí' if h.cumplimiento_documentado else 'No'], ('fecha_prevista', 'pk'))
        notas.append('Período por fecha prevista. El estado cumplido solo acredita cumplimiento con fecha no futura y evidencia; no se exporta la evidencia.')
    elif categoria == 'equipamiento':
        qs = estado(_busqueda(consulta('EquipoCentro', 'componente__centro', True), texto, ('nombre', 'codigo', 'categoria')))
        cifras = qs.aggregate(total=Count('pk'), unidades=Sum('cantidad'), operativos=Count('pk', filter=Q(estado='operativo')))
        metrica('equipos', 'Registros de equipamiento', cifras['total'])
        metrica('unidades', 'Unidades declaradas', cifras['unidades'] or 0, 'unidades')
        metrica('operativos', 'Registros en estado operativo', cifras['operativos'])
        resultado = tabla(qs.select_related('componente__centro'),
            ('pk', 'componente__centro__nombre', 'componente__nombre', 'codigo', 'nombre', 'categoria', 'cantidad', 'estado'),
            ['Centro', 'Área', 'Código', 'Equipo', 'Categoría', 'Cantidad declarada', 'Estado'],
            lambda e: [e.componente.centro.nombre, e.componente.nombre, e.codigo, e.nombre, e.categoria,
                       e.cantidad, str(e.get_estado_display())], ('componente__centro__nombre', 'nombre', 'pk'))
        notas.append('Inventario actual. Cantidades declaradas y estado operativo no acreditan calibración ni disponibilidad para reservar. Este catálogo no tiene fecha histórica y no se filtra por año.')
    elif categoria == 'capacidades':
        qs = estado(_busqueda(consulta('Componente'), texto, ('nombre', 'codigo')))
        metrica('areas', 'Divisiones y plataformas registradas', qs.count())
        metrica('zonas', 'Zonas no demostrativas', consulta('Zona', contenido=True).count())
        metrica('procesos', 'Procesos de áreas', consulta('ProcesoArea', 'componente__centro').count())
        metrica('pasos', 'Pasos de procesos', consulta('PasoProceso', 'proceso__componente__centro').count())
        metrica('relaciones', 'Flujos entre áreas', consulta('RelacionArea').count())
        metrica('herramientas', 'Herramientas registradas', consulta('HerramientaCentro').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'codigo', 'nombre', 'tipo', 'estado', 'nivel', 'area_m2'),
            ['Centro', 'Código', 'Área', 'Tipo', 'Estado', 'Nivel', 'Superficie declarada (m²)'],
            lambda c: [c.centro.nombre, c.codigo, c.nombre, str(c.get_tipo_display()), str(c.get_estado_display()),
                       c.nivel, c.area_m2 if c.area_m2 is not None else 'Sin registrar'], ('centro__nombre', 'nombre', 'pk'))
        notas.append('Capacidades actuales. Los conteos auxiliares abarcan el centro seleccionado, sin filtro de búsqueda ni año. Herramienta registrada no equivale a simulador validado.')
    elif categoria == 'equipo':
        qs = consulta('Integrante', contenido=True)
        metrica('personas', 'Integrantes no demostrativos', qs.count(), 'personas registradas')
        metrica('vigentes', 'Integrantes vigentes', qs.filter(vigente=True).count(), 'personas registradas')
        metrica('grupos', 'Grupos activos no demostrativos', consulta('Grupo', contenido=True).filter(activo=True).count())
        metrica('lineas', 'Líneas de investigación', consulta('LineaInvestigacion').count())
        agrupado = qs.values('centro_id', 'centro__nombre', 'rol', 'vigente').annotate(total=Count('pk')).order_by('centro__nombre', 'centro_id', 'rol', 'vigente')
        objetos, paginacion = _pagina(agrupado, filtros['pagina'], exportar)
        resultado = (['Centro', 'ID del centro', 'Rol', 'Vigencia', 'Personas registradas'],
            [[o['centro__nombre'], o['centro_id'], str(dict(models.Integrante.ROLES).get(o['rol'], o['rol'])),
              'Vigente' if o['vigente'] else 'No vigente', o['total']] for o in objetos], paginacion)
        notas.append('Agrupación por rol y vigencia, sin nombres, correos, perfiles ni ORCID. No existe fecha de alta/baja histórica; año y búsqueda de contenido no alteran esta fotografía actual.')
    elif categoria == 'colaboracion':
        qs = _busqueda(consulta('Aliado', contenido=True), texto, ('nombre', 'pais', 'tipo'))
        metrica('aliados', 'Aliados no demostrativos', qs.count())
        metrica('activos', 'Aliados marcados activos', qs.filter(activo=True).count())
        metrica('articulaciones', 'Articulaciones registradas', consulta('Articulacion').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'nombre', 'tipo', 'pais', 'activo', 'vigencia_hasta'),
            ['Centro', 'Entidad aliada', 'Tipo', 'País', 'Activo registrado', 'Vigencia hasta'],
            lambda a: [a.centro.nombre, a.nombre, a.tipo, a.pais, 'Sí' if a.activo else 'No', _fecha(a.vigencia_hasta)],
            ('centro__nombre', 'nombre', 'pk'))
        notas.append('Situación actual sin atribución anual. Marcado activo no acredita un convenio vigente. Articulaciones se cuentan para todo el centro, sin filtro de búsqueda.')
    elif categoria == 'repositorio':
        qs = estado(_busqueda(_por_anio(consulta('DocumentoCentro', contenido=True), 'fecha', anio), texto, ('titulo', 'tipo')), 'estado_documental')
        metrica('documentos', 'Documentos no demostrativos', qs.count(), temporal=periodo)
        metrica('carpetas', 'Carpetas activas', consulta('CarpetaCentro').filter(activa=True).count())
        metrica('recursos', 'Recursos activos en carpetas', consulta('RecursoCentro', 'carpeta__centro').filter(activo=True).count())
        metrica('imagenes', 'Imágenes registradas', consulta('ImagenCentro').count())
        metrica('planos', 'Planos registrados', consulta('PlanoCentro').count())
        metrica('secciones', 'Secciones personalizadas', consulta('AjusteSeccion').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'titulo', 'tipo', 'fecha', 'version', 'estado_documental', 'publico'),
            ['Centro', 'Documento', 'Tipo', 'Fecha', 'Versión', 'Estado documental', 'Divulgación'],
            lambda d: [d.centro.nombre, d.titulo, d.tipo, _fecha(d.fecha), d.version,
                       str(d.get_estado_documental_display()), 'Público' if d.publico else 'Interno'], ('centro__nombre', 'titulo', 'pk'))
        notas.append('Documentos por su fecha registrada; los demás contenidos son existencias actuales sin filtro de año/búsqueda. No se exportan archivos, enlaces de descarga ni contenido de documentos internos.')
    elif categoria == 'planificacion':
        qs = estado(_busqueda(consulta('Fase'), texto, ('nombre', 'horizonte')))
        metrica('fases', 'Fases de implementación', qs.count())
        metrica('gobierno', 'Instancias de gobierno', consulta('OrganoGobierno').count())
        metrica('ruta', 'Etapas de atención', consulta('EtapaOperativa').count())
        metrica('modalidades', 'Modalidades', consulta('Modalidad').count())
        presupuesto = consulta('PartidaPresupuesto').aggregate(total=Count('pk'), monto_total=Sum('monto'),
            sin_monto=Count('pk', filter=Q(monto__isnull=True)))
        metrica('partidas', 'Partidas presupuestarias referenciales', presupuesto['total'])
        metrica('monto', 'Suma de montos referenciales registrados', presupuesto['monto_total'] or 0, 'USD')
        metrica('sin_monto', 'Partidas sin monto registrado', presupuesto['sin_monto'])
        metrica('riesgos', 'Riesgos registrados', consulta('Riesgo').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'numero', 'nombre', 'horizonte', 'estado'),
            ['Centro', 'Fase', 'Nombre', 'Horizonte registrado', 'Estado'],
            lambda f: [f.centro.nombre, f.numero, f.nombre, f.horizonte, str(f.get_estado_display())], ('centro__nombre', 'numero', 'pk'))
        notas.append('Planificación actual sin filtro anual. Los montos son referenciales; no representan ejecución, ingresos, saldos ni presupuesto aprobado. Conteos auxiliares sin filtro de búsqueda.')
    elif categoria == 'indicadores':
        qs = _busqueda(consulta('Indicador'), texto, ('nombre', 'categoria'))
        metrica('configurados', 'Indicadores configurados', qs.count())
        metrica('manuales', 'Indicadores manuales con valor', qs.filter(calculo='', valor__isnull=False).count())
        metrica('automaticos', 'Indicadores con cálculo configurado', qs.exclude(calculo='').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'categoria', 'nombre', 'calculo', 'valor', 'meta', 'actualizado'),
            ['Centro', 'Categoría', 'Indicador', 'Fuente del valor', 'Valor manual registrado', 'Meta registrada', 'Actualizado'],
            lambda i: [i.centro.nombre, i.categoria, i.nombre, 'Calculado en la ficha' if i.calculo else 'Registro manual',
                       'Ver ficha del centro' if i.calculo else (i.valor if i.valor is not None else 'Sin medir'),
                       i.meta if i.meta is not None else 'Sin meta', _fecha(i.actualizado)], ('centro__nombre', 'orden', 'pk'))
        notas.append('Configuración actual sin filtro anual: los valores automáticos se calculan en la ficha del centro, no se sustituye su cálculo por un valor manual almacenado. Los logros científicos medidos están en las demás categorías.')
    elif categoria == 'portafolio':
        qs = _busqueda(consulta('Servicio'), texto, ('nombre', 'linea', 'descripcion'))
        metrica('servicios', 'Servicios registrados', qs.count())
        metrica('activos', 'Servicios activos', qs.filter(activo=True).count())
        metrica('disponibles', 'Activos que reciben solicitudes', qs.filter(activo=True, estado_oferta='disponible').count())
        resultado = tabla(qs.select_related('centro'), ('pk', 'centro__nombre', 'nombre', 'linea', 'modalidad', 'estado_oferta', 'activo'),
            ['Centro', 'Servicio', 'Línea de servicio', 'Modalidad', 'Estado de oferta', 'En portafolio'],
            lambda s: [s.centro.nombre, s.nombre, s.linea, str(s.get_modalidad_display()),
                       str(s.get_estado_oferta_display()), 'Sí' if s.activo else 'No'], ('centro__nombre', 'nombre', 'pk'))
        notas.append('Portafolio actual sin filtro anual; no acredita servicios ejecutados, facturación ni una tarifa aprobada. La atención efectiva se registra en solicitudes y su seguimiento.')
    else:
        qs = consulta('SolicitudCentro')
        qs = _busqueda(_por_anio(qs, 'creada', anio), texto, ('titulo',))
        asignaciones = consulta('GestorCentro')
        metrica('asignaciones', 'Asignaciones locales de gestores', asignaciones.count())
        metrica('horarios', 'Reglas de horario', consulta('HorarioRecurso').count())
        metrica('bloqueos', 'Bloqueos de recursos en el período', _por_anio(consulta('BloqueoRecurso'), 'inicio', anio).count(), temporal=periodo)
        habilitaciones = consulta('HabilitacionEquipo', 'equipo__componente__centro')
        metrica('habilitaciones', 'Habilitaciones no revocadas vigentes', habilitaciones.filter(
            revocada=False, desde__lte=timezone.localdate(), hasta__gte=timezone.localdate()).count())
        historial = consulta('RegistroSolicitud', 'solicitud__centro')
        metrica('historial', 'Registros de trazabilidad en el período', _por_anio(historial, 'fecha', anio).count(), temporal=periodo)
        tareas = consulta('TareaSolicitud', 'solicitud__centro')
        metrica('tareas', 'Tareas de atención', tareas.count())
        metrica('pendientes', 'Tareas pendientes', tareas.filter(completada=False).count())
        agrupado = qs.values('centro_id', 'centro__nombre', 'estado').annotate(total=Count('pk')).order_by('centro__nombre', 'centro_id', 'estado')
        objetos, paginacion = _pagina(agrupado, filtros['pagina'], exportar)
        resultado = (['Centro', 'ID del centro', 'Estado de la solicitud', 'Solicitudes recibidas'],
            [[o['centro__nombre'], o['centro_id'], str(dict(models.SolicitudCentro.ESTADOS).get(o['estado'], o['estado'])), o['total']] for o in objetos], paginacion)
        notas.append('Solicitudes por año de recepción; trazabilidad y bloqueos por fecha de registro/inicio. Tareas, habilitaciones, horarios y asignaciones son actuales, sin búsqueda de contenido. No se exportan identidades, motivos, evidencias ni mensajes de trazabilidad.')
    columnas, filas, paginacion = resultado
    return metricas, columnas, filas, paginacion, notas
