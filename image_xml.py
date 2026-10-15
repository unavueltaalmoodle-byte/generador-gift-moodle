"""Lectura de imágenes DOCX y exportación Moodle XML con archivos incrustados."""
from dataclasses import dataclass, field
from io import BytesIO
import base64
import html
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from zipfile import ZipFile, BadZipFile

from gift_core import FormatError

IMAGE_TOKEN = re.compile(r'\[\[IMAGEN_\d{3,}\]\]')
MAX_EXPANDED_DOCX = 80 * 1024 * 1024


@dataclass
class EmbeddedImage:
    name: str
    data: bytes
    alt: str = ''
    width: int = 600


@dataclass
class DocxContent:
    text: str
    images: dict[str, EmbeddedImage] = field(default_factory=dict)


def read_docx_with_images(data):
    """Conserva el orden de texto e imágenes en párrafos y celdas simples."""
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.table import Table

    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_DOCX:
                raise FormatError('El Word descomprimido supera los 80 MB. Reducí el tamaño de las imágenes.')
    except BadZipFile as error:
        raise FormatError('El archivo no es un Word DOCX válido.') from error
    document = Document(BytesIO(data))
    images, lines = {}, []

    if document.element.body.xpath('.//w:txbxContent'):
        raise FormatError('El Word contiene cuadros de texto. Pasá las preguntas e imágenes a párrafos normales.')
    if document.element.body.xpath('.//wp:anchor'):
        raise FormatError('El Word contiene imágenes u objetos flotantes. En Word, seleccioná cada imagen → Opciones de diseño → En línea con el texto.')
    if document.element.body.xpath('.//w:object') or document.element.body.xpath('.//a:graphicData[not(@uri="http://schemas.openxmlformats.org/drawingml/2006/picture")]'):
        raise FormatError('El Word contiene un gráfico u objeto que no se puede extraer. Convertí ese objeto a una imagen PNG o JPG en línea con el texto.')

    if any(any(int(value) != 0 for value in node.attrib.values())
           for node in document.element.body.xpath('.//a:srcRect')):
        raise FormatError('Hay una imagen recortada en Word. Guardá el recorte como una nueva imagen PNG o JPG y volvé a insertarla para conservar lo que se ve.')
    if any(node.get('rot', '0') != '0' or node.get('flipH', '0') not in ('0', 'false')
           or node.get('flipV', '0') not in ('0', 'false')
           for node in document.element.body.xpath('.//a:xfrm')):
        raise FormatError('Hay una imagen girada o reflejada en Word. Guardala con ese aspecto como una nueva imagen PNG o JPG y volvé a insertarla.')

    def paragraph_text(paragraph):
        if IMAGE_TOKEN.search(paragraph.text):
            raise FormatError('El Word contiene una etiqueta reservada [[IMAGEN_…]]. Eliminá esa etiqueta del texto.')
        pieces = []
        for node in paragraph._p.iter():
            if node.tag == qn('w:t'):
                pieces.append(node.text or '')
            elif node.tag in (qn('w:br'), qn('w:cr')):
                pieces.append('\n')
            elif node.tag == qn('w:tab'):
                pieces.append('\t')
            elif node.tag in (qn('a:blip'), '{urn:schemas-microsoft-com:vml}imagedata'):
                relation_id = node.get(qn('r:embed')) or node.get(qn('r:id'))
                if not relation_id or relation_id not in document.part.related_parts:
                    raise FormatError('Hay una imagen vinculada o inaccesible. Insertala dentro del Word, sin vincularla a un archivo externo.')
                part = document.part.related_parts[relation_id]
                extensions = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/gif': 'gif'}
                extension = extensions.get(part.content_type)
                if extension is None:
                    raise FormatError(f'Imagen de formato no admitido ({part.content_type}). Usá PNG, JPG o GIF.')
                number = len(images) + 1
                token = f'[[IMAGEN_{number:03d}]]'
                alt, width = '', 600
                drawing = next((ancestor for ancestor in node.iterancestors() if ancestor.tag == qn('w:drawing')), None)
                if drawing is not None:
                    properties = drawing.xpath('.//wp:docPr')
                    if properties:
                        alt = properties[0].get('descr', '') or properties[0].get('title', '')
                    extents = drawing.xpath('.//wp:extent')
                    if extents:
                        width = max(1, min(700, round(int(extents[0].get('cx', '5715000')) / 9525)))
                images[token] = EmbeddedImage(f'imagen_{number:03d}.{extension}', part.blob, alt, width)
                pieces.append(token)
        return ''.join(pieces)

    def visit(container, parent):
        for element in container:
            if element.tag == qn('w:p'):
                lines.append(paragraph_text(Paragraph(element, parent)))
            elif element.tag == qn('w:tbl'):
                table = Table(element, parent)
                seen_cells = set()
                for row in table.rows:
                    for cell in row.cells:
                        if cell._tc in seen_cells:
                            continue
                        seen_cells.add(cell._tc)
                        visit(cell._tc, cell)
    visit(document.element.body, document)
    # Evita omitir imágenes dentro de estructuras de Word que no se recorren.
    expected_images = sum(node.tag in (qn('a:blip'), '{urn:schemas-microsoft-com:vml}imagedata')
                          for node in document.element.body.iter())
    if len(images) != expected_images:
        raise FormatError('Hay imágenes dentro de una estructura de Word no admitida. Copialas a párrafos normales o celdas simples, en línea con el texto.')
    return DocxContent('\n'.join(lines), images)


def html_content(text, images):
    """Escapa el texto; sólo las etiquetas internas generan HTML de imágenes."""
    parts, used, offset = [], {}, 0
    for match in IMAGE_TOKEN.finditer(text):
        parts.append(html.escape(text[offset:match.start()]).replace('\n', '<br />'))
        token = match.group()
        if token not in images:
            raise FormatError(f'Falta el archivo de la imagen {token}. Subí el Word original con la imagen insertada.')
        image = images[token]
        parts.append(f'<img src="@@PLUGINFILE@@/{image.name}" alt="{html.escape(image.alt, quote=True)}" width="{image.width}" style="max-width:100%;height:auto;" />')
        used[image.name] = image
        offset = match.end()
    parts.append(html.escape(text[offset:]).replace('\n', '<br />'))
    return '<div>' + ''.join(parts) + '</div>', used


def make_xml(questions, category='', prefix='Pregunta'):
    quiz = ET.Element('quiz')

    def text_element(parent, tag, text):
        node = ET.SubElement(parent, tag)
        node.text = text
        return node

    def rich_element(parent, tag, text, images=None, **attributes):
        node = ET.SubElement(parent, tag, format='html', **attributes)
        content, used = html_content(text, images or {})
        text_element(node, 'text', content)
        for image in used.values():
            file = ET.SubElement(node, 'file', name=image.name, path='/', encoding='base64')
            file.text = base64.b64encode(image.data).decode('ascii')
        return node

    if category.strip():
        if '\n' in category or '\r' in category:
            raise FormatError('La categoría debe ocupar una sola línea.')
        category_question = ET.SubElement(quiz, 'question', type='category')
        container = ET.SubElement(category_question, 'category')
        text_element(container, 'text', '$course$/' + category.strip())
    for index, question in enumerate(questions, 1):
        node = ET.SubElement(quiz, 'question', type='multichoice')
        name = ET.SubElement(node, 'name')
        text_element(name, 'text', f'{prefix.strip() or "Pregunta"} {index:03d}')
        rich_element(node, 'questiontext', question.stem, question.images)
        rich_element(node, 'generalfeedback', question.general_feedback)
        for tag, value in [('defaultgrade', '1.0000000'), ('penalty', '0.3333333'),
                           ('hidden', '0'), ('single', 'true'), ('shuffleanswers', '0'),
                           ('answernumbering', 'ABCD')]:
            text_element(node, tag, value)
        for letter, option in question.options.items():
            answer = rich_element(node, 'answer', option, question.images,
                                  fraction='100' if letter == question.correct else '0')
            rich_element(answer, 'feedback', question.feedback if letter == question.correct else '')
    # CDATA conserva el HTML; las imágenes se adjuntan a su campo correspondiente.
    from xml.parsers.expat import ExpatError
    try:
        dom = minidom.parseString(ET.tostring(quiz, encoding='utf-8'))
    except ExpatError as error:
        raise FormatError('El texto contiene un carácter de control no válido para XML. Copiá el texto a un editor y eliminá los caracteres extraños.') from error
    for node in dom.getElementsByTagName('text'):
        if node.parentNode.getAttribute('format') == 'html' and node.firstChild is not None:
            value = node.firstChild.nodeValue
            node.replaceChild(dom.createCDATASection(value), node.firstChild)
    return dom.toprettyxml(indent='  ', encoding='UTF-8').decode('utf-8')
