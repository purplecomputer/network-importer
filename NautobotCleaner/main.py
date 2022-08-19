#Angelo.Poggi - Angelo.Poggi@opti9tech.com
#(c) Opti9 Tech

from importdevicevlans import NautobotCleanerVlans
from importdeviceroutes import NautobotCleanerRoutes
from netmonimporter import NautobotCleanerNetmonImport
import pprint

if __name__ == "__main__":
    nbn = NautobotCleanerNetmonImport()
    nbv = NautobotCleanerVlans()
    nbr = NautobotCleanerRoutes()
    #Build device inventory
    # nbn.add_device_to_nautobot(deviceGroup=[
    #     'Webair_Edge'
    # ])
    #run network Importer
    #IMPORTING VLANS
    # nbv.importdevicevlans(selected_devices=[
    #     'es0.chi.webair.net',
    #     'es1.chi.webair.net',
    # ],
    #     group='chi-l3')
    #IMPORTING STATIC ROUTES
    # nbr.importdevicestaticroutes(selected_devices=[
    #     'es0.chi.webair.net',
    #     'es1.chi.webair.net',

    # ])
    # nbv.importdevicevlans(selected_devices=[
    #     'es0.sg.webair.net',
    #     'es1.sg.webair.net',
    # ],
    #     group='sg-l3')
    #IMPORTING STATIC ROUTES
    # nbr.importdevicestaticroutes(selected_devices=[
    #     'es0.sg.webair.net',
    #     'es1.sg.webair.net',
    # ])
    # nbv.importdevicevlans(selected_devices=[
    #     'es0.lon.webair.net',
    #     'es1.lon.webair.net',
    # ],
    #     group='lon-l3')
    #IMPORTING STATIC ROUTES
    # nbr.importdevicestaticroutes(selected_devices=[
    #     'es0.lon.webair.net',
    #     'es1.lon.webair.net',
    # ])

