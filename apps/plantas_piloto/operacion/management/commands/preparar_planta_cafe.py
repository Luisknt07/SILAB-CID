"""Completa exclusivamente el catálogo de café; no carga stock ni operaciones.

Por defecto sólo calcula altas pendientes mediante SELECT. --aplicar publica
contenido original revisado; conserva registros existentes y decisiones de la
unidad. Los archivos generados se retiran si falla la transacción.
"""
from collections import Counter
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.presentacion import PresentacionUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.plantas_piloto.operacion.management.plantas.cafe import ALCANCE, FAMILIAS, INSUMOS, PRODUCTOS, PROCESOS, SLUG, VERSION
from apps.plantas_piloto.operacion.management.plantas.cafe_documentos import documento_html
from apps.plantas_piloto.operacion.management.plantas.cafe_guias import GUIAS
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, InsumoReceta, Producto, Receta
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_PLANTA
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso


EQUIPOS_REFERENCIA = {
    'PPCA-BENEFICIO': (
        ('Báscula de recepción y balanza de muestra', 'Pesaje con tara y control de fracciones.', 'Rango y resolución según cargas reales; verificación con patrones, plataforma lavable.'),
        ('Mesa y recipientes de selección de cereza', 'Clasificar por microlote y retirar material extraño.', 'Superficies aptas, limpiables y drenables; identificación y ergonomía.'),
        ('Separación de flotantes y conducción de agua', 'Clasificación complementaria del fruto.', 'Agua apta, recuperación de sólidos y medición del consumo; no sustituye selección.'),
        ('Despulpadora regulable', 'Separar pulpa sin dañar semillas.', 'Ajuste a tamaño de fruto, resguardos, limpieza, repuestos y prueba con lote real.'),
        ('Desmucilaginador mecánico (alternativa)', 'Remover mucílago en la ruta que lo requiera.', 'Evaluar caudal, agua, daño y limpieza; no implica instalación ni uso obligatorio.'),
        ('Recipientes de fermentación y muestreo', 'Mantener tratamientos segregados y monitorizados.', 'Material apto, drenaje/limpieza, termometría y ventilación; sin presión improvisada.'),
        ('Termómetros y registro ambiental', 'Seguir masa, aire y ambiente.', 'Sondas identificadas, rango adecuado y calibración; registrar ubicación y hora.'),
        ('pH-metro y refractómetro de investigación', 'Mediciones complementarias del tratamiento.', 'Calibración, temperatura de medida, limpieza y método; no liberan inocuidad por sí solos.'),
        ('Camas elevadas y marquesina', 'Secado solar segregado por lote.', 'Malla apta, ventilación, protección de lluvia y carga por área verificada.'),
        ('Secador mecánico o mixto', 'Complementar secado según clima y demanda.', 'Control de aire/grano, uniformidad, fuente térmica y extracción; ensayo de capacidad útil.'),
        ('Medidor de humedad por matriz', 'Comprobar evolución y homogeneidad.', 'Calibración apropiada para pergamino/verde; método de contraste y muestreo multipunto.'),
        ('Medidor de actividad de agua (ampliación)', 'Caracterización de estabilidad.', 'Instrumento y calibración propios; no inferir aw directamente de la humedad.'),
        ('Trilladora y aspiración de polvo', 'Obtener almendra de pergamino o natural.', 'Ajuste por matriz, extracción, resguardos y medición de quebrados/pérdidas.'),
        ('Tamices y mesa de clasificación', 'Evaluación física y selección.', 'Método, masa de muestra, tamices identificados; separador densimétrico/óptico si se justifica.'),
        ('Estibas, envases y monitoreo de bodega', 'Conservar café seco sin olores ni rehumectación.', 'Aptitud alimentaria, barrera, integridad, ubicación y control de plagas/ambiente.'),
    ),
    'PPCA-TORREFACCION': (
        ('Tostador de muestras', 'Comparar lotes y preparar evaluación.', 'Carga de muestras, sondas, curva, enfriamiento y protocolo de preparación declarado.'),
        ('Tostador de producción', 'Reproducir perfiles por lote y equipo.', 'Capacidad útil por prueba, suministro seguro, registro, extracción y manual de operación.'),
        ('Extracción, ciclón y colector de cascarilla', 'Controlar humo, polvo y fracción combustible.', 'Diseño y mantenimiento técnico, acceso a limpieza y evaluación de incendio.'),
        ('Enfriador y separación de cuerpos extraños', 'Estabilizar y revisar el café tostado.', 'Enfriamiento homogéneo; sistema de separación según riesgo y recursos verificados.'),
        ('Balanza y medición de color', 'Controlar carga, pérdida y perfil.', 'Tara, condición de pesaje, método de color y referencia; calibración y registro.'),
        ('Molino de muestras y molino de producción', 'Preparación sensorial y comercial diferenciada.', 'Granulometría verificable, purga, calentamiento, resguardos y limpieza sin olores.'),
        ('Mesa y utensilios de evaluación sensorial', 'Preparar y comparar muestras ciegas.', 'Recipientes homogéneos, agua, balanza, temporización y ambiente sin interferencias.'),
        ('Agua y equipos de preparación de bebidas', 'Evaluar uso previsto: filtro o espresso.', 'Calidad de agua, receta y método documentados; no implica certificación SCA del equipo.'),
        ('Dosificación y control de peso neto', 'Llenar presentaciones sin confundir kg y bolsas.', 'Rango/resolución, tara por envase y plan de comprobación aprobado.'),
        ('Selladora compatible con bolsa de barrera', 'Cerrar envases con integridad verificable.', 'Parámetros del envase, ensayo de sello/fugas, protección térmica y mantenimiento.'),
        ('Codificador e impresión de etiqueta', 'Relacionar presentación y lote.', 'Arte aprobado, legibilidad, fecha/lote y control de cambios; QR complementario.'),
        ('Sistema de atmósfera protectora (opcional)', 'Estudiar conservación en envase.', 'Suministro apropiado, medición cuando proceda y seguridad; incorporar sólo tras evaluación.'),
        ('Estantería y control de producto terminado', 'Segregar retenidos, liberados y muestras.', 'Envase íntegro, lote, condición ambiental, rotación y custodia.'),
        ('Estación de datos y registro de curvas', 'Analizar mediciones y conservar evidencia.', 'Exportación CSV, respaldo institucional al desplegar, permisos y trazabilidad de versiones.'),
    ),
}


class Command(BaseCommand):
    help = 'Publica procesos, procedimientos, prácticas y calculadora de café sin crear existencias ni ventas.'

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument('--aplicar', action='store_true')
        modo.add_argument('--simular', action='store_true')

    def handle(self, *args, **opciones):
        self.aplicar = opciones['aplicar']
        self.resumen, self.archivos = Counter(), []
        if self.aplicar:
            try:
                with transaction.atomic():
                    unidad = Unidad.objects.select_for_update().get(slug=SLUG, dependencia='plantas_piloto')
                    self.cargar(unidad)
                    if sum(self.resumen.values()):
                        registrar_auditoria(None, unidad=unidad, accion='actualizar', objeto=unidad,
                                            descripcion='CAF-CONT v1: catálogo técnico, prácticas y cálculo; sin stock, corridas o ventas',
                                            nuevos=dict(self.resumen))
            except Exception:
                for storage, nombre in self.archivos:
                    storage.delete(nombre)
                raise
        else:
            unidad = Unidad.objects.filter(slug=SLUG, dependencia='plantas_piloto').first()
            if unidad is None:
                raise CommandError('Primero registre la planta de café; este cargador no crea unidades institucionales.')
            self.cargar(unidad)
        self.stdout.write(('Aplicado: ' if self.aplicar else 'Simulación de altas (SELECT): ') +
                          (', '.join(f'{k}: {v}' for k, v in self.resumen.items()) or 'sin cambios') + '.')

    def obtener(self, modelo, filtro, valores):
        """Sólo altas; cualquier edición, desactivación o código existente se conserva."""
        nuevo_padre = any(isinstance(v, models.Model) and v.pk is None for v in filtro.values())
        objeto = None if nuevo_padre else modelo.objects.filter(**filtro).first()
        if objeto:
            esperado = valores.get('unidad')
            if esperado is not None and getattr(objeto, 'unidad_id', esperado.pk) != esperado.pk:
                raise CommandError(f'El código de {modelo.__name__} pertenece a otra unidad; no se modifica.')
            return objeto, False
        objeto = modelo(**filtro, **valores)
        self.resumen[modelo.__name__] += 1
        if self.aplicar:
            objeto.full_clean()
            objeto.save()
        return objeto, True

    def editorial(self, objeto, tipo):
        if not self.aplicar:
            return
        ficha = FichaContenido.objects.filter(content_type=ContentType.objects.get_for_model(objeto), object_id=objeto.pk).first()
        if ficha is None:
            ficha = FichaContenido(unidad=objeto.unidad, codigo='CAF-F-' + objeto.codigo, tipo=tipo,
                                  titulo=objeto.nombre, content_type=ContentType.objects.get_for_model(objeto), object_id=objeto.pk)
        # Sólo se llama para objetos nuevos, antes de cualquier edición de la unidad.
        ficha.estado = 'publicada'
        ficha.visibilidad = 'publica'
        ficha.descripcion = ALCANCE
        ficha.estado_validacion = 'pendiente'
        ficha.observacion_validacion = 'Contenido de referencia publicado; no equivale a protocolo operativo validado ni certificación.'
        ficha.full_clean()
        ficha.save()

    def cargar(self, unidad):
        catalogo_existia = Receta.objects.filter(unidad=unidad, codigo__startswith='CAF-R-').exists()
        familias = {}
        for orden, (clave, nombre, descripcion) in enumerate(FAMILIAS, 1):
            familias[clave], _ = self.obtener(FamiliaProducto, {'codigo': 'CAF-F-' + clave},
                dict(unidad=unidad, orden=orden, nombre=nombre, descripcion=descripcion))
        productos = {}
        for clave, familia, nombre, tipo, presentacion, descripcion in PRODUCTOS:
            producto, creado = self.obtener(Producto, {'codigo': 'CAF-P-' + clave},
                dict(unidad=unidad, familia=familias[familia], nombre=nombre, tipo=tipo, unidad_medida='kg',
                     presentacion=presentacion, descripcion=descripcion + '\n\n' + ALCANCE,
                     precio_venta=0, vida_util_dias=0, publico=tipo != 'residuo'))
            productos[clave] = producto
            if creado:
                self.editorial(producto, 'producto')
        insumos = {}
        for clave, nombre, medida, clasificacion, especificacion in INSUMOS:
            insumos[clave], _ = self.obtener(Consumible, {'codigo': 'CAF-I-' + clave},
                dict(unidad=unidad, nombre=nombre, unidad_medida=medida, clasificacion=clasificacion,
                     especificacion_tecnica=especificacion, descripcion='Catálogo técnico sin existencias precargadas. ' + especificacion,
                     stock_total=0, minimo=0))
        areas = {a.codigo: a for a in EspacioReservable.objects.filter(unidad=unidad)}
        for datos in PROCESOS:
            producto = productos[datos['producto']]
            receta, creada = self.obtener(Receta, {'codigo': 'CAF-R-' + datos['clave']},
                dict(unidad=unidad, familia=producto.familia, producto=producto, nombre=producto.nombre,
                     cantidad_base=Decimal(datos['base']), unidad_base='kg', rendimiento_esperado=Decimal(datos['salida']),
                     instrucciones=datos['instrucciones'], origen='referencia'))
            # Un proceso existente se administra completo en su editor, sin recomponer sus hijos al recargar.
            if not creada:
                continue
            etapas = []
            for orden, paso in enumerate(datos['etapas'], 1):
                valores = {k: v for k, v in paso.items() if k != 'area'}
                valores['rendimiento_pct'] = Decimal(valores['rendimiento_pct']).quantize(Decimal('.01'))
                etapa, _ = self.obtener(EtapaReceta, {'receta': receta, 'orden': orden},
                    dict(familia=receta.familia, espacio=areas.get(paso['area']), **valores))
                etapas.append(etapa)
            self.obtener(InsumoReceta, {'receta': receta, 'consumible': insumos[datos['insumo']]},
                dict(cantidad=Decimal(datos['base']), forma_parte='base', etapa=etapas[0]))
            for clave, cantidad in datos['empaques']:
                self.obtener(InsumoReceta, {'receta': receta, 'consumible': insumos[clave]},
                    dict(cantidad=Decimal(cantidad), forma_parte='no', etapa=etapas[-2]))
            self.editorial(receta, 'proceso')
        self.areas(areas)
        self.documentos(unidad)
        self.presentacion(unidad)
        config = ConfiguracionOperativaUnidad.objects.filter(unidad=unidad).first()
        if config and not config.registra_produccion and not catalogo_existia:
            # Habilita el módulo y sesiones; no altera estados de planta, inventario ni permisos.
            self.resumen['ERP habilitado'] += 1
            if self.aplicar:
                config.registra_produccion = True
                config.save(update_fields=['registra_produccion'])

    def areas(self, areas):
        for codigo, equipos in EQUIPOS_REFERENCIA.items():
            area = areas.get(codigo)
            if area is None:
                continue
            beneficio = codigo == 'PPCA-BENEFICIO'
            pasos = ('Recibir e identificar', 'Seleccionar y beneficiar', 'Secar y comprobar', 'Preparar verde y conservar') if beneficio else (
                'Preparar muestra y perfil', 'Tostar y enfriar', 'Evaluar y liberar', 'Moler, empacar y despachar')
            ficha, creada = self.obtener(FichaArea, {'espacio': area}, dict(
                que_es='Área de ' + area.nombre + ' dentro de la cadena de café de origen. ' + ALCANCE,
                como_funciona='Cada lote conserva finca, cosecha, ruta, masas, mediciones y decisión. Las zonas siguientes son una distribución funcional de referencia para verificar en el levantamiento de planta.',
                principio='\n'.join(p + ' | Registrar entrada, recursos, control, responsable y salida; ver procedimientos del café.' for p in pasos),
                distribucion='\n'.join(p + ' | Flujo segregado; confirmar ubicación y recursos reales | ' + '; '.join(e[0] for e in equipos[i*3:(i+1)*3]) for i, p in enumerate(pasos)),
                aplicaciones='\n'.join(('Prácticas de transformación y control', 'Comparación de microlotes de finca', 'Ensayos de mejora con repetición y evidencia', 'Preparación de servicios sujetos a habilitación')),
                conexiones='Agua apta según uso y drenajes con tratamiento\nEnergía y extracción según equipo real\nSeparación de café, químicos, residuos y visitantes\nDatos y trazabilidad con acceso restringido a información personal',
                seguridad='Resguardos y bloqueo antes de mantenimiento\nPrevención de calor, incendio, polvo y atrapamiento\nLimpieza/metrología y retención de no conformes\nInducción y supervisión antes de operar',
                fuente='CAF-CONT v1 · Referencia técnica original; equipos por verificar, no inventario instalado', publicada=True))
            if not creada:
                continue
            for orden, (nombre, uso, especificacion) in enumerate(equipos, 1):
                self.obtener(ElementoFichaArea, {'ficha': ficha, 'nombre': nombre, 'tipo': 'equipo'}, dict(
                    nivel='basico', para_que=uso, especificaciones=especificacion, cantidad='Dimensionar mediante levantamiento y pruebas',
                    ejemplo='Referencia funcional; no acredita equipo instalado', cuidados='Consultar fabricante y procedimiento validado; verificar antes de operar.', orden=orden))

    def documentos(self, unidad):
        modulos = {m.clave: m for m in ModuloUnidad.objects.filter(unidad=unidad)}
        carpetas = {}
        lista = [(clave, d['titulo'], d['seccion'], d['objetivo'], documento_html(clave, d).encode('utf-8'), '') for clave, d in GUIAS.items()]
        lista.extend((
            ('registro-microlote', 'Plantilla CSV · pasaporte y transformaciones del microlote', '1.5',
             'Formato vacío para registrar origen, lotes padre/hijo, matriz, masas y decisiones; acceso privado para datos reales.',
             b'microlote,finca_codigo,parcela_codigo,variedad_declarada,cosecha_fecha,ruta,lote_padre,lote_hijo,matriz,masa_entrada_kg,masa_salida_kg,metodo_medicion,estado_calidad,ubicacion,responsable_codigo\r\n', ''),
            ('serie-tueste', 'CSV docente · curvas de tueste para comparar', '2.4',
             'Serie sintética de dos perfiles; no es un perfil para operar un tostador ni resultados de planta.',
             b'clase,perfil,minuto,temperatura_sonda_c,eventos\r\nsintetico,A,0,190,carga\r\nsintetico,A,2,105,retorno\r\nsintetico,A,4,135,\r\nsintetico,A,6,160,\r\nsintetico,A,8,181,\r\nsintetico,A,10,196,primer_crack_ilustrativo\r\nsintetico,A,12,207,descarga\r\nsintetico,B,0,185,carga\r\nsintetico,B,2,102,retorno\r\nsintetico,B,4,130,\r\nsintetico,B,6,155,\r\nsintetico,B,8,178,\r\nsintetico,B,10,193,primer_crack_ilustrativo\r\nsintetico,B,13,209,descarga\r\n', ''),
        ))
        for clave, nombre, seccion, descripcion, contenido, url in lista:
            marca = 'caf-cont:' + clave
            if Recurso.objects.filter(unidad=unidad, palabras_clave=marca).exists():
                continue
            modulo = modulos.get(MAPA_PLANTA.modulo_de(seccion))
            if modulo is None:
                raise CommandError('Falta el módulo estándar de la sección ' + seccion)
            if seccion not in carpetas:
                carpetas[seccion], _ = self.obtener(CarpetaRecurso, {'unidad': unidad, 'nombre': 'Café de origen · ' + MAPA_PLANTA.secciones[seccion]['titulo']},
                    dict(modulo='recursos', modulo_config=modulo, seccion_planta=seccion, orden=20, activa=True))
                if carpetas[seccion].seccion_planta != seccion:
                    raise CommandError('Una carpeta existente tiene otro uso; se conserva sin mezclar contenidos.')
            self.resumen['Recursos'] += 1
            if not self.aplicar:
                continue
            recurso = Recurso(unidad=unidad, nombre=nombre, descripcion=descripcion, carpeta=carpetas[seccion],
                              palabras_clave=marca, tipo_adjunto='manual', autor='Contenido técnico original · Plataforma UPEC',
                              fuente='interna', licencia_uso='interna', version=VERSION, activo=True,
                              visibilidad='publica', seguridad_verificada=True, descargar=bool(contenido), url=url)
            try:
                if contenido:
                    extension = 'csv' if clave in ('registro-microlote', 'serie-tueste') else 'html'
                    recurso.archivo.save(f'caf-cont-{clave}.{extension}', ContentFile(contenido), save=False)
                    self.archivos.append((recurso.archivo.storage, recurso.archivo.name))
                recurso.full_clean()
                recurso.save()
            finally:
                recurso.archivo.close()

    def presentacion(self, unidad):
        self.obtener(PresentacionUnidad, {'unidad': unidad}, dict(
            lema='Café de finca: del fruto al cliente, con identidad y decisiones trazables.',
            que_es='Planta piloto para desarrollar la transformación del café de origen vinculado al Centro Experimental Alonso Tadeo. Su ruta técnica conecta beneficio, secado, preparación de verde, torrefacción, empaque y gestión de producto. La constitución y el alcance presencial se consultan en los registros institucionales.',
            que_hace='Organiza microlotes por finca y cosecha; compara lavado, honey y natural; prepara café verde; desarrolla perfiles de tueste; documenta calidad, masa, materiales, inventario, costo y entrega. Los procedimientos y prácticas publicados permiten preparar actividades con evidencia.',
            capacidades='Referencias técnicas para beneficio y preparación de microlotes, evaluación física/sensorial, tostado por perfil, molienda/empaque, formación, investigación aplicada y servicios a productores. Cada servicio requiere recursos verificados, responsable y habilitación antes de ofertarse.',
            areas_trabajo='Beneficio y secado: origen, selección, rutas, humedad y preparación de verde.\nTorrefacción y molienda: muestras, perfiles, calidad, empaque y producto terminado.',
            mision='Aportar formación y desarrollo de café de origen con procesos medibles, trazables y útiles para productores, estudiantes e iniciativas de innovación.',
            vision='Desarrollar una planta piloto referente por la calidad de su evidencia, articulación con fincas y mejora continua, conforme a sus capacidades verificadas.',
            objetivos='Conservar identidad del microlote\nMedir rendimientos y pérdidas\nComparar tratamientos con evidencia\nDesarrollar perfiles y presentaciones\nArticular formación, investigación y servicios\nEvitar duplicación de inventario y proteger registros',
            beneficiarios='Estudiantes y docentes\nProductores y asociaciones\nInvestigadores\nEmprendimientos y empresas\nComunidad vinculada al territorio', publicada=True))
