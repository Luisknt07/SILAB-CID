"""Lectura de controles ya guardados: fuentes, filtros y presentación sin análisis."""
from decimal import Decimal
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.presentation.cumplimiento import _rastro, filtrar_bandeja_automatizacion
from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega


class ConformidadEstadoActualTests(SimpleTestCase):
    def documento(self):
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
        from apps.recursos.models.recursos import Recurso

        unidad = Unidad(pk=1, slug='unidad-del-plan')
        documento = DocumentoExpediente(pk=12, unidad=unidad,
            exigido=DocumentoExigido(pk=1, codigo='PLANIFICACION', requiere_firma=True),
            anio=2026, corte='B', version=2, estado='validado', firma_verificada=True,
            evaluacion=0, evaluacion_version=1, evaluacion_observacion='Antecedente conservado.')
        documento.recurso = Recurso(pk=5, unidad=unidad, version=2, activo=True,
            estado='vigente', archivo='plan-firmado.pdf', hash_sha256='a' * 64)
        documento.avance_redaccion = 100
        documento._conformidad_plan_registro = None
        documento.automatizacion = dict(vigente=True, aplicado=True, estado='automatico',
            resumen=dict(conformidad_documental={'alcance': 'conformidad_documental'}))
        return documento

    def test_redaccion_completa_y_observacion_vieja_no_sustituyen_archivo_ni_envio(self):
        from apps.documentos.presentation.conformidad_lectura import lectura_conformidad

        documento = self.documento()
        documento.estado, documento.recurso = 'observado', None
        lectura = lectura_conformidad(documento)
        self.assertEqual(documento.avance_redaccion, 100)
        self.assertEqual(lectura['estado'], 'corregir')
        self.assertFalse(lectura['fuente'])
        self.assertEqual(lectura['historica']['nota'], 0)
        self.assertEqual((documento.estado, documento.evaluacion), ('observado', 0))

    def test_conformidad_nativa_actual_no_se_define_con_nota_historica(self):
        from apps.documentos.presentation.conformidad_lectura import lectura_conformidad

        documento = self.documento()
        lectura = lectura_conformidad(documento)
        self.assertEqual((lectura['estado'], lectura['fuente']), ('conforme', 'Sistema'))
        self.assertEqual(lectura['historica']['observacion'], 'Antecedente conservado.')
        self.assertEqual((documento.evaluacion, documento.evaluacion_version), (0, 1))

    def test_la_firma_y_el_archivo_actual_son_necesarios_aunque_editor_y_control_esten_completos(self):
        from apps.documentos.presentation.conformidad_lectura import lectura_conformidad

        for campo, valor in (('firma_verificada', False), ('estado', 'cargado'), ('recurso', None)):
            with self.subTest(campo=campo):
                documento = self.documento()
                setattr(documento, campo, valor)
                self.assertNotEqual(lectura_conformidad(documento)['estado'], 'conforme')
                self.assertEqual(documento.evaluacion, 0)

    def test_plan_devuelto_sin_firma_muestra_su_paso_actual_sin_recalificar(self):
        from apps.documentos.presentation.conformidad_lectura import lectura_conformidad

        documento = self.documento()
        documento.estado, documento.firma_verificada = 'observado', False
        documento.automatizacion = dict(estado='desactualizado', vigente=False, aplicado=False)
        conformidad = lectura_conformidad(documento)
        lectura = resumen_de_entrega(documento)
        self.assertEqual(lectura['estado_unidad'], 'Falta firmar y reenviar')
        self.assertEqual((lectura['grupo'], lectura['grupo_visual']), ('observados', 'pendientes'))
        self.assertEqual(lectura['paso_unidad'], 'Falta firmar y reenviar')
        self.assertIn('El porcentaje del editor mide apartados redactados', conformidad['explicacion'])
        self.assertIn('aplica la conformidad automática si pasan sus reglas', conformidad['explicacion'])
        self.assertIn('consúltalas en Observaciones', conformidad['explicacion'])
        html = render_to_string('portal/pages/unidades/gestion/includes/resultado_documental.html',
            dict(lectura=lectura, nombre_documento='Planificación semestral'))
        actual = html.split('<template', 1)[0]
        self.assertIn('Falta firmar y reenviar', actual)
        self.assertIn('is-amarillo', actual)
        self.assertNotIn('0 %', actual)
        self.assertIn('Calificación histórica registrada: 0 %', html)
        modal = render_to_string('admin/gestion_unidades/reporteoperativounidad/revision_conformidad.html',
            dict(revision=dict(documento=documento, conformidad=conformidad, permanente=False,
                modalidad='conformidad', conforme=False, aprobacion={}, recibible=False, evaluable=False,
                control=documento.automatizacion), user=SimpleNamespace(is_superuser=True)))
        self.assertIn('Falta firmar y reenviar', modal)
        self.assertIn('El archivo actual aún no tiene la firma comprobada', modal)
        self.assertNotIn('name="accion" value="confirmar_conformidad"', modal)
        self.assertNotIn('Consulta el archivo y los hallazgos del sistema antes de confirmar', modal)
        self.assertEqual((documento.estado, documento.version, documento.evaluacion), ('observado', 2, 0))

    def test_una_incidencia_vigente_no_se_oculta_tras_pendiente_de_firma(self):
        from apps.documentos.presentation.conformidad_lectura import lectura_conformidad

        documento = self.documento()
        documento.estado, documento.firma_verificada = 'observado', False
        documento.automatizacion = dict(estado='bloqueado', vigente=True, aplicado=False,
            hallazgos=[dict(regla='archivo_modificado', severidad='bloqueo', mensaje='La huella cambió.')])
        etapa = lectura_conformidad(documento)['etapa_actual']
        self.assertEqual((etapa['codigo'], etapa['color']), ('incidencia', 'rojo'))
        self.assertFalse(etapa['pendiente_unidad'])


class AutomatizacionDocumentalInterfazTests(SimpleTestCase):
    def documento(self, **cambios):
        datos = dict(estado='validado', nota=Decimal('80.00'), evaluacion=None,
            version=2, evaluacion_version=None, exigido=SimpleNamespace(es_anexo=False, codigo='INFORME-SEMESTRAL', periodicidad='semestral'),
            evaluado_por_id=None, recibido_por_id=None, incumplimiento_procesado_hasta=None,
            integridad_documental=dict(aplica=True, correspondencia_verificada=True),
            automatizacion=dict(estado='automatico', vigente=True, aplicado=True,
                nota=Decimal('80.00'), resumen=dict(recepcion_automatica=True), hallazgos=[]),
            recibido_en=None, plazo_entrega=None, prorroga_hasta=None, correccion_hasta=None,
            ultimatum_hasta=None, recurso_id=1, observacion='', evaluacion_observacion='',
            evaluacion_debilidades='', tardanza_motivo='', evaluado_en=None,
            validado_en=None, cumple=True)
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_resultado_y_recepcion_identifican_fuente_sistema_sin_consultar(self):
        # SimpleTestCase rechaza cualquier acceso a la base de datos.
        d = self.documento()
        lectura = resumen_de_entrega(d)
        self.assertEqual((lectura['nota'], lectura['fuente_nota_etiqueta']), (Decimal('80.00'), 'Sistema'))
        self.assertEqual(lectura['fuente_recepcion'], 'Sistema')
        self.assertIsNone(d.evaluacion)
        # Una evaluación vieja no se atribuye a la versión automática actual.
        anterior = self.documento(evaluacion=90, evaluacion_version=1, evaluado_por_id=7)
        self.assertEqual(resumen_de_entrega(anterior)['fuente_nota_etiqueta'], 'Sistema')
        d.automatizacion['resumen']['aprobacion_reutilizada'] = dict(anio=2025)
        self.assertEqual(resumen_de_entrega(d)['fuente_nota_etiqueta'], 'Dirección · aprobación previa')

    def test_nota_humana_se_conserva_con_su_fuente_aunque_exista_control(self):
        d = self.documento(nota=90, evaluacion=90, evaluacion_version=2, evaluado_por_id=7)
        lectura = resumen_de_entrega(d)
        self.assertEqual((lectura['nota'], lectura['fuente_nota_etiqueta']), (90, 'Dirección'))
        self.assertTrue(lectura['evaluacion_humana_vigente'])
        self.assertEqual(d.automatizacion['nota'], Decimal('80.00'))

    def test_rastro_distingue_control_sistema_autor_humano_y_legado_sin_consultar(self):
        from django.utils import timezone

        ahora = timezone.now()
        d = self.documento(cargado_en=None, generado_en=None, tardanza_pedida_en=None,
            tardanza_habilitada_en=None, validado_en=ahora, validado_por_id=None,
            recibido_en=ahora, recurso_id=None)
        pasos = _rastro(d)
        self.assertTrue(any('Validación automática: Sistema' in paso for paso in pasos))
        self.assertTrue(any('Recepción técnica: Sistema' in paso for paso in pasos))
        self.assertIn('Resultado: Sistema · 80.00 %', pasos)
        self.assertFalse(any('Dirección:' in paso for paso in pasos))

        # Incluso con un control aplicado, el actor humano explícito conserva su autoría.
        humano = SimpleNamespace(get_full_name=lambda: 'Directora de prueba', get_username=lambda: 'direccion')
        d.validado_por_id = d.recibido_por_id = d.evaluado_por_id = 7
        d.validado_por = d.recibido_por = d.evaluado_por = humano
        d.evaluacion, d.evaluacion_version, d.evaluado_en = 90, d.version, ahora
        pasos = _rastro(d)
        self.assertTrue(any('Validó Directora de prueba' in paso for paso in pasos))
        self.assertTrue(any('Recibió la Dirección: Directora de prueba' in paso for paso in pasos))
        self.assertTrue(any('Calificó Directora de prueba' in paso for paso in pasos))
        self.assertFalse(any('Resultado: Sistema' in paso for paso in pasos))

        d.validado_por_id = d.recibido_por_id = d.evaluado_por_id = None
        d.automatizacion = {}
        pasos = _rastro(d)
        self.assertTrue(any('Validación registrada sin autor' in paso for paso in pasos))
        self.assertTrue(any('Recepción registrada sin autor' in paso for paso in pasos))
        self.assertFalse(any('Sistema' in paso or 'el sistema' in paso for paso in pasos))

    def test_bandeja_usa_vigencia_y_no_recorta_el_avance_general(self):
        humano = dict(evaluacion=90, evaluacion_version=2, evaluado_por_id=7)
        casos = [
            ('automatico', True, {}, [], 'automatico'),
            ('revision', True, {}, [], 'excepciones'),
            ('bloqueado', True, {}, [], 'excepciones'),
            ('sin_archivo', True, dict(estado='pendiente'), [], 'unidad'),
            ('revision', True, dict(estado='observado', **humano), [], 'unidad'),
            ('bloqueado', True, dict(estado='generado'), [], 'unidad'),
            ('automatico', False, {}, [], 'sin_analizar'),
            ('revision', True, humano, [dict(regla='criterio_humano')], ''),
            ('bloqueado', True, humano, [dict(regla='cierre_incompleto', severidad='bloqueo')], ''),
            ('bloqueado', True, humano, [dict(regla='anexo_modificado', severidad='bloqueo')], 'excepciones'),
            ('revision', True, dict(evaluacion=90, evaluacion_version=1, evaluado_por_id=7), [], 'excepciones'),
            ('bloqueado', True, dict(exigido=SimpleNamespace(es_anexo=True, codigo='ANEXO-PRUEBA', periodicidad='semestral')), [], ''),
            ('sin_archivo', True, {}, [], ''),
            ('revision', False, dict(estado='pendiente'), [], 'sin_analizar'),
        ]
        casillas = []
        for indice, (estado, vigente, cambios, hallazgos, esperado) in enumerate(casos):
            control = dict(estado=estado, vigente=vigente, hallazgos=hallazgos)
            d = self.documento(automatizacion=control, **cambios)
            d.resumen_interfaz = dict(laboratorio=True, automatizacion=control)
            casilla = dict(documento=d)
            casillas.append(casilla)
            for filtro in ('excepciones', 'unidad', 'automatico', 'sin_analizar'):
                with self.subTest(caso=indice, filtro=filtro):
                    self.assertEqual(bool(filtrar_bandeja_automatizacion([dict(matriz=[casilla])], filtro)),
                                     esperado == filtro)
        extra = self.documento()
        extra.resumen_interfaz = dict(laboratorio=False)
        casillas.append(dict(documento=extra))
        avance = dict(total=len(casos), porcentaje=16)
        fila = dict(matriz=casillas, progreso_general=avance)
        for filtro, cantidad in [('excepciones', 4), ('unidad', 3), ('automatico', 1), ('sin_analizar', 2)]:
            with self.subTest(filtro=filtro):
                visibles = filtrar_bandeja_automatizacion([fila], filtro)
                self.assertEqual(len(visibles[0]['matriz']), cantidad)
                self.assertIs(visibles[0]['progreso_general'], avance)
        self.assertEqual(len(fila['matriz']), len(casos) + 1)

    def test_control_aplicado_muestra_hallazgos_sin_links_de_esquema_ajeno(self):
        control = dict(estado='automatico', vigente=True, aplicado=True,
            hallazgos=[dict(mensaje='Comprobación identificada.', url='javascript:alert(1)')])
        html = render_to_string('portal/pages/unidades/gestion/includes/control_automatico.html',
                                dict(control=control))
        self.assertIn('Validado automáticamente', html)
        self.assertIn('Comprobación identificada.', html)
        self.assertNotIn('javascript:', html)
        control['resumen'] = dict(aprobacion_reutilizada=dict(anio=2025))
        html = render_to_string('portal/pages/unidades/gestion/includes/control_automatico.html',
                                dict(control=control))
        self.assertIn('Aprobación de Dirección conservada', html)
        self.assertNotIn('Validado automáticamente', html)

        # Un anexo validado por el motor no inventa un revisor de la unidad.
        control.pop('resumen')
        anexo = SimpleNamespace(pk=1, estado='validado', recurso=SimpleNamespace(pk=1),
            exigido=SimpleNamespace(get_carpeta_display='Planificación'), version=1,
            nombre_documental='Anexo de prueba', automatizacion=control, validado_por=None)
        contexto = dict(unidad=SimpleNamespace(codigo_base='laboratorios'), solo_lectura=True,
            entrega=SimpleNamespace(documento=SimpleNamespace(pk=2), nombre='Planificación',
                anexos=[anexo], anexos_validados=1), periodo=SimpleNamespace(etiqueta='2026-B'))
        html = render_to_string('portal/pages/unidades/gestion/includes/expediente_anexos.html', contexto)
        self.assertIn('Validado automáticamente', html)
        self.assertNotIn('Revisado por la unidad', html)

        self.assertIn('El sistema comprueba y valida los anexos conformes', html)
        contexto['unidad'].codigo_base = 'observatorios'
        html = render_to_string('portal/pages/unidades/gestion/includes/expediente_anexos.html', contexto)
        self.assertNotIn('Revisado por la unidad', html)
        self.assertIn('Validado automáticamente', html)

    def test_el_calculo_no_acreditado_se_identifica_como_provisional_sin_ocultar_metas(self):
        base = dict(nota=Decimal(0), avance_metas=Decimal('16.67'), filas=[],
            alertas=[], congelado=True, provisional=False, demostracion=False,
            completo=True, plan_aprobado=True)
        for cambios in (dict(congelado=False), dict(provisional=True),
                dict(demostracion=True), dict(completo=False), dict(plan_aprobado=False)):
            with self.subTest(cambios=cambios):
                html = render_to_string('portal/pages/unidades/gestion/includes/cumplimiento_cierre.html',
                    dict(cierre={**base, **cambios}, anexos=[]))
                self.assertIn('Cálculo provisional', html)
                self.assertIn('no es una nota acreditada', html)
                self.assertNotIn('Nota calculada del cierre', html)
                self.assertIn('aria-label="Avance de las metas"', html)
                self.assertIn('value="16.67"', html)
        html = render_to_string('portal/pages/unidades/gestion/includes/cumplimiento_cierre.html',
            dict(cierre=base, anexos=[]))
        self.assertIn('Resultado archivado del cierre', html)
        self.assertNotIn('Cálculo provisional', html)

    def test_control_modal_conserva_resumen_breve_y_trazabilidad_completa(self):
        from django.utils import timezone

        control = dict(estado='bloqueado', vigente=True, aplicado=False,
            comprobado_en=timezone.now(),
            hallazgos=[dict(mensaje=f'Comprobación {i}', url='/registro/') for i in range(140)])
        html = render_to_string('portal/pages/unidades/gestion/includes/control_automatico.html',
                                dict(control=control))
        resumen = html.split('<button', 1)[1].split('</button>', 1)[0]
        self.assertIn('Con bloqueos', resumen)
        self.assertIn('140 comprobaciones', resumen)
        self.assertNotIn('Control: Sistema', resumen)
        self.assertNotIn('Ver comprobaciones (140)', resumen)
        self.assertIn('aria-haspopup="dialog"', resumen)
        self.assertIn('<template data-reporte-informacion-contenido>', html)
        contenido = html.split('class="control-documental__contenido"', 1)[1]
        self.assertIn('Control: Sistema', contenido)
        self.assertIn('Comprobaciones (140)', contenido)
        self.assertIn('Comprobación 139', contenido)
        self.assertNotIn('<details', html)
        self.assertEqual(html.count('data-reporte-informacion-abrir'), 1)

    def test_anexo_muestra_control_una_vez_en_detalle_y_documento_solo_abre_pdf(self):
        control = dict(estado='revision', vigente=True, aplicado=False,
                       hallazgos=[dict(mensaje='Revisión técnica pendiente.')])
        indicador = dict(codigo='seguridad', exigencia='Obligatorio institucional',
            indicador='Inducciones documentadas', meta='100 %', registrado=0,
            estado='No cumple', porcentaje=None)
        html = render_to_string('portal/pages/unidades/gestion/includes/anexo_cierre_fila.html', dict(
            unidad=SimpleNamespace(codigo_base='laboratorios'),
            anexo=SimpleNamespace(pk=1, automatizacion=control), indicadores=[indicador, indicador],
            modo_admin=True, recurso=7, nombre='Seguridad', numero_item=1))
        self.assertEqual(html.count('data-control-documental='), 1)
        detalle = html.index('<td class="cierre-detalle">')
        control_posicion = html.index('data-control-documental=')
        documento = html.index('<td rowspan="2">', detalle)
        self.assertLess(detalle, control_posicion)
        self.assertLess(control_posicion, documento)
        self.assertIn('data-ver-pdf', html[documento:])
        self.assertNotIn('data-control-documental=', html[documento:])

    def test_resultado_conserva_fuente_visible_y_revision_en_contenido_modal(self):
        from django.utils import timezone

        d = self.documento(pk=1, numero_item=1, nombre_documental='Informe de prueba',
            etiqueta_corte='2026-B', anio=2026, corte='B',
            exigido=SimpleNamespace(redactable=False, generable=False),
            aporte_cumplimiento=dict(tipo='cierre', puntua=True,
                resultado_porcentaje=80, aporte=80, maximo=100))
        lectura = resumen_de_entrega(d)
        lectura.update(laboratorio=True, fuente_nota_etiqueta='Sistema',
                       fecha_revision=timezone.now(), tipo_revision='Control automático')
        d.resumen_interfaz = lectura
        html = render_to_string('portal/pages/unidades/gestion/includes/expediente_fila.html',
            dict(documento=d, unidad=SimpleNamespace(slug='fablab'), anio=2026, corte='B', solo_lectura=True))
        self.assertNotIn('class="entregas__resultado-detalle"', html)
        contenido = html.split('<template data-reporte-informacion-contenido>', 1)[1].split('</template>', 1)[0]
        self.assertIn('Fuente del resultado: Sistema', contenido)
        self.assertIn('Resultado del cierre: 80,00 %', contenido)
        self.assertIn('Los documentos administrativos no agregan puntos', contenido)
        self.assertIn('Revisión:', contenido)

    def test_respaldo_integrado_conserva_estado_y_no_inventa_revision_humana(self):
        anexo = SimpleNamespace(pk=7, nombre_documental='Planificación por asignatura',
            exigido=SimpleNamespace(codigo='INDICADORES-PLAN'), recurso_id=7,
            soporte_planificacion=dict(url='/expediente/?gestionar=2', descripcion='Origen de prácticas'),
            url_informe='', generado_en=None, avance_documental={},
            estado='generado', automatizacion={})
        contexto = dict(soporte=anexo, periodo=SimpleNamespace(etiqueta='2026-B'))
        plantilla = 'portal/pages/unidades/gestion/includes/expediente_fila_soporte.html'
        html = render_to_string(plantilla, contexto)
        self.assertIn('is-amarillo', html)
        self.assertIn('Por revisar', html)
        self.assertIn('data-ver-pdf', html)
        self.assertIn('Anexo de planificación', html)
        self.assertNotIn('target="_blank"', html)
        anexo.estado = 'validado'
        html = render_to_string(plantilla, contexto)
        self.assertIn('is-verde', html)
        self.assertIn('Revisado por la unidad', html)
        anexo.automatizacion = dict(estado='automatico', vigente=True, aplicado=True, hallazgos=[])
        html = render_to_string(plantilla, contexto)
        self.assertIn('Validado automáticamente', html)
        self.assertNotIn('Revisado por la unidad', html)
