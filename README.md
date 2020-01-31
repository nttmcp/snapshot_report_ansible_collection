# MCP Snapshot Management and Reporting using Ansible

This collection of Playbooks can be used to enable the snapshot service on servers as well as report on snapshot status

## Information
**Version:** 1.0.0

**Author:** Ken Sinfield <ken.sinfield@cis.ntt.com>

## Requirements

### Reporting System Requirements

* <250 servers 2GB of RAM 2 vCPUs
* 250-750 servers 4GB of RAM 2 vCPUs
* \>750 servers 6GB of RAM 2 vCPUs
* Running 2 simultaneous reports against 2 different MCPs: Double the RAM and vCPU count

### Ansible Version

* >2.9

### Python Modules

* jmespath
* requests
* configparser
* PyOpenSSL
* netaddr
* Jinja2
* PyYaml

To install these modules execute:

> pip install --user jmespath requests configparser PyOpenSSL netaddr Jinja2 PyYaml


## Ansible Collection(s)

Additionally, the NTTMCP-MCP Ansible collection is required.

https://galaxy.ansible.com/nttmcp/mcp

> ansible-galaxy collection install nttmcp.mcp


## Authentication

Configure Cloud Control credentials by creating/editing a `.nttmcp` file in your home directory containing the following information:

    [nttmcp]
    NTTMCP_API: api-<geo>.mcp-services.net
    NTTMCP_API_VERSION: 2.10
    NTTMCP_PASSWORD: mypassword
    NTTMCP_USER: myusername

OR

Use environment variables:

    set +o history
    export NTTMCP_API=api-<geo>.mcp-services.net
    export NTTMCP_API_VERSION=2.10
    export NTTMCP_PASSWORD=mypassword
    export NTTMCP_USER=myusername
    set -o history


## Playbooks

* **snapshot_report.yml** -- Use to generate a report showing servers with snapshots enabled and any failed snapshots

* **snapshot_service.yml** -- Use to enable snapshots for a provided list of servers using meta data tags within Cloud Control

* **snapshot_server_csv.yml** -- Use to enable snapshots for a provided list of servers via a CSV file (use example_server_input.csv as a template)

### snapshot_report.yml

* Update **region** and **mcp** extra-vars to the desired region and MCP ID.
* Optionally include a Cloud Network Domain with the variable **cnd** to limit the reporting to a specific Cloud Network Domain. Otherwise all servers within the MCP will be reported on

> snapshot_report.yml -e"region=na mcp=NA9"

### snapshot_service.yml

* Use with caution still in beta
* Update **region**, **mcp** (MCP ID where the servers are hosted), **rep_mcp** (MCP ID to be used for replication)
* Optionally include a Cloud Network Domain with the variable **cnd** to limit the reporting to a specific Cloud Network Domain. Otherwise all servers within the MCP will be reported on
* Tag names by default are 'snapshot' for the snapshot plan name and 'window' for the start time of the snapshot
* Default tag value mappings to Cloud Control snapshot plans can be found (and modified) in files/snapshot_config.json
* No batching at this stage so do not use for large numbers of servers (e.g. more than 15 at a time)
* Will skip servers that have already been enabled and had an initial snapshot taken (idempotent)
* Monitor snapshot.log for progress reports

> ansible-playbook snapshot_service.yml -e"region=na mcp=na9 rep_mcp=na12"

### snapshot_service_csv.yml

* Update **region**, **csv**, **primary_mcp** (MCP ID where the servers are hosted) and **secondary_mcp** (MCP ID to be used for replication)
* Takes an initial snapshot of the server once the service has successfully been enabled
* By default will process servers in batches of 15 servers at a time and pause for 30min to allow for the initial manual snapshot to be taken before proceeding
* Will skip servers that have already been enabled and had an initial snapshot taken (idempotent)
* Monitor snapshot.log for progress reports

> ansible-playbook snapshot_service_csv.yml -e"region=na csv=my_csv.csv primary_mcp=NA9 secondary_mcp=NA12"
