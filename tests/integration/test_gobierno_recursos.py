"""Gobierno editorial y recursos configurables integrados en la ficha pública."""

import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, Producto, Receta
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.admin.fichas import FichaContenidoAdmin


class GobiernoRecursosUnidadTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media.cleanup)
        Usuario = get_user_model()
        self.gestor = Usuario.objects.create_user('gestor.recursos', password='clave')
        self.comunidad = Usuario.objects.create_user('estudiante.recursos', password='clave')
        self.planta = Unidad.objects.create(
            nombre='Planta editorial', descripcion='Prueba de recursos.', fecha_inicio=date(2026, 1, 1),
            slug='planta-editorial', dependencia='plantas_piloto', clasificacion_funcional='planta_piloto',
            modo_operacion='lotes', administrador=self.gestor,
        )
        self.planta.configuracion_operativa.registra_produccion = True
        self.planta.configuracion_operativa.save(update_fields=['registra_produccion'])
        self.modulo_info = self.planta.modulos_contenido.get(clave='informacion-general')

    def archivo(self, nombre, contenido=b'contenido'):
        return SimpleUploadedFile(nombre, contenido, content_type='text/plain')

    def test_el_admin_de_fichas_limita_el_indice_a_las_unidades_gestionables(self):
        FichaContenido.objects.create(
            unidad=self.planta,
            codigo='EDI-DOC-PROPIO',
            tipo='documento',
            titulo='Documento propio',
        )
        ajena = Unidad.objects.create(
            nombre='Planta ajena', descripcion='Otra unidad.', fecha_inicio=date(2026, 1, 1),
            slug='planta-ajena', dependencia='plantas_piloto',
            clasificacion_funcional='planta_piloto', modo_operacion='lotes',
        )
        FichaContenido.objects.create(
            unidad=ajena,
            codigo='AJE-DOC-OTRO',
            tipo='documento',
            titulo='Documento ajeno',
        )
        peticion = RequestFactory().get('/admin/gestion_unidades/fichacontenido/')
        peticion.user = self.gestor
        administrador = FichaContenidoAdmin(FichaContenido, admin.site)
        self.assertEqual(
            list(administrador.get_queryset(peticion).values_list('codigo', flat=True)),
            ['EDI-DOC-PROPIO'],
        )

    def test_integra_carpetas_y_subcarpetas_en_la_seccion_sin_duplicar_menu(self):
        raiz = CarpetaRecurso.objects.create(
            nombre='Normas aplicables', unidad=self.planta, modulo_config=self.modulo_info,
            seccion_planta='1.4', orden=1,
        )
        hija = CarpetaRecurso.objects.create(
            nombre='Normas sanitarias', unidad=self.planta, modulo_config=self.modulo_info,
            seccion_planta='1.4', carpeta_padre=raiz,
        )
        Recurso.objects.create(
            nombre='Norma pública', unidad=self.planta, carpeta=hija,
            archivo=self.archivo('norma.txt'), visibilidad='publica', descripcion='Norma.', seguridad_verificada=True,
        )
        Recurso.objects.create(
            nombre='Documento interno', unidad=self.planta, carpeta=hija,
            archivo=self.archivo('interno.txt'), visibilidad='interna', descripcion='Interno.', seguridad_verificada=True,
        )
        Recurso.objects.create(
            nombre='Documento oculto', unidad=self.planta, carpeta=hija,
            archivo=self.archivo('oculto.txt'), activo=False,
        )

        respuesta = self.client.get(self.planta.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Normas aplicables')
        self.assertContains(respuesta, 'Normas sanitarias')
        self.assertContains(respuesta, 'Norma pública')
        self.assertNotContains(respuesta, 'Documento interno')
        self.assertNotContains(respuesta, 'Documento oculto')
        self.assertEqual(respuesta.content.decode().count('Normas aplicables'), 1)

        self.client.force_login(self.gestor)
        gestionada = self.client.get(self.planta.get_absolute_url())
        self.assertContains(gestionada, 'Documento interno')

    def test_recurso_restringido_exige_cuenta_y_el_archivo_se_sirve_controlado(self):
        carpeta = CarpetaRecurso.objects.create(
            nombre='Repositorio', unidad=self.planta, modulo_config=self.modulo_info,
            seccion_planta='1.5', visibilidad='restringida',
        )
        recurso = Recurso.objects.create(
            nombre='Manual institucional', unidad=self.planta, carpeta=carpeta,
            archivo=self.archivo('manual.txt', b'manual'), visibilidad='publica', descargar=True,
            descripcion='Manual.', seguridad_verificada=True,
        )
        ficha = self.client.get(self.planta.get_absolute_url())
        self.assertContains(ficha, 'Manual institucional')
        protegido = self.client.get(reverse('recurso_unidad', args=[recurso.pk]))
        self.assertEqual(protegido.status_code, 302)
        self.assertIn('login', protegido['Location'])

        self.client.force_login(self.comunidad)
        permitido = self.client.get(reverse('recurso_unidad', args=[recurso.pk]))
        self.assertEqual(permitido.status_code, 200)
        self.assertEqual(b''.join(permitido.streaming_content), b'manual')
        self.assertEqual(permitido['X-Frame-Options'], 'SAMEORIGIN')

    def test_valida_seccion_modulo_y_unidad_de_la_jerarquia(self):
        modulo_procesos = self.planta.modulos_contenido.get(clave='procesos-protocolos')
        incorrecta = CarpetaRecurso(
            nombre='Mal ubicada', unidad=self.planta, modulo_config=modulo_procesos,
            seccion_planta='1.4',
        )
        with self.assertRaises(ValidationError):
            incorrecta.full_clean()

    def test_laboratorio_coloca_sus_carpetas_en_su_propio_mapa(self):
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio existente', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-existente', dependencia='laboratorios',
            clasificacion_funcional='laboratorio_academico',
        )
        modulo = laboratorio.modulos_contenido.get(clave='docencia-capacitacion')
        carpeta = CarpetaRecurso.objects.create(
            nombre='Guías del laboratorio', unidad=laboratorio, modulo_config=modulo, seccion_planta='4.4',
        )
        Recurso.objects.create(
            nombre='Guía sin cambios', unidad=laboratorio, carpeta=carpeta,
            archivo=self.archivo('guia.txt'), descripcion='Guía.', seguridad_verificada=True,
        )
        respuesta = self.client.get(laboratorio.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Guías del laboratorio')
        # Las guías son 3.1 en el laboratorio (2.6 en la planta); nada de la planta se cuela.
        self.assertContains(respuesta, 'data-seccion="4.4"')
        self.assertEqual(respuesta.context['secciones_planta']['guias']['numero'], '4.1')
        self.assertNotIn('haccp', respuesta.context['secciones_planta'])

    def test_la_senal_conserva_la_decision_editorial(self):
        familia = FamiliaProducto.objects.create(
            unidad=self.planta, codigo='ED-FAM', orden=1, nombre='Familia editorial',
        )
        producto = Producto.objects.create(
            unidad=self.planta, familia=familia, codigo='ED-PROD-1', nombre='Producto editorial',
            unidad_medida='kg', descripcion='Primera versión',
        )
        ficha = FichaContenido.objects.get(codigo='ED-PROD-1')
        ficha.estado = 'borrador'
        ficha.visibilidad = 'interna'
        ficha.save(update_fields=['estado', 'visibilidad'])

        producto.descripcion = 'Datos técnicos actualizados'
        producto.save()
        ficha.refresh_from_db()
        self.assertEqual(ficha.estado, 'borrador')
        self.assertEqual(ficha.visibilidad, 'interna')
        self.assertEqual(ficha.descripcion, 'Datos técnicos actualizados')

        producto.activo = False
        producto.save()
        ficha.refresh_from_db()
        self.assertEqual((ficha.estado, ficha.visibilidad), ('archivada', 'interna'))

    def test_el_admin_expone_el_gobierno_y_el_silabo_sin_filas_vacias(self):
        administrador = get_user_model().objects.create_superuser(
            'admin.recursos', 'admin@example.test', 'clave',
        )
        self.client.force_login(administrador)
        unidad = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.planta.pk]))
        self.assertEqual(unidad.status_code, 200)
        # Cada bloque dice a qué sección de la ficha llega; las carpetas se ordenan en su organizador.
        self.assertContains(unidad, 'Se ve en la ficha: 1.2 La unidad.')
        self.assertContains(unidad, reverse('admin:directorio_unidades_unidad_contenidos', args=[self.planta.pk]))
        self.assertContains(unidad, 'Visibilidad')
        self.assertContains(unidad, 'name="recursos-TOTAL_FORMS" value="0"', html=False)
        asignaturas = self.client.get(reverse('admin:formacion_asignatura_changelist'))
        self.assertEqual(asignaturas.status_code, 200)
        self.assertContains(asignaturas, 'Asignaturas')

    def test_el_gobierno_editorial_controla_la_ficha_sin_desactivar_el_proceso(self):
        familia = FamiliaProducto.objects.create(
            unidad=self.planta, codigo='ED-FAM-2', orden=1, nombre='Otra familia',
        )
        producto = Producto.objects.create(
            unidad=self.planta, familia=familia, codigo='ED-PROD-2', nombre='Producto reservado',
            unidad_medida='kg',
        )
        receta = Receta.objects.create(
            unidad=self.planta, familia=familia, producto=producto,
            codigo='ED-REC-2', nombre='Proceso reservado', cantidad_base='10',
            unidad_base='kg', rendimiento_esperado='8',
        )
        EtapaReceta.objects.create(
            receta=receta, familia=familia, orden=1, nombre='Operación', duracion_min=10,
        )
        ficha = FichaContenido.objects.get(codigo=producto.codigo)
        ficha.estado = 'publicada'
        ficha.visibilidad = 'restringida'
        ficha.save(update_fields=['estado', 'visibilidad'])
        ficha_proceso = FichaContenido.objects.get(codigo=receta.codigo)
        ficha_proceso.estado = 'publicada'
        ficha_proceso.visibilidad = 'restringida'
        ficha_proceso.save(update_fields=['estado', 'visibilidad'])
        self.assertTrue(Receta.objects.filter(pk=receta.pk, activa=True).exists())

        publica = self.client.get(reverse('ficha_producto_publica', args=[self.planta.slug, producto.pk]))
        self.assertEqual(publica.status_code, 404)
        self.client.force_login(self.comunidad)
        from apps.formacion.presentation.aula import procesos_publicos
        self.assertEqual([item.pk for item in procesos_publicos(self.planta, self.comunidad)], [receta.pk])
        restringida = self.client.get(reverse('ficha_producto_publica', args=[self.planta.slug, producto.pk]))
        self.assertEqual(restringida.status_code, 200)


class CargadorRespetaGobiernoEditorialTests(TestCase):
    def test_el_admin_registra_quien_valida_y_protege_la_decision(self):
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        ficha = FichaContenido.objects.get(codigo='LAC-REC-QUESO-100')
        administrador = get_user_model().objects.create_superuser(
            'admin.validacion', 'validacion@example.test', 'clave',
        )
        self.client.force_login(administrador)
        respuesta = self.client.post(reverse('admin:gestion_unidades_fichacontenido_changelist'), {
            'action': 'validar_institucionalmente',
            '_selected_action': [ficha.pk],
        })
        self.assertEqual(respuesta.status_code, 302)
        ficha.refresh_from_db()
        self.assertEqual(ficha.estado_validacion, 'validada')
        self.assertEqual(ficha.validado_por, administrador)
        self.assertIsNotNone(ficha.validado_en)
        self.assertTrue(ficha.decision_editorial_manual)
        self.assertEqual(ficha.decision_editorial_por, administrador)
        validado_en = ficha.validado_en

        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        ficha.refresh_from_db()
        self.assertEqual(ficha.estado_validacion, 'validada')
        self.assertEqual(ficha.validado_por, administrador)
        self.assertEqual(ficha.validado_en, validado_en)

    def test_una_recarga_tecnica_no_republica_una_ficha_archivada(self):
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        ficha = FichaContenido.objects.get(codigo='LAC-REC-QUESO-100')
        ficha.estado = 'archivada'
        ficha.visibilidad = 'interna'
        ficha.version = 4
        ficha.estado_validacion = 'bloqueada'
        ficha.observacion_validacion = 'Falta acta firmada por la institución.'
        ficha.decision_editorial_manual = True
        ficha.save(update_fields=[
            'estado', 'visibilidad', 'version', 'estado_validacion',
            'observacion_validacion', 'decision_editorial_manual',
        ])

        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        ficha.refresh_from_db()
        self.assertEqual((ficha.estado, ficha.visibilidad, ficha.version), ('archivada', 'interna', 4))
        self.assertEqual(ficha.estado_validacion, 'bloqueada')
        self.assertEqual(ficha.observacion_validacion, 'Falta acta firmada por la institución.')
        self.assertTrue(ficha.decision_editorial_manual)
