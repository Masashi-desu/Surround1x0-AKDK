#ifdef CONFIG_LAYOUT_SHIFT_TARGET_SWAP_CTRL_CMD
#define LAYOUT_DEFINED
// Swap Ctrl and Cmd
static const struct keycode_mapping layout_map[] = {
    /* from -> to, optional_modifiers */
    {LEFT_CONTROL,  LEFT_COMMAND,  OPTIONAL_ALL},
    {LEFT_COMMAND,  LEFT_CONTROL,  OPTIONAL_ALL},
    {RIGHT_CONTROL, RIGHT_COMMAND, OPTIONAL_ALL},
    {RIGHT_COMMAND, RIGHT_CONTROL, OPTIONAL_ALL},
};
#endif
