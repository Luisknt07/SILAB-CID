"""«Contenidos de la ficha»: el árbol del menú público de una unidad, para ordenarlo sin adivinar.

Pestaña → sección (en las plantas piloto, las 33 comunes, que la plataforma llena
sola con sus datos) → carpetas propias → archivos. Cada sección dice dónde se edita
lo que muestra, con el enlace al bloque exacto; lo que no llega a ninguna parte se
reúne arriba para darle destino. Desde aquí se renombran u ocultan pestañas y
secciones, y se crean, ordenan, editan, mueven, ocultan o eliminan las carpetas
propias. Las subcarpetas automáticas (cada área en las fichas de equipo, el escáner…)
y cada elemento automático se renombran, ordenan u ocultan sin tocar el registro de
origen. Junto a las pestañas comunes de su tipo, la unidad crea pestañas propias, que
se eliminan cuando quedan vacías. Los archivos se suben en el editor de la unidad.
"""
import re

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.text import slugify

from apps.formacion.presentation.aula import ajustar_grupos, carpetas_del_aula, procesos_publicos
from apps.gestion_unidades.presentation.rutas_ficha import CABECERA, CAMPOS_DE_NAVEGACION, CARPETAS, MENU, SECCIONES_DE_EXPEDIENTE, SECCIONES_DEL_PANEL, ancla_de_bloque, campos_planos, partes_de, partes_de_bloque, partes_de_campos, ruta_de_carpeta, ruta_del_archivo
from apps.plantas_piloto.operacion.presentation.secciones_plantas import ajustes_de, mapa_de, seccion_de
from apps.gestion_unidades.presentation.secciones_propias import crear_seccion, numero_de
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.gestion_unidades.models.secciones_propias import SeccionPropia
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.recursos import VISIBILIDADES_CONTENIDO

VISIBILIDADES = dict(VISIBILIDADES_CONTENIDO)


def nombre_de_la_vista(modelo_admin):
    opciones = modelo_admin.model._meta
    return f'{opciones.app_label}_{opciones.model_name}_contenidos'


def url_contenidos(modelo_admin, unidad):
    return reverse(f'admin:{nombre_de_la_vista(modelo_admin)}', args=[unidad.pk])


def _mapa(unidad):
    """El mapa de secciones del tipo de la unidad; None en centros y observatorios."""
    return mapa_de(unidad)


# --------------------------------------------------------------------- el árbol
def _cuenta(total, singular, plural):
    return f'{total} {singular if total == 1 else plural}'


def _archivos(unidad):
    return (
        Recurso.objects.filter(unidad=unidad, informe_mejora__isnull=True, documentos_expediente__isnull=True)
        .exclude(carpeta__del_expediente=True)
        .select_related('carpeta__carpeta_padre__modulo_config', 'carpeta__modulo_config', 'ficha')
        .prefetch_related('artefactos_externos', 'artefactos_validados')
        .order_by('orden', 'nombre', 'pk')
    )


def _carpetas_raiz(unidad, archivos):
    """Las carpetas propias de la unidad en sus dos niveles, cada una con sus archivos."""
    carpetas = list(
        CarpetaRecurso.objects.filter(unidad=unidad, del_expediente=False)
        .select_related('modulo_config', 'ficha', 'carpeta_padre__modulo_config').order_by('orden', 'nombre', 'pk')
    )
    por_carpeta = {}
    for recurso in archivos:
        por_carpeta.setdefault(recurso.carpeta_id, []).append(recurso)
    for carpeta in carpetas:
        carpeta.archivos = por_carpeta.get(carpeta.pk, [])
        carpeta.hijas = [hija for hija in carpetas if hija.carpeta_padre_id == carpeta.pk]
        carpeta.vacia = not carpeta.archivos and not carpeta.hijas
        carpeta.rotulo_visibilidad = VISIBILIDADES.get(carpeta.visibilidad, carpeta.visibilidad)
        carpeta.destino = f's:{carpeta.seccion_planta}' if carpeta.seccion_planta else f'm:{carpeta.modulo_config_id}'
        # Adónde vuelve la página tras actuar: a la carpeta o, si se elimina, a lo que la contiene.
        carpeta.ancla = f'carpeta-{carpeta.pk}'
        if carpeta.carpeta_padre_id:
            carpeta.ancla_superior = f'carpeta-{carpeta.carpeta_padre_id}'
        elif carpeta.seccion_planta:
            carpeta.ancla_superior = 'seccion-' + carpeta.seccion_planta.replace('.', '-')
        else:
            carpeta.ancla_superior = f'pestana-{carpeta.modulo_config_id}'
    return [carpeta for carpeta in carpetas if not carpeta.carpeta_padre_id]


def _marcar_extremos(carpetas):
    """La primera no sube y la última no baja: el orden se cambia entre hermanas."""
    for indice, carpeta in enumerate(carpetas):
        carpeta.primera, carpeta.ultima = indice == 0, indice == len(carpetas) - 1
        _marcar_extremos(carpeta.hijas)


def _clave_foranea(instancia):
    return next(campo for campo in instancia.model._meta.fields
                if campo.is_relation and campo.related_model is Unidad
                and campo.name == (instancia.fk_name or campo.name))


def _estado(consulta):
    """Cuántos registros tiene un bloque y cuántos se ven, si el bloque decide qué se publica."""
    total = consulta.count()
    if not total:
        return 'Sin registros'
    campos = {campo.name for campo in consulta.model._meta.fields}
    visible = next((campo for campo in ('publicada', 'publicado', 'publico', 'activo', 'activa') if campo in campos), None)
    if visible is None:
        return _cuenta(total, 'registro', 'registros')
    visibles = consulta.filter(**{visible: True}).count()
    if total == 1:
        return 'Visible' if visibles else 'Oculto: todavía no se ve'
    return f'{visibles} de {total} visibles'


def _fuentes(modelo_admin, request, unidad, mapa, editor_url):
    """Por parte de la ficha, dónde se edita lo que muestra; con la clave vacía, los bloques de uso interno."""
    from apps.gestion_unidades.admin.tablero_unidad import fila_de_expediente
    fuentes = {}

    def sumar(partes, fuente):
        for parte in partes or ('',):
            fuentes.setdefault(parte, []).append(fuente)

    for nombre, opciones in modelo_admin.bloques_de_campos(request, unidad):
        campos = set(campos_planos(opciones.get('fields', ())))
        if nombre and not campos <= CAMPOS_DE_NAVEGACION:
            sumar(partes_de_campos(campos, mapa), {'nombre': nombre, 'url': f'{editor_url}#{ancla_de_bloque(nombre)}',
                                                   'tipo': 'editor', 'donde': 'Editor de la unidad'})
    for instancia in modelo_admin.get_inline_instances(request, unidad):
        partes = partes_de_bloque(instancia.model.__name__, mapa)
        if MENU in partes or CARPETAS in partes:
            continue
        clave = _clave_foranea(instancia)
        prefijo = clave.remote_field.get_accessor_name(model=instancia.model).replace('+', '')
        sumar(partes, {
            'nombre': str(type(instancia).verbose_name_plural or instancia.model._meta.verbose_name_plural),
            'url': f'{editor_url}#{prefijo}-group', 'tipo': 'editor', 'donde': 'Editor de la unidad',
            'estado': _estado(instancia.model._default_manager.filter(**{clave.name: unidad})),
        })
    for nombre, claves in SECCIONES_DE_EXPEDIENTE.items():
        partes = partes_de(claves, mapa)
        fila = fila_de_expediente(request, unidad, mapa.app_label, nombre) if partes else None
        if fila:
            sumar(partes, {'nombre': fila['nombre'], 'url': fila['lista'], 'nuevo': fila['nuevo'],
                           'tipo': 'expediente', 'donde': 'Plantas piloto',
                           'estado': _cuenta(fila['total'], 'registro', 'registros')})
    for vista, (nombre, claves) in SECCIONES_DEL_PANEL.items():
        vigentes = RequisitoAcceso.objects.filter(unidad=unidad, activo=True).count()
        sumar(partes_de(claves, mapa), {'nombre': nombre, 'url': reverse('gestion_unidad', args=[unidad.slug]) + f'?view={vista}',
                       'tipo': 'panel', 'donde': 'Panel de la planta', 'estado': _cuenta(vigentes, 'vigente', 'vigentes')})
    return fuentes


def _que_falta(recurso):
    """Lo que le falta a un archivo sin carpeta para entrar al repositorio de la ficha."""
    falta = []
    if recurso.estado != 'vigente':
        falta.append('estar vigente')
    if not recurso.seguridad_verificada:
        falta.append('la verificación de seguridad')
    if not recurso.metadatos_completos:
        falta.append('descripción y tipo')
    return falta


def _por_que_no_se_ve(carpeta, mapa):
    if carpeta.modulo_config_id is None:
        return 'No tiene pestaña: no aparece en la ficha.'
    if mapa and not carpeta.seccion_planta:
        return 'No tiene sección: en esta unidad, cada carpeta va dentro de una sección numerada.'
    return 'Su sección no corresponde a su pestaña.'


def _grupos_del_organizador(aula, numero):
    """Las subcarpetas automáticas de una sección, en su orden, con lo necesario para ajustarlas."""
    if aula is None or aula.get('pendiente'):
        return []
    grupos = aula['grupos']
    orden = ','.join(grupo['clave'] for grupo in grupos)
    for indice, grupo in enumerate(grupos):
        grupo.update(
            primera=indice == 0, ultima=indice == len(grupos) - 1, orden_actual=orden,
            ancla='grupo-' + re.sub('[^a-z0-9-]', '-', f'{numero}-{grupo["clave"]}'.replace('.', '-')),
            visibles=sum(1 for boton in grupo['botones'] if not boton['oculto']),
        )
    return grupos


def _es_comun(modulo, mapa):
    """Las pestañas comunes del tipo de unidad se conservan: se renombran u ocultan, no se eliminan."""
    return mapa is not None and modulo.clave in mapa.pestanas


def _pestana_eliminable(unidad, modulo, mapa):
    return not (_es_comun(modulo, mapa) or modulo.mostrar_herramientas_reserva
                or modulo.clave == 'informacion-general'
                or CarpetaRecurso.objects.filter(unidad=unidad, modulo_config=modulo).exists()
                or SeccionPropia.objects.filter(modulo=modulo).exists())


def _propias_de(unidad, modulo, mapa):
    """Las secciones con plantilla de una pestaña, en su orden, con lo que el organizador muestra de cada una."""
    propias = list(SeccionPropia.objects.filter(modulo=modulo).select_related('modulo').order_by('orden', 'pk'))
    for indice, propia in enumerate(propias):
        elementos = list(propia.elementos.values_list('es_ejemplo', flat=True))
        propia.total, propia.muestras = len(elementos), sum(elementos)
        propia.eliminable = propia.total == propia.muestras
        propia.primera, propia.ultima = indice == 0, indice == len(propias) - 1
        propia.numero = numero_de(propia, mapa)
        propia.url = reverse('seccion_propia', args=[unidad.slug, propia.pk])
    return propias


def arbol(modelo_admin, request, unidad, editor_url):
    """Lo que dibuja la página: pestañas con sus secciones y carpetas, y lo que quedó sin ruta."""
    mapa = _mapa(unidad)
    modulos = list(ModuloUnidad.objects.filter(unidad=unidad).order_by('orden', 'pk'))
    ajustes = ajustes_de(unidad) if mapa else {}
    ocultas = {numero for numero, ajuste in ajustes.items() if ajuste.oculta}
    archivos = list(_archivos(unidad))
    for recurso in archivos:
        recurso.ruta = ruta_del_archivo(recurso, ajustes, mapa, ocultas)
        recurso.falta = _que_falta(recurso)
    raices = _carpetas_raiz(unidad, archivos)
    automatico, fuentes = {}, {}
    if mapa:
        activos = [modulo for modulo in modulos if modulo.activo]
        # Todas las secciones, también las ocultas, con sus subcarpetas y elementos ocultos marcados.
        automatico = {
            carpeta['numero']: ajustar_grupos(carpeta, ajustes.get(carpeta['numero']), con_ocultos=True)
            for carpeta in carpetas_del_aula(unidad, activos, procesos_publicos(unidad, request.user), request.user)
            if carpeta['seccion']
        }
        fuentes = _fuentes(modelo_admin, request, unidad, mapa, editor_url)
    ubicadas = set()
    pestanas = []
    for modulo in modulos:
        pestana = {'modulo': modulo, 'ancla': f'pestana-{modulo.pk}', 'destino': f'm:{modulo.pk}', 'comun': '',
                   'secciones': [], 'carpetas': [], 'propia': mapa is not None and not _es_comun(modulo, mapa),
                   'eliminable': _pestana_eliminable(unidad, modulo, mapa), 'propias': _propias_de(unidad, modulo, mapa)}
        if _es_comun(modulo, mapa):
            pestana['comun'] = mapa.pestanas[modulo.clave][0]
            for numero, comun in mapa.pestanas[modulo.clave][1]:
                propias = [c for c in raices if c.seccion_planta == numero and c.modulo_config_id == modulo.pk]
                ubicadas.update(c.pk for c in propias)
                aula = automatico.get(numero)
                ajuste = ajustes.get(numero)
                pestana['secciones'].append({
                    **seccion_de(numero, ajustes, mapa),
                    'ancla': 'seccion-' + numero.replace('.', '-'),
                    'destino': f's:{numero}',
                    'comun': comun,
                    'origen': mapa.origen[numero],
                    'automatico': None if aula is None else (0 if aula.get('pendiente') else aula['total']),
                    'carpetas': propias,
                    'fuentes': fuentes.get(numero, []),
                    'grupos': _grupos_del_organizador(aula, numero),
                    'ajustada': bool(ajuste and (ajuste.grupos or ajuste.elementos_ocultos)),
                })
                _marcar_extremos(propias)
        else:
            # Sin mapa, o una pestaña propia junto a las comunes: sus carpetas van directo en ella.
            pestana['carpetas'] = [c for c in raices if c.modulo_config_id == modulo.pk and not c.ficha_id
                                   and (mapa is None or not c.seccion_planta)]
            ubicadas.update(c.pk for c in pestana['carpetas'])
            _marcar_extremos(pestana['carpetas'])
        pestanas.append(pestana)
    en_fichas = [c for c in raices if c.ficha_id and c.pk not in ubicadas]
    sin_ubicar = [c for c in raices if not c.ficha_id and c.pk not in ubicadas]
    for carpeta in sin_ubicar:
        carpeta.motivo = _por_que_no_se_ve(carpeta, mapa)
    _marcar_extremos(en_fichas)
    _marcar_extremos(sin_ubicar)
    # Los archivos de una carpeta sin ubicar se ven dentro de ella; aquí, los que no tienen ninguna.
    sueltos = [recurso for recurso in archivos if not recurso.ruta['lugares'] and not recurso.carpeta_id]
    # Las carpetas a las que se puede llevar un archivo suelto: las que llegan a la ficha.
    con_ruta = [(carpeta.pk, ruta) for raiz in raices for carpeta in (raiz, *raiz.hijas)
                if (ruta := ruta_de_carpeta(carpeta, ajustes, mapa))]
    if mapa:
        claves = {modulo.clave: modulo for modulo in modulos}
        destinos = [
            (f's:{numero}', f"{numero} {seccion_de(numero, ajustes, mapa)['titulo']}")
            for numero, seccion in mapa.secciones.items() if seccion['modulo'] in claves
        ] + [(f'm:{modulo.pk}', f'{modulo.nombre} (pestaña propia)') for modulo in modulos
             if not _es_comun(modulo, mapa)]
    else:
        destinos = [(f'm:{modulo.pk}', modulo.nombre) for modulo in modulos]
    return {
        'es_planta': mapa is not None,
        'tipo_unidad': {'plantas_piloto': 'planta', 'observatorios': 'observatorio'}.get(getattr(mapa, 'tipo', ''),
                                                                                         'laboratorio'),
        'total_secciones': len(mapa.secciones) if mapa else 0,
        'pestanas': pestanas,
        'en_fichas': en_fichas,
        'sin_ubicar': sin_ubicar,
        'archivos_sin_ruta': sueltos,
        'total_sin_ruta': len(sueltos) + len(sin_ubicar),
        'carpetas_con_ruta': con_ruta,
        'cabecera': fuentes.get(CABECERA, []),
        'internos': fuentes.get('', []),
        'destinos': destinos,
        'visibilidades': VISIBILIDADES_CONTENIDO,
        'plantillas_seccion': SeccionPropia.PLANTILLAS,
        'faltantes': [titulo for clave, (titulo, _) in (mapa.pestanas.items() if mapa else ())
                      if clave not in {modulo.clave for modulo in modulos}],
    }


# ------------------------------------------------------------------ las acciones
def _nombre(datos, largo=120):
    nombre = ' '.join((datos.get('nombre') or '').split())
    if not nombre:
        raise ValidationError('Escriba un nombre.')
    if len(nombre) > largo:
        raise ValidationError(f'El nombre admite hasta {largo} caracteres.')
    return nombre


def _modulo(unidad, datos):
    return get_object_or_404(ModuloUnidad, unidad=unidad, pk=datos.get('modulo') or 0)


def _carpeta(unidad, datos):
    return get_object_or_404(CarpetaRecurso, unidad=unidad, del_expediente=False, pk=datos.get('carpeta') or 0)


CLAVE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')


def _clave(datos, campo):
    valor = (datos.get(campo) or '').strip()
    if not CLAVE.match(valor):
        raise ValidationError('Ese elemento no existe en esta sección.')
    return valor


def _ajuste(unidad, numero):
    return AjusteSeccionPlanta.objects.filter(unidad=unidad, numero=numero).first() or AjusteSeccionPlanta(
        unidad=unidad, numero=numero)


def _decision(ajuste, clave):
    """Lo que la unidad decidió de una subcarpeta automática, para modificarlo."""
    ajuste.grupos = dict(ajuste.grupos or {})
    return ajuste.grupos.setdefault(clave, {})


def _numero(unidad, datos):
    numero = datos.get('numero', '')
    mapa = _mapa(unidad)
    if mapa is None or numero not in mapa.secciones:
        raise ValidationError('Esa sección no existe en esta unidad.')
    return numero


def _nombre_libre(unidad, nombre, carpeta=None):
    repetidas = CarpetaRecurso.objects.filter(unidad=unidad, nombre=nombre)
    if carpeta is not None:
        repetidas = repetidas.exclude(pk=carpeta.pk)
    if repetidas.exists():
        raise ValidationError(f'Ya hay una carpeta «{nombre}» en esta unidad: los nombres no se repiten, '
                              'aunque estén en secciones distintas.')


def _visibilidad(datos):
    visibilidad = datos.get('visibilidad', 'publica')
    if visibilidad not in VISIBILIDADES:
        raise ValidationError('Elija quién puede ver la carpeta.')
    return visibilidad


def _destino(unidad, destino):
    """Pestaña y sección que corresponden a un destino del selector («s:1.4» o «m:12»)."""
    tipo, _, valor = (destino or '').partition(':')
    mapa = _mapa(unidad)
    if tipo == 's' and mapa and valor in mapa.secciones:
        modulo = ModuloUnidad.objects.filter(unidad=unidad, clave=mapa.modulo_de(valor)).first()
        if modulo:
            return {'modulo_config': modulo, 'seccion_planta': valor, 'ficha': None}
    if tipo == 'm' and valor.isdigit():
        modulo = ModuloUnidad.objects.filter(unidad=unidad, pk=valor).first()
        if modulo and not _es_comun(modulo, mapa):
            return {'modulo_config': modulo, 'seccion_planta': '', 'ficha': None}
    raise ValidationError('Elija dónde va la carpeta.')


def _limpiar_ajuste(ajuste):
    """Un ajuste sin nombre propio, sección oculta ni decisiones sobre lo automático no ajusta nada: se borra."""
    ajuste.grupos = {clave: decision for clave, decision in (ajuste.grupos or {}).items() if decision}
    if ajuste.titulo or ajuste.oculta or ajuste.grupos or ajuste.elementos_ocultos:
        ajuste.save()
    elif ajuste.pk:
        ajuste.delete()


def renombrar_pestana(unidad, datos):
    modulo = _modulo(unidad, datos)
    anterior, modulo.nombre = modulo.nombre, _nombre(datos)
    modulo.save(update_fields=['nombre'])
    return f'La pestaña «{anterior}» ahora se llama «{modulo.nombre}».'


def alternar_pestana(unidad, datos):
    modulo = _modulo(unidad, datos)
    if modulo.activo and not ModuloUnidad.objects.filter(unidad=unidad, activo=True).exclude(pk=modulo.pk).exists():
        raise ValidationError('La ficha necesita al menos una pestaña visible.')
    modulo.activo = not modulo.activo
    modulo.save(update_fields=['activo'])
    if modulo.activo:
        return f'La pestaña «{modulo.nombre}» vuelve a mostrarse en la ficha.'
    return f'La pestaña «{modulo.nombre}» ya no se muestra en la ficha; todo lo suyo se conserva.'


def nueva_pestana(unidad, datos):
    nombre = _nombre(datos)
    orden = (ModuloUnidad.objects.filter(unidad=unidad).aggregate(Max('orden'))['orden__max'] or 0) + 1
    clave = ''
    if _mapa(unidad):
        # Junto a las comunes de su tipo, con una clave que nunca coincide con la de una común.
        base = f'propia-{slugify(nombre)[:60] or "pestana"}'
        clave, sufijo = base, 2
        while ModuloUnidad.objects.filter(unidad=unidad, clave=clave).exists():
            clave, sufijo = f'{base}-{sufijo}', sufijo + 1
    modulo = ModuloUnidad.objects.create(unidad=unidad, nombre=nombre, orden=orden, clave=clave)
    return f'Nueva pestaña «{modulo.nombre}», al final del menú.'


def eliminar_pestana(unidad, datos):
    modulo = _modulo(unidad, datos)
    if _es_comun(modulo, _mapa(unidad)) or modulo.clave == 'informacion-general':
        raise ValidationError('Las pestañas comunes de su tipo no se eliminan: se renombran u ocultan.')
    if modulo.mostrar_herramientas_reserva:
        raise ValidationError('La pestaña de reservas no se elimina: se puede ocultar.')
    if CarpetaRecurso.objects.filter(unidad=unidad, modulo_config=modulo).exists():
        raise ValidationError('Solo se elimina una pestaña vacía: mueva o elimine antes sus carpetas, '
                              'o simplemente ocúltela.')
    if modulo.activo and not ModuloUnidad.objects.filter(unidad=unidad, activo=True).exclude(pk=modulo.pk).exists():
        raise ValidationError('La ficha necesita al menos una pestaña visible.')
    modulo.delete()
    return f'Pestaña «{modulo.nombre}» eliminada.'


def renombrar_seccion(unidad, datos):
    numero = _numero(unidad, datos)
    nombre = _nombre(datos)
    ajuste = _ajuste(unidad, numero)
    ajuste.titulo = '' if nombre == _mapa(unidad).secciones[numero]['titulo'] else nombre
    _limpiar_ajuste(ajuste)
    return f'La sección {numero} ahora se llama «{nombre}».'


def alternar_seccion(unidad, datos):
    numero = _numero(unidad, datos)
    ajuste = _ajuste(unidad, numero)
    ajuste.oculta = not ajuste.oculta
    _limpiar_ajuste(ajuste)
    if ajuste.oculta:
        return f'La sección {numero} ya no se muestra en la ficha, con sus carpetas propias.'
    return f'La sección {numero} vuelve a mostrarse en la ficha.'


def restablecer_seccion(unidad, datos):
    numero = _numero(unidad, datos)
    AjusteSeccionPlanta.objects.filter(unidad=unidad, numero=numero).delete()
    return f'La sección {numero} recupera su nombre común, sus subcarpetas automáticas y se muestra.'


def renombrar_grupo(unidad, datos):
    numero, clave = _numero(unidad, datos), _clave(datos, 'grupo')
    nombre = ' '.join((datos.get('nombre') or '').split())
    comun = ' '.join((datos.get('comun') or '').split())
    if len(nombre) > 120:
        raise ValidationError('El nombre admite hasta 120 caracteres.')
    ajuste = _ajuste(unidad, numero)
    decision = _decision(ajuste, clave)
    if nombre and nombre != comun:
        decision['titulo'] = nombre
    else:
        decision.pop('titulo', None)
    _limpiar_ajuste(ajuste)
    if decision.get('titulo'):
        return f'La subcarpeta ahora se llama «{nombre}».'
    return 'La subcarpeta recupera su nombre común.'


def alternar_grupo(unidad, datos):
    numero, clave = _numero(unidad, datos), _clave(datos, 'grupo')
    ajuste = _ajuste(unidad, numero)
    decision = _decision(ajuste, clave)
    if decision.pop('oculta', False):
        _limpiar_ajuste(ajuste)
        return 'La subcarpeta vuelve a mostrarse en el menú.'
    decision['oculta'] = True
    _limpiar_ajuste(ajuste)
    return 'La subcarpeta ya no se muestra en el menú; sus áreas y equipos se conservan.'


def ordenar_grupo(unidad, datos):
    numero, clave = _numero(unidad, datos), _clave(datos, 'grupo')
    paso = {'subir': -1, 'bajar': 1}.get(datos.get('direccion'))
    orden = [valor for valor in (datos.get('orden') or '').split(',') if CLAVE.match(valor)]
    if paso is None or clave not in orden or len(set(orden)) != len(orden):
        raise ValidationError('Elija si la subcarpeta sube o baja.')
    indice = orden.index(clave)
    if not 0 <= indice + paso < len(orden):
        raise ValidationError(f'La subcarpeta ya está {"primera" if paso < 0 else "última"}.')
    orden[indice], orden[indice + paso] = orden[indice + paso], orden[indice]
    ajuste = _ajuste(unidad, numero)
    for posicion, valor in enumerate(orden):
        _decision(ajuste, valor)['orden'] = posicion
    _limpiar_ajuste(ajuste)
    return f'La subcarpeta {"sube" if paso < 0 else "baja"} un lugar.'


def alternar_elemento(unidad, datos):
    numero, elemento = _numero(unidad, datos), _clave(datos, 'elemento')
    nombre = ' '.join((datos.get('nombre') or elemento).split())[:200]
    ajuste = _ajuste(unidad, numero)
    ocultos = list(ajuste.elementos_ocultos or [])
    if elemento in ocultos:
        ocultos.remove(elemento)
        mensaje = f'«{nombre}» vuelve a mostrarse en el menú.'
    else:
        ocultos.append(elemento)
        mensaje = f'«{nombre}» ya no se muestra en el menú; el registro se conserva.'
    ajuste.elementos_ocultos = ocultos
    _limpiar_ajuste(ajuste)
    return mensaje


def crear_carpeta(unidad, datos):
    nombre = _nombre(datos, 255)
    _nombre_libre(unidad, nombre)
    if datos.get('padre'):
        padre = get_object_or_404(CarpetaRecurso, unidad=unidad, del_expediente=False, pk=datos['padre'])
        ubicacion = {'modulo_config': padre.modulo_config, 'seccion_planta': padre.seccion_planta,
                     'ficha': padre.ficha, 'carpeta_padre': padre}
    else:
        ubicacion = _destino(unidad, datos.get('destino'))
    hermanas = CarpetaRecurso.objects.filter(unidad=unidad, **ubicacion)
    carpeta = CarpetaRecurso(unidad=unidad, nombre=nombre, visibilidad=_visibilidad(datos),
                             orden=(hermanas.aggregate(Max('orden'))['orden__max'] or 0) + 1, **ubicacion)
    carpeta.full_clean(exclude=['modulo'])
    carpeta.save()
    return f'Carpeta «{nombre}» creada. Suba sus archivos en el editor de la unidad eligiendo esta carpeta.'


def editar_carpeta(unidad, datos):
    carpeta = _carpeta(unidad, datos)
    anterior = carpeta.nombre
    carpeta.nombre = _nombre(datos, 255)
    _nombre_libre(unidad, carpeta.nombre, carpeta)
    # Renombrar en la fila no envía la visibilidad: se conserva la que tiene.
    if 'visibilidad' in datos:
        carpeta.visibilidad = _visibilidad(datos)
    carpeta.save(update_fields=['nombre', 'visibilidad'])
    return f'Carpeta «{anterior}» actualizada.' if anterior == carpeta.nombre else (
        f'La carpeta «{anterior}» ahora se llama «{carpeta.nombre}».')


def mover_carpeta(unidad, datos):
    carpeta = _carpeta(unidad, datos)
    if carpeta.carpeta_padre_id:
        raise ValidationError('Una subcarpeta se mueve junto con su carpeta superior.')
    ubicacion = _destino(unidad, datos.get('destino'))
    for campo, valor in ubicacion.items():
        setattr(carpeta, campo, valor)
    carpeta.full_clean(exclude=['modulo'])
    carpeta.save()
    # Las subcarpetas viven en la misma sección que su carpeta superior.
    carpeta.subcarpetas.update(**ubicacion)
    return f'Carpeta «{carpeta.nombre}» movida, con sus subcarpetas y archivos.'


def ordenar_carpeta(unidad, datos):
    carpeta = _carpeta(unidad, datos)
    paso = {'subir': -1, 'bajar': 1}.get(datos.get('direccion'))
    if paso is None:
        raise ValidationError('Elija si la carpeta sube o baja.')
    hermanas = list(CarpetaRecurso.objects.filter(
        unidad=unidad, del_expediente=False, carpeta_padre=carpeta.carpeta_padre_id,
        modulo_config=carpeta.modulo_config_id, seccion_planta=carpeta.seccion_planta, ficha=carpeta.ficha_id,
    ).order_by('orden', 'nombre', 'pk'))
    indice = hermanas.index(carpeta)
    if not 0 <= indice + paso < len(hermanas):
        raise ValidationError(f'La carpeta «{carpeta.nombre}» ya está {"primera" if paso < 0 else "última"}.')
    hermanas[indice], hermanas[indice + paso] = hermanas[indice + paso], hermanas[indice]
    for orden, hermana in enumerate(hermanas, start=1):
        if hermana.orden != orden:
            hermana.orden = orden
            hermana.save(update_fields=['orden'])
    return f'La carpeta «{carpeta.nombre}» {"sube" if paso < 0 else "baja"} un lugar.'


def _archivo(unidad, datos):
    return get_object_or_404(
        Recurso.objects.exclude(carpeta__del_expediente=True), unidad=unidad, informe_mejora__isnull=True,
        pk=datos.get('recurso') or 0)


def renombrar_archivo(unidad, datos):
    recurso = _archivo(unidad, datos)
    nombre = _nombre(datos, 255)
    # Solo cambia el rótulo: el archivo ya pasó sus controles al cargarse.
    Recurso.objects.filter(pk=recurso.pk).update(nombre=nombre)
    return f'El archivo «{recurso.nombre}» ahora se llama «{nombre}».'


def alternar_archivo(unidad, datos):
    recurso = _archivo(unidad, datos)
    Recurso.objects.filter(pk=recurso.pk).update(activo=not recurso.activo)
    if recurso.activo:
        return f'El archivo «{recurso.nombre}» queda oculto; nada se borra.'
    return f'El archivo «{recurso.nombre}» vuelve a mostrarse.'


def _cambios_de_acceso(datos):
    """Quién lo ve y, si se confirma, que pasó la revisión de seguridad (sin ella, el público no lo abre)."""
    cambios = {'visibilidad': _visibilidad(datos)}
    if datos.get('seguridad_verificada'):
        cambios['seguridad_verificada'] = True
    return cambios


def editar_archivo(unidad, datos):
    recurso = _archivo(unidad, datos)
    cambios = _cambios_de_acceso(datos)
    Recurso.objects.filter(pk=recurso.pk).update(**cambios)
    return f'«{recurso.nombre}»: ahora lo ve {VISIBILIDADES[cambios["visibilidad"]].lower()}.'


def acceso_de_carpeta(unidad, datos):
    """Quién ve la carpeta y sus subcarpetas y, si se pide, también todos sus archivos."""
    carpeta = _carpeta(unidad, datos)
    cambios = _cambios_de_acceso(datos)
    carpetas = [carpeta.pk, *carpeta.subcarpetas.values_list('pk', flat=True)]
    CarpetaRecurso.objects.filter(pk__in=carpetas).update(visibilidad=cambios['visibilidad'])
    quien = VISIBILIDADES[cambios['visibilidad']].lower()
    if not datos.get('con_archivos'):
        return f'La carpeta «{carpeta.nombre}»: ahora la ve {quien}.'
    total = Recurso.objects.filter(unidad=unidad, carpeta_id__in=carpetas).update(**cambios)
    return f'La carpeta «{carpeta.nombre}» y sus {total} archivos: ahora los ve {quien}.'


def asignar_carpeta(unidad, datos):
    recurso = get_object_or_404(
        Recurso.objects.exclude(carpeta__del_expediente=True), unidad=unidad, informe_mejora__isnull=True,
        pk=datos.get('recurso') or 0)
    carpeta = get_object_or_404(CarpetaRecurso, unidad=unidad, del_expediente=False, pk=datos.get('carpeta') or 0)
    # Solo cambia de lugar: el archivo ya pasó sus controles al cargarse.
    Recurso.objects.filter(pk=recurso.pk).update(carpeta=carpeta)
    return f'«{recurso.nombre}» queda en la carpeta «{carpeta.nombre}».'


def alternar_carpeta(unidad, datos):
    carpeta = _carpeta(unidad, datos)
    carpeta.activa = not carpeta.activa
    carpeta.save(update_fields=['activa'])
    if carpeta.activa:
        return f'La carpeta «{carpeta.nombre}» vuelve a mostrarse.'
    return f'La carpeta «{carpeta.nombre}» queda oculta, con sus subcarpetas y archivos; nada se borra.'


def eliminar_carpeta(unidad, datos):
    carpeta = _carpeta(unidad, datos)
    if carpeta.recursos.exists() or carpeta.subcarpetas.exists():
        raise ValidationError('Solo se elimina una carpeta vacía: mueva o elimine antes sus archivos y '
                              'subcarpetas, o simplemente ocúltela.')
    carpeta.delete()
    return f'Carpeta «{carpeta.nombre}» eliminada.'


def _seccion_propia(unidad, datos):
    return get_object_or_404(SeccionPropia, unidad=unidad, pk=datos.get('seccion_propia') or 0)


def crear_seccion_propia(unidad, datos):
    modulo = _modulo(unidad, datos)
    plantilla = datos.get('plantilla', 'tarjetas')
    if plantilla not in dict(SeccionPropia.PLANTILLAS):
        raise ValidationError('Elija una plantilla.')
    seccion = crear_seccion(unidad, modulo, _nombre(datos), plantilla)
    return (f'Sección «{seccion.titulo}» creada al final de «{modulo.nombre}», con tres elementos de muestra. '
            'Ábrala para completarla.')


def renombrar_seccion_propia(unidad, datos):
    seccion = _seccion_propia(unidad, datos)
    anterior, seccion.titulo = seccion.titulo, _nombre(datos)
    seccion.save(update_fields=['titulo', 'fecha_actualizacion'])
    return f'La sección «{anterior}» ahora se llama «{seccion.titulo}».'


def alternar_seccion_propia(unidad, datos):
    seccion = _seccion_propia(unidad, datos)
    seccion.activa = not seccion.activa
    seccion.save(update_fields=['activa', 'fecha_actualizacion'])
    if seccion.activa:
        return f'La sección «{seccion.titulo}» vuelve a mostrarse.'
    return f'La sección «{seccion.titulo}» queda oculta; nada se borra.'


def ordenar_seccion_propia(unidad, datos):
    seccion = _seccion_propia(unidad, datos)
    paso = {'subir': -1, 'bajar': 1}.get(datos.get('direccion'))
    if paso is None:
        raise ValidationError('Elija si la sección sube o baja.')
    hermanas = list(SeccionPropia.objects.filter(modulo=seccion.modulo).order_by('orden', 'pk'))
    indice = hermanas.index(seccion)
    if not 0 <= indice + paso < len(hermanas):
        raise ValidationError(f'La sección «{seccion.titulo}» ya está {"primera" if paso < 0 else "última"}.')
    hermanas[indice], hermanas[indice + paso] = hermanas[indice + paso], hermanas[indice]
    for orden, hermana in enumerate(hermanas, start=1):
        if hermana.orden != orden:
            hermana.orden = orden
            hermana.save(update_fields=['orden'])
    return f'La sección «{seccion.titulo}» {"sube" if paso < 0 else "baja"} un lugar.'


def eliminar_seccion_propia(unidad, datos):
    seccion = _seccion_propia(unidad, datos)
    if seccion.elementos.filter(es_ejemplo=False).exists():
        raise ValidationError('Solo se elimina una sección sin contenido propio: quite antes sus elementos, o ocúltela.')
    seccion.delete()
    return f'Sección «{seccion.titulo}» eliminada.'


ACCIONES = {accion.__name__: accion for accion in (
    renombrar_pestana, alternar_pestana, nueva_pestana, eliminar_pestana,
    renombrar_seccion, alternar_seccion, restablecer_seccion,
    renombrar_grupo, alternar_grupo, ordenar_grupo, alternar_elemento, renombrar_archivo, alternar_archivo,
    editar_archivo, acceso_de_carpeta,
    crear_seccion_propia, renombrar_seccion_propia, alternar_seccion_propia, ordenar_seccion_propia,
    eliminar_seccion_propia,
    crear_carpeta, ordenar_carpeta, editar_carpeta, mover_carpeta, alternar_carpeta, eliminar_carpeta,
    asignar_carpeta,
)}


# ---------------------------------------------------------------------- la vista
def vista_contenidos(modelo_admin, request, object_id):
    """La página del organizador; fuera del alcance de la cuenta, la unidad no existe."""
    unidad = get_object_or_404(modelo_admin.get_queryset(request), pk=object_id)
    if not modelo_admin.has_view_or_change_permission(request, unidad):
        raise PermissionDenied
    puede_editar = modelo_admin.has_change_permission(request, unidad)
    if request.method == 'POST':
        if not puede_editar:
            raise PermissionDenied
        accion = ACCIONES.get(request.POST.get('accion'))
        if accion is None:
            messages.error(request, 'Acción desconocida.')
        else:
            try:
                with transaction.atomic():
                    mensaje = accion(unidad, request.POST)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                modelo_admin.log_change(request, unidad, f'Contenidos de la ficha: {mensaje}')
                messages.success(request, mensaje)
        volver = request.POST.get('volver', '')
        return redirect(f'{request.path}#{volver}' if volver.replace('-', '').isalnum() else request.path)
    opciones = modelo_admin.model._meta
    panel_recursos = modelo_admin.admin_site._registry.get(Recurso)
    editor_url = reverse(f'admin:{opciones.app_label}_{opciones.model_name}_change', args=[unidad.pk])
    return TemplateResponse(request, 'admin/unidades/contenidos_ficha.html', {
        **modelo_admin.admin_site.each_context(request),
        **arbol(modelo_admin, request, unidad, editor_url),
        'title': f'Contenidos de la ficha · {unidad.nombre}',
        'unidad': unidad,
        'opts': opciones,
        'puede_editar': puede_editar,
        'editor_url': editor_url,
        'tablero_url': (reverse(f'admin:{opciones.app_label}_{opciones.model_name}_tablero', args=[unidad.pk])
                        if hasattr(modelo_admin, 'tablero_view') else ''),
        'subir_url': (reverse('admin:recursos_recurso_add')
                      if panel_recursos and panel_recursos.has_add_permission(request) else ''),
    })
