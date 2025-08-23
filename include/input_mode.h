#ifndef INPUT_MODE_H
#define INPUT_MODE_H

#include <zephyr/kernel.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Input Mode API
 * ---------------
 *
 * The input mode feature allows a keymap to behave differently depending on
 * the active host OS (for example macOS or Windows).  The number of modes is
 * configurable at build time through the Kconfig option ``IM_NUM_STATES``.
 *
 * The functions below expose the current mode and helper operations used by
 * the behavior drivers in ``src/behaviors``.  All indices are zero based and
 * must be smaller than ``IM_NUM_STATES``.  When ``CONFIG_IM_SETTINGS`` is
 * enabled the selected mode is saved using Zephyr's settings subsystem so that
 * it persists across reboots.
 */

/**
 * @brief Retrieve the current input mode.
 *
 * @return The current mode number, ranging from ``0`` to
 *         ``CONFIG_IM_NUM_STATES - 1``.
 */
uint8_t im_get_state(void);

/**
 * @brief Set the current input mode.
 *
 * The new mode is persisted if ``CONFIG_IM_SETTINGS`` is enabled.
 *
 * @param state The mode to activate.
 *
 * @retval 0       on success.
 * @retval -EINVAL if ``state`` is out of range.
 */
int im_set_state(uint8_t state);

/**
 * @brief Advance to the next input mode.
 *
 * The sequence wraps around once the last mode is reached.
 *
 * @retval 0       on success.
 * @retval -EINVAL if the configuration is invalid.
 */
int im_next_state(void);

/**
 * @brief Return the number of configured input modes.
 */
static inline uint8_t im_num_states(void) {
    return CONFIG_IM_NUM_STATES;
}

/**
 * @brief Initialise the input mode subsystem.
 *
 * Called automatically during system start-up.
 */
int input_mode_init(const struct device *device);

#ifdef __cplusplus
}
#endif

#endif /* INPUT_MODE_H */
