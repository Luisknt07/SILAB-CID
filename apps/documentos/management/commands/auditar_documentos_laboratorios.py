"""Auditoría repetible y de solo lectura del expediente de laboratorios."""
import hashlib
import json
from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.expediente import (
    cortes_del_anio, del_periodo, leer_expedientes, periodo_vigente, tramo_del_documento,
)
from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
from apps.documentos.presentation.perfil_laboratorios import es_laboratorio


def comprobar_archivo(documento):
    if not documento.recurso_id or not documento.recurso.archivo:
        return False, 'Falta el archivo.'
    try:
        archivo = documento.recurso.archivo
        with archivo.open('rb') as stream:
            contenido = stream.read(25 * 1024 * 1024 + 1)
        if not contenido or len(contenido) > 25 * 1024 * 1024:
            return False, 'Archivo vacío o fuera del límite de 25 MB.'
        if hashlib.sha256(contenido).hexdigest() != documento.recurso.hash_sha256:
            return False, 'La huella del archivo no coincide con la registrada.'
        if Path(archivo.name).suffix.lower() == '.pdf':
            from pypdf import PdfReader
            pdf = PdfReader(BytesIO(contenido))
            if pdf.is_encrypted or not pdf.pages:
                return False, 'PDF ilegible o cifrado.'
    except Exception:
        return False, 'El archivo no está disponible o no se puede leer.'
    return True, ''


class Command(BaseCommand):
    help = 'Revisa nombres, periodicidad, archivos y correspondencia sin cambiar documentos, notas ni estados.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', help='Slug del laboratorio; omitido revisa todos los laboratorios.')
        parser.add_argument('--anio', type=int, default=timezone.localdate().year)
        parser.add_argument('--corte', choices=('A', 'B', 'todos'), default='todos')
        parser.add_argument('--salida', help='Archivo JSON de resultados; omitido escribe a la salida estándar.')

    def handle(self, *args, **options):
        anio = options['anio']
        if not 2000 <= anio <= 2200:
            raise CommandError('Indica un año entre 2000 y 2200.')
        queryset = Unidad.objects.all().select_related('administrador')
        if options.get('unidad'):
            queryset = queryset.filter(slug=options['unidad'])
        unidades = [u for u in queryset if es_laboratorio(u)]
        if not unidades:
            raise CommandError('No se encontraron laboratorios dentro del alcance solicitado.')
        hoy = timezone.localdate()
        cortes = cortes_del_anio(anio)
        expedientes = leer_expedientes(unidades, anio, hoy, cortes=cortes)
        resultado = dict(fecha=hoy.isoformat(), anio=anio, corte=options['corte'],
                         solo_lectura=True, unidades=[])
        for unidad in unidades:
            documentos = expedientes[unidad.pk]
            if options['corte'] != 'todos':
                documentos = del_periodo(documentos, options['corte'], cortes)
            filas = []
            for d in sorted(documentos, key=lambda d: (d.exigido.orden, d.exigido.codigo, d.corte)):
                integro, error_archivo = comprobar_archivo(d)
                correspondencia = estado_integridad_documental(d, inspeccionar=True)
                pendientes = []
                if error_archivo:
                    pendientes.append(error_archivo)
                if d.firma_pendiente:
                    pendientes.append('Falta firma electrónica verificada.')
                if d.recurso_id and correspondencia.get('aviso'):
                    pendientes.append(correspondencia['aviso'])
                if not d.exigido.es_anexo and d.estado != 'validado':
                    pendientes.append('Sin envío vigente a Dirección.')
                inicio, fin = tramo_del_documento(d, cortes)
                filas.append(dict(codigo=d.exigido.codigo, nombre=d.nombre_documental,
                    documento_id=d.pk, periodo=d.etiqueta_corte, tramo=[inicio.isoformat(), fin.isoformat()],
                    periodicidad=d.periodicidad_documental, anexo=d.exigido.es_anexo,
                    estado=d.estado, recurso_id=d.recurso_id, version=d.version,
                    archivo_integro=integro, firma_verificada=d.firma_verificada,
                    correspondencia_verificada=correspondencia.get('correspondencia_verificada', False),
                    enviado=d.estado == 'validado', recibido=bool(d.recibido_en),
                    nota_director=d.nota, requisitos=list(d.requisitos_documentales), pendientes=pendientes))
            principales = [f for f in filas if not f['anexo']]
            resultado['unidades'].append(dict(unidad_id=unidad.pk, nombre=unidad.nombre, slug=unidad.slug,
                periodo_actual=periodo_vigente(cortes, hoy),
                principales=len(principales), enviados=sum(f['enviado'] for f in principales),
                documentos=filas))
        contenido = json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
        if options.get('salida'):
            destino = Path(options['salida'])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido + '\n', encoding='utf-8')
            self.stdout.write(f'Auditoría de solo lectura: {len(unidades)} laboratorios. Resultado: {destino}')
        else:
            self.stdout.write(contenido)
