void setup() {
  // Communicate with HC-06 in AT mode at the default baudrate of 9600
  // If 9600 fails, you can try 
  Serial3.begin(9600);
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
    // Directly send your command to HC-06. 
    // If you use serial monitor in Arduino IDE, 
    // Serial read would contain line endings ('\n')
    // Note that the AT commands for HC-06 shouldn't contain line endings ('\n')
    Serial3.print(Serial.readStringUntil('\n'));
  }
  // Check if there are responses from HC-06
  if(Serial3.available())
  {
    // Print response to serial monitor with prefix 'BT: '
    Serial.print("BT: ");
    Serial.println(Serial3.readStringUntil('\n'));
  }
}
