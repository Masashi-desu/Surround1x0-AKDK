// &im_set <state>
// -----------------
// Set the current input mode to the specified state.

#include <zephyr/kernel.h>
#include <drivers/behavior.h>

#include "input_mode.h"

static int im_set_pressed(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    return im_set_state(binding->param1);
}

static const struct behavior_driver_api im_set_driver_api = {
    .binding_pressed = im_set_pressed,
};

BEHAVIOR_DT_INST_DEFINE(0, im_set, NULL, NULL, NULL, APPLICATION,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &im_set_driver_api);

