/* oled.c — minimal SSD1306 128x32 driver over the ESP-IDF v6 I2C master API. */
#include "oled.h"

#include <string.h>

#include "font_cn.h"

#include <string.h>

#include "driver/i2c_master.h"
#include "esp_log.h"

static const char *TAG = "oled";

#define OLED_FB_SIZE (OLED_WIDTH * OLED_PAGES)

static i2c_master_bus_handle_t s_bus;
static i2c_master_dev_handle_t s_dev;
static bool s_ready;
static uint8_t s_fb[OLED_PAGES][OLED_WIDTH];

/* 5x7 column-major font (LSB = top row), ASCII subset used by the UI. */
typedef struct {
    char ch;
    uint8_t col[5];
} glyph_t;

static const glyph_t s_font[] = {
    {' ', {0x00, 0x00, 0x00, 0x00, 0x00}},
    {'+', {0x08, 0x08, 0x3E, 0x08, 0x08}},
    {'-', {0x08, 0x08, 0x08, 0x08, 0x08}},
    {'.', {0x00, 0x60, 0x60, 0x00, 0x00}},
    {'/', {0x20, 0x10, 0x08, 0x04, 0x02}},
    {':', {0x00, 0x36, 0x36, 0x00, 0x00}},
    {'%', {0x62, 0x64, 0x08, 0x13, 0x23}},
    {'?', {0x02, 0x01, 0x51, 0x09, 0x06}},
    {'>', {0x41, 0x22, 0x14, 0x08, 0x00}},
    {'0', {0x3E, 0x51, 0x49, 0x45, 0x3E}},
    {'1', {0x00, 0x42, 0x7F, 0x40, 0x00}},
    {'2', {0x42, 0x61, 0x51, 0x49, 0x46}},
    {'3', {0x21, 0x41, 0x45, 0x4B, 0x31}},
    {'4', {0x18, 0x14, 0x12, 0x7F, 0x10}},
    {'5', {0x27, 0x45, 0x45, 0x45, 0x39}},
    {'6', {0x3C, 0x4A, 0x49, 0x49, 0x30}},
    {'7', {0x01, 0x71, 0x09, 0x05, 0x03}},
    {'8', {0x36, 0x49, 0x49, 0x49, 0x36}},
    {'9', {0x06, 0x49, 0x49, 0x29, 0x1E}},
    {'A', {0x7E, 0x11, 0x11, 0x11, 0x7E}},
    {'B', {0x7F, 0x49, 0x49, 0x49, 0x36}},
    {'C', {0x3E, 0x41, 0x41, 0x41, 0x22}},
    {'D', {0x7F, 0x41, 0x41, 0x22, 0x1C}},
    {'E', {0x7F, 0x49, 0x49, 0x49, 0x41}},
    {'F', {0x7F, 0x09, 0x09, 0x09, 0x01}},
    {'G', {0x3E, 0x41, 0x49, 0x49, 0x7A}},
    {'H', {0x7F, 0x08, 0x08, 0x08, 0x7F}},
    {'I', {0x00, 0x41, 0x7F, 0x41, 0x00}},
    {'J', {0x20, 0x40, 0x41, 0x3F, 0x01}},
    {'K', {0x7F, 0x08, 0x14, 0x22, 0x41}},
    {'L', {0x7F, 0x40, 0x40, 0x40, 0x40}},
    {'M', {0x7F, 0x02, 0x0C, 0x02, 0x7F}},
    {'N', {0x7F, 0x04, 0x08, 0x10, 0x7F}},
    {'O', {0x3E, 0x41, 0x41, 0x41, 0x3E}},
    {'P', {0x7F, 0x09, 0x09, 0x09, 0x06}},
    {'Q', {0x3E, 0x41, 0x51, 0x21, 0x5E}},
    {'R', {0x7F, 0x09, 0x19, 0x29, 0x46}},
    {'S', {0x46, 0x49, 0x49, 0x49, 0x31}},
    {'T', {0x01, 0x01, 0x7F, 0x01, 0x01}},
    {'U', {0x3F, 0x40, 0x40, 0x40, 0x3F}},
    {'V', {0x1F, 0x20, 0x40, 0x20, 0x1F}},
    {'W', {0x3F, 0x40, 0x38, 0x40, 0x3F}},
    {'X', {0x63, 0x14, 0x08, 0x14, 0x63}},
    {'Y', {0x07, 0x08, 0x70, 0x08, 0x07}},
    {'Z', {0x61, 0x51, 0x49, 0x45, 0x43}},
};

static const uint8_t *glyph_for(char c)
{
    static const uint8_t fallback[5] = {0x02, 0x01, 0x51, 0x09, 0x06}; /* '?' */

    if (c >= 'a' && c <= 'z') {
        c = (char)(c - 'a' + 'A');
    }
    for (size_t i = 0; i < sizeof(s_font) / sizeof(s_font[0]); i++) {
        if (s_font[i].ch == c) {
            return s_font[i].col;
        }
    }
    return fallback;
}

static esp_err_t oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd}; /* Co=0, D/C#=0: command stream */
    return i2c_master_transmit(s_dev, buf, sizeof(buf), 100);
}

esp_err_t oled_init(int sda_gpio, int scl_gpio, uint8_t i2c_addr)
{
    i2c_master_bus_config_t bus_cfg = {
        .i2c_port = 0,
        .sda_io_num = sda_gpio,
        .scl_io_num = scl_gpio,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    esp_err_t err = i2c_new_master_bus(&bus_cfg, &s_bus);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c bus init failed: %s", esp_err_to_name(err));
        return err;
    }

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = i2c_addr,
        .scl_speed_hz = 400000,
    };
    err = i2c_master_bus_add_device(s_bus, &dev_cfg, &s_dev);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "oled add_device 0x%02X failed: %s", i2c_addr, esp_err_to_name(err));
        return err;
    }

    static const uint8_t init_seq[] = {
        0xAE,       /* display off */
        0xD5, 0x80, /* clock div */
        0xA8, 0x1F, /* multiplex 1/32 */
        0xD3, 0x00, /* display offset */
        0x40,       /* start line 0 */
        0x8D, 0x14, /* charge pump on */
        0x20, 0x00, /* horizontal addressing */
        0xA1,       /* segment remap */
        0xC8,       /* COM scan dec */
        0xDA, 0x02, /* COM pins for 128x32 */
        0x81, 0x8F, /* contrast */
        0xD9, 0xF1, /* pre-charge */
        0xDB, 0x40, /* VCOMH */
        0xA4, 0xA6, /* resume RAM content, normal (not inverted) */
        0xAF,       /* display on */
    };
    for (size_t i = 0; i < sizeof(init_seq); i++) {
        err = oled_cmd(init_seq[i]);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "oled init cmd 0x%02X failed: %s", init_seq[i], esp_err_to_name(err));
            return err;
        }
    }

    s_ready = true;
    oled_clear();
    oled_flush();
    ESP_LOGI(TAG, "SSD1306 128x32 ready at 0x%02X (sda=%d scl=%d)", i2c_addr, sda_gpio, scl_gpio);
    return ESP_OK;
}

void oled_display_on(void)
{
    if (s_ready) oled_cmd(0xAF);
}

void oled_display_off(void)
{
    if (s_ready) oled_cmd(0xAE);
}

bool oled_ready(void)
{
    return s_ready;
}

void oled_clear(void)
{
    memset(s_fb, 0, sizeof(s_fb));
}

static void fb_px(int x, int y)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    s_fb[y / 8][x] |= (uint8_t)(1u << (y % 8));
}

/* Mixed 16 px CJK + 2x ASCII line (Chinese labels with digits). */
void oled_text_cn(int x, int y, const char *text)
{
    if (text == NULL) return;
    while (*text) {
        const unsigned char c = (unsigned char)*text;
        if (c < 0x80) {
            const uint8_t *g = glyph_for((char)c);
            for (int col = 0; col < 5; col++) {
                for (int r = 0; r < 7; r++) {
                    if (g[col] & (1u << r)) {
                        fb_px(x + 2 * col, y + 2 * r);
                        fb_px(x + 2 * col + 1, y + 2 * r);
                        fb_px(x + 2 * col, y + 2 * r + 1);
                        fb_px(x + 2 * col + 1, y + 2 * r + 1);
                    }
                }
            }
            x += 12;
            text++;
        } else if ((c & 0xF0) == 0xE0 && text[1] && text[2]) {
            char code[4] = {text[0], text[1], text[2], 0};
            for (int i = 0; i < CN_GLYPH_COUNT; i++) {
                if (strcmp(code, CN_GLYPHS[i].code) == 0) {
                    const uint8_t *b = CN_GLYPHS[i].bmp;
                    for (int row = 0; row < 16; row++) {
                        uint8_t hi = b[2 * row], lo = b[2 * row + 1];
                        for (int col = 0; col < 8; col++) {
                            if (hi & (1u << (7 - col))) fb_px(x + col, y + row);
                            if (lo & (1u << (7 - col))) fb_px(x + 8 + col, y + row);
                        }
                    }
                    break;
                }
            }
            x += 16;
            text += 3;
        } else {
            text++;
        }
    }
}

void oled_text(int x, int page, const char *text)
{
    if (page < 0 || page >= OLED_PAGES || text == NULL) {
        return;
    }
    for (const char *p = text; *p != '\0'; p++, x += 6) {
        if (x <= -6 || x >= OLED_WIDTH) {
            continue;
        }
        const uint8_t *g = glyph_for(*p);
        for (int c = 0; c < 5; c++) {
            if (x + c >= 0 && x + c < OLED_WIDTH) {
                s_fb[page][x + c] |= g[c];
            }
        }
    }
}

void oled_bar(int x, int page, int width, int height, float fraction)
{
    int filled;

    if (page < 0 || page >= OLED_PAGES) {
        return;
    }
    if (fraction < 0.0f) {
        fraction = 0.0f;
    }
    if (fraction > 1.0f) {
        fraction = 1.0f;
    }
    if (height > 8) {
        height = 8;
    }
    filled = (int)(fraction * (float)width + 0.5f);
    for (int c = 0; c < filled && x + c < OLED_WIDTH; c++) {
        s_fb[page][x + c] |= (uint8_t)((1u << height) - 1u);
    }
}

/* Blit one page; control byte + 128 data bytes. */
static esp_err_t oled_flush_page(int page)
{
    uint8_t buf[1 + OLED_WIDTH];
    buf[0] = 0x40; /* Co=0, D/C#=1: data stream */
    memcpy(&buf[1], s_fb[page], OLED_WIDTH);
    return i2c_master_transmit(s_dev, buf, sizeof(buf), 100);
}

void oled_flush(void)
{
    if (!s_ready) {
        return;
    }
    /* Window: columns 0..127, pages 0..3. */
    oled_cmd(0x21);
    oled_cmd(0x00);
    oled_cmd(0x7F);
    oled_cmd(0x22);
    oled_cmd(0x00);
    oled_cmd(OLED_PAGES - 1);
    for (int page = 0; page < OLED_PAGES; page++) {
        esp_err_t err = oled_flush_page(page);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "flush page %d failed: %s", page, esp_err_to_name(err));
            return;
        }
    }
}

bool oled_selftest(void)
{
    if (!s_ready) {
        return false;
    }
    oled_clear();
    oled_text(0, 0, "SMARTCOASTER");
    oled_text(0, 1, "FW SKELETON");
    oled_text(0, 2, "ESP32-S3");
    oled_bar(0, 3, OLED_WIDTH, 5, 0.0f);
    oled_flush();
    return true;
}
