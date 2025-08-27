/*
 * MIT License
 *
 * Original code by kot149 (https://github.com/kot149/zmk-layout-shift)
 * See https://opensource.org/licenses/MIT for license details.
 * Forked and modified for Surround1x0-AKDK.
 */

#define DT_DRV_COMPAT zmk_behavior_layout_env_to

#include <drivers/behavior.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <zmk/behavior.h>
#include <zmk/event_manager.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

extern void zmk_layout_env_set_active(bool active);

struct behavior_layout_env_to_config {};
struct behavior_layout_env_to_data {};

static int on_layout_env_to_binding_pressed(struct zmk_behavior_binding *binding,
                                            struct zmk_behavior_binding_event event) {
    const bool state = (bool)binding->param1;
    zmk_layout_env_set_active(state);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_layout_env_to_binding_released(struct zmk_behavior_binding *binding,
                                             struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_layout_env_to_driver_api = {
    .binding_pressed = on_layout_env_to_binding_pressed,
    .binding_released = on_layout_env_to_binding_released,
};

static int layout_env_to_init(const struct device *dev) { return 0; }

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)
#define LAYOUT_ENV_TO_INST(n)                                                    \
    static struct behavior_layout_env_to_data behavior_layout_env_to_data_##n = {}; \
    BEHAVIOR_DT_INST_DEFINE(n, layout_env_to_init, NULL,                         \
                            &behavior_layout_env_to_data_##n, NULL,             \
                            POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,   \
                            &behavior_layout_env_to_driver_api);

DT_INST_FOREACH_STATUS_OKAY(LAYOUT_ENV_TO_INST)
#endif

