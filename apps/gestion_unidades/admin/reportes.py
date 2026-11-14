"""Reportes operativos internos por unidad."""

from apps.core.presentation.administracion import AdministracionTraducida

from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import BadRequest, PermissionDenied
from django.shortcuts import get_object_or_404
from urllib.parse import urlencode

from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.core.presentation.tipologias import codigos_por_base, tipologias_actuales
from apps.gestion_unidades.presentation.tablero_operativo import construir_tablero_operativo
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte, anio_pedido, entero_pedido
from apps.gestion_unidades.models.operaciones import ReporteOperativoUnidad


@admin.register(ReporteOperativoUnidad)
class ReporteOperativoUnidadAdmin(AdministracionTraducida):
    """Concentra indicadores operativos sin exponerlos en el portal público."""

    change_list_template = "admin/gestion_unidades/reporteoperativounidad/change_list.html"
    list_display = (
        "unidad",
        "estado_operativo",
        "equipos_activos",
        "incidencias_abiertas",
        "mantenimientos_vencidos",
        "consumibles_criticos",
        "acciones_administrativas",
    )
    # Solo las unidades que el queryset (ya acotado por administrador) contiene:
    # un administrador de unidad no debe ver ni el nombre de las demas.
    list_filter = (("unidad", admin.RelatedOnlyFieldListFilter),)
    list_select_related = ("unidad",)
    search_fields = ("unidad__nombre", "unidad__codigo")
    ordering = ("unidad__nombre",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        from apps.gestion_unidades.admin.acceso import unidades_editables
        return queryset.filter(unidad__in=unidades_editables(request.user))

    def has_module_permission(self, request):
        from apps.gestion_unidades.admin.acceso import unidades_editables
        if unidades_editables(request.user).exists():
            return True
        return bool(
            request.user.is_active
            and request.user.is_staff
            and (
                request.user.is_superuser
                or ReporteOperativoUnidad.objects.filter(
                    unidad__administrador=request.user
                ).exists()
            )
        )

    def has_view_permission(self, request, obj=None):
        if not self.has_module_permission(request):
            return False
        return obj is None or request.user.is_superuser or self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        propias = [
            path("evidencia/<slug:slug>/", self.admin_site.admin_view(self.documento_evidencia),
                 name="reportes-documento-evidencia"),
            path("institucional/", self.admin_site.admin_view(self.reporte_institucional),
                 name="reportes-institucional"),
            path("evidencias/", self.admin_site.admin_view(self.evidencias_por_tipo),
                 name="reportes-evidencias-por-tipo"),
            path("expediente/", self.admin_site.admin_view(self.expediente_por_tipo),
                 name="reportes-expediente-por-tipo"),
            path("cumplimiento/", self.admin_site.admin_view(self.cumplimiento_del_expediente),
                 name="reportes-cumplimiento-expediente"),
            path('necesidades-decanatos/', self.admin_site.admin_view(self.necesidades_decanatos),
                 name='reportes-necesidades-decanato'),
        ]
        return propias + super().get_urls()

    def necesidades_decanatos(self, request):
        from apps.documentos.presentation.necesidades_decanato_vistas import necesidades_decanato_view
        return necesidades_decanato_view(request, admin_site=self.admin_site)

    def cumplimiento_del_expediente(self, request):
        """Qué entregó cada unidad en el período, y la decisión de la Dirección aquí mismo.

        Es la lectura con la que el director del sistema responde cuántas
        unidades cumplen, y donde decide: recibe la entrega que la unidad
        archivó sin validar, habilita una entrega vencida, califica de 0 a 100 o
        devuelve el documento. Cada decisión queda en la auditoría de la unidad,
        y el PDF sale con el mismo marco institucional.
        """
        from django.contrib import messages
        from django.core.exceptions import ValidationError
        from django.shortcuts import redirect

        from apps.documentos.presentation.cumplimiento import (
            completar_controles_de_lectura, cumplimiento_por_periodo, filtrar_bandeja_automatizacion,
            grupos_por_tipo, nombre_del_tipo, pdf_de_cumplimiento, tipos_auditados,
            unidades_auditadas, ventana_del_periodo,
        )
        from apps.documentos.presentation.expediente import evaluar_documento, habilitar_entrega_tardia, observar_documento, recibir_documento
        from apps.documentos.models.expediente import DocumentoExpediente

        if not request.user.has_perm("documentos.view_documentoexpediente"):
            raise PermissionDenied
        if request.method == "POST":
            if not request.user.is_active or not request.user.is_superuser:
                raise PermissionDenied
            documento = get_object_or_404(
                DocumentoExpediente.objects.select_related("exigido", "unidad"),
                pk=entero_pedido(request.POST.get("documento"), 'Documento'))
            destino = f'{request.path}?{request.POST.get("query", "")}'
            accion = request.POST.get("accion")
            if documento.exigido.codigo == 'INFORME-SEMESTRAL' and accion in ('evaluar_rubrica', 'evaluar'):
                from apps.documentos.presentation.evaluacion_cierre import cierre_archivado
                if cierre_archivado(documento):
                    accion = 'confirmar_cierre'
            try:
                if accion in ('corregir_observacion', 'corregir_justificacion_tardia'):
                    from apps.documentos.presentation.expediente import anotar_observacion
                    from apps.documentos.presentation.observaciones_documentales import corregir_justificacion_tardia
                    funcion = anotar_observacion if accion == 'corregir_observacion' else corregir_justificacion_tardia
                    funcion(documento, request.user, request.POST.get('texto', ''),
                        version=request.POST.get('version'), recurso_id=request.POST.get('recurso_id'),
                        huella=request.POST.get('huella'), huella_anterior=request.POST.get('huella_texto'),
                        motivo=request.POST.get('motivo'), request=request)
                    mensaje = 'Texto corregido. Se conservan historial, resultado, plazos y aprobaciones.'
                elif accion == 'aprobar_permanente':
                    from apps.documentos.presentation.conformidad_permanente import aprobar_permanente
                    aprobar_permanente(documento, request.user, request.POST.get('version'),
                        request.POST.get('huella'), request.POST.get('confirmado') == '1',
                        request.POST.get('comentario', ''), request=request)
                    mensaje = 'Documento permanente aprobado. Se conserva para los siguientes períodos, sin recalificarlo.'
                elif accion in ('aprobar_documento', 'rechazar_documento'):
                    from apps.documentos.presentation.revision_documental import decidir_desde_listado
                    decidir_desde_listado(documento, request.user, version=request.POST.get('version'),
                        huella=request.POST.get('huella'), decision='aprobar' if accion == 'aprobar_documento' else 'rechazar',
                        observacion=request.POST.get('observacion', ''), request=request)
                    mensaje = 'Documento aprobado.' if accion == 'aprobar_documento' else 'Documento rechazado. La unidad puede corregir y reenviar.'
                elif accion in ('aprobar_qr', 'observar_qr'):
                    from apps.documentos.presentation.aprobacion_en_linea import decidir_documento_qr
                    decidir_documento_qr(documento, request.user, token=request.POST.get('token'),
                        version=request.POST.get('version'), decision='aprobar' if accion == 'aprobar_qr' else 'observar',
                        observacion=request.POST.get('observacion', ''), request=request)
                    mensaje = 'Documento aprobado.' if accion == 'aprobar_qr' else 'Documento rechazado. La unidad puede corregir y reenviar.'
                elif accion == 'confirmar_conformidad':
                    from apps.documentos.presentation.conformidad_planes import confirmar_conformidad
                    confirmar_conformidad(documento, request.user, request.POST.get('version'),
                        request.POST.get('huella'), request.POST.get('confirmado') == '1',
                        request.POST.get('comentario', ''), request=request)
                    mensaje = 'Conformidad documental confirmada. Los resultados se medirán con los indicadores del cierre.'
                elif accion == 'confirmar_cierre':
                    from apps.documentos.presentation.evaluacion_cierre import confirmar_cierre
                    confirmar_cierre(documento, request.user, request.POST.get('version'),
                                     request.POST.get('huella'), request.POST.get('confirmado') == '1',
                                     request.POST.get('comentario', ''), request=request)
                    mensaje = 'Informe revisado: cumplimiento de metas confirmado por Dirección.'
                elif accion == 'retirar_archivo':
                    from apps.documentos.presentation.expediente_archivos import retirar_archivo
                    if request.POST.get('confirmar_retiro') != '1':
                        raise ValidationError('Confirma la retirada del archivo indicado.')
                    retirar_archivo(documento, request.user, request.POST.get('motivo'),
                                    request.POST.get('version'), request.POST.get('huella'), request=request)
                    mensaje = 'Archivo retirado de la entrega; permanece en el historial. La unidad debe cargar el correcto.'
                elif accion == 'ultimatum':
                    from apps.documentos.presentation.incumplimiento_documental import establecer_ultimatum
                    cantidad = establecer_ultimatum(documento, request.user, request.POST.get('hasta'),
                                                    request.POST.get('motivo'), request=request)
                    mensaje = f'Ultimátum establecido para {cantidad} unidades pendientes. Avisos registrados.'
                elif accion == 'asignar_plazo':
                    from apps.documentos.presentation.plazos_documentales import asignar_plazo_inicial
                    asignar_plazo_inicial(documento, request.user, request.POST.get('hasta'), request=request)
                    mensaje = 'Plazo institucional asignado para todas las unidades de este a?o.'
                elif accion == 'evaluar_rubrica':
                    from apps.formacion.presentation.evaluacion_rubrica import evaluar_con_rubrica
                    evaluar_con_rubrica(documento, request.user, request.POST,
                        request.POST.get('version'), request.POST.get('huella'),
                        confirmado=request.POST.get('confirmado') == '1',
                        comentario=request.POST.get('comentario', ''), request=request)
                    mensaje = f'Evaluación guardada: {documento.nota} %. Criterios y observaciones registrados.'
                elif accion == "recibir":
                    recibir_documento(documento, request.user, request=request)
                    mensaje = (f"{documento.nombre_documental} de {documento.unidad.nombre}: recibido"
                               + (" fuera de plazo." if documento.entregado_tarde else "."))
                elif accion == "habilitar_tardia":
                    habilitar_entrega_tardia(documento, request.user, hasta=request.POST.get('hasta'), request=request)
                    mensaje = (f"{documento.nombre_documental} de {documento.unidad.nombre}: "
                               + ("corrección reabierta; conserva la puntualidad de la entrega inicial."
                                  if documento.correccion_hasta else
                                  "entrega fuera de plazo habilitada; lo que llegue quedará marcado como tardío."))
                elif accion == "observar":
                    observar_documento(documento, request.user, request.POST.get("observacion", ""),
                                       hasta=request.POST.get('hasta_correccion'), request=request)
                    mensaje = (f"{documento.nombre_documental} de {documento.unidad.nombre}: devuelto a la unidad "
                               "para que lo corrija.")
                elif accion == 'evaluar':
                    evaluar_documento(
                        documento, request.user, request.POST.get("evaluacion"),
                        request.POST.get("evaluacion_observacion", ""),
                        request.POST.get("evaluacion_fortalezas", ""),
                        request.POST.get("evaluacion_debilidades", ""),
                        request.POST.get("evaluacion_recomendaciones", ""), request=request)
                    mensaje = (f"{documento.nombre_documental} de {documento.unidad.nombre}: "
                               f"{documento.nota} % de cumplimiento.")
                else:
                    raise ValidationError('Acción documental no reconocida.')
            except ValidationError as error:
                messages.error(request, " ".join(error.messages))
            else:
                messages.success(request, mensaje)
            return redirect(destino)
        hoy = timezone.localdate()
        anio = anio_pedido(request.GET.get("anio"), hoy.year)
        corte = request.GET.get("corte") or ""
        if not any(clave in request.GET for clave in ('anio', 'corte', 'desde', 'hasta')):
            from apps.documentos.presentation.expediente import cortes_del_anio, periodo_vigente
            corte = periodo_vigente(cortes_del_anio(anio), hoy)
        if corte not in ("", "A", "B"):
            raise BadRequest('Corte inexistente.')
        # El alcance del reporte: todas las unidades, las de un tipo o una sola,
        # y con el tramo de fechas que se pida en lugar del período completo.
        tipos = tipos_auditados()
        tipo = request.GET.get("tipo") or ""
        if tipo and tipo not in {codigo for codigo, _ in tipos}:
            raise BadRequest('Tipo de unidad inexistente.')
        unidades = list(unidades_auditadas(request.user))
        unidad = request.GET.get("unidad") or ""
        if unidad:
            seleccionada = next((u for u in unidades if u.slug == unidad), None)
            if seleccionada is None:
                seleccionada = next((u for u in unidades if str(u.pk) == unidad), None)
            if seleccionada is None:
                raise BadRequest('Unidad fuera del alcance del reporte.')
            unidad = seleccionada.slug
        periodo = PeriodoReporte.pedido(request.GET)
        desde, hasta = periodo.desde, periodo.hasta
        automatizacion = request.GET.get('automatizacion', '')
        if automatizacion not in ('', 'excepciones', 'unidad', 'automatico', 'sin_analizar'):
            raise BadRequest('Bandeja de control inexistente.')
        filas, totales = cumplimiento_por_periodo(
            anio, corte, usuario=request.user, dependencias=(tipo,) if tipo else None,
            desde=desde, hasta=hasta, solo_unidad=unidad)
        alcance = "todas las unidades"
        if unidad:
            alcance = next((u.nombre for u in unidades if u.slug == unidad), unidad)
        elif tipo:
            alcance = nombre_del_tipo(tipo)
        filas_pantalla = filtrar_bandeja_automatizacion(filas, automatizacion)
        if request.GET.get("formato") == "pdf":
            contenido = pdf_de_cumplimiento(filas_pantalla, totales, anio, corte, alcance=alcance,
                                            tramo=(desde, hasta) if desde or hasta else None,
                                            bandeja=automatizacion)
            respuesta = HttpResponse(contenido, content_type="application/pdf")
            nombre = f"cumplimiento-expediente-{anio}{corte or 'anual'}{'-' + unidad if unidad else ''}"
            respuesta["Content-Disposition"] = (
                f'{"attachment" if request.GET.get("download") else "inline"}; filename="{nombre}.pdf"')
            return respuesta
        pagina_controles = None
        if automatizacion:
            from django.core.paginator import Paginator
            pagina_controles = Paginator(filas_pantalla, 25).get_page(request.GET.get('pagina'))
            filas_pantalla = list(pagina_controles.object_list)
        inicio, fin = ventana_del_periodo(anio, corte)
        revision = None
        archivos_documento = None
        versiones_archivo = []
        plazos_casilla = None
        plazos = entero_pedido(request.GET.get('plazos'), 'Documento')
        if plazos:
            plazos_casilla = next((c for fila in filas for c in fila['matriz']
                                  if c['documento'].pk == plazos), None)
            if plazos_casilla is None:
                raise BadRequest('Documento fuera del alcance del reporte.')
        revisar = entero_pedido(request.GET.get('revisar'), 'Documento')
        if revisar:
            from apps.formacion.presentation.evaluacion_rubrica import revisar_documento
            documento = next((d for fila in filas for d in fila['documentos'] if d.pk == revisar), None)
            if documento is None or documento.exigido.es_anexo:
                raise BadRequest('Documento fuera del alcance del reporte.')
            if request.GET.get('vista') == 'observaciones':
                from apps.documentos.presentation.observaciones_documentales import contexto_observaciones
                revision = dict(documento=documento, solo_observaciones=True,
                    observaciones_documentales=contexto_observaciones(documento, request.user),
                    observaciones_query=request.GET.urlencode() + '#evaluacion')
            else:
                revision = revisar_documento(documento)
        archivos = entero_pedido(request.GET.get('archivos'), 'Documento')
        if archivos:
            from apps.documentos.presentation.expediente_archivos import versiones_del_documento
            archivos_documento = next((d for fila in filas for d in fila['documentos'] if d.pk == archivos), None)
            if archivos_documento is None or archivos_documento.exigido.es_anexo:
                raise BadRequest('Documento fuera del alcance del reporte.')
            versiones_archivo = versiones_del_documento(archivos_documento)
        from apps.documentos.presentation.documentos_entrega import ruta_borrador
        from apps.documentos.presentation.expediente import anexos_del
        anexos_revision_obj = anexos_del(revision['documento']) if revision and revision.get('cierre') else []
        anexos_revision_obj = completar_controles_de_lectura(anexos_revision_obj)
        anexos_revision = [dict(documento=a.pk, nombre=a.nombre_documental, recurso=a.recurso_id,
                                version=a.version, sha256=a.recurso.hash_sha256 if a.recurso_id else '',
                                porcentaje=None) for a in anexos_revision_obj]
        if revision and revision.get('cierre') and revision['cierre'].get('congelado'):
            # La lista usa exclusivamente los recursos que viajaron en esa entrega.
            anexos_revision = [dict(a) for a in revision['cierre']['anexos']]
        actuales = {a.pk: a for a in anexos_revision_obj}
        for anexo in anexos_revision:
            actual = actuales.get(anexo.get('documento'))
            if (actual and anexo.get('version') == actual.version
                    and anexo.get('recurso') == actual.recurso_id
                    and anexo.get('sha256') == (actual.recurso.hash_sha256 if actual.recurso_id else '')):
                anexo['automatizacion'] = getattr(actual, 'automatizacion', {})
        if revision and revision.get('cierre'):
            from apps.documentos.presentation.evaluacion_cierre import detalle_anexo
            por_pk = {a.pk: a.exigido.codigo for a in anexos_revision_obj}
            for anexo in anexos_revision:
                codigo = por_pk.get(anexo.get('documento'))
                if codigo is None:
                    codigo = next((a.exigido.codigo for a in anexos_revision_obj
                                   if a.nombre_documental == anexo['nombre']), '')
                anexo['detalle_indicadores'] = anexo.get('detalle_indicadores') or detalle_anexo(
                    codigo, revision['cierre'], anexo.get('indicadores'))
        # El seguimiento detallado se carga solo para la unidad seleccionada;
        # el consolidado no multiplica consultas de trámites por todas las unidades.
        if unidad:
            from apps.documentos.presentation.expediente import nivel_de_cumplimiento
            from apps.documentos.presentation.mejora_seguimiento import contexto_mejora
            from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
            for fila in filas_pantalla:
                if fila['unidad'].slug != unidad:
                    continue
                fila['resultado_periodo'] = nivel_de_cumplimiento(fila['unidad'], anio, corte, hoy)
                fila['mejora_contexto'] = contexto_mejora(fila['unidad'], anio, corte, request.user)
                tramite = fila['mejora_contexto'].get('tramite_mejora')
                fila['mejora_contexto']['mejora_antecedente'] = bool(
                    tramite and not tramite.remitido_en and not fila['resultado_periodo']['requiere_mejora'])
                fila['volver_mejora'] = request.get_full_path()
                fila['solo_lectura_mejora'] = not puede_operar_modulo_unidad(request.user, fila['unidad'], 'reportes')
        contexto = {
            **self.admin_site.each_context(request),
            "title": "Cumplimiento del expediente por unidad",
            'url_necesidades_decanato': (reverse('admin:reportes-necesidades-decanato')
                if request.user.is_superuser or request.user.dependencias_que_recibe.filter(activa=True).exists() else ''),
            'revision': revision,
            'plazos_casilla': plazos_casilla,
            'archivos_documento': archivos_documento,
            'versiones_archivo': versiones_archivo,
            'borrador_url': ruta_borrador(archivos_documento) if archivos_documento else '',
            'borrador_revision_url': ruta_borrador(revision['documento']) if revision else '',
            'anexos_revision': anexos_revision,
            'ruta_archivos': (reverse('gestion_expediente_unidad', args=[archivos_documento.unidad.slug])
                             + '?' + urlencode(dict(anio=archivos_documento.anio,
                                                    corte=archivos_documento.corte, gestionar=archivos_documento.pk))
                             if archivos_documento else ''),
            "anio": anio, "corte": corte, "filas": filas_pantalla, "totales": totales,
            "automatizacion": automatizacion, 'pagina_controles': pagina_controles,
            'automatizacion_resumen': totales['automatizacion_resumen'],
            "grupos": grupos_por_tipo(filas_pantalla),
            "tipos": tipos, "tipo": tipo, "unidades": unidades, "unidad": unidad,
            "desde": desde, "hasta": hasta, "alcance": alcance,
            "inicio": inicio, "fin": fin, 'hoy': hoy,
            "query": urlencode({
                "anio": anio, "corte": corte, "tipo": tipo, "unidad": unidad,
                'automatizacion': automatizacion,
                "desde": desde.isoformat() if desde else "", "hasta": hasta.isoformat() if hasta else "",
            }),
            # El visor cambia el tramo sobre el mismo reporte: su enlace no lleva fechas.
            "query_sin_tramo": urlencode({
                "anio": anio, "corte": corte, "tipo": tipo, "unidad": unidad,
                'automatizacion': automatizacion}),
            "minimo": totales["minimo"],
        }
        if request.GET.get('fragmento') == 'avance':
            from django.http import JsonResponse
            from django.template.loader import render_to_string
            if not unidad or len(filas_pantalla) != 1:
                raise BadRequest('Selecciona una unidad para consultar su avance actual.')
            fila = filas_pantalla[0]
            base = 'portal/pages/unidades/gestion/includes/'
            progreso = render_to_string(base + 'progreso_general.html', dict(contexto,
                progreso_general=fila['progreso_general'], progreso_unidad_id=fila['unidad'].pk,
                progreso_control_documental=True, unidad=fila['unidad']), request=request)
            avances = {str(d.pk): render_to_string(base + 'avance_documental.html',
                dict(avance=d.avance_documental, nombre_documento=d.nombre_documental), request=request)
                for d in fila['documentos'] if d.pk}
            return JsonResponse(dict(progreso=progreso, avances=avances))
        return TemplateResponse(
            request, "admin/gestion_unidades/reporteoperativounidad/cumplimiento.html", contexto)

    def documento_evidencia(self, request, slug):
        from apps.gestion_unidades.presentation.gestion import gestion_reporte_unidad_pdf_view

        if not self.has_module_permission(request):
            raise PermissionDenied
        respuesta = gestion_reporte_unidad_pdf_view(request, slug)
        if request.GET.get('descargar') != '1':
            respuesta['Content-Disposition'] = respuesta['Content-Disposition'].replace('attachment;', 'inline;', 1)
        return respuesta

    def reporte_institucional(self, request):
        from apps.plantas_piloto.operacion.presentation.trazabilidad import contexto_institucional, exportar_institucional
        from apps.documentos.presentation.documentos import enlaces_de_documento
        from apps.gestion_unidades.presentation.exportaciones_reportes import formato_reporte
        from apps.core.presentation.identidad import identidad_publica

        from apps.centros_id.informes import puede_reportar_centros
        if not self.has_view_permission(request) and not puede_reportar_centros(request.user):
            raise PermissionDenied
        formato = formato_reporte(request, permitir_csv=False)
        contexto = contexto_institucional(request)
        if formato:
            return exportar_institucional(contexto, formato, request.GET.get('descargar') == '1')
        contexto.update({**self.admin_site.each_context(request), **identidad_publica(),
                         **enlaces_de_documento(request), 'en_admin': True,
                         'title': 'Reporte institucional',
                         'volver_url': reverse('admin:index') + '#reportes'})
        return TemplateResponse(request, 'admin/gestion_unidades/reporteoperativounidad/institucional.html', contexto)

    def expediente_por_tipo(self, request):
        """Cuanto de lo exigido tiene cada unidad del tipo, carpeta por carpeta."""
        from apps.documentos.presentation.expediente import resumen_unidad
        from apps.gestion_unidades.presentation.permisos import unidades_del_expediente

        if not self.has_view_permission(request):
            raise PermissionDenied
        bases = [(t.base, t.etiqueta("es", plural=True)) for t in tipologias_actuales() if t.codigo == t.base]
        tipo = request.GET.get("tipo") or "laboratorios"
        if tipo not in dict(bases):
            raise BadRequest('Tipo de unidad inexistente.')
        anio = anio_pedido(request.GET.get("anio"), timezone.localdate().year)
        unidades = unidades_del_expediente(request.user).filter(
            dependencia__in=codigos_por_base(tipo), activo=True).order_by("nombre")
        filas = [resumen_unidad(unidad, anio) for unidad in unidades]
        contexto = {
            **self.admin_site.each_context(request),
            "title": "Resumen anual de entregas",
            "tipos": bases, "tipo": tipo, "anio": anio, "filas": filas,
        }
        return TemplateResponse(request, "admin/gestion_unidades/reporteoperativounidad/expediente.html", contexto)

    def evidencias_por_tipo(self, request):
        """Conserva los accesos anteriores a la vista original de la Dirección."""
        from apps.documentos.presentation.cumplimiento import tipos_auditados, unidades_auditadas
        from django.shortcuts import redirect

        if not self.has_module_permission(request):
            raise PermissionDenied
        tipos = tipos_auditados()
        tipo = request.GET.get('tipo', '')
        if tipo and tipo not in dict(tipos):
            raise BadRequest('Tipo de unidad inexistente.')
        hoy = timezone.localdate()
        periodo = PeriodoReporte.pedido(request.GET, defecto=(hoy - timedelta(days=89), hoy), maximo_dias=730)
        anio = anio_pedido(request.GET.get('anio'), hoy.year)
        parametros = {}
        if request.GET.get('anio'):
            parametros['anio'] = anio
        if request.GET.get('desde') or request.GET.get('hasta'):
            parametros.update(periodo.parametros(), anio=periodo.hasta.year, corte='')
        if request.user.has_perm('documentos.view_documentoexpediente'):
            for clave in ('tipo', 'unidad', 'corte', 'automatizacion'):
                if request.GET.get(clave):
                    parametros[clave] = request.GET[clave]
            destino = reverse('admin:reportes-cumplimiento-expediente')
            if parametros:
                destino += '?' + urlencode(parametros)
            return redirect(destino)
        grupos = {codigo: dict(codigo=codigo, nombre=nombre, filas=[]) for codigo, nombre in tipos
                  if not tipo or codigo == tipo}
        filas = []
        for unidad in unidades_auditadas(request.user).filter(dependencia__in=grupos).only('nombre', 'slug', 'dependencia'):
            url = reverse('gestion_expediente_unidad', args=[unidad.slug])
            if parametros:
                url += '?' + urlencode(parametros)
            fila = dict(unidad=unidad, url=url)
            grupos[unidad.dependencia]['filas'].append(fila)
            filas.append(fila)
        contexto = {
            **self.admin_site.each_context(request),
            'title': 'Expedientes de las unidades',
            'tipos': tipos, 'tipo': tipo, 'filas': filas,
            'grupos': [grupo for grupo in grupos.values() if grupo['filas']],
        }
        return TemplateResponse(request, "admin/gestion_unidades/reporteoperativounidad/evidencias.html", contexto)

    def _tablero(self, obj):
        if not hasattr(obj, "_reporte_tablero"):
            obj._reporte_tablero = construir_tablero_operativo(obj.unidad, obj)
        return obj._reporte_tablero

    @admin.display(description="Estado")
    def estado_operativo(self, obj):
        estado = self._tablero(obj)["estado"]
        colores = {
            "estable": ("#e8f5ee", "#185c3d"),
            "advertencia": ("#fff5d8", "#7c5700"),
            "critico": ("#fdeaea", "#9e2f2f"),
        }
        fondo, texto = colores.get(estado["tono"], colores["advertencia"])
        return format_html(
            '<span style="display:inline-block;padding:.3rem .55rem;border-radius:999px;'
            'background:{};color:{};font-weight:700">{}</span>',
            fondo,
            texto,
            estado["etiqueta"],
        )

    @admin.display(description="Equipos activos")
    def equipos_activos(self, obj):
        return self._tablero(obj)["total_equipos"]

    @admin.display(description="Incidencias abiertas")
    def incidencias_abiertas(self, obj):
        return self._tablero(obj)["incidencias_abiertas"]

    @admin.display(description="Mant. vencidos")
    def mantenimientos_vencidos(self, obj):
        metricas = self._tablero(obj)["metricas"]
        return metricas[3]["valor"]

    @admin.display(description="Stock crítico")
    def consumibles_criticos(self, obj):
        return self._tablero(obj)["consumibles_bajos"]

    @admin.display(description="Administrar")
    def acciones_administrativas(self, obj):
        unidad_id = obj.unidad_id
        app = self.opts.app_label
        from django.apps import apps
        def namespace(nombre, predeterminado):
            try:
                modelo = apps.get_model(app, nombre)
            except LookupError:
                return predeterminado
            return app if modelo in self.admin_site._registry else predeterminado
        app_reservas = namespace('Reserva', 'reservas')
        app_recursos = namespace('Consumible', 'recursos')
        enlaces = (
            ("Unidad", reverse("admin:directorio_unidades_unidad_change", args=[unidad_id])),
            ("Reservas", f'{reverse(f"admin:{app_reservas}_reserva_changelist")}?laboratorio__id__exact={unidad_id}'),
            ("Inventario", f'{reverse(f"admin:{app_recursos}_consumible_changelist")}?unidad__id__exact={unidad_id}'),
        )
        return format_html(
            " &nbsp; ".join('<a href="{}">{}</a>' for _ in enlaces),
            *(valor for enlace in enlaces for valor in (enlace[1], enlace[0])),
        )
