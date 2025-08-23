#include "input_mode.h"
#include <zephyr/sys/util.h>
#include <string.h>

/*
 * Input Mode core implementation
 * ------------------------------
 *
 * This file keeps track of the currently selected input mode and provides
 * helper functions for the behaviour drivers.  The number of modes is
 * determined at build time by ``CONFIG_IM_NUM_STATES``.  Mode information can
 * optionally be persisted using Zephyr's settings subsystem so that the last
 * active mode is restored on the next boot.
 */

#define IM_SETTINGS_KEY "im/state"

static uint8_t current_state = CONFIG_IM_DEFAULT_STATE;

#if IS_ENABLED(CONFIG_IM_SETTINGS)
#include <zephyr/settings/settings.h>

/*
 * Settings handler: loads the stored state if present.
 */
static int im_settings_set(const char *name, size_t len, settings_read_cb read_cb,
                           void *cb_arg) {
    if (strncmp(name, "state", len) != 0 || len != sizeof("state") - 1) {
        return -ENOENT;
    }

    if (len != sizeof(uint8_t)) {
        return -EINVAL;
    }

    uint8_t state;
    ssize_t rc = read_cb(cb_arg, &state, sizeof(state));
    if (rc >= 0 && state < CONFIG_IM_NUM_STATES) {
        current_state = state;
    }
    return 0;
}

/* Handler registration structure. */
static struct settings_handler im_conf = {
    .name = "im",
    .h_set = im_settings_set,
};
#endif /* CONFIG_IM_SETTINGS */

uint8_t im_get_state(void) { return current_state; }

int im_set_state(uint8_t state) {
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }

    current_state = state;
#if IS_ENABLED(CONFIG_IM_SETTINGS)
    settings_save_one(IM_SETTINGS_KEY, &current_state, sizeof(current_state));
#endif
    return 0;
}

int im_next_state(void) {
    uint8_t next = (current_state + 1) % CONFIG_IM_NUM_STATES;
    return im_set_state(next);
}

/*
 * Called automatically during start-up.
 */
int input_mode_init(const struct device *device) {
    ARG_UNUSED(device);
#if IS_ENABLED(CONFIG_IM_SETTINGS)
    settings_register(&im_conf);
    settings_load_subtree("im");
#endif
    return 0;
}

SYS_INIT(input_mode_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
