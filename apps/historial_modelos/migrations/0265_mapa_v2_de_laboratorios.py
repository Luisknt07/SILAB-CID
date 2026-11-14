"""Los laboratorios pasan al mapa v2: seis pestañas, con procesos y productos e investigación formativa.

«Equipos y tecnología» pasa a «Áreas y equipos», «Prácticas y formación» a «Docencia y
capacitación» (sus secciones 3.x pasan a 4.x) y «Proyectos e investigación» a «Investigación
formativa y vinculación» (4.1 → 6.1, 4.2 → 6.3, 4.3 → 6.4). Se agrega «Procesos y
productos». Las pestañas conservan su registro y sus carpetas; los nombres propios y las
secciones ocultas de cada unidad siguen a su sección. La pestaña de investigación queda
visible solo en los laboratorios cuyo modo de uso incluye investigación o que ya publicaron
algo en ella. Nada se borra.
"""
from django.db import migrations, models

# Pestaña anterior → (clave nueva, nombre, ícono)
RENOMBRES = {
    'equipos-tecnologia': ('areas-equipos', 'Áreas y equipos', 'iconsminds-optimization'),
    'practicas-formacion': ('docencia-capacitacion', 'Docencia y capacitación', 'iconsminds-library'),
    'proyectos-investigacion': ('investigacion-formativa', 'Investigación formativa y vinculación',
                                'iconsminds-big-data'),
}
PESTANAS = [
    ('informacion-general', 'Información general', 'iconsminds-gears', False),
    ('areas-equipos', 'Áreas y equipos', 'iconsminds-optimization', False),
    ('procesos-productos', 'Procesos y productos', 'iconsminds-gear', False),
    ('docencia-capacitacion', 'Docencia y capacitación', 'iconsminds-library', False),
    ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', True),
    ('investigacion-formativa', 'Investigación formativa y vinculación', 'iconsminds-big-data', False),
]
# Sección anterior → sección nueva; las demás conservan su número.
SECCIONES = {'3.1': '4.1', '3.2': '4.2', '3.3': '4.3', '3.4': '4.4', '4.1': '6.1', '4.2': '6.3', '4.3': '6.4'}
INVESTIGACION = 'investigacion-formativa'


def alinear(apps, schema_editor):
    Unidad = apps.get_model('webcitt', 'Unidad')
    ModuloUnidad = apps.get_model('webcitt', 'ModuloUnidad')
    CarpetaRecurso = apps.get_model('webcitt', 'CarpetaRecurso')
    AjusteSeccionPlanta = apps.get_model('webcitt', 'AjusteSeccionPlanta')
    for unidad in Unidad.objects.filter(dependencia='laboratorios'):
        modulos = {modulo.clave: modulo for modulo in ModuloUnidad.objects.filter(unidad=unidad)}
        if 'docencia-capacitacion' in modulos:
            continue  # ya está en el mapa v2
        # 1. Las pestañas cambian de clave y nombre conservando su registro y sus carpetas.
        for vieja, (nueva, nombre, icono) in RENOMBRES.items():
            modulo = modulos.pop(vieja, None)
            if modulo is not None and nueva not in modulos:
                modulo.clave, modulo.nombre, modulo.icono = nueva, nombre, icono
                modulo.save()
                modulos[nueva] = modulo
        # 2. Las carpetas propias pasan a su sección nueva en una sola pasada.
        for carpeta in CarpetaRecurso.objects.filter(unidad=unidad, seccion_planta__in=list(SECCIONES)):
            carpeta.seccion_planta = SECCIONES[carpeta.seccion_planta]
            carpeta.save(update_fields=['seccion_planta'])
        # 3. Los nombres propios y las secciones ocultas siguen a su sección.
        ajustes = list(AjusteSeccionPlanta.objects.filter(unidad=unidad, numero__in=list(SECCIONES)))
        for ajuste in ajustes:
            ajuste.delete()
        for ajuste in ajustes:
            AjusteSeccionPlanta.objects.create(unidad=unidad, numero=SECCIONES[ajuste.numero],
                                               titulo=ajuste.titulo, oculta=ajuste.oculta)
        # 4. Las pestañas que faltan se crean y todas toman el orden del mapa.
        investiga = (unidad.tipos_laboratorio.filter(nombre__iexact='Investigación').exists()
                     or (INVESTIGACION in modulos and CarpetaRecurso.objects.filter(
                         modulo_config=modulos[INVESTIGACION], activa=True).exists()))
        for orden, (clave, nombre, icono, reservas) in enumerate(PESTANAS, start=1):
            activo = investiga if clave == INVESTIGACION else True
            if clave not in modulos:
                ModuloUnidad.objects.create(unidad=unidad, clave=clave, nombre=nombre, icono=icono, orden=orden,
                                            activo=activo, mostrar_herramientas_reserva=reservas)
                continue
            modulo = modulos[clave]
            if (modulo.orden, modulo.mostrar_herramientas_reserva) != (orden, reservas) or (
                    clave == INVESTIGACION and modulo.activo != activo):
                modulo.orden, modulo.mostrar_herramientas_reserva = orden, reservas
                if clave == INVESTIGACION:
                    modulo.activo = activo
                modulo.save()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0264_auditoria_sobrevive_a_la_unidad'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ajusteseccionplanta',
            name='numero',
            field=models.CharField(choices=[('1.1', '1.1'), ('1.2', '1.2'), ('1.3', '1.3'), ('1.4', '1.4'), ('1.5', '1.5'), ('1.6', '1.6'), ('2.1', '2.1'), ('2.2', '2.2'), ('2.3', '2.3'), ('2.4', '2.4'), ('2.5', '2.5'), ('2.6', '2.6'), ('3.1', '3.1'), ('3.2', '3.2'), ('3.3', '3.3'), ('3.4', '3.4'), ('4.1', '4.1'), ('4.2', '4.2'), ('4.3', '4.3'), ('4.4', '4.4'), ('4.5', '4.5'), ('4.6', '4.6'), ('5.1', '5.1'), ('5.2', '5.2'), ('5.3', '5.3'), ('5.4', '5.4'), ('5.5', '5.5'), ('5.6', '5.6'), ('5.7', '5.7'), ('6.1', '6.1'), ('6.2', '6.2'), ('6.3', '6.3'), ('6.4', '6.4'), ('6.5', '6.5'), ('6.6', '6.6'), ('6.7', '6.7')], max_length=5, verbose_name='Sección'),
        ),
        migrations.RunPython(alinear, migrations.RunPython.noop),
    ]
