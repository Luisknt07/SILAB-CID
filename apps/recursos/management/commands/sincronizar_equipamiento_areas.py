"""Convierte el equipamiento descrito en las fichas de área en inventario real y trazable de cada unidad.

Cada equipo de una ficha queda como un tipo de equipo con su ficha técnica (características, uso,
cuidados, ícono e imagen con su crédito) y tantas unidades físicas con código propio como dice la
ficha, asociadas al área y ubicadas en su zona del boceto. Si la unidad ya tenía ese equipo
registrado (por enlace o por el mismo nombre) se reutiliza y no se duplica. Los insumos pasan al
inventario de materiales y el software al catálogo de programas, instalado en las computadoras del
área. Así reservas, gestión, reportes y páginas públicas leen los mismos registros.

Lo que la unidad ya cargó no se pisa: solo se llenan los campos vacíos y se cambian los textos de
relleno («Demostración», «dato de prueba»). Los registros de prueba dejan de verse. El equipamiento
de alta capacidad se registra como no disponible hasta que la unidad lo confirme. Es idempotente y
`--simular` no guarda nada.
"""
import re
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.core.presentation.codigos_sistema import siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.recursos.presentation.catalogo_inventario import asignar_familia, clave_de_programa, heredar_foto, normalizar
from apps.gestion_unidades.management.fichas_area.imagenes_equipos import imagen_de_equipo
from apps.gestion_unidades.management.fichas_area.imagenes_insumos import imagen_de_insumo
from apps.gestion_unidades.management.fichas_area.logos_software import logo_de
from apps.gestion_unidades.management.fichas_area.sitios_software import SITIOS
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

# Textos de relleno de cargas demostrativas: no describen el equipo real.
RELLENOS = ('demostracion', 'demostrativ', 'registro de prueba', 'equipamiento institucional', 'registro operativo',
            'dato de prueba')
# Lo que describe al equipo con palabras: si es de relleno, la ficha del área lo reemplaza.
TEXTOS_DEL_TIPO = ('descripcion', 'caracteristicas_publicas', 'uso_publico', 'instrucciones_publicas')
# Valores técnicos que una carga demostrativa inventó; sin levantamiento declarado se vacían.
VALORES_DEMOSTRATIVOS = ('modo_operacion', 'capacidad_nominal', 'unidad_capacidad', 'capacidad_util_min',
                         'capacidad_util_max', 'tiempo_setup', 'tiempo_limpieza')
MAXIMO_DE_UNIDADES = 40
# Equipos donde se instala el software del área.
COMPUTADORAS = ('computador', 'estacion de trabajo', 'estacion grafica', 'workstation', 'portatil', 'laptop',
                'servidor', 'pc ', 'tableta', 'tablet', 'equipo de computo', 'puesto de')
CLASIFICACION = (
    ('proteccion', ('guante', 'mascarilla', 'cofia', 'bata', 'gafas de seguridad', 'protector', 'respirador',
                    'mandil', 'delantal', 'botas', 'tapon auditivo', 'careta')),
    ('limpieza', ('detergente', 'desinfectante', 'limpieza', 'jabon', 'sanitizante', 'cloro', 'toalla',
                  'alcohol isopropilico', 'paño', 'escoba')),
    ('reactivo', ('reactivo', 'medio de cultivo', 'agar', 'kit ', 'kits', 'solucion', 'buffer', 'tampon',
                  'etanol', 'acido', 'hidroxido', 'tincion', 'colorante', 'enzima', 'primer', 'cebador',
                  'estandar', 'patron', 'indicador', 'cuajo', 'cultivo')),
    ('empaque', ('envase', 'empaque', 'bolsa', 'frasco', 'etiqueta', 'film', 'caja', 'tapa', 'funda', 'tripa')),
    ('material', ('lamina', 'filamento', 'resina', 'cable', 'tornillo', 'madera', 'acrilico', 'mdf', 'componente',
                  'punta', 'tubo', 'papel', 'tarjeta', 'bateria', 'pila', 'vinilo', 'tela', 'hilo')),
)


class Simulacion(Exception):
    """Deshace la sincronización al final de una simulación."""


def es_relleno(texto):
    return any(relleno in normalizar(texto) for relleno in RELLENOS)


def cantidad_de(texto):
    """Cuántas unidades físicas registrar y si son opcionales («0 a 1»)."""
    numero = re.match(r'\s*(\d+)', texto or '')
    if not numero:
        return 1, False
    cantidad = int(numero.group(1))
    return max(1, min(cantidad, MAXIMO_DE_UNIDADES)), cantidad == 0


def clasificacion_de(nombre):
    clave = f' {normalizar(nombre)} '
    for clasificacion, palabras in CLASIFICACION:
        if any(f' {palabra}' in clave for palabra in palabras):
            return clasificacion
    return 'insumo'


def variantes_de(consumibles, clave):
    """Los insumos del inventario cuyas palabras están todas en el nombre de la ficha: «Filamento PLA blanco
    1,75 mm» dentro de «Filamento PLA 1,75 mm (blanco, azul, gris, negro y rojo)». La primera, la de código
    más corto, es la base de la familia."""
    palabras = set(clave.split())
    return sorted((consumible for nombre, consumible in consumibles.items()
                   if len(nombre.split()) >= 3 and set(nombre.split()) <= palabras),
                  key=lambda consumible: (len(consumible.codigo), consumible.codigo))


def completar_programa(programa, sitio, resumen):
    """El sitio oficial y su ícono, si la unidad todavía no los cargó."""
    cambios = []
    sitio = sitio or SITIOS.get(clave_de_programa(programa.nombre), '')
    if sitio and not programa.sitio_web:
        programa.sitio_web = sitio
        cambios.append('sitio_web')
    if not programa.logo and not programa.logo_catalogo and logo_de(programa.sitio_web):
        programa.logo_catalogo = logo_de(programa.sitio_web)
        cambios.append('logo_catalogo')
    if cambios:
        programa.save(update_fields=cambios)
        resumen['programas con sitio o logo'] += 1


def prefijo_de(espacio):
    return (espacio.codigo.split('-')[0] or 'AREA')[:5].upper()


class Command(BaseCommand):
    help = 'Registra como inventario trazable los equipos, insumos y software de las fichas de área.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', help='Slug de la unidad; se puede repetir.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        unidades = Unidad.objects.filter(espacios_reservables__ficha__isnull=False).distinct().order_by('nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
        total = Counter()
        for unidad in unidades:
            resumen = Counter()
            try:
                with transaction.atomic():
                    self._sincronizar(unidad, resumen)
                    if opciones['simular']:
                        raise Simulacion
                    if resumen:
                        registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=unidad,
                                            descripcion='Sincronización del equipamiento de las fichas de área',
                                            nuevos=dict(resumen))
            except Simulacion:
                pass
            total.update(resumen)
            prefijo = '[simulación] ' if opciones['simular'] else ''
            detalle = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in sorted(resumen.items())) or 'ya sincronizada'
            self.stdout.write(self.style.SUCCESS(f'{prefijo}{unidad.nombre}: {detalle}.'))
        self.stdout.write(', '.join(f'{cantidad} {nombre}' for nombre, cantidad in sorted(total.items())) or 'Nada que hacer.')

    def _sincronizar(self, unidad, resumen):
        self._retirar_pruebas(unidad, resumen)
        inventario = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True).distinct()
        # Equipos ya registrados que ninguna ficha describe: se enlazan por nombre en vez de duplicarse.
        sin_ficha = {}
        for equipo in inventario.filter(elementos_de_ficha__isnull=True).select_related('equipo'):
            sin_ficha.setdefault(normalizar(equipo.equipo.nombre), equipo)
        consumibles = {normalizar(c.nombre): c for c in Consumible.objects.filter(unidad=unidad)}
        # Los activos primero; uno que la unidad desactivó se enlaza igual, sin reactivarlo ni duplicarlo.
        programas = {}
        for programa in SoftwareDisponible.objects.filter(unidad=unidad).order_by('-activo', 'codigo'):
            programas.setdefault(clave_de_programa(programa.nombre), programa)
        fichas = FichaArea.objects.filter(espacio__unidad=unidad).select_related('espacio').prefetch_related('elementos')
        for ficha in fichas:
            espacio = ficha.espacio
            zona_de = {normalizar(nombre): zona['nombre'] for zona in ficha.zonas for nombre in zona['equipos']}
            # Una propuesta describe una capacidad por evaluar; nunca acredita
            # unidades físicas, stock ni instalaciones de software.
            elementos = list(ficha.elementos.filter(solo_referencia=False))
            software = [e.nombre for e in elementos if e.tipo == 'software']
            tipos, computadoras = {}, []
            for elemento in (e for e in elementos if e.tipo == 'equipo'):
                ubicacion = ' · '.join(filter(None, (espacio.nombre, zona_de.get(normalizar(elemento.nombre)))))
                tipo, unidades = self._equipo(unidad, espacio, elemento, ubicacion, software, sin_ficha, resumen)
                tipos[elemento.pk] = (elemento, tipo)
                if any(palabra in f'{normalizar(tipo.nombre)} ' for palabra in COMPUTADORAS):
                    computadoras += unidades
            for elemento in (e for e in elementos if e.tipo == 'insumo'):
                self._insumo(unidad, espacio, elemento, consumibles, tipos.values(), resumen)
            for elemento in (e for e in elementos if e.tipo == 'software'):
                self._software(unidad, espacio, elemento, programas, computadoras, resumen)
        # El software instalado que ninguna ficha nombra también recibe su sitio y su ícono.
        for programa in programas.values():
            completar_programa(programa, '', resumen)
        # Los insumos que ninguna ficha nombra también reciben su foto de catálogo.
        for consumible in Consumible.objects.filter(unidad=unidad, imagen_catalogo='').filter(Q(imagen='') | Q(imagen__isnull=True)):
            imagen = imagen_de_insumo(consumible.nombre)
            if imagen:
                consumible.imagen_catalogo, consumible.credito_imagen, consumible.fuente_imagen = imagen
                consumible.save(update_fields=['imagen_catalogo', 'credito_imagen', 'fuente_imagen'])
                resumen['insumos con imagen'] += 1
        # Todo el equipo de la unidad queda en su familia de producto, también el que no está en una ficha.
        vistos = set()
        for equipo in inventario.select_related('equipo'):
            if equipo.equipo_id in vistos:
                continue
            vistos.add(equipo.equipo_id)
            elemento = ElementoFichaArea.objects.filter(registrado__equipo=equipo.equipo).first()
            asignar_familia(equipo.equipo, resumen, *(filter(None, (elemento.nombre if elemento else '', equipo.equipo.nombre))))
            heredar_foto(equipo.equipo, resumen)

    @staticmethod
    def _retirar_pruebas(unidad, resumen):
        pruebas = UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad), Q(codigo_unidad__startswith='UNIT-TEST-')
            | Q(equipo__codigo__startswith='TEST-'), activa=True,
        ).distinct()
        for equipo in pruebas:
            equipo.activa = False
            equipo.estado_unidad = 'no_disponible'
            equipo.observaciones = 'Registro de prueba retirado del inventario de la unidad.'
            equipo.save(update_fields=['activa', 'estado_unidad', 'observaciones'])
            equipo.espacios_asociados.clear()
            resumen['registros de prueba retirados'] += 1

    def _equipo(self, unidad, espacio, elemento, ubicacion, software, sin_ficha, resumen):
        registrado = elemento.registrado if elemento.registrado_id and elemento.registrado.activa else None
        if registrado is None:
            registrado = self._ya_registrado(sin_ficha, normalizar(elemento.nombre))
        if registrado is not None:
            tipo = registrado.equipo
        else:
            # El código estándar del área (FAB-IMP3D-06); al rehacer la ficha, el elemento ya queda enlazado.
            tipo = EquiposServicios.objects.create(
                codigo=siguiente_codigo_modelo(unidad, espacio), nombre=elemento.nombre[:100],
                estado='disponible', rol='principal',
            )
            resumen['tipos de equipo creados'] += 1
        self._completar_tipo(tipo, elemento, software)
        cantidad, opcional = cantidad_de(elemento.cantidad)
        # Las unidades del área (o sin área) de ese tipo; lo que falta para la cantidad de la ficha se crea.
        unidades = list(UnidadEquipo.objects.filter(
            Q(espacios_asociados=espacio) | Q(espacios_asociados__isnull=True),
            Q(laboratorio=unidad) | Q(laboratorios=unidad), equipo=tipo, activa=True,
        ).distinct().order_by('codigo_unidad'))
        if registrado is not None and registrado not in unidades:
            unidades.insert(0, registrado)
        while len(unidades) < cantidad:
            codigo = siguiente_codigo_unidad(unidad, espacio, tipo)
            nueva = UnidadEquipo(
                codigo_unidad=codigo, equipo=tipo, laboratorio=unidad,
                estado_unidad='no_disponible' if (opcional or elemento.nivel == 'alta') else 'disponible',
                ubicacion_especifica=ubicacion[:200], criticidad='normal',
                observaciones=(
                    f'Registrado desde la ficha del área {espacio.nombre}. Confirmar marca, modelo y número de serie.'
                    + (' Equipamiento de alta capacidad: se habilita para reservas cuando la unidad lo confirme.'
                       if (opcional or elemento.nivel == 'alta') else '')
                ),
            )
            nueva.save()
            nueva.laboratorios.add(unidad)
            unidades.append(nueva)
            resumen['unidades de equipo creadas'] += 1
        for equipo in unidades:
            if not equipo.ubicacion_especifica or es_relleno(equipo.ubicacion_especifica):
                equipo.ubicacion_especifica = ubicacion[:200]
                equipo.save(update_fields=['ubicacion_especifica'])
            if (equipo.numero_serie or '').upper().startswith('DEMO-'):
                equipo.numero_serie = None
                equipo.save(update_fields=['numero_serie'])
            if not equipo.espacios_asociados.filter(pk=espacio.pk).exists():
                espacio.equipos_asociados.add(equipo)
                resumen['equipos asociados a su área'] += 1
        # Un puesto descrito aparte en la ficha conserva su propia unidad; si no tenía, toma la primera.
        enlace = registrado or unidades[0]
        if elemento.registrado_id != enlace.pk:
            elemento.registrado = enlace
            elemento.save(update_fields=['registrado'])
            resumen['equipos de ficha enlazados'] += 1
        return tipo, unidades

    @staticmethod
    def _ya_registrado(sin_ficha, clave):
        """El equipo del inventario con el mismo nombre, o con uno que contiene al otro («Estación de lavado y
        curado» y «Estación de lavado y curado de resina»); se saca de la lista para no enlazarlo dos veces."""
        if clave in sin_ficha:
            return sin_ficha.pop(clave)
        parecido = next((nombre for nombre in sin_ficha if len(min(nombre, clave, key=len).split()) >= 3
                         and (nombre in clave or clave in nombre)), None)
        return sin_ficha.pop(parecido) if parecido else None

    @staticmethod
    def _completar_tipo(tipo, elemento, software):
        """Llena lo vacío y cambia los rellenos; lo que la unidad escribió se respeta."""
        especificaciones = '\n'.join(f'{clave}: {valor}' if valor else clave for clave, valor in elemento.lista_especificaciones)
        if elemento.ejemplo and not es_relleno(elemento.ejemplo):
            especificaciones += f'\n{elemento.ejemplo}' if ':' in elemento.ejemplo else f'\nModelo de referencia: {elemento.ejemplo}'
        imagen = imagen_de_equipo(elemento.nombre)
        propuestos = {
            'descripcion': elemento.para_que,
            'caracteristicas_publicas': especificaciones.strip(),
            'uso_publico': elemento.para_que,
            'instrucciones_publicas': '\n'.join(elemento.lista_cuidados),
            'software': ', '.join(software),
            'icono': elemento.icono,
        }
        if imagen and not tipo.imagen and not tipo.imagen_catalogo:
            propuestos.update(imagen_catalogo=imagen[0], credito_imagen=imagen[1], fuente_imagen=imagen[2])
        demostrativo = any(es_relleno(getattr(tipo, campo)) for campo in TEXTOS_DEL_TIPO)
        cambios = [campo for campo, valor in propuestos.items()
                   if valor and (not getattr(tipo, campo) or (demostrativo and campo in TEXTOS_DEL_TIPO))]
        for campo in cambios:
            setattr(tipo, campo, propuestos[campo])
        if demostrativo and not tipo.origen_datos_tecnicos:
            for campo in VALORES_DEMOSTRATIVOS:
                if getattr(tipo, campo) not in (None, ''):
                    setattr(tipo, campo, '' if campo in ('modo_operacion', 'unidad_capacidad') else None)
                    cambios.append(campo)
        for campo in ('marca', 'modelo'):
            if getattr(tipo, campo) and es_relleno(getattr(tipo, campo)):
                setattr(tipo, campo, '')
                cambios.append(campo)
        if cambios:
            tipo.save(update_fields=cambios)

    @staticmethod
    def _insumo(unidad, espacio, elemento, consumibles, tipos, resumen):
        clave = normalizar(elemento.nombre)
        variantes = [consumibles[clave]] if clave in consumibles else variantes_de(consumibles, clave)
        consumible = variantes[0] if variantes else None
        if consumible is None:
            consumible = Consumible.objects.create(
                unidad=unidad, codigo=f'{prefijo_de(espacio)}-A{espacio.pk}-I{elemento.orden:02d}',
                nombre=elemento.nombre[:200], clasificacion=clasificacion_de(elemento.nombre),
                presentacion=elemento.ejemplo[:120], descripcion=elemento.para_que,
                instrucciones_solicitud=f'Consumo de referencia: {elemento.cantidad}.' if elemento.cantidad else '',
                ubicacion=espacio.nombre[:200], visible_en_reservas=False, activo=True,
            )
            consumibles[clave] = consumible
            resumen['insumos registrados'] += 1
        for variante in variantes:
            if es_relleno(variante.descripcion) and elemento.para_que:
                variante.descripcion = elemento.para_que
                variante.save(update_fields=['descripcion'])
                resumen['insumos con texto de relleno corregido'] += 1
        imagen = imagen_de_insumo(elemento.nombre) or imagen_de_insumo(consumible.nombre)
        if imagen and not consumible.imagen and not consumible.imagen_catalogo:
            consumible.imagen_catalogo, consumible.credito_imagen, consumible.fuente_imagen = imagen
            consumible.save(update_fields=['imagen_catalogo', 'credito_imagen', 'fuente_imagen'])
            resumen['insumos con imagen'] += 1
        if elemento.insumo_registrado_id != consumible.pk:
            elemento.insumo_registrado = consumible
            elemento.save(update_fields=['insumo_registrado'])
            resumen['insumos de ficha enlazados'] += 1
        # El insumo se ata a los equipos del área que lo nombran entre los que usan.
        palabras = set(clave.split()[:3])
        for equipo_de_ficha, tipo in tipos:
            if any(palabras <= set(normalizar(linea).split()) for linea in equipo_de_ficha.lista_consumibles):
                _relacion, creada = ConsumiblePorEquipo.objects.get_or_create(
                    consumible=consumible, equipo=tipo, defaults={'ubicacion': espacio.nombre[:200]})
                if creada:
                    resumen['insumos atados a su equipo'] += 1

    @staticmethod
    def _software(unidad, espacio, elemento, programas, computadoras, resumen):
        clave = clave_de_programa(elemento.nombre)
        programa = programas.get(clave)
        if programa is None:
            licencia = normalizar(elemento.licencia)
            en_linea = any(palabra in licencia or palabra in normalizar(elemento.para_que)
                           for palabra in ('web', 'en linea', 'nube', 'navegador'))
            programa = SoftwareDisponible.objects.create(
                unidad=unidad, nombre=elemento.nombre[:100], codigo=f'{prefijo_de(espacio)}-A{espacio.pk}-S{elemento.orden:02d}',
                descripcion=elemento.para_que,
                tipo_recurso='software' if any(p in licencia for p in ('libre', 'gratuit', 'abierto', 'open')) else 'licencia',
                tipo_acceso='remoto' if en_linea else 'instalacion',
                licencias_totales=max(1, len(computadoras)), licencias_disponibles=max(1, len(computadoras)),
                requiere_reserva=False,
                instrucciones_acceso='. '.join(filter(None, (f'Licencia: {elemento.licencia}' if elemento.licencia else '',
                                                             elemento.url))),
                activo=True,
            )
            programas[clave] = programa
            resumen['programas registrados'] += 1
        completar_programa(programa, elemento.url, resumen)
        nuevos = [equipo for equipo in computadoras if not programa.equipos_instalados.filter(pk=equipo.pk).exists()]
        if nuevos:
            programa.equipos_instalados.add(*nuevos)
            resumen['instalaciones de software'] += len(nuevos)
        if elemento.software_registrado_id != programa.pk:
            elemento.software_registrado = programa
            elemento.save(update_fields=['software_registrado'])
            resumen['programas de ficha enlazados'] += 1
