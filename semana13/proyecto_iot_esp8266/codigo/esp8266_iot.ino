/*
 * PROYECTO INTEGRADOR IoT - ADAFRUIT IO
 * Plataforma : ESP8266 NodeMCU
 * Asignatura : Internet de las Cosas - UTS
 * Integrantes: Neiver Granados & Kevin Gonzalez
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// ------------------------------------------------
// WIFI: reemplaza estos valores antes de cargar
// ------------------------------------------------
const char* SECRET_SSID = "TU_RED_WIFI";
const char* SECRET_PASS = "TU_PASSWORD";

// ------------------------------------------------
// ADAFRUIT IO: reemplaza con tus credenciales
// ------------------------------------------------
const char* AIO_SERVER = "io.adafruit.com";
const int AIO_PORT = 1883;
const char* AIO_USERNAME = "TU_USUARIO_ADAFRUIT";
const char* AIO_KEY = "TU_AIO_KEY";

// ------------------------------------------------
// PINES ESP8266 NODEMCU
// ------------------------------------------------
#define LDR_PIN       A0
#define DHTPIN        16  // D0 = GPIO16
#define DHTTYPE       DHT11
#define LED_PIN       5   // D1 = GPIO5
#define BUZZER_PIN    4   // D2 = GPIO4

// true = buzzer activo; false = buzzer pasivo
#define BUZZER_ACTIVO true

// ------------------------------------------------
// CONFIGURACION GENERAL
// ------------------------------------------------
const unsigned long INTERVALO_ENVIO = 15000; // 15 segundos

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long ultimoEnvio = 0;

// ------------------------------------------------
// FEEDS
// ------------------------------------------------
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

  topic_temp = base + "temperatura";
  topic_hum = base + "humedad";
  topic_luz = base + "luminosidad";
  topic_led = base + "led-rojo";
  topic_buzzer = base + "buzzer";
}

// ------------------------------------------------
// CONTROL DEL BUZZER
// ------------------------------------------------
void controlarBuzzer(bool encender) {
  if (BUZZER_ACTIVO) {
    digitalWrite(BUZZER_PIN, encender ? HIGH : LOW);
  } else {
    if (encender) {
      tone(BUZZER_PIN, 2000);
    } else {
      noTone(BUZZER_PIN);
      digitalWrite(BUZZER_PIN, LOW);
    }
  }
}

// ------------------------------------------------
// BANNER
// ------------------------------------------------
void imprimirBanner() {
  Serial.println();
  Serial.println("========================================");
  Serial.println("       SISTEMA IoT - ESP8266");
  Serial.println("       ADAFRUIT IO - MQTT");
  Serial.println("       Neiver Granados");
  Serial.println("       Kevin Gonzalez");
  Serial.println("========================================");

  Serial.println("LDR       : A0");
  Serial.println("DHT11     : D0");
  Serial.println("LED AZUL  : D1");
  Serial.println("BUZZER    : D2");
  Serial.println("----------------------------------------");
}

// ------------------------------------------------
// WIFI
// ------------------------------------------------
void conectarWiFi() {
  Serial.println("[WIFI] Conectando...");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(SECRET_SSID, SECRET_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("[WIFI] CONECTADO");
  Serial.print("[WIFI] IP: ");
  Serial.println(WiFi.localIP());
}

// ------------------------------------------------
// RECIBIR COMANDOS MQTT
// ------------------------------------------------
void callback(char* topic, byte* payload, unsigned int length) {
  String mensaje = "";

  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }

  mensaje.trim();
  mensaje.toUpperCase();

  Serial.println();
  Serial.println("[MQTT] COMANDO RECIBIDO");
  Serial.print("Feed: ");
  Serial.println(topic);
  Serial.print("Valor: ");
  Serial.println(mensaje);

  if (String(topic) == topic_led) {
    if (mensaje == "1" || mensaje == "ON") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("[LED AZUL] ENCENDIDO");
    } else if (mensaje == "0" || mensaje == "OFF") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("[LED AZUL] APAGADO");
    }
  } else if (String(topic) == topic_buzzer) {
    if (mensaje == "1" || mensaje == "ON") {
      controlarBuzzer(true);
      Serial.println("[BUZZER] ACTIVADO");
    } else if (mensaje == "0" || mensaje == "OFF") {
      controlarBuzzer(false);
      Serial.println("[BUZZER] DESACTIVADO");
    }
  }

  Serial.println("----------------------------------------");
}

// ------------------------------------------------
// RECONEXION MQTT
// ------------------------------------------------
void reconnectMQTT() {
  while (!client.connected()) {
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WIFI] Reconectando...");
      WiFi.reconnect();
      delay(2000);
      continue;
    }

    Serial.println("[MQTT] Conectando a Adafruit IO...");
    String clientId = "ESP8266_Neiver_Kevin_" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), AIO_USERNAME, AIO_KEY)) {
      Serial.println("[MQTT] CONECTADO");
      client.subscribe(topic_led.c_str());
      client.subscribe(topic_buzzer.c_str());
      Serial.println("[MQTT] Suscripciones activadas");
    } else {
      Serial.print("[MQTT] Error: ");
      Serial.println(client.state());
      delay(3000);
    }
  }
}

// ------------------------------------------------
// PUBLICAR DATOS
// ------------------------------------------------
void publicarDatos() {
  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();
  int luminosidad = analogRead(LDR_PIN);

  Serial.println();
  Serial.println("========== LECTURAS IoT ==========");

  if (!isnan(temperatura)) {
    bool enviado = client.publish(
      topic_temp.c_str(),
      String(temperatura, 1).c_str()
    );
    Serial.print("Temperatura: ");
    Serial.print(temperatura);
    Serial.print(" C | ");
    Serial.println(enviado ? "ENVIADO" : "ERROR");
  } else {
    Serial.println("[ERROR] Lectura de temperatura DHT11");
  }

  if (!isnan(humedad)) {
    bool enviado = client.publish(
      topic_hum.c_str(),
      String(humedad, 1).c_str()
    );
    Serial.print("Humedad: ");
    Serial.print(humedad);
    Serial.print(" % | ");
    Serial.println(enviado ? "ENVIADO" : "ERROR");
  } else {
    Serial.println("[ERROR] Lectura de humedad DHT11");
  }

  bool enviadoLuz = client.publish(
    topic_luz.c_str(),
    String(luminosidad).c_str()
  );

  Serial.print("Luminosidad ADC: ");
  Serial.print(luminosidad);
  Serial.print(" | ");
  Serial.println(enviadoLuz ? "ENVIADO" : "ERROR");

  Serial.println("==================================");
  Serial.println("[INFO] Proximo envio en 15 segundos");
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
  controlarBuzzer(false);

  randomSeed(micros());
  imprimirBanner();
  construirTopicos();
  dht.begin();

  conectarWiFi();

  client.setServer(AIO_SERVER, AIO_PORT);
  client.setCallback(callback);
  client.setKeepAlive(60);

  Serial.println("[SYSTEM] Inicializacion completada");
}

// ------------------------------------------------
// LOOP
// ------------------------------------------------
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    delay(500);
    return;
  }

  if (!client.connected()) {
    reconnectMQTT();
  }

  client.loop();

  unsigned long ahora = millis();
  if (ahora - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = ahora;
    publicarDatos();
  }
}
