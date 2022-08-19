#Angelo.Poggi - Angelo.Poggi@opti9tech.com
#(c) Opti9 Tech

from importdevicevlans import NautobotCleanerVlans
from importdeviceroutes import NautobotCleanerRoutes
from import_cid import ImportClientIDs
import os
import logging
from datetime import datetime

def network_sync():
    ######################
    # Network Importer
    ######################
    with open("list_of_devices.txt",'r') as ListOfDevices:
        for device in ListOfDevices:
            device_group = device.split(',')
            try:
                logging.info(f"attempting network importer for {device_group[0]}")
                os.system(f"network-importer apply --update-configs --limit={device_group[0]}")
            except Exception as e:
                logging.warning(f"Could not run network-importer on {device_group[0]}")
                logging.warning(e)
        ######################
        # Cleaner scripts
        ######################
    nbv = NautobotCleanerVlans()
    nbc = ImportClientIDs()
    nbr = NautobotCleanerRoutes()
    with open("list_of_devices.txt", 'r') as ListOfDevices:
        for device in ListOfDevices:
            device_group = device.split(',')
            try:
                logging.info(f"Attempting to import vlans on {device_group[0]}")
                nbv.importdevicevlans(selected_devices=[device_group[0]], group=str(device_group[1]).rstrip())
            except Exception as e:
                logging.warning(f"Failed to import vlans on {device_group[0]}")
                logging.warning(e)
            try:
                logging.info(f"Attempting to import static routes on {device_group[0]}")
                nbr.importdevicestaticroutes(selected_devices=[str(device_group[0]).rstrip()])
            except Exception as e:
                logging.warning(f"Failed to import static routes on {device_group[0]}")
                logging.warning(e)
            ######################
            # wrap it up and link CIDs
            ######################
        try:
            logging.info("Importing CIDs from SCP")
            nbc.linkclientidtoip()
        except Exception as e:
            logging.warning("Failed to import CIDS from SCP")
            logging.warning(e)

if __name__ == "__main__":
    runtime = datetime.now()
    logging.basicConfig(filename=f'MAINRUN/{runtime}.log', level=logging.INFO)
    network_sync()