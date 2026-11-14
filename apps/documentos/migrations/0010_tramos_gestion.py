"""Conserva el alcance legado antes de separar gestión y calendario docente.

Sólo añade metadatos: no regenera recursos, no recalifica y no cambia los
plazos ya guardados. Los documentos creados después usan semestres naturales.
"""
from datetime import date, datetime
import re

from django.conf import settings
from django.db import migrations, models, router


def _ambitos_historicos(apps, alias, configuracion):
    """La publicación de la misma base prevalece sobre un contexto de proceso.

    No importar modelos o selectores actuales desde una migración histórica:
    podrían consultar otra conexión o depender de columnas añadidas después.
    """
    Publicacion = apps.get_model('configuracion_institucional', 'PublicacionPoliticaCalendario')
    puntero = Publicacion.objects.using(alias).select_related('revision').filter(pk=1).first()
    revision = puntero.revision if puntero and puntero.revision_id else None
    datos = configuracion.ACADEMIC_CALENDAR
    if revision:
        if (revision.estado != 'publicada'
                or revision.institucion_codigo != configuracion.INSTITUTION_IDENTITY['siglas']
                or revision.producto_codigo != configuracion.PRODUCT_IDENTITY['codigo']):
            raise RuntimeError('La política de calendario guardada no es una publicación válida de este despliegue. '
                               'Revisa la configuración antes de conservar los alcances históricos.')
        if not isinstance(revision.contenido, dict):
            raise RuntimeError('La publicación de calendario no conserva una estructura de datos válida.')
        if 'ambitos_operacion' in revision.contenido:
            datos = revision.contenido
    ambitos = datos.get('ambitos_operacion') if isinstance(datos, dict) else None
    if (not isinstance(ambitos, (list, tuple))
            or any(not isinstance(a, str) or not a.strip() for a in ambitos)):
        raise RuntimeError('No se pueden determinar los ámbitos operativos del calendario histórico. '
                           'No se modificaron archivos ni resultados; corrige la política y vuelve a migrar.')
    return tuple(dict.fromkeys(ambitos))


def conservar_tramos(apps, schema_editor):
    alias = schema_editor.connection.alias
    if not router.allow_migrate(alias, 'documentos'):
        return
    Documento = apps.get_model('documentos', 'DocumentoExpediente')
    Exigido = apps.get_model('documentos', 'DocumentoExigido')
    Version = apps.get_model('core', 'VersionCalendarioAcademico')
    Redaccion = apps.get_model('documentos', 'DocumentoElaborado')
    Recurso = apps.get_model('recursos', 'Recurso')
    Tipologia = apps.get_model('configuracion_institucional', 'TipologiaUnidad')
    bases = dict(Tipologia.objects.using(alias).values_list('codigo', 'base'))
    ambitos = _ambitos_historicos(apps, alias, settings)
    calendarios = {}
    for v in Version.objects.using(alias).filter(vigente=True,
            periodo__estado__in=('publicado', 'cerrado'), periodo__tipo='ordinario',
            periodo__ciclo__in=('A', 'B'), periodo__ambito__in=ambitos).select_related('periodo'):
        calendarios.setdefault(v.periodo.anio_referencia, {})[v.periodo.ciclo] = (
            v.fecha_inicio_clases, v.fecha_fin_periodo)
    alcances_plan = {}
    for r in Redaccion.objects.using(alias).filter(documento__exigido__codigo='PLANIFICACION'):
        contenido = r.contenido if isinstance(r.contenido, dict) else {}
        actividades = contenido.get('actividades')
        capacidad = actividades.get('capacidad') if isinstance(actividades, dict) else None
        if isinstance(capacidad, dict):
            try:
                inicio, fin = map(date.fromisoformat, (capacidad.get('inicio'), capacidad.get('fin')))
                if inicio <= fin:
                    alcances_plan[r.documento_id] = (inicio, fin)
            except (ValueError, TypeError):
                pass
    recursos = {}
    pendientes = set(Documento.objects.using(alias).exclude(recurso_id=None).values_list('recurso_id', flat=True))
    for _ in range(64):
        if not pendientes:
            break
        lote = {r.pk: r for r in Recurso.objects.using(alias).filter(pk__in=pendientes)
                .only('pk', 'descripcion', 'reemplaza_a_id')}
        recursos.update(lote)
        pendientes = {r.reemplaza_a_id for r in lote.values() if r.reemplaza_a_id} - recursos.keys()
    for d in Documento.objects.using(alias).select_related('exigido', 'unidad').iterator(chunk_size=250):
        cortes = {'A': (date(d.anio, 1, 1), date(d.anio, 6, 30)),
                  'B': (date(d.anio, 7, 1), date(d.anio, 12, 31))}
        cortes.update(calendarios.get(d.anio, {}))
        anual = d.exigido.periodicidad == 'anual'
        if (d.exigido.codigo == 'INVENTARIO-CORTE'
                and bases.get(d.unidad.dependencia, d.unidad.dependencia) == 'laboratorios'):
            anual = False
        if anual or not (d.corte or d.mes):
            inicio, fin = cortes['A'][0], cortes['B'][1]
        elif d.mes:
            inicio = date(d.anio, d.mes, 1)
            siguiente = date(d.anio + (d.mes == 12), d.mes % 12 + 1, 1)
            fin = date.fromordinal(siguiente.toordinal() - 1)
        else:
            inicio, fin = cortes[d.corte]
        # Los originales nativos conservan el rango en su descripción; una
        # carga firmada puede apuntar al original por la cadena de recursos.
        recurso, vistos = recursos.get(d.recurso_id), set()
        while recurso and recurso.pk not in vistos:
            vistos.add(recurso.pk)
            texto = recurso.descripcion or ''
            encontrado = re.search(r'\bdel (\d{2}/\d{2}/\d{4}) al (\d{2}/\d{2}/\d{4})', texto)
            if encontrado:
                try:
                    a, b = (datetime.strptime(t, '%d/%m/%Y').date() for t in encontrado.groups())
                    if a <= b:
                        inicio, fin = a, b
                        break
                except ValueError:
                    pass
            recurso = recursos.get(recurso.reemplaza_a_id)
        if d.pk in alcances_plan:
            inicio, fin = alcances_plan[d.pk]
        Documento.objects.using(alias).filter(pk=d.pk).update(
            tramo_inicio=inicio, tramo_fin=fin, marco_periodo='academico_legacy')
    # Sólo la regla estándar cambia para las futuras filas. Las ventanas
    # individuales, correcciones y prórrogas existentes siguen intactas.
    cierre = Exigido.objects.using(alias).filter(plazo_regla='fin', plazo_dias=0).filter(
        models.Q(codigo='INFORME-SEMESTRAL') | models.Q(anexo_de__codigo='INFORME-SEMESTRAL'))
    cierre.update(plazo_regla='cierre', plazo_dias=15)


class Migration(migrations.Migration):
    dependencies = [('documentos', '0009_documentos_por_tipo_unidad'),
                    ('core', '0001_propiedad_modelos'),
                    ('configuracion_institucional', '0009_ayudas_presentacion')]
    operations = [
        migrations.AddField(model_name='documentoexpediente', name='tramo_inicio',
            field=models.DateField(null=True, blank=True, editable=False)),
        migrations.AddField(model_name='documentoexpediente', name='tramo_fin',
            field=models.DateField(null=True, blank=True, editable=False)),
        migrations.AddField(model_name='documentoexpediente', name='marco_periodo',
            field=models.CharField(max_length=32, default='academico_legacy', editable=False,
                help_text='Marco y fechas conservados del documento; no se recalculan al cambiar el calendario académico.')),
        migrations.AlterField(model_name='documentoexigido', name='plazo_regla',
            field=models.CharField(max_length=8, default='ninguno', choices=[
                ('inicio', 'Días después del inicio del año o período'),
                ('fin', 'Días antes del cierre del año o período'),
                ('cierre', 'Entrega después del cierre del semestre de gestión'),
                ('meses', 'Entre dos meses del año'), ('ninguno', 'Sin plazo')])),
        migrations.RunPython(conservar_tramos, migrations.RunPython.noop),
        migrations.AlterField(model_name='documentoexpediente', name='marco_periodo',
            field=models.CharField(max_length=32, default='gestion_v1', editable=False,
                help_text='Marco y fechas conservados del documento; no se recalculan al cambiar el calendario académico.')),
    ]
