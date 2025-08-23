// &im_next
// --------
// Cycle to the next input mode.

#include <zephyr/kernel.h>
#include <drivers/behavior.h>

#include "input_mode.h"

static int im_next_pressed(struct zmk_behavior_binding *binding,
                           struct zmk_behavior_binding_event event) {
    return im_next_state();
}

static const struct behavior_driver_api im_next_driver_api = {
    .binding_pressed = im_next_pressed,
};

BEHAVIOR_DT_INST_DEFINE(0, im_next, NULL, NULL, NULL, APPLICATION,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &im_next_driver_api);

