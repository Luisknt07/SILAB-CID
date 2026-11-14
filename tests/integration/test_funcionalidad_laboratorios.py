"""Una prueba funcional es evidencia específica y no se deduce de disponibilidad."""
import io
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.funcionalidad_laboratorios import acciones_funcionalidad, funcionalidad_documentada
from apps.documentos.presentation.medicion_metas import registrar_evidencia, rectificar_evidencia
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class FuncionalidadLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='funcionalidad-qa-responsable')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de funcionalidad QA', slug='funcionalidad-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otro laboratorio QA', slug='funcionalidad-otra-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.observatorio = Unidad.objects.create(nombre='Observatorio QA', slug='funcionalidad-observatorio-qa',
            dependencia='observatorios', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        tipo = EquiposServicios.objects.create(codigo='TIPO-FUNC-QA', nombre='Equipo técnico QA')
        cls.equipo = UnidadEquipo.objects.create(equipo=tipo, laboratorio=cls.unidad,
            codigo_unidad='EQUIPO-FUNC-QA', numero_serie='SERIE-FUNC-QA')
        cls.ajeno = UnidadEquipo.objects.create(equipo=tipo, laboratorio=cls.otra, codigo_unidad='EQUIPO-AJENO-QA')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-qa-funcionalidad-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        reloj = patch('django.utils.timezone.localdate', return_value=date(2026, 10, 17))
        reloj.start()
        self.addCleanup(reloj.stop)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)

    def pdf(self, codigo):
        salida = io.BytesIO()
        pagina = Canvas(salida)
        pagina.drawString(35, 780, codigo + ': informe verificable de procedimiento, criterio y resultado de prueba funcional QA.')
        pagina.save()
        return SimpleUploadedFile(codigo + '.pdf', salida.getvalue(), 'application/pdf')

    def datos(self, codigo='FUNC-QA', **cambios):
        datos = dict(tipo='FUNCIONALIDAD', codigo=codigo, fecha=date(2026, 10, 16),
            titulo='Verificación funcional del equipo QA', descripcion='Conclusión del ensayo realizado y sus limitaciones.',
            responsable=self.actor, detalle=dict(equipo_id=self.equipo.pk,
                procedimiento='Ensayo de arranque y ciclo completo con carga de referencia.',
                criterio='Completar el ciclo sin alarmas y dentro de la tolerancia del procedimiento QA.',
                resultado_funcional='operativo', hallazgos_funcionales=''))
        datos.update(cambios)
        return datos

    def prueba(self, codigo='FUNC-QA', **cambios):
        return registrar_evidencia(self.unidad, self.actor, self.datos(codigo, **cambios),
            verificar=True, archivo=self.pdf(codigo))

    def lectura(self):
        return funcionalidad_documentada(self.unidad, self.inicio, self.fin)

    def test_disponible_sin_prueba_sigue_pendiente_y_no_inventa_funcionalidad(self):
        self.assertEqual(self.equipo.estado_unidad, 'disponible')
        lectura = self.lectura()
        self.assertEqual((lectura['universo_equipos'], lectura['comprobados_en_periodo']), (1, 0))
        self.assertEqual(lectura['sin_comprobacion_periodo'], 1)
        self.assertFalse(lectura['ultimas'][0]['apto'])

    def test_prueba_real_conserva_identidad_respaldo_y_no_cambia_estado_del_equipo(self):
        anterior = UnidadEquipo.objects.filter(pk=self.equipo.pk).values().get()
        prueba = self.prueba()
        self.assertEqual(UnidadEquipo.objects.filter(pk=self.equipo.pk).values().get(), anterior)
        self.assertEqual(prueba.detalle['equipo_snapshot']['equipo'], self.equipo.pk)
        self.assertEqual(prueba.detalle['equipo_snapshot']['unidad_registro'], self.unidad.pk)
        lectura = self.lectura()
        self.assertEqual((lectura['reales'], lectura['operativos'], lectura['comprobados_en_periodo']), (1, 1, 1))
        self.assertEqual(lectura['ultimas'][0]['pk'], prueba.pk)
        self.assertEqual(len(lectura['filas'][0]['contenido_sha256']), 64)
        self.assertEqual(len(lectura['filas'][0]['sha256']), 64)

    def test_observado_o_no_operativo_requieren_hallazgos_y_no_se_muestran_aptos(self):
        for resultado in ('observado', 'no_operativo'):
            detalle = self.datos()['detalle']
            detalle['resultado_funcional'] = resultado
            with self.assertRaisesMessage(ValidationError, 'fallas'):
                self.prueba(detalle=detalle)
        detalle['hallazgos_funcionales'] = 'El ciclo se interrumpe por alarma de sobretemperatura.'
        self.prueba(detalle=detalle)
        lectura = self.lectura()
        self.assertEqual(lectura['no_operativos'], 1)
        self.assertFalse(lectura['ultimas'][0]['apto'])
        self.assertEqual(UnidadEquipo.objects.get(pk=self.equipo.pk).estado_unidad, 'disponible')

    def test_exige_procedimiento_criterio_resultado_y_respaldo_real(self):
        for clave in ('procedimiento', 'criterio', 'resultado_funcional'):
            detalle = self.datos()['detalle']
            detalle[clave] = ''
            with self.assertRaises(ValidationError):
                self.prueba(detalle=detalle)
        datos = self.datos(enlace='https://example.org/prueba')
        with self.assertRaisesMessage(ValidationError, 'informe o respaldo'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        with self.assertRaisesMessage(ValidationError, 'legible'):
            registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True,
                archivo=SimpleUploadedFile('vacio.pdf', b'%PDF-1.4 Sin contenido'))

    def test_equipo_ajeno_no_se_admite_pero_equipo_compartido_si(self):
        detalle = self.datos()['detalle']
        detalle['equipo_id'] = self.ajeno.pk
        with self.assertRaisesMessage(ValidationError, 'compartido'):
            self.prueba(detalle=detalle)
        self.ajeno.laboratorios.add(self.unidad)
        prueba = self.prueba(detalle=detalle)
        self.assertIn(self.unidad.pk, prueba.detalle['equipo_snapshot']['laboratorios'])
        self.assertEqual(self.lectura()['universo_equipos'], 2)

    def test_traslado_conserva_prueba_historica_sin_atribuirla_a_nueva_unidad(self):
        self.prueba()
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(laboratorio=self.otra)
        lectura = self.lectura()
        self.assertEqual((lectura['registrados'], lectura['reales'], lectura['universo_equipos']), (1, 1, 0))
        otra = funcionalidad_documentada(self.otra, self.inicio, self.fin)
        self.assertEqual(otra['reales'], 0)
        self.assertEqual(otra['sin_comprobacion_periodo'], 2)

    def test_alterar_resultado_o_equipo_invalida_huella_sin_borrar_el_archivo(self):
        prueba = self.prueba()
        original = dict(prueba.detalle)
        prueba.detalle['resultado_funcional'] = 'no_operativo'
        prueba.detalle['hallazgos_funcionales'] = 'Resultado cambiado fuera del flujo.'
        EvidenciaGestionUnidad.objects.filter(pk=prueba.pk).update(detalle=prueba.detalle)
        self.assertEqual(self.lectura()['reales'], 0)
        original['equipo_id'] = self.ajeno.pk
        EvidenciaGestionUnidad.objects.filter(pk=prueba.pk).update(detalle=original)
        self.assertEqual(self.lectura()['reales'], 0)
        self.assertTrue(prueba.recurso.archivo.storage.exists(prueba.recurso.archivo.name))

    def test_demo_no_acredita_ni_se_convierte_en_real_al_quitar_bandera(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            prueba = self.prueba()
        self.assertEqual((self.lectura()['reales'], self.lectura()['demostracion']), (0, 1))
        EvidenciaGestionUnidad.objects.filter(pk=prueba.pk).update(demostracion=False)
        self.assertEqual(self.lectura()['reales'], 0)
        self.assertEqual(self.lectura()['sin_comprobacion_periodo'], 1)

    def test_ultima_real_se_distingue_de_antigua_y_demo_no_la_sustituye(self):
        antigua = self.prueba(fecha=date(2026, 6, 30))
        lectura = self.lectura()
        self.assertEqual(lectura['registrados'], 0)
        self.assertEqual(lectura['ultimas'][0]['pk'], antigua.pk)
        self.assertFalse(lectura['ultimas'][0]['vigente_en_periodo'])
        real = self.prueba('ACTUAL-QA')
        with override_settings(MEDICION_SOLO_DEMO=True):
            self.prueba('DEMO-POSTERIOR-QA', fecha=date(2026, 10, 17))
        self.assertEqual(self.lectura()['ultimas'][0]['pk'], real.pk)

    def test_rectificar_ultima_recupera_comprobacion_previa_sin_borrar_historial(self):
        primera = self.prueba()
        detalle = self.datos()['detalle']
        detalle.update(resultado_funcional='observado', hallazgos_funcionales='Vibración fuera de la referencia.')
        ultima = self.prueba('ULTIMA-QA', fecha=date(2026, 10, 17), detalle=detalle)
        self.assertEqual(self.lectura()['observados'], 1)
        rectificar_evidencia(self.unidad, self.actor, ultima.pk, 'Verificación repetida incorrectamente')
        self.assertEqual(self.lectura()['ultimas'][0]['pk'], primera.pk)
        self.assertEqual(self.lectura()['registrados'], 2)

    def test_fuentes_borrador_futuras_y_tipos_inspeccion_no_acreditan(self):
        registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=False, archivo=self.pdf('BORRADOR'))
        self.assertEqual(self.lectura()['reales'], 0)
        with self.assertRaisesMessage(ValidationError, 'futura'):
            self.prueba('FUTURA-QA', fecha=date(2026, 10, 18))
        self.assertEqual(self.lectura()['sin_comprobacion_periodo'], 1)

    def test_formulario_directo_guarda_campos_snapshot_y_muestra_respaldo(self):
        self.client.force_login(self.actor)
        datos = self.datos()
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        respuesta = self.client.post(ruta, dict(anio=2026, corte='B', verificar='on',
            archivo=self.pdf('FORMULARIO-FUNC'), responsable=self.actor.pk,
            **{k: v for k, v in datos.items() if k not in ('detalle', 'responsable')}, **datos['detalle']))
        self.assertEqual(respuesta.status_code, 302)
        respuesta = self.client.get(ruta, dict(anio=2026, corte='B', tipo='FUNCIONALIDAD'))
        self.assertContains(respuesta, self.equipo.codigo_unidad)
        self.assertContains(respuesta, 'La disponibilidad calculada')
        self.assertContains(respuesta, 'Ver respaldo')
        self.assertEqual(self.lectura()['reales'], 1)

    def test_observatorio_recibe_formulario_y_rechaza_equipo_ajeno(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.observatorio.slug])
        self.assertEqual(self.client.get(ruta, dict(tipo='FUNCIONALIDAD')).status_code, 200)
        self.assertEqual(funcionalidad_documentada(self.observatorio, self.inicio, self.fin)['reales'], 0)
        self.assertEqual(len(acciones_funcionalidad(self.observatorio, self.inicio, self.fin)), 1)
        with self.assertRaisesMessage(ValidationError, 'pertenecer'):
            registrar_evidencia(self.observatorio, self.actor, self.datos(), verificar=False)

    def test_lectura_no_crea_auditorias_ni_modifica_evidencias_y_link_es_directo(self):
        self.prueba()
        evidencias = list(EvidenciaGestionUnidad.objects.values())
        auditorias = RegistroAuditoriaUnidad.objects.count()
        self.lectura()
        self.assertEqual(list(EvidenciaGestionUnidad.objects.values()), evidencias)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)
        self.assertIn('tipo=FUNCIONALIDAD', acciones_funcionalidad(self.unidad, self.inicio, self.fin)[0]['url'])

    def test_snapshot_importado_malformado_no_produce_error_ni_acredita(self):
        prueba = self.prueba()
        prueba.detalle['equipo_snapshot']['laboratorios'] = 5
        EvidenciaGestionUnidad.objects.filter(pk=prueba.pk).update(detalle=prueba.detalle)
        self.assertEqual(self.lectura()['reales'], 0)
