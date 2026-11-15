"""Carga en su unidad un curso precargado con todo su contenido, siguiendo la estructura estándar.

Los cursos están en cursos_precargados/ (uno por archivo): presentación, primera edición y módulos con lecturas,
videos, guías en PDF que se generan aquí, evaluaciones con sus preguntas, deberes y prácticas. Se puede repetir:
crea lo que falta, no toca lo que la unidad ya escribió y retira los módulos y lecciones que el contenido ya no trae,
salvo que alguien los haya usado. --reescribir reemplaza los textos; las preguntas de una evaluación que alguien ya
rindió no se tocan. El curso queda sin publicar hasta que la unidad lo revise. --simular muestra lo que haría.
"""
from collections import Counter
from datetime import date
from importlib import import_module
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.formacion.presentation.cursos import codigo_de_curso_nuevo
from apps.formacion.models.cursos import Curso, EdicionCurso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.directorio_unidades.models.core import Unidad

# Nombre en la orden → (módulo con el contenido, unidad donde se carga).
CURSOS = {
    'bambu-lab': ('bambu_lab', 'laboratorio-fabricacion-digital-prototipado'),
    'fusion': ('fusion', 'laboratorio-fabricacion-digital-prototipado'),
    'odoo': ('odoo', 'laboratorio-logistica-comercio-internacional'),
    'aplicaciones-logisticas-ia': ('aplicaciones_logisticas_ia', 'laboratorio-logistica-comercio-internacional'),
    'ordeno-calidad-leche': ('ordeno_calidad_leche', 'centro-experimental-san-francisco'),
    'cafe-cereza-taza': ('cafe_cereza_taza', 'centro-experimental-alonso-tadeo'),
    'realidad-extendida': ('realidad_extendida', 'laboratorio-realidad-extendida'),
}


class Simulacion(Exception):
    """Deshace todo al final de una simulación."""


def en_uso(leccion):
    """Una lección que alguien ya recorrió, rindió, entregó o comentó no se retira."""
    return (leccion.progresos.exists() or leccion.intentos_rendidos.exists() or leccion.entregas.exists()
            or leccion.comentarios.exists())


class Command(BaseCommand):
    help = 'Carga un curso precargado con todo su contenido.'

    def add_arguments(self, parser):
        parser.add_argument('curso', choices=sorted(CURSOS), help='El curso que se carga.')
        parser.add_argument('--unidad', help='Slug de la unidad, si no es la del curso.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')
        parser.add_argument('--reescribir', action='store_true', help='Reemplaza los textos aunque ya existan.')

    def handle(self, *args, **opciones):
        modulo_datos, slug = CURSOS[opciones['curso']]
        datos = import_module(f'apps.formacion.management.cursos_precargados.{modulo_datos}')
        unidad = Unidad.objects.filter(slug=opciones['unidad'] or slug).first()
        if unidad is None:
            raise CommandError(f'No existe la unidad «{opciones["unidad"] or slug}».')
        self.reescribir = opciones['reescribir']
        self.resumen = Counter()
        try:
            with transaction.atomic():
                curso = self._curso(unidad, datos.CURSO)
                self._edicion(curso, datos.EDICION)
                textos, guias, archivos, vigentes = {}, [], [], {}
                self.modulos_vistos = []
                for orden, (titulo, descripcion, lecciones) in enumerate(datos.MODULOS, start=1):
                    modulo = self._modulo(curso, orden, titulo, descripcion)
                    self.modulos_vistos.append(titulo)
                    vigentes[modulo.pk] = set()
                    for posicion, (tipo, titulo_leccion, campos) in enumerate(lecciones, start=1):
                        leccion = self._leccion(modulo, posicion, tipo, titulo_leccion, campos)
                        vigentes[modulo.pk].add(leccion.pk)
                        textos[titulo_leccion] = campos.get('contenido', '')
                        if campos.get('guia_pdf'):
                            guias.append((leccion, campos['guia_pdf']))
                        if campos.get('archivo_generado'):
                            archivos.append((leccion, campos['archivo_generado']))
                        if tipo == 'evaluacion':
                            self._preguntas(leccion, campos['preguntas'])
                self._retirar_sobrantes(curso, vigentes)
                # Una simulación no escribe archivos: el PDF quedaría en disco aunque se deshaga lo demás.
                for leccion, secciones in guias if not opciones['simular'] else ():
                    self._guia_pdf(leccion, curso, secciones, textos)
                for leccion, especificacion in archivos if not opciones['simular'] else ():
                    self._archivo_generado(leccion, especificacion)
                if opciones['simular']:
                    raise Simulacion()
        except Simulacion:
            self.stdout.write(self.style.WARNING('Simulación: no se guardó nada.'))
        resumen = ', '.join(f'{cantidad} {que}' for que, cantidad in sorted(self.resumen.items())) or 'nada nuevo'
        self.stdout.write(self.style.SUCCESS(f'{curso.codigo} · {curso.nombre}: {resumen}.'))

    def _asignar(self, objeto, datos, nuevo):
        """Llena los campos vacíos; con --reescribir, también los que ya tienen texto."""
        cambio = False
        for campo, valor in datos.items():
            if (nuevo or self.reescribir or getattr(objeto, campo) in ('', None)) and getattr(objeto, campo) != valor:
                setattr(objeto, campo, valor)
                cambio = True
        return cambio

    def _guardar(self, objeto, nuevo, cambio, que, validar=True):
        if nuevo or cambio:
            if validar:
                objeto.full_clean()
            objeto.save()
            self.resumen[f'{que}: {"nuevos" if nuevo else "actualizados"}'] += 1

    def _curso(self, unidad, datos):
        curso = Curso.objects.filter(unidad=unidad, nombre=datos['nombre']).first()
        nuevo = curso is None
        if nuevo:
            orden = (Curso.objects.filter(unidad=unidad).order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
            curso = Curso(unidad=unidad, codigo=codigo_de_curso_nuevo(unidad), orden=orden, publicado=False)
        self._guardar(curso, nuevo, self._asignar(curso, datos, nuevo), 'cursos')
        return curso

    def _edicion(self, curso, datos):
        datos = {**datos, **{campo: date.fromisoformat(datos[campo]) for campo in
                             ('inicio', 'fin', 'inscripciones_desde', 'inscripciones_hasta') if datos.get(campo)}}
        edicion = EdicionCurso.objects.filter(curso=curso, nombre=datos['nombre']).first()
        nuevo = edicion is None
        edicion = edicion or EdicionCurso(curso=curso)
        self._guardar(edicion, nuevo, self._asignar(edicion, datos, nuevo), 'ediciones')

    def _modulo(self, curso, orden, titulo, descripcion):
        modulo = ModuloCurso.objects.filter(curso=curso, titulo=titulo).first()
        nuevo = modulo is None
        modulo = modulo or ModuloCurso(curso=curso)
        # El orden sigue siempre al contenido; el texto, solo si está vacío o se pide reescribir.
        cambio = self._asignar(modulo, {'titulo': titulo, 'descripcion': descripcion}, nuevo) or modulo.orden != orden
        modulo.orden = orden
        self._guardar(modulo, nuevo, cambio, 'módulos')
        return modulo

    def _leccion(self, modulo, orden, tipo, titulo, campos):
        valores = {clave: valor for clave, valor in campos.items() if clave not in ('preguntas', 'guia_pdf', 'archivo_generado')}
        # Primero en su módulo; si no está, en otro módulo del curso (la lección se movió de lugar).
        leccion = (LeccionCurso.objects.filter(modulo=modulo, titulo=titulo).first()
                   or LeccionCurso.objects.filter(modulo__curso=modulo.curso, titulo=titulo).exclude(
                       modulo__titulo__in=self.modulos_vistos).first())
        nuevo = leccion is None
        leccion = leccion or LeccionCurso(modulo=modulo)
        cambio = self._asignar(leccion, {'tipo': tipo, 'titulo': titulo, **valores}, nuevo)
        cambio = cambio or leccion.orden != orden or leccion.modulo_id != modulo.pk
        leccion.orden, leccion.modulo = orden, modulo
        # La guía en PDF todavía no tiene su archivo: se valida al generarlo.
        self._guardar(leccion, nuevo, cambio, 'lecciones', validar=not (campos.get('guia_pdf') or campos.get('archivo_generado')))
        return leccion

    def _preguntas(self, leccion, preguntas):
        if leccion.intentos_rendidos.exists() or (leccion.preguntas.exists() and not self.reescribir):
            return
        leccion.preguntas.all().delete()
        for orden, (tipo, enunciado, opciones, explicacion) in enumerate(preguntas, start=1):
            pregunta = PreguntaEvaluacion(leccion=leccion, orden=orden, tipo=tipo, enunciado=enunciado, explicacion=explicacion)
            if tipo == 'corta':
                pregunta.respuestas_aceptadas = opciones
            else:
                pregunta.opciones = opciones
            pregunta.full_clean()
            pregunta.save()
            self.resumen['preguntas'] += 1

    def _retirar_sobrantes(self, curso, vigentes):
        for leccion in LeccionCurso.objects.filter(modulo__curso=curso).exclude(
                pk__in=[pk for lecciones in vigentes.values() for pk in lecciones]):
            if en_uso(leccion):
                self.stdout.write(self.style.WARNING(f'Se conserva «{leccion.titulo}»: ya tiene actividad de inscritos.'))
                continue
            leccion.delete()
            self.resumen['lecciones retiradas'] += 1
        for modulo in ModuloCurso.objects.filter(curso=curso).exclude(pk__in=vigentes):
            if not modulo.lecciones.exists():
                modulo.delete()
                self.resumen['módulos retirados'] += 1

    def _archivo_generado(self, leccion, especificacion):
        """Adjunta un material del contenido confiable; nunca se genera durante --simular."""
        if leccion.archivo and not self.reescribir:
            return
        nombre, generar = especificacion
        leccion.archivo.save(nombre, ContentFile(generar()), save=False)
        leccion.full_clean()
        leccion.save()
        self.resumen['materiales generados'] += 1

    def _guia_pdf(self, leccion, curso, secciones, textos):
        if leccion.archivo and not self.reescribir:
            return
        nombre = f'guia-{curso.codigo.lower()}.pdf'
        leccion.archivo.save(nombre, ContentFile(guia_pdf(curso, leccion.titulo, secciones, textos)), save=False)
        leccion.full_clean()
        leccion.save()
        self.resumen['guías en PDF'] += 1


def guia_pdf(curso, titulo, secciones, textos):
    """Una guía con el marco institucional que reúne las lecturas indicadas del curso."""
    from xml.sax.saxutils import escape

    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from apps.core.presentation.pdf_institucional import marco_institucional
    from apps.formacion.presentation.curso_wiki_pdf import bloques_pdf

    dibujar, lienzo, medidas = marco_institucional(formato=titulo.upper().replace(' (PDF)', ''),
                                                   metadatos=[f'Curso: {curso.codigo}', curso.get_clasificacion_display()],
                                                   pie=curso.unidad.nombre)
    tinta = medidas['colores']
    estilo_titulo = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=tinta['primario'],
                                   spaceBefore=8, spaceAfter=6, keepWithNext=True)
    cuerpo = ParagraphStyle('cuerpo', fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=tinta['oscuro'], spaceAfter=4)
    flujo = [Paragraph(escape(curso.nombre), ParagraphStyle('curso', parent=estilo_titulo, fontSize=15, leading=19)),
             Spacer(1, 2 * mm)]
    imagenes_vistas = set()
    for seccion in secciones:
        flujo.append(Paragraph(escape(seccion), estilo_titulo))
        ancho = medidas['pagesize'][0] - 2 * medidas['margen']
        flujo.extend(bloques_pdf(textos.get(seccion, ''), ancho, cuerpo, estilo_titulo, imagenes_vistas=imagenes_vistas))
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=medidas['pagesize'], leftMargin=medidas['margen'],
                                  rightMargin=medidas['margen'], topMargin=medidas['margen_superior'],
                                  bottomMargin=medidas['margen_inferior'], title=f'{titulo} · {curso.nombre}')
    documento.build(flujo, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=lienzo)
    return salida.getvalue()
