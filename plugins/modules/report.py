#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020, NTT Ltd.
#
# Author: Ken Sinfield <ken.sinfield@cis.ntt.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'Ken Sinfield <ken.sinfield@cis.ntt.com>'
}

DOCUMENTATION = '''
---
module: report
short_description: Generate a set of reports for servers within a specified MCP
description:
    - Generate reports for server snapshots
    - Reports are generated from the templates/ directory and written to reports/
version_added: "2.10"
author:
    - Ken Sinfield (@kensinfield)
options:
    region:
        description:
            - The geographical region
        required: false
        type: str
        default: na
    datacenter:
        description:
            - The datacenter name
        required: true
        type: str
    network_domain:
        description:
            - The name of a Cloud Network Domain
            - Used to limit the search space for servers. Without a network domain
        required: false
        type: str
notes:
    - Requires NTT Ltd. MCP account/credentials
    - Requires nttmcp.mcp Ansible Galaxy Collection
    - ansible-galaxy collection install nttmcp.mcp -f
requirements:
    - requests
    - configparser
    - pyOpenSSL
    - netaddr
'''

EXAMPLES = '''
- hosts: 127.0.0.1
  connection: local
  tasks:

  - name: Run a report on all servers in NA12 in the CND myCND
    kensinfield.snapshot_report.report:
      region: na
      datacenter: NA12
      network_domain: myCND
'''

RETURN = '''
msg:
    description: A cool message
    type: str
    returned: always
servers:
    description: The number of servers found and processed
    type: int
    returned: success
snapshot_servers:
    description: The number of servers found with the snapshot service enabled
    type: int
    returned: success
'''

from ansible.module_utils.basic import AnsibleModule
try:
    from ansible_collections.nttmcp.mcp.plugins.module_utils.utils import get_credentials, get_regions
    from ansible_collections.nttmcp.mcp.plugins.module_utils.provider import NTTMCPClient, NTTMCPAPIException
    HAS_NTTMCP = True
except ImportError:
    HAS_NTTMCP = False
try:
    from jinja2 import Environment, FileSystemLoader
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
import os

# Python3 workaround for unicode function so the same code can be used with ipaddress later
try:
    unicode('')
except NameError:
    unicode = str


def main():
    """
    Main function
    :returns: Snapshot Report Data
    """
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', type='str'),
            datacenter=dict(required=True, type='str'),
            network_domain=dict(type='str')
        ),
        supports_check_mode=True
    )

    if not HAS_NTTMCP:
        module.fail_json(msg='This module requires the nttmcp.mcp Ansible Galaxy collection')
    if not HAS_JINJA2:
        module.fail_json(msg='This module requires the jinja2 Python module')

    try:
        credentials = get_credentials(module)
    except ImportError as e:
        module.fail_json(msg='{0}'.format(e))

    datacenter = module.params.get('datacenter')
    network_domain_name = module.params.get('network_domain')
    network_domain_id = None
    servers = list()
    servers_w_snapshots = list()
    failed_servers = list()
    failed_snapshots = list()
    snapshot_report = list()
    server_count = 0
    server_w_snapshot_count = 0
    total_snapshots = 0
    total_replica_snapshots = 0
    snapshot_dates = list()

    # Check the region supplied is valid
    regions = get_regions()
    if module.params.get('region') not in regions:
        module.fail_json(msg='Invalid region. Regions must be one of {0}'.format(regions))

    if credentials is False:
        module.fail_json(msg='Could not load the user credentials')

    try:
        client = NTTMCPClient(credentials, module.params.get('region'))
    except NTTMCPAPIException as e:
        module.fail_json(msg=e.msg)

    # Get the CND object based on the supplied name (if applicable)
    try:
        if network_domain_name:
            network_domain = client.get_network_domain_by_name(name=network_domain_name, datacenter=datacenter)
            network_domain_id = network_domain.get('id')
        else:
            network_domain_id = None
        if network_domain_name and not network_domain:
            module.fail_json(msg='Failed to locate the Cloud Network Domain - {0}'.format(network_domain_name))
    except (KeyError, IndexError, AttributeError, NTTMCPAPIException):
        module.fail_json(msg='Failed to locate the Cloud Network Domain - {0}'.format(network_domain_name))

    # Get a list of servers to process, filtering on the CND if one is supplied
    try:
        servers = client.list_servers(datacenter, network_domain_id, None, None)
    except NTTMCPAPIException as e:
        module.fail_json(msg='{0}'.format(e))

    server_count = len(servers)

    # Iterate around the list of servers and create a new list of servers that have the snapshot service enabled
    for server in servers:
        if server.get('snapshotService') is not None:
            servers_w_snapshots.append({
                                       'name': server.get('name'),
                                       'id': server.get('id'),
                                       'replication': True if server.get('snapshotService', {}).get('replicationTargetDatacenterId') is not None else False,
                                       'plan': server.get('snapshotService', {}).get('servicePlan'),
                                       'state': server.get('snapshotService', {}).get('state'),
                                       'family': server.get('guest', {}).get('operatingSystem', {}).get('family'),
                                       })
    server_w_snapshot_count = len(servers_w_snapshots)
    # For those servers with the snapshot service enabled, iterate around this list and gather stats on the snapshots
    for server in servers_w_snapshots:
        snapshot_count = 0
        server_failed_snapshots = 0
        local_snapshot = 0
        remote_snapshot = 0
        try:
            snapshots = client.list_snapshot(server.get('id'))
            if snapshots is None:
                failed_servers.append({'name': server.get('name'), 'id': server.get('id'), 'error': 'N/A'})
            else:
                snapshot_count = len(snapshots)
                total_snapshots += len(snapshots)
                for snapshot in snapshots:
                    # Create a list of tuples of snapshot creation times and state to be used to determine the date
                    # and state of the last snapshot later on
                    if not snapshot.get('replica', False):
                        snapshot_dates.append((snapshot.get('startTime'), snapshot.get('state')))
                    if snapshot.get('state') != 'NORMAL':
                        server_failed_snapshots += 1
                        failed_snapshots.append({
                                                'server': server.get('name'),
                                                'server_id': server.get('id'),
                                                'snapshot': snapshot.get('id'),
                                                'consistency': snapshot.get('consistencyLevel', 'N/A'),
                                                'state': snapshot.get('state', 'N/A'),
                                                'index': snapshot.get('indexState', 'N/A'),
                                                'start': snapshot.get('startTime', 'N/A'),
                                                'replica': snapshot.get('replica', False),
                                                'family': server.get('family')
                                                })
                    else:
                        if snapshot.get('type') == 'SYSTEM' and not snapshot.get('replica'):
                            local_snapshot += 1
                        elif snapshot.get('type') == 'SYSTEM' and snapshot.get('replica'):
                            remote_snapshot += 1
                            total_replica_snapshots += 1
                # This is now later on... we need to sort the list of tuples on the creation date (not the state)
                snapshot_dates.sort(key=lambda tmp_tuple: tmp_tuple[1])
            snapshot_report.append({
                                   'name': server.get('name'),
                                   'id': server.get('id'),
                                   'replication': server.get('replication'),
                                   'count': snapshot_count,
                                   'failed': server_failed_snapshots,
                                   'local': local_snapshot,
                                   'remote': remote_snapshot,
                                   'last': snapshot_dates.pop()[0],
                                   'last_state': snapshot_dates.pop()[1]
                                   })
        except (KeyError, NTTMCPAPIException) as e:
            failed_servers.append({'name': server.get('name'), 'id': server.get('id'), 'error': e})

    # Report generation time
    try:
        # Check stuff exists cause apparently it's the right thing to do
        if not os.path.exists('reports'):
            os.makedirs('reports')
        if not os.path.exists('templates'):
            module.fail_json('No templates directory found. Ensure you are in Collection directory before running')
        env = Environment(
            loader=FileSystemLoader('templates')
        )
        # Love me some hardcoding....... Will make these arguments at a later date
        summary_tmp = env.get_template('summary_report_csv.j2')
        failed_server_tmp = env.get_template('failed_server_report_csv.j2')
        failed_tmp = env.get_template('failed_report_csv.j2')
        server_tmp = env.get_template('server_report_csv.j2')
        # Oh yeah some repetitive code time
        # Generate the reports from the Jinja2 templates.
        f = open('reports/{0}_summary_report.csv'.format(datacenter), 'w')
        f.write('{0}\n'.format(summary_tmp.render(servers=server_count, snapshot_servers=len(servers_w_snapshots), snapshot_count=total_snapshots, snapshot_replica_count=total_replica_snapshots)))
        f.close()
        f = open('reports/{0}_failed_server_report.csv'.format(datacenter), 'w')
        f.write(failed_server_tmp.render(failed_servers=failed_servers))
        f.close()
        f = open('reports/{0}_failed_report.csv'.format(datacenter), 'w')
        f.write(failed_tmp.render(failed_report=failed_snapshots))
        f.close()
        f = open('reports/{0}_server_report.csv'.format(datacenter), 'w')
        f.write(server_tmp.render(server_report=snapshot_report))
        f.close()
    except OSError as e:
        module.fail_json(msg='Could not create the reports directory: {0}'.format(e))
    except Exception as e:
        module.fail_json(msg='Could not template out the reports: {0}'.format(e))

    # Hashtag goodtimes
    module.exit_json(msg="Success", servers=server_count, snapshot_servers=server_w_snapshot_count)


if __name__ == '__main__':
    main()
