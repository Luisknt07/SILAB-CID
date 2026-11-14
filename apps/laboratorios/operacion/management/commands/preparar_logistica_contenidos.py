"""Publicación versionada de manuales, prácticas, programas y datos de Logística."""
import hashlib
import json
from pathlib import Path

from django.core.management.base import CommandError

from apps.laboratorios.operacion.management.commands.preparar_logistica_paso1 import Command as CommandPaso1, contenido_recurso, nombre_archivo_recurso, recursos_del_paquete
from apps.laboratorios.operacion.management.laboratorios.logistica_catalogo import recursos_complementarios, validar_catalogo


class Command(CommandPaso1):
    help = 'Completa contenidos de las seis pestañas de Logística, preservando las ediciones de la unidad.'
    descripcion_auditoria = 'LOG-CONT: procedimientos, doce prácticas, formación y datos sintéticos; sin alterar inventario, reservas ni oferta'
    prefijo_respaldo = 'logistica-contenidos-'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--exportar-directorio', type=Path, help='Exporta los bytes exactos para revisión; no escribe en la base ni aprueba seguridad.')

    def _recursos(self, asignaturas):
        recursos = recursos_del_paquete(asignaturas) + recursos_complementarios()
        validar_catalogo(recursos)
        return recursos

    def handle(self, *args, **opciones):
        destino = opciones.get('exportar_directorio')
        if destino is None:
            return super().handle(*args, **opciones)
        if opciones['aplicar'] or opciones['simular']:
            raise CommandError('La exportación no se combina con --aplicar ni --simular.')
        unidad = self._unidad()
        recursos = self._recursos(list(unidad.asignaturas.all()))
        # Un directorio nuevo evita mezclar revisiones o sobrescribir archivos.
        if destino.exists():
            raise CommandError('El directorio de revisión ya existe; use otro directorio vacío nuevo.')
        destino.mkdir(parents=True)
        adjuntos, enlaces = [], []
        for datos in recursos:
            contenido = contenido_recurso(datos)
            if contenido:
                nombre = nombre_archivo_recurso(datos)
                (destino / nombre).write_bytes(contenido)
                adjuntos.append({'clave': datos['clave'], 'archivo': nombre,
                                 'sha256': hashlib.sha256(contenido).hexdigest(),
                                 'bytes': len(contenido), 'seccion': datos['seccion']})
            elif datos['url']:
                enlaces.append({'clave': datos['clave'], 'url': datos['url']})
        inventario = {'estado': 'pendiente_de_revision', 'adjuntos': adjuntos, 'enlaces': enlaces}
        (destino / 'inventario-revision.json').write_text(
            json.dumps(inventario, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(
            f'Exportados {len(adjuntos)} adjuntos y {len(enlaces)} referencias para revisión. La base no cambió.'))
