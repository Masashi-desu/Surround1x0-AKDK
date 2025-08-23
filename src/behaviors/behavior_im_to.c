#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/layers.h>
#include "input_mode.h"

/*
 * &im_to <L0 L1 ... LN>
 * ---------------------
 *
 * Switch directly to a layer selected by the current input mode.
 */

static inline uint32_t im_param_at(const struct zmk_behavior_binding *binding, uint8_t idx) {
    const uint32_t *params = &binding->param1;
    return params[idx];
}

static int im_to_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    uint8_t state = im_get_state();
    if (state >= CONFIG_IM_NUM_STATES) {
        return -EINVAL;
    }
    zmk_layer_to(im_param_at(binding, state));
    return ZMK_BEHAVIOR_OPAQUE;
}

static int im_to_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_to_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

static const struct behavior_driver_api behavior_im_to_driver_api = {
    .binding_pressed = im_to_pressed,
    .binding_released = im_to_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_to

#define IM_TO_INST(n)                                                                       \
    DEVICE_DT_INST_DEFINE(n, behavior_im_to_init, NULL, NULL, NULL, APPLICATION,             \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_to_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_TO_INST);
