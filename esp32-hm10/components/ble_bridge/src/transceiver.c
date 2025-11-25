/**
 * @file transceiver.c
 * @brief Transceiver mode - UART to BLE bridge
 */

#include <string.h>
#include "ble_bridge_internal.h"
#include "driver/uart.h"

#define UART_PORT_NUM    UART_NUM_0
#define UART_TX_PIN      UART_PIN_NO_CHANGE
#define UART_RX_PIN      UART_PIN_NO_CHANGE

/* Forward declarations */
static void uart_rx_task(void *arg);
static void hm10_data_received(const uint8_t *data, size_t len);

esp_err_t transceiver_init(const ble_bridge_config_t *config)
{
    /* Configure UART */
    const uart_config_t uart_config = {
        .baud_rate = config->transceiver.uart_baud_rate,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    /* Install UART driver */
    esp_err_t ret = uart_driver_install(
        UART_PORT_NUM,
        config->transceiver.uart_buf_size * 2,
        0, 0, NULL, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = uart_param_config(UART_PORT_NUM, &uart_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART param config failed: %s", esp_err_to_name(ret));
        uart_driver_delete(UART_PORT_NUM);
        return ret;
    }

    ret = uart_set_pin(UART_PORT_NUM, UART_TX_PIN, UART_RX_PIN,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART set pin failed: %s", esp_err_to_name(ret));
        uart_driver_delete(UART_PORT_NUM);
        return ret;
    }

    /* Allocate UART buffer */
    g_bridge_state.mode.transceiver.uart_buffer = malloc(config->transceiver.uart_buf_size);
    if (!g_bridge_state.mode.transceiver.uart_buffer) {
        ESP_LOGE(TAG, "UART buffer allocation failed");
        uart_driver_delete(UART_PORT_NUM);
        return ESP_ERR_NO_MEM;
    }

    /* Create UART RX task */
    BaseType_t task_ret = xTaskCreate(
        uart_rx_task,
        "uart_rx_task",
        2048,
        NULL,
        10,
        &g_bridge_state.mode.transceiver.uart_task_handle);

    if (task_ret != pdPASS) {
        ESP_LOGE(TAG, "UART RX task creation failed");
        free(g_bridge_state.mode.transceiver.uart_buffer);
        g_bridge_state.mode.transceiver.uart_buffer = NULL;
        uart_driver_delete(UART_PORT_NUM);
        return ESP_FAIL;
    }

    /* Register callback for HM-10 data */
    ble_bridge_register_recv_callback(hm10_data_received);

    /* Print welcome banner */
    printf("\n");
    printf("========================================\n");
    printf("  ESP32 BLE Bridge - Transceiver Mode\n");
    printf("========================================\n");
    printf("Computer (UART) <-> ESP32 <-> HM-10\n");
    printf("Baud rate: %lu\n", (unsigned long)config->transceiver.uart_baud_rate);
    printf("Waiting for HM-10 connection...\n");
    printf("========================================\n\n");

    ESP_LOGI(TAG, "Transceiver mode initialized");
    return ESP_OK;
}

esp_err_t transceiver_deinit(void)
{
    /* Delete UART task */
    if (g_bridge_state.mode.transceiver.uart_task_handle) {
        vTaskDelete(g_bridge_state.mode.transceiver.uart_task_handle);
        g_bridge_state.mode.transceiver.uart_task_handle = NULL;
    }

    /* Free UART buffer */
    if (g_bridge_state.mode.transceiver.uart_buffer) {
        free(g_bridge_state.mode.transceiver.uart_buffer);
        g_bridge_state.mode.transceiver.uart_buffer = NULL;
    }

    /* Uninstall UART driver */
    uart_driver_delete(UART_PORT_NUM);

    ESP_LOGI(TAG, "Transceiver mode deinitialized");
    return ESP_OK;
}

static void uart_rx_task(void *arg)
{
    uint8_t *buffer = g_bridge_state.mode.transceiver.uart_buffer;
    size_t buf_size = g_bridge_state.config.transceiver.uart_buf_size;

    while (1) {
        /* Read from UART */
        int len = uart_read_bytes(UART_PORT_NUM, buffer, buf_size - 1, 20 / portTICK_PERIOD_MS);

        if (len > 0) {
            buffer[len] = '\0';  /* Null terminate for safety */

            /* Check if HM-10 is connected */
            if (ble_bridge_is_hm10_connected()) {
                /* Log sent data */
                ESP_LOGI(TAG_BT_COM, "%s", buffer);

                /* Send to HM-10 */
                esp_err_t ret = ble_bridge_send_to_hm10(buffer, len);
                if (ret != ESP_OK) {
                    printf("[WARNING] Failed to send data to HM-10\n");
                }
            } else {
                printf("[WARNING] HM-10 not connected. Cannot send data.\n");
            }
        }

        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

static void hm10_data_received(const uint8_t *data, size_t len)
{
    /* Log received data */
    ESP_LOGE(TAG_BT_COM, "%.*s", len, data);

    /* Forward to UART */
    uart_write_bytes(UART_PORT_NUM, (const char *)data, len);
}
