#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include "input_mode.h"

/*
 * &im_next
 * --------
 *
 * Cycle to the next input mode.  The release event does nothing; the function
 * simply returns ``ZMK_BEHAVIOR_OPAQUE`` so that no further processing takes
 * place.
 */

static int im_next_pressed(struct zmk_behavior_binding *binding,
                           struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return im_next_state() < 0 ? -EINVAL : ZMK_BEHAVIOR_OPAQUE;
}

static int im_next_released(struct zmk_behavior_binding *binding,
                            struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_im_next_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

static const struct behavior_driver_api behavior_im_next_driver_api = {
    .binding_pressed = im_next_pressed,
    .binding_released = im_next_released,
};

#define DT_DRV_COMPAT zmk_behavior_im_next

#define IM_NEXT_INST(n)                                                                     \
    DEVICE_DT_INST_DEFINE(n, behavior_im_next_init, NULL, NULL, NULL, APPLICATION,          \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_im_next_driver_api);

DT_INST_FOREACH_STATUS_OKAY(IM_NEXT_INST);
