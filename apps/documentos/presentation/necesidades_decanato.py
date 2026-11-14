"""Lectura y transferencia de necesidades evaluadas a sus centros de costo.

La consulta no emite, aprueba ni modifica expedientes. Los renglones proceden
exclusivamente de la captura enviada que corresponde al archivo vigente.
"""
from copy import copy, deepcopy
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.html import strip_tags


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def _plano(valor):
    from html import unescape
    return ' '.join(unescape(strip_tags(_texto(valor))).split())


def _fecha(valor):
    return valor.isoformat() if valor else ''


def _numero(valor):
    try:
        # La redacción y su validador admiten coma decimal; la remisión debe
        # leer el mismo importe sin alterar el texto de la captura emitida.
        numero = Decimal(_texto(valor).replace(',', '.'))
        return numero if numero.is_finite() and abs(numero) <= Decimal('1e12') else None
    except (InvalidOperation, ValueError):
        return None


def _importe(fila):
    cantidad, costo = _numero(fila.get('cantidad')), _numero(fila.get('costo_unitario'))
    try:
        importe = cantidad * costo if cantidad is not None and cantidad > 0 and costo is not None and costo >= 0 else None
        return importe if importe is not None and importe.is_finite() else None
    except DecimalException:
        return None


def _captura_actual(documento):
    """Comprueba identidad completa sin volver a consultar inventario o redacción."""
    constancia = getattr(documento, '_constancia_qr', None)
    recurso = documento.recurso if documento.recurso_id else None
    if not (documento.estado == 'validado' and constancia and recurso
            and documento.verificacion_qr == constancia.token
            and constancia.documento_id == documento.pk
            and constancia.recurso_id == documento.recurso_id
            and constancia.version == documento.version == recurso.version
            and constancia.sha256 == recurso.hash_sha256 and len(constancia.sha256) == 64
            and recurso.unidad_id == documento.unidad_id and recurso.activo
            and recurso.estado == 'vigente' and constancia.enviado_en and not constancia.observado_en):
        return None
    datos = constancia.contenido_emitido
    contenido = datos.get('pac_datos') if isinstance(datos, dict) else None
    if not (isinstance(contenido, dict) and type(contenido.get('pac_version')) is int
            and contenido['pac_version'] in (1, 2) and isinstance(contenido.get('compras'), list)
            and all(isinstance(f, dict) for f in contenido['compras'])):
        return None
    if contenido['pac_version'] == 2:
        fuentes = contenido.get('diagnostico_compras_fuentes')
        if not (isinstance(fuentes, dict) and type(fuentes.get('version')) is int
                and fuentes['version'] == 1 and type(fuentes.get('unidad')) is int
                and fuentes['unidad'] == documento.unidad_id and type(fuentes.get('anio')) is int
                and fuentes['anio'] == documento.anio and isinstance(fuentes.get('areas'), list)):
            return None
    return deepcopy(contenido)


def _evaluacion(documento):
    from .aprobacion_en_linea import lectura_aprobacion_qr
    from .conformidad_lectura import lectura_conformidad
    qr = lectura_aprobacion_qr(documento)
    if qr:
        return bool(qr['aprobado']), _fecha(qr.get('fecha')), qr.get('actor', '')
    # Una validación de la unidad o una revisión automática no es Dirección.
    conformidad = lectura_conformidad(documento)
    if conformidad and conformidad['estado'] == 'conforme' and conformidad['fuente'] == 'Dirección':
        registro = getattr(documento, '_conformidad_plan_registro', None)
        actor = registro.usuario if registro and registro.usuario_id else None
        return True, _fecha(conformidad.get('fecha')), (actor.get_full_name() or actor.get_username()) if actor else ''
    return False, '', ''


def _necesidad(fila, numero, *, incluir_fases=False, incluir_detalle=False, incluir_resumen=False):
    from .pac_universitario import clases_bien_de, MESES_COMPRA, TIPOS_NECESIDAD, semestre_compra
    mes = _texto(fila.get('mes_compra'))
    importe = _importe(fila)
    if incluir_resumen and importe is not None:
        importe = importe.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    necesidad = dict(numero=numero, id=_texto(fila.get('id_necesidad')), area=_texto(fila.get('area_nombre')),
        motivo=dict(TIPOS_NECESIDAD).get(fila.get('tipo_necesidad'), 'Por confirmar'),
        clase=dict(clases_bien_de({'matriz_detalle_version': 1} if incluir_detalle else {})).get(fila.get('clase_bien'), 'Por confirmar'),
        item=_texto(fila.get('item')), cantidad=_texto(fila.get('cantidad')),
        costo_unitario=_texto(fila.get('costo_unitario')), total=str(importe) if importe is not None else None,
        mes=dict(MESES_COMPRA).get(mes, 'Por confirmar'), mes_numero=int(mes) if mes in dict(MESES_COMPRA) else None,
        semestre=semestre_compra(mes), justificacion=_plano(fila.get('justificacion')),
        equipos_actuales=_texto(fila.get('equipo_referencia')))
    if incluir_fases:
        necesidad.update({clave: _plano(fila.get(clave)) for clave in (
            'grupo_fases', 'fase_numero', 'resultado_fase', 'condicion_siguiente_fase')})
    if incluir_detalle:
        necesidad.update({clave: _plano(fila.get(clave)) for clave in (
            'especificaciones', 'unidad_medida', 'cpc', 'partida', 'fuente_pac', 'clasificacion_pac')})
        necesidad['clase_codigo'] = _texto(fila.get('clase_bien'))
    if incluir_resumen:
        necesidad['compras_resumen_version'] = 1
    return necesidad


def lectura_necesidades(anio, usuario, dependencia=None):
    """Año N de preparación; solicitudes para N+1, sólo al alcance receptor.

    Incluye toda unidad adscrita permitida, aunque no haya presentado una
    declaración. Esa ausencia nunca equivale a que no requiere compras.
    """
    from apps.documentos.models.expediente import DocumentoExpediente
    from apps.directorio_unidades.models.core import DependenciaAcademica
    from apps.gestion_unidades.presentation.permisos import unidades_del_expediente
    from .aprobacion_en_linea import completar_constancias
    from .conformidad_lectura import completar_conformidades
    from .perfil_unidades import es_unidad_auditable
    if not getattr(usuario, 'is_authenticated', False) or not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied('Debes ingresar con una cuenta institucional activa.')
    if isinstance(anio, bool) or not _texto(anio).isdecimal() or not 2000 <= int(anio) <= 9998:
        raise ValidationError('Selecciona el año de preparación de las necesidades.')
    anio = int(anio)
    dependencias = DependenciaAcademica.objects.all()
    if not usuario.is_superuser:
        dependencias = dependencias.filter(activa=True, receptores=usuario)
        if not dependencias.exists():
            raise PermissionDenied('La consulta corresponde a los receptores de la dependencia activa.')
    unidades = unidades_del_expediente(usuario)
    if not usuario.is_superuser:
        unidades = unidades.filter(adscrita_a__activa=True, adscrita_a__receptores=usuario)
    if dependencia is not None:
        identificador = getattr(dependencia, 'pk', dependencia)
        if isinstance(identificador, bool) or not _texto(identificador).isdecimal():
            raise ValidationError('Selecciona la dependencia receptora.')
        dependencias = dependencias.filter(pk=int(identificador))
        if not dependencias.exists():
            raise PermissionDenied('No tienes acceso a la dependencia seleccionada.')
        unidades = unidades.filter(adscrita_a_id=int(identificador))
    unidades = [u for u in unidades.select_related('adscrita_a').distinct().order_by('adscrita_a__nombre', 'nombre', 'pk')
        if es_unidad_auditable(u)]
    documentos = list(DocumentoExpediente.objects.filter(unidad_id__in=[u.pk for u in unidades], anio=anio,
        exigido__codigo='PLAN-COMPRAS-ANUAL', corte='', mes__isnull=True).select_related('exigido', 'recurso'))
    completar_constancias(documentos)
    completar_conformidades(documentos)
    por_unidad = {d.unidad_id: d for d in documentos}
    grupos = {dep.pk: dict(id=dep.pk, nombre=dep.nombre, centro_costo=_texto(getattr(dep, 'centro_costo', '')),
        unidades=[]) for dep in dependencias.order_by('nombre', 'pk')}
    filas = []
    for unidad in unidades:
        dep = unidad.adscrita_a
        grupo = grupos.setdefault(unidad.adscrita_a_id, dict(id=unidad.adscrita_a_id,
            nombre=dep.nombre if dep else 'Sin dependencia receptora asignada',
            centro_costo=_texto(getattr(dep, 'centro_costo', '')), unidades=[]))
        fila = dict(id=unidad.pk, nombre=unidad.nombre, dependencia_id=grupo['id'], dependencia_nombre=grupo['nombre'],
            documento_id=None, estado='sin_declaracion', estado_etiqueta='Sin declaración enviada',
            evaluado=False, transferible=False, declaracion='pendiente', sin_compras_justificacion='',
            centro_costo='', total=None, necesidades=[], pac_datos=None, fuente=None)
        documento = por_unidad.get(unidad.pk)
        if documento:
            fila['documento_id'] = documento.pk
            evaluado, fecha, actor = _evaluacion(documento)
            fila['evaluado'] = evaluado
            captura = _captura_actual(documento)
            if documento.estado == 'observado':
                fila.update(estado='corregir', estado_etiqueta='Devuelto para corregir')
            elif not evaluado:
                etiqueta = 'Pendiente de evaluación por Dirección' if documento.estado == 'validado' else 'Sin declaración enviada'
                fila.update(estado='pendiente_evaluacion' if documento.estado == 'validado' else 'sin_declaracion', estado_etiqueta=etiqueta)
            elif captura is None:
                fila.update(estado='sin_matriz', estado_etiqueta='Evaluado por Dirección · sin matriz estructurada', declaracion='sin_matriz')
            else:
                gestion_inversion = captura.get('inversion_gestion_version') == 1
                detalle_matriz = captura.get('matriz_detalle_version') == 1
                necesidades = [_necesidad(f, n, incluir_fases=gestion_inversion, incluir_detalle=detalle_matriz,
                               incluir_resumen=captura.get('compras_resumen_version') == 1)
                               for n, f in enumerate(captura['compras'], 1)]
                justificacion = _plano(captura.get('sin_compras_justificacion'))
                matriz_incompleta = any(not _plano(n['item']) or n['total'] is None for n in necesidades)
                if matriz_incompleta or not necesidades and not justificacion:
                    fila.update(estado='incompleto', estado_etiqueta='Declaración de necesidades incompleta', declaracion='incompleta')
                else:
                    constancia = documento._constancia_qr
                    fila.update(nombre=constancia.unidad_nombre, transferible=True,
                        estado='con_compras' if necesidades else 'sin_compras',
                        estado_etiqueta='Necesidades evaluadas por Dirección' if necesidades else 'Sin compras · evaluado por Dirección',
                        declaracion='compras' if necesidades else 'sin_compras',
                        sin_compras_justificacion=justificacion if not necesidades else '',
                        centro_costo=_texto(captura.get('centro_costo')), necesidades=necesidades, pac_datos=captura,
                        total=str(sum((Decimal(n['total']) for n in necesidades), Decimal('0'))) if all(n['total'] is not None for n in necesidades) else None,
                        fuente=dict(documento_id=documento.pk, recurso_id=documento.recurso_id,
                            token=str(constancia.token), version=constancia.version, sha256=constancia.sha256,
                            emitido_en=_fecha(constancia.emitido_en), enviado_en=_fecha(constancia.enviado_en),
                            fecha_evaluacion=fecha, actor=actor))
                    if detalle_matriz:
                        fila['matriz_detalle_version'] = 1
                    if captura.get('compras_resumen_version') == 1:
                        fila['compras_resumen_version'] = 1
                    if gestion_inversion:
                        from .priorizacion_necesidades import captura_gestion_inversion
                        fila.update(inversion_gestion_version=1,
                                    gestion_inversion=captura_gestion_inversion(documento, captura))
        grupo['unidades'].append(fila)
        filas.append(fila)
    transferibles = [u for u in filas if u['transferible']]
    importes = [u['total'] for u in transferibles]
    resumen = dict(unidades_total=len(filas), evaluadas=sum(u['evaluado'] for u in filas),
        con_compras=sum(u['estado'] == 'con_compras' for u in filas),
        sin_compras=sum(u['estado'] == 'sin_compras' for u in filas),
        pendientes=sum(not u['transferible'] for u in filas),
        necesidades_total=sum(len(u['necesidades']) for u in transferibles),
        total=str(sum((Decimal(v) for v in importes), Decimal('0'))) if all(v is not None for v in importes) else None)
    return dict(version=1, anio_preparacion=anio, anio_compras=anio + 1, grupos=list(grupos.values()),
        unidades=filas, resumen=resumen,
        alcance='Dirección evalúa las necesidades; la dependencia receptora gestiona las compras con su centro de costo.')


def _programacion_necesidad(necesidad):
    texto = necesidad['mes'] + (f"\nSemestre {necesidad['semestre']}" if necesidad['semestre'] else '')
    if necesidad.get('grupo_fases'):
        texto += '\n' + necesidad['grupo_fases'] + ' · fase ' + (necesidad.get('fase_numero') or 'Por completar')
    return texto


def _sustento_necesidad(necesidad):
    texto = necesidad['item'] + '\n' + necesidad['justificacion']
    if necesidad.get('especificaciones'):
        texto += '\nEspecificaciones: ' + necesidad['especificaciones']
    if necesidad.get('unidad_medida'):
        texto += '\nUnidad de medida: ' + necesidad['unidad_medida']
    if necesidad['equipos_actuales']:
        texto += '\nActivos actuales: ' + necesidad['equipos_actuales']
    if necesidad.get('grupo_fases'):
        if necesidad.get('resultado_fase'):
            texto += '\nResultado de la fase: ' + necesidad['resultado_fase']
        if necesidad.get('condicion_siguiente_fase'):
            texto += '\nCondición para continuar: ' + necesidad['condicion_siguiente_fase']
    return texto


def _sustento_gestion(unidad):
    """Sólo resume la lectura capturada; no convierte una remisión en análisis vivo."""
    gestion = unidad.get('gestion_inversion')
    if not isinstance(gestion, dict):
        return [('Revisión de uso y cumplimiento', 'Sin captura verificable de la revisión. Consultar a Dirección; no se infiere cumplimiento ni se asigna presupuesto.')]
    pares = [('Revisión de inversión', _plano(gestion.get('label')) or 'Por revisar')]
    if gestion.get('explicacion'):
        pares.append(('Sustento de la revisión', _plano(gestion['explicacion'])))
    motivos = gestion.get('motivos', [])
    if isinstance(motivos, list) and motivos:
        pares.append(('Aspectos por revisar', '\n'.join(_plano(m) for m in motivos)))
    documentacion = gestion.get('documentacion')
    if isinstance(documentacion, dict):
        pares.append(('Documentación al corte', 'Al día' if documentacion.get('al_dia') is True else
                      'Pendiente de completar o revisar' if documentacion.get('al_dia') is False else 'Por verificar'))
    if gestion.get('justificacion_uso_existente'):
        pares.append(('Uso de los recursos existentes', _plano(gestion['justificacion_uso_existente'])))
    acciones = gestion.get('acciones_cumplimiento', [])
    if isinstance(acciones, list):
        for accion in acciones:
            if not isinstance(accion, dict):
                continue
            detalle = '\n'.join(etiqueta + ': ' + _plano(accion.get(clave))
                for clave, etiqueta in (('accion', 'Acción'), ('responsable', 'Responsable'),
                    ('plazo', 'Plazo'), ('resultado', 'Resultado verificable')) if _plano(accion.get(clave)))
            if detalle:
                pares.append(('Compromiso de cumplimiento', detalle))
    return pares


def render_necesidades_xlsx(lectura):
    """Matriz universitaria consolidada, sin mezclar unidades ni atribuir fondos."""
    if any((u.get('pac_datos') or {}).get('compras_resumen_version') == 1 for u in lectura['unidades'] if u.get('transferible')):
        from .necesidades_resumen import render_necesidades_resumen_xlsx
        return render_necesidades_resumen_xlsx(lectura)
    from openpyxl import load_workbook
    from openpyxl.formula.translate import Translator
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from .pac_universitario import render_pac_xlsx
    unidades = [u for u in lectura['unidades'] if u['transferible']]
    libro = load_workbook(BytesIO(render_pac_xlsx({'pac_version': 1, 'compras': []}, '', lectura['anio_compras'], borrador=False)))
    for nombre in ('CONSOLIDADO', 'PAC', 'NO PAC'):
        hoja = libro[nombre]
        hoja.unmerge_cells('A5:F5')
        hoja.delete_rows(5, hoja.max_row)
        hoja['A3'] = 'NECESIDADES EVALUADAS POR DIRECCIÓN · GESTIÓN POR CENTRO DE COSTO'
    for unidad in unidades:
        individual = load_workbook(BytesIO(render_pac_xlsx(unidad['pac_datos'], unidad['nombre'], lectura['anio_compras'], borrador=False)))
        try:
            for nombre in ('CONSOLIDADO', 'PAC', 'NO PAC'):
                origen, destino = individual[nombre], libro[nombre]
                for numero in range(5, origen.max_row):
                    nueva = destino.max_row + 1
                    for celda in origen[numero]:
                        copia = destino.cell(nueva, celda.column)
                        valor = celda.value
                        if celda.data_type == 'f':
                            valor = Translator(valor, origin=celda.coordinate).translate_formula(copia.coordinate)
                        copia.value, copia.data_type = valor, celda.data_type
                        copia._style, copia.alignment = copy(celda._style), copy(celda.alignment)
                        copia.comment = copy(celda.comment)
                        copia.quotePrefix = celda.quotePrefix
                    destino.cell(nueva, 1, nueva - 4)
                    destino.row_dimensions[nueva].height = origen.row_dimensions[numero].height
        finally:
            individual.close()
    for nombre in ('CONSOLIDADO', 'PAC', 'NO PAC'):
        hoja = libro[nombre]
        final = hoja.max_row + 1
        incompletos = any(hoja.cell(n, 7).value is None for n in range(5, final))
        hoja.merge_cells(start_row=final, start_column=1, end_row=final, end_column=6)
        hoja.cell(final, 1, 'TOTAL POR COMPLETAR (USD)' if incompletos else 'TOTAL DE NECESIDADES EVALUADAS (USD)')
        if not incompletos:
            hoja.cell(final, 7, f'=SUM(G5:G{final - 1})' if final > 5 else '=0').number_format = '#,##0.00'
        ultima = get_column_letter(hoja.max_column)
        hoja.auto_filter.ref = f'A4:{ultima}{max(4, final - 1)}'
        hoja.print_area = f'A1:{ultima}{final}'
    def texto(celda, valor):
        celda.value, celda.data_type = _texto(valor), 's'
        celda.quotePrefix = celda.value.lstrip().startswith(('=', '+', '-', '@'))
    def adicional(nombre, cabeceras, filas):
        hoja = libro.create_sheet(nombre)
        for columna, etiqueta in enumerate(cabeceras, 1):
            celda = hoja.cell(1, columna, etiqueta)
            celda.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            celda.fill = PatternFill('solid', fgColor='27613B')
            hoja.column_dimensions[get_column_letter(columna)].width = 27 if columna < 4 else 35
        for numero, valores in enumerate(filas, 2):
            for columna, valor in enumerate(valores, 1):
                celda = hoja.cell(numero, columna)
                texto(celda, valor)
                celda.font = Font(name='Arial', size=10)
                celda.alignment = Alignment(wrap_text=True, vertical='top')
        hoja.freeze_panes = 'C2'
        hoja.auto_filter.ref = f'A1:{get_column_letter(len(cabeceras))}{max(1, hoja.max_row)}'
        hoja.print_title_rows = '1:1'
        hoja.page_setup.orientation = 'landscape'
        hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
    adicional('UNIDADES', ['DEPENDENCIA RECEPTORA', 'UNIDAD', 'CENTRO DE COSTO DECLARADO', 'ESTADO', 'NECESIDADES', 'TOTAL (USD)', 'JUSTIFICACIÓN SIN COMPRAS', 'EVALUACIÓN DE DIRECCIÓN', 'REFERENCIA DOCUMENTAL'],
        [[u['dependencia_nombre'], u['nombre'], u['centro_costo'], u['estado_etiqueta'], len(u['necesidades']) if u['transferible'] else '',
            u['total'], u['sin_compras_justificacion'], (u['fuente'] or {}).get('fecha_evaluacion', ''),
            (u['fuente'] or {}).get('token', '')] for u in lectura['unidades']])
    con_gestion = any(u.get('inversion_gestion_version') == 1 for u in unidades)
    cabeceras_programacion = ['DEPENDENCIA RECEPTORA', 'UNIDAD', 'CENTRO DE COSTO DECLARADO', 'ÁREA', 'CLASE DE BIEN O SERVICIO', 'MOTIVO', 'BIEN O SERVICIO', 'CANTIDAD', 'V. UNITARIO', 'TOTAL', 'SEMESTRE', 'MES', 'JUSTIFICACIÓN', 'EQUIPOS ACTUALES']
    if con_gestion:
        from .pac_universitario import ENCABEZADOS_FASES
        cabeceras_programacion.extend(ENCABEZADOS_FASES)
    adicional('PROGRAMACION', cabeceras_programacion,
        [[u['dependencia_nombre'], u['nombre'], u['centro_costo'], n['area'], n['clase'], n['motivo'], n['item'],
            n['cantidad'], n['costo_unitario'], n['total'], n['semestre'], n['mes'], n['justificacion'], n['equipos_actuales']]
            + ([n.get(clave, '') for clave in ('grupo_fases', 'fase_numero', 'resultado_fase', 'condicion_siguiente_fase')]
               if con_gestion else []) for u in unidades for n in u['necesidades']])
    if con_gestion:
        adicional('CUMPLIMIENTO_Y_USO', ['DEPENDENCIA RECEPTORA', 'UNIDAD', 'CENTRO DE COSTO DECLARADO',
            'CRITERIO', 'LECTURA CAPTURADA EN LA PRESENTACIÓN'],
            [[u['dependencia_nombre'], u['nombre'], u['centro_costo'], criterio, sustento]
             for u in unidades if u.get('inversion_gestion_version') == 1 for criterio, sustento in _sustento_gestion(u)])
    if any(u.get('matriz_detalle_version') == 1 for u in unidades):
        from .pac_universitario import CLASES_BIEN
        orden = {clave: indice for indice, (clave, _) in enumerate(CLASES_BIEN)}
        detalle = [(u, n) for u in unidades for n in u['necesidades']]
        detalle.sort(key=lambda par: (orden.get(par[1].get('clase_codigo'), 99), par[0]['nombre'], par[1]['numero']))
        adicional('DETALLE POR CLASE', ['CLASE', 'UNIDAD', 'ÁREA', 'NOMBRE DEL BIEN O SERVICIO',
            'ESPECIFICACIONES', 'UNIDAD DE MEDIDA', 'CANTIDAD', 'V. UNITARIO', 'TOTAL', 'CPC',
            'GRUPO', 'PARTIDA', 'PAC/NO PAC', 'FUENTE DE FINANCIAMIENTO', 'SEMESTRE', 'MES', 'JUSTIFICACIÓN'],
            [[n['clase'], u['nombre'], n['area'], n['item'], n.get('especificaciones', ''),
              n.get('unidad_medida', ''), n['cantidad'], n['costo_unitario'], n['total'], n.get('cpc', ''),
              n.get('partida', '')[:2], n.get('partida', ''), n.get('clasificacion_pac', ''),
              n.get('fuente_pac', ''), n['semestre'], n['mes'], n['justificacion']] for u, n in detalle])
    salida = BytesIO()
    libro.save(salida)
    libro.close()
    return salida.getvalue()


def render_necesidades_pdf(lectura, *, marco_pdf=None):
    """Resumen de gestión y sustento legible, sin consulta a datos operativos."""
    from apps.core.reportes import render_reporte
    from django.utils import timezone
    if marco_pdf is None:
        from apps.core.presentation.pdf_institucional import marco_institucional
        marco_pdf = marco_institucional(formato='Necesidades anuales por centro de costo', estilo='informe',
            metadatos=[f"Preparación: {lectura['anio_preparacion']}", f"Compras previstas: {lectura['anio_compras']}"],
            pie='Necesidades evaluadas por Dirección')
    secciones = [dict(titulo='Situación de las unidades', headers=['Dependencia / unidad', 'Declaración', 'Total previsto (USD)'],
        rows=[[u['dependencia_nombre'] + '\n' + u['nombre'], u['estado_etiqueta'], u['total'] if u['transferible'] and u['total'] is not None else 'Por completar' if u['transferible'] else '—'] for u in lectura['unidades']])]
    from .compras_resumen import resumen_compras, formato_monto
    from .necesidades_resumen import lectura_compras_consolidadas
    contenido_compras, importes_documentados = lectura_compras_consolidadas(lectura)
    resumen_clases = resumen_compras(contenido_compras, importes_documentados=importes_documentados)
    def importe(valor):
        return formato_monto(valor, conservar_precision=True)
    secciones.insert(0, dict(titulo='Compras solicitadas por clase',
        headers=['Clase', 'Necesidades', '1.er semestre USD', '2.º semestre USD', 'Total USD'],
        rows=[[c['nombre'], str(c['numero_necesidades']), importe(c['semestre_1']), importe(c['semestre_2']), importe(c['total'])]
              for c in resumen_clases['clases']] + [['Total solicitado', str(resumen_clases['numero_necesidades']),
                importe(resumen_clases['semestre_1']), importe(resumen_clases['semestre_2']), importe(resumen_clases['total_general'])]]))
    for unidad in lectura['unidades']:
        if not unidad['transferible']:
            continue
        if unidad.get('inversion_gestion_version') == 1:
            secciones.append(dict(titulo=unidad['nombre'] + ' · cumplimiento y uso para la inversión',
                headers=['Criterio', 'Lectura capturada en la presentación'], rows=_sustento_gestion(unidad)))
        if not unidad['necesidades']:
            secciones.append(dict(titulo=unidad['nombre'], headers=['Declaración sin compras', 'Referencia'],
                rows=[[unidad['sin_compras_justificacion'], unidad['fuente']['token']]]))
            continue
        secciones.append(dict(titulo=unidad['nombre'] + ' · ' + (unidad['centro_costo'] or 'Centro de costo por confirmar'),
            headers=['Área / clase / motivo', 'Necesidad y sustento', 'Cantidad / total USD', 'Programación'],
            rows=[[n['area'] + '\n' + n['clase'] + '\n' + n['motivo'], _sustento_necesidad(n),
                n['cantidad'] + '\nUSD ' + (n['total'] if n['total'] is not None else 'Por completar'),
                _programacion_necesidad(n)] for n in unidad['necesidades']]))
    resumen = lectura['resumen']
    reporte = dict(title=f"Necesidades de compras para {lectura['anio_compras']}", scope=lectura['alcance'],
        generated_at=timezone.now(), filter_summary=[('Año de preparación', lectura['anio_preparacion']), ('Año de compra previsto', lectura['anio_compras'])],
        metrics=[dict(nombre=nombre, valor=valor, unidad='unidades', periodo=str(lectura['anio_compras']))
            for nombre, valor in [('Unidades', resumen['unidades_total']), ('Con compras evaluadas', resumen['con_compras']),
                                 ('Sin compras evaluadas', resumen['sin_compras']), ('Pendientes', resumen['pendientes'])]],
        sections=secciones, notes=['Sólo las necesidades evaluadas por Dirección integran la matriz de transferencia. '
            'Una declaración ausente o una entrega sin matriz estructurada no equivale a que la unidad no necesita compras.',
            'Los importes y meses son previsiones. La aprobación documental no acredita financiamiento ni autoriza la contratación.'])
    return render_reporte(reporte, 'pdf', marco_pdf=marco_pdf)
