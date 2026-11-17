"""Hipótesis reproducibles por las API reales, exclusivamente en bases QA locales."""
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExpediente, penalizacion_vigente
from apps.documentos.presentation.expediente import (
    cargar_documento, construir_expediente, cortes_del_anio, del_periodo,
    evaluar_documento, observar_documento, recibir_documento, validar_documento,
)
from apps.documentos.presentation.expediente_archivos import (
    exigir_integridad_documental, identidad_documental,
)
from apps.documentos.presentation.progreso_general import progreso_general


TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')
FECHA_QA = date(2026, 8, 25)
FECHA_TARDIA_QA = date(2026, 9, 5)


def exigir_qa_local():
    base = connection.settings_dict
    if not (settings.DEBUG and str(base['NAME']).startswith(('test_citt_ideal_', 'test_citt_revision_', 'test_citt_qa_', 'test_citt_ci'))
            and base.get('HOST') in ('127.0.0.1', 'localhost')
            and settings.EMAIL_BACKEND in ('django.core.mail.backends.dummy.EmailBackend',
                                           'django.core.mail.backends.locmem.EmailBackend')):
        raise CommandError('Las hipótesis sólo se ejecutan en una base test_citt_ideal_/test_citt_revision_/test_citt_qa_/test_citt_ci '
                           'local, con DEBUG y correo dummy/locmem. No se admite la base operativa.')


@contextmanager
def reloj_qa(fecha=FECHA_QA):
    instante = timezone.make_aware(datetime.combine(fecha, time(10))).astimezone(dt_timezone.utc)
    with patch('django.utils.timezone.now', return_value=instante), patch(
            'django.utils.timezone.localdate', return_value=fecha):
        yield


def declaracion(documento):
    return dict(identidad_documental(documento), version=documento.version, revisado=True)


def pdf_qa(documento):
    from reportlab.pdfgen.canvas import Canvas
    salida = BytesIO()
    lienzo = Canvas(salida, invariant=1)
    lienzo.setTitle('QA de hipótesis, sin validez institucional')
    for y, texto in ((800, 'DATOS SINTETICOS QA - SIN VALIDEZ INSTITUCIONAL'),
            (775, documento.unidad.nombre), (750, documento.exigido.nombre),
            (725, f'Periodo {documento.anio}-{documento.corte or "anual"}; version de ensayo {documento.version + 1}.'),
            (700, 'Evaluacion ficticia exclusivamente para probar la logica del sistema.')):
        lienzo.drawString(40, y, texto)
    lienzo.save()
    datos = salida.getvalue()
    if documento.exigido.requiere_firma:
        # Sólo estructura reconocible por el detector existente. No hay certificado ni firma real.
        datos += b'\n% /Type /Sig /ByteRange [0 100 200 300] /Contents <00>\n'
    return SimpleUploadedFile('hipotesis-qa.pdf', datos, content_type='application/pdf')


def _rechazo(operacion):
    try:
        operacion()
    except (ValidationError, ValueError) as error:
        return dict(rechazado=True, motivo=' '.join(error.messages) if isinstance(error, ValidationError) else str(error))
    return dict(rechazado=False, motivo='La operación fue aceptada.')


class AuditoriaHipotesis:
    """Comprueba aprobación, corrección y vigencia sin puntos administrativos."""
    def __init__(self, identificador, tipos=TIPOS):
        self.identificador, self.tipos = identificador, tipos
        self.casos = []

    def registrar(self, unidad, hipotesis, observado, esperado, **detalle):
        self.casos.append(dict(tipo=unidad.dependencia, unidad_id=unidad.pk,
            hipotesis=hipotesis, observado=observado, esperado=esperado,
            conforme=observado == esperado, **detalle))

    def documentos(self, unidad):
        return [d for d in del_periodo(DocumentoExpediente.objects.filter(unidad=unidad, anio=2026)
            .select_related('unidad', 'exigido', 'recurso'), 'B', cortes_del_anio(2026))
            if not d.exigido.es_anexo]

    def progreso(self, unidad):
        return progreso_general(self.documentos(unidad))

    def nota(self, unidad, total):
        return str((Decimal(total) / len(self.documentos(unidad))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

    def aprobar_documental(self, documento, coordinacion, direccion, *, recibir=True):
        cargar_documento(documento, pdf_qa(documento), coordinacion,
            declaracion_correspondencia=declaracion(documento))
        if recibir:
            from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobar_permanente
            from apps.documentos.presentation.conformidad_planes import confirmar_conformidad
            if es_permanente(documento):
                aprobar_permanente(documento, direccion, documento.version, documento.recurso.hash_sha256,
                    confirmado=True, declaracion_correspondencia=declaracion(documento))
            else:
                confirmar_conformidad(documento, direccion, documento.version, documento.recurso.hash_sha256,
                    confirmado=True, declaracion_correspondencia=declaracion(documento))

    def capacidad(self, unidad, actor):
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.reservas.models.reservas import Reserva
        from apps.reservas.models.seguridad import RequisitoAcceso
        from apps.reservas.presentation.seguridad import validar_aforo
        area = EspacioReservable.objects.create(unidad=unidad, codigo='QA-AFORO',
            nombre='QA: área con capacidad para dos personas', capacidad=2)
        RequisitoAcceso.objects.create(unidad=unidad, nombre='QA: inducción obligatoria',
            tipo='induccion', obligatorio=True, activo=True)
        reserva = Reserva.objects.create(laboratorio=unidad, usuario=actor,
            fecha=FECHA_QA, hora_inicio=time(8), hora_fin=time(9), numero_participantes=3,
            titulo_solicitud='QA: grupo superior a la capacidad', estado='pendiente')
        reserva.espacios_solicitados.add(area)
        rechazo = _rechazo(lambda: validar_aforo(reserva))
        self.registrar(unidad, 'aforo_insuficiente', rechazo['rechazado'], True,
            motivo=rechazo['motivo'], reserva_id=reserva.pk, personas=3, aforo=2,
            alcance='Compuerta de aforo real; no aprueba ni ejecuta la reserva.')

    def unidad(self, tipo, coordinacion, direccion):
        unidad = Unidad.objects.create(nombre=f'[QA HIPOTESIS] {tipo} {self.identificador}',
            slug=f'qa-hipotesis-{tipo.replace("_", "-")}-{self.identificador}',
            dependencia=tipo, administrador=coordinacion, activo=True, fecha_inicio=date(2026, 1, 1))
        construir_expediente(unidad, 2026, FECHA_QA)
        documentos = {d.exigido.codigo: d for d in self.documentos(unidad)}
        resolucion = documentos['RESOLUCION-CREACION']
        # Un observatorio no tiene el protocolo biológico del laboratorio. Se ejercita
        # su compra anual como segunda obligación, respetando el catálogo aplicable.
        protocolo = documentos.get('PROTOCOLO-BIOSEGURIDAD') or documentos['PLAN-COMPRAS-ANUAL']
        self.registrar(unidad, 'sin_datos_no_inventa_cumplimiento', str(self.progreso(unidad)['porcentaje']), '0.00',
            obligaciones=len(documentos))
        rechazo = _rechazo(lambda: validar_documento(resolucion, coordinacion))
        self.registrar(unidad, 'sin_archivo_no_se_envia', rechazo['rechazado'], True, motivo=rechazo['motivo'])
        self.aprobar_documental(resolucion, coordinacion, direccion, recibir=False)
        self.registrar(unidad, 'cargar_no_equivale_a_evaluar', str(self.progreso(unidad)['porcentaje']), '0.00')
        rechazo = _rechazo(lambda: recibir_documento(resolucion, direccion))
        self.registrar(unidad, 'director_confirma_correspondencia', rechazo['rechazado'], True, motivo=rechazo['motivo'])
        recibir_documento(resolucion, direccion, declaracion_correspondencia=declaracion(resolucion))
        from apps.documentos.presentation.conformidad_permanente import aprobar_permanente
        aprobar_permanente(resolucion, direccion, resolucion.version, resolucion.recurso.hash_sha256,
            confirmado=True, declaracion_correspondencia=declaracion(resolucion))
        self.registrar(unidad, 'resolucion_vigente_sin_puntos', str(self.progreso(unidad)['porcentaje']), '0.00')
        self.aprobar_documental(protocolo, coordinacion, direccion)
        self.registrar(unidad, 'documentos_administrativos_sin_puntos', str(self.progreso(unidad)['porcentaje']), '0.00')
        rechazo = _rechazo(lambda: evaluar_documento(resolucion, direccion, 100,
            declaracion_correspondencia=declaracion(resolucion)))
        self.registrar(unidad, 'permanente_no_admite_nota', rechazo['rechazado'], True, motivo=rechazo['motivo'])
        rechazo = _rechazo(lambda: observar_documento(protocolo, direccion, 'QA: falta completar la evidencia.'))
        self.registrar(unidad, 'correccion_exige_fecha', rechazo['rechazado'], True, motivo=rechazo['motivo'])
        observar_documento(protocolo, direccion, 'QA: corregir los apartados indicados.',
            hasta=timezone.now() + timedelta(days=5))
        self.registrar(unidad, 'devolver_no_inventa_aporte', str(self.progreso(unidad)['porcentaje']), '0.00',
            correccion_hasta=protocolo.correccion_hasta.isoformat())
        self.aprobar_documental(protocolo, coordinacion, direccion)
        self.registrar(unidad, 'correccion_reenviada_y_revisada', str(self.progreso(unidad)['porcentaje']), '0.00',
            version=protocolo.version)
        compras = documentos['PLAN-COMPRAS-ANUAL'] if protocolo.exigido.codigo != 'PLAN-COMPRAS-ANUAL' else documentos['PLANIFICACION']
        # Dirección puede recibir después del cierre; la misma API conserva y penaliza la tardanza.
        fecha_tardia = max(FECHA_TARDIA_QA, compras.plazo_original.date() + timedelta(days=1))
        with reloj_qa(fecha_tardia):
            # Quien carga tras el cierre no revisa lo que cargó: la revisión es de otra persona.
            self.aprobar_documental(compras, self.carga_tardia, direccion)
        self.registrar(unidad, 'entrega_tardia_conserva_condicion', compras.entregado_tarde, True,
            tardia=compras.entregado_tarde, penalizacion=penalizacion_vigente())
        self.registrar(unidad, 'tardanza_administrativa_sin_puntos', self.progreso(unidad)['resultado_porcentaje'], None)
        original = Path(resolucion.recurso.archivo.path).read_bytes()
        try:
            Path(resolucion.recurso.archivo.path).write_bytes(original + b'\n% QA: alteracion fuera del flujo\n')
            rechazo = _rechazo(lambda: exigir_integridad_documental(resolucion, direccion,
                etapa='evaluar', declaracion=declaracion(resolucion)))
            self.registrar(unidad, 'archivo_alterado_detiene_evaluacion', rechazo['rechazado'], True,
                motivo=rechazo['motivo'], nota_historica=resolucion.evaluacion,
                alcance='La comprobación profunda se hace al operar; un GET no abre todos los PDF.')
        finally:
            Path(resolucion.recurso.archivo.path).write_bytes(original)
        self.capacidad(unidad, coordinacion)
        return unidad

    def ejecutar(self):
        exigir_qa_local()
        usuario = get_user_model()
        direccion = usuario.objects.create(username=f'qa.hipotesis.direccion.{self.identificador}',
            first_name='Dirección ficticia QA', email=f'qa-direccion-{self.identificador}@example.invalid',
            is_superuser=True, is_staff=True, is_active=True)
        coordinacion = usuario.objects.create(username=f'qa.hipotesis.coordinacion.{self.identificador}',
            first_name='Coordinación ficticia QA', email=f'qa-coordinacion-{self.identificador}@example.invalid',
            is_active=True)
        self.carga_tardia = usuario.objects.create(username=f'qa.hipotesis.tecnica.{self.identificador}',
            first_name='Administración técnica ficticia QA', email=f'qa-tecnica-{self.identificador}@example.invalid',
            is_superuser=True, is_staff=True, is_active=True)
        for actor in (direccion, coordinacion, self.carga_tardia):
            actor.set_unusable_password()
            actor.save(update_fields=['password'])
        # Revisar exige la función de seguimiento vigente; la cuenta técnica no la tiene.
        from apps.core.models.gobernanza import AsignacionGobernanza
        AsignacionGobernanza.objects.create(usuario=direccion, rol='seguimiento', referencia='',
            acto='Acto ficticio exclusivamente de QA', dedicacion='Cobertura de QA',
            desde=date(2026, 1, 1), registrado_por=direccion)
        unidades = []
        with reloj_qa():
            for tipo in self.tipos:
                unidades.append(self.unidad(tipo, coordinacion, direccion))
        return dict(es_prueba=True, fecha_simulada=FECHA_QA.isoformat(), base=connection.settings_dict['NAME'],
            identificador=self.identificador, unidades=[dict(id=u.pk, tipo=u.dependencia, slug=u.slug,
                progreso=str(self.progreso(u)['porcentaje']), resultado_operativo=self.progreso(u)['resultado_porcentaje']) for u in unidades],
            casos=self.casos, total=len(self.casos), conformes=sum(c['conforme'] for c in self.casos),
            brechas=[c for c in self.casos if not c['conforme']],
            alcance='Obligaciones y controles reales en QA. No constituye evidencia de actividad universitaria; '
                    'no demuestra por sí solo resultados académicos ni cumplimiento de indicadores operativos.')


class Command(BaseCommand):
    help = 'Ejercita hipótesis reales de documentos, evaluaciones y progreso en cuatro tipologías, sólo en QA local.'

    def add_arguments(self, parser):
        parser.add_argument('--conservar', action='store_true', help='Conserva las cuatro unidades sintéticas en la base QA.')
        parser.add_argument('--salida', help='Archivo JSON de resultados.')
        parser.add_argument('--identificador', default=None)

    def handle(self, *args, **options):
        exigir_qa_local()
        identificador = options['identificador'] or uuid4().hex[:10]
        if not identificador.isalnum() or len(identificador) > 16:
            raise CommandError('El identificador debe tener hasta 16 letras/números.')
        with transaction.atomic():
            resultado = AuditoriaHipotesis(identificador).ejecutar()
            if not options['conservar']:
                transaction.set_rollback(True)
        resultado['registros_conservados_en_qa'] = options['conservar']
        salida = Path(options['salida']) if options['salida'] else (
            settings.BASE_DIR / 'var/revision-tipologias-20261017' / f'hipotesis-{identificador}.json')
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding='utf8')
        self.stdout.write(f"{resultado['conformes']}/{resultado['total']} hipótesis conformes; "
                          f"{len(resultado['brechas'])} brechas. Informe: {salida}")
