
from netmiko import ConnectHandler
from config import nautobot_url, nautobot_token,device_username,device_password
import pynautobot
import ipaddress
import gevent
import gevent.pool
import logging
from datetime import datetime

class NautobotCleanerRoutes():
    def __init__(self):
        self.pynb = pynautobot.api(nautobot_url, token=nautobot_token)
        self.runTime = datetime.now()
        logging.basicConfig(filename=f'ROUTES/{self.runTime}_routes.log',level=logging.DEBUG)

    ######################
    # IP And Prefix Tool Functions
    ######################
    def _findprefix(self, ip):
        '''Takes an IP address and attempts find it in nautobot to get prefix length
            Uses that to compute the prefix and queries that in nautobot to get the VLAN ID if its associated'''
        ip_lookup = self.pynb.ipam.ip_addresses.filter(str(ip))
        if len(ip_lookup) == 0:
            logging.debug('Could not Find the IP address in Nautobot')
            return None
        prefix_check = ipaddress.ip_network(ip_lookup[0], strict=False)
        try:
            prefix_lookup = self.pynb.ipam.prefixes.get(prefix=prefix_check.with_prefixlen)
        except:
            logging.debug('Could not Find the Parent Prefix in Nautobot')
        return prefix_lookup

    def _isIP(self, network):
        try:
            ipaddress.ip_network(network)
            return True
        except:
            return False

    ######################
    #Nautobot Tool Functions
    ######################
    def _get_prefix(self, **kwargs):
        if 'vlan' in kwargs:
            return self.pynb.ipam.prefixes.get(
                prefix=kwargs.get('prefix'),
                site_id=kwargs.get('site'),
                vlan=kwargs.get('vlan')
            )
        else:
            return self.pynb.ipam.prefixes.get(
                prefix=kwargs.get('prefix'),
                site_id=kwargs.get('site'),
            )
    def _create_or_update_prefix(self, data):
        if 'vlan' in data:
            self.pynb.ipam.prefixes.create(
                prefix=str(data['prefix_join']),
                status='active',
                site=data['device_object.site.id'],
                vlan=data['vlan']
            )
        else:
            self.pynb.ipam.prefixes.create(
                prefix=str(data['prefix_join']),
                status='active',
                site=data['device_object.site.id'],
            )




    def _getstaticroutes(self, device):
        '''uses netmiko and NTC textfsm tempalte to pull static routes'''
        logging.debug(f'Import prefix from routing table for {device}')
        device_object = self.pynb.dcim.devices.get(name=str(device))
        # device_os = device_platform_connection[str(device.platform)]['os']
        net_connect = ConnectHandler(
            device_type='cisco_ios',
            host=str(device),
            username=str(device_username),
            password=str(device_password),
            secret=str(device_password)
        )
        net_connect.find_prompt()
        output = net_connect.send_command('show ip route static',use_textfsm=True)
        logging.debug(f'routing table info {output}')
        for data in output:
            '''If Null0 set as conatiner'''
            prefix_join = f'''{data['network']}/{data['mask']}'''
            prefix_check = self._isIP(prefix_join)
            logging.debug(f'Import prefix {prefix_join}')
            if prefix_check != True:
                continue
            if data['nexthop_if'] == 'Null0':
                prefix_object = self.pynb.ipam.prefixes.get(
                    prefix=str(prefix_join),
                    site_id=device_object.site.id,
                    #tenant_id = device_object.tenant.id
                )
                #queries the prefix
                # if it does not exsist: creates the prefix and sets it as a container
                if prefix_object is None:
                    self.pynb.ipam.prefixes.create(
                        prefix= str(prefix_join),
                        status='container',
                        site=device_object.site.id,
                        #tenant=device_object.tenant.id
                    )
                else:
                    #otherwise it updates it as a container
                    prefix_object.update({
                        'prefix':str(prefix_join),
                        'status':'container',
                        'site':device_object.site.id,
                        'tenant':device_object.tenant.id
                    })
            else:
                '''Else logic if next hop is not Null0'''
                # we pull the prefix from the next hop IP
                nexthop_prefix = self._findprefix(data['nexthop_ip'])
                if nexthop_prefix is None:

                #see if the prefix we want to create is already in nautobot
                    prefix_object = self.pynb.ipam.prefixes.get(
                        prefix=str(prefix_join),
                        #status='container',
                        site_id=device_object.site.id,
                        #tenant_id=device_object.tenant.id
                    )
                    if prefix_object is None:
                        self.pynb.ipam.prefixes.create(
                            prefix=str(prefix_join),
                            status='active',
                            site=device_object.site.id,
                            vlan=nexthop_prefix.vlan.id
                            #tenant=device_object.tenant.id
                        )
                    else:
                        prefix_object.update({
                            'prefix': str(prefix_join),
                            'status': 'active',
                            'site':   device_object.site.id,
                            'vlan' : nexthop_prefix.vlan.id
                            #'tenant': device_object.tenant.id
                        })

                # TODO Link the prefix with the same VLAN ID as its next hop if not NULL0

    def importdevicestaticroutes(self, selected_devices=[]):
        if len(selected_devices) == 0:
            raise('no devices given')
        elif len(selected_devices) == 1:
            self._getstaticroutes(selected_devices[0])
        elif len(selected_devices) > 1:
            gpool = gevent.pool.Pool(100)
            for device in selected_devices:
                gpool.spawn(self._getstaticroutes(device))




