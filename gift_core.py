"""Conversión estricta de preguntas de opción múltiple a GIFT (sin IA)."""
from dataclasses import dataclass
import re
import unicodedata


@dataclass
class Question:
    stem: str
    options: dict[str, str]
    correct: str
    feedback: str = ""


class FormatError(ValueError):
    pass


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')


def parse_questions(text):
    questions, errors = [], []
    stem, options, current = [], {}, None
    started_options = False
    number = 1

    def location(lineno=None):
        excerpt = ' '.join(stem).strip()
        if len(excerpt) > 85:
            excerpt = excerpt[:82] + '…'
        label = f'Pregunta {number}'
        if excerpt:
            label += f' («{excerpt}»)'
        if lineno is not None:
            label += f' · línea {lineno}'
        return label

    for lineno, raw in enumerate(text.lstrip('\ufeff').splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        key = re.match(r'^(?:opcion|respuesta)\s+correcta\s*:\s*(.*)$', normalized(line))
        option = re.match(r'^([A-Z])\s*[).:-]\s*(.*)$', line, re.I)
        if key:
            value = line.split(':', 1)[1].strip()
            answer = re.fullmatch(r'([A-Z])\s*\.?\s*(?:\((.*)\)\s*\.?)?', value, re.I)
            if not answer:
                errors.append(f'{location(lineno)}: use «Opción correcta: B» o «Opción correcta: B (explicación)».')
            elif not stem or not ' '.join(stem).strip():
                errors.append(f'{location(lineno)}: falta el enunciado.')
            elif len(options) < 2:
                errors.append(f'{location(lineno)}: hacen falta al menos dos opciones.')
            elif list(options) != [chr(65+i) for i in range(len(options))]:
                errors.append(f'{location(lineno)}: las opciones deben ser consecutivas desde A.')
            elif any(not value.strip() for value in options.values()):
                errors.append(f'{location(lineno)}: hay una opción vacía.')
            elif answer.group(1).upper() not in options:
                errors.append(f'{location(lineno)}: la letra correcta no corresponde a una opción.')
            else:
                questions.append(Question('\n'.join(stem), options.copy(), answer.group(1).upper(), answer.group(2) or ''))
            number += 1
            stem, options, current, started_options = [], {}, None, False
        elif option:
            letter, value = option.group(1).upper(), option.group(2)
            if letter in options:
                errors.append(f'{location(lineno)}: opción {letter} repetida; puede faltar «Opción correcta» en la pregunta anterior.')
            options[letter], current, started_options = value, letter, True
        elif started_options:
            errors.append(f'{location(lineno)}: texto sin etiqueta después de las opciones. Escriba cada opción en una sola línea y cierre con «Opción correcta: letra».')
        else:
            if not stem:
                line = re.sub(r'^(?:Pregunta\s+)?\d+\s*[).:-]\s*', '', line, flags=re.I)
            stem.append(line)
    if stem or options:
        errors.append(f'{location()}: falta el cierre «Opción correcta: letra».')
    if errors:
        raise FormatError('\n'.join(errors))
    if not questions:
        raise FormatError('No se encontraron preguntas. Use el ejemplo como plantilla.')
    return questions


def escape_gift(text):
    text = text.replace('\\', '\\\\')
    for character in '~=#{}:':
        text = text.replace(character, '\\' + character)
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', r'\n')


def make_gift(questions, category='', prefix='Pregunta'):
    parts = []
    if category.strip():
        if '\n' in category or '\r' in category:
            raise FormatError('La categoría debe ocupar una sola línea.')
        parts.append('$CATEGORY: ' + escape_gift(category.strip()))
    for index, q in enumerate(questions, 1):
        title = escape_gift(f'{prefix.strip() or "Pregunta"} {index:03d}')
        lines = [f'::{title}::[plain]{escape_gift(q.stem)} {{']
        for letter, option in q.options.items():
            line = ('=' if letter == q.correct else '~') + escape_gift(option)
            if letter == q.correct and q.feedback:
                line += '#' + escape_gift(q.feedback)
            lines.append(line)
        lines.append('}')
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts) + '\n'


def read_docx(data):
    from io import BytesIO
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    document = Document(BytesIO(data))
    lines = []
    for element in document.element.body:
        if element.tag == qn('w:p'):
            lines.append(Paragraph(element, document).text)
        elif element.tag == qn('w:tbl'):
            for row in Table(element, document).rows:
                for cell in row.cells:
                    lines.extend(p.text for p in cell.paragraphs)
    return '\n'.join(lines)
