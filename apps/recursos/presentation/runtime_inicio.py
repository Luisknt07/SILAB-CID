"""Se copia al contenedor; ofrece portada solo cuando el paquete no define /."""
from importlib import import_module

from django.conf import settings
from django.http import HttpResponse
from django.urls import Resolver404, path, resolve
from django.utils.html import format_html


def inicio(request):
    return HttpResponse(format_html('''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6f4;color:#203b30;font:17px/1.6 system-ui,sans-serif}}
header{{padding:18px 5vw;background:#173e2d;color:white;border-bottom:4px solid #f8d43b}}
main{{max-width:950px;margin:9vh auto;padding:0 24px}}article{{background:white;border:1px solid #dce5df;border-radius:18px;padding:clamp(24px,5vw,60px)}}
.etiqueta{{font-size:13px;font-weight:700;letter-spacing:.1em;color:#557462;text-transform:uppercase}}
h1{{font-size:clamp(28px,4vw,44px);line-height:1.2;margin:16px 0}}p{{max-width:680px;color:#52675b}}
.nota{{margin:28px 0;padding:18px;border-left:4px solid #f8d43b;background:#faf8ed;font-size:15px}}
a{{display:inline-block;padding:12px 20px;border:1px solid #28633f;border-radius:8px;color:#28633f;text-decoration:none;font-weight:600}}
a:hover,a:focus{{background:#eaf2ed}}footer{{margin-top:20px;font-size:14px;color:#687c70}}
</style></head><body><header>Inicio del proyecto</header><main><article>
<span class="etiqueta">Bienvenido</span><h1>{}</h1>
<p>Esta es la entrada del proyecto. La administración está disponible mediante su acceso independiente.</p>
<p class="nota">El paquete cargado todavía no incluye una página de inicio propia. Esta portada se muestra hasta que el proyecto incorpore su interfaz pública.</p>
<a href="/admin/">Acceso administrativo</a>
</article><footer>Use las credenciales del proyecto para acceder a su administración.</footer></main></body></html>''',
        settings.CITT_PROJECT_TITLE, settings.CITT_PROJECT_TITLE))


original = import_module(settings.CITT_ORIGINAL_URLCONF)
urlpatterns = list(original.urlpatterns)
try:
    resolve('/', urlconf=original)
except Resolver404:
    urlpatterns.append(path('', inicio, name='citt_inicio_proyecto'))
