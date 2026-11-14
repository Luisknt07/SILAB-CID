"""Piezas, accesorios y protecciones de los equipos de fabricación digital.

La unidad necesita distinguir lo que se consume de lo que compone la máquina:
un filamento se gasta en el trabajo, una boquilla decide si el equipo imprime.
Estas son las piezas de referencia por familia de equipo, con las que suelen
desgastarse, cuáles conviene tener en repuesto y qué cuidado las alarga.

Es un catálogo de partida: la unidad lo ajusta desde el administrador.
"""

import re

from django.db import migrations

# palabras clave del equipo, y sus piezas: (nombre, clase, cantidad, crítica,
# horas de vida, recomendación, descripción)
PIEZAS = (
    (('resina', 'sla'), (
        ('Película FEP del tanque', 'componente', 1, True, 300,
         'Revisar antes de cada trabajo; cambiarla ante cualquier marca o rayón.',
         'Permite que la pieza se despegue del tanque en cada capa.'),
        ('Pantalla LCD de exposición', 'componente', 1, True, 2000,
         'Limpiar salpicaduras de resina de inmediato: la resina curada la inutiliza.',
         'Proyecta la máscara de luz que cura cada capa.'),
        ('Plataforma de construcción', 'componente', 1, True, 0,
         'Nivelar tras cada limpieza profunda.', 'Sostiene la pieza durante la impresión.'),
        ('Tanque de resina', 'componente', 1, False, 0, 'Filtrar la resina antes de guardarla.',
         'Contiene la resina líquida durante el trabajo.'),
        ('Guantes de nitrilo y gafas', 'proteccion', 1, True, 0,
         'Obligatorios al manipular resina: es irritante y sensibilizante.',
         'Protección personal del operador.'),
        ('Espátula y filtros de resina', 'accesorio', 1, False, 0, '', 'Para retirar piezas y filtrar la resina.'),
    )),
    (('impresora 3d', 'fdm', 'imp3d'), (
        ('Boquilla (nozzle) 0,4 mm', 'componente', 1, True, 800,
         'Limpiar en frío tras cada cambio de material; sustituir si el filamento sale torcido.',
         'Define el diámetro de extrusión y la calidad de la pieza.'),
        ('Extrusor y engranaje de arrastre', 'componente', 1, True, 4000,
         'Revisar la tensión del muelle y limpiar restos de filamento cada mes.',
         'Empuja el filamento hacia el hotend; su desgaste provoca atascos.'),
        ('Cama de impresión con lámina PEI', 'componente', 1, True, 2000,
         'Limpiar con alcohol isopropílico antes de cada sesión; no rayar con espátula metálica.',
         'Superficie sobre la que se adhiere la primera capa.'),
        ('Termistor y cartucho calefactor', 'componente', 2, True, 5000,
         'Verificar el aislamiento cada semestre: una lectura errática quema el hotend.',
         'Miden y generan la temperatura del hotend.'),
        ('Sensor de nivelación', 'componente', 1, False, 0,
         'Mantener la punta libre de restos de filamento.',
         'Mide la distancia a la cama para nivelar automáticamente.'),
        ('Correas y poleas de los ejes', 'componente', 2, False, 6000,
         'Revisar la tensión cada trimestre; una correa floja desplaza las capas.',
         'Transmiten el movimiento de los motores a los ejes.'),
        ('Cubierta y ventiladores', 'componente', 1, False, 0,
         'Soplar el polvo de los ventiladores cada mes.',
         'Protegen la zona de trabajo y refrigeran la electrónica.'),
        ('Espátula de desmontaje', 'accesorio', 1, False, 0, '', 'Para retirar la pieza sin dañar la lámina.'),
        ('Juego de llaves Allen', 'herramienta', 1, False, 0, '', 'Ajuste de ejes, extrusor y cubierta.'),
        ('Regulador de voltaje o UPS', 'proteccion', 1, True, 0,
         'Conectar siempre a través del regulador: un corte durante la impresión daña la electrónica.',
         'Protege la fuente y la placa de variaciones de la red.'),
    )),
    (('laser', 'láser'), (
        ('Tubo láser', 'componente', 1, True, 8000,
         'No operar sin refrigeración: el tubo se agrieta.', 'Genera el haz de corte y grabado.'),
        ('Espejos y lente de enfoque', 'componente', 3, True, 1500,
         'Limpiar con paño de óptica y alcohol tras cada jornada intensa.',
         'Dirigen y enfocan el haz sobre el material.'),
        ('Extractor y ducto de humos', 'componente', 1, True, 0,
         'Revisar el filtro cada mes: sin extracción no se debe operar.',
         'Evacua los gases del corte.'),
        ('Bomba y circuito de refrigeración', 'componente', 1, True, 0,
         'Verificar el nivel y la temperatura del agua antes de cada uso.',
         'Mantiene el tubo dentro de su rango térmico.'),
        ('Panal y rejilla de trabajo', 'accesorio', 1, False, 0, '', 'Soporta el material durante el corte.'),
        ('Extintor de CO₂ cercano', 'proteccion', 1, True, 0,
         'Nunca dejar la máquina sin vigilancia mientras corta.', 'Respuesta inmediata ante ignición.'),
    )),
    (('cnc', 'fresadora', 'mecanizado'), (
        ('Fresas y brocas', 'componente', 1, True, 200,
         'Cambiar al primer signo de desgaste: una fresa gastada daña el husillo.',
         'Herramienta de corte del material.'),
        ('Husillo (spindle)', 'componente', 1, True, 6000,
         'Respetar las revoluciones recomendadas por material.', 'Gira la herramienta de corte.'),
        ('Guías lineales y husillos de bolas', 'componente', 3, False, 5000,
         'Lubricar cada trimestre y mantener libres de viruta.', 'Mueven los ejes con precisión.'),
        ('Sistema de aspiración de viruta', 'componente', 1, False, 0,
         'Vaciar el depósito tras cada jornada.', 'Retira el material desprendido.'),
        ('Juego de pinzas y llaves de husillo', 'herramienta', 1, False, 0, '', 'Para el cambio de herramienta.'),
        ('Paro de emergencia y resguardos', 'proteccion', 1, True, 0,
         'Probar el paro de emergencia cada mes.', 'Detiene la máquina ante un riesgo.'),
    )),
    (('escáner', 'escaner', 'scan'), (
        ('Cabezal óptico y cámaras', 'componente', 1, True, 0,
         'No tocar las lentes; transportar siempre en su estuche.',
         'Captura la geometría del objeto.'),
        ('Marcadores de calibración', 'accesorio', 1, True, 0,
         'Guardarlos completos: sin ellos la calibración no cierra.',
         'Referencias que el escáner usa para alinear capturas.'),
        ('Placa de calibración', 'accesorio', 1, True, 0, 'Mantener libre de rayones.',
         'Patrón con el que se calibra el equipo.'),
        ('Trípode y mesa giratoria', 'accesorio', 1, False, 0, '', 'Sostienen el equipo y el objeto.'),
    )),
    (('secador', 'curado', 'lavado'), (
        ('Resistencia y ventilador', 'componente', 1, False, 0,
         'Revisar que el flujo de aire no esté obstruido.', 'Genera y mueve el aire caliente.'),
        ('Cesta o contenedor de lavado', 'accesorio', 1, False, 0,
         'Cambiar el alcohol cuando pierda transparencia.', 'Contiene la pieza durante el lavado.'),
    )),
    (('computadora', 'estación de diseño', 'cad'), (
        ('Tarjeta gráfica', 'componente', 1, True, 0,
         'Limpiar el polvo del disipador cada semestre.', 'Sostiene el modelado y el renderizado.'),
        ('Unidad de almacenamiento', 'componente', 1, False, 0,
         'Mantener copia de los proyectos fuera del equipo.', 'Guarda el sistema y los archivos de trabajo.'),
        ('Regulador de voltaje o UPS', 'proteccion', 1, True, 0,
         'Conectar siempre a través del regulador.', 'Protege la fuente ante variaciones de la red.'),
    )),
    (('vinilo', 'plotter'), (
        ('Cuchilla de corte', 'componente', 1, True, 400,
         'Ajustar la profundidad al material: forzarla la rompe.', 'Corta el vinilo.'),
        ('Rodillos de arrastre', 'componente', 2, False, 0,
         'Limpiar los restos de adhesivo cada mes.', 'Mueven el material durante el corte.'),
        ('Base de corte', 'accesorio', 1, False, 0, '', 'Superficie sobre la que se apoya el vinilo.'),
    )),
)

# Garantía de referencia por familia: meses y qué cubre.
GARANTIAS = (
    (('impresora 3d', 'fdm', 'imp3d', 'resina', 'sla'), 12,
     'Doce meses del fabricante: partes y mano de obra por defecto de fabricación. No cubre boquillas, '
     'láminas ni películas FEP, que son piezas de desgaste, ni daños por corte eléctrico sin regulador.'),
    (('laser', 'láser', 'cnc', 'fresadora', 'mecanizado'), 24,
     'Veinticuatro meses del proveedor: partes, mano de obra y dos visitas preventivas. No cubre ópticas, '
     'fresas ni daños por operar sin refrigeración o sin extracción.'),
    (('escáner', 'escaner', 'scan', 'computadora', 'cad', 'vinilo', 'plotter'), 12,
     'Doce meses del proveedor: partes y mano de obra en taller. No cubre golpes, humedad ni pérdida de '
     'accesorios.'),
)


def _casa(clave, texto):
    """La clave vale como palabra, no como trozo de otra.

    Sin esto 'cad' casaba dentro de 'secador' y de 'empacadora', y un molino
    terminaba con las piezas de una computadora de diseño.
    """
    return re.search(r'(?<![0-9a-záéíóúñ])%s(?![0-9a-záéíóúñ])' % re.escape(clave), texto) is not None


def _para(textos, catalogo):
    for claves, *resto in catalogo:
        for texto in textos:
            if any(_casa(clave, texto) for clave in claves):
                return resto
    return None


def sembrar(apps, schema_editor):
    EquiposServicios = apps.get_model('webcitt', 'EquiposServicios')
    PiezaEquipo = apps.get_model('webcitt', 'PiezaEquipo')
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')

    for equipo in EquiposServicios.objects.prefetch_related('categorias'):
        textos = [(equipo.nombre or '').lower(), (equipo.codigo or '').lower()]
        textos += [(categoria.nombre or '').lower() for categoria in equipo.categorias.all()]
        piezas = _para(textos, PIEZAS)
        if piezas and not PiezaEquipo.objects.filter(equipo=equipo).exists():
            for orden, (nombre, clase, cantidad, critica, horas, recomendacion, descripcion) in enumerate(
                    piezas[0], start=1):
                PiezaEquipo.objects.create(
                    equipo=equipo, nombre=nombre, clase=clase, cantidad=cantidad, critica=critica,
                    vida_util_horas=horas, recomendacion=recomendacion, descripcion=descripcion,
                    orden=orden * 10, repuesto_disponible=False,
                )
        garantia = _para(textos, GARANTIAS)
        if garantia:
            meses, cobertura = garantia
            UnidadEquipo.objects.filter(equipo=equipo, garantia_meses=0).update(
                garantia_meses=meses, garantia_cobertura=cobertura)


def retirar(apps, schema_editor):
    PiezaEquipo = apps.get_model('webcitt', 'PiezaEquipo')
    UnidadEquipo = apps.get_model('webcitt', 'UnidadEquipo')
    PiezaEquipo.objects.filter(cambios__isnull=True).delete()
    # Solo las garantías de referencia que sembró esta migración: una
    # registrada a mano por la unidad no se borra.
    for _claves, _meses, cobertura in GARANTIAS:
        UnidadEquipo.objects.filter(garantia_cobertura=cobertura).update(
            garantia_meses=0, garantia_cobertura='')


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0217_piezas_ejecutor_y_garantia'),
    ]

    operations = [
        migrations.RunPython(sembrar, retirar),
    ]
