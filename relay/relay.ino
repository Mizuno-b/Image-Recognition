#include <M5StickCPlus2.h> // M5StickC Plus2の場合（初代なら <M5StickC.h>）

const int inputPin = 25;  // Jetsonからの入力ピン
const int outputPin = 26; // フォトカプラへの出力ピン

void setup() {
    // M5Stickの初期化
    auto cfg = M5.config();
    M5.begin(cfg);
    
    // ピンモードの設定
    pinMode(inputPin, INPUT);       // G25を入力に設定
    pinMode(outputPin, OUTPUT);     // G26を出力に設定
    digitalWrite(outputPin, LOW);   // 初期状態はOFF
    
    // 画面の初期設定（デバッグ用）
    M5.Lcd.setRotation(1);
    M5.Lcd.setTextSize(2);
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(10, 10);
    M5.Lcd.print("System Ready");
}

void loop() {
    M5.update(); // 本体のボタン等の状態更新（基本処理）

    // Jetsonからの信号を読み取る
    int jetsonStatus = digitalRead(inputPin);

    if (jetsonStatus == HIGH) {
        // Jetsonから「人検知（HIGH）」が来たら、フォトカプラをONにする
        digitalWrite(outputPin, HIGH);
        
        // 画面に状態を表示（確認用）
        M5.Lcd.setCursor(10, 40);
        M5.Lcd.setTextColor(GREEN, BLACK);
        M5.Lcd.print("DETECTED (ON) ");
    } else {
        // 信号がない（LOW）ときは、フォトカプラをOFFにする
        digitalWrite(outputPin, LOW);
        
        // 画面に状態を表示（確認用）
        M5.Lcd.setCursor(10, 40);
        M5.Lcd.setTextColor(WHITE, BLACK);
        M5.Lcd.print("WAITING... (OFF)");
    }

    delay(10); // チャタリング防止・少し待つ
}