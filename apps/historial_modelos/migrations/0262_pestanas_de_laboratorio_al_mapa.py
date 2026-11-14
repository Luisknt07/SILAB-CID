"""Las pestañas de los laboratorios existentes pasan al mapa de cinco pestañas y sus carpetas a una sección.

Las seis pestañas genéricas («Recursos y prácticas», «Tecnología y software», «Gestión y
reserva», «Proyectos», «Formación y comunidad») se convierten en las del mapa de
laboratorios; la que sobra se funde en «Prácticas y formación». Cada carpeta propia sin
sección recibe la que corresponde a su pestaña, para que siga viéndose. Un laboratorio
al que le falten pestañas las recibe. Nada se borra.
"""
from django.db import migrations

# Pestaña anterior → (clave nueva, nombre, ícono, sección para sus carpetas)
RENOMBRES = {
    'informacion-general': ('informacion-general', 'Información general', 'iconsminds-gears', '1.5'),
    'tecnologia-software': ('equipos-tecnologia', 'Equipos y tecnología', 'iconsminds-optimization', '2.3'),
    'recursos-practicas': ('practicas-formacion', 'Prácticas y formación', 'iconsminds-library', '3.4'),
    'proyectos': ('proyectos-investigacion', 'Proyectos e investigación', 'iconsminds-big-data', '4.1'),
    'gestion-reserva': ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', ''),
}
# Pestañas que se funden en otra: sus carpetas van a la sección indicada.
FUSIONES = {
    'formacion-comunidad': ('practicas-formacion', '3.3'),
}
# Las carpetas de la antigua «Gestión y reserva» eran material, no reservas: van a 2.4 Materiales.
DESTINO_GESTION = ('equipos-tecnologia', '2.4')
PESTANAS = [
    ('informacion-general', 'Información general', 'iconsminds-gears', False),
    ('equipos-tecnologia', 'Equipos y tecnología', 'iconsminds-optimization', False),
    ('practicas-formacion', 'Prácticas y formación', 'iconsminds-library', False),
    ('proyectos-investigacion', 'Proyectos e investigación', 'iconsminds-big-data', False),
    ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', True),
]
CLAVES = {clave for clave, *_ in PESTANAS}


def alinear(apps, schema_editor):
    Unidad = apps.get_model('webcitt', 'Unidad')
    ModuloUnidad = apps.get_model('webcitt', 'ModuloUnidad')
    CarpetaRecurso = apps.get_model('webcitt', 'CarpetaRecurso')
    for unidad in Unidad.objects.filter(dependencia='laboratorios'):
        modulos = {modulo.clave: modulo for modulo in ModuloUnidad.objects.filter(unidad=unidad)}
        # 1. Las pestañas que cambian de nombre conservan su registro y sus carpetas.
        for vieja, (nueva, nombre, icono, _seccion) in RENOMBRES.items():
            modulo = modulos.get(vieja)
            if modulo is None or vieja == nueva or nueva in modulos:
                continue
            modulo.clave, modulo.nombre, modulo.icono = nueva, nombre, icono
            modulo.mostrar_herramientas_reserva = nueva == 'reservas-servicios'
            modulo.save()
            modulos[nueva] = modulos.pop(vieja)
        # 2. Las que faltan se crean, en el orden del mapa.
        for orden, (clave, nombre, icono, reservas) in enumerate(PESTANAS, start=1):
            if clave not in modulos:
                modulos[clave] = ModuloUnidad.objects.create(
                    unidad=unidad, clave=clave, nombre=nombre, icono=icono, orden=orden,
                    mostrar_herramientas_reserva=reservas,
                )
            else:
                modulo = modulos[clave]
                if modulo.orden != orden or modulo.mostrar_herramientas_reserva != reservas:
                    modulo.orden, modulo.mostrar_herramientas_reserva = orden, reservas
                    modulo.save()
        # 3. Las que se funden pasan sus carpetas y desaparecen; las ajenas al mapa se ocultan.
        for clave, modulo in list(modulos.items()):
            if clave in FUSIONES:
                destino, seccion = FUSIONES[clave]
                CarpetaRecurso.objects.filter(modulo_config=modulo).update(
                    modulo_config=modulos[destino], seccion_planta=seccion)
                modulo.delete()
                modulos.pop(clave)
            elif clave not in CLAVES and modulo.activo:
                modulo.activo = False
                modulo.save()
        # 4. Cada carpeta propia sin sección recibe la de su pestaña; las subcarpetas siguen a su superior.
        carpetas = CarpetaRecurso.objects.filter(unidad=unidad, del_expediente=False, ficha__isnull=True)
        for carpeta in carpetas.filter(carpeta_padre__isnull=True, modulo_config__isnull=False):
            clave = carpeta.modulo_config.clave
            if clave == 'reservas-servicios' and not carpeta.seccion_planta:
                carpeta.modulo_config = modulos[DESTINO_GESTION[0]]
                carpeta.seccion_planta = DESTINO_GESTION[1]
                carpeta.save()
            elif not carpeta.seccion_planta:
                seccion = next((s for _v, (n, _nombre, _i, s) in RENOMBRES.items() if n == clave and s), '')
                if seccion:
                    carpeta.seccion_planta = seccion
                    carpeta.save()
        for carpeta in carpetas.filter(carpeta_padre__isnull=False):
            padre = carpeta.carpeta_padre
            if (carpeta.modulo_config_id, carpeta.seccion_planta) != (padre.modulo_config_id, padre.seccion_planta):
                carpeta.modulo_config_id, carpeta.seccion_planta = padre.modulo_config_id, padre.seccion_planta
                carpeta.save()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0261_mapa_de_secciones_por_tipo'),
    ]

    operations = [
        migrations.RunPython(alinear, migrations.RunPython.noop),
    ]
