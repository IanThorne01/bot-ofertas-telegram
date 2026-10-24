# GUÍA PASO A PASO: tu bot de ofertas en Telegram (100 % gratis)

Pensada para Windows. Tiempo total: 2 a 3 horas la primera vez. Hazla en orden y no saltes pasos.

---------------------------------------------------------------------------------------------
## 0. ¿Qué vas a construir?

    Get on Board (API) ─┐
    Computrabajo (web) ─┼─► main.py ─► filtra y puntúa (config.json) ─► Telegram (tu celular)
    LinkedIn (web) ─────┘                  │
                                           └─► state.json (memoria: qué ya te mandó y qué guardaste)

- **sources.py**  → va a buscar las ofertas a cada sitio.
- **scoring.py**  → les pone puntaje según TU perfil.
- **storage.py**  → recuerda lo ya enviado, para no repetirlo.
- **telegram_api.py** → habla con Telegram.
- **main.py**     → une todo y es lo que se ejecuta.
- **config.json** → AQUÍ decides tú: qué buscar, palabras que suman o restan, mínimo de puntaje.

---------------------------------------------------------------------------------------------
## 1. Instalar lo necesario (una sola vez)

1. **Python**: entra a python.org/downloads, descarga la versión 3.12 o más nueva.
   IMPORTANTE: en el instalador marca la casilla **"Add python.exe to PATH"**.
2. **Visual Studio Code** (el editor): code.visualstudio.com.
3. **Git**: git-scm.com/downloads (todo "Siguiente, siguiente").
4. Comprueba en la terminal (tecla Windows, escribe "cmd", Enter):

       python --version
       git --version

   Si salen versiones, vas bien.

---------------------------------------------------------------------------------------------
## 2. Preparar la carpeta del proyecto

1. Descomprime el ZIP `bot-ofertas.zip` donde quieras (por ejemplo, Documentos).
2. Abre VS Code → Archivo → Abrir carpeta → elige `bot-ofertas`.
3. Abre la terminal de VS Code (menú Terminal → Nueva terminal) y escribe, línea por línea:

       python -m venv venv
       venv\Scripts\activate
       pip install -r requirements.txt

   - La 1.ª crea un "entorno virtual" (una caja aislada para las librerías de este proyecto).
   - La 2.ª lo activa (verás `(venv)` al inicio de la línea).
   - La 3.ª instala las librerías: requests (internet), beautifulsoup4 (leer páginas web) y python-dotenv (leer el .env).
   Si PowerShell dice que "la ejecución de scripts está deshabilitada", usa la terminal "Command Prompt" en lugar de PowerShell.

---------------------------------------------------------------------------------------------
## 3. Crear tu bot en Telegram (gratis)

1. En Telegram busca **@BotFather** (tiene el check azul) y escríbele `/newbot`.
2. Te pide un nombre (ej.: "Ofertas de Ian") y un usuario que termine en `bot` (ej.: `ian_ofertas_bot`).
3. Te entrega un **token**, algo como `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxx`. Es como la contraseña de tu bot:
   NO lo compartas ni lo subas a GitHub.
4. Abre tu bot (el enlace que te da BotFather) y pulsa **Iniciar** o escríbele "hola".

---------------------------------------------------------------------------------------------
## 4. Guardar tus datos secretos en el archivo .env

1. En VS Code, copia `.env.example` y pégalo con el nombre **.env** (así, con el punto al inicio).
2. Ábrelo y pega tu token:

       TELEGRAM_TOKEN=123456789:AAExxxxxxxxxxxxxxxxxxxxxxxx
       TELEGRAM_CHAT_ID=

3. Averigua tu chat_id (el número que identifica TU chat con el bot). En la terminal:

       python main.py --chat-id

   Te imprime "Tu chat_id es: 987654321". Pégalo en `TELEGRAM_CHAT_ID=`. Guarda el archivo.

> Por qué un .env: así el token vive fuera del código. El archivo `.gitignore` ya tiene `.env`,
> por eso Git nunca lo sube.

---------------------------------------------------------------------------------------------
## 5. Primera prueba

    python main.py --prueba

Debe llegarte a Telegram: "✅ ¡Tu bot de ofertas funciona!". Si llega, la mitad del proyecto está lista.

---------------------------------------------------------------------------------------------
## 6. Decidir TÚ qué ofertas quieres (config.json)

Abre `config.json`. Lo que puedes cambiar:

| Campo | Qué hace |
|---|---|
| `buscar` | Las búsquedas (como si las escribieras en la página). Agrega o quita las tuyas. |
| `ubicacion` | País o ciudad para LinkedIn. |
| `solo_remoto` | `true` = solo remoto. |
| `antiguedad_horas` | Descarta ofertas más viejas que esto (72 = 3 días). |
| `puntaje_minimo` | Mientras más alto, menos ofertas pero más relevantes. |
| `max_por_corrida` | Tope de mensajes por ejecución, para que no te inunde. |
| `fuentes` | Pon `false` a la que no quieras (p. ej. `"linkedin": false`). |
| `palabras_suman` | Palabra → puntos. Ej.: `"sql": 3`. Las del TÍTULO valen el doble. |
| `palabras_restan` | Palabras que bajan el puntaje (senior, ventas...). |
| `excluir_si_el_titulo_dice` | Si el título trae una de estas, la oferta se descarta sin más. |

Cómo calcula el puntaje (scoring.py): para cada palabra de tu lista mira si está en el título (peso × 2)
o solo en el texto (peso × 1) y suma todo. Una oferta "Analista de datos junior" con Excel y SQL
suma mucho; una de "Gerente de ventas" ni llega a tu celular.

---------------------------------------------------------------------------------------------
## 7. Prueba "en seco" y luego real

    python main.py --seco

Busca y MUESTRA en pantalla las ofertas que pasarían el filtro, sin enviar ni guardar nada. Úsalo para
afinar `config.json`: si salen muchas basura, sube `puntaje_minimo` o agrega palabras a `palabras_restan`.

Cuando te guste el resultado:

    python main.py

Te llegan las ofertas a Telegram, cada una con dos botones:
- **⭐ Guardar**: la guarda. Escribe `/guardadas` al bot para ver tu lista.
- **🗑 Descartar**: quita los botones y la olvida.

Los botones se procesan en la siguiente ejecución del bot (no al instante, porque el bot no está
encendido todo el tiempo; esto es lo que lo mantiene gratis).

### ¿Y si una fuente dice "falló"?
Es normal y esperado en Computrabajo y LinkedIn (no tienen API oficial):
- **Get on Board** usa la API pública: debería funcionar siempre.
- **LinkedIn** viene APAGADO por defecto (`"linkedin": false`): responde 429 o 999 (bloqueo temporal) con frecuencia.
  Si quieres probarlo, ponlo en `true`, pero con poca frecuencia.
- **Remotive** (API pública) trae ofertas remotas en inglés y el bot solo deja las abiertas a Latinoamérica o al mundo. Desde GitHub Actions suele bloquear más
  que desde tu casa, porque sus IP son de datacenter. Si no te sirve, ponle `false` en `fuentes`.
- **Computrabajo**: si cambia su HTML, hay que ajustar los "selectores" en `parsear_computrabajo()`
  (sources.py). Cómo: abre una búsqueda en el navegador, clic derecho sobre el título de una oferta →
  **Inspeccionar**, mira qué etiqueta y clase tiene (por ejemplo `article` con clase `box_offer`) y
  cámbiala en el código. Corre `python -m unittest` para comprobar que no rompiste nada.
- Siempre usa baja frecuencia y no inicies sesión. Los términos de uso de LinkedIn y Computrabajo
  limitan el scraping: úsalo solo para ti, con pocas búsquedas, y desactiva la fuente si te molesta.

---------------------------------------------------------------------------------------------
## 8. Pruebas automáticas (puntos extra en el portafolio)

    python -m unittest discover -s tests -v

Comprueba el puntaje, los filtros, la memoria y los lectores de páginas con datos de ejemplo, sin internet.
Mostrar pruebas en un proyecto junior llama la atención.

---------------------------------------------------------------------------------------------
## 9. Subirlo a GitHub (con tu cuenta)

> Para este paso y el siguiente usa mejor `GUIA_NUBE.md`, que es más detallada y más fácil de seguir.

1. En github.com crea un repositorio nuevo llamado `bot-ofertas-telegram`. Públicalo (Public) si lo quieres
   en tu portafolio. No marques "Add README" (ya tienes uno).
2. En la terminal de VS Code (dentro de la carpeta):

       git init
       git add .
       git commit -m "Bot de ofertas de trabajo para Telegram"
       git branch -M main
       git remote add origin https://github.com/TU_USUARIO/bot-ofertas-telegram.git
       git push -u origin main

3. **Verifica en la página del repositorio que NO aparezca `.env`.** Si apareciera, borra el repositorio,
   revoca el token con @BotFather (/revoke) y empieza de nuevo.

---------------------------------------------------------------------------------------------
## 10. Que corra solo, gratis (GitHub Actions)

1. En tu repositorio: Settings → Secrets and variables → Actions → **New repository secret**. Crea dos:
   - `TELEGRAM_TOKEN` = tu token
   - `TELEGRAM_CHAT_ID` = tu chat_id
2. Pestaña **Actions** → si pide permiso para activar los flujos, acéptalo.
3. Elige "bot-ofertas" → **Run workflow** para probar a mano. Debe aparecer un check verde y llegarte
   las ofertas.
4. Desde ahora corre solo. El flujo se ejecuta **cada 15 minutos** (para atender tus comandos del chat) y
   **busca ofertas cada 60 minutos** (campo `intervalo_busqueda_min` de `config.json`, para no abusar de los
   sitios). Cada vez que cambia algo, el propio flujo guarda `state.json` en el repositorio: esa es la
   "memoria" del bot entre ejecuciones.
5. Crea el menú de comandos una sola vez desde tu computador: `python main.py --comandos`.
   Luego, al escribir `/` en el chat con tu bot, verás la lista.

Cosas a saber:
- Usa un repositorio **público**: Actions es gratis y sin tope práctico. En uno privado tienes unos 2.000
  minutos al mes y con ejecuciones cada 15 minutos se acaban; si lo prefieres privado, cambia en
  `.github/workflows/bot.yml` el cron a `*/30` o `0 * * * *`.
- Como el repositorio es público, `state.json` (con las ofertas que guardas) también lo es. Son solo
  enlaces de ofertas, nunca tu token ni tu chat_id.
- En repositorios públicos Actions es gratis. GitHub puede pausar los flujos programados si pasan 60 días
  sin actividad en el repositorio; se reactivan con un clic en la pestaña Actions.
- Los horarios no son exactos: pueden atrasarse unos minutos.
- Si prefieres no usar la nube, deja el bot en tu PC: Programador de tareas de Windows → Crear tarea
  básica → repetir cada 30 minutos → acción: ejecutar `venv\Scripts\python.exe main.py` con "Iniciar en"
  la carpeta del proyecto.

---------------------------------------------------------------------------------------------
## 11. Controlarlo desde el chat

| Comando | Qué hace |
|---|---|
| `/estado` | Dice si está activo o en pausa, hace cuánto buscó y cuántas te envió. |
| `/pausar` | Deja de buscar y de enviarte ofertas (sigue escuchando tus comandos). |
| `/reanudar` | Vuelve a buscar en la siguiente ejecución. |
| `/guardadas` | Lista las ofertas que guardaste con ⭐. |
| `/ayuda` | Muestra esta lista. |

**Importante:** el bot no está encendido todo el tiempo; se despierta cada 15 minutos. Por eso tus comandos
y botones se aplican en la siguiente ejecución, con una demora máxima de unos 15 minutos (a veces GitHub
se atrasa un poco más). Es el precio de que sea gratis.

**Resumen diario:** cada mañana (después de las 8:00, hora de Colombia, configurable en `hora_resumen`) te
llega un mensaje con cuántas ofertas revisó y te envió. Sirve de "señal de vida": si un día no llega el
resumen, algo falló y debes mirar la pestaña Actions del repositorio. Si ese día ninguna oferta pasó tu
filtro, el resumen te muestra las 3 más cercanas, para que siempre recibas algo y puedas decidir si bajas
el `puntaje_minimo`.

**Sobre "que siempre haya ofertas":** el bot no puede inventar ofertas. Lo que sí garantiza es que
siempre sabrás qué pasó (resumen diario) y que, si el filtro es muy estricto, te muestre lo más cercano.

---------------------------------------------------------------------------------------------
## 12. Cómo explicarlo en una entrevista

"Hice un pipeline ETL personal: extraigo ofertas de tres fuentes, las transformo (limpieza, duplicados,
puntaje por palabras clave según mi perfil), las cargo en un archivo de estado y las notifico por Telegram.
Corre gratis en GitHub Actions, se controla desde Telegram, tiene pruebas automáticas y maneja fallos de las fuentes
sin caerse."

Ideas para crecer el proyecto (cada una es un commit más en tu GitHub):
1. Cambiar `state.json` por una base SQLite y consultarla con SQL.
2. Un comando `/palabras` para editar tu config desde Telegram.
3. Un tablero en tu página web (GitHub Pages) con estadísticas SIN datos personales: cuántas ofertas
   por día, qué habilidades piden más.
4. Un borrador automático de mensaje al reclutador usando tu perfil.
