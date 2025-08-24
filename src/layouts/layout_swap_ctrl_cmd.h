#ifdef CONFIG_LAYOUT_SHIFT_TARGET_SWAP_CTRL_CMD
#define LAYOUT_DEFINED
// Rotate modifier keys to match Mac/Windows layouts
// Default (layout shift off): Mac layout (Ctrl-Opt-Cmd)
// Layout shift on: rotate Cmd→Ctrl→Alt→Win→Cmd
static const struct keycode_mapping layout_map[] = {
    /* from -> to, optional_modifiers */
    {LEFT_COMMAND,  LEFT_CONTROL, OPTIONAL_ALL},  /* Cmd -> Ctrl */
    {LEFT_CONTROL,  LEFT_ALT,     OPTIONAL_ALL},  /* Ctrl -> Alt */
    {LEFT_ALT,      LEFT_GUI,     OPTIONAL_ALL},  /* Alt -> Win */
    {LEFT_GUI,      LEFT_COMMAND, OPTIONAL_ALL},  /* Win -> Cmd */
    {RIGHT_COMMAND, RIGHT_CONTROL, OPTIONAL_ALL}, /* Cmd -> Ctrl */
    {RIGHT_CONTROL, RIGHT_ALT,    OPTIONAL_ALL},  /* Ctrl -> Alt */
    {RIGHT_ALT,     RIGHT_GUI,    OPTIONAL_ALL},  /* Alt -> Win */
    {RIGHT_GUI,     RIGHT_COMMAND, OPTIONAL_ALL}, /* Win -> Cmd */
};
#endif
