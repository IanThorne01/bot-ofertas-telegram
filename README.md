# Bot de ofertas de trabajo → Telegram

Bot que busca ofertas de empleo remoto en Colombia, las **puntúa según mi perfil** y me avisa por
Telegram con botones para **guardar** o **descartar**. Corre gratis en la nube con GitHub Actions y se controla desde el chat (`/pausar`, `/reanudar`, `/estado`).

## ¿Qué hace?
1. **Extrae** ofertas de Get on Board (API pública), Remotive (API pública, ofertas remotas en inglés para LATAM/mundo) y Computrabajo (página pública de búsqueda). LinkedIn está incluido pero apagado por defecto: bloquea con frecuencia.
2. **Transforma**: limpia el texto, quita repetidas y las ya vistas, descarta títulos no deseados y
   calcula un puntaje con palabras clave y pesos definidos en `config.json`.
3. **Carga**: guarda en `state.json` lo ya enviado y las ofertas que guardo con el botón ⭐.
4. **Notifica**: envía las mejores a Telegram (con botones ⭐ Guardar / 🗑 Descartar), un resumen diario y comandos para pausarlo o consultarlo.

## Tecnologías
Python · Telegram Bot API · requests · BeautifulSoup · GitHub Actions · pruebas con `unittest`

## Cómo correrlo
```bash
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env                             # y pon tu token y chat_id
python main.py --prueba                            # mensaje de prueba
python main.py --seco                              # busca y muestra, sin enviar
python main.py                                     # corrida real
python -m unittest discover -s tests -v            # pruebas
```
Para correrlo solo en la nube: sigue `GUIA_NUBE.md` (subir a GitHub, agregar los *secrets* `TELEGRAM_TOKEN` y
`TELEGRAM_CHAT_ID` y activar Actions).

## Decisiones de diseño
- **Nunca inicia sesión** en ninguna plataforma y **no postula automáticamente**: cuida mis cuentas y
  cada postulación la hago yo, con un buen mensaje.
- Si una fuente falla (cambio de HTML, bloqueo), el bot sigue con las demás y me avisa máximo una vez al día.
- Los secretos viven en `.env` / *GitHub Secrets*, nunca en el código.
- Solo yo puedo usar los botones: el bot ignora cualquier otro chat.

## Límites conocidos
Computrabajo y LinkedIn no tienen API pública; sus páginas pueden cambiar o bloquear conexiones.
Los términos de uso de esas plataformas restringen el scraping, por eso el uso es personal, de baja
frecuencia y sin cuenta.
