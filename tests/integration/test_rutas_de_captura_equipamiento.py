"""Prueba de cargue de los anexos 2, 3 y 4 y de su respaldo: cada dato se captura por la pantalla de la unidad.

Una cuenta de unidad (administra y coordina su laboratorio; no es personal de Administración ni superusuario)
registra cada dato por la misma ruta y con los mismos nombres de campo que su formulario, lo lleva hasta el
estado que el documento cuenta y lo encuentra después en su tabla:

- anexo 2, mantenimiento y equipamiento: plan, órdenes con su informe, cumplimiento en equipos críticos, fallas,
  pruebas funcionales, estado de los equipos e infraestructura;
- anexo 3, inventario: acta de revisión física, equipos, y bajas y traspasos (reactivos, insumos y movimientos
  se prueban con las rutas de captura del inventario de existencias);
- anexo 4, fichas técnicas: ficha de la unidad, espacios y talleres, y software y simuladores;
- respaldo para auditoría: calibración de equipos y personal de la unidad. El reglamento de uso ya no se
  edita en la ficha: se redacta en el expediente (tests/integration/test_reglamento_uso.py).

El documento se pide como lo pide la unidad: el anexo, con «borrador al día» desde el Centro de reportes; el
respaldo, como consulta del Centro de reportes en PDF.
"""
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.core.roles import MODULOS_OPERATIVOS
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import constructor_de, contexto_del_anexo
from apps.documentos.presentation.documentos_entrega import ruta_borrador
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.recursos.models.recursos import ReglamentoUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar, pdf_legible_prueba


def _plano(valor):
    """El texto de una celda del anexo, también si es un par o un enlace."""
    if hasattr(valor, 'principal'):
        return f'{_plano(valor.principal)} {_plano(valor.secundario)}'
    if hasattr(valor, 'url'):
        return f'{valor.texto} {valor.url}'
    return str(valor)


def _texto_del_pdf(contenido):
    """El texto del PDF en una sola línea, para buscar frases que una celda parte en renglones."""
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


def _respaldo(nombre):
    return SimpleUploadedFile(f'{nombre}.pdf', pdf_legible_prueba(
        f'Respaldo ficticio {nombre}: alcance, responsable, trabajo realizado y resultado de la prueba.'),
        content_type='application/pdf')


def _datos_de(formulario, **cambios):
    """Lo que enviaría el navegador al guardar ese formulario sin tocarlo, más los cambios."""
    datos = {}
    for campo in formulario:
        valor = campo.value()
        if valor in (None, '', False) or hasattr(valor, 'read') or hasattr(valor, 'url'):
            continue  # Una casilla sin marcar y un archivo que no se cambia no viajan.
        if isinstance(valor, (list, tuple)):
            datos[campo.html_name] = [str(getattr(v, 'pk', v)) for v in valor]
        elif valor is True:
            datos[campo.html_name] = 'on'
        else:
            datos[campo.html_name] = valor.isoformat() if hasattr(valor, 'isoformat') else str(valor)
    for nombre, valor in cambios.items():
        datos[formulario.add_prefix(nombre)] = valor
    return datos


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class RutasDeCapturaDeEquipamientoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        # La cuenta de la unidad, como la crea «crear_administradores_unidad»: administra y coordina, sin
        # acceso de personal a Administración.
        cls.cuenta = get_user_model().objects.create_user('admin.lab-rutas-h3', password='clave-ficticia',
                                                          first_name='Administración', last_name='Laboratorio H3')
        identificar(cls.cuenta, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio de rutas H3', slug='lab-rutas-h3', dependencia='laboratorios',
            descripcion='Unidad ficticia', fecha_inicio=cls.hoy.replace(year=cls.hoy.year - 1, day=1),
            administrador=cls.cuenta, activo=True)
        cls.coordinacion = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.cuenta, nombre='Administración Laboratorio H3', rol='coordinacion',
            permisos_operativos={modulo: True for modulo in MODULOS_OPERATIVOS}, activo=True, recibe_reservas=True)
        cls.periodo = dict(anio=cls.hoy.year, corte='A' if cls.hoy.month <= 6 else 'B')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='rutas-captura-h3-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.assertFalse(self.cuenta.is_staff or self.cuenta.is_superuser)
        self.client.force_login(self.cuenta)

    # -- las rutas, como las usa la unidad --------------------------------------------------------

    def operar(self, **datos):
        """Un formulario del panel de la unidad («Guardar» en el cajón lateral)."""
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        return respuesta.json()['registro']['id']

    def panel(self, vista, **parametros):
        respuesta = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), dict(view=vista, **parametros))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def evidencia(self, tipo, codigo, **datos):
        """«Registrar evidencia» de una meta, marcada como comprobada y con su respaldo."""
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug]) + '?anio={anio}&corte={corte}'.format(**self.periodo)
        base = dict(tipo=tipo, codigo=codigo, fecha=self.hoy.isoformat(), titulo=f'Registro ficticio {codigo}',
                    descripcion='Registro ficticio de la prueba de cargue.', responsable=self.cuenta.pk,
                    archivo=_respaldo(codigo), verificar='on', **self.periodo)
        respuesta = self.client.post(ruta, base | datos)
        if respuesta.status_code != 302:
            self.fail(f'La evidencia {codigo} no se guardó: {respuesta.context["form"].errors.as_json()}')
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo=codigo)
        self.assertEqual((evidencia.estado, evidencia.validado_por), ('validado', self.cuenta))
        return evidencia

    def equipo(self, codigo='H3BAL01', nombre='Balanza analítica ficticia', **datos):
        """«Nuevo equipo» en Recursos, con sus datos patrimoniales."""
        base = dict(
            modulo='recursos', entidad='equipo', nombre_catalogo=nombre, marca='Marca Ficticia', modelo='MF-200',
            codigo_unidad=codigo, numero_serie='SERIE' + codigo, codigo_bien='BIEN' + codigo, tipo_bien='BLD',
            clase_bien='Equipo de laboratorio ficticio', custodio='Custodia Ficticia', ubicacion_bodega='Bodega ficticia',
            valor_contable='1250.50', estado_unidad='disponible', criticidad='critico',
            ubicacion_especifica='Mesón ficticio', origen_adquisicion='compra_publica',
            fecha_adquisicion=self.unidad.fecha_inicio.isoformat(), documento_adquisicion='Acta ficticia 001',
            activa='on')
        return UnidadEquipo.objects.get(pk=self.operar(**(base | datos)))

    def plan(self, equipo, **datos):
        """«Nuevo plan» en Mantenimiento: basta el equipo, el tipo y la frecuencia."""
        base = dict(modulo='plan_mantenimiento', equipo_id=equipo.pk, tipo='preventivo', frecuencia_dias='90',
                    responsable=self.cuenta.pk)
        return PlanMantenimientoEquipo.objects.get(pk=self.operar(**(base | datos)))

    def orden(self, equipo, **datos):
        """«Programar» en Mantenimiento: una orden que se completa con su resultado y su informe."""
        hoy = self.hoy.isoformat()
        base = dict(modulo='mantenimiento', equipo_id=equipo.pk, responsable=self.cuenta.pk, tipo='preventivo',
                    titulo='Mantenimiento ficticio', estado='programado', ejecutor='interno',
                    fecha_programada=f'{hoy}T08:00', duracion_horas='2', plan_id='', incidencia_id='')
        return MantenimientoEquipo.objects.get(pk=self.operar(**(base | datos)))

    def completar(self, orden, nombre_informe, **datos):
        hoy = self.hoy.isoformat()
        base = dict(modulo='mantenimiento', registro_id=orden.pk, equipo_id=orden.equipo_id,
                    responsable=self.cuenta.pk, tipo=orden.tipo, titulo=orden.titulo, estado='completado',
                    ejecutor='interno', fecha_programada=f'{hoy}T08:00', fecha_inicio=f'{hoy}T08:00',
                    fecha_fin=f'{hoy}T09:30', duracion_horas='2', costo='45.50', plan_id=orden.plan_id or '',
                    incidencia_id=orden.incidencia_id or '', resultado='Limpieza, ajuste y verificación ficticios.',
                    prueba_funcionamiento='Pesa patrón ficticia dentro de tolerancia.', resultado_operativo='apto',
                    informe=_respaldo(nombre_informe))
        self.operar(**(base | datos))
        orden.refresh_from_db()
        return orden

    # -- los documentos, como los pide la unidad --------------------------------------------------

    def anexo(self, codigo):
        documentos = construir_expediente(self.unidad, self.hoy.year, hoy=self.hoy)
        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL'
                       and tramo_del_documento(d)[0] <= self.hoy <= tramo_del_documento(d)[1])
        return next(a for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.codigo == codigo)

    def pdf_del_anexo(self, codigo):
        """«Borrador al día» del anexo, en el Centro de reportes de la unidad."""
        respuesta = self.client.get(ruta_borrador(self.anexo(codigo)))
        self.assertEqual((respuesta.status_code, respuesta['Content-Type']), (200, 'application/pdf'))
        return _texto_del_pdf(respuesta.content)

    def tabla(self, codigo, titulo):
        """Las filas de una tabla del anexo, cada una como texto, y su pie."""
        anexo = self.anexo(codigo)
        registro = next(r for r in constructor_de(codigo)(contexto_del_anexo(anexo, *tramo_del_documento(anexo)))
                        if r.titulo == titulo)
        return [' | '.join(_plano(celda) for celda in fila) for fila in registro.filas], str(registro.total or '')

    def fila(self, codigo, titulo, contiene):
        filas, _pie = self.tabla(codigo, titulo)
        encontradas = [fila for fila in filas if contiene in fila]
        self.assertEqual(len(encontradas), 1, f'«{contiene}» en «{titulo}»: {filas}')
        return encontradas[0]

    def consulta(self, categoria):
        """Un documento de «Respaldo para auditoría» del Centro de reportes, en PDF."""
        inicio, fin = tramo_del_documento(self.anexo('EQUIPAMIENTO'))
        respuesta = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), dict(
            categoria_reporte=categoria, desde=inicio.isoformat(), hasta=fin.isoformat(), formato='pdf'))
        self.assertEqual(respuesta.status_code, 200)
        return _texto_del_pdf(respuesta.content)

    def pantalla_de_consulta(self, categoria):
        """La consulta en pantalla, que es donde se ofrece «Registrar…» de cada evidencia."""
        inicio, fin = tramo_del_documento(self.anexo('EQUIPAMIENTO'))
        respuesta = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]), dict(
            categoria_reporte=categoria, desde=inicio.isoformat(), hasta=fin.isoformat()))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    # -- anexo 2: mantenimiento y equipamiento ----------------------------------------------------

    def test_el_plan_de_mantenimiento_se_registra_desde_el_panel_y_sale_en_el_plan_vigente(self):
        equipo = self.equipo()
        self.assertIn('data-agenda-operation-open="plan_mantenimiento"', self.panel('mantenimiento'))
        plan = self.plan(equipo, proveedor='Servicio Técnico Ficticio')
        # El nombre y la próxima fecha se completan solos.
        self.assertEqual(plan.nombre, 'Preventivo de H3BAL01')
        self.assertEqual((plan.fecha_inicio, (plan.proxima_ejecucion - plan.fecha_inicio).days), (self.hoy, 90))
        fila = self.fila('EQUIPAMIENTO', 'Plan de mantenimiento vigente', 'H3BAL01')
        for dato in ('Crítico', 'Preventivo de H3BAL01', 'Cada 90 días', 'Servicio Técnico Ficticio',
                     'Administración Laboratorio H3'):
            self.assertIn(dato, fila)
        _filas, pie = self.tabla('EQUIPAMIENTO', 'Plan de mantenimiento vigente')
        self.assertIn('equipos críticos sin plan: 0', pie)
        # El formulario de la orden ofrece el plan para enlazarla y pide el informe.
        panel = self.panel('mantenimiento')
        self.assertIn(f'<option value="{plan.pk}">H3BAL01 · Preventivo de H3BAL01</option>', panel)
        self.assertIn('name="informe"', panel)
        self.assertIn('Preventivo de H3BAL01', self.pdf_del_anexo('EQUIPAMIENTO'))
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad, entidad='recursos.PlanMantenimientoEquipo', accion='crear').exists())
        # El plan se corrige y se desactiva desde el mismo formulario.
        self.operar(modulo='plan_mantenimiento', registro_id=plan.pk, tipo='preventivo', frecuencia_dias='60',
                    nombre='Limpieza y ajuste ficticios')
        self.assertIn('Cada 60 días', self.fila('EQUIPAMIENTO', 'Plan de mantenimiento vigente', 'H3BAL01'))
        self.operar(modulo='plan_mantenimiento', registro_id=plan.pk, accion='desactivar')
        self.assertEqual(self.tabla('EQUIPAMIENTO', 'Plan de mantenimiento vigente')[0], [])

    def test_una_orden_preventiva_completada_con_su_informe_cuenta_en_el_equipo_critico(self):
        equipo = self.equipo()
        plan = self.plan(equipo)
        orden = self.orden(equipo)
        # Sin elegir plan, la orden toma el único plan vigente de su tipo.
        self.assertEqual(orden.plan, plan)
        # El plan de otro equipo se rechaza diciendo qué hacer.
        otro = self.equipo('H3BAL02', 'Balanza auxiliar ficticia', criticidad='normal')
        rechazo = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), dict(
            modulo='mantenimiento', equipo_id=otro.pk, tipo='preventivo', titulo='Orden ficticia mal enlazada',
            estado='programado', fecha_programada=f'{self.hoy.isoformat()}T10:00', plan_id=plan.pk))
        self.assertEqual(rechazo.status_code, 400)
        self.assertIn('no es de este equipo', rechazo.json()['error'])
        orden = self.completar(orden, 'informe-preventivo')
        self.assertTrue(orden.informe.name.endswith('.pdf'))
        fila = self.fila('EQUIPAMIENTO', 'Mantenimientos del período', orden.codigo)
        for dato in ('H3BAL01', 'Preventivo', 'Plan: Preventivo de H3BAL01', 'Completado', 'USD 45,50',
                     'Limpieza, ajuste y verificación ficticios.', 'Apto', 'Abrir'):
            self.assertIn(dato, fila)
        critico = self.fila('EQUIPAMIENTO', 'Cumplimiento del plan en equipos críticos', 'H3BAL01')
        self.assertEqual(critico.split(' | ')[1:], ['1', '1', '0', 'Al día'])
        pdf = self.pdf_del_anexo('EQUIPAMIENTO')
        self.assertIn(orden.codigo, pdf)
        self.assertIn('Limpieza, ajuste y verificación ficticios.', pdf)
        # Guardar de nuevo la orden sin subir otro archivo conserva su informe y su plan.
        informe = orden.informe.name
        self.operar(modulo='mantenimiento', registro_id=orden.pk, equipo_id=equipo.pk, responsable=self.cuenta.pk,
                    tipo='preventivo', titulo=orden.titulo, estado='completado', ejecutor='interno',
                    fecha_programada=f'{self.hoy.isoformat()}T08:00', resultado='Resultado ficticio corregido.',
                    plan_id=plan.pk, duracion_horas='2')
        orden.refresh_from_db()
        self.assertEqual((orden.informe.name, orden.plan), (informe, plan))

    def test_una_falla_con_su_orden_correctiva_y_su_solucion_sale_en_las_incidencias(self):
        equipo = self.equipo()
        incidencia = IncidenciaEquipo.objects.get(pk=self.operar(
            modulo='incidencia', equipo_id=equipo.pk, titulo='No enciende la pantalla ficticia', tipo='falla',
            prioridad='alta', estado='abierta', descripcion='La pantalla ficticia no responde al encender.',
            detiene_operacion='on', asignada_a=self.cuenta.pk))
        equipo.refresh_from_db()
        self.assertNotEqual(equipo.estado_unidad, 'disponible')
        orden = self.orden(equipo, tipo='correctivo', titulo='Cambio de fuente ficticia', incidencia_id=incidencia.pk)
        orden = self.completar(orden, 'informe-correctivo')
        self.operar(modulo='incidencia', registro_id=incidencia.pk, titulo=incidencia.titulo, tipo='falla',
                    prioridad='alta', estado='resuelta', descripcion=incidencia.descripcion, detiene_operacion='on',
                    asignada_a=self.cuenta.pk, solucion='Se reemplazó la fuente ficticia y se probó el encendido.')
        fila = self.fila('EQUIPAMIENTO', 'Disponibilidad: fallas e incidencias técnicas', 'No enciende la pantalla')
        for dato in ('H3BAL01', 'Falla o avería', 'Alta', 'Sí', 'Se reemplazó la fuente ficticia', orden.codigo,
                     'Resuelta'):
            self.assertIn(dato, fila)
        correctiva = self.fila('EQUIPAMIENTO', 'Mantenimientos del período', orden.codigo)
        self.assertIn('Correctivo', correctiva)
        self.assertIn('Incidencia del', correctiva)
        self.assertIn('No enciende la pantalla ficticia', self.pdf_del_anexo('EQUIPAMIENTO'))
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado_unidad, 'disponible')

    def test_una_prueba_funcional_verificada_sale_en_las_pruebas_funcionales(self):
        equipo = self.equipo()
        self.evidencia('FUNCIONALIDAD', 'H3-FUNC-01', equipo_id=equipo.pk,
                       procedimiento='Pesada ficticia de tres patrones.', criterio='Error menor que 0,1 g ficticio.',
                       resultado_funcional='operativo', hallazgos_funcionales='')
        fila = self.fila('EQUIPAMIENTO', 'Funcionalidad: pruebas funcionales', 'H3BAL01')
        for dato in ('Pesada ficticia de tres patrones.', 'Error menor que 0,1 g ficticio.', 'Operativo',
                     'Administración Laboratorio H3', 'Evidencia verificada'):
            self.assertIn(dato, fila)
        self.assertIn('equipos probados: 1 de 1 activos', self.tabla('EQUIPAMIENTO', 'Funcionalidad: pruebas funcionales')[1])
        self.assertIn('Pesada ficticia de tres patrones.', self.pdf_del_anexo('EQUIPAMIENTO'))

    def test_el_estado_de_un_equipo_se_cambia_en_el_panel_y_sale_en_el_estado_al_corte(self):
        equipo = self.equipo()
        self.assertIn('Disponible | 1 | 1', self.tabla('EQUIPAMIENTO', 'Estado de los equipos al corte')[0])
        self.operar(modulo='recursos', entidad='equipo', registro_id=equipo.pk, codigo_unidad='H3BAL01',
                    numero_serie=equipo.numero_serie, estado_unidad='dañado', criticidad='critico', activa='on')
        filas, _pie = self.tabla('EQUIPAMIENTO', 'Estado de los equipos al corte')
        self.assertIn('Dañado | 1 | 1', filas)
        self.assertIn('Disponible | 0 | 0', filas)

    def test_el_plan_y_la_ejecucion_de_infraestructura_salen_en_su_tabla(self):
        sala = EspacioReservable.objects.get(pk=self.operar(
            modulo='recursos', entidad='espacio', codigo='H3SALA', nombre='Sala ficticia de ensayos', tipo='sala',
            politica_reserva='mixto', capacidad='6', reservable='on', activo='on'))
        hoy = self.hoy.isoformat()
        plan = self.evidencia(
            'PLAN-INFRA', 'H3-PLAN-INFRA', alcance_infraestructura='aplica',
            justificacion_alcance='El plan ficticio comprende la sala de ensayos y sus instalaciones eléctricas.',
            espacio_id=sala.pk, ubicacion='Sala ficticia de ensayos', intervencion='Revisión ficticia de tomas eléctricas',
            criticidad='critica', fecha_programada=hoy, frecuencia_dias='0', fecha_fin_programacion=hoy)
        # Programada para hoy y sin informe de ejecución, la intervención está pendiente.
        self.assertIn(' | Pendiente | ',
                      self.fila('EQUIPAMIENTO', 'Mantenimiento de infraestructura y espacios', 'H3SALA'))
        # Las dos evidencias se registran desde la consulta de mantenimiento del Centro de reportes.
        consulta = self.pantalla_de_consulta('equipamiento')
        for tipo in ('PLAN-INFRA', 'EJECUCION-INFRA', 'FUNCIONALIDAD'):
            self.assertIn(f'tipo={tipo}', consulta)
        self.evidencia('EJECUCION-INFRA', 'H3-EJEC-INFRA', plan_id=plan.pk, fecha_programada=hoy, fecha_inicio=hoy,
                       fecha_fin=hoy, resultado='Tomas ficticias revisadas y probadas.')
        fila = self.fila('EQUIPAMIENTO', 'Mantenimiento de infraestructura y espacios', 'H3SALA')
        for dato in ('Sala ficticia de ensayos', 'Revisión ficticia de tomas eléctricas',
                     'Tomas ficticias revisadas y probadas.', 'Ejecutada', 'Administración Laboratorio H3'):
            self.assertIn(dato, fila)
        self.assertIn('Revisión ficticia de tomas eléctricas', self.pdf_del_anexo('EQUIPAMIENTO'))

    # -- anexo 3: inventario ------------------------------------------------------------------------

    def test_un_equipo_con_sus_datos_patrimoniales_y_su_verificacion_fisica_sale_en_equipos(self):
        equipo = self.equipo(ficha_tecnica=_respaldo('ficha-tecnica-balanza'))
        self.assertEqual(equipo.laboratorio, self.unidad)
        self.assertTrue(equipo.equipo.ficha_tecnica.name.endswith('.pdf'))
        # Verificación física: «Confirmar que existe» en la ficha del equipo.
        respuesta = self.client.post(reverse('verificar_equipo', args=[self.unidad.slug, 'H3BAL01']),
                                     dict(resultado='existe', nota='Etiqueta ficticia legible.'))
        self.assertEqual(respuesta.status_code, 302)
        # Garantía: «Editar la ficha» del equipo, sección «Esta unidad».
        editor = reverse('editar_equipo_ficha', args=[self.unidad.slug, 'H3BAL01'])
        formulario = self.client.get(editor, dict(seccion='unidad')).context['form_unidad']
        garantia = self.hoy.replace(year=self.hoy.year + 2, day=1)
        respuesta = self.client.post(editor, dict(_datos_de(formulario, garantia_hasta=garantia.isoformat()),
                                                  seccion='unidad'), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode()[:600])
        self.assertEqual(respuesta.json(), {'ok': True})
        fila = self.fila('INVENTARIO-CORTE', 'Equipos', 'H3BAL01')
        for dato in ('Balanza analítica ficticia', 'Marca Ficticia', 'MF-200', 'SERIEH3BAL01', 'BIENH3BAL01', 'BLD',
                     'Equipo de laboratorio ficticio', 'Custodia Ficticia', 'Mesón ficticio', 'Disponible', 'Crítico',
                     'Compra pública', 'USD 1.250,50', self.hoy.strftime('%d/%m/%Y'), 'Administración Laboratorio H3',
                     'garantía hasta ' + garantia.strftime('%d/%m/%Y')):
            self.assertIn(dato, fila)
        # La ficha técnica del fabricante, subida al crear el equipo, queda enlazada en la última columna.
        self.assertIn('Abrir http', fila.rsplit(' | ', 1)[1])
        _filas, pie = self.tabla('INVENTARIO-CORTE', 'Equipos')
        self.assertIn('1 equipo activo · verificados: 1 · críticos: 1 · valor contable total: USD 1.250,50', pie)
        pdf = self.pdf_del_anexo('INVENTARIO-CORTE')
        for dato in ('SERIEH3BAL01', 'BIENH3BAL01', 'Custodia Ficticia'):
            self.assertIn(dato, pdf)

    def test_el_acta_de_revision_fisica_verificada_sale_en_el_inventario(self):
        self.equipo()
        # El acta se registra desde la consulta del inventario, en el Centro de reportes.
        self.assertIn('tipo=INVENTARIO', self.pantalla_de_consulta('recursos'))
        self.evidencia('INVENTARIO', 'H3-ACTA-INV', alcance=['equipos', 'software', 'espacios', 'insumos'],
                       revision_criticidad='on', descripcion='Sin diferencias en la revisión ficticia.')
        fila = self.fila('INVENTARIO-CORTE', 'Acta de revisión física del período', 'H3-ACTA-INV')
        for dato in (self.hoy.strftime('%d/%m/%Y'), 'Equipos, software, espacios, insumos',
                     'Administración Laboratorio H3', 'Sin diferencias en la revisión ficticia.', 'Evidencia verificada'):
            self.assertIn(dato, fila)
        self.assertIn('verificadas: 1', self.tabla('INVENTARIO-CORTE', 'Acta de revisión física del período')[1])
        self.assertIn('H3-ACTA-INV', self.pdf_del_anexo('INVENTARIO-CORTE'))

    def test_la_baja_de_un_equipo_se_registra_desde_el_panel_y_sale_en_bajas_y_traspasos(self):
        viejo, nuevo = self.equipo(), self.equipo('H3BAL02', 'Balanza de reemplazo ficticia')
        self.assertIn('data-agenda-operation-open="baja_equipo"', self.panel('recursos', modo_recursos='activos'))
        # Sin justificación no se retira: el mensaje dice qué falta.
        rechazo = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), dict(
            modulo='baja_equipo', registro_id=viejo.pk, motivo_baja='dano_irreparable', observacion_baja=''))
        self.assertEqual(rechazo.status_code, 400)
        self.assertIn('justificación', rechazo.json()['error'])
        self.operar(modulo='baja_equipo', registro_id=viejo.pk, fecha_baja=self.hoy.isoformat(),
                    motivo_baja='dano_irreparable', reemplazado_por=nuevo.pk,
                    observacion_baja='Informe técnico ficticio 007: celda de carga irreparable.',
                    respaldo_retiro=_respaldo('acta-de-baja'))
        viejo.refresh_from_db()
        self.assertEqual((viejo.fecha_baja, viejo.activa, viejo.estado_unidad), (self.hoy, False, 'no_disponible'))
        self.assertTrue(viejo.eventos_ciclo_vida.exclude(evidencia='').exists())
        fila = self.fila('INVENTARIO-CORTE', 'Bajas y traspasos del período', 'H3BAL01')
        for dato in ('Baja', self.hoy.strftime('%d/%m/%Y'), 'Daño irreparable', 'Reemplazado por H3BAL02',
                     'Informe técnico ficticio 007'):
            self.assertIn(dato, fila)
        # El dado de baja deja la lista de equipos; su reemplazo sigue en ella.
        equipos, _pie = self.tabla('INVENTARIO-CORTE', 'Equipos')
        self.assertEqual([('H3BAL01' in fila, 'H3BAL02' in fila) for fila in equipos], [(False, True)])
        self.assertIn('Informe técnico ficticio 007', self.pdf_del_anexo('INVENTARIO-CORTE'))

    # -- anexo 4: fichas técnicas ------------------------------------------------------------------

    def test_el_horario_la_capacidad_y_el_personal_salen_en_la_ficha_de_la_unidad(self):
        # La unidad nace con su jornada de lunes a viernes; aquí agrega la del sábado y la del domingo.
        for dia in (5, 6):
            respuesta = self.client.post(reverse('gestion_agenda_accion', args=[self.unidad.slug]), dict(
                entidad='horario', accion='guardar', nombre='Jornada ficticia', dia_semana=dia, hora_inicio='08:00',
                hora_fin='12:00', permite_recursos='on', permite_servicios='on', activo='on'))
            self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        self.assertEqual(HorarioOperacionUnidad.objects.filter(unidad=self.unidad, activo=True, dia_semana__gte=5).count(), 2)
        self.operar(modulo='capacidad', vigente_desde=self.hoy.isoformat(), aforo_seguridad='24',
                    puestos_mobiliario='18', puestos_equipados='12', capacidad_personal='9',
                    fuente='Acta ficticia de aforo')
        self.assertTrue(CapacidadOperativaUnidad.objects.filter(unidad=self.unidad, activo=True).exists())
        self.operar(modulo='responsable', nombre='Tecla Técnica Ficticia', rol='laboratorista', activo='on',
                    email='tecla.ficticia@example.org', publico='on', formacion='Tecnóloga ficticia en laboratorio')
        # Ubicación y carreras: «Datos de la unidad», desde Configuración.
        ruta = reverse('editar_registro', args=[self.unidad.slug, 'unidad', 'unidad'])
        formulario = self.client.get(ruta).context['formulario']
        respuesta = self.client.post(ruta, _datos_de(formulario, ubicacion='Bloque ficticio B, planta baja',
                                                     carreras='Alimentos ficticia; Agropecuaria ficticia'))
        self.assertEqual(respuesta.status_code, 302)
        filas, _pie = self.tabla('FICHAS-TECNICAS', 'Ficha de la unidad')
        ficha = dict(fila.split(' | ', 1) for fila in filas)
        self.assertIn('Laboratorio ficticio de rutas H3', ficha['Nombre y tipo'])
        self.assertIn('Bloque ficticio B, planta baja', ficha['Ubicación'])
        self.assertIn('Tecla Técnica Ficticia', ficha['Responsable'])
        self.assertIn('Sábado a domingo 08:00–12:00', ficha['Horario de operación'])
        self.assertEqual(ficha['Aforo de seguridad'], '24 personas')
        self.assertEqual(ficha['Puestos con mobiliario / equipados'], '18 / 12')
        self.assertIn('9 personas', ficha['Personal'])
        self.assertEqual(ficha['Carreras que atiende'], 'Alimentos ficticia; Agropecuaria ficticia')
        pdf = self.pdf_del_anexo('FICHAS-TECNICAS')
        for dato in ('Sábado a domingo 08:00–12:00', 'Tecla Técnica Ficticia', 'Bloque ficticio B, planta baja'):
            self.assertIn(dato, pdf)

    def test_un_espacio_con_su_responsable_sale_en_espacios_y_talleres(self):
        equipo = self.equipo()
        taller = EspacioReservable.objects.get(pk=self.operar(
            modulo='recursos', entidad='espacio', codigo='H3TALLER', nombre='Taller ficticio de prototipos',
            tipo='taller', politica_reserva='mixto', capacidad='8', superficie_m2='36.5',
            ubicacion='Bloque ficticio B', mobiliario_incluido='Cuatro mesones ficticios',
            caracteristicas='Extracción ficticia de gases', equipos_asociados=[equipo.pk], reservable='on',
            activo='on'))
        # El responsable del espacio: «Editar» en la página del área, sección de datos.
        editor = reverse('editar_area', args=[self.unidad.slug, 'H3TALLER'])
        formulario = self.client.get(editor, dict(seccion='datos')).context['form_datos']
        self.assertIn(self.coordinacion, formulario.fields['responsable'].queryset)
        respuesta = self.client.post(editor, dict(_datos_de(formulario, responsable=self.coordinacion.pk),
                                                  seccion='datos'), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode()[:600])
        taller.refresh_from_db()
        self.assertEqual((taller.responsable, taller.superficie_m2 is not None), (self.coordinacion, True))
        # Visitable: «Oferta de visitas», donde se marcan las áreas del recorrido.
        self.operar(modulo='oferta_visitas', acepta_visitas='on', personas_por_guia='10',
                    areas_visitables=[taller.pk])
        fila = self.fila('FICHAS-TECNICAS', 'Espacios y talleres', 'H3TALLER')
        for dato in ('Taller ficticio de prototipos', 'Taller', 'Bloque ficticio B', '8 personas', '36,5 m²',
                     'Cuatro mesones ficticios', 'Extracción ficticia de gases', 'H3BAL01',
                     'Administración Laboratorio H3', 'Sí visitable: sí'):
            self.assertIn(dato, fila)
        self.assertIn('Taller ficticio de prototipos', self.pdf_del_anexo('FICHAS-TECNICAS'))

    def test_un_simulador_con_sus_licencias_sale_en_software_y_simuladores(self):
        equipo = self.equipo()
        programa = SoftwareDisponible.objects.get(pk=self.operar(
            modulo='recursos', entidad='software', nombre='Simulador ficticio de procesos', codigo='H3SIM',
            version='4.2', tipo_recurso='simulador', tipo_acceso='instalacion', licencias_totales='6',
            licencias_disponibles='4', equipos_instalados=[equipo.pk], requiere_reserva='on', activo='on'))
        # «Uso en el equipo»: «Editar» en la página de software de la unidad.
        ruta = reverse('editar_registro', args=[self.unidad.slug, 'software', programa.pk])
        formulario = self.client.get(ruta).context['formulario']
        respuesta = self.client.post(ruta, _datos_de(formulario, uso_en_equipo='obligatorio'))
        self.assertEqual(respuesta.status_code, 302)
        fila = self.fila('FICHAS-TECNICAS', 'Software y simuladores', 'H3SIM')
        for dato in ('Simulador ficticio de procesos', '4.2', 'Simulador', '6', 'disponibles: 4', 'H3BAL01',
                     'Obligatorio'):
            self.assertIn(dato, fila)
        self.assertIn('simuladores: 1', self.tabla('FICHAS-TECNICAS', 'Software y simuladores')[1])
        self.assertIn('Simulador ficticio de procesos', self.pdf_del_anexo('FICHAS-TECNICAS'))

    # -- respaldo para auditoría -------------------------------------------------------------------

    def test_las_fechas_y_la_orden_de_calibracion_salen_en_calibracion_de_equipos(self):
        equipo = self.equipo()
        # Las fechas de calibración: «Editar la ficha» del equipo, sección «Esta unidad» (son del equipo físico).
        editor = reverse('editar_equipo_ficha', args=[self.unidad.slug, 'H3BAL01'])
        self.assertNotIn('proxima_calibracion', self.client.get(editor, dict(seccion='modelo')).context['form_modelo'].fields)
        formulario = self.client.get(editor, dict(seccion='unidad')).context['form_unidad']
        self.assertIn('proxima_calibracion', formulario.fields)
        proxima = self.hoy.replace(year=self.hoy.year + 1, day=1)
        respuesta = self.client.post(editor, dict(
            _datos_de(formulario, ultima_calibracion=self.hoy.isoformat(),
                      proxima_calibracion=proxima.isoformat()), seccion='unidad'), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode()[:600])
        self.assertEqual(respuesta.json(), {'ok': True})
        equipo.refresh_from_db()
        self.assertEqual((equipo.ultima_calibracion, equipo.proxima_calibracion), (self.hoy, proxima))
        # La orden de calibración, completada con su informe: queda como certificado del equipo.
        orden = self.completar(self.orden(equipo, tipo='calibracion', titulo='Calibración ficticia anual'),
                               'certificado-de-calibracion')
        equipo.refresh_from_db()
        self.assertEqual((equipo.ultima_calibracion, equipo.proxima_calibracion), (self.hoy, proxima))
        self.assertTrue(equipo.certificado_calibracion.name.startswith('equipos/calibraciones/'))
        pdf = self.consulta('calibracion')
        for dato in ('H3BAL01', self.hoy.strftime('%d/%m/%Y'), proxima.strftime('%d/%m/%Y'), 'Vigente',
                     orden.codigo, 'Certificado:'):
            self.assertIn(dato, pdf)

    def test_la_formacion_y_la_designacion_del_personal_salen_en_personal_de_la_unidad(self):
        self.assertIn('name="acto_designacion"', self.panel('configuracion'))
        # Una persona sin cuenta en la plataforma, con las casillas tal como las trae marcadas el formulario:
        # se guarda en el personal, sin reservas ni permisos, y el mensaje lo dice.
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), dict(
            modulo='responsable', nombre='Lauro Laboratorista Ficticio', rol='laboratorista',
            email='lauro.ficticio@example.org', horario_atencion='Lunes a viernes, 08:00 a 12:00',
            formacion='Ingeniero ficticio en alimentos', acto_designacion='Memorando ficticio 0042',
            fecha_designacion=self.hoy.isoformat(), publico='on', recibe_reservas='on', activo='on',
            **{f'permiso_{modulo}': 'on' for modulo in MODULOS_OPERATIVOS}))
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        self.assertIn('sin cuenta vinculada (no recibe reservas ni opera el panel)', respuesta.json()['message'])
        persona = ResponsableUnidad.objects.get(unidad=self.unidad, nombre='Lauro Laboratorista Ficticio')
        self.assertEqual((persona.recibe_reservas, any(persona.permisos_operativos.values())), (False, False))
        pdf = self.consulta('personal')
        for dato in ('Lauro Laboratorista Ficticio', 'Laboratorista', 'Ingeniero ficticio en alimentos',
                     'Memorando ficticio 0042', self.hoy.strftime('%d/%m/%Y'), 'Lunes a viernes, 08:00 a 12:00'):
            self.assertIn(dato, pdf)

    def test_el_reglamento_ya_no_se_edita_en_la_ficha_y_el_panel_remite_al_expediente(self):
        panel = self.panel('configuracion')
        self.assertNotIn('/editar/reglamento/', panel)
        self.assertIn(reverse('gestion_expediente_unidad', args=[self.unidad.slug]) + '#entregas-documentos', panel)
        self.assertIn('Reglamento de uso (expediente)', panel)
        ruta = reverse('editar_registro', args=[self.unidad.slug, 'reglamento', 'unidad'])
        self.assertEqual(self.client.get(ruta).status_code, 404)
        self.assertEqual(self.client.post(ruta, {'titulo': 'Reglamento ficticio'}).status_code, 404)
        self.assertNotEqual(ReglamentoUnidad.objects.get(unidad=self.unidad).titulo, 'Reglamento ficticio')

    # -- lo que la unidad no registra ---------------------------------------------------------------

    def test_el_traspaso_lo_propone_la_unidad_en_su_panel_y_la_direccion_lo_aprueba_en_administracion(self):
        # La cuenta de unidad propone el traspaso desde la fila del equipo; la lista de traspasos de Administración
        # es de la Dirección, que allí lo aprueba. El circuito completo (aceptación de la unidad que recibe,
        # aprobación, recepción y «Bajas y traspasos») está en tests/integration/test_simplificaciones_k2.py.
        equipo = self.equipo()
        self.assertIn(reverse('proponer_traspaso_equipo', args=[self.unidad.slug, equipo.pk]),
                      self.panel('recursos', modo_recursos='activos'))
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        for ruta in ('admin:recursos_traspasoequipo_add', 'admin:recursos_traspasoequipo_changelist'):
            self.assertEqual(self.client.get(reverse(ruta)).status_code, 403, ruta)
