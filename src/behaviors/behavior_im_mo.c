#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/keymap.h>
#include <zmk/layers.h>
#include <string.h>
#include "input_mode.h"

/*
 * &im_mo <L0 L1 ... LN>
 * ---------------------
 *
 * Momentary layer switch that selects the layer to activate based on the
 * current input mode.  The layer activated on press is remembered per key
 * position so that it can be deactivated correctly even if the mode changes
 * while the key is held.
 */

#ifndef ZMK_KEYMAP_LEN_MAX
#define ZMK_KEYMAP_LEN_MAX 160
#endif

static uint8_t pressed_layer[ZMK_KEYMAP_LEN_MAX];

static inline uint32_t im_param_at(const struct zmk_behavior_binding *binding, uint8_t idx) {
    const uint32_t *params = &binding->param1;
    return params[idx];
}

static int im_mo_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    uint8_t state = im_get_state();
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }
    uint8_t layer = im_param_at(binding, state);
    pressed_layer[event.position] = layer;
    zmk_layer_activate(layer);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_mo_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    uint8_t layer = pressed_layer[event.position];
    pressed_layer[event.position] = 0;
    zmk_layer_deactivate(layer);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_mo_init(const struct device *dev) {
    ARG_UNUSED(dev);
    memset(pressed_layer, 0, sizeof(pressed_layer));
    return 0;
}

static const struct behavior_driver_api behavior_im_mo_driver_api = {
    .binding_pressed = im_mo_pressed,
    .binding_released = im_mo_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_mo

#define IM_MO_INST(n)                                                                       \
    DEVICE_DT_INST_DEFINE(n, behavior_im_mo_init, NULL, NULL, NULL, APPLICATION,             \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_mo_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_MO_INST);
