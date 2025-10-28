void setup() {
  // Communicate with HC-05 in AT mode at a baudrate of 38400
  Serial3.begin(38400);
  // Communicate with your PC at a baud rate of 115200
  Serial.begin(115200);
  // Set 10 ms timeout for faster return from readStringUntil()
  Serial.setTimeout(1000);
  Serial3.setTimeout(10);
}

void loop() {
  // Check if there exists user's input
  if(Serial.available())
  {
    // Directly send your command to HC-05. 
    // If you use serial monitor in Arduino IDE, 
    // Serial read would contain line endings ('\n')
    Serial3.println(Serial.readStringUntil('\n'));
  }
  // Check if there are responses from HC-05
  if(Serial3.available())
  {
    // Print response to serial monitor with prefix 'BT: '
    Serial.print("BT: ");
    Serial.println(Serial3.readStringUntil('\n'));
  }
}
