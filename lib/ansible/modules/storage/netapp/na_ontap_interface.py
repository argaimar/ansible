#!/usr/bin/python
""" this is interface module

 (c) 2018, NetApp, Inc
 # GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'certified'
}

DOCUMENTATION = '''
---

module: na_ontap_interface
short_description: NetApp ONTAP LIF configuration

extends_documentation_fragment:
    - netapp.na_ontap
version_added: '2.6'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
    - Creating / deleting and modifying the LIF.

options:
  state:
    description:
    - Whether the specified interface should exist or not.
    choices: ['present', 'absent']
    default: present

  interface_name:
    description:
    - Specifies the logical interface (LIF) name.
    required: true

  home_node:
    description:
    - Specifies the LIF's home node.
    - Required when C(state=present).

  home_port:
    description:
    - Specifies the LIF's home port.
    - Required when C(state=present)

  role:
    description:
    - Specifies the role of the LIF.
    - When setting role as "intercluster", setting protocol is not supported.
    - Required when C(state=present).

  address:
    description:
    - Specifies the LIF's IP address.
    - Required when C(state=present)

  netmask:
    description:
    - Specifies the LIF's netmask.
    - Required when C(state=present).

  vserver:
    description:
    - The name of the vserver to use.
    required: true

  firewall_policy:
    description:
    - Specifies the firewall policy for the LIF.

  failover_policy:
    description:
    - Specifies the failover policy for the LIF.
    - Possible values are 'disabled', 'system-defined', 'local-only', 'sfo-partner-only', and 'broadcast-domain-wide'

  subnet_name:
    description:
    - Subnet where the interface address is allocated from.
      If the option is not used, the IP address will need to be provided by
      the administrator during configuration.
    version_added: '2.8'

  admin_status:
    choices: ['up', 'down']
    description:
    - Specifies the administrative status of the LIF.

  is_auto_revert:
    description:
       If true, data LIF will revert to its home node under certain circumstances such as startup, and load balancing
       migration capability is disabled automatically
    type: bool

  protocols:
    description:
       Specifies the list of data protocols configured on the LIF. By default, the values in this element are nfs, cifs and fcache.
       Other supported protocols are iscsi and fcp. A LIF can be configured to not support any data protocols by specifying 'none'.
       Protocol values of none, iscsi or fcp can't be combined with any other data protocol(s).

'''

EXAMPLES = '''
    - name: Create interface
      na_ontap_interface:
        state: present
        interface_name: data2
        home_port: e0d
        home_node: laurentn-vsim1
        role: data
        protocols: nfs
        admin_status: up
        failover_policy: local-only
        firewall_policy: mgmt
        is_auto_revert: true
        address: 10.10.10.10
        netmask: 255.255.255.0
        vserver: svm1
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Delete interface
      na_ontap_interface:
        state: absent
        interface_name: data2
        vserver: svm1
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

'''

RETURN = """

"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.netapp_module import NetAppModule
from ansible.module_utils._text import to_native
import ansible.module_utils.netapp as netapp_utils

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapInterface(object):
    ''' object to describe  interface info '''
    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=[
                       'present', 'absent'], default='present'),
            interface_name=dict(required=True, type='str'),
            home_node=dict(required=False, type='str', default=None),
            home_port=dict(required=False, type='str'),
            role=dict(required=False, type='str'),
            address=dict(required=False, type='str'),
            netmask=dict(required=False, type='str'),
            vserver=dict(required=True, type='str'),
            firewall_policy=dict(required=False, type='str', default=None),
            failover_policy=dict(required=False, type='str', default=None),
            admin_status=dict(required=False, choices=['up', 'down']),
            subnet_name=dict(required=False, type='str'),
            is_auto_revert=dict(required=False, type=bool, default=None),
            protocols=dict(required=False, type='list')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(
                msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_interface(self, interface_name=None):
        """
        Return details about the interface
        :param:
            name : Name of the name of the interface

        :return: Details about the interface. None if not found.
        :rtype: dict
        """
        if interface_name is None:
            interface_name = self.parameters['interface_name']
        interface_info = netapp_utils.zapi.NaElement('net-interface-get-iter')
        interface_attributes = netapp_utils.zapi.NaElement('net-interface-info')
        interface_attributes.add_new_child('interface-name', interface_name)
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(interface_attributes)
        interface_info.add_child_elem(query)
        result = self.server.invoke_successfully(interface_info, True)
        return_value = None

        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) >= 1:

            interface_attributes = result.get_child_by_name('attributes-list').\
                get_child_by_name('net-interface-info')
            return_value = {
                'interface_name': self.parameters['interface_name'],
                'admin_status': interface_attributes['administrative-status'],
                'home_port': interface_attributes['home-port'],
                'home_node': interface_attributes['home-node'],
                'address': interface_attributes['address'],
                'netmask': interface_attributes['netmask'],
                'failover_policy': interface_attributes['failover-policy'].replace('_', '-'),
                'firewall_policy': interface_attributes['firewall-policy'],
                'is_auto_revert': True if interface_attributes['is-auto-revert'] == 'true' else False,
            }
        return return_value

    def set_options(self, options, parameters):
        """ set attributes for create or modify """
        if parameters.get('home_port') is not None:
            options['home-port'] = parameters['home_port']
        if parameters.get('subnet_name') is not None:
            options['subnet-name'] = parameters['subnet_name']
        if parameters.get('address') is not None:
            options['address'] = parameters['address']
        if parameters.get('netmask') is not None:
            options['netmask'] = parameters['netmask']
        if parameters.get('failover_policy') is not None:
            options['failover-policy'] = parameters['failover_policy']
        if parameters.get('firewall_policy') is not None:
            options['firewall-policy'] = parameters['firewall_policy']
        if parameters.get('is_auto_revert') is not None:
            options['is-auto-revert'] = 'true' if parameters['is_auto_revert'] is True else 'false'
        if parameters.get('admin_status') is not None:
            options['administrative-status'] = parameters['admin_status']

    def create_interface(self):
        ''' calling zapi to create interface '''
        # validate if mandatory parameters are present for create
        required_keys = set(['role', 'address', 'home_node', 'home_port', 'netmask'])
        if not required_keys.issubset(set(self.parameters.keys())):
            self.module.fail_json(msg='Error: Missing one or more required parameters for creating interface: %s'
                                  % ', '.join(required_keys))
        # if role is intercluster, protocol cannot be specified
        if self.parameters['role'] == "intercluster" and self.parameters.get('protocols') is not None:
            self.module.fail_json(msg='Error: Protocol cannot be specified for intercluster role,'
                                      'failed to create interface')
        options = {'interface-name': self.parameters['interface_name'],
                   'role': self.parameters['role'],
                   'home-node': self.parameters.get('home_node'),
                   'vserver': self.parameters['vserver']}
        self.set_options(options, self.parameters)
        interface_create = netapp_utils.zapi.NaElement.create_node_with_children('net-interface-create', **options)
        if self.parameters.get('protocols') is not None:
            data_protocols_obj = netapp_utils.zapi.NaElement('data-protocols')
            interface_create.add_child_elem(data_protocols_obj)
            for protocol in self.parameters.get('protocols'):
                data_protocols_obj.add_new_child('data-protocol', protocol)
        try:
            self.server.invoke_successfully(interface_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error Creating interface %s: %s' %
                                  (self.parameters['interface_name'], to_native(exc)), exception=traceback.format_exc())

    def delete_interface(self, current_status):
        ''' calling zapi to delete interface '''
        if current_status == 'up':
            self.parameters['admin_status'] = 'down'
            self.modify_interface({'admin_status': 'down'})

        interface_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'net-interface-delete', **{'interface-name': self.parameters['interface_name'],
                                       'vserver': self.parameters['vserver']})
        try:
            self.server.invoke_successfully(interface_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error deleting interface %s: %s' % (self.parameters['interface_name'], to_native(exc)),
                                  exception=traceback.format_exc())

    def modify_interface(self, modify):
        """
        Modify the interface.
        """
        options = {'interface-name': self.parameters['interface_name'],
                   'vserver': self.parameters['vserver']
                   }
        self.set_options(options, modify)
        interface_modify = netapp_utils.zapi.NaElement.create_node_with_children('net-interface-modify', **options)
        try:
            self.server.invoke_successfully(interface_modify, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as err:
            self.module.fail_json(msg='Error modifying interface %s: %s' % (self.parameters['interface_name'],
                                  to_native(err)), exception=traceback.format_exc())

    def autosupport_log(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(
            module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_interface", cserver)

    def apply(self):
        ''' calling all interface features '''
        self.autosupport_log()
        current = self.get_interface()
        # rename and create are mutually exclusive
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_interface()
                elif cd_action == 'delete':
                    self.delete_interface(current['admin_status'])
                elif modify:
                    self.modify_interface(modify)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    interface = NetAppOntapInterface()
    interface.apply()


if __name__ == '__main__':
    main()
