#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include "input_mode.h"

/*
 * &im_set <state>
 * ----------------
 *
 * Simple helper used by the keymap to force the input mode to the value
 * specified as its single argument.
 */

static inline uint32_t im_param_at(const struct zmk_behavior_binding *binding, uint8_t idx) {
    const uint32_t *params = &binding->param1;
    return params[idx];
}

static int im_set_pressed(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    return im_set_state(im_param_at(binding, 0)) < 0 ? -EINVAL : ZMK_BEHAVIOR_OPAQUE;
}

static int im_set_released(struct zmk_behavior_binding *binding,
                           struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_set_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

static const struct behavior_driver_api behavior_im_set_driver_api = {
    .binding_pressed = im_set_pressed,
    .binding_released = im_set_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_set

#define IM_SET_INST(n)                                                                      \
    DEVICE_DT_INST_DEFINE(n, behavior_im_set_init, NULL, NULL, NULL, APPLICATION,            \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_set_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_SET_INST);
