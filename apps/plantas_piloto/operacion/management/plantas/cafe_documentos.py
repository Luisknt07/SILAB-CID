"""HTML original ligero, imprimible y autocontenido; sin código de terceros."""
from html import escape

from .cafe import ALCANCE, FUENTES, VERSION

CSS = '''
:root{color-scheme:light;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif;color:#183b31;background:#f3f6f3}
*{box-sizing:border-box}body{margin:0}header{padding:clamp(22px,5vw,55px);background:#103b2b;color:white;border-bottom:5px solid #e5bd54}
main{max-width:1080px;margin:auto;padding:clamp(16px,4vw,42px)}h1{font-size:clamp(1.7rem,4vw,2.8rem);line-height:1.15;margin:.5em 0}h2{font-size:1.35rem;color:#125b3c;line-height:1.3}p{overflow-wrap:anywhere}section{background:white;border:1px solid #dce5df;border-radius:16px;padding:clamp(16px,3vw,30px);margin:20px 0;break-inside:avoid}small{display:block}.eyebrow{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#efce73;font-weight:750}.note{border-left:4px solid #c6962f;padding:12px 18px;background:#fff9e9;border-radius:4px;font-size:.9rem}.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:8px}.flow span{padding:12px;border:1px solid #bfd6c7;border-radius:10px;background:#edf5ef;font-weight:650;font-size:.84rem}.flow b{display:block;color:#986c16;font-size:.75rem}a{color:#00593a;overflow-wrap:anywhere}nav{display:flex;gap:10px;flex-wrap:wrap}nav a{border:1px solid #c9dbcf;border-radius:99px;padding:8px 14px;text-decoration:none;background:#fff}footer{padding:20px;text-align:center;font-size:.85rem;color:#536b60}@media print{body{background:white;font-size:11pt}header{background:white;color:#183b31;padding:15px}section{break-inside:auto}nav{display:none}a{color:inherit}main{padding:0}}'''


def documento_html(clave, datos):
    titulo = escape(datos['titulo'])
    bloques = ''.join('<section id="b' + str(i) + '"><h2>' + escape(t) + '</h2>' +
                      ''.join('<p>' + escape(p) + '</p>' for p in parrafos) + '</section>'
                      for i, (t, parrafos) in enumerate(datos['bloques'], 1))
    fuentes = ''.join('<li><a href="' + escape(FUENTES[f][1], quote=True) + '" target="_blank" rel="noopener noreferrer">' +
                      escape(FUENTES[f][0]) + '</a></li>' for f in datos['fuentes'])
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;; base-uri &apos;none&apos;; form-action &apos;none&apos;">'
            '<title>' + titulo + '</title><style>' + CSS + '</style></head><body><header><span class="eyebrow">Planta piloto · Café de origen · Sección ' +
            escape(datos['seccion']) + '</span><h1>' + titulo + '</h1><p>' + escape(datos['objetivo']) + '</p></header><main>'
            '<nav aria-label="Índice del documento">' + ''.join('<a href="#b' + str(i) + '">' + escape(t) + '</a>' for i, (t, _) in enumerate(datos['bloques'], 1)) +
            '</nav><section aria-label="Cadena productiva"><div class="flow">' + ''.join('<span><b>' + str(i) + '</b>' + escape(t) + '</span>' for i, t in enumerate(
                ('Finca y recepción', 'Beneficio diferenciado', 'Secado y verde', 'Perfil y tueste', 'Empaque e inventario', 'Servicio y cliente'), 1)) +
            '</div></section>' + bloques + ('<section><h2>Fuentes para contrastar métodos</h2><ul>' + fuentes + '</ul><p>Consulta: 13 de octubre de 2026. Síntesis y organización originales; las fuentes conservan sus derechos. Revisar versión y alcance del documento externo.</p></section>' if fuentes else '') +
            '<p class="note">' + escape(ALCANCE) + '</p></main><footer>CAF-CONT · ' + escape(clave) + ' · v' + str(VERSION) + ' · Contenido técnico original de la plataforma</footer></body></html>')
