"""Desempeño del cierre, requisitos y ausencia de actividad al final del ciclo."""

from datetime import date

from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.documentos.presentation.expediente import construir_expediente, cortes_del_anio
from apps.documentos.presentation.mejora_continua import cumplimiento_del_periodo, generar_informe_de_mejora, informe_archivado
from tests.integration.test_cumplimiento_expediente import BaseDeCumplimiento
from tests.integration.utiles import abrir_entrega, evaluar_documento_revisado as evaluar_documento


class NivelDeCumplimientoTests(BaseDeCumplimiento):
    def test_la_unidad_y_direccion_comparten_documentos_estados_y_resultado(self):
        from apps.documentos.presentation.cumplimiento import cumplimiento_de_unidad
        hoy = date(2026, 9, 26)
        unidad = cumplimiento_del_periodo(self.laboratorio, 2026, 'A', hoy=hoy)
        direccion = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=hoy)
        self.assertEqual(unidad['total'], direccion['nivel']['total'])
        self.assertEqual([f['documento'].pk for f in unidad['filas']],
                         [f['documento'].pk for f in direccion['matriz']])
        for local, central in zip(unidad['filas'], direccion['matriz']):
            for campo in ('enviado', 'recibido', 'evaluado', 'observacion', 'rastro'):
                self.assertEqual(local[campo], central[campo])

    def test_periodo_futuro_no_exige_mejora_por_ausencia_de_uso(self):
        datos = cumplimiento_del_periodo(self.laboratorio, 2027, 'A', hoy=date(2026, 9, 25))
        self.assertTrue(datos['sin_uso'])
        self.assertFalse(datos['periodo_iniciado'])
        self.assertFalse(datos['requiere_mejora'])
        with self.assertRaises(ValidationError):
            generar_informe_de_mejora(self.laboratorio, 2027, 'A', self.direccion, hoy=date(2026, 9, 25))

    def test_borrador_vencido_es_faltante_documental_sin_inventar_nota_cero(self):
        from apps.documentos.presentation.cumplimiento import _nivel_evaluado
        from apps.documentos.presentation.mejora_continua import _nota

        documento, url = self.enviar('INFORME-SEMESTRAL')
        documento.estado = 'generado'
        documento.firma_verificada = False
        documento.vence_el = date(2026, 6, 1)
        documento.save(update_fields=['estado', 'firma_verificada', 'vence_el'])
        hoy = date(2026, 9, 22)
        self.assertIsNone(_nota(documento, hoy))
        self.assertIsNone(_nivel_evaluado([documento], hoy)['total'])
        self.assertIsNone(_nota(documento, date(2026, 5, 1)))
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        self.assertContains(pagina, reverse('redactar_documento_expediente',
                                           args=[self.laboratorio.slug, documento.pk]))
        self.assertContains(pagina, 'data-entrega-editor')
        self.assertContains(pagina, 'Borrador')
        self.assertContains(pagina, 'Documentos obligatorios')
        self.assertNotContains(pagina, 'sin puntuar')
        documento.estado = 'validado'
        documento.firma_verificada = True
        self.assertIsNone(_nota(documento, hoy))
        documento.save(update_fields=['estado', 'firma_verificada'])
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        fila = next(f for f in pagina.context['cumplimiento']['filas']
                    if f['documento'].pk == documento.pk)
        self.assertEqual(fila['pendiente'], 'Correspondencia por revisar por Dirección')
        self.assertContains(pagina, 'Pendiente de revisión')

    def enviar(self, codigo, corte='A'):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == codigo and d.corte == corte)
        self.firmar_y_cargar(url, documento, corte)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})
        documento.refresh_from_db()
        return documento, url

    def test_la_nota_historica_no_acredita_desempeno_sin_el_plan_del_semestre(self):
        informe, _url = self.enviar('INFORME-SEMESTRAL')
        evaluar_documento(informe, self.direccion, 90, 'Completo.')

        nivel = cumplimiento_del_periodo(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        por_codigo = {f['documento'].exigido.codigo: f for f in nivel['filas']}
        self.assertIsNone(por_codigo['INFORME-SEMESTRAL']['nota'])
        self.assertFalse(por_codigo['INFORME-SEMESTRAL']['evaluado'])
        self.assertEqual(nivel['total_registrado'], 90)
        # El plan faltante es un requisito pendiente, sin calificación artificial.
        self.assertIsNone(por_codigo['PLANIFICACION']['nota'])
        self.assertFalse(por_codigo['PLANIFICACION']['evaluado'])
        # Lo que todavía no vence ni se evaluó no puntúa.
        self.assertIsNone(por_codigo['RESOLUCION-CREACION']['nota'])
        self.assertIsNone(nivel['total'])
        self.assertEqual(nivel['minimo'], 70)

    def test_bajo_el_minimo_o_sin_uso_se_abre_la_mejora_continua(self):
        informe, _url = self.enviar('INFORME-SEMESTRAL')
        evaluar_documento(informe, self.direccion, 100, 'Completo.')

        nivel = cumplimiento_del_periodo(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        # No se inventa una nota insuficiente promediando el plan ausente.
        self.assertFalse(nivel['bajo_minimo'])
        self.assertIsNone(nivel['total'])
        self.assertEqual(nivel['semaforo'], 'sin_uso')
        self.assertEqual(nivel['etiqueta'], 'Sin actividad efectiva al cierre')
        # El semestre ya cerró y una unidad existente no acredita actividad efectiva.
        self.assertTrue(nivel['sin_uso'])
        self.assertTrue(nivel['requiere_mejora'])
        self.assertFalse(nivel['incumplidos'])

    def test_la_pantalla_muestra_el_nivel_por_documento_el_total_y_el_uso(self):
        informe, url = self.enviar('INFORME-SEMESTRAL')
        evaluar_documento(informe, self.direccion, 90, 'Completo.', debilidades='Faltan guías.',
                          recomendaciones='Actualizar dos guías.')

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        self.assertContains(pagina, 'Resultado operativo')
        self.assertIsNone(pagina.context['cumplimiento']['total'])
        self.assertEqual(pagina.context['cumplimiento']['total_registrado'], 90)
        self.assertTrue(pagina.context['cumplimiento']['requiere_mejora'])
        self.assertContains(pagina, 'Generar informe de mejora')
        self.assertTrue(any(f['pendiente'] == 'Pendiente de entrega obligatoria'
                            for f in pagina.context['cumplimiento']['filas']))
        self.assertContains(pagina, 'data-entrega-editor')
        self.assertEqual(pagina.context['cumplimiento']['minimo'], 70)


class InformeDeMejoraContinuaTests(BaseDeCumplimiento):
    def test_el_informe_se_produce_y_se_archiva_para_el_decanato(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documentos = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        plan = next(d for d in documentos if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'A')

        respuesta = self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': plan.pk, 'accion': 'mejora'},
                                     follow=True)

        self.assertContains(respuesta, 'Informe de mejora continua archivado')
        recurso = informe_archivado(self.laboratorio, 2026, 'A')
        self.assertIsNotNone(recurso)
        self.assertEqual(recurso.version, 1)
        self.assertTrue(recurso.archivo.read().startswith(b'%PDF'))
        self.assertEqual(recurso.carpeta.nombre, 'Mejora continua')
        self.assertIn('mínimo', recurso.descripcion)
        self.assertContains(respuesta, 'Ver informe')

        # Regenerar sube la versión y deja obsoleta la anterior.
        self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': plan.pk, 'accion': 'mejora'})
        nuevo = informe_archivado(self.laboratorio, 2026, 'A')
        self.assertEqual(nuevo.version, 2)
        self.assertEqual(nuevo.reemplaza_a_id, recurso.pk)

    def test_no_se_informa_un_incumplimiento_que_no_existe(self):
        from apps.documentos.presentation import mejora_continua

        nivel = mejora_continua.cumplimiento_del_periodo(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        nivel['requiere_mejora'] = False
        original = mejora_continua.cumplimiento_del_periodo
        mejora_continua.cumplimiento_del_periodo = lambda *a, **k: nivel
        try:
            with self.assertRaises(ValidationError) as contexto:
                generar_informe_de_mejora(self.laboratorio, 2026, 'A', self.coordinador)
        finally:
            mejora_continua.cumplimiento_del_periodo = original
        self.assertIn('dictamen obligatorio', ' '.join(contexto.exception.messages))

    def test_el_tablero_de_la_direccion_muestra_el_nivel_evaluado(self):
        from apps.documentos.presentation.cumplimiento import cumplimiento_de_unidad

        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        informe = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')
        self.firmar_y_cargar(url, informe)
        self.client.post(url, {'anio': 2026, 'documento': informe.pk, 'accion': 'validar'})
        informe.refresh_from_db()
        evaluar_documento(informe, self.direccion, 80, 'Bien.')

        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        self.assertIsNone(fila['nivel']['total'])
        self.assertEqual(fila['nivel']['total_registrado'], 80)
        self.assertEqual(fila['nivel']['minimo'], 70)
        self.client.force_login(self.direccion)
        tablero = self.client.get(reverse('admin:reportes-cumplimiento-expediente'), {'anio': 2026, 'corte': 'A'})
        self.assertContains(tablero, 'Resultado del cierre pendiente')


class RangoEnElVisorTests(BaseDeCumplimiento):
    def test_el_rango_se_cambia_en_el_visor_sin_salir_del_expediente(self):
        """Una sola acción por anexo: verlo. El rango de fechas va en el visor."""
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        cortes = cortes_del_anio(2026)

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        pdf = reverse('gestion_reporte_unidad_pdf', args=[self.laboratorio.slug])
        contenido = pagina.content.decode()
        # El visor recibe la dirección del informe y el rango del período.
        # Las evidencias de guías conservan el documento y período definidos;
        # los informes de consulta permiten variar el rango en el visor.
        self.assertIn('anexo=GUIAS&amp;borrador=1', contenido)
        self.assertIn('data-ver-pdf', contenido)
        self.assertIn(f'data-pdf-desde="{cortes["A"][0]}" data-pdf-hasta="{cortes["A"][1]}"', contenido)
        self.assertIn(f'data-pdf-rango="{pdf}?categoria_reporte=aula"', contenido)
        # Y ya no saca a nadie a otra pantalla ni repite botones.
        self.assertNotIn('Otras fechas', contenido)
        self.assertNotIn('Informe al día', contenido)
        self.assertEqual(contenido.count('Revisado, validar'), 0)

    def test_cada_anexo_dice_si_falta_validarlo_o_ya_esta_validado(self):
        from apps.documentos.models.expediente import DocumentoExigido
        from apps.documentos.presentation.expediente import anexos_del, generar_anexos, validar_anexo

        # El catálogo distribuido no da anexos al plan (documentos.0024); uno institucional sí se presenta con él.
        DocumentoExigido.objects.create(codigo='SOPORTE-PLAN-PROPIO', nombre='Respaldo propio de la planificación',
            carpeta='planeacion', periodicidad='semestral', origen='sistema', fuente_reporte='asignaturas',
            plazo_regla='inicio', plazo_dias=15, orden=30,
            anexo_de=DocumentoExigido.objects.get(codigo='PLANIFICACION'))
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        informe = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'A')
        abrir_entrega(informe)
        generar_anexos(informe, self.coordinador)
        informe.refresh_from_db()

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        # El respaldo aparece con los anexos, conservando su vínculo,
        # estado de revisión y archivo.
        entrega_plan = next(e for e in pagina.context['periodos'][0]['entregas']
                            if e['documento'].exigido.codigo == 'PLANIFICACION')
        anexo_plan = next(a for a in entrega_plan['anexos_integrados'] if a.recurso_id)
        contenido = pagina.content.decode()
        fila_integrada = contenido.split(
            f'data-soporte-planificacion="{anexo_plan.exigido.codigo}"', 1)[1].split('</tr>', 1)[0]
        self.assertIn('Por revisar', fila_integrada)
        self.assertIn('data-control-documental="revision"', fila_integrada)
        self.assertIn('data-ver-pdf', fila_integrada)
        self.assertIn('los anexos no agregan puntos', contenido)
        self.assertNotIn('target="_blank"', fila_integrada)

        # Se validan los anexos de las dos entregas del período: planificación e informe.
        for entrega in self.client.get(url, {'anio': 2026, 'corte': 'A'}).context['periodos'][0]['entregas']:
            for anexo in anexos_del(entrega['documento']):
                if anexo.recurso_id:
                    validar_anexo(anexo, self.coordinador)
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        contenido = pagina.content.decode()
        fila_integrada = contenido.split(
            f'data-soporte-planificacion="{anexo_plan.exigido.codigo}"', 1)[1].split('</tr>', 1)[0]
        # Revisar manualmente el archivo no resuelve las excepciones del
        # control del sistema ni acredita actividades o puntos independientes.
        self.assertIn('Por revisar', fila_integrada)
        self.assertIn('data-control-documental="revision"', fila_integrada)
        # Las incidencias automáticas de otros documentos no desaparecen por
        # marcar estos anexos como revisados manualmente.
        anexos_con_archivo = [a for e in pagina.context['periodos'][0]['entregas']
                             for a in e['anexos'] if a.recurso_id]
        self.assertTrue(all(a.estado == 'validado' for a in anexos_con_archivo))

    def test_al_abrir_el_informe_los_filtros_traen_el_periodo_y_admiten_otro_rango(self):
        from apps.documentos.presentation.expediente import cortes_del_anio, periodo_vigente
        from django.utils import timezone

        self.client.force_login(self.coordinador)
        panel = self.client.get(reverse('gestion_unidad', args=[self.laboratorio.slug]),
                                {'view': 'reportes', 'categoria_reporte': 'guias'})

        hoy = timezone.localdate()
        inicio, fin = cortes_del_anio(hoy.year)[periodo_vigente(cortes_del_anio(hoy.year), hoy)]
        self.assertContains(panel, f'name="desde" value="{inicio}"')
        self.assertContains(panel, f'name="hasta" value="{fin}"')
        self.assertContains(panel, 'por omisión, el período vigente')

        # Y con fechas propias manda lo que se pidió.
        semana = self.client.get(reverse('gestion_unidad', args=[self.laboratorio.slug]),
                                 {'view': 'reportes', 'categoria_reporte': 'guias',
                                  'desde': '2026-03-02', 'hasta': '2026-03-08'})
        reporte = semana.context['reporte_gestion']
        self.assertEqual((str(reporte['start_date']), str(reporte['end_date'])), ('2026-03-02', '2026-03-08'))
