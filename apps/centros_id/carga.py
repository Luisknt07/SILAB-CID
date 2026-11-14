"""Carga el contenido documentado de cada Centro I+D: identidad, áreas con sus equipos y procesos, gobierno, ruta,
servicios, espacios ubicados en el plano, relaciones entre áreas, indicadores, riesgos, articulación, imágenes, planos,
documentos (los copiados y los que se generan desde los registros) y videos. Con `muestra`, suma el contenido
representativo del centro operando (personas por su cargo, proyectos, resultados, casos, aliados, convocatorias,
novedades y normas), que vive aparte para que el centro lo valide o lo reemplace.

Es idempotente: crea lo que falta y no pisa lo que el centro editó en el administrador, salvo con `reescribir`.
Los valores de los indicadores nunca se escriben: los que tienen cálculo se cuentan solos desde los registros.
"""
import importlib
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.files.base import ContentFile
from django.db import router, transaction
from django.utils import timezone

from .models import (
    Aliado, Articulacion, CasoExito, CentroID, Componente, Convocatoria, DocumentoCentro, EquipoCentro, EtapaOperativa,
    Fase, ImagenCentro, Indicador, Integrante, LineaInvestigacion, Modalidad, Novedad, OrganoGobierno,
    PartidaPresupuesto, PasoProceso, PlanoCentro, ProcesoArea, Proyecto, RelacionArea, Resultado, Riesgo, Servicio,
    Zona,
)

MEDIOS = Path(__file__).resolve().parent / 'contenido' / 'medios'


def _videos(filas):
    return '\n'.join(' | '.join(fila) for fila in filas)


class Cargador:
    def __init__(self, contenido, reescribir=False, medios=False, muestra=False, conservar_existentes=False):
        if reescribir and conservar_existentes:
            raise ValueError("Conservar existentes y reescribir son modos excluyentes.")
        self.conservar_existentes = conservar_existentes
        self._creados = set()
        self.c = contenido
        self.reescribir = reescribir
        self.medios = medios
        self.muestra = muestra
        self.cuenta = {}

    def _anotar(self, que, creado):
        clave = ('crearon' if creado else 'revisaron', que)
        self.cuenta[clave] = self.cuenta.get(clave, 0) + 1

    def resumen(self):
        partes = []
        for accion in ('crearon', 'revisaron'):
            lista = ', '.join(f'{valor} {que}' for (cual, que), valor in sorted(self.cuenta.items()) if cual == accion)
            if lista:
                partes.append(f'se {accion} {lista}')
        return '; '.join(partes).capitalize() if partes else 'Al día'

    def _preservar(self, objeto):
        """Preserva incluso vacíos intencionales de los registros anteriores a esta carga."""
        return (self.conservar_existentes and objeto is not None
                and (type(objeto), objeto.pk) not in self._creados)

    def _guardar(self, modelo, que, buscar, valores):
        """Crea faltantes; en modo normal completa vacíos y en modo conservador respeta existentes."""
        objeto = modelo.objects.filter(**buscar).first()
        creado = objeto is None
        if self._preservar(objeto):
            return objeto
        if creado:
            objeto = modelo(**buscar)
        cambio = creado
        for campo, valor in valores.items():
            actual = getattr(objeto, campo)
            if (creado or self.reescribir or actual in ('', None)) and actual != valor:
                setattr(objeto, campo, valor)
                cambio = True
        if cambio:
            objeto.full_clean()
            objeto.save()
            if creado:
                self._creados.add((type(objeto), objeto.pk))
            self._anotar(que, creado)
        return objeto

    def _guardar_muestra(self, modelo, que, buscar, valores):
        existente = modelo.objects.filter(**buscar).first()
        # Una coincidencia institucional nunca autoriza a reemplazar el registro con una muestra.
        if existente is not None and not existente.es_muestra:
            return existente
        return self._guardar(modelo, que, buscar, {**valores, 'es_muestra': True})

    def cargar(self):
        with transaction.atomic(using=router.db_for_write(CentroID)):
            return self._cargar()

    def _cargar(self):
        self._creados.clear()
        datos = dict(self.c.CENTRO)
        slug = datos.pop('slug')
        datos['videos'] = _videos(self.c.VIDEOS.get('centro', ()))
        centro = self._guardar(CentroID, 'centro', {'slug': slug}, datos)
        componentes = {}
        integraciones = {}
        for fila in self.c.COMPONENTES:
            fila = dict(fila)
            codigo = fila.pop('codigo')
            integraciones[codigo] = fila.pop('integrado_en_codigo', '')
            fila['videos'] = _videos(self.c.VIDEOS.get(codigo, ()))
            # Mientras el centro se implementa, sus áreas también.
            fila.setdefault('estado', 'operativa' if centro.en_operacion else 'implementacion')
            componentes[codigo] = self._guardar(Componente, 'componentes', {'centro': centro, 'codigo': codigo}, fila)
        for codigo, padre in integraciones.items():
            if padre:
                if padre not in componentes:
                    raise ValueError('El área principal del módulo no está en el catálogo del centro.')
                self._guardar(Componente, 'integraciones', {'centro': centro, 'codigo': codigo},
                              {'integrado_en': componentes[padre]})
        self._equipos(componentes)
        self._procesos(componentes)
        for orden, (origen, destino, que) in enumerate(getattr(self.c, 'RELACIONES', ()), start=1):
            if origen in componentes and destino in componentes:
                self._guardar(RelacionArea, 'relaciones', {'centro': centro, 'origen': componentes[origen],
                                                           'destino': componentes[destino]},
                              {'que_fluye': que, 'orden': orden})
        for orden, (nombre, rol, icono, responsabilidad, funciones) in enumerate(self.c.GOBIERNO, start=1):
            self._guardar(OrganoGobierno, 'instancias de gobierno', {'centro': centro, 'nombre': nombre},
                          {'rol': rol, 'icono': icono, 'responsabilidad': responsabilidad, 'funciones': funciones,
                           'orden': orden})
        for numero, nombre, proposito, responsable, resultado in self.c.RUTA:
            self._guardar(EtapaOperativa, 'etapas', {'centro': centro, 'numero': numero},
                          {'nombre': nombre, 'proposito': proposito, 'responsable': responsable, 'resultado': resultado})
        for orden, (nombre, proposito, usuarios, icono) in enumerate(self.c.MODALIDADES, start=1):
            self._guardar(Modalidad, 'modalidades', {'centro': centro, 'nombre': nombre},
                          {'proposito': proposito, 'usuarios': usuarios, 'icono': icono, 'orden': orden})
        for orden, (nombre, resultados, codigo) in enumerate(self.c.LINEAS, start=1):
            self._guardar(LineaInvestigacion, 'líneas', {'centro': centro, 'nombre': nombre},
                          {'resultados': resultados, 'componente': componentes.get(codigo), 'orden': orden})
        for orden, (linea, codigo, nombre, descripcion, entregable) in enumerate(self.c.SERVICIOS, start=1):
            self._guardar(Servicio, 'servicios', {'centro': centro, 'nombre': nombre},
                          {'linea': linea, 'componente': componentes.get(codigo), 'descripcion': descripcion,
                           'entregable': entregable, 'orden': orden})
        posiciones = getattr(self.c, 'POSICIONES', {})
        for orden, (codigo, nombre, nivel, dimensiones, area, componente, reservable) in enumerate(self.c.ZONAS, start=1):
            x, y = posiciones.get(codigo, (None, None))
            self._guardar(Zona, 'espacios', {'centro': centro, 'codigo': codigo},
                          {'nombre': nombre, 'nivel': nivel, 'dimensiones': dimensiones, 'area_m2': area,
                           'componente': componentes.get(componente), 'reservable': reservable, 'orden': orden,
                           'plano_x': None if x is None else Decimal(x), 'plano_y': None if y is None else Decimal(y)})
        # Un centro en implementación puede traer fases, presupuesto e indicadores por medir; uno que opera no los lleva.
        for numero, nombre, actividades, horizonte, estado in getattr(self.c, 'FASES', ()):
            self._guardar(Fase, 'fases', {'centro': centro, 'numero': numero},
                          {'nombre': nombre, 'actividades': actividades, 'horizonte': horizonte, 'estado': estado})
        for orden, (concepto, contenido, monto, nota) in enumerate(getattr(self.c, 'PRESUPUESTO', ()), start=1):
            self._guardar(PartidaPresupuesto, 'partidas', {'centro': centro, 'concepto': concepto},
                          {'contenido': contenido, 'monto': monto, 'nota': nota, 'orden': orden})
        for orden, (categoria, nombre, medicion, *calculo) in enumerate(getattr(self.c, 'INDICADORES', ()), start=1):
            self._guardar(Indicador, 'indicadores', {'centro': centro, 'nombre': nombre},
                          {'categoria': categoria, 'medicion': medicion, 'calculo': calculo[0] if calculo else '',
                           'orden': orden})
        for orden, (categoria, riesgo, efecto, mitigacion) in enumerate(getattr(self.c, 'RIESGOS', ()), start=1):
            self._guardar(Riesgo, 'riesgos', {'centro': centro, 'riesgo': riesgo},
                          {'categoria': categoria, 'efecto': efecto, 'mitigacion': mitigacion, 'orden': orden})
        for orden, (tipo, actor, forma, unidad) in enumerate(self.c.ARTICULACION, start=1):
            self._guardar(Articulacion, 'articulaciones', {'centro': centro, 'tipo': tipo, 'actor': actor},
                          {'forma': forma, 'unidad_slug': unidad, 'orden': orden})
        self._contenido_ampliado(centro)
        if self.muestra and getattr(self.c, 'MUESTRA', ''):
            self._muestra(centro, componentes, importlib.import_module(self.c.MUESTRA))
        if self.medios:
            self._imagenes(centro, componentes)
            self._planos(centro)
            self._documentos(centro)
            self._documentos_generados(centro)
        return centro

    def _contenido_ampliado(self, centro):
        """Completa métodos y condiciones de la oferta sin sustituir ediciones del gestor."""
        for nombre, valores in getattr(self.c, 'DETALLES_LINEAS', {}).items():
            self._guardar(LineaInvestigacion, 'líneas detalladas',
                          {'centro': centro, 'nombre': nombre}, valores)
        for nombre, valores in getattr(self.c, 'DETALLES_SERVICIOS', {}).items():
            self._guardar(Servicio, 'servicios detallados',
                          {'centro': centro, 'nombre': nombre}, valores)
        for orden, fila in enumerate(getattr(self.c, 'DOCUMENTOS_ENLACES', ()), 1):
            valores = dict(fila)
            titulo = valores.pop('titulo')
            self._guardar(DocumentoCentro, 'referencias académicas',
                          {'centro': centro, 'titulo': titulo},
                          {**valores, 'orden': orden})

    def _equipos(self, componentes):
        """Cada línea del equipamiento del área entra al catálogo como un equipo, con el tipo de área como categoría;
        el centro completa después código, especificaciones y foto en el administrador."""
        for componente in componentes.values():
            for orden, (nombre, detalle, funcion) in enumerate(componente.lista_equipamiento, start=1):
                self._guardar(EquipoCentro, 'equipos', {'componente': componente, 'nombre': nombre[:160]},
                              {'categoria': str(componente.get_tipo_display()), 'detalle': detalle[:255],
                               'funcion': funcion[:255],
                               'estado': 'operativo' if componente.estado == 'operativa' else 'planificado',
                               'orden': orden})

    def _procesos(self, componentes):
        """El flujo de trabajo de las plataformas, paso a paso, como proceso del área."""
        for codigo, (nombre, entrada, salida) in getattr(self.c, 'PROCESOS', {}).items():
            componente = componentes.get(codigo)
            if componente is None or not componente.pasos:
                continue
            proceso = self._guardar(ProcesoArea, 'procesos', {'componente': componente, 'nombre': nombre},
                                    {'entrada': entrada, 'salida': salida, 'orden': 1})
            for numero, (paso, detalle) in enumerate(componente.pasos, start=1):
                self._guardar(PasoProceso, 'pasos', {'proceso': proceso, 'numero': numero},
                              {'nombre': re.sub(r'^\d+\.\s*', '', paso)[:160], 'descripcion': detalle})

    def _imagenes(self, centro, componentes):
        """Las imágenes viajan con el código: el archivo se copia al almacenamiento una sola vez por título y sus datos
        (crédito, fuente, orden) se completan o, con `reescribir`, se reemplazan."""
        for archivo, codigo, titulo, credito, fuente, es_plano, orden in self.c.IMAGENES:
            componente = componentes.get(codigo)
            existente = ImagenCentro.objects.filter(centro=centro, componente=componente, titulo=titulo).first()
            if existente:
                self._guardar(ImagenCentro, 'imágenes', {'pk': existente.pk},
                              {'credito': credito, 'fuente': fuente, 'es_plano': es_plano, 'orden': orden})
                continue
            with (MEDIOS / archivo).open('rb') as origen:
                imagen = ImagenCentro(centro=centro, componente=componente, titulo=titulo, credito=credito,
                                      fuente=fuente, es_plano=es_plano, orden=orden)
                imagen.imagen.save(archivo, File(origen), save=False)
                imagen.save()
            self._anotar('imágenes', True)
        portada = next((fila for fila in self.c.IMAGENES if not fila[1] and not fila[5]), None)
        if not portada:
            return
        if self._preservar(centro):
            return
        if not centro.imagen:
            with (MEDIOS / portada[0]).open('rb') as origen:
                centro.imagen.save(portada[0], File(origen), save=False)
            centro.credito_imagen = portada[3]
            centro.save(update_fields=['imagen', 'credito_imagen'])
        elif (self.reescribir or not centro.credito_imagen) and centro.credito_imagen != portada[3]:
            centro.credito_imagen = portada[3]
            centro.save(update_fields=['credito_imagen'])
            self._anotar('centro', False)

    def _planos(self, centro):
        for nivel, titulo, archivo, credito, orden in getattr(self.c, 'PLANOS', ()):
            existente = PlanoCentro.objects.filter(centro=centro, nivel=nivel)
            if existente.exists():
                # La imagen no se vuelve a subir; su texto vuelve al del documento si se reescribe.
                if self.reescribir:
                    existente.update(titulo=titulo, credito=credito, orden=orden)
                continue
            with (MEDIOS / archivo).open('rb') as origen:
                plano = PlanoCentro(centro=centro, nivel=nivel, titulo=titulo, credito=credito, orden=orden)
                plano.imagen.save(archivo, File(origen), save=False)
                plano.save()
            self._anotar('planos', True)

    def _documentos(self, centro):
        for tipo, titulo, periodo, resumen, archivo in getattr(self.c, 'DOCUMENTOS', ()):
            if DocumentoCentro.objects.filter(centro=centro, titulo=titulo).exists():
                continue
            with (MEDIOS / archivo).open('rb') as origen:
                documento = DocumentoCentro(centro=centro, tipo=tipo, titulo=titulo, periodo=periodo, resumen=resumen)
                documento.archivo.save(archivo, File(origen), save=False)
                documento.save()
            self._anotar('documentos', True)

    def _documentos_generados(self, centro):
        """Los documentos que salen de lo registrado: se generan una vez y se rehacen con `reescribir`."""
        from .documentos import GENERADORES, pdf

        for orden, (tipo, titulo, generador, resumen) in enumerate(getattr(self.c, 'DOCUMENTOS_GENERADOS', ()), start=1):
            documento = DocumentoCentro.objects.filter(centro=centro, titulo=titulo).first()
            if self._preservar(documento):
                continue
            if documento and (documento.estado_documental != 'borrador' or documento.validado_en
                              or (documento.archivo and not self.reescribir)):
                continue
            creado = documento is None
            documento = documento or DocumentoCentro(centro=centro, titulo=titulo,
                                                     estado_documental='borrador', publico=False)
            documento.tipo, documento.resumen, documento.orden = tipo, resumen, orden
            documento.periodo = documento.periodo or str(timezone.localdate().year)
            contenido = pdf(centro, titulo, resumen, GENERADORES[generador](centro))
            documento.archivo.save(f'{centro.slug}-{generador}.pdf', ContentFile(contenido), save=False)
            documento.save()
            self._anotar('documentos generados', creado)

    # ------------------------------------------------------------------ contenido representativo (--muestra)
    def _muestra(self, centro, componentes, m):
        """Personas por su cargo, aliados, proyectos, resultados, casos, convocatorias, novedades y normas que muestran el
        centro operando; las fechas de novedades y convocatorias se cuentan desde hoy."""
        hoy = timezone.localdate()
        lineas = {linea.nombre: linea for linea in centro.lineas.all()}
        for nombre, retos in getattr(m, 'RETOS', {}).items():
            if nombre in lineas:
                self._guardar(LineaInvestigacion, 'retos de líneas', {'pk': lineas[nombre].pk}, {'retos_muestra': '\n'.join(retos)})
        aliados = {}
        for orden, (nombre, tipo, aporte) in enumerate(getattr(m, 'ALIADOS', ()), start=1):
            aliados[nombre] = self._guardar_muestra(Aliado, 'aliados', {'centro': centro, 'nombre': nombre},
                                            {'tipo': tipo, 'pais': 'Ecuador', 'aporte': aporte, 'orden': orden})
        personas = {}
        for orden, (nombre, rol, cargo, area, facultad, perfil, de_lineas) in enumerate(getattr(m, 'INTEGRANTES', ()), start=1):
            persona = self._guardar_muestra(Integrante, 'integrantes', {'centro': centro, 'nombre': nombre},
                                    {'rol': rol, 'cargo': cargo, 'componente': componentes.get(area), 'facultad': facultad,
                                     'perfil': perfil, 'orden': orden})
            self._enlazar(persona.lineas, [lineas[n] for n in de_lineas if n in lineas])
            personas[nombre] = persona
        proyectos = {}
        for (codigo, titulo, resumen, linea, areas, estado, etapa, avance, inicio, fin, responsable, equipo, de_aliados,
             hitos, destacado) in getattr(m, 'PROYECTOS', ()):
            proyecto = self._guardar_muestra(Proyecto, 'proyectos', {'centro': centro, 'codigo': codigo}, {
                'titulo': titulo, 'resumen': resumen, 'linea': lineas.get(linea), 'estado': estado, 'etapa': etapa,
                'avance': avance, 'inicio': inicio, 'fin': fin, 'responsable': personas.get(responsable),
                'hitos': '\n'.join(hitos), 'destacado': destacado, 'investigadores': len(equipo) + 1})
            self._enlazar(proyecto.componentes, [componentes[a] for a in areas if a in componentes])
            self._enlazar(proyecto.equipo, [personas[n] for n in equipo if n in personas])
            self._enlazar(proyecto.aliados, [aliados[n] for n in de_aliados if n in aliados])
            proyectos[codigo] = proyecto
        for tipo, titulo, descripcion, revista, anio, proyecto, area, autores, trl, estado_pi, licencia in getattr(m, 'RESULTADOS', ()):
            resultado = self._guardar_muestra(Resultado, 'resultados', {'centro': centro, 'titulo': titulo}, {
                'tipo': tipo, 'descripcion': descripcion, 'revista': revista, 'anio': anio, 'proyecto': proyectos.get(proyecto),
                'componente': componentes.get(area), 'trl': trl, 'estado_pi': estado_pi, 'licencia': licencia})
            self._enlazar(resultado.autores, [personas[n] for n in autores if n in personas])
        for orden, (titulo, beneficiario, sector, reto, solucion, resultado, area, proyecto, aliado, anio) in enumerate(
                getattr(m, 'CASOS', ()), start=1):
            self._guardar_muestra(CasoExito, 'casos', {'centro': centro, 'titulo': titulo}, {
                'beneficiario': beneficiario, 'sector': sector, 'reto': reto, 'solucion': solucion, 'resultado': resultado,
                'componente': componentes.get(area), 'proyecto': proyectos.get(proyecto), 'aliado': aliados.get(aliado),
                'anio': anio, 'orden': orden})
        for orden, (tipo, titulo, descripcion, area, dias) in enumerate(getattr(m, 'CONVOCATORIAS', ()), start=1):
            self._guardar_muestra(Convocatoria, 'convocatorias', {'centro': centro, 'titulo': titulo}, {
                'tipo': tipo, 'descripcion': descripcion, 'componente': componentes.get(area),
                'cierre': hoy + timedelta(days=dias), 'orden': orden})
        for tipo, titulo, resumen, dias, hasta, lugar in getattr(m, 'NOVEDADES', ()):
            self._guardar_muestra(Novedad, 'novedades', {'centro': centro, 'titulo': titulo}, {
                'tipo': tipo, 'resumen': resumen, 'fecha': hoy + timedelta(days=dias),
                'fecha_fin': hoy + timedelta(days=hasta) if hasta is not None else None, 'lugar': lugar})
        if self.medios:
            self._documentos_escritos(centro, getattr(m, 'DOCUMENTOS', ()))

    def _enlazar(self, relacion, objetos):
        """Una relación de muchos a muchos se llena si está vacía; con `reescribir`, se reemplaza."""
        if self._preservar(relacion.instance):
            return
        if getattr(relacion.instance, 'es_muestra', False) and objetos and (self.reescribir or not relacion.exists()):
            relacion.set(objetos)

    def _documentos_escritos(self, centro, documentos):
        from .documentos import pdf

        for orden, (tipo, titulo, periodo, resumen, bloques) in enumerate(documentos, start=1):
            documento = DocumentoCentro.objects.filter(centro=centro, titulo=titulo).first()
            if self._preservar(documento):
                continue
            if documento and (not documento.es_muestra or (documento.archivo and not self.reescribir)):
                continue
            creado = documento is None
            documento = documento or DocumentoCentro(centro=centro, titulo=titulo, es_muestra=True,
                                                     estado_documental='borrador', publico=False)
            documento.tipo, documento.periodo, documento.resumen, documento.orden = tipo, periodo, resumen, 10 + orden
            documento.archivo.save(f'{centro.slug}-{tipo}.pdf', ContentFile(pdf(centro, titulo, resumen, bloques)), save=False)
            documento.save()
            self._anotar('documentos', creado)
