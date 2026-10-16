from pathlib import Path
import streamlit as st
from gift_core import parse_questions, make_gift, FormatError
from image_xml import read_docx_with_images, make_xml, IMAGE_TOKEN

st.set_page_config(page_title='Generador GIFT y XML · Una Vuelta', page_icon='📝', layout='centered')
st.title('Generador GIFT y XML para Moodle')
st.write('Convertí preguntas de opción múltiple en un archivo listo para importar al banco de preguntas.')
st.caption('Versión 1.4 · Una respuesta correcta por pregunta · Retroalimentación opcional · Imágenes de Word en Moodle XML')
example = Path(__file__).with_name('ejemplo.txt').read_text(encoding='utf-8')


def numbered_text(text):
    st.caption('Estas líneas corresponden al texto procesado; pueden diferir de las líneas visibles en Word.')
    st.code('\n'.join(f'{i:>4} | {line}' for i, line in enumerate(text.lstrip('\ufeff').splitlines(), 1)), language=None)


def preview(text, images):
    offset = 0
    for match in IMAGE_TOKEN.finditer(text):
        if text[offset:match.start()].strip():
            st.text(text[offset:match.start()])
        image = images[match.group()]
        st.image(image.data, width=image.width, caption=image.alt or None)
        offset = match.end()
    if text[offset:].strip():
        st.text(text[offset:])


with st.expander('Cómo preparar las preguntas', expanded=True):
    st.write('Escribí las opciones con letras consecutivas: A), B), C)… Cada opción de texto debe ocupar una sola línea. Cerrá cada pregunta con «Opción correcta: B».')
    st.write('Para agregar retroalimentación: «Opción correcta: B (Explicación)». También se acepta un punto después de la letra o del paréntesis. El enunciado puede ocupar varias líneas.')
    st.write('Para una devolución distinta por opción, agregá después de «Opción correcta» líneas como «Retroalimentación A: explicación», «Retroalimentación B: explicación», etc. Sirve tanto para la correcta como para las incorrectas. No dupliques la devolución de la correcta en una etiqueta y entre paréntesis.')
    st.write('Para una devolución general de la pregunta, agregá después de «Opción correcta» una línea «Retroalimentación general: explicación». Es opcional y puede coexistir con la devolución entre paréntesis. Escribí toda la devolución en una sola línea o párrafo; el ajuste automático de líneas de Word no afecta la lectura.')
    st.write('Con imágenes: subí un Word (.docx), con imágenes PNG, JPG o GIF insertadas «En línea con el texto». Colocá las imágenes del enunciado antes de A). Para una opción, insertá la imagen junto a su texto o en el párrafo inmediatamente posterior a su letra, antes de la siguiente opción. También podés escribir A) y luego insertar sólo la imagen.')
    st.caption('Las imágenes se guardan dentro del XML. Revisá su ubicación en la vista previa. Se conserva el texto y el orden de las imágenes; no el diseño, las tipografías ni el formato completo de Word.')
    st.code(example, language=None)
    st.download_button('Descargar plantilla de texto', example.encode('utf-8'), 'ejemplo.txt', 'text/plain', key='template')

mode = st.radio('¿Cómo querés cargar las preguntas?', ['Pegar texto', 'Subir archivo'], horizontal=True)
text, images = '', {}
if mode == 'Pegar texto':
    text = st.text_area('Preguntas', height=300, placeholder=example)
    st.caption('Para incluir imágenes, elegí «Subir archivo» y cargá un Word (.docx).')
else:
    upload = st.file_uploader('Archivo TXT o Word (.docx), hasta 10 MB', type=['txt', 'docx'])
    st.caption('Word: escribí las letras A), B)… manualmente. No se extraen encabezados ni pies de página. Pasá los cuadros de texto a párrafos normales y las imágenes a «En línea con el texto».')
    if upload is not None:
        try:
            data = upload.getvalue()
            if len(data) > 10 * 1024 * 1024:
                raise FormatError('El archivo supera los 10 MB. Reducí el tamaño de las imágenes o dividí las preguntas.')
            if upload.name.lower().endswith('.docx'):
                content = read_docx_with_images(data)
                text, images = content.text, content.images
            else:
                text = data.decode('utf-8-sig')
        except FormatError as error:
            st.error(str(error))
        except UnicodeDecodeError:
            st.error('El TXT debe estar guardado como UTF-8. Podés copiar su contenido y usar «Pegar texto».')
        except Exception:
            st.error('No se pudo leer el archivo. Comprobá que sea un TXT UTF-8 o un DOCX válido de hasta 10 MB.')
    if text:
        with st.expander('Ver texto extraído del archivo'):
            numbered_text(text)
            if images:
                st.caption('Las etiquetas [[IMAGEN_…]] indican dónde se extrajo cada imagen. Las imágenes se muestran más abajo, dentro de cada pregunta.')

category = st.text_input('Categoría en Moodle (opcional)', placeholder='Parcial · Módulo 1')
prefix = st.text_input('Prefijo de los nombres de pregunta', value='Pregunta')
st.caption('Sin categoría indicada, elegirás la categoría al importar en Moodle.')

if text.strip():
    try:
        questions = parse_questions(text, images)
        xml = make_xml(questions, category, prefix)
    except FormatError as error:
        st.error('Corregí estos detalles antes de descargar:')
        st.text(str(error))
        with st.expander('Ubicar los errores en el texto con líneas numeradas'):
            numbered_text(text)
    else:
        image_count = sum(len(q.images) for q in questions)
        st.success(f'{len(questions)} preguntas listas' + (f' · {image_count} imágenes incluidas.' if image_count else '.'))
        st.caption('Revisá el contenido, la ubicación de las imágenes y las respuestas correctas antes de descargar.')
        for index, question in enumerate(questions, 1):
            with st.expander(f'Pregunta {index:03d} · Correcta: {question.correct}'):
                preview(question.stem, question.images)
                for letter, option in question.options.items():
                    st.text(f'{"✓" if letter == question.correct else "·"} {letter})')
                    preview(option, question.images)
                    if question.feedback_for(letter):
                        st.text(f'Retroalimentación de {letter}: ' + question.feedback_for(letter))
                if question.general_feedback:
                    st.text('Retroalimentación general de la pregunta: ' + question.general_feedback)
        if image_count:
            st.info('Estas preguntas contienen imágenes. Descargá Moodle XML para conservarlas.')
            st.download_button('Descargar Moodle XML con imágenes', xml.encode('utf-8'), 'preguntas_moodle.xml', 'application/xml', type='primary')
        else:
            output_format = st.radio('Formato de descarga', ['GIFT', 'Moodle XML'], horizontal=True)
            if output_format == 'GIFT':
                gift = make_gift(questions, category, prefix)
                st.download_button('Descargar archivo GIFT', gift.encode('utf-8'), 'preguntas_moodle.gift', 'text/plain', type='primary')
                with st.expander('Ver código GIFT generado'):
                    st.code(gift, language=None)
            else:
                st.download_button('Descargar Moodle XML', xml.encode('utf-8'), 'preguntas_moodle.xml', 'application/xml', type='primary')
else:
    st.info('Pegá tus preguntas o subí un archivo para comenzar.')

with st.expander('Cómo importar en Moodle'):
    st.write('Abrí el banco de preguntas del curso → Importar. Para un archivo .gift, elegí «Formato GIFT»; para un archivo .xml, elegí «Formato Moodle XML». Cargá el archivo y pulsá Importar.')
    st.write('Si incluiste categoría, activá «Obtener categoría del archivo»; si no, seleccioná la categoría de destino. Hacé una primera prueba en una categoría de prueba y verificá las respuestas, las imágenes y su retroalimentación.')
    st.write('Para mostrar la devolución general de cada pregunta, revisá «Opciones de revisión → Retroalimentación general» en el cuestionario de Moodle. Su visibilidad depende de esa configuración.')
    st.caption('El XML conserva el orden de las opciones y usa letras A, B, C… Podés modificar la configuración de las preguntas en Moodle después de importar.')
st.caption('La app no genera preguntas con IA ni guarda un historial. Los archivos se procesan en el servidor donde se ejecuta la app.')
