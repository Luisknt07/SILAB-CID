"""Lo que la ficha de un centro muestra en cada pestaña, armado desde sus registros.

Cada sección del mapa recibe su página en el visualizador y, en el panel, solo lo esencial; las áreas del centro
cuelgan de «Áreas del centro», cada una con su página de procesos, equipos, servicios, proyectos, resultados y
personas, junto al edificio que las aloja. Una sección sin contenido no se ofrece al público; quien gestiona el
centro la ve marcada como pendiente, con el enlace para completarla. El centro renombra u oculta secciones con un
ajuste y suma carpetas propias con sus recursos. Los indicadores con cálculo se miden solos desde los registros.
"""
from django.db.models import Prefetch
from django.urls import reverse

from .gestion_catalogo import url_edicion
from django.utils import timezone
from django.utils.functional import cached_property

from .mapa import MAPA, SUBPAGINAS
from .escenarios import contenido_admitido, escenario_activo, filtro_contenido

# Dónde completa el gestor cada sección vacía, dentro del panel dinámico propio.
ADMIN_SECCION = {
    'relaciones': 'centroid', 'direccion': 'integrante',
    'investigadores': 'integrante', 'personal': 'integrante', 'grupos': 'grupo', 'proyectos': 'proyecto',
    'produccion': 'resultado', 'desarrollos': 'resultado', 'casos': 'casoexito', 'alianzas': 'aliado',
    'portafolio': 'servicio', 'oportunidades': 'convocatoria', 'ahora': 'novedad', 'documentos': 'documentocentro',
    'gobierno': 'documentocentro', 'areas': 'componente',
}


def _boton(identificador, nombre, url, icono, detalle='', subtitulo='', externo=False, imagen=''):
    return {'id': identificador, 'nombre': nombre, 'url': url, 'icono': icono, 'detalle': detalle,
            'subtitulo': subtitulo, 'externo': externo, 'imagen': imagen}


def _grupo(identificador, nombre, botones, icono='fas fa-folder', url='', propia=False):
    """Una carpeta dentro de una sección: agrupa archivos en el árbol del panel."""
    return {'id': identificador, 'nombre': nombre, 'botones': botones, 'icono': icono, 'url': url, 'propia': propia}


def _nombre(area):
    return area.nombre_corto or area.nombre


# Los indicadores que se miden solos: cada cálculo cuenta registros del centro, nunca se escribe un valor a mano.
CALCULOS = {
    'proyectos_activos': lambda c: c.resumen_proyectos['activos'],
    'proyectos_concluidos': lambda c: c.resumen_proyectos['concluidos'],
    'proyectos_con_aliados': lambda c: sum(1 for p in c.proyectos if any(contenido_admitido(a) and a.activo for a in p.aliados.all())),
    'investigadores': lambda c: len(c.investigadores),
    'en_formacion': lambda c: len(c.por_rol('tesista', 'estudiante')),
    'produccion': lambda c: c.resumen_produccion['total'],
    'datos_y_software': lambda c: c.consulta_resultados('produccion').filter(tipo__in=('dato', 'software')).count(),
    'propiedad_intelectual': lambda c: c.resumen_desarrollos['propiedad'],
    'prototipos': lambda c: c.resumen_desarrollos['prototipos'],
    'casos': lambda c: len(c.casos),
    'aliados': lambda c: len(c.aliados_vigentes),
    'servicios': lambda c: len(c.servicios),
}


def ocultar_referencias_muestra(objeto):
    """Evita divulgar relaciones de demostración desde un registro institucional. Solo modifica la instancia leída."""
    for campo in ('responsable', 'proyecto', 'aliado', 'desarrollo'):
        relacionado = getattr(objeto, campo, None)
        oculto = bool(relacionado and getattr(relacionado, 'es_muestra', False) and not contenido_admitido(relacionado)) or bool(
            relacionado and getattr(relacionado, 'centro_id', None) != objeto.centro_id)
        if campo == 'responsable' and relacionado:
            oculto = oculto or not relacionado.vigente or relacionado.rol not in relacionado.PUBLICOS
        if campo == 'proyecto' and relacionado:
            oculto = oculto or not relacionado.publicado
        if campo == 'desarrollo' and relacionado:
            oculto = oculto or not relacionado.visible
        if oculto:
            setattr(objeto, campo, None)
    return objeto


class Contenidos:
    """Consulta cada colección al usarla y la reutiliza dentro de la petición."""

    def __init__(self, centro, usuario=None):
        self.centro = centro
        self.usuario = usuario
        self.hoy = timezone.localdate()
        self.escenario = escenario_activo(centro)
        self._filtro = filtro_contenido(centro)

    @cached_property
    def gestor(self):
        return self.centro.puede_gestionar(self.usuario) if self.usuario is not None else False

    # Cada sección materializa solo sus colecciones. La caché dura esta petición:
    # no conserva permisos ni conteos entre usuarios o escrituras concurrentes.
    @cached_property
    def areas(self):
        from .models import EquipoCentro
        return list(self.centro.componentes.filter(publicado=True).prefetch_related(
            'imagenes', 'servicios', 'procesos',
            Prefetch('equipos', queryset=EquipoCentro.objects.filter(**self._filtro))))

    @cached_property
    def zonas(self):
        return list(self.centro.zonas.filter(**self._filtro).select_related('componente'))

    @cached_property
    def planos(self):
        return list(self.centro.planos.all())

    @cached_property
    def herramientas(self):
        return [h for h in self.centro.herramientas.all() if h.visible]

    @cached_property
    def lineas(self):
        filas = list(self.centro.lineas.select_related('componente', 'responsable'))
        for linea in filas:
            ocultar_referencias_muestra(linea)
            if self.escenario and not linea.retos:
                linea.retos = linea.retos_muestra
        return filas

    @cached_property
    def servicios(self):
        return list(self.centro.servicios.filter(activo=True).select_related('componente'))

    @cached_property
    def proyectos(self):
        from .models import Aliado
        filas = list(self.centro.proyectos.filter(publicado=True, **self._filtro)
                     .select_related('linea', 'responsable').prefetch_related(
                         'componentes', Prefetch('aliados', queryset=Aliado.objects.filter(
                             centro=self.centro, activo=True, **self._filtro)), 'casos', 'hitos_registrados'))
        return [ocultar_referencias_muestra(objeto) for objeto in filas]

    @cached_property
    def resultados(self):
        filas = list(self.centro.resultados.filter(publicado=True, confidencial=False, **self._filtro)
                     .select_related('proyecto__linea', 'componente').prefetch_related('autores'))
        return [ocultar_referencias_muestra(objeto) for objeto in filas]

    @cached_property
    def integrantes(self):
        return list(self.centro.integrantes.filter(vigente=True, **self._filtro)
                    .select_related('componente', 'grupo').prefetch_related('lineas'))

    @cached_property
    def grupos(self):
        return list(self.centro.grupos.filter(activo=True, **self._filtro).prefetch_related('lineas'))

    @cached_property
    def casos(self):
        filas = self.centro.casos.filter(publicado=True, **self._filtro).select_related(
            'componente', 'aliado', 'proyecto', 'desarrollo')
        return [ocultar_referencias_muestra(caso) for caso in filas if caso.transferencia_documentada]

    @cached_property
    def aliados(self):
        return list(self.centro.aliados.filter(activo=True, **self._filtro))

    @cached_property
    def aliados_vigentes(self):
        return [a for a in self.aliados if a.vigente]

    @cached_property
    def convocatorias(self):
        return [c for c in self.centro.convocatorias.filter(activa=True, **self._filtro) if c.vigente]

    @cached_property
    def novedades(self):
        return list(self.centro.novedades.filter(publicada=True, **self._filtro)[:12])

    @cached_property
    def documentos(self):
        # Mantener el alcance público/privado y demostrativo del dominio.
        return [d for d in self.centro.documentos.filter(**self._filtro)
                if (d.publico and d.estado_documental != 'borrador') or self.gestor
                or (self.escenario and d.es_muestra)]

    @cached_property
    def articulaciones(self):
        return list(self.centro.articulaciones.all())

    @cached_property
    def relaciones(self):
        return list(self.centro.relaciones_areas.select_related('origen', 'destino'))

    @cached_property
    def gobierno(self):
        return list(self.centro.gobierno.all())

    @cached_property
    def ruta(self):
        return list(self.centro.ruta.all())

    @cached_property
    def modalidades(self):
        return list(self.centro.modalidades.all())

    @cached_property
    def fases(self):
        return list(self.centro.fases.all())

    @cached_property
    def fase_actual(self):
        return next((f for f in reversed(self.fases) if f.estado == 'en_curso'), None)

    @cached_property
    def indicadores(self):
        filas = list(self.centro.indicadores.all())
        for indicador in filas:
            # Un conteo vacío vale cero; una medición manual ausente sigue pendiente.
            indicador.calculado = indicador.calculo in CALCULOS
            if indicador.calculado:
                indicador.valor, indicador.actualizado = CALCULOS[indicador.calculo](self), self.hoy
        return filas

    @cached_property
    def indicadores_medidos(self):
        return [i for i in self.indicadores if i.valor is not None]

    @cached_property
    def riesgos(self):
        return list(self.centro.riesgos.all())

    @cached_property
    def ajustes(self):
        return {a.clave: a for a in self.centro.ajustes.all()}

    @cached_property
    def carpetas_propias(self):
        return [c for c in self.centro.carpetas.filter(activa=True).prefetch_related('recursos')
                if c.visibilidad == 'publica' or self.gestor]

    @property
    def roles(self):
        from .models import Integrante
        return Integrante.ROLES

    @property
    def _tipos_resultado(self):
        from .models import Resultado
        return Resultado

    @cached_property
    def alertas_investigacion(self):
        from .investigacion import alertas_del_centro
        return alertas_del_centro(self.centro, self.hoy) if self.gestor else []

    # ------------------------------------------------------------------ lo que cuenta cada sección
    @cached_property
    def consulta_proyectos(self):
        from .selectors_cientificos import proyectos_publicos
        return proyectos_publicos(self.centro)

    def consulta_resultados(self, catalogo):
        from .selectors_cientificos import resultados_publicos
        return resultados_publicos(self.centro, catalogo)

    @cached_property
    def resumen_proyectos(self):
        from .selectors_cientificos import cifras_proyectos
        return cifras_proyectos(self.centro)

    @cached_property
    def resumen_produccion(self):
        from .selectors_cientificos import cifras_resultados
        return cifras_resultados(self.centro, 'produccion')

    @cached_property
    def resumen_desarrollos(self):
        from .selectors_cientificos import cifras_resultados
        return cifras_resultados(self.centro, 'desarrollos')

    def cifras_cientificas(self, clave):
        if clave == 'proyectos':
            r = self.resumen_proyectos
            return [(r['total'], 'Proyectos en la cartera', 'fas fa-folder-open'),
                    (r['activos'], 'En curso', 'fas fa-rocket'),
                    (r['concluidos'], 'Concluidos o transferidos', 'fas fa-flag-checkered'),
                    (r['financiados'], 'Con financiamiento', 'fas fa-coins')]
        if clave == 'produccion':
            r = self.resumen_produccion
            return [(r['total'], 'Productos científicos', 'fas fa-book-open'),
                    (r['tipos'], 'Tipos de producto', 'fas fa-layer-group'),
                    (r['anios'], 'Años con producción', 'fas fa-calendar')]
        r = self.resumen_desarrollos
        return [(r['prototipos'], 'Prototipos y desarrollos', 'fas fa-cogs'),
                (r['propiedad'], 'Registros de propiedad intelectual', 'fas fa-certificate'),
                (r['trl'], 'Nivel de madurez más alto (TRL)', 'fas fa-signal')]

    def por_rol(self, *roles):
        return [p for p in self.integrantes if p.rol in roles]

    @property
    def investigadores(self):
        return self.por_rol('investigador', 'asociado')

    @property
    def proyectos_activos(self):
        return [p for p in self.proyectos if p.activo]

    @property
    def produccion(self):
        return [r for r in self.resultados if r.tipo in self._tipos_resultado.CIENTIFICOS]

    @property
    def desarrollos(self):
        return [r for r in self.resultados if r.tipo in self._tipos_resultado.INNOVACION]

    @property
    def unidades_vinculadas(self):
        """Los identificadores de las unidades vinculadas, desde la articulación y desde cada área."""
        vistos, slugs = set(), []
        for slug in ([a.unidad_slug for a in self.articulaciones if a.unidad_slug]
                     + [slug for area in self.areas for slug in area.lista_unidades]):
            if slug and slug not in vistos:
                vistos.add(slug)
                slugs.append(slug)
        return slugs

    def documentos_de(self, *tipos):
        return [d for d in self.documentos if d.tipo in tipos]

    @property
    def eventos_proximos(self):
        return [n for n in self.novedades if n.proximo]

    @cached_property
    def en_ejecucion(self):
        """Cuántas solicitudes de servicio están en ejecución; solo el número, nunca quién los pidió."""
        return self.centro.solicitudes.filter(tipo='servicio', estado='ejecucion').count()

    def tiene(self, clave):
        """Si la sección tiene algo que mostrar al público."""
        centro = self.centro
        comprobaciones = {
            'presentacion': lambda: True,
            'ahora': lambda: bool(self.proyectos_activos or self.en_ejecucion or self.resultados or self.novedades
                          or self.convocatorias or (self.fase_actual and not centro.en_operacion)),
            'como_trabaja': lambda: bool(self.ruta or centro.etapas_cadena or self.modalidades),
            'gobierno': lambda: bool(self.gobierno or self.indicadores_medidos or self.riesgos
                             or self.documentos_de(*self._gob())),
            'documentos': lambda: True,  # Siempre ofrece la ficha PDF generada desde los registros del centro.
            'areas': lambda: bool(self.areas or self.zonas or self.planos or centro.recorrido_360_url),
            'relaciones': lambda: bool(self.relaciones),
            'vinculadas': lambda: bool(self.unidades_vinculadas),
            'direccion': lambda: bool(self.por_rol('director', 'comite')),
            'investigadores': lambda: bool(self.investigadores),
            'grupos': lambda: bool(self.grupos or [a for a in self.articulaciones if a.tipo in ('carrera', 'futura')]),
            'personal': lambda: bool(self.por_rol('tecnico', 'visitante', 'tesista', 'estudiante')),
            'lineas': lambda: bool(self.lineas),
            'proyectos': lambda: self.consulta_proyectos.exists(),
            'produccion': lambda: self.consulta_resultados('produccion').exists(),
            'desarrollos': lambda: self.consulta_resultados('desarrollos').exists(),
            'casos': lambda: bool(self.casos),
            'alianzas': lambda: bool(self.aliados or [a for a in self.articulaciones if a.tipo == 'externo']
                             or [p for p in self.proyectos if p.financiador]),
            'portafolio': lambda: bool(self.servicios),
            'solicitar': lambda: True,
            'visitas': lambda: bool(centro.visitas_texto),
            'oportunidades': lambda: bool(self.convocatorias or self.oferta_vinculada['cursos']),
            'recursos': lambda: bool(self.zonas or self.herramientas or self.oferta_vinculada['unidades'] or self.areas),
        }
        comprobar = comprobaciones.get(clave)
        return bool(comprobar and comprobar())

    @cached_property
    def oferta_vinculada(self):
        from .vinculos import oferta_vinculada
        return oferta_vinculada(self.unidades_vinculadas)

    def _gob(self):
        from .models import DocumentoCentro
        return DocumentoCentro.GOBIERNO

    def _documentales(self):
        """Los documentos de «Documentos y normativa»: todos menos los de gobierno, que viven en su sección."""
        from .models import DocumentoCentro
        return DocumentoCentro.NORMATIVA + ('proyecto', 'otro')

    @cached_property
    def estructura_areas(self):
        """Jerarquía pública desde la colección ya cargada; no consulta cada padre."""
        visibles = {a.pk: a for a in self.areas}
        principales, modulos = [], {}
        for area in self.areas:
            padre = visibles.get(area.integrado_en_id)
            if padre and padre.pk != area.pk and not padre.integrado_en_id:
                modulos.setdefault(padre.pk, []).append(area)
            else:
                principales.append(area)
        return [(area, modulos.get(area.pk, [])) for area in principales]

    def modulos_de(self, area):
        return next((modulos for principal, modulos in self.estructura_areas if principal.pk == area.pk), [])

    def areas_por_tipo(self):
        """Áreas principales por función; los módulos se presentan dentro de su plataforma."""
        return list(_agrupar([area for area, _ in self.estructura_areas], lambda a: a.tipo_plural).items())

    def _carpetas(self, pestana, seccion):
        return [c for c in self.carpetas_propias if c.pestana == pestana and c.seccion == seccion]

    def completar(self, clave):
        """El panel donde el gestor completa una sección."""
        return self._admin(ADMIN_SECCION.get(clave, 'centroid'))

    def _admin(self, nombre):
        """Compatibilidad con el árbol existente: siempre apunta al gestor propio."""
        return url_edicion(self.centro, nombre)

    def nueva_carpeta(self, pestana, seccion=''):
        """Nueva carpeta en el modal del centro, con su pestaña y sección propuestas."""
        if not self.gestor:
            return ''
        return url_edicion(self.centro, 'carpetacentro', 'nuevo', pestana=pestana, seccion=seccion)

    # ------------------------------------------------------------------ las cifras vivas
    def cifras(self, cuantas=4):
        """Las cifras de investigación primero; si valen cero, las de estructura. Nunca metros cuadrados."""
        anio = self.hoy.year
        candidatas = [
            ('proyectos', len(self.proyectos_activos), 'Proyectos en curso', 'fas fa-rocket'),
            ('investigadores', len(self.investigadores), 'Investigadores', 'fas fa-user-graduate'),
            ('resultados', len([r for r in self.resultados if r.anio == anio]), f'Resultados en {anio}', 'fas fa-book-open'),
            ('atendidos', self.centro.solicitudes.filter(tipo='servicio', estado__in=('entregada', 'cerrada')).count(),
             'Servicios atendidos (histórico)', 'fas fa-check-double'),
            ('aliados', len(self.aliados_vigentes), 'Alianzas con vigencia documentada', 'fas fa-handshake'),
        ]
        investigacion = [{'clave': c, 'valor': v, 'titulo': t, 'icono': i} for c, v, t, i in candidatas if v]
        estructura = [cifra for cifra in self.cifras_capacidades() if cifra['valor']]
        return (investigacion + estructura)[:cuantas]

    @cached_property
    def informacion_general(self):
        """Ficha lateral pública; reutiliza los registros consultados por el árbol."""
        return {
            'adscripcion': self.centro.adscripcion if self.centro.identidad_validada or self.escenario else '',
            'direccion': next(iter(self.por_rol('director')), None),
            'carreras': list(dict.fromkeys(a.actor.strip() for a in self.articulaciones
                                         if a.tipo == 'carrera' and a.actor.strip())),
            'cifras': self.cifras_capacidades(),
            'editar_url': url_edicion(self.centro) if self.gestor else '',
        }

    def cifras_capacidades(self):
        """Cuatro medidas comparables para todo centro, incluso cuando un conteo es cero."""
        filas = [
            ('areas', len(self.areas), 'Áreas del centro', 'fas fa-th-large'),
            ('servicios', len(self.servicios), 'Servicios en el portafolio', 'fas fa-concierge-bell'),
            ('vinculadas', len(self.unidades_vinculadas), 'Unidades vinculadas', 'fas fa-link'),
            ('lineas', len(self.lineas), 'Líneas de investigación', 'fas fa-compass'),
        ]
        return [{'clave': c, 'valor': v, 'titulo': t, 'icono': i} for c, v, t, i in filas]

    # ------------------------------------------------------------------ las carpetas de cada pestaña
    def carpetas(self, solo_pestana=None):
        """{pestaña: [secciones]} con las secciones del mapa que tienen contenido y las carpetas propias.

        Cada sección trae sus archivos directos (`botones`) y sus carpetas (`grupos`), que el panel dibuja como un
        árbol; las carpetas propias del centro dentro de una sección son grupos más, y las que no cuelgan de ninguna
        sección son secciones nuevas de la pestaña. Las secciones son las mismas para todo centro.
        """
        slug = self.centro.slug
        resultado = {}
        for clave_pestana, pestana in MAPA.pestanas.items():
            if solo_pestana is not None and clave_pestana != solo_pestana:
                continue
            lista = []
            for seccion in pestana['secciones']:
                ajuste = self.ajustes.get(seccion['clave'])
                if ajuste and ajuste.oculta:
                    continue
                pendiente = not self.tiene(seccion['clave'])
                if pendiente and not self.gestor:
                    continue
                botones, grupos = ([], []) if pendiente else self._contenido(seccion['clave'])
                grupos += [self._grupo_propio(carpeta) for carpeta in self._carpetas(clave_pestana, seccion['clave'])]
                url = reverse('seccion_centro_id', args=[slug, seccion['clave']])
                # La página de la sección es la puerta; lo que se cuenta son sus archivos y los de sus carpetas.
                archivos = [boton for boton in botones if boton['url'] != url]
                lista.append({
                    'id': f'Seccion_{seccion["clave"]}', 'clave': seccion['clave'],
                    'titulo': ajuste.titulo if ajuste and ajuste.titulo else seccion['titulo'],
                    'icono': seccion['icono'], 'url': url,
                    'botones': botones, 'grupos': grupos,
                    'total': len(archivos) + sum(len(grupo['botones']) for grupo in grupos),
                    'directa': not pendiente and not grupos and not archivos and len(botones) == 1,
                    'pendiente': pendiente, 'propia': False, 'interna': False, 'descripcion': '',
                    'completar': self.completar(seccion['clave']) if pendiente else '',
                    'nueva_carpeta': self.nueva_carpeta(clave_pestana, seccion['clave']),
                })
            for carpeta in self._carpetas(clave_pestana, ''):
                lista.append(self._seccion_propia(carpeta))
            resultado[clave_pestana] = lista
        return resultado

    def _recursos_de(self, carpeta):
        url = reverse('carpeta_centro_id', args=[self.centro.slug, carpeta.pk])
        return [_boton(f'recurso-{r.pk}', r.titulo, f'{url}?recurso={r.pk}', _icono_recurso(r), r.descripcion,
                       r.get_tipo_display()) for r in carpeta.recursos.all() if r.activo]

    def _grupo_propio(self, carpeta):
        return _grupo(f'carpeta-{carpeta.pk}', carpeta.nombre, self._recursos_de(carpeta), carpeta.icono,
                      reverse('carpeta_centro_id', args=[self.centro.slug, carpeta.pk]), propia=True)

    def _seccion_propia(self, carpeta):
        botones = self._recursos_de(carpeta)
        return {
            'id': f'Carpeta{carpeta.pk}', 'clave': f'carpeta-{carpeta.pk}', 'titulo': carpeta.nombre,
            'icono': carpeta.icono, 'url': reverse('carpeta_centro_id', args=[self.centro.slug, carpeta.pk]),
            'botones': botones, 'grupos': [], 'total': len(botones), 'directa': False,
            'pendiente': False, 'propia': True, 'interna': carpeta.visibilidad != 'publica',
            'descripcion': carpeta.descripcion, 'completar': '', 'nueva_carpeta': '',
        }

    def _contenido(self, clave):
        """Lo que cuelga de una sección en el panel: solo lo esencial. La mayoría es una sola página que se abre directo;
        despliegan elementos la presentación (con su identidad y su ubicación), los documentos (cada PDF), las áreas
        (cada una abre su página con todo lo que hace; el edificio que las aloja está en la página de todas).
        Nunca un salto a una parte de la misma página: eso vive dentro de ella."""
        slug = self.centro.slug
        seccion = reverse('seccion_centro_id', args=[slug, clave])
        datos = MAPA.seccion(clave)
        titulo, icono = datos['titulo'], datos['icono']

        def pagina(identificador, nombre, detalle=''):
            return _boton(identificador, nombre, seccion, icono, detalle)

        def subpagina(clave_sub):
            datos = SUBPAGINAS[clave_sub]
            return _boton(clave_sub, datos['titulo'], reverse('seccion_centro_id', args=[slug, clave_sub]), datos['icono'],
                          datos['detalle'])

        if clave == 'presentacion':
            return [pagina('presentacion', titulo, 'Qué es el centro, sus cifras, sus objetivos y sus áreas'),
                    subpagina('identidad'), subpagina('ubicacion')], []
        if clave == 'documentos':
            return [pagina('documentos', titulo, 'Los documentos y las normas con las que trabaja el centro')] + [
                _boton(f'documento-{d.pk}', d.titulo, d.url or seccion, d.icono, d.resumen, d.periodo or d.get_tipo_display(),
                       externo=bool(d.url) and not d.archivo) for d in self.documentos_de(*self._documentales())], []
        if clave == 'areas':
            botones = [pagina('areas', 'Todas las áreas', 'Tecnologías, plataformas, módulos integrados y sistemas de apoyo')]
            for principal, modulos in self.estructura_areas:
                for area in (principal, *modulos):
                    boton = _boton(f'area-{area.codigo}', _nombre(area),
                        reverse('componente_centro_id', args=[slug, area.codigo]), area.icono,
                        area.resumen, area.get_tipo_display(), imagen=_portada(area))
                    boton.update(grupo=principal.tipo_plural, integrado=area.pk != principal.pk,
                                 contenedor=_nombre(principal) if area.pk != principal.pk else '')
                    botones.append(boton)
            return botones, []
        detalles = {
            'ahora': 'Proyectos en marcha, novedades, eventos y convocatorias',
            'como_trabaja': 'La ruta del reto a la solución, la cadena integrada y las modalidades',
            'gobierno': 'Quién dirige, qué mide y qué riesgos controla',
            'relaciones': 'Qué entrega cada área a las demás',
            'vinculadas': 'Los laboratorios, plantas y observatorios con los que se articula',
            'lineas': 'Los retos y las líneas con sus proyectos',
            'proyectos': 'La cartera de proyectos con su estado y su avance',
            'produccion': 'Informes, datos, software, métodos y tesis',
            'desarrollos': 'Prototipos y propiedad intelectual con su madurez',
            'casos': 'Lo que cambió gracias al centro',
            'alianzas': 'Con quién coopera y cómo se financia',
            'direccion': 'Quién dirige el centro y quiénes evalúan sus proyectos',
            'investigadores': 'Quienes investigan en el centro, con sus líneas',
            'grupos': 'Los grupos y las carreras que participan',
            'personal': 'Quienes operan las áreas y quienes se forman en ellas',
            'portafolio': 'Cada servicio con lo que incluye y lo que entrega',
            'solicitar': 'La ruta para proponer un reto o pedir un servicio, y el estado de tus solicitudes',
            'visitas': 'Qué se recorre, para quién y cómo se pide',
            'oportunidades': 'Temas de tesis, pasantías y convocatorias abiertas',
        }
        return [pagina(clave, titulo, detalles.get(clave, ''))], []

    def _publicos(self):
        from .models import Integrante
        return Integrante.PUBLICOS


def _agrupar(filas, clave):
    grupos = {}
    for fila in filas:
        grupos.setdefault(clave(fila), []).append(fila)
    return grupos


def _portada(area):
    imagen = next((i for i in area.imagenes.all() if not i.es_plano), None)
    return imagen.imagen.url if imagen else ''


def _icono_recurso(recurso):
    return {'archivo': 'fas fa-file-pdf' if recurso.es_pdf else 'fas fa-file', 'enlace': 'fas fa-external-link-alt',
            'video': 'fab fa-youtube', 'texto': 'fas fa-align-left'}.get(recurso.tipo, 'fas fa-file')
