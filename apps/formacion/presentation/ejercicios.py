"""Ejercicios del aula: un escenario por estudiante, corregido por el mismo motor.

El docente arma un ejercicio sobre un proceso real y uno de los tres
simuladores de la unidad. Cada participante de la sesión recibe su propia
escala, de modo que dos estudiantes no resuelven el mismo número. Las
preguntas se responden con el simulador abierto y se corrigen contra el motor
de la planta con la tolerancia que el docente fijó: la nota sale de la
ingeniería, no de una respuesta guardada a mano. El docente puede ajustarla y
comentar.
"""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.reservas.models.reservas import Reserva
from apps.formacion.models.asignaturas import TemaAsignatura
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.aula import SIMULADORES_EJERCICIO

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.plantas_piloto.operacion.presentation.motores import balance_de_energia, balance_de_linea, etapas_termicas, masa_de, requerimiento_de_materiales
from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido, respuesta_pdf
from apps.formacion.presentation.documentos_aula import documento_de_pagina
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, datos_de_receta


def _num(valor):
    return Decimal(str(valor if valor not in (None, '') else 0))


def _redondeo(clave):
    """Cuánto decimal se le pide al estudiante en cada respuesta."""
    return {
        'estaciones': Decimal('1'),
        'insumos': Decimal('1'),
        'faltantes': Decimal('1'),
        'ciclo': Decimal('1'),
    }.get(clave, Decimal('0.01'))


# --------------------------------------------------------------- las preguntas
def _preguntas_balance(ejercicio, factor):
    datos = datos_de_receta(ejercicio.receta, factor)
    calientes, _frias = etapas_termicas(datos)
    parametros = ejercicio.parametros or {}
    por_defecto = next((fila['temperatura'] for fila in calientes if fila['temperatura'] is not None), Decimal('65'))
    t_proceso = _num(parametros.get('t_proceso') or por_defecto)
    t_inicial = _num(parametros.get('t_inicial') if parametros.get('t_inicial') not in (None, '') else 4)
    t_final = _num(parametros.get('t_final') if parametros.get('t_final') not in (None, '') else 4)
    eficiencia = _num(parametros.get('eficiencia') or 85)
    energia = balance_de_energia(
        datos,
        t_inicial=t_inicial,
        t_proceso=t_proceso,
        t_final=t_final,
        eficiencia=eficiencia / 100,
        potencia_kw=_num(parametros.get('potencia_kw')),
    )
    masa = balance_de_masa(datos)
    return [
        {
            'clave': 'masa_entrada',
            'texto': 'Masa que entra a la corrida',
            'unidad': 'kg',
            'ayuda': 'Los litros de leche pesan su densidad: el simulador lo dice en la primera tarjeta.',
            'esperado': masa_de(datos),
        },
        {
            'clave': 'producto',
            'texto': 'Producto principal que rinde la corrida',
            'unidad': datos['unidad_producto'],
            'ayuda': 'El rendimiento esperado del proceso a esta escala.',
            'esperado': _num(masa['producto_esperado']),
        },
        {
            'clave': 'calor_kwh',
            'texto': f'Energía para llevar la masa de {_texto(t_inicial)} a {_texto(t_proceso)} °C',
            'unidad': 'kWh',
            'ayuda': f'Con {_texto(eficiencia)} % de eficiencia del equipo.',
            'esperado': _num(energia['calor_kwh']),
        },
        {
            'clave': 'vapor_kg',
            'texto': 'Vapor que hace falta para ese calentamiento',
            'unidad': 'kg',
            'ayuda': 'El calor suministrado dividido por el calor latente del vapor.',
            'esperado': _num(energia['vapor_kg']),
        },
    ]


def _preguntas_linea(ejercicio, factor):
    parametros = ejercicio.parametros or {}
    jornada = _num(parametros.get('jornada') or 8)
    datos = datos_de_receta(ejercicio.receta)
    linea = balance_de_linea(datos, corridas=factor, jornada_min=jornada * 60)
    return [
        {
            'clave': 'takt',
            'texto': f'Ritmo que pide la jornada para {_texto(factor)} corridas en {_texto(jornada)} horas',
            'unidad': 'min',
            'ayuda': 'Minutos de jornada divididos por las corridas pedidas.',
            'esperado': _num(linea['takt']),
        },
        {
            'clave': 'ciclo',
            'texto': 'Tiempo de trabajo del cuello de botella',
            'unidad': 'min',
            'ayuda': 'La etapa que más trabajo pide; marca el ritmo real de la línea.',
            'esperado': _num(linea['ciclo']),
        },
        {
            'clave': 'estaciones',
            'texto': 'Estaciones en que queda repartida la línea',
            'unidad': '',
            'ayuda': 'Etapas consecutivas agrupadas mientras quepan en el takt.',
            'esperado': _num(linea['numero_estaciones']),
        },
        {
            'clave': 'eficiencia',
            'texto': 'Eficiencia de la línea equilibrada',
            'unidad': '%',
            'ayuda': 'Trabajo total sobre estaciones por takt.',
            'esperado': _num(linea['eficiencia']),
        },
    ]


def _preguntas_materiales(ejercicio, factor):
    plan = [{'receta': ejercicio.receta, 'factor': Decimal(factor), 'etiqueta': ejercicio.receta.nombre}]
    requerimiento = requerimiento_de_materiales(plan)
    base = next(
        (
            insumo for insumo in ejercicio.receta.insumos.select_related('consumible').order_by('pk')
            if insumo.forma_parte == 'base'
        ),
        None,
    )
    bruto_base = Decimal('0')
    unidad_base = ''
    if base is not None:
        bruto_base = _num(base.cantidad) * Decimal(factor)
        unidad_base = base.consumible.unidad_medida or ''
    principal = next((salida for salida in requerimiento['salidas'] if salida['principal']), None)
    return [
        {
            'clave': 'materia_prima',
            'texto': f'Materia prima base que pide el plan{f" ({base.consumible.nombre})" if base else ""}',
            'unidad': unidad_base,
            'ayuda': 'La cantidad de la receta multiplicada por las corridas del plan.',
            'esperado': bruto_base,
        },
        {
            'clave': 'insumos',
            'texto': 'Insumos distintos que consume el plan',
            'unidad': '',
            'ayuda': 'Cada renglón de la lista de materiales cuenta una vez.',
            'esperado': _num(requerimiento['insumos']),
        },
        {
            'clave': 'faltantes',
            'texto': 'Insumos que el inventario no alcanza a cubrir',
            'unidad': '',
            'ayuda': 'Sin tocar el stock de seguridad de cada insumo.',
            'esperado': _num(requerimiento['faltantes']),
        },
        {
            'clave': 'producto',
            'texto': 'Producto principal que rinde el plan',
            'unidad': principal['unidad'] if principal else '',
            'ayuda': 'La salida principal de la receta a esta escala.',
            'esperado': _num(principal['cantidad']) if principal else Decimal('0'),
        },
    ]


MOTORES = {
    'balance': _preguntas_balance,
    'linea': _preguntas_linea,
    'materiales': _preguntas_materiales,
}


def _texto(valor, paso=Decimal('0.01')):
    numero = Decimal(valor).quantize(paso)
    entero = numero.to_integral_value()
    if numero == entero:
        return str(int(entero))
    return format(numero.normalize(), 'f')


def preguntas_de(ejercicio, factor):
    """Las preguntas del ejercicio a esa escala, con el valor que da el motor."""
    motor = MOTORES.get(ejercicio.simulador)
    if motor is None:
        raise ValidationError('Ese simulador no tiene preguntas definidas.')
    preguntas = motor(ejercicio, Decimal(factor))
    for pregunta in preguntas:
        paso = _redondeo(pregunta['clave'])
        pregunta['esperado'] = Decimal(pregunta['esperado']).quantize(paso)
        pregunta['esperado_texto'] = _texto(pregunta['esperado'], paso)
    return preguntas


def url_del_simulador(ejercicio, factor):
    """El simulador del ejercicio, abierto con los datos que le tocan al estudiante."""
    slug = ejercicio.unidad.slug
    parametros = ejercicio.parametros or {}
    if ejercicio.simulador == 'balance':
        consulta = [f'receta={ejercicio.receta_id}', f'cantidad={_texto(ejercicio.receta.cantidad_base * Decimal(factor))}']
        for clave in ('t_inicial', 't_proceso', 't_final', 'eficiencia', 'potencia_kw'):
            if parametros.get(clave) not in (None, ''):
                consulta.append(f'{clave}={parametros[clave]}')
        return reverse('simulador_balance', args=[slug]) + '?' + '&'.join(consulta)
    if ejercicio.simulador == 'linea':
        jornada = parametros.get('jornada') or 8
        return (
            reverse('simulador_linea', args=[slug])
            + f'?receta={ejercicio.receta_id}&corridas={_texto(Decimal(factor))}&jornada={jornada}'
        )
    return (
        reverse('simulador_materiales', args=[slug])
        + f'?receta={ejercicio.receta_id}&factor={_texto(Decimal(factor))}'
    )


# ------------------------------------------------------------- la asignación
def estudiantes_de(ejercicio):
    """Quiénes reciben el ejercicio: los participantes de la sesión, y quien la pidió."""
    if ejercicio.reserva_id is None:
        return []
    reserva = ejercicio.reserva
    personas = list(reserva.participantes.all().order_by('last_name', 'username', 'pk'))
    if reserva.usuario_id and all(persona.pk != reserva.usuario_id for persona in personas):
        personas.append(reserva.usuario)
    return personas


def asignar_intentos(ejercicio):
    """A cada estudiante su escala; quien ya tenía el suyo lo conserva."""
    if ejercicio.reserva_id is None:
        raise ValidationError('El ejercicio necesita una sesión para saber a quién se le asigna.')
    personas = estudiantes_de(ejercicio)
    if not personas:
        raise ValidationError('La sesión todavía no tiene participantes registrados.')
    creados = []
    for indice, persona in enumerate(personas):
        intento, creado = IntentoEjercicio.objects.get_or_create(
            ejercicio=ejercicio,
            estudiante=persona,
            defaults={'factor': ejercicio.factor_para(indice)},
        )
        if creado:
            creados.append(intento)
    return creados


# ------------------------------------------------------------ la calificación
def calificar(intento, respuestas):
    """Compara cada respuesta con el motor y reparte el puntaje entre las preguntas."""
    ejercicio = intento.ejercicio
    preguntas = preguntas_de(ejercicio, intento.factor)
    tolerancia = Decimal(ejercicio.tolerancia_pct) / 100
    valor_pregunta = Decimal(ejercicio.puntaje) / len(preguntas)
    resultados, puntaje, guardadas = [], Decimal('0'), {}
    for pregunta in preguntas:
        bruto = str(respuestas.get(pregunta['clave'], '') or '').strip().replace(',', '.')
        guardadas[pregunta['clave']] = bruto
        try:
            valor = Decimal(bruto)
        except InvalidOperation:
            valor = None
        esperado = pregunta['esperado']
        margen = abs(esperado) * tolerancia
        # Una respuesta que debe dar cero se admite con el margen mínimo de su redondeo.
        if margen == 0:
            margen = _redondeo(pregunta['clave'])
        correcta = valor is not None and abs(valor - esperado) <= margen
        if correcta:
            puntaje += valor_pregunta
        resultados.append({
            'clave': pregunta['clave'],
            'texto': pregunta['texto'],
            'unidad': pregunta['unidad'],
            'esperado': pregunta['esperado_texto'],
            'respuesta': bruto,
            'correcta': correcta,
        })
    intento.respuestas = guardadas
    intento.resultados = resultados
    intento.puntaje = puntaje.quantize(Decimal('0.01'))
    intento.estado = 'calificado'
    intento.entregado_en = intento.entregado_en or timezone.now()
    intento.calificado_en = timezone.now()
    intento.save()
    return intento


def resumen_de(ejercicio):
    """Cuántos entregaron, cuántos acertaron y con qué nota promedio."""
    intentos = list(ejercicio.intentos.select_related('estudiante').all())
    calificados = [intento for intento in intentos if intento.puntaje is not None]
    promedio = (
        sum((Decimal(intento.puntaje) for intento in calificados), Decimal('0')) / len(calificados)
        if calificados else None
    )
    return {
        'intentos': intentos,
        'asignados': len(intentos),
        'entregados': len(calificados),
        'pendientes': len(intentos) - len(calificados),
        'promedio': promedio.quantize(Decimal('0.01')) if promedio is not None else None,
    }


# ----------------------------------------------------------------- el panel
def _texto_post(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def contexto_ejercicios(unidad, permisos_operativos):
    """Lo que la pestaña del aula muestra: los ejercicios y cómo van sus estudiantes."""
    puede = bool(permisos_operativos.get('practicas'))
    recetas = list(Receta.objects.filter(unidad=unidad, activa=True).order_by('nombre'))
    if not recetas:
        # Sin procesos publicados no hay nada que simular: la pestaña no aparece.
        return {'ejercicios_habilitados': False, 'puede_operar_ejercicios': False}
    ejercicios = list(
        EjercicioAula.objects.filter(unidad=unidad)
        .select_related('receta', 'reserva', 'tema')
        .prefetch_related('intentos__estudiante')
        .order_by('-creado_en', '-pk')[:30]
    )
    filas = []
    for ejercicio in ejercicios:
        resumen = resumen_de(ejercicio)
        filas.append({
            'ejercicio': ejercicio,
            'resumen': resumen,
            'url': reverse('resultados_ejercicio', args=[unidad.slug, ejercicio.pk]),
        })
    hoy = timezone.localdate()
    sesiones = list(
        Reserva.objects.filter(
            laboratorio=unidad, receta__isnull=False, fecha__gte=hoy - timedelta(days=60),
        )
        .select_related('receta')
        .order_by('-fecha', '-pk')[:40]
    )
    return {
        'ejercicios_habilitados': puede,
        'puede_operar_ejercicios': puede,
        'ejercicios_aula': filas,
        'ejercicios_abiertos': [fila for fila in filas if fila['ejercicio'].abierto],
        'intentos_pendientes': sum(fila['resumen']['pendientes'] for fila in filas),
        'simuladores_ejercicio': SIMULADORES_EJERCICIO,
        'estados_ejercicio': EjercicioAula.ESTADOS,
        'recetas_para_ejercicio': recetas,
        'sesiones_para_ejercicio': sesiones,
        'temas_para_ejercicio': list(
            TemaAsignatura.objects.filter(asignatura__unidad=unidad)
            .select_related('asignatura').order_by('asignatura__nombre', 'orden')
        ),
    }


def operar_ejercicio(request, unidad):
    registro_id = _texto_post(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(EjercicioAula.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id else EjercicioAula(unidad=unidad, creado_por=request.user)
    )
    if _texto_post(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el ejercicio que quieres cerrar.')
        objeto.estado = 'cerrado'
        objeto.save(update_fields=['estado', 'actualizado_en'])
        return objeto, 'Ejercicio cerrado', False
    if _texto_post(request, 'accion_ejercicio') == 'asignar':
        if creado:
            raise ValidationError('Guarda el ejercicio antes de asignarlo.')
        nuevos = asignar_intentos(objeto)
        if objeto.estado == 'borrador':
            objeto.estado = 'abierto'
            objeto.save(update_fields=['estado', 'actualizado_en'])
        return objeto, f'Ejercicio asignado: {len(nuevos)} estudiantes nuevos', False
    objeto.nombre = _texto_post(request, 'nombre', 160)
    simulador = _texto_post(request, 'simulador') or 'balance'
    if simulador not in MOTORES:
        raise ValidationError('Elige uno de los simuladores de la unidad.')
    objeto.simulador = simulador
    receta_id = _texto_post(request, 'receta_id')
    if not receta_id:
        raise ValidationError('Selecciona el proceso del ejercicio.')
    objeto.receta = get_object_or_404(Receta, pk=receta_id, unidad=unidad, activa=True)
    reserva_id = _texto_post(request, 'reserva_id')
    objeto.reserva = (
        get_object_or_404(Reserva, pk=reserva_id, laboratorio=unidad) if reserva_id else None
    )
    tema_id = _texto_post(request, 'tema_id')
    objeto.tema = (
        get_object_or_404(TemaAsignatura, pk=tema_id, asignatura__unidad=unidad) if tema_id else None
    )
    objeto.consigna = _texto_post(request, 'consigna')
    if not objeto.consigna:
        raise ValidationError('Escribe la consigna: qué debe hacer el estudiante.')
    objeto.factor_base = _decimal_positivo(request.POST.get('factor_base'), 'La escala del primero')
    objeto.paso = _decimal_no_negativo(request.POST.get('paso'), 'El paso entre estudiantes')
    objeto.tolerancia_pct = _decimal_no_negativo(request.POST.get('tolerancia_pct'), 'La tolerancia')
    objeto.puntaje = _decimal_positivo(request.POST.get('puntaje'), 'El puntaje')
    limite = _texto_post(request, 'fecha_limite')
    objeto.fecha_limite = datetime.strptime(limite, '%Y-%m-%d').date() if limite else None
    estado = _texto_post(request, 'estado') or objeto.estado
    if estado not in dict(EjercicioAula.ESTADOS):
        raise ValidationError('Elige un estado válido.')
    objeto.estado = estado
    objeto.parametros = {
        clave: (request.POST.get(clave) or '').strip()
        for clave in ('t_inicial', 't_proceso', 't_final', 'eficiencia', 'potencia_kw', 'jornada')
        if (request.POST.get(clave) or '').strip()
    }
    objeto.full_clean(exclude=['codigo'])
    objeto.save()
    return objeto, 'Ejercicio creado' if creado else 'Ejercicio actualizado', creado


def operar_intento_ejercicio(request, unidad):
    registro_id = _texto_post(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona la entrega que quieres revisar.')
    objeto = get_object_or_404(
        IntentoEjercicio.objects.select_for_update(), pk=registro_id, ejercicio__unidad=unidad,
    )
    puntaje = (request.POST.get('puntaje') or '').strip()
    if puntaje:
        objeto.puntaje = _decimal_no_negativo(puntaje, 'El puntaje')
        if objeto.puntaje > Decimal(objeto.ejercicio.puntaje):
            raise ValidationError('El puntaje no puede superar al del ejercicio.')
        objeto.estado = 'calificado'
        objeto.calificado_en = timezone.now()
    objeto.comentario = _texto_post(request, 'comentario')
    objeto.save()
    return objeto, 'Entrega revisada', False


def _decimal_positivo(texto, nombre):
    valor = _decimal_no_negativo(texto, nombre)
    if valor <= 0:
        raise ValidationError(f'{nombre} debe ser mayor que cero.')
    return valor


def _decimal_no_negativo(texto, nombre):
    try:
        valor = Decimal(str(texto or '0').strip().replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError(f'{nombre} debe ser un número.') from error
    if valor < 0:
        raise ValidationError(f'{nombre} no puede ser negativa.')
    return valor


OPERADORES_EJERCICIOS = {
    'ejercicio_aula': operar_ejercicio,
    'intento_ejercicio': operar_intento_ejercicio,
}
PERMISOS_EJERCICIOS = {clave: 'practicas' for clave in OPERADORES_EJERCICIOS}
MODELOS_EJERCICIOS = {
    'ejercicio_aula': EjercicioAula,
    'intento_ejercicio': IntentoEjercicio,
}


# ----------------------------------------------------------------- las vistas
@xframe_options_sameorigin
@login_required
def mis_ejercicios_view(request, slug):
    """Los ejercicios que un estudiante tiene asignados en esta unidad."""
    unidad = get_object_or_404(Unidad, slug=slug)
    intentos = list(
        IntentoEjercicio.objects.filter(ejercicio__unidad=unidad, estudiante=request.user)
        .exclude(ejercicio__estado='borrador')
        .select_related('ejercicio__receta', 'ejercicio__reserva')
        .order_by('ejercicio__fecha_limite', '-pk')
    )
    filas = [
        {
            'intento': intento,
            'url': reverse('resolver_ejercicio', args=[unidad.slug, intento.pk]),
            'simulador_url': url_del_simulador(intento.ejercicio, intento.factor),
        }
        for intento in intentos
    ]
    contexto = {
        'unidad': unidad,
        'filas': filas,
        'pendientes': [fila for fila in filas if fila['intento'].estado == 'asignado'],
        'estudiante': request.user.get_full_name() or request.user.username,
        'generado_en': timezone.localtime(),
        'volver_url': unidad.get_absolute_url(),
        **enlaces_de_documento(request),
    }
    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(
            documento_de_pagina('mis_ejercicios', contexto),
            f'mis-ejercicios-{unidad.slug}.pdf',
            formato,
        )
    return render(request, 'portal/pages/unidades/aula/mis_ejercicios.html', contexto)


@xframe_options_sameorigin
@login_required
@require_http_methods(['GET', 'POST'])
def resolver_ejercicio_view(request, slug, intento_id):
    """El ejercicio de un estudiante: su escala, su simulador y sus respuestas."""
    unidad = get_object_or_404(Unidad, slug=slug)
    intento = get_object_or_404(
        IntentoEjercicio.objects.select_related('ejercicio__receta', 'ejercicio__reserva', 'estudiante'),
        pk=intento_id, ejercicio__unidad=unidad,
    )
    docente = puede_operar_modulo_unidad(request.user, unidad, 'practicas')
    if intento.estudiante_id != request.user.pk and not docente:
        raise PermissionDenied('Ese ejercicio es de otra persona.')
    ejercicio = intento.ejercicio
    error = ''
    if request.method == 'POST':
        if intento.estudiante_id != request.user.pk:
            raise PermissionDenied('Solo el estudiante entrega su propio ejercicio.')
        if not ejercicio.abierto:
            error = 'El ejercicio no está abierto: ya no admite entregas.'
        elif ejercicio.vencido:
            error = 'El plazo del ejercicio venció.'
        else:
            with transaction.atomic():
                calificar(intento, request.POST)
            return redirect(reverse('resolver_ejercicio', args=[unidad.slug, intento.pk]) + '?hecho=1')
    preguntas = preguntas_de(ejercicio, intento.factor)
    if intento.estado != 'calificado' or intento.estudiante_id != request.user.pk:
        # Mientras no entregue, el estudiante no ve el valor que espera el motor.
        for pregunta in preguntas:
            pregunta['esperado_texto'] = ''
    return render(request, 'portal/pages/unidades/aula/ejercicio.html', {
        'unidad': unidad,
        'intento': intento,
        'ejercicio': ejercicio,
        'preguntas': preguntas,
        'respuestas': intento.respuestas or {},
        'simulador_url': url_del_simulador(ejercicio, intento.factor),
        'escala': (
            f'{_texto(ejercicio.receta.cantidad_base * Decimal(intento.factor))} '
            f'{ejercicio.receta.unidad_base}'
        ),
        'error': error,
        'hecho': request.GET.get('hecho') == '1',
        'es_docente': docente,
        'generado_en': timezone.localtime(),
        'volver_url': reverse('mis_ejercicios', args=[unidad.slug]),
    })


@xframe_options_sameorigin
@login_required
def resultados_ejercicio_view(request, slug, ejercicio_id):
    """La hoja del docente: quién entregó, con qué escala y con qué nota."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, 'practicas'):
        raise PermissionDenied('Solo quien conduce las prácticas ve los resultados.')
    ejercicio = get_object_or_404(
        EjercicioAula.objects.select_related('receta', 'reserva', 'tema'), pk=ejercicio_id, unidad=unidad,
    )
    resumen = resumen_de(ejercicio)
    filas = []
    for intento in resumen['intentos']:
        filas.append({
            'intento': intento,
            'preguntas': preguntas_de(ejercicio, intento.factor),
            'url': reverse('resolver_ejercicio', args=[unidad.slug, intento.pk]),
        })
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/resultados_ejercicio.html', {
        'unidad': unidad,
        'ejercicio': ejercicio,
        'resumen': resumen,
        'filas': filas,
        'generado_en': timezone.localtime(),
        'volver_url': reverse('gestion_unidad', args=[unidad.slug]) + '?view=ejercicios',
    })
