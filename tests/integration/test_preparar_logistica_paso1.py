"""Publicación metodológica aislada: preservación, seguridad y simulación sin escrituras."""
import hashlib
import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.laboratorios.operacion.management.commands.preparar_logistica_paso1 import MARCA, RECURSO_MARCA, guia_academica, huella_ficha, recursos_del_paquete
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import AREAS_PASO1, FACULTAD_UPEC, FUENTES, GUIAS, MATRIZ_ASIGNATURAS, SLUG, documento_html
from apps.formacion.models.asignaturas import Asignatura
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad


class PrepararLogisticaPaso1Tests(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)
        self.media = self.base / 'media'
        self.enterContext(override_settings(BASE_DIR=self.base, MEDIA_ROOT=self.media))
        self.unidad = Unidad.objects.create(
            slug=SLUG, nombre='Laboratorio de Logística', dependencia='laboratorios',
            descripcion='Descripción institucional que se conserva', fecha_inicio=date(2025, 1, 1),
        )
        for codigo, area in AREAS_PASO1.items():
            EspacioReservable.objects.create(
                unidad=self.unidad, codigo=codigo, nombre=area['titulo'], capacidad=8,
                reservable=False, politica_reserva='tecnico',
            )
        self.asignatura = Asignatura.objects.create(
            unidad=self.unidad, codigo='LOGT-TIC-APLICADAS-A-LA-LOGISTICA',
            nombre='TIC aplicadas a la logística', carrera='Logística y Transporte',
            semestre='Semestre 4', descripcion='Descripción editable de la asignatura',
        )
        self.otra = Unidad.objects.create(
            slug='otro-laboratorio', nombre='Otro laboratorio', dependencia='laboratorios',
            descripcion='Sin modificar', fecha_inicio=date(2025, 1, 1),
        )
        self.manifiesto = self.base / 'revision.json'
        self.revisar()

    def revisar(self):
        hashes = [hashlib.sha256(datos['html'].encode('utf-8')).hexdigest()
                  for datos in recursos_del_paquete(list(self.unidad.asignaturas.all())) if datos['html']]
        self.manifiesto.write_text(json.dumps({
            'sha256': hashes, 'motor': 'Fixture de revisión aislada',
            'resultado': 'sin_amenazas', 'fecha': '2026-10-11', 'fuentes_enlaces_revisadas': True,
        }), encoding='utf-8')

    def correr(self, aplicar=False, **opciones):
        salida = StringIO()
        if aplicar:
            opciones.update(aplicar=True, manifiesto_revision=self.manifiesto)
        call_command('preparar_logistica_paso1', stdout=salida, **opciones)
        return salida.getvalue()

    def test_simulacion_y_modo_por_defecto_solo_select_sin_archivos(self):
        inicial = self.unidad.facultad
        for opciones in ({'simular': True}, {}):
            with CaptureQueriesContext(connection) as consultas:
                texto = self.correr(**opciones)
            self.assertIn('[simulación SELECT]', texto)
            self.assertTrue(consultas.captured_queries)
            self.assertTrue(all(fila['sql'].lstrip().upper().startswith('SELECT') for fila in consultas))
            self.assertFalse(any('FOR UPDATE' in fila['sql'].upper() for fila in consultas))
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.facultad, inicial)
        self.assertFalse(FichaArea.objects.exists())
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertFalse(self.media.exists())
        self.assertFalse((self.base / 'var').exists())

    def test_aplicar_requiere_revision_exacta_antes_de_escribir_o_respaldar(self):
        with self.assertRaisesMessage(CommandError, '--manifiesto-revision'):
            call_command('preparar_logistica_paso1', aplicar=True, stdout=StringIO())
        self.assertFalse(FichaArea.objects.exists())
        self.assertFalse((self.base / 'var').exists())
        self.manifiesto.write_text(json.dumps({'sha256': []}), encoding='utf-8')
        with self.assertRaisesMessage(CommandError, 'no cubre los hashes exactos'):
            self.correr(aplicar=True)
        self.assertFalse(FichaArea.objects.exists())
        self.assertFalse(self.media.exists())

    def test_publica_seis_fichas_y_treinta_recursos_con_respaldo_y_sin_tocar_operacion(self):
        ids = dict(self.unidad.espacios_reservables.values_list('codigo', 'pk'))
        self.correr(aplicar=True)
        self.assertEqual(FichaArea.objects.filter(espacio__unidad=self.unidad, publicada=True).count(), 6)
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).count(), 30)
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).exclude(archivo='').count(), 18)
        self.assertEqual(ElementoFichaArea.objects.filter(ficha__espacio__unidad=self.unidad).count(), 18)
        self.assertEqual(len(list(self.media.rglob('*.html'))), 18)
        self.assertEqual(len(list((self.base / 'var' / 'backups').glob('*.json'))), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1)
        for recurso in Recurso.objects.filter(unidad=self.unidad):
            self.assertTrue(RECURSO_MARCA.fullmatch(recurso.palabras_clave))
            self.assertTrue(recurso.seguridad_verificada)
            self.assertEqual((recurso.visibilidad, recurso.activo), ('publica', True))
            self.assertFalse(recurso.navegador_remoto)
        self.unidad.refresh_from_db()
        self.asignatura.refresh_from_db()
        self.otra.refresh_from_db()
        self.assertEqual(self.unidad.facultad, FACULTAD_UPEC)
        self.assertEqual(self.unidad.descripcion, 'Descripción institucional que se conserva')
        self.assertEqual(self.asignatura.descripcion, 'Descripción editable de la asignatura')
        self.assertEqual(self.asignatura.nombre, 'TIC aplicadas a la logística')
        self.assertEqual(self.otra.descripcion, 'Sin modificar')
        self.assertEqual(dict(self.unidad.espacios_reservables.values_list('codigo', 'pk')), ids)
        self.assertTrue(all(not fila.reservable and fila.capacidad == 8
                            for fila in self.unidad.espacios_reservables.all()))
        self.assertFalse(self.unidad.cursos.exists())

    def test_repetir_es_idempotente_sin_nuevos_adjuntos_auditoria_o_respaldo(self):
        self.correr(aplicar=True)
        self.assertIn('sin cambios', self.correr(aplicar=True))
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).count(), 30)
        self.assertEqual(len(list(self.media.rglob('*.html'))), 18)
        self.assertEqual(len(list((self.base / 'var' / 'backups').glob('*.json'))), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1)

    def test_conserva_ficha_manual_y_elementos_existentes(self):
        area = self.unidad.espacios_reservables.get(codigo='LOG-ALMACEN')
        ficha = FichaArea.objects.create(espacio=area, que_es='Contenido institucional revisado', publicada=True)
        elemento = ElementoFichaArea.objects.create(ficha=ficha, tipo='equipo', nombre='Equipo propio')
        self.assertIn('se conserva la ficha editada', self.correr(aplicar=True))
        ficha.refresh_from_db()
        self.assertEqual(ficha.que_es, 'Contenido institucional revisado')
        self.assertTrue(ficha.publicada)
        self.assertTrue(ElementoFichaArea.objects.filter(pk=elemento.pk, ficha=ficha).exists())
        self.assertTrue(Recurso.objects.filter(nombre='Ficha metodológica: ' + AREAS_PASO1['LOG-ALMACEN']['titulo']).exists())

    def test_modificacion_manual_ficha_o_recurso_se_conserva_incluso_desactivacion(self):
        self.correr(aplicar=True)
        ficha = FichaArea.objects.get(espacio__codigo='LOG-ALMACEN', espacio__unidad=self.unidad)
        ficha.seguridad = 'Procedimiento autorizado propio'
        ficha.publicada = False
        ficha.save(update_fields=['seguridad', 'publicada'])
        recurso = Recurso.objects.get(unidad=self.unidad, palabras_clave__startswith='log-p1:sop-almacen;')
        recurso.nombre = 'Procedimiento personalizado'
        recurso.activo = False
        recurso.visibilidad = 'interna'
        try:
            recurso.save(update_fields=['nombre', 'activo', 'visibilidad'])
        finally:
            recurso.archivo.close()
        self.correr(aplicar=True)
        ficha.refresh_from_db()
        recurso.refresh_from_db()
        self.assertEqual(ficha.seguridad, 'Procedimiento autorizado propio')
        self.assertFalse(ficha.publicada)
        self.assertEqual((recurso.nombre, recurso.activo, recurso.visibilidad), ('Procedimiento personalizado', False, 'interna'))
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).count(), 30)

    def test_perdida_de_marca_de_recurso_no_crea_otra_copia(self):
        self.correr(aplicar=True)
        recurso = Recurso.objects.get(unidad=self.unidad, palabras_clave__startswith='log-p1:datos;')
        recurso.palabras_clave = 'Material del docente'
        try:
            recurso.save(update_fields=['palabras_clave'])
        finally:
            recurso.archivo.close()
        self.correr(aplicar=True)
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).count(), 30)
        recurso.refresh_from_db()
        self.assertEqual(recurso.palabras_clave, 'Material del docente')

    def test_ficha_legado_reconocida_actualiza_textos_sin_borrar_elementos(self):
        area = self.unidad.espacios_reservables.get(codigo='LOG-ALMACEN')
        from apps.gestion_unidades.management.fichas_area import FUENTES_DE_CARGADOR
        ficha = FichaArea.objects.create(espacio=area, que_es='Texto de cargador conocido', fuente=FUENTES_DE_CARGADOR[0])
        elemento = ElementoFichaArea.objects.create(ficha=ficha, tipo='equipo', nombre='Referencia que se conserva')
        with patch.dict('apps.laboratorios.operacion.management.commands.preparar_logistica_paso1.LEGADO_FICHAS_SHA256',
                        {'LOG-ALMACEN': huella_ficha(ficha)}):
            self.correr(aplicar=True)
        ficha.refresh_from_db()
        self.assertTrue(ficha.publicada)
        self.assertTrue(ficha.fuente.startswith(MARCA))
        self.assertEqual(ficha.que_es, AREAS_PASO1['LOG-ALMACEN']['que_es'])
        self.assertTrue(ElementoFichaArea.objects.filter(pk=elemento.pk).exists())

    def test_activa_investigacion_con_contenidos_sin_alterar_modalidades_y_respeta_desactivacion_posterior(self):
        modulo = self.unidad.modulos_contenido.get(clave='investigacion-formativa')
        modulo.activo = False
        modulo.save(update_fields=['activo'])
        modalidades = list(self.unidad.tipos_laboratorio.values_list('pk', flat=True))
        self.correr(aplicar=True)
        modulo.refresh_from_db()
        self.assertTrue(modulo.activo)
        self.assertEqual(list(self.unidad.tipos_laboratorio.values_list('pk', flat=True)), modalidades)
        self.assertTrue(self.unidad.carpetas.filter(seccion_planta='6.2').exists())
        self.assertTrue(self.unidad.carpetas.filter(seccion_planta='6.3').exists())
        modulo.activo = False
        modulo.save(update_fields=['activo'])
        self.assertIn('se conserva la desactivación posterior', self.correr(aplicar=True))
        modulo.refresh_from_db()
        self.assertFalse(modulo.activo)

    def test_facultad_manual_se_conserva(self):
        self.unidad.facultad = 'Dependencia confirmada por la unidad'
        self.unidad.save(update_fields=['facultad'])
        self.correr(aplicar=True)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.facultad, 'Dependencia confirmada por la unidad')

    def test_area_faltante_impide_actualizacion_parcial_y_archivos(self):
        self.unidad.espacios_reservables.get(codigo='LOG-AREA-ERP').delete()
        with self.assertRaisesMessage(CommandError, 'Faltan áreas existentes'):
            self.correr(aplicar=True)
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse((self.base / 'var').exists())
        self.assertFalse(self.media.exists())

    def test_error_posterior_limpia_solo_archivos_nuevos_y_revierte_base(self):
        self.media.mkdir(parents=True)
        previo = self.media / 'evidencia-previa.txt'
        previo.write_text('No eliminar', encoding='utf-8')
        with patch('apps.laboratorios.operacion.management.commands.preparar_logistica_paso1.registrar_auditoria', side_effect=RuntimeError('fallo')):
            with self.assertRaisesMessage(RuntimeError, 'fallo'):
                self.correr(aplicar=True)
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(FichaArea.objects.exists())
        self.assertFalse(list(self.media.rglob('*.html')))
        self.assertEqual(previo.read_text(encoding='utf-8'), 'No eliminar')
        self.assertEqual(len(list((self.base / 'var' / 'backups').glob('*.json'))), 1)

    def test_no_mezcla_carpeta_del_expediente_con_contenido(self):
        CarpetaRecurso.objects.create(
            unidad=self.unidad, nombre='Inducción y operación segura', del_expediente=True,
            modulo_config=self.unidad.modulos_contenido.get(clave='informacion-general'), seccion_planta='1.4',
        )
        with self.assertRaisesMessage(CommandError, 'tiene otro uso'):
            self.correr(aplicar=True)
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(FichaArea.objects.exists())

    def test_reclasifica_solo_documento_de_compra_identificado_sin_borrar_archivo(self):
        recurso = Recurso.objects.create(
            unidad=self.unidad, nombre='Guia de laboratorio', descripcion='guia lab',
            nombre_original='SOLICITUD_DE_COMPRA_11983_2026.pdf',
            hash_sha256='334909dfb31c4da9660353a94ee34624eecb0468fae6d333d6ca00a249f6da7e',
            url='https://upec.edu.ec/', visibilidad='publica', seguridad_verificada=True,
        )
        self.correr(aplicar=True)
        recurso.refresh_from_db()
        self.assertEqual(recurso.visibilidad, 'interna')
        self.assertIn('Solicitud de compra', recurso.nombre)
        self.assertEqual(recurso.url, 'https://upec.edu.ec/')

    def test_reclasifica_enlace_abe_exactamente_identificado_y_conserva_url(self):
        recurso = Recurso.objects.create(
            unidad=self.unidad, nombre='Virtual reality', descripcion='virtual',
            url='https://www.labxchange.org/library/clusters/lx-cluster:abe',
            visibilidad='publica', fuente='interna', seguridad_verificada=True,
        )
        with CaptureQueriesContext(connection) as consultas:
            salida = self.correr(simular=True)
        self.assertIn('1 enlaces reclasificados', salida)
        self.assertTrue(all(fila['sql'].lstrip().upper().startswith('SELECT') for fila in consultas))
        recurso.refresh_from_db()
        self.assertEqual(recurso.nombre, 'Virtual reality')
        self.correr(aplicar=True)
        recurso.refresh_from_db()
        self.assertEqual(recurso.nombre, 'LabXchange ABE — fundamentos de biotecnología')
        self.assertIn('No corresponde a realidad virtual logística', recurso.descripcion)
        self.assertEqual((recurso.fuente, recurso.visibilidad), ('externa', 'interna'))
        self.assertEqual(recurso.url, 'https://www.labxchange.org/library/clusters/lx-cluster:abe')
        self.assertIn('sin cambios', self.correr(aplicar=True))

    def test_preserva_ediciones_manuales_del_enlace_y_no_toca_otra_unidad(self):
        casos = [
            {'nombre': 'Referencia revisada por el docente'},
            {'descripcion': 'Contexto revisado por el responsable'},
            {'url': 'https://www.labxchange.org/'},
            {'visibilidad': 'restringida'},
            {'unidad': self.otra},
        ]
        registros = []
        for cambio in casos:
            valores = dict(
                unidad=self.unidad, nombre='Virtual reality', descripcion='virtual',
                url='https://www.labxchange.org/library/clusters/lx-cluster:abe',
                visibilidad='publica', fuente='interna', seguridad_verificada=True,
            )
            valores.update(cambio)
            registros.append((Recurso.objects.create(**valores), valores))
        self.correr(aplicar=True)
        for recurso, valores in registros:
            recurso.refresh_from_db()
            self.assertEqual(recurso.nombre, valores['nombre'])
            self.assertEqual(recurso.descripcion, valores['descripcion'])
            self.assertEqual(recurso.url, valores['url'])
            self.assertEqual(recurso.visibilidad, valores['visibilidad'])
            self.assertEqual(recurso.fuente, 'interna')

    def test_matriz_conserva_tres_carreras_y_relaciona_23_asignaturas_con_evidencia(self):
        self.assertEqual(len(MATRIZ_ASIGNATURAS), 23)
        self.assertEqual({fila['carrera'] for fila in MATRIZ_ASIGNATURAS.values()}, {
            'Logística y Transporte', 'Comercio Exterior', 'Administración de Empresas',
        })
        for fila in MATRIZ_ASIGNATURAS.values():
            self.assertTrue(fila['resultado'])
            self.assertTrue(fila['evidencia'])
            self.assertTrue(set(fila['areas']).issubset(AREAS_PASO1))
        guia = guia_academica([self.asignatura])
        documento = documento_html('matriz-academica', guia)
        self.assertIn(self.asignatura.nombre, documento)
        self.assertNotIn('Comercio electrónico —', documento)

    def test_documentos_estaticos_escapan_texto_y_no_ejecutan_codigo(self):
        for clave, guia in GUIAS.items():
            texto = documento_html(clave, guia)
            self.assertIn('Content-Security-Policy', texto)
            self.assertNotIn('<script', texto.lower())
            self.assertNotIn('<iframe', texto.lower())
            self.assertNotIn('javascript:', texto.lower())
            self.assertNotIn('onclick=', texto.lower())
            self.assertGreater(len(texto), 3000)
        guia = dict(GUIAS['datos'], titulo='<img src=x onerror=alert(1)>')
        texto = documento_html('datos', guia)
        self.assertIn('&lt;img', texto)
        self.assertNotIn('<img', texto)
        self.assertTrue(all(fila['url'].startswith('https://') for fila in FUENTES.values()))
