# Generador GIFT y XML para Moodle · Una Vuelta

Versión 1.2 de una microapp en Python y Streamlit. Convierte preguntas de opción múltiple con una sola respuesta correcta a GIFT o Moodle XML UTF-8. Moodle XML incluye las imágenes insertadas en el Word, tanto en el enunciado como en las opciones. No utiliza IA ni necesita claves de API.

## Actualizar la app existente

1. Descomprimir este ZIP.
2. Abrir el repositorio existente en GitHub: https://github.com/unavueltaalmoodle-byte/generador-gift-moodle.
3. En **Add file → Upload files**, subir los archivos que están dentro de `generador-gift` a la raíz del repositorio, reemplazando los anteriores. No subir el ZIP ni la carpeta contenedora.
4. Guardar con **Commit changes**. La app conectada a esa rama incorporará la actualización.
5. Subir un Word con imágenes, revisar la vista previa y descargar XML. En el banco de preguntas, elegir **Formato Moodle XML** para importarlo. Repetir una prueba con texto y GIFT.

No hace falta crear una nueva app. Se agregó `image_xml.py`: es necesario subirlo junto con `app.py` y `gift_core.py`. Las dependencias no cambiaron.

### Cambios de la versión 1.2

- Descarga en Moodle XML para texto e imágenes; GIFT sigue disponible cuando no hay imágenes.
- Extrae PNG, JPG/JPEG y GIF insertados en párrafos y celdas simples del Word.
- Muestra las imágenes dentro de cada pregunta en la vista previa.
- Incluye los archivos de imagen en base64 dentro del campo correspondiente del XML y usa referencias `@@PLUGINFILE@@`. No requiere subir imágenes a otra web.
- Conserva una respuesta correcta, la retroalimentación, los nombres y la categoría opcional. El XML mantiene el orden de las opciones y usa letras A, B, C…
- Bloquea la descarga GIFT si hay imágenes, para impedir una conversión incompleta.
- Avisa sobre imágenes flotantes, vinculadas, recortadas, giradas o de formatos no compatibles, y sobre cuadros de texto u objetos gráficos.

### Cambios de la versión 1.1

- Acepta `Opción correcta: A.` y `Opción correcta: B (explicación).`, también con punto tras la letra antes de la explicación.
- Los errores indican la pregunta por su orden en el archivo, el inicio del enunciado y la línea del texto procesado. La numeración sigue siendo correcta aunque una pregunta anterior tenga errores.
- La app muestra el texto con líneas numeradas para ubicar los errores de Word y TXT.
- Mantiene el bloqueo de la descarga si hay errores; no interpreta varias respuestas como una sola.

## Publicar desde el navegador

1. Descomprimir el ZIP en la computadora. No hace falta instalar Python.
2. Entrar a GitHub y pulsar **+ → New repository**.
3. Nombre sugerido: `generador-gift-moodle`. Elegir público o privado. Para un repositorio privado, Streamlit debe tener los permisos adicionales correspondientes.
4. Pulsar **Create repository**.
5. Usar **uploading an existing file** (o **Add file → Upload files**, si ya tiene archivos).
6. Subir los archivos que están DENTRO de la carpeta `generador-gift`: `app.py`, `gift_core.py`, `image_xml.py`, `requirements.txt`, `ejemplo.txt` y `README.md` (también pueden subir los archivos `test_*.py`). Deben quedar en la raíz del repositorio. No subir el ZIP.
7. Pulsar **Commit changes** para guardar.
8. Entrar en https://share.streamlit.io/ y pulsar **Create app**. Elegir la opción para usar un repositorio existente, **Yup, I have an app** si aparece.
9. Seleccionar el repositorio `generador-gift-moodle`, su rama (normalmente `main`) y **Main file path: `app.py`**. Si subieron la carpeta completa, el archivo principal será `generador-gift/app.py`.
10. Pulsar **Deploy** y esperar a que termine la instalación automática de las dependencias.

Streamlit entregará un enlace para abrir la aplicación. Para actualizarla, modificar los archivos de GitHub y guardar con **Commit changes**.

## Primera prueba

Abrir `ejemplo.txt`, copiar su contenido y pegarlo en la app. Deben aparecer dos preguntas, con respuestas correctas B y A. Descargar el GIFT y hacer una importación de prueba en Moodle.

## Formato de entrada

```text
1. ¿Cuál es la capital de Argentina?
A) Córdoba
B) Buenos Aires
C) Rosario
D) Mendoza
Opción correcta: B (Buenos Aires es la capital de Argentina.)
```

- Enunciado con numeración opcional. Puede ocupar varias líneas.
- Opciones con letras consecutivas desde A: A), B), C)… Cada opción ocupa una sola línea. Se aceptan también A., A: y A-.
- Entre 2 y 26 opciones; una sola correcta.
- Cierre obligatorio: `Opción correcta: B` o `Respuesta correcta: B`.
- Se admite un punto final después de la letra o del paréntesis de cierre.
- La explicación opcional entre paréntesis se asigna como retroalimentación de la respuesta correcta.
- Separar las preguntas con una línea en blanco para facilitar la lectura.
- TXT: codificación UTF-8. Word: formato DOCX. Tamaño máximo procesado: 10 MB.
- En Word, las letras deben estar escritas manualmente: la numeración automática de listas puede no extraerse. Se lee texto e imágenes compatibles de párrafos y celdas, pero no encabezados ni pies de página. Los cuadros de texto deben pasarse a párrafos normales. Las tablas combinadas o complejas pueden requerir copiar y ordenar el texto.
- No admite varias respuestas correctas, verdadero/falso ni retroalimentación individual de cada distractor en esta versión.
- Si hay errores, no se genera un archivo parcial.

## Preparar un Word con imágenes

1. Escribir el enunciado y, antes de la opción A), insertar las imágenes del enunciado.
2. Escribir las opciones A), B), C)… manualmente. La imagen de una opción debe estar junto al texto de esa opción o en el párrafo inmediatamente siguiente, antes de la próxima opción. Una opción puede tener sólo una imagen: escribir `A)` e insertar la imagen después.
3. Para cada imagen, elegir **Opciones de diseño → En línea con el texto**. Usar PNG, JPG/JPEG o GIF. No usar imágenes vinculadas a archivos externos.
4. Si una imagen está recortada, girada o reflejada dentro de Word, guardar primero su aspecto final en un archivo de imagen y volver a insertarla. El conversor no reconstruye esas transformaciones.
5. Cerrar con `Opción correcta: B`, opcionalmente con la explicación entre paréntesis.
6. En la app, elegir **Subir archivo**, cargar el DOCX y desplegar cada pregunta para revisar texto, imágenes y respuesta correcta.
7. Descargar **Moodle XML con imágenes**. El archivo incluye las imágenes y no depende de una dirección web externa.

El texto se conserva, pero no la maquetación, las tipografías o los estilos completos de Word. La app limita el ancho de visualización a 700 píxeles; conserva los datos originales de las imágenes. La suma de los contenidos descomprimidos del DOCX no puede superar 80 MB. Las etiquetas `[[IMAGEN_…]]` de la vista de texto son marcas internas: no deben escribirse manualmente ni se exportan a Moodle.

## Importar en Moodle

Para GIFT: Banco de preguntas → Importar → **Formato GIFT** → cargar `preguntas_moodle.gift` → Importar.

Para XML (con o sin imágenes): Banco de preguntas → Importar → **Formato Moodle XML** → cargar `preguntas_moodle.xml` → Importar.

Si se indicó una categoría en la app, activar **Obtener categoría del archivo**. Si se dejó vacía, seleccionar la categoría de destino en Moodle. La ubicación de estas opciones puede variar según versión y permisos.

Revisar primero en una categoría de prueba las respuestas, la retroalimentación y los caracteres especiales. El conversor valida estructura, no la exactitud disciplinar de las respuestas. La versión anterior fue probada por ustedes en Moodle. Esta versión se verificó con pruebas automatizadas de extracción, asociación de imágenes y estructura XML; falta verificar su importación en el campus. Repetir una importación de prueba después de actualizar, comprobando cada imagen, respuesta y retroalimentación.

## Datos

La app no programa almacenamiento de archivos ni historial. El contenido se procesa en la memoria del servidor de Streamlit; no es procesamiento local. No subir exámenes confidenciales a una aplicación pública sin revisar quién puede acceder y las condiciones del alojamiento. La visibilidad del repositorio y el acceso a la app son configuraciones distintas.

## Ejecutar localmente (opcional)

Con Python instalado, dentro de la carpeta del proyecto:

```bash
python -m venv .venv
```

Activar el entorno en Windows (Símbolo del sistema):

```bat
.venv\Scripts\activate.bat
```

O en macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar y ejecutar:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Pruebas del conversor (opcional)

```bash
python -m unittest discover -v
```

Las pruebas verifican GIFT, texto XML, imágenes en enunciado/opciones, datos base64, tablas, errores y formatos de respuesta. No requieren Streamlit ni conexión a Moodle.

## Referencias

- Moodle XML: https://docs.moodle.org/en/Moodle_XML_format
- GIFT: https://docs.moodle.org/en/GIFT_format
- Publicación en Streamlit: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
