"""La unidad valida, la Dirección recibe y califica, el decanato recibe el informe.

No hay firma intermedia: el responsable de cada unidad responde por que lo que
sube sea verídico, y el director del sistema dice si la unidad cumple. Lo que
califica se remite al decanato para que decida —responsables, compras,
repotenciación— y el mínimo con el que se mide a todas las unidades vive en la
política de calidad, no en el código.

Entregar fuera de plazo no exime de entregar: el responsable lo solicita, la
Dirección lo habilita, el documento se recibe y la tardanza descuenta puntos.
"""

from datetime import date, timedelta
from unittest.mock import patch
from django.utils import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.documentos.presentation.cumplimiento import cumplimiento_de_unidad, cumplimiento_por_periodo, grupos_por_tipo, unidades_auditadas
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, cortes_del_anio, es_receptor_de, habilitar_entrega_tardia, observar_documento, periodo_vigente, solicitar_entrega_tardia, validar_anexo, validar_documento, tramo_del_documento
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.documentos.models.expediente import PoliticaDeCalidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.documentos.models.expediente import minimo_vigente, olvidar_politica, penalizacion_vigente
from tests.integration.test_cumplimiento_expediente import PDF_FIRMADO
from tests.integration.utiles import identificar
from tests.integration.utiles import (datos_correspondencia_revisada, recibir_documento_revisado, evaluar_documento_revisado)

HOY = date.today()
ANIO = HOY.year


class BaseDelExpediente(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user('coordinador-recibe', password='clave-segura')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.decano = get_user_model().objects.create_user(
            'decano-recibe', password='clave-segura', first_name='Rosa', last_name='Decana')
        identificar(cls.decano, tipo_usuario='administrativo', carrera='')
        cls.direccion = get_user_model().objects.create_superuser(
            'direccion-recibe', 'd@ejemplo.ec', 'clave-segura')
        cls.decanato = DependenciaAcademica.objects.create(
            nombre='Facultad de Industrias Agropecuarias y Ciencias Ambientales', tipo='decanato')
        cls.decanato.receptores.add(cls.decano)
        cls.laboratorio = Unidad.objects.create(
            nombre='Laboratorio adscrito', slug='laboratorio-adscrito', dependencia='laboratorios',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1), administrador=cls.coordinador,
            activo=True, adscrita_a=cls.decanato)
        cls.suelto = Unidad.objects.create(
            nombre='Laboratorio sin dependencia', slug='laboratorio-sin-dependencia', dependencia='laboratorios',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1), administrador=cls.coordinador,
            activo=True)
        # El período en curso es el único donde la entrega está abierta sin permiso;
        # el otro corte del año sirve para probar lo que ya venció.
        cls.corte = periodo_vigente(cortes_del_anio(ANIO), HOY)

    def documento(self, unidad, codigo='INFORME-SEMESTRAL', corte=None):
        corte = self.corte if corte is None else corte
        return next(
            d for d in construir_expediente(unidad, ANIO, HOY)
            if d.exigido.codigo == codigo and d.corte == corte)

    def abrir_plazo(self, documento):
        """Deja la ventana abierta aunque el período esté en sus últimos días.

        Lo que se mide aquí es la regla, no en qué día del calendario corre la
        prueba; la entrega fuera de plazo tiene sus propias pruebas.
        """
        from tests.integration.utiles import abrir_entrega
        abrir_entrega(documento)

    def archivado(self, unidad, corte=None):
        """Archivo firmado externo anterior al editor, todavía sin enviar.

        No se genera primero un PDF nativo: eso dejaría una preparación del
        editor que este contrato histórico nunca tuvo.
        """
        corte = self.corte if corte is None else corte
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[unidad.slug])
        documento = self.documento(unidad, corte=corte)
        # Estas regresiones prueban recepción, permisos y acceso a archivos
        # del contrato legado. Fijar su alcance antes de cargar el original
        # evita atribuirles un cierre anticipado del nuevo semestre de gestión;
        # esa prohibición se comprueba con documentos gestion_v1 por separado.
        for fila in (documento, *anexos_del(documento)):
            inicio, fin = tramo_del_documento(fila)
            fila.tramo_inicio, fila.tramo_fin = inicio, fin
            fila.marco_periodo = 'academico_legacy'
            fila.save(update_fields=['tramo_inicio', 'tramo_fin', 'marco_periodo'])
        self.abrir_plazo(documento)
        datos = {'anio': ANIO, 'corte': corte, 'documento': documento.pk}
        self.client.post(url, {**datos, **datos_correspondencia_revisada(documento), 'accion': 'cargar',
                               'archivo': SimpleUploadedFile('firmado.pdf', PDF_FIRMADO + unidad.slug.encode())})
        documento.refresh_from_db()
        return documento, url

    def enviado(self, unidad, corte=None):
        """Lo anterior y, además, validado por el responsable de la unidad."""
        documento, url = self.archivado(unidad, corte)
        for anexo in anexos_del(documento):
            validar_anexo(anexo, self.coordinador)
        validar_documento(documento, self.coordinador)
        documento.refresh_from_db()
        return documento, url


class PoliticaDeCalidadTests(BaseDelExpediente):
    """El mínimo institucional es administrable: es el indicador de todas las unidades."""

    def tearDown(self):
        # La base vuelve atrás al cerrar la prueba; lo recordado también tiene que volver.
        olvidar_politica()
        super().tearDown()

    def test_el_minimo_de_por_omision_es_el_institucional(self):
        self.assertEqual(minimo_vigente(), 70)
        self.assertEqual(penalizacion_vigente(), 20)

    def test_cambiar_el_minimo_cambia_quien_cumple_sin_tocar_el_codigo(self):
        documento, _url = self.enviado(self.laboratorio)
        evaluar_documento_revisado(documento, self.direccion, 65, 'Cumple a medias.',
                          debilidades='Falta el detalle de uso.', recomendaciones='Completarlo.')
        documento.refresh_from_db()
        self.assertFalse(documento.cumple)

        PoliticaDeCalidad(minimo_cumplimiento=60).save()

        self.assertEqual(minimo_vigente(), 60)
        documento.refresh_from_db()
        self.assertTrue(documento.cumple)

    def test_solo_hay_una_politica(self):
        PoliticaDeCalidad(minimo_cumplimiento=80).save()
        PoliticaDeCalidad(minimo_cumplimiento=75).save()

        self.assertEqual(PoliticaDeCalidad.objects.count(), 1)
        self.assertEqual(minimo_vigente(), 75)

    def test_la_direccion_la_cambia_desde_el_administrador(self):
        PoliticaDeCalidad().save()
        self.client.force_login(self.direccion)
        url = reverse('admin:documentos_politicadecalidad_change', args=[1])

        ficha = self.client.get(url)
        self.assertContains(ficha, 'minimo_cumplimiento')
        self.client.post(url, {'minimo_cumplimiento': 75, 'penalizacion_entrega_tardia': 25})

        politica = PoliticaDeCalidad.objects.get()
        self.assertEqual(politica.minimo_cumplimiento, 75)
        self.assertEqual(politica.actualizado_por, self.direccion)
        # Existiendo la política, no se crea otra ni se borra la que mide a todos.
        self.assertEqual(self.client.get(reverse('admin:documentos_politicadecalidad_add')).status_code, 403)
        self.assertEqual(self.client.get(
            reverse('admin:documentos_politicadecalidad_delete', args=[1])).status_code, 403)


class LaDireccionRecibeTests(BaseDelExpediente):
    """Lo que cuenta es contar con el documento: si la unidad no validó, la Dirección recibe."""

    def test_recibe_lo_archivado_y_desde_ahi_lo_califica(self):
        documento, _url = self.archivado(self.laboratorio)
        self.assertEqual(documento.estado, 'cargado')
        with self.assertRaises(ValidationError):
            evaluar_documento_revisado(documento, self.direccion, 90, 'Bien.')

        recibir_documento_revisado(documento, self.direccion)

        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'validado')
        self.assertEqual(documento.recibido_por, self.direccion)
        self.assertIsNotNone(documento.recibido_en)
        evaluar_documento_revisado(documento, self.direccion, 90, 'Cumple.')
        documento.refresh_from_db()
        self.assertEqual(documento.nota, 90)
        self.assertTrue(documento.cumple)

    def test_solo_la_direccion_recibe_y_solo_lo_que_existe(self):
        documento, _url = self.archivado(self.laboratorio)
        with self.assertRaises(ValidationError):
            recibir_documento_revisado(documento, self.coordinador)

        pendiente = self.documento(self.suelto, codigo='PLANIFICACION')
        with self.assertRaises(ValidationError) as contexto:
            recibir_documento_revisado(pendiente, self.direccion)
        self.assertIn('no se recibe lo que todavía no existe', ' '.join(contexto.exception.messages))

    def test_lo_validado_por_la_unidad_se_califica_sin_pasar_por_nadie_mas(self):
        documento, _url = self.enviado(self.laboratorio)

        evaluar_documento_revisado(documento, self.direccion, 85, 'Cumple.')

        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 85)
        self.assertIsNone(documento.recibido_en)

    def test_devolver_observado_borra_la_recepcion(self):
        documento, _url = self.archivado(self.laboratorio)
        recibir_documento_revisado(documento, self.direccion)

        observar_documento(documento, self.direccion, 'Faltan las evidencias de las prácticas.', hasta=timezone.now() + timedelta(days=3))

        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'observado')
        self.assertIsNone(documento.recibido_en)
        # Lo enviado solo lo devuelve la Dirección.
        documento, _url = self.enviado(self.suelto)
        with self.assertRaises(ValidationError) as contexto:
            observar_documento(documento, self.coordinador, 'Me equivoqué.')
        self.assertIn('solo la dirección', ' '.join(contexto.exception.messages).lower())

    def test_desde_el_tablero_recibe_califica_y_queda_auditado(self):
        documento, _url = self.archivado(self.laboratorio)
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        query = f'anio={ANIO}&corte={self.corte}'

        sin_envio = self.client.get(url, {'anio': ANIO, 'corte': self.corte, 'revisar': documento.pk})
        self.assertContains(sin_envio, 'class="revision-documental__boton is-aprobar" disabled')
        self.client.post(url, dict(query=query, documento=documento.pk, accion='aprobar_documento',
                                   version=documento.version, huella=documento.recurso.hash_sha256))
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'cargado')
        self.assertIsNone(documento.recibido_en)
        self.assertIsNone(documento.evaluacion)

        for anexo in anexos_del(documento):
            validar_anexo(anexo, self.coordinador)
        validar_documento(documento, self.coordinador)
        documento.refresh_from_db()
        tablero = self.client.get(url, {'anio': ANIO, 'corte': self.corte, 'revisar': documento.pk})
        self.assertContains(tablero, 'value="aprobar_documento"')
        self.client.post(url, {'query': query, 'documento': documento.pk, 'accion': 'evaluar',
                               'evaluacion': 92, 'evaluacion_observacion': 'Cumple.'})

        documento.refresh_from_db()
        # El informe actual confirma sus indicadores, no una nota libre enviada por POST.
        self.assertIsNone(documento.evaluacion)
        # La acción del listado recibe y confirma el resultado conservado
        # de la versión enviada; no expone una calificación libre.
        self.client.post(url, dict(query=query, documento=documento.pk, accion='aprobar_documento',
                                   version=documento.version,
                                   huella=documento.recurso.hash_sha256))
        documento.refresh_from_db()
        self.assertEqual(documento.recibido_por, self.direccion)
        self.assertEqual(documento.evaluacion, 0)
        rastro = RegistroAuditoriaUnidad.objects.filter(
            unidad=self.laboratorio, entidad='documentos.DocumentoExpediente',
            objeto_id=str(documento.pk), usuario=self.direccion, accion='actualizar')
        self.assertEqual({'recibir_documento', 'evaluar_documento', 'confirmar_cierre', 'decidir_desde_listado'},
                         {r.descripcion.split(':')[0] for r in rastro})
        self.assertTrue(all(r.datos_anteriores and r.datos_nuevos for r in rastro))

    def test_quien_recibe_el_informe_lee_pero_no_interviene(self):
        documento, url = self.enviado(self.laboratorio)
        self.assertTrue(es_receptor_de(self.decano, self.laboratorio))
        self.assertTrue(es_receptor_de(self.direccion, self.laboratorio))
        self.assertFalse(es_receptor_de(self.coordinador, self.laboratorio))
        self.assertFalse(es_receptor_de(self.decano, self.suelto))
        self.client.force_login(self.decano)

        pagina = self.client.get(url, {'anio': ANIO, 'corte': self.corte})
        self.assertContains(pagina, 'Recibes el informe de Facultad de Industrias')
        self.assertContains(pagina, 'lees el expediente')
        self.assertNotContains(pagina, 'value="evaluar"')
        self.assertNotContains(pagina, 'value="validar"')
        self.assertNotContains(pagina, 'value="recibir"')
        self.assertEqual(self.client.get(reverse('recurso_unidad', args=[documento.recurso_id])).status_code, 200)

        respuesta = self.client.post(url, {'anio': ANIO, 'corte': self.corte,
                                           'documento': documento.pk, 'accion': 'observar',
                                           'observacion': 'No me gusta.'})
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(list(unidades_auditadas(self.decano)), [self.laboratorio])


class EntregaFueraDePlazoTests(BaseDelExpediente):
    """Se recibe, pero cuesta: se solicita, la Dirección habilita y la nota pierde puntos."""

    # El período A del año pasado está vencido cualquier día en que se corra la prueba.
    ANIO_CERRADO = ANIO - 1

    def _vencido(self):
        documento = next(
            d for d in construir_expediente(self.laboratorio, self.ANIO_CERRADO, HOY)
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')
        documento.ultimatum_hasta = timezone.now() - timedelta(days=1)
        documento.save(update_fields=['ultimatum_hasta'])
        self.assertTrue(documento.vencido)
        return documento

    def _entrega(self, documento, usuario):
        self.client.force_login(usuario)
        return self.client.post(
            reverse('gestion_expediente_unidad', args=[self.laboratorio.slug]),
            {'anio': self.ANIO_CERRADO, 'corte': 'A', 'documento': documento.pk, 'accion': 'cargar',
             **datos_correspondencia_revisada(documento),
             'archivo': SimpleUploadedFile('firmado.pdf', PDF_FIRMADO)},
            follow=True)

    def test_la_unidad_no_entrega_vencido_el_plazo_sin_habilitacion(self):
        documento = self._vencido()

        respuesta = self._entrega(documento, self.coordinador)

        self.assertContains(respuesta, 'Solicita a la Dirección la entrega fuera de plazo')
        documento.refresh_from_db()
        self.assertIsNone(documento.recurso_id)

    def test_se_solicita_la_direccion_habilita_y_la_entrega_queda_marcada(self):
        documento = self._vencido()
        with self.assertRaises(ValidationError) as contexto:
            habilitar_entrega_tardia(documento, self.direccion, hasta=timezone.now() + timedelta(days=7))
        self.assertIn('tiene que pedirla primero', ' '.join(contexto.exception.messages))

        solicitar_entrega_tardia(documento, self.coordinador, 'El período cerró antes de la firma.')
        habilitar_entrega_tardia(documento, self.direccion, hasta=timezone.now() + timedelta(days=7))

        documento.refresh_from_db()
        self.assertEqual(documento.tardanza_habilitada_por, self.direccion)
        self._entrega(documento, self.coordinador)
        documento.refresh_from_db()
        self.assertIsNotNone(documento.recurso_id)
        self.assertTrue(documento.entregado_tarde)

    def test_la_tardanza_descuenta_puntos_del_cumplimiento(self):
        documento = self._vencido()
        solicitar_entrega_tardia(documento, self.coordinador, 'El período cerró antes de la firma.')
        habilitar_entrega_tardia(documento, self.direccion, hasta=timezone.now() + timedelta(days=7))
        self._entrega(documento, self.coordinador)
        documento.refresh_from_db()
        recibir_documento_revisado(documento, self.direccion)

        evaluar_documento_revisado(documento, self.direccion, 85, 'Completo, pero tarde.',
                          recomendaciones='Entregar dentro de la ventana del próximo período.')

        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 85)
        self.assertEqual(documento.nota, 85 - penalizacion_vigente())
        self.assertFalse(documento.cumple)

    def test_la_direccion_entrega_cuando_quiera(self):
        """El director recibe fuera de plazo sin pedirse permiso a sí mismo."""
        documento = self._vencido()

        self._entrega(documento, self.direccion)

        documento.refresh_from_db()
        self.assertIsNotNone(documento.recurso_id)
        self.assertTrue(documento.entregado_tarde)


class IndicadorDelMinimoTests(BaseDelExpediente):
    """Cuántas unidades alcanzan el mínimo: es lo que la Dirección responde al decanato."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico

        # La acreditación del plan usa un calendario publicado de la misma
        # cohorte; esta clase prueba el indicador, no la ausencia de calendario.
        inicio, fin = cortes_del_anio(ANIO)[cls.corte]
        periodo = PeriodoAcademico.objects.create(codigo=f'{ANIO}-{cls.corte}',
            anio_referencia=ANIO, ciclo=cls.corte, tipo='ordinario',
            ambito='carreras_centros', estado='publicado')
        VersionCalendarioAcademico.objects.create(periodo=periodo, numero=1, vigente=True,
            fecha_inicio_clases=inicio, fecha_fin_clases=fin, fecha_fin_periodo=fin)

    def plan_conforme(self):
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.presentation.expediente import _generar, generar_anexos
        from apps.documentos.presentation.conformidad_planes import confirmar_conformidad
        from tests.integration.utiles import (
            cargar_documento_revisado, contenido_plan_completo, correspondencia_revisada,
        )

        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        # El informe de esta clase representa el contrato legado. El plan y
        # sus respaldos conservan ese mismo alcance antes de redactarse y
        # aprobarse; una conformidad de otro marco no puede habilitar el cierre.
        for fila in (plan, *anexos_del(plan)):
            inicio, fin = tramo_del_documento(fila)
            fila.tramo_inicio, fila.tramo_fin = inicio, fin
            fila.marco_periodo = 'academico_legacy'
            fila.save(update_fields=['tramo_inicio', 'tramo_fin', 'marco_periodo'])
        self.abrir_plazo(plan)
        DocumentoElaborado.objects.update_or_create(documento=plan,
            defaults=dict(contenido=contenido_plan_completo(plan, self.coordinador), version=1))
        generar_anexos(plan, self.coordinador)
        _generar(plan, self.coordinador)
        with plan.recurso.archivo.open('rb') as archivo:
            firmado = archivo.read() + b'\n% /Type /Sig /ByteRange [0 100 200 300] /Contents <00>\n'
        cargar_documento_revisado(plan, SimpleUploadedFile('plan-firmado.pdf', firmado), self.coordinador)
        for anexo in anexos_del(plan):
            if anexo.recurso_id:
                validar_anexo(anexo, self.coordinador)
        validar_documento(plan, self.coordinador)
        confirmar_conformidad(plan, self.direccion, plan.version, plan.recurso.hash_sha256,
            confirmado=True, declaracion_correspondencia=correspondencia_revisada(plan))
        return plan

    def comprobar_alcance_del_ciclo(self, plan, cierre):
        campos = ('unidad_id', 'anio', 'corte', 'marco_periodo', 'tramo_inicio', 'tramo_fin')
        self.assertEqual(tuple(getattr(plan, c) for c in campos),
                         tuple(getattr(cierre, c) for c in campos))

    def medicion_cierre_acreditada(self, plan, porcentaje):
        """Aísla la medición aceptada; el agregado, archivos y requisito son reales.

        Las garantías del cálculo congelado y su rechazo cuando está incompleto
        se prueban en test_cierre_automatico_laboratorios y test_cierre_no_compensable.
        Estos casos comprueban el indicador institucional con un resultado ya
        acreditado, sin fabricar actividad de la unidad ni reescribir auditorías.
        """
        from apps.documentos.presentation import cumplimiento
        original = cumplimiento.completar_controles_de_lectura

        def controles(documentos):
            documentos = original(documentos)
            for d in documentos:
                if d.exigido.codigo != 'INFORME-SEMESTRAL' or d.unidad_id != plan.unidad_id:
                    continue
                control = dict(getattr(d, 'automatizacion', {}) or {})
                control['vigente'] = True
                control['resumen'] = {**(control.get('resumen') or {}), 'cierre': dict(
                    version=d.version, recurso=d.recurso_id, nota=porcentaje,
                    plan=dict(documento=plan.pk, version=plan.version, recurso=plan.recurso_id),
                    plan_aprobado=True, completo=True, congelado=True, demostracion=False,
                    filas=[dict(exigible=True, definida=True, pendiente=False, porcentaje=porcentaje)])}
                d.automatizacion = control
            return documentos

        return patch('apps.documentos.presentation.cumplimiento.completar_controles_de_lectura',
            side_effect=controles)

    def test_el_tablero_dice_cuantas_unidades_alcanzan_el_minimo(self):
        plan = self.plan_conforme()
        documento, _url = self.enviado(self.laboratorio)
        self.comprobar_alcance_del_ciclo(plan, documento)
        evaluar_documento_revisado(documento, self.direccion, 90, 'Cumple.')

        # Recortado a lo que mira el decanato: una sola unidad, la suya.
        with self.medicion_cierre_acreditada(plan, 90):
            filas, totales = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.decano)

        nivel = filas[0]['nivel']['total']
        self.assertEqual(totales['minimo'], 70)
        self.assertEqual(totales['evaluadas'], 1)
        self.assertEqual(totales['nivel_medio'], nivel)
        self.assertEqual(totales['cumplen_minimo'], 1 if nivel >= 70 else 0)
        self.assertEqual(totales['bajo_minimo'], 0 if nivel >= 70 else 1)
        self.assertEqual(totales['indicador'], 100 if nivel >= 70 else 0)

    def test_bajo_el_minimo_la_unidad_cuenta_como_incumplida(self):
        plan = self.plan_conforme()
        documento, _url = self.enviado(self.laboratorio)
        self.comprobar_alcance_del_ciclo(plan, documento)
        evaluar_documento_revisado(documento, self.direccion, 40, 'No cumple.',
                          debilidades='Sin evidencias.', recomendaciones='Entregarlas.')

        with self.medicion_cierre_acreditada(plan, 40):
            _filas, totales = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.decano)

        self.assertEqual(totales['cumplen_minimo'], 0)
        self.assertEqual(totales['bajo_minimo'], 1)
        self.assertEqual(totales['indicador'], 0)

    def test_un_cierre_sin_plan_conforme_no_cuenta_como_unidad_evaluada_ni_cero(self):
        documento, _url = self.enviado(self.laboratorio)
        evaluar_documento_revisado(documento, self.direccion, 90, 'Antecedente conservado.')
        filas, totales = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.decano)
        self.assertIsNone(filas[0]['nivel']['total'])
        self.assertEqual((totales['evaluadas'], totales['cumplen_minimo'], totales['bajo_minimo']), (0, 0, 0))
        self.assertIsNone(totales['indicador'])
        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 90)

    def test_la_pantalla_lo_muestra_con_el_porcentaje_de_la_politica(self):
        self.client.force_login(self.direccion)

        tablero = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                                  {'anio': ANIO, 'corte': self.corte})

        self.assertContains(tablero, 'alcanzan el 70 %')
        self.assertContains(tablero, 'bajo el mínimo')
        self.assertContains(tablero, 'El sistema comprueba los datos objetivos')


class DesignacionDesdeElDecanatoTests(BaseDelExpediente):
    """El decanato designa quién coordina cada laboratorio y recibe su informe."""

    # El menú del administrador comprueba también el alcance de Centros I+D.
    # Esa lectura debe usar su base aislada de pruebas cuando está separada.
    databases = {'default', 'centros'} if settings.CENTROS_DB_ENABLED else {'default'}

    def test_nombrar_receptor_le_da_el_acceso_que_necesita_y_nada_mas(self):
        nuevo = get_user_model().objects.create_user('otro-decano-recibe', password='clave-segura')
        self.assertFalse(nuevo.is_staff)

        self.decanato.receptores.add(nuevo)

        nuevo.refresh_from_db()
        self.assertTrue(nuevo.is_staff)
        self.assertTrue(nuevo.groups.filter(name='Recepción de informes de calidad').exists())
        permisos = set(nuevo.get_all_permissions())
        self.assertIn('directorio_unidades.view_dependenciaacademica', permisos)
        self.assertIn('documentos.view_documentoexpediente', permisos)
        # No se le abre la edición de unidades ni del catálogo.
        self.assertNotIn('directorio_unidades.change_unidad', permisos)
        self.assertNotIn('documentos.change_documentoexigido', permisos)

    def test_el_decanato_ve_solo_su_dependencia_y_designa_el_coordinador(self):
        otra = DependenciaAcademica.objects.create(nombre='Facultad ajena', tipo='decanato')
        self.client.force_login(self.decano)

        lista = self.client.get(reverse('admin:directorio_unidades_dependenciaacademica_changelist'))
        self.assertContains(lista, self.decanato.nombre)
        self.assertNotContains(lista, otra.nombre)
        self.assertEqual(self.client.get(
            reverse('admin:directorio_unidades_dependenciaacademica_change', args=[otra.pk])).status_code, 302)

        ficha = self.client.get(reverse('admin:directorio_unidades_dependenciaacademica_change', args=[self.decanato.pk]))
        self.assertContains(ficha, 'Unidades adscritas')
        self.assertContains(ficha, self.laboratorio.nombre)
        # Designa: el coordinador y las carreras se editan; el nombre de la unidad no.
        self.assertContains(ficha, 'unidades-0-administrador')
        self.assertContains(ficha, 'unidades-0-carreras')
        # Quién recibe el informe lo nombra la Dirección, no la dependencia.
        self.assertNotContains(ficha, 'name="receptores"')

    def test_el_expediente_dice_quien_coordina_quien_designa_y_quien_califica(self):
        self.client.force_login(self.coordinador)

        pagina = self.client.get(reverse('gestion_expediente_unidad', args=[self.laboratorio.slug]),
                                 {'anio': ANIO, 'corte': self.corte})

        self.assertContains(pagina, 'Coordina y envía')
        self.assertContains(pagina, 'lo designa Facultad de Industrias Agropecuarias y Ciencias Ambientales')
        self.assertContains(pagina, 'control automático y revisión de excepciones por Dirección')

    def test_la_migracion_crea_la_dependencia_desde_la_facultad_escrita(self):
        from importlib import import_module
        from types import SimpleNamespace

        modulo = import_module('apps.historial_modelos.migrations.0233_cadena_de_aprobacion')
        Unidad.objects.create(
            nombre='Planta con facultad', slug='planta-con-facultad', dependencia='plantas_piloto',
            descripcion='.', fecha_inicio=date(2024, 1, 1), activo=True, facultad='Facultad de Comercio')
        # Se prueba el RunPython sobre las tablas actuales, no un esquema
        # histórico sin columnas posteriores (por ejemplo centro_costo).
        modelos = {'Unidad': Unidad, 'DependenciaAcademica': DependenciaAcademica}
        apps = SimpleNamespace(get_model=lambda etiqueta, nombre: modelos[nombre])

        modulo.dependencias_desde_la_facultad(apps, None)

        planta = Unidad.objects.get(slug='planta-con-facultad')
        self.assertEqual(planta.adscrita_a.nombre, 'Facultad de Comercio')
        self.assertEqual(planta.adscrita_a.tipo, 'decanato')


class TableroPorTipoDeUnidadTests(BaseDelExpediente):
    """Cada tipo de unidad se lee en su bloque, con su propio indicador."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.planta = Unidad.objects.create(
            nombre='Planta piloto de prueba', slug='planta-piloto-tablero', dependencia='plantas_piloto',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1),
            administrador=cls.coordinador, activo=True, adscrita_a=cls.decanato)

    def mias(self, grupos):
        """Solo lo que esta prueba creó: la base de pruebas trae más unidades."""
        return {
            grupo['codigo']: [f['unidad'].slug for f in grupo['filas']
                              if f['unidad'].slug in {self.laboratorio.slug, self.suelto.slug,
                                                      self.planta.slug}]
            for grupo in grupos
        }

    def test_las_unidades_se_reparten_por_tipologia_con_su_indicador(self):
        filas, _totales = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.direccion)

        grupos = grupos_por_tipo(filas)

        repartidas = self.mias(grupos)
        self.assertIn(self.laboratorio.slug, repartidas['laboratorios'])
        self.assertIn(self.planta.slug, repartidas['plantas_piloto'])
        self.assertNotIn(self.planta.slug, repartidas['laboratorios'])
        # Cada grupo trae el indicador de los suyos, no el de todas las unidades.
        for grupo in grupos:
            self.assertEqual(grupo['totales']['unidades'], len(grupo['filas']))
            self.assertEqual(grupo['totales']['minimo'], 70)

    def test_la_pantalla_encabeza_cada_tipo_y_el_reporte_se_abre_en_el_visor(self):
        self.client.force_login(self.direccion)

        tablero = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                                  {'anio': ANIO, 'corte': self.corte})

        self.assertContains(tablero, 'Laboratorios')
        self.assertContains(tablero, 'Plantas Piloto')
        self.assertContains(tablero, 'Ver reporte')
        # El visor conserva el alcance filtrado y permite ajustar su rango.
        from re import search
        enlace = search(r'<a\b[^>]*class="[^"]*citt-cumplimiento__reporte[^"]*"[^>]*>',
                        tablero.content.decode()).group(0)
        self.assertIn('data-ver-pdf', enlace)
        self.assertIn('data-pdf-rango', enlace)
        self.assertNotIn('data-pdf-directo', enlace)
        self.assertNotIn('target=', enlace)

    def test_el_alcance_se_acota_por_tipo_y_por_unidad(self):
        filas, _t = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.direccion,
                                             dependencias=('plantas_piloto',))
        slugs = {fila['unidad'].slug for fila in filas}
        self.assertIn(self.planta.slug, slugs)
        self.assertNotIn(self.laboratorio.slug, slugs)

        filas, totales = cumplimiento_por_periodo(ANIO, self.corte, usuario=self.direccion,
                                                  solo_unidad=self.laboratorio.slug)

        self.assertEqual([fila['unidad'].slug for fila in filas], [self.laboratorio.slug])
        self.assertEqual(totales['unidades'], 1)

    def test_el_tramo_propio_deja_solo_lo_que_vence_dentro(self):
        fila = cumplimiento_de_unidad(self.laboratorio, ANIO, self.corte, HOY,
                                      desde=date(ANIO + 5, 1, 1), hasta=date(ANIO + 5, 12, 31))

        # Nada vence en un año futuro; queda lo que se exige sin plazo.
        con_plazo = [d for d in fila['documentos'] if d.vence_el]
        self.assertEqual(con_plazo, [])
        self.assertTrue(fila['documentos'])

    def test_la_pantalla_avisa_del_tramo_y_el_pdf_sale_con_el_alcance(self):
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        filtros = {'anio': ANIO, 'corte': self.corte, 'unidad': self.laboratorio.slug,
                   'desde': f'{ANIO}-01-01', 'hasta': f'{ANIO}-12-31'}

        tablero = self.client.get(url, filtros)
        self.assertContains(tablero, 'Tramo propio')
        # La planta sigue estando en el desplegable de unidades; lo que se acota es la lectura.
        self.assertEqual(
            [f['unidad'].slug for grupo in tablero.context['grupos'] for f in grupo['filas']],
            [self.laboratorio.slug])

        pdf = self.client.get(url, {**filtros, 'formato': 'pdf'})
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertIn('inline', pdf['Content-Disposition'])
        descarga = self.client.get(url, {**filtros, 'formato': 'pdf', 'download': '1'})
        self.assertIn('attachment', descarga['Content-Disposition'])
        self.assertTrue(descarga.content.startswith(b'%PDF'))
