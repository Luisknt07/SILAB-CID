"""Fase 2 de reportes: evidencias adjuntas a la práctica y registro de desechos.

La evidencia documental cuelga de la ejecución (FT03) y se sirve solo a quien
puede ver la práctica; los desechos peligrosos y especiales tienen registro,
reporte por unidad y consolidado por tipo en el administrador.
"""

from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica
from apps.recursos.models.desechos import RegistroDesecho
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar, pdf_legible_prueba

import tempfile

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix='citt-evidencias-')


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseDePracticas(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.coordinador = Usuario.objects.create_user(username='coordinador-evidencia', password='clave-segura',
                                                       first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.ajeno = Usuario.objects.create_user(username='ajeno-evidencia', password='clave-segura')
        identificar(cls.ajeno, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de evidencias', slug='laboratorio-evidencias-f2',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1), administrador=cls.coordinador)
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Impresión FDM')
        cls.reserva = Reserva.objects.create(
            laboratorio=cls.unidad, usuario=cls.coordinador, fecha=date(2026, 3, 4), hora_inicio=time(9, 0),
            hora_fin=time(11, 0), titulo_solicitud='Práctica FDM', estado='confirmada',
            actividad_catalogo=cls.actividad, numero_participantes=12)
        cls.plan = PlanificacionPractica.objects.create(
            codigo='PL-F2-0001', unidad=cls.unidad, actividad=cls.actividad, reserva=cls.reserva,
            fecha=date(2026, 3, 4), hora_inicio=time(9, 0), hora_fin=time(11, 0), asignatura='Manufactura',
            docente_tutor='Ana', tema='Impresión 3D', resultado_aprendizaje='Imprime', estado='aprobada',
            creado_por=cls.coordinador)

    def setUp(self):
        self.client.force_login(self.coordinador)

    def archivo(self, nombre='foto-practica.jpg', contenido=b'\xff\xd8\xff imagen', tipo='image/jpeg'):
        return SimpleUploadedFile(nombre, contenido, content_type=tipo)

    def datos_ejecucion(self, **extra):
        datos = {
            'fecha_ejecucion': '2026-03-04', 'hora_inicio_real': '09:05', 'hora_fin_real': '10:55',
            'resultado': 'ejecutada', 'motivo': '', 'estudiantes_asistentes': 11, 'tuvo_incidente': '',
            'cumplimiento_resultado': 'si', 'observaciones_docente': 'Sin novedad', 'accion': 'guardar',
        }
        datos.update(extra)
        return datos


class EvidenciasEnLaEjecucionTests(BaseDePracticas):
    def url(self):
        return reverse('editar_ejecucion_practica', args=[self.unidad.slug, self.plan.pk])

    def test_el_formulario_de_ejecucion_admite_archivos_y_los_guarda_con_su_identificacion(self):
        respuesta = self.client.post(self.url(), self.datos_ejecucion(
            evidencia_tipo='fotografia',
            evidencia_descripcion='Grupo 2 imprimiendo la pieza, 4 de marzo',
            evidencias=[self.archivo(), self.archivo('informe.pdf', b'%PDF-1.4', 'application/pdf')],
        ))

        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'context', None) and respuesta.context['form'].errors)
        ejecucion = EjecucionPractica.objects.get(planificacion=self.plan)
        evidencias = list(ejecucion.evidencias.order_by('nombre_original'))
        self.assertEqual([e.nombre_original for e in evidencias], ['foto-practica.jpg', 'informe.pdf'])
        self.assertEqual({e.tipo for e in evidencias}, {'fotografia'})
        self.assertEqual(evidencias[0].descripcion, 'Grupo 2 imprimiendo la pieza, 4 de marzo')
        self.assertEqual(evidencias[0].subido_por, self.coordinador)
        self.assertTrue(evidencias[0].archivo.name.startswith(f'practicas/evidencias/{self.unidad.pk}/'))

    def test_sin_descripcion_o_con_formato_no_admitido_nada_se_guarda(self):
        sin_descripcion = self.client.post(self.url(), self.datos_ejecucion(
            evidencia_tipo='informe', evidencia_descripcion='', evidencias=[self.archivo()]))
        self.assertEqual(sin_descripcion.status_code, 200)
        self.assertContains(sin_descripcion, 'Describe la evidencia')
        self.assertFalse(EjecucionPractica.objects.filter(planificacion=self.plan).exists())

        ejecutable = self.client.post(self.url(), self.datos_ejecucion(
            evidencia_tipo='producto', evidencia_descripcion='Programa', evidencias=[self.archivo('virus.exe', b'MZ')]))
        self.assertContains(ejecutable, 'no tiene un formato admitido')
        self.assertEqual(EvidenciaPractica.objects.count(), 0)

    def test_la_evidencia_se_sirve_solo_a_quien_ve_la_practica_y_se_puede_retirar(self):
        self.client.post(self.url(), self.datos_ejecucion(
            evidencia_tipo='fotografia', evidencia_descripcion='Grupo 2', evidencias=[self.archivo()]))
        evidencia = EvidenciaPractica.objects.get()
        ruta = reverse('evidencia_practica', args=[self.unidad.slug, evidencia.pk])

        propia = self.client.get(ruta)
        self.assertEqual(propia.status_code, 200)
        self.assertEqual(b''.join(propia.streaming_content), b'\xff\xd8\xff imagen')

        detalle = self.client.get(reverse('detalle_planificacion_practica', args=[self.unidad.slug, self.plan.pk]))
        self.assertContains(detalle, 'foto-practica.jpg')

        self.client.force_login(self.ajeno)
        self.assertIn(self.client.get(ruta).status_code, (403, 404))

        self.client.force_login(self.coordinador)
        self.client.post(self.url(), self.datos_ejecucion(evidencias_eliminar=[str(evidencia.pk)]))
        self.assertEqual(EvidenciaPractica.objects.count(), 0)

    def test_el_formato_ft03_resume_y_lista_las_evidencias(self):
        self.client.post(self.url(), self.datos_ejecucion(
            evidencia_tipo='informe', evidencia_descripcion='Informe del grupo 2',
            evidencias=[self.archivo('informe-g2.pdf', b'%PDF-1.4', 'application/pdf')]))

        reporte = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), {
            'categoria_reporte': 'ejecuciones', 'desde': '2026-03-01', 'hasta': '2026-03-31'})

        self.assertContains(reporte, 'Evidencias adjuntas')
        self.assertContains(reporte, '1 × Informe de estudiante')
        # La ficha FT03 por secciones alimenta el PDF: se comprueba el registro estructurado.
        from django.test import RequestFactory

        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report

        peticion = RequestFactory().get('/', {'categoria_reporte': 'ejecuciones', 'desde': '2026-03-01',
                                             'hasta': '2026-03-31'})
        peticion.user = self.coordinador
        registro = build_unit_report(peticion, self.unidad)['dataset']['records'][0]
        seccion = next(s for s in registro['sections'] if s['title'] == 'Evidencias de la práctica')
        self.assertEqual([c['value'] for c in seccion['fields']],
                         ['1 × Informe de estudiante', 'informe-g2.pdf — Informe del grupo 2'])
        pdf = self.client.get(reverse('gestion_reporte_unidad_pdf', args=[self.unidad.slug]), {
            'categoria_reporte': 'ejecuciones', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        self.assertTrue(pdf.content.startswith(b'%PDF'))


class DesechosTests(BaseDePracticas):
    def registro(self, **campos):
        datos = dict(unidad=self.unidad, fecha_generacion=date(2026, 3, 3), clase='peligroso',
                     clave_listado='Q.01.01', nombre='Solventes usados', origen='Limpieza de boquillas',
                     estado_fisico='liquido', cantidad=Decimal('4.5'), unidad_medida='l', envase='Bidón 5 L',
                     etiquetado=True, almacenamiento='Bodega de reactivos', etapa='almacenado',
                     registrado_por=self.coordinador)
        datos.update(campos)
        return RegistroDesecho.objects.create(**datos)

    def test_una_entrega_exige_gestor_manifiesto_y_fecha(self):
        entrega = RegistroDesecho(unidad=self.unidad, fecha_generacion=date(2026, 3, 3), clase='especial',
                                  nombre='Aceite usado', cantidad=Decimal('10'), etapa='entregado')
        with self.assertRaises(ValidationError) as contexto:
            entrega.full_clean()
        self.assertEqual(set(contexto.exception.message_dict) & {'gestor_autorizado', 'manifiesto', 'fecha_entrega'},
                         {'gestor_autorizado', 'manifiesto', 'fecha_entrega'})

    def test_el_reporte_de_desechos_lista_registros_y_cuenta_entregas(self):
        self.registro()
        self.registro(nombre='Aceite usado', clase='especial', cantidad=Decimal('12'), unidad_medida='kg',
                      etapa='entregado', fecha_entrega=date(2026, 3, 8), gestor_autorizado='Gestor Ambiental S.A.',
                      licencia_gestor='MAE-LIC-123', manifiesto='MAN-2026-0042')

        pagina = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), {
            'categoria_reporte': 'desechos', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        hoja = self.client.get(reverse('gestion_reporte_unidad_xlsx', args=[self.unidad.slug]), {
            'categoria_reporte': 'desechos', 'desde': '2026-03-01', 'hasta': '2026-03-31'})

        self.assertContains(pagina, 'Solventes usados')
        self.assertContains(pagina, 'MAN-2026-0042')
        self.assertContains(pagina, 'Entregados a gestor')
        self.assertContains(pagina, 'Kilogramos registrados')
        self.assertEqual(hoja.status_code, 200)
        solo_entregados = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), {
            'categoria_reporte': 'desechos', 'desde': '2026-03-01', 'hasta': '2026-03-31', 'estado': 'entregado'})
        self.assertNotContains(solo_entregados, 'Solventes usados')
        self.assertContains(solo_entregados, 'Aceite usado')

    def test_los_desechos_se_administran_dentro_de_cada_tipo_de_unidad(self):
        from django.contrib import admin

        from apps.laboratorios.models import RegistroDesecho as DesechoDeLaboratorio

        superusuario = get_user_model().objects.create_superuser('desechos.admin')
        self.client.force_login(superusuario)
        self.registro()

        self.assertIn(DesechoDeLaboratorio, admin.site._registry)
        lista = self.client.get(reverse('admin:laboratorios_registrodesecho_changelist'), {'todas': '1'})
        self.assertContains(lista, 'Solventes usados')
        alta = self.client.get(reverse('admin:laboratorios_registrodesecho_add'))
        self.assertEqual(alta.status_code, 200)


class EntregasDesdeLaUnidadTests(BaseDePracticas):
    """La unidad registra desde su gestión la entrega al gestor, con el manifiesto escaneado."""

    def setUp(self):
        super().setUp()
        self.ruta = reverse('entregas_desechos_unidad', args=[self.unidad.slug])

    def almacenado(self, nombre='Solventes usados', **campos):
        datos = dict(unidad=self.unidad, fecha_generacion=date(2026, 3, 3), clase='peligroso', nombre=nombre,
                     cantidad=Decimal('4.5'), unidad_medida='l', etapa='almacenado',
                     registrado_por=self.coordinador)
        datos.update(campos)
        return RegistroDesecho.objects.create(**datos)

    def manifiesto(self, nombre='manifiesto-prueba.pdf', contenido=None, tipo='application/pdf'):
        contenido = contenido or pdf_legible_prueba(
            'Manifiesto ficticio MAN-PRUEBA-0001: entrega de desechos de la unidad de prueba al gestor de prueba.')
        return SimpleUploadedFile(nombre, contenido, content_type=tipo)

    def entrega(self, *desechos, **extra):
        datos = {'desechos': [d.pk for d in desechos], 'fecha_entrega': '2026-03-10',
                 'gestor_autorizado': 'Gestor de Prueba S.A.', 'licencia_gestor': 'LIC-PRUEBA-001',
                 'manifiesto': 'MAN-PRUEBA-0001', 'responsable': self.coordinador.pk,
                 'documento': self.manifiesto()}
        datos.update(extra)
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def test_la_unidad_registra_la_entrega_de_varios_desechos_con_un_manifiesto(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad

        solventes, aceite = self.almacenado(), self.almacenado('Aceite usado', clase='especial')
        tratado = self.almacenado('Ácido neutralizado', etapa='tratado', observaciones='Neutralizado.')
        pagina = self.client.get(self.ruta)
        self.assertContains(pagina, 'Registrar una entrega')
        self.assertEqual(set(pagina.context['form'].fields['desechos'].queryset), {solventes, aceite})
        self.assertNotIn(tratado, pagina.context['form'].fields['desechos'].queryset)

        respuesta = self.client.post(self.ruta, self.entrega(solventes, aceite))

        self.assertRedirects(respuesta, self.ruta)
        solventes.refresh_from_db()
        aceite.refresh_from_db()
        for desecho in (solventes, aceite):
            self.assertEqual(
                (desecho.etapa, desecho.fecha_entrega, desecho.gestor_autorizado, desecho.licencia_gestor,
                 desecho.manifiesto, desecho.responsable),
                ('entregado', date(2026, 3, 10), 'Gestor de Prueba S.A.', 'LIC-PRUEBA-001', 'MAN-PRUEBA-0001',
                 self.coordinador))
            self.assertTrue(desecho.documento.name.startswith(f'desechos/{self.unidad.pk}/'))
            self.assertTrue(desecho.documento.name.endswith('.pdf'))
            desecho.full_clean()
        # Un solo archivo respalda a todos los desechos del manifiesto.
        self.assertEqual(solventes.documento.name, aceite.documento.name)
        rastro = RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad, entidad=RegistroDesecho._meta.label,
                                                        accion='actualizar')
        self.assertEqual({r.objeto_id for r in rastro}, {str(solventes.pk), str(aceite.pk)})
        registro = rastro.get(objeto_id=str(solventes.pk))
        self.assertEqual(registro.usuario, self.coordinador)
        self.assertEqual(registro.datos_anteriores['etapa'], 'almacenado')
        self.assertEqual((registro.datos_nuevos['etapa'], registro.datos_nuevos['manifiesto'],
                          registro.datos_nuevos['documento']),
                         ('entregado', 'MAN-PRUEBA-0001', solventes.documento.name))

        lista = self.client.get(self.ruta)
        abrir = reverse('manifiesto_desecho_unidad', args=[self.unidad.slug, solventes.pk])
        self.assertContains(lista, abrir)
        self.assertContains(lista, 'No hay desechos almacenados pendientes de entrega.')
        self.assertNotContains(lista, '/media/')
        archivo = self.client.get(abrir)
        self.assertEqual(archivo.status_code, 200)
        self.assertEqual(archivo['Content-Type'], 'application/pdf')
        self.assertTrue(b''.join(archivo.streaming_content).startswith(b'%PDF'))

    def test_un_archivo_de_tipo_no_permitido_ilegible_o_muy_pesado_se_rechaza(self):
        desecho = self.almacenado()
        rechazos = (
            (self.manifiesto('manifiesto.exe', b'MZ programa'), 'El manifiesto debe ser un archivo PDF, PNG o JPG.'),
            (self.manifiesto('manifiesto.docx', b'PK documento'), 'El manifiesto debe ser un archivo PDF, PNG o JPG.'),
            (self.manifiesto('manifiesto.pdf', b'Esto no es un PDF.'), 'un PDF o una imagen legible'),
            (self.manifiesto('manifiesto.jpg', b'\xff\xd8\xff imagen rota', 'image/jpeg'),
             'un PDF o una imagen legible'),
        )
        for archivo, mensaje in rechazos:
            with self.subTest(archivo=archivo.name):
                respuesta = self.client.post(self.ruta, self.entrega(desecho, documento=archivo))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, mensaje)
        with patch('apps.recursos.presentation.desechos.MAXIMO_BYTES_MANIFIESTO', 100):
            pesado = self.client.post(self.ruta, self.entrega(desecho))
        self.assertContains(pesado, 'El manifiesto no puede superar 25 MB.')
        sin_archivo = self.client.post(self.ruta, self.entrega(desecho, documento=None))
        self.assertTrue(sin_archivo.context['form'].errors['documento'])
        desecho.refresh_from_db()
        self.assertEqual((desecho.etapa, desecho.manifiesto, bool(desecho.documento)), ('almacenado', '', False))

    def test_una_entrega_incoherente_no_guarda_nada_ni_deja_el_archivo(self):
        from pathlib import Path

        antes, despues = self.almacenado(), self.almacenado('Generado después', fecha_generacion=date(2026, 3, 12))
        carpeta = Path(MEDIA_TEMPORAL, 'desechos', str(self.unidad.pk))
        guardados = set(carpeta.glob('*'))
        # La entrega del 10 de marzo no puede incluir lo que se generó el 12.
        respuesta = self.client.post(self.ruta, self.entrega(antes, despues))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Generado después: La entrega no puede ser anterior a la generación.')
        futura = self.client.post(self.ruta, self.entrega(antes, fecha_entrega='2999-01-01'))
        self.assertContains(futura, 'la fecha no puede ser futura')
        ajeno = RegistroDesecho.objects.create(
            unidad=Unidad.objects.create(nombre='Otro laboratorio', slug='otro-laboratorio-desechos',
                                         dependencia='laboratorios', fecha_inicio=date(2026, 1, 1)),
            fecha_generacion=date(2026, 3, 1), clase='peligroso', nombre='De otra unidad', cantidad=Decimal('1'))
        de_otra = self.client.post(self.ruta, self.entrega(ajeno))
        self.assertEqual(de_otra.status_code, 200)
        self.assertTrue(de_otra.context['form'].errors['desechos'])
        for desecho in (antes, despues, ajeno):
            desecho.refresh_from_db()
            self.assertEqual((desecho.etapa, bool(desecho.documento)), ('almacenado', False))
        self.assertEqual(set(carpeta.glob('*')), guardados)

    def test_una_entrega_ya_registrada_se_completa_y_se_corrige_conservando_el_manifiesto(self):
        entregado = self.almacenado(
            etapa='entregado', fecha_entrega=date(2026, 3, 8), gestor_autorizado='Gestor de Prueba S.A.',
            manifiesto='MAN-PRUEBA-0007')
        corregir = self.ruta + f'?corregir={entregado.pk}'
        lista = self.client.get(self.ruta)
        self.assertContains(lista, 'Falta el archivo')
        self.assertContains(lista, f'?corregir={entregado.pk}')
        formulario = self.client.get(corregir)
        self.assertContains(formulario, 'Esta entrega todavía no tiene su manifiesto escaneado.')
        self.assertContains(formulario, 'value="MAN-PRUEBA-0007"')
        self.assertNotIn('desechos', formulario.context['form'].fields)

        datos = self.entrega(desechos=None, corregir=entregado.pk, manifiesto='MAN-PRUEBA-0007',
                             fecha_entrega='2026-03-08')
        self.assertRedirects(self.client.post(self.ruta, datos), self.ruta)
        entregado.refresh_from_db()
        primero = entregado.documento.name
        self.assertTrue(primero)
        self.assertEqual(entregado.licencia_gestor, 'LIC-PRUEBA-001')

        # Sin subir otro archivo se corrige el dato y se conserva el manifiesto.
        datos = self.entrega(desechos=None, corregir=entregado.pk, manifiesto='MAN-PRUEBA-0008',
                             fecha_entrega='2026-03-08', documento=None)
        self.assertRedirects(self.client.post(self.ruta, datos), self.ruta)
        entregado.refresh_from_db()
        self.assertEqual((entregado.manifiesto, entregado.documento.name), ('MAN-PRUEBA-0008', primero))
        # Solo se corrige una entrega: un desecho almacenado se registra con el formulario de entrega.
        self.assertEqual(self.client.get(self.ruta + f'?corregir={self.almacenado().pk}').status_code, 404)

    def test_quien_no_gestiona_la_seguridad_de_la_unidad_no_registra_ni_abre_el_manifiesto(self):
        from apps.gestion_unidades.models.espacios import ResponsableUnidad
        from tests.integration.test_seguimiento_gobernanza import designar

        desecho, otro = self.almacenado(), self.almacenado('Aceite usado')
        self.client.post(self.ruta, self.entrega(desecho))
        desecho.refresh_from_db()
        abrir = reverse('manifiesto_desecho_unidad', args=[self.unidad.slug, desecho.pk])
        Usuario = get_user_model()
        # Un técnico de la unidad opera recursos y mantenimiento, no la seguridad ni los reportes.
        tecnico = Usuario.objects.create_user(username='tecnico-desechos', password='clave-segura')
        identificar(tecnico, tipo_usuario='administrativo', carrera='')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=tecnico, rol='tecnico')
        for usuario in (self.ajeno, tecnico):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.ruta).status_code, 403)
                self.assertEqual(self.client.post(self.ruta, self.entrega(otro)).status_code, 403)
                self.assertEqual(self.client.get(abrir).status_code, 404)
                # Tampoco por la ruta de medios.
                self.assertEqual(self.client.get(desecho.documento.url).status_code, 404)
        otro.refresh_from_db()
        self.assertEqual(otro.etapa, 'almacenado')
        self.client.logout()
        self.assertEqual(self.client.get(self.ruta).status_code, 302)
        self.assertEqual(self.client.get(abrir).status_code, 302)
        # La Dirección lee el expediente de la unidad: abre el manifiesto, pero no registra entregas.
        direccion = Usuario.objects.create_user(username='direccion-desechos', password='clave-segura')
        identificar(direccion, tipo_usuario='administrativo', carrera='')
        designar(direccion)
        self.client.force_login(direccion)
        self.assertEqual(self.client.get(abrir).status_code, 200)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)

    def test_el_centro_de_reportes_lleva_a_registrar_la_entrega(self):
        self.almacenado()
        pagina = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), {
            'categoria_reporte': 'desechos', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        self.assertContains(pagina, 'Registrar entrega al gestor y manifiesto')
        self.assertContains(pagina, self.ruta)
        otra_categoria = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), {
            'categoria_reporte': 'seguridad', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        self.assertNotContains(otra_categoria, self.ruta)


class ConsolidadoPorTipoTests(BaseDePracticas):
    def abrir_cumplimiento(self, parametros=None):
        pagina = self.client.get(reverse('admin:reportes-evidencias-por-tipo'), parametros or {}, follow=True)
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual([estado for _url, estado in pagina.redirect_chain], [302])
        destino = urlsplit(pagina.redirect_chain[0][0])
        self.assertEqual(destino.path, reverse('admin:reportes-cumplimiento-expediente'))
        self.assertTemplateUsed(pagina, 'admin/gestion_unidades/reporteoperativounidad/cumplimiento.html')
        self.assertNotContains(pagina, 'data-directorio-unidades')
        return pagina, parse_qs(destino.query)

    def test_la_entrada_anterior_abre_el_panel_real_de_cumplimiento_con_sus_filtros(self):
        superusuario = get_user_model().objects.create_superuser('consolidado.admin')
        self.client.force_login(superusuario)
        RegistroDesecho.objects.create(unidad=self.unidad, fecha_generacion=date(2026, 3, 3), clase='peligroso',
                                       nombre='Solventes', cantidad=Decimal('1'), etapa='almacenado')
        with patch('apps.gestion_unidades.presentation.reportes_consolidados.evidencias_por_unidad',
                   side_effect=AssertionError('Esta entrada usa la lectura documental de Cumplimiento.')):
            pagina, parametros = self.abrir_cumplimiento(
                {'tipo': 'laboratorios', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        self.assertContains(pagina, 'Cumplimiento del expediente por unidad')
        self.assertContains(pagina, 'class="citt-tipo__cabecera"')
        fila = next(f for f in pagina.context['filas'] if f['unidad'] == self.unidad)
        self.assertIn('matriz', fila)
        self.assertIn('progreso_general', fila)
        self.assertIn('totales', pagina.context)
        self.assertEqual(parametros['tipo'], ['laboratorios'])
        self.assertEqual(parametros['desde'], ['2026-03-01'])
        self.assertEqual(parametros['hasta'], ['2026-03-31'])
        self.assertEqual(pagina.context['tipo'], 'laboratorios')
        self.assertEqual((pagina.context['desde'], pagina.context['hasta']), (date(2026, 3, 1), date(2026, 3, 31)))
        # El menú conserva la entrada existente; no ofrece una portada paralela.
        indice = self.client.get(reverse('admin:index'))
        self.assertContains(indice, 'Cumplimiento del expediente por unidad')
        self.assertNotContains(indice, 'Unidades por tipo')

    def test_el_administrador_de_una_unidad_solo_ve_la_suya(self):
        otra = Unidad.objects.create(nombre='Laboratorio ajeno', slug='laboratorio-ajeno-f2',
                                     dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.coordinador.is_staff = True
        self.coordinador.save(update_fields=['is_staff'])
        # El coordinador administra su unidad; el reporte operativo se lo permite.
        from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad

        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=self.unidad)

        from django.contrib import admin
        # El menú general consulta otra base de Centros I+D. El alcance del
        # directorio se comprueba con el permiso real y el resto del admin se
        # sustituye únicamente al dibujar este caso de coordinador.
        with patch.object(admin.site, 'each_context', return_value={
                'site_title': 'Administración', 'site_header': 'Administración',
                'has_permission': True, 'available_apps': [], 'is_popup': False}):
            pagina = self.client.get(reverse('admin:reportes-evidencias-por-tipo'), {'tipo': 'laboratorios'})

        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context['title'], 'Expedientes de las unidades')
        self.assertContains(pagina, 'Expedientes de las unidades')
        self.assertEqual([f['unidad'] for f in pagina.context['filas']], [self.unidad])
        self.assertNotContains(pagina, otra.nombre)
        self.assertEqual(urlsplit(pagina.context['filas'][0]['url']).path,
                         reverse('gestion_expediente_unidad', args=[self.unidad.slug]))

    def test_la_entrada_abre_todos_los_tipos_en_cumplimiento_sin_filtrar_laboratorios_por_omision(self):
        direccion = get_user_model().objects.create_superuser('directorio-todos-tipos')
        self.client.force_login(direccion)
        unidades = {base: Unidad.objects.create(nombre=nombre, slug='directorio-' + base.replace('_', '-'),
            dependencia=base, fecha_inicio=date(2026, 1, 1)) for base, nombre in (
                ('plantas_piloto', 'Planta QA'), ('centro_experimental', 'Centro QA'), ('observatorios', 'Observatorio QA'))}
        inactiva = Unidad.objects.create(nombre='Unidad inactiva fuera del directorio', slug='directorio-inactiva',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1), activo=False)
        with patch('apps.gestion_unidades.presentation.reportes_consolidados.evidencias_por_unidad',
                   side_effect=AssertionError('Cumplimiento usa su propio cálculo documental.')):
            pagina, parametros = self.abrir_cumplimiento()
        self.assertNotIn('tipo', parametros)
        self.assertEqual(pagina.context['tipo'], '')
        self.assertEqual({g['codigo'] for g in pagina.context['grupos']},
                         {'laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'})
        self.assertEqual({f['unidad'].pk for f in pagina.context['filas']},
                         {self.unidad.pk, *(u.pk for u in unidades.values())})
        self.assertNotContains(pagina, inactiva.nombre)
        self.assertIn('totales', pagina.context)
        self.assertContains(pagina, 'class="citt-tipo__cabecera"', count=4)
        self.assertContains(pagina, 'class="citt-unidad"', count=4)
        for grupo in pagina.context['grupos']:
            nombres = [fila['unidad'].nombre for fila in grupo['filas']]
            self.assertEqual(nombres, sorted(nombres, key=str.casefold))
            self.assertIn('totales', grupo)
            self.assertContains(pagina, grupo['nombre'])

    def test_conserva_las_validaciones_de_enlaces_anteriores(self):
        direccion = get_user_model().objects.create_superuser('directorio-validaciones')
        self.client.force_login(direccion)
        ruta = reverse('admin:reportes-evidencias-por-tipo')
        for query in ({'tipo': 'inexistente'}, {'desde': 'fecha-inválida'}, {'anio': 'texto'}):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(ruta, query).status_code, 400)
        # La regla compartida de reportes ordena los extremos invertidos.
        pagina, parametros = self.abrir_cumplimiento({'desde': '2026-03-31', 'hasta': '2026-03-01'})
        self.assertEqual((parametros['desde'], parametros['hasta']), (['2026-03-01'], ['2026-03-31']))
        self.assertEqual((pagina.context['desde'], pagina.context['hasta']), (date(2026, 3, 1), date(2026, 3, 31)))

    def test_las_cifras_siguen_disponibles_en_el_calculo_de_evidencias(self):
        from apps.gestion_unidades.presentation.reportes_consolidados import evidencias_por_unidad
        direccion = get_user_model().objects.create_superuser('calculo-evidencias')
        RegistroDesecho.objects.create(unidad=self.unidad, fecha_generacion=date(2026, 3, 3), clase='peligroso',
            nombre='Solventes', cantidad=Decimal('1'), etapa='almacenado')
        filas, totales = evidencias_por_unidad(['laboratorios'], date(2026, 3, 1), date(2026, 3, 31), direccion)
        fila = next(f for f in filas if f['unidad'] == self.unidad)
        self.assertEqual(fila['planificaciones'], 1)
        self.assertEqual(fila['desechos_almacenados'], 1)
        self.assertEqual(totales['planificaciones'], 1)
