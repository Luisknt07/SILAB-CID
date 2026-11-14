"""Completa el FabLab solicitado sin convertir propuestas en existencias.

Por defecto simula. --aplicar guarda sólo esta unidad. No inventa números de
serie, recepciones, licencias instaladas, movimientos, precios ni vida útil.
"""
from collections import Counter
import re
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.core.presentation.codigos_sistema import siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.management.catalogos.fablab_2026 import (
    CATALOGOS_APORTADOS, DECLARADOS, FECHA_REVISION, FUENTE, MATERIALES, MATERIALES_COMUNES, PROPUESTAS, SLUG,
    SOFTWARE, X1_ESPECIFICACIONES, X1_FUENTE,
)
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


def normalizar(valor):
    texto = unicodedata.normalize('NFKD', valor or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', texto.lower())


class Command(BaseCommand):
    help = 'Prepara fichas, dotación propuesta y 12 impresoras declaradas del FabLab. Simula salvo --aplicar.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Guarda la preparación revisada de esta unidad.')

    def handle(self, *args, **opciones):
        with transaction.atomic():
            unidad = Unidad.objects.select_for_update().filter(slug=SLUG).first()
            if not unidad:
                raise CommandError('No existe el FabLab solicitado; no se prepara otra unidad.')
            resumen, avisos = self.preparar(unidad)
            if opciones['aplicar']:
                registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=unidad,
                    descripcion='Preparación FabLab: fichas con fuentes, dotación propuesta y cantidades declaradas',
                    nuevos=dict(resumen))
            else:
                transaction.set_rollback(True)
        self.stdout.write(('Aplicado' if opciones['aplicar'] else 'Simulación sin guardar') + ': ' +
                          ', '.join(f'{v} {k}' for k, v in resumen.items()))
        for aviso in avisos:
            self.stdout.write('Revisar: ' + aviso)

    def preparar(self, unidad):
        resumen, avisos = Counter(), []
        areas = {a.codigo: a for a in EspacioReservable.objects.filter(unidad=unidad)}
        area = areas.get('FAB-AREA-IMP3D')
        if area is None:
            raise CommandError('Falta el área de manufactura aditiva; no se inventa su ubicación ni aforo.')
        categoria = CategoriaEquipo.objects.filter(nombre__iexact='Impresión 3D').first()
        if categoria is None:
            categoria, _ = CategoriaEquipo.objects.get_or_create(codigo='IMP3D', defaults={
                'nombre': 'Impresión 3D', 'icono': 'fas fa-cubes', 'color': '#006633'})
        modelos = {}
        for dato in DECLARADOS:
            modelo = self._modelo(unidad, area, dato, categoria, resumen)
            modelos[dato['clave']] = modelo
            activos = list(UnidadEquipo.objects.filter(
                Q(laboratorio=unidad) | Q(laboratorios=unidad), equipo=modelo).distinct().order_by('pk'))
            while len(activos) < dato['cantidad']:
                activo = UnidadEquipo.objects.create(
                    codigo_unidad=siguiente_codigo_unidad(unidad, area, modelo), equipo=modelo, laboratorio=unidad,
                    estado_unidad='no_disponible', activa=True, existencia_verificada=False,
                    origen_adquisicion='otro',
                    existencia_nota=f'Cantidad declarada por el responsable el {FECHA_REVISION}; pendiente placa, serie y bodega.',
                    observaciones='Existencia declarada. Confirmar condición física, origen y habilitación antes de reservar.',
                    ubicacion_especifica=area.nombre,
                )
                activo.laboratorios.add(unidad)
                area.equipos_asociados.add(activo)
                activos.append(activo)
                resumen['activos declarados añadidos'] += 1
            if len(activos) > dato['cantidad']:
                avisos.append(f'{modelo.modelo}: {len(activos)} registros frente a {dato["cantidad"]} declarados; conciliar sin borrar.')
            self._elemento_confirmado(area, modelo, activos, dato, resumen)
            self._compatibles(unidad, modelo, resumen)
        # PF001-P es el número de modelo de X1-Carbon en la declaración UE.
        adscritos = Q(unidades__laboratorio=unidad) | Q(unidades__laboratorios=unidad)
        x1 = (EquiposServicios.objects.filter(adscritos, modelo__iregex=r'^PF001\s*-\s*P$')
              .distinct().first())
        if x1:
            self._ficha_modelo(x1, dict(nombre='Impresora 3D FDM X1-Carbon', marca='Bambu Lab', modelo='X1-Carbon',
                especificaciones=X1_ESPECIFICACIONES, fuente=X1_FUENTE,
                cuidados=('Usar el perfil oficial y verificar las zonas excluidas de la cama.',
                          'Controlar limpieza, secado y componentes según manual; registrar horas e incidencias.'),
                repuestos=()), resumen, corregir_identidad=True)
            modelos['x1'] = x1
        else:
            x1 = EquiposServicios.objects.filter(adscritos, modelo__iexact='X1-Carbon').distinct().first()
            if x1:
                modelos['x1'] = x1
        self._software_propuesto(unidad, area, modelos, resumen)
        self._materiales_propuestos(unidad, areas, modelos, resumen)
        self._catalogos_aportados(unidad, resumen)
        for codigo, nombre, nivel, uso, url, condicion in PROPUESTAS:
            espacio = areas.get(codigo)
            if not espacio:
                avisos.append(f'Área {codigo} inexistente: se omite su propuesta, sin crear aforo ni ubicación.')
                continue
            # Las áreas integradas siguen conservando su ficha propia como
            # referencia funcional; no se reactivan ni trasladan sus activos.
            ficha, _ = FichaArea.objects.get_or_create(espacio=espacio, defaults={'fuente': FUENTE, 'publicada': False})
            _, nuevo = ElementoFichaArea.objects.get_or_create(ficha=ficha, tipo='equipo', nombre=nombre, defaults={
                'solo_referencia': True, 'nivel': nivel, 'para_que': uso[:300],
                'cantidad': 'Por dimensionar con demanda y capacidad existentes', 'ejemplo': 'Capacidad por evaluar; no adquirida',
                'especificaciones': 'Criterio de evaluación: ' + condicion + '\nFuente de consulta: ' + url,
                'cuidados': condicion, 'url': url, 'orden': 500})
            resumen['propuestas añadidas'] += nuevo
        avisos.append('Los registros genéricos previos y las fichas duplicadas de resina requieren conciliación por serie; no se fusionaron activos.')
        return resumen, avisos

    def _modelo(self, unidad, area, dato, categoria, resumen):
        candidatos = EquiposServicios.objects.filter(
            Q(unidades__laboratorio=unidad) | Q(unidades__laboratorios=unidad),
        ).distinct()
        encontrados = [m for m in candidatos if normalizar(m.marca) == normalizar(dato['marca'])
                       and normalizar(m.modelo) == normalizar(dato['modelo'])]
        if len(encontrados) > 1:
            raise CommandError(f'{dato["modelo"]}: varios modelos coinciden; conciliarlos antes de crear activos.')
        if encontrados:
            modelo = encontrados[0]
        else:
            modelo = EquiposServicios.objects.create(codigo=siguiente_codigo_modelo(unidad, area),
                nombre=dato['nombre'], marca=dato['marca'], modelo=dato['modelo'], estado='no_disponible', cantidad=0)
            resumen['modelos añadidos'] += 1
        self._ficha_modelo(modelo, dato, resumen)
        modelo.categorias.add(categoria)
        return modelo

    @staticmethod
    def _ficha_modelo(modelo, dato, resumen, corregir_identidad=False):
        """Completa lo faltante sin sustituir mediciones ni ediciones del responsable.

        La identificación PF001-P tiene una corrección documental explícita;
        esa excepción no autoriza a reemplazar el resto de la ficha técnica.
        """
        medido = modelo.origen_datos_tecnicos == 'medido'
        if medido and not corregir_identidad:
            return
        anteriores = dict(modelo.especificaciones or {})
        specs = dict(anteriores)
        referencia = dict(dato['especificaciones'], **{'Fuente técnica': dato['fuente'], 'Revisión de fuente': FECHA_REVISION})
        for clave, valor in referencia.items():
            if clave not in specs or specs[clave] in ('', None):
                specs[clave] = valor
        propuestos = dict(nombre=dato['nombre'], marca=dato['marca'], modelo=dato['modelo'],
            caracteristicas_publicas='\n'.join(f'{k}: {v}' for k, v in specs.items()),
            uso_publico='Prototipado y fabricación con perfil validado; contrastar prestaciones con el trabajo solicitado.',
            instrucciones_publicas='\n'.join(dato['cuidados']), origen_datos_tecnicos='referencia')
        valores = {campo: valor for campo, valor in propuestos.items() if not getattr(modelo, campo)}
        valores['especificaciones'] = specs
        # El texto que el comando generó y nadie editó puede reflejar las claves
        # añadidas; una descripción libre o modificada se conserva literalmente.
        texto_anterior = '\n'.join(f'{k}: {v}' for k, v in anteriores.items())
        if (anteriores.get('Fuente técnica') and anteriores.get('Revisión de fuente')
                and modelo.caracteristicas_publicas == texto_anterior):
            valores['caracteristicas_publicas'] = propuestos['caracteristicas_publicas']
        if medido:
            valores = {}  # La carga de referencia no completa ni altera un levantamiento validado.
        if corregir_identidad:
            valores.update({campo: dato[campo] for campo in ('nombre', 'marca', 'modelo')})
        # Las piezas son referencias técnicas, no cantidades recibidas ni stock.
        if not medido and dato['repuestos'] and not modelo.repuestos:
            valores['repuestos'] = [{'nombre': n, 'cantidad': '', 'uso': 'Referencia; validar variante antes de comprar.'}
                                   for n in dato['repuestos']]
        cambiados = [k for k, v in valores.items() if getattr(modelo, k) != v]
        if cambiados:
            for campo in cambiados:
                setattr(modelo, campo, valores[campo])
            modelo.save(update_fields=[*cambiados, 'fecha_actualizacion'])
            resumen['fichas técnicas actualizadas'] += 1

    @staticmethod
    def _elemento_confirmado(area, modelo, activos, dato, resumen):
        ficha, _ = FichaArea.objects.get_or_create(espacio=area, defaults={'fuente': FUENTE, 'publicada': False})
        _, creado = ElementoFichaArea.objects.get_or_create(ficha=ficha, tipo='equipo', nombre=dato['nombre'], defaults={
            'registrado': activos[0], 'nivel': 'basico', 'solo_referencia': False, 'ejemplo': f'{modelo.marca} {modelo.modelo}',
            'cantidad': str(dato['cantidad']), 'para_que': 'Capacidad declarada por el responsable; pendiente verificación patrimonial y habilitación.',
            'especificaciones': modelo.caracteristicas_publicas, 'cuidados': modelo.instrucciones_publicas,
            'url': dato['fuente'], 'orden': 20})
        resumen['elementos de ficha añadidos'] += creado

    @staticmethod
    def _compatibles(unidad, modelo, resumen):
        for consumible in Consumible.objects.filter(unidad=unidad):
            if any(normalizar(consumible.nombre).startswith(normalizar(p)) for p in MATERIALES_COMUNES):
                # Las fichas declaradas usan 1,75 mm: no enlazar filamentos de
                # otro diámetro ni materiales de nombre incompleto.
                if '175mm' not in normalizar(consumible.nombre + ' ' + consumible.variante):
                    continue
                _, nuevo = ConsumiblePorEquipo.objects.get_or_create(consumible=consumible, equipo=modelo)
                resumen['compatibilidades añadidas'] += nuevo

    @staticmethod
    def _software_propuesto(unidad, area, modelos, resumen):
        ficha = FichaArea.objects.get(espacio=area)
        for dato in SOFTWARE:
            existente = SoftwareDisponible.objects.filter(unidad=unidad, nombre__iexact=dato['nombre']).first()
            # El vínculo de una recomendación NO es una instalación acreditada.
            # Si el programa no existe se prepara inactivo y sin licencias.
            if existente is None:
                existente = SoftwareDisponible.objects.create(unidad=unidad, nombre=dato['nombre'], activo=False,
                    licencias_totales=0, licencias_disponibles=0, requiere_reserva=False,
                    sitio_web=dato['url'], descripcion=dato['uso'], instrucciones_acceso=dato['licencia'])
                resumen['software preparado sin habilitar'] += 1
            _, nuevo = ElementoFichaArea.objects.get_or_create(ficha=ficha, tipo='software', nombre=dato['nombre'], defaults={
                'solo_referencia': True, 'software_registrado': existente, 'url': dato['url'],
                'para_que': dato['uso'], 'licencia': 'Validar instalación y términos de licencia',
                'especificaciones': 'Compatible con: ' + ', '.join(modelos[k].modelo for k in dato['modelos'] if k in modelos),
                'orden': 30})
            resumen['referencias de software añadidas'] += nuevo

    @staticmethod
    def _materiales_propuestos(unidad, areas, modelos, resumen):
        for indice, (codigo_area, clase, familia, nombre, medida, condicion, compatibles) in enumerate(MATERIALES, start=1):
            espacio = areas.get(codigo_area)
            if espacio is None:
                continue
            coincidencias = [c for c in Consumible.objects.filter(unidad=unidad)
                             if normalizar(c.nombre) == normalizar(nombre)]
            if coincidencias:
                consumible = coincidencias[0]
            else:
                consumible = Consumible.objects.create(
                    unidad=unidad, codigo=f'FAB-REF-MAT-{indice:03d}', nombre=nombre,
                    clasificacion=clase, familia=familia, unidad_medida=medida,
                    especificacion_tecnica=condicion, descripcion='Referencia por evaluar; sin recepción acreditada.',
                    stock_total=0, minimo=0, stock_seguridad=0, stock_objetivo=0,
                    visible_en_reservas=False, activo=True)
                resumen['materiales preparados sin existencias'] += 1
            ficha, _ = FichaArea.objects.get_or_create(espacio=espacio, defaults={'fuente': FUENTE, 'publicada': False})
            _, nuevo = ElementoFichaArea.objects.get_or_create(ficha=ficha, tipo='insumo', nombre=nombre, defaults={
                'solo_referencia': True, 'insumo_registrado': consumible, 'para_que': condicion[:300],
                'cantidad': 'Según trabajo y consumo acreditado; sin cantidad comprada', 'orden': 500})
            resumen['referencias de materiales añadidas'] += nuevo
            for clave in compatibles:
                if clave in modelos:
                    _, nuevo = ConsumiblePorEquipo.objects.get_or_create(consumible=consumible, equipo=modelos[clave])
                    resumen['compatibilidades añadidas'] += nuevo

    @staticmethod
    def _catalogos_aportados(unidad, resumen):
        for codigo, modelo_documentado, documento, observacion, url in CATALOGOS_APORTADOS:
            modelo = EquiposServicios.objects.filter(
                Q(unidades__laboratorio=unidad) | Q(unidades__laboratorios=unidad), codigo=codigo,
            ).exclude(origen_datos_tecnicos='medido').distinct().first()
            if modelo is None:
                continue
            specs = dict(modelo.especificaciones or {})
            notas = {'Catálogo aportado': documento, 'Modelo descrito en catálogo': modelo_documentado,
                     'Contraste documental pendiente': observacion, 'Fecha del contraste': FECHA_REVISION}
            if url:
                notas['Consulta de fabricante'] = url
            for clave, valor in notas.items():
                if clave not in specs or specs[clave] in ('', None):
                    specs[clave] = valor
            if specs != (modelo.especificaciones or {}):
                modelo.especificaciones = specs
                modelo.save(update_fields=['especificaciones', 'fecha_actualizacion'])
                resumen['fichas contrastadas con catálogos'] += 1
