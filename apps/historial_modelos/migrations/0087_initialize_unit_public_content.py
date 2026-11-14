from django.db import migrations


RESERVATION_KEY_BY_TYPE = {
    'laboratorios': 'gestion-reserva',
    'observatorios': 'acceso-servicios',
    'plantas_piloto': 'reservas-servicios',
    'centro_experimental': 'visitas-servicios',
}


CONTENT_BY_TYPE = {
    'laboratorios': {
        'label': 'laboratorio',
        'purpose': 'Apoyar la docencia, la investigación formativa y aplicada, la innovación y la prestación de servicios mediante prácticas y recursos especializados.',
        'management': 'Es administrado por una persona responsable y la dependencia académica vinculada. La disponibilidad de espacios, equipos y materiales se coordina mediante el sistema de reservas.',
        'users': 'Estudiantes, docentes, investigadores, personal técnico y usuarios autorizados de proyectos o servicios.',
        'contents': 'Recursos y prácticas, guías, equipos, inventario, tecnología y software, reservas de equipos o espacios, proyectos y actividades de formación.',
    },
    'observatorios': {
        'label': 'observatorio',
        'purpose': 'Monitorear, analizar e interpretar información relevante para convertir datos e indicadores en conocimiento útil para el territorio.',
        'management': 'Es coordinado por un equipo académico y técnico que valida fuentes, indicadores, metodologías, publicaciones y servicios de consulta.',
        'users': 'Estudiantes, docentes, investigadores, instituciones, organizaciones y actores del territorio que requieren evidencia para tomar decisiones.',
        'contents': 'Datos, mapas, indicadores, tableros, alertas, reportes, publicaciones, metodologías y mecanismos de acceso a servicios de información.',
    },
    'plantas_piloto': {
        'label': 'planta piloto',
        'purpose': 'Validar procesos, protocolos y productos en una escala intermedia que conecta la formación, la experimentación y la transferencia tecnológica.',
        'management': 'Opera bajo responsables técnicos, protocolos de calidad e inocuidad, programación de lotes y control de equipos, materiales y condiciones de proceso.',
        'users': 'Estudiantes, docentes, investigadores, productores, emprendedores y organizaciones autorizadas para prácticas, ensayos o servicios.',
        'contents': 'Procesos y protocolos, equipos e infraestructura, producción y lotes, calidad e inocuidad, recursos técnicos, reservas y servicios.',
    },
    'centro_experimental': {
        'label': 'centro experimental',
        'purpose': 'Facilitar investigación, validación en territorio, producción experimental, prácticas y transferencia de conocimiento en condiciones reales.',
        'management': 'Es administrado por personal responsable del centro y equipos académicos que coordinan áreas productivas, infraestructura, ensayos, visitas y servicios.',
        'users': 'Estudiantes, docentes, investigadores, productores, comunidades, instituciones y visitantes autorizados.',
        'contents': 'Áreas y sistemas productivos, producción y ensayos, infraestructura y equipos, proyectos, vinculación, visitas guiadas y servicios.',
    },
}


def initialize_content(apps, schema_editor):
    Proyecto = apps.get_model('webcitt', 'Proyecto')
    ModuloUnidad = apps.get_model('webcitt', 'ModuloUnidad')
    PresentacionUnidad = apps.get_model('webcitt', 'PresentacionUnidad')
    ReglamentoUnidad = apps.get_model('webcitt', 'ReglamentoUnidad')

    for module in ModuloUnidad.objects.select_related('proyecto').all().iterator():
        expected_key = RESERVATION_KEY_BY_TYPE.get(
            module.proyecto.dependencia,
            'gestion-reserva',
        )
        expected = module.clave == expected_key
        if module.mostrar_herramientas_reserva != expected:
            ModuloUnidad.objects.filter(pk=module.pk).update(
                mostrar_herramientas_reserva=expected,
            )

    for project in Proyecto.objects.all().iterator():
        content = CONTENT_BY_TYPE.get(project.dependencia, CONTENT_BY_TYPE['laboratorios'])
        description = project.descripcion_corta or project.descripcion or (
            'Explora sus capacidades, servicios y oportunidades de participación.'
        )
        PresentacionUnidad.objects.get_or_create(
            proyecto_id=project.pk,
            defaults={
                'titulo': f'Conoce este {content["label"]}',
                'introduccion': description,
                'proposito': content['purpose'],
                'gestion_administracion': content['management'],
                'usuarios': content['users'],
                'contenidos_disponibles': content['contents'],
                'activo': True,
            },
        )
        ReglamentoUnidad.objects.get_or_create(
            proyecto_id=project.pk,
            defaults={
                'titulo': f'Reglamento de uso de {project.nombre}',
                'subtitulo': 'Lineamientos para el uso responsable de espacios, equipos y recursos.',
                'normas_generales': 'Utiliza responsablemente los espacios y recursos.\nMantén el orden y la limpieza.\nCumple las indicaciones del personal responsable.',
                'reservas_horarios': 'Realiza las reservas mediante el sistema institucional.\nRespeta el horario autorizado.\nCancela con anticipación cuando no puedas asistir.',
                'equipos_materiales': 'Verifica el estado antes de utilizar cada recurso.\nReporta daños o funcionamiento irregular.\nEntrega los equipos y materiales en las condiciones recibidas.',
                'seguridad': 'Utiliza los elementos de protección requeridos.\nIdentifica las rutas y elementos de emergencia.\nReporta inmediatamente cualquier incidente.',
                'contacto_texto': 'Para dudas o emergencias, comunícate con el equipo responsable.',
                'contacto_email': project.contacto_email or 'laboratorio@upec.edu.ec',
                'activo': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('webcitt', '0086_reglamentounidad_presentacionunidad'),
    ]

    operations = [
        migrations.RunPython(initialize_content, migrations.RunPython.noop),
    ]
