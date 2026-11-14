from django.db import migrations, models


TIPOS_USUARIO = [
    ('estudiante', 'Estudiante UPEC'),
    ('docente', 'Docente UPEC'),
    ('investigador', 'Investigador UPEC'),
    ('administrativo', 'Personal administrativo UPEC'),
    ('egresado', 'Egresado UPEC'),
    ('externo', 'Usuario externo'),
]

FACULTADES = [
    ('salud_educacion', 'Facultad de Ciencias de la Salud y Ciencias de la Educación'),
    ('agropecuarias_ambientales', 'Facultad de Industrias Agropecuarias y Ciencias Ambientales'),
    ('comercio_administracion', 'Facultad de Comercio Internacional, Integración, Administración y Economía Empresarial'),
    ('administracion_central', 'Administración central u otra dependencia UPEC'),
    ('otra', 'Otra facultad o dependencia UPEC'),
    ('externo', 'Externo a la Universidad'),
]

CARRERAS = [
    ('enfermeria', 'Carrera de Enfermería'),
    ('laboratorio_clinico', 'Carrera de Laboratorio Clínico'),
    ('educacion_inicial', 'Carrera de Educación Inicial'),
    ('educacion_basica', 'Carrera de Educación Básica'),
    ('multimedia_audiovisual', 'Carrera de Multimedia y Producción Audiovisual'),
    ('actividad_fisica_deporte', 'Carrera de Ciencias de la Actividad Física y Deporte'),
    ('veterinaria', 'Carrera de Veterinaria'), ('agropecuaria', 'Carrera de Agropecuaria'),
    ('alimentos', 'Carrera de Alimentos'), ('computacion', 'Carrera de Computación'),
    ('administracion_empresas', 'Carrera de Administración de Empresas'),
    ('administracion_publica', 'Carrera de Administración Pública'),
    ('comercio_exterior', 'Carrera de Comercio Exterior'),
    ('logistica_transporte', 'Carrera de Logística y Transporte'),
    ('contabilidad_auditoria', 'Carrera de Contabilidad y Auditoría'),
    ('docente', 'Personal Docente'), ('administrativo', 'Personal Administrativo'),
    ('investigador', 'Investigador'), ('egresado', 'Egresado'), ('otro', 'Otro'),
]

NIVELES = [
    ('primer_semestre', '1er Semestre'), ('segundo_semestre', '2do Semestre'),
    ('tercer_semestre', '3er Semestre'), ('cuarto_semestre', '4to Semestre'),
    ('quinto_semestre', '5to Semestre'), ('sexto_semestre', '6to Semestre'),
    ('septimo_semestre', '7mo Semestre'), ('octavo_semestre', '8vo Semestre'),
    ('noveno_semestre', '9no Semestre'), ('decimo_semestre', '10mo Semestre'),
    ('pasantias', 'Pasantías'), ('tesis', 'Desarrollo de Tesis'),
    ('egresado', 'Egresado'), ('posgrado', 'Posgrado'), ('maestria', 'Maestría'),
    ('doctorado', 'Doctorado'), ('docente', 'Personal Docente'),
    ('administrativo', 'Personal Administrativo'), ('investigador', 'Investigador'),
    ('visitante', 'Estudiante de Intercambio'),
]


def clasificar_datos_existentes(apps, schema_editor):
    UserProfile = apps.get_model('webcitt', 'UserProfile')
    Reserva = apps.get_model('webcitt', 'Reserva')
    SoftwareDisponible = apps.get_model('webcitt', 'SoftwareDisponible')

    facultad_por_carrera = {
        'enfermeria': 'salud_educacion', 'laboratorio_clinico': 'salud_educacion',
        'educacion_inicial': 'salud_educacion', 'educacion_basica': 'salud_educacion',
        'multimedia_audiovisual': 'salud_educacion', 'actividad_fisica_deporte': 'salud_educacion',
        'veterinaria': 'agropecuarias_ambientales', 'agropecuaria': 'agropecuarias_ambientales',
        'alimentos': 'agropecuarias_ambientales', 'computacion': 'agropecuarias_ambientales',
        'administracion_empresas': 'comercio_administracion',
        'administracion_publica': 'comercio_administracion',
        'comercio_exterior': 'comercio_administracion',
        'logistica_transporte': 'comercio_administracion',
        'contabilidad_auditoria': 'comercio_administracion',
    }
    niveles_estudiante = {
        'primer_semestre', 'segundo_semestre', 'tercer_semestre', 'cuarto_semestre',
        'quinto_semestre', 'sexto_semestre', 'septimo_semestre', 'octavo_semestre',
        'noveno_semestre', 'decimo_semestre',
    }
    for perfil in UserProfile.objects.all():
        institucion = (perfil.institucion or '').lower()
        if institucion and 'upec' not in institucion and 'politécnica estatal del carchi' not in institucion:
            perfil.tipo_usuario = 'externo'
            perfil.facultad = 'externo'
        else:
            if perfil.nivel_academico in niveles_estudiante:
                perfil.tipo_usuario = 'estudiante'
            elif perfil.nivel_academico in {'docente', 'administrativo', 'investigador'}:
                perfil.tipo_usuario = perfil.nivel_academico
            elif perfil.carrera in {'docente', 'administrativo', 'investigador', 'egresado'}:
                perfil.tipo_usuario = perfil.carrera
                perfil.carrera = ''
            elif perfil.carrera in facultad_por_carrera:
                perfil.tipo_usuario = 'estudiante'
            perfil.facultad = facultad_por_carrera.get(perfil.carrera, perfil.facultad)
            if perfil.tipo_usuario:
                perfil.institucion = perfil.institucion or 'UPEC'
        perfil.save(update_fields=['tipo_usuario', 'facultad', 'carrera', 'institucion'])

    perfiles = {perfil.user_id: perfil for perfil in UserProfile.objects.all()}
    for reserva in Reserva.objects.exclude(usuario_id=None):
        perfil = perfiles.get(reserva.usuario_id)
        if not perfil:
            continue
        reserva.tipo_usuario_solicitante = perfil.tipo_usuario
        reserva.facultad_solicitante = perfil.facultad
        reserva.carrera_solicitante = perfil.carrera or ''
        reserva.nivel_academico_solicitante = perfil.nivel_academico or ''
        reserva.save(update_fields=[
            'tipo_usuario_solicitante', 'facultad_solicitante',
            'carrera_solicitante', 'nivel_academico_solicitante',
        ])

    SoftwareDisponible.objects.filter(tipo_acceso__in=['licencia', 'red']).update(
        tipo_recurso='licencia'
    )


class Migration(migrations.Migration):

    dependencies = [('webcitt', '0104_flujos_software_servicios_cotizacion')]

    operations = [
        migrations.AddField(
            model_name='softwaredisponible', name='tipo_recurso',
            field=models.CharField(
                choices=[
                    ('software', 'Software instalado o de libre acceso'),
                    ('licencia', 'Licencia institucional'),
                ],
                default='software',
                help_text='Diferencia el programa disponible de una licencia institucional limitada.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='userprofile', name='tipo_usuario',
            field=models.CharField(
                blank=True, choices=TIPOS_USUARIO,
                help_text='Clasificación institucional usada para validación y reportes.',
                max_length=20, verbose_name='Tipo de usuario',
            ),
        ),
        migrations.AddField(
            model_name='userprofile', name='facultad',
            field=models.CharField(
                blank=True, choices=FACULTADES, max_length=50,
                verbose_name='Facultad o dependencia',
            ),
        ),
        migrations.AddField(
            model_name='reserva', name='tipo_usuario_solicitante',
            field=models.CharField(
                blank=True, choices=TIPOS_USUARIO,
                help_text='Clasificación del usuario conservada al momento de solicitar.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='reserva', name='facultad_solicitante',
            field=models.CharField(
                blank=True, choices=FACULTADES,
                help_text='Facultad o dependencia conservada al momento de solicitar.',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='reserva', name='carrera_solicitante',
            field=models.CharField(
                blank=True, choices=CARRERAS,
                help_text='Carrera conservada al momento de solicitar.',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='reserva', name='nivel_academico_solicitante',
            field=models.CharField(
                blank=True, choices=NIVELES,
                help_text='Nivel académico conservado al momento de solicitar.',
                max_length=30,
            ),
        ),
        migrations.RunPython(clasificar_datos_existentes, migrations.RunPython.noop),
    ]
