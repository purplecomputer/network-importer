#Angelo.Poggi

from config import nb_url, nb_token, device_platform_connection,device_username,device_password
import pynautobot
import napalm
import gevent
import gevent.pool
import ipaddress
from netmiko import ConnectHandler
import logging
from datetime import datetime

class NautobotCleanerVlans:
    def __init__(self):
        '''creates a connection to nautobot and device during instantiation of class'''
        self.pynb = pynautobot.api(nb_url, token=nb_token)
        self.runTime = datetime.now()
        #logging.basicConfig(filename=f'synclogs/VLANS/{self.runTime}.log',level=logging.INFO)

    def _connecttodevice(self, device):
        '''Connects to the devices and returns a dict containing vlans using VLANS'''
        # query Device
        device = self.pynb.dcim.devices.get(name=str(device))
        device_os = device_platform_connection[str(device.platform)]['os']
        driver = napalm.get_network_driver(device_os)
        device_init = driver(
            hostname=str(device),
            username=str(device_username),
            password=str(device_password),
            optional_args={
                'secret': str(device_password)
            }
        )
        return device_init

    def _parseportchannelvlans(self, device, group):
        '''Uses netmiko to pull vlans from portgroups since napalm is unable to'''
        device = self.pynb.dcim.devices.get(name=str(device))
        #device_os = device_platform_connection[str(device.platform)]['os']
        net_connect = ConnectHandler(
            device_type='cisco_ios',
            host=str(device),
            username=str(device_username),
            password=str(device_password),
            secret=str(device_password)
        )
        net_connect.find_prompt()
        output = net_connect.send_command('show interface', use_textfsm=True)
        vlan_group = self.pynb.ipam.vlan_groups.get(name=group)
        if vlan_group is None:
            vlan_group = self.pynb.ipam.vlan_groups.create(
                name=group,
                slug=group.lower(),
                site=device.site.id
            )
        tenant_group = self.pynb.tenancy.tenants.get(name=str(group).lower())
        if tenant_group is None:
            tenant_group = self.pynb.tenancy.tenants.create(
                name=str(group).lower()
            )
            '''Link the freshly created tenant group to the device'''
            device.update({'tenant': tenant_group.id})
        else:
            device.update({'tenant': tenant_group.id})
        for data in output:
            if data['encapsulation'] == '802.1Q Virtual LAN':
                vlan_obj = self.pynb.ipam.vlans.get(name=str(data['vlan_id']),
                                                    vid=str(data['vlan_id']),
                                                    group_id=vlan_group.id)
                if vlan_obj is None:
                    vlan_obj = self.pynb.ipam.vlans.create(
                        vid=int(data['vlan_id']),
                        name=str(data['vlan_id']),
                        group=str(vlan_group.id),
                        site=device.site.id,
                        status='active',
                        description=str(data['description']),
                        tenant=tenant_group.id
                    )
                else:
                    vlan_obj.update({
                        'name': str(data['vlan_id']),
                        'vid': int(data['vlan_id']),
                        'group':str(vlan_group.id),
                        'site':device.site.id,
                        'status': 'active',
                        'description':str(data['description']),
                        'tenant':tenant_group.id
                    })
                interface_obj = self.pynb.dcim.interfaces.get(name=data['interface'], device_id=device.id)
                if interface_obj is None:
                    logging.warning(f'''interface {data['interface']} not found on {device}''')
                    continue
                interface_obj.update({
                    'mode' : 'tagged',
                    'tagged_vlans' : [vlan_obj.id]
                })
                self._linkPrefixtoVlan(interface_id=interface_obj.id, vlan_nb_id=vlan_obj.id)


    def _getipv6(self,device):
        '''gets a device name, data is passed in when ran from parent function'''
        device_obj = self.pynb.dcim.devices.get(name=device)
        device = self._connecttodevice(device)
        device.open()
        output = device.get_interfaces_ip()
        for k,v in output.items():
            if 'ipv6' in v:
                for ips,netmask in v['ipv6'].items():
                    interface_obj = self.pynb.dcim.interfaces.get(name=str(k), device_id=device_obj.id)
                    if interface_obj is None:
                        logging.warning(f'{k} not found on {device_obj.name}')
                        continue
                    #check to see if address i link local/private
                    ip_validation = ipaddress.IPv6Network(ips)
                    if ip_validation.is_private is True:
                        logging.info(f"{ips} appears to be a private address - SKIPPING!")
                        continue
                    ip_obj = self.pynb.ipam.ip_addresses.get(address=str(ips))
                    if ip_obj is None:
                        address = f"{ips}/{netmask['prefix_length']}"
                        logging.info(address)
                        self.pynb.ipam.ip_addresses.create({
                            'address': address,
                            'site':device_obj.site.id,
                            'status':'active',
                            'tenant':device_obj.tenant.id,
                            'assigned_object_type': 'dcim.interface',
                            'assigned_object_id': interface_obj.id
                        })
                    else:
                        ip_obj.update({
                            'site' : device_obj.site,
                            'status' : 'active',
                            'tenant' : device_obj.tenant.id,
                            'assigned_object_type': 'dcim.interface',
                            'assigned_object_id' : interface_obj.id

                        })

    def _getvlans(self,device):
        '''Queries device info and grabs VLAN'''
        #give me that data
        device = self._connecttodevice(device)
        device.open()
        return device.get_vlans()

    def _getinterfaces(self, device):
        device = self._connecttodevice(device)
        device.open()
        return device.get_interfaces()

    def _formatnapalmvlandict(self, group,vlans,device):
        '''Swaps Key and Values and converts VLANS to Nautobot IDs or creates it if it doesnt exsist'''
        newdict = {}
        #find the group cause you'll need it later
        # Check that group exsists & create it if it dont
        device = self.pynb.dcim.devices.get(name=str(device))
        vlangroup = self.pynb.ipam.vlan_groups.get(name=str(group))
        if vlangroup is None:
            vlangroup = self.pynb.ipam.vlan_groups.create(
                name=str(group),
                site=device.site.id,
                slug=str(group).lower()
            )
        tenant_group = self.pynb.tenancy.tenants.get(name=str(group))
        if tenant_group is None:
            tenant_group = self.pynb.tenancy.tenants.create(
                name =str(group).lower()
            )

        if not isinstance(vlans, dict):
            raise Exception("vlan arg must be a dictionary")
        for k, v in vlans.items():
            vlanid = self.pynb.ipam.vlans.get(
                vid=str(k),
                group_id=vlangroup.id
            )
            if vlanid is None:
                vlanid = self.pynb.ipam.vlans.create(
                    name=str(k),
                    vid=k,
                    group=str(vlangroup.id),
                    site=device.site.id,
                    status='active',
                    description=str(v['name']),
                    tenant=tenant_group.id
                )
            else:
                vlanid.update({
                    'name' : str(k),
                    'vid' : k,
                    'group' : str(vlangroup.id),
                    'site' : device.site.id,
                    'status' : 'active',
                    'description' : str(v['name']),
                    'tenant' : tenant_group.id
                })
            for j in v['interfaces']:
                if j in newdict:
                    #if the key is already there add the vlan
                    newdict[j].append(vlanid.id)
                else:
                    newdict[j] = [vlanid.id]
        return(newdict)

    def _linkSVItoImportVlan(self,group,device):
        #TODO :
        '''Iterates through the interfaces and tries to link SVI to nautobot VLAN object'''
        device = self.pynb.dcim.devices.get(name=str(device))
        device_interfaces = self.pynb.dcim.interfaces.filter(device_id=device.id)
        for interface in device_interfaces:
            #check to see if tenancy is linked here
            '''This code will only work when we have a SVI, wont work with stuff like portchanels etc'''
            if 'Vlan' in interface.name:
                interface_name_strip = interface.name.strip('Vlan') #Vlan110 --> 110
                vidQuery = self.pynb.ipam.vlans.get(name=str(interface_name_strip), group=group)
                #if the vlan exsists
                if vidQuery is not None:
                    interface.update({
                        'mode' : 'tagged',
                        'tagged_vlans' : [vidQuery.id]
                    })
                    #then we call this function that links the VLAN ID to the Prefix itself
                    try:
                     self._linkPrefixtoVlan(interface_id=interface.id, vlan_nb_id=vidQuery.id)
                    except Exception as e:
                        logging.warning(e)

    def _linkPrefixtoVlan(self, interface_id,vlan_nb_id):
        '''Tested this code on 08 01 22 the prefix.update method is still valid way of updting the prefix'''
        #Grab all da ips assocaited with da interface
        interface_addresses = self.pynb.ipam.ip_addresses.filter(interface_id)
        if len(interface_addresses) == 0:
            raise Exception(f'Interface ID {interface_id} as not prefixes assigned')
        else:
            for ips in interface_addresses:
            #grab the ip and turn it into a prefix
                prefix_obj = ipaddress.ip_network(ips, strict=False)
                '''If pulling the prefix by ID, it is not necessary to pass along param, just put the ID in the parent'''
                prefix = self.pynb.ipam.prefixes.get(prefix=prefix_obj.with_prefixlen)
                #add code to create prefix if it doesnt exsist?
                logging.info(f"trying to link prefix {prefix} to ID {vlan_nb_id}")
                try:
                    prefix.update({
                        'vlan': vlan_nb_id
                    })
                    logging.info(f'Linked Prefix {prefix} to VLAN ID {vlan_nb_id}')
                except:
                    logging.warning(f'Unable to link a prefix for interface to VLAN ID {vlan_nb_id}')

    def _vlanimporter(self,group, device):
        '''dumps them vlans into them groups and links it to the SVI created'''
        # query Device
        device_object = self.pynb.dcim.devices.get(name=str(device))
        if 'cisco_iosxe' in device_object.platform.slug:
            logging.info('IOS XE - Just parsing Portchannels for VLANS')
            self._parseportchannelvlans(device,group)
            logging.info(f"Linking SVIs to VLAN Objects for {device_object.name}")
            self._linkSVItoImportVlan(group, device)
            logging.info(f'''IPv6 Houskeeping on {device_object.name}''')
            self._getipv6(device)

        elif 'l2' in device_object.name:
            # TODO Move this to a dev branch?
            logging.info("Layer 2 device - only need VLANS")
            vlans = self._getvlans(device_object.name)
            vlans = self._formatnapalmvlandict(group, vlans, device)
            tenant_group = self.pynb.tenancy.tenants.get(name=str(group))
            if device_object.tenant is None:
                device_object.update({
                    'tenant': tenant_group.id
                })
            else:
                device_object.update({
                    'tenant': tenant_group.id
                })
            for interface, vlan in vlans.items():
                '''query interface object'''
                logging.info(interface)
                interfaceQuery = self.pynb.dcim.interfaces.get(
                    name__ie=str(interface),
                    device_id=device_object.id
                )
                if interfaceQuery is None:
                    logging.warning(f'Interface: {interface} does not match SOT list - Skipping!')
                    continue

                if len(vlan) == 1:
                    logging.info(f"Setting {interfaceQuery.name} on {device_object.name} as access port with VLAN {vlan[0]}")
                    '''if the interface exsist but has no vlans or mode set
                    update and link curent vlan to vlan we are
                    set the interface as access'''
                    logging.info('setting int as untagged')
                    interfaceQuery.update({
                        'mode':          'access',
                        'untagged_vlan': vlan[0]
                    })
                else:
                    '''If vlan dict value list is longer than 1'''
                    logging.info(f"Setting {interfaceQuery.name} on {device_object.name} as Trunk with tagged")
                    interfaceQuery.update({
                        'mode':         'tagged',
                        'tagged_vlans': vlan
                    })
                    interface_ips = self.pynb.ipam.ip_addresses.filter(interface_id=interfaceQuery.id)
                    for ips in interface_ips:
                        for vid in vlan:
                            ips.update({
                                'assigned_object_type': 'ipam.vlans',
                                'assigned_object_id':   vid,
                                'tenant':               tenant_group.id
                            })

        else:
            # assumes this is IOS or other
            #pull VLANs from Device directly
            vlans = self._getvlans(device)
            #convert the Dict to something thats easier to use here
            vlans = self._formatnapalmvlandict(group,vlans,device)
            #check tenancy of device
            tenant_group = self.pynb.tenancy.tenants.get(name=str(group).lower())
            if device_object.tenant is None:
                device_object.update({
                    'tenant' : tenant_group.id
                })
            else:
                device_object.update({
                    'tenant': tenant_group.id
                })
            # working w/ the dict here
            for interface,vlan in vlans.items():
                '''query interface object'''
                interfaceQuery = self.pynb.dcim.interfaces.get(
                    name=str(interface),
                    device_id=device_object.id
                )
                if interfaceQuery is None:
                    logging.warning(f'Interface: {interface} does not match SOT list - Skipping!')
                    continue

                if len(vlan) == 1:
                    logging.info(f"Setting {interfaceQuery.name} on {device_object.name} as access port with VLAN {vlan[0]}")
                    '''if the interface exsist but has no vlans or mode set
                    update and link curent vlan to vlan we are
                    set the interface as access'''
                    logging.info('setting int as untagged')
                    interfaceQuery.update({
                        'mode' : 'access',
                        'untagged_vlan' : vlan[0]
                    })
                else:
                    '''If vlan dict value list is longer than 1'''
                    logging.info(f"Setting {interfaceQuery.name} on {device_object.name} as Trunk with tagged")
                    interfaceQuery.update({
                        'mode' : 'tagged',
                        'tagged_vlans' : vlan
                    })
                    self._linkSVItoImportVlan(group, device)
                    #interface_ips = self.pynb.ipam.ip_addresses.filter(interface_id=interfaceQuery.id)

                    # # Try to link the IP to the VLAN
                    # for ips in interface_ips:
                    #     for vid in vlan:
                    #         ips.update({
                    #             'assigned_object_type': 'ipam.vlans',
                    #             'assigned_object_id':   vid,
                    #             'tenant':               tenant_group.id
                    #         })
            #Link VLANs to SVI
            logging.info(f"Linking SVIs to VLAN Objects for {device_object.name}")
            try:
                self._linkSVItoImportVlan(group,device)
            except:
                logging.warning(f'Something went wrong importing SVIs on {device_object.name}')
            #Parse port channels
            try:
                logging.info("Parsing portchannels")
                self._parseportchannelvlans(device_object.name, group)
            except:
                logging.warning(f'Something went wrong importing portchannel vlans on {device_object.name}')

            #IPv6 House keeping since we are already on the device
            try:
                logging.info(f'''IPv6 Houskeeping on {device_object.name}''')
                self._getipv6(device_object.name)
            except:
                logging.warning(f'Something went wrong importing IPV6 on {device_object.name}')

    def importdevicevlans(self,group, selected_devices=[]):
        if len(selected_devices) == 0:
            raise("No devices given")
        elif len(selected_devices) == 1:
            self._vlanimporter(group,selected_devices[0])
        elif len(selected_devices) > 1:
            gpool = gevent.pool.Pool(100)
            for device in selected_devices:
                gpool.spawn(self._vlanimporter(group, device))

if __name__ == "__main__":
    nbv = NautobotCleanerVlans()
    nbv.importdevicevlans(group='ds121-l3', selected_devices=['dsc121.gsc.webair.net', 'dsd121.gsc.webair.net'])

        


