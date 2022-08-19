# Nautobot Cleaner

### what it does?

Cleaner isnt the best word, but it helps to import data that network importer does not do well in a multi-tenant enviroment.

### How it works?

Uses a mix of Napalm and Netmiko to parse vlan & static route information and create it in Nautobot

## Importing VLANs

```python
from importdevicevlans import NautobotCleanerVlans

nbv = NautobotCleanerVlans()
nbv.importdevicevlans(selected_devices=[
    'device1-fqdn',
    'device2-fqdn',
],
    group='vlan-group')
```
```mermaid
graph TD
start
yes
no
q1['Is device IOSXE?']
q2['Is device layer 2?']

start-->q1
start-->q2

q1-->no
no-->a1['Pull VLANS from device DB']
a1-->a2['reverse getvlan dict']
a2-->a3['create vlans, assign to group and link to interface']
a3-->a4['link VLAN to SVI and prefix']
a4-->a5['Parse port channels and link vlans']
a5-->a6['Link Import IPv6']

q1-->yes
yes-->b1['parse only port channels']
b1-->b2['create vlans, assign to group and link to interface']
b2-->b3['link VLAN to SVI and prefix']
b3-->b4['Import IPv6']

q2-->c1['Pull VLANS from device DB']
c1-->c2['reverse getvlan dict']
c2-->c3['create vlans, assign to group and link to interface']
c3-->c4['link VLAN to SVI and prefix']
```

## Importing Static routes

We are using the devices static route table to import prefixes direclty into Nautobot.

To use, import and instatiate, then call the method as such

```Python
from importdeviceroutes import NautobotCleanerRoutes

nbr = NautobotCleanerRoutes()
nbr.importdevicestaticroutes(selected_devices=[
        'router1.acme.com',
        'router2.acme.com',
    ])
```

```mermaid
graph TD

s['start']
s-->a1['Login and pull route table']
a1-->a2['iterate over prefixes and check if it is valid']
a2-->q1['prefix is valid']
a2-->q2['prefix is not valid']
q1-->a3['Create or Update prefix object in Nautobot']
q2-->a4['Return none']

```

## Importing from LibreNMS

This function just pulls the device information based on groups from Librenms to populate Nautobot

Instatiate the class and run the method. Currently it expect a group name from Librensm. It must match!

```python
from netmonimporter import NautobotCleanerNetmonImport

nbn = NautobotCleanerNetmonImport()

nbn.add_device_to_nautobot(deviceGroup=[
        'ACME_ROUTERS'
    ])
```

part of the inventory build is to match the mgmt interface that the resolved IP of the FQDN uses to its interface. 
This is needed as it is important to stage this for the Network Imported from Network To Code

