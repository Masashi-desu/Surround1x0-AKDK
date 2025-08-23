# CMake configuration for the local ZMK extension: Input Mode
# - Adds include/ to the search path
# - Registers source files for the Input Mode core and behaviors

zephyr_include_directories(${CMAKE_CURRENT_LIST_DIR}/include)

# Core and behaviors (minimal set: im_set, im_next, im_mo)
  target_sources(app PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/src/input_mode.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_set.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_next.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_mo.c
  )
