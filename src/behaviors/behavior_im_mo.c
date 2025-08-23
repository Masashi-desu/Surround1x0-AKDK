// &im_mo <L0 L1 ...>
// -------------------
// Momentarily activate layer Ls while held, where s is current input mode.
// The activated layer is tracked per key position to ensure proper release
// even if the mode changes while the key is held.

#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <zmk/layers.h>
#include <zmk/keymap.h>

#include "input_mode.h"

#ifndef ZMK_KEYMAP_LEN_MAX
#define ZMK_KEYMAP_LEN_MAX 160
#endif

static uint8_t pressed_layer[ZMK_KEYMAP_LEN_MAX];

static int im_mo_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    uint8_t s = im_get_state();
    if (s >= im_num_states()) {
        return -EINVAL;
    }
    uint32_t layer = im_param_at(binding, s);
    zmk_layer_activate(layer);
    pressed_layer[event.position] = layer;
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_mo_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    uint8_t layer = pressed_layer[event.position];
    zmk_layer_deactivate(layer);
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api im_mo_driver_api = {
    .binding_pressed = im_mo_pressed,
    .binding_released = im_mo_released,
};

BEHAVIOR_DT_INST_DEFINE(0, im_mo, NULL, NULL, NULL, APPLICATION,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &im_mo_driver_api);

