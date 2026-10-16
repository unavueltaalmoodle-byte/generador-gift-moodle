"""Conversión estricta de preguntas de opción múltiple a GIFT (sin IA)."""
from dataclasses import dataclass, field
import re
import unicodedata


@dataclass
class Question:
    stem: str
    options: dict[str, str]
    correct: str
    feedback: str = ""
    images: dict = field(default_factory=dict)
    general_feedback: str = ""
    option_feedback: dict[str, str] = field(default_factory=dict)

    def feedback_for(self, letter):
        return self.option_feedback.get(letter, self.feedback if letter == self.correct else '')


class FormatError(ValueError):
    pass


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')


def parse_questions(text, images=None):
    images = images or {}
    image_token = re.compile(r"\[\[IMAGEN_\d{3,}\]\]")
    questions, errors = [], []
    stem, options, current = [], {}, None
    started_options = False
    number = 1
    completed_question = None

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
        line = re.sub(r'^[•●▪]\s*(?=[A-Z]\s*[).:-])', '', line, flags=re.I)
        key = re.match(r'^(?:opcion|respuesta)\s+correcta\s*:\s*(.*)$', normalized(line))
        option = re.match(r'^([A-Z])\s*[).:-]\s*(.*)$', line, re.I)
        general = re.match(r'^retroalimentacion\s+general\b', normalized(line))
        specific = re.match(r'^(?:retroalimentacion|feedback)(?:\s+para)?(?:\s+la)?(?:\s+opcion)?\s+([a-z])\s*:', normalized(line))
        feedback_like = re.match(r'^(?:retroalimentacion|feedback)\b', normalized(line))
        if specific:
            letter = specific.group(1).upper()
            value = line.split(':', 1)[1].strip()
            label = f'Pregunta {number - 1} · línea {lineno}' if completed_question else location(lineno)
            if completed_question is None:
                errors.append(f'{label}: «Retroalimentación {letter}» debe ir después de «Opción correcta» y antes de la siguiente pregunta.')
            elif letter not in completed_question.options:
                errors.append(f'{label}: la opción {letter} de la retroalimentación no existe.')
            elif letter in completed_question.option_feedback or (letter == completed_question.correct and completed_question.feedback):
                errors.append(f'{label}: hay dos devoluciones para la opción {letter}. Usá una sola etiqueta o los paréntesis, sin duplicar.')
            elif not value:
                errors.append(f'{label}: falta el texto de «Retroalimentación {letter}». Escribí la etiqueta y la explicación juntas en una línea o párrafo.')
            elif image_token.search(value):
                errors.append(f'{label}: la retroalimentación por opción admite texto; colocá las imágenes en el enunciado o en las opciones.')
            else:
                completed_question.option_feedback[letter] = value
        elif general:
            match = re.match(r'^retroalimentacion\s+general\s*:', normalized(line))
            if not match:
                errors.append(f'Línea {lineno}: use «Retroalimentación general: explicación» después de «Opción correcta».')
            elif completed_question is None:
                errors.append(f'{location(lineno)}: «Retroalimentación general» debe ir después de «Opción correcta» y antes de la siguiente pregunta.')
            elif completed_question.general_feedback:
                errors.append(f'Pregunta {number - 1} · línea {lineno}: «Retroalimentación general» está repetida; escribí una sola línea o párrafo por pregunta.')
            else:
                value = line.split(':', 1)[1].strip()
                if not value:
                    errors.append(f'Pregunta {number - 1} · línea {lineno}: falta el texto de «Retroalimentación general».')
                elif image_token.search(value):
                    errors.append(f'Pregunta {number - 1} · línea {lineno}: la retroalimentación general admite texto; colocá las imágenes en el enunciado o en las opciones.')
                else:
                    completed_question.general_feedback = value
        elif feedback_like:
            errors.append(f'Línea {lineno}: use «Retroalimentación A: explicación» o «Retroalimentación general: explicación», después de «Opción correcta».')
        elif key:
            completed_question = None
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
                content = '\n'.join(stem) + '\n' + '\n'.join(options.values())
                tokens = image_token.findall(content)
                missing = [token for token in tokens if token not in images]
                if missing:
                    errors.append(f'{location(lineno)}: faltan los archivos de imágenes; subí el Word original.')
                else:
                    completed_question = Question('\n'.join(stem), options.copy(), answer.group(1).upper(), answer.group(2) or '', {token: images[token] for token in tokens})
                    questions.append(completed_question)
            number += 1
            stem, options, current, started_options = [], {}, None, False
        elif option:
            completed_question = None
            letter, value = option.group(1).upper(), option.group(2)
            if letter in options:
                errors.append(f'{location(lineno)}: opción {letter} repetida; puede faltar «Opción correcta» en la pregunta anterior.')
            options[letter], current, started_options = value, letter, True
        elif started_options and image_token.search(line) and not image_token.sub('', line).strip():
            # Una imagen en un párrafo propio pertenece a la opción anterior.
            options[current] += '\n' + line
        elif started_options:
            errors.append(f'{location(lineno)}: texto sin etiqueta después de las opciones. Escriba cada opción en una sola línea y cierre con «Opción correcta: letra».')
        else:
            completed_question = None
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
    if any(q.images for q in questions):
        raise FormatError('Estas preguntas contienen imágenes. Descargá Moodle XML para conservarlas.')
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
            feedback = q.feedback_for(letter)
            if feedback:
                line += '#' + escape_gift(feedback)
            lines.append(line)
        if q.general_feedback:
            lines.append('####' + escape_gift(q.general_feedback))
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
