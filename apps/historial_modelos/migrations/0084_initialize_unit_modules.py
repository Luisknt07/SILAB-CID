from django.db import migrations


DEFAULTS = {
    'laboratorios': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('recursos-practicas', 'Recursos y prácticas', 'iconsminds-library', False),
        ('tecnologia-software', 'Tecnología y software', 'iconsminds-optimization', False),
        ('gestion-reserva', 'Gestión y reserva', 'iconsminds-conference', True),
        ('proyectos', 'Proyectos', 'iconsminds-big-data', False),
        ('formacion-comunidad', 'Formación y comunidad', 'iconsminds-communication-tower-2', False),
    ],
    'observatorios': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('datos-indicadores', 'Datos, mapas e indicadores', 'iconsminds-data-center', False),
        ('monitoreo-alertas', 'Monitoreo y alertas', 'iconsminds-bell', False),
        ('reportes-publicaciones', 'Reportes y publicaciones', 'iconsminds-file', False),
        ('investigacion-vinculacion', 'Investigación y vinculación', 'iconsminds-big-data', False),
        ('acceso-servicios', 'Acceso y servicios', 'iconsminds-conference', True),
    ],
    'plantas_piloto': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('procesos-protocolos', 'Procesos y protocolos', 'iconsminds-gear', False),
        ('equipos-infraestructura', 'Equipos e infraestructura', 'iconsminds-factory', False),
        ('produccion-lotes', 'Producción y lotes', 'iconsminds-box-with-folders', False),
        ('calidad-inocuidad', 'Calidad e inocuidad', 'iconsminds-check', False),
        ('reservas-servicios', 'Reservas y servicios', 'iconsminds-calendar', True),
    ],
    'centro_experimental': [
        ('informacion-general', 'Información general', 'iconsminds-gears', False),
        ('areas-productivas', 'Áreas y sistemas productivos', 'iconsminds-environmental-3', False),
        ('produccion-ensayos', 'Producción y ensayos', 'iconsminds-plant', False),
        ('infraestructura-equipos', 'Infraestructura y equipos', 'iconsminds-factory', False),
        ('investigacion-vinculacion', 'Investigación y vinculación', 'iconsminds-big-data', False),
        ('visitas-servicios', 'Visitas y servicios', 'iconsminds-calendar', True),
    ],
}

LEGACY_TARGET = {
    'laboratorios': {
        'informacionGeneral': 'informacion-general',
        'recursos': 'recursos-practicas',
        'software': 'tecnologia-software',
        'reserva': 'gestion-reserva',
        'proyectos': 'proyectos',
        'colaboracion': 'formacion-comunidad',
    },
    'observatorios': {
        'informacionGeneral': 'informacion-general',
        'recursos': 'datos-indicadores',
        'software': 'monitoreo-alertas',
        'reserva': 'acceso-servicios',
        'proyectos': 'investigacion-vinculacion',
        'colaboracion': 'reportes-publicaciones',
    },
    'plantas_piloto': {
        'informacionGeneral': 'informacion-general',
        'recursos': 'procesos-protocolos',
        'software': 'equipos-infraestructura',
        'reserva': 'reservas-servicios',
        'proyectos': 'produccion-lotes',
        'colaboracion': 'calidad-inocuidad',
    },
    'centro_experimental': {
        'informacionGeneral': 'informacion-general',
        'recursos': 'areas-productivas',
        'software': 'infraestructura-equipos',
        'reserva': 'visitas-servicios',
        'proyectos': 'investigacion-vinculacion',
        'colaboracion': 'produccion-ensayos',
    },
}


def initialize_modules(apps, schema_editor):
    Proyecto = apps.get_model('webcitt', 'Proyecto')
    ModuloUnidad = apps.get_model('webcitt', 'ModuloUnidad')
    CarpetaRecurso = apps.get_model('webcitt', 'CarpetaRecurso')

    for proyecto in Proyecto.objects.all().iterator():
        dependencia = proyecto.dependencia if proyecto.dependencia in DEFAULTS else 'laboratorios'
        modules = {}
        for order, (key, name, icon, reservations) in enumerate(DEFAULTS[dependencia], start=1):
            module = ModuloUnidad.objects.create(
                proyecto_id=proyecto.id,
                clave=key,
                nombre=name,
                icono=icon,
                orden=order,
                activo=True,
                mostrar_herramientas_reserva=reservations,
            )
            modules[key] = module

        mapping = LEGACY_TARGET[dependencia]
        for folder in CarpetaRecurso.objects.filter(proyecto_id=proyecto.id):
            target_key = mapping.get(folder.modulo, 'informacion-general')
            folder.modulo_config_id = modules[target_key].id
            folder.save(update_fields=['modulo_config'])


def clear_module_links(apps, schema_editor):
    CarpetaRecurso = apps.get_model('webcitt', 'CarpetaRecurso')
    ModuloUnidad = apps.get_model('webcitt', 'ModuloUnidad')
    CarpetaRecurso.objects.update(modulo_config=None)
    ModuloUnidad.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('webcitt', '0083_modulounidad_carpetarecurso_modulo_config'),
    ]

    operations = [
        migrations.RunPython(initialize_modules, clear_module_links),
    ]
