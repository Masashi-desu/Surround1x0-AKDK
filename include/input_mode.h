#ifndef INPUT_MODE_H
#define INPUT_MODE_H

/*
 * Input Mode core API
 * --------------------
 *  - im_get_state():   Get the current input mode (0..N-1)
 *  - im_set_state(s):  Set the current input mode to s
 *  - im_next_state():  Advance to the next input mode
 *  - im_num_states():  Compile-time number of modes
 *
 * Behaviors pass multiple parameters; im_param_at() is a small helper to
 * fetch the Nth parameter from a behavior binding.
 */

#include <stdint.h>
#include <zmk/behavior.h>

uint8_t im_get_state(void);
int im_set_state(uint8_t state);
int im_next_state(void);
static inline uint8_t im_num_states(void) { return CONFIG_IM_NUM_STATES; }

static inline uint32_t im_param_at(const struct zmk_behavior_binding *b, uint8_t idx) {
    const uint32_t *params = &b->param1;
    return params[idx];
}

#endif /* INPUT_MODE_H */
