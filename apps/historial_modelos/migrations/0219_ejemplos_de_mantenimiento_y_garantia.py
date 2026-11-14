"""Ejemplos diversos de mantenimiento, garantía y cambio de piezas.

El seguimiento se entiende cuando se ve funcionando. Aquí quedan, para el
laboratorio de manufactura digital, los tres casos que la unidad va a repetir:

1. Lo que resuelve el laboratorista o el técnico de la unidad: limpieza,
   calibración y cambio de piezas de desgaste.
2. Lo que exige técnico especializado externo: óptica, potencia del tubo,
   husillo y calibración certificada.
3. Lo que cubre la garantía del proveedor mientras está vigente, que se
   registra igual aunque no cueste nada a la unidad.

Todo es dato de partida: la unidad lo edita o lo borra desde el administrador.
"""

from datetime import date, datetime, timedelta, timezone as utc

from django.db import migrations

PROVEEDOR_OPTICA = 'Servicio técnico autorizado (ejemplo) · soporte@proveedor.ejemplo'
PROVEEDOR_CNC = 'Metalmecánica de precisión (ejemplo) · calibracion@proveedor.ejemplo'
CONTACTO = 'Proveedor adjudicado del contrato de compra · garantias@proveedor.ejemplo'

# Piezas de desgaste de las que la unidad sí guarda repuesto. Lo que no está
# aquí queda en «sin repuesto»: es justo lo que hay que presupuestar.
CON_REPUESTO = (
    ('FAB-EQ-FDM', 'Boquilla (nozzle) 0,4 mm'),
    ('FAB-EQ-FDM', 'Cama de impresión con lámina PEI'),
    ('FAB-EQ-FDM', 'Espátula de desmontaje'),
    ('FAB-EQ-FDM', 'Juego de llaves Allen'),
    ('FAB-EQ-FDM', 'Regulador de voltaje o UPS'),
    ('FAB-EQ-SLA', 'Película FEP del tanque'),
    ('FAB-EQ-SLA', 'Guantes de nitrilo y gafas'),
    ('FAB-EQ-CNC', 'Fresas y brocas'),
    ('FAB-EQ-CNC', 'Juego de pinzas y llaves de husillo'),
    ('FAB-EQ-LASER', 'Espejos y lente de enfoque'),
    ('FAB-EQ-LASER', 'Panal y rejilla de trabajo'),
    ('FAB-EQ-VINIL', 'Cuchilla de corte'),
    ('FAB-EQ-CAD', 'Regulador de voltaje o UPS'),
    ('FAB-EQ-SCAN', 'Marcadores de calibración'),
)

# Equipos que entraron hace poco: su garantía sigue corriendo.
RECIEN_ADQUIRIDOS = (
    ('FAB-UNIT-FDM-03', date(2026, 6, 15)),
    ('FAB-UNIT-VINIL-01', date(2026, 3, 10)),
)

# (código, nombre, tipo, frecuencia, ejecutor, próxima, proveedor, instrucciones)
PLANES = (
    ('FAB-UNIT-FDM-01', 'Limpieza, nivelación y tensión de correas', 'preventivo', 30,
     'interno', date(2026, 10, 5), '',
     'Limpiar la lámina con alcohol isopropílico, revisar la tensión de las correas, '
     'verificar el nivel de la cama y soplar el polvo de los ventiladores.'),
    ('FAB-UNIT-FDM-01', 'Cambio de boquilla por horas de uso', 'preventivo', 180,
     'interno', date(2026, 11, 20), '',
     'Cambiar la boquilla al acumular 800 horas de extrusión o antes si el filamento '
     'sale torcido. Calentar el hotend para aflojarla y apretar en caliente.'),
    ('FAB-UNIT-SLA-01', 'Cambio de película FEP y limpieza del tanque', 'preventivo', 60,
     'interno', date(2026, 10, 15), '',
     'Filtrar la resina, lavar el tanque y sustituir la película ante cualquier marca. '
     'Usar guantes de nitrilo y gafas durante todo el procedimiento.'),
    ('FAB-UNIT-LASER-01', 'Limpieza de óptica y revisión de la extracción', 'preventivo', 30,
     'interno', date(2026, 10, 2), '',
     'Limpiar espejos y lente con paño de óptica, revisar el filtro del extractor y '
     'comprobar el nivel y la temperatura del agua de refrigeración.'),
    ('FAB-UNIT-LASER-01', 'Calibración de potencia y alineación del tubo', 'calibracion', 365,
     'externo', date(2027, 4, 18), PROVEEDOR_OPTICA,
     'Requiere instrumental del proveedor: medición de potencia del tubo, alineación '
     'de los tres espejos y certificado de calibración para el expediente.'),
    ('FAB-UNIT-CNC-01', 'Calibración de ejes y lubricación de guías', 'calibracion', 180,
     'externo', date(2026, 12, 10), PROVEEDOR_CNC,
     'Verificación de perpendicularidad, juego de husillos de bolas y lubricación de '
     'guías lineales con el instrumental del proveedor.'),
    ('FAB-UNIT-SCAN-01', 'Verificación de precisión con placa patrón', 'calibracion', 365,
     'externo', date(2027, 2, 20), PROVEEDOR_OPTICA,
     'Contraste contra patrón certificado y emisión del informe de precisión.'),
    ('FAB-UNIT-CAD-01', 'Limpieza interna y actualización de controladores', 'preventivo', 120,
     'interno', date(2026, 11, 8), '',
     'Soplar disipadores y fuente, revisar el regulador de voltaje y actualizar los '
     'controladores de la tarjeta gráfica y el software de diseño.'),
    ('FAB-UNIT-FDM-03', 'Revisión preventiva incluida en la garantía', 'inspeccion', 180,
     'garantia', date(2026, 12, 15), CONTACTO,
     'El proveedor realiza dos visitas preventivas dentro de los doce meses de '
     'garantía. Se agenda con él y se archiva su informe.'),
)

# (código del activo, título, tipo, ejecutor, fecha, horas que duró, costo del
#  servicio, proveedor, descripción, resultado, repuestos). El costo de la orden
#  es la mano de obra: los repuestos suman aparte, con su cantidad y su precio.
ORDENES = (
    ('FAB-UNIT-FDM-01', 'Reemplazo de la lámina PEI rayada', 'correctivo', 'interno',
     date(2026, 2, 3), 2, '0.00', '',
     'Las piezas dejaron de adherirse en la zona central de la cama.',
     'Se retiró la lámina, se limpió el vidrio con alcohol y se colocó una lámina PEI '
     'nueva del inventario. Se renivelo la cama en nueve puntos y se imprimió una '
     'pieza de prueba con adherencia correcta en toda la superficie.',
     (('Cama de impresión con lámina PEI', 'Lámina PEI texturizada 250 × 210 mm', '1',
       '28.00', 'compra', 'La anterior duró dieciocho meses.'),)),
    ('FAB-UNIT-FDM-01', 'Cambio de boquilla obstruida', 'correctivo', 'interno',
     date(2026, 5, 12), 1, '0.00', '',
     'Extrusión intermitente y filamento saliendo torcido tras un trabajo con PETG.',
     'Se calentó el hotend a 240 °C, se retiró la boquilla obstruida y se instaló una '
     'nueva de 0,4 mm de latón apretándola en caliente. Se recalibró el offset del eje '
     'Z y se verificó el flujo con un cubo de prueba.',
     (('Boquilla (nozzle) 0,4 mm', 'Boquilla de latón 0,4 mm', '1', '12.50', 'inventario',
       'Acumulaba 840 horas de extrusión.'),)),
    ('FAB-UNIT-FDM-01', 'Limpieza mensual y tensión de correas', 'preventivo', 'interno',
     date(2026, 8, 10), 1, '0.00', '',
     'Rutina mensual del plan preventivo.',
     'Limpieza de la lámina, revisión de la tensión de las correas de los ejes X e Y, '
     'lubricación de las varillas y soplado de los ventiladores. Sin repuestos.',
     ()),
    ('FAB-UNIT-SLA-01', 'Cambio de película FEP del tanque', 'preventivo', 'interno',
     date(2026, 9, 1), 2, '0.00', '',
     'La película mostraba una marca blanquecina tras un desprendimiento.',
     'Se filtró la resina, se lavó el tanque con alcohol isopropílico y se montó una '
     'película FEP nueva con la tensión recomendada. Prueba de exposición correcta.',
     (('Película FEP del tanque', 'Película FEP 200 × 140 mm', '1', '18.00', 'inventario',
       'Pieza de desgaste: la garantía no la cubre.'),)),
    ('FAB-UNIT-LASER-01', 'Alineación del tubo y reemplazo de la lente de enfoque',
     'correctivo', 'externo', date(2026, 4, 20), 6, '50.00', PROVEEDOR_OPTICA,
     'Corte irregular en el extremo derecho de la mesa y pérdida de potencia.',
     'El técnico del proveedor alineó los tres espejos, midió la potencia del tubo '
     '(dentro de rango) y sustituyó la lente de enfoque, que presentaba una quemadura. '
     'Entregó informe de alineación. Exige instrumental propio: no lo ejecuta la unidad.',
     (('Espejos y lente de enfoque', 'Lente de enfoque 50,8 mm', '1', '145.00', 'compra',
       'La mano de obra del técnico se registra en el costo de la orden.'),)),
    ('FAB-UNIT-CNC-01', 'Calibración de ejes y lubricación de guías', 'calibracion',
     'externo', date(2026, 6, 2), 5, '250.00', PROVEEDOR_CNC,
     'Calibración anual exigida por el plan y por el expediente de calidad.',
     'Verificación de perpendicularidad de los tres ejes, ajuste del juego de los '
     'husillos de bolas y lubricación de guías. Se emitió certificado de calibración, '
     'que se archiva en el expediente de la unidad.',
     ()),
    ('FAB-UNIT-FDM-03', 'Reemplazo del extrusor cubierto por la garantía', 'correctivo',
     'garantia', date(2026, 8, 20), 3, '0.00', CONTACTO,
     'El engranaje de arrastre patinaba desde la primera semana de uso.',
     'El proveedor reconoció el defecto de fabricación dentro de los doce meses de '
     'garantía y reemplazó el conjunto extrusor completo. Sin costo para la unidad: '
     'la garantía cubre partes y mano de obra. Queda registrado para la trazabilidad '
     'del activo y como antecedente ante el proveedor.',
     (('Extrusor y engranaje de arrastre', 'Conjunto extrusor completo', '1', '0.00',
       'garantia', 'Cubierto por la garantía del proveedor.'),)),
)

# (código del activo, título, tipo, prioridad, estado, detiene, fecha, descripción, solución)
INCIDENCIAS = (
    ('FAB-UNIT-LASER-01', 'Corte irregular en el extremo derecho de la mesa', 'falla',
     'alta', 'resuelta', True, date(2026, 4, 17),
     'El corte no atraviesa el MDF de 3 mm en el tercio derecho de la mesa, con la '
     'misma potencia con la que sí lo hace a la izquierda.',
     'Se derivó al proveedor: la lente de enfoque estaba quemada y los espejos '
     'desalineados. Resuelto con la orden de mantenimiento externa.'),
    ('FAB-UNIT-FDM-02', 'Ruido del ventilador de capa', 'desgaste', 'baja', 'abierta',
     False, date(2026, 9, 10),
     'El ventilador de capa hace un zumbido intermitente al superar el 60 % de '
     'velocidad. El equipo sigue imprimiendo con calidad normal.',
     ''),
)


def _momento(dia, hora=9):
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=utc.utc)


def sembrar(apps, schema_editor):
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')
    PiezaEquipo = apps.get_model('webcitt', 'PiezaEquipo')
    Plan = apps.get_model('webcitt', 'PlanMantenimientoEquipo')
    Orden = apps.get_model('webcitt', 'MantenimientoEquipo')
    Repuesto = apps.get_model('webcitt', 'RepuestoMantenimiento')
    Incidencia = apps.get_model('webcitt', 'IncidenciaEquipo')

    activos = {
        equipo.codigo_unidad: equipo
        for equipo in UnidadEquipo.objects.filter(
            codigo_unidad__in={c for c, *_ in RECIEN_ADQUIRIDOS}
            | {p[0] for p in PLANES} | {o[0] for o in ORDENES} | {i[0] for i in INCIDENCIAS})
    }

    for codigo_tipo, nombre in CON_REPUESTO:
        PiezaEquipo.objects.filter(equipo__codigo=codigo_tipo, nombre=nombre).update(
            repuesto_disponible=True)

    for codigo, adquisicion in RECIEN_ADQUIRIDOS:
        equipo = activos.get(codigo)
        if equipo and not equipo.fecha_adquisicion:
            equipo.fecha_adquisicion = adquisicion
            equipo.save(update_fields=['fecha_adquisicion'])

    UnidadEquipo.objects.filter(
        codigo_unidad__startswith='FAB-UNIT-', garantia_contacto=''
    ).exclude(garantia_meses=0).update(garantia_contacto=CONTACTO)

    for codigo, nombre, tipo, frecuencia, ejecutor, proxima, proveedor, instrucciones in PLANES:
        equipo = activos.get(codigo)
        if not equipo or Plan.objects.filter(equipo=equipo, nombre=nombre).exists():
            continue
        Plan.objects.create(
            equipo=equipo, nombre=nombre, tipo=tipo, frecuencia_dias=frecuencia,
            ejecutor=ejecutor, proveedor=proveedor, instrucciones=instrucciones,
            fecha_inicio=proxima - timedelta(days=frecuencia), proxima_ejecucion=proxima,
            responsable=equipo.laboratorio.administrador if equipo.laboratorio else None,
        )

    for (codigo, titulo, tipo, ejecutor, dia, horas, costo, proveedor,
         descripcion, resultado, repuestos) in ORDENES:
        equipo = activos.get(codigo)
        if not equipo or Orden.objects.filter(equipo=equipo, titulo=titulo).exists():
            continue
        inicio = _momento(dia)
        orden = Orden.objects.create(
            equipo=equipo, unidad=equipo.laboratorio, tipo=tipo, estado='completado',
            titulo=titulo, descripcion=descripcion, resultado=resultado,
            fecha_programada=inicio, fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(hours=horas), ejecutor=ejecutor,
            proveedor=proveedor, costo=costo,
            responsable=equipo.laboratorio.administrador if equipo.laboratorio else None,
        )
        for pieza_nombre, detalle, cantidad, unitario, procedencia, observacion in repuestos:
            Repuesto.objects.create(
                mantenimiento=orden, descripcion=detalle, cantidad=cantidad,
                costo_unitario=unitario, procedencia=procedencia, observacion=observacion,
                pieza=PiezaEquipo.objects.filter(
                    equipo=equipo.equipo, nombre=pieza_nombre).first(),
            )

    for (codigo, titulo, tipo, prioridad, estado, detiene, dia,
         descripcion, solucion) in INCIDENCIAS:
        equipo = activos.get(codigo)
        if not equipo or Incidencia.objects.filter(equipo=equipo, titulo=titulo).exists():
            continue
        incidencia = Incidencia.objects.create(
            equipo=equipo, unidad=equipo.laboratorio, titulo=titulo, tipo=tipo,
            prioridad=prioridad, estado=estado, descripcion=descripcion,
            detiene_operacion=detiene, solucion=solucion,
            reportada_por=equipo.laboratorio.administrador if equipo.laboratorio else None,
            fecha_resolucion=_momento(dia, 16) if solucion else None,
        )
        # fecha_reporte se llena sola al crear: se fija al día del ejemplo.
        Incidencia.objects.filter(pk=incidencia.pk).update(fecha_reporte=_momento(dia))

    # La incidencia de la láser es la que originó su orden externa.
    laser = activos.get('FAB-UNIT-LASER-01')
    if laser:
        origen = Incidencia.objects.filter(
            equipo=laser, titulo=INCIDENCIAS[0][1]).first()
        Orden.objects.filter(equipo=laser, titulo=ORDENES[4][1], incidencia__isnull=True).update(
            incidencia=origen)

    # El seguimiento lee el último mantenimiento desde el activo.
    for codigo in {o[0] for o in ORDENES}:
        equipo = activos.get(codigo)
        if not equipo:
            continue
        ultima = Orden.objects.filter(
            equipo=equipo, estado='completado').order_by('-fecha_programada').first()
        plan = Plan.objects.filter(equipo=equipo, activo=True).order_by('proxima_ejecucion').first()
        campos = {}
        if ultima and not equipo.fecha_ultimo_mantenimiento:
            campos['fecha_ultimo_mantenimiento'] = ultima.fecha_programada.date()
        if plan and not equipo.proximo_mantenimiento:
            campos['proximo_mantenimiento'] = plan.proxima_ejecucion
        if campos:
            UnidadEquipo.objects.filter(pk=equipo.pk).update(**campos)


def retirar(apps, schema_editor):
    PiezaEquipo = apps.get_model('webcitt', 'PiezaEquipo')
    Plan = apps.get_model('webcitt', 'PlanMantenimientoEquipo')
    Orden = apps.get_model('webcitt', 'MantenimientoEquipo')
    Incidencia = apps.get_model('webcitt', 'IncidenciaEquipo')
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')

    Orden.objects.filter(titulo__in=[o[1] for o in ORDENES],
                         equipo__codigo_unidad__in=[o[0] for o in ORDENES]).delete()
    Plan.objects.filter(nombre__in=[p[1] for p in PLANES],
                        equipo__codigo_unidad__in=[p[0] for p in PLANES]).delete()
    Incidencia.objects.filter(titulo__in=[i[1] for i in INCIDENCIAS],
                              equipo__codigo_unidad__in=[i[0] for i in INCIDENCIAS]).delete()
    for codigo_tipo, nombre in CON_REPUESTO:
        PiezaEquipo.objects.filter(equipo__codigo=codigo_tipo, nombre=nombre).update(
            repuesto_disponible=False)
    UnidadEquipo.objects.filter(garantia_contacto=CONTACTO).update(garantia_contacto='')
    for codigo, adquisicion in RECIEN_ADQUIRIDOS:
        UnidadEquipo.objects.filter(
            codigo_unidad=codigo, fecha_adquisicion=adquisicion).update(fecha_adquisicion=None)


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0218_piezas_de_ejemplo_del_fablab'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
