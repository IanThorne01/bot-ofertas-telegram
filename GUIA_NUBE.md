# SUBIR EL BOT A LA NUBE (GitHub Actions) — paso a paso

Meta: que el bot corra solo, gratis y sin tu computador encendido.
Haz un paso, comprueba que salió bien y recién pasa al siguiente.

## PASO 1. Comprobar Git
En la terminal (Command Prompt) escribe:

    git --version

Si sale una versión (ej. `git version 2.45.0`), sigue. Si dice que no se reconoce el comando, instala Git
desde git-scm.com/downloads (todo "Next"), CIERRA y vuelve a abrir VS Code.

## PASO 2. Decirle a Git quién eres (una sola vez)
    git config --global user.name "Ian Thorne"
    git config --global user.email "TU_CORREO_DE_GITHUB"

Ojo: en un repositorio público, ese correo se ve en cada cambio. Si no quieres mostrar el tuyo, en GitHub
ve a Settings → Emails, marca "Keep my email addresses private" y usa el correo
`numero+usuario@users.noreply.github.com` que te muestra ahí.

## PASO 3. Crear el repositorio vacío en GitHub
1. Entra a github.com (con tu sesión iniciada) → botón verde **New** (o el "+" de arriba → New repository).
2. Nombre: `bot-ofertas-telegram`
3. Marca **Public** (así Actions es gratis y además te sirve de portafolio).
4. **NO marques** "Add a README", ni .gitignore, ni licencia.
5. Pulsa **Create repository**. Te queda una página con una dirección parecida a
   `https://github.com/TU_USUARIO/bot-ofertas-telegram.git`. Cópiala.

## PASO 4. Subir tu carpeta
En la terminal de VS Code (abierta en la carpeta bot-ofertas) escribe, una línea a la vez:

    git init
    git add .
    git commit -m "Bot de ofertas de trabajo para Telegram"
    git branch -M main
    git remote add origin PEGA_AQUI_LA_DIRECCION_DEL_PASO_3
    git push -u origin main

Se abrirá una ventana del navegador para iniciar sesión en GitHub: acepta. Al terminar, recarga la página
del repositorio: deben aparecer tus archivos.

**REVISIÓN DE SEGURIDAD:** en la lista de archivos de GitHub NO debe aparecer `.env`.
(Debe aparecer `.env.example`, que es solo la plantilla.) Si apareciera `.env`, avísame de inmediato y
revoca el token con @BotFather (/revoke).

## PASO 5. Guardar tus secretos en GitHub
1. En tu repositorio: **Settings** (arriba) → a la izquierda **Secrets and variables** → **Actions**.
2. Pulsa **New repository secret** y crea DOS secretos (los nombres deben ser EXACTOS):
   - Name: `TELEGRAM_TOKEN`   → Secret: tu token
   - Name: `TELEGRAM_CHAT_ID` → Secret: tu número de chat_id
Los secretos nadie los puede ver después, ni siquiera tú: solo los usa el bot.

## PASO 6. Encender el bot
1. Pestaña **Actions**. Si aparece un botón verde que dice algo como "I understand my workflows, enable
   them", púlsalo.
2. A la izquierda elige **bot-ofertas** → botón **Run workflow** → **Run workflow** (verde).
3. Espera 1 o 2 minutos y recarga. Debe salir un círculo con **check verde**.
   - Si sale una **X roja**: entra a esa ejecución, abre el paso que falló y pégame el texto del error.
4. Mira Telegram: te deben llegar las ofertas.

Desde ese momento corre solo: cada 15 minutos revisa tus comandos y cada 60 busca ofertas.

## PASO 7. Menú de comandos (una vez, desde tu PC)
    python main.py --comandos

Luego escribe `/` en el chat con tu bot: verás /estado /pausar /reanudar /guardadas /ayuda.

## IMPORTANTE después de esto
- Con el bot en la nube, en tu computador usa solo `--seco` o `--prueba`. Si corres `python main.py`
  normal en tu PC, tendrás dos "cerebros" y te llegarán ofertas repetidas.
- Para cambiar qué ofertas recibes: edita `config.json` y súbelo:

      git add .
      git commit -m "ajusto mis filtros"
      git push

- Si GitHub pausa el flujo por inactividad (pasa si el repositorio queda 60 días sin actividad), entra a
  la pestaña Actions y pulsa el botón para reactivarlo.
- Si un día NO te llega el resumen de la mañana, entra a Actions y mira si hay una X roja.
