"""Deja listo para atender el Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales.

Completa lo que la unidad necesita para operar y que ningún cargador cubría: servicios, ejemplos de solicitud,
requisitos de acceso, guías de práctica de referencia, documentos de la sala, recorrido de visitas, plano funcional,
ilustraciones de las áreas y de los servicios y el curso del laboratorio; y publica las fichas de área en borrador.

Por defecto simula: hace todo dentro de una transacción y la deshace. `--aplicar` guarda solo esta unidad. Se puede
repetir: crea lo que falta y no cambia lo que la unidad ya editó; lo que es una decisión de la unidad (el recorrido de
visitas, publicar la inducción) se propone solo la primera vez. No inventa marcas, series, existencias ni precios.
Los archivos generados se retiran si la transacción falla.
"""
from collections import Counter
from decimal import Decimal
from io import BytesIO, StringIO

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.cursos import Curso, LeccionCurso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.management.fichas_area import FUENTE as FUENTE_DE_CARGADOR
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.interior import MedioInterior
from apps.gestion_unidades.models.presentacion import HitoUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.laboratorios.operacion.management.laboratorios import esquemas
from apps.laboratorios.operacion.management.laboratorios import realidad_extendida as datos
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva
from apps.reservas.models.seguridad import RequisitoAcceso

CURSO_PRECARGADO = 'realidad-extendida'
CARPETAS = {'1.4': 'Seguridad y protocolos de la sala', '4.4': 'Formatos y guías del laboratorio'}


class Command(BaseCommand):
    help = 'Completa la operación del Laboratorio de Realidad Extendida. Simula por defecto; --aplicar guarda.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Guarda los cambios. Sin esto solo se simula.')

    def handle(self, *args, **opciones):
        self.aplicar = opciones['aplicar']
        self.resumen, self.avisos, self.archivos = Counter(), [], []
        try:
            with transaction.atomic():
                unidad = Unidad.objects.select_for_update().filter(slug=datos.SLUG, dependencia='laboratorios').first()
                if unidad is None:
                    raise CommandError('Primero registre el laboratorio; este cargador no crea unidades.')
                self.cargar(unidad)
                if self.aplicar and sum(self.resumen.values()):
                    registrar_auditoria(
                        None, unidad=unidad, accion='actualizar', objeto=unidad,
                        descripcion=f'{datos.VERSION}: operación, guías, documentos e imágenes; sin existencias ni precios',
                        nuevos=dict(self.resumen))
                if not self.aplicar:
                    transaction.set_rollback(True)
        except Exception:
            for almacenamiento, nombre in self.archivos:
                almacenamiento.delete(nombre)
            raise
        prefijo = 'Aplicado: ' if self.aplicar else 'Simulación (nada se guardó): '
        self.stdout.write(prefijo + (', '.join(f'{clave}: {valor}' for clave, valor in self.resumen.items() if valor)
                                     or 'nada nuevo') + '.')
        for aviso in self.avisos:
            self.stdout.write('Revisar: ' + aviso)

    def cargar(self, unidad):
        self.areas = {espacio.codigo: espacio for espacio in
                      EspacioReservable.objects.filter(unidad=unidad, codigo__in=datos.AREAS, activo=True)}
        faltan = sorted(set(datos.AREAS) - set(self.areas))
        if faltan:
            raise CommandError('Faltan áreas activas del laboratorio: ' + ', '.join(faltan))
        # La primera aplicación deja su registro de auditoría; con él se reconoce una repetición.
        self.primera_vez = not RegistroAuditoriaUnidad.objects.filter(
            unidad=unidad, descripcion__startswith=datos.VERSION).exists()
        self.correcciones(unidad)
        self.recorrido(unidad)
        self.servicios(unidad)
        self.ejemplos(unidad)
        self.requisitos(unidad)
        self.actividades(unidad)
        self.guias(unidad)
        self.fichas(unidad)
        self.imagenes(unidad)
        self.documentos(unidad)
        self.curso(unidad)

    # ------------------------------------------------------------ saneamiento
    def correcciones(self, unidad):
        retirados = UnidadEquipo.objects.filter(laboratorio=unidad, codigo_unidad=datos.EQUIPO_DE_PRUEBA, activa=True)
        self.resumen['registros de prueba retirados'] += retirados.update(activa=False, estado_unidad='no_disponible')
        for hito in HitoUnidad.objects.filter(unidad=unidad, descripcion__contains=datos.HITO_ANTERIOR):
            hito.descripcion = hito.descripcion.replace(datos.HITO_ANTERIOR, datos.HITO_VIGENTE)
            hito.save(update_fields=['descripcion'])
            self.resumen['hitos corregidos'] += 1
        # Al integrar dos áreas quedaron repetidas las imágenes de referencia que ambas compartían.
        vistos = set()
        for medio in MedioInterior.objects.filter(unidad=unidad, tipo='foto').order_by('espacio_id', 'orden', 'pk'):
            clave = (medio.espacio_id, medio.imagen.name)
            if medio.es_referencial and clave in vistos:
                medio.delete()
                self.resumen['imágenes de referencia repetidas retiradas'] += 1
            vistos.add(clave)
        # Dos zonas de la misma área quedaron con el mismo nombre al integrarla.
        for codigo, (nombre, pista, distinto) in datos.ZONAS_A_DISTINGUIR.items():
            ficha = FichaArea.objects.filter(espacio=self.areas[codigo]).first()
            lineas = ficha.distribucion.splitlines() if ficha else []
            for posicion, linea in enumerate(lineas):
                if linea.split('|')[0].strip(' -•\t') == nombre and pista in linea:
                    lineas[posicion] = linea.replace(nombre, distinto, 1)
                    ficha.distribucion = '\n'.join(lineas)
                    ficha.save(update_fields=['distribucion'])
                    self.resumen['zonas con nombre repetido distinguidas'] += 1
                    break

    def recorrido(self, unidad):
        # Solo la primera vez y si la unidad no ha decidido su recorrido.
        if not self.primera_vez or EspacioReservable.objects.filter(unidad=unidad, visitable=True).exists():
            return
        self.resumen['áreas en el recorrido de visitas'] += EspacioReservable.objects.filter(
            unidad=unidad, codigo__in=datos.AREAS_DEL_RECORRIDO, activo=True).update(visitable=True)

    # -------------------------------------------------------------- operación
    def servicios(self, unidad):
        for servicio in datos.SERVICIOS:
            if FablabService.objects.filter(code=servicio['code']).exists():
                continue
            # Sin tarifas: quedan en cero hasta que la unidad las apruebe.
            nuevo = FablabService(**servicio, unidad=unidad, activo=True, publico=True, requiere_reserva=True,
                                  requiere_revision_tecnica=True, requiere_cotizacion=False)
            if self.aplicar:
                self._guardar(nuevo.imagen_referencial, f"{servicio['code'].lower()}.png",
                              esquemas.ilustracion(datos.MOTIVOS_DE_SERVICIO[servicio['code']]))
            nuevo.full_clean()
            nuevo.save()
            self.resumen['servicios'] += 1

    def ejemplos(self, unidad):
        for ejemplo in datos.EJEMPLOS:
            if EjemploSolicitudUnidad.objects.filter(unidad=unidad, proposito_codigo=ejemplo['proposito']).exists():
                continue
            nuevo = EjemploSolicitudUnidad(unidad=unidad, proposito_codigo=ejemplo['proposito'],
                                           ejemplo=ejemplo['ejemplo'], checklist=ejemplo['checklist'], activo=True)
            nuevo.full_clean()
            nuevo.save()
            self.resumen['ejemplos de solicitud'] += 1

    def requisitos(self, unidad):
        for orden, requisito in enumerate(datos.REQUISITOS, start=1):
            if RequisitoAcceso.objects.filter(unidad=unidad, codigo=requisito['codigo']).exists():
                continue
            consumible = None
            if requisito.get('consumible'):
                consumible = Consumible.objects.filter(unidad=unidad, nombre=requisito['consumible']).first()
                if consumible is None:
                    self.avisos.append(f"el insumo «{requisito['consumible']}» no está en el inventario; "
                                       f"el requisito {requisito['codigo']} queda sin insumo asociado.")
            nuevo = RequisitoAcceso(
                unidad=unidad, codigo=requisito['codigo'], nombre=requisito['nombre'], tipo=requisito['tipo'],
                aplica_a=requisito['aplica_a'], obligatorio=requisito['obligatorio'], momento=requisito['momento'],
                vigencia_dias=requisito.get('vigencia_dias'), consumible=consumible,
                cantidad_por_persona=Decimal(requisito.get('cantidad_por_persona', '1')),
                descripcion=requisito['descripcion'], orden=orden, activo=True)
            nuevo.full_clean()
            nuevo.save()
            self.resumen['requisitos de acceso'] += 1

    def actividades(self, unidad):
        if not self.primera_vez:
            return
        publicadas = CatalogoActividadReserva.objects.filter(
            unidad=unidad, nombre__in=datos.ACTIVIDADES_A_PUBLICAR, estado_publicacion='borrador')
        self.resumen['actividades de inducción publicadas'] += publicadas.update(estado_publicacion='publicado')

    def guias(self, unidad):
        for orden, guia in enumerate(datos.GUIAS, start=1):
            actividad, creada = CatalogoActividadReserva.objects.get_or_create(unidad=unidad, codigo=guia['codigo'], defaults={
                'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'practica_curricular',
                'nombre': 'Práctica: ' + guia['nombre'], 'responsable': 'Equipo del laboratorio',
                'descripcion': guia['descripcion'], 'estado_publicacion': 'publicado', 'visibilidad': 'unidad',
                'activo': True, 'orden': orden,
            })
            self.resumen['prácticas en el catálogo'] += int(creada)
            codigo = guia['codigo'].replace('-PRA-', '-GUI-', 1)
            if GuiaActividadReserva.objects.filter(actividad=actividad, codigo_guia=codigo).exists():
                continue
            contenido = {
                'docente_responsable': 'Docente de la asignatura',
                'laboratorio': f"{unidad.nombre} · {self.areas[guia['area']].nombre}",
                'reactivos': [], 'formato_procedimiento': 'numerado',
                'medidas_seguridad': list(datos.SEGURIDAD_COMUN),
                'manejo_residuos': ['Máscaras faciales y toallitas usadas van al recipiente de residuos comunes.',
                                    'Pilas y baterías agotadas se entregan al personal para su disposición.'],
                **guia['contenido'],
            }
            nueva = GuiaActividadReserva(
                actividad=actividad, titulo='Guía de práctica: ' + guia['nombre'],
                descripcion=('Guía de referencia del laboratorio: el docente la adapta a su asignatura y la unidad '
                             'la valida.'),
                codigo_guia=codigo, numero_version=1, es_estructurada=True, es_vigente=True, contenido=contenido,
                visibilidad='publica', estado_publicacion='publicada', permite_descarga=True, activo=True, orden=orden)
            faltantes = nueva.secciones_faltantes()
            if faltantes:
                raise CommandError(f"La guía {codigo} no está completa: {', '.join(faltantes)}")
            nueva.save()
            self.resumen['guías de práctica'] += 1

    def fichas(self, unidad):
        # Solo las que siguen como las dejó el cargador: su fuente decía que la unidad aún no las validaba. Una ficha
        # que la unidad retire después conserva la fuente nueva y no se vuelve a publicar.
        for ficha in FichaArea.objects.filter(espacio__in=self.areas.values(), publicada=False, fuente=FUENTE_DE_CARGADOR):
            ficha.publicada, ficha.fuente = True, datos.FUENTE_FICHAS
            ficha.save(update_fields=['publicada', 'fuente'])
            self.resumen['fichas de área publicadas'] += 1
        sin_ficha = [codigo for codigo, espacio in self.areas.items() if not FichaArea.objects.filter(espacio=espacio).exists()]
        if sin_ficha:
            self.avisos.append('áreas sin ficha explicativa: ' + ', '.join(sorted(sin_ficha)))

    # --------------------------------------------------------------- imágenes
    def _guardar(self, campo, nombre, contenido):
        """Escribe un archivo generado y lo anota para retirarlo si la transacción falla."""
        campo.save(nombre, ContentFile(contenido), save=False)
        self.archivos.append((campo.storage, campo.name))

    def imagenes(self, unidad):
        equipos = dict(EspacioReservable.objects.filter(pk__in=[espacio.pk for espacio in self.areas.values()])
                       .annotate(total=Count('equipos_asociados', filter=Q(equipos_asociados__activa=True)))
                       .values_list('pk', 'total'))
        fichas = {ficha.espacio_id: ficha for ficha in FichaArea.objects.filter(espacio__in=self.areas.values())}
        ordenadas = sorted(self.areas.values(), key=lambda espacio: (espacio.orden, espacio.nombre))
        if not unidad.plano_espacios:
            self.resumen['plano funcional'] += 1
            if self.aplicar:
                self._guardar(unidad.plano_espacios, 'xr-plano-funcional.png', esquemas.plano_funcional(unidad.nombre, [
                    {'nombre': espacio.nombre, 'capacidad': espacio.capacidad, 'equipos': equipos.get(espacio.pk, 0),
                     'zonas': [zona['nombre'] for zona in fichas[espacio.pk].zonas] if espacio.pk in fichas else []}
                    for espacio in ordenadas]))
                unidad.save(update_fields=['plano_espacios'])
        # La imagen del área es la foto de su tarjeta: mientras la unidad no suba la suya, una ilustración.
        for espacio in ordenadas:
            if espacio.imagen:
                continue
            self.resumen['ilustraciones de área'] += 1
            if self.aplicar:
                self._guardar(espacio.imagen, f'{espacio.codigo.lower()}.png',
                              esquemas.ilustracion(datos.MOTIVOS_DE_AREA[espacio.codigo]))
                espacio.save(update_fields=['imagen'])

    # ------------------------------------------------------------- documentos
    def documentos(self, unidad):
        modulos = {modulo.clave: modulo for modulo in ModuloUnidad.objects.filter(unidad=unidad)}
        carpetas = {}
        for clave, seccion, nombre, descripcion, bloques in datos.DOCUMENTOS:
            marca = datos.MARCA + clave
            if Recurso.objects.filter(unidad=unidad, palabras_clave=marca).exists():
                continue
            modulo = modulos.get(MAPA_LABORATORIO.modulo_de(seccion))
            if modulo is None:
                raise CommandError('Falta el módulo estándar de la sección ' + seccion)
            if seccion not in carpetas:
                carpetas[seccion], _ = CarpetaRecurso.objects.get_or_create(
                    unidad=unidad, nombre=CARPETAS[seccion], seccion_planta=seccion,
                    defaults={'modulo': 'recursos', 'modulo_config': modulo, 'orden': 30, 'activa': True,
                              'visibilidad': 'publica'})
            self.resumen['documentos de la sala'] += 1
            if not self.aplicar:
                continue
            recurso = Recurso(
                unidad=unidad, nombre=nombre, descripcion=descripcion, carpeta=carpetas[seccion], palabras_clave=marca,
                tipo_adjunto='manual', autor='Laboratorio de Realidad Extendida · Plataforma', fuente='interna',
                licencia_uso='interna', activo=True, visibilidad='publica', seguridad_verificada=True, descargar=True)
            try:
                self._guardar(recurso.archivo, f'xr-{clave}.pdf', documento_pdf(unidad, nombre, bloques, self.areas))
                recurso.full_clean()
                recurso.save()
            finally:
                recurso.archivo.close()

    # ------------------------------------------------------------------ curso
    def curso(self, unidad):
        from apps.formacion.management.cursos_precargados import realidad_extendida as curso_xr

        cursos = Curso.objects.filter(unidad=unidad, nombre=curso_xr.CURSO['nombre'])
        existia = cursos.exists()
        salida = StringIO()
        call_command('cargar_curso_precargado', CURSO_PRECARGADO, '--unidad', unidad.slug,
                     *([] if self.aplicar else ['--simular']), stdout=salida)
        if 'nada nuevo' not in salida.getvalue():
            self.resumen['curso del laboratorio'] += 1
        curso = cursos.first()
        if curso is None:
            # En una simulación el curso no llega a existir, pero su portada se generaría.
            self.resumen['portada del curso'] += int(not existia)
            return
        if not existia:
            # Las guías en PDF que el curso acaba de generar se retiran si esta transacción falla.
            self.archivos.extend((leccion.archivo.storage, leccion.archivo.name) for leccion in
                                 LeccionCurso.objects.filter(modulo__curso=curso).exclude(archivo=''))
        if curso.imagen:
            return
        self.resumen['portada del curso'] += 1
        if self.aplicar:
            self._guardar(curso.imagen, 'xr-curso-portada.png',
                          esquemas.portada(curso.nombre, curso.lema, f'{unidad.nombre} · Curso'))
            curso.save(update_fields=['imagen'])


def documento_pdf(unidad, titulo, bloques, areas):
    """Un documento de la sala con el marco institucional, a partir de bloques simples."""
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.pdf_institucional import marco_institucional

    dibujar, lienzo, medidas = marco_institucional(formato=titulo.upper(), metadatos=[datos.VERSION, 'Documento de la sala'],
                                                   pie=unidad.nombre)
    tinta = medidas['colores']
    ancho = medidas['pagesize'][0] - 2 * medidas['margen']
    estilo_titulo = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=tinta['primario'],
                                   spaceBefore=9, spaceAfter=5, keepWithNext=True)
    cuerpo = ParagraphStyle('cuerpo', fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=tinta['oscuro'], spaceAfter=4)
    punto = ParagraphStyle('punto', parent=cuerpo, leftIndent=11, bulletIndent=1, spaceAfter=2.5)
    celda = ParagraphStyle('celda', parent=cuerpo, fontSize=8.8, leading=11.5, spaceAfter=0)
    cabecera = ParagraphStyle('cabecera', parent=celda, fontName='Helvetica-Bold', textColor=colors.white)

    def tabla(encabezados, filas, anchos=None):
        if anchos is None:
            # La columna de texto más largo recibe el espacio que sobra.
            largos = [max([len(encabezados[i])] + [len(fila[i]) for fila in filas]) for i in range(len(encabezados))]
            anchos = [max(9 * mm, min(ancho * 0.6, ancho * largo / max(sum(largos), 1))) for largo in largos]
            sobra = ancho - sum(anchos)
            anchos[largos.index(max(largos))] += sobra
        contenido = [[Paragraph(escape(texto), cabecera) for texto in encabezados]]
        contenido += [[Paragraph(escape(texto), celda) for texto in fila] for fila in filas]
        hoja = Table(contenido, colWidths=anchos, repeatRows=1)
        hoja.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), tinta['primario']),
            ('GRID', (0, 0), (-1, -1), 0.5, tinta['linea']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return hoja

    flujo = [Paragraph(escape(titulo), ParagraphStyle('portada', parent=estilo_titulo, fontSize=15, leading=19)),
             Spacer(1, 2 * mm)]
    for tipo, *resto in bloques:
        contenido = resto[0] if len(resto) == 1 else resto
        if tipo == 'titulo':
            flujo.append(Paragraph(escape(contenido), estilo_titulo))
        elif tipo == 'parrafo':
            flujo.append(Paragraph(escape(contenido), cuerpo))
        elif tipo == 'lista':
            flujo.extend(Paragraph(escape(linea), punto, bulletText='•') for linea in contenido)
        elif tipo == 'pasos':
            flujo.extend(Paragraph(escape(linea), punto, bulletText=f'{numero}.')
                         for numero, linea in enumerate(contenido, start=1))
        elif tipo == 'casillas':
            hoja = Table([['', Paragraph(escape(linea), celda)] for linea in contenido], colWidths=[5 * mm, ancho - 5 * mm])
            hoja.setStyle(TableStyle([
                ('BOX', (0, 0), (0, -1), 0.8, tinta['oscuro']), ('INNERGRID', (0, 0), (0, -1), 0.8, tinta['oscuro']),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (1, 0), (1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 4.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
            ]))
            flujo.extend([hoja, Spacer(1, 2 * mm)])
        elif tipo == 'campos':
            hoja = Table([[Paragraph(escape(etiqueta), celda), ''] for etiqueta in contenido],
                         colWidths=[ancho * 0.32, ancho * 0.68], rowHeights=[9 * mm] * len(contenido))
            hoja.setStyle(TableStyle([('LINEBELOW', (1, 0), (1, -1), 0.6, tinta['oscuro']),
                                      ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
            flujo.extend([hoja, Spacer(1, 2 * mm)])
        elif tipo == 'tabla':
            flujo.extend([tabla(*contenido), Spacer(1, 2 * mm)])
        elif tipo == 'areas':
            filas = [[espacio.nombre, espacio.descripcion_publica or '', str(espacio.capacidad)]
                     for espacio in sorted(areas.values(), key=lambda espacio: (espacio.orden, espacio.nombre))]
            flujo.extend([tabla(['Área', 'Para qué', 'Personas'], filas, [ancho * 0.36, ancho * 0.5, ancho * 0.14]),
                          Spacer(1, 2 * mm)])
        else:
            raise CommandError('Bloque de documento desconocido: ' + tipo)
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=medidas['pagesize'], leftMargin=medidas['margen'],
                                  rightMargin=medidas['margen'], topMargin=medidas['margen_superior'],
                                  bottomMargin=medidas['margen_inferior'], title=f'{titulo} · {unidad.nombre}')
    documento.build(flujo, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=lienzo)
    return salida.getvalue()
