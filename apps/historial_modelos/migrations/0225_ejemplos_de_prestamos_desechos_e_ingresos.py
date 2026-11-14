"""Tres evidencias que salían en cero porque nunca se habían registrado.

El reporte existía y leía bien su tabla, pero la tabla estaba vacía: sin un
préstamo, un desecho ni un ingreso registrados no hay forma de ver cómo se
llena el expediente ni de revisar si las columnas dicen lo que la auditoría
pide. Aquí quedan casos de los que la unidad va a repetir, con sus dos caras:
lo que salió bien y lo que quedó pendiente.

Son datos de partida: la unidad los edita o los borra desde la consola.
"""

from datetime import date, datetime, timedelta, timezone as utc
from decimal import Decimal

from django.db import migrations

# (código del activo, tipo, estado, quién retira, institución, autoriza, propósito,
#  día de salida, días de plazo, día de retorno real, condición de retorno, acta)
PRESTAMOS = (
    ('FAB-UNIT-SCAN-01', 'externo', 'devuelto', 'Ing. Marcela Terán', 'Colegio Técnico Bolívar',
     'Dirección de Vinculación', 'Demostración de escaneo 3D en la feria de ciencia del colegio.',
     date(2026, 7, 14), 3, date(2026, 7, 17), 'bueno', True,
     'Se entregó con maletín, trípode y placa de calibración. Volvió completo y calibrado.'),
    ('FAB-UNIT-CAD-02', 'interno', 'devuelto', 'Docente de Diseño Industrial', 'Carrera de Diseño Industrial',
     '', 'Renderizado de un proyecto de titulación durante la semana de entregas.',
     date(2026, 8, 3), 7, date(2026, 8, 12), 'observado', False,
     'Volvió cinco días tarde y con el cable de poder rayado; se repuso el cable.'),
    ('FAB-UNIT-VINIL-01', 'externo', 'entregado', 'Sra. Patricia Yépez', 'Junta Parroquial de Julio Andrade',
     'Dirección de Vinculación', 'Señalética del centro comunitario, convenio de vinculación.',
     date(2026, 9, 14), 10, None, '', True,
     'Salió con dos rollos de vinilo de la unidad, descontados del inventario.'),
    ('FAB-UNIT-ELEC-01', 'interno', 'entregado', 'Laboratorio de Robótica', 'Laboratorio de Robótica',
     '', 'Armado de la placa de control del brazo didáctico.',
     date(2026, 8, 24), 14, None, '', False,
     'Plazo vencido: se recordó por correo y sigue sin volver.'),
)

# (día, clase, clave, nombre, origen, estado físico, cantidad, unidad, envase, etapa,
#  día de entrega, gestor, licencia, manifiesto)
DESECHOS = (
    (date(2026, 7, 8), 'peligroso', 'NE-43', 'Resina fotopolimérica no curada',
     'Impresión 3D de resina: purga del tanque y sobrantes', 'liquido', '3.500', 'l',
     'Bidón HDPE de 5 L, etiquetado', 'entregado', date(2026, 7, 30),
     'Gestión Ambiental del Norte', 'MAE-GA-0127', 'MF-2026-0431'),
    (date(2026, 7, 22), 'peligroso', 'NE-06', 'Alcohol isopropílico contaminado con resina',
     'Lavado de piezas impresas en resina', 'liquido', '5.000', 'l',
     'Bidón HDPE de 10 L, etiquetado', 'entregado', date(2026, 7, 30),
     'Gestión Ambiental del Norte', 'MAE-GA-0127', 'MF-2026-0431'),
    (date(2026, 8, 19), 'especial', 'ES-02', 'Filamento y soportes de impresión descartados',
     'Prácticas de impresión FDM: soportes, purgas y piezas falladas', 'solido', '4.200', 'kg',
     'Saco de rafia rotulado', 'almacenado', None, '', '', ''),
    (date(2026, 9, 2), 'peligroso', 'NE-40', 'Trapos y guantes impregnados de resina',
     'Limpieza del tanque de la impresora de resina', 'solido', '1.100', 'kg',
     'Funda roja en el acopio temporal', 'almacenado', None, '', '', ''),
    (date(2026, 9, 9), 'especial', 'ES-05', 'Placas electrónicas y cables fuera de uso',
     'Baja de equipos electrónicos del laboratorio', 'solido', '2.800', 'kg',
     'Caja de cartón rotulada', 'almacenado', None, '', '', ''),
)


def _momento(dia, hora=9):
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=utc.utc)


def sembrar(apps, schema_editor):
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')
    PrestamoEquipo = apps.get_model('webcitt', 'PrestamoEquipo')
    BloqueoAgendaUnidad = apps.get_model('webcitt', 'BloqueoAgendaUnidad')
    RegistroDesecho = apps.get_model('webcitt', 'RegistroDesecho')

    activos = {
        equipo.codigo_unidad: equipo
        for equipo in UnidadEquipo.objects.filter(
            codigo_unidad__in=[codigo for codigo, *_ in PRESTAMOS]).select_related('laboratorio')
    }
    unidad = next((equipo.laboratorio for equipo in activos.values() if equipo.laboratorio_id), None)

    for (codigo, tipo, estado, quien, institucion, autoriza, proposito, salida, plazo,
         retorno, condicion, con_acta, nota) in PRESTAMOS:
        equipo = activos.get(codigo)
        if not equipo or not equipo.laboratorio_id:
            continue
        if PrestamoEquipo.objects.filter(equipo=equipo, proposito=proposito).exists():
            continue
        prestamo = PrestamoEquipo.objects.create(
            equipo=equipo, unidad_id=equipo.laboratorio_id, tipo=tipo, estado=estado,
            nombre_solicitante=quien, institucion=institucion, autorizado_por=autoriza,
            proposito=proposito, fecha_salida=_momento(salida),
            fecha_retorno_previsto=_momento(salida + timedelta(days=plazo), 17),
            fecha_retorno_real=_momento(retorno, 16) if retorno else None,
            condicion_salida='bueno', condicion_retorno=condicion,
            observaciones_salida=nota if estado != 'devuelto' else '',
            observaciones_retorno=nota if estado == 'devuelto' else '',
            estado_equipo_previo='disponible' if estado == 'entregado' else '',
            bloquea_agenda=True,
        )
        # El acta se declara sin archivo: la unidad sube el escaneado.
        if estado == 'entregado':
            # El activo está afuera: el calendario y el estado lo reflejan.
            UnidadEquipo.objects.filter(pk=equipo.pk).update(estado_unidad='prestado')
            bloqueo = BloqueoAgendaUnidad.objects.create(
                unidad_id=equipo.laboratorio_id, prestamo=prestamo, tipo='prestamo',
                titulo=f'{prestamo.codigo} · {equipo.codigo_unidad} prestado'[:160],
                motivo=f'{quien}. {proposito}',
                fecha_inicio=salida, fecha_fin=salida + timedelta(days=plazo),
                dia_completo=True, alcance='equipos', bloquea_recursos=True,
                bloquea_servicios=True, visible_en_agenda=True, activo=True,
            )
            bloqueo.equipos.set([equipo.pk])

    if not unidad:
        return
    for (dia, clase, clave, nombre, origen, fisico, cantidad, medida, envase, etapa,
         entrega, gestor, licencia, manifiesto) in DESECHOS:
        if RegistroDesecho.objects.filter(unidad=unidad, fecha_generacion=dia, nombre=nombre).exists():
            continue
        RegistroDesecho.objects.create(
            unidad=unidad, fecha_generacion=dia, clase=clase, clave_listado=clave, nombre=nombre,
            origen=origen, estado_fisico=fisico, cantidad=Decimal(cantidad), unidad_medida=medida,
            envase=envase, etiquetado=True, almacenamiento='Acopio temporal del laboratorio',
            etapa=etapa, fecha_entrega=entrega, gestor_autorizado=gestor,
            licencia_gestor=licencia, manifiesto=manifiesto,
        )


def retirar(apps, schema_editor):
    PrestamoEquipo = apps.get_model('webcitt', 'PrestamoEquipo')
    RegistroDesecho = apps.get_model('webcitt', 'RegistroDesecho')
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')

    prestados = list(
        PrestamoEquipo.objects.filter(proposito__in=[p[6] for p in PRESTAMOS])
        .values_list('equipo_id', flat=True))
    PrestamoEquipo.objects.filter(proposito__in=[p[6] for p in PRESTAMOS]).delete()
    UnidadEquipo.objects.filter(pk__in=prestados, estado_unidad='prestado').update(
        estado_unidad='disponible')
    RegistroDesecho.objects.filter(nombre__in=[d[3] for d in DESECHOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0224_evidencias_que_faltaban_en_el_expediente'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
