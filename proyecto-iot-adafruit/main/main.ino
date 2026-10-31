/*
 * PROYECTO INTEGRADOR IoT - FASE CLOUD (Adafruit IO)
 * Plataforma : ESP32 DevKit v1
 * Asignatura : Internet de las Cosas (IoT) - UTS
 * Integrantes: Neiver Granados & Kevin Gonzalez
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

#include "config.h"   // Credenciales privadas (no se sube a GitHub)

// --- Credenciales Wi-Fi (vienen de config.h) ---
const char* SECRET_SSID     = WIFI_SSID;
const char* SECRET_PASS     = WIFI_PASSWORD;

// --- Credenciales Adafruit IO (vienen de config.h) ---
const char* AIO_SERVER      = "io.adafruit.com";
const int   AIO_PORT        = 1883;
const char* AIO_USERNAME    = AIO_USER;
const char* AIO_KEY         = AIO_KEY_SECRET;

// --- Asignación de Pines en ESP32 ---
#define LDR_PIN       34
#define DHTPIN        4
#define DHTTYPE       DHT11
#define LED_PIN       2
#define BUZZER_PIN    15

// --- Intervalo de publicación ---
const unsigned long INTERVALO_ENVIO = 15000;

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long ultimoEnvio = 0;

String topic_temp;
String topic_hum;
String topic_luz;
String topic_led;
String topic_buzzer;

// ------------------------------------------------
// CONSTRUIR TOPICOS
// ------------------------------------------------

void construirTopicos() {
  String base = String(AIO_USERNAME) + "/feeds/";

  topic_temp   = base + "temperatura";
  topic_hum    = base + "humedad";
  topic_luz    = base + "luminosidad";
  topic_led    = base + "led-rojo";
  topic_buzzer = base + "buzzer";
}

// ------------------------------------------------
// BANNER
// ------------------------------------------------

void imprimirBanner() {
  Serial.println("\n==============================================");
  Serial.println("   SYSTEM INITIALIZATION | ESP32 DevKit v1");
  Serial.println("   Proyecto   : Cloud IoT - Adafruit IO");
  Serial.println("   Integrantes: Neiver Granados & Kevin Gonzalez");
  Serial.println("==============================================\n");
}

// ------------------------------------------------
// CONEXION WIFI
// ------------------------------------------------

void conectarWiFi() {
  Serial.println("[WIFI] Iniciando conexion a la red...");
  Serial.print("[WIFI] SSID: ");
  Serial.println(SECRET_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(SECRET_SSID, SECRET_PASS);

  Serial.print("[WIFI] Conectando ");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[WIFI] Status   : CONECTADO");
  Serial.print("[WIFI] Local IP : ");
  Serial.println(WiFi.localIP());
  Serial.println("----------------------------------------------");
}

// ------------------------------------------------
// RECIBIR COMANDOS MQTT
// ------------------------------------------------

void callback(char* topic, byte* payload, unsigned int length) {

  String mensaje = "";

  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }

  Serial.println("\n>> [ADAFRUIT IO RECIBIDO] --------------------");
  Serial.print("   Topico : ");
  Serial.println(topic);
  Serial.print("   Comando: ");
  Serial.println(mensaje);

  if (String(topic) == topic_led) {

    if (mensaje == "1" || mensaje == "ON") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("   Estado : LED -> ENCENDIDO [HIGH]");
    }
    else if (mensaje == "0" || mensaje == "OFF") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("   Estado : LED -> APAGADO [LOW]");
    }
  }

  else if (String(topic) == topic_buzzer) {

    if (mensaje == "1" || mensaje == "ON") {
      digitalWrite(BUZZER_PIN, HIGH);
      Serial.println("   Estado : BUZZER -> ACTIVADO [HIGH]");
    }
    else if (mensaje == "0" || mensaje == "OFF") {
      digitalWrite(BUZZER_PIN, LOW);
      Serial.println("   Estado : BUZZER -> DESACTIVADO [LOW]");
    }
  }

  Serial.println("----------------------------------------------");
}

// ------------------------------------------------
// CONEXION MQTT
// ------------------------------------------------

void reconnectMQTT() {

  while (!client.connected()) {

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WIFI] Reconectando...");
      WiFi.reconnect();
      delay(2000);
      continue;
    }

    Serial.println("[MQTT] Intentando conectar con io.adafruit.com...");

    String clientId =
      "ESP32_granados_gonzalez_" +
      String(random(0xffff), HEX);

    if (client.connect(
          clientId.c_str(),
          AIO_USERNAME,
          AIO_KEY)) {

      Serial.println("[MQTT] Status : CONECTADO A ADAFRUIT IO EXITOSAMENTE");

      client.subscribe(topic_led.c_str());
      client.subscribe(topic_buzzer.c_str());

      Serial.println("[MQTT] Suscripcion a Feeds activada.");
      Serial.println("----------------------------------------------");

    } else {

      Serial.print("[MQTT] ERROR - Codigo de fallo: ");
      Serial.print(client.state());
      Serial.println(" | Reintentando en 3 segundos...");

      delay(3000);
    }
  }
}

// ------------------------------------------------
// PUBLICAR DATOS
// ------------------------------------------------

void publicarDatos() {

  float temperatura = dht.readTemperature();
  float humedad     = dht.readHumidity();

  int estadoLuz = analogRead(LDR_PIN);

  if (isnan(temperatura) || isnan(humedad)) {
    Serial.println("[ERROR] No se pudo leer el sensor DHT11 en P4!");
    return;
  }

  // Publicar temperatura
  bool envioTemp = client.publish(
    topic_temp.c_str(),
    String(temperatura, 1).c_str()
  );

  // Publicar humedad
  bool envioHum = client.publish(
    topic_hum.c_str(),
    String(humedad, 1).c_str()
  );

  // Publicar luminosidad
  bool envioLuz = client.publish(
    topic_luz.c_str(),
    String(estadoLuz).c_str()
  );

  Serial.println("\n<< [ADAFRUIT IO PUBLICADO] -------------------");

  Serial.print("   [+] Temperatura : ");
  Serial.print(temperatura, 1);
  Serial.print(" C | ");
  Serial.println(envioTemp ? "ENVIADO" : "ERROR");

  Serial.print("   [+] Humedad     : ");
  Serial.print(humedad, 1);
  Serial.print(" % | ");
  Serial.println(envioHum ? "ENVIADO" : "ERROR");

  Serial.print("   [+] Luminosidad : ");
  Serial.print(estadoLuz);
  Serial.print(" (P34) | ");
  Serial.println(envioLuz ? "ENVIADO" : "ERROR");

  Serial.println("----------------------------------------------");
  Serial.println("[INFO] Intervalo: 15 segundos");
  Serial.println("[INFO] Frecuencia: 4 puntos por minuto");
  Serial.println("----------------------------------------------");
}

// ------------------------------------------------
// SETUP
// ------------------------------------------------

void setup() {

  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LDR_PIN, INPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  randomSeed(micros());

  imprimirBanner();
  construirTopicos();

  dht.begin();

  conectarWiFi();

  client.setServer(AIO_SERVER, AIO_PORT);
  client.setCallback(callback);

  Serial.println("[SYSTEM] Inicializacion completada");
}

// ------------------------------------------------
// LOOP PRINCIPAL
// ------------------------------------------------

void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Conexion perdida");
    WiFi.reconnect();
    delay(500);
    return;
  }

  if (!client.connected()) {
    reconnectMQTT();
  }

  client.loop();

  unsigned long tiempoActual = millis();

  if (tiempoActual - ultimoEnvio >= INTERVALO_ENVIO) {

    ultimoEnvio = tiempoActual;

    publicarDatos();
  }
}
