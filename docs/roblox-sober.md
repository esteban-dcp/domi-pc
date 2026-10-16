# Roblox (Sober) en la sesión aislada

Roblox no tiene cliente nativo en Linux; se usa [Sober](https://vinegarhq.org/Sober/) (flatpak `org.vinegarhq.Sober`).
Para que funcione dentro de Moonshine hacen falta cuatro cosas. Todas salieron de depurar un cliente que
"abría pero no respondía".

1. **Runtime NVIDIA del flatpak con la versión EXACTA del driver.** Si no coincide, el sandbox no ve la
   NVIDIA y Roblox se dibuja en la iGPU (se nota en `latest.log` de Sober: `Vulkan Device: AMD ...`).
   ```
   nvidia-smi --query-gpu=driver_version --format=csv,noheader     # p. ej. 615.78.08
   pkexec flatpak install --system flathub \
     org.freedesktop.Platform.GL.nvidia-615-78-08 org.freedesktop.Platform.GL32.nvidia-615-78-08
   ```
   Hay que repetirlo tras cada actualización del driver NVIDIA.
2. **Overrides del usuario de juego** (ejecutar como `domi`):
   ```
   flatpak override --user --device=input org.vinegarhq.Sober
   flatpak override --user --nosocket=wayland --socket=x11 org.vinegarhq.Sober
   flatpak override --user --env=VK_DRIVER_FILES=/usr/lib/x86_64-linux-gnu/GL/vulkan/icd.d/nvidia_icd.json org.vinegarhq.Sober
   ```
   El último fija Sober a la NVIDIA (no ve otras GPU).
3. **gamescope.** Sin gestor de ventanas, la ventana de Sober (800x600) no recibe foco ni entrada dentro del
   compositor de Moonshine. `gamescope -f` le da pantalla completa y foco.
4. **Cerrar Sober al salir.** `flatpak run` crea su propio scope de systemd, así que "Quit" en Moonlight no lo
   mata. La app de `system/moonshine-config.example.toml` hace `flatpak kill` antes y después.
