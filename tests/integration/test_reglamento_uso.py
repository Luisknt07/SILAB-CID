"""El reglamento de uso de la unidad es un documento principal permanente, como el protocolo.

Se redacta con el editor guiado sobre un texto estándar que solo cambia por tipo de unidad, sale con el
formato de los documentos principales, se envía con QR y la Dirección confirma su conformidad. Al enviarse,
su contenido se publica en la página de la unidad. Ya no es una consulta de «Respaldo para auditoría».
"""
from datetime import date
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.aprobacion_en_linea import decidir_documento_qr, enviar_documento_qr
from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente, es_permanente
from apps.documentos.presentation.expediente import construir_expediente, generar_documento, tramo_del_documento
from apps.documentos.presentation.expediente_redaccion import (
    avance, componer, datos_automaticos, obtener_redaccion, pdf_del_documento,
)
from apps.documentos.presentation.guia_reportes import REPORTES
from apps.documentos.presentation.perfil_unidades import aplica_documento
from apps.documentos.presentation.reglamento_uso import texto_estandar
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.gestion_reportes import CATEGORIAS_RESPALDO, REPORT_FAMILIES
from apps.gestion_unidades.presentation.reportes_auditoria import REPORTES_DE_RESPALDO
from apps.recursos.models.recursos import ReglamentoUnidad
from apps.reservas.models.seguridad import RequisitoAcceso
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.test_seguimiento_gobernanza import designar

TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')


def reglamento_completo(documento, **cambios):
    contenido = dict(obtener_redaccion(documento).contenido, revision_propuestas='revisado')
    contenido.update(cambios)
    return contenido


class ReglamentoUsoTests(BaseDeRedaccion):
    def setUp(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(capacidad_personas=24, horario_atencion='Lunes a viernes, 08:00 a 16:00')
        self.unidad.refresh_from_db()
        self.reglamento = self.documento('REGLAMENTO-USO', corte='')

    def unidad_de(self, tipo):
        if tipo == 'laboratorios':
            return self.unidad
        return Unidad.objects.create(nombre=f'Unidad ficticia {tipo}', slug=f'unidad-ficticia-{tipo}'.replace('_', '-'),
            dependencia=tipo, administrador=self.coordinador, fecha_inicio=date(2025, 1, 1))

    def reglamento_de(self, unidad):
        return next(d for d in construir_expediente(unidad, 2026, hoy=date(2026, 9, 22))
                    if d.exigido.codigo == 'REGLAMENTO-USO')

    def emitir_y_enviar(self, **cambios):
        DocumentoElaborado.objects.create(documento=self.reglamento, version=1,
            contenido=reglamento_completo(self.reglamento, **cambios))
        generar_documento(self.reglamento, self.coordinador)
        enviar_documento_qr(self.reglamento, self.coordinador,
            token=self.reglamento.verificacion_qr, version=self.reglamento.version)
        return ConstanciaDocumento.objects.get(token=self.reglamento.verificacion_qr)

    # -- el exigido -------------------------------------------------------------------------------------

    def test_es_un_documento_base_permanente_despues_del_protocolo_y_aplica_a_los_cuatro_tipos(self):
        e = self.reglamento.exigido
        self.assertEqual((e.periodicidad, e.anexo_de_id, e.fuente_reporte, e.carpeta), ('unica', None, 'reglamento', 'planeacion'))
        self.assertTrue(e.redactable and e.generable and e.cargable and e.requiere_firma)
        self.assertTrue(es_permanente(self.reglamento))
        for tipo in TIPOS:
            self.assertTrue(aplica_documento(e, tipo, base=tipo), tipo)
        base = sorted((d for d in construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
                       if d.exigido.periodicidad == 'unica' and not d.exigido.es_anexo),
                      key=lambda d: (d.exigido.orden, d.exigido.codigo))
        self.assertEqual([d.exigido.codigo for d in base], ['RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'REGLAMENTO-USO'])
        nombres = {tipo: self.reglamento_de(self.unidad_de(tipo)).nombre_documental for tipo in TIPOS}
        self.assertEqual(nombres, {
            'laboratorios': 'Reglamento de uso del laboratorio',
            'plantas_piloto': 'Reglamento de uso de la planta piloto',
            'centro_experimental': 'Reglamento de uso del centro experimental',
            'observatorios': 'Reglamento de uso del observatorio'})

    # -- el editor ----------------------------------------------------------------------------------------

    def test_el_editor_propone_el_texto_estandar_con_los_datos_de_la_unidad_y_cambia_por_tipo(self):
        RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND-QA', nombre='Inducción ficticia de ingreso',
                                       tipo='induccion')
        contenido = obtener_redaccion(self.reglamento).contenido
        self.assertIn('Laboratorio de redes', contenido['objeto_reglamento'])
        self.assertIn('reactivos', contenido['recursos_reglamento'])
        self.assertEqual(contenido['firma_nombre'], 'Ana Coordinadora')
        self.assertEqual(contenido['revision_propuestas'], '')
        # Lo que la plataforma ya sabe entra solo, sin escribirlo en el editor.
        automaticos = datos_automaticos(self.reglamento, *tramo_del_documento(self.reglamento), contenido)
        texto = str(automaticos)
        for dato in ('Laboratorio de redes', 'Lunes a viernes, 08:00 a 16:00', '24 personas',
                     'Inducción ficticia de ingreso', 'Luis Técnico', 'Ana Coordinadora'):
            self.assertIn(dato, texto)
        # Sin la revisión el documento no está listo; con ella, el texto propuesto basta.
        self.assertLess(avance('reglamento', contenido)['porcentaje'], 100)
        self.assertEqual(avance('reglamento', dict(contenido, revision_propuestas='revisado'))['porcentaje'], 100)
        # Mismo texto para todas las unidades del mismo tipo; solo cambia el nombre de la unidad.
        otro = SimpleNamespace(nombre='Otro laboratorio ficticio')
        self.assertEqual({k: v.replace('Laboratorio de redes', 'Otro laboratorio ficticio')
                          for k, v in texto_estandar(self.unidad, 'laboratorios').items()},
                         texto_estandar(otro, 'laboratorios'))
        propios = {
            'plantas_piloto': ('Buenas Prácticas de Manufactura', 'control de calidad'),
            'centro_experimental': ('agroquímicos', 'maquinaria agrícola', 'animales'),
            'observatorios': ('política de datos', 'fuentes'),
        }
        for tipo, frases in propios.items():
            with self.subTest(tipo=tipo):
                propio = obtener_redaccion(self.reglamento_de(self.unidad_de(tipo))).contenido
                propuesto = ' '.join(propio[clave] for clave in texto_estandar(self.unidad, tipo))
                for frase in frases:
                    self.assertIn(frase, propuesto)
                self.assertNotIn('mandil', propuesto)
        self.assertNotIn('reactivos', ' '.join(texto_estandar(self.unidad, 'observatorios').values()))

    def test_lo_que_la_unidad_ya_habia_escrito_en_su_reglamento_es_el_punto_de_partida(self):
        ReglamentoUnidad.objects.filter(unidad=self.unidad).update(
            seguridad='Medida propia ficticia QA-01.\nOtra medida propia ficticia QA-02.')
        contenido = obtener_redaccion(self.reglamento).contenido
        self.assertIn('Medida propia ficticia QA-01.', contenido['seguridad_reglamento'])
        self.assertIn('Otra medida propia ficticia QA-02.', contenido['seguridad_reglamento'])
        # Lo genérico con el que nació la unidad no sustituye el texto estándar.
        self.assertIn('Buenas', texto_estandar(self.unidad, 'plantas_piloto')['acceso_reglamento'])
        self.assertIn('inducción de la unidad', contenido['acceso_reglamento'])

    # -- formato, envío, publicación y conformidad ----------------------------------------------------------

    def test_sale_con_el_formato_de_los_documentos_principales(self):
        for tipo, prefijo in (('laboratorios', 'LAB'), ('observatorios', 'OBS')):
            with self.subTest(tipo=tipo):
                documento = self.reglamento_de(self.unidad_de(tipo))
                contenido = reglamento_completo(documento)
                compuesto = componer(documento, contenido, *tramo_del_documento(documento))
                self.assertEqual(compuesto['periodo'], 'Documento permanente')
                self.assertEqual(len(compuesto['secciones']), 9)
                pdf = PdfReader(BytesIO(pdf_del_documento(documento,
                    DocumentoElaborado(documento=documento, contenido=contenido), *tramo_del_documento(documento))))
                paginas = [p.extract_text() or '' for p in pdf.pages]
                texto = '\n'.join(paginas)
                self.assertIn(f'Código de referencia: SLCID-{prefijo}-REGLAMENTO', paginas[0])
                self.assertIn('CONTENIDO', paginas[1])
                self.assertIn(f'Código de referencia: SLCID-{prefijo}-REGLAMENTO · Cobertura: Documento permanente', texto)
                self.assertIn('HORARIO DE ATENCIÓN Y RESERVAS', texto)
                self.assertIn('RESPONSABILIDADES, DAÑOS Y SANCIONES', texto)
                self.assertNotIn('Versión:', texto)
                self.assertNotIn('BORRADOR', texto)
                self.assertNotIn('Revisión del texto propuesto', texto)

    def test_se_genera_se_envia_se_publica_y_la_direccion_confirma_su_conformidad(self):
        director = get_user_model().objects.create_superuser('direccion-reglamento', password=None,
                                                              first_name='Directora', last_name='de prueba')
        designar(director)
        for usuario, cedula in ((self.coordinador, '0400000011'), (director, '0400000012')):
            usuario.profile.cedula = cedula
            usuario.profile.save(update_fields=['cedula'])
        constancia = self.emitir_y_enviar(conducta_reglamento='<ul><li>Norma ficticia QA-REG-01.</li></ul>')
        self.reglamento.refresh_from_db()
        self.assertEqual(self.reglamento.estado, 'validado')
        self.assertEqual(constancia.periodo, 'Documento permanente')
        # Al enviarse, la página pública muestra el reglamento oficial.
        publicado = ReglamentoUnidad.objects.get(unidad=self.unidad)
        self.assertTrue(publicado.activo)
        self.assertEqual(publicado.titulo, 'Reglamento de uso del laboratorio: Laboratorio de redes')
        self.assertIn('Norma ficticia QA-REG-01.', publicado.normas_generales.splitlines())
        self.assertIn('Horario de atención: Lunes a viernes, 08:00 a 16:00.', publicado.reservas_horarios)
        self.assertIn('Aforo: 24 personas.', publicado.reservas_horarios)
        self.assertIn('protocolo de seguridad', publicado.seguridad)
        self.assertNotIn('<', publicado.normas_generales + publicado.seguridad + publicado.equipos_materiales)
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad, entidad='recursos.ReglamentoUnidad', accion='actualizar').exists())
        self.assertContains(self.client.get(self.unidad.get_absolute_url()), 'Norma ficticia QA-REG-01.')
        # La Dirección, con su designación de seguimiento, confirma la conformidad una vez por versión.
        self.assertFalse(aprobacion_vigente(self.reglamento))
        decidir_documento_qr(self.reglamento, director, token=constancia.token,
                             version=constancia.version, decision='aprobar')
        self.reglamento.refresh_from_db()
        self.assertTrue(aprobacion_vigente(self.reglamento, inspeccionar=True))
        # Se hereda al año siguiente con el mismo archivo y su conformidad.
        heredado = next(d for d in construir_expediente(self.unidad, 2027)
                        if d.exigido.codigo == 'REGLAMENTO-USO')
        self.assertEqual(heredado.recurso_id, self.reglamento.recurso_id)
        self.assertTrue(aprobacion_vigente(heredado))

    def test_una_redaccion_posterior_al_pdf_no_se_publica_hasta_generar_de_nuevo(self):
        from apps.documentos.presentation.reglamento_uso import publicar
        DocumentoElaborado.objects.create(documento=self.reglamento, version=1,
            contenido=reglamento_completo(self.reglamento))
        generar_documento(self.reglamento, self.coordinador)
        DocumentoElaborado.objects.filter(documento=self.reglamento).update(version=2)
        antes = ReglamentoUnidad.objects.get(unidad=self.unidad).titulo
        self.assertIsNone(publicar(self.reglamento))
        self.assertEqual(ReglamentoUnidad.objects.get(unidad=self.unidad).titulo, antes)

    # -- la consulta retirada y la migración --------------------------------------------------------------

    def test_la_consulta_reglamento_ya_no_existe_en_el_respaldo_para_auditoria(self):
        self.assertNotIn('reglamento', CATEGORIAS_RESPALDO)
        self.assertNotIn('reglamento', REPORTES_DE_RESPALDO)
        self.assertNotIn('reglamento', REPORTES)
        self.assertNotIn('reglamento', {codigo for _familia, categorias in REPORT_FAMILIES for codigo, _n in categorias})
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
                                    dict(categoria_reporte='reglamento', desde='2026-03-01', hasta='2026-07-31'))
        self.assertEqual(respuesta.status_code, 400)

    def test_la_migracion_agrega_el_exigido_y_su_fila_en_el_ultimo_expediente_preparado(self):
        migracion = import_module('apps.documentos.migrations.0031_reglamento_uso_documento_principal')
        protocolo = DocumentoExpediente.objects.get(unidad=self.unidad, anio=2026, exigido__codigo='PROTOCOLO-BIOSEGURIDAD')
        construir_expediente(self.unidad, 2025, hoy=date(2025, 9, 22))
        DocumentoExpediente.objects.filter(exigido__codigo='REGLAMENTO-USO').delete()
        DocumentoExigido.objects.filter(codigo='REGLAMENTO-USO').delete()
        otros = list(DocumentoExigido.objects.order_by('codigo').values_list('codigo', 'nombre', 'orden', 'activo'))
        editor = SimpleNamespace(connection=connection)
        migracion.agregar_reglamento(apps, editor)
        migracion.agregar_reglamento(apps, editor)
        exigido = DocumentoExigido.objects.get(codigo='REGLAMENTO-USO')
        self.assertEqual((exigido.fuente_reporte, exigido.periodicidad, exigido.orden, exigido.activo),
                         ('reglamento', 'unica', 18, True))
        self.assertEqual(list(DocumentoExigido.objects.exclude(pk=exigido.pk).order_by('codigo')
                              .values_list('codigo', 'nombre', 'orden', 'activo')), otros)
        filas = DocumentoExpediente.objects.filter(exigido=exigido)
        self.assertEqual(list(filas.values_list('unidad_id', 'anio', 'corte', 'estado')),
                         [(self.unidad.pk, 2026, '', 'pendiente')])
        fila = filas.get()
        self.assertEqual((fila.abre_el, fila.vence_el, fila.tramo_inicio, fila.tramo_fin),
                         (protocolo.abre_el, protocolo.vence_el, protocolo.tramo_inicio, protocolo.tramo_fin))
        # Revertir sin trabajo hecho lo retira por completo.
        migracion.retirar_reglamento(apps, editor)
        self.assertFalse(DocumentoExigido.objects.filter(codigo='REGLAMENTO-USO').exists())
