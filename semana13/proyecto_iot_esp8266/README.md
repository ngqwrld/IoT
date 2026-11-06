# Proyecto IoT - ESP8266 y Adafruit IO

**Integrantes:** Neiver Granados y Kevin Gonzalez  
**Plataforma:** ESP8266 NodeMCU  
**Sensores/actuadores:** LDR, DHT11, LED azul y buzzer  
**Comunicación:** MQTT con Adafruit IO

## Contenido
- `codigo/esp8266_iot.ino`: programa completo para Arduino IDE.

## Conexiones
| Componente | Pin NodeMCU |
|---|---|
| Fotoresistencia (salida del divisor) | A0 |
| DHT11 (DATA) | D0 |
| LED azul (con resistencia en serie) | D1 |
| Buzzer (control) | D2 |

Conecta GND de los módulos al GND común. La LDR debe formar un divisor de tensión; no conectes la LDR directamente entre A0 y GND sin el circuito correspondiente. Verifica el voltaje máximo admitido por A0 en tu placa ESP8266 (algunas placas NodeMCU incorporan divisor y otras no).

## Antes de cargar el programa
1. Abre `codigo/esp8266_iot.ino` en Arduino IDE.
2. Sustituye `TU_RED_WIFI`, `TU_PASSWORD`, `TU_USUARIO_ADAFRUIT` y `TU_AIO_KEY` por tus credenciales.
3. Instala las librerías `PubSubClient` y `DHT sensor library` (junto con `Adafruit Unified Sensor` si el gestor la solicita).
4. Selecciona la placa ESP8266 NodeMCU y el puerto COM correcto.
5. Compila y carga el programa.

## Feeds esperados en Adafruit IO
- `temperatura`
- `humedad`
- `luminosidad`
- `led-rojo`
- `buzzer`

El feed de control del LED conserva el nombre `led-rojo` porque así está definido en el código original, aunque el componente físico sea un LED azul. Si en Adafruit IO el feed se llama de otra manera, cambia el nombre en `construirTopicos()`.

## Nota sobre el buzzer
El código está configurado inicialmente para buzzer activo (`BUZZER_ACTIVO true`). Si el componente es pasivo, cambia el valor a `false`. Si no conoces el tipo, compruébalo antes de energizarlo.

## Seguridad
No publiques tus contraseñas ni tu AIO Key en un repositorio público. El archivo incluido usa marcadores de posición para proteger tus credenciales. Como las credenciales reales se compartieron en el chat, es recomendable cambiar la contraseña del punto de acceso Wi-Fi y regenerar la AIO Key en Adafruit IO antes de continuar.
