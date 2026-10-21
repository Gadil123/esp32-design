/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: CC0-1.0
 *
 * Draft board bring-up hooks for Waveshare ESP32-C5-Touch-LCD-2.8.
 * Derived from the factory BSP call sequence; not hardware-validated yet.
 */

#include <string.h>
#include "esp_check.h"
#include "esp_log.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_st7789.h"
#include "esp_lcd_touch.h"
#include "esp_lcd_touch_cst3530.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_board_device.h"
#include "esp_board_periph.h"
#include "dev_gpio_expander.h"
#include "custom_io_expander_ch32v003.h"

static const char *TAG = "C5_TOUCH_2_8_SETUP";

#define LCD_RST_PIN      (IO_EXPANDER_PIN_NUM_1)
#define TOUCH_RST_PIN    (IO_EXPANDER_PIN_NUM_0)
#define POWER_AMP_PIN    (IO_EXPANDER_PIN_NUM_3)

static esp_err_t get_expander(esp_io_expander_handle_t **handle)
{
    /* dev_gpio_expander publishes esp_io_expander_handle_t *, not the handle itself. */
    ESP_RETURN_ON_ERROR(
        esp_board_device_get_handle("gpio_expander", (void **)handle), TAG, "Get gpio_expander failed"
    );
    ESP_RETURN_ON_FALSE(handle != NULL && *handle != NULL && **handle != NULL,
                        ESP_ERR_INVALID_STATE, TAG, "gpio_expander handle is NULL");
    return ESP_OK;
}

esp_err_t io_expander_factory_entry_t(i2c_master_bus_handle_t i2c_handle, const uint16_t dev_addr,
                                      esp_io_expander_handle_t *handle_ret)
{
    esp_err_t ret = custom_io_expander_new_i2c_ch32v003(i2c_handle, dev_addr, handle_ret);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Create CH32V003 expander failed: %s", esp_err_to_name(ret));
    }
    return ret;
}

esp_err_t lcd_panel_factory_entry_t(esp_lcd_panel_io_handle_t io, const esp_lcd_panel_dev_config_t *panel_dev_config,
                                    esp_lcd_panel_handle_t *ret_panel)
{
    esp_io_expander_handle_t *expander = NULL;
    ESP_RETURN_ON_ERROR(get_expander(&expander), TAG, "Get expander failed");

    /* Factory BSP: LCD reset is on expander pin 1, 200 ms low / 200 ms high. */
    ESP_RETURN_ON_ERROR(esp_io_expander_set_level(*expander, LCD_RST_PIN, 0), TAG, "LCD reset low failed");
    vTaskDelay(pdMS_TO_TICKS(200));
    ESP_RETURN_ON_ERROR(esp_io_expander_set_level(*expander, LCD_RST_PIN, 1), TAG, "LCD reset high failed");
    vTaskDelay(pdMS_TO_TICKS(200));

    /* Keep the amplifier enabled; the board has no ESP32 GPIO for PA control. */
    ESP_RETURN_ON_ERROR(esp_io_expander_set_level(*expander, POWER_AMP_PIN, 1), TAG, "PA enable failed");

    esp_lcd_panel_dev_config_t panel_cfg = {0};
    memcpy(&panel_cfg, panel_dev_config, sizeof(panel_cfg));

    ESP_RETURN_ON_ERROR(esp_lcd_new_panel_st7789(io, &panel_cfg, ret_panel), TAG, "Create ST7789 failed");
    ESP_RETURN_ON_FALSE(*ret_panel != NULL, ESP_FAIL, TAG, "ST7789 handle is NULL");

    /*
     * Temporary bring-up backlight: CH32V003 PWM register accepts 0..255.
     * Replace this with a custom display/backlight HAL implementation to get
     * runtime brightness control from Brookesia.
     */
    ESP_RETURN_ON_ERROR(
        custom_io_expander_set_pwm(*expander, 255), TAG, "Backlight PWM failed"
    );

    return ESP_OK;
}

esp_err_t lcd_touch_factory_entry_t(esp_lcd_panel_io_handle_t io, const esp_lcd_touch_config_t *touch_dev_config,
                                    esp_lcd_touch_handle_t *ret_touch)
{
    esp_log_level_set("lcd_panel.io.i2c", ESP_LOG_NONE);
    esp_log_level_set("i2c.master", ESP_LOG_NONE);

    esp_io_expander_handle_t *expander = NULL;
    ESP_RETURN_ON_ERROR(get_expander(&expander), TAG, "Get expander failed");

    /* Factory BSP: touch reset is on expander pin 0, 10 ms low / 10 ms high. */
    ESP_RETURN_ON_ERROR(esp_io_expander_set_level(*expander, TOUCH_RST_PIN, 0), TAG, "Touch reset low failed");
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_RETURN_ON_ERROR(esp_io_expander_set_level(*expander, TOUCH_RST_PIN, 1), TAG, "Touch reset high failed");
    vTaskDelay(pdMS_TO_TICKS(10));

    i2c_master_bus_handle_t i2c_bus = NULL;
    ESP_RETURN_ON_ERROR(
        esp_board_periph_get_handle("i2c_master", (void **)&i2c_bus), TAG, "Get i2c_master failed"
    );

    esp_lcd_touch_config_t touch_cfg = {0};
    memcpy(&touch_cfg, touch_dev_config, sizeof(touch_cfg));
    /* Public BSP: give CST3530 the bus handle so it creates its own I2C device. */
    touch_cfg.user_data = (void *)i2c_bus;

    esp_err_t ret = esp_lcd_touch_new_i2c_cst3530(io, &touch_cfg, ret_touch);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Create CST3530 failed: %s", esp_err_to_name(ret));
    }
    return ret;
}
