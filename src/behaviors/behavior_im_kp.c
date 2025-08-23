#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <string.h>
#include "input_mode.h"

/*
 * &im_kp <KC0 KC1 ... KCN>
 * ------------------------
 *
 * Emit a keycode depending on the current input mode.  The keycode that was
 * sent on press is tracked per key position so that the correct one is released
 * even if the mode changes while the key is held.
 */

#ifndef ZMK_KEYMAP_LEN_MAX
#define ZMK_KEYMAP_LEN_MAX 160
#endif

static uint32_t pressed_keycode[ZMK_KEYMAP_LEN_MAX];

static inline uint32_t im_param_at(const struct zmk_behavior_binding *binding, uint8_t idx) {
    const uint32_t *params = &binding->param1;
    return params[idx];
}

static int im_kp_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    uint8_t state = im_get_state();
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }
    uint32_t kc = im_param_at(binding, state);
    pressed_keycode[event.position] = kc;
    zmk_hid_implicit_press(kc);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_kp_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    uint32_t kc = pressed_keycode[event.position];
    pressed_keycode[event.position] = 0;
    zmk_hid_implicit_release(kc);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_kp_init(const struct device *dev) {
    ARG_UNUSED(dev);
    memset(pressed_keycode, 0, sizeof(pressed_keycode));
    return 0;
}

static const struct behavior_driver_api behavior_im_kp_driver_api = {
    .binding_pressed = im_kp_pressed,
    .binding_released = im_kp_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_kp

#define IM_KP_INST(n)                                                                       \
    DEVICE_DT_INST_DEFINE(n, behavior_im_kp_init, NULL, NULL, NULL, APPLICATION,             \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_kp_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_KP_INST);
