# CMake configuration for the local ZMK extension: Input Mode
# - Adds include/ to the search path
# - Registers source files for the Input Mode core and behaviors

zephyr_include_directories(${CMAKE_CURRENT_LIST_DIR}/include)

# Core module and all Input Mode aware behaviors
  target_sources(app PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/src/input_mode.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_set.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_next.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_mo.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_to.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_tog.c
    ${CMAKE_CURRENT_LIST_DIR}/src/behaviors/behavior_im_kp.c
  )
