"""Paso 7: adjuntos gobernados, repositorio y artefactos externos."""

from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.presentation.repositorio import paquete_entrada
from apps.gestion_unidades.models.repositorio import ArtefactoExterno, ResultadoArtefacto
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.admin.repositorio import ArtefactoExternoAdmin
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class RepositorioPaso7Tests(BasePracticaPorProceso):
    def evidencia(self):
        recurso = Recurso(
            nombre='Evidencia de validación', descripcion='Comparación con una corrida institucional.',
            unidad=self.unidad, url='https://example.test/evidencia.pdf', tipo_adjunto='evidencia',
            autor='Unidad de Lácteos', licencia_uso='interna', seguridad_verificada=True,
        )
        recurso.full_clean()
        recurso.save()
        return recurso

    def artefacto(self, **cambios):
        datos = {
            'codigo': 'LAC-SIM-BAL-01', 'nombre': 'Modelo externo de balance',
            'descripcion': 'Modelo para contrastar el balance del proceso.', 'tipo': 'hoja_calculo',
            'nivel_integracion': 2, 'unidad': self.unidad, 'receta': self.receta_queso,
            'software_requerido': 'Hoja de cálculo compatible con XLSX',
            'licencia_software': 'libre', 'requisitos_tecnicos': 'Lector XLSX.',
            'instrucciones_uso': 'Exportar entradas, ejecutar externamente e importar resultados.',
            'entradas_esperadas': ['Receta.codigo', 'Receta.cantidad_base', 'Operacion.tiempo_maquina'],
            'salidas_devueltas': ['masa_final', 'desviacion_pct'], 'formato_intercambio': 'xlsx',
            'esquema': {'masa_final': 'decimal', 'desviacion_pct': 'decimal'},
            'que_representa': 'Balance estacionario de la corrida.',
            'supuestos_simplificaciones': 'Densidad constante y sin acumulación.',
            'estado_verificacion': 'verificado', 'estado_validacion': 'datos',
            'evidencia_validacion': self.evidencia(),
            'fuente_referencia': 'Acta UPEC LAC-VAL-2026-01 y corrida institucional.',
            'responsable_validacion': self.coordinacion,
            'vigente_desde': timezone.localdate() - timedelta(days=30),
            'vigente_hasta': timezone.localdate() + timedelta(days=365),
            'limitaciones_conocidas': 'No representa transitorios.', 'autor': 'UPEC',
            'licencia_uso': 'Uso académico UPEC', 'estado': 'publicado', 'visibilidad': 'publica',
        }
        datos.update(cambios)
        return ArtefactoExterno.objects.create(**datos)

    def test_indices_dos_dos_dos_tres_y_dos_cinco_tienen_contenido_real(self):
        for nombre, textos in {
            'materiales_insumos': ('Leche cruda', 'Materiales e insumos'),
            'metodos_tiempos': ('Recepción', 'min de trabajo'),
            'ruta_saber_documentacion': ('Fundamentos y variables', 'Ruta del saber'),
        }.items():
            with self.subTest(nombre=nombre):
                respuesta = self.client.get(reverse(nombre, args=[self.unidad.slug]))
                self.assertEqual(respuesta.status_code, 200)
                for texto in textos:
                    self.assertContains(respuesta, texto)
                self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')

    def test_adjunto_exige_descripcion_formato_seguro_y_dos_niveles(self):
        sin_descripcion = Recurso(
            nombre='Incompleto', unidad=self.unidad, url='https://example.test/manual.pdf',
        )
        with self.assertRaises(ValidationError):
            sin_descripcion.full_clean()
        ejecutable = Recurso(
            nombre='Ejecutable', descripcion='No debe entrar.', unidad=self.unidad,
            archivo=SimpleUploadedFile('programa.exe', b'MZ'),
        )
        with self.assertRaises(ValidationError):
            ejecutable.full_clean()
        modulo = self.unidad.modulos_contenido.get(clave='informacion-general')
        raiz = CarpetaRecurso.objects.create(
            nombre='Raíz paso 7', unidad=self.unidad, modulo_config=modulo, seccion_planta='1.5',
        )
        hija = CarpetaRecurso.objects.create(
            nombre='Segundo nivel', unidad=self.unidad, modulo_config=modulo,
            seccion_planta='1.5', carpeta_padre=raiz,
        )
        tercera = CarpetaRecurso(
            nombre='Tercer nivel', unidad=self.unidad, modulo_config=modulo,
            seccion_planta='1.5', carpeta_padre=hija,
        )
        with self.assertRaises(ValidationError):
            tercera.full_clean()

    def test_un_pdf_subido_con_titulo_sin_extension_abre_en_el_visualizador(self):
        modulo = self.unidad.modulos_contenido.get(clave='informacion-general')
        carpeta = CarpetaRecurso.objects.create(
            nombre='Presentación de prueba', unidad=self.unidad,
            modulo_config=modulo, seccion_planta='1.1', visibilidad='publica',
        )
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            recurso = Recurso(
                nombre='Prueba', descripcion='PDF de prueba para el visualizador.',
                unidad=self.unidad, carpeta=carpeta,
                archivo=SimpleUploadedFile('plan_estudio.pdf', b'%PDF-1.4\n%%EOF'),
                tipo_adjunto='manual', visibilidad='publica',
                seguridad_verificada=True,
            )
            recurso.full_clean()
            recurso.save()

            recurso.acceso_restringido = False
            recurso.url_contenido = reverse('recurso_unidad', args=[recurso.pk])
            carpeta.recursos_publicos = [recurso]
            carpeta.subcarpetas_publicas = []
            carpeta.total_recursos = 1
            html = render_to_string(
                'portal/pages/unidades/detalle/carpeta_recurso.html',
                {'carpeta': carpeta, 'puede_gestionar_unidad': False},
            )
            self.assertIn('plan_estudio.pdf', html)
            self.assertIn(
                f'data-ui-click="replaceContent" data-ui-arg0="{recurso.url_contenido}" data-ui-arg1="plan_estudio.pdf" data-ui-arg2="false"', html,
            )
            archivo = self.client.head(reverse('recurso_unidad', args=[recurso.pk]))
            self.assertEqual(archivo.status_code, 200)
            self.assertEqual(archivo['Content-Type'], 'application/pdf')
            archivo.close()

            recurso_zip = Recurso(
                pk=999, nombre='Recorrido XR', descripcion='Paquete interactivo.',
                unidad=self.unidad, carpeta=carpeta, archivo='recorrido_xr.zip',
                nombre_original='recorrido_xr.zip',
            )
            recurso_zip.acceso_restringido = False
            recurso_zip.url_contenido = '/recursos-unidad/999/'
            carpeta.recursos_publicos = [recurso_zip]
            html_zip = render_to_string(
                'portal/pages/unidades/detalle/carpeta_recurso.html',
                {'carpeta': carpeta, 'puede_gestionar_unidad': False},
            )
            self.assertIn(
                'data-ui-click="handleZipResource" data-ui-arg0="/recursos-unidad/999/" '
                'data-ui-arg1="recorrido_xr.zip" data-ui-arg2="/recursos-unidad/999/" data-ui-arg3="false"',
                html_zip,
            )

    def test_artefacto_exporta_solo_el_contrato_y_detecta_cambios(self):
        artefacto = self.artefacto()
        paquete = paquete_entrada(artefacto)
        self.assertEqual(set(paquete['contrato']), set(artefacto.entradas_esperadas))
        respuesta = self.client.get(reverse(
            'exportar_paquete_artefacto', args=[self.unidad.slug, artefacto.codigo],
        ))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(respuesta.content.startswith(b'PK'))
        etapa = self.receta_queso.etapas.first()
        etapa.duracion_min += 1
        etapa.save(update_fields=['duracion_min'])
        artefacto.refresh_from_db()
        self.assertTrue(artefacto.posiblemente_desactualizado)
        self.assertIn('operación', artefacto.motivo_desactualizacion)
        self.assertEqual(self.client.get(reverse(
            'artefacto_externo', args=[self.unidad.slug, artefacto.codigo],
        )).status_code, 404)
        self.assertEqual(self.client.get(reverse(
            'exportar_paquete_artefacto', args=[self.unidad.slug, artefacto.codigo],
        )).status_code, 404)

    def test_publicacion_sin_evidencia_ni_validacion_es_rechazada(self):
        with self.assertRaises(ValidationError):
            self.artefacto(
                codigo='LAC-SIM-INVALIDO', evidencia_validacion=None,
                estado_validacion='sin_validar',
            )
        with self.assertRaises(ValidationError):
            self.artefacto(codigo='LAC-ART-INVALIDO')
        for campo in ('fuente_referencia', 'responsable_validacion', 'vigente_desde'):
            with self.subTest(campo=campo), self.assertRaises(ValidationError):
                self.artefacto(codigo=f'LAC-SIM-FALTA-{campo[:3].upper()}', **{campo: None})

    def test_un_artefacto_vencido_deja_de_publicarse_y_descargarse(self):
        artefacto = self.artefacto(codigo='LAC-SIM-VIGENCIA-01')
        ArtefactoExterno.objects.filter(pk=artefacto.pk).update(
            vigente_hasta=timezone.localdate() - timedelta(days=1),
        )
        artefacto.refresh_from_db()
        self.assertFalse(artefacto.publicable)
        self.assertEqual(self.client.get(reverse(
            'artefacto_externo', args=[self.unidad.slug, artefacto.codigo],
        )).status_code, 404)
        self.assertEqual(self.client.get(reverse(
            'exportar_paquete_artefacto', args=[self.unidad.slug, artefacto.codigo],
        )).status_code, 404)

    def test_los_resultados_importados_solo_se_muestran_a_gestores(self):
        artefacto = self.artefacto(codigo='LAC-SIM-RESULTADO-01')
        ResultadoArtefacto.objects.create(
            artefacto=artefacto,
            archivo='artefactos/resultados/LAC-SIM-RESULTADO-01/resultado_privado.xlsx',
            importado_por=self.coordinacion,
        )
        url = reverse('artefacto_externo', args=[self.unidad.slug, artefacto.codigo])
        publica = self.client.get(url)
        self.assertEqual(publica.status_code, 200)
        self.assertNotContains(publica, 'resultado_privado.xlsx')
        self.assertContains(publica, 'Acta UPEC LAC-VAL-2026-01')

        self.client.force_login(self.coordinacion)
        gestion = self.client.get(url)
        self.assertContains(gestion, 'resultado_privado.xlsx')

    def test_importar_un_resultado_no_oculta_una_desactualizacion_sin_aprobacion(self):
        artefacto = self.artefacto(codigo='LAC-SIM-REVALIDAR-01')
        ArtefactoExterno.objects.filter(pk=artefacto.pk).update(
            posiblemente_desactualizado=True,
            motivo_desactualizacion='Cambió la receta de origen.',
        )
        self.client.force_login(self.coordinacion)
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            respuesta = self.client.post(reverse(
                'importar_resultado_artefacto', args=[self.unidad.slug, artefacto.codigo],
            ), {'archivo': SimpleUploadedFile('resultado.xlsx', b'PK-prueba')})
        self.assertEqual(respuesta.status_code, 302)
        artefacto.refresh_from_db()
        self.assertTrue(artefacto.posiblemente_desactualizado)

        peticion = RequestFactory().post('/admin/gestion_unidades/artefactoexterno/')
        peticion.user = self.coordinacion
        administrador = ArtefactoExternoAdmin(ArtefactoExterno, admin.site)
        administrador.confirmar_sincronizacion(
            peticion,
            administrador.get_queryset(peticion).filter(pk=artefacto.pk),
        )
        artefacto.refresh_from_db()
        self.assertFalse(artefacto.posiblemente_desactualizado)
        self.assertEqual(artefacto.responsable_validacion, self.coordinacion)
        self.assertIsNotNone(artefacto.validado_en)

    def test_repositorio_y_artefacto_se_integran_en_la_ruta_principal(self):
        artefacto = self.artefacto()
        portada = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(portada, 'Repositorio institucional')
        self.assertContains(portada, artefacto.nombre)
        ficha = self.client.get(reverse(
            'ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk],
        ))
        self.assertContains(ficha, 'Artefacto externo')
        self.assertContains(ficha, reverse('artefacto_externo', args=[self.unidad.slug, artefacto.codigo]))
        self.assertContains(ficha, f'Exportar datos · {artefacto.nombre}')
        self.assertContains(ficha, reverse(
            'exportar_paquete_artefacto', args=[self.unidad.slug, artefacto.codigo],
        ))
