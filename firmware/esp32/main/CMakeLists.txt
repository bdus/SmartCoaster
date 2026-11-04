idf_component_register(
    SRCS
        "app_main.c"
        "core_types.c"
        "weight_process.c"
        "intake.c"
        "reminder.c"
        "weight_sensor.c"
        "hydration.c"
        "ui.c"
        "hx711_hw.c"
        "hx711_mock.c"
        "oled.c"
        "button.c"
        "halo.c"
        "battery.c"
        "ble.c"
        "storage.c"
    INCLUDE_DIRS "."
    REQUIRES
        nvs_flash
        esp_driver_gpio
        esp_driver_i2c
        esp_driver_ledc
        esp_adc
        esp_timer
)

if(CONFIG_SMARTCOASTER_BATTERY_STUB)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE SMARTCOASTER_BATTERY_STUB=1)
endif()
