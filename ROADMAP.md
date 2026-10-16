# 🗺️ Roadmap

El objetivo: que **cualquier juego** que quiera la otra persona esté a un clic, **sin tocar archivos de configuración**
y sin salir del panel. Las etiquetas indican el estado real: ✅ hecho · 🚧 en diseño · 💡 idea · ❓ por investigar.

## ✅ Hoy

- Sesión aislada por usuario + Moonshine en la NVIDIA + tailnet personal en netns
- `domictl on/off` con verificación al apagar, `status --json`, `doctor` con pistas
- Panel web: portadas (SteamGridDB), añadir, renombrar y eliminar juegos, estado en vivo
- Buzón `~/Juegos-Domi` (zip/7z/rar/carpeta) → Steam de Domi
- Roblox (Sober) + gamescope, widget de Noctalia, partidas LAN en el mismo PC

## 🚧 Siguiente

### Minecraft Java, con administración de instalaciones desde el panel
Una pestaña **Minecraft** en el panel para gestionar instancias sin abrir ningún launcher a mano.

- Crear, clonar y eliminar instancias (vanilla, Fabric, Quilt, Forge, NeoForge) eligiendo la versión
- Elegir el Java correcto según la versión del juego y fijar el límite de RAM por instancia
- Gestionar mods, resource packs y mundos (importar/exportar, respaldar antes de borrar)
- Cada instancia aparece como juego en el Steam de Domi (o como app de Moonshine) con su propia portada
- Base probable: [Prism Launcher](https://prismlauncher.org/) por línea de comandos / sus archivos de instancia, para no reinventar lo difícil
- Cuenta de Microsoft: inicio de sesión **de Domi** dentro de su sesión; domi-pc nunca guarda ni transmite credenciales

### Minecraft Bedrock
- ❓ Evaluar un launcher compatible en Linux (p. ej. el de la comunidad `mcpelauncher`) corriendo en la sesión de Domi
- ❓ Requisito legal: el juego debe poseerse en la cuenta de quien lo use; el proyecto **no** distribuye ni descarga el juego
- 💡 Alternativa: Bedrock de Windows bajo Proton si el soporte mejora
- 💡 Mando, entrada táctil y pantalla dividida como parte de las pruebas

### Editor de apps de Moonshine en el panel
Hoy Roblox se añade editando `config.toml` a mano. Debería ser un formulario.
- Añadir/quitar apps (comando, directorio, `pre_command` / `post_command`) con validación
- Subir o buscar la portada (SteamGridDB) para cada app
- Plantillas: flatpak, AppImage, Heroic/Lutris, "ejecutable de Proton"
- Reinicio de Moonshine solo cuando nadie está conectado (o avisando)

## 💡 Después

### Más fuentes de juegos
- Epic, GOG y Amazon vía **Heroic** y **Lutris**, con login en la sesión de Domi
- Emuladores (RetroArch y compañía) con mando ya mapeado
- Juegos de navegador / apps web en una ventana de gamescope

### Cuidar al invitado (y a ti)
- Horarios y límite de tiempo por día, con aviso en pantalla antes de cortar
- "Pausa" suave: congelar la sesión sin cerrarla (`SIGSTOP` del cgroup de Domi)
- Notificación en tu escritorio cuando se conecta o se desconecta
- Más de un invitado, cada uno con su usuario, su espacio y sus límites

### Calidad de vida
- Respaldo y restauración de partidas por juego (prefijos de Proton y carpetas de mundos)
- Opciones por juego en el panel: versión de Proton, opciones de lanzamiento, variables de entorno
- Detector de "el driver NVIDIA cambió → reinstalar el runtime del flatpak"
- Barra de progreso al importar juegos grandes
- Modo "actualizar todo": launchers, Proton y flatpaks, con el modo apagado

### Proyecto
- 📦 Paquete para AUR (`domi-pc-git`)
- 🧪 Pruebas automáticas del instalador en un contenedor / VM
- 🌍 Traducciones (README en inglés completo, mensajes de `domictl`)
- 🧱 Soporte oficial para AMD / Intel (encoder VA-API) y otros compositores
- 📸 Capturas y un vídeo corto de demostración

## Cómo proponer algo

Abre un *issue* con la plantilla **Idea** (qué juego o flujo quieres, qué haces hoy a mano, qué esperarías ver).
Si ya sabes cómo hacerlo, mira el [CONTRIBUTING](CONTRIBUTING.md): hay una sección de "primeras tareas".
