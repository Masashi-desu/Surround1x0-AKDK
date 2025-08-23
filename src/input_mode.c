// Input Mode core implementation
// -------------------------------
// Maintains a device-wide input mode state (0..N-1) with optional persistence
// via Zephyr settings. Future split support can hook synchronization where
// indicated below.

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/settings/settings.h>
#include <string.h>

#include "input_mode.h"

static uint8_t current_state = CONFIG_IM_DEFAULT_STATE;

static int save_state(void) {
    if (!IS_ENABLED(CONFIG_IM_SETTINGS)) {
        return 0;
    }
    return settings_save_one("im/state", &current_state, sizeof(current_state));
}

uint8_t im_get_state(void) {
    return current_state;
}

int im_set_state(uint8_t state) {
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }
    current_state = state;
    // TODO: future split sync hook goes here
    return save_state();
}

int im_next_state(void) {
    uint8_t next = current_state + 1;
    if (next >= CONFIG_IM_NUM_STATES) {
        next = 0;
    }
    return im_set_state(next);
}

static int im_settings_set(const char *name, size_t len,
                           settings_read_cb read_cb, void *cb_arg) {
    if (!strncmp(name, "state", len)) {
        uint8_t state;
        if (read_cb(cb_arg, &state, sizeof(state)) == sizeof(state)) {
            if (state < CONFIG_IM_NUM_STATES) {
                current_state = state;
            }
        }
        return 0;
    }
    return -ENOENT;
}

static struct settings_handler im_conf = {
    .name = "im",
    .h_set = im_settings_set,
};

static int im_init(const struct device *dev) {
    ARG_UNUSED(dev);
    if (IS_ENABLED(CONFIG_IM_SETTINGS)) {
        settings_subsys_init();
        settings_register(&im_conf);
        settings_load_subtree("im");
    }
    return 0;
}

SYS_INIT(im_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

