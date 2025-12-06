# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico_w CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(picow_tcpip_client C CXX ASM)

set(TEST_TCP_SERVER_IP "192.168.1.9") # Change this to your TCP server IP

set(WIFI_SSID "Airtel_ix1")
set(WIFI_PASSWORD "Manu@A504")

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable. Default name is the project name, version 0.1

if (NOT TEST_TCP_SERVER_IP)
    message("Skipping tcp_client example as TEST_TCP_SERVER_IP is not defined")
else()
    add_executable(picow_tcpip_client_background
            picow_tcp_client.c
            )
    target_compile_definitions(picow_tcpip_client_background PRIVATE
            WIFI_SSID=\"${WIFI_SSID}\"
            WIFI_PASSWORD=\"${WIFI_PASSWORD}\"
            TEST_TCP_SERVER_IP=\"${TEST_TCP_SERVER_IP}\"
            )
    target_include_directories(picow_tcpip_client_background PRIVATE
            ${CMAKE_CURRENT_LIST_DIR}
            ${CMAKE_CURRENT_LIST_DIR}/.. # for our common lwipopts
            )
    target_link_libraries(picow_tcpip_client_background
            pico_cyw43_arch_lwip_threadsafe_background
            pico_stdlib
            )

    pico_add_extra_outputs(picow_tcpip_client_background)

    add_executable(picow_tcpip_client_poll
            picow_tcp_client.c
            )
    target_compile_definitions(picow_tcpip_client_poll PRIVATE
            WIFI_SSID=\"${WIFI_SSID}\"
            WIFI_PASSWORD=\"${WIFI_PASSWORD}\"
            TEST_TCP_SERVER_IP=\"${TEST_TCP_SERVER_IP}\"
            )
    target_include_directories(picow_tcpip_client_poll PRIVATE
            ${CMAKE_CURRENT_LIST_DIR}
            ${CMAKE_CURRENT_LIST_DIR}/.. # for our common lwipopts
            )
    target_link_libraries(picow_tcpip_client_poll
            pico_cyw43_arch_lwip_poll
            pico_stdlib
            )
    pico_add_extra_outputs(picow_tcpip_client_poll)
endif()
