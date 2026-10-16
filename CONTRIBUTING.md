# 🤝 Contribuir a domi-pc

Gracias por querer meter mano. Este proyecto tiene una particularidad que lo vuelve distinto a la mayoría:
**el código corre con permisos de root y separa a dos personas dentro de un mismo equipo.** Un fallo no es solo
un bug: puede ser que el juego de alguien vea tus archivos. Por eso este documento es más estricto de lo normal,
y a cambio es corto y sin relleno.

## 🏛️ Las tres reglas de oro

Todo cambio se mide contra esto. Si un PR rompe una, no se acepta aunque sea genial.

1. **`off` devuelve todo.** Tras `domictl off`, no queda ningún proceso, GPU, puerto, namespace ni servicio del invitado.
   Si añades algo que se enciende con el modo, tiene que apagarse **y** estar en `verify_off`.
2. **El invitado no toca al administrador.** Ni su LAN, ni su input, ni su `$HOME`, ni sus servicios. Si dudas de si un
   cambio abre una puerta, ábrelo como *issue* primero y lo hablamos.
3. **Cero secretos y cero datos personales.** Ni claves, ni IPs, ni nombres de usuario, ni rutas `/home/tu-usuario`
   en el repo. Todo va por `/etc/domi-pc.conf` o por las plantillas `@ADMIN@ @DOMI@ @NV_PCI@`.

## 🧪 Antes de abrir un PR

Marca esto en la descripción. Si no pudiste probar algo, **dilo**: preferimos honestidad a un check falso.

- [ ] `bash -n` en cada script de shell que tocaste (y `shellcheck` si lo tienes)
- [ ] `python3 -m py_compile` en los `.py`, y `node --check scripts/panel/app.js` si tocaste el panel
- [ ] `pkexec bash "$PWD/system/install-system.sh"` corre sin errores **dos veces seguidas** (es idempotente)
- [ ] `domictl doctor` termina en «Todo en orden»
- [ ] `domictl off` termina en «Todo devuelto» (con el modo encendido de verdad, no solo apagado)
- [ ] Si tocaste el panel: lo reiniciaste (`domictl panel`) y probaste el flujo completo en el navegador
- [ ] Buscaste datos personales: `git grep -nIiE "tu-usuario|tu-correo|100\.[0-9]+\.|BEGIN .*PRIVATE"`
- [ ] No añadiste imágenes ni binarios con derechos de terceros (portadas, logos, ejecutables)

> ⚠️ **No pruebes `domictl on` con trabajo sin guardar.** Cierra tu IDE (JetBrains) y detiene Docker a propósito.

## 🛠️ Entorno de desarrollo

```bash
git clone https://github.com/esteban-dcp/domi-pc && cd domi-pc
pkexec bash "$PWD/system/install-system.sh"   # tras editar scripts/ o system/, repite esto
```

- `bin/` y `scripts/` se instalan en `/usr/local/lib/domi-pc/` (root). **Editar el repo no cambia lo instalado** hasta que reinstales.
- El panel que ya estaba abierto sigue con el código viejo: el instalador lo cierra, y lo reabres con `domictl panel`.
- Las plantillas de `system/` llevan `@ADMIN@`, `@DOMI@` y `@NV_PCI@`; el instalador las rellena. No las sustituyas a mano.
- El panel corre **como el usuario invitado**. Piensa siempre: *¿qué podría hacer un juego malicioso con este endpoint?*

## 🧱 Estilo

- **Shell:** `set -uo pipefail`, comillas en todo, funciones pequeñas, mensajes con `ok` / `warn` / `err` / `info`. Sin dependencias raras.
- **Python:** biblioteca estándar (más `vdf`), tipado donde ayude, nada de frameworks. El panel es una sola dependencia de cero.
- **JS/CSS del panel:** sin build, sin librerías, sin `onclick` inline; escapa todo lo que venga de fuera con `esc()`.
- **Comentarios:** explican el *porqué* (un permiso, un caso borde, un bug que costó horas), no lo que el código ya dice.
- **Idioma:** el proyecto es en español. Los PR en inglés también son bienvenidos.

## 📝 Commits y PRs

- Un cambio, un PR. Mejor pequeño y revisable que enorme y heroico.
- Commits en imperativo y concretos: `Añade verify_off para puertos de Moonshine`, no `arreglos`.
- Explica el **problema**, no solo la solución. Si arreglas un bug, pega la salida que lo mostraba.
- Cambios de seguridad (firewall, udev, sudoers, polkit): describe **qué amplía o reduce** y por qué es aceptable.

## 🔒 Reportar un problema de seguridad

**No abras un issue público** si el fallo permite que el invitado salga de su sesión o lea cosas del administrador.
Usa *Security → Report a vulnerability* en GitHub (aviso privado). Te respondemos lo antes posible.

## Reporta tu hardware

La matriz de hardware probado es corta y queremos que crezca. Si lo pruebas, abre un issue **Hardware** con:

| Dato | Cómo obtenerlo |
|---|---|
| Distro y kernel | `uname -r`, `cat /etc/os-release` |
| GPU y driver | `nvidia-smi --query-gpu=name,driver_version --format=csv` |
| Compositor del administrador | Hyprland, Sway, GNOME, KDE… |
| Resultado | `domictl doctor` y `domictl off` (**borra tu nombre, IPs y rutas antes de pegar**) |
| Cliente Moonlight | dispositivo, resolución y si la entrada funciona |

Quitar `100.x.x.x`, tu usuario y tu correo de lo que pegues es tu responsabilidad. Revísalo dos veces.

## 🎯 Primeras tareas (para entrar sin sufrir)

Etiquetadas como `good first issue` cuando existan. Ideas ordenadas de más fácil a más ambiciosa:

1. **Versión en inglés completa** del README y de los mensajes de `domictl`.
2. **Paquete para AUR** (`PKGBUILD` que instale `bin/`, `scripts/` y `system/`).
3. **`doctor` más listo:** detectar que el runtime del flatpak de NVIDIA ya no coincide con el driver y decirlo.
4. **Pruebas del instalador** en un contenedor o VM, dos pasadas, comprobando idempotencia.
5. **Plantillas de apps de Moonshine** (flatpak, AppImage, Heroic) para el [editor de apps](ROADMAP.md).
6. **Minecraft Java en el panel** ([ROADMAP](ROADMAP.md)): la pieza grande que más pidieron.

## 🎖️ Hall of Aura

Todo contribuidor que deje `domictl off` en verde con su cambio gana, de forma totalmente oficial, **+100 de aura**
y un lugar en este archivo. Pasa por el PR, no hace falta pedirlo.

*(vacío por ahora… ¿serás el primero?)*

---

¿Dudas antes de empezar? Abre un *issue* con la plantilla **Idea** y lo hablamos: preferimos una conversación corta
a un PR de 800 líneas que no podemos aceptar.
