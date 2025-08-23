// &im_tog <L0 L1 ...>
// -------------------
// Toggle layer Ls depending on current input mode.

#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <zmk/layers.h>

#include "input_mode.h"

static int im_tog_pressed(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    uint8_t s = im_get_state();
    if (s >= im_num_states()) {
        return -EINVAL;
    }
    zmk_layer_toggle(im_param_at(binding, s));
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api im_tog_driver_api = {
    .binding_pressed = im_tog_pressed,
};

BEHAVIOR_DT_INST_DEFINE(0, im_tog, NULL, NULL, NULL, APPLICATION,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &im_tog_driver_api);

