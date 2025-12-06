#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include <stdio.h>

#define HX711_DOUT_PIN 16
#define HX711_SCK_PIN 17

// Function to read a 24-bit value from the HX711
long read_hx711_value() {
    // Wait for DOUT to go low, indicating data is ready
    while (gpio_get(HX711_DOUT_PIN) == 1) {
        // Sleep a little to yield to other processes (optional, but good practice)
        sleep_us(1); 
    }

    unsigned long count = 0;

    // Send 24 clock pulses to read the 24-bit data (MSB first)
    for (int i = 0; i < 24; i++) {
        gpio_put(HX711_SCK_PIN, 1); // Clock high
        sleep_us(1); // Clock pulse must be short

        // Shift the read bit into the count
        count = count << 1;
        if (gpio_get(HX711_DOUT_PIN)) {
            count++;
        }

        gpio_put(HX711_SCK_PIN, 0); // Clock low
        sleep_us(1); 
    }

    // Send the 25th pulse for channel A and gain 128 (datasheet requirement)
    gpio_put(HX711_SCK_PIN, 1);
    sleep_us(1);
    gpio_put(HX711_SCK_PIN, 0);
    sleep_us(1);

    // Convert the 24-bit 2's complement number to a signed long
    // If the 24th bit (sign bit) is set, we need to extend the sign
    if (count & 0x800000) {
        // Perform 2's complement conversion for negative numbers
        return (long)((~count + 1) * -1); 
    } else {
        return (long)count;
    }
}

// Function to initialize GPIO pins
void hx711_init() {
    gpio_init(HX711_SCK_PIN);
    gpio_init(HX711_DOUT_PIN);
    
    gpio_set_dir(HX711_SCK_PIN, GPIO_OUT);
    gpio_set_dir(HX711_DOUT_PIN, GPIO_IN);

    // Start with SCK low
    gpio_put(HX711_SCK_PIN, 0);

    // Wait for the sensor to settle after power-up (approx 50ms min)
    sleep_ms(100); 
}

// Simple tare function (adjust for better averaging in production)
long tare_offset = 0;

void hx711_tare() {
    long sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += read_hx711_value();
        sleep_ms(10); // Small delay between reads
    }
    tare_offset = sum / 10;
}

long hx711_get_weight() {
    return ((read_hx711_value() - tare_offset) & 0x0000ffff);
    // return (read_hx711_value() & 0x0000ffff);
}
