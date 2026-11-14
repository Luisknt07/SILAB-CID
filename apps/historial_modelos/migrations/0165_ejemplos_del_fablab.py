"""El FabLab conserva sus ejemplos de redacción, ahora como datos suyos.

Los textos vivían escritos en el asistente y se mostraban en todas las
unidades. Aquí pasan a ser filas del laboratorio que los escribió, para que
sigan apareciendo donde tienen sentido y desaparezcan del resto.
"""

from django.db import migrations

SLUG = 'laboratorio-manufactura-digital-prototipado-prueba'

EJEMPLOS = {
    'servicio': {
        'checklist': [
            'Qué pieza o resultado necesitas y para qué proyecto, asignatura o uso.',
            'Cuántas piezas y sus dimensiones aproximadas.',
            'Material, color y acabado deseados; tolerancias si importan.',
            'Qué archivos entregas (STL, planos, referencias) o si el laboratorio diseñará.',
            'Fecha en la que lo necesitas y cualquier condición especial.',
        ],
        'ejemplo': (
            'Necesito fabricar la carcasa de un prototipo de sensor de humedad '
            'para el proyecto de investigación sobre riego inteligente. Son dos '
            'piezas de 80 × 40 × 20 mm en PLA rojo, con tapa a presión y dos '
            'orificios laterales para el paso de cables; requiero acabado natural '
            'sin soportes visibles y una tolerancia de 0,3 mm para el ensamblaje '
            'con la placa electrónica. Adjunto el modelo STL ya laminado y '
            'necesito la entrega antes de la feria de proyectos del próximo mes.'
        ),
    },
    'docencia_practica': {
        'checklist': [],
        'ejemplo': (
            'Con el grupo de tercer semestre de la asignatura Diseño Asistido por '
            'Computador realizaremos la práctica de modelado e impresión de una '
            'pieza mecánica sencilla. Cada estudiante diseñará un soporte en el '
            'software CAD de la estación de trabajo, lo preparará en el laminador '
            'y lo imprimirá en la impresora 3D FDM con filamento PLA del '
            'laboratorio. Buscamos que apliquen tolerancias de ensamble, calculen '
            'tiempos de impresión y registren el consumo de material en una tabla '
            'de evidencias; usaremos dos horas por sesión durante cuatro semanas.'
        ),
    },
    'investigacion_innovacion': {
        'checklist': [],
        'ejemplo': (
            'Para el proyecto de riego inteligente necesitamos imprimir en la '
            'impresora 3D FDM las carcasas de tres sensores de humedad y probar su '
            'ensamble con la placa electrónica en la estación de soldadura. '
            'Participamos dos investigadores del grupo de sistemas embebidos; '
            'usaremos filamento PLA del laboratorio y traeremos los modelos STL. '
            'Prevemos dos sesiones de tres horas para imprimir, ajustar '
            'tolerancias y documentar el montaje.'
        ),
    },
    'vinculacion': {
        'checklist': [],
        'ejemplo': (
            'Con el programa de vinculación con la junta parroquial elaboraremos '
            'señalética en corte láser para el centro comunitario. Participan '
            'cuatro estudiantes y el docente responsable; usaremos la cortadora '
            'láser con MDF del laboratorio y el software de diseño de la estación '
            'de trabajo. Esperamos veinte piezas listas para instalar y '
            'necesitamos dos sesiones de dos horas.'
        ),
    },
    'capacitacion': {
        'checklist': [],
        'ejemplo': (
            'Dictaremos el taller de introducción al modelado 3D para doce '
            'docentes de la facultad. Usaremos la estación de trabajo CAD con el '
            'software instalado y la impresora 3D FDM para una demostración final. '
            'Necesitamos la sala con proyector durante tres sesiones de dos horas; '
            'los participantes no traen materiales.'
        ),
    },
    'servicio_cientifico_tecnologico': {
        'checklist': [],
        'ejemplo': (
            'Realizaremos el escaneo 3D y la medición dimensional de una pieza '
            'mecánica para una empresa local que solicitó el ensayo. Usaremos el '
            'escáner 3D de objetos y el software de inspección de la estación de '
            'trabajo; entregaremos un informe con las desviaciones encontradas. '
            'Necesitamos una sesión de tres horas y traeremos la pieza con su plano.'
        ),
    },
    'titulacion': {
        'checklist': [],
        'ejemplo': (
            'Para mi trabajo de titulación sobre prótesis de bajo costo imprimiré '
            'en la impresora 3D de resina dos prototipos de una articulación y '
            'verificaré su ajuste en la estación de trabajo. Traeré los modelos '
            'STL ya laminados y usaré resina del laboratorio; necesito dos '
            'sesiones de tres horas con acompañamiento del laboratorista para el '
            'curado y el postprocesado.'
        ),
    },
    'otro': {
        'checklist': [],
        'ejemplo': (
            'Necesitamos usar la sala de trabajo colaborativo con su mobiliario '
            'para la reunión de planificación del club de robótica, con diez '
            'integrantes. Solo requerimos el proyector y una estación de trabajo '
            'para presentar los avances; no usaremos equipos de fabricación ni '
            'insumos del laboratorio. La sesión durará dos horas.'
        ),
    },
}


def cargar(apps, schema_editor):
    Unidad = apps.get_model('webcitt', 'Unidad')
    Ejemplo = apps.get_model('webcitt', 'EjemploSolicitudUnidad')
    unidad = Unidad.objects.filter(slug=SLUG).first()
    if not unidad:
        return
    for codigo, datos in EJEMPLOS.items():
        Ejemplo.objects.update_or_create(
            unidad=unidad,
            proposito_codigo=codigo,
            defaults={
                'ejemplo': datos['ejemplo'],
                'checklist': datos['checklist'],
                'activo': True,
            },
        )


def borrar(apps, schema_editor):
    Unidad = apps.get_model('webcitt', 'Unidad')
    Ejemplo = apps.get_model('webcitt', 'EjemploSolicitudUnidad')
    unidad = Unidad.objects.filter(slug=SLUG).first()
    if unidad:
        Ejemplo.objects.filter(unidad=unidad).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0164_ejemplo_de_redaccion_por_unidad'),
    ]

    operations = [
        migrations.RunPython(cargar, borrar),
    ]
