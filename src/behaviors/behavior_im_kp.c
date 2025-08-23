// &im_kp <KC0 KC1 ...>
// --------------------
// Emit a keycode depending on current input mode. The keycode pressed is
// remembered per key position to ensure proper release even if the mode
// changes while the key is held.

#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>

#include "input_mode.h"

#ifndef ZMK_KEYMAP_LEN_MAX
#define ZMK_KEYMAP_LEN_MAX 160
#endif

static uint32_t pressed_kc[ZMK_KEYMAP_LEN_MAX];

static int im_kp_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    uint8_t s = im_get_state();
    if (s >= im_num_states()) {
        return -EINVAL;
    }
    uint32_t kc = im_param_at(binding, s);
    pressed_kc[event.position] = kc;
    zmk_hid_keyboard_press(kc);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_kp_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    zmk_hid_keyboard_release(pressed_kc[event.position]);
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api im_kp_driver_api = {
    .binding_pressed = im_kp_pressed,
    .binding_released = im_kp_released,
};

BEHAVIOR_DT_INST_DEFINE(0, im_kp, NULL, NULL, NULL, APPLICATION,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &im_kp_driver_api);

