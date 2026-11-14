"""Publicación respaldada y solicitudes contextualizadas de investigación y transferencia."""
from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, router, transaction
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.contenidos import Contenidos
from apps.centros_id.formularios import SolicitudForm
from apps.centros_id.models import (
    AjusteSeccion, Aliado, CasoExito, CentroID, HitoProyecto, Integrante, Proyecto, Resultado, SolicitudCentro,
    normalizar_doi,
)


class InvestigacionTransferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.otro = CentroID.objects.create(nombre='Otro centro', sigla='OTRO', slug='otro-centro')
        cls.usuario = get_user_model().objects.create_user('investigacion.usuario')
        cls.gestor = get_user_model().objects.create_user('investigacion.gestor', is_staff=True)
        cls.centro.gestores.add(cls.gestor)
        cls.hoy = timezone.localdate()
        cls.linea = cls.centro.lineas.first()
        cls.proyecto = Proyecto.objects.create(centro=cls.centro, titulo='Proyecto trazable', resumen='Investigación real',
                                              linea=cls.linea, estado='ejecucion', sector='Agro', inicio=cls.hoy)
        cls.resultado = Resultado.objects.create(centro=cls.centro, titulo='Datos de investigación', tipo='dato',
                                                anio=cls.hoy.year, proyecto=cls.proyecto, doi='10.1234/DATOS',
                                                enlace='https://example.org/datos', version='1.0')
        cls.desarrollo = Resultado.objects.create(centro=cls.centro, titulo='Sensor experimental', tipo='prototipo',
                                                 anio=cls.hoy.year, proyecto=cls.proyecto, sector='Agro', tecnologia='IoT')

    def seccion(self, clave, **parametros):
        return self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, clave]), parametros)

    def fragmento(self, tipo, objeto):
        return self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, tipo, objeto.pk]))

    def exportar(self, **parametros):
        return self.client.get(reverse('exportar_resultados_centro_id', args=[self.centro.slug]), parametros)

    def caso(self, **extras):
        datos = dict(centro=self.centro, titulo='Adopción del sensor', beneficiario='Asociación receptora',
                     reto='Monitorear', solucion='Instrumentación', resultado='Ahorro del 30%', anio=self.hoy.year,
                     proyecto=self.proyecto, desarrollo=self.desarrollo)
        datos.update(extras)
        return CasoExito.objects.create(**datos)

    def documentar_caso(self, caso):
        caso.receptor = 'Asociación receptora'
        caso.mecanismo = 'Licencia y capacitación'
        caso.fecha_transferencia = self.hoy
        caso.evidencia = 'Acta de aceptación 01'
        caso.autorizacion_publicacion = 'Autorización de la asociación'
        caso.save()

    def datos_solicitud(self, **extras):
        datos = dict(tipo='reto', perfil='externo', titulo='Colaborar', problema='Validar en campo',
                     resultado_esperado='Informe', finalidad='codesarrollo', proyecto=self.proyecto.pk,
                     desarrollo=self.desarrollo.pk)
        datos.update(extras)
        return datos

    def test_linea_explica_agenda_y_relaciona_resultados_reales(self):
        self.linea.problema = 'Problema científico verificable'
        self.linea.objetivos = 'Objetivos específicos'
        self.linea.preguntas = 'Pregunta científica'
        self.linea.metodologia = 'Diseño experimental'
        self.linea.save()
        pagina = self.fragmento('linea', self.linea)
        for texto in (self.linea.problema, self.linea.objetivos, self.linea.preguntas, self.linea.metodologia,
                      self.proyecto.titulo, self.resultado.titulo):
            self.assertContains(pagina, texto)
        self.assertNotContains(self.seccion('lineas', q='sin coincidencias'), self.linea.nombre)

    def test_linea_no_divulga_responsable_en_formacion_y_valida_centro(self):
        persona = Integrante.objects.create(centro=self.centro, nombre='Nombre reservado de tesista', rol='tesista')
        self.linea.responsable = persona
        self.linea.save()
        self.assertNotContains(self.fragmento('linea', self.linea), persona.nombre)
        persona.centro = self.otro
        persona.save()
        with self.assertRaises(ValidationError):
            self.linea.full_clean()

    def test_avance_se_publica_con_respaldo_incluso_si_es_cero(self):
        self.proyecto.avance = 37
        self.proyecto.save()
        self.assertNotContains(self.fragmento('proyecto', self.proyecto), '37%')
        self.assertNotContains(self.seccion('proyectos'), '37%')
        self.proyecto.avance = 0
        self.proyecto.avance_metodo = 'Hitos ponderados'
        self.proyecto.avance_fecha = self.hoy
        self.proyecto.avance_evidencia = 'Informe 01'
        self.proyecto.save()
        self.assertContains(self.fragmento('proyecto', self.proyecto), '0%')
        self.proyecto.avance_fecha = self.hoy + timedelta(days=1)
        self.assertFalse(self.proyecto.avance_acreditado)

    def test_etapa_no_imputa_todas_las_anteriores_y_suspension_no_es_actividad(self):
        self.proyecto.etapa = 'validacion'
        self.assertEqual(self.proyecto.etapas_recorridas, ['validacion'])
        for estado in ('suspendido', 'cancelado'):
            self.proyecto.estado = estado
            self.proyecto.full_clean()
            self.proyecto.save()
            self.assertNotIn(self.proyecto, Contenidos(self.centro).proyectos_activos)
            self.assertContains(self.seccion('proyectos', estado=estado), self.proyecto.titulo)

    def test_fecha_final_del_proyecto_no_precede_inicio(self):
        self.proyecto.fin = self.hoy - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.proyecto.full_clean()

    def test_finanzas_privadas_no_se_suman_en_proyectos_ni_alianzas(self):
        self.proyecto.financiador = 'Entidad financiadora'
        self.proyecto.monto = Decimal('123456.00')
        self.proyecto.save()
        self.assertNotContains(self.fragmento('proyecto', self.proyecto), 'USD')
        self.assertEqual(self.seccion('proyectos').context['financiado'], 0)
        self.assertEqual(self.seccion('alianzas').context['financiadores'][0]['monto'], 0)
        self.proyecto.monto_publico = True
        self.proyecto.save()
        self.assertContains(self.fragmento('proyecto', self.proyecto), 'USD')
        self.assertEqual(self.seccion('proyectos').context['financiado'], self.proyecto.monto)
        self.assertEqual(self.seccion('alianzas').context['financiadores'][0]['monto'], self.proyecto.monto)

    def test_hito_cumplido_requiere_evidencia_y_fecha(self):
        hito = HitoProyecto(proyecto=self.proyecto, titulo='Validación de campo', fecha_prevista=self.hoy,
                            estado='cumplido')
        with self.assertRaises(ValidationError):
            hito.full_clean()
        hito.fecha_cumplida, hito.evidencia = self.hoy + timedelta(days=1), 'Acta'
        with self.assertRaises(ValidationError):
            hito.full_clean()
        hito.fecha_cumplida, hito.evidencia = self.hoy, 'Acta'
        hito.full_clean()
        hito.save()
        self.assertNotContains(self.fragmento('proyecto', self.proyecto), hito.titulo)
        hito.publico = True
        hito.save()
        self.assertContains(self.fragmento('proyecto', self.proyecto), hito.titulo)

    @override_settings(CENTROS_ID_ALERTAS_DIAS=7)
    def test_alertas_solo_para_gestor_y_proyectos_activos_reales(self):
        hito = HitoProyecto.objects.create(proyecto=self.proyecto, titulo='Hito interno vencido',
                                          fecha_prevista=self.hoy - timedelta(days=1))
        HitoProyecto.objects.create(proyecto=self.proyecto, titulo='Muy lejano',
                                   fecha_prevista=self.hoy + timedelta(days=8))
        muestra = Proyecto.objects.create(centro=self.centro, titulo='Muestra', resumen='Ejemplo', es_muestra=True)
        HitoProyecto.objects.create(proyecto=muestra, titulo='Solo muestra', fecha_prevista=self.hoy)
        self.assertEqual(Contenidos(self.centro).alertas_investigacion, [])
        alertas = Contenidos(self.centro, self.gestor).alertas_investigacion
        self.assertEqual([(a['titulo'], a['estado']) for a in alertas], [(hito.titulo, 'Vencido')])
        self.proyecto.estado = 'cancelado'
        self.proyecto.save()
        self.assertEqual(Contenidos(self.centro, self.gestor).alertas_investigacion, [])

    def test_plazos_se_revisan_en_administracion_sin_avisos_en_la_ficha(self):
        hito = HitoProyecto.objects.create(proyecto=self.proyecto, titulo='Plazo interno <b>urgente</b>',
                                          fecha_prevista=self.hoy)
        self.client.force_login(self.gestor)
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        self.assertNotContains(pagina, 'Plazos por revisar')
        self.assertNotContains(pagina, hito.titulo)
        panel = admin.site._registry[CentroID]
        request = RequestFactory().get('/')
        request.user = self.gestor
        self.assertIn('plazos_por_revisar', str(panel.get_fieldsets(request, self.centro)))
        salida = str(panel.plazos_por_revisar(self.centro))
        self.assertIn('&lt;b&gt;urgente&lt;/b&gt;', salida)
        self.assertIn(reverse('admin:centros_id_proyecto_change', args=[self.proyecto.pk]), salida)
        request.user = self.usuario
        self.assertNotIn('plazos_por_revisar', str(panel.get_fieldsets(request, self.centro)))

    def test_doi_normaliza_url_y_rechaza_duplicados_dentro_del_centro(self):
        self.assertEqual(normalizar_doi('https://doi.org/10.1234/DATOS'), self.resultado.doi)
        duplicado = Resultado(centro=self.centro, titulo='Duplicado', anio=self.hoy.year,
                              doi='DOI:10.1234/DATOS')
        with self.assertRaises(ValidationError):
            duplicado.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic(using=router.db_for_write(Resultado)):
            duplicado.save()
        duplicado.centro = self.otro
        duplicado.full_clean()
        duplicado.save()

    def test_doi_respeta_unicode_y_codifica_caracteres_de_url(self):
        self.resultado.doi = 'https://doi.org/10.1234/%C3%91%20ABC%3F%23'
        self.resultado.full_clean()
        self.assertEqual(self.resultado.doi, '10.1234/Ñ abc?#')
        self.assertEqual(self.resultado.url_doi, 'https://doi.org/10.1234/%C3%91%20abc%3F%23')
        for doi in ('solo-texto', '10.1234/', '10.1234/control' + chr(10)):
            self.resultado.doi = doi + ('interno' if doi.endswith(chr(10)) else '')
            with self.assertRaises(ValidationError):
                self.resultado.full_clean()

    def test_archivo_protegido_no_se_escribe_en_almacenamiento_publico(self):
        for condicion in ('restringido', 'embargo', 'confidencial'):
            resultado = Resultado(centro=self.centro, titulo='Archivo protegido', anio=self.hoy.year,
                                  acceso=condicion if condicion != 'confidencial' else 'abierto',
                                  confidencial=condicion == 'confidencial', embargo_hasta=self.hoy,
                                  archivo=SimpleUploadedFile('secreto.txt', b'dato sensible'))
            with self.assertRaises(ValidationError):
                resultado.full_clean()
            with self.assertRaises(ValidationError):
                resultado.save()
            self.assertFalse(resultado.archivo._committed)

    def test_embargo_oculta_url_y_solo_se_abre_despues_de_fecha(self):
        self.resultado.acceso, self.resultado.embargo_hasta = 'embargo', self.hoy
        self.resultado.save()
        self.assertEqual(self.resultado.url, '')
        self.assertEqual(self.exportar().json()['resultados'][0]['url'], '')
        self.assertNotContains(self.fragmento('resultado', self.resultado), self.resultado.enlace)
        self.resultado.embargo_hasta = self.hoy - timedelta(days=1)
        self.assertEqual(self.resultado.url, self.resultado.enlace)
        self.assertEqual(self.resultado.estado_acceso_publico, 'Embargo finalizado')

    def test_exportacion_filtrada_excluye_confidencial_muestra_y_otro_centro(self):
        for campos in ({'confidencial': True}, {'es_muestra': True}, {'publicado': False}, {'centro': self.otro}):
            Resultado.objects.create(**(dict(centro=self.centro, titulo='No divulgar', anio=self.hoy.year) | campos))
        parametros = dict(tipo='dato', anio=str(self.hoy.year), proyecto=str(self.proyecto.pk), linea=str(self.linea.pk), q='DATOS')
        datos = self.exportar(**parametros).json()
        self.assertEqual(datos['total'], 1)
        self.assertEqual(datos['resultados'][0]['id'], self.resultado.pk)
        self.assertEqual(self.seccion('produccion', **parametros).context['total'], datos['total'])
        self.assertEqual(self.exportar(anio='invalido').json()['total'], 0)
        self.assertEqual(self.exportar(proyecto=str(self.proyecto.pk + 1000)).json()['total'], 0)

    def test_ris_es_multilinea_y_no_permite_inyectar_campos(self):
        self.resultado.titulo = 'Datos' + chr(10) + 'UR  - https://malicioso.example'
        self.resultado.autores_texto = 'Autora Uno; Autor Dos'
        self.resultado.save()
        respuesta = self.exportar(formato='ris')
        texto = respuesta.content.decode()
        self.assertIn(chr(10) + 'AU  - Autora Uno' + chr(10), texto)
        self.assertNotIn(chr(10) + 'UR  - https://malicioso.example', texto)
        self.assertIn(chr(10) + 'DO  - 10.1234/datos' + chr(10), texto)
        self.assertIn('attachment;', respuesta['Content-Disposition'])

    def test_seccion_oculta_no_ofrece_exportacion_ni_al_gestor(self):
        AjusteSeccion.objects.create(centro=self.centro, clave='produccion', oculta=True)
        self.assertEqual(self.exportar().status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.exportar().status_code, 404)
        self.assertEqual(self.exportar(catalogo='inexistente').status_code, 404)
        self.assertEqual(self.exportar(catalogo='desarrollos', formato='inexistente').status_code, 404)

    def test_trl_solo_se_publica_y_filtra_cuando_tiene_respaldo(self):
        self.desarrollo.trl = 6
        self.desarrollo.save()
        self.assertNotContains(self.fragmento('resultado', self.desarrollo), 'TRL 6')
        self.assertEqual(self.exportar(catalogo='desarrollos', trl='6').json()['total'], 0)
        self.desarrollo.trl_fecha = self.hoy
        self.desarrollo.trl_evaluador = 'Comité técnico'
        self.desarrollo.trl_alcance = 'Prototipo en entorno relevante'
        self.desarrollo.trl_evidencia = 'Informe de evaluación'
        self.desarrollo.save()
        self.assertContains(self.fragmento('resultado', self.desarrollo), 'TRL 6')
        self.assertEqual(self.exportar(catalogo='desarrollos', sector='Agro', tecnologia='IoT', trl='6').json()['total'], 1)
        self.desarrollo.trl_fecha = self.hoy + timedelta(days=1)
        self.assertFalse(self.desarrollo.trl_documentado)

    def test_proteccion_solicitada_no_se_presenta_concedida(self):
        self.desarrollo.tipo = 'propiedad_intelectual'
        self.desarrollo.estado_pi = 'solicitada'
        self.desarrollo.save()
        self.assertNotContains(self.fragmento('resultado', self.desarrollo), 'Solicitada')
        self.assertEqual(next(i.valor for i in Contenidos(self.centro).indicadores
                              if i.calculo == 'propiedad_intelectual'), 0)
        self.desarrollo.pi_modalidad, self.desarrollo.pi_titular = 'Patente', 'Institución titular'
        self.desarrollo.pi_fecha, self.desarrollo.pi_evidencia = self.hoy, 'Acuse de solicitud'
        self.desarrollo.save()
        pagina = self.fragmento('resultado', self.desarrollo)
        self.assertContains(pagina, 'Solicitada')
        self.assertNotContains(pagina, 'Concedida')
        self.assertEqual(next(i.valor for i in Contenidos(self.centro).indicadores
                              if i.calculo == 'propiedad_intelectual'), 1)

    def test_caso_no_es_publico_sin_aceptacion_y_autorizacion(self):
        caso = self.caso()
        self.assertNotIn(caso, Contenidos(self.centro).casos)
        self.assertEqual(self.fragmento('caso', caso).status_code, 404)
        self.documentar_caso(caso)
        self.assertIn(caso, Contenidos(self.centro).casos)
        pagina = self.fragmento('caso', caso)
        self.assertContains(pagina, caso.receptor)
        self.assertNotContains(pagina, caso.resultado)
        caso.fecha_transferencia = self.hoy + timedelta(days=1)
        self.assertFalse(caso.transferencia_documentada)

    def test_impacto_requiere_referencia_unidad_periodo_y_metodo(self):
        caso = self.caso()
        self.documentar_caso(caso)
        caso.referencia, caso.unidad_medida = 'Situación inicial: 100 horas', 'Horas'
        caso.periodo_medicion, caso.metodo_medicion = 'Tres meses', 'Registro antes y después'
        caso.limites = 'Cambios de personal pueden influir'
        caso.save()
        pagina = self.fragmento('caso', caso)
        self.assertContains(pagina, caso.resultado)
        self.assertContains(pagina, caso.limites)
        self.assertContains(self.seccion('casos'), caso.resultado)

    def test_estado_transferido_requiere_caso_documentado(self):
        self.proyecto.estado = 'transferido'
        self.proyecto.save()
        self.assertEqual(self.proyecto.estado_publico, 'Transferencia pendiente de documentar')
        self.assertEqual(next(i.valor for i in Contenidos(self.centro).indicadores
                              if i.calculo == 'proyectos_concluidos'), 0)
        caso = self.caso()
        self.documentar_caso(caso)
        self.assertEqual(self.proyecto.estado_publico, 'Transferido')
        self.assertEqual(next(i.valor for i in Contenidos(self.centro).indicadores
                              if i.calculo == 'proyectos_concluidos'), 1)
        self.assertIn(self.proyecto, self.seccion('casos').context['transferidos'])

    def test_caso_y_resultado_validan_relaciones_del_mismo_centro_y_proyecto(self):
        ajeno = Proyecto.objects.create(centro=self.otro, titulo='Ajeno', resumen='Ajeno')
        self.resultado.proyecto = ajeno
        with self.assertRaises(ValidationError):
            self.resultado.full_clean()
        caso = self.caso(proyecto=ajeno)
        with self.assertRaises(ValidationError):
            caso.full_clean()
        otro_proyecto = Proyecto.objects.create(centro=self.centro, titulo='Otro proyecto', resumen='Otro')
        caso.proyecto = otro_proyecto
        with self.assertRaises(ValidationError):
            caso.full_clean()

    def test_alianza_visible_no_equivale_a_instrumento_vigente(self):
        aliado = Aliado.objects.create(centro=self.centro, nombre='Entidad colaboradora', tipo='empresa',
                                       convenio='Convenio 01', vigencia_desde=self.hoy - timedelta(days=5),
                                       vigencia_hasta=self.hoy + timedelta(days=5))
        self.assertFalse(aliado.vigente)
        aliado.fuente_validacion = 'Expediente institucional'
        aliado.save()
        self.assertIn(aliado, Contenidos(self.centro).aliados_vigentes)
        aliado.vigencia_hasta = self.hoy - timedelta(days=1)
        aliado.save()
        self.assertIn(aliado, Contenidos(self.centro).aliados)
        self.assertNotIn(aliado, Contenidos(self.centro).aliados_vigentes)
        self.assertContains(self.fragmento('aliado', aliado), 'Instrumento vencido')

    def test_contexto_sobrevive_inicio_de_sesion(self):
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        parametros = dict(tipo='visita', finalidad='demostracion', desarrollo=str(self.desarrollo.pk))
        respuesta = self.client.get(url, parametros)
        siguiente = parse_qs(urlsplit(respuesta.context['entrar_url']).query)['next'][0]
        self.assertEqual(urlsplit(siguiente).path, url)
        self.assertEqual(parse_qs(urlsplit(siguiente).query)['desarrollo'], [str(self.desarrollo.pk)])
        self.client.force_login(self.usuario)
        respuesta = self.client.get(siguiente)
        self.assertEqual(respuesta.context['formulario'].initial['desarrollo'], self.desarrollo.pk)
        self.assertEqual(respuesta.context['formulario'].initial['finalidad'], 'demostracion')

    def test_solicitud_guarda_contexto_sin_aprobar_automaticamente(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('solicitar_centro_id', args=[self.centro.slug]), self.datos_solicitud())
        self.assertEqual(respuesta.status_code, 302)
        solicitud = SolicitudCentro.objects.get(usuario=self.usuario)
        self.assertEqual((solicitud.proyecto, solicitud.desarrollo, solicitud.finalidad),
                         (self.proyecto, self.desarrollo, 'codesarrollo'))
        self.assertEqual(solicitud.estado, 'recibida')
        self.assertIsNone(solicitud.inicio_reservado)

    def test_formulario_rechaza_registros_ajenos_muestra_confidencial_y_proyecto_incompatible(self):
        for campos in ({'centro': self.otro}, {'es_muestra': True}, {'confidencial': True}, {'publicado': False}):
            resultado = Resultado.objects.create(**(dict(centro=self.centro, titulo='No seleccionable', anio=self.hoy.year) | campos))
            formulario = SolicitudForm(self.datos_solicitud(desarrollo=resultado.pk), centro=self.centro)
            self.assertFalse(formulario.is_valid())
            self.assertIn('desarrollo', formulario.errors)
            respuesta = self.client.get(reverse('solicitar_centro_id', args=[self.centro.slug]), {'desarrollo': resultado.pk})
            self.assertEqual(respuesta.status_code, 404)
        otro_proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto incompatible', resumen='Otro')
        formulario = SolicitudForm(self.datos_solicitud(proyecto=otro_proyecto.pk), centro=self.centro)
        self.assertFalse(formulario.is_valid())
        self.assertIn('desarrollo', formulario.errors)
