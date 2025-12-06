#include <stdio.h>
#include "pico/stdlib.h"
#include "hx711_driver.c" // Include the driver code

int main() {
    stdio_init_all(); // Initialize USB serial communication
    sleep_ms(2000); // Wait for serial connection to open
    printf("Starting HX711 Pico C Driver Example\n");

    hx711_init();
    printf("HX711 initialized. Taring scale...\n");
    hx711_tare();
    printf("Tare complete. Offset: %ld\n", tare_offset);

    while (1) {
        long raw_value = hx711_get_weight();
        // Use your calibration factor here to convert raw_value to grams/lbs
        // Example: float weight_grams = (float)raw_value / calibration_factor;
        
        printf("Raw Weight Value (Offset Applied): %ld\n", raw_value);

        sleep_ms(500);
    }
}

