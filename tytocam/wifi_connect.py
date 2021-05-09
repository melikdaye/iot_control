import time
import pynmcli

from subprocess import check_call, CalledProcessError, PIPE


def is_reachable(inter, i, add):
    command = ["ping", "-I", inter, "-c", i, add]
    try:
        check_call(command, stdout=PIPE)
        return True
    except CalledProcessError as e:
        print(e)
        return False


def checkWifiConnectivity():
    available_wifis = search_wifi()
    inuseDevice = [x for x in available_wifis['Devices'] if x["IN-USE"] == True]
    if len(inuseDevice) > 0:
        is_reachable("wlan0", "4", "www.google.com")
    else:
        return False


def check_registered(cells, ssid):
    for i in cells:
        if i["NAME"] == ssid:
            return True
    return False


def search_wifi():
    avail_wifi = {}
    avail_wifi.setdefault("Devices", [])
    # avail_wifi.setdefault("Registered", [])
    pynmcli.NetworkManager().Device().wifi('rescan').execute()
    cells = pynmcli.get_data(pynmcli.NetworkManager.Device().wifi('list').execute())
    registered_cells = pynmcli.get_data(pynmcli.NetworkManager.Connection().show().execute())

    for cell in cells:

        filtered_dict = dict(
            (key, value) for key, value in cell.items() if key in ("IN-USE", "SSID", "SIGNAL", "SECURITY"))
        if filtered_dict["IN-USE"] == '*':
            filtered_dict["IN-USE"] = True
        else:
            filtered_dict["IN-USE"] = False
        filtered_dict["SIGNAL"] = filtered_dict["SIGNAL"] + "/100"
        if filtered_dict["SECURITY"] == '':
            filtered_dict["SECURITY"] = False
        else:
            filtered_dict["SECURITY"] = True
        if check_registered(registered_cells, filtered_dict["SSID"]):
            filtered_dict["REGISTERED"] = True

        else:
            filtered_dict["REGISTERED"] = False

        avail_wifi["Devices"].append(filtered_dict)

    print(avail_wifi)
    return avail_wifi


def wifi_connect(ssid, password):
    pynmcli.NetworkManager().Device().wifi('rescan').execute()
    wifi_list = pynmcli.get_data(pynmcli.NetworkManager.Device().wifi('list').execute())
    registered_cells = pynmcli.get_data(pynmcli.NetworkManager.Connection().show().execute())
    selected_wifi = None
    registered = False
    for wifi in wifi_list:
        if wifi["SSID"] == ssid:
            selected_wifi = wifi
            registered = check_registered(registered_cells, wifi["SSID"])
            break
    if selected_wifi is not None:
        if registered:
            pynmcli.NetworkManager.Connection().up('"{:s}"'.format(ssid)).execute()
        else:
            pynmcli.NetworkManager.Device().wifi().connect('"{:s}" password "{:s}"'.format(ssid, password)).execute()
        time.sleep(20)
