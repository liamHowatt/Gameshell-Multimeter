#define CPI 2
#define ARD 4
#define DAT_OUT 5
#define DAT_IN 3
#define CURRENT_MODE A3
#define VOLT_MODE A2
#define Z1_RESISTOR 12
#define VOLT_MEASURE A1
#define CURRENT_MEASURE A4
#define RESISTANCE_MEASURE A0
#define TIMEOUT 1000
#define BITS 12

bool cpiState;
bool avrState = false;
unsigned long startTime;
int dIn = 0;
int outgoing = 0;
int incoming = 0;

// 0:volt 1:current 2:resistance
byte mode = 0;
int reading = 0;

int exchange(int dOut){
  cpiState = !cpiState;
  dIn = 0;
  
  for(int i=0; i<BITS; i++){
    digitalWrite(DAT_OUT, (dOut >> i) % 2);
    dIn += !digitalRead(DAT_IN) << i;
    avrState = !avrState;
    digitalWrite(ARD, avrState);
    startTime = millis();
    while(cpiState == digitalRead(CPI)){
      if(startTime + TIMEOUT < millis()){
        cpiState = digitalRead(CPI);
        return 0;
      }
    }
    cpiState = !cpiState;
  }
  return dIn;
}

void setup() {
  pinMode(CPI, INPUT_PULLUP);
  pinMode(ARD, OUTPUT);
  pinMode(DAT_OUT, OUTPUT);
  pinMode(DAT_IN, INPUT_PULLUP);

  pinMode(CURRENT_MODE, INPUT_PULLUP);
  pinMode(VOLT_MODE, INPUT_PULLUP);
  pinMode(Z1_RESISTOR, OUTPUT);

  cpiState = digitalRead(CPI);
}

void loop() {
  if (cpiState != digitalRead(CPI)){
    exchange((reading << 2) + mode);
  }
  
  if(!digitalRead(CURRENT_MODE)){
    mode = 1;
    digitalWrite(Z1_RESISTOR, LOW);
    reading = analogRead(CURRENT_MEASURE);
  }
  else if(!digitalRead(VOLT_MODE)){
    mode = 0;
    digitalWrite(Z1_RESISTOR, LOW);
    reading = analogRead(VOLT_MEASURE);
  }
  else{
    mode = 2;
    digitalWrite(Z1_RESISTOR, HIGH);
    reading = analogRead(RESISTANCE_MEASURE);
  }
}
