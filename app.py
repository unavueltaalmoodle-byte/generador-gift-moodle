from pathlib import Path
import streamlit as st
from gift_core import parse_questions, make_gift, read_docx, FormatError

st.set_page_config(page_title='Generador GIFT · Una Vuelta', page_icon='📝', layout='centered')
st.title('Generador GIFT para Moodle')
st.write('Convertí preguntas de opción múltiple en un archivo listo para importar al banco de preguntas.')
st.caption('Versión 1.1 · Una respuesta correcta por pregunta · Texto en español · Retroalimentación opcional')
example = Path(__file__).with_name('ejemplo.txt').read_text(encoding='utf-8')

with st.expander('Cómo preparar las preguntas', expanded=True):
    st.write('Escribí las opciones con letras consecutivas: A), B), C)… Cada opción debe ocupar una sola línea. Cerrá cada pregunta con «Opción correcta: B».')
    st.write('Para agregar retroalimentación a la opción correcta: «Opción correcta: B (Explicación)». También se acepta un punto después de la letra o del paréntesis: «Opción correcta: B.» y «Opción correcta: B (Explicación).». El enunciado puede ocupar varias líneas.')
    st.code(example, language=None)
    st.download_button('Descargar plantilla de ejemplo', example.encode('utf-8'), 'ejemplo.txt', 'text/plain', key='template')

mode = st.radio('¿Cómo querés cargar las preguntas?', ['Pegar texto', 'Subir archivo'], horizontal=True)
text = ''
if mode == 'Pegar texto':
    text = st.text_area('Preguntas', height=300, placeholder=example)
else:
    upload = st.file_uploader('Archivo TXT o Word (.docx), hasta 10 MB', type=['txt', 'docx'])
    st.caption('Word: las letras A), B)… deben estar escritas en el texto, no generadas por una lista automática. No se extraen imágenes, encabezados ni cuadros de texto.')
    if upload is not None:
        try:
            data = upload.getvalue()
            if len(data) > 10 * 1024 * 1024:
                raise ValueError('El archivo supera los 10 MB.')
            text = read_docx(data) if upload.name.lower().endswith('.docx') else data.decode('utf-8-sig')
        except UnicodeDecodeError:
            st.error('El TXT debe estar guardado como UTF-8. Podés copiar su contenido y usar «Pegar texto».')
        except Exception:
            st.error('No se pudo leer el archivo. Comprobá que sea un TXT UTF-8 o un DOCX válido de hasta 10 MB.')
    if text:
        with st.expander('Ver texto extraído del archivo'):
            st.caption('Estas líneas corresponden al texto extraído; pueden diferir de las líneas visibles en Word.')
            st.code('\n'.join(f'{i:>4} | {line}' for i, line in enumerate(text.lstrip('\ufeff').splitlines(), 1)), language=None)

category = st.text_input('Categoría en Moodle (opcional)', placeholder='Parcial · Módulo 1')
prefix = st.text_input('Prefijo de los nombres de pregunta', value='Pregunta')
st.caption('Sin categoría indicada, elegirás la categoría al importar en Moodle.')

if text.strip():
    try:
        questions = parse_questions(text)
        gift = make_gift(questions, category, prefix)
    except FormatError as error:
        st.error('Corregí estos detalles antes de descargar:')
        st.text(str(error))
        with st.expander('Ubicar los errores en el texto con líneas numeradas'):
            st.caption('La pregunta se identifica por su orden en el archivo y el comienzo de su enunciado. Las líneas corresponden al texto procesado.')
            st.code('\n'.join(f'{i:>4} | {line}' for i, line in enumerate(text.lstrip('\ufeff').splitlines(), 1)), language=None)
    else:
        st.success(f'{len(questions)} preguntas listas. Revisá el contenido y las respuestas correctas antes de descargar.')
        for index, question in enumerate(questions, 1):
            with st.expander(f'Pregunta {index:03d} · Correcta: {question.correct}'):
                st.text(question.stem)
                for letter, option in question.options.items():
                    st.text(f'{"✓" if letter == question.correct else "·"} {letter}) {option}')
                if question.feedback:
                    st.text('Retroalimentación de la opción correcta: ' + question.feedback)
        st.download_button('Descargar archivo GIFT', gift.encode('utf-8'), 'preguntas_moodle.gift', 'text/plain', type='primary')
        with st.expander('Ver código GIFT generado'):
            st.code(gift, language=None)
else:
    st.info('Pegá tus preguntas o subí un archivo para comenzar.')

with st.expander('Cómo importar en Moodle'):
    st.write('Abrí el banco de preguntas del curso → Importar → Formato GIFT → cargá el archivo → Importar. Si incluiste categoría, activá «Obtener categoría del archivo»; si no, seleccioná la categoría de destino.')
    st.write('Hacé una primera prueba en una categoría de prueba y verificá cada respuesta y su retroalimentación. La ubicación del banco puede variar según la versión de Moodle.')
st.caption('Esta versión convierte texto: no genera preguntas con IA, no incorpora imágenes ni guarda un historial. Los archivos se procesan en el servidor donde se ejecuta la app.')
