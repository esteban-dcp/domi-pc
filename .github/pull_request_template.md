## Qué cambia y por qué
<!-- Explica el problema, no solo la solución. -->

## Reglas de oro
- [ ] `off` sigue devolviendo todo (y lo nuevo está en `verify_off` si se enciende con el modo)
- [ ] El invitado no gana acceso al administrador (LAN, input, `$HOME`, servicios)
- [ ] Sin secretos ni datos personales (usuarios, IPs, rutas)

## Pruebas (marca solo lo que de verdad hiciste)
- [ ] `bash -n` / `py_compile` / `node --check`
- [ ] `install-system.sh` dos veces seguidas sin errores
- [ ] `domictl doctor` en verde · `domictl off` → «Todo devuelto»
- [ ] Panel reiniciado y flujo probado en el navegador
