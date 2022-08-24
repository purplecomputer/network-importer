import requests
import gevent
import gevent.pool
import logging
from datetime import datetime
import pynautobot
from config import nb_url, nb_token
import sys


class ImportClientIDs():
    def __init__(self):
        self.pynb = pynautobot.api(nb_url, token=nb_token)
        self.runTime = datetime.now()
        logging.basicConfig(filename=f'synclogs/CID/{self.runTime}_cid.log', level=logging.INFO)

    def _update_or_create_tenant(self, **kwargs ):
        '''Finds the tenant, if not cretes it and returns ID'''
        tenant_group = self.pynb.tenancy.tenants.get(name=f"{kwargs.get('CID')}-{kwargs.get('site')}-{kwargs.get('service')}")
        if tenant_group is None:
            tenant_group = self.pynb.tenancy.tenants.create(
                name=f"{kwargs.get('CID')}-{kwargs.get('site')}-{kwargs.get('service')}"
            )
            return tenant_group.id
        else:
            tenant_group.update({
                'name' : f"{kwargs.get('CID')}-{kwargs.get('site')}-{kwargs.get('service')}"
            }
            )
            return tenant_group.id


    def _fetchscpid(self,ip):
        if "/" in str(ip):
            logging.debug(ip)
            ip = str(ip).split("/")[0]
        else:
            pass
        logging.debug(ip)
        clientID = requests.get(f'http://admin.webair.com/cgi-bin/clientbyip.cgi?ip={ip}')
        if clientID.status_code != 200:
            logging.debug(f'could not find CID for : {ip}')
            return None
            exit(1)
        else:
            logging.debug(f"Found CID:{clientID.json()['cid']} for {ip}")
            return clientID.json()['cid']
    def _add_tenant_to_prefix(self,prefix_id):
        try:
            prefix_object = self.pynb.ipam.prefixes.get(prefix_id)
        except:
            logging.warning(f"Could not locate the following prefix ID: {prefix_id}")
            raise
        cid = self._fetchscpid(prefix_object)
        tenant_id = self._update_or_create_tenant(CID=cid,site=prefix_object.site,service='DIA')
        try:
            prefix_object.update({
                'tenant' : tenant_id
            }
            )
        except Exception as e:
            logging.warning(f"Could not add the custom field due to the following error - {e}")
        logging.debug(f"Succesfully linked tenant object {tenant_id} to prefix {prefix_id}")

    def _add_cid_to_cf(self,prefix):
        try:
            prefix_object = self.pynb.ipam.prefixes.get(prefix)
        except:
            logging.warning(f"Could not locate the following prefix {prefix}")
            raise
        cid = self._fetchscpid(prefix_object)
        try:
            prefix_object.update({
                "custom_fields": {
                    "Client ID Number": str(cid)
            }
            }
            )
        except Exception as e:
            logging.warning(f"Could not add the custom field due to the following error - {e}")


    def linkclientidtoip(self):
        gpool = gevent.pool.Pool(100)
        all_prefixes = self.pynb.ipam.prefixes.all()
        for prefix in all_prefixes:
            gpool.spawn(self._add_tenant_to_prefix(prefix.id))

