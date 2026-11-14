"""Los documentos del centro en PDF, armados desde sus registros o desde un texto por bloques.

Un documento generado (el plan de desarrollo, la ruta de atención, el protocolo de seguridad, el catálogo de servicios
o el equipamiento por área) sale de lo que el centro tiene registrado: si cambia el registro, se vuelve a generar con
`cargar_centros_id --reescribir --medios`. Un documento escrito se arma con sus bloques de texto. Ambos usan la
identidad institucional y los estilos del reporte del centro.
"""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, SimpleDocTemplate, Spacer

from apps.core.presentation.identidad import identidad_actual, logo_institucional

from .reportes import _estilos, _p, _paleta, _seccion, _tabla
from .texto import pares_de


def pdf(centro, titulo, resumen, bloques):
    """El PDF de un documento del centro. `bloques` es una lista de (título, elementos); cada elemento es un párrafo
    (texto), una lista ('lista', [textos]) o una tabla ('tabla', cabecera, filas, anchos)."""
    primario, oscuro = _paleta()
    estilos = _estilos(primario)
    institucion = identidad_actual()[1]
    hoy = timezone.localdate()
    salida = BytesIO()

    def marco(lienzo, documento):
        lienzo.saveState()
        lienzo.setFillColor(oscuro)
        lienzo.rect(0, A4[1] - 18 * mm, A4[0], 18 * mm, stroke=0, fill=1)
        logo = logo_institucional(fondo='oscuro')
        if logo:
            try:
                lienzo.drawImage(str(logo), 15 * mm, A4[1] - 15 * mm, width=38 * mm, height=12 * mm,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:  # noqa: BLE001 - un logo ilegible no impide el documento
                pass
        lienzo.setFillColor(colors.white)
        lienzo.setFont('Helvetica-Bold', 9)
        lienzo.drawRightString(A4[0] - 15 * mm, A4[1] - 9 * mm, (centro.sigla or centro.nombre).upper())
        lienzo.setFont('Helvetica', 7.5)
        lienzo.drawRightString(A4[0] - 15 * mm, A4[1] - 13.5 * mm, f'{hoy:%d/%m/%Y}')
        lienzo.setFillColor(colors.HexColor('#6b7a72'))
        lienzo.drawString(15 * mm, 10 * mm, f'{getattr(institucion, "nombre", "")} · {centro.nombre}')
        lienzo.drawRightString(A4[0] - 15 * mm, 10 * mm, f'Página {documento.page}')
        lienzo.restoreState()

    documento = SimpleDocTemplate(salida, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=26 * mm,
                                  bottomMargin=18 * mm, title=titulo, author=str(centro))
    flujo = [_p(titulo, estilos['titulo']), _p(centro.nombre, estilos['nota'])]
    if resumen:
        flujo += [Spacer(1, 6), _p(resumen, estilos['lema'])]
    for encabezado, elementos in bloques:
        flujo += _seccion(encabezado, estilos)
        for elemento in elementos:
            if isinstance(elemento, str):
                flujo += [_p(elemento, estilos['base']), Spacer(1, 4)]
            elif elemento[0] == 'lista':
                flujo.append(ListFlowable([ListItem(_p(texto, estilos['base']), leftIndent=10) for texto in elemento[1]],
                                          bulletType='bullet', start='•', leftIndent=10))
                flujo.append(Spacer(1, 4))
            elif elemento[0] == 'tabla':
                flujo += [_tabla(elemento[1], elemento[2], elemento[3], estilos, primario), Spacer(1, 6)]
    documento.build(flujo, onFirstPage=marco, onLaterPages=marco)
    return salida.getvalue()


# ----------------------------------------------------------------------------- documentos que salen de los registros
def _plan(centro):
    lineas = list(centro.lineas.all())
    bloques = [('Objetivo general', [centro.objetivo_general or centro.proposito])]
    if centro.lista_objetivos:
        bloques.append(('Objetivos específicos', [('lista', centro.lista_objetivos)]))
    if lineas:
        bloques.append(('Líneas de investigación y lo que buscan', [
            ('tabla', ['Línea', 'Resultados que busca', 'Retos prioritarios'],
             [(linea.nombre, linea.resultados, '; '.join(linea.lista_retos) or '—') for linea in lineas], (0.22, 0.42, 0.36))]))
    modalidades = list(centro.modalidades.all())
    if modalidades:
        bloques.append(('Modalidades de trabajo', [
            ('tabla', ['Modalidad', 'Para qué', 'Usuarios'], [(m.nombre, m.proposito, m.usuarios) for m in modalidades],
             (0.25, 0.5, 0.25))]))
    indicadores = list(centro.indicadores.all())
    if indicadores:
        bloques.append(('Indicadores con los que rinde cuentas', [
            ('tabla', ['Categoría', 'Indicador', 'Cómo se mide'], [(i.categoria, i.nombre, i.medicion) for i in indicadores],
             (0.25, 0.35, 0.4))]))
    return bloques


def _ruta(centro):
    bloques = []
    etapas = list(centro.ruta.all())
    if etapas:
        bloques.append(('La ruta de atención', [
            'Toda necesidad entra por una solicitud y avanza por estas etapas; cada una tiene un responsable y deja un '
            'resultado registrado.',
            ('tabla', ['Etapa', 'Propósito', 'Responsable', 'Resultado'],
             [(f'{e.numero}. {e.nombre}', e.proposito, e.responsable, e.resultado) for e in etapas], (0.22, 0.32, 0.24, 0.22))]))
    modalidades = list(centro.modalidades.all())
    if modalidades:
        bloques.append(('Modalidades de acceso', [('lista', [f'{m.nombre}: {m.proposito}' for m in modalidades])]))
    bloques.append(('Reglas de acceso a las áreas', [('lista', [
        'El acceso a un área se pide para un proyecto, una práctica o un servicio; el centro lo evalúa y confirma el área '
        'y el horario.',
        'Dos accesos aprobados no se cruzan en la misma área.',
        'Quien usa un área cumple su protocolo de seguridad y la inducción que corresponda.',
        'Los servicios con costo se pagan solo por los mecanismos institucionales.'])]))
    return bloques


def _seguridad(centro):
    bloques = []
    riesgos = list(centro.riesgos.all())
    if riesgos:
        bloques.append(('Riesgos de operación y su control', [
            ('tabla', ['Tipo', 'Riesgo', 'Posible efecto', 'Control'],
             [(r.categoria, r.riesgo, r.efecto, r.mitigacion) for r in riesgos], (0.16, 0.26, 0.26, 0.32))]))
    filas = [(area.nombre_corto or area.nombre, riesgo, control) for area in centro.componentes.filter(publicado=True)
             for riesgo, control in pares_de(area.seguridad)]
    if filas:
        bloques.append(('Seguridad en cada división y plataforma', [
            ('tabla', ['Área', 'Qué se cuida', 'Cómo se controla'], filas, (0.22, 0.38, 0.40))]))
    bloques.append(('Reglas generales', [('lista', [
        'Nadie opera un equipo sin la inducción y la autorización que corresponden a su nivel de riesgo.',
        'Se usa el equipo de protección que indica cada área y se respetan las zonas demarcadas.',
        'Todo incidente se reporta a la coordinación técnico-operativa el mismo día y queda registrado.',
        'Los paros de emergencia, extintores y rutas de evacuación se mantienen libres y señalizados.'])]))
    return bloques


def _servicios(centro):
    bloques = []
    lineas = {}
    for servicio in centro.servicios.filter(activo=True).select_related('componente'):
        lineas.setdefault(servicio.linea, []).append(servicio)
    for linea, servicios in lineas.items():
        bloques.append((linea, [('tabla', ['Servicio', 'Qué incluye', 'Entregable', 'Área'],
                                 [(s.nombre, s.descripcion, s.entregable,
                                   (s.componente.nombre_corto or s.componente.nombre) if s.componente else 'El centro')
                                  for s in servicios], (0.24, 0.36, 0.22, 0.18))]))
    return bloques


def _equipamiento(centro):
    bloques = []
    for area in centro.componentes.filter(publicado=True).prefetch_related('equipos'):
        from .escenarios import filtro_contenido
        equipos = list(area.equipos.filter(**filtro_contenido(centro)))
        if equipos:
            bloques.append((f'{area.nombre_corto or area.nombre} · {area.get_tipo_display()}', [
                ('tabla', ['Equipo', 'Qué incluye', 'Para qué sirve'], [(e.nombre, e.detalle, e.funcion) for e in equipos],
                 (0.26, 0.4, 0.34))]))
    return bloques


GENERADORES = {'plan': _plan, 'ruta': _ruta, 'seguridad': _seguridad, 'servicios': _servicios,
               'equipamiento': _equipamiento}
