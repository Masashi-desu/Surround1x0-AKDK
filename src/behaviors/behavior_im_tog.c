#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/layers.h>
#include "input_mode.h"

/*
 * &im_tog <L0 L1 ... LN>
 * ----------------------
 *
 * Toggle the layer selected by the current input mode.
 */

static inline uint32_t im_param_at(const struct zmk_behavior_binding *binding, uint8_t idx) {
    const uint32_t *params = &binding->param1;
    return params[idx];
}

static int im_tog_pressed(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    uint8_t state = im_get_state();
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }
    zmk_layer_toggle(im_param_at(binding, state));
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_tog_released(struct zmk_behavior_binding *binding,
                           struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_tog_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

static const struct behavior_driver_api behavior_im_tog_driver_api = {
    .binding_pressed = im_tog_pressed,
    .binding_released = im_tog_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_tog

#define IM_TOG_INST(n)                                                                      \
    DEVICE_DT_INST_DEFINE(n, behavior_im_tog_init, NULL, NULL, NULL, APPLICATION,            \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_tog_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_TOG_INST);
