# Arquitectura y Plan del Proyecto DDNS Controller

Esta arquitectura resuelve el dilema de tener un entorno demostrable y visual en la nube sin gastar dinero, sin exponer tu red doméstica y sin cortar la conexión durante las pruebas.

---

## Los Actores del Sistema

```text
[Reclutador / Navegador]
       │ 
       ▼ (1. Acceso web continuo)
[Dominio A: api-panel.duckdns.org] ──► [Máquina Virtual AWS (EC2)]
                                            │
                                            ├─► [Docker: API + HTML Dashboard]
                                            │        │
                                            │        ▼ (2. Envío de cambio de IP)
                                            │   [DuckDNS API]
                                            │        │
                                            │        ▼ (3. Actualiza registro)
                                            └─► [Dominio B: test-target.duckdns.org]
                                                     ▲
                                                     │ (4. Consulta DNS de verificación)
                                             [Servidores DNS Globales]
```

### 1. El Reclutador (Usuario / Evaluador)
- Accede a `api-panel.duckdns.org` desde su navegador.
- Visualiza un dashboard con dos secciones: el estado actual del servicio y un formulario para enviar una nueva IP al dominio de prueba.
- Ejecuta consultas o pulsa botones sin riesgo de perder acceso al panel.

### 2. Dominio A (`api-panel.duckdns.org` — El Dominio Fijo)
- Apunta de forma permanente a la IP pública de tu máquina virtual en AWS.
- **Misión:** Garantizar que la interfaz web y los endpoints de la API estén siempre accesibles. Este dominio nunca se modifica en las pruebas.

### 3. Dominio B (`test-target.duckdns.org` — El Dominio Conejillo de Indias)
- Es el registro DNS que tu API manipula.
- **Misión:** Recibir las actualizaciones de IP (simuladas o reales). Su único propósito es demostrar que la API puede alterar registros en DuckDNS en tiempo real y que los servidores DNS de Internet reflejan el cambio.

### 4. DuckDNS (El Proveedor DNS Autoritativo)
- Mantiene la base de datos de nombres.
- Expone una API REST protegida por un token privado que tu backend consume para actualizar los registros tipo A.

---

## Rol de cada tecnología y por qué es estrictamente necesaria

| Tecnología | ¿Qué hace en el proyecto? | ¿Por qué es estrictamente necesaria? |
| :--- | :--- | :--- |
| **Terraform** | Define en código (`.tf`) la máquina EC2 en AWS, la red (VPC), la IP pública y las reglas de firewall (Security Groups para puertos 80/443). | **Elimina la configuración manual.** Demuestra a la empresa que no creas infraestructura "haciendo clics" en una consola web, sino mediante Infraestructura como Código (IaC) reproducible y versionable. |
| **Docker** | Empaqueta el runtime (Node.js o Python), las dependencias del servidor y el código de la API en una imagen autocontenida. | **Aislamiento y portabilidad.** Evita el problema de "en mi máquina funciona pero en AWS falla por versiones de librerías". La máquina virtual solo necesita instalar el motor de Docker para correr el servicio idéntico al de tu entorno local. |
| **API Backend (FastAPI o Express)** | Procesa las peticiones, valida tokens de seguridad, gestiona la idempotencia (no llamar a DuckDNS si la IP no cambió) y consulta la resolución DNS real. | **Lógica de negocio.** Es el núcleo del servicio. Proporciona los endpoints estructurados (`POST /v1/sync`, `GET /v1/status`) y sirve la página HTML estática del dashboard. |
| **GitHub Actions (CI/CD)** | Cada vez que haces `git push` a `main`, ejecuta los tests unitarios, construye la imagen Docker, se conecta por SSH a la VM de AWS y despliega la nueva versión sin tiempo de inactividad. | **Automatización profesional.** Demuestra que dominas el ciclo completo de entrega continua: el código viaja del repositorio a producción sin intervención humana manual. |

---

## Flujo paso a paso durante una prueba

1. **Acceso al panel:** El reclutador entra a [http://api-panel.duckdns.org](http://api-panel.duckdns.org).
2. **Visualización inicial:** En el panel ve:
   - Dominio objetivo: `test-target.duckdns.org`
   - IP resuelta actualmente: `198.51.100.1`
3. **Acción del usuario:** El reclutador introduce una nueva IP (por ejemplo, `203.0.113.88`) y pulsa **Actualizar**.
4. **Procesamiento de la petición:** La API en AWS recibe la petición, valida la estructura y ejecuta una llamada HTTP a DuckDNS:
   ```http
   GET https://www.duckdns.org/update?domains=test-target&token=SECRET_TOKEN&ip=203.0.113.88
   ```
5. **Respuesta del proveedor:** DuckDNS responde `OK`.
6. **Verificación DNS:** La API realiza una consulta de resolución directa (`dns.resolve4('test-target.duckdns.org')`) y devuelve la respuesta al frontend.
7. **Confirmación en la UI:** El dashboard muestra: *"IP actualizada correctamente a 203.0.113.88"*. La sesión del reclutador sigue intacta porque `api-panel.duckdns.org` jamás cambió de dirección.
