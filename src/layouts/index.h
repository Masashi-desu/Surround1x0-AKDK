/*
 * MIT License
 *
 * Original code by kot149 (https://github.com/kot149/zmk-layout-shift)
 * See https://opensource.org/licenses/MIT for license details.
 * Forked and modified for Surround1x0-AKDK.
 */

// Layout index - includes all available layout definitions
// Each layout file contains its own conditional compilation directives

#include "layout_jis.h"
#include "layout_dvorak.h"
#include "layout_swap_ctrl_cmd.h"

// Ensure at least one layout is defined
#ifndef LAYOUT_DEFINED
#error "No target layout selected. Please select a layout in Kconfig."
#endif
