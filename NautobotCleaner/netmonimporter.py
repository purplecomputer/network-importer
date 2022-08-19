#2022 - Opti9Technologies
#By: Angelo Poggi angelo.poggi@opti9tech.com

from config import device_platform_connection,nautobot_token,nautobot_url,device_password,device_username,netmon_url,netmon_token
import requests
from requests.exceptions import HTTPError
import sys
import napalm
import pynautobot

class NautobotCleanerNetmonImport:
    def __init__(self):
        self.pynb = pynautobot.api(nautobot_url, token=nautobot_token)

    def _netmon_connect(self,endpoint):
        try:
            connect = requests.get(f'{netmon_url}/api/v0/{endpoint}',
                                   headers={'X-Auth-Token': netmon_token}).json()
        except HTTPError as http_error:
            raise (f"Issue connecting to netmon: {http_error}")
        else:
            return connect

    def _connecttodevice(self, device):
        '''Connects to the devices and returns a dict containing vlans using VLANS'''
        # query Device
        device = self.pynb.dcim.devices.get(name=str(device))
        device_os = device_platform_connection[str(device.platform.name)]['os']
        driver = napalm.get_network_driver(device_os)
        device_init = driver(
            hostname=str(device.name),
            username=str(device_username),
            password=str(device_password),
            optional_args={
                'secret': str(device_password)
            }
        )
        return device_init

    def _getinterfaceips(self,device,ip):
        device = self._connecttodevice(device)
        device.open()
        interface_list = device.get_interfaces_ip()
        for k, v in interface_list.items():
            for i, j in v['ipv4'].items():
                if i == ip:
                    return k

    def add_device_to_nautobot(self,deviceGroup=[]):
        '''Function to add missing devices in Nautobot based on the device group given
        I.E OPti9NetmonTools.add_device_to_nautobot(deviceGroup=['core']
        '''
        if len(deviceGroup) == 0:
            print("You did not pass a group of devices")
            sys.exit(1)
        else:
            group = deviceGroup
        for groups in group:
            try:
                api = self._netmon_connect(f'devicegroups/{groups}')
            except Exception as e:
                raise(f"Following error from Netmon: {e}")
            for devices in api['devices']:
                #iterate through the items and repace any None Values with a string
                router = self._netmon_connect(f"devices/{devices['device_id']}")
                for device in router['devices']:
                    # pull manufacture from the icon
                    manufacturer = device['icon'].split('/')
                    manufacturer = manufacturer[2].split('.')
                    location = device['hostname'].split('.')
                    groupSplit = groups.split('_')
                    # we dont have AMSL in netbox, just AMS
                    if location[1].upper() == 'AMSNL':
                        location[1] = 'AMS'
                    elif location[1].upper() == 'DMVPN':
                        location.pop(1)
                    if device['status'] == 1:
                        deviceStatus = 'active'
                    else:
                        deviceStatus = 'offline'
                    if groups.startswith('SAN') or groups.startswith('Access_switches'):
                        group = groupSplit[0]
                    else:
                        group = groupSplit[1]
                    #Pull NoneType values and replace them
                    for k, v in device.items():
                        if v is None:
                            device.update({k: "NotAvailable"})
                    else:
                        print(f"adding in {device['hostname']}")
                        deviceManufacturer = self.pynb.dcim.manufacturers.get(slug=manufacturer[0].lower().replace(" ", ""))
                        if deviceManufacturer is None:
                            deviceManufacturer = self.pynb.dcim.manufacturers.create({
                                'name': manufacturer[0].capitalize(),
                                'slug': manufacturer[0].lower().replace(" ", "")
                            })

                        #find the "device type or create it
                        deviceType = self.pynb.dcim.device_types.get(slug=device['hardware'].lower().replace(" ", ""))
                        if deviceType is None:
                            deviceType = self.pynb.dcim.device_types.create({
                                'manufacturer': deviceManufacturer.id,
                                'model': device['hardware'].upper(),
                                'slug' : device['hardware'].lower().replace(" ", "")
                            })

                        #need to find deviceRole; if not create it!
                        deviceRole = self.pynb.dcim.device_roles.get(slug=group.lower().replace(" ", ""))
                        if deviceRole is None:
                            deviceRole = self.pynb.dcim.device_roles.create({
                                'name': group.capitalize(),
                                'slug': group.lower().replace(" ", ""),
                                'vm_role': False
                            })

                        #need to find device platform
                        '''should format to something like cisco_ios or cisco_nxos'''
                        devicePlatform = self.pynb.dcim.platforms.get(slug=f"""{manufacturer[0].lower().replace(" ", "")}_{device['os'].lower().replace(" ", "")}""")
                        if devicePlatform is None:
                            devicePlatform = self.pynb.dcim.platforms.create({
                                'name': f"""{manufacturer[0].lower().replace(" ", "")}_{device['os'].lower().replace(" ", "")}""",
                                'slug': f"""{manufacturer[0].lower().replace(" ", "")}_{device['os'].lower().replace(" ", "")}""",
                                'manufacturer' : deviceManufacturer.id,
                                # Napalm just expects ios, nxos_ssh etc
                                '''should query the dict in config file'''
                                'napalm_driver' : str(device_platform_connection[f'''cisco_{device['os']}'''])
                            })

                        #need to find location
                        deviceLocation = self.pynb.dcim.sites.get(slug=location[1].lower().replace(" ", ""))
                        if deviceLocation is None:
                            deviceLocation = self.pynb.dcim.sites.create({
                                'name': location[1].upper(),
                                'status': "active",
                                'slug': location[1].lower().replace(" ", "")
                            })
                        # if device['os'] in telnetList:
                        #     netopsMgmtPort = 23
                        # elif device['os'] in sshList:
                        #     netopsMgmtPort = 22
                        # else:
                        #     netopsMgmtPort = 22
                        # try:
                        #     ipQuery = self.pynb.ipam.ip_addresses.get(address=str(device['ip']))
                        #     if ipQuery is None:
                        #         ipQuery = self.pynb.ipam.ip_addresses.create({
                        #             'address':              str(device['ip']),
                        #             'status' : "active"
                        #         })
                        # except Exception as e:
                        #     print(f"Error adding in {device['ip']} due to this error {e}")
                        try:
                            deviceObj = self.pynb.dcim.devices.get(name=device['hostname'])
                            if deviceObj is None:
                            #Create the device if it is not in nautobot
                                deviceObj = self.pynb.dcim.devices.create(
                                    {
                                     'name': device['hostname'],
                                     'display_name': device['hostname'],
                                     'device_type': deviceType.id, #int
                                     'device_role': deviceRole.id, #int
                                     'platform': devicePlatform.id, #int
                                     'site': deviceLocation.id, #int
                                     'status' : deviceStatus,
                                     'serial': device['serial'],
                                     }
                                )
                            else:
                                #Update the device if it already is in nautobot
                                deviceObjUpdate = {
                                     'name':          device['hostname'],
                                     'display_name':  device['hostname'],
                                     'device_type':   deviceType.id,  # int
                                     'device_role':   deviceRole.id,  # int
                                     'platform':      devicePlatform.id,  # int
                                     'site':          deviceLocation.id,  # int
                                     'status':        deviceStatus,
                                     'serial':        device['serial'],
                                     }
                                deviceObj.update(deviceObjUpdate)
                        except Exception as e:
                            print(e)
                        #create the psudo int for management
                        try:
                            '''Get interface IPs and match resolved IP of FQDN to an interface and use that to link it to device'''
                            mgmt_interface = self._getinterfaceips(device=deviceObj, ip=str(device['ip']))
                            if mgmt_interface is None:
                                '''If for some reason cant match to interface, make generic interface object'''
                                mgmt_interface = 'Pseudo-Interface'
                            mgmtInt_obj = self.pynb.dcim.interfaces.get(name=mgmt_interface, device_id=deviceObj.id)
                            if mgmtInt_obj is None:
                                mgmtInt_obj = self.pynb.dcim.interfaces.create({
                                    'device' : deviceObj.id,
                                    'name' : mgmt_interface,
                                    'type' : 'other',
                                })
                        except Exception as e:
                            print(f'issue loggig into {deviceObj.name} - partial information was imported')
                            continue
                        #link IP to mgmt psudo int and set is as primary
                        try:
                            ipQuery = self.pynb.ipam.ip_addresses.get(address=str(device['ip']), interface_id=mgmtInt_obj.id, device_id=deviceObj.id)
                            if ipQuery is None:
                                ipQuery = self.pynb.ipam.ip_addresses.create({
                                    'address': str(device['ip']),
                                    'assigned_object_type' : 'dcim.interface',
                                    'assigned_object_id' : mgmtInt_obj.id,
                                    'status': 'active'
                                })
                                deviceObj.update({
                                    'primary_ip4': ipQuery.id
                                })
                            else:
                                ipUpdate = {
                                    'assigned_object_type' : 'dcim.interface',
                                    'assigned_object_id' : mgmtInt_obj.id
                                }
                                ipQuery.update(ipUpdate)
                                deviceObj.update({
                                    'primary_ip4': ipQuery.id
                                })
                        except:
                            print('issue')