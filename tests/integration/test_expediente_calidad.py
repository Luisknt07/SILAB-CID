"""Expediente de calidad por año: catálogo exigido, estados, plazos, carga, validación.

Lo que la institución exige se materializa por unidad y año en carpetas por período;
el sistema genera lo que puede desde el Centro de reportes, la unidad carga lo
suyo (firmado si hace falta) y la Dirección valida u observa.
"""

import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente import construir_expediente, cortes_academicos_del_anio, cortes_del_anio, generar_documento, observar_documento, periodo_vigente, resumen, validar_documento
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import abrir_entrega, identificar
from tests.integration.utiles import (pdf_legible_prueba, datos_correspondencia_revisada, cargar_documento_revisado)
from tests.integration.test_seguimiento_gobernanza import designar

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix='citt-expediente-')
PDF_FIRMADO = pdf_legible_prueba(firmado=True)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseDelExpediente(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            username='coordinador-expediente', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.direccion = get_user_model().objects.create_superuser('direccion-investigacion')
        designar(cls.direccion)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de expediente', slug='laboratorio-expediente', dependencia='laboratorios',
            fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)
        periodo = PeriodoAcademico.objects.create(
            codigo='2026-A', nombre='Período 2026-A', anio_referencia=2026, ciclo='A', tipo='ordinario',
            ambito='carreras_centros', semanas_planificadas=16, estado='publicado')
        VersionCalendarioAcademico.objects.create(
            periodo=periodo, numero=1, nombre='Calendario', fecha_inicio_clases=date(2026, 3, 9),
            fecha_fin_clases=date(2026, 7, 10), fecha_fin_periodo=date(2026, 7, 17), vigente=True)

    def exigido(self, codigo):
        return DocumentoExigido.objects.get(codigo=codigo)

    def documento(self, codigo, anio=2026, corte='', mes=None):
        construir_expediente(self.unidad, anio, hoy=date(anio, 9, 22))
        return DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo=codigo, anio=anio, corte=corte, mes=mes)


class CatalogoYPlazosTests(BaseDelExpediente):
    def test_la_unidad_firma_dos_documentos_por_periodo_y_lo_demas_viaja_como_anexo(self):
        """Lo mínimo suficiente: planificación al abrir, informe al cerrar, y dos de una sola vez."""
        carpetas = {c for c in DocumentoExigido.objects.filter(activo=True).values_list('carpeta', flat=True)}
        # Las acciones de mejora van en la sección 8 del informe (documentos.0025): no hay carpeta de mejora aparte.
        self.assertEqual(carpetas, {'planeacion', 'ejecucion', 'evaluacion'})
        firmados = DocumentoExigido.objects.filter(activo=True, anexo_de__isnull=True, periodicidad='semestral')
        self.assertEqual({e.codigo for e in firmados}, {'PLANIFICACION', 'INFORME-SEMESTRAL'})
        self.assertTrue(all(e.requiere_firma for e in firmados))
        unicos = DocumentoExigido.objects.filter(activo=True, anexo_de__isnull=True, periodicidad='unica')
        self.assertEqual({e.codigo for e in unicos}, {'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'REGLAMENTO-USO'})
        plan = self.exigido('PLANIFICACION')
        self.assertEqual((plan.plazo_regla, plan.plazo_dias, plan.periodicidad), ('inicio', 15, 'semestral'))
        self.assertTrue(plan.redactable and plan.generable and plan.cargable)
        # Todo lo demás es anexo del informe y ya no es «condicional»; la planificación viaja sin anexos.
        anexos = DocumentoExigido.objects.filter(activo=True, anexo_de__isnull=False)
        # Once anexos comunes, uno por documento que pide la universidad (documentos.0027), y los siete
        # propios de las otras tipologías.
        self.assertEqual(anexos.count(), 18)
        self.assertFalse(anexos.exclude(anexo_de__codigo='INFORME-SEMESTRAL').exists())
        # Los siete propios de otras tipologías no añaden obligaciones
        # a un laboratorio ni desaparecen del catálogo de sus propias unidades.
        aplicables = [e for e in anexos if e.aplica_a(self.unidad.dependencia,
                                                    base=self.unidad.codigo_base)]
        self.assertEqual({e.codigo for e in aplicables},
                         {'REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS', 'PRACTICAS-FT02',
                          'GUIAS', 'PRACTICAS-FT03', 'INDUCCION-SEGURIDAD', 'DESECHOS', 'INVESTIGACION',
                          'TRANSFERENCIA'})
        self.assertFalse(any(e.codigo.startswith(('PP-', 'CE-', 'OBS-')) for e in aplicables))
        # Desechos, investigación y transferencia se presentan según los registros y el plan, pero eso lo
        # decide la generación: en el catálogo ningún anexo es «condicional» que la unidad declare.
        self.assertFalse(anexos.filter(condicional=True).exists())
        self.assertEqual(self.exigido('PRACTICAS-FT02').anexo_de.codigo, 'INFORME-SEMESTRAL')
        # El equipamiento es semestral y viaja con el informe de cada período; el inventario también, en el
        # laboratorio (anual solo en el observatorio).
        self.assertEqual(self.exigido('EQUIPAMIENTO').periodicidad, 'semestral')
        self.assertEqual(self.exigido('EQUIPAMIENTO').periodicidad_para(self.unidad), 'semestral')
        self.assertEqual(self.exigido('INVENTARIO-CORTE').periodicidad_para(self.unidad), 'semestral')
        # Las listas de chequeo, los anexos depurados y las acciones de mejora dejaron de pedirse aparte.
        for codigo in ('CHEQUEO-SEGURIDAD', 'INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS',
                       'INSUMOS-CORTE', 'ACCIONES-MEJORA'):
            self.assertFalse(DocumentoExigido.objects.filter(codigo=codigo, activo=True).exists(), codigo)
    def test_los_cortes_de_gestion_son_naturales_y_el_calendario_solo_es_referencia(self):
        cortes = cortes_del_anio(2026)
        self.assertEqual(cortes['A'], (date(2026, 1, 1), date(2026, 6, 30)))
        self.assertEqual(cortes['B'], (date(2026, 7, 1), date(2026, 12, 31)))
        self.assertEqual(cortes_del_anio(2024)['A'], (date(2024, 1, 1), date(2024, 6, 30)))
        # Las fechas docentes publicadas se conservan como referencia aparte.
        referencia = cortes_academicos_del_anio(2026)
        self.assertEqual(referencia['A'], (date(2026, 3, 9), date(2026, 7, 17)))
        self.assertEqual(referencia['B'], cortes['B'])

    def test_construir_materializa_las_filas_con_su_plazo(self):
        documentos = construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))

        plan = next(d for d in documentos if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'A')
        # El plazo de apertura parte del semestre de gestión, no de las clases.
        self.assertEqual(plan.abre_el, date(2026, 1, 1))
        self.assertEqual(plan.vence_el, date(2026, 1, 16))
        self.assertEqual(plan.estado, 'pendiente')
        self.assertEqual(plan.semaforo(date(2026, 9, 22)), 'vencido')
        self.assertEqual(plan.semaforo(date(2026, 1, 12)), 'por_vencer')
        informes = [d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL']
        self.assertEqual({(d.corte, d.vence_el) for d in informes},
                         {('A', date(2026, 7, 15)), ('B', date(2027, 1, 15))})
        # Un anexo semestral tiene fila en los dos períodos.
        practicas = [d for d in documentos if d.exigido.codigo == 'PRACTICAS-FT02']
        self.assertEqual(sorted(d.corte for d in practicas), ['A', 'B'])
        # El equipamiento y el inventario del laboratorio viajan con el informe de cada período.
        self.assertEqual(sorted(d.corte for d in documentos if d.exigido.codigo == 'EQUIPAMIENTO'), ['A', 'B'])
        self.assertEqual(sorted(d.corte for d in documentos if d.exigido.codigo == 'INVENTARIO-CORTE'), ['A', 'B'])
        self.assertFalse({'PLAN-MANTENIMIENTO', 'INDICADORES-PLAN', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE',
                          'ACCIONES-MEJORA'} & {d.exigido.codigo for d in documentos})
        self.assertNotIn('ORGANIGRAMA', {d.exigido.codigo for d in documentos})
        # Construir otra vez no duplica.
        self.assertEqual(len(construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))), len(documentos))

    def test_un_documento_de_una_sola_vez_se_hereda_al_ano_siguiente(self):
        resolucion = self.documento('RESOLUCION-CREACION', anio=2025)
        cargar_documento_revisado(abrir_entrega(resolucion), SimpleUploadedFile('resolucion.pdf', pdf_legible_prueba('%PDF-1.4 resolucion')),
                         self.coordinador)
        validar_documento(resolucion, self.direccion)

        heredado = self.documento('RESOLUCION-CREACION', anio=2026)

        self.assertEqual(heredado.estado, 'validado')
        self.assertEqual(heredado.recurso, resolucion.recurso)
        self.assertIn('Heredado del año 2025', heredado.observacion)


class GenerarCargarValidarTests(BaseDelExpediente):
    def test_el_informe_sale_con_sus_anexos_y_ninguno_se_genera_suelto(self):
        """La evidencia lleva la fecha del informe que la presenta."""
        from apps.documentos.presentation.expediente import anexos_del

        practicas = self.documento('PRACTICAS-FT02', corte='A')
        with self.assertRaises(ValidationError) as contexto:
            generar_documento(abrir_entrega(practicas), self.coordinador)
        self.assertIn('es un anexo', ' '.join(contexto.exception.messages))

        informe = self.documento('INFORME-SEMESTRAL', corte='A')
        generar_documento(abrir_entrega(informe), self.coordinador)

        informe.refresh_from_db()
        practicas.refresh_from_db()
        self.assertEqual((informe.estado, informe.version), ('generado', 1))
        self.assertEqual((practicas.estado, practicas.version), ('generado', 1))
        recurso = practicas.recurso
        self.assertTrue(recurso.archivo.read().startswith(b'%PDF'))
        self.assertEqual(recurso.carpeta.nombre, 'Ejecución')
        self.assertEqual(recurso.carpeta.carpeta_padre.nombre, 'Expediente de calidad 2026')
        self.assertEqual(recurso.visibilidad, 'interna')
        self.assertFalse(recurso.seguridad_verificada)
        self.assertIn('01/01/2026 al 30/06/2026', recurso.descripcion)
        anexos = anexos_del(informe)
        self.assertIn(practicas.pk, [a.pk for a in anexos])
        # La investigación no se presenta si el plan no compromete su meta; todo lo que sí se presenta tiene archivo.
        self.assertNotIn('INVESTIGACION', {a.exigido.codigo for a in anexos})
        self.assertTrue(all(a.recurso_id for a in anexos))
        # El equipamiento va con el informe de los dos semestres.
        self.assertIn('EQUIPAMIENTO', {a.exigido.codigo for a in anexos})
        self.assertIn('EQUIPAMIENTO',
                      {a.exigido.codigo for a in anexos_del(self.documento('INFORME-SEMESTRAL', corte='B'))})

        generar_documento(abrir_entrega(informe), self.coordinador)
        practicas.refresh_from_db()
        self.assertEqual(practicas.version, 2)
        self.assertEqual(Recurso.objects.get(pk=recurso.pk).estado, 'obsoleto')
        self.assertEqual(practicas.recurso.reemplaza_a_id, recurso.pk)
        anexo_original = practicas.recurso_id
        cargar_documento_revisado(informe, SimpleUploadedFile('informe-firmado.pdf', PDF_FIRMADO), self.coordinador)
        practicas.refresh_from_db()
        self.assertEqual(practicas.version, 2)
        self.assertEqual(practicas.recurso_id, anexo_original)

    def test_no_se_genera_lo_que_la_unidad_debe_cargar_ni_se_carga_lo_que_genera_el_sistema(self):
        with self.assertRaises(ValidationError):
            generar_documento(self.documento('RESOLUCION-CREACION'), self.coordinador)
        with self.assertRaises(ValidationError):
            cargar_documento_revisado(abrir_entrega(self.documento('PRACTICAS-FT02', corte='A')),
                             SimpleUploadedFile('g.pdf', pdf_legible_prueba('%PDF-1.4')), self.coordinador)

    def test_la_planificacion_exige_pdf_firmado(self):
        plan = self.documento('PLANIFICACION', corte='A')

        with self.assertRaises(ValidationError) as contexto:
            cargar_documento_revisado(abrir_entrega(plan), SimpleUploadedFile('plan.pdf', pdf_legible_prueba('%PDF-1.4 sin firma')),
                             self.coordinador)
        self.assertIn('firma electrónica', ' '.join(contexto.exception.messages))
        self.assertEqual(plan.estado, 'pendiente')

        cargar_documento_revisado(abrir_entrega(plan), SimpleUploadedFile('plan-firmado.pdf', PDF_FIRMADO),
                         self.coordinador)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'cargado')
        self.assertEqual(plan.cargado_por, self.coordinador)
        self.assertEqual(plan.recurso.tipo_adjunto, 'certificado')
        self.assertIn('firma(s) electrónica(s)', plan.recurso.descripcion)

    def test_validar_cierra_el_documento_y_solo_la_direccion_lo_devuelve(self):
        """Lo enviado es inmutable: se corrige abriendo una versión nueva, con motivo y firma."""
        protocolo = self.documento('PROTOCOLO-BIOSEGURIDAD')
        with self.assertRaises(ValidationError):
            validar_documento(protocolo, self.direccion)
        cargar_documento_revisado(abrir_entrega(protocolo), SimpleUploadedFile('protocolo.pdf', PDF_FIRMADO),
                         self.coordinador)

        with self.assertRaises(ValidationError):
            observar_documento(protocolo, self.direccion, '   ')
        validar_documento(protocolo, self.coordinador)
        protocolo.refresh_from_db()
        self.assertEqual((protocolo.estado, protocolo.validado_por), ('validado', self.coordinador))

        # Enviado: ni se recarga ni lo devuelve la unidad.
        with self.assertRaises(ValidationError):
            cargar_documento_revisado(abrir_entrega(protocolo),
                             SimpleUploadedFile('p2.pdf', PDF_FIRMADO + b'%otra' + b'\n'), self.coordinador)
        with self.assertRaises(ValidationError):
            observar_documento(protocolo, self.coordinador, 'me arrepentí')
        protocolo.refresh_from_db()
        self.assertEqual((protocolo.estado, protocolo.version), ('validado', 1))

        observar_documento(protocolo, self.direccion, 'Falta el apartado de manejo de reactivos.', hasta=timezone.now() + timedelta(days=3))
        protocolo.refresh_from_db()
        self.assertEqual((protocolo.estado, protocolo.validado_por), ('observado', self.direccion))
        self.assertEqual(protocolo.semaforo(), 'observado')

        cargar_documento_revisado(abrir_entrega(protocolo), SimpleUploadedFile('protocolo-v2.pdf', PDF_FIRMADO + b'%v2' + b'\n'),
                         self.coordinador)
        protocolo.refresh_from_db()
        self.assertEqual((protocolo.estado, protocolo.observacion, protocolo.version),
                         ('cargado', 'Falta el apartado de manejo de reactivos.', 2))
        validar_documento(protocolo, self.direccion)
        protocolo.refresh_from_db()
        self.assertEqual(protocolo.semaforo(), 'validado')
    def test_el_resumen_cuenta_solo_lo_que_la_unidad_firma(self):
        """Cuatro firmas al año y dos documentos de una vez; los anexos no son obligaciones.

        Antes contaban diecinueve por período, quince de ellos producidos por el
        sistema: una unidad impecable aparecía con 11 % de cumplimiento.
        """
        documentos = construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        cifras = resumen(documentos, hoy=date(2026, 9, 22))

        exigibles = [d for d in documentos if d.exigible]
        self.assertEqual({d.exigido.codigo for d in exigibles},
                         {'PLANIFICACION', 'INFORME-SEMESTRAL', 'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD',
                          'REGLAMENTO-USO', 'PLAN-COMPRAS-ANUAL'})
        self.assertEqual(cifras['total'], 8)
        self.assertGreater(cifras['vencidos'], 0)
        self.assertEqual(cifras['validados'], 0)
        self.assertEqual(cifras['completo'], 0)
        practicas = next(d for d in documentos if d.exigido.codigo == 'PRACTICAS-FT02' and d.corte == 'A')
        self.assertTrue(practicas.exigido.es_anexo)
        self.assertFalse(practicas.exigible)
    def test_lo_que_cierra_el_periodo_no_se_reclama_antes_de_su_ventana(self):
        """Un informe de cierre no puede aparecer pendiente desde enero."""
        documentos = construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))

        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')
        self.assertIsNotNone(informe.abre_el)
        self.assertEqual(informe.abre_el, date(2026, 12, 16))
        self.assertEqual(informe.vence_el, date(2027, 1, 15))
        self.assertEqual((informe.vence_el - informe.abre_el).days, 30)
        self.assertEqual(informe.semaforo(informe.abre_el - timedelta(days=1)), 'no_abierto')
        self.assertEqual(informe.semaforo(informe.abre_el), 'a_tiempo')
        self.assertEqual(informe.semaforo(informe.vence_el - timedelta(days=5)), 'por_vencer')
        self.assertEqual(informe.semaforo(informe.vence_el + timedelta(days=1)), 'vencido')

    def test_la_planificacion_se_entrega_en_los_primeros_quince_dias(self):
        documentos = construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))

        plan = next(d for d in documentos if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'A')
        self.assertEqual(plan.abre_el, date(2026, 1, 1))
        self.assertEqual(plan.vence_el, date(2026, 1, 16))

    def test_ya_nada_se_declara_no_aplicable(self):
        """Si no hubo datos, el anexo sale vacío y lo dice; nadie tiene que justificar nada."""
        from apps.documentos.presentation.expediente import marcar_no_aplica

        with self.assertRaises(ValidationError):
            marcar_no_aplica(self.documento('PRACTICAS-FT02', corte='A'), self.coordinador, 'no tuvimos prácticas')
        # Ni siquiera el anexo condicional: si no aplica lo decide la generación con el plan, no la unidad.
        with self.assertRaises(ValidationError):
            marcar_no_aplica(self.documento('INVESTIGACION', corte='A'), self.coordinador, 'no investigamos')
        with self.assertRaises(ValidationError):
            marcar_no_aplica(self.documento('INFORME-SEMESTRAL', corte='A'), self.coordinador, 'no queremos')
        cifras = resumen(construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22)), hoy=date(2026, 9, 22))
        self.assertEqual(cifras['no_aplican'], 0)


class ConsolaYAdminTests(BaseDelExpediente):
    def test_la_pagina_del_expediente_integra_el_flujo_y_permite_generar_y_cargar(self):
        self.client.force_login(self.coordinador)
        ruta = reverse('gestion_expediente_unidad', args=[self.unidad.slug])

        pagina = self.client.get(ruta, {'anio': 2026, 'corte': 'B'})

        self.assertEqual(pagina.status_code, 200)
        for etapa in ('1. Documentos base', '2. Planificación', '3. Anexos y seguimiento',
                      '4. Mejora y seguimiento'):
            self.assertContains(pagina, etapa)
        # La planificación viaja sin anexos: no hay soportes aparte que revisar.
        self.assertNotContains(pagina, 'data-soporte-planificacion=')
        self.assertContains(pagina, 'Planificación semestral del laboratorio')
        self.assertContains(pagina, 'Vencido')
        self.assertContains(pagina, 'Habilitar expediente del año')
        self.assertFalse(DocumentoExpediente.objects.filter(unidad=self.unidad, anio=2026).exists())
        self.client.post(ruta, {'anio': 2026, 'accion': 'preparar'})
        planificacion = DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='PLANIFICACION', anio=2026, corte='B')
        # Los formularios se cargan al seleccionar la entrega, en el mismo centro.
        pagina = self.client.get(ruta, {'anio': 2026, 'corte': 'B'})
        self.assertContains(pagina, reverse('redactar_documento_expediente',
                                          args=[self.unidad.slug, planificacion.pk]))
        self.assertContains(pagina, 'data-entrega-editor')

        informe = DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='INFORME-SEMESTRAL', anio=2026, corte='A')
        abrir_entrega(informe)
        respuesta = self.client.post(ruta, {'anio': 2026, 'documento': informe.pk, 'accion': 'generar'})
        # Volver conserva el período abierto y el enlace al documento gestionado.
        corte = periodo_vigente(cortes_del_anio(2026), timezone.localdate())
        self.assertRedirects(respuesta, f'{ruta}?anio=2026&corte={corte}#entrega-{informe.pk}',
                             fetch_redirect_response=False)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, 'generado')
        practicas = DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo='PRACTICAS-FT02', anio=2026,
                                                    corte='A')
        self.assertEqual(practicas.estado, 'generado')

        organigrama = DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo='RESOLUCION-CREACION',
                                                      anio=2026)
        abrir_entrega(organigrama)
        self.client.post(ruta, {'anio': 2026, 'documento': organigrama.pk, 'accion': 'cargar',
                                **datos_correspondencia_revisada(organigrama),
                                'archivo': SimpleUploadedFile('resolucion.pdf', pdf_legible_prueba('%PDF-1.4 res'))})
        organigrama.refresh_from_db()
        self.assertEqual(organigrama.estado, 'cargado')
        # Los reportes de seguridad se presentan siempre (documentos.0027).
        seguridad = DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo='INDUCCION-SEGURIDAD',
                                                    anio=2026, corte='A')
        # Un anexo no se declara «no aplica»: si no hubo registros, el anexo sale vacío y lo dice.
        self.client.post(ruta, {'anio': 2026, 'documento': seguridad.pk, 'accion': 'no_aplica',
                                'justificacion': 'La unidad no tuvo inspecciones.'})
        seguridad.refresh_from_db()
        self.assertEqual(seguridad.estado, 'generado')
        self.assertIsNone(seguridad.validado_por_id)
        # El archivo se abre por la ruta de recursos de la unidad, solo para quien la gestiona.
        self.assertEqual(self.client.get(reverse('recurso_unidad', args=[organigrama.recurso_id])).status_code, 200)

    def test_quien_no_gestiona_la_unidad_no_entra_al_expediente(self):
        ajeno = get_user_model().objects.create_user('ajeno-expediente', password='clave-segura')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)

        self.assertEqual(self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug])).status_code, 403)

    def test_la_consola_enlaza_el_expediente_desde_el_centro_de_reportes(self):
        self.client.force_login(self.coordinador)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'reportes'})
        self.assertContains(panel, reverse('gestion_expediente_unidad', args=[self.unidad.slug]))

    def test_el_administrador_valida_por_tipo_y_ve_el_consolidado(self):
        organigrama = self.documento('RESOLUCION-CREACION')
        cargar_documento_revisado(abrir_entrega(organigrama), SimpleUploadedFile('resolucion.pdf', pdf_legible_prueba('%PDF-1.4 res')),
                         self.coordinador)
        self.client.force_login(self.direccion)

        lista = self.client.get(reverse('admin:laboratorios_documentoexpediente_changelist'), {'todas': '1'})
        self.assertContains(lista, 'Resolución de creación de la unidad')
        respuesta = self.client.post(reverse('admin:laboratorios_documentoexpediente_changelist'), {
            'action': 'validar_documentos', '_selected_action': [organigrama.pk], 'todas': '1'})
        self.assertEqual(respuesta.status_code, 302)
        organigrama.refresh_from_db()
        self.assertEqual((organigrama.estado, organigrama.validado_por), ('validado', self.direccion))

        consolidado = self.client.get(reverse('admin:reportes-expediente-por-tipo'), {'tipo': 'laboratorios', 'anio': 2026})
        self.assertEqual(consolidado.status_code, 200)
        fila = next(f for f in consolidado.context['filas'] if f['unidad'] == self.unidad)
        self.assertEqual(fila['validados'], 1)
        # El tablero lee dos firmas por período y lo de una sola vez, no carpetas.
        self.assertEqual([p['corte'] for p in fila['periodos']], ['A', 'B'])
        self.assertEqual([e['nombre'] for e in fila['periodos'][0]['entregas']],
            ['Planificación semestral del laboratorio',
             'Informe semestral de actividades y cumplimiento de la planificación'])
        self.assertIn(organigrama.pk, [d.pk for d in fila['de_la_unidad']])
        self.assertContains(consolidado, 'Documentos de la unidad')
        indice = self.client.get(reverse('admin:index'))
        self.assertContains(indice, 'Resumen anual de entregas')
        self.assertContains(indice, 'Documentos exigidos del expediente')
