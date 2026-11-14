"""Entidades reales prellenadas, aliados independientes y edición de diseños existentes."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.core.presentation.identidad import identidad_actual
from apps.formacion.presentation.certificados_cursos import _huella_previa, pdf_del_certificado
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.cursos_certificacion import IMAGENES_CERTIFICADO


class EntidadesCertificadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('gestor-entidades-cert', 'entidades@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio registrado', slug='lab-entidades-cert',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1),
            facultad='Facultad registrada de ingeniería', carreras='Logística y Transporte')
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='ENT-CERT-001', nombre='Aplicaciones de logística',
            duracion_horas=40, firma_nombre='Responsable registrado', firma_cargo='Coordinación registrada')
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo registrado', anio=2026,
            inicio=date(2026, 10, 12), fin=date(2026, 10, 23), horas_certificadas=Decimal('7.50'))

    def setUp(self):
        self.media = self.enterContext(TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=self.media))
        self.client.force_login(self.gestor)

    def url(self, nombre, grupo=None):
        url = reverse(nombre, args=[self.unidad.slug, self.curso.codigo])
        return url + ('?edicion=' + str(grupo.pk) if grupo else '')

    def datos(self, config=None, **cambios):
        config = config or ConfiguracionCertificadoCurso(curso=self.curso)
        datos = {campo: getattr(config, campo) for campo in ConfiguracionCertificadoForm.Meta.fields
                 if campo not in IMAGENES_CERTIFICADO and getattr(config, campo) is not None}
        datos.update(cambios)
        return datos

    def datos_del_get(self, respuesta):
        form = respuesta.context['formulario']
        datos = {}
        for campo in ConfiguracionCertificadoForm.Meta.fields:
            if campo in IMAGENES_CERTIFICADO:
                continue
            valor = form[campo].value()
            if valor is not None and valor is not False:
                datos[campo] = valor
        return datos

    def png(self, color='white'):
        salida = BytesIO()
        Image.new('RGBA', (300, 100), color).save(salida, format='PNG')
        return salida.getvalue()

    def test_get_prellena_fuentes_reales_sin_guardar_ni_inventar_adscripciones(self):
        respuesta = self.client.get(self.url('editar_certificado_curso'))
        self.assertEqual(respuesta.status_code, 200)
        form = respuesta.context['formulario']
        esperados = {'emisor': self.unidad.nombre, 'facultad_nombre': self.unidad.facultad,
            'carrera_nombre': self.unidad.carreras, 'fecha_inicio': self.grupo.inicio,
            'fecha_fin': self.grupo.fin, 'horas_certificadas': self.grupo.horas_certificadas,
            'firma_nombre': self.curso.firma_nombre, 'firma_cargo': self.curso.firma_cargo}
        for campo, esperado in esperados.items():
            self.assertEqual(form[campo].value(), esperado, campo)
        self.assertFalse(form['mostrar_facultad'].value())
        self.assertFalse(form['mostrar_carrera'].value())
        self.assertEqual(form.carreras_sugeridas, ['Logística y Transporte'])
        self.assertEqual(form['color_primario'].value(), '')
        self.assertEqual(form.fields['color_primario'].widget.attrs['placeholder'], dict(identidad_actual()[1].paleta).get('primario', '#006633'))
        self.assertEqual(respuesta.context['institucion_certificado']['nombre'], identidad_actual()[1].nombre)
        self.assertEqual(len(form.instituciones_editor), 4)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_get_conserva_personalizaciones_y_archivos_de_configuracion_existente(self):
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso, emisor='Organizador registrado propio',
            mostrar_facultad=True, facultad_nombre='Facultad autorizada propia', mostrar_carrera=True,
            carrera_nombre='Carrera autorizada propia', fecha_inicio=date(2027, 1, 2), fecha_fin=date(2027, 1, 3),
            horas_certificadas=Decimal('12.75'), firma_nombre='Firmante confirmado', firma_cargo='Cargo confirmado',
            color_primario='#123456', color_acento='#ABCDEF', texto_aprobacion='Texto personalizado.',
            logo_1_nombre='Entidad autorizada', logo_1_contraste='original')
        config.logo_1_imagen.save('propia.png', ContentFile(self.png()), save=True)
        antes = ConfiguracionCertificadoCurso.objects.values().get(pk=config.pk)
        respuesta = self.client.get(self.url('editar_certificado_curso'))
        self.assertEqual(respuesta.status_code, 200)
        form = respuesta.context['formulario']
        for campo in ('emisor', 'facultad_nombre', 'carrera_nombre', 'fecha_inicio', 'fecha_fin',
                      'horas_certificadas', 'firma_nombre', 'firma_cargo', 'color_primario',
                      'color_acento', 'texto_aprobacion', 'logo_1_nombre', 'logo_1_contraste'):
            self.assertEqual(form[campo].value(), getattr(config, campo), campo)
        self.assertEqual(ConfiguracionCertificadoCurso.objects.values().get(pk=config.pk), antes)

    def test_campos_ambiguos_o_pendientes_no_se_prellenan_como_datos_reales(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(facultad='Facultad por registrar', carreras='Logística y Transporte, Computación')
        EdicionCurso.objects.create(curso=self.curso, nombre='Otro grupo', anio=2027, inicio=date(2027, 1, 1), fin=date(2027, 1, 2))
        Curso.objects.filter(pk=self.curso.pk).update(firma_nombre='', firma_cargo='', duracion_horas=None)
        respuesta = self.client.get(self.url('editar_certificado_curso'))
        form = respuesta.context['formulario']
        self.assertEqual(form['facultad_nombre'].value(), '')
        self.assertEqual(form['carrera_nombre'].value(), '')
        self.assertEqual(form.carreras_sugeridas, ['Logística y Transporte', 'Computación'])
        for campo in ('fecha_inicio', 'fecha_fin', 'horas_certificadas'):
            self.assertIsNone(form[campo].value())
        self.assertEqual(form['firma_nombre'].value(), '')
        self.assertEqual(form['firma_cargo'].value(), '')
        Unidad.objects.filter(pk=self.unidad.pk).update(carreras='Por definir')
        form = self.client.get(self.url('editar_certificado_curso')).context['formulario']
        self.assertEqual(form.carreras_sugeridas, [])
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())

    def test_grupo_explicito_prellena_y_se_usa_en_previa_con_aislamiento_por_curso(self):
        grupo_b = EdicionCurso.objects.create(curso=self.curso, nombre='Grupo B registrado', anio=2027,
            inicio=date(2027, 2, 3), fin=date(2027, 2, 4), horas_certificadas=Decimal('6.25'))
        respuesta = self.client.get(self.url('editar_certificado_curso', grupo_b))
        form = respuesta.context['formulario']
        self.assertEqual(form['fecha_inicio'].value(), grupo_b.inicio)
        self.assertEqual(form['horas_certificadas'].value(), grupo_b.horas_certificadas)
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-muestra') as generar:
            previa = self.client.post(self.url('previsualizar_certificado_curso', grupo_b), self.datos())
        self.assertEqual(previa.status_code, 200)
        muestra = generar.call_args.args[0]
        self.assertEqual(muestra.fecha_inicio, grupo_b.inicio)
        self.assertEqual(muestra.fecha_fin, grupo_b.fin)
        self.assertEqual(muestra.horas, grupo_b.horas_certificadas)
        self.assertEqual(muestra.edicion, grupo_b.nombre)
        otro = Curso.objects.create(unidad=self.unidad, codigo='ENT-CERT-OTRO', nombre='Otro curso')
        ajeno = EdicionCurso.objects.create(curso=otro, nombre='Ajeno', anio=2027)
        self.assertEqual(self.client.get(self.url('editar_certificado_curso', ajeno)).status_code, 404)
        self.assertEqual(self.client.post(self.url('previsualizar_certificado_curso', ajeno), self.datos()).status_code, 404)

    def test_nuevo_logo_exige_nombre_real_y_alias_sin_logo_se_permite(self):
        datos = self.datos()
        archivos = {'logo_1_imagen': SimpleUploadedFile('aliado.png', self.png(), content_type='image/png')}
        form = ConfiguracionCertificadoForm(datos, archivos, instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertFalse(form.is_valid())
        self.assertIn('logo_1_nombre', form.errors)
        datos['logo_1_nombre'] = 'Entidad colaboradora registrada'
        archivos['logo_1_imagen'] = SimpleUploadedFile('aliado.png', self.png(), content_type='image/png')
        form = ConfiguracionCertificadoForm(datos, archivos, instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertTrue(form.is_valid(), form.errors)
        form = ConfiguracionCertificadoForm(self.datos(logo_2_nombre='Organizador sin logo'), instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertTrue(form.is_valid(), form.errors)
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso)
        config.logo_1_imagen.save('legado.png', ContentFile(self.png()), save=True)
        form = ConfiguracionCertificadoForm(self.datos(config), instance=config)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['logo_1_nombre'], '')
        self.assertEqual(form.cleaned_data['logo_1_imagen'].name, config.logo_1_imagen.name)

    def test_facultad_carrera_y_entidades_validan_texto_y_visibilidad(self):
        for campo in ('facultad', 'carrera'):
            form = ConfiguracionCertificadoForm(self.datos(**{'mostrar_' + campo: True}), instance=ConfiguracionCertificadoCurso(curso=self.curso))
            self.assertFalse(form.is_valid())
            self.assertIn(campo + '_nombre', form.errors)
        for campo in ('facultad_nombre', 'carrera_nombre', 'logo_1_nombre'):
            form = ConfiguracionCertificadoForm(self.datos(**{campo: '<script>entidad</script>'}), instance=ConfiguracionCertificadoCurso(curso=self.curso))
            self.assertFalse(form.is_valid())
            self.assertIn(campo, form.errors)
        form = ConfiguracionCertificadoForm(self.datos(logo_1_contraste='inexistente'), instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertFalse(form.is_valid())
        self.assertIn('logo_1_contraste', form.errors)

    def test_huella_incluye_nombre_contraste_y_adscripciones_opcionales(self):
        config = ConfiguracionCertificadoCurso(curso=self.curso)
        original = _huella_previa(config, self.curso, self.gestor)
        for campo, valor in [('logo_1_nombre', 'Entidad registrada'), ('logo_2_contraste', 'claro'),
            ('facultad_nombre', 'Facultad registrada'), ('carrera_nombre', 'Carrera registrada'),
            ('mostrar_facultad', True), ('mostrar_carrera', True)]:
            anterior = getattr(config, campo)
            setattr(config, campo, valor)
            self.assertNotEqual(_huella_previa(config, self.curso, self.gestor), original, campo)
            setattr(config, campo, anterior)

    def test_reabrir_diseno_con_archivos_permite_editar_y_guardar_dos_veces(self):
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso,
            firma_nombre='Primera firmante', firma_cargo='Responsable', segunda_firma_nombre='Segunda firmante',
            segunda_firma_cargo='Dirección', tercera_firma_nombre='Tercera firmante', tercera_firma_cargo='Docencia',
            texto_aprobacion='Texto propio de la coordinación.', color_primario='#123456')
        for campo in IMAGENES_CERTIFICADO:
            getattr(config, campo).save('existente.png', ContentFile(self.png()), save=False)
        config.save()
        archivos = {campo: getattr(config, campo).name for campo in IMAGENES_CERTIFICADO}
        inscripcion = InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.gestor, estado='aceptada')
        legado = {'version': 5, 'texto': 'Certificado anterior inalterable', 'logos': [{'imagen': 'congelada'}]}
        certificado = CertificadoCurso.objects.create(inscripcion=inscripcion, codigo='CERT-ENT-ANT5', nombre='Identidad registrada',
            curso_nombre=self.curso.nombre, clasificacion='Curso', edicion=self.grupo.nombre, unidad_nombre=self.unidad.nombre,
            diseno_certificado=deepcopy(legado))
        for modelo in ('sobrio', 'ia_particulas'):
            datos = self.datos_del_get(self.client.get(self.url('editar_certificado_curso')))
            datos.update(diseno=modelo, texto_aprobacion='Texto revisado por coordinación: ' + modelo + '.')
            previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
            self.assertEqual(previa.status_code, 200, previa.content[:500])
            datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
            guardado = self.client.post(self.url('editar_certificado_curso'), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(guardado.status_code, 200, guardado.content)
            self.assertTrue(guardado.json()['ok'])
            config.refresh_from_db()
            self.assertEqual(config.diseno, modelo)
            for campo, nombre in archivos.items():
                self.assertEqual(getattr(config, campo).name, nombre)
                self.assertTrue(getattr(config, campo).storage.exists(nombre))
        certificado.refresh_from_db()
        self.assertEqual(certificado.diseno_certificado, legado)
        self.assertEqual(CertificadoCurso.objects.count(), 1)

    def test_previa_sin_actividad_definida_no_inventa_fechas_ni_cuarenta_horas(self):
        Curso.objects.filter(pk=self.curso.pk).update(duracion_horas=None)
        self.curso.refresh_from_db()
        self.grupo.delete()
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', wraps=pdf_del_certificado) as generar:
            previa = self.client.post(self.url('previsualizar_certificado_curso'), self.datos())
        self.assertEqual(previa.status_code, 200, previa.content[:500])
        muestra = generar.call_args.args[0]
        self.assertIsNone(muestra.fecha_inicio)
        self.assertIsNone(muestra.fecha_fin)
        self.assertIsNone(muestra.horas)
        self.assertEqual(muestra.diseno_certificado['periodo'], 'Período por definir')
        self.assertEqual(muestra.diseno_certificado['horas'], 'Duración por definir')
        texto = muestra.diseno_certificado['texto'].casefold()
        self.assertIn('período por definir', texto)
        self.assertIn('duración por definir', texto)
        self.assertNotIn('0 horas', texto)
        self.assertNotIn('40 horas', texto)
        self.assertNotIn('none', texto)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_emisor_con_variables_invalidas_devuelve_error_de_campo_y_no_500(self):
        for emisor in ('Entidad {desconocida}', 'Entidad {nombre', 'Entidad {nombre.__class__}'):
            previa = self.client.post(self.url('previsualizar_certificado_curso'), self.datos(emisor=emisor))
            self.assertEqual(previa.status_code, 400)
            self.assertIn('emisor', previa.json()['errores'])
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())

    def test_logo_primero_aliado_no_sustituye_institucion_y_organizadores_sin_logo_se_incluyen(self):
        datos = self.datos(logo_1_nombre='Entidad aliada con logo', logo_2_nombre='Organizador registrado sin logo',
            mostrar_facultad=True, facultad_nombre=self.unidad.facultad,
            mostrar_carrera=True, carrera_nombre=self.unidad.carreras)
        datos['logo_1_imagen'] = SimpleUploadedFile('aliado.png', self.png(), content_type='image/png')
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-muestra') as generar:
            previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200, previa.content[:500])
        diseno = generar.call_args.args[0].diseno_certificado
        self.assertEqual(diseno['version'], 12)
        self.assertEqual(diseno['logo_institucional']['nombre'], identidad_actual()[1].nombre)
        self.assertEqual(diseno['logo_institucional']['unidad'], self.unidad.nombre)
        self.assertEqual(diseno['logo_institucional']['facultad'], self.unidad.facultad)
        self.assertEqual(diseno['logo_institucional']['carrera'], self.unidad.carreras)
        self.assertEqual(len(diseno['logos_aliados']), 2)
        self.assertEqual(diseno['logos_aliados'][0]['nombre'], 'Entidad aliada con logo')
        self.assertEqual(diseno['logos_aliados'][1]['imagen'], '')
        self.assertIn('Organizador registrado sin logo', diseno['texto'])
        self.assertNotIn('{organizadores}', diseno['texto'])
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())


    def test_sobrio_conserva_fondo_y_destaca_upec_con_colaborador_separado(self):
        import hashlib
        import fitz
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso,
            tema_fondo='redes', modo_fondo='claro', intensidad_fondo='alta',
            color_primario='#164B72', color_acento='#38B9CF',
            logo_1_nombre='Institución aliada registrada', logo_1_posicion='izquierda')
        config.logo_1_imagen.save('institucion.png', ContentFile(self.png('#234b69')), save=True)
        raster_fondos = []
        for modelo in ('sobrio', 'ondas_tecnologicas'):
            respuesta = self.client.post(self.url('previsualizar_certificado_curso'), self.datos(config, diseno=modelo))
            self.assertEqual(respuesta.status_code, 200, respuesta.content[:500])
            self.assertIn('X-Certificado-Vista-Previa', respuesta)
            with fitz.open(stream=respuesta.content, filetype='pdf') as pdf:
                self.assertEqual(len(pdf), 1)
                pagina = pdf[0]
                pix = pagina.get_pixmap(alpha=False)
                imagen = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                banda = imagen.crop((0, 0, round(18 * imagen.width / 297), imagen.height))
                raster_fondos.append(hashlib.sha256(banda.tobytes()).hexdigest())
                logos = pagina.get_image_info()
                self.assertEqual(len(logos), 2)
                cajas = sorted((fitz.Rect(logo['bbox']) for logo in logos), key=lambda caja: caja.get_area(), reverse=True)
                self.assertGreater(cajas[0].get_area(), cajas[1].get_area())
                self.assertFalse(cajas[0].intersects(cajas[1]))
                self.assertTrue(pagina.search_for(identidad_actual()[1].nombre))
                self.assertTrue(pagina.search_for('En colaboración con'))
                self.assertTrue(pagina.search_for('Institución aliada registrada'))
                if modelo == 'sobrio':
                    from statistics import median
                    for x_mm, esperado in ((5, (22, 75, 114)), (10.75, (56, 185, 207))):
                        # El motivo puede cruzar unas muestras; la mediana interior verifica
                        # el color predominante de toda la franja sin depender del antialias.
                        muestras = [imagen.getpixel((round((x_mm + dx) * imagen.width / 297),
                                                     round((210 - y_mm) * imagen.height / 210)))
                                    for dx in (-0.25, 0, 0.25) for y_mm in range(65, 146, 5)]
                        predominante = tuple(median(pixel[canal] for pixel in muestras) for canal in range(3))
                        self.assertLessEqual(max(abs(a - b) for a, b in zip(predominante, esperado)), 4,
                                             (modelo, x_mm, predominante, esperado))
        self.assertNotEqual(*raster_fondos)
        config.refresh_from_db()
        self.assertEqual(config.diseno, 'clasico')
        self.assertEqual((config.tema_fondo, config.modo_fondo, config.intensidad_fondo), ('redes', 'claro', 'alta'))
        self.assertFalse(CertificadoCurso.objects.exists())
