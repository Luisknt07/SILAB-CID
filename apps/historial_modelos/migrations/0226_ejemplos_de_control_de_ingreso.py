"""El control de ingreso también necesitaba un caso para poder revisarse.

El reporte de seguridad leía bien su tabla, pero sin un solo ingreso
registrado no se veía ni la evidencia de inducción que pide el expediente ni
el caso que de verdad importa: la persona que llegó sin protección y no
entró. Se registran sobre reservas ya atendidas de la unidad.
"""

from django.db import migrations

# (desplazamiento sobre las reservas, nombre, categoría, ingresa, motivo,
#  protección, restricciones, habilitaciones, pendientes)
INGRESOS = (
    (0, 'Ana Lucía Chamorro', 'estudiante', True, '', True, True, True, []),
    (0, 'Diego Fernando Ruiz', 'estudiante', True, '', True, True, True, []),
    (0, 'Kevin Alexander Pozo', 'estudiante', False,
     'Llegó en sandalias: el laboratorio exige calzado cerrado.', False, True, True,
     ['Calzado cerrado']),
    (1, 'María José Benavides', 'docente', True, '', True, True, True, []),
    (1, 'Santiago Andrés Cuásquer', 'estudiante', True,
     'Ingresa con gafas prestadas por la unidad.', True, True, False, ['Inducción de seguridad']),
    (2, 'Visita del Colegio Bolívar', 'externo', True,
     'Recorrido guiado, sin operar equipos.', True, True, True, []),
)


def sembrar(apps, schema_editor):
    Reserva = apps.get_model('webcitt', 'Reserva')
    RegistroIngreso = apps.get_model('webcitt', 'RegistroIngreso')
    Unidad = apps.get_model('webcitt', 'Unidad')

    unidad = Unidad.objects.filter(
        slug='laboratorio-manufactura-digital-prototipado-prueba').first()
    if not unidad:
        return
    reservas = list(
        Reserva.objects.filter(laboratorio=unidad, estado__in=['completada', 'aprobada'])
        .order_by('-fecha')[:3]
    )
    if not reservas:
        return
    for (indice, nombre, categoria, ingresa, motivo, proteccion, restricciones,
         habilitaciones, pendientes) in INGRESOS:
        if indice >= len(reservas):
            continue
        reserva = reservas[indice]
        if RegistroIngreso.objects.filter(reserva=reserva, nombre=nombre).exists():
            continue
        RegistroIngreso.objects.create(
            reserva=reserva, nombre=nombre, categoria=categoria, ingresa=ingresa, motivo=motivo,
            hora_ingreso=reserva.hora_inicio if ingresa else None,
            hora_salida=reserva.hora_fin if ingresa else None,
            proteccion_verificada=proteccion, restricciones_verificadas=restricciones,
            habilitaciones_vigentes=habilitaciones, pendientes=pendientes,
        )


def retirar(apps, schema_editor):
    RegistroIngreso = apps.get_model('webcitt', 'RegistroIngreso')
    RegistroIngreso.objects.filter(nombre__in=[fila[1] for fila in INGRESOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0225_ejemplos_de_prestamos_desechos_e_ingresos'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
