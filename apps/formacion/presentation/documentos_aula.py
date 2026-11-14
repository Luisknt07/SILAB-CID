"""El documento descargable de cada página del aula.

Una página del aula ya es un documento en pantalla: tiene su cabecera con el
logo, sus cifras y sus tablas. Lo que faltaba era bajarla sin pasar por el
«Imprimir» del navegador, que le mete la dirección y la fecha en los bordes y
corta las tablas donde caiga.

Cada constructor de aquí recibe el contexto que la vista ya armó —no vuelve a
consultar nada— y lo traduce al diccionario del presentador institucional. Así
el archivo dice exactamente lo mismo que la pantalla: si una cifra cambia en la
página, cambia en el PDF, porque salen del mismo cálculo.
"""

from apps.documentos.presentation.documentos import documento, tabla


def _texto(valor, vacio='—'):
    valor = '' if valor is None else str(valor).strip()
    return valor or vacio


# --------------------------------------------------------------- el proceso
def documento_de_ficha(contexto):
    """La ficha del proceso: sus etapas, su balance y su cursograma."""
    receta, proceso = contexto['receta'], contexto['proceso']
    resumen, balance = contexto['resumen'], contexto['balance']
    return documento(
        titulo='Ficha del proceso',
        alcance=f"{contexto['unidad'].nombre} · {receta.codigo} · {receta.nombre_publico}",
        criterios=[
            ('Proceso', f"{receta.codigo} · {receta.nombre_publico}"),
            ('Corrida base', f"{proceso['cantidad_base']} {proceso['unidad_base']}"),
            ('Producto', f"{proceso['producto']} · {proceso['rendimiento_esperado']} {proceso['unidad_producto']}"),
            ('Duración', resumen['duracion_texto']),
        ],
        notas=proceso.get('instrucciones') or '',
        tarjetas=[
            ('Etapas', resumen['etapas'], 'pasos declarados en la receta'),
            ('Duración de la corrida', resumen['duracion_texto'], f"{resumen['trabajo_texto']} de trabajo"),
            ('Puntos críticos', resumen['puntos_criticos'], 'etapas con límite declarado'),
            ('Personas a la vez', resumen['personas_max'], 'el máximo que pide una etapa'),
        ],
        headers=[
            'N.º', 'Etapa', 'Tipo', 'Equipo', 'Área', 'Trabajo', 'Espera',
            'Personas', 'Rendimiento', 'Punto crítico',
        ],
        filas=[
            [
                etapa['orden'], etapa['nombre'], etapa.get('tipo_nombre') or etapa['tipo'].capitalize(),
                _texto(etapa['equipo']), _texto(etapa['espacio']),
                f"{etapa['duracion_min']} min", f"{etapa['espera_min']} min",
                etapa['personas'], f"{etapa['rendimiento_pct']} %",
                f"{'PCC' if etapa['punto_critico'] else 'PC'}: {_texto(etapa['parametro'], 'Sin parámetro')} · "
                f"{_texto(etapa['limite'], 'sin límite')}" if etapa['punto_critico'] or etapa.get('punto_control') else '—',
            ]
            for etapa in proceso['etapas']
        ],
        tablas=[
            tabla(
                'BALANCE DE MATERIA POR ETAPA',
                ['N.º', 'Etapa', 'Rendimiento', 'Entra', 'Se incorpora', 'Continúa', 'Sale declarado', 'Pérdida'],
                [
                    [
                        fila['orden'], fila['nombre'], f"{fila['rendimiento_pct']} %", fila['entra'],
                        f"+{fila['agregado']}" if fila['agregado'] != '0' else '—',
                        fila['continua'], ' · '.join(fila['salidas']) or '—',
                        fila['perdida'] if fila['perdida'] != '0' else '—',
                    ]
                    for fila in balance['filas']
                ],
                'La receta no declara etapas.',
            ),
            tabla(
                'CRONOGRAMA DE LA CORRIDA',
                ['N.º', 'Etapa', 'Empieza en el minuto', 'Dura', 'Termina en el minuto', 'Personas'],
                [
                    [fila['orden'], fila['nombre'], fila['inicio_min'],
                     f"{fila['duracion_min']} min", fila['fin_min'], fila['personas']]
                    for fila in contexto['cronograma']['filas']
                ],
                'Sin etapas no hay cronograma.',
            ),
            *([tabla(
                'COSTO ESTÁNDAR DE LA CORRIDA BASE', ['Concepto', 'Base de cálculo', 'Costo'],
                contexto['costo']['filas'], 'Sin costo calculado.',
            )] if contexto.get('costo') else []),
        ],
        dibujos=_diagramas_del_proceso(proceso, contexto['cursograma']),
    )


def _diagramas_del_proceso(proceso, cursograma_datos):
    """Los diagramas de la ficha para el PDF: la misma geometría que la página."""
    from apps.plantas_piloto.operacion.presentation.diagramas import cursograma, diagrama_flujo, diagrama_operaciones, diagrama_recorrido
    if not proceso.get('etapas'):
        return []
    dibujos = [
        ('Diagrama de flujo del proceso (Codex CXC 1-1969 · ASME Y15.3)', diagrama_flujo(proceso)),
        ('Diagrama de operaciones del proceso (DOP)', diagrama_operaciones(proceso)),
        ('Cursograma analítico (OIT)', cursograma(proceso, cursograma_datos)),
    ]
    recorrido = diagrama_recorrido(proceso)
    if recorrido:
        dibujos.append(('Diagrama de recorrido', recorrido))
    return dibujos


# ---------------------------------------------------------- los simuladores
def documento_de_balance(contexto):
    """El balance de materia y energía tal como quedó en el simulador."""
    balance, general = contexto['balance'], contexto['general']
    energia, proceso = contexto['energia'], contexto['proceso']
    criterios = [
        ('Proceso', f"{contexto['receta'].codigo} · {contexto['receta'].nombre}"),
        ('Materia prima', f"{contexto['cantidad']} {contexto['receta'].unidad_base}"),
        ('Datos movidos', str(len(contexto['cambios']))),
    ]
    lienzo = contexto.get('diagrama_escenario_lienzo')
    return documento(
        titulo='Simulación: balance de materia y energía',
        alcance=f"{contexto['unidad'].nombre} · {contexto['receta'].nombre}",
        criterios=criterios,
        dibujos=[('Diagrama de flujo del escenario', lienzo)] if lienzo else [],
        tarjetas=[
            ('Entra', f"{balance['entrada']} {balance['unidad_base']}", 'materia prima de la corrida'),
            ('Producto por balance', f"{balance['producto_por_balance']} {balance['unidad_producto']}",
             'lo que deja este escenario'),
            ('Producto esperado', f"{balance['producto_esperado']} {balance['unidad_producto']}",
             'lo que la receta promete'),
            ('Merma total', f"{general['merma_total']} {general['unidad_base']}",
             f"{general['proporcion_merma']} % de lo que entra"),
        ],
        headers=['N.º', 'Etapa', 'Rendimiento', 'Entra', 'Se incorpora', 'Continúa', 'Sale declarado', 'Pérdida'],
        filas=[
            [
                fila['orden'], fila['nombre'], f"{fila['rendimiento_pct']} %", fila['entra'],
                f"+{fila['agregado']}" if fila['agregado'] != '0' else '—',
                fila['continua'], ' · '.join(fila['salidas']) or '—',
                fila['perdida'] if fila['perdida'] != '0' else '—',
            ]
            for fila in balance['filas']
        ],
        tablas=[
            tabla(
                'LO QUE SE MOVIÓ RESPECTO DE LA RECETA',
                ['Variable', 'La receta dice', 'Este escenario'],
                [[cambio['variable'], cambio['de'], cambio['a']] for cambio in contexto['cambios']],
                'Esta simulación corre con los datos de la receta, sin cambios.',
            ),
            tabla(
                'EL ESCENARIO FRENTE A LA RECETA',
                ['Resultado', 'Receta', 'Este escenario'],
                [list(fila) for fila in contexto.get('comparacion', [])],
                'Sin cambios, el escenario es la receta.',
            ),
            tabla(
                'TODO LO QUE ENTRA',
                ['Etapa', 'Insumo', 'Cantidad', 'Su papel en el balance'],
                [
                    [entrada['etapa'] or 'Sin etapa', entrada['nombre'], entrada['cantidad'], entrada['rol']]
                    for entrada in contexto['entradas']
                ],
                'La receta no declara insumos.',
            ),
            tabla(
                'TODO LO QUE SALE',
                ['Etapa', 'Salida', 'Cantidad', 'Qué es'],
                [
                    [salida['etapa'], salida['nombre'], salida['cantidad'] or '—',
                     f"{salida['tipo']} · {salida['detalle']}"]
                    for salida in contexto['salidas']
                ],
                'Con estos datos el proceso no pierde masa ni declara subproductos.',
            ),
            tabla(
                'BALANCE DE ENERGÍA DE LA CORRIDA',
                ['Concepto', 'Valor', 'De qué depende'],
                [
                    ['Masa a calentar', f"{energia['masa_kg']} kg",
                     f"{contexto['cantidad']} {contexto['receta'].unidad_base}"],
                    ['Calor útil', f"{energia['calor_util_kj']} kJ",
                     f"de {contexto['parametros']['t_inicial']} a {contexto['parametros']['t_proceso']} °C"
                     f" ({energia['salto_calor']} K)"],
                    ['Energía a suministrar', f"{energia['calor_kwh']} kWh",
                     f"{energia['calor_suministrado_kj']} kJ con {energia['eficiencia_pct']} % de eficiencia"
                     f" · ≈ {energia['vapor_kg']} kg de vapor"],
                    ['Calor por retirar', f"{energia['frio_kj']} kJ",
                     f"de {contexto['parametros']['t_proceso']} a {contexto['parametros']['t_final']} °C"
                     f" · ≈ {energia['frio_kwh']} kWh eléctricos"],
                ] + ([
                    ['Tiempo de calentamiento', f"{energia['minutos']} min",
                     f"a {contexto['parametros']['potencia_kw']} kW"],
                ] if energia['minutos'] else []),
                'El proceso no declara etapas térmicas.',
            ),
            tabla(
                'ETAPAS TÉRMICAS DEL PROCESO',
                ['N.º', 'Etapa', 'Trabajo térmico', 'Parámetro', 'Límite', 'Equipo'],
                [
                    [fila['orden'], fila['nombre'],
                     trabajo + ('' if fila['temperatura'] is None else f" · {fila['temperatura']} °C"),
                     _texto(fila['parametro']), _texto(fila['limite']), _texto(fila['equipo'])]
                    for trabajo, grupo in (('Calienta', contexto['calientes']), ('Enfría', contexto['frias']))
                    for fila in grupo
                ],
                'El proceso no declara etapas térmicas.',
            ),
        ],
        notas=(
            f"Producto de la corrida: {proceso['producto']}. "
            'Calor específico y densidad son los de la leche y sus derivados líquidos; '
            'es una estimación para el aula, la planta mide lo real en cada corrida.'
        ),
    )


def documento_de_linea(contexto):
    """El balance de línea: el ritmo que pide la jornada y quién no lo alcanza."""
    linea = contexto['linea']
    cuello = linea['cuello'] or {}
    return documento(
        titulo='Simulación: balance de línea',
        alcance=f"{contexto['unidad'].nombre} · {contexto['receta'].nombre}",
        criterios=[
            ('Proceso', f"{contexto['receta'].codigo} · {contexto['receta'].nombre}"),
            ('Corridas en la jornada', contexto['corridas']),
            ('Jornada', f"{contexto['jornada']} h ({linea['jornada_min']} min)"),
        ],
        tarjetas=[
            ('Ritmo que pide la jornada', f"{linea['takt']} min", 'takt por corrida'),
            ('Ciclo real', f"{linea['ciclo']} min",
             f"cuello de botella: {cuello.get('nombre') or 'sin etapas'}"),
            ('Estaciones', str(linea['numero_estaciones']),
             f"mínimo teórico: {linea['estaciones_minimas']}"),
            ('Alcanza la jornada', 'Sí' if linea['alcanza'] else 'No',
             f"eficiencia de línea {linea['eficiencia']} %"),
        ],
        headers=['N.º', 'Etapa', 'Equipo', 'Trabajo', 'Espera', 'Personas', 'Utilización del takt'],
        filas=[
            [
                etapa['orden'], etapa['nombre'], _texto(etapa['equipo']),
                f"{etapa['trabajo']} min", f"{etapa['espera']} min", etapa['personas'],
                f"{etapa['utilizacion']} %",
            ]
            for etapa in linea['etapas']
        ],
        tablas=[
            tabla(
                'CÓMO QUEDAN LAS ESTACIONES',
                ['Estación', 'Etapas que agrupa', 'Tiempo', 'Ocupación del takt', 'Personas'],
                [
                    [
                        estacion['numero'],
                        ' · '.join(f"{etapa['orden']}. {etapa['nombre']}" for etapa in estacion['etapas']),
                        f"{estacion['tiempo']} min",
                        f"{estacion['ocupacion']} %" + (' (excede el takt)' if estacion['excede'] else ''),
                        estacion['personas'],
                    ]
                    for estacion in linea['estaciones']
                ],
                'El proceso no declara etapas con tiempo de trabajo.',
            ),
        ],
        notas=(
            f"Trabajo total {linea['trabajo_total']} min; esperas del proceso {linea['espera_total']} min, "
            'fuera del balance porque no ocupan personas. Las etapas se agrupan en orden mientras caben '
            'en el takt; una etapa más larga que el takt ocupa su propia estación.'
        ),
    )


def documento_de_materiales(contexto):
    """El requerimiento de materiales del plan frente a las existencias de hoy."""
    requerimiento = contexto['requerimiento'] or {
        'filas': [], 'salidas': [], 'faltantes': 0, 'cubiertos': 0, 'insumos': 0, 'corridas': '0',
    }
    return documento(
        titulo='Simulación: requerimiento de materiales',
        alcance=f"{contexto['unidad'].nombre} · plan de {requerimiento['corridas']} corridas",
        criterios=[
            ('Plan', ' · '.join(
                f"{fila['receta'].nombre} × {fila['factor']}" for fila in contexto['plan']
            ) or 'Sin corridas en el plan'),
            ('Origen del plan',
             'Las sesiones de la reserva o programación' if contexto['desde_referencia']
             else 'Escrito a mano en el simulador'),
        ],
        tarjetas=[
            ('Insumos', str(requerimiento['insumos']), 'que pide el plan'),
            ('Cubiertos', str(requerimiento['cubiertos']), 'con lo que hay en bodega'),
            ('Faltantes', str(requerimiento['faltantes']), 'hay que comprarlos'),
            ('Corridas', requerimiento['corridas'], 'del plan simulado'),
        ],
        headers=['Insumo', 'Clasificación', 'Procesos que lo piden', 'Necesita', 'En bodega',
                 'Reserva', 'Disponible', 'Falta comprar'],
        filas=[
            [
                f"{fila['nombre']} ({fila['unidad']})" + ('' if fila['obligatorio'] else ' · opcional'),
                fila['clasificacion'], ' · '.join(fila['procesos']),
                fila['bruto'], fila['stock'], fila['seguridad'], fila['disponible'],
                '—' if fila['cubre'] else fila['neto'],
            ]
            for fila in requerimiento['filas']
        ],
        tablas=[
            tabla(
                'LO QUE EL PLAN DEBERÍA ENTREGAR',
                ['Producto', 'Tipo', 'Cantidad', 'Papel'],
                [
                    [f"{salida['nombre']} ({salida['unidad']})", salida['tipo'], salida['cantidad'],
                     'Producto principal' if salida['principal'] else 'Subproducto']
                    for salida in requerimiento['salidas']
                ],
                'La receta no declara productos de salida.',
            ),
        ],
        notas=(
            'Lo disponible descuenta el stock de seguridad: es lo que se puede consumir sin dejar la '
            'bodega por debajo de su mínimo.'
        ),
    )


# -------------------------------------------------- las páginas informativas
def documento_de_protocolos(contexto):
    """Los puntos críticos de control de todos los procesos publicados."""
    protocolos = contexto['protocolos']
    filas = []
    for item in protocolos:
        if not item['puntos']:
            filas.append([
                f"{item['receta'].codigo} · {item['receta'].nombre}", '—',
                'Este proceso todavía no declara puntos críticos.', '—', '—', '—', '—',
            ])
            continue
        for punto in item['puntos']:
            filas.append([
                f"{item['receta'].codigo} · {item['receta'].nombre}", punto['orden'], punto['nombre'],
                punto['tipo'], _texto(punto['parametro'], 'Sin parámetro declarado'),
                _texto(punto['limite'], 'Sin límite declarado'),
                _texto(punto['equipo'] or punto['espacio'], 'Sin equipo ni área declarada'),
            ])
    return documento(
        titulo='Protocolos de control de la unidad',
        alcance=contexto['unidad'].nombre,
        criterios=[
            ('Procesos publicados', str(len(protocolos))),
            ('Puntos críticos de control', str(contexto['total_puntos'])),
        ],
        tarjetas=[
            ('Procesos publicados', str(len(protocolos)), 'recetas activas con etapas declaradas'),
            ('Puntos críticos', str(contexto['total_puntos']), 'etapas que deciden inocuidad o calidad'),
            ('Etapas declaradas', str(sum(item['total_etapas'] for item in protocolos)),
             'pasos que suman todos los procesos'),
            ('Procesos sin punto crítico', str(sum(1 for item in protocolos if not item['puntos'])),
             'su protocolo todavía está vacío'),
        ],
        headers=['Proceso', 'N.º', 'Etapa', 'Tipo', 'Parámetro que se mide',
                 'Límite que debe cumplir', 'Dónde se controla'],
        filas=filas,
        tablas=[
            tabla(
                'CUÁNTO DE CADA PROCESO ESTÁ BAJO CONTROL',
                ['Proceso', 'Etapas del proceso', 'Etapas vigiladas'],
                [
                    [f"{item['receta'].codigo} · {item['receta'].nombre}", item['total_etapas'],
                     f"{len(item['puntos'])} punto{'s' if len(item['puntos']) != 1 else ''} crítico"
                     f"{'s' if len(item['puntos']) != 1 else ''}"]
                    for item in protocolos
                ],
                'La unidad no publica procesos.',
            ),
            tabla(
                'PUNTOS CRÍTICOS CON EL PROTOCOLO INCOMPLETO',
                ['Proceso', 'N.º', 'Etapa', 'Qué le falta'],
                [
                    [
                        f"{item['receta'].codigo} · {item['receta'].nombre}", punto['orden'], punto['nombre'],
                        ' y '.join(falta for falta in (
                            'el parámetro que se mide' if not punto['parametro'] else '',
                            'el límite que debe cumplir' if not punto['limite'] else '',
                            'la instrucción de control' if not punto['instrucciones'] else '',
                        ) if falta),
                    ]
                    for item in protocolos
                    for punto in item['puntos']
                    if not (punto['parametro'] and punto['limite'] and punto['instrucciones'])
                ],
                'Todos los puntos críticos declaran parámetro, límite e instrucción.',
            ),
        ],
        notas=(
            'Un punto crítico de control es la etapa donde una desviación compromete la inocuidad o la '
            'calidad del producto, y por eso se mide y se registra en cada corrida.'
        ),
    )


def documento_de_produccion(contexto):
    """El catálogo estable que la planta publica."""
    produccion = contexto['produccion']
    resumen = produccion['resumen']
    return documento(
        titulo='Producción y lotes de la unidad',
        alcance=contexto['unidad'].nombre,
        criterios=[
            ('Corte', f"{contexto['hoy']:%d/%m/%Y}"),
            ('Productos publicados', str(resumen['productos'])),
            ('Procesos con ficha', str(resumen['procesos'])),
        ],
        tarjetas=[
            ('Productos publicados', str(resumen['productos']), 'terminados, intermedios y subproductos'),
            ('Procesos', str(resumen['procesos']), 'con su ficha publicada'),
        ],
        headers=['Línea de producción', 'Producto', 'Qué es', 'Presentación', 'Vida útil',
                 'Conservación', 'Precio de venta'],
        filas=[
            [
                linea['nombre'], producto.nombre, producto.get_tipo_display(),
                _texto(producto.presentacion, 'Sin presentación declarada'),
                f"{producto.vida_util_dias} días" if producto.vida_util_dias else '—',
                producto.conservacion,
                f"${producto.precio_venta} por {producto.unidad_medida}" if producto.se_vende else 'No se vende',
            ]
            for linea in produccion['lineas']
            for producto in linea['productos']
        ],
        notas='El catálogo se agrupa con la taxonomía institucional de familias de producto.',
    )


def documento_de_producto(contexto):
    """La ficha individual del catálogo, sin duplicar la ficha de proceso."""
    producto = contexto['producto']
    receta = contexto.get('receta')
    return documento(
        titulo='Ficha de producto',
        alcance=f"{contexto['unidad'].nombre} · {producto.codigo}",
        criterios=[
            ('Producto', producto.nombre),
            ('Familia', producto.familia.nombre),
            ('Tipo', producto.get_tipo_display()),
        ],
        tarjetas=[
            ('Unidad de medida', producto.unidad_medida, 'unidad de salida'),
            ('Presentación', _texto(producto.presentacion, 'Por definir'), 'presentación comercial'),
            ('Vida útil', f'{producto.vida_util_dias} días' if producto.vida_util_dias else '—',
             'declarada por la unidad'),
            ('Conservación', producto.conservacion, 'condición declarada'),
        ],
        headers=['Dato', 'Valor'],
        filas=[
            ['Código', producto.codigo],
            ['Producto', producto.nombre],
            ['Familia', producto.familia.nombre],
            ['Tipo', producto.get_tipo_display()],
            ['Unidad de medida', producto.unidad_medida],
            ['Presentación', _texto(producto.presentacion, 'Por definir')],
            ['Conservación', producto.conservacion],
            ['Precio', f'${producto.precio_venta} / {producto.unidad_medida}' if producto.se_vende else '—'],
            ['Proceso técnico', receta.nombre_publico if receta is not None else 'Pendiente de publicación'],
        ],
        notas=producto.descripcion or 'Referencia de la taxonomía institucional de productos.',
    )


def documento_de_corridas_lotes(contexto):
    """El mismo agregado público de actividad que aparece en pantalla."""
    actividad = contexto['actividad']
    return documento(
        titulo='Actividad de producción de la unidad',
        alcance=contexto['unidad'].nombre,
        criterios=[('Corte', f"{contexto['hoy']:%d/%m/%Y}")],
        tarjetas=[
            ('Corridas cerradas este mes', str(actividad['corridas_mes']), 'órdenes terminadas'),
            ('Lotes vigentes', str(actividad['lotes_vigentes']), 'aprobados, disponibles y no vencidos'),
        ],
        headers=[],
        filas=[],
        notas=(
            'El detalle de órdenes, cantidades, ubicaciones y lotes es interno y requiere '
            'sesión con rol de la unidad.'
        ),
    )


def documento_de_calidad(contexto):
    """Lo que la unidad controla: puntos críticos, planes y el estado de los lotes."""
    calidad = contexto['calidad']
    publicada = calidad['publicada']
    conteo = calidad['conteo']
    con_control = conteo['aprobado'] + conteo['pendiente'] + conteo['rechazado']
    filas = []
    for item in calidad['protocolos']:
        etiqueta = f"{item['receta'].codigo} · {item['receta'].nombre}"
        vigiladas = f"{len(item['puntos'])} de {item['total_etapas']} etapas"
        if not item['puntos']:
            filas.append([etiqueta, vigiladas, '—', 'El proceso no declara puntos críticos', '—', '—', '—'])
            continue
        for punto in item['puntos']:
            filas.append([
                etiqueta, vigiladas, punto['orden'], punto['nombre'],
                _texto(punto['parametro'], 'Sin parámetro declarado'),
                _texto(punto['limite'], 'Sin límite declarado'),
                _texto(punto['equipo'] or punto['espacio']),
            ])
    return documento(
        titulo='Calidad e inocuidad de la unidad',
        alcance=contexto['unidad'].nombre,
        criterios=[
            ('Puntos críticos de control', str(calidad['total_puntos'])),
            ('Planes de calidad publicados', str(len(publicada['planes']))),
            ('Lotes con control registrado', str(con_control)),
        ],
        tarjetas=[
            ('Puntos críticos', str(calidad['total_puntos']), 'etapas vigiladas en los procesos'),
            ('Parámetros con límite', str(publicada['parametros_totales']),
             'se miden en cada control de calidad'),
            ('Controles conformes', f"{publicada['conformes']} de {publicada['controles']}",
             'registros que salieron dentro de límite'),
            ('Lotes aprobados', f"{conteo['aprobado']} de {con_control}",
             'liberados sobre los lotes con control'),
        ],
        headers=['Proceso', 'Etapas vigiladas', 'N.º', 'Punto crítico', 'Qué se vigila',
                 'Límite que debe cumplir', 'Dónde se controla'],
        filas=filas,
        tablas=[
            tabla(
                'QUÉ MIDE CADA PLAN Y CON QUÉ LÍMITE',
                ['Plan', 'Parámetro', 'Unidad', 'Mínimo', 'Máximo', 'Método'],
                [
                    [
                        item['plan'].nombre, parametro.nombre, _texto(parametro.unidad_medida),
                        _texto(parametro.minimo), _texto(parametro.maximo),
                        _texto(parametro.metodo),
                    ]
                    for item in publicada['planes']
                    for parametro in item['parametros']
                ],
                'La unidad todavía no publica planes de calidad.',
            ),
            tabla(
                'CONTROL DE CALIDAD DE LOS LOTES, POR PRODUCTO',
                ['Producto', 'Lotes', 'Liberados', 'Rechazados', 'Por liberar'],
                [
                    [fila['producto__nombre'], str(fila['total']), str(fila['liberados']),
                     str(fila['rechazados']), str(fila['por_liberar'])]
                    for fila in calidad['por_producto']
                ],
                'Todavía no hay lotes registrados.',
            ),
            tabla(
                'REQUISITOS PARA INGRESAR A LA UNIDAD',
                ['Requisito', 'Tipo', 'A quién aplica', 'Obligatorio', 'Vigencia', 'Detalle'],
                [
                    [
                        requisito['nombre'], requisito['tipo_display'],
                        _texto(requisito['aplica_display'], 'A todos'),
                        'Sí' if requisito['obligatorio'] else 'Recomendado',
                        f"{requisito['vigencia_dias']} días" if requisito['vigencia_dias'] else 'Sin caducidad',
                        _texto(requisito['descripcion'], ''),
                    ]
                    for requisito in calidad['requisitos']
                ],
                'La unidad no declara requisitos de ingreso.',
            ),
            tabla(
                'NORMAS DE SEGURIDAD DEL REGLAMENTO',
                ['N.º', 'Norma'],
                [[numero, norma] for numero, norma in enumerate(calidad['normas'], 1)],
                'El reglamento publicado no detalla normas de seguridad.',
            ),
        ],
    )


def documento_de_areas(contexto):
    """Las áreas de la unidad con los equipos que alojan."""
    infraestructura = contexto['infraestructura']
    return documento(
        titulo='Áreas y equipos de la unidad',
        alcance=contexto['unidad'].nombre,
        criterios=[
            ('Áreas publicadas', str(infraestructura['total_areas'])),
            ('Equipos activos', str(infraestructura['total_equipos'])),
        ],
        tarjetas=[
            ('Áreas publicadas', str(infraestructura['total_areas']), 'espacios activos de la unidad'),
            ('Equipos instalados', str(infraestructura['total_equipos']), 'unidades de equipo activas'),
            ('Equipos sin área', str(len(infraestructura['sin_area'])), 'todavía no declaran su espacio'),
            ('Áreas sin equipos', str(sum(1 for area in infraestructura['areas'] if not area['equipos'])),
             'publicadas pero vacías'),
        ],
        headers=['Área', 'Equipo', 'Marca y modelo', 'Código de la unidad', 'Estado',
                 'Ubicación exacta', 'Auxiliares que lo acompañan'],
        filas=[
            [
                area['espacio'].nombre, unidad_equipo.equipo.nombre,
                _texto(' '.join(
                    parte for parte in (unidad_equipo.equipo.marca, unidad_equipo.equipo.modelo) if parte
                )),
                unidad_equipo.codigo_unidad, unidad_equipo.get_estado_unidad_display(),
                _texto(unidad_equipo.ubicacion_especifica),
                _texto(', '.join(
                    auxiliar.nombre for auxiliar in unidad_equipo.equipo.auxiliares.all()
                ), 'Ninguno'),
            ]
            for area in infraestructura['areas']
            for unidad_equipo in area['equipos']
        ],
        tablas=[
            tabla(
                'ÁREAS PUBLICADAS Y LO QUE ALOJA CADA UNA',
                ['Área', 'Tipo', 'Capacidad', 'Equipos que aloja'],
                [
                    [
                        area['espacio'].nombre, area['espacio'].get_tipo_display(),
                        f"{area['espacio'].capacidad} personas" if area['espacio'].capacidad else '—',
                        str(len(area['equipos'])),
                    ]
                    for area in infraestructura['areas']
                ],
                'La unidad no publica áreas.',
            ),
            tabla(
                'EQUIPOS SIN ÁREA ASIGNADA',
                ['Equipo', 'Código de la unidad', 'Estado', 'Ubicación exacta'],
                [
                    [
                        unidad_equipo.equipo.nombre, unidad_equipo.codigo_unidad,
                        unidad_equipo.get_estado_unidad_display(),
                        _texto(unidad_equipo.ubicacion_especifica),
                    ]
                    for unidad_equipo in infraestructura['sin_area']
                ],
                'Todos los equipos declaran su área.',
            ),
        ],
        notas='Un equipo puede aparecer en más de un área si la unidad lo declaró en varias.',
    )


def documento_de_equipo(contexto):
    """Ficha pública del equipo con los datos que la unidad publicó."""
    unidad_equipo = contexto['unidad_equipo']
    equipo = unidad_equipo.equipo
    return documento(
        titulo='Ficha de equipo',
        alcance=f"{contexto['unidad'].nombre} · {equipo.nombre}",
        criterios=[
            ('Código', unidad_equipo.codigo_unidad),
            ('Marca y modelo', _texto(' '.join(parte for parte in (equipo.marca, equipo.modelo) if parte), 'No publicado')),
            ('Estado', unidad_equipo.get_estado_unidad_display()),
            ('Ubicación', _texto(unidad_equipo.ubicacion_especifica, 'No publicada')),
        ],
        tarjetas=[
            ('Modo de operación', equipo.get_modo_operacion_display() if equipo.modo_operacion else 'No publicado', ''),
            ('Capacidad nominal', f"{equipo.capacidad_nominal} {equipo.unidad_capacidad}" if equipo.capacidad_nominal is not None else 'No publicada', ''),
            ('Carga útil', f"{equipo.capacidad_util_min or '—'} a {equipo.capacidad_util_max or '—'} {equipo.unidad_capacidad}", ''),
            ('Preparación y limpieza', f"{equipo.tiempo_setup or '—'} + {equipo.tiempo_limpieza or '—'} min", ''),
        ],
        headers=['Campo', 'Valor'],
        filas=[
            ['Características', _texto(equipo.caracteristicas_publicas)],
            ['Uso autorizado', _texto(equipo.uso_publico)],
            ['Preparación', _texto(equipo.instrucciones_publicas)],
        ],
        tablas=[tabla(
            'CONEXIONES, CONSUMOS E IMPLANTACIÓN', ['Campo', 'Valor'],
            [
                ['Potencia', f"{equipo.potencia_kw} kW" if equipo.potencia_kw is not None else 'No publicada'],
                ['Alimentación', f"{equipo.voltaje or '—'} V · {equipo.fases or '—'} fases · {equipo.frecuencia or '—'} Hz"],
                ['Vapor', f"{equipo.consumo_vapor} kg/h" if equipo.consumo_vapor is not None else 'No publicado'],
                ['Agua', f"{equipo.consumo_agua} L/ciclo" if equipo.consumo_agua is not None else 'No publicada'],
                ['Aire', f"{equipo.consumo_aire} m³/h" if equipo.consumo_aire is not None else 'No publicado'],
                ['Dimensiones', f"{equipo.largo_mm or '—'} × {equipo.ancho_mm or '—'} × {equipo.alto_mm or '—'} mm"],
                ['Lados de acceso', _texto(equipo.lados_de_acceso, 'No publicados')],
            ],
            'La unidad todavía no publica datos técnicos del equipo.',
        )],
        notas='Los campos vacíos se conservan como no publicados; el documento no los reemplaza por valores de ejemplo.',
    )


# ------------------------------------------------- la teoría y las listas
def documento_de_documentacion(contexto):
    """La documentación del proceso: por qué cada etapa está donde está."""
    proceso, resumen, general = contexto['proceso'], contexto['resumen'], contexto['general']
    return documento(
        titulo='Documentación del proceso',
        alcance=f"{contexto['unidad'].nombre} · {contexto['receta'].nombre}",
        criterios=[
            ('Proceso', f"{contexto['receta'].codigo} · {contexto['receta'].nombre}"),
            ('Corrida base', f"{proceso['cantidad_base']} {proceso['unidad_base']}"),
            ('Producto', f"{proceso['producto']} · {proceso['rendimiento_esperado']} {proceso['unidad_producto']}"),
            ('Cierre del balance',
             'Cuadra: lo que entra es lo que sale' if general['cuadra']
             else f"Descuadre de {general['diferencia']} {general['unidad_base']}"),
        ],
        tarjetas=[
            ('Etapas', resumen['etapas'], f"{len(contexto['operaciones'])} operaciones unitarias"),
            ('Duración de la corrida', resumen['duracion_texto'], f"{resumen['trabajo_texto']} de trabajo"),
            ('Puntos críticos', len(contexto['puntos_criticos']), 'etapas con su límite declarado'),
            ('Merma del balance', f"{general['merma_total']} {general['unidad_base']}",
             f"{general['proporcion_merma']} % de lo que entra"),
        ],
        headers=['N.º', 'Etapa', 'Operación unitaria', 'Equipo y tiempo', 'Insumos que entran',
                 'Entra', 'Lo que sale', 'Continúa', 'Punto crítico'],
        filas=[
            [
                fila['orden'], fila['nombre'], fila['operacion']['nombre'],
                _texto(' · '.join(parte for parte in (
                    fila['equipo'], f"{fila['minutos']} min" if fila['minutos'] else '',
                ) if parte)),
                _texto(' · '.join(f"{insumo['nombre']} {insumo['cantidad']}" for insumo in fila['insumos'])),
                _texto(fila['entra']),
                _texto(' · '.join(salida['nombre'] for salida in fila['salidas'])),
                _texto(fila['continua']),
                f"{'PCC' if fila['punto_critico'] else 'PC'}: {_texto(fila['parametro'], 'Sin parámetro')} · "
                f"{_texto(fila['limite'], 'sin límite')}" if fila['punto_critico'] or fila.get('punto_control') else '—',
            ]
            for fila in contexto['flujo']
        ],
        tablas=[
            tabla(
                'RUTA DEL SABER Y DEL HACER',
                ['Paso', 'Propósito'],
                [[f"{paso['numero']} · {paso['clave']}", paso['detalle']] for paso in contexto['ruta_aprendizaje']],
                'La ruta de aprendizaje no está disponible.',
            ),
            tabla(
                'BASES PARA LEER Y CALCULAR EL PROCESO',
                ['Fundamento', 'Ecuación', 'Para qué se usa', 'Datos necesarios', 'Cómo se comprueba'],
                [[base['nombre'], base['formula'], base['uso'], base['datos'], base['comprobacion']]
                 for base in contexto['fundamentos']],
                'No hay fundamentos publicados.',
            ),
            tabla(
                'DISPONIBILIDAD DE DIAGRAMAS Y SIMULACIONES',
                ['Diagrama o simulación', 'Estado', 'Condición'],
                [[item['nombre'], item['estado'], item['detalle']] for item in contexto['artefactos']],
                'No hay artefactos evaluados.',
            ),
            tabla(
                'LAS OPERACIONES UNITARIAS DE ESTE PROCESO',
                ['Familia', 'Operación', 'Qué le ocurre al producto', 'Variable que la gobierna',
                 'Qué pasa fuera de rango', 'Cómo se mide', 'Etapas donde aparece'],
                [
                    [
                        operacion['familia'], operacion['nombre'], operacion['fenomeno'],
                        operacion['variable'], operacion['fuera_de_rango'], operacion['se_mide'],
                        ' · '.join(f"{etapa['orden']}. {etapa['nombre']}" for etapa in operacion['etapas']),
                    ]
                    for operacion in contexto['operaciones']
                ],
                'Sin etapas no se puede clasificar ninguna operación unitaria.',
            ),
            tabla(
                'VARIABLES QUE SE PUEDEN MOVER EN LOS SIMULADORES',
                ['Variable', 'Valor en esta receta', 'De dónde sale', 'Qué cambia si la mueves', 'Dónde se simula'],
                [
                    [variable['nombre'], variable['valor'], variable['de_donde'],
                     variable['efecto'], variable['simulador']]
                    for variable in contexto['variables']
                ],
                'Esta receta no declara variables que los simuladores puedan mover.',
            ),
            tabla(
                'TODO LO QUE ENTRA',
                ['Etapa', 'Insumo', 'Cantidad por corrida base', 'Su papel en el balance'],
                [
                    [entrada['etapa'] or 'Sin etapa',
                     entrada['nombre'] if entrada['obligatorio'] else f"{entrada['nombre']} (opcional)",
                     entrada['cantidad'], entrada['rol']]
                    for entrada in contexto['entradas']
                ],
                'La receta no declara insumos.',
            ),
            tabla(
                'DE DÓNDE SALEN LOS DATOS',
                ['Dato', 'Fuente', 'Quién lo mantiene'],
                [[fila['dato'], fila['fuente'], fila['quien']] for fila in contexto['datos_que_usa']],
                'Sin fuentes declaradas para este proceso.',
            ),
            tabla(
                'REFERENCIAS PARA PROFUNDIZAR',
                ['Fuente', 'Aplicación', 'Dirección'],
                [[fila['nombre'], fila['uso'], fila['url']] for fila in contexto['referencias_tecnicas']],
                'No hay referencias registradas.',
            ),
        ],
        notas=(
            'La ficha dice qué hace la planta paso a paso; esta documentación dice por qué: qué operación '
            'unitaria es cada etapa, qué fenómeno ocurre y qué la gobierna.'
        ),
    )


def documento_de_mis_ejercicios(contexto):
    """Los ejercicios que un estudiante tiene asignados en la unidad."""
    filas = contexto['filas']
    return documento(
        titulo='Mis ejercicios del aula',
        alcance=f"{contexto['unidad'].nombre} · {contexto['estudiante']}",
        criterios=[
            ('Estudiante', contexto['estudiante']),
            ('Ejercicios asignados', str(len(filas))),
        ],
        tarjetas=[
            ('Asignados', str(len(filas)), 'en esta unidad'),
            ('Por resolver', str(len(contexto['pendientes'])), 'todavía sin entregar'),
            ('Entregados', str(sum(1 for fila in filas if fila['intento'].estado == 'entregado')),
             'esperando calificación'),
            ('Calificados', str(sum(1 for fila in filas if fila['intento'].estado == 'calificado')),
             'con su nota publicada'),
        ],
        headers=['Ejercicio', 'Simulador', 'Proceso', 'Tu escala', 'Fecha límite', 'Estado',
                 'Nota', 'Aciertos'],
        filas=[
            [
                f"{fila['intento'].ejercicio.codigo} · {fila['intento'].ejercicio.nombre}",
                fila['intento'].ejercicio.get_simulador_display(),
                fila['intento'].ejercicio.receta.nombre_publico,
                f"× {fila['intento'].factor}",
                f"{fila['intento'].ejercicio.fecha_limite:%d/%m/%Y}"
                if fila['intento'].ejercicio.fecha_limite else 'Sin fecha límite',
                fila['intento'].get_estado_display(),
                f"{fila['intento'].puntaje} / {fila['intento'].ejercicio.puntaje}"
                if fila['intento'].puntaje is not None else '—',
                f"{fila['intento'].aciertos} de {fila['intento'].preguntas_totales}"
                if fila['intento'].resultados else '—',
            ]
            for fila in filas
        ],
        tablas=[
            tabla(
                'LO QUE TE PIDE CADA EJERCICIO',
                ['Ejercicio', 'Consigna', 'Comentario del docente'],
                [
                    [fila['intento'].ejercicio.codigo, fila['intento'].ejercicio.consigna,
                     _texto(fila['intento'].comentario, 'Sin comentario')]
                    for fila in filas
                ],
                'Todavía no tienes ejercicios asignados en esta unidad.',
            ),
        ],
        notas=(
            'Cada estudiante resuelve el mismo ejercicio con su propia escala, así que dos compañeros '
            'no llegan al mismo número.'
        ),
    )


def documento_de_mis_simulaciones(contexto):
    """Las simulaciones que alguien guardó en la unidad."""
    simulaciones = contexto['simulaciones']
    return documento(
        titulo='Mis simulaciones guardadas',
        alcance=f"{contexto['unidad'].nombre} · {contexto['autor']}",
        criterios=[
            ('Autor', contexto['autor']),
            ('Simulaciones guardadas', str(len(simulaciones))),
        ],
        tarjetas=[
            ('Guardadas', str(len(simulaciones)), 'en esta unidad'),
            ('Balance de materia',
             str(sum(1 for fila in simulaciones if fila['objeto'].simulador == 'balance')),
             'corridas simuladas'),
            ('Balance de línea',
             str(sum(1 for fila in simulaciones if fila['objeto'].simulador == 'linea')),
             'jornadas simuladas'),
            ('Requerimiento de materiales',
             str(sum(1 for fila in simulaciones if fila['objeto'].simulador == 'materiales')),
             'planes simulados'),
        ],
        headers=['Nombre', 'Simulador', 'Proceso', 'Resumen', 'Guardada el', 'Actualizada el'],
        filas=[
            [
                fila['objeto'].nombre,
                fila['objeto'].get_simulador_display(),
                fila['objeto'].receta.nombre_publico if fila['objeto'].receta_id else 'Varios procesos',
                ' · '.join(f"{etiqueta}: {valor}" for etiqueta, valor in fila['objeto'].resumen) or '—',
                f"{fila['objeto'].creada_en:%d/%m/%Y %H:%M}",
                f"{fila['objeto'].actualizada_en:%d/%m/%Y %H:%M}",
            ]
            for fila in simulaciones
        ],
        tablas=[
            tabla(
                'PARA QUÉ HICISTE CADA UNA',
                ['Nombre', 'Notas'],
                [
                    [fila['objeto'].nombre, _texto(fila['objeto'].notas, 'Sin notas')]
                    for fila in simulaciones
                ],
                'Todavía no has guardado ninguna simulación en esta unidad.',
            ),
        ],
        notas=(
            'Cada simulación guarda las variables con que se corrió, no los resultados: al abrirla se '
            'vuelve a calcular con el proceso como está hoy.'
        ),
    )


def documento_de_indice_procesos(contexto):
    """Los índices 2.2, 2.3 y 2.5 conservan en PDF la misma ruta de consulta."""
    filas = []
    for grupo in contexto['grupos_indice']:
        for ficha in grupo['fichas']:
            if not ficha['filas']:
                filas.append([grupo['nombre'], ficha['receta'].nombre_publico, '—', 'Sin datos declarados'])
            for item in ficha['filas']:
                filas.append([
                    grupo['nombre'], ficha['receta'].nombre_publico,
                    item['principal'], f"{item['detalle']} · {item['meta']} · {item['extra']}",
                ])
    return documento(
        titulo=f"{contexto['numero_indice']} · {contexto['titulo_indice']}",
        alcance=contexto['unidad'].nombre,
        criterios=[('Sección', contexto['numero_indice']), ('Fuente', 'Núcleo técnico de procesos')],
        notas=contexto['descripcion_indice'],
        headers=['Familia', 'Proceso', 'Contenido', 'Detalle'],
        filas=filas,
    )


def documento_de_especificaciones(contexto):
    """Las especificaciones de liberación, igual que en la página."""
    familia = contexto.get('familia_activa')
    return documento(
        titulo='Especificaciones de producto',
        alcance=f"{contexto['unidad'].nombre}{f' · {familia.nombre}' if familia else ''}",
        criterios=[
            ('Productos', str(len(contexto['especificaciones']))),
            ('Parámetros', str(contexto['parametros_totales'])),
        ],
        tarjetas=[
            ('Productos especificados', str(len(contexto['especificaciones'])), 'con plan de liberación'),
            ('Parámetros', str(contexto['parametros_totales']), 'con límite y método'),
        ],
        headers=['Producto', 'Parámetro', 'Límite', 'Método', 'Decide el lote'],
        filas=[
            [
                item['plan'].producto.nombre if item['plan'].producto_id else item['plan'].nombre,
                parametro.nombre, parametro.limite_texto, _texto(parametro.metodo),
                'Sí' if parametro.critico else 'Referencial',
            ]
            for item in contexto['especificaciones']
            for parametro in item['parametros']
        ],
    )


def documento_de_servicios(contexto):
    """Los servicios industriales de la planta, igual que en la página."""
    servicios = contexto['servicios_planta']
    return documento(
        titulo='Servicios industriales de la planta',
        alcance=contexto['unidad'].nombre,
        criterios=[
            ('Servicios con datos', str(servicios['con_datos'])),
            ('Equipos con valores de referencia', str(servicios['de_referencia'])),
        ],
        tarjetas=[
            (servicio['nombre'], servicio['total'] or 'Sin datos', servicio['nota'])
            for servicio in servicios['servicios']
        ],
        headers=['Servicio', 'Equipo o proceso', 'Unidades o descarga', 'Valor', 'Total o corrida base'],
        filas=[
            [
                servicio['nombre'],
                fila['equipo'].nombre if fila['equipo'] else fila['proceso'],
                str(fila['unidades']), fila['valor'], fila['subtotal'],
            ]
            for servicio in servicios['servicios']
            for fila in servicio['filas']
        ],
    )


CONSTRUCTORES = {
    'ficha': documento_de_ficha,
    'documentacion': documento_de_documentacion,
    'mis_ejercicios': documento_de_mis_ejercicios,
    'mis_simulaciones': documento_de_mis_simulaciones,
    'balance': documento_de_balance,
    'linea': documento_de_linea,
    'materiales': documento_de_materiales,
    'protocolos': documento_de_protocolos,
    'producto': documento_de_producto,
    'produccion': documento_de_produccion,
    'corridas_lotes': documento_de_corridas_lotes,
    'calidad': documento_de_calidad,
    'areas': documento_de_areas,
    'servicios': documento_de_servicios,
    'especificaciones': documento_de_especificaciones,
    'equipo': documento_de_equipo,
    'indice_materiales': documento_de_indice_procesos,
    'indice_metodos': documento_de_indice_procesos,
    'indice_empaque': documento_de_indice_procesos,
    'indice_documentacion': documento_de_indice_procesos,
}


def documento_de_pagina(clave, contexto):
    """El documento de una página del aula, armado con el contexto que ya tiene."""
    constructor = CONSTRUCTORES.get(clave)
    return constructor(contexto) if constructor else None
