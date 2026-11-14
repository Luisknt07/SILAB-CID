"""Filtros, metadatos públicos y seguimiento interno de investigación."""

def filtrar_resultados(resultados, parametros):
    filas = list(resultados)
    for campo in ('tipo', 'sector', 'tecnologia'):
        valor = parametros.get(campo, '').strip()
        if valor:
            filas = [r for r in filas if getattr(r, campo) == valor]
    for campo in ('anio', 'proyecto', 'linea'):
        valor = parametros.get(campo, '')
        if not valor:
            continue
        if not valor.isdigit():
            return []
        numero = int(valor)
        if campo == 'anio':
            filas = [r for r in filas if r.anio == numero]
        elif campo == 'proyecto':
            filas = [r for r in filas if r.proyecto_id == numero]
        else:
            filas = [r for r in filas if r.proyecto and r.proyecto.linea_id == numero]
    texto = parametros.get('q', '').strip().casefold()
    if texto:
        filas = [r for r in filas if texto in f'{r.titulo} {r.descripcion} {r.autores_texto} {r.doi}'.casefold()]
    trl = parametros.get('trl', '')
    if trl:
        filas = [r for r in filas if trl.isdigit() and r.trl_documentado and r.trl == int(trl)]
    return filas


def autores_publicos(resultado):
    if resultado.autores_texto:
        return [parte.strip() for parte in resultado.autores_texto.split(';') if parte.strip()]
    from .escenarios import contenido_admitido
    return [a.nombre for a in resultado.autores.all() if contenido_admitido(a) and a.vigente and a.rol in a.PUBLICOS]


def metadatos(resultado):
    datos = {'id': resultado.pk, 'titulo': resultado.titulo, 'tipo': resultado.tipo, 'anio': resultado.anio,
            'autores': autores_publicos(resultado), 'version': resultado.version, 'doi': resultado.doi,
            'licencia': resultado.licencia, 'acceso': str(resultado.estado_acceso_publico),
            'embargo_hasta': resultado.embargo_hasta.isoformat() if resultado.embargo_hasta else None,
            'url': resultado.url, 'proyecto': resultado.proyecto.titulo if resultado.proyecto else None}
    if resultado.es_muestra:
        datos['procedencia'] = 'Escenario operativo de desarrollo; no acredita producción institucional.'
    return datos


def referencias_ris(resultados):
    tipos = {'publicacion': 'JOUR', 'dato': 'DATA', 'software': 'COMP', 'tesis': 'THES', 'informe': 'RPRT'}
    bloques = []
    for resultado in resultados:
        datos = metadatos(resultado)
        valores = [('TY', tipos.get(resultado.tipo, 'GEN')), ('TI', datos['titulo']), ('PY', datos['anio'])]
        valores += [('AU', autor) for autor in datos['autores']]
        valores += [('DO', datos['doi']), ('UR', datos['url']), ('ET', datos['version'])]
        if datos.get('procedencia'):
            valores.append(('N1', datos['procedencia']))
        bloques.append('\n'.join(f'{clave}  - {" ".join(str(valor).split())}' for clave, valor in valores if valor)
                       + '\nER  -')
    return '\n\n'.join(bloques) + '\n'

def alertas_del_centro(centro, hoy=None):
    """Plazos internos para gestión, consultados solo cuando se necesitan."""
    from datetime import timedelta
    from django.conf import settings
    from django.urls import reverse
    from django.utils import timezone
    from .models import HitoProyecto

    hoy = hoy or timezone.localdate()
    dias = max(0, int(getattr(settings, 'CENTROS_ID_ALERTAS_DIAS', 30)))
    limite = hoy + timedelta(days=dias)
    hitos = HitoProyecto.objects.filter(proyecto__centro=centro, proyecto__es_muestra=False,
        proyecto__estado__in=('formulacion', 'ejecucion'), estado='pendiente',
        fecha_prevista__lte=limite).select_related('proyecto').order_by('fecha_prevista', 'pk')
    alertas = [{'titulo': h.titulo, 'contexto': h.proyecto.titulo, 'fecha': h.fecha_prevista,
        'estado': 'Vencido' if h.vencido else 'Próximo',
        'url': reverse('admin:centros_id_proyecto_change', args=[h.proyecto_id])} for h in hitos[:20]]
    aliados = centro.aliados.filter(activo=True, es_muestra=False, vigencia_hasta__lte=limite).order_by('vigencia_hasta', 'pk')
    alertas += [{'titulo': a.nombre, 'contexto': 'Revisar instrumento de colaboración', 'fecha': a.vigencia_hasta,
        'estado': 'Vencido' if a.vigencia_hasta < hoy else 'Próximo',
        'url': reverse('admin:centros_id_aliado_change', args=[a.pk])} for a in aliados[:20]]
    return sorted(alertas, key=lambda a: a['fecha'])[:20]
